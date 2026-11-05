# Unduh data pasar untuk Kilas Pasar (lewat Docker) di Windows.
#   scripts\unduh-data.bat            menu pilihan (bisa diklik dua kali)
#   scripts\unduh-data.bat cepat      preset cepat
#   scripts\unduh-data.bat penuh      preset penuh (puluhan GB)
#   scripts\unduh-data.bat saham      saham IDX + US saja (preset cepat)
#   scripts\unduh-data.bat update     lengkapi data yang sudah ada
#   scripts\unduh-data.bat contoh     data buatan tanpa internet
#   scripts\unduh-data.bat status     lihat jumlah data
param([string]$Pilihan = "")
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not $Pilihan) {
  Write-Host ""
  Write-Host "  Unduh data Kilas Pasar" -ForegroundColor Cyan
  Write-Host "  1) Cepat        - 30 saham IDX, 20 saham US, 5 kripto (1 menit sejak 2024-07). Beberapa menit."
  Write-Host "  2) Penuh        - +-140 saham IDX, +-90 saham US, lalu +-65 kripto 1 menit sejak 2017. Beberapa jam, puluhan GB."
  Write-Host "  3) Saham saja   - 30 saham IDX + 20 saham US. Beberapa menit."
  Write-Host "  4) Saham penuh  - +-140 saham IDX + +-90 saham US (tanpa kripto)."
  Write-Host "  5) Update       - lengkapi data yang sudah ada dengan data terbaru"
  Write-Host "  6) Funding rate - riwayat funding futures untuk kripto yang sudah ada (mode Futures)"
  Write-Host "  7) Contoh       - data buatan untuk mencoba tanpa internet"
  Write-Host "  8) Status       - lihat jumlah data yang sudah ada"
  Write-Host ""
  Write-Host "  Saham selalu diunduh lebih dulu, jadi tetap ada walaupun unduhan kripto dihentikan." -ForegroundColor DarkGray
  $c = Read-Host "  Pilih 1-8"
  $Pilihan = @{ "1" = "cepat"; "2" = "penuh"; "3" = "saham"; "4" = "saham-penuh"; "5" = "update"; "6" = "funding"; "7" = "contoh"; "8" = "status" }[$c]
  if (-not $Pilihan) { Write-Host "Pilihan tidak dikenal."; exit 1 }
}

$argumen = switch ($Pilihan) {
  "cepat"  { "semua --preset cepat" }
  "penuh"  { "semua --preset penuh" }
  "saham"  { "saham --preset cepat" }
  "saham-penuh" { "saham --preset penuh" }
  "funding" { "funding" }
  "update" { "update" }
  "contoh" { "contoh" }
  "status" { "status" }
  default  { $Pilihan }
}

cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker belum berjalan. Buka Docker Desktop, tunggu sampai 'Engine running', lalu jalankan lagi." -ForegroundColor Red
  exit 1
}
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
if ($Pilihan -eq "penuh") {
  Write-Host "Preset penuh mengunduh puluhan GB dan butuh beberapa jam. Bisa dihentikan (Ctrl+C) dan dilanjutkan kapan saja." -ForegroundColor Yellow
}
Write-Host "==> Mulai (build image pertama kali bisa beberapa menit)..."
cmd /c "docker compose -f docker-compose.yml run --rm --no-deps suitbot python -m app.trading.unduh $argumen 2>&1"
if ($LASTEXITCODE -eq 0) {
  Write-Host ""
  Write-Host "Selesai. Kalau game sedang jalan, cukup muat ulang halaman Kilas Pasar." -ForegroundColor Green
}
