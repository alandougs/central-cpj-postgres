#!/bin/sh
set -eu

mkdir -p "$CPJ_WORKSPACE"/{casos,config,consulta,referencias,producao,rag,modelos,exportacoes}
if [ ! -d "$CPJ_WORKSPACE/casos/_MODELO-CASO" ]; then
	cp -R /app/casos/_MODELO-CASO "$CPJ_WORKSPACE/casos/_MODELO-CASO"
fi
exec python /app/plugin/investigacao-cpj/app/servidor.py --porta "${CPJ_PORT:-8765}" --host "${CPJ_HOST:-0.0.0.0}" --sem-navegador
