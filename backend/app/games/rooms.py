"""Room Arena Mabar: kursi manusia/bot (boleh campur), timer giliran, penonton, reaksi, dan replay."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..bot.errors import BotError
from ..bot.interpreter import Limits
from .base import ActionError, Game
from .registry import GAMES
from .runner import play_sync, thin_frames
from .runtime import BotSeat, compile_for

log = logging.getLogger("arena")
Sender = Callable[[dict[str, Any]], Awaitable[None]]
EMOJI = ["👏", "😂", "😮", "🔥", "😭", "🤝", "💀", "🎉"]
NAME_RE = re.compile(r"^[\w .\-]{1,16}$", re.UNICODE)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class RoomError(Exception):
    pass


def clean_name(raw: Any) -> str:
    name = " ".join(str(raw or "").split())
    if not name or not NAME_RE.match(name):
        raise RoomError("Nama 1-16 karakter: huruf, angka, spasi, titik, - atau _.")
    return name


@dataclass
class Member:
    id: str
    token: str
    name: str
    user: dict[str, Any] | None
    send: Sender | None
    spectator: bool
    online: bool = True
    last_react: float = 0.0
    last_seen: float = field(default_factory=time.time)


@dataclass
class Seat:
    id: str
    name: str
    kind: str                     # manusia | bot
    owner: str                    # id member pemilik
    self_seat: bool = False       # kursi milik pemain sendiri (bisa diubah jadi bot / kembali manusia)
    code: str | None = None
    label: str = ""
    bot: BotSeat | None = None

    def public(self, members: dict[str, Member]) -> dict[str, Any]:
        m = members.get(self.owner)
        return {"id": self.id, "name": self.name, "kind": self.kind, "label": self.label,
                "owner": self.owner, "owner_name": m.name if m else "?", "online": bool(m and m.online)}


class GameRoom:
    def __init__(self, code: str, game: Game, settings: dict[str, Any], waktu: int, jeda: float, pool=None, on_finish=None):
        self.code, self.game = code, game
        self.settings = game.clean_settings(settings)
        self.waktu = int(min(max(waktu or game.timer, 3), 300))
        self.jeda = float(min(max(jeda, 0.0), 5.0))
        self.members: dict[str, Member] = {}
        self.seats: list[Seat] = []
        self.host_id = ""
        self.status = "lobby"
        self.state: dict[str, Any] | None = None
        self.step = 0
        self.pending: list[int] = []
        self.actions: dict[int, Any] = {}
        self.deadline = 0.0
        self.turn_start = 0.0
        self.deadlines: dict[int, float] = {}   # mode mandiri
        self.wake = asyncio.Event()
        self.frames: list[dict[str, Any]] = []
        self.recent: list[dict[str, Any]] = []
        self.final: dict[str, Any] | None = None
        self.task: asyncio.Task | None = None
        self.pool = pool
        self.on_finish = on_finish
        self.created = self.last = time.time()
        self.match_no = 0
        self.dirty = False   # mode mandiri: ada aksi manusia yang belum disiarkan ke semua

    # ------------------------------------------------------------ util
    def _id(self) -> str:
        return secrets.token_hex(4)

    def seat_of(self, member_id: str) -> int | None:
        for i, s in enumerate(self.seats):
            if s.owner == member_id and s.self_seat and s.kind == "manusia":
                return i
        return None

    def view_seat(self, member_id: str) -> int | None:
        i = self.seat_of(member_id)
        if i is not None:
            return i
        for i, s in enumerate(self.seats):
            if s.owner == member_id:
                return i
        return None

    def _unique(self, name: str, except_id: str | None = None) -> None:
        if any(s.name.lower() == name.lower() and s.id != except_id for s in self.seats):
            raise RoomError("Nama itu sudah dipakai di room ini.")

    def lobby(self) -> dict[str, Any]:
        g = self.game
        return {
            "type": "room", "kode": self.code, "game": g.id, "nama_game": g.nama, "host_id": self.host_id,
            "status": self.status, "settings": self.settings, "waktu": self.waktu, "jeda": self.jeda,
            "min": g.min_pemain, "max": g.max_pemain, "match_no": self.match_no,
            "kursi": [s.public(self.members) for s in self.seats],
            "penonton": [m.name for m in self.members.values() if m.online and self.view_seat(m.id) is None],
            "anggota": [{"id": m.id, "name": m.name, "online": m.online} for m in self.members.values()],
        }

    async def _send(self, m: Member, msg: dict[str, Any]) -> None:
        if m.send is None:
            return
        try:
            await m.send(msg)
        except Exception:  # noqa: BLE001
            m.send, m.online = None, False

    async def broadcast(self, msg: dict[str, Any]) -> None:
        await asyncio.gather(*(self._send(m, msg) for m in list(self.members.values()) if m.send))

    async def push_lobby(self) -> None:
        await self.broadcast(self.lobby())

    # ------------------------------------------------------------ lobby
    def join(self, name: str, user: dict[str, Any] | None, send: Sender, spectator: bool) -> Member:
        name = clean_name(user["username"] if user else name)
        if len(self.members) >= 60:
            raise RoomError("Room penuh.")
        if any(m.name.lower() == name.lower() for m in self.members.values()):
            raise RoomError("Nama itu sudah dipakai di room ini.")
        if not spectator and self.status == "lobby" and len(self.seats) >= self.game.max_pemain:
            spectator = True
        m = Member(self._id(), secrets.token_urlsafe(18), name, user, send, spectator)
        self.members[m.id] = m
        if not self.host_id:
            self.host_id = m.id
        if not spectator and self.status == "lobby":
            self._unique(name)
            self.seats.append(Seat(self._id(), name, "manusia", m.id, self_seat=True, label="Manusia"))
        return m

    def rejoin(self, member_id: str, token: str, send: Sender) -> Member:
        m = self.members.get(str(member_id))
        if m is None or not secrets.compare_digest(m.token, str(token or "")):
            raise RoomError("Sesi sudah berakhir. Masuk lagi dengan nama.")
        m.send, m.online, m.last_seen = send, True, time.time()
        return m

    def _need_lobby(self) -> None:
        if self.status == "main":
            raise RoomError("Match sedang berjalan.")

    def add_bot(self, m: Member, name: str, code: str, label: str) -> Seat:
        self._need_lobby()
        if len(self.seats) >= self.game.max_pemain:
            raise RoomError(f"Kursi penuh (maksimal {self.game.max_pemain}).")
        if sum(1 for s in self.seats if s.owner == m.id and s.kind == "bot" and not s.self_seat) >= 7:
            raise RoomError("Maksimal 7 bot per orang.")
        name = clean_name(name)
        self._unique(name)
        try:
            compile_for(self.game, code)
        except BotError as e:
            raise RoomError(f"Kode bot belum valid: {e}") from None
        seat = Seat(self._id(), name, "bot", m.id, code=code, label=label or "Kode sendiri")
        self.seats.append(seat)
        return seat

    def set_bot_code(self, m: Member, seat_id: str, code: str, label: str) -> None:
        self._need_lobby()
        seat = next((s for s in self.seats if s.id == seat_id), None)
        if seat is None or seat.owner != m.id:
            raise RoomError("Kursi itu bukan milikmu.")
        try:
            compile_for(self.game, code)
        except BotError as e:
            raise RoomError(f"Kode bot belum valid: {e}") from None
        seat.kind, seat.code, seat.label = "bot", code, label or "Kode sendiri"

    def to_human(self, m: Member) -> None:
        self._need_lobby()
        seat = next((s for s in self.seats if s.owner == m.id and s.self_seat), None)
        if seat is None:
            raise RoomError("Kamu tidak punya kursi.")
        seat.kind, seat.code, seat.label = "manusia", None, "Manusia"

    def take_seat(self, m: Member) -> None:
        self._need_lobby()
        if any(s.owner == m.id and s.self_seat for s in self.seats):
            return
        if len(self.seats) >= self.game.max_pemain:
            raise RoomError("Kursi penuh.")
        self._unique(m.name)
        m.spectator = False
        self.seats.append(Seat(self._id(), m.name, "manusia", m.id, self_seat=True, label="Manusia"))

    def remove_seat(self, m: Member, seat_id: str) -> None:
        self._need_lobby()
        seat = next((s for s in self.seats if s.id == seat_id), None)
        if seat is None:
            raise RoomError("Kursi tidak ditemukan.")
        if m.id not in (seat.owner, self.host_id):
            raise RoomError("Hanya pemilik kursi atau host yang bisa menghapus.")
        self.seats.remove(seat)
        if seat.self_seat and seat.owner in self.members:
            self.members[seat.owner].spectator = True

    def set_settings(self, m: Member, cfg: dict[str, Any], waktu: Any, jeda: Any) -> None:
        self._need_lobby()
        if m.id != self.host_id:
            raise RoomError("Hanya host yang bisa mengubah aturan.")
        self.settings = self.game.clean_settings({**self.settings, **(cfg or {})})
        try:
            if waktu is not None:
                self.waktu = int(min(max(float(waktu), 3), 300))
            if jeda is not None:
                self.jeda = float(min(max(float(jeda), 0.0), 5.0))
        except (TypeError, ValueError):
            raise RoomError("Angka waktu tidak valid.") from None

    # ------------------------------------------------------------ mulai
    async def start(self, m: Member) -> None:
        if m.id != self.host_id:
            raise RoomError("Hanya host yang bisa memulai.")
        self._need_lobby()
        g = self.game
        if len(self.seats) < g.min_pemain:
            raise RoomError(f"Butuh minimal {g.min_pemain} pemain (manusia atau bot).")
        names = [s.name for s in self.seats]
        for s in self.seats:
            s.bot = BotSeat(compile_for(g, s.code)) if s.kind == "bot" and s.code else None
        self.match_no += 1
        seed = secrets.randbits(62)
        self.status = "main"
        self.step = 0
        self.frames, self.recent, self.final = [], [], None
        self.last = time.time()
        all_bots = all(s.kind == "bot" for s in self.seats)
        if all_bots and self.jeda == 0 and self.pool is not None:
            await self.push_lobby()
            await self.broadcast({"type": "mulai", "instan": True, "names": names})
            self.task = asyncio.create_task(self._run_instant(names, seed))
            return
        self.state = g.init(self.settings, names, seed)
        self.frames.append({"step": 0, "view": g.public(self.state), "events": []})
        await self.push_lobby()
        for mem in list(self.members.values()):
            await self._send(mem, {"type": "mulai", "instan": False, "names": names, "seat": self.view_seat(mem.id),
                                   "main_sendiri": self.seat_of(mem.id) is not None})
        self.task = asyncio.create_task(self._run_mandiri() if g.mandiri else self._run())

    async def _run_instant(self, names: list[str], seed: int) -> None:
        codes = [s.code for s in self.seats]
        loop = asyncio.get_running_loop()
        try:
            out = await loop.run_in_executor(self.pool, play_sync, self.game.id, self.settings, names, codes, seed)
        except Exception:  # noqa: BLE001
            log.exception("instant match gagal")
            self.status = "lobby"
            await self.broadcast({"type": "error", "message": "Match gagal dijalankan di server."})
            await self.push_lobby()
            return
        self.frames = out["frames"]
        for s, lg in zip(self.seats, out["logs"]):
            s.bot = BotSeat(None, log=lg)
        await self._finish(out["result"], out["reveal"])

    # ------------------------------------------------------------ main loop
    def _view_for(self, mem: Member) -> tuple[dict[str, Any], int | None]:
        p = self.view_seat(mem.id)
        if p is None:
            return self.game.public(self.state), None
        return self.game.observe(self.state, p), p

    async def _push_state(self, events: list[dict[str, Any]], only: set[str] | None = None) -> None:
        msgs = []
        for mem in list(self.members.values()):
            if mem.send is None or (only is not None and mem.id not in only):
                continue
            view, p = self._view_for(mem)
            mine = self.seat_of(mem.id)
            my_turn = mine is not None and mine in self.pending and mine not in self.actions and self.status == "main"
            dl = self.deadlines.get(mine, 0) if self.game.mandiri and mine is not None else self.deadline
            msgs.append(self._send(mem, {"type": "update", "view": view, "seat": p, "pending": self.pending,
                                         "acted": list(self.actions.keys()), "my_turn": my_turn,
                                         "deadline": dl, "now": time.time(), "step": self.step, "events": events}))
        await asyncio.gather(*msgs)

    def _bot_action(self, p: int) -> Any:
        seat = self.seats[p]
        if seat.bot is None:
            return self.game.default(self.state, p)
        return seat.bot.act(self.game, self.state, p, self.step, Limits())

    def _record(self, events: list[dict[str, Any]]) -> None:
        self.frames.append({"step": self.step, "view": self.game.public(self.state), "events": events})
        if len(self.frames) > self.game.max_frames * 2:
            self.frames = self.frames[:1] + self.frames[1::2]
        self.recent = (self.recent + events)[-60:]

    async def _run(self) -> None:
        g, s = self.game, self.state
        try:
            while not g.over(s):
                pend = g.pending(s)
                if not pend:
                    break
                self.step += 1
                self.pending, self.actions = pend, {}
                for p in pend:
                    if self.seats[p].kind == "bot":
                        self.actions[p] = self._bot_action(p)
                humans = [p for p in pend if self.seats[p].kind == "manusia"]
                timeouts: list[int] = []
                if humans:
                    self.turn_start = time.time()
                    self.deadline = self.turn_start + self.waktu
                    await self._push_state([])
                    while any(p not in self.actions for p in humans):
                        now = time.time()
                        if now >= self.deadline:
                            break
                        for p in humans:
                            owner = self.members.get(self.seats[p].owner)
                            if p not in self.actions and (owner is None or not owner.online) and now - self.turn_start > 2:
                                self.actions[p] = g.default(s, p)
                        self.wake.clear()
                        try:
                            await asyncio.wait_for(self.wake.wait(), timeout=min(1.0, max(0.05, self.deadline - now)))
                        except asyncio.TimeoutError:
                            pass
                    for p in humans:
                        if p not in self.actions:
                            self.actions[p] = g.default(s, p)
                            timeouts.append(p)
                elif self.jeda > 0:
                    await asyncio.sleep(self.jeda)
                else:
                    await asyncio.sleep(0)
                events = g.apply(s, dict(self.actions))
                if timeouts:
                    events = [{"jenis": "waktu_habis", "pemain": [s["names"][p] for p in timeouts]}] + events
                self.pending, self.actions = [], {}
                self._record(events)
                await self._push_state(events)
                self.last = time.time()
            await self._finish(g.result(s), g.reveal(s))
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("room %s error", self.code)
            self.status = "lobby"
            await self.broadcast({"type": "error", "message": "Terjadi kesalahan di server, match dihentikan."})
            await self.push_lobby()

    async def _run_mandiri(self) -> None:
        """Setiap pemain jalan sendiri (misalnya deck-builder): tidak menunggu pemain lain."""
        g, s = self.game, self.state
        next_bot: dict[int, float] = {}
        last_push = 0.0
        try:
            while not g.over(s):
                now = time.time()
                pend = set(g.pending(s))
                self.pending = sorted(pend)
                changed: list[dict[str, Any]] = []
                for p in self.pending:
                    seat = self.seats[p]
                    if seat.kind == "bot":
                        if now >= next_bot.get(p, 0):
                            self.step += 1
                            changed += g.apply(s, {p: self._bot_action(p)})
                            next_bot[p] = now + max(self.jeda, 0.05)
                    else:
                        if p not in self.deadlines:
                            self.deadlines[p] = now + self.waktu
                        owner = self.members.get(seat.owner)
                        offline = owner is None or not owner.online
                        if now >= self.deadlines[p] or (offline and now - self.deadlines[p] + self.waktu > 2):
                            self.step += 1
                            changed += [{"jenis": "waktu_habis", "pemain": [s["names"][p]]}] + g.apply(s, {p: g.default(s, p)})
                            self.deadlines[p] = now + self.waktu
                if changed:
                    self._record(changed)
                if (changed or self.dirty) and now - last_push > 0.25:
                    last_push = now
                    self.dirty = False
                    await self._push_state(changed)
                self.last = now
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=0.05 if any(self.seats[p].kind == "bot" for p in pend) else 0.5)
                except asyncio.TimeoutError:
                    pass
            await self._push_state([])
            await self._finish(g.result(s), g.reveal(s))
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("room %s error", self.code)
            self.status = "lobby"
            await self.broadcast({"type": "error", "message": "Terjadi kesalahan di server, match dihentikan."})
            await self.push_lobby()

    async def act(self, m: Member, action: Any) -> None:
        if self.status != "main" or self.state is None:
            raise RoomError("Match belum berjalan.")
        p = self.seat_of(m.id)
        if p is None:
            raise RoomError("Kamu tidak punya kursi manusia di match ini.")
        if p not in self.game.pending(self.state):
            raise RoomError("Belum giliranmu.")
        try:
            a = self.game.validate(self.state, p, action)
        except ActionError as e:
            raise RoomError(str(e)) from None
        if self.game.mandiri:
            self.step += 1
            events = self.game.apply(self.state, {p: a})
            self.deadlines[p] = time.time() + self.waktu
            self._record(events)
            self.dirty = True
            await self._push_state(events, only={m.id})
            self.wake.set()
            return
        if p in self.actions:
            raise RoomError("Kamu sudah bertindak di langkah ini.")
        self.actions[p] = a
        await self._send(m, {"type": "aksi_ok", "step": self.step})
        self.wake.set()

    async def react(self, m: Member, emoji: str) -> None:
        if emoji not in EMOJI:
            raise RoomError("Reaksi tidak dikenal.")
        now = time.time()
        if now - m.last_react < 0.6:
            return
        m.last_react = now
        await self.broadcast({"type": "reaksi", "nama": m.name, "emoji": emoji})

    async def _finish(self, result: dict[str, Any], reveal: dict[str, Any]) -> None:
        self.status = "selesai"
        self.pending, self.actions = [], {}
        names = [s.name for s in self.seats]
        ratings = None
        if self.on_finish:
            try:
                ratings = self.on_finish(self, result)
            except Exception:  # noqa: BLE001
                log.exception("rating gagal")
        self.final = {"type": "selesai", "result": result, "reveal": reveal, "names": names,
                      "kinds": [s.kind for s in self.seats], "ratings": ratings,
                      "frames": thin_frames(self.frames, self.game.max_frames)}
        for mem in list(self.members.values()):
            logs = {s.name: s.bot.log for s in self.seats if s.owner == mem.id and s.bot is not None}
            await self._send(mem, {**self.final, "logs": logs})
        await self.push_lobby()
        self.status = "lobby"
        self.state = None
        await self.push_lobby()


class ArenaManager:
    def __init__(self, pool=None, on_finish=None):
        self.rooms: dict[str, GameRoom] = {}
        self.pool = pool
        self.on_finish = on_finish

    def create(self, game_id: str, settings: dict[str, Any], waktu: Any, jeda: Any) -> GameRoom:
        g = GAMES.get(str(game_id))
        if g is None:
            raise RoomError("Game tidak dikenal.")
        if len(self.rooms) >= 300:
            raise RoomError("Server penuh, coba lagi nanti.")
        for _ in range(200):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(5))
            if code not in self.rooms:
                break
        try:
            w = float(waktu) if waktu not in (None, "") else g.timer
            j = float(jeda) if jeda not in (None, "") else 0.6
        except (TypeError, ValueError):
            w, j = g.timer, 0.6
        room = GameRoom(code, g, settings or {}, int(w), j, self.pool, self.on_finish)
        self.rooms[code] = room
        return room

    def get(self, code: Any) -> GameRoom:
        room = self.rooms.get(str(code or "").strip().upper())
        if room is None:
            raise RoomError("Room tidak ditemukan. Cek lagi kodenya.")
        return room

    def cleanup(self) -> None:
        now = time.time()
        for code, r in list(self.rooms.items()):
            online = any(m.online for m in r.members.values())
            idle = now - r.last
            if (not online and idle > 900) or (r.status != "main" and idle > 3 * 3600):
                if r.task:
                    r.task.cancel()
                self.rooms.pop(code, None)
