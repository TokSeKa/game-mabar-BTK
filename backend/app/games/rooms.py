"""Room Arena Mabar: kursi manusia/bot (boleh campur), timer giliran, penonton, reaksi, dan replay."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from collections import OrderedDict
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
Kicker = Callable[[], Awaitable[None]]
SEND_TIMEOUT = 10.0      # kirim ke satu anggota lebih lama dari ini = koneksi macet, diputus supaya klien menyambung ulang
OFFLINE_LAMA = 30.0      # putus lebih lama dari ini = tidak ditunggu lagi
REPLAY_MAKS = 200        # jumlah match terakhir yang bisa diputar ulang dari sudut pandang pemain
EMOJI = ["👏", "😂", "😮", "🔥", "😭", "🤝", "💀", "🎉"]
NAME_RE = re.compile(r"^[\w .\-]{1,16}$", re.UNICODE)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class RoomError(Exception):
    def __init__(self, message: str = "", kode: str = ""):
        super().__init__(message)
        self.kode = kode    # kode mesin untuk klien, misalnya "nama_dipakai" atau "telat"


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
    kick: Kicker | None = None       # menutup koneksi websocket anggota ini (supaya kliennya menyambung ulang)
    offline_since: float = 0.0       # 0 = keluar dengan sengaja / sudah lama sekali


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
        return {"id": self.id, "name": self.name, "kind": self.kind, "label": self.label, "self": self.self_seat,
                "owner": self.owner, "owner_name": m.name if m else "?", "online": bool(m and m.online)}


class GameRoom:
    def __init__(self, code: str, game: Game, settings: dict[str, Any], waktu: int, jeda: float, pool=None, on_finish=None,
                 jeda_hasil: float | None = None, replay_store: Callable[[dict[str, Any]], str] | None = None):
        self.code, self.game = code, game
        self.settings = game.clean_settings(settings)
        self.waktu = int(min(max(waktu or game.timer, 3), 300))
        self.jeda = float(min(max(jeda, 0.0), 5.0))
        self.jeda_hasil = float(min(max(game.jeda_hasil if jeda_hasil is None else jeda_hasil, 0.0), 30.0))
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
        self.drafts: dict[int, Any] = {}        # pilihan terakhir manusia yang belum dikirim (submit otomatis saat waktu habis)
        self.pause_until = 0.0                  # jeda lihat hasil ronde
        self.ready: set[int] = set()            # kursi manusia yang menekan "Lanjut" selama jeda
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
        self.vers: dict[int, int] = {}          # mode mandiri: nomor langkah tiap kursi (untuk menolak klik telat)
        self.paused_at = 0.0                    # > 0: match dijeda host sejak waktu ini
        self.penonton_semua = False             # penonton melihat tampilan lengkap (rahasia terbuka)
        self.sesi: dict[str, dict[str, Any]] = {}   # klasemen gabungan semua match di room ini
        self.langkah: list[dict[str, Any]] = []     # aksi tiap langkah (untuk replay sudut pandang pemain)
        self.seed = 0
        self.replay_store = replay_store

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
            "jeda_hasil": self.jeda_hasil, "penonton_semua": self.penonton_semua, "dijeda": self.paused_at > 0,
            "sesi": sorted(self.sesi.values(), key=lambda e: (-e["poin"], -e["juara"], e["main"], e["nama"].lower())),
            "min": g.min_pemain, "max": g.max_pemain, "match_no": self.match_no,
            "kursi": [s.public(self.members) for s in self.seats],
            "penonton": [m.name for m in self.members.values() if m.online and self.view_seat(m.id) is None],
            "anggota": [{"id": m.id, "name": m.name, "online": m.online} for m in self.members.values()],
        }

    async def _send(self, m: Member, msg: dict[str, Any]) -> None:
        send = m.send
        if send is None:
            return
        try:
            await asyncio.wait_for(send(msg), timeout=SEND_TIMEOUT)
        except Exception:  # noqa: BLE001
            # Hanya tandai offline kalau anggota ini belum tersambung lagi lewat koneksi baru. Dulu koneksi lama yang gagal
            # menimpa koneksi baru, sehingga pemain yang baru menyambung ulang tidak menerima update lagi (layar "beku")
            # dan setiap ronde berikutnya otomatis memakai aksi bawaan.
            if m.send is send:
                kick = m.kick
                m.send, m.kick, m.online, m.offline_since = None, None, False, time.time()
                if kick is not None:
                    asyncio.get_running_loop().create_task(self._kick(kick))

    @staticmethod
    async def _kick(kick: Kicker) -> None:
        try:
            await kick()
        except Exception:  # noqa: BLE001
            pass

    async def broadcast(self, msg: dict[str, Any]) -> None:
        await asyncio.gather(*(self._send(m, msg) for m in list(self.members.values()) if m.send))

    async def push_lobby(self) -> None:
        await self.broadcast(self.lobby())

    # ------------------------------------------------------------ lobby
    def join(self, name: str, user: dict[str, Any] | None, send: Sender, spectator: bool, kick: Kicker | None = None,
             ambil_alih: bool = False) -> Member:
        name = clean_name(user["username"] if user else name)
        same = next((x for x in self.members.values() if x.name.lower() == name.lower()), None)
        if same is not None:
            # Masuk lagi dengan nama yang sama = kembali ke kursi itu (misalnya sesi browser hilang atau pindah HP).
            if same.user and (not user or user.get("id") != same.user.get("id")):
                raise RoomError("Nama itu milik akun lain di room ini. Masuk dengan akun itu, atau pakai nama lain.")
            same_account = bool(user and same.user)
            if same.online and same.send is not None and not ambil_alih and not same_account:
                raise RoomError(f"Nama {same.name} sedang dipakai di room ini.", kode="nama_dipakai")
            return self.rejoin(same.id, same.token, send, kick)
        if len(self.members) >= 60:
            raise RoomError("Room penuh.")
        if not spectator and self.status == "lobby" and len(self.seats) >= self.game.max_pemain:
            spectator = True
        m = Member(self._id(), secrets.token_urlsafe(18), name, user, send, spectator, kick=kick)
        self.members[m.id] = m
        if not self.host_id:
            self.host_id = m.id
        if not spectator and self.status == "lobby":
            self._unique(name)
            self.seats.append(Seat(self._id(), name, "manusia", m.id, self_seat=True, label="Manusia"))
        return m

    def rejoin(self, member_id: str, token: str, send: Sender, kick: Kicker | None = None) -> Member:
        m = self.members.get(str(member_id))
        if m is None or not secrets.compare_digest(m.token, str(token or "")):
            raise RoomError("Sesi sudah berakhir. Masuk lagi dengan nama.")
        old = m.send
        m.send, m.kick, m.online, m.last_seen = send, kick, True, time.time()
        if old is not None and old != send:
            # room yang sama dibuka di tab/perangkat lain: beri tahu tab lama supaya tidak diam membeku
            try:
                asyncio.get_running_loop().create_task(self._tell_old(old))
            except RuntimeError:
                pass
        self.wake.set()
        return m

    @staticmethod
    async def _tell_old(old: Sender) -> None:
        try:
            await asyncio.wait_for(old({"type": "pindah", "message": "Room ini dibuka di tab atau perangkat lain."}), timeout=3)
        except Exception:  # noqa: BLE001
            pass

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

    def set_settings(self, m: Member, cfg: dict[str, Any], waktu: Any, jeda: Any, jeda_hasil: Any = None,
                     penonton_semua: Any = None) -> None:
        self._need_lobby()
        if m.id != self.host_id:
            raise RoomError("Hanya host yang bisa mengubah aturan.")
        self.settings = self.game.clean_settings({**self.settings, **(cfg or {})})
        try:
            if waktu is not None:
                self.waktu = int(min(max(float(waktu), 3), 300))
            if jeda is not None:
                self.jeda = float(min(max(float(jeda), 0.0), 5.0))
            if jeda_hasil is not None:
                self.jeda_hasil = float(min(max(float(jeda_hasil), 0.0), 30.0))
            if penonton_semua is not None:
                self.penonton_semua = bool(penonton_semua)
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
        self.seed = seed
        self.status = "main"
        self.step = 0
        self.frames, self.recent, self.final = [], [], None
        self.drafts, self.ready, self.pause_until, self.deadlines = {}, set(), 0.0, {}
        self.vers, self.paused_at, self.langkah = {}, 0.0, []
        self.last = time.time()
        all_bots = all(s.kind == "bot" for s in self.seats)
        if all_bots and self.jeda == 0 and self.pool is not None:
            await self.push_lobby()
            await self.broadcast({"type": "mulai", "instan": True, "names": names})
            self.task = asyncio.create_task(self._run_instant(names, seed))
            return
        self.state = g.init(self.settings, names, seed)
        self.frames.append({"step": 0, "view": g.frame_view(self.state), "events": []})
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
        self.langkah = out.get("langkah", [])
        for s, lg in zip(self.seats, out["logs"]):
            s.bot = BotSeat(None, log=lg)
        await self._finish(out["result"], out["reveal"])

    # ------------------------------------------------------------ main loop
    def _view_for(self, mem: Member) -> tuple[dict[str, Any], int | None]:
        p = self.view_seat(mem.id)
        if p is None:
            # penonton: tampilan berkabut, kecuali host mengizinkan penonton melihat semua
            return (self.game.full_view(self.state) if self.penonton_semua else self.game.public(self.state)), None
        return self.game.observe(self.state, p), p

    async def _push_state(self, events: list[dict[str, Any]], only: set[str] | None = None) -> None:
        msgs = []
        for mem in list(self.members.values()):
            if mem.send is None or (only is not None and mem.id not in only):
                continue
            view, p = self._view_for(mem)
            viewer: Any = p if p is not None else ("semua" if self.penonton_semua else None)
            evs = [x for x in (self.game.event_for(self.state, e, viewer) for e in events) if x is not None] if events else events
            mine = self.seat_of(mem.id)
            my_turn = mine is not None and mine in self.pending and mine not in self.actions and self.status == "main"
            dl = self.deadlines.get(mine, 0) if self.game.mandiri and mine is not None else self.deadline
            msgs.append(self._send(mem, {"type": "update", "view": view, "seat": p, "pending": self.pending,
                                         "acted": list(self.actions.keys()), "my_turn": my_turn,
                                         "deadline": dl, "now": time.time(), "step": self.step, "events": evs,
                                         "jeda": self._pause_msg(), "dijeda_sejak": self.paused_at or None,
                                         "versi": self.vers.get(mine, 0) if self.game.mandiri and mine is not None else None}))
        await asyncio.gather(*msgs)

    def _bot_action(self, p: int) -> Any:
        seat = self.seats[p]
        if seat.bot is None:
            return self.game.default(self.state, p)
        return seat.bot.act(self.game, self.state, p, self.step, Limits())

    def _record(self, events: list[dict[str, Any]]) -> None:
        self.frames.append({"step": self.step, "view": self.game.frame_view(self.state), "events": events})
        if len(self.frames) > self.game.max_frames * 2:
            self.frames = self.frames[:1] + self.frames[1::2]
        self.recent = (self.recent + events)[-60:]

    async def _hold(self) -> None:
        """Tunggu selama host menjeda match."""
        while self.paused_at and self.status == "main":
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

    def _log_step(self, actions: dict[int, Any]) -> None:
        """Simpan aksi satu langkah. Game deterministik, jadi seed + daftar ini cukup untuk membuat ulang match
        (misalnya replay dari sudut pandang satu pemain)."""
        self.langkah.append({str(p): a for p, a in actions.items()})

    async def _run(self) -> None:
        g, s = self.game, self.state
        try:
            while not g.over(s):
                await self._hold()
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
                auto: list[int] = []
                self.drafts = {}

                def fill(p: int) -> None:
                    if p in self.drafts:
                        self.actions[p] = self.drafts[p]
                        auto.append(p)
                    else:
                        self.actions[p] = g.default(s, p)
                        timeouts.append(p)

                if humans:
                    self.turn_start = time.time()
                    self.deadline = self.turn_start + self.waktu
                    await self._push_state([])
                    while any(p not in self.actions for p in humans):
                        if self.paused_at:
                            await self._hold()
                            continue
                        now = time.time()
                        if now >= self.deadline:
                            break
                        for p in humans:
                            if p not in self.actions and self._gone(p, now):
                                fill(p)
                        self.wake.clear()
                        try:
                            await asyncio.wait_for(self.wake.wait(), timeout=min(1.0, max(0.05, self.deadline - now)))
                        except asyncio.TimeoutError:
                            pass
                    for p in humans:
                        if p not in self.actions:
                            fill(p)
                elif self.jeda > 0:
                    self.deadline = 0.0
                    await asyncio.sleep(self.jeda)
                    await self._hold()
                else:
                    self.deadline = 0.0
                    await asyncio.sleep(0)
                final = dict(self.actions)
                self._log_step(final)
                events = g.apply(s, final)
                if timeouts or auto:
                    events = [{"jenis": "waktu_habis", "pemain": [s["names"][p] for p in timeouts],
                               "otomatis": [s["names"][p] for p in auto]}] + events
                self.pending, self.actions, self.drafts = [], {}, {}
                self._record(events)
                pause = self._pause_len(events)
                if pause > 0:
                    self.pause_until, self.ready = time.time() + pause, set()
                await self._push_state(events)
                if pause > 0:
                    await self._wait_pause()
                self.last = time.time()
            await self._finish(g.result(s), g.reveal(s))
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("room %s error", self.code)
            self.status = "lobby"
            await self.broadcast({"type": "error", "message": "Terjadi kesalahan di server, match dihentikan."})
            await self.push_lobby()

    def _gone(self, p: int, now: float) -> bool:
        """Kursi manusia yang pemiliknya putus: jangan buat pemain lain menunggu terlalu lama, tapi beri waktu
        sambung ulang (HP sering putus sebentar saat layar mati atau pindah aplikasi)."""
        owner = self.members.get(self.seats[p].owner)
        if owner is None:
            return now - self.turn_start > 2
        if owner.online:
            return False
        since = owner.offline_since
        if since <= 0 or now - since > OFFLINE_LAMA:
            return now - self.turn_start > 2
        return now - max(since, self.turn_start) > min(10.0, self.waktu)

    def _human_seats(self) -> list[int]:
        return [i for i, seat in enumerate(self.seats) if seat.kind == "manusia"]

    def _pause_len(self, events: list[dict[str, Any]]) -> float:
        """Jeda lihat hasil: hanya setelah event akhir ronde, dan hanya kalau ada pemain manusia."""
        if self.jeda_hasil <= 0 or not self.game.jeda_pada or not self._human_seats():
            return 0.0
        if any(e.get("jenis") in self.game.jeda_pada for e in events):
            return self.jeda_hasil
        return 0.0

    def _pause_msg(self) -> dict[str, Any] | None:
        if self.pause_until <= 0:
            return None
        return {"sampai": self.pause_until, "siap": sorted(self.ready), "lama": self.jeda_hasil}

    def _all_ready(self) -> bool:
        waiting = []
        for p in self._human_seats():
            owner = self.members.get(self.seats[p].owner)
            if owner is not None and owner.online:
                waiting.append(p)
        return bool(waiting) and all(p in self.ready for p in waiting)

    async def _wait_pause(self) -> None:
        try:
            while (time.time() < self.pause_until or self.paused_at) and not self._all_ready():
                if self.paused_at:
                    await self._hold()
                    continue
                self.wake.clear()
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=max(0.05, min(1.0, self.pause_until - time.time())))
                except asyncio.TimeoutError:
                    pass
        finally:
            self.pause_until, self.ready = 0.0, set()

    def _apply_mandiri(self, p: int, a: Any) -> list[dict[str, Any]]:
        self.step += 1
        self._log_step({p: a})
        events = self.game.apply(self.state, {p: a})
        self.vers[p] = self.vers.get(p, 0) + 1
        return events

    async def _run_mandiri(self) -> None:
        """Setiap pemain jalan sendiri (misalnya deck-builder): tidak menunggu pemain lain."""
        g, s = self.game, self.state
        next_bot: dict[int, float] = {}
        last_push = 0.0
        try:
            while not g.over(s):
                if self.paused_at:
                    await self._hold()
                    continue
                now = time.time()
                pend = set(g.pending(s))
                self.pending = sorted(pend)
                changed: list[dict[str, Any]] = []
                for p in self.pending:
                    seat = self.seats[p]
                    if seat.kind == "bot":
                        if now >= next_bot.get(p, 0):
                            changed += self._apply_mandiri(p, self._bot_action(p))
                            next_bot[p] = now + max(self.jeda, 0.05)
                    else:
                        if p not in self.deadlines:
                            self.deadlines[p] = now + self.waktu
                        owner = self.members.get(seat.owner)
                        offline = owner is None or not owner.online
                        if now >= self.deadlines[p] or (offline and now - self.deadlines[p] + self.waktu > 2):
                            changed += [{"jenis": "waktu_habis", "pemain": [s["names"][p]]}] + self._apply_mandiri(p, g.default(s, p))
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

    def _expected_step(self, p: int) -> int:
        return self.vers.get(p, 0) if self.game.mandiri else self.step

    def _check_step(self, p: int, step: Any) -> bool:
        """True kalau pesan klien dibuat untuk langkah yang sedang berjalan (atau klien lama tanpa nomor langkah)."""
        if step is None:
            return True
        try:
            return int(step) == self._expected_step(p)
        except (TypeError, ValueError):
            return False

    async def act(self, m: Member, action: Any, step: Any = None) -> None:
        if self.status != "main" or self.state is None:
            raise RoomError("Match belum berjalan.")
        p = self.seat_of(m.id)
        if p is None:
            raise RoomError("Kamu tidak punya kursi manusia di match ini.")
        if self.paused_at:
            raise RoomError("Match sedang dijeda host.")
        # Jawaban selalu membawa nomor langkah. Klik yang sampai setelah waktunya habis DITOLAK, bukan dipakai untuk
        # langkah berikutnya (dulu ini membuat pemain tidak bisa memilih apa pun di ronde berikutnya).
        if not self._check_step(p, step):
            raise RoomError("Terlambat: waktu langkah itu sudah habis, jawabanmu tidak dihitung. Pilih lagi untuk langkah ini.",
                            kode="telat")
        if p not in self.game.pending(self.state) or (not self.game.mandiri and p not in self.pending):
            raise RoomError("Belum giliranmu." if self.pause_until <= 0 else "Tunggu, hasil ronde sedang ditampilkan.")
        try:
            a = self.game.validate(self.state, p, action)
        except ActionError as e:
            raise RoomError(str(e)) from None
        if self.game.mandiri:
            events = self._apply_mandiri(p, a)
            self.deadlines[p] = time.time() + self.waktu
            self._record(events)
            self.dirty = True
            await self._push_state(events, only={m.id})
            self.wake.set()
            return
        changed = p in self.actions
        self.actions[p] = a      # boleh diubah selama ronde belum ditutup
        self.drafts.pop(p, None)
        await self._send(m, {"type": "aksi_ok", "step": self.step, "aksi": a, "ubah": changed})
        if not changed:
            await self.broadcast({"type": "sudah", "kursi": p, "step": self.step})
        self.wake.set()

    async def retract(self, m: Member, step: Any = None) -> None:
        """Tarik kembali jawaban (tombol "Ubah") selama ronde belum ditutup."""
        if self.status != "main" or self.state is None or self.game.mandiri:
            return
        p = self.seat_of(m.id)
        if p is None or p not in self.pending or not self._check_step(p, step) or p not in self.actions:
            return
        del self.actions[p]
        await self._send(m, {"type": "batal_ok", "step": self.step})
        await self.broadcast({"type": "batal", "kursi": p, "step": self.step})

    def draft(self, m: Member, action: Any, step: Any = None) -> None:
        """Pilihan yang sedang terlihat di layar pemain (belum menekan kirim). Dipakai otomatis kalau waktunya habis."""
        if self.status != "main" or self.state is None or self.game.mandiri:
            return
        p = self.seat_of(m.id)
        if p is None or p not in self.pending or p in self.actions or not self._check_step(p, step):
            return
        try:
            self.drafts[p] = self.game.validate(self.state, p, action)
        except (ActionError, TypeError, ValueError):
            self.drafts.pop(p, None)

    async def next_round(self, m: Member, step: Any = None) -> None:
        """Tombol "Lanjut" saat jeda lihat hasil. Jeda selesai lebih cepat kalau semua manusia yang online sudah siap."""
        p = self.seat_of(m.id)
        if self.pause_until <= 0 or p is None or p in self.ready:
            return
        if step is not None and str(step) != str(self.step):
            return
        self.ready.add(p)
        await self.broadcast({"type": "siap_lanjut", "kursi": p, "siap": sorted(self.ready)})
        self.wake.set()

    def toggle_pause(self, m: Member) -> bool:
        """Host menjeda / melanjutkan match. Sisa waktu langkah yang sedang berjalan dibekukan selama jeda."""
        if m.id != self.host_id:
            raise RoomError("Hanya host yang bisa menjeda match.")
        if self.status != "main":
            raise RoomError("Match belum berjalan.")
        now = time.time()
        if self.paused_at:
            d = now - self.paused_at
            if self.deadline:
                self.deadline += d
            if self.pause_until:
                self.pause_until += d
            self.turn_start += d
            for k in self.deadlines:
                self.deadlines[k] += d
            self.paused_at = 0.0
        else:
            self.paused_at = now
        self.wake.set()
        return self.paused_at > 0

    def reset_sesi(self, m: Member) -> None:
        if m.id != self.host_id:
            raise RoomError("Hanya host yang bisa mengulang klasemen sesi.")
        self.sesi = {}

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
        n = len(result["ranking"])
        for rank, i in enumerate(result["ranking"]):
            e = self.sesi.setdefault(names[i], {"nama": names[i], "main": 0, "juara": 0, "poin": 0})
            e["main"] += 1
            e["poin"] += n - 1 - rank
            if rank == 0:
                e["juara"] += 1
        replay_id = None
        if self.replay_store is not None and self.langkah:
            try:
                replay_id = self.replay_store({"game": self.game.id, "settings": self.settings, "names": names,
                                               "seed": self.seed, "langkah": self.langkah})
            except Exception:  # noqa: BLE001
                log.exception("simpan replay gagal")
        self.final = {"type": "selesai", "result": result, "reveal": reveal, "names": names,
                      "kinds": [s.kind for s in self.seats], "ratings": ratings, "replay_id": replay_id,
                      "frames": thin_frames(self.frames, self.game.max_frames)}
        for mem in list(self.members.values()):
            logs = {s.name: s.bot.log for s in self.seats if s.owner == mem.id and s.bot is not None}
            await self._send(mem, {**self.final, "logs": logs})
        await self.push_lobby()
        self.status = "lobby"
        self.state = None
        self.paused_at = 0.0
        await self.push_lobby()


class ArenaManager:
    def __init__(self, pool=None, on_finish=None):
        self.rooms: dict[str, GameRoom] = {}
        self.pool = pool
        self.on_finish = on_finish
        self.replays: OrderedDict[str, dict[str, Any]] = OrderedDict()   # match terakhir (untuk replay sudut pandang)

    def add_replay(self, data: dict[str, Any]) -> str:
        rid = secrets.token_urlsafe(9)
        self.replays[rid] = data
        while len(self.replays) > REPLAY_MAKS:
            self.replays.popitem(last=False)
        return rid

    def create(self, game_id: str, settings: dict[str, Any], waktu: Any, jeda: Any, jeda_hasil: Any = None) -> GameRoom:
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
        try:
            jh = float(jeda_hasil) if jeda_hasil not in (None, "") else None
        except (TypeError, ValueError):
            jh = None
        room = GameRoom(code, g, settings or {}, int(w), j, self.pool, self.on_finish, jeda_hasil=jh, replay_store=self.add_replay)
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
