#!/usr/bin/env python3
"""Embeddings locais para a busca híbrida do RAG.

Roda 100% local (ONNX via fastembed); a rede é usada uma única vez para baixar o
modelo para `rag/modelos/`. Nenhum conteúdo de caso sai do computador.

O vetor é gravado em `trechos.embedding` (um por trecho, mesma granularidade do
FTS). Como o modelo trunca em 128 tokens e um trecho de transcrição é uma página
inteira, o texto é dividido em janelas de palavras; a média normalizada das
janelas representa o trecho todo em vez de só o começo dele.

Limite conhecido: `MAX_JANELAS` corta o trecho em 24 janelas (cerca de 2.300
palavras). O que passa disso não entra no vetor, então um trecho muito longo é
representado pelo seu começo. A busca textual (FTS) continua cobrindo o trecho
inteiro, e é ela que garante a recuperação por palavra em qualquer posição.
"""
import os

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384
PALAVRAS_JANELA = 96
MAX_JANELAS = 24

_modelo = None


def ws_padrao():
    v = os.environ.get("CPJ_WORKSPACE")
    if v:
        return v
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))


def cache_dir(ws=None):
    """Pasta do modelo. `CPJ_EMBEDDINGS_CACHE` evita baixar de novo em workspace de teste."""
    v = os.environ.get("CPJ_EMBEDDINGS_CACHE")
    if v:
        return v
    return os.path.join(ws or ws_padrao(), "rag", "modelos")


def disponivel():
    """True se as dependências locais de embedding estão instaladas."""
    try:
        import fastembed  # noqa: F401
        import numpy  # noqa: F401
    except Exception:
        return False
    return True


def modelo(ws=None):
    """Carrega o modelo uma vez por processo."""
    global _modelo
    if _modelo is None:
        from fastembed import TextEmbedding
        destino = cache_dir(ws)
        os.makedirs(destino, exist_ok=True)
        _modelo = TextEmbedding(model_name=MODELO, cache_dir=destino)
    return _modelo


def janelas(texto, palavras=PALAVRAS_JANELA, maximo=MAX_JANELAS):
    """Divide o texto em janelas de palavras, limitando o custo por trecho."""
    partes = (texto or "").split()
    if not partes:
        return []
    saida = [" ".join(partes[i:i + palavras]) for i in range(0, len(partes), palavras)]
    return saida[:maximo]


def empacotar(vetor):
    """float32 contíguo, pronto para gravar como BLOB."""
    import numpy as np
    return np.asarray(vetor, dtype="float32").tobytes()


def desempacotar(blob):
    import numpy as np
    return np.frombuffer(blob, dtype="float32")


def _normalizar(v):
    import numpy as np
    n = float(np.linalg.norm(v))
    return v / n if n else v


def vetores(textos, ws=None, lote=64):
    """Um BLOB por texto, na mesma ordem. Texto vazio devolve None."""
    import numpy as np
    m = modelo(ws)
    pedidos, indice = [], []
    for i, t in enumerate(textos):
        for j in janelas(t):
            pedidos.append(j)
            indice.append(i)
    saida = [None] * len(textos)
    if not pedidos:
        return saida
    acumulado = {}
    for pos, emb in enumerate(m.embed(pedidos, batch_size=lote)):
        i = indice[pos]
        v = np.asarray(emb, dtype="float32")
        acumulado[i] = v if i not in acumulado else acumulado[i] + v
    for i, v in acumulado.items():
        saida[i] = empacotar(_normalizar(v))
    return saida


def vetor(texto, ws=None):
    """BLOB de um texto só."""
    return vetores([texto], ws=ws)[0]


def similaridade(a, b):
    """Cosseno entre dois BLOBs já normalizados."""
    import numpy as np
    va, vb = desempacotar(a), desempacotar(b)
    if va.size != vb.size or not va.size:
        return 0.0
    return float(np.dot(_normalizar(va), _normalizar(vb)))
