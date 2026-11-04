"""Akun trading spot: saldo, order, eksekusi per candle, fee, dan statistik.

Aturan eksekusi (didokumentasikan juga di panduan dalam game):

* Order **market** terisi langsung di harga terakhir (close candle terakhir) ± slippage.
* Order yang menunggu diperiksa di setiap candle *dasar* (timeframe terkecil sesi itu).
  Urutan harga di dalam satu candle diasumsikan: candle naik O → L → H → C,
  candle turun O → H → L → C.
* Kalau harga **membuka melewati** harga order (gap), order terisi di harga open.
* **Limit** terisi tepat di harganya. **Stop** (stop loss / stop buy) berubah jadi order market
  saat tersentuh, jadi kena slippage.
* SL/TP yang dipasang bersama order beli aktif setelah order beli terisi, sebagai pasangan OCO:
  kalau salah satu terisi, yang lain otomatis batal.
* Spot: tidak bisa jual melebihi aset yang dimiliki dan tidak bisa beli melebihi saldo.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

EPS = 1e-9


class TradeError(Exception):
    """Order ditolak. Pesannya ditampilkan ke pemain."""


@dataclass
class Order:
    id: int
    side: str                 # buy | sell
    kind: str                 # limit | stop
    price: float
    qty: float
    created: int              # waktu tampilan (detik)
    label: str = ""           # Entry | SL | TP | ""
    group: int | None = None  # pasangan OCO
    sl: float | None = None   # bracket untuk order beli
    tp: float | None = None
    reserved_cash: float = 0.0
    status: str = "open"      # open | filled | cancelled

    @property
    def cond(self) -> str:
        """'le' = terpicu saat harga turun ke ≤ price, 'ge' = saat naik ke ≥ price."""
        return "le" if (self.side == "buy") == (self.kind == "limit") else "ge"

    def public(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("reserved_cash", None)
        return d


@dataclass
class Fill:
    id: int
    order_id: int | None
    time: int
    side: str
    qty: float
    price: float
    fee: float
    label: str
    pnl: float | None = None   # laba/rugi terealisasi (untuk jual)
    note: str = ""


@dataclass
class Account:
    capital: float
    fee_buy: float
    fee_sell: float
    slippage: float
    qty_step: float
    min_notional: float
    cash: float = 0.0
    qty: float = 0.0
    avg_cost: float = 0.0        # per unit, termasuk fee beli
    realized: float = 0.0
    fees_paid: float = 0.0
    orders: dict[int, Order] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    cycle: dict[str, Any] | None = None
    peak: float = 0.0
    max_dd: float = 0.0
    exposure_n: int = 0
    tracked_n: int = 0
    curve: list[tuple[int, float]] = field(default_factory=list)
    _next_id: int = 1
    _next_group: int = 1

    def __post_init__(self) -> None:
        self.cash = float(self.capital)
        self.peak = float(self.capital)

    # ------------------------------------------------------------ util
    def _id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    def norm_qty(self, q: Any) -> float:
        try:
            q = float(q)
        except (TypeError, ValueError):
            raise TradeError("Jumlah tidak valid.") from None
        if not math.isfinite(q) or q <= 0:
            raise TradeError("Jumlah harus lebih dari 0.")
        step = self.qty_step
        n = math.floor(q / step + 1e-7)
        q = round(n * step, 10)
        if q <= 0:
            raise TradeError(f"Jumlah minimal {step:g}.")
        return q

    @staticmethod
    def _price(p: Any, what: str = "Harga") -> float:
        try:
            p = float(p)
        except (TypeError, ValueError):
            raise TradeError(f"{what} tidak valid.") from None
        if not math.isfinite(p) or p <= 0:
            raise TradeError(f"{what} harus lebih dari 0.")
        return p

    @property
    def reserved_cash(self) -> float:
        return sum(o.reserved_cash for o in self.orders.values() if o.status == "open" and o.side == "buy")

    @property
    def reserved_qty(self) -> float:
        total, groups = 0.0, {}
        for o in self.orders.values():
            if o.status != "open" or o.side != "sell":
                continue
            if o.group is None:
                total += o.qty
            else:
                groups[o.group] = max(groups.get(o.group, 0.0), o.qty)
        return total + sum(groups.values())

    def free_cash(self) -> float:
        return self.cash - self.reserved_cash

    def free_qty(self) -> float:
        return self.qty - self.reserved_qty

    def max_buy_qty(self, price: float) -> float:
        p = price * (1 + self.slippage) * (1 + self.fee_buy)
        if p <= 0:
            return 0.0
        n = math.floor(max(self.free_cash(), 0) / p / self.qty_step + 1e-9)
        return round(n * self.qty_step, 10)

    # ------------------------------------------------------------ order dari pemain
    def market(self, side: str, qty: Any, last: float, time: int, sl: Any = None, tp: Any = None) -> Fill:
        q = self.norm_qty(qty)
        if side == "buy":
            p = last * (1 + self.slippage)
            sl_p, tp_p = self._bracket(sl, tp, p)
            cost = p * q
            if cost < self.min_notional - EPS:
                raise TradeError(f"Nilai transaksi minimal {self.min_notional:g}.")
            if cost * (1 + self.fee_buy) > self.free_cash() + 1e-6:
                raise TradeError("Saldo tidak cukup (termasuk fee dan dana yang sedang dipakai order lain).")
            f = self._do_buy(q, p, time, None, "Market")
            if sl_p or tp_p:
                self.protect(f.qty, sl_p, tp_p, time)
            return f
        if side == "sell":
            if q > self.free_qty() + 1e-9:
                raise TradeError("Aset yang bisa dijual tidak cukup (sebagian mungkin terkunci di order SL/TP).")
            p = last * (1 - self.slippage)
            return self._do_sell(q, p, time, None, "Market")
        raise TradeError("Sisi order tidak dikenal.")

    def _bracket(self, sl: Any, tp: Any, ref: float) -> tuple[float | None, float | None]:
        sl_p = self._price(sl, "Harga SL") if sl not in (None, "", 0) else None
        tp_p = self._price(tp, "Harga TP") if tp not in (None, "", 0) else None
        if sl_p is not None and sl_p >= ref:
            raise TradeError("Stop loss harus di bawah harga beli.")
        if tp_p is not None and tp_p <= ref:
            raise TradeError("Take profit harus di atas harga beli.")
        return sl_p, tp_p

    def place(self, side: str, kind: str, price: Any, qty: Any, time: int, last: float,
              sl: Any = None, tp: Any = None) -> Order:
        if kind not in ("limit", "stop") or side not in ("buy", "sell"):
            raise TradeError("Jenis order tidak dikenal.")
        p = self._price(price)
        q = self.norm_qty(qty)
        if len([o for o in self.orders.values() if o.status == "open"]) >= 50:
            raise TradeError("Maksimal 50 order aktif.")
        od = Order(self._id(), side, kind, p, q, time)
        if side == "buy":
            if kind == "limit" and p > last * 1.5:
                raise TradeError("Harga limit beli terlalu jauh di atas harga sekarang.")
            if kind == "stop" and p < last:
                raise TradeError("Stop buy harus di atas harga sekarang (dipakai untuk beli saat breakout).")
            if p * q < self.min_notional - EPS:
                raise TradeError(f"Nilai transaksi minimal {self.min_notional:g}.")
            od.sl, od.tp = self._bracket(sl, tp, p)
            per = p * (1 + (self.slippage if kind == "stop" else 0)) * (1 + self.fee_buy)
            od.reserved_cash = per * q
            if od.reserved_cash > self.free_cash() + 1e-6:
                raise TradeError("Saldo tidak cukup untuk order ini (termasuk fee).")
            od.label = "Entry" if (od.sl or od.tp) else ""
        else:
            if q > self.free_qty() + 1e-9:
                raise TradeError("Aset yang bisa dijual tidak cukup.")
            if kind == "stop" and p >= last:
                raise TradeError("Stop loss jual harus di bawah harga sekarang.")
            if kind == "limit" and p < last * 0.5:
                raise TradeError("Harga limit jual terlalu jauh di bawah harga sekarang.")
            od.label = "SL" if kind == "stop" else "TP"
        self.orders[od.id] = od
        return od

    def protect(self, qty: Any, sl: Any, tp: Any, time: int, last: float | None = None) -> list[Order]:
        """Pasang SL dan/atau TP (OCO) untuk aset yang sudah dimiliki."""
        q = self.norm_qty(qty)
        if q > self.free_qty() + 1e-9:
            raise TradeError("Aset yang bisa dilindungi tidak cukup.")
        sl_p = self._price(sl, "Harga SL") if sl not in (None, "", 0) else None
        tp_p = self._price(tp, "Harga TP") if tp not in (None, "", 0) else None
        if sl_p is None and tp_p is None:
            raise TradeError("Isi harga SL atau TP.")
        if last is not None:
            if sl_p is not None and sl_p >= last:
                raise TradeError("Stop loss harus di bawah harga sekarang.")
            if tp_p is not None and tp_p <= last:
                raise TradeError("Take profit harus di atas harga sekarang.")
        g = self._next_group
        self._next_group += 1
        made = []
        if sl_p is not None:
            made.append(Order(self._id(), "sell", "stop", sl_p, q, time, "SL", g))
        if tp_p is not None:
            made.append(Order(self._id(), "sell", "limit", tp_p, q, time, "TP", g))
        for o in made:
            self.orders[o.id] = o
        return made

    def cancel(self, order_id: Any) -> Order:
        try:
            od = self.orders[int(order_id)]
        except (KeyError, TypeError, ValueError):
            raise TradeError("Order tidak ditemukan.") from None
        if od.status != "open":
            raise TradeError("Order sudah tidak aktif.")
        od.status = "cancelled"
        od.reserved_cash = 0.0
        return od

    # ------------------------------------------------------------ pengisian
    def _do_buy(self, q: float, p: float, time: int, od: Order | None, label: str) -> Fill:
        cost = p * q
        fee = cost * self.fee_buy
        self.cash -= cost + fee
        self.fees_paid += fee
        if self.qty <= EPS:
            self.cycle = {"entry_time": time, "cost": 0.0, "proceeds": 0.0, "fees": 0.0, "max_qty": 0.0,
                          "n_buy": 0, "n_sell": 0, "entry_price": p}
        self.avg_cost = (self.avg_cost * self.qty + cost + fee) / (self.qty + q)
        self.qty = round(self.qty + q, 10)
        c = self.cycle
        c["cost"] += cost + fee
        c["fees"] += fee
        c["n_buy"] += 1
        c["max_qty"] = max(c["max_qty"], self.qty)
        f = Fill(self._id(), od.id if od else None, time, "buy", q, p, fee, label)
        self.fills.append(f)
        return f

    def _do_sell(self, q: float, p: float, time: int, od: Order | None, label: str) -> Fill:
        q = min(q, self.qty)
        gross = p * q
        fee = gross * self.fee_sell
        self.cash += gross - fee
        self.fees_paid += fee
        pnl = gross - fee - self.avg_cost * q
        self.realized += pnl
        self.qty = round(self.qty - q, 10)
        c = self.cycle
        f = Fill(self._id(), od.id if od else None, time, "sell", q, p, fee, label, pnl)
        self.fills.append(f)
        if c is not None:
            c["proceeds"] += gross - fee
            c["fees"] += fee
            c["n_sell"] += 1
        if self.qty <= EPS:
            self.qty = 0.0
            self.avg_cost = 0.0
            if c is not None:
                pnl_t = c["proceeds"] - c["cost"]
                self.trades.append({
                    "entry_time": c["entry_time"], "exit_time": time, "entry_price": c["entry_price"],
                    "exit_price": p, "pnl": pnl_t, "pnl_pct": pnl_t / c["cost"] * 100 if c["cost"] else 0.0,
                    "fees": c["fees"], "max_qty": c["max_qty"], "n_buy": c["n_buy"], "n_sell": c["n_sell"],
                })
            self.cycle = None
            # semua order jual sisa jadi tidak berguna
            for o in self.orders.values():
                if o.status == "open" and o.side == "sell":
                    o.status = "cancelled"
        return f

    def _fill_order(self, od: Order, price: float, time: int) -> Fill | None:
        if od.side == "buy":
            q = od.qty
            available = self.free_cash() + od.reserved_cash
            if price * q * (1 + self.fee_buy) > available + 1e-6:
                n = math.floor(available / (price * (1 + self.fee_buy)) / self.qty_step + 1e-9)
                q = round(n * self.qty_step, 10)
                if q <= 0 or price * q < self.min_notional - EPS:
                    od.status = "cancelled"
                    od.reserved_cash = 0.0
                    return None
            od.reserved_cash = 0.0
            od.status = "filled"
            f = self._do_buy(q, price, time, od, od.label or ("Limit" if od.kind == "limit" else "Stop"))
            if q < od.qty:
                f.note = "terisi sebagian karena saldo kurang"
            if od.sl or od.tp:
                self.protect(q, od.sl, od.tp, time)
            return f
        od.status = "filled"
        if od.group is not None:
            for o in self.orders.values():
                if o.group == od.group and o.id != od.id and o.status == "open":
                    o.status = "cancelled"
        q = min(od.qty, self.qty)
        if q <= EPS:
            return None
        return self._do_sell(q, price, time, od, od.label or ("Limit" if od.kind == "limit" else "Stop"))

    def _exec_price(self, od: Order, trigger: float) -> float:
        if od.kind == "limit":
            return trigger
        return trigger * (1 + self.slippage) if od.side == "buy" else trigger * (1 - self.slippage)

    def _candle(self, o: float, h: float, l: float, c: float, time: int) -> list[Fill]:
        out: list[Fill] = []
        # 1) gap di harga open
        while True:
            hit = [od for od in self._open()
                   if (od.cond == "le" and o <= od.price) or (od.cond == "ge" and o >= od.price)]
            if not hit:
                break
            hit.sort(key=lambda od: 0 if od.side == "sell" else 1)
            od = hit[0]
            f = self._fill_order(od, self._exec_price(od, o), time)
            if f:
                out.append(f)
        # 2) jalur harga di dalam candle
        path = [o, l, h, c] if c >= o else [o, h, l, c]
        for a, b in zip(path, path[1:]):
            cur = a
            while True:
                if b < cur:
                    cands = [od for od in self._open() if od.cond == "le" and cur > od.price >= b]
                    pick = max(cands, key=lambda od: (od.price, od.side == "sell"), default=None)
                elif b > cur:
                    cands = [od for od in self._open() if od.cond == "ge" and cur < od.price <= b]
                    pick = min(cands, key=lambda od: (od.price, od.side != "sell"), default=None)
                else:
                    pick = None
                if pick is None:
                    break
                cur = pick.price
                f = self._fill_order(pick, self._exec_price(pick, pick.price), time)
                if f:
                    out.append(f)
        return out

    def _open(self) -> list[Order]:
        return [od for od in self.orders.values() if od.status == "open"]

    def _track(self, closes: np.ndarray) -> None:
        if len(closes) == 0:
            return
        self.tracked_n += len(closes)
        if self.qty <= EPS:
            eq = np.array([self.cash])
        else:
            self.exposure_n += len(closes)
            eq = self.cash + self.qty * closes
        run = np.maximum.accumulate(np.concatenate([[self.peak], eq]))[1:]
        dd = (run - eq) / np.maximum(run, 1e-12)
        self.max_dd = max(self.max_dd, float(dd.max()))
        self.peak = float(run[-1])

    def process(self, O: np.ndarray, H: np.ndarray, L: np.ndarray, C: np.ndarray, T: np.ndarray) -> list[Fill]:
        """Jalankan semua order aktif melewati candle-candle dasar yang baru terbuka."""
        n = len(O)
        fills: list[Fill] = []
        i = 0
        while i < n:
            active = self._open()
            if not active:
                break
            j = n
            for od in active:
                seg = L[i:j] <= od.price if od.cond == "le" else H[i:j] >= od.price
                k = int(np.argmax(seg)) if seg.size and seg.any() else -1
                if k >= 0:
                    j = i + k
            if j >= n:
                break
            self._track(C[i:j])
            fills += self._candle(float(O[j]), float(H[j]), float(L[j]), float(C[j]), int(T[j]))
            self._track(C[j:j + 1])
            i = j + 1
        self._track(C[i:n])
        return fills

    # ------------------------------------------------------------ laporan
    def equity(self, price: float) -> float:
        return self.cash + self.qty * price

    def snapshot(self, price: float) -> dict[str, Any]:
        eq = self.equity(price)
        return {
            "cash": self.cash, "free_cash": self.free_cash(), "reserved_cash": self.reserved_cash,
            "qty": self.qty, "free_qty": self.free_qty(), "avg_cost": self.avg_cost,
            "equity": eq, "return_pct": (eq / self.capital - 1) * 100,
            "realized": self.realized, "unrealized": self.qty * (price - self.avg_cost) if self.qty > EPS else 0.0,
            "fees_paid": self.fees_paid, "max_dd_pct": self.max_dd * 100,
            "max_buy": self.max_buy_qty(price),
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
        }
