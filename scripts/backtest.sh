#!/usr/bin/env bash
# Jalankan backtest dari terminal lewat Docker. Contoh:
#   ./scripts/backtest.sh daftar
#   ./scripts/backtest.sh jalankan contoh_ema_cross --set mulai=2023-01-01 --param cepat=10
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker-compose.yml build --quiet suitbot >/dev/null 2>&1 || true
exec docker compose -f docker-compose.yml run --rm --no-deps suitbot python -m app.backtest "${@:-daftar}"
