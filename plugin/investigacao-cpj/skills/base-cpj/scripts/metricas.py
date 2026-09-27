#!/usr/bin/env python3
"""Métricas de QUALIDADE do fluxo (somente leitura, sem nomes de pessoas):
  - versões de minuta até o FINAL (por caso entregue);
  - achados do revisor por classificação (primeira revisão de cada caso = qualidade da minuta inicial);
  - tempo por etapa do caso (dias entre as datas registradas no caso.json);
  - tempo por tarefa de IA (espera na fila e execução, por ação; taxa de conclusão).

Uso: metricas.py            -> grava producao\\metricas.json e mostra o resumo
     metricas.py --json     -> só imprime o JSON
O gerar_painel.py importa calcular() e exibe as métricas na seção "Qualidade do fluxo".
"""
import datetime, glob, json, os, re, sqlite3, sys

ETAPAS = ["recebido", "extraido", "em_analise", "analisado", "minuta", "entregue"]
CLASSES = ["sustentada", "parcial", "nao_localizada", "contraditoria"]
_RX_CLASSE = {
    "sustentada": r"(\d+)\s+sustentad",
    "parcial": r"(\d+)\s+parcia",
    "nao_localizada": r"(\d+)\s+n[ãa]o\s+localizad",
    "contraditoria": r"(\d+)\s+contradit[óo]ri",
}


def _data(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError): return None


def _dt(s):
    try: return datetime.datetime.fromisoformat(str(s))
    except (TypeError, ValueError): return None


def _versao(nome):
    m = re.search(r"-v(\d+)\.", nome, re.I)
    return int(m.group(1)) if m else None


def ler_revisao(caminho):
    """Contagens do 'Resultado:' de revisao-vNN.md, ou None se não houver linha reconhecível."""
    try: txt = open(caminho, encoding="utf-8-sig", errors="replace").read()
    except OSError: return None
    linha = next((l for l in txt.splitlines() if re.match(r"\s*\**\s*resultado\s*\**\s*:", l, re.I)), None)
    if not linha: return None
    linha = linha.lower()
    cont = {k: int(m.group(1)) if (m := re.search(rx, linha)) else 0 for k, rx in _RX_CLASSE.items()}
    return cont if sum(cont.values()) else None


def metricas_caso(pasta):
    """Linha anônima de um caso: id, datas-chave, versões, primeira revisão e dias por etapa."""
    try: c = json.load(open(os.path.join(pasta, "caso.json"), encoding="utf-8"))
    except (OSError, ValueError): return None
    datas = c.get("datas") or {}
    rel = os.path.join(pasta, "03-relatorios")
    arqs = os.listdir(rel) if os.path.isdir(rel) else []
    minutas = sorted({v for a in arqs if a.lower().startswith("minuta-") and a.lower().endswith(".md") and (v := _versao(a))})
    revisoes = sorted((v, a) for a in arqs if a.lower().startswith("revisao-") and a.lower().endswith(".md") and (v := _versao(a)))
    registrada = next((r.get("versoes") for r in reversed(c.get("relatorios") or []) if r.get("versoes")), None)
    versoes = registrada or (len(minutas) or None)
    primeira = None
    for _, a in revisoes:
        primeira = ler_revisao(os.path.join(rel, a))
        if primeira: break
    etapas, anterior = {}, None
    for e in ETAPAS:
        d = _data(datas.get(e))
        if d is None: continue
        if anterior is not None and d >= anterior: etapas[e] = (d - anterior).days
        anterior = d
    return {"id": c.get("id") or os.path.basename(pasta), "status": c.get("status"),
            "recebido": datas.get("recebido"), "entregue": datas.get("entregue") if c.get("status") == "entregue" else None,
            "versoes": versoes, "minutas": len(minutas), "revisao": primeira, "etapas": etapas,
            "datas_etapas": {e: datas.get(e) for e in etapas}}


def metricas_ia(ws):
    """Pedidos de IA do plantão (config\\plantao.sqlite), sem solicitante nem nome de agente."""
    p = os.path.join(ws, "config", "plantao.sqlite")
    if not os.path.isfile(p): return []
    try:
        db = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
        try: linhas = db.execute("SELECT acao, estado, tentativas, criado_em, iniciado_em, fim FROM pedidos").fetchall()
        finally: db.close()
    except sqlite3.Error:
        return []
    out = []
    for acao, estado, tent, criado, ini, fim in linhas:
        c, i, f = _dt(criado), _dt(ini), _dt(fim)
        out.append({"acao": acao, "estado": estado, "tentativas": tent or 0, "criado": (criado or "")[:10],
                    "espera_min": round((i - c).total_seconds() / 60, 1) if c and i and i >= c else None,
                    "execucao_min": round((f - i).total_seconds() / 60, 1) if i and f and f >= i and estado == "concluida" else None})
    return out


def calcular(ws):
    casos = []
    for pasta in sorted(glob.glob(os.path.join(ws, "casos", "*"))):
        if os.path.basename(pasta).startswith("_") or not os.path.isdir(pasta): continue
        m = metricas_caso(pasta)
        if m: casos.append(m)
    return {"gerado": datetime.datetime.now().isoformat(timespec="seconds"), "casos": casos, "ia": metricas_ia(ws)}


def _mediana(v):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    n = len(v) // 2
    return v[n] if len(v) % 2 else (v[n - 1] + v[n]) / 2


def resumo(m):
    ent = [c for c in m["casos"] if c["entregue"]]
    vers = [c["versoes"] for c in ent if c["versoes"]]
    rev = {k: sum((c["revisao"] or {}).get(k, 0) for c in m["casos"]) for k in CLASSES}
    linhas = [f"Casos: {len(m['casos'])} · entregues: {len(ent)}",
              f"Versões até o FINAL: mediana {_mediana(vers)} ({len(vers)} caso(s) com versões)",
              "1ª revisão: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in rev.items())]
    for e in ETAPAS[1:]:
        md = _mediana([c["etapas"].get(e) for c in m["casos"]])
        if md is not None: linhas.append(f"Até {e}: mediana {md} dia(s)")
    por = {}
    for p in m["ia"]: por.setdefault(p["acao"], []).append(p)
    for a, ps in sorted(por.items()):
        linhas.append(f"IA {a}: {len(ps)} pedido(s), espera mediana {_mediana([p['espera_min'] for p in ps])} min, "
                      f"execução mediana {_mediana([p['execucao_min'] for p in ps])} min")
    return "\n".join(linhas)


if __name__ == "__main__":
    WS = os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO")
    m = calcular(WS)
    if "--json" in sys.argv:
        print(json.dumps(m, ensure_ascii=False, indent=1)); raise SystemExit
    prod = os.path.join(WS, "producao"); os.makedirs(prod, exist_ok=True)
    tmp = os.path.join(prod, "metricas.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f: json.dump(m, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(prod, "metricas.json"))
    print(resumo(m))
