"""Data contoh buatan (bukan pasar nyata) supaya game bisa dicoba tanpa mengunduh apa pun.

Harga dibuat dengan random walk yang punya fase tren, sideways, dan volatilitas berubah-ubah,
memakai seed tetap sehingga hasilnya selalu sama.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .markets import MARKETS
from .store import derive, series_path, update_catalog_asset, write_series
from .timeframes import REC

DEMO_ASSETS = {"DEMO-A": 20_000.0, "DEMO-B": 35.0, "DEMO-C": 1.25}


def make_series(start_price: float, minutes: int, seed: int, start_ms: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # fase pasar: tiap ~1-5 hari ganti drift & volatilitas
    phase_len = rng.integers(1440, 7200, size=minutes // 1440 + 10)
    bounds = np.cumsum(phase_len)
    phase = np.searchsorted(bounds, np.arange(minutes), side="right")
    drift = rng.normal(0, 0.00006, size=len(phase_len))[phase]
    vol = rng.uniform(0.0004, 0.0018, size=len(phase_len))[phase]
    ret = drift + vol * rng.standard_t(4, size=minutes) / np.sqrt(2)
    close = start_price * np.exp(np.cumsum(ret))
    open_ = np.concatenate([[start_price], close[:-1]])
    wick = np.abs(rng.normal(0, 1, size=(2, minutes))) * vol * close * 0.6
    rec = np.empty(minutes, REC)
    rec["t"] = start_ms + np.arange(minutes, dtype=np.int64) * 60_000
    rec["lt"] = rec["t"]
    rec["o"], rec["c"] = open_, close
    rec["h"] = np.maximum(open_, close) + wick[0]
    rec["l"] = np.maximum(np.minimum(open_, close) - wick[1], 1e-9)
    rec["v"] = np.round(rng.gamma(2.0, 50.0, size=minutes) * (1 + 30 * vol), 4)
    return rec


def build_demo(root: Path, days: int = 120, log=print) -> None:
    start_ms = 946_684_800_000  # 2000-01-01, sengaja jauh dari data nyata
    for i, (sym, price) in enumerate(DEMO_ASSETS.items()):
        rec = make_series(price, days * 1440, seed=1000 + i, start_ms=start_ms)
        write_series(series_path(root, "demo", sym, "1m"), rec)
        derive(root, "demo", sym, "1m", list(MARKETS["demo"].tfs))
        update_catalog_asset(root, "demo", sym, native={"1m"})
        log(f"  {sym}: {len(rec):,} candle 1m")
