@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python "%~dp0central-daemon.py" status
echo.
pause
