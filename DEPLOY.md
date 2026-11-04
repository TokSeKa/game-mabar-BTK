# Deploy Suit Bot Arena ke VPS

Panduan ini untuk VPS Linux (Ubuntu/Debian) yang juga menjalankan proyekmu yang lain. Suit Bot Arena berjalan sebagai **satu container Docker** di port lokal (default `127.0.0.1:8080`), lalu dibuka ke internet lewat reverse proxy (Nginx atau Caddy) yang mungkin sudah kamu pakai.

```
Internet ──HTTPS──▶ Nginx / Caddy (port 80/443) ──▶ 127.0.0.1:8080 ──▶ container suit-bot-arena (port 8000)
```

Konfigurasi di folder `deploy/` sudah diuji dengan Nginx, baik di subdomain maupun di sub-path `/suitbot/`, termasuk WebSocket dan sambung ulang.

---

## 0. Yang dibutuhkan

- VPS dengan Docker. RAM 512 MB untuk game ini sudah cukup.
- (Disarankan) domain atau subdomain yang mengarah ke IP VPS, misalnya `suit.domainmu.com`.
- Akses SSH.

## 1. Pasang Docker (lewati kalau sudah ada)

```bash
curl -fsSL https://get.docker.com | sudo sh
```

```bash
sudo usermod -aG docker $USER
```

Logout lalu login lagi, kemudian cek:

```bash
docker compose version
```

## 2. Ambil kode

```bash
cd /opt
```

```bash
sudo git clone https://github.com/TokSeKa/game-mabar-BTK.git suitbot
```

```bash
sudo chown -R $USER:$USER /opt/suitbot && cd /opt/suitbot
```

Kalau kode masih di branch lain (belum di-merge ke `main`), pindah dulu ke branch itu:

```bash
git checkout suit-bot-arena
```

## 3. Atur konfigurasi

```bash
cp .env.example .env
```

```bash
nano .env
```

Yang paling penting:

| Variabel | Default | Keterangan |
|---|---|---|
| `PORT` | `8080` | Port di VPS. Pilih yang belum dipakai proyekmu yang lain. |
| `BIND_ADDRESS` | `127.0.0.1` | Biarkan begini kalau memakai reverse proxy. Ganti `0.0.0.0` hanya kalau ingin langsung diakses lewat `http://IP:PORT`. |
| `MATCH_WORKERS` | `2` | Jumlah proses yang menghitung match secara paralel. |
| `BOT_MAX_STEPS` | `20000` | Batas "langkah berpikir" bot per ronde. |
| `MEM_LIMIT` / `CPUS` | `512m` / `1.0` | Batas sumber daya container, supaya tidak mengganggu proyek lain. |

Cek port yang sudah dipakai:

```bash
sudo ss -ltnp | grep -E ':(8080|8081|8090)\b'
```

## 4. Build dan jalankan

```bash
docker compose up -d --build
```

Build pertama butuh beberapa menit (mengunduh Node dan Python). Cek hasilnya:

```bash
docker compose ps
```

```bash
curl -s http://127.0.0.1:8080/api/health
```

Hasilnya harus seperti `{"ok":true,"rooms":0}`. Container otomatis menyala lagi setelah VPS reboot (`restart: unless-stopped`).

> **Kalau build gagal dengan `429 Too Many Requests` dari Docker Hub**, pakai mirror:
> ```bash
> docker compose build --build-arg NODE_IMAGE=mirror.gcr.io/library/node:20-alpine --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.12-slim
> ```
> lalu jalankan `docker compose up -d`.

### 4b. Data pasar untuk Kilas Pasar

Unduh data candle ke volume Docker `pasar-data`. Server yang sedang berjalan langsung membaca data baru tanpa perlu restart.

```bash
./scripts/unduh-data.sh cepat
```

Untuk data lengkap (±65 kripto 1 menit sejak 2017 + ±230 saham, puluhan GB, beberapa jam), jalankan di dalam `tmux` atau `screen` supaya tidak terputus saat SSH ditutup:

```bash
tmux new -s data './scripts/unduh-data.sh penuh'
```

Unduhan yang terhenti bisa dijalankan ulang dan akan melanjutkan dari bagian yang belum ada. Cek hasilnya:

```bash
./scripts/unduh-data.sh status
```

Supaya data selalu baru dan riwayat intraday saham makin panjang, pasang update otomatis setiap hari lewat `crontab -e`. Contoh berikut berjalan pukul 01:17:

```bash
17 1 * * * cd /opt/suitbot && ./scripts/unduh-data.sh update >> /var/log/kilas-update.log 2>&1
```

Catatan:
- Pengunduh butuh RAM sekitar 1,5 GB saat memproses kripto besar (BTC/ETH), jadi `MEM_LIMIT` default di `.env` adalah `2g`.
- Pastikan disk VPS cukup untuk preset penuh. Cek dengan `df -h`.
- Kalau ingin data disimpan di folder biasa, set `PASAR_DATA=./data` di `.env`, lalu jalankan `sudo chown -R 10001:10001 ./data`.

