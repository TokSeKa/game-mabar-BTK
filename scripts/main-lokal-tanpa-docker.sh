#!/usr/bin/env bash
# Jalankan Suit Bot Arena di laptop TANPA Docker (Mac / Linux / WSL), lalu buka lewat Cloudflare Quick Tunnel.
# Butuh: Python 3.10+, Node 18+ (hanya untuk build pertama), dan cloudflared.
#
#   ./scripts/main-lokal-tanpa-docker.sh          jalankan (Ctrl+C untuk berhenti)
#   PORT=9000 ./scripts/main-lokal-tanpa-docker.sh
#   TUNNEL=0 ./scripts/main-lokal-tanpa-docker.sh  tanpa tunnel (hanya laptop / Wi-Fi yang sama)
#   REBUILD=1 ./scripts/main-lokal-tanpa-docker.sh build ulang frontend
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PORT=${PORT:-8080}
LOGDIR="$ROOT/.lokal"
mkdir -p "$LOGDIR"

butuh() { command -v "$1" >/dev/null 2>&1; }

if ! butuh python3; then echo "Python 3 belum terpasang: https://www.python.org/downloads/" >&2; exit 1; fi

# 1. frontend
if [ ! -f frontend/dist/index.html ] || [ "${REBUILD:-0}" = "1" ]; then
  if ! butuh npm; then echo "Node.js belum terpasang (dibutuhkan untuk build pertama): https://nodejs.org/" >&2; exit 1; fi
  echo "==> Build frontend (sekali saja)…"
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
fi

# 2. backend
if [ ! -x backend/.venv/bin/uvicorn ]; then
  echo "==> Menyiapkan Python venv…"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q --disable-pip-version-check -r backend/requirements.txt
fi

pids=()
berhenti() {
  echo
  echo "==> Mematikan game…"
  for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap berhenti EXIT INT TERM

BIND=127.0.0.1
[ "${TUNNEL:-1}" = "0" ] && BIND=0.0.0.0
echo "==> Menyalakan server di http://127.0.0.1:${PORT}"
(cd backend && exec .venv/bin/uvicorn app.main:app --host "$BIND" --port "$PORT" --workers 1) > "$LOGDIR/server.log" 2>&1 &
pids+=($!)

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1 && break
  sleep 1
done
if ! curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
  echo "Server gagal menyala. Log:" >&2; tail -20 "$LOGDIR/server.log" >&2; exit 1
fi

if [ "${TUNNEL:-1}" = "0" ]; then
  IP=$( (hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || true) | awk '{print $1}')
  echo
  echo "  Game jalan tanpa tunnel."
  echo "  - Di laptop ini:            http://127.0.0.1:${PORT}"
  [ -n "$IP" ] && echo "  - Teman di Wi-Fi yang sama: http://${IP}:${PORT}"
  echo "  Tekan Ctrl+C untuk berhenti."
  wait
  exit 0
fi

if ! butuh cloudflared; then
  cat >&2 <<MSG

cloudflared belum terpasang, jadi game hanya bisa dibuka di laptop ini: http://127.0.0.1:${PORT}
Pasang cloudflared lalu jalankan lagi:
  Mac:    brew install cloudflared
  Linux:  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
Tekan Ctrl+C untuk berhenti.
MSG
  wait
  exit 0
fi

echo "==> Membuka tunnel Cloudflare…"
cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}" > "$LOGDIR/tunnel.log" 2>&1 &
pids+=($!)

url=""
for _ in $(seq 1 60); do
  url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOGDIR/tunnel.log" | tail -n 1 || true)
  [ -n "$url" ] && break
  sleep 1
done
if [ -z "$url" ]; then
  echo "Link tunnel belum muncul. Lihat $LOGDIR/tunnel.log" >&2
  echo "Game tetap bisa dibuka di laptop ini: http://127.0.0.1:${PORT}" >&2
else
  cat <<MSG

  Game siap!  Buka dan bagikan link ini ke teman-temanmu:

      $url

  - Kamu juga buka lewat link di atas (bukan localhost) supaya link undangan room benar.
  - Laptop harus tetap menyala dan tersambung internet selama main.
  - Tekan Ctrl+C untuk berhenti. Log ada di folder .lokal/

MSG
  if butuh open; then open "$url" >/dev/null 2>&1 || true
  elif butuh xdg-open; then xdg-open "$url" >/dev/null 2>&1 || true
  fi
fi
wait
