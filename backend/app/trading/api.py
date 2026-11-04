"""REST + WebSocket untuk Kilas Pasar."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import numpy as np
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .accounts import AccountDB, AuthError
from .engine import TradeError
from .service import GameError, TradingService, session_payload
from .session import SessionError
from .store import CandleStore, data_dir

log = logging.getLogger("kilas")
MAX_MSG = 64 * 1024


class Cred(BaseModel):
    username: str = Field(max_length=40)
    password: str = Field(max_length=200)


def _json_default(o: Any) -> Any:
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def dumps(msg: dict[str, Any]) -> str:
    return json.dumps(msg, default=_json_default, separators=(",", ":"), allow_nan=False)


def _clean(o: Any) -> Any:
    """Ganti NaN/inf jadi None supaya JSON valid."""
    if isinstance(o, float):
        return o if np.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def create_trading(store: CandleStore | None = None, db: AccountDB | None = None) -> TradingService:
    store = store or CandleStore()
    db = db or AccountDB(data_dir().parent / "akun.db")
    return TradingService(store, db)


def mount(app: FastAPI, svc: TradingService) -> None:
    r = APIRouter()

    def user_from(auth: str | None) -> dict[str, Any] | None:
        if auth and auth.lower().startswith("bearer "):
            return svc.db.user_for_token(auth[7:].strip())
        return None

    def need_user(auth: str | None) -> dict[str, Any]:
        u = user_from(auth)
        if not u:
            raise HTTPException(401, "Masuk dulu ke akunmu.")
        return u

    @r.get("/api/pasar/katalog")
    async def katalog() -> dict[str, Any]:
        return svc.catalog()

    @r.get("/api/pasar/harian")
    async def harian(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        return _clean(svc.daily_info(user_from(authorization)))

    @r.get("/api/pasar/harian/papan")
    async def papan(tanggal: str) -> dict[str, Any]:
        return _clean({"date": tanggal, "board": svc.db.daily_board(tanggal[:10])})

    @r.get("/api/pasar/riwayat")
    async def riwayat(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        u = need_user(authorization)
        return _clean({"profil": svc.db.profile(u["id"]), "hasil": svc.db.results(u["id"])})

    @r.post("/api/akun/daftar")
    async def daftar(c: Cred) -> dict[str, Any]:
        try:
            user, token = await asyncio.to_thread(svc.db.register, c.username, c.password)
        except AuthError as e:
            raise HTTPException(400, str(e)) from None
        return {"user": user, "token": token}

    @r.post("/api/akun/masuk")
    async def masuk(c: Cred, request: Request) -> dict[str, Any]:
        ip = request.client.host if request.client else ""
        try:
            user, token = await asyncio.to_thread(svc.db.login, c.username, c.password, ip)
        except AuthError as e:
            raise HTTPException(400 if "salah" in str(e) else 429, str(e)) from None
        return {"user": user, "token": token}

    @r.post("/api/akun/keluar")
    async def keluar(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        if authorization and authorization.lower().startswith("bearer "):
            svc.db.logout(authorization[7:].strip())
        return {"ok": True}

    @r.get("/api/akun/saya")
    async def saya(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        u = need_user(authorization)
        return _clean({"user": u, "profil": svc.db.profile(u["id"])})

    @r.websocket("/ws/pasar")
    async def ws_pasar(ws: WebSocket) -> None:
        await ws.accept()
        conn = Conn(svc, ws)
        try:
            while True:
                raw = await ws.receive_text()
                await conn.on_raw(raw)
        except WebSocketDisconnect:
            pass
        except Exception:  # noqa: BLE001
            log.exception("ws pasar error")
        finally:
            await conn.closed()

    app.include_router(r)
    app.state.trading = svc


class Conn:
    """Satu koneksi WebSocket: bisa memegang satu sesi solo/harian atau satu kursi balapan."""

    def __init__(self, svc: TradingService, ws: WebSocket):
        self.svc, self.ws = svc, ws
        self.lock = asyncio.Lock()
        self.user: dict[str, Any] | None = None
        self.sess = None
        self.room = None
        self.tr = None

    async def send(self, msg: dict[str, Any]) -> None:
        async with self.lock:
            await self.ws.send_text(dumps(_clean(msg)))

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
        t = msg.get("type")
        try:
            await self.dispatch(str(t), msg)
        except (GameError, TradeError, SessionError) as e:
            await self.send({"type": "error", "message": str(e), "for": t})

    async def dispatch(self, t: str, msg: dict[str, Any]) -> None:
        svc = self.svc
        if t == "ping":
            await self.send({"type": "pong"})
            return
        if msg.get("token"):
            self.user = svc.db.user_for_token(str(msg["token"])) or self.user
        if t == "auth":
            await self.send({"type": "auth", "user": self.user})
        elif t in ("solo_start", "daily_start"):
            s = svc.start_solo(msg.get("config") or {}, self.user, self.send) if t == "solo_start" else svc.start_daily(self.user, self.send)
            await self._attach(s, resumed=False)
        elif t == "solo_resume":
            s = svc.sessions.get(str(msg.get("id")))
            if s is None or s.secret != msg.get("secret"):
                raise GameError("Sesi sudah berakhir. Mulai sesi baru.")
            await self._attach(s, resumed=True)
        elif t in ("history", "subscribe", "order", "protect", "cancel", "step", "finish"):
            await self.play(t, msg)
        elif t in ("race_create", "race_join", "race_rejoin"):
            name, cfg = str(msg.get("name") or ""), msg.get("config") or {}
            if t == "race_create":
                room, tr = svc.race_create(name, cfg, self.user, self.send)
            elif t == "race_join":
                room, tr = svc.race_join(str(msg.get("code") or ""), name, self.user, self.send)
            else:
                room, tr = svc.race_rejoin(str(msg.get("code")), str(msg.get("player_id")), str(msg.get("token")), self.send)
            self.sess, self.room, self.tr = None, room, tr
            await self.send({"type": "race_joined", "code": room.code, "player_id": tr.id, "token": tr.token})
            await svc.race_broadcast(room, svc.race_state(room))
            if t == "race_rejoin" and room.view:
                await self.send(svc._race_session(room, tr))
                await self.send(svc.account_msg(room.view, tr, full=True))
                await self.send(svc.race_board(room))
                if room.status == "done":
                    await self.send({"type": "summary", "mode": "balapan", **svc.summary(room.view, tr), "board": room.results or []})
        elif t in ("race_start", "race_pause", "race_resume", "race_speed", "race_leave"):
            await self.race(t, msg)
        else:
            raise GameError("Perintah tidak dikenal.")

    async def _attach(self, s: Any, resumed: bool) -> None:
        self.sess, self.room, self.tr = s, None, None
        s.trader.send = self.send
        s.last = time.time()
        await self.send(session_payload(s.view, s.trader.account, s.mode, s.chart_tf,
                                        {"id": s.id, "secret": s.secret, "resumed": resumed,
                                         "fixed_end": s.mode.startswith("harian")}))
        await self.send(self.svc.account_msg(s.view, s.trader, full=True))
        if s.finished:
            await self.send(s.finished)

    def _ctx(self):
        if self.sess is not None:
            return self.sess.view, self.sess.trader
        if self.room is not None and self.room.view is not None:
            return self.room.view, self.tr
        raise GameError("Sesi belum dimulai.")

    async def play(self, t: str, msg: dict[str, Any]) -> None:
        svc = self.svc
        view, tr = self._ctx()
        if self.sess is not None:
            self.sess.last = time.time()
        if t == "history":
            await self.send(svc.history(view, str(msg.get("tf")), msg.get("before"), msg.get("limit")))
        elif t == "subscribe":
            tfs = [tf for tf in (msg.get("tfs") or []) if tf in view.tfs][:3]
            tr.subs = set(tfs) or tr.subs
        elif t in ("order", "protect", "cancel"):
            finished = (self.sess and self.sess.finished) or (self.room and self.room.status == "done")
            if finished or view.done:
                raise GameError("Sesi sudah selesai.")
            fills = svc.trade(view, tr, msg)
            await self.send(svc.account_msg(view, tr, fills))
        elif t == "step":
            if self.sess is None:
                raise GameError("Di balapan, candle maju otomatis.")
            if self.sess.finished:
                raise GameError("Sesi sudah selesai.")
            tf = str(msg.get("tf") or self.sess.chart_tf)
            if tf not in view.tfs:
                raise GameError("Timeframe tidak tersedia.")
            n = int(max(1, min(int(msg.get("n") or 1), 500)))
            old, new = view.advance(tf, n)
            fills = svc.run_engine(view, tr, old, new)
            await self.send(svc.tick_msg(view, tr, old, fills))
            if view.done:
                await self.send(svc.finish(self.sess))
        elif t == "finish":
            if self.sess is None:
                raise GameError("Balapan selesai otomatis saat candle habis.")
            await self.send(svc.finish(self.sess))

    async def race(self, t: str, msg: dict[str, Any]) -> None:
        svc, room, tr = self.svc, self.room, self.tr
        if room is None or tr is None:
            raise GameError("Kamu belum masuk room balapan.")
        if t == "race_leave":
            if room.status == "lobby":
                room.players.pop(tr.id, None)
                if tr.id == room.host_id and room.players:
                    room.host_id = next(iter(room.players))
            else:
                tr.online, tr.send = False, None
            self.room = self.tr = None
            await svc.race_broadcast(room, svc.race_state(room))
            await self.send({"type": "race_left"})
            return
        if tr.id != room.host_id:
            raise GameError("Hanya host yang bisa mengatur balapan.")
        if t == "race_start":
            await svc.race_start(room, tr)
            return
        if t == "race_pause" and room.status == "running":
            room.status = "paused"
        elif t == "race_resume" and room.status == "paused":
            room.status = "running"
        elif t == "race_speed":
            try:
                room.speed = min(max(float(msg.get("speed")), 0.3), 15.0)
            except (TypeError, ValueError):
                raise GameError("Kecepatan tidak valid.") from None
        await svc.race_broadcast(room, svc.race_state(room))

    async def closed(self) -> None:
        if self.sess is not None and self.sess.trader.send is self.send:
            self.sess.trader.send = None
        if self.room is not None and self.tr is not None and self.tr.send is self.send:
            self.tr.send, self.tr.online = None, False
            try:
                await self.svc.race_broadcast(self.room, self.svc.race_state(self.room))
            except Exception:  # noqa: BLE001
                pass


__all__ = ["mount", "create_trading"]
