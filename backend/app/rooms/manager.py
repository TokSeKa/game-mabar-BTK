"""Room, pemain, dan alur lobby → match → lobby."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..bot.errors import BotError
from ..bot.validator import compile_bot
from ..engine.match import MatchSettings

log = logging.getLogger("suitbot.rooms")

COLORS = ["#7aa2ff", "#c29bff", "#ffd166", "#6ee7a8", "#ff9f7a", "#5ad1e6", "#f7a8d8", "#c9d36a"]
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
NAME_RE = re.compile(r"^[\w .\-]{1,16}$", re.UNICODE)

Sender = Callable[[dict[str, Any]], Awaitable[None]]
MatchFn = Callable[[list[tuple[str, str]], dict[str, Any]], Awaitable[dict[str, Any]]]


class RoomError(Exception):
    """Kesalahan yang ditampilkan ke pemain (bahasa Indonesia)."""


@dataclass
class Player:
    id: str
    token: str
    name: str
    color: str
    seq: int
    code: str | None = None
    bot_ok: bool = False
    bot_error: dict | None = None
    ready: bool = False
    online: bool = True
    send: Sender | None = None
    last_seen: float = field(default_factory=time.monotonic)
    wins: int = 0
    matches: int = 0

    def public(self, host_id: str) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "color": self.color, "ready": self.ready,
            "bot_ok": self.bot_ok, "online": self.online, "wins": self.wins,
            "matches": self.matches, "is_host": self.id == host_id,
        }


@dataclass
class Room:
    code: str
    host_id: str
    settings: MatchSettings = field(default_factory=MatchSettings)
    players: dict[str, Player] = field(default_factory=dict)
    status: str = "lobby"  # lobby | running
    seq: int = 0
    match_count: int = 0
    last_match: dict[str, Any] | None = None
    empty_since: float | None = None

    def ordered(self) -> list[Player]:
        return sorted(self.players.values(), key=lambda p: p.seq)

    def public(self) -> dict[str, Any]:
        return {
            "code": self.code, "host_id": self.host_id, "status": self.status,
            "settings": self.settings.to_dict(), "match_count": self.match_count,
            "players": [p.public(self.host_id) for p in self.ordered()],
            "last_match_id": self.last_match["public"]["id"] if self.last_match else None,
        }


def clean_name(raw: Any) -> str:
    name = " ".join(str(raw or "").split())
    if not name:
        raise RoomError("Nama tidak boleh kosong.")
    if not NAME_RE.match(name):
        raise RoomError("Nama maksimal 16 karakter: huruf, angka, spasi, titik, - atau _.")
    return name


class RoomManager:
    def __init__(self, run_match: MatchFn, *, max_rooms: int = 200, max_players: int = 8,
                 player_grace: float = 600, room_idle: float = 1800):
        self.rooms: dict[str, Room] = {}
        self.run_match = run_match
        self.max_rooms = max_rooms
        self.max_players = max_players
        self.player_grace = player_grace
        self.room_idle = room_idle
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------ util
    def _new_code(self) -> str:
        for _ in range(1000):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(5))
            if code not in self.rooms:
                return code
        raise RoomError("Server sedang penuh, coba lagi nanti.")

    def _new_player(self, room: Room, name: str, send: Sender) -> Player:
        used = {p.color for p in room.players.values()}
        color = next((c for c in COLORS if c not in used), COLORS[0])
        room.seq += 1
        p = Player(id=secrets.token_hex(4), token=secrets.token_urlsafe(18), name=name, color=color,
                   seq=room.seq, send=send)
        room.players[p.id] = p
        room.empty_since = None
        return p

    def get_room(self, code: str) -> Room:
        room = self.rooms.get(str(code or "").strip().upper())
        if room is None:
            raise RoomError("Room tidak ditemukan. Cek lagi kodenya.")
        return room

    async def _send(self, p: Player, msg: dict[str, Any]) -> None:
        if p.send is None:
            return
        try:
            await p.send(msg)
        except Exception:  # noqa: BLE001 - koneksi putus, tandai offline
            p.send = None
            p.online = False

    async def broadcast(self, room: Room, msg: dict[str, Any]) -> None:
        await asyncio.gather(*(self._send(p, msg) for p in room.players.values() if p.send))

    async def broadcast_state(self, room: Room) -> None:
        await self.broadcast(room, {"type": "room_state", "room": room.public()})

    def _match_payload_for(self, room: Room, p: Player) -> dict[str, Any] | None:
        lm = room.last_match
        if not lm:
            return None
        payload = {"type": "match_result", "match": lm["public"], "revealed": lm["revealed"]}
        idx = lm["index_of"].get(p.id)
        if idx is not None:
            payload["my_index"] = idx
            payload["my_log"] = lm["logs"][idx]
        return payload

    # ------------------------------------------------------------ join/leave
    async def create_room(self, name: Any, send: Sender) -> tuple[Room, Player]:
        if len(self.rooms) >= self.max_rooms:
            raise RoomError("Jumlah room di server sudah maksimal. Coba lagi nanti.")
        name = clean_name(name)
        room = Room(code=self._new_code(), host_id="")
        self.rooms[room.code] = room
        p = self._new_player(room, name, send)
        room.host_id = p.id
        log.info("room %s dibuat oleh %s", room.code, name)
        return room, p

    async def join_room(self, code: Any, name: Any, send: Sender) -> tuple[Room, Player]:
        room = self.get_room(code)
        name = clean_name(name)
        if any(x.name.lower() == name.lower() for x in room.players.values()):
            raise RoomError("Nama itu sudah dipakai di room ini. Pilih nama lain.")
        if len(room.players) >= self.max_players:
            raise RoomError(f"Room penuh (maksimal {self.max_players} pemain).")
        p = self._new_player(room, name, send)
        return room, p

    async def rejoin(self, code: Any, player_id: Any, token: Any, send: Sender) -> tuple[Room, Player]:
        room = self.get_room(code)
        p = room.players.get(str(player_id))
        if p is None or not secrets.compare_digest(p.token, str(token or "")):
            raise RoomError("Sesi lama sudah berakhir. Masuk lagi dengan nama.")
        p.send = send
        p.online = True
        p.last_seen = time.monotonic()
        room.empty_since = None
        return room, p

    async def after_join(self, room: Room, p: Player) -> None:
        await self._send(p, {"type": "joined", "room_code": room.code, "player_id": p.id, "token": p.token})
        await self._send(p, {"type": "bot_status", "ok": p.bot_ok, "error": p.bot_error, "code": p.code})
        await self.broadcast_state(room)
        payload = self._match_payload_for(room, p)
        if payload:
            payload["replay"] = False
            await self._send(p, payload)

    async def disconnect(self, room: Room, p: Player, send: Sender) -> None:
        if p.send is not send:  # sudah tersambung lagi lewat koneksi baru
            return
        p.send = None
        p.online = False
        p.last_seen = time.monotonic()
        if not any(x.online for x in room.players.values()):
            room.empty_since = time.monotonic()
        self._fix_host(room)
        await self.broadcast_state(room)

    async def leave(self, room: Room, p: Player) -> None:
        room.players.pop(p.id, None)
        if not room.players:
            self.rooms.pop(room.code, None)
            return
        self._fix_host(room)
        await self.broadcast_state(room)

    def _fix_host(self, room: Room) -> None:
        host = room.players.get(room.host_id)
        if host is not None and host.online:
            return
        online = [p for p in room.ordered() if p.online]
        if online:
            room.host_id = online[0].id
        elif host is None and room.players:
            room.host_id = room.ordered()[0].id

    async def cleanup(self) -> None:
        now = time.monotonic()
        for code, room in list(self.rooms.items()):
            for p in list(room.players.values()):
                if not p.online and now - p.last_seen > self.player_grace:
                    room.players.pop(p.id, None)
            if not room.players or (room.empty_since is not None and now - room.empty_since > self.room_idle):
                self.rooms.pop(code, None)
                continue
            self._fix_host(room)

    # ------------------------------------------------------------ actions
    async def handle(self, room: Room, p: Player, msg: dict[str, Any]) -> None:
        t = msg.get("type")
        p.last_seen = time.monotonic()
        if t == "submit_bot":
            await self.submit_bot(room, p, msg.get("code"))
        elif t == "set_ready":
            await self.set_ready(room, p, bool(msg.get("ready")))
        elif t == "update_settings":
            await self.update_settings(room, p, msg.get("settings"))
        elif t == "start_match":
            await self.start_match(room, p)
        elif t == "reveal_code":
            await self.reveal_code(room, p)
        elif t == "kick":
            await self.kick(room, p, msg.get("player_id"))
        elif t == "ping":
            await self._send(p, {"type": "pong"})
        else:
            raise RoomError("Perintah tidak dikenal.")

    async def submit_bot(self, room: Room, p: Player, code: Any) -> None:
        if room.status == "running" and p.ready:
            raise RoomError("Match sedang berjalan. Tunggu selesai dulu untuk mengganti bot.")
        try:
            compile_bot(code if isinstance(code, str) else "")
            p.code, p.bot_ok, p.bot_error = code, True, None
        except BotError as e:
            p.code, p.bot_ok, p.bot_error = (code if isinstance(code, str) else None), False, e.to_dict()
            p.ready = False
        await self._send(p, {"type": "bot_status", "ok": p.bot_ok, "error": p.bot_error, "code": p.code})
        await self.broadcast_state(room)

    async def set_ready(self, room: Room, p: Player, ready: bool) -> None:
        if ready and not p.bot_ok:
            raise RoomError("Simpan bot yang valid dulu sebelum siap.")
        if room.status == "running":
            raise RoomError("Match sedang berjalan.")
        p.ready = ready
        await self.broadcast_state(room)

    async def update_settings(self, room: Room, p: Player, settings: Any) -> None:
        if p.id != room.host_id:
            raise RoomError("Hanya host yang bisa mengubah aturan.")
        if room.status == "running":
            raise RoomError("Aturan tidak bisa diubah saat match berjalan.")
        room.settings = MatchSettings.from_dict(settings if isinstance(settings, dict) else {})
        await self.broadcast_state(room)

    async def kick(self, room: Room, p: Player, target_id: Any) -> None:
        if p.id != room.host_id:
            raise RoomError("Hanya host yang bisa mengeluarkan pemain.")
        target = room.players.get(str(target_id))
        if target is None or target.id == p.id:
            raise RoomError("Pemain tidak ditemukan.")
        await self._send(target, {"type": "kicked"})
        target.send = None
        room.players.pop(target.id, None)
        await self.broadcast_state(room)

    async def start_match(self, room: Room, p: Player) -> None:
        if p.id != room.host_id:
            raise RoomError("Hanya host yang bisa memulai match.")
        if room.status == "running":
            raise RoomError("Match sedang berjalan.")
        peserta = [x for x in room.ordered() if x.online and x.ready and x.bot_ok and x.code]
        if len(peserta) < 2:
            raise RoomError("Butuh minimal 2 pemain yang siap (bot valid + tombol Siap).")
        room.status = "running"
        await self.broadcast_state(room)
        task = asyncio.create_task(self._run(room, peserta))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, room: Room, peserta: list[Player]) -> None:
        settings = room.settings.to_dict()
        entries = [(x.name, x.code or "") for x in peserta]
        try:
            result = await self.run_match(entries, settings)
        except Exception:  # noqa: BLE001
            log.exception("match di room %s gagal", room.code)
            room.status = "lobby"
            await self.broadcast(room, {"type": "error", "message": "Match gagal dijalankan di server. Coba lagi."})
            await self.broadcast_state(room)
            return
        room.match_count += 1
        match_id = f"{room.code}-{room.match_count}"
        public = {
            "id": match_id,
            "settings": result["settings"],
            "players": [{"index": i, "id": x.id, "name": x.name, "color": x.color} for i, x in enumerate(peserta)],
            "rounds": result["rounds"],
            "ranking": result["ranking"],
            "winners": result["winners"],
            "reason": result["reason"],
            "elim_round": result["elim_round"],
            "final_hp": result["final_hp"],
        }
        room.last_match = {
            "public": public,
            "logs": result["logs"],
            "codes": {x.id: x.code for x in peserta},
            "index_of": {x.id: i for i, x in enumerate(peserta)},
            "revealed": {},
        }
        for i, x in enumerate(peserta):
            x.matches += 1
            if i in result["winners"]:
                x.wins += 1
        for x in room.players.values():
            x.ready = False
        room.status = "lobby"
        for x in list(room.players.values()):
            payload = self._match_payload_for(room, x)
            if payload:
                payload["replay"] = True
                await self._send(x, payload)
        await self.broadcast_state(room)

    async def reveal_code(self, room: Room, p: Player) -> None:
        lm = room.last_match
        if not lm or p.id not in lm["codes"]:
            raise RoomError("Kamu tidak ikut match terakhir.")
        code = lm["codes"][p.id]
        lm["revealed"][p.id] = code
        await self.broadcast(room, {"type": "code_revealed", "match_id": lm["public"]["id"],
                                    "player_id": p.id, "name": p.name, "code": code})
