# Game Mabar BTK

Kumpulan game browser untuk dimainkan bareng teman, dalam satu server:

| Game | Ringkasnya |
|---|---|
| **Suit Bot Arena** | Program bot batu-gunting-kertas dengan blok ala Scratch atau Python, lalu adu dengan bot teman (2–8 pemain) sampai HP habis. |
| **Kilas Pasar** | Simulasi trading dengan candle **asli** kripto, saham IDX, dan saham US. Mode buta, fee realistis, indikator & alat gambar. Main sendiri, tantangan harian, atau balapan bareng teman. |

---

## Kilas Pasar

Kamu dilempar ke satu titik di masa lalu. Candle berikutnya belum terlihat: putuskan beli atau jual, lalu majukan waktu candle demi candle (atau putar otomatis). Server memegang semua data, jadi candle masa depan tidak bisa diintip dari browser.

![Kilas Pasar: dua chart, indikator, alat gambar, dan order](docs/screenshots/kilas-chart.png)

**Fitur**

- **Data pasar asli.**
  - Kripto dari arsip publik Binance: candle 1 menit sejak 2017.
  - Saham IDX dan US dari Yahoo Finance.
- **13 timeframe** (1m, 3m, 5m, 15m, 30m, 1j, 2j, 4j, 6j, 12j, 1h, 1mg, 1b) yang tetap sinkron saat diganti. Candle timeframe besar tampil "sedang terbentuk", dan bisa dilihat dalam tampilan 2 chart sekaligus.
- **Mode buta** (default): nama aset, tanggal, dan level harga disamarkan. Persentase gerakan harga tetap persis sama. Identitas aslinya dibuka di layar hasil.
- **Spot penuh dengan modal dan fee.**
  - Jenis order: market, limit, stop buy (breakout), stop loss, take profit, dan pasangan OCO.
  - Fee dan slippage bisa diatur.
  - Saham IDX memakai lot 100 lembar.
- **Indikator:** EMA/SMA (hingga 5 periode), Bollinger Bands, VWAP, volume, RSI, MACD, Stochastic, ATR.
- **Alat gambar:** garis tren, sinar, garis horizontal, kotak zona, Fibonacci, dan alat ukur (%, jumlah candle). Gambar ikut tampil di semua timeframe.
- **Tiga mode main:**
  - Main sendiri.
  - Tantangan harian: soal sama untuk semua orang, ada papan peringkat, dan hanya percobaan pertama yang dinilai.
  - Balapan: room untuk sampai 20 orang, candle maju otomatis, dengan klasemen langsung.
- **Layar hasil:** return dibanding strategi beli-lalu-tahan, win rate, profit factor, max drawdown, fee, kurva ekuitas, dan daftar transaksi.
- **Akun** (opsional) untuk papan peringkat dan riwayat hasil.

| Hasil sesi | Balapan |
|---|---|
| ![Hasil](docs/screenshots/kilas-hasil.png) | ![Balapan](docs/screenshots/kilas-balapan.png) |

**Data pasar** diunduh sekali, lalu bisa di-update kapan saja:

| Preset | Isi | Waktu & ukuran |
|---|---|---|
| `cepat` | 5 kripto (1m sejak 2024-07), 30 saham IDX, 20 saham US | beberapa menit, <1 GB |
| `penuh` | ±65 kripto (1m sejak 2017), ±140 saham IDX, ±90 saham US | beberapa jam, puluhan GB |
| `update` | data terbaru untuk semua aset yang sudah ada | jalankan rutin |
| `contoh` | data buatan, tanpa internet | instan |

- Windows: `scripts\unduh-data.bat`
- Mac/Linux: `./scripts/unduh-data.sh cepat`
- Tanpa Docker: `python -m app.trading.unduh semua --preset cepat` dari folder `backend`

Aturan eksekusi order dijelaskan lengkap di halaman **Cara main** di dalam game.

---

## Suit Bot Arena

Pemain tidak memilih senjata sendiri. Yang memilih adalah **algoritma botmu**, dijalankan setiap ronde tanpa unsur acak. Strategi lawan tersembunyi; yang terlihat hanya pilihan mereka di ronde-ronde sebelumnya. Bot bisa dibuat dengan **blok visual**, **Python**, atau dibuatkan **AI** dengan menempelkan [panduan lengkap](docs/PANDUAN_BOT_LLM.md).

