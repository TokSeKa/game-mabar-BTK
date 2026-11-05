"""Breakout Donchian long/short (futures kripto, leverage)

Long saat close menembus atas kanal Donchian, short saat menembus bawah. Stop di sisi kanal yang berlawanan
(trailing mengikuti kanal keluar yang lebih pendek). Memakai futures perpetual: fee maker/taker, funding, likuidasi.
"""
from app.backtest.ta import atr, donchian

PENGATURAN = {
    "pasar": "crypto",
    "aset": ["BTCUSDT", "ETHUSDT"],
    "timeframe": "4h",
    "mulai": "2021-01-01",
    "mode": "per_aset",
    "produk": "futures",
    "leverage": 3,
    "margin": "isolated",     # cross | isolated
    "modal": 10_000,
}

PARAMETER = {"masuk": 55, "keluar": 20, "persen": 30}

PLOT = ["atas", "bawah", "keluar_atas", "keluar_bawah"]


def siapkan(df, p):
    m = donchian(df, p.masuk)
    k = donchian(df, p.keluar)
    df["atas"], df["bawah"] = m.atas, m.bawah
    df["keluar_atas"], df["keluar_bawah"] = k.atas, k.bawah
    df["atr"] = atr(df, 14)
    return df


def langkah(bt, p):
    for a in bt.aset:
        x = bt[a]
        q = bt.posisi(a)
        if q == 0:
            if x.close > x.atas:
                bt.beli(a, persen=p.persen, sl=x.keluar_bawah)
            elif x.close < x.bawah:
                bt.jual(a, persen=p.persen, sl=x.keluar_atas)
        elif q > 0 and x.close < x.keluar_bawah:
            bt.tutup(a)
        elif q < 0 and x.close > x.keluar_atas:
            bt.tutup(a)
