"""Data untuk backtest: candle Kilas Pasar + data tambahan dari ``anything/pengumpul-data``.

Data tambahan selalu disertai kolom ``tersedia`` (UTC), yaitu kapan data itu *sudah bisa diketahui* di dunia nyata:

* bar Yahoo  → waktu bar + panjang interval (bar 1d baru lengkap setelah harinya selesai)
* ringkasan asing/domestik & broker IDX → tanggal tersebut pukul 18:00 WIB (setelah IDX menerbitkannya)
* tick       → waktunya sendiri

Di dalam ``langkah`` hanya baris dengan ``tersedia`` ≤ waktu keputusan yang terlihat, jadi strategi tidak bisa
memakai data yang belum terbit. Di ``siapkan`` pakai ``ekstra.gabung(df, data)`` supaya penggabungannya juga aman.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..trading.markets import MARKETS
from ..trading.store import CandleStore
from ..trading.timeframes import MS

YAHOO_LEN = {"1m": "1min", "2m": "2min", "5m": "5min", "15m": "15min", "30m": "30min", "60m": "60min", "90m": "90min",
             "1h": "60min", "1d": "1D", "5d": "5D", "1wk": "7D", "1mo": "31D"}
MENIT = {"1m", "2m", "5m", "15m", "30m", "60m", "90m"}
IDX_TERBIT_UTC = pd.Timedelta(hours=11)  # 18:00 WIB


def pengumpul_dir() -> Path:
    from ..config import ROOT
    env = os.environ.get("PENGUMPUL_DIR")
    return Path(env) if env else ROOT.parent / "anything" / "pengumpul-data" / "data"


def _safe(simbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9.=_\-]", "_", simbol)


def _read(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for p in paths:
        try:
            frames.append(pd.read_parquet(p))
        except Exception:  # noqa: BLE001 - file rusak/kosong dilewati
            continue
    frames = [f for f in frames if len(f)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _utc(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s)
    return s.dt.tz_localize("UTC") if s.dt.tz is None else s.dt.tz_convert("UTC")


class Eksternal:
    """Pembaca data pengumpul-data. ``batas`` (UTC) memotong data yang belum tersedia pada waktu itu."""

    def __init__(self, root: Path | None = None, tf_ms: int = 86_400_000, batas: pd.Timestamp | None = None,
                 _cache: dict[str, pd.DataFrame] | None = None):
        self.root = Path(root) if root else pengumpul_dir()
        self.tf = pd.Timedelta(milliseconds=tf_ms)
        self.batas = batas
        self._cache = {} if _cache is None else _cache

    def pada(self, batas: pd.Timestamp) -> "Eksternal":
        """Tampilan yang hanya melihat data yang sudah tersedia pada ``batas`` (dipakai di dalam ``langkah``)."""
        return Eksternal(self.root, int(self.tf / pd.Timedelta(milliseconds=1)), batas, self._cache)

    # ------------------------------------------------------------ util
    def _cut(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.batas is None or df.empty:
            return df
        return df[df["tersedia"] <= self.batas]

    def _cached(self, key: str, load) -> pd.DataFrame:
        if key not in self._cache:
            self._cache[key] = load()
        return self._cache[key]

    def ada(self) -> bool:
        return self.root.is_dir()

    def status(self) -> dict[str, Any]:
        """Data apa saja yang tersedia (untuk layar Backtest)."""
        r = self.root
        out: dict[str, Any] = {"folder": str(r), "ada": r.is_dir(), "yahoo": {}, "idx_saham": 0, "idx_broker": 0, "tick": []}
        if not r.is_dir():
            return out
        y = r / "yahoo"
        if y.is_dir():
            for iv in sorted(p.name for p in y.iterdir() if p.is_dir()):
                names = sorted({p.stem if p.is_file() else p.name for p in (y / iv).iterdir()})
                out["yahoo"][iv] = names[:500]
        out["idx_saham"] = len(list((r / "idx" / "ringkasan_saham").glob("*.parquet"))) if (r / "idx" / "ringkasan_saham").is_dir() else 0
        out["idx_broker"] = len(list((r / "idx" / "ringkasan_broker").glob("*.parquet"))) if (r / "idx" / "ringkasan_broker").is_dir() else 0
        t = r / "tick" / "dukascopy"
        out["tick"] = sorted(p.name for p in t.iterdir() if p.is_dir()) if t.is_dir() else []
        return out

    # ------------------------------------------------------------ Yahoo (indeks, VIX, forex, komoditas, saham)
    def yahoo(self, simbol: str, interval: str = "1d") -> pd.DataFrame:
        """Bar Yahoo: index ``waktu`` (UTC), kolom open/high/low/close/adj_close/volume + ``tersedia``."""
        def load() -> pd.DataFrame:
            base = self.root / "yahoo" / interval
            name = _safe(simbol)
            paths = sorted((base / name).glob("*.parquet")) if interval in MENIT else [base / f"{name}.parquet"]
            df = _read([p for p in paths if p.exists()])
            if df.empty:
                return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume", "tersedia"])
            df["waktu"] = _utc(df["waktu"])
            df = df.drop_duplicates("waktu").sort_values("waktu").set_index("waktu")
            df["tersedia"] = df.index + pd.Timedelta(YAHOO_LEN.get(interval, "1D"))
            return df
        return self._cut(self._cached(f"y:{interval}:{simbol}", load))

    # ------------------------------------------------------------ IDX
    def ringkasan_saham(self) -> pd.DataFrame:
        """Semua emiten, semua hari: tanggal, kode, asing_beli/jual/bersih, domestik_*, porsi_asing_pct, ..."""
        def load() -> pd.DataFrame:
            df = _read(sorted((self.root / "idx" / "ringkasan_saham").glob("*.parquet")))
            if df.empty:
                return pd.DataFrame(columns=["tanggal", "kode", "tersedia"])
            df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.tz_localize(None).dt.normalize()
            df["tersedia"] = (df["tanggal"] + IDX_TERBIT_UTC).dt.tz_localize("UTC")
            return df.sort_values(["tanggal", "kode"]).reset_index(drop=True)
        return self._cut(self._cached("idx:saham", load))

    def asing(self, kode: str) -> pd.DataFrame:
        """Riwayat harian asing/domestik satu emiten IDX (index ``tanggal``)."""
        df = self.ringkasan_saham()
        if df.empty or "kode" not in df.columns:
            return df
        return df[df["kode"] == kode.upper().replace(".JK", "")].set_index("tanggal")

    def broker(self, kode_broker: str | None = None) -> pd.DataFrame:
        """Ringkasan harian semua broker IDX (volume/nilai/frekuensi di seluruh pasar)."""
        def load() -> pd.DataFrame:
            df = _read(sorted((self.root / "idx" / "ringkasan_broker").glob("*.parquet")))
            if df.empty:
                return pd.DataFrame(columns=["tanggal", "kode_broker", "tersedia"])
            df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.tz_localize(None).dt.normalize()
            df["tersedia"] = (df["tanggal"] + IDX_TERBIT_UTC).dt.tz_localize("UTC")
            return df.sort_values(["tanggal", "kode_broker"]).reset_index(drop=True)
        df = self._cut(self._cached("idx:broker", load))
        if kode_broker and not df.empty:
            df = df[df["kode_broker"] == kode_broker.upper()]
        return df

    # ------------------------------------------------------------ tick Dukascopy
    def tick(self, simbol: str, dari: str, sampai: str) -> pd.DataFrame:
        """Tick bid/ask (index ``waktu`` UTC) untuk rentang tanggal ``YYYY-MM-DD``."""
        days = pd.date_range(dari, sampai, freq="D")
        base = self.root / "tick" / "dukascopy" / simbol.upper()
        df = _read([base / f"{d:%Y-%m-%d}.parquet" for d in days if (base / f"{d:%Y-%m-%d}.parquet").exists()])
        if df.empty:
            return pd.DataFrame(columns=["bid", "ask", "bid_vol", "ask_vol", "tersedia"])
        df["waktu"] = _utc(df["waktu"])
        df = df.sort_values("waktu").set_index("waktu")
        df["tersedia"] = df.index
        return self._cut(df)

    # ------------------------------------------------------------ gabung aman
    def gabung(self, df: pd.DataFrame, data: pd.DataFrame, kolom: list[str] | str | None = None,
               awalan: str = "") -> pd.DataFrame:
        """Tempel kolom ``data`` ke candle ``df``: tiap candle mendapat nilai terakhir yang SUDAH tersedia
        saat candle itu ditutup (merge_asof ke belakang berdasarkan ``tersedia``)."""
        if isinstance(kolom, str):
            kolom = [kolom]
        if data is None or data.empty:
            for k in kolom or []:
                df[awalan + k] = np.nan
            return df
        kolom = kolom or [c for c in data.columns if c != "tersedia" and pd.api.types.is_numeric_dtype(data[c])]
        right = data[["tersedia"] + list(kolom)].sort_values("tersedia").rename(columns={k: awalan + k for k in kolom})
        right["tersedia"] = pd.to_datetime(right["tersedia"], utc=True).dt.as_unit("ns")
        left = pd.DataFrame({"_tutup": (df.index + self.tf).as_unit("ns"), "_urut": np.arange(len(df))})
        m = pd.merge_asof(left.sort_values("_tutup"), right, left_on="_tutup", right_on="tersedia", direction="backward")
        m = m.sort_values("_urut")
        for k in kolom:
            df[awalan + k] = m[awalan + k].to_numpy()
        return df


# ---------------------------------------------------------------- candle Kilas Pasar
def load_candles(store: CandleStore, market: str, symbol: str, tf: str, mulai_ms: int | None, selesai_ms: int | None,
                 warmup: int) -> tuple[pd.DataFrame, int, np.ndarray]:
    """Candle satu aset sebagai DataFrame (index ``waktu`` UTC = waktu buka candle).

    Mengembalikan (df, posisi baris pertama yang diperdagangkan, waktu lokal bursa dalam ms)."""
    key = f"{market}:{symbol}"
    rec = store.series(key, tf)
    if len(rec) == 0:
        raise ValueError(f"{symbol}: tidak ada data {tf}.")
    t = np.asarray(rec["t"])
    i0 = int(np.searchsorted(t, mulai_ms, side="left")) if mulai_ms else 0
    i1 = int(np.searchsorted(t, selesai_ms, side="right")) if selesai_ms else len(t)
    if i1 <= i0:
        raise ValueError(f"{symbol}: tidak ada candle {tf} di rentang tanggal itu.")
    iw = max(0, i0 - warmup)
    rows = np.asarray(rec[iw:i1])
    df = pd.DataFrame({
        "open": rows["o"].astype(float), "high": rows["h"].astype(float), "low": rows["l"].astype(float),
        "close": rows["c"].astype(float), "volume": rows["v"].astype(float),
    }, index=pd.DatetimeIndex(pd.to_datetime(rows["t"], unit="ms", utc=True), name="waktu"))
    return df, i0 - iw, np.asarray(rows["lt"], dtype=np.int64)


def market_assets(store: CandleStore, market: str, tf: str) -> list[str]:
    return sorted(a["symbol"] for a in store.assets().values() if a["market"] == market and tf in a["series"])


def tf_ms(tf: str) -> int:
    return MS[tf]


def annual_periods(market: str) -> int:
    return 365 if market in ("crypto", "demo") else 252


__all__ = ["Eksternal", "load_candles", "market_assets", "pengumpul_dir", "MARKETS"]
