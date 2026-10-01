@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publicar-github.ps1"
if errorlevel 1 goto fim
choice /M "Enviar essas alteracoes ao GitHub"
if errorlevel 2 goto fim
set /p MSG=Descricao da alteracao: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publicar-github.ps1" -Enviar -Mensagem "%MSG%"
:fim
pause
