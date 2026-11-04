"""Tampilan pasar untuk satu sesi replay.

Server memegang semua data; klien hanya menerima candle yang *sudah terbuka*. Candle
timeframe besar yang belum selesai dikirim sebagai candle "sedang terbentuk" yang dihitung
dari candle dasar yang sudah terbuka, jadi tidak ada informasi masa depan yang bocor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .markets import MARKETS, MarketSpec
from .store import CandleStore
from .timeframes import INTRADAY, MS, REC, aggregate, bucket, bucket_start, rank

FAKE_EPOCH_MS = 978_307_200_000  # 2001-01-01 (Senin) 00:00, dipakai untuk menyamarkan tanggal
WEEK = 7 * 86_400_000


class SessionError(Exception):
    pass


@dataclass
class Blind:
    nama: bool = True
    tanggal: bool = True
    harga: bool = True

    @classmethod
    def from_any(cls, v: Any) -> "Blind":
        if isinstance(v, bool):
            return cls(v, v, v)
        if isinstance(v, dict):
            return cls(bool(v.get("nama", True)), bool(v.get("tanggal", True)), bool(v.get("harga", True)))
        return cls()

    @property
    def any(self) -> bool:
        return self.nama or self.tanggal or self.harga


def price_decimals(p: float, market: str, scaled: bool) -> int:
    if market == "idx" and not scaled:
        return 0
    if market == "us" and not scaled:
        return 2
    if p >= 1000:
        return 2
    if p >= 10:
        return 3
    if p >= 1:
        return 4
    if p >= 0.01:
        return 6
    return 8


class MarketView:
    def __init__(self, store: CandleStore, key: str, base_tf: str, start_idx: int, end_idx: int,
                 blind: Blind, rng: np.random.Generator):
        info = store.asset(key)
        if not info:
            raise SessionError("Aset tidak ditemukan.")
        self.store, self.key, self.info = store, key, info
        self.market: str = info["market"]
        self.spec: MarketSpec = MARKETS[self.market]
        self.base_tf = base_tf
        self.base = store.series(key, base_tf)
        if not (1 <= start_idx < end_idx <= len(self.base)):
            raise SessionError("Rentang data tidak valid.")
        self.origin = self.spec.origin_ms
        self.tfs = [tf for tf in self.spec.tfs if rank(tf) >= rank(base_tf) and tf in info["series"]]
        self.start_idx, self.end_idx, self.cursor = start_idx, end_idx, start_idx
        self.blind = blind
        p0 = float(self.base["c"][start_idx - 1])
        if blind.harga:
            target = 10 ** rng.uniform(1.0, 3.0)
            self.k = target / p0
            self.kv = float(rng.uniform(0.3, 3.0)) / self.k
        else:
            self.k, self.kv = 1.0, 1.0
        start_lt = int(self.base["lt"][start_idx])
        # geser kelipatan 7 hari dari Senin ke Senin supaya hari & jam tetap sama
        monday = ((start_lt // 86_400_000 + 3) // 7 * 7 - 3) * 86_400_000
        self.shift = (FAKE_EPOCH_MS - monday) if blind.tanggal else 0
        self.decimals = price_decimals(p0 * self.k, self.market, blind.harga)
        self._agg: dict[str, dict[str, Any]] = {}
        self._hist_cut: dict[str, int] = {}

    # ------------------------------------------------------------ waktu & harga
    def disp_time(self, lt: int | np.ndarray) -> Any:
        return (np.asarray(lt, dtype=np.int64) + self.shift) // 1000

    @property
    def done(self) -> bool:
        return self.cursor >= self.end_idx

    def last_price(self) -> float:
        return float(self.base["c"][self.cursor - 1]) * self.k

    def first_price(self) -> float:
        return float(self.base["c"][self.start_idx - 1]) * self.k

    def now(self) -> int:
        return int(self.disp_time(int(self.base["lt"][self.cursor - 1])))

    def progress(self) -> float:
        return (self.cursor - self.start_idx) / max(1, self.end_idx - self.start_idx)

    # ------------------------------------------------------------ candle
    def _fmt(self, rows: np.ndarray) -> list[list[float]]:
        if len(rows) == 0:
            return []
        d = self.decimals + 2
        t = self.disp_time(rows["lt"]).astype(np.float64)
        cols = [t, np.round(rows["o"] * self.k, d), np.round(rows["h"] * self.k, d),
                np.round(rows["l"] * self.k, d), np.round(rows["c"] * self.k, d), np.round(rows["v"] * self.kv, 4)]
        return np.column_stack(cols).tolist()

    def _scan_bucket_start(self, tf: str, idx: int) -> int:
        """Indeks candle dasar pertama di bucket yang sama dengan ``base[idx]``."""
        lt = self.base["lt"]
        target = int(bucket(int(lt[idx]), tf, self.origin))
        start_lt = int(bucket_start(target, tf, self.origin))
        return int(np.searchsorted(lt, start_lt, side="left"))

    def _hist(self, tf: str) -> np.ndarray:
        native = self.store.series(self.key, tf)
        if tf not in self._hist_cut:
            b = bucket(int(self.base["lt"][self.start_idx]), tf, self.origin)
            self._hist_cut[tf] = int(np.searchsorted(native["lt"], int(bucket_start(b, tf, self.origin)), side="left"))
        return native[: self._hist_cut[tf]]

    def _ensure(self, tf: str) -> np.ndarray:
        c = self._agg.get(tf)
        if c is not None and c["upto"] == self.cursor:
            return c["arr"]
        if c is None:
            i0 = self._scan_bucket_start(tf, self.start_idx)
            arr = aggregate(self.base[i0:self.cursor], tf, self.origin)
        else:
            i0 = c["last_i"]
            tail = aggregate(self.base[i0:self.cursor], tf, self.origin)
            arr = np.concatenate([c["arr"][:-1], tail]) if len(c["arr"]) else tail
        if self.cursor > i0:
            b = bucket(self.base["lt"][i0:self.cursor], tf, self.origin)
            last_i = i0 + int(np.searchsorted(b, b[-1], side="left"))
        else:
            last_i = i0
        self._agg[tf] = {"arr": arr, "upto": self.cursor, "last_i": last_i}
        return arr

    def candles(self, tf: str, before: float | None = None, limit: int = 1500) -> tuple[list[list[float]], bool]:
        """Candle yang terlihat untuk ``tf`` (paling baru di akhir). ``before`` = waktu tampilan (detik)."""
        if tf not in self.tfs:
            raise SessionError("Timeframe tidak tersedia untuk sesi ini.")
        limit = max(10, min(int(limit), 5000))
        before_lt = None if before is None else int(before) * 1000 - self.shift
        if tf == self.base_tf:
            rows = self.base[: self.cursor]
            if before_lt is not None:
                rows = rows[: int(np.searchsorted(rows["lt"], before_lt, side="left"))]
            more = len(rows) > limit
            return self._fmt(np.asarray(rows[-limit:])), more
        agg = self._ensure(tf)
        hist = self._hist(tf)
        if before_lt is not None:
            agg = agg[agg["lt"] < before_lt]
            hist = hist[: int(np.searchsorted(hist["lt"], before_lt, side="left"))]
        if len(agg) >= limit:
            return self._fmt(agg[-limit:]), True
        need = limit - len(agg)
        h = np.asarray(hist[-need:]) if need < len(hist) else np.asarray(hist)
        return self._fmt(np.concatenate([h, agg]) if len(h) else agg), len(hist) > need

    def updates(self, tf: str, old_cursor: int) -> list[list[float]]:
        """Candle yang berubah/bertambah sejak ``old_cursor`` (untuk series.update di klien)."""
        if tf not in self.tfs or old_cursor == self.cursor:
            return []
        if tf == self.base_tf:
            return self._fmt(np.asarray(self.base[old_cursor:self.cursor]))
        agg = self._ensure(tf)
        if old_cursor <= self.start_idx:
            return self._fmt(agg)
        b = bucket(int(self.base["lt"][old_cursor - 1]), tf, self.origin)
        i = int(np.searchsorted(agg["lt"], int(bucket_start(b, tf, self.origin)), side="left"))
        return self._fmt(agg[i:])

    # ------------------------------------------------------------ maju
    def next_cursor(self, tf: str, n: int = 1) -> int:
        cur = self.cursor
        lt = self.base["lt"]
        for _ in range(max(1, n)):
            if cur >= self.end_idx:
                break
            if tf == self.base_tf:
                cur += 1
                continue
            b = int(bucket(int(lt[cur]), tf, self.origin))
            nxt_lt = int(bucket_start(b + 1, tf, self.origin))
            cur = min(self.end_idx, max(cur + 1, int(np.searchsorted(lt, nxt_lt, side="left"))))
        return cur

    def advance(self, tf: str, n: int = 1) -> tuple[int, int]:
        old = self.cursor
        self.cursor = self.next_cursor(tf, n)
        return old, self.cursor

    def slice_for_engine(self, a: int, b: int) -> tuple[np.ndarray, ...]:
        rows = np.asarray(self.base[a:b])
        k = self.k
        return rows["o"] * k, rows["h"] * k, rows["l"] * k, rows["c"] * k, self.disp_time(rows["lt"])

    # ------------------------------------------------------------ info
    def label(self) -> str:
        if self.blind.nama:
            return "Aset rahasia"
        return f"{self.info['symbol']} · {self.info['name']}"

    def reveal(self) -> dict[str, Any]:
        import datetime as dt

        def iso(i: int) -> str:
            return dt.datetime.fromtimestamp(int(self.base["lt"][i]) / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")

        return {
            "symbol": self.info["symbol"], "name": self.info["name"], "market": self.spec.nama,
            "mulai": iso(self.start_idx), "selesai": iso(max(self.start_idx, self.cursor - 1)),
            "zona": {"crypto": "UTC", "idx": "WIB", "us": "waktu New York", "demo": "-"}[self.market],
            "faktor_harga": self.k, "harga_awal_asli": float(self.base["c"][self.start_idx - 1]),
            "harga_akhir_asli": float(self.base["c"][self.cursor - 1]),
        }


# ---------------------------------------------------------------- memilih titik awal
def _segment_for(info: dict[str, Any], tf: str, t: int) -> tuple[int, int] | None:
    for a, b in info["series"].get(tf, {}).get("segments", []):
        if a <= t <= b:
            return a, b
    return None


def pick_base(store: CandleStore, key: str, chart_tf: str, start_t: int, need_ms: int) -> str:
    """Timeframe dasar terkecil yang datanya ada di sekitar titik awal."""
    info = store.asset(key)
    m = info["market"]
    if m in ("crypto", "demo"):
        return "1m"
    for tf in ("1m", "5m", "15m", "30m", "1h", "1d"):
        if rank(tf) > rank(chart_tf) or tf not in info["series"] or not info["series"][tf].get("native"):
            continue
        seg = _segment_for(info, tf, start_t)
        if seg and seg[0] <= start_t - (0 if tf == "1d" else MS[tf]) and seg[1] >= min(start_t + need_ms, info["series"][tf]["t1"]):
            return tf
    return "1d" if rank(chart_tf) >= rank("1d") else chart_tf


def build_view(store: CandleStore, key: str, chart_tf: str, rng: np.random.Generator, blind: Blind,
               start: float | None = None, steps: int | None = None, min_history: int = 200) -> MarketView:
    """Pilih titik awal (acak kalau ``start`` kosong) dan buat ``MarketView``.

    ``steps`` = jumlah candle ``chart_tf`` yang boleh dimainkan (None = sampai data habis).
    """
    info = store.asset(key)
    if not info:
        raise SessionError("Aset tidak ditemukan.")
    spec = MARKETS[info["market"]]
    if chart_tf not in spec.tfs or chart_tf not in info["series"]:
        raise SessionError("Timeframe ini tidak tersedia untuk aset tersebut.")
    chart = store.series(key, chart_tf)
    future = steps if steps else max(5, min(60, len(chart) // 5))
    lo = min(min_history, max(1, len(chart) // 4))
    hi = len(chart) - future - 1
    if hi <= lo:
        raise SessionError("Data aset ini terlalu sedikit untuk timeframe itu. Pilih timeframe lain atau unduh data lebih banyak.")
    if start is None:
        idx = int(rng.integers(lo, hi))
    else:
        idx = int(np.searchsorted(chart["t"], int(start) * 1000, side="left"))
        idx = min(max(idx, 1), hi)
    start_t = int(chart["t"][idx])
    approx_ms = MS[chart_tf] * future * (3 if chart_tf in INTRADAY else 1)
    base_tf = pick_base(store, key, chart_tf, start_t, approx_ms)
    base = store.series(key, base_tf)
    start_idx = int(np.searchsorted(base["t"], start_t, side="left"))
    start_idx = max(1, min(start_idx, len(base) - 2))
    # batas akhir: ujung segmen data dasar
    seg = _segment_for(info, base_tf, int(base["t"][start_idx])) if info["market"] not in ("crypto", "demo") else None
    end_idx = len(base) if seg is None else int(np.searchsorted(base["t"], seg[1], side="right"))
    view = MarketView(store, key, base_tf, start_idx, end_idx, blind, rng)
    if steps:
        view.end_idx = view.next_cursor(chart_tf, steps)
        if view.end_idx <= view.start_idx:
            raise SessionError("Data ke depan tidak cukup.")
    return view


def eligible_assets(store: CandleStore, market: str | None, chart_tf: str, need: int) -> list[str]:
    out = []
    for key, a in store.assets().items():
        if market and a["market"] != market:
            continue
        s = a["series"].get(chart_tf)
        if s and s["n"] >= need and chart_tf in MARKETS[a["market"]].tfs:
            out.append(key)
    return sorted(out)


def tf_ms(tf: str) -> int:
    return MS[tf]


__all__ = ["MarketView", "Blind", "SessionError", "build_view", "eligible_assets", "REC", "math"]
