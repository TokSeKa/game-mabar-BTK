# Menulis strategi backtest

Setiap file `.py` di folder ini adalah satu strategi. Buka tab **Kilas Pasar → Backtest**, pilih strategi, atur
tanggal/aset/parameter, lalu **Jalankan**. File boleh diedit kapan saja (misalnya di VS Code); cukup muat ulang
halaman, tidak perlu build ulang. File yang namanya diawali `_` tidak muncul di daftar.

Mulai dari `_template.py` (salin jadi nama baru) atau salah satu `contoh_*.py`.

```python
"""Judul strategi (baris pertama tampil di daftar)"""
from app.backtest.ta import ema, atr, crossover

PENGATURAN = {"pasar": "crypto", "aset": ["BTCUSDT"], "timeframe": "4h", "mulai": "2022-01-01"}
PARAMETER = {"cepat": 20, "lambat": 50}
PLOT = ["ema_cepat", "ema_lambat"]

def siapkan(df, p):
    df["ema_cepat"] = ema(df.close, p.cepat)
    df["ema_lambat"] = ema(df.close, p.lambat)
    return df

def langkah(bt, p):
    for a in bt.aset:
        x = bt[a]
        if x.ema_cepat > x.ema_lambat and bt.posisi(a) == 0:
            bt.beli(a, persen=100)
        elif x.ema_cepat < x.ema_lambat and bt.posisi(a) > 0:
            bt.tutup(a)
```

Strategi adalah Python biasa: boleh `pandas`, `numpy`, fungsi sendiri, `import` file lain di folder ini.
`PENGATURAN`, `PARAMETER`, dan `PLOT` harus berisi nilai biasa (angka, teks, list, dict), karena dibaca tanpa
menjalankan kode untuk ditampilkan di web.

## PENGATURAN

| Kunci | Nilai | Default |
|---|---|---|
| `pasar` | `crypto`, `idx`, `us` | `crypto` |
| `aset` | list simbol (`["BBCA", "TLKM"]`) atau `"semua"` | `"semua"` |
| `timeframe` | kripto `1m 3m 5m 15m 30m 1h 2h 4h 6h 12h 1d 1w 1M`; saham `1m 5m 15m 30m 1h 1d 1w 1M` | `1d` |
| `mulai`, `selesai` | `"YYYY-MM-DD"` atau `None` (semua data) | `None` |
| `mode` | `per_aset`: tiap aset diuji sendiri dengan modal penuh, hasilnya dibandingkan. `portofolio`: satu modal untuk semua aset | `per_aset` |
| `produk` | `spot`; `futures` (kripto, atau saham dengan aturan bebas); `margin` (saham, bisa short) | `spot` |
| `aturan` | `nyata` (aturan bursa asli) atau `bebas` (short/futures di semua saham) | `nyata` |
| `modal` | angka dalam mata uang pasar | 10.000 USDT/USD, Rp100 juta |
| `leverage` | futures 1–125 (tergantung tier), margin 1–2 | 1 |
| `margin` | futures: `cross` atau `isolated` | `cross` |
| `slippage`, `fee_beli`, `fee_jual`, `fee_maker`, `fee_taker`, `bunga`, `biaya_pinjam` | proporsi (0.001 = 0,1%); kosong = default pasar | sama dengan game |
| `pemanasan` | jumlah candle sebelum `mulai` untuk memanaskan indikator | 300 |
| `maks_aset` | batas jumlah aset kalau `aset = "semua"` | 60 |

Semua bisa diubah lagi dari layar Backtest tanpa mengedit file.

## siapkan(df, p) atau siapkan(df, p, ekstra)

Dipanggil **sekali per aset** sebelum simulasi. `df` adalah DataFrame:

- index `waktu` = waktu **buka** candle (UTC); kolom `open`, `high`, `low`, `close`, `volume`
- `df.attrs["simbol"]`, `df.attrs["pasar"]`, `df.attrs["timeframe"]`

Tambahkan kolom indikator lalu kembalikan `df` (jumlah baris harus tetap). Semua kolom bisa dibaca di `langkah`
lewat `bt[a].nama_kolom`, dan kolom yang disebut di `PLOT` digambar di chart hasil.

Indikator siap pakai di `app.backtest.ta`: `sma ema rma wma rsi atr true_range macd bollinger donchian keltner
stoch roc momentum zscore highest lowest crossover crossunder obv vwap adx supertrend`.

**Jangan memakai data masa depan.** Nilai di baris *i* hanya boleh dihitung dari baris ≤ *i*. Yang curang misalnya
`shift(-1)`, `rolling(..., center=True)`, atau menormalkan dengan rata-rata seluruh data. Backtest otomatis
memeriksa ini (menghitung ulang `siapkan` di data yang dipotong) dan memberi peringatan kalau ada kolom yang curang.

## langkah(bt, p)

Dipanggil setiap candle **ditutup**. Order yang dibuat di sini dieksekusi **mulai candle berikutnya**
(order market terisi di open candle berikutnya), sama seperti di dunia nyata.