## 5. Buka ke internet lewat reverse proxy

Pilih **satu** cara yang cocok dengan VPS-mu.

### A. Nginx + subdomain (misalnya `suit.domainmu.com`)

1. Buat DNS record **A** `suit` yang mengarah ke IP VPS.
2. Salin contoh config dan ganti nama domain:

```bash
sudo cp deploy/nginx-subdomain.conf.example /etc/nginx/sites-available/suitbot
```

```bash
sudo nano /etc/nginx/sites-available/suitbot
```

3. Aktifkan, cek, lalu reload:

```bash
sudo ln -s /etc/nginx/sites-available/suitbot /etc/nginx/sites-enabled/suitbot
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

> Kalau `nginx -t` mengeluh `duplicate "map"` / `$connection_upgrade`, berarti proyekmu yang lain sudah punya blok `map` yang sama. Hapus blok `map` dari file `suitbot`.

4. Pasang HTTPS (gratis, Let's Encrypt):

```bash
sudo apt install -y certbot python3-certbot-nginx
```

```bash
sudo certbot --nginx -d suit.domainmu.com
```

### B. Nginx + sub-path (misalnya `domainmu.com/suitbot/`)

Cocok kalau tidak ingin membuat subdomain baru. Buka `deploy/nginx-subpath.conf.example`:

- tempel blok `map` di level `http` (sekali saja; lewati kalau sudah ada),
- tempel dua blok `location` ke dalam `server { ... }` domain yang sudah ada,
- lalu `sudo nginx -t && sudo systemctl reload nginx`.

Game akan terbuka di `https://domainmu.com/suitbot/`. Semua link dan WebSocket di game memakai alamat relatif, jadi tidak perlu build ulang.

### C. Caddy

Caddy mengurus HTTPS dan WebSocket otomatis. Lihat `deploy/Caddyfile.example`, tambahkan bloknya ke `/etc/caddy/Caddyfile`, lalu:

```bash
sudo systemctl reload caddy
```

### D. Tanpa domain (cepat untuk coba-coba)

Di `.env` set `BIND_ADDRESS=0.0.0.0`, jalankan `docker compose up -d`, buka port-nya di firewall, lalu akses `http://IP-VPS:8080`. Tanpa HTTPS. Jangan dipakai lama-lama.

## 6. Firewall

Kalau memakai `ufw`, cukup buka HTTP/HTTPS. Port 8080 tidak perlu dibuka karena hanya diakses Nginx/Caddy dari dalam VPS.

```bash
sudo ufw allow 'Nginx Full'
```

## 7. Update ke versi terbaru

```bash
./deploy/update.sh
```

Script itu menjalankan `git pull`, build ulang, menyalakan ulang container, lalu mengecek health. Catatan: **room yang sedang berjalan hilang saat restart**, karena semua data room disimpan di memori. Update saat tidak ada yang sedang main. Bot tiap pemain tetap aman karena tersimpan di browser masing-masing.

## 8. Perintah yang sering dipakai

| Keperluan | Perintah |
|---|---|
| Lihat log | `docker compose logs -f --tail 100` |
| Restart | `docker compose restart` |
| Stop | `docker compose down` |
| Status & health | `docker compose ps` |
| Pemakaian CPU/RAM | `docker stats suit-bot-arena` |

## 9. Kalau ada masalah

| Gejala | Penyebab & solusi |
|---|---|
| Di game muncul "Menyambung ulang…" terus | WebSocket diblok proxy. Pastikan ada `proxy_http_version 1.1` dan header `Upgrade`/`Connection` seperti di contoh, lalu reload Nginx. |
| 502 Bad Gateway | Container mati atau port salah. Cek `docker compose ps` dan pastikan `PORT` di `.env` sama dengan `proxy_pass`. |
| Halaman putih di sub-path | Pastikan URL diakhiri `/` (`/suitbot/`) dan `proxy_pass` diakhiri `/`. |
| Pemain terputus setiap ±60 detik | `proxy_read_timeout` terlalu kecil. Pakai `3600s` seperti contoh. Game juga mengirim ping setiap 25 detik. |
| Match terasa lambat | Naikkan `MATCH_WORKERS` dan `CPUS`, atau turunkan `BOT_MAX_STEPS`. |
| `address already in use` | Port dipakai proyek lain. Ganti `PORT` di `.env`, lalu sesuaikan `proxy_pass`. |

## 10. Catatan teknis

- Server **harus berjalan dengan 1 worker uvicorn** (sudah diatur di Dockerfile) karena state room ada di memori proses. Perhitungan match tetap paralel lewat process pool (`MATCH_WORKERS`).
- Tidak ada database dan tidak ada data pribadi yang disimpan. Nama pemain dan kode bot hanya ada di memori server selama room aktif, ditambah di `localStorage` browser masing-masing pemain.
- Kode bot dijalankan oleh interpreter khusus (bukan `exec`). Kode itu tidak bisa mengakses file, jaringan, atau sistem VPS. Container juga berjalan sebagai user non-root dengan batas RAM dan CPU.
