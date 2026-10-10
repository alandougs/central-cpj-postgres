@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "CPJ_WORKSPACE=%~dp0.."
set "CPJ_WORKSPACES="
set "CPJ_PYTHON=python"
if exist "%~dp0..\.venv\Scripts\python.exe" set "CPJ_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%~dp0..\.venv\Scripts\python.exe" set "PATH=%~dp0..\.venv\Scripts;%PATH%"
"%CPJ_PYTHON%" "%~dp0central-daemon.py" status
echo.
pause
