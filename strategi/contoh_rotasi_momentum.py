"""Rotasi momentum: pegang N aset terkuat (portofolio, saham US)

Tiap minggu: urutkan aset berdasarkan kenaikan `periode` candle terakhir, pegang `jumlah` teratas yang momentumnya
positif dengan bobot sama, sisanya dijual. Filter risiko: kalau VIX (dari pengumpul-data) di atas `vix_maks`,
semua posisi dijual. Tanpa data VIX, filter ini otomatis tidak dipakai.
"""
from app.backtest.ta import roc

PENGATURAN = {
    "pasar": "us",
    "aset": "semua",
    "timeframe": "1d",
    "mulai": "2015-01-01",
    "mode": "portofolio",     # satu modal untuk semua aset
    "produk": "spot",
    "modal": 10_000,
}

PARAMETER = {"periode": 90, "jumlah": 5, "hari_rebalance": 0, "vix_maks": 30.0}


def siapkan(df, p, ekstra):
    df["mom"] = roc(df.close, p.periode)
    # VIX harian, ditempel dengan aman (hanya nilai yang sudah terbit saat candle ditutup)
    df = ekstra.gabung(df, ekstra.yahoo("^VIX", "1d"), kolom="close", awalan="vix_")
    return df


def langkah(bt, p):
    if bt.waktu.dayofweek != p.hari_rebalance:   # 0 = Senin
        return
    vix = bt[bt.aset[0]].vix_close
    if vix == vix and vix > p.vix_maks:          # vix == vix → bukan NaN
        for a in bt.aset:
            bt.target(a, persen=0)
        return
    skor = {a: bt[a].mom for a in bt.aset if bt.ada(a) and bt[a].mom == bt[a].mom}
    pilih = [a for a, m in sorted(skor.items(), key=lambda kv: -kv[1])[: p.jumlah] if m > 0]
    bobot = 98 / max(1, len(pilih))              # sisakan 2% untuk fee
    for a in bt.aset:
        bt.target(a, persen=bobot if a in pilih else 0)
