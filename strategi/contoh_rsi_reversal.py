"""RSI oversold di atas EMA 200 (mean reversion, saham IDX)

Beli saat RSI(2) < batas_beli dan harga masih di atas EMA 200 (tren besar naik).
Jual saat RSI(2) > batas_jual atau setelah tahan_maks hari. Fee IDX: beli 0,15%, jual 0,25%.
"""
from app.backtest.ta import ema, rsi

PENGATURAN = {
    "pasar": "idx",
    "aset": "semua",
    "timeframe": "1d",
    "mulai": "2018-01-01",
    "mode": "per_aset",
    "produk": "spot",
    "modal": 100_000_000,
}

PARAMETER = {"rsi_n": 2, "batas_beli": 10, "batas_jual": 70, "ema_tren": 200, "tahan_maks": 10}

PLOT = ["ema_tren"]


def siapkan(df, p):
    df["rsi"] = rsi(df.close, p.rsi_n)
    df["ema_tren"] = ema(df.close, p.ema_tren)
    return df


def langkah(bt, p):
    for a in bt.aset:
        if not bt.ada(a):           # hari libur / belum listing
            continue
        x = bt[a]
        if bt.posisi(a) == 0:
            if x.rsi < p.batas_beli and x.close > x.ema_tren:
                bt.beli(a, persen=100)
                bt.state[a] = bt.i   # catat kapan masuk (state boleh dipakai bebas)
        elif x.rsi > p.batas_jual or bt.i - bt.state.get(a, bt.i) >= p.tahan_maks:
            bt.tutup(a)
