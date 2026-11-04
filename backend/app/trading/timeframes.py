"""Timeframe, format record candle, dan agregasi.

Semua logika "candle mana yang sudah selesai" memakai *bucket* yang dihitung dari
waktu lokal bursa (``lt``), bukan dari jam UTC. Dengan begitu candle harian saham IDX
mengikuti tanggal Jakarta, dan candle 1 jam saham US mulai pukul 09:30 New York.
"""

from __future__ import annotations

import numpy as np

#: Satu candle: waktu buka UTC (ms), waktu buka lokal bursa (ms, "jam dinding" sebagai epoch), OHLCV.
REC = np.dtype([("t", "<i8"), ("lt", "<i8"), ("o", "<f8"), ("h", "<f8"), ("l", "<f8"), ("c", "<f8"), ("v", "<f8")])

MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000, "12h": 43_200_000,
    "1d": 86_400_000, "1w": 604_800_000, "1M": 2_592_000_000,  # 1M hanya perkiraan (30 hari)
}
ORDER = list(MS.keys())
INTRADAY = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h"}
LABEL = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1J", "2h": "2J", "4h": "4J",
    "6h": "6J", "12h": "12J", "1d": "1H", "1w": "1Mg", "1M": "1B",
}
DAY = 86_400_000


def rank(tf: str) -> int:
    return ORDER.index(tf)


def bucket(lt: np.ndarray | int, tf: str, origin: int = 0) -> np.ndarray:
    """Nomor bucket tiap candle untuk timeframe ``tf`` (berdasarkan waktu lokal)."""
    lt = np.asarray(lt, dtype=np.int64)
    if tf in INTRADAY:
        return (lt - origin) // MS[tf]
    day = lt // DAY
    if tf == "1d":
        return day
    if tf == "1w":
        return (day + 3) // 7  # minggu mulai Senin (1970-01-05 = hari ke-4)
    if tf == "1M":
        return day.astype("datetime64[D]").astype("datetime64[M]").astype(np.int64)
    raise ValueError(tf)


def bucket_start(b: np.ndarray | int, tf: str, origin: int = 0) -> np.ndarray:
    """Waktu lokal (ms) awal bucket."""
    b = np.asarray(b, dtype=np.int64)
    if tf in INTRADAY:
        return b * MS[tf] + origin
    if tf == "1d":
        return b * DAY
    if tf == "1w":
        return (b * 7 - 3) * DAY
    if tf == "1M":
        return b.astype("datetime64[M]").astype("datetime64[D]").astype(np.int64) * DAY
    raise ValueError(tf)


def aggregate(rec: np.ndarray, tf: str, origin: int = 0) -> np.ndarray:
    """Gabungkan candle kecil menjadi candle ``tf``. ``rec`` harus urut waktu."""
    n = len(rec)
    if n == 0:
        return np.empty(0, REC)
    lt = np.asarray(rec["lt"])
    b = bucket(lt, tf, origin)
    change = np.flatnonzero(np.diff(b)) + 1
    starts = np.concatenate([[0], change]).astype(np.int64)
    ends = np.concatenate([change - 1, [n - 1]]).astype(np.int64)
    out = np.empty(len(starts), REC)
    out["lt"] = bucket_start(b[starts], tf, origin)
    out["t"] = out["lt"] - (lt[starts] - np.asarray(rec["t"])[starts])
    out["o"] = np.asarray(rec["o"])[starts]
    out["h"] = np.maximum.reduceat(np.asarray(rec["h"]), starts)
    out["l"] = np.minimum.reduceat(np.asarray(rec["l"]), starts)
    out["c"] = np.asarray(rec["c"])[ends]
    out["v"] = np.add.reduceat(np.asarray(rec["v"]), starts)
    return out


def dedupe_sorted(rec: np.ndarray) -> np.ndarray:
    """Urutkan berdasarkan waktu dan buang duplikat (yang terakhir menang)."""
    if len(rec) == 0:
        return rec
    order = np.argsort(rec["t"], kind="stable")
    rec = rec[order]
    # simpan kemunculan terakhir untuk setiap t
    rev = rec[::-1]
    _, idx = np.unique(rev["t"], return_index=True)
    return rev[idx]
