"""REST + WebSocket Arena Mabar (/api/main, /ws/main)."""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..bot.errors import BotError
from .guide import guide_markdown
from .registry import GAMES
from .rooms import ArenaManager, GameRoom, RoomError
from .runner import play_sync, sudut_sync
from .runtime import compile_for

log = logging.getLogger("arena")
MAX_MSG = 96 * 1024


class CodeIn(BaseModel):
    game: str = Field(max_length=40)
    kode: str = Field(max_length=20_000)


class LatihanIn(BaseModel):
    game: str = Field(max_length=40)
    kode: str = Field(max_length=20_000)
    nama: str = Field(default="Botku", max_length=16)
    lawan: list[str] = Field(default_factory=list, max_length=11)
    settings: dict[str, Any] = Field(default_factory=dict)


def _dumps(m: dict[str, Any]) -> str:
    return json.dumps(m, separators=(",", ":"), ensure_ascii=False, default=str)


def make_on_finish(db):
    def on_finish(room: GameRoom, result: dict[str, Any]) -> dict[str, Any] | None:
        if db is None:
            return None
        entries, who, seen = [], {}, set()
        for i, seat in enumerate(room.seats):
            owner = room.members.get(seat.owner)
            user = owner.user if owner else None
            if not user or user["id"] in seen:
                continue
            seen.add(user["id"])
            entries.append((user["id"], result["ranking"].index(i), float(result["skor"][i])))
            who[user["id"]] = seat.name
        out = db.rate(room.game.id, entries)
        return {who[uid]: v for uid, v in out.items()}
    return on_finish


def mount(app: FastAPI, pool=None, db=None) -> ArenaManager:
    mgr = ArenaManager(pool=pool, on_finish=make_on_finish(db))
    r = APIRouter()

    @r.get("/api/main/games")
    async def games() -> list[dict[str, Any]]:
        return [g.meta() for g in GAMES.values()]

    @r.get("/api/main/panduan/{game_id}", response_class=PlainTextResponse)
    async def panduan(game_id: str) -> str:
        g = GAMES.get(game_id)
        if g is None:
            raise HTTPException(404, "Game tidak dikenal")
        return guide_markdown(g)

    @r.post("/api/main/validasi")
    async def validasi(body: CodeIn) -> dict[str, Any]:
        g = GAMES.get(body.game)
        if g is None:
            raise HTTPException(404, "Game tidak dikenal")
        try:
            compile_for(g, body.kode)
            return {"ok": True, "error": None}
        except BotError as e:
            return {"ok": False, "error": e.to_dict()}

    @r.post("/api/main/latihan")
    async def latihan(body: LatihanIn) -> dict[str, Any]:
        g = GAMES.get(body.game)
        if g is None:
            raise HTTPException(404, "Game tidak dikenal")
        try:
            compile_for(g, body.kode)
        except BotError as e:
            return {"ok": False, "error": e.to_dict()}
        tpl = {t["id"]: t for t in g.templates}
        lawan = [x for x in body.lawan if x in tpl] or [t["id"] for t in g.templates[: max(1, g.min_pemain - 1)]]
        lawan = lawan[: g.max_pemain - 1]
        names = [" ".join(body.nama.split()) or "Botku"]
        codes = [body.kode]
        for x in lawan:
            base, k = tpl[x]["nama"], 2
            n = base
            while n.lower() in {a.lower() for a in names}:
                n, k = f"{base} {k}", k + 1
            names.append(n[:16])
            codes.append(tpl[x]["kode"])
        if len(names) < g.min_pemain:
            raise HTTPException(400, "Lawan kurang")
        loop = asyncio.get_running_loop()
        seed = secrets.randbits(62)
        out = await loop.run_in_executor(pool, play_sync, g.id, body.settings, names, codes, seed)
        rid = mgr.add_replay({"game": g.id, "settings": out["settings"], "names": names, "seed": seed, "langkah": out["langkah"]})
        return {"ok": True, "result": out["result"], "frames": out["frames"], "log": out["logs"][0],
                "names": names, "reveal": out["reveal"], "settings": out["settings"], "replay_id": rid}

    @r.get("/api/main/sudut/{rid}")
    async def sudut(rid: str, kursi: int = -1) -> dict[str, Any]:
        """Replay match yang sudah selesai dari sudut pandang satu kursi (kursi -1 = penonton). Match dibuat ulang dari
        seed + aksi yang tercatat, jadi tampilannya persis seperti yang dilihat kursi itu saat main."""
        data = mgr.replays.get(rid)
        if data is None:
            raise HTTPException(404, "Replay sudah tidak tersimpan (server menyimpan 200 match terakhir).")
        if not -1 <= kursi < len(data["names"]):
            raise HTTPException(400, "Kursi tidak ada di match ini.")
        loop = asyncio.get_running_loop()
        try:
            frames = await loop.run_in_executor(pool, sudut_sync, data["game"], data["settings"], data["names"],
                                                data["seed"], data["langkah"], kursi)
        except Exception:  # noqa: BLE001
            log.exception("replay sudut pandang gagal")
            raise HTTPException(500, "Replay gagal dibuat ulang.") from None
        return {"kursi": kursi, "frames": frames}

    @r.get("/api/main/liga/{game_id}")
    async def liga(game_id: str) -> dict[str, Any]:
        if game_id not in GAMES and game_id != "suit_arena":
            raise HTTPException(404, "Game tidak dikenal")
        return {"game": game_id, "board": db.liga(game_id) if db else []}

    @r.websocket("/ws/main")
    async def ws_main(ws: WebSocket) -> None:
        await ws.accept()
        conn = HubConn(mgr, db, ws)
        try:
            while True:
                await conn.on_raw(await ws.receive_text())
        except WebSocketDisconnect:
            pass
        except Exception:  # noqa: BLE001
            log.exception("ws main error")
        finally:
            await conn.closed()

    app.include_router(r)
    app.state.arena = mgr
    return mgr


