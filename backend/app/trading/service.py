"""Sesi solo, tantangan harian, dan balapan room untuk Kilas Pasar."""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import logging
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable

import numpy as np

from .accounts import AccountDB
from .derivatives import DerivAccount
from .engine import Account, TradeError
from .markets import MARKETS
from .products import catalog as product_catalog
from .products import product_for, products
from .session import Blind, MarketView, SessionError, build_view, eligible_assets
from .store import CandleStore
from .timeframes import LABEL

log = logging.getLogger("kilas")
Sender = Callable[[dict[str, Any]], Awaitable[None]]

DAILY_STEPS = 150
DAILY_TFS = {"crypto": ["15m", "1h", "4h"], "idx": ["1d", "1h"], "us": ["1d", "1h"], "demo": ["15m", "1h"]}
WIB = dt.timezone(dt.timedelta(hours=7))


class GameError(Exception):
    pass


def today_wib() -> str:
    return dt.datetime.now(WIB).strftime("%Y-%m-%d")


def _num(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(x):
        return default
    return min(max(x, lo), hi)


def rules_of(cfg: dict[str, Any]) -> str:
    return "bebas" if str(cfg.get("aturan") or "") == "bebas" else "nyata"


def make_account(view: MarketView, cfg: dict[str, Any]) -> Account | DerivAccount:
    spec = view.spec
    capital = _num(cfg.get("modal"), 1, 1e13, spec.capital)
    slippage = _num(cfg.get("slippage"), 0, 0.02, spec.slippage)
    qty_step = spec.qty_step if not (view.blind.harga and spec.qty_step < 1) else 1e-8
    pid = str(cfg.get("produk") or "spot")
    if pid == "spot":
        return Account(
            capital=capital,
            fee_buy=_num(cfg.get("fee_beli"), 0, 0.05, spec.fee_buy),
            fee_sell=_num(cfg.get("fee_jual"), 0, 0.05, spec.fee_sell),
            slippage=slippage, qty_step=qty_step, min_notional=spec.min_notional,
        )
    prod = product_for(view.market, pid, view.info["symbol"], rules_of(cfg))
    if prod is None:
        raise GameError(f"Produk itu tidak tersedia untuk {spec.nama}" + (" dengan aturan pasar asli." if rules_of(cfg) == "nyata" else "."))
    if prod.kind == "perp":
        fee_buy = fee_sell = _num(cfg.get("fee_taker"), 0, 0.05, prod.fee_buy)
        maker = _num(cfg.get("fee_maker"), -0.001, 0.05, prod.maker or 0.0)
    else:
        fee_buy = _num(cfg.get("fee_beli"), 0, 0.05, prod.fee_buy)
        fee_sell = _num(cfg.get("fee_jual"), 0, 0.05, prod.fee_sell)
        maker = None
    return DerivAccount(
        prod, capital, slippage, qty_step, spec.min_notional, symbol=view.info["symbol"],
        unit_factor=view.k, fee_buy=fee_buy, fee_sell=fee_sell, maker=maker,
        interest_apr=_num(cfg.get("bunga"), 0, 1, prod.interest_apr),
        borrow_apr=_num(cfg.get("biaya_pinjam"), 0, 1, prod.borrow_apr),
        funding_schedule=view.funding_schedule(prod.funding, prod.funding_hours) if prod.kind == "perp" else None,
        leverage=_num(cfg.get("leverage"), 1, prod.max_lev, prod.default_lev),
    )


def session_payload(view: MarketView, acc: Account | DerivAccount, mode: str, chart_tf: str,
                    extra: dict[str, Any]) -> dict[str, Any]:
    spec = view.spec
    deriv = isinstance(acc, DerivAccount)
    product = None
    if deriv:
        product = acc.p.public(view.info["symbol"])
        product.update({"fee_beli": acc.fee_buy, "fee_jual": acc.fee_sell, "maker": acc.maker,
                        "interest_apr": acc.interest_apr, "borrow_apr": acc.borrow_apr})
        if view.blind.nama:
            product["short_list"] = None  # jangan bocorkan nama aset lewat daftar short
    return {
        "produk": acc.p.id if deriv else "spot", "product": product,
        "type": "session", "mode": mode, "market": view.market, "market_nama": spec.nama,
        "currency": spec.currency, "label": view.label(), "blind": asdict(view.blind),
        "tfs": view.tfs, "tf_label": {tf: LABEL[tf] for tf in view.tfs}, "base_tf": view.base_tf,
        "chart_tf": chart_tf, "decimals": view.decimals, "lot": spec.lot, "qty_step": acc.qty_step,
        "satuan": spec.satuan, "min_notional": acc.min_notional,
        "fees": {"beli": acc.fee_buy, "jual": acc.fee_sell, "slippage": acc.slippage, "catatan": spec.catatan_fee},
        "capital": acc.capital, "start_time": int(view.disp_time(int(view.base["lt"][view.start_idx]))),
        "now": view.now(), "price": view.last_price(), "progress": view.progress(),
        "fixed_end": extra.pop("fixed_end", False), **extra,
    }


def fill_payload(f: Any) -> dict[str, Any]:
    return asdict(f)


def downsample(points: list[tuple[int, float]], n: int = 600) -> list[list[float]]:
    if len(points) <= n:
        return [list(p) for p in points]
    idx = np.linspace(0, len(points) - 1, n).astype(int)
    return [list(points[i]) for i in idx]


@dataclass
class Trader:
    """Satu pemain dalam satu sesi (solo/harian) atau balapan."""
    account: Account
    subs: set[str]
    send: Sender | None = None
    name: str = ""
    user: dict[str, Any] | None = None
    id: str = field(default_factory=lambda: secrets.token_hex(4))
    token: str = field(default_factory=lambda: secrets.token_urlsafe(18))
    online: bool = True


@dataclass
class SoloSession:
    id: str
    secret: str
    mode: str                 # solo | harian | harian-latihan
    view: MarketView
    chart_tf: str
    trader: Trader
    daily_date: str | None = None
    created: float = field(default_factory=time.time)
    last: float = field(default_factory=time.time)
    finished: dict[str, Any] | None = None


@dataclass
class RaceRoom:
    code: str
    host_id: str
    config: dict[str, Any]
    players: dict[str, Trader] = field(default_factory=dict)
    status: str = "lobby"     # lobby | running | paused | done
    view: MarketView | None = None
    chart_tf: str = "1h"
    speed: float = 2.0
    steps_total: int = 100
    step_n: int = 0
    task: asyncio.Task | None = None
    created: float = field(default_factory=time.time)
    last: float = field(default_factory=time.time)
    results: list[dict[str, Any]] | None = None


class TradingService:
    def __init__(self, store: CandleStore, db: AccountDB):
        self.store = store
        self.db = db
        self.sessions: dict[str, SoloSession] = {}
        self.rooms: dict[str, RaceRoom] = {}

    # ------------------------------------------------------------ katalog
    def catalog(self) -> dict[str, Any]:
        summ = self.store.summary()
        specs = {
            m: {"id": m, "nama": s.nama, "currency": s.currency, "modal": s.capital, "fee_beli": s.fee_buy,
                "fee_jual": s.fee_sell, "slippage": s.slippage, "lot": s.lot, "satuan": s.satuan,
                "catatan_fee": s.catatan_fee, "tfs": list(s.tfs)}
            for m, s in MARKETS.items()
        }
        return {"pasar": summ, "spec": specs, "tf_label": LABEL,
                "produk": {"nyata": product_catalog("nyata"), "bebas": product_catalog("bebas")}}

    def _pick_asset(self, rng: np.random.Generator, market: str | None, asset: str | None, tf: str) -> str:
        if asset:
            if not self.store.asset(asset):
                raise GameError("Aset tidak ditemukan.")
            return asset
        keys = eligible_assets(self.store, market, tf, 300)
        if not keys:
            raise GameError("Belum ada data untuk pilihan ini. Unduh data dulu (lihat panduan) atau pilih pasar/timeframe lain.")
        return keys[int(rng.integers(0, len(keys)))]

    # ------------------------------------------------------------ solo
    def start_solo(self, cfg: dict[str, Any], user: dict[str, Any] | None, send: Sender) -> SoloSession:
        rng = np.random.default_rng()
        tf = str(cfg.get("tf") or "1h")
        market = cfg.get("pasar") or None
        key = self._pick_asset(rng, market, cfg.get("aset") or None, tf)
        blind = Blind.from_any(cfg.get("buta", True))
        start = _num(cfg.get("mulai"), 0, 4e9, 0) if (cfg.get("mulai") and not blind.tanggal) else None
        try:
            view = build_view(self.store, key, tf, rng, blind, start=start or None)
        except SessionError as e:
            raise GameError(str(e)) from None
        trader = Trader(make_account(view, cfg), {tf}, send, user=user)
        s = SoloSession(secrets.token_hex(8), secrets.token_urlsafe(18), "solo", view, tf, trader)
        self.sessions[s.id] = s
        return s

    # ------------------------------------------------------------ harian
    def daily_config(self, date: str) -> dict[str, Any]:
        cfg = self.db.daily_config(date)
        if cfg:
            return cfg
        seed = int(hashlib.sha256(f"kilas-harian-{date}".encode()).hexdigest()[:12], 16)
        rng = np.random.default_rng(seed)
        markets = [m for m in ("crypto", "idx", "us") if eligible_assets(self.store, m, DAILY_TFS[m][0], 400)]
        if not markets and eligible_assets(self.store, "demo", "15m", 400):
            markets = ["demo"]
        if not markets:
            raise GameError("Tantangan harian butuh data pasar. Unduh data dulu.")
        day_no = dt.date.fromisoformat(date).toordinal()
        market = markets[day_no % len(markets)]
        tfs = [tf for tf in DAILY_TFS[market] if eligible_assets(self.store, market, tf, 400)]
        tf = tfs[int(rng.integers(0, len(tfs)))]
        keys = eligible_assets(self.store, market, tf, 400)
        key = keys[int(rng.integers(0, len(keys)))]
        chart = self.store.series(key, tf)
        idx = int(rng.integers(200, len(chart) - DAILY_STEPS - 2))
        cfg = {"date": date, "pasar": market, "aset": key, "tf": tf, "mulai": int(chart["t"][idx]) // 1000,
               "langkah": DAILY_STEPS, "seed": seed}
        return self.db.save_daily_config(date, cfg)

    def _daily_view(self, cfg: dict[str, Any]) -> MarketView:
        rng = np.random.default_rng(cfg["seed"])
        return build_view(self.store, cfg["aset"], cfg["tf"], rng, Blind(), start=cfg["mulai"], steps=cfg["langkah"])

    def start_daily(self, user: dict[str, Any] | None, send: Sender) -> SoloSession:
        date = today_wib()
        cfg = self.daily_config(date)
        mode = "harian-latihan"
        if user:
            entry = self.db.daily_entry(date, user["id"])
            live = any(s.daily_date == date and s.mode == "harian" and s.trader.user and s.trader.user["id"] == user["id"]
                       and not s.finished for s in self.sessions.values())
            if live:
                raise GameError("Tantangan harianmu masih berjalan. Lanjutkan dari halaman Tantangan harian.")
            if entry is None or entry["status"] == "started":
                mode = "harian"
                self.db.daily_begin(date, user["id"])
        try:
            view = self._daily_view(cfg)
        except SessionError as e:
            raise GameError(str(e)) from None
        trader = Trader(make_account(view, {}), {cfg["tf"]}, send, user=user)
        s = SoloSession(secrets.token_hex(8), secrets.token_urlsafe(18), mode, view, cfg["tf"], trader, daily_date=date)
        self.sessions[s.id] = s
        return s

    def daily_info(self, user: dict[str, Any] | None) -> dict[str, Any]:
        date = today_wib()
        try:
            cfg = self.daily_config(date)
        except GameError as e:
            return {"date": date, "error": str(e), "board": []}
        spec = MARKETS[cfg["pasar"]]
        me = None
        if user:
            e = self.db.daily_entry(date, user["id"])
            live = next((s for s in self.sessions.values() if s.daily_date == date and s.trader.user
                         and s.trader.user["id"] == user["id"] and not s.finished), None)
            me = {"status": e["status"] if e else None, "return_pct": e["return_pct"] if e else None,
                  "rank": self.db.daily_rank(date, user["id"]),
                  "resume": {"id": live.id, "secret": live.secret} if live else None}
        return {"date": date, "pasar": spec.nama, "tf": cfg["tf"], "tf_label": LABEL[cfg["tf"]],
                "langkah": cfg["langkah"], "board": self.db.daily_board(date), "me": me}

    # ------------------------------------------------------------ aksi umum
    def history(self, view: MarketView, tf: str, before: Any, limit: Any) -> dict[str, Any]:
        b = None if before in (None, "") else _num(before, -1e12, 1e12, 0)
        candles, more = view.candles(tf, b, int(_num(limit, 10, 5000, 1500)))
        return {"type": "candles", "tf": tf, "candles": candles, "more": more, "before": before}

    def trade(self, view: MarketView, tr: Trader, msg: dict[str, Any]) -> list[dict[str, Any]]:
        acc = tr.account
        price, now = view.last_price(), view.now()
        t = msg.get("type")
        if isinstance(acc, DerivAccount):
            return [fill_payload(f) for f in acc.handle(msg, price, now)]
        if t in ("close", "leverage", "margin_mode", "margin_adjust"):
            raise GameError("Fitur ini hanya ada di mode Futures atau Margin.")
        fills = []
        if t == "order":
            kind = msg.get("kind", "market")
            if kind == "market":
                fills.append(acc.market(msg.get("side"), msg.get("qty"), price, now, msg.get("sl"), msg.get("tp")))
            else:
                acc.place(msg.get("side"), kind, msg.get("price"), msg.get("qty"), now, price, msg.get("sl"), msg.get("tp"))
        elif t == "protect":
            acc.protect(msg.get("qty"), msg.get("sl"), msg.get("tp"), now, price)
        elif t == "cancel":
            acc.cancel(msg.get("id"))
        return [fill_payload(f) for f in fills]

    def account_msg(self, view: MarketView, tr: Trader, fills: list[dict[str, Any]] | None = None,
                    full: bool = False) -> dict[str, Any]:
        if full:  # saat (re)connect: kirim riwayat transaksi supaya penanda di chart lengkap
            return {"type": "account", "account": tr.account.snapshot(view.last_price()), "full": True,
                    "fills": [fill_payload(f) for f in tr.account.fills[-300:]]}
        return {"type": "account", "account": tr.account.snapshot(view.last_price()), "fills": fills or []}

    def run_engine(self, view: MarketView, tr: Trader, old: int, new: int) -> list[dict[str, Any]]:
        if new <= old:
            return []
        O, H, L, C, T = view.slice_for_engine(old, new)
        fills = tr.account.process(O, H, L, C, T)
        tr.account.curve.append((view.now(), tr.account.equity(view.last_price())))
        return [fill_payload(f) for f in fills]

    def tick_msg(self, view: MarketView, tr: Trader, old: int, fills: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"type": "tick", "now": view.now(), "price": view.last_price(), "progress": view.progress(),
                "done": view.done, "updates": {tf: view.updates(tf, old) for tf in tr.subs if tf in view.tfs},
                "account": tr.account.snapshot(view.last_price()), "fills": fills, **(extra or {})}

    def summary(self, view: MarketView, tr: Trader) -> dict[str, Any]:
        acc = tr.account
        st = acc.summary(view.last_price(), view.first_price())
        st["produk"] = acc.p.id if isinstance(acc, DerivAccount) else "spot"
        return {"stats": st, "curve": downsample([(view.disp_time(int(view.base["lt"][view.start_idx])).item(), acc.capital)] + acc.curve),
                "trades": acc.trades[-300:], "fills": [fill_payload(f) for f in acc.fills[-500:]],
                "reveal": view.reveal(), "currency": view.spec.currency}

    def finish(self, s: SoloSession) -> dict[str, Any]:
        if s.finished:
            return s.finished
        summ = self.summary(s.view, s.trader)
        st = summ["stats"]
        user = s.trader.user
        if user:
            self.db.add_result(user["id"], s.mode, s.view.market, s.view.info["symbol"], s.chart_tf,
                               st["return_pct"], st["buy_hold_pct"], st)
            if s.mode == "harian" and s.daily_date:
                self.db.daily_finish(s.daily_date, user["id"], st["return_pct"], st)
                summ["rank"] = self.db.daily_rank(s.daily_date, user["id"])
        summ["mode"] = s.mode
        s.finished = {"type": "summary", **summ}
        return s.finished

    # ------------------------------------------------------------ balapan
    def _room_code(self) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        for _ in range(500):
            code = "".join(secrets.choice(alphabet) for _ in range(5))
            if code not in self.rooms:
                return code
        raise GameError("Server penuh.")

    def race_create(self, name: str, cfg: dict[str, Any], user: dict[str, Any] | None, send: Sender) -> tuple[RaceRoom, Trader]:
        if len(self.rooms) >= 100:
            raise GameError("Jumlah room balapan sudah maksimal.")
        tf = str(cfg.get("tf") or "1h")
        if tf not in LABEL:
            raise GameError("Timeframe tidak dikenal.")
        pid = str(cfg.get("produk") or "spot")
        if pid != "spot" and cfg.get("pasar") and pid not in products(str(cfg["pasar"]), rules_of(cfg)):
            raise GameError("Produk itu tidak tersedia untuk pasar yang dipilih.")
        room = RaceRoom(self._room_code(), "", cfg, chart_tf=tf,
                        speed=_num(cfg.get("kecepatan"), 0.3, 15, 2.0),
                        steps_total=int(_num(cfg.get("langkah"), 20, 1000, 100)))
        tr = self._race_trader(room, name, user, send)
        room.host_id = tr.id
        self.rooms[room.code] = room
        return room, tr

    def _race_trader(self, room: RaceRoom, name: str, user: dict[str, Any] | None, send: Sender) -> Trader:
        name = " ".join(str(user["username"] if user else name or "").split())[:16]
        if not name:
            raise GameError("Isi namamu dulu.")
        if any(p.name.lower() == name.lower() for p in room.players.values()):
            raise GameError("Nama itu sudah dipakai di room ini.")
        if len(room.players) >= 20:
            raise GameError("Room penuh (maksimal 20 pemain).")
        dummy = Account(1, 0, 0, 0, 1, 0)
        tr = Trader(dummy, {room.chart_tf}, send, name=name, user=user)
        room.players[tr.id] = tr
        return tr

    def race_join(self, code: str, name: str, user: dict[str, Any] | None, send: Sender) -> tuple[RaceRoom, Trader]:
        room = self.rooms.get(str(code or "").strip().upper())
        if room is None:
            raise GameError("Room tidak ditemukan.")
        if room.status != "lobby":
            raise GameError("Balapan sudah dimulai. Tunggu balapan berikutnya.")
        return room, self._race_trader(room, name, user, send)

    def race_rejoin(self, code: str, pid: str, token: str, send: Sender) -> tuple[RaceRoom, Trader]:
        room = self.rooms.get(str(code or "").strip().upper())
        tr = room.players.get(str(pid)) if room else None
        if tr is None or not secrets.compare_digest(tr.token, str(token or "")):
            raise GameError("Sesi balapan sudah berakhir.")
        tr.send, tr.online = send, True
        return room, tr

    def race_state(self, room: RaceRoom) -> dict[str, Any]:
        cfg = room.config
        spec = MARKETS.get(cfg.get("pasar") or "", None)
        return {"type": "race_state", "code": room.code, "host_id": room.host_id, "status": room.status,
                "tf": room.chart_tf, "tf_label": LABEL.get(room.chart_tf, room.chart_tf), "speed": room.speed,
                "steps_total": room.steps_total, "step_n": room.step_n,
                "pasar": spec.nama if spec else "Acak", "modal": cfg.get("modal"),
                "produk": str(cfg.get("produk") or "spot"), "aturan": rules_of(cfg),
                "players": [{"id": p.id, "name": p.name, "online": p.online, "is_host": p.id == room.host_id}
                            for p in room.players.values()]}

    def race_board(self, room: RaceRoom) -> dict[str, Any]:
        price = room.view.last_price() if room.view else 0
        rows = []
        for p in room.players.values():
            snap = p.account.snapshot(price) if room.view else {}
            q = p.account.qty
            rows.append({"id": p.id, "name": p.name, "return_pct": snap.get("return_pct", 0.0),
                         "n_trades": snap.get("n_trades", 0), "in_market": bool(abs(q) > 1e-12), "online": p.online,
                         "side": "long" if q > 1e-12 else "short" if q < -1e-12 else None,
                         "n_liq": snap.get("n_liq", 0)})
        rows.sort(key=lambda r: -r["return_pct"])
        return {"type": "race_board", "board": rows, "step_n": room.step_n, "steps_total": room.steps_total}

    async def _send(self, tr: Trader, msg: dict[str, Any]) -> None:
        send = tr.send
        if send is None:
            return
        try:
            await send(msg)
        except Exception:  # noqa: BLE001
            if tr.send is send:  # jangan timpa koneksi baru hasil sambung ulang
                tr.send, tr.online = None, False

    async def race_broadcast(self, room: RaceRoom, msg: dict[str, Any]) -> None:
        await asyncio.gather(*(self._send(p, msg) for p in room.players.values()))

    async def race_start(self, room: RaceRoom, tr: Trader) -> None:
        if tr.id != room.host_id:
            raise GameError("Hanya host yang bisa memulai.")
        if room.status != "lobby":
            raise GameError("Balapan sudah berjalan.")
        cfg = room.config
        rng = np.random.default_rng()
        market = cfg.get("pasar") or None
        pid = str(cfg.get("produk") or "spot")
        if pid != "spot" and not market and not cfg.get("aset"):
            ok = [m for m in ("crypto", "idx", "us", "demo") if pid in products(m, rules_of(cfg))
                  and eligible_assets(self.store, m, room.chart_tf, 300)]
            if not ok:
                raise GameError("Belum ada data pasar yang mendukung produk ini.")
            market = ok[int(rng.integers(0, len(ok)))]
        key = self._pick_asset(rng, market, cfg.get("aset") or None, room.chart_tf)
        try:
            room.view = build_view(self.store, key, room.chart_tf, rng, Blind.from_any(cfg.get("buta", True)),
                                   steps=room.steps_total)
        except SessionError as e:
            raise GameError(str(e)) from None
        for p in room.players.values():
            p.account = make_account(room.view, cfg)
            p.subs = {room.chart_tf}
        room.status = "running"
        await self.race_broadcast(room, self.race_state(room))
        for p in room.players.values():
            await self._send(p, self._race_session(room, p))
            await self._send(p, self.account_msg(room.view, p, full=True))
        await self.race_broadcast(room, self.race_board(room))
        room.task = asyncio.create_task(self._race_loop(room))

    def _race_session(self, room: RaceRoom, p: Trader) -> dict[str, Any]:
        return session_payload(room.view, p.account, "balapan", room.chart_tf,
                               {"fixed_end": True, "room": room.code, "player_id": p.id})

    async def _race_loop(self, room: RaceRoom) -> None:
        view = room.view
        try:
            while room.status in ("running", "paused") and not view.done:
                await asyncio.sleep(room.speed)
                if room.status == "paused":
                    continue
                old, new = view.advance(room.chart_tf, 1)
                room.step_n += 1
                room.last = time.time()
                for p in room.players.values():
                    fills = self.run_engine(view, p, old, new)
                    await self._send(p, self.tick_msg(view, p, old, fills))
                await self.race_broadcast(room, self.race_board(room))
            if room.status != "done":
                await self.race_end(room)
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("race loop error")

    async def race_end(self, room: RaceRoom) -> None:
        room.status = "done"
        board = self.race_board(room)["board"]
        room.results = board
        for p in room.players.values():
            summ = self.summary(room.view, p)
            st = summ["stats"]
            if p.user:
                self.db.add_result(p.user["id"], "balapan", room.view.market, room.view.info["symbol"], room.chart_tf,
                                   st["return_pct"], st["buy_hold_pct"], st)
            await self._send(p, {"type": "summary", "mode": "balapan", **summ, "board": board})
        await self.race_broadcast(room, self.race_state(room))

    # ------------------------------------------------------------ bersih-bersih
    def cleanup(self) -> None:
        now = time.time()
        for sid, s in list(self.sessions.items()):
            idle = now - s.last
            if s.finished and idle > 1800:
                self.sessions.pop(sid, None)
            elif not s.finished and idle > 2 * 3600:
                if s.mode == "harian":
                    self.finish(s)  # percobaan yang ditinggal tetap dihitung
                self.sessions.pop(sid, None)
        for code, r in list(self.rooms.items()):
            if now - r.last > 3600 and (r.status in ("lobby", "done") or not any(p.online for p in r.players.values())):
                if r.task:
                    r.task.cancel()
                self.rooms.pop(code, None)
