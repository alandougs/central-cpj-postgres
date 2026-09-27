@echo off
cd /d "%~dp0.."
python ferramentas\configurar-codex.py --instalar-usuario
if errorlevel 1 (
    echo Falha ao configurar as skills CPJ.
) else (
    echo Skills configuradas. Se nao aparecerem, reinicie o Codex.
)
pause
