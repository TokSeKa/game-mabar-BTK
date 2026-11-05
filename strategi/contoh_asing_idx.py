"""Ikut arus dana asing (saham IDX + data pengumpul-data)

Beli kalau total beli bersih asing `hari` hari terakhir positif dan harga di atas EMA; jual kalau asing berbalik
jual bersih. Butuh data ringkasan IDX dari folder anything/pengumpul-data (jalankan pengumpulnya dulu);
data asing hari ini baru dianggap terbit pukul 18:00 WIB, jadi baru dipakai untuk keputusan berikutnya.
"""
from app.backtest.ta import ema

PENGATURAN = {
    "pasar": "idx",
    "aset": ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"],
    "timeframe": "1d",
    "mulai": "2026-01-01",
    "mode": "per_aset",
    "produk": "spot",
    "modal": 100_000_000,
}

PARAMETER = {"hari": 5, "ema_n": 20}

PLOT = ["ema"]


def siapkan(df, p, ekstra):
    kode = df.attrs["simbol"]                       # simbol aset yang sedang disiapkan
    df = ekstra.gabung(df, ekstra.asing(kode), kolom="asing_bersih")
    df["asing_n"] = df.asing_bersih.rolling(p.hari, min_periods=1).sum()
    df["ema"] = ema(df.close, p.ema_n)
    return df


def langkah(bt, p):
    for a in bt.aset:
        x = bt[a]
        if x.asing_n != x.asing_n:                  # NaN: belum ada data asing di tanggal ini
            continue
        if bt.posisi(a) == 0 and x.asing_n > 0 and x.close > x.ema:
            bt.beli(a, persen=100)
        elif bt.posisi(a) > 0 and x.asing_n < 0:
            bt.tutup(a)
