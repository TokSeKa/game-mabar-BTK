"""Judul strategimu (baris pertama tampil di daftar)

Penjelasan singkat. File yang namanya diawali _ tidak muncul di daftar; salin file ini jadi nama baru.
"""
from app.backtest.ta import ema, rsi, atr, crossover, crossunder  # noqa: F401

PENGATURAN = {
    "pasar": "crypto",          # crypto | idx | us
    "aset": ["BTCUSDT"],        # list simbol, atau "semua"
    "timeframe": "1h",          # 1m 3m 5m 15m 30m 1h 2h 4h 6h 12h 1d 1w 1M (saham: 1m 5m 15m 30m 1h 1d 1w 1M)
    "mulai": "2023-01-01",
    "selesai": None,
    "mode": "per_aset",         # per_aset (tiap aset modal sendiri) | portofolio (satu modal bersama)
    "produk": "spot",           # spot | futures (kripto) | margin (saham, bisa short)
    "leverage": 1,
    "margin": "cross",          # futures: cross | isolated
    "modal": 10_000,
}

PARAMETER = {"n": 20}

PLOT = []                       # nama kolom dari siapkan() yang digambar di chart


def siapkan(df, p):
    """Sekali per aset. df: index waktu (UTC), kolom open/high/low/close/volume. Tambah kolom indikator."""
    df["ema"] = ema(df.close, p.n)
    return df


def langkah(bt, p):
    """Tiap candle ditutup. Order market terisi di open candle berikutnya."""
    for a in bt.aset:
        x = bt[a]                # candle yang baru ditutup: x.close, x.ema, ...
        if bt.posisi(a) == 0 and x.close > x.ema:
            bt.beli(a, persen=100)
        elif bt.posisi(a) > 0 and x.close < x.ema:
            bt.tutup(a)
