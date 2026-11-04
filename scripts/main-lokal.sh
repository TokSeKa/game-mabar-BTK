#!/usr/bin/env bash
# Jalankan Suit Bot Arena di laptop + buka ke internet lewat Cloudflare Quick Tunnel.
#
#   ./scripts/main-lokal.sh          nyalakan & tampilkan link
#   ./scripts/main-lokal.sh link     tampilkan link lagi
#   ./scripts/main-lokal.sh logs     lihat log
#   ./scripts/main-lokal.sh stop     matikan
#
# BUILD=0 ./scripts/main-lokal.sh   lewati build ulang image
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.tunnel.yml)

cari_link() {
  "${COMPOSE[@]}" logs --no-log-prefix tunnel 2>/dev/null \
    | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -n 1 || true
}

case "${1:-start}" in
  stop)
    "${COMPOSE[@]}" down
    echo "Game dan tunnel sudah dimatikan."
    exit 0 ;;
  logs)
    exec "${COMPOSE[@]}" logs -f --tail 100 ;;
  link)
    url=$(cari_link)
    if [ -n "$url" ]; then echo "$url"; else echo "Link belum ada. Jalankan dulu: $0" >&2; exit 1; fi
    exit 0 ;;
  start) ;;
  *)
    echo "Pemakaian: $0 [start|link|logs|stop]" >&2; exit 1 ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker belum terpasang. Pasang Docker Desktop: https://www.docker.com/products/docker-desktop/" >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker belum berjalan. Buka Docker Desktop dulu, tunggu sampai siap, lalu jalankan lagi." >&2
  exit 1
fi
[ -f .env ] || cp .env.example .env

echo "==> Menyalakan game (build pertama bisa beberapa menit)…"
if [ "${BUILD:-1}" = "0" ]; then
  "${COMPOSE[@]}" up -d
else
  "${COMPOSE[@]}" up -d --build
fi

echo "==> Menunggu link tunnel dari Cloudflare…"
url=""
for _ in $(seq 1 60); do
  url=$(cari_link)
  [ -n "$url" ] && break
  sleep 2
done

PORT=$(grep -E '^PORT=' .env | cut -d= -f2 || true)
PORT=${PORT:-8080}

if [ -z "$url" ]; then
  echo "Link tunnel belum muncul. Cek log: $0 logs" >&2
  echo "Game tetap bisa dibuka di laptop ini: http://127.0.0.1:${PORT}" >&2
  exit 1
fi

cat <<MSG

  Game siap!  Buka dan bagikan link ini ke teman-temanmu:

      $url

  - Kamu juga buka lewat link di atas (bukan localhost) supaya link undangan room benar.
  - Link berubah setiap kali tunnel dinyalakan ulang. Lihat lagi dengan: $0 link
  - Laptop harus tetap menyala dan tersambung internet selama main.
  - Matikan dengan: $0 stop

MSG

if command -v open >/dev/null 2>&1; then open "$url" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" >/dev/null 2>&1 || true
fi