| Data | |
|---|---|
| `bt.aset` | list simbol (mode per_aset: satu simbol) |
| `bt[a]` | candle yang baru ditutup: `bt[a].close`, `bt[a].rsi`, `bt[a]["kolom"]` |
| `bt.hist(a, n=None, kolom=None)` | DataFrame riwayat sampai candle ini (tidak pernah ada masa depan) |
| `bt.ada(a)` | `False` kalau aset ini tidak punya candle baru (saham libur/belum listing) |
| `bt.waktu`, `bt.i` | waktu buka candle ini (UTC) dan nomor langkah |
| `bt.ekuitas`, `bt.kas`, `bt.tersedia`, `bt.leverage` | kondisi akun |
| `bt.posisi(a)` | jumlah bertanda (+ long, − short) |
| `bt.harga_masuk(a)`, `bt.nilai(a)`, `bt.laba(a)`, `bt.harga_likuidasi(a)` | info posisi |
| `bt.order(a=None)` | order yang masih menunggu |
| `bt.state` | dict bebas untuk menyimpan catatanmu sendiri |
| `bt.ekstra` | data pengumpul-data yang sudah terbit pada waktu ini (lihat bawah) |

| Order | |
|---|---|
| `bt.beli(a, ...)` / `bt.jual(a, ...)` (alias `bt.short`) | ukuran: `qty=` unit, `nilai=` uang, atau `persen=` % ekuitas sebagai margin × leverage |
| `harga=` | order limit; `stop=` stop-market; keduanya stop-limit |
| `sl=`, `tp=` | stop loss & take profit, dipasang otomatis (OCO) setelah order masuk terisi |
| `reduce_only=True` | hanya mengurangi posisi |
| `bt.tutup(a=None, harga=None)` | tutup posisi (semua aset kalau `a` kosong); `harga` = tutup dengan limit |
| `bt.target(a, persen=/qty=/nilai=)` | atur posisi jadi target (bertanda: `persen=-50` = short 50%); cocok untuk portofolio |
| `bt.batal(a=None, id=None)` | batalkan order yang menunggu |
| `bt.log(...)` | catatan yang tampil di hasil |

Order yang ditolak (kas/margin kurang, short tidak boleh, uptick BEI, dll.) tidak menghentikan backtest;
alasannya muncul di **Log** hasil.

## Cara eksekusi & biaya

- Market: open candle berikutnya ± slippage, fee taker. Limit: terisi di harganya (maker), atau di open kalau
  harga membuka melewatinya. Stop: jadi market saat tersentuh.
- Di dalam satu candle harga diasumsikan bergerak O → Low → High → Close (candle naik) atau O → High → Low → Close.
  Pakai timeframe kecil kalau SL/TP-mu sangat rapat.
- Fee, lot, aturan short, likuidasi, funding, dan bunga persis sama dengan mode Futures/Margin di game
  (Binance USDⓈ-M untuk kripto, Reg T untuk US, aturan BEI untuk IDX). Lihat **Cara main** di Kilas Pasar.
- Funding memakai data asli Binance kalau sudah diunduh (`scripts\unduh-data.bat` → Funding rate),
  kalau belum 0,01% per 8 jam. Harga acuan futures = candle spot.
- Mode portofolio: penjualan diisi sebelum pembelian di open yang sama (supaya rebalance tidak kekurangan kas).
  Likuidasi cross dengan beberapa posisi diperiksa per candle memakai harga terburuk (low untuk long, high untuk short).
- Posisi yang masih terbuka di akhir ditutup di harga terakhir (kena fee) supaya ikut dihitung.

## Data tambahan dari pengumpul-data (`ekstra`)

Kalau repo `anything/pengumpul-data` sudah mengumpulkan data (folder `anything/pengumpul-data/data`), strategi bisa
memakai:

| Fungsi | Isi |
|---|---|
| `ekstra.yahoo("^VIX", "1d")` | bar Yahoo: indeks (`^VIX`, `^JKSE`, `^GSPC`), forex (`USDIDR=X`), komoditas (`GC=F`), saham |
| `ekstra.asing("BBCA")` | harian asing/domestik satu emiten IDX: `asing_beli`, `asing_jual`, `asing_bersih`, `porsi_asing_pct`, … |
| `ekstra.ringkasan_saham()` | semua emiten semua hari |
| `ekstra.broker(kode=None)` | ringkasan harian per broker IDX |
| `ekstra.tick("XAUUSD", "2025-01-01", "2025-01-31")` | tick bid/ask Dukascopy |
| `ekstra.gabung(df, data, kolom, awalan="")` | tempel kolom data ke candle dengan aman |

Setiap data punya kolom `tersedia`: kapan data itu sudah bisa diketahui (bar Yahoo setelah bar-nya selesai,
ringkasan IDX pukul 18:00 WIB). `ekstra.gabung` di `siapkan` dan `bt.ekstra` di `langkah` hanya memberi data yang
sudah tersedia saat candle ditutup, jadi tidak ada kebocoran informasi. Contoh: `contoh_asing_idx.py`,
`contoh_rotasi_momentum.py` (filter VIX).

## Dari terminal (opsional)

```
scripts\backtest.bat daftar
scripts\backtest.bat jalankan contoh_ema_cross --set mulai=2023-01-01 --set aset=BTCUSDT,ETHUSDT --param cepat=10
```

Hasilnya juga muncul di riwayat tab Backtest.

## Supaya hasilnya jujur

- Bandingkan dengan **beli-lalu-tahan** yang selalu ditampilkan. Strategi yang kalah dari beli-tahan setelah fee
  biasanya tidak berguna.
- Hati-hati *overfitting*: cari parameter di satu rentang (misalnya 2019–2022), lalu uji tanpa diubah di rentang lain
  (2023–sekarang). Kalau hasilnya runtuh, parameternya hanya cocok dengan masa lalu.
- Lihat jumlah transaksi: hasil dari 5 transaksi belum berarti apa-apa.
- Data saham intraday dari Yahoo hanya ±60 hari (5–30 menit) atau ±2 tahun (1 jam); untuk riwayat panjang pakai 1d.

Semua ini simulasi dengan uang virtual, bukan saran investasi.
