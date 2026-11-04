@echo off
rem Klik dua kali untuk mengunduh data pasar Kilas Pasar. Lihat scripts\unduh-data.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0unduh-data.ps1" %*
if "%~1"=="" pause
