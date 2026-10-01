@echo off
title Backup Central CPJ para SSD
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup-para-ssd.ps1"
echo.
pause
