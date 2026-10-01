@echo off
set /p DESTINO=Pasta de destino do backup (ex.: E:\Backup): 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup.ps1" -Destino "%DESTINO%"
pause
