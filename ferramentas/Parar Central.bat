@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Solicitando parada da Central CPJ...
python "%~dp0central-daemon.py" parar
echo.
pause