![Replay match](docs/screenshots/replay.png)

- **Room multiplayer**: kode 5 huruf dan link undangan. Host mengatur HP awal, HP hilang saat kalah, batas ronde, dan ingatan bot.
- **Replay animasi**: bot berpikir, kartu dibuka, bot berkumpul ke 3 kotak senjata, aliran HP, rincian pembagian poin, dan podium.
- **Editor blok** (Blockly) dan **editor kode** (CodeMirror), dengan pesan error per baris dalam bahasa Indonesia.
- **Arena latihan** melawan 11 bot contoh.
- **Aman untuk VPS**: kode bot dijalankan interpreter khusus dengan batas langkah, memori, dan rekursi.

Aturan: setiap bot yang senjatanya dikalahkan kehilangan 100 HP (bisa diatur), lalu HP itu dibagi rata ke golongan pemenang. Aturannya sirkular, jadi kalau ketiga senjata muncul, setiap golongan sekaligus menang dan kalah. Sisa pembagian diberikan ke pemenang ber-HP terendah.

```python
def pilih():
    if ronde() == 1:
        return KERTAS
    return pengalah(terbanyak(jumlah_terakhir()))   # lawan senjata terpopuler
```

---

## Menjalankan

| Situasi | Panduan |
|---|---|
| Main dari laptop, dibuka ke internet lewat Cloudflare Tunnel | [MAIN-LOKAL.md](MAIN-LOKAL.md): Windows klik dua kali `scripts\main-lokal.bat`, Mac/Linux `./scripts/main-lokal.sh` |
| Deploy ke VPS (Nginx/Caddy, HTTPS, update data rutin) | [DEPLOY.md](DEPLOY.md) |

Development (Python 3.12+, Node 20+):

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
```

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Buka http://localhost:5173. Vite meneruskan `/api` dan `/ws` ke backend di port 8000.

## Tes

```bash
cd backend && pytest -q
```

Tes backend Kilas Pasar mencakup:
- agregasi timeframe dan zona waktu bursa
- parser arsip Binance (termasuk timestamp mikrodetik 2025)
- eksekusi order (fee, slippage, gap, urutan SL/TP di dalam candle, OCO, lot IDX)
- **tidak ada candle masa depan yang bocor** untuk setiap timeframe
- mode buta
- akun, tantangan harian, dan balapan lewat WebSocket

## Struktur proyek

```
backend/app/
  engine/, bot/, rooms/      Suit Bot Arena: aturan, interpreter bot aman, room
  trading/
    timeframes.py, store.py  format candle, agregasi multi-timeframe, katalog (memmap)
    ingest_binance.py        pengunduh arsip Binance
    ingest_yahoo.py          pengunduh Yahoo Finance (IDX & US)
    unduh.py                 CLI: python -m app.trading.unduh ...
    session.py               tampilan sesi replay (tanpa bocor masa depan, mode buta)
    engine.py                akun spot: order, eksekusi per candle, fee, statistik
    service.py, api.py       solo, harian, balapan, REST & WebSocket /ws/pasar
    accounts.py              akun & papan peringkat (SQLite)
frontend/src/
  trading/                   Kilas Pasar: chart (lightweight-charts), indikator, alat gambar, panel order
  replay/, editor/, views/   Suit Bot Arena
docs/                        panduan bot untuk AI, screenshot
scripts/                     main dari laptop + tunnel, unduh data (Windows/Mac/Linux)
deploy/                      contoh Nginx/Caddy + script update
```

## Konfigurasi

Semua konfigurasi lewat `.env` (lihat `.env.example`): `PORT`, `BIND_ADDRESS`, `MATCH_WORKERS`, `BOT_MAX_STEPS`, `MAX_ROOMS`, `PLAYER_GRACE_SECONDS`, `ROOM_IDLE_SECONDS`, `PRACTICE_CONCURRENCY`, `MEM_LIMIT`, `CPUS`, `PASAR_DATA`.

Data Kilas Pasar (candle + database akun) disimpan di volume Docker `pasar-data`, atau di folder `data/` kalau dijalankan tanpa Docker.

Semua uang di Kilas Pasar virtual. Ini alat latihan membaca chart, bukan saran investasi.
