#!/usr/bin/env bash
# Unduh data pasar untuk Kilas Pasar (lewat Docker). Data disimpan di volume Docker "pasar-data",
# jadi server yang sedang berjalan langsung bisa memakainya (cukup muat ulang halaman).
#
#   ./scripts/unduh-data.sh cepat     30 saham IDX, 20 saham US, lalu 5 kripto (1m sejak 2024-07)   (beberapa menit)
#   ./scripts/unduh-data.sh penuh     ±140 saham IDX, ±90 saham US, lalu ±65 kripto 1m sejak 2017   (beberapa jam, puluhan GB)
#   ./scripts/unduh-data.sh saham     saham IDX + US saja (preset cepat; "saham-penuh" untuk semua saham)
#   ./scripts/unduh-data.sh update    lengkapi semua aset yang sudah ada dengan data terbaru (jalankan rutin)
#   ./scripts/unduh-data.sh funding   riwayat funding rate futures untuk kripto yang sudah ada
#   ./scripts/unduh-data.sh contoh    data buatan untuk mencoba tanpa internet
#   ./scripts/unduh-data.sh status    lihat jumlah candle & ukuran data
#   ./scripts/unduh-data.sh kripto --simbol BTCUSDT,DOGEUSDT --mulai 2021-01   (argumen bebas)
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker belum terpasang atau belum berjalan. Buka Docker Desktop dulu." >&2
  exit 1
fi
[ -f .env ] || cp .env.example .env

case "${1:-cepat}" in
  cepat)  args=(semua --preset cepat) ;;
  penuh)
    echo "Preset penuh mengunduh puluhan GB dan butuh beberapa jam. Bisa dihentikan (Ctrl+C) dan dilanjutkan kapan saja."
    args=(semua --preset penuh) ;;
  saham)  args=(saham --preset cepat) ;;
  saham-penuh) args=(saham --preset penuh) ;;
  funding) args=(funding) ;;
  update) args=(update) ;;
  contoh) args=(contoh) ;;
  status) args=(status) ;;
  *)      args=("$@") ;;
esac

if [ "${1:-cepat}" != "status" ]; then
  jalan=$(docker ps --filter "label=com.docker.compose.oneoff=True" --filter "label=com.docker.compose.service=suitbot" --format "{{.ID}} {{.Names}} (mulai {{.RunningFor}})" 2>/dev/null || true)
  if [ -n "$jalan" ]; then
    echo "Ada unduhan lain yang masih berjalan di Docker:"
    echo "$jalan" | sed 's/^[^ ]* /  /'
    read -r -p "Hentikan unduhan itu lalu lanjut? (y/N) " j
    case "$j" in
      [yY]*) echo "$jalan" | awk '{print $1}' | xargs -r docker stop >/dev/null ;;
      *) echo "Oke, biarkan selesai dulu."; exit 1 ;;
    esac
  fi
fi

echo "==> Menyiapkan image dengan kode terbaru..."
docker compose -f docker-compose.yml build suitbot || echo "Build gagal; memakai image yang sudah ada." >&2
exec docker compose -f docker-compose.yml run --rm --no-deps suitbot python -m app.trading.unduh "${args[@]}"
