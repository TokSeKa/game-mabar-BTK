# Main dari Laptop (tanpa VPS)

Sebelum punya VPS, kamu bisa menjalankan semua game (Arena Mabar, Suit Bot Arena, Kilas Pasar) di laptop sendiri lalu membukanya ke internet lewat **Cloudflare Quick Tunnel**. Gratis, tidak perlu akun, dan tidak perlu domain. Kamu langsung dapat link seperti `https://kata-acak-acak.trycloudflare.com` yang bisa dibuka teman-temanmu dari HP atau laptop mana pun.

```
Teman-teman ──HTTPS──▶ Cloudflare ──tunnel──▶ cloudflared di laptopmu ──▶ game (port 8080)
```

Laptopmu jadi "VPS sementara". Port router tidak perlu dibuka dan IP publik tidak perlu diketahui.

---

## Ambil kodenya

Kode ada di branch `suit-bot-arena` (belum di-merge ke `main`).

- **Pakai git:**

  ```bash
  git clone -b suit-bot-arena https://github.com/TokSeKa/game-mabar-BTK.git
  ```

  ```bash
  cd game-mabar-BTK
  ```

- **Tanpa git:** unduh ZIP dari https://github.com/TokSeKa/game-mabar-BTK/archive/refs/heads/suit-bot-arena.zip, lalu ekstrak.

---

## Cara A: pakai Docker Desktop (paling mudah, semua OS)

1. Pasang **Docker Desktop**: https://www.docker.com/products/docker-desktop/ (di Windows, ikuti saja kalau diminta mengaktifkan WSL 2).
2. Buka Docker Desktop dan tunggu sampai statusnya "running".
3. Jalankan script:
   - **Windows:** klik dua kali `scripts\main-lokal.bat`
   - **Mac / Linux:**

     ```bash
     ./scripts/main-lokal.sh
     ```

4. Tunggu. Build pertama butuh beberapa menit, setelah itu cepat. Script akan menampilkan link `https://….trycloudflare.com` dan membukanya di browser.
5. Bagikan link itu ke teman-temanmu. **Kamu juga buka lewat link itu**, bukan `localhost`, supaya tombol "Salin link undangan" di room memberi alamat yang benar.

Perintah lain:

| Keperluan | Windows | Mac / Linux |
|---|---|---|
| Lihat link lagi | `scripts\main-lokal.bat link` | `./scripts/main-lokal.sh link` |
| Lihat log | `scripts\main-lokal.bat logs` | `./scripts/main-lokal.sh logs` |
| Matikan | `scripts\main-lokal.bat stop` | `./scripts/main-lokal.sh stop` |

Selama Docker Desktop menyala, game dan tunnel tetap berjalan meski terminal ditutup. Jangan lupa `stop` setelah selesai main.

### Data untuk Kilas Pasar (game trading)

Kilas Pasar butuh data candle pasar. Unduh sekali, lalu update kapan saja:

- **Windows:** klik dua kali `scripts\unduh-data.bat`, lalu pilih:
  - **1 Cepat**: ±5 menit. Berisi 30 saham IDX, 20 saham US, dan 5 kripto (1 menit sejak 2024-07).
  - **2 Penuh**: beberapa jam dan puluhan GB. Berisi ±140 saham IDX, ±90 saham US, lalu ±65 kripto (1 menit sejak 2017).
  - **3 Saham saja** / **4 Saham penuh**: hanya IDX + US, tanpa kripto. Pakai ini kalau sudah punya kripto tapi belum punya saham.
  - **5 Update**: menambahkan data terbaru ke semua aset yang sudah ada.
  - **6 Funding rate**: riwayat funding futures Binance untuk kripto yang sudah ada (dipakai mode Futures; tanpa ini dipakai 0,01% per 8 jam).

  Saham selalu diunduh lebih dulu (cuma beberapa menit), baru kripto yang lama. Jadi kalau unduhan penuh dihentikan
  di tengah jalan, saham sudah tersedia. **Update tidak menambah pasar baru**: kalau datamu baru kripto saja, pilih
  "Saham saja" sekali, setelah itu Update akan ikut memperbarui saham.
- **Mac / Linux:**

  ```bash
  ./scripts/unduh-data.sh cepat
  ```

  Ganti `cepat` dengan `penuh`, `saham`, `saham-penuh`, `update`, `funding`, `contoh`, atau `status` sesuai kebutuhan.

Pengunduhan bisa dijalankan saat game sedang menyala. Setelah selesai, cukup muat ulang halaman Kilas Pasar. Unduhan yang terputus (Ctrl+C, internet mati) bisa diulang dan akan melanjutkan dari bagian yang belum ada.

Data tersimpan di volume Docker `pasar-data`, jadi tidak hilang walaupun container dimatikan atau di-build ulang. Kalau memakai preset penuh, cek batas disk Docker Desktop di **Settings → Resources → Advanced → Disk image size**.

