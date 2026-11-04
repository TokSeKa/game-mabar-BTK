"""Server FastAPI: WebSocket untuk room, REST untuk arena latihan, dan file frontend."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .bot.errors import BotError
from .bot.library import LIBRARY_DOCS
from .bot.templates import TEMPLATE_BY_ID, TEMPLATES
from .bot.validator import compile_bot
from .compute import MatchRunner
from .config import Config, config as default_config
from .rooms.manager import RoomError, RoomManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("suitbot")

MAX_WS_MESSAGE = 64 * 1024


class CodeIn(BaseModel):
    code: str = Field(max_length=20_000)


class PracticeIn(BaseModel):
    code: str = Field(max_length=20_000)
    nama: str = Field(default="Botku", max_length=16)
    lawan: list[str] = Field(default_factory=list, max_length=7)
    settings: dict[str, Any] = Field(default_factory=dict)


def create_app(cfg: Config = default_config) -> FastAPI:
    runner = MatchRunner(cfg.match_workers, cfg.bot_max_steps)
    manager = RoomManager(runner.run, max_rooms=cfg.max_rooms, max_players=cfg.max_players,
                          player_grace=cfg.player_grace_seconds, room_idle=cfg.room_idle_seconds)
    practice_slots = asyncio.Semaphore(cfg.practice_concurrency)

    async def cleanup_loop() -> None:
        while True:
            await asyncio.sleep(60)
            try:
                await manager.cleanup()
            except Exception:  # noqa: BLE001
                log.exception("cleanup gagal")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(cleanup_loop())
        yield
        task.cancel()
        runner.shutdown()

    app = FastAPI(title="Suit Bot Arena", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.manager = manager

    # ------------------------------------------------------------ REST
    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "rooms": len(manager.rooms)}

    @app.get("/api/templates")
    async def templates() -> list[dict[str, str]]:
        return TEMPLATES

    @app.get("/api/library")
    async def library() -> dict[str, Any]:
        return {"fungsi": LIBRARY_DOCS, "max_langkah": cfg.bot_max_steps}

    @app.get("/api/guide", response_class=PlainTextResponse)
    async def guide() -> str:
        try:
            return cfg.guide_path.read_text(encoding="utf-8")
        except OSError:
            raise HTTPException(404, "Panduan tidak ditemukan") from None

    @app.post("/api/validate")
    async def validate(body: CodeIn) -> dict[str, Any]:
        try:
            compile_bot(body.code)
            return {"ok": True, "error": None}
        except BotError as e:
            return {"ok": False, "error": e.to_dict()}

    @app.post("/api/practice")
    async def practice(body: PracticeIn) -> JSONResponse:
        try:
            compile_bot(body.code)
        except BotError as e:
            return JSONResponse({"ok": False, "error": e.to_dict()})
        lawan = body.lawan or ["anti_mayoritas", "pemutar", "minoritas"]
        if any(t not in TEMPLATE_BY_ID for t in lawan):
            raise HTTPException(400, "Bot lawan tidak dikenal")
        nama = " ".join(body.nama.split()) or "Botku"
        entries = [(nama, body.code)]
        used = {nama.lower()}
        for t in lawan:
            base = TEMPLATE_BY_ID[t]["nama"]
            name, k = base, 2
            while name.lower() in used:
                name, k = f"{base} {k}", k + 1
            used.add(name.lower())
            entries.append((name, TEMPLATE_BY_ID[t]["kode"]))
        if practice_slots.locked():
            raise HTTPException(429, "Server sedang sibuk, coba lagi sebentar lagi.")
        async with practice_slots:
            result = await runner.run(entries, body.settings)
        colors = ["#7aa2ff", "#c29bff", "#ffd166", "#6ee7a8", "#ff9f7a", "#5ad1e6", "#f7a8d8", "#c9d36a"]
        public = {
            "id": "latihan",
            "settings": result["settings"],
            "players": [{"index": i, "id": f"p{i}", "name": n, "color": colors[i % 8]} for i, (n, _) in enumerate(entries)],
            "rounds": result["rounds"], "ranking": result["ranking"], "winners": result["winners"],
            "reason": result["reason"], "elim_round": result["elim_round"], "final_hp": result["final_hp"],
        }
        return JSONResponse({"ok": True, "match": public, "my_index": 0, "my_log": result["logs"][0]})

    # ------------------------------------------------------------ WebSocket
    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        lock = asyncio.Lock()

        async def send(msg: dict[str, Any]) -> None:
            async with lock:
                await ws.send_text(json.dumps(msg, separators=(",", ":")))

        room = player = None
        try:
            while True:
                raw = await ws.receive_text()
                if len(raw) > MAX_WS_MESSAGE:
                    await send({"type": "error", "message": "Pesan terlalu besar."})
                    continue
                try:
                    msg = json.loads(raw)
                    if not isinstance(msg, dict):
                        raise ValueError
                except ValueError:
                    await send({"type": "error", "message": "Format pesan tidak valid."})
                    continue
                try:
                    t = msg.get("type")
                    if player is None or room is None:
                        if t == "create_room":
                            room, player = await manager.create_room(msg.get("name"), send)
                        elif t == "join_room":
                            room, player = await manager.join_room(msg.get("code"), msg.get("name"), send)
                        elif t == "rejoin":
                            room, player = await manager.rejoin(msg.get("code"), msg.get("player_id"), msg.get("token"), send)
                        else:
                            raise RoomError("Masuk ke room dulu.")
                        await manager.after_join(room, player)
                        continue
                    if player.id not in room.players or manager.rooms.get(room.code) is not room:
                        await send({"type": "kicked"})
                        room = player = None
                        continue
                    if t == "leave_room":
                        await manager.leave(room, player)
                        await send({"type": "left"})
                        room = player = None
                        continue
                    await manager.handle(room, player, msg)
                except RoomError as e:
                    await send({"type": "error", "message": str(e)})
        except WebSocketDisconnect:
            pass
        except Exception:  # noqa: BLE001
            log.exception("websocket error")
        finally:
            if room is not None and player is not None and player.id in room.players:
                await manager.disconnect(room, player, send)

    # ------------------------------------------------------------ frontend
    if cfg.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=cfg.static_dir, html=True), name="static")
    else:
        @app.get("/")
        async def no_frontend() -> PlainTextResponse:
            return PlainTextResponse("Frontend belum dibuild. Jalankan `npm run build` di folder frontend.")

    return app


app = create_app()
