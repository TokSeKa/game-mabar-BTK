"""Unduh candle saham (IDX & US) dari Yahoo Finance lewat ``yfinance``.

Batas dari Yahoo: harian bisa sejak awal pencatatan, 1 jam hanya ~730 hari terakhir,
5m/15m/30m ~60 hari, dan 1m ~30 hari. Karena itu perintah ``update`` sebaiknya dijalankan
rutin (misalnya setiap hari): data intraday baru disambung ke data lama sehingga
riwayatnya makin panjang dari waktu ke waktu.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .markets import YAHOO_INTERVALS, YAHOO_SUFFIX
from .store import derive, read_series, series_path, update_catalog_asset, write_series
from .timeframes import REC, dedupe_sorted

Log = Callable[[str], None]

PERIODS = {"1d": "max", "1h": "730d", "30m": "60d", "15m": "60d", "5m": "60d"}


def df_to_rec(df: Any) -> np.ndarray:
    """DataFrame yfinance (index bertimezone bursa) → record ``REC``."""
    if df is None or len(df) == 0:
        return np.empty(0, REC)
    cols = {c.lower(): c for c in df.columns}
    need = [cols.get(k) for k in ("open", "high", "low", "close")]
    if any(c is None for c in need):
        return np.empty(0, REC)
    df = df.dropna(subset=need)
    if len(df) == 0:
        return np.empty(0, REC)
    idx = df.index
    if getattr(idx, "tz", None) is None:
        idx = idx.tz_localize("UTC")
    t = idx.tz_convert("UTC").tz_localize(None).values.astype("datetime64[ms]").astype(np.int64)
    lt = idx.tz_localize(None).values.astype("datetime64[ms]").astype(np.int64)
    rec = np.empty(len(df), REC)
    rec["t"], rec["lt"] = t, lt
    rec["o"] = df[cols["open"]].to_numpy(dtype=np.float64)
    rec["h"] = df[cols["high"]].to_numpy(dtype=np.float64)
    rec["l"] = df[cols["low"]].to_numpy(dtype=np.float64)
    rec["c"] = df[cols["close"]].to_numpy(dtype=np.float64)
    vcol = cols.get("volume")
    rec["v"] = np.nan_to_num(df[vcol].to_numpy(dtype=np.float64)) if vcol else 0.0
    ok = (rec["h"] >= rec["l"]) & (rec["c"] > 0) & (rec["o"] > 0)
    return rec[ok]


def _history(ticker: Any, tries: int = 4, **kw: Any) -> Any:
    from yfinance.exceptions import YFRateLimitError

    for i in range(tries):
        try:
            return ticker.history(auto_adjust=False, actions=False, repair=False, **kw)
        except YFRateLimitError:
            time.sleep(20 * (i + 1))
        except Exception:  # noqa: BLE001 - jaringan/parsing: coba lagi sebentar
            time.sleep(3 * (i + 1))
    return None


def fetch_interval(ticker: Any, interval: str) -> np.ndarray:
    if interval == "1m":
        parts = []
        now = datetime.now(timezone.utc)
        for k in range(4):  # Yahoo: 1m maks 8 hari per permintaan, 30 hari ke belakang
            end = now - timedelta(days=7 * k)
            start = end - timedelta(days=7)
            parts.append(df_to_rec(_history(ticker, interval="1m", start=start, end=end)))
            time.sleep(0.4)
        return dedupe_sorted(np.concatenate(parts)) if parts else np.empty(0, REC)
    return df_to_rec(_history(ticker, interval=interval, period=PERIODS[interval]))


def ingest_symbol(root: Path, market: str, symbol: str, log: Log, intervals: tuple[str, ...] = YAHOO_INTERVALS) -> bool:
    import yfinance as yf

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    ticker = yf.Ticker(symbol + YAHOO_SUFFIX[market])
    got: list[str] = []
    for interval in intervals:
        new = fetch_interval(ticker, interval)
        time.sleep(0.4)
        if len(new) == 0:
            continue
        path = series_path(root, market, symbol, interval)
        old = read_series(path, mmap=False)
        write_series(path, dedupe_sorted(np.concatenate([old, new])))
        got.append(f"{interval}:{len(new)}")
    if not got:
        log(f"  {symbol}: tidak ada data dari Yahoo (kode salah atau sudah delisting?), dilewati")
        return False
    if (root / "series" / market / symbol / "1d.bin").exists():
        derive(root, market, symbol, "1d", ["1w", "1M"])
    update_catalog_asset(root, market, symbol, native=set(YAHOO_INTERVALS))
    log(f"  {symbol}: " + ", ".join(got))
    return True
