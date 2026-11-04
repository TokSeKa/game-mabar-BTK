# Jalankan Suit Bot Arena di laptop Windows + buka ke internet lewat Cloudflare Quick Tunnel.
#   scripts\main-lokal.bat          nyalakan & tampilkan link (bisa diklik dua kali)
#   scripts\main-lokal.bat link     tampilkan link lagi
#   scripts\main-lokal.bat logs     lihat log
#   scripts\main-lokal.bat stop     matikan
param([string]$Perintah = "start")
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$files = @("-f", "docker-compose.yml", "-f", "docker-compose.tunnel.yml")

function Cari-Link {
  $log = (docker compose @files logs --no-log-prefix tunnel 2>$null) | Out-String
  $m = [regex]::Matches($log, 'https://[a-z0-9-]+\.trycloudflare\.com')
  if ($m.Count -gt 0) { return $m[$m.Count - 1].Value }
  return $null
}

switch ($Perintah) {
  "stop" { docker compose @files down; Write-Host "Game dan tunnel sudah dimatikan."; exit 0 }
  "logs" { docker compose @files logs -f --tail 100; exit 0 }
  "link" { $u = Cari-Link; if ($u) { Write-Host $u } else { Write-Host "Link belum ada. Jalankan dulu main-lokal.bat" }; exit 0 }
  "start" { }
  default { Write-Host "Pemakaian: main-lokal.bat [start|link|logs|stop]"; exit 1 }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker belum terpasang. Pasang Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
  exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker belum berjalan. Buka Docker Desktop dulu, tunggu sampai siap, lalu jalankan lagi." -ForegroundColor Red
  exit 1
}
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

Write-Host "==> Menyalakan game (build pertama bisa beberapa menit)..."
if ($env:BUILD -eq "0") { docker compose @files up -d } else { docker compose @files up -d --build }
if ($LASTEXITCODE -ne 0) { Write-Host "Gagal menyalakan game. Lihat pesan error di atas." -ForegroundColor Red; exit 1 }

Write-Host "==> Menunggu link tunnel dari Cloudflare..."
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) { Start-Sleep -Seconds 2; $url = Cari-Link }

if (-not $url) {
  Write-Host "Link tunnel belum muncul. Cek log: scripts\main-lokal.bat logs" -ForegroundColor Yellow
  Write-Host "Game tetap bisa dibuka di laptop ini: http://127.0.0.1:8080"
  exit 1
}

Write-Host ""
Write-Host "  Game siap!  Buka dan bagikan link ini ke teman-temanmu:" -ForegroundColor Green
Write-Host ""
Write-Host "      $url" -ForegroundColor Cyan
Write-Host ""
Write-Host "  - Kamu juga buka lewat link di atas (bukan localhost) supaya link undangan room benar."
Write-Host "  - Link berubah setiap kali tunnel dinyalakan ulang. Lihat lagi: scripts\main-lokal.bat link"
Write-Host "  - Laptop harus tetap menyala dan tersambung internet selama main."
Write-Host "  - Matikan dengan: scripts\main-lokal.bat stop"
Write-Host ""
Start-Process $url
