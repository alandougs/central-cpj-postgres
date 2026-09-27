@echo off
chcp 65001 >nul
title Teste de velocidade do SSD
cd /d "%~dp0.."
set "DESTINO=%~1"
if "%DESTINO%"=="" set /p "DESTINO=Informe a letra ou pasta do SSD (ex.: E:\): "
if "%DESTINO%"=="" exit /b 1
echo.
python "%~dp0testar-velocidade-ssd.py" "%DESTINO%" --gb 1
echo.
pause
