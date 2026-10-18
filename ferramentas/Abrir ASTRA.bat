@echo off
chcp 65001 >nul
set "RAIZ=%~dp0.."
set "URL=http://127.0.0.1:8765"
set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"

curl -s -m 2 -o nul "%URL%" && goto abrir

echo Iniciando a Central CPJ (ASTRA)...
start "Central CPJ" /min "%RAIZ%\Central CPJ.bat"

set /a TENT=0
:esperar
set /a TENT+=1
if %TENT% gtr 30 (
  echo A Central nao respondeu em 30 segundos. Verifique a janela "Central CPJ".
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
curl -s -m 2 -o nul "%URL%" || goto esperar

:abrir
if exist "%CHROME%" (
  start "" "%CHROME%" "%URL%"
) else (
  start "" "%URL%"
)
