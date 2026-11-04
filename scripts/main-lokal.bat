@echo off
rem Klik dua kali untuk menyalakan Suit Bot Arena + tunnel. Lihat scripts\main-lokal.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0main-lokal.ps1" %*
if "%~1"=="" pause
