"""Data uji sintetis untuk Kilas Pasar."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.trading.demo import make_series
from app.trading.markets import MARKETS
from app.trading.store import derive, series_path, update_catalog_asset, write_series
from app.trading.timeframes import REC

JKT = 7 * 3_600_000
DAY = 86_400_000
T0 = 1_704_067_200_000  # 2024-01-01 00:00 UTC (Senin)


def make_crypto(root: Path, symbol: str = "TESTUSDT", days: int = 40, seed: int = 1) -> None:
    rec = make_series(100.0, days * 1440, seed=seed, start_ms=T0)
    write_series(series_path(root, "crypto", symbol, "1m"), rec)
    derive(root, "crypto", symbol, "1m", list(MARKETS["crypto"].tfs))
    update_catalog_asset(root, "crypto", symbol, native={"1m"})


def _stock_rows(start_day_ms: int, days: int, minutes: list[int], step_min: int, price: float, seed: int) -> np.ndarray:
    """Candle saham hari kerja saja; ``minutes`` = menit sejak tengah malam lokal untuk tiap candle."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(days):
        day_lt = start_day_ms + d * DAY
        if ((day_lt // DAY) + 3) % 7 >= 5:  # Sabtu/Minggu
            continue
        for m in minutes:
            lt = day_lt + m * 60_000
            rows.append(lt)
    lt = np.array(rows, dtype=np.int64)
    n = len(lt)
    close = price * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    open_ = np.concatenate([[price], close[:-1]])
    rec = np.empty(n, REC)
    rec["lt"] = lt
    rec["t"] = lt - JKT
    rec["o"], rec["c"] = open_, close
    rec["h"] = np.maximum(open_, close) * (1 + rng.uniform(0, 0.003, n))
    rec["l"] = np.minimum(open_, close) * (1 - rng.uniform(0, 0.003, n))
    rec["v"] = rng.uniform(1e3, 1e5, n)
    return rec


def make_idx(root: Path, symbol: str = "TEST") -> None:
    end_day = (T0 + JKT) // DAY * DAY + 400 * DAY  # tanggal lokal terakhir
    session_5m = [9 * 60 + 5 * i for i in range(36)] + [13 * 60 + 30 + 5 * i for i in range(30)]
    session_1h = [9 * 60, 10 * 60, 11 * 60, 13 * 60 + 30, 14 * 60 + 30, 15 * 60 + 30]
    write_series(series_path(root, "idx", symbol, "1d"), _stock_rows(end_day - 1000 * DAY, 1000, [0], 1440, 5000, 3))
    write_series(series_path(root, "idx", symbol, "1h"), _stock_rows(end_day - 120 * DAY, 120, session_1h, 60, 5000, 4))
    write_series(series_path(root, "idx", symbol, "5m"), _stock_rows(end_day - 20 * DAY, 20, session_5m, 5, 5000, 5))
    derive(root, "idx", symbol, "1d", ["1w", "1M"])
    update_catalog_asset(root, "idx", symbol, native={"1d", "1h", "5m"})
