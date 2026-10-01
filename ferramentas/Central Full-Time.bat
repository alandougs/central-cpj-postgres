@echo off
chcp 65001 >nul
title Central CPJ — Iniciar Full-Time 24/7

cd /d "%~dp0.."
echo Iniciando Central CPJ em segundo plano (Full-Time 24/7)...
wscript.exe "%~dp0iniciar-central-24-7.vbs"

timeout /t 3 /nobreak >nul
python "%~dp0central-daemon.py" status

echo.
echo Para verificar o status a qualquer momento: ferramentas\Status Central.bat
echo Para parar a Central: ferramentas\Parar Central.bat
echo.
pause
