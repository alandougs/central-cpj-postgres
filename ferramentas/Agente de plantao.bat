@echo off
title Agente de plantao - Central CPJ
cd /d "%~dp0.."
echo Agente de plantao automatico da Central CPJ
echo   1 = Codex (usa sua conta ChatGPT ja logada)
echo   2 = Claude Code (requer login: Sistema - Entrar no Claude)
choice /C 12 /M "Qual agente"
if errorlevel 2 (set TIPO=claude& set NOME=Claude-Auto) else (set TIPO=codex& set NOME=Codex-Auto)
python ferramentas\agente-plantao.py executar --agente %NOME% --tipo %TIPO%
if errorlevel 2 (
  echo.
  echo Se o agente ainda nao foi aprovado, rode no computador da Central:
  echo   python ferramentas\agente-plantao.py aprovar %NOME%
)
pause
