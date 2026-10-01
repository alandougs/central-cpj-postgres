@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python "%~dp0testar-tudo.py" %*
exit /b %errorlevel%
