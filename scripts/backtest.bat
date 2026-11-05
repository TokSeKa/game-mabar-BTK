@echo off
rem Jalankan backtest dari terminal lewat Docker. Contoh:
rem   scripts\backtest.bat daftar
rem   scripts\backtest.bat jalankan contoh_ema_cross --set mulai=2023-01-01 --param cepat=10
cd /d "%~dp0.."
docker compose -f docker-compose.yml build --quiet suitbot >nul 2>&1
if "%~1"=="" (
  docker compose -f docker-compose.yml run --rm --no-deps suitbot python -m app.backtest daftar
  pause
  exit /b
)
docker compose -f docker-compose.yml run --rm --no-deps suitbot python -m app.backtest %*
