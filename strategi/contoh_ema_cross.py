"""EMA cross + stop ATR (trend following, spot kripto)

Beli saat EMA cepat memotong ke atas EMA lambat, keluar saat memotong ke bawah.
Stop loss awal = harga masuk − atr_kali × ATR. Diuji per aset (masing-masing modal penuh).
"""
from app.backtest.ta import atr, crossover, crossunder, ema

PENGATURAN = {
    "pasar": "crypto",
    "aset": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "timeframe": "4h",
    "mulai": "2022-01-01",
    "selesai": None,          # None = sampai data terakhir
    "mode": "per_aset",       # per_aset | portofolio
    "produk": "spot",         # spot | futures | margin
    "modal": 10_000,
}

PARAMETER = {"cepat": 20, "lambat": 50, "atr_n": 14, "atr_kali": 2.5}

PLOT = ["ema_cepat", "ema_lambat"]


def siapkan(df, p):
    df["ema_cepat"] = ema(df.close, p.cepat)
    df["ema_lambat"] = ema(df.close, p.lambat)
    df["atr"] = atr(df, p.atr_n)
    df["naik"] = crossover(df.ema_cepat, df.ema_lambat)
    df["turun"] = crossunder(df.ema_cepat, df.ema_lambat)
    return df


def langkah(bt, p):
    for a in bt.aset:
        x = bt[a]
        if x.naik and bt.posisi(a) == 0:
            bt.beli(a, persen=100, sl=x.close - p.atr_kali * x.atr)
        elif x.turun and bt.posisi(a) > 0:
            bt.tutup(a)
