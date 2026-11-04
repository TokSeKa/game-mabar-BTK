# Jalankan Suit Bot Arena di laptop Windows + buka ke internet lewat Cloudflare Quick Tunnel.
#   scripts\main-lokal.bat          nyalakan & tampilkan link (bisa diklik dua kali)
#   scripts\main-lokal.bat link     tampilkan link lagi
#   scripts\main-lokal.bat logs     lihat log
#   scripts\main-lokal.bat stop     matikan
param([string]$Perintah = "start")

# Jangan pakai "Stop". Docker menulis pesan biasa (progress build, peringatan plugin) ke stderr,
# dan Windows PowerShell 5.1 menganggap itu error lalu menghentikan script.
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")
$F = "-f docker-compose.yml -f docker-compose.tunnel.yml"

# Semua perintah docker dijalankan lewat cmd, supaya stderr dibaca sebagai teks biasa.
function Jalankan-Docker([string]$argumen) {
  cmd /c "docker $argumen 2>&1"
}

function Cari-Link {
  $log = Jalankan-Docker "compose $F logs --no-log-prefix tunnel" | Out-String
  $m = [regex]::Matches($log, 'https://[a-z0-9-]+\.trycloudflare\.com')
  if ($m.Count -gt 0) { return $m[$m.Count - 1].Value }
  return $null
}

switch ($Perintah) {
  "stop" { Jalankan-Docker "compose $F down"; Write-Host "Game dan tunnel sudah dimatikan."; exit 0 }
  "logs" { cmd /c "docker compose $F logs -f --tail 100"; exit 0 }
  "link" {
    $u = Cari-Link
    if ($u) { Write-Host $u } else { Write-Host "Link belum ada. Jalankan dulu main-lokal.bat" }
    exit 0
  }
  "start" { }
  default { Write-Host "Pemakaian: main-lokal.bat [start|link|logs|stop]"; exit 1 }
}

Write-Host "==> [1/4] Mengecek Docker..."
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker belum terpasang. Pasang Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
  exit 1
}
cmd /c "docker info >nul 2>&1"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker belum berjalan. Buka aplikasi Docker Desktop, tunggu sampai tulisannya 'Engine running', lalu jalankan lagi." -ForegroundColor Red
  exit 1
}
Write-Host "    Docker OK."

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host "==> [2/4] Menyiapkan game. Pertama kali bisa 3-10 menit (mengunduh dan build), berikutnya cepat..."
if ($env:BUILD -eq "0") { Jalankan-Docker "compose $F up -d" } else { Jalankan-Docker "compose $F up -d --build" }
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Gagal menyalakan game. Lihat pesan di atas (biasanya baris paling bawah)." -ForegroundColor Red
  exit 1
}

Write-Host "==> [3/4] Menunggu link dari Cloudflare (biasanya 10-30 detik)..."
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) { Start-Sleep -Seconds 2; $url = Cari-Link }

if (-not $url) {
  Write-Host "Link tunnel belum muncul. Cek log: scripts\main-lokal.bat logs" -ForegroundColor Yellow
  Write-Host "Game tetap bisa dibuka di laptop ini: http://127.0.0.1:8080"
  exit 1
}

Write-Host "==> [4/4] Selesai!"
Write-Host ""
Write-Host "  Game siap!  Buka dan bagikan link ini ke teman-temanmu:" -ForegroundColor Green
Write-Host ""
Write-Host "      $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "  - Kamu juga buka lewat link di atas (bukan localhost) supaya link undangan room benar."
Write-Host "  - Link berubah setiap kali tunnel dinyalakan ulang. Lihat lagi: scripts\main-lokal.bat link"
Write-Host "  - Laptop harus tetap menyala dan tersambung internet selama main."
Write-Host "  - Jendela ini boleh ditutup; game tetap jalan selama Docker Desktop menyala."
Write-Host "  - Matikan dengan: scripts\main-lokal.bat stop"
Write-Host ""
Start-Process $url
