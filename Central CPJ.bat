@echo off
title Central CPJ
chcp 65001 >nul
cd /d "%~dp0"
set "CPJ_WORKSPACE=%~dp0."
set "CPJ_WORKSPACES="
set "CPJ_PYTHON=python"
if exist "%~dp0.venv\Scripts\python.exe" set "CPJ_PYTHON=%~dp0.venv\Scripts\python.exe"
if exist "%~dp0.venv\Scripts\python.exe" set "PATH=%~dp0.venv\Scripts;%PATH%"
echo Iniciando a Central CPJ em http://127.0.0.1:8765 ...
echo Mantenha esta janela aberta enquanto usar a Central. Feche-a para encerrar.
"%CPJ_PYTHON%" "%~dp0plugin\investigacao-cpj\app\servidor.py"
if errorlevel 1 (
  echo.
  echo A Central foi encerrada com erro. Se a porta 8765 ja estiver em uso, a Central provavelmente ja esta aberta:
  echo acesse http://127.0.0.1:8765 no navegador.
  pause
)
