@echo off
chcp 65001 >nul
title Central CPJ — Iniciar Full-Time 24/7

cd /d "%~dp0.."
set "CPJ_WORKSPACE=%~dp0.."
set "CPJ_WORKSPACES="
set "CPJ_PYTHON=python"
if exist "%~dp0..\.venv\Scripts\python.exe" set "CPJ_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%~dp0..\.venv\Scripts\python.exe" set "PATH=%~dp0..\.venv\Scripts;%PATH%"
echo Iniciando Central CPJ em segundo plano (Full-Time 24/7)...
wscript.exe "%~dp0iniciar-central-24-7.vbs"

timeout /t 3 /nobreak >nul
"%CPJ_PYTHON%" "%~dp0central-daemon.py" status

echo.
echo Para verificar o status a qualquer momento: ferramentas\Status Central.bat
echo Para parar a Central: ferramentas\Parar Central.bat
echo.
pause
