FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CPJ_WORKSPACE=/workspace \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY plugin/investigacao-cpj/app ./plugin/investigacao-cpj/app
COPY plugin/investigacao-cpj/skills ./plugin/investigacao-cpj/skills
COPY plugin/investigacao-cpj/agents ./plugin/investigacao-cpj/agents
COPY plugin/investigacao-cpj/commands ./plugin/investigacao-cpj/commands
COPY ferramentas ./ferramentas
COPY portatil ./portatil
COPY modelos/dados-padrao.json ./modelos/dados-padrao.json
COPY deploy/entrypoint.sh ./deploy/entrypoint.sh
RUN chmod +x ./deploy/entrypoint.sh \
    && mkdir -p /workspace/casos /workspace/config /workspace/consulta /workspace/referencias /workspace/producao /workspace/rag /workspace/modelos /workspace/exportacoes

EXPOSE 8765
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
