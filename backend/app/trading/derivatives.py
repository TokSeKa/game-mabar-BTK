"""Akun futures perpetual & akun margin (long/short dengan leverage).

Model akun (one-way mode: satu posisi bersih per sesi, positif = long, negatif = short)::

    ekuitas        = wallet + qty × (harga − entry)
    initial margin = |qty| × harga / leverage
    maintenance    = |qty| × harga × MMR − maintenance amount       (perp: MMR bertingkat)

* Cross: seluruh ekuitas jadi jaminan. Isolated: hanya margin yang dialokasikan ke posisi.
* Likuidasi saat (cross) ekuitas ≤ maintenance, atau (isolated) margin posisi + uPnL ≤ maintenance.
  Harga likuidasi dihitung tertutup lalu diperiksa di jalur harga tiap candle dasar, sama seperti order.
* Perp: funding dibayar di jam funding (default tiap 8 jam UTC). Long membayar kalau rate positif.
* Margin saham: bunga harian atas dana pinjaman (kas negatif) dan biaya pinjam saham atas nilai short.

Urutan harga di dalam candle sama dengan akun spot: candle naik O → L → H → C, candle turun O → H → L → C.
Pada titik harga yang sama, order diproses sebelum likuidasi.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

import numpy as np

from .engine import EPS, Fill, TradeError
from .products import Product

FundingSchedule = Callable[[int, int], Iterable[tuple[int, float]]]


@dataclass
class DOrder:
    id: int
    side: str                   # buy | sell
    kind: str                   # limit | stop | stop_limit
    price: float                # harga limit, atau harga picu untuk stop (market)
    qty: float
    created: int
    stop: float | None = None   # harga picu untuk stop_limit
    label: str = ""             # Entry | SL | TP | Tutup | ""
    group: int | None = None    # pasangan OCO
    sl: float | None = None
    tp: float | None = None
    reduce_only: bool = False
    post_only: bool = False
    triggered: bool = False     # stop_limit yang sudah terpicu (jadi limit)
    reserved: float = 0.0       # margin + perkiraan fee yang dikunci
    status: str = "open"

    @property
    def trigger(self) -> float:
        return self.stop if (self.kind == "stop_limit" and not self.triggered and self.stop) else self.price

    @property
    def is_limit(self) -> bool:
        return self.kind == "limit" or (self.kind == "stop_limit" and self.triggered)

    @property
    def cond(self) -> str:
        """'le' = terpicu saat harga ≤ trigger, 'ge' = saat harga ≥ trigger."""
        buy = self.side == "buy"
        return ("le" if buy else "ge") if self.is_limit else ("ge" if buy else "le")

    def public(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("reserved", None)
        return d


def _f(x: Any, what: str) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise TradeError(f"{what} tidak valid.") from None
    if not math.isfinite(v) or v <= 0:
        raise TradeError(f"{what} harus lebih dari 0.")
    return v


def _opt(x: Any, what: str) -> float | None:
    return None if x in (None, "", 0, "0") else _f(x, what)


class DerivAccount:
    def __init__(self, product: Product, capital: float, slippage: float, qty_step: float, min_notional: float,
                 symbol: str = "", unit_factor: float = 1.0, fee_buy: float | None = None,
                 fee_sell: float | None = None, maker: float | None = None, interest_apr: float | None = None,
                 borrow_apr: float | None = None, funding_schedule: FundingSchedule | None = None,
                 leverage: float | None = None):
        self.p = product
        self.capital = float(capital)
        self.slippage = slippage
        self.qty_step = qty_step
        self.min_notional = min_notional
        self.symbol = symbol
        self.unit_factor = unit_factor        # lembar asli per 1 unit di game (mode harga buta)
        self.fee_buy = product.fee_buy if fee_buy is None else fee_buy
        self.fee_sell = product.fee_sell if fee_sell is None else fee_sell
        self.maker = product.maker if maker is None else maker
        self.interest_apr = product.interest_apr if interest_apr is None else interest_apr
        self.borrow_apr = product.borrow_apr if borrow_apr is None else borrow_apr
        self.funding_schedule = funding_schedule
        self.lev = float(min(product.max_lev, max(1.0, leverage or product.default_lev)))
        self.mode = "cross"
        self.wallet = float(capital)
        self.qty = 0.0
        self.entry = 0.0
        self.iso = 0.0
        self.realized = 0.0
        self.fees_paid = 0.0
        self.funding_paid = 0.0
        self.interest_paid = 0.0
        self.borrow_paid = 0.0
        self.liq_loss = 0.0
        self.n_liq = 0
        self.last_funding: tuple[int, float] | None = None
        self.orders: dict[int, DOrder] = {}
        self.fills: list[Fill] = []
        self.trades: list[dict[str, Any]] = []
        self.cycle: dict[str, Any] | None = None
        self.peak = float(capital)
        self.max_dd = 0.0
        self.exposure_n = 0
        self.tracked_n = 0
        self.max_lev_used = 0.0
        self.curve: list[tuple[int, float]] = []
        self._last_t: int | None = None
        self._next_id = 1
        self._next_group = 1

    # ================================================================ dasar
    @property
    def kind(self) -> str:
        return self.p.kind

    def _id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    @property
    def sign(self) -> int:
        return 1 if self.qty > EPS else -1 if self.qty < -EPS else 0

    @property
    def size(self) -> float:
        return abs(self.qty)

    def short_ok(self) -> bool:
        return self.p.short_ok(self.symbol)

    def norm_qty(self, q: Any) -> float:
        try:
            q = float(q)
        except (TypeError, ValueError):
            raise TradeError("Jumlah tidak valid.") from None
        if not math.isfinite(q) or q <= 0:
            raise TradeError("Jumlah harus lebih dari 0.")
        n = math.floor(q / self.qty_step + 1e-7)
        q = round(n * self.qty_step, 10)
        if q <= 0:
            raise TradeError(f"Jumlah minimal {self.qty_step:g}.")
        return q

    def _floor(self, q: float) -> float:
        if q <= 0:
            return 0.0
        return round(math.floor(q / self.qty_step + 1e-9) * self.qty_step, 10)

    # ------------------------------------------------------------ fee
    def fee(self, side: str, q: float, price: float, maker: bool) -> float:
        notional = q * price
        if maker and self.maker is not None:
            rate = self.maker
        else:
            rate = self.fee_buy if side == "buy" else self.fee_sell
        f = rate * notional
        shares = q * self.unit_factor
        if self.p.per_share:
            per, lo, hi_pct = self.p.per_share
            f += min(max(lo, per * shares), hi_pct * notional)
        if side == "sell":
            f += self.p.sec_fee * notional
            if self.p.taf:
                f += min(self.p.taf[0] * shares, self.p.taf[1])
        return f

    def _fee_rate_est(self, side: str) -> float:
        r = self.fee_buy if side == "buy" else self.fee_sell
        if self.p.per_share:
            r += self.p.per_share[2] * 0.2  # perkiraan kasar, dicek ulang saat eksekusi
        if side == "sell":
            r += self.p.sec_fee
        return r

    # ------------------------------------------------------------ margin
    def tier(self, notional: float) -> tuple[float, float, float]:
        """(mmr, maintenance amount, leverage maks) untuk posisi senilai ``notional``."""
        if self.p.tiers:
            for t in self.p.tiers:
                if notional <= t.cap:
                    return t.mmr, t.cum, float(t.max_lev)
            t = self.p.tiers[-1]
            return t.mmr, t.cum, float(t.max_lev)
        mmr = self.p.mmr_long if self.qty >= 0 else self.p.mmr_short
        return mmr, 0.0, float(self.p.max_lev)

    def _mmr_for(self, sign: int, notional: float) -> tuple[float, float]:
        if self.p.tiers:
            mmr, cum, _ = self.tier(notional)
            return mmr, cum
        return (self.p.mmr_long if sign > 0 else self.p.mmr_short), 0.0

    def max_lev_for(self, notional: float) -> float:
        if self.p.tiers:
            return self.tier(notional)[2]
        return float(self.p.max_lev)

    def cap_for_lev(self, lev: float) -> float:
        """Nilai posisi terbesar yang boleh dipegang dengan leverage ``lev``."""
        if not self.p.tiers:
            return math.inf
        cap = 0.0
        for t in self.p.tiers:
            if t.max_lev >= lev - 1e-9:
                cap = t.cap
        return cap

    def upnl(self, price: float) -> float:
        return self.qty * (price - self.entry) if self.sign else 0.0

    def equity(self, price: float) -> float:
        return self.wallet + self.upnl(price)

    def maint(self, price: float) -> float:
        if not self.sign:
            return 0.0
        notional = self.size * price
        mmr, cum = self._mmr_for(self.sign, notional)
        return max(0.0, notional * mmr - cum)

    def position_margin(self, price: float) -> float:
        if not self.sign:
            return 0.0
        if self.mode == "isolated":
            return self.iso
        return self.size * price / self.lev

    def reserved(self) -> float:
        return sum(o.reserved for o in self.orders.values() if o.status == "open")

    def available(self, price: float) -> float:
        if self.mode == "isolated":
            return self.wallet - self.iso - self.reserved()
        return self.equity(price) - self.position_margin(price) - self.reserved()

    def margin_balance(self, price: float) -> float:
        """Jaminan yang menahan posisi: seluruh ekuitas (cross) atau margin posisi + uPnL (isolated)."""
        if self.mode == "isolated":
            return self.iso + self.upnl(price)
        return self.equity(price)

    def _solve_price(self, mmr_override: float | None = None) -> float | None:
        if not self.sign:
            return None
        q, e = self.size, self.entry
        base = self.iso if self.mode == "isolated" else self.wallet
        mmr, cum = self._mmr_for(self.sign, q * e)
        if mmr_override is not None:
            mmr, cum = mmr_override, 0.0
        price = None
        for _ in range(3):
            if self.sign > 0:
                den = q * (1 - mmr)
                price = (q * e - base - cum) / den if den > 0 else None
            else:
                price = (base + q * e + cum) / (q * (1 + mmr))
            if price is None or price <= 0 or mmr_override is not None:
                break
            mmr2, cum2 = self._mmr_for(self.sign, q * price)
            if (mmr2, cum2) == (mmr, cum):
                break
            mmr, cum = mmr2, cum2
        if price is None or price <= 0:
            return None
        return price

    def liq_price(self) -> float | None:
        return self._solve_price()

    def call_price(self) -> float | None:
        """Harga saat margin call (peringatan) untuk akun margin saham."""
        if self.kind != "margin" or not self.sign:
            return None
        lvl = self.p.call_long if self.sign > 0 else self.p.call_short
        return self._solve_price(lvl) if lvl else None

    # ------------------------------------------------------------ bagian buka/tutup
    def reducible(self, side: str) -> float:
        s = 1 if side == "buy" else -1
        return self.size if self.sign and self.sign != s else 0.0

    def _split(self, side: str, q: float) -> tuple[float, float]:
        red = min(q, self.reducible(side))
        return red, max(0.0, round(q - red, 10))

    def _check_short(self, side: str, q_open: float) -> None:
        if side != "sell" or q_open <= EPS:
            return
        if not self.short_ok():
            if not self.p.short:
                raise TradeError("Produk ini tidak bisa short.")
            lst = ", ".join(sorted(self.p.short_list or []))
            raise TradeError(f"Short tidak tersedia untuk saham ini. Di BEI short hanya untuk Daftar Efek Short Selling: {lst}.")

    def _need(self, side: str, q_open: float, price: float, maker: bool) -> float:
        return q_open * price / self.lev + self.fee(side, q_open, price, maker)

    def _check_open(self, side: str, q: float, price: float, maker: bool, mark: float | None = None) -> None:
        """Pastikan bagian yang membuka/menambah posisi punya margin cukup dan tidak melewati tier.

        ``price`` = harga eksekusi order, ``mark`` = harga pasar sekarang (untuk ekuitas & margin tersedia)."""
        mark = price if mark is None else mark
        red, q_open = self._split(side, q)
        if q_open <= EPS:
            return
        self._check_short(side, q_open)
        if side == "sell" and self.p.min_short_equity and self.equity(mark) < self.p.min_short_equity - 1e-6:
            raise TradeError(f"Short butuh jaminan awal minimal {self.p.min_short_equity:,.0f}.".replace(",", "."))
        same = self.size if (self.sign and self.sign == (1 if side == "buy" else -1)) else 0.0
        new_notional = (same + q_open) * price
        if new_notional > self.cap_for_lev(self.lev) + 1e-6:
            raise TradeError(f"Posisi sebesar itu melewati batas leverage {self.lev:g}×. Turunkan leverage atau jumlah.")
        avail = self.available(mark)
        if red > EPS:  # posisi lama ditutup dulu, margin & laba/ruginya ikut dilepas
            avail += self.position_margin(mark) + (self.upnl(mark) if self.mode == "isolated" else 0.0)
        if self._need(side, q_open, price, maker) > avail + 1e-6:
            raise TradeError("Margin tidak cukup (termasuk fee dan margin yang dipakai order lain).")

    def max_qty(self, side: str, price: float) -> float:
        """Jumlah terbesar yang bisa dipesan di sisi ini (market) – untuk tombol 25/50/75/100%."""
        red = self.reducible(side)
        if side == "sell" and not self.short_ok():
            return self._floor(red)
        avail = self.available(price)
        if red > EPS:
            avail += self.position_margin(price) + (self.upnl(price) if self.mode == "isolated" else 0.0)
        p = price * (1 + self.slippage if side == "buy" else 1)
        per = p * (1 / self.lev + self._fee_rate_est(side))
        q_open = max(0.0, avail) / per if per > 0 else 0.0
        same = self.size if (self.sign and self.sign == (1 if side == "buy" else -1)) else 0.0
        cap = self.cap_for_lev(self.lev)
        if math.isfinite(cap):
            q_open = min(q_open, max(0.0, cap / price - same))
        return self._floor(red + q_open)

    # ================================================================ perintah pemain
    def _bracket(self, side: str, sl: Any, tp: Any, ref: float) -> tuple[float | None, float | None]:
        sl_p, tp_p = _opt(sl, "Harga SL"), _opt(tp, "Harga TP")
        if side == "buy":
            if sl_p is not None and sl_p >= ref:
                raise TradeError("Stop loss posisi long harus di bawah harga masuk.")
            if tp_p is not None and tp_p <= ref:
                raise TradeError("Take profit posisi long harus di atas harga masuk.")
        else:
            if sl_p is not None and sl_p <= ref:
                raise TradeError("Stop loss posisi short harus di atas harga masuk.")
            if tp_p is not None and tp_p >= ref:
                raise TradeError("Take profit posisi short harus di bawah harga masuk.")
        return sl_p, tp_p

    def _uptick(self, side: str, q: float, kind: str, price: float | None, last: float) -> None:
        if not self.p.uptick or side != "sell":
            return
        _, q_open = self._split(side, q)
        if q_open <= EPS:
            return
        if kind != "limit" or price is None or price < last - 1e-9:
            raise TradeError("Aturan uptick BEI: short wajib order limit di harga ≥ harga terakhir.")

    def market(self, side: str, qty: Any, last: float, time: int, sl: Any = None, tp: Any = None,
               reduce_only: bool = False) -> Fill:
        if side not in ("buy", "sell"):
            raise TradeError("Sisi order tidak dikenal.")
        self._mark(time)
        q = self.norm_qty(qty)
        if reduce_only:
            q = self._floor(min(q, self.reducible(side)))
            if q <= 0:
                raise TradeError("Reduce-only: tidak ada posisi berlawanan yang bisa dikurangi.")
        self._uptick(side, q, "market", None, last)
        p = last * (1 + self.slippage) if side == "buy" else last * (1 - self.slippage)
        if q * p < self.min_notional - EPS:
            raise TradeError(f"Nilai transaksi minimal {self.min_notional:g}.")
        self._check_open(side, q, p, maker=False, mark=last)
        _, q_open = self._split(side, q)
        sl_p, tp_p = self._bracket(side, sl, tp, p) if q_open > EPS else (None, None)
        f = self._exec(side, q, p, time, None, "Market", maker=False)
        if (sl_p or tp_p) and self.sign:
            self.protect(None, sl_p, tp_p, time)
        return f

    def place(self, side: str, kind: str, price: Any, qty: Any, time: int, last: float, sl: Any = None,
              tp: Any = None, stop: Any = None, reduce_only: bool = False, post_only: bool = False,
              label: str = "") -> list[Fill]:
        """Pasang order limit / stop (market) / stop-limit. Limit yang langsung bisa terisi dieksekusi sekarang."""
        if side not in ("buy", "sell") or kind not in ("limit", "stop", "stop_limit"):
            raise TradeError("Jenis order tidak dikenal.")
        self._mark(time)
        p = _f(price, "Harga")
        q = self.norm_qty(qty)
        if len([o for o in self.orders.values() if o.status == "open"]) >= 50:
            raise TradeError("Maksimal 50 order aktif.")
        if p > last * 3 or p < last / 3:
            raise TradeError("Harga order terlalu jauh dari harga sekarang.")
        stop_p = None
        if kind == "stop_limit":
            stop_p = _f(stop, "Harga picu")
        trig = stop_p if kind == "stop_limit" else p
        if kind in ("stop", "stop_limit"):
            if side == "buy" and trig <= last:
                raise TradeError("Harga picu stop beli harus di atas harga sekarang.")
            if side == "sell" and trig >= last:
                raise TradeError("Harga picu stop jual harus di bawah harga sekarang.")
        if reduce_only and self.reducible(side) <= EPS:
            raise TradeError("Reduce-only: tidak ada posisi berlawanan yang bisa dikurangi.")
        self._uptick(side, q, kind, p, last)
        od = DOrder(self._id(), side, kind, p, q, time, stop=stop_p, label=label, reduce_only=reduce_only,
                    post_only=post_only and kind == "limit")
        marketable = kind == "limit" and ((side == "buy" and p >= last) or (side == "sell" and p <= last))
        if marketable and od.post_only:
            raise TradeError("Post-only ditolak: harga limit itu akan langsung terisi (jadi taker).")
        ref = p if kind != "stop" else p * (1 + self.slippage if side == "buy" else 1 - self.slippage)
        if q * ref < self.min_notional - EPS:
            raise TradeError(f"Nilai transaksi minimal {self.min_notional:g}.")
        if not reduce_only:
            _, q_open = self._split(side, q)
            if q_open > EPS:
                od.sl, od.tp = self._bracket(side, sl, tp, p)
                if od.sl or od.tp:
                    od.label = "Entry"
                self._check_open(side, q, ref, maker=not marketable, mark=last)
                od.reserved = self._need(side, q_open, ref, maker=(kind != "stop" and not marketable))
        if marketable:
            fill_px = min(p, last * (1 + self.slippage)) if side == "buy" else max(p, last * (1 - self.slippage))
            od.reserved = 0.0
            od.status = "filled"
            f = self._exec(side, q, fill_px, time, od, label or "Limit", maker=False)
            f.note = "langsung terisi (taker)"
            out = [f]
            if (od.sl or od.tp) and self.sign:
                self.protect(None, od.sl, od.tp, time)
            return out
        self.orders[od.id] = od
        return []

    def protect(self, qty: Any, sl: Any, tp: Any, time: int, last: float | None = None) -> list[DOrder]:
        """Pasang SL dan/atau TP (OCO, reduce-only) untuk posisi yang sedang dipegang."""
        if not self.sign:
            raise TradeError("Belum ada posisi untuk dilindungi.")
        side = "sell" if self.sign > 0 else "buy"
        q = self.size if qty in (None, "", 0) else min(self.norm_qty(qty), self.size)
        q = self._floor(q)
        locked, groups = 0.0, {}
        for o in self.orders.values():
            if o.status == "open" and o.reduce_only and o.side == side:
                if o.group is None:
                    locked += o.qty
                else:
                    groups[o.group] = max(groups.get(o.group, 0.0), o.qty)
        free = self.size - locked - sum(groups.values())
        if q > free + 1e-9:
            raise TradeError("Sebagian posisi sudah dilindungi SL/TP lain. Batalkan dulu yang lama.")
        sl_p, tp_p = _opt(sl, "Harga SL"), _opt(tp, "Harga TP")
        if sl_p is None and tp_p is None:
            raise TradeError("Isi harga SL atau TP.")
        if last is not None:
            if self.sign > 0:
                if sl_p is not None and sl_p >= last:
                    raise TradeError("Stop loss long harus di bawah harga sekarang.")
                if tp_p is not None and tp_p <= last:
                    raise TradeError("Take profit long harus di atas harga sekarang.")
            else:
                if sl_p is not None and sl_p <= last:
                    raise TradeError("Stop loss short harus di atas harga sekarang.")
                if tp_p is not None and tp_p >= last:
                    raise TradeError("Take profit short harus di bawah harga sekarang.")
        g = self._next_group
        self._next_group += 1
        made = []
        if sl_p is not None:
            made.append(DOrder(self._id(), side, "stop", sl_p, q, time, label="SL", group=g, reduce_only=True))
        if tp_p is not None:
            made.append(DOrder(self._id(), side, "limit", tp_p, q, time, label="TP", group=g, reduce_only=True))
        for o in made:
            self.orders[o.id] = o
        return made

    def cancel(self, order_id: Any) -> DOrder:
        try:
            od = self.orders[int(order_id)]
        except (KeyError, TypeError, ValueError):
            raise TradeError("Order tidak ditemukan.") from None
        if od.status != "open":
            raise TradeError("Order sudah tidak aktif.")
        od.status, od.reserved = "cancelled", 0.0
        return od

    def close(self, last: float, time: int, kind: str = "market", price: Any = None) -> list[Fill]:
        """Tutup seluruh posisi (reduce-only)."""
        if not self.sign:
            raise TradeError("Tidak ada posisi.")
        side = "sell" if self.sign > 0 else "buy"
        if kind == "limit":
            return self.place(side, "limit", price, self.size, time, last, reduce_only=True, label="Tutup")
        f = self.market(side, self.size, last, time, reduce_only=True)
        f.label = "Tutup"
        return [f]

    def set_leverage(self, lev: Any, price: float) -> None:
        try:
            v = float(lev)
        except (TypeError, ValueError):
            raise TradeError("Leverage tidak valid.") from None
        v = round(v)
        if not (1 <= v <= self.p.max_lev):
            raise TradeError(f"Leverage harus 1–{self.p.max_lev:g}×.")
        if self.sign and self.size * price > self.cap_for_lev(v) + 1e-6:
            raise TradeError(f"Posisimu terlalu besar untuk leverage {v:g}× (lihat tabel tier).")
        if self.sign and self.mode == "isolated":
            raise TradeError("Mode isolated: tutup posisi dulu sebelum mengganti leverage.")
        old = self.lev
        self.lev = float(v)
        self._rereserve(price)
        if self.sign and self.available(price) < -1e-6:
            self.lev = old
            self._rereserve(price)
            raise TradeError("Margin tidak cukup untuk menurunkan leverage sebesar itu.")

    def set_mode(self, mode: Any) -> None:
        mode = str(mode)
        if mode not in self.p.modes:
            raise TradeError("Mode margin tidak tersedia untuk produk ini.")
        if self.sign or any(o.status == "open" for o in self.orders.values()):
            raise TradeError("Ganti mode margin hanya bisa saat tidak ada posisi dan order aktif.")
        self.mode = mode

    def adjust_margin(self, amount: Any, price: float) -> None:
        """Tambah (+) atau kurangi (−) margin posisi isolated."""
        if self.mode != "isolated" or not self.sign:
            raise TradeError("Atur margin hanya untuk posisi isolated.")
        try:
            a = float(amount)
        except (TypeError, ValueError):
            raise TradeError("Jumlah tidak valid.") from None
        if not math.isfinite(a) or a == 0:
            raise TradeError("Jumlah tidak valid.")
        if a > 0:
            if a > self.available(price) + 1e-6:
                raise TradeError("Saldo tersedia tidak cukup.")
            self.iso += a
        else:
            need = max(self.size * price / self.lev, self.maint(price)) - self.upnl(price)
            if self.iso + a < need - 1e-6:
                raise TradeError("Margin yang tersisa harus tetap di atas initial margin posisi.")
            self.iso += a

    def _rereserve(self, price: float) -> None:
        for o in self.orders.values():
            if o.status == "open" and not o.reduce_only:
                _, q_open = self._split(o.side, o.qty)
                ref = o.price if o.kind != "stop" else o.price * (1 + self.slippage if o.side == "buy" else 1 - self.slippage)
                o.reserved = self._need(o.side, q_open, ref, maker=o.kind != "stop") if q_open > EPS else 0.0

    def handle(self, msg: dict[str, Any], last: float, now: int) -> list[Fill]:
        """Satu pesan dari pemain → daftar transaksi yang langsung terjadi."""
        t = msg.get("type")
        ro, po = bool(msg.get("reduce_only")), bool(msg.get("post_only"))
        if t == "order":
            kind = msg.get("kind", "market")
            if kind == "market":
                return [self.market(msg.get("side"), msg.get("qty"), last, now, msg.get("sl"), msg.get("tp"), ro)]
            return self.place(msg.get("side"), kind, msg.get("price"), msg.get("qty"), now, last,
                              msg.get("sl"), msg.get("tp"), msg.get("stop"), ro, po)
        if t == "protect":
            self.protect(msg.get("qty"), msg.get("sl"), msg.get("tp"), now, last)
        elif t == "cancel":
            self.cancel(msg.get("id"))
        elif t == "close":
            return self.close(last, now, str(msg.get("kind") or "market"), msg.get("price"))
        elif t == "leverage":
            self.set_leverage(msg.get("lev"), last)
        elif t == "margin_mode":
            self.set_mode(msg.get("mode"))
        elif t == "margin_adjust":
            self.adjust_margin(msg.get("amount"), last)
        else:
            raise TradeError("Perintah tidak dikenal.")
        return []

    def _mark(self, time: int) -> None:
        if self._last_t is None or time > self._last_t:
            self._last_t = int(time)

    # ================================================================ eksekusi
    def _exec(self, side: str, q: float, price: float, time: int, od: DOrder | None, label: str,
              maker: bool) -> Fill:
        s = 1 if side == "buy" else -1
        fee = self.fee(side, q, price, maker)
        self.wallet -= fee
        self.fees_paid += fee
        pnl_c: float | None = None
        red = min(q, self.size) if self.sign and self.sign != s else 0.0
        if red > EPS:
            pnl_c = red * (price - self.entry) * self.sign
            self.wallet += pnl_c
            self.realized += pnl_c
            if self.cycle is not None:
                self.cycle["fees"] += fee * red / q
                self.cycle["pnl"] += pnl_c
                self.cycle["exit_val"] += red * price
                self.cycle["exit_q"] += red
            left = round(self.size - red, 10)
            if self.mode == "isolated":
                self.iso = self.iso * (left / self.size) if self.size > EPS else 0.0
            if left <= EPS:
                self.qty, self.entry, self.iso = 0.0, 0.0, 0.0
                self._end_cycle(time, price)
            else:
                self.qty = left * self.sign
        rest = round(q - red, 10)
        if rest > EPS:
            if not self.sign:
                self.cycle = {"side": "long" if s > 0 else "short", "entry_time": time, "entry_price": price,
                              "lev": self.lev, "max_notional": 0.0, "fees": 0.0, "funding": 0.0, "interest": 0.0,
                              "pnl": 0.0, "exit_val": 0.0, "exit_q": 0.0, "n": 0}
            new = self.size + rest
            self.entry = (self.size * self.entry + rest * price) / new
            self.qty = new * s
            if self.mode == "isolated":
                self.iso += rest * price / self.lev
            if self.cycle is not None:
                self.cycle["fees"] += fee * rest / q
                self.cycle["max_notional"] = max(self.cycle["max_notional"], new * price)
                self.cycle["lev"] = self.lev
            eq = self.wallet
            if eq > 0:
                self.max_lev_used = max(self.max_lev_used, new * price / eq)
        if self.cycle is not None:
            self.cycle["n"] += 1
        f = Fill(self._id(), od.id if od else None, time, side, q, price, fee, label,
                 None if pnl_c is None else pnl_c - fee * (red / q))
        self.fills.append(f)
        return f

    def _end_cycle(self, time: int, price: float) -> None:
        c = self.cycle
        self.cycle = None
        for o in self.orders.values():  # SL/TP & reduce-only lain tidak berguna lagi
            if o.status == "open" and o.reduce_only:
                o.status, o.reserved = "cancelled", 0.0
        if c is None:
            return
        net = c["pnl"] - c["fees"] - c["funding"] - c["interest"]
        base = c["max_notional"] or 1.0
        margin0 = base / max(c["lev"], 1.0)
        self.trades.append({
            "side": c["side"], "entry_time": c["entry_time"], "exit_time": time, "entry_price": c["entry_price"],
            "exit_price": c["exit_val"] / c["exit_q"] if c["exit_q"] else price, "pnl": net,
            "pnl_pct": net / base * 100, "roe_pct": net / margin0 * 100, "lev": c["lev"], "fees": c["fees"],
            "funding": c["funding"], "interest": c["interest"], "max_qty": base / max(c["entry_price"], 1e-12),
            "n_fills": c["n"], "liquidated": bool(c.get("liq")), "notional": base,
        })

    def _fill_order(self, od: DOrder, px: float, time: int, maker: bool) -> Fill | None:
        """Isi order di harga ``px`` (sudah termasuk slippage untuk stop)."""
        od.status = "filled"
        if od.group is not None:
            for o in self.orders.values():
                if o.group == od.group and o.id != od.id and o.status == "open":
                    o.status, o.reserved = "cancelled", 0.0
        q = od.qty
        note = ""
        if od.reduce_only:
            q = self._floor(min(q, self.reducible(od.side)))
            if q <= EPS:
                od.status, od.reserved = "cancelled", 0.0
                return None
        else:
            od.reserved = 0.0  # margin order ini dilepas dulu, lalu dicek ulang di harga eksekusi
            try:
                self._check_open(od.side, q, px, maker)
            except TradeError:
                red, q_open = self._split(od.side, q)
                avail = max(0.0, self.available(px))
                if red > EPS:
                    avail += self.position_margin(px) + (self.upnl(px) if self.mode == "isolated" else 0.0)
                per = px * (1 / self.lev + self._fee_rate_est(od.side))
                cap = self.cap_for_lev(self.lev)
                q_fit = avail / per if per > 0 else 0.0
                if math.isfinite(cap):
                    same = self.size if self.sign == (1 if od.side == "buy" else -1) else 0.0
                    q_fit = min(q_fit, max(0.0, cap / px - same))
                if self.p.min_short_equity and od.side == "sell" and self.equity(px) < self.p.min_short_equity:
                    q_fit = 0.0
                q = self._floor(red + min(q_open, q_fit * 0.999))
                if q <= EPS or q * px < self.min_notional - EPS:
                    od.status = "cancelled"
                    return None
                note = "terisi sebagian karena margin kurang"
        label = od.label or {"limit": "Limit", "stop": "Stop", "stop_limit": "Stop-limit"}[od.kind]
        f = self._exec(od.side, q, px, time, od, label, maker)
        f.note = note
        if (od.sl or od.tp) and self.sign:
            try:
                self.protect(None, od.sl, od.tp, time)
            except TradeError:
                pass
        return f

    def _trigger(self, od: DOrder, at: float, time: int, gap: bool) -> Fill | None:
        """Order tersentuh di harga ``at`` (harga order, atau open kalau gap)."""
        if od.kind == "stop_limit" and not od.triggered:
            od.triggered = True
            lim = od.price
            if (od.side == "buy" and at <= lim) or (od.side == "sell" and at >= lim):
                return self._fill_order(od, at, time, maker=False)
            return None
        if od.is_limit:
            return self._fill_order(od, at, time, maker=True)
        px = at * (1 + self.slippage) if od.side == "buy" else at * (1 - self.slippage)
        return self._fill_order(od, px, time, maker=False)

    def _liquidate(self, at: float, time: int) -> Fill:
        side = "sell" if self.sign > 0 else "buy"
        q = self.size
        self.n_liq += 1
        if self.cycle is not None:
            self.cycle["liq"] = True
        for o in self.orders.values():
            if o.status == "open":
                o.status, o.reserved = "cancelled", 0.0
        if self.kind == "perp":
            iso_before = self.iso
            mm = self.maint(at)
            w0 = self.wallet
            f = self._exec(side, q, at, time, None, "Likuidasi", maker=False)
            if self.mode == "isolated":
                penalty = max(0.0, iso_before + (self.wallet - w0))
            else:
                penalty = min(max(0.0, self.wallet), mm)
            self.wallet -= penalty
            self.liq_loss += penalty
            if self.wallet < 0:
                self.liq_loss += self.wallet  # ditanggung dana asuransi
                self.wallet = 0.0
            if f.pnl is not None:
                f.pnl -= penalty
            f.note = "sisa margin masuk dana asuransi"
            if self.trades and penalty:
                t = self.trades[-1]
                t["pnl"] -= penalty
                t["pnl_pct"] = t["pnl"] / (t["notional"] or 1.0) * 100
                t["roe_pct"] = t["pnl"] / ((t["notional"] or 1.0) / max(t["lev"], 1.0)) * 100
            return f
        px = at * (1 - self.slippage) if side == "sell" else at * (1 + self.slippage)
        f = self._exec(side, q, px, time, None, "Forced sell" if side == "sell" else "Forced buy", maker=False)
        f.note = "jaminan di bawah batas, posisi ditutup paksa"
        return f

    def _hit_at(self, od: DOrder, price: float) -> bool:
        return (od.cond == "le" and price <= od.trigger) or (od.cond == "ge" and price >= od.trigger)

    def _liq_hit(self, price: float) -> bool:
        lp = self.liq_price()
        if lp is None:
            return False
        return price <= lp if self.sign > 0 else price >= lp

    def _candle(self, o: float, h: float, l: float, c: float, time: int) -> list[Fill]:
        out: list[Fill] = []

        def add(f: Fill | None) -> None:
            if f is not None:
                out.append(f)

        # 1) gap di harga open
        for _ in range(200):
            hit = [od for od in self._open() if self._hit_at(od, o)]
            if hit:
                hit.sort(key=lambda od: (0 if od.reduce_only else 1, od.id))
                add(self._trigger(hit[0], o, time, gap=True))
                continue
            if self._liq_hit(o):
                add(self._liquidate(o, time))
                continue
            break
        # 2) jalur harga di dalam candle
        path = [o, l, h, c] if c >= o else [o, h, l, c]
        for a, b in zip(path, path[1:]):
            cur = a
            for _ in range(400):
                lp = self.liq_price()
                if b < cur:
                    cands = [od for od in self._open() if od.cond == "le" and cur > od.trigger >= b]
                    pick = max(cands, key=lambda od: (od.trigger, od.reduce_only), default=None)
                    liq = lp if (self.sign > 0 and lp is not None and cur > lp >= b) else None
                    if liq is not None and (pick is None or liq > pick.trigger):
                        cur = liq
                        add(self._liquidate(liq, time))
                        continue
                elif b > cur:
                    cands = [od for od in self._open() if od.cond == "ge" and cur < od.trigger <= b]
                    pick = min(cands, key=lambda od: (od.trigger, not od.reduce_only), default=None)
                    liq = lp if (self.sign < 0 and lp is not None and cur < lp <= b) else None
                    if liq is not None and (pick is None or liq < pick.trigger):
                        cur = liq
                        add(self._liquidate(liq, time))
                        continue
                else:
                    pick = None
                if pick is None:
                    break
                cur = pick.trigger
                add(self._trigger(pick, pick.trigger, time, gap=False))
        return out

    def _open(self) -> list[DOrder]:
        return [od for od in self.orders.values() if od.status == "open"]

    # ------------------------------------------------------------ funding & bunga
    def _events(self, T: np.ndarray, t_prev: int) -> list[tuple[int, str, float, int]]:
        t_end = int(T[-1])
        ev: list[tuple[int, str, float, int]] = []
        if self.kind == "perp":
            sched = self.funding_schedule or default_schedule(self.p.funding, self.p.funding_hours)
            for ts, rate in sched(t_prev, t_end):
                ev.append((int(np.searchsorted(T, ts, side="left")), "funding", float(rate), int(ts)))
        else:
            d0, d1 = t_prev // 86_400 + 1, t_end // 86_400
            if d1 >= d0:
                days = np.arange(d0, d1 + 1, dtype=np.int64) * 86_400
                idx = np.searchsorted(T, days, side="left")
                ev += [(int(i), "day", 1.0, int(ts)) for i, ts in zip(idx, days)]
        ev.sort(key=lambda e: (e[0], e[3]))
        return ev

    def _apply_event(self, kind: str, val: float, price: float, ts: int) -> None:
        if not self.sign:
            return
        if kind == "funding":
            pay = self.qty * price * val
            self.wallet -= pay
            self.funding_paid += pay
            self.last_funding = (ts, val)
            if self.mode == "isolated":
                self.iso = max(0.0, self.iso - pay)
            if self.cycle is not None:
                self.cycle["funding"] += pay
            return
        # satu hari kalender untuk akun margin saham
        cost = 0.0
        if self.sign > 0:
            debt = max(0.0, -(self.wallet - self.qty * self.entry))
            cost = debt * self.interest_apr / self.p.day_count * val
            self.interest_paid += cost
        else:
            cost = self.size * price * self.borrow_apr / self.p.day_count * val
            self.borrow_paid += cost
        self.wallet -= cost
        if self.cycle is not None:
            self.cycle["interest"] += cost

    def _track(self, closes: np.ndarray) -> None:
        if len(closes) == 0:
            return
        self.tracked_n += len(closes)
        if not self.sign:
            eq = np.array([self.wallet])
        else:
            self.exposure_n += len(closes)
            eq = self.wallet + self.qty * (closes - self.entry)
        run = np.maximum.accumulate(np.concatenate([[self.peak], eq]))[1:]
        dd = (run - eq) / np.maximum(run, 1e-12)
        self.max_dd = max(self.max_dd, float(min(1.0, dd.max())))
        self.peak = float(run[-1])

    def process(self, O: np.ndarray, H: np.ndarray, L: np.ndarray, C: np.ndarray, T: np.ndarray) -> list[Fill]:
        """Jalankan order, funding/bunga, dan cek likuidasi melewati candle-candle dasar yang baru terbuka."""
        n = len(O)
        if n == 0:
            return []
        T = np.asarray(T, dtype=np.int64)
        t_prev = self._last_t if self._last_t is not None else int(T[0]) - 1
        events = self._events(T, t_prev)
        k = 0
        fills: list[Fill] = []
        i = 0
        while i < n:
            while k < len(events) and events[k][0] <= i:
                idx, kind, val, ts = events[k]
                if idx == i:
                    self._apply_event(kind, val, float(O[i]), ts)
                k += 1
            active = self._open()
            if not active and not self.sign:
                self._track(C[i:n])
                break
            j = events[k][0] if (k < len(events) and self.sign) else n
            j = min(j, n)
            stop = j
            for od in active:
                if od.cond == "le":
                    seg = L[i:stop] <= od.trigger
                else:
                    seg = H[i:stop] >= od.trigger
                if seg.size and seg.any():
                    stop = i + int(np.argmax(seg))
            lp = self.liq_price()
            if lp is not None:
                seg = (L[i:stop] <= lp) if self.sign > 0 else (H[i:stop] >= lp)
                if seg.size and seg.any():
                    stop = i + int(np.argmax(seg))
            self._track(C[i:stop])
            if stop >= j:
                i = j
                continue
            fills += self._candle(float(O[stop]), float(H[stop]), float(L[stop]), float(C[stop]), int(T[stop]))
            self._track(C[stop:stop + 1])
            i = stop + 1
        self._last_t = int(T[-1])
        return fills

    # ================================================================ laporan
    def snapshot(self, price: float) -> dict[str, Any]:
        eq = self.equity(price)
        notional = self.size * price
        mm = self.maint(price)
        mb = self.margin_balance(price)
        pm = self.position_margin(price)
        lp = self.liq_price()
        cp = self.call_price()
        warn = False
        if self.kind == "margin" and self.sign and cp is not None:
            warn = price <= cp if self.sign > 0 else price >= cp
        nxt = None
        if self.kind == "perp" and self._last_t is not None:
            sched = self.funding_schedule or default_schedule(self.p.funding, self.p.funding_hours)
            for ts, rate in sched(self._last_t, self._last_t + self.p.funding_hours * 3600):
                nxt = {"time": int(ts), "rate": float(rate)}
                break
        return {
            "product": self.p.id, "kind": self.kind, "mode": self.mode, "lev": self.lev,
            "cash": self.wallet - self.qty * self.entry, "wallet": self.wallet,
            "free_cash": self.available(price), "reserved_cash": self.reserved(),
            "qty": self.qty, "free_qty": self.size, "avg_cost": self.entry, "entry": self.entry,
            "side": "long" if self.sign > 0 else "short" if self.sign < 0 else None,
            "notional": notional, "equity": eq, "return_pct": (eq / self.capital - 1) * 100,
            "realized": self.realized, "unrealized": self.upnl(price),
            "roe_pct": (self.upnl(price) / (notional / self.lev) * 100) if self.sign and notional else None,
            "margin": pm, "maint": mm, "margin_balance": mb,
            "margin_ratio": (mm / mb * 100) if self.sign and mb > 0 else (100.0 if self.sign else 0.0),
            "liq_price": lp, "call_price": cp, "margin_call": warn,
            "max_lev": self.max_lev_for(max(notional, 1e-9)), "short_ok": self.short_ok(),
            "fees_paid": self.fees_paid, "funding_paid": self.funding_paid, "interest_paid": self.interest_paid,
            "borrow_paid": self.borrow_paid, "liq_loss": self.liq_loss, "n_liq": self.n_liq,
            "next_funding": nxt, "max_dd_pct": self.max_dd * 100,
            "max_buy": self.max_qty("buy", price), "max_sell": self.max_qty("sell", price),
            "orders": [o.public() for o in self.orders.values() if o.status == "open"],
            "n_trades": len(self.trades),
        }

    def summary(self, price: float, first_price: float) -> dict[str, Any]:
        eq = self.equity(price)
        pnls = [t["pnl"] for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        gp, gl = sum(wins), -sum(losses)
        pct = [t["pnl_pct"] for t in self.trades]
        return {
            "capital": self.capital, "equity": eq, "return_pct": (eq / self.capital - 1) * 100,
            "buy_hold_pct": (price / first_price - 1) * 100 if first_price else 0.0,
            "n_trades": len(self.trades), "n_fills": len(self.fills),
            "win_rate": len(wins) / len(pnls) * 100 if pnls else None,
            "profit_factor": (gp / gl if gl > 0 else None),
            "avg_win_pct": (sum(p for p in pct if p > 0) / len(wins)) if wins else None,
            "avg_loss_pct": (sum(p for p in pct if p <= 0) / len(losses)) if losses else None,
            "best_pct": max(pct) if pct else None, "worst_pct": min(pct) if pct else None,
            "max_dd_pct": self.max_dd * 100, "fees_paid": self.fees_paid, "realized": self.realized,
            "exposure_pct": self.exposure_n / self.tracked_n * 100 if self.tracked_n else 0.0,
            "open_qty": self.qty, "open_value": self.qty * price,
            "product": self.p.id, "kind": self.kind, "funding_paid": self.funding_paid,
            "interest_paid": self.interest_paid, "borrow_paid": self.borrow_paid, "liq_loss": self.liq_loss,
            "n_liq": self.n_liq, "n_long": sum(1 for t in self.trades if t["side"] == "long"),
            "n_short": sum(1 for t in self.trades if t["side"] == "short"), "max_lev_used": self.max_lev_used,
        }


def default_schedule(rate: float, hours: int) -> FundingSchedule:
    period = hours * 3600

    def sched(t0: int, t1: int) -> Iterable[tuple[int, float]]:
        k = t0 // period + 1
        while k * period <= t1:
            yield k * period, rate
            k += 1
    return sched
