"""Broker portofolio untuk backtest: banyak aset, satu modal, aturan & fee sama dengan Kilas Pasar.

Model akun sama dengan akun futures/margin di game (``app.trading.derivatives``)::

    ekuitas = wallet + Σ qty × (harga − entry)        qty positif = long, negatif = short
    kas     = wallet − Σ qty × entry                  (spot: tidak boleh negatif)

Produk:
* ``spot``    – tanpa leverage, tanpa short, fee beli/jual pasar.
* ``futures`` – perpetual (fee maker/taker, tier leverage, funding, likuidasi, cross atau isolated).
* ``margin``  – saham dengan pinjaman (Reg T / BEI): bunga harian, biaya pinjam saham, likuidasi paksa.

Eksekusi (dijelaskan juga di panduan):
* Keputusan dibuat saat candle ditutup; order **market** terisi di **open candle berikutnya** ± slippage.
* Limit/stop mulai aktif di candle berikutnya. Jalur harga di dalam candle: naik O → L → H → C, turun O → H → L → C.
  Gap melewati harga order → terisi di open. Limit = maker, market/stop = taker.
* Likuidasi: isolated (per posisi) dan cross dengan satu posisi memakai harga likuidasi tepat seperti di game.
  Cross dengan beberapa posisi diperiksa per candle dengan asumsi terburuk (low untuk long, high untuk short).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from ..trading.markets import MarketSpec
from ..trading.products import Product

EPS = 1e-9


class OrderError(Exception):
    """Order ditolak (dicatat di log backtest, tidak menghentikan backtest)."""


@dataclass
class BOrder:
    id: int
    sym: str
    side: str                    # buy | sell
    kind: str                    # market | limit | stop | stop_limit
    qty: float
    price: float | None          # harga limit, atau harga picu untuk stop
    created: int                 # waktu (detik UTC) candle saat order dibuat
    stop: float | None = None    # harga picu stop_limit
    label: str = ""
    group: int | None = None
    sl: float | None = None
    tp: float | None = None
    reduce_only: bool = False
    triggered: bool = False
    reserved: float = 0.0
    status: str = "open"

    @property
    def trigger(self) -> float:
        if self.kind == "stop_limit" and not self.triggered and self.stop:
            return self.stop
        return float(self.price or 0.0)

    @property
    def is_limit(self) -> bool:
        return self.kind == "limit" or (self.kind == "stop_limit" and self.triggered)

    @property
    def cond(self) -> str:
        buy = self.side == "buy"
        return ("le" if buy else "ge") if self.is_limit else ("ge" if buy else "le")

    def public(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("reserved", None)
        return d


@dataclass
class Pos:
    qty: float = 0.0
    entry: float = 0.0
    iso: float = 0.0
    cycle: dict[str, Any] | None = None

    @property
    def sign(self) -> int:
        return 1 if self.qty > EPS else -1 if self.qty < -EPS else 0

    @property
    def size(self) -> float:
        return abs(self.qty)


@dataclass
class BFill:
    id: int
    sym: str
    order_id: int | None
    time: int
    side: str
    qty: float
    price: float
    fee: float
    label: str
    pnl: float | None = None
    note: str = ""


@dataclass
class BrokerConfig:
    market: MarketSpec
    produk: str                               # spot | futures | margin
    products: dict[str, Product] = field(default_factory=dict)   # per simbol (futures/margin)
    capital: float = 10_000.0
    leverage: float = 1.0
    margin_mode: str = "cross"
    slippage: float = 0.0
    fee_buy: float | None = None              # spot/margin: beli; futures: taker
    fee_sell: float | None = None
    maker: float | None = None
    interest_apr: float | None = None
    borrow_apr: float | None = None
    qty_step: float = 1e-6
    min_notional: float = 0.0
    funding: dict[str, Callable[[int, int], Iterable[tuple[int, float]]]] = field(default_factory=dict)


class Broker:
    def __init__(self, cfg: BrokerConfig, symbols: list[str]):
        self.cfg = cfg
        self.spec = cfg.market
        self.produk = cfg.produk
        self.kind = {"spot": "spot", "futures": "perp", "margin": "margin"}[cfg.produk]
        if self.kind != "spot" and not cfg.products:
            raise ValueError("products wajib untuk futures/margin")
        self.symbols = list(symbols)
        p0 = next(iter(cfg.products.values()), None)
        self.p0 = p0
        if self.kind == "spot":
            self.fee_buy = self.spec.fee_buy if cfg.fee_buy is None else cfg.fee_buy
            self.fee_sell = self.spec.fee_sell if cfg.fee_sell is None else cfg.fee_sell
            self.maker = None
            self.lev = 1.0
        else:
            self.fee_buy = p0.fee_buy if cfg.fee_buy is None else cfg.fee_buy
            self.fee_sell = p0.fee_sell if cfg.fee_sell is None else cfg.fee_sell
            self.maker = p0.maker if cfg.maker is None else cfg.maker
            self.lev = float(min(p0.max_lev, max(1.0, cfg.leverage)))
        self.interest_apr = (p0.interest_apr if p0 else 0.0) if cfg.interest_apr is None else cfg.interest_apr
        self.borrow_apr = (p0.borrow_apr if p0 else 0.0) if cfg.borrow_apr is None else cfg.borrow_apr
        self.mode = cfg.margin_mode if (self.kind == "perp" and cfg.margin_mode in ("cross", "isolated")) else "cross"
        self.slippage = cfg.slippage
        self.capital = float(cfg.capital)
        self.wallet = float(cfg.capital)
        self.pos: dict[str, Pos] = {s: Pos() for s in symbols}
        self.price: dict[str, float] = {}
        self.prev_close: dict[str, float] = {}
        self.orders: dict[int, BOrder] = {}
        self.fills: list[BFill] = []
        self.trades: list[dict[str, Any]] = []
        self.log: list[str] = []
        self.fees_paid = self.funding_paid = self.interest_paid = self.borrow_paid = self.liq_loss = 0.0
        self.realized = 0.0
        self.n_liq = 0
        self.t_now = 0
        self._next_id = 1
        self._next_group = 1

    # ================================================================ dasar
    def _id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    def note(self, msg: str) -> None:
        if len(self.log) < 2000:
            self.log.append(msg)

    def prod(self, sym: str) -> Product | None:
        return self.cfg.products.get(sym)

    def px(self, sym: str) -> float:
        return self.price.get(sym, 0.0)

    def floor_qty(self, q: float) -> float:
        step = self.cfg.qty_step
        if q <= 0:
            return 0.0
        return round(math.floor(q / step + 1e-9) * step, 10)

    def short_ok(self, sym: str) -> bool:
        if self.kind == "spot":
            return False
        p = self.prod(sym)
        return bool(p and p.short_ok(sym))

    # ------------------------------------------------------------ nilai akun
    def upnl(self, sym: str, price: float | None = None) -> float:
        p = self.pos[sym]
        if not p.sign:
            return 0.0
        return p.qty * ((self.px(sym) if price is None else price) - p.entry)

    def equity(self) -> float:
        return self.wallet + sum(self.upnl(s) for s in self.symbols)

    def cash(self) -> float:
        return self.wallet - sum(p.qty * p.entry for p in self.pos.values())

    def n_open(self) -> int:
        return sum(1 for p in self.pos.values() if p.sign)

    def reserved(self) -> float:
        return sum(o.reserved for o in self.orders.values() if o.status == "open")

    def position_margin(self) -> float:
        if self.kind == "spot":
            return 0.0
        if self.mode == "isolated":
            return sum(p.iso for p in self.pos.values())
        return sum(p.size * self.px(s) for s, p in self.pos.items()) / self.lev

    def available(self) -> float:
        if self.kind == "spot":
            return self.cash() - self.reserved()
        if self.mode == "isolated":
            return self.wallet - sum(p.iso for p in self.pos.values()) - self.reserved()
        return self.equity() - self.position_margin() - self.reserved()

    def gross(self) -> float:
        return sum(p.size * self.px(s) for s, p in self.pos.items())

    # ------------------------------------------------------------ fee & margin
    def fee(self, sym: str, side: str, q: float, price: float, maker: bool) -> float:
        notional = q * price
        if maker and self.maker is not None:
            rate = self.maker
        else:
            rate = self.fee_buy if side == "buy" else self.fee_sell
        f = rate * notional
        p = self.prod(sym) if self.kind != "spot" else None
        if p is not None:
            if p.per_share:
                per, lo, hi_pct = p.per_share
                f += min(max(lo, per * q), hi_pct * notional)
            if side == "sell":
                f += p.sec_fee * notional
                if p.taf:
                    f += min(p.taf[0] * q, p.taf[1])
        return f

    def _fee_rate_est(self, sym: str, side: str) -> float:
        r = self.fee_buy if side == "buy" else self.fee_sell
        p = self.prod(sym) if self.kind != "spot" else None
        if p is not None:
            if p.per_share:
                r += p.per_share[2] * 0.2
            if side == "sell":
                r += p.sec_fee
        return r

    def _mmr(self, sym: str, sign: int, notional: float) -> tuple[float, float]:
        p = self.prod(sym)
        if p is None:
            return 0.0, 0.0
        if p.tiers:
            for t in p.tiers:
                if notional <= t.cap:
                    return t.mmr, t.cum
            t = p.tiers[-1]
            return t.mmr, t.cum
        return (p.mmr_long if sign > 0 else p.mmr_short), 0.0

    def maint(self, sym: str, price: float | None = None) -> float:
        pos = self.pos[sym]
        if not pos.sign or self.kind == "spot":
            return 0.0
        notional = pos.size * (self.px(sym) if price is None else price)
        mmr, cum = self._mmr(sym, pos.sign, notional)
        return max(0.0, notional * mmr - cum)

    def cap_for_lev(self, sym: str) -> float:
        p = self.prod(sym)
        if p is None or not p.tiers:
            return math.inf
        cap = 0.0
        for t in p.tiers:
            if t.max_lev >= self.lev - 1e-9:
                cap = t.cap
        return cap

    def liq_price(self, sym: str) -> float | None:
        """Harga likuidasi tepat untuk posisi isolated, atau cross yang hanya punya satu posisi."""
        if self.kind == "spot":
            return None
        pos = self.pos[sym]
        if not pos.sign:
            return None
        if self.mode == "isolated":
            base = pos.iso
        elif self.n_open() == 1:
            base = self.wallet
        else:
            return None
        q, e = pos.size, pos.entry
        mmr, cum = self._mmr(sym, pos.sign, q * e)
        price = None
        for _ in range(3):
            if pos.sign > 0:
                den = q * (1 - mmr)
                price = (q * e - base - cum) / den if den > 0 else None
            else:
                price = (base + q * e + cum) / (q * (1 + mmr))
            if price is None or price <= 0:
                return None
            m2, c2 = self._mmr(sym, pos.sign, q * price)
            if (m2, c2) == (mmr, cum):
                break
            mmr, cum = m2, c2
        return price if price and price > 0 else None

    # ================================================================ order dari strategi
    def reducible(self, sym: str, side: str) -> float:
        p = self.pos[sym]
        s = 1 if side == "buy" else -1
        return p.size if p.sign and p.sign != s else 0.0

    def _split(self, sym: str, side: str, q: float) -> tuple[float, float]:
        red = min(q, self.reducible(sym, side))
        return red, max(0.0, round(q - red, 10))

    def submit(self, sym: str, side: str, qty: float, kind: str = "market", price: float | None = None,
               stop: float | None = None, sl: float | None = None, tp: float | None = None,
               reduce_only: bool = False, label: str = "") -> BOrder:
        if sym not in self.pos:
            raise OrderError(f"{sym}: aset tidak ada di backtest ini.")
        if side not in ("buy", "sell") or kind not in ("market", "limit", "stop", "stop_limit"):
            raise OrderError("Jenis order tidak dikenal.")
        q = self.floor_qty(float(qty))
        if q <= 0:
            raise OrderError(f"{sym}: jumlah terlalu kecil (minimal {self.cfg.qty_step:g}).")
        last = self.px(sym)
        if kind != "market":
            if price is None or not (price > 0):
                raise OrderError(f"{sym}: harga order tidak valid.")
        if kind == "stop_limit" and not (stop and stop > 0):
            raise OrderError(f"{sym}: stop-limit butuh harga picu.")
        trig = stop if kind == "stop_limit" else price
        if kind in ("stop", "stop_limit") and last:
            if side == "buy" and trig <= last:
                raise OrderError(f"{sym}: harga picu stop beli harus di atas harga sekarang.")
            if side == "sell" and trig >= last:
                raise OrderError(f"{sym}: harga picu stop jual harus di bawah harga sekarang.")
        red, q_open = self._split(sym, side, q)
        if reduce_only:
            if red <= EPS and not self._pending_entry(sym, side):
                raise OrderError(f"{sym}: reduce-only tanpa posisi berlawanan.")
            q_open = 0.0
        if self.kind == "spot" and side == "sell":
            free = self.pos[sym].size - self._locked_sell(sym)
            if q > free + 1e-9 and not reduce_only:
                raise OrderError(f"{sym}: spot tidak bisa jual melebihi aset yang dimiliki (short butuh produk futures/margin).")
        if q_open > EPS and side == "sell" and self.kind != "spot" and not self.short_ok(sym):
            p = self.prod(sym)
            lst = ", ".join(sorted(p.short_list or [])) if p and p.short_list else ""
            raise OrderError(f"{sym}: short tidak tersedia" + (f" (BEI: hanya {lst})" if lst else "") + ".")
        p = self.prod(sym)
        if q_open > EPS and side == "sell" and p and p.uptick and kind in ("stop", "stop_limit"):
            raise OrderError(f"{sym}: aturan uptick BEI – short tidak boleh lewat order stop.")
        if q_open > EPS and side == "sell" and p and p.uptick and kind == "limit" and price < last - 1e-9:
            raise OrderError(f"{sym}: aturan uptick BEI – limit short harus ≥ harga terakhir.")
        od = BOrder(self._id(), sym, side, kind, q, price, self.t_now, stop=stop, label=label,
                    reduce_only=reduce_only)
        if q_open > EPS:
            ref = price if kind in ("limit", "stop_limit") else (price or last) * (1 + self.slippage)
            if sl or tp:
                od.sl, od.tp = sl, tp
                od.label = od.label or "Entry"
            if kind != "market" and ref:
                od.reserved = self._need(sym, side, q_open, ref, maker=kind != "stop")
        self.orders[od.id] = od
        return od

    def _pending_entry(self, sym: str, side: str) -> bool:
        """Ada order masuk berlawanan yang menunggu (untuk SL/TP yang dipasang bersamaan)."""
        return any(o.status == "open" and o.sym == sym and o.side != side and not o.reduce_only for o in self.orders.values())

    def _locked_sell(self, sym: str) -> float:
        total, groups = 0.0, {}
        for o in self.orders.values():
            if o.status != "open" or o.sym != sym or o.side != "sell" or o.kind == "market":
                continue
            if o.group is None:
                total += o.qty
            else:
                groups[o.group] = max(groups.get(o.group, 0.0), o.qty)
        return total + sum(groups.values())

    def cancel(self, sym: str | None = None, order_id: int | None = None) -> int:
        n = 0
        for o in self.orders.values():
            if o.status != "open":
                continue
            if order_id is not None and o.id != order_id:
                continue
            if sym is not None and o.sym != sym:
                continue
            o.status, o.reserved = "cancelled", 0.0
            n += 1
        return n

    def protect(self, sym: str, sl: float | None, tp: float | None) -> None:
        pos = self.pos[sym]
        if not pos.sign or (sl is None and tp is None):
            return
        side = "sell" if pos.sign > 0 else "buy"
        g = self._next_group
        self._next_group += 1
        if sl is not None:
            o = BOrder(self._id(), sym, side, "stop", pos.size, sl, self.t_now, label="SL", group=g, reduce_only=True)
            self.orders[o.id] = o
        if tp is not None:
            o = BOrder(self._id(), sym, side, "limit", pos.size, tp, self.t_now, label="TP", group=g, reduce_only=True)
            self.orders[o.id] = o

    def _need(self, sym: str, side: str, q_open: float, price: float, maker: bool) -> float:
        if self.kind == "spot":
            return q_open * price + self.fee(sym, side, q_open, price, maker) if side == "buy" else 0.0
        return q_open * price / self.lev + self.fee(sym, side, q_open, price, maker)

    # ================================================================ eksekusi
    def _fits(self, sym: str, side: str, q: float, px: float, maker: bool) -> float:
        """Jumlah terbesar (≤ q) yang boleh diisi sekarang dengan margin/kas yang ada."""
        red, q_open = self._split(sym, side, q)
        if q_open <= EPS:
            return q
        if self.kind == "spot":
            if side == "sell":
                return red
            per = px * (1 + self._fee_rate_est(sym, side))
            fit = max(0.0, self.available()) / per if per > 0 else 0.0
            return self.floor_qty(min(q_open, fit))
        if side == "sell" and not self.short_ok(sym):
            return red
        p = self.prod(sym)
        if side == "sell" and p and p.min_short_equity and self.equity() < p.min_short_equity - 1e-6:
            self.note(f"{sym}: short ditolak, jaminan awal minimal {p.min_short_equity:,.0f}".replace(",", "."))
            return red
        avail = self.available()
        pos = self.pos[sym]
        if red > EPS:
            avail += (pos.iso + self.upnl(sym, px)) if self.mode == "isolated" else pos.size * px / self.lev
        per = px * (1 / self.lev + self._fee_rate_est(sym, side))
        fit = max(0.0, avail) / per if per > 0 else 0.0
        same = pos.size if (pos.sign and pos.sign == (1 if side == "buy" else -1)) else 0.0
        cap = self.cap_for_lev(sym)
        if math.isfinite(cap):
            fit = min(fit, max(0.0, cap / px - same))
        return self.floor_qty(red + min(q_open, fit))

    def _exec(self, sym: str, side: str, q: float, price: float, od: BOrder | None, label: str, maker: bool) -> BFill:
        pos = self.pos[sym]
        s = 1 if side == "buy" else -1
        fee = self.fee(sym, side, q, price, maker)
        self.wallet -= fee
        self.fees_paid += fee
        pnl_c: float | None = None
        red = min(q, pos.size) if pos.sign and pos.sign != s else 0.0
        if red > EPS:
            pnl_c = red * (price - pos.entry) * pos.sign
            self.wallet += pnl_c
            self.realized += pnl_c
            c = pos.cycle
            if c is not None:
                c["fees"] += fee * red / q
                c["pnl"] += pnl_c
                c["exit_val"] += red * price
                c["exit_q"] += red
            left = round(pos.size - red, 10)
            if self.mode == "isolated" and pos.size > EPS:
                pos.iso *= left / pos.size
            if left <= EPS:
                pos.qty, pos.entry, pos.iso = 0.0, 0.0, 0.0
                self._end_cycle(sym, price)
            else:
                pos.qty = left * pos.sign
        rest = round(q - red, 10)
        if rest > EPS:
            if not pos.sign:
                pos.cycle = {"sym": sym, "side": "long" if s > 0 else "short", "entry_time": self.t_now,
                             "entry_price": price, "lev": self.lev, "max_notional": 0.0, "fees": 0.0,
                             "funding": 0.0, "borrow": 0.0, "pnl": 0.0, "exit_val": 0.0, "exit_q": 0.0, "n": 0}
            new = pos.size + rest
            pos.entry = (pos.size * pos.entry + rest * price) / new
            pos.qty = new * s
            if self.mode == "isolated":
                pos.iso += rest * price / self.lev
            c = pos.cycle
            if c is not None:
                c["fees"] += fee * rest / q
                c["max_notional"] = max(c["max_notional"], new * price)
        if pos.cycle is not None:
            pos.cycle["n"] += 1
        f = BFill(self._id(), sym, od.id if od else None, self.t_now, side, q, price, fee, label,
                  None if pnl_c is None else pnl_c - fee * red / q)
        self.fills.append(f)
        return f

    def _end_cycle(self, sym: str, price: float) -> None:
        pos = self.pos[sym]
        c, pos.cycle = pos.cycle, None
        for o in self.orders.values():
            if o.status == "open" and o.sym == sym and o.reduce_only:
                o.status, o.reserved = "cancelled", 0.0
        if c is None:
            return
        net = c["pnl"] - c["fees"] - c["funding"] - c["borrow"]
        base = c["max_notional"] or 1.0
        self.trades.append({
            "sym": sym, "side": c["side"], "entry_time": c["entry_time"], "exit_time": self.t_now,
            "entry_price": c["entry_price"], "exit_price": c["exit_val"] / c["exit_q"] if c["exit_q"] else price,
            "pnl": net, "pnl_pct": net / base * 100, "roe_pct": net / (base / max(c["lev"], 1.0)) * 100,
            "lev": c["lev"], "fees": c["fees"], "funding": c["funding"], "borrow": c["borrow"], "notional": base,
            "n_fills": c["n"], "liquidated": bool(c.get("liq")),
        })

    def _fill_order(self, od: BOrder, px: float, maker: bool) -> BFill | None:
        od.status = "filled"
        if od.group is not None:
            for o in self.orders.values():
                if o.group == od.group and o.id != od.id and o.status == "open":
                    o.status, o.reserved = "cancelled", 0.0
        od.reserved = 0.0
        q = od.qty
        if od.reduce_only:
            q = self.floor_qty(min(q, self.reducible(od.sym, od.side)))
            if q <= EPS:
                od.status = "cancelled"
                return None
        else:
            fit = self._fits(od.sym, od.side, q, px, maker)
            if fit <= EPS or fit * px < self.cfg.min_notional - EPS:
                od.status = "cancelled"
                self.note(f"{od.sym}: order {od.side} {q:g} batal (margin/kas tidak cukup)")
                return None
            if fit < q - 1e-12:
                self.note(f"{od.sym}: order {od.side} terisi sebagian {fit:g}/{q:g} (margin/kas kurang)")
            q = fit
        label = od.label or {"market": "Market", "limit": "Limit", "stop": "Stop", "stop_limit": "Stop-limit"}[od.kind]
        f = self._exec(od.sym, od.side, q, px, od, label, maker)
        if (od.sl or od.tp) and self.pos[od.sym].sign:
            self.protect(od.sym, od.sl, od.tp)
        return f

    def _trigger(self, od: BOrder, at: float) -> BFill | None:
        if od.kind == "stop_limit" and not od.triggered:
            od.triggered = True
            lim = od.price or at
            if (od.side == "buy" and at <= lim) or (od.side == "sell" and at >= lim):
                return self._fill_order(od, at, maker=False)
            return None
        if od.is_limit:
            return self._fill_order(od, at, maker=True)
        px = at * (1 + self.slippage) if od.side == "buy" else at * (1 - self.slippage)
        return self._fill_order(od, px, maker=False)

    def _liquidate(self, sym: str, at: float, mm_total: float | None = None) -> BFill:
        pos = self.pos[sym]
        side = "sell" if pos.sign > 0 else "buy"
        self.n_liq += 1
        if pos.cycle is not None:
            pos.cycle["liq"] = True
        for o in self.orders.values():
            if o.status == "open" and (self.mode == "cross" or o.sym == sym):
                o.status, o.reserved = "cancelled", 0.0
        if self.kind == "perp":
            iso0 = pos.iso
            mm = self.maint(sym, at) if mm_total is None else mm_total
            w0 = self.wallet
            f = self._exec(sym, side, pos.size, at, None, "Likuidasi", maker=False)
            if self.mode == "isolated":
                penalty = max(0.0, iso0 + (self.wallet - w0))
            else:
                penalty = min(max(0.0, self.wallet), mm) if self.n_open() == 0 else 0.0
            self.wallet -= penalty
            self.liq_loss += penalty
            if self.mode == "cross" and self.n_open() == 0 and self.wallet < 0:
                self.liq_loss += self.wallet
                self.wallet = 0.0
            if penalty and self.trades and self.trades[-1]["sym"] == sym:
                t = self.trades[-1]
                t["pnl"] -= penalty
                t["pnl_pct"] = t["pnl"] / (t["notional"] or 1.0) * 100
                t["roe_pct"] = t["pnl"] / ((t["notional"] or 1.0) / max(t["lev"], 1.0)) * 100
            f.note = "sisa margin masuk dana asuransi"
            self.note(f"{sym}: LIKUIDASI di {at:g}")
            return f
        px = at * (1 - self.slippage) if side == "sell" else at * (1 + self.slippage)
        f = self._exec(sym, side, pos.size, px, None, "Forced sell" if side == "sell" else "Forced buy", maker=False)
        f.note = "jaminan di bawah batas, ditutup paksa"
        self.note(f"{sym}: posisi ditutup paksa (margin) di {px:g}")
        return f

    # ------------------------------------------------------------ per candle
    def _open_orders(self, sym: str) -> list[BOrder]:
        return [o for o in self.orders.values() if o.status == "open" and o.sym == sym and o.kind != "market"]

    def _hit(self, od: BOrder, price: float) -> bool:
        return (od.cond == "le" and price <= od.trigger) or (od.cond == "ge" and price >= od.trigger)

    def _liq_hit(self, sym: str, price: float) -> bool:
        lp = self.liq_price(sym)
        if lp is None:
            return False
        return price <= lp if self.pos[sym].sign > 0 else price >= lp

    def open_reducing(self, sym: str, o: float, t: int) -> list[BFill]:
        """Order market yang mengurangi/menutup posisi diisi lebih dulu di open (sebelum aset lain membeli),
        supaya kas hasil penjualan bisa dipakai untuk rebalance di open yang sama."""
        self.t_now = t
        out = []
        for od in [x for x in self.orders.values() if x.status == "open" and x.sym == sym and x.kind == "market"]:
            if od.status == "open" and self.reducible(sym, od.side) > EPS and od.qty <= self.reducible(sym, od.side) + 1e-12:
                px = o * (1 + self.slippage) if od.side == "buy" else o * (1 - self.slippage)
                f = self._fill_order(od, px, maker=False)
                if f:
                    out.append(f)
        return out

    def bar(self, sym: str, o: float, h: float, l: float, c: float, t: int) -> list[BFill]:
        """Proses satu candle satu aset: order market (di open), gap, lalu jalur harga di dalam candle."""
        self.t_now = t
        out: list[BFill] = []
        prev = self.prev_close.get(sym)
        self.price[sym] = o
        # 1) order market dari keputusan candle sebelumnya
        for od in [x for x in self.orders.values() if x.status == "open" and x.sym == sym and x.kind == "market"]:
            if od.status != "open":
                continue
            p = self.prod(sym)
            red, q_open = self._split(sym, od.side, od.qty)
            if q_open > EPS and od.side == "sell" and p and p.uptick and prev is not None and o < prev - 1e-9 and not od.reduce_only:
                od.status = "cancelled"
                self.note(f"{sym}: short market ditolak aturan uptick (open {o:g} < harga terakhir {prev:g})")
                continue
            px = o * (1 + self.slippage) if od.side == "buy" else o * (1 - self.slippage)
            f = self._fill_order(od, px, maker=False)
            if f:
                out.append(f)
        # 2) gap di open
        for _ in range(200):
            hit = [x for x in self._open_orders(sym) if self._hit(x, o)]
            if hit:
                hit.sort(key=lambda x: (0 if x.reduce_only else 1, x.id))
                f = self._trigger(hit[0], o)
                if f:
                    out.append(f)
                continue
            if self._liq_hit(sym, o):
                out.append(self._liquidate(sym, o))
                continue
            break
        # 3) jalur di dalam candle
        path = [o, l, h, c] if c >= o else [o, h, l, c]
        for a, b in zip(path, path[1:]):
            cur = a
            for _ in range(400):
                lp = self.liq_price(sym)
                sign = self.pos[sym].sign
                if b < cur:
                    cands = [x for x in self._open_orders(sym) if x.cond == "le" and cur > x.trigger >= b]
                    pick = max(cands, key=lambda x: (x.trigger, x.reduce_only), default=None)
                    liq = lp if (sign > 0 and lp is not None and cur > lp >= b) else None
                    if liq is not None and (pick is None or liq > pick.trigger):
                        cur = liq
                        self.price[sym] = liq
                        out.append(self._liquidate(sym, liq))
                        continue
                elif b > cur:
                    cands = [x for x in self._open_orders(sym) if x.cond == "ge" and cur < x.trigger <= b]
                    pick = min(cands, key=lambda x: (x.trigger, not x.reduce_only), default=None)
                    liq = lp if (sign < 0 and lp is not None and cur < lp <= b) else None
                    if liq is not None and (pick is None or liq < pick.trigger):
                        cur = liq
                        self.price[sym] = liq
                        out.append(self._liquidate(sym, liq))
                        continue
                else:
                    pick = None
                if pick is None:
                    break
                cur = pick.trigger
                self.price[sym] = cur
                f = self._trigger(pick, cur)
                if f:
                    out.append(f)
        self.price[sym] = c
        self.prev_close[sym] = c
        return out

    def cross_check(self, worst: dict[str, float], t: int) -> list[BFill]:
        """Cross dengan >1 posisi: likuidasi semua kalau ekuitas di harga terburuk ≤ maintenance."""
        if self.kind == "spot" or self.mode != "cross" or self.n_open() < 2:
            return []
        eq = self.wallet
        mm = 0.0
        for s, p in self.pos.items():
            if not p.sign:
                continue
            w = worst.get(s, self.px(s))
            eq += p.qty * (w - p.entry)
            mm += self.maint(s, w)
        if eq > mm:
            return []
        self.t_now = t
        self.note(f"Likuidasi cross semua posisi (ekuitas {eq:,.2f} ≤ maintenance {mm:,.2f})")
        out = []
        for s, p in list(self.pos.items()):
            if p.sign:
                w = worst.get(s, self.px(s))
                self.price[s] = w
                out.append(self._liquidate(s, w, mm_total=mm if self.n_open() == 1 else 0.0))
        return out

    # ------------------------------------------------------------ funding & bunga
    def funding(self, sym: str, rate: float, price: float) -> None:
        pos = self.pos[sym]
        if not pos.sign or self.kind != "perp":
            return
        pay = pos.qty * price * rate
        self.wallet -= pay
        self.funding_paid += pay
        if self.mode == "isolated":
            pos.iso = max(0.0, pos.iso - pay)
        if pos.cycle is not None:
            pos.cycle["funding"] += pay

    def day(self, days: float = 1.0) -> None:
        if self.kind != "margin" or not self.n_open():
            return
        p0 = self.p0
        debt = max(0.0, -self.cash())
        interest = debt * self.interest_apr / p0.day_count * days
        self.interest_paid += interest
        self.wallet -= interest
        for s, pos in self.pos.items():
            if pos.sign < 0:
                cost = pos.size * self.px(s) * self.borrow_apr / p0.day_count * days
                self.borrow_paid += cost
                self.wallet -= cost
                if pos.cycle is not None:
                    pos.cycle["borrow"] += cost

    # ------------------------------------------------------------ penutup
    def close_all(self, t: int) -> None:
        """Tutup semua posisi di harga terakhir (akhir backtest) supaya transaksi terakhir ikut dihitung."""
        self.t_now = t
        self.cancel()
        for s, p in self.pos.items():
            if p.sign:
                side = "sell" if p.sign > 0 else "buy"
                self._exec(s, side, p.size, self.px(s), None, "Akhir backtest", maker=False)