Untuk saham, Yahoo hanya menyediakan data 5–30 menit untuk ±60 hari terakhir, dan 1 menit untuk ±30 hari. Jalankan **Update** rutin (misalnya seminggu sekali) supaya riwayat intraday saham makin panjang.

---

## Cara B: tanpa Docker (Mac / Linux / WSL)

Lebih ringan untuk laptop. Butuh:

- **Python 3.10+**
- **Node.js 18+** (hanya untuk build pertama)
- **cloudflared**:
  - Mac: `brew install cloudflared`
  - Linux: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

Jalankan:

```bash
./scripts/main-lokal-tanpa-docker.sh
```

Script akan build frontend (sekali saja), menyiapkan Python venv, menyalakan server, membuka tunnel, lalu menampilkan link. Tekan **Ctrl+C** untuk berhenti; server dan tunnel ikut mati.

Pilihan tambahan:

```bash
PORT=9000 ./scripts/main-lokal-tanpa-docker.sh      # kalau port 8080 sudah dipakai
```

```bash
REBUILD=1 ./scripts/main-lokal-tanpa-docker.sh      # build ulang frontend setelah update kode
```

Data Kilas Pasar tanpa Docker (disimpan di folder `data/` di dalam repo). Jalankan dari folder `backend`:

```bash
.venv/bin/python -m app.trading.unduh semua --preset cepat
```

Ganti `semua --preset cepat` dengan `semua --preset penuh`, `saham`, `update`, `funding`, `contoh`, atau `status`.

### Main dengan teman di Wi-Fi yang sama (tanpa internet/tunnel)

```bash
TUNNEL=0 ./scripts/main-lokal-tanpa-docker.sh
```

Script menampilkan alamat seperti `http://192.168.1.23:8080` yang bisa dibuka HP/laptop lain di Wi-Fi yang sama.

---

## Cara C: Windows tanpa Docker (manual)

Pasang Python (https://www.python.org/downloads/, centang "Add to PATH"), Node.js (https://nodejs.org/), dan cloudflared:

```powershell
winget install --id Cloudflare.cloudflared
```

Build sekali (PowerShell, dari folder repo):

```powershell
cd frontend; npm ci; npm run build; cd ..
```

```powershell
cd backend; py -m venv .venv; .venv\Scripts\pip install -r requirements.txt
```

Setiap mau main, buka **dua** jendela PowerShell.

Jendela 1, di folder `backend`:

```powershell
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Jendela 2:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

Cari baris berisi `https://….trycloudflare.com` di jendela 2. Itu link untuk dibagikan.

---

## Hal yang perlu diingat

- **Laptop harus tetap menyala dan tersambung internet** selama main. Matikan sleep otomatis dan colokkan charger.
- **Link berubah** setiap kali tunnel dinyalakan ulang. Bagikan link baru ke teman-teman.
- **Siapa pun yang punya link bisa membuka game**. Matikan tunnel setelah selesai main. Kode bot tetap berjalan di sandbox, jadi tidak bisa menyentuh file di laptopmu.
- Quick Tunnel dari Cloudflare ditujukan untuk uji coba, tanpa jaminan selalu tersedia. Untuk main bareng 8 orang sudah cukup. Untuk dipakai terus-menerus, pindah ke VPS ([DEPLOY.md](DEPLOY.md)).
- Room hilang kalau game dimatikan atau di-restart. Bot tiap pemain aman karena tersimpan di browser masing-masing.

## Kalau ada masalah

| Gejala | Solusi |
|---|---|
| "Docker belum berjalan" | Buka Docker Desktop, tunggu sampai siap, lalu jalankan lagi. |
| Link tidak muncul | Cek log (`main-lokal logs`, atau `.lokal/tunnel.log` untuk cara B). Jaringan kantor/kampus kadang memblokir tunnel; coba hotspot HP. |
| `address already in use` / port 8080 dipakai | Cara A: ubah `PORT` di file `.env`. Cara B: `PORT=9000 ./scripts/main-lokal-tanpa-docker.sh`. |
| Teman melihat "Menyambung ulang…" terus | Biasanya koneksi internet laptop putus-nyambung. Pastikan laptop tidak sleep. |
| Windows: script `.bat` langsung tertutup | Jalankan dari PowerShell supaya pesan error terlihat: `powershell -ExecutionPolicy Bypass -File scripts\main-lokal.ps1` |

## Alternatif tunnel lain

Semua alternatif ini cukup diarahkan ke `http://127.0.0.1:8080`:

- **ngrok**: daftar gratis di https://ngrok.com, lalu `ngrok http 8080`.
- **Tailscale Funnel**: cocok kalau kamu sudah pakai Tailscale.
- **localhost.run**: tanpa instalasi, cukup SSH: `ssh -R 80:localhost:8080 nokey@localhost.run`.