class HubConn:
    def __init__(self, mgr: ArenaManager, db, ws: WebSocket):
        self.mgr, self.db, self.ws = mgr, db, ws
        self.lock = asyncio.Lock()
        self.room: GameRoom | None = None
        self.member = None
        self.user: dict[str, Any] | None = None

    async def send(self, msg: dict[str, Any]) -> None:
        async with self.lock:
            await self.ws.send_text(_dumps(msg))

    async def kick(self) -> None:
        """Tutup koneksi yang macet; klien akan menyambung ulang dan menerima keadaan terbaru."""
        try:
            await self.ws.close(code=4000)
        except Exception:  # noqa: BLE001
            pass

    async def on_raw(self, raw: str) -> None:
        if len(raw) > MAX_MSG:
            await self.send({"type": "error", "message": "Pesan terlalu besar."})
            return
        try:
            msg = json.loads(raw)
            assert isinstance(msg, dict)
        except (ValueError, AssertionError):
            await self.send({"type": "error", "message": "Format pesan tidak valid."})
            return
        t = str(msg.get("type"))
        try:
            await self.dispatch(t, msg)
        except RoomError as e:
            await self.send({"type": "error", "message": str(e), "for": t, "kode": e.kode})

    async def _enter(self, room: GameRoom, member) -> None:
        self.room, self.member = room, member
        await self.send({"type": "masuk", "kode": room.code, "member_id": member.id, "token": member.token,
                         "game": room.game.id})
        await room.push_lobby()
        if room.status == "main" and room.state is not None:
            await self.send({"type": "mulai", "instan": False, "names": [s.name for s in room.seats],
                             "seat": room.view_seat(member.id), "main_sendiri": room.seat_of(member.id) is not None})
            await room._push_state([], only={member.id})
        elif room.final is not None:
            logs = {s.name: s.bot.log for s in room.seats if s.owner == member.id and s.bot is not None}
            await self.send({**room.final, "logs": logs, "ulang": True})

    async def dispatch(self, t: str, msg: dict[str, Any]) -> None:
        if t == "ping":
            # jam server + jam klien yang dikirim balik: klien menghitung selisih jam & waktu tempuh supaya hitung mundur pas
            await self.send({"type": "pong", "t": msg.get("t"), "now": time.time()})
            return
        if msg.get("token") and self.db is not None:
            self.user = self.db.user_for_token(str(msg["token"])) or self.user
        if t in ("buat", "gabung", "kembali"):
            if t == "buat":
                room = self.mgr.create(str(msg.get("game")), msg.get("settings") or {}, msg.get("waktu"), msg.get("jeda"),
                                       msg.get("jeda_hasil"))
                member = room.join(str(msg.get("nama") or ""), self.user, self.send, bool(msg.get("tonton")), self.kick)
            elif t == "gabung":
                room = self.mgr.get(msg.get("kode"))
                member = room.join(str(msg.get("nama") or ""), self.user, self.send, bool(msg.get("tonton")), self.kick,
                                   ambil_alih=bool(msg.get("ambil_alih")))
            else:
                room = self.mgr.get(msg.get("kode"))
                member = room.rejoin(str(msg.get("member_id")), str(msg.get("token_anggota") or ""), self.send, self.kick)
            await self._enter(room, member)
            return
        room, m = self.room, self.member
        if room is None or m is None or m.id not in room.members:
            raise RoomError("Masuk ke room dulu.")
        if t == "aksi":
            await room.act(m, msg.get("aksi"), msg.get("step"))
            return
        if t == "draf":
            room.draft(m, msg.get("aksi"), msg.get("step"))
            return
        if t == "batal":
            await room.retract(m, msg.get("step"))
            return
        if t == "lanjut":
            await room.next_round(m, msg.get("step"))
            return
        if t == "jeda_host":
            paused = room.toggle_pause(m)
            await room.broadcast({"type": "jeda_host", "dijeda": paused, "oleh": m.name})
            await room._push_state([])
            await room.push_lobby()
            return
        if t == "reset_sesi":
            room.reset_sesi(m)
            await room.push_lobby()
            return
        if t == "reaksi":
            await room.react(m, str(msg.get("emoji") or ""))
            return
        if t == "tambah_bot":
            room.add_bot(m, str(msg.get("nama") or ""), str(msg.get("kode") or ""), str(msg.get("label") or ""))
        elif t == "ubah_bot":
            room.set_bot_code(m, str(msg.get("seat_id")), str(msg.get("kode") or ""), str(msg.get("label") or ""))
        elif t == "jadi_bot":
            seat = next((s for s in room.seats if s.owner == m.id and s.self_seat), None)
            if seat is None:
                raise RoomError("Kamu belum punya kursi.")
            room.set_bot_code(m, seat.id, str(msg.get("kode") or ""), str(msg.get("label") or ""))
        elif t == "jadi_manusia":
            room.to_human(m)
        elif t == "duduk":
            room.take_seat(m)
        elif t == "hapus_kursi":
            room.remove_seat(m, str(msg.get("seat_id")))
        elif t == "atur":
            room.set_settings(m, msg.get("settings") or {}, msg.get("waktu"), msg.get("jeda"), msg.get("jeda_hasil"),
                              msg.get("penonton_semua"))
        elif t == "mulai":
            await room.start(m)
            return
        elif t == "keluar":
            if room.status == "main":
                m.online, m.send, m.kick, m.offline_since = False, None, None, 0.0
                room.wake.set()
            else:
                room.seats = [s for s in room.seats if s.owner != m.id]
                room.members.pop(m.id, None)
                if room.host_id == m.id:
                    room.host_id = next(iter(room.members), "")
            self.room = self.member = None
            await self.send({"type": "keluar_ok"})
            await room.push_lobby()
            return
        else:
            raise RoomError("Perintah tidak dikenal.")
        await room.push_lobby()

    async def closed(self) -> None:
        # bound method dibuat baru setiap diakses, jadi bandingkan dengan == (bukan `is`, yang selalu False)
        if self.room is not None and self.member is not None and self.member.send == self.send:
            self.member.send, self.member.kick, self.member.online = None, None, False
            self.member.offline_since = time.time()
            self.room.wake.set()
            if self.room.host_id == self.member.id:
                nxt = next((x for x in self.room.members.values() if x.online), None)
                if nxt and self.room.status != "main":
                    self.room.host_id = nxt.id
            try:
                await self.room.push_lobby()
            except Exception:  # noqa: BLE001
                pass
