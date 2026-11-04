#!/usr/bin/env bash
# Update Suit Bot Arena ke versi terbaru dari git, build ulang, lalu cek health.
set -euo pipefail
cd "$(dirname "$0")/.."

PORT=$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 || true)
PORT=${PORT:-8080}

echo "==> git pull"
git pull --ff-only

echo "==> build & restart"
docker compose up -d --build

echo "==> menunggu server siap di port $PORT"
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "OK: $(curl -fsS "http://127.0.0.1:${PORT}/api/health")"
    docker image prune -f >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 2
done
echo "Server belum merespons. Cek log: docker compose logs --tail 100" >&2
exit 1
