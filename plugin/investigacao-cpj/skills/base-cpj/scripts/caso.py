#!/usr/bin/env python3
"""Registro de casos do workspace CPJ (fonte da verdade para estatística, calibração e RAG).
Pasta do caso = número da Ordem de Serviço (ex.: O.S. "123/2026" -> casos\\OS-123-2026).

Uso (CLI):
  caso.py novo --os 123/2026 [--bo TXT] [--ip TXT] [--processo TXT] [--natureza TXT] [--recebido AAAA-MM-DD] [--id ID]
  caso.py status <ID> <status> [--data AAAA-MM-DD]
  caso.py set <ID> chave=valor [chave.sub=valor ...]      (números viram número; a,b,c em listas)
  caso.py ip <ID> <relatorio_extracao.json>                 (registra documento extraído: páginas, hash, métodos)
  caso.py relatorio <ID> --arquivo NOME [--data AAAA-MM-DD] [--versoes N] [--paginas N]
  caso.py ver <ID>
  caso.py listar [--status S]

Status: recebido > extraido > em_analise > analisado > minuta > entregue  (ou devolvido / arquivado)
Baixa na produção (status entregue), com origem registrada em caso.json["baixa"]:
  - automatica-pasta: arquivo com "FINAL" no nome em 03-relatorios\\ (docx/pdf/md), detectado pelo indexar.py
  - central: botão "Dar baixa" na Central CPJ · agente: /entregar · manual: caso.py status <ID> entregue
"""
import argparse, datetime, json, os, re, shutil

WS = os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO")
CASOS = os.path.join(WS, "casos")
MODELO = os.path.join(CASOS, "_MODELO-CASO")
STATUS = ["recebido", "extraido", "em_analise", "analisado", "minuta", "entregue", "devolvido", "arquivado"]
LISTAS = {"vitimas", "investigados"}


def hoje(): return datetime.date.today().isoformat()


def id_de_os(os_num):
    """'123/2026' -> 'OS-123-2026'. Sem O.S. -> 'SEMOS-AAAAMMDD-HHMMSS'."""
    s = re.sub(r"[^\w]+", "-", (os_num or "").strip(), flags=re.A).strip("-")
    return f"OS-{s}" if s else "SEMOS-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def caminho(id_):
    if not re.fullmatch(r"[\w.\-]+", id_ or "", flags=re.A):
        raise ValueError("ID inválido: use letras, números, ponto, hífen ou sublinhado.")
    return os.path.join(CASOS, id_)


def existe(id_): return os.path.exists(os.path.join(caminho(id_), "caso.json"))


def carregar(id_):
    p = os.path.join(caminho(id_), "caso.json")
    if not os.path.exists(p): raise FileNotFoundError(f"Caso {id_} não existe.")
    c = json.load(open(p, encoding="utf-8"))
    for k, v in (("bo", ""), ("inquerito", ""), ("processo", ""), ("documentos", []), ("prazo", None),
                 ("requisitante", ""), ("escrivao", ""), ("prioridade", "normal"), ("determinacao", ""), ("criado_por", ""),
                 ("responsavel", ""), ("visto", True)):
        c.setdefault(k, v)
    return c


def situacao_prazo(c, hoje_=None):
    """'vencido' | 'hoje' | 'proximo' (<=3 dias) | 'ok' | None (sem prazo ou já entregue)."""
    if not c.get("prazo") or c.get("status") in ("entregue", "arquivado"): return None
    try: d = (datetime.date.fromisoformat(c["prazo"]) - (hoje_ or datetime.date.today())).days
    except ValueError: return None
    return "vencido" if d < 0 else "hoje" if d == 0 else "proximo" if d <= 3 else "ok"


def salvar(c):
    c["atualizado_em"] = datetime.datetime.now().isoformat(timespec="seconds")
    p = os.path.join(caminho(c["id"]), "caso.json"); tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(c, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return c


def listar():
    out = []
    if not os.path.isdir(CASOS): return out
    for d in sorted(os.listdir(CASOS)):
        if d.startswith("_") or not os.path.exists(os.path.join(CASOS, d, "caso.json")): continue
        try: out.append(carregar(d))
        except Exception: pass
    return out


EXTRAS_NOVO = ("prazo", "requisitante", "escrivao", "prioridade", "determinacao", "criado_por", "responsavel", "visto")


def novo(os_num="", bo="", inquerito="", processo="", natureza="Estelionato", recebido=None, id_=None, extras=None):
    id_ = id_ or id_de_os(os_num)
    d = caminho(id_)
    if os.path.exists(d): raise FileExistsError(id_)
    shutil.copytree(MODELO, d)
    c = json.load(open(os.path.join(d, "caso.json"), encoding="utf-8"))
    c.update(id=id_, ordem_servico=os_num, bo=bo, inquerito=inquerito, processo=processo, natureza=natureza,
             status="recebido", documentos=[], criado_em=datetime.datetime.now().isoformat(timespec="seconds"))
    c["referencia"] = " / ".join(x for x in (f"BO {bo}" if bo else "", f"IP {inquerito}" if inquerito else "",
                                             f"Processo {processo}" if processo else "") if x)
    c["datas"]["recebido"] = recebido or hoje()
    for k, v in (extras or {}).items():
        if k in EXTRAS_NOVO: c[k] = v
    return salvar(c)


ORIGENS_BAIXA = ("manual", "central", "agente", "automatica-pasta")


def status(id_, st, data=None, origem=None, arquivo=None):
    """Troca o status gravando a data. 'entregue' = baixa na produção, com origem registrada;
    sair de 'entregue' desfaz a baixa."""
    if st not in STATUS: raise ValueError(f"status inválido: {st}")
    c = carregar(id_); anterior = c.get("status")
    c["status"] = st; c["datas"][st] = data or hoje()
    if st == "entregue":
        c["baixa"] = {"data": c["datas"]["entregue"], "origem": origem if origem in ORIGENS_BAIXA else "manual",
                      "arquivo": arquivo, "registrado_em": datetime.datetime.now().isoformat(timespec="seconds")}
    elif anterior == "entregue":
        c["baixa_ignorar"] = (c.get("baixa") or {}).get("arquivo")  # não refazer baixa automática pelo mesmo arquivo
        c["baixa"] = None; c["datas"]["entregue"] = None
    return salvar(c)


def finais(id_):
    """Relatórios finais presentes na pasta: 03-relatorios\\*FINAL*.docx|pdf|md (ignora temporários do Word)."""
    d = os.path.join(caminho(id_), "03-relatorios")
    if not os.path.isdir(d): return []
    return sorted((f for f in os.listdir(d) if "final" in f.lower() and not f.startswith("~$")
                   and os.path.splitext(f)[1].lower() in (".docx", ".pdf", ".md")),
                  key=lambda f: os.path.getmtime(os.path.join(d, f)))


def baixa_automatica(id_):
    """Se houver relatório FINAL na pasta e o caso ainda não tiver baixa, dá baixa com a data do arquivo."""
    c = carregar(id_)
    if c.get("status") in ("entregue", "arquivado"): return False
    fs = finais(id_)
    if not fs or fs[-1] == c.get("baixa_ignorar"): return False
    arq = fs[-1]
    data = datetime.date.fromtimestamp(os.path.getmtime(os.path.join(caminho(id_), "03-relatorios", arq))).isoformat()
    c = status(id_, "entregue", data=data, origem="automatica-pasta", arquivo=arq)
    if not any(r.get("arquivo") == arq for r in c.get("relatorios", [])):
        registrar_relatorio(id_, arq, data=data)
    return True


def _valor(v):
    v = str(v).strip()
    if v.lower() in ("null", "none", ""): return None
    if v.lower() in ("true", "sim"): return True
    if v.lower() in ("false", "nao", "não"): return False
    if re.fullmatch(r"-?\d+", v): return int(v)
    if re.fullmatch(r"-?\d+[.,]\d+", v): return float(v.replace(",", "."))
    return v


def set_campos(id_, pares):
    """pares: dict {'financeiro.valor_rastreado': '100.5', 'vitimas': 'A, B'}"""
    c = carregar(id_)
    for k, v in pares.items():
        alvo, partes = c, k.strip().split(".")
        for p in partes[:-1]: alvo = alvo.setdefault(p, {})
        ch = partes[-1]
        if ch in LISTAS:
            alvo[ch] = v if isinstance(v, list) else [x.strip() for x in str(v).split(",") if x.strip()]
        elif ch in ("ordem_servico", "bo", "inquerito", "processo", "referencia", "natureza", "observacoes"):
            alvo[ch] = str(v).strip()
        else:
            alvo[ch] = _valor(v)
    return salvar(c)


def importar_ip(id_, rel_json):
    c = carregar(id_); r = json.load(open(rel_json, encoding="utf-8"))
    doc = {"arquivo": r.get("arquivo"), "paginas": r.get("paginas"), "sha256": r.get("sha256_original"),
           "metodos": r.get("metodos", {}), "pendentes": len(r.get("pendentes_transcricao_visual", [])),
           "conferir": len(r.get("conferir_visualmente", [])), "pasta": os.path.basename(os.path.dirname(rel_json))}
    c["documentos"] = [d for d in c.get("documentos", []) if d.get("arquivo") != doc["arquivo"]] + [doc]
    met = {}
    for d in c["documentos"]:
        for k, v in (d.get("metodos") or {}).items(): met[k] = met.get(k, 0) + v
    c["ip"].update(arquivo=", ".join(d["arquivo"] for d in c["documentos"]),
                   paginas=sum(d.get("paginas") or 0 for d in c["documentos"]),
                   sha256=doc["sha256"] if len(c["documentos"]) == 1 else "ver documentos",
                   metodos=met, pendentes=sum(d["pendentes"] for d in c["documentos"]),
                   conferir=sum(d["conferir"] for d in c["documentos"]))
    if c["status"] == "recebido": c["status"] = "extraido"
    c["datas"]["extraido"] = c["datas"].get("extraido") or hoje()
    return salvar(c)


def registrar_relatorio(id_, arquivo, data=None, versoes=None, paginas=None):
    c = carregar(id_)
    c["relatorios"].append({"arquivo": arquivo, "data": data or hoje(), "versoes": versoes, "paginas": paginas})
    return salvar(c)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("novo"); s.add_argument("--os", default=""); s.add_argument("--bo", default="")
    s.add_argument("--ip", default=""); s.add_argument("--processo", default="")
    s.add_argument("--natureza", default="Estelionato"); s.add_argument("--recebido"); s.add_argument("--id")
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("status", choices=STATUS); s.add_argument("--data")
    s.add_argument("--origem", choices=ORIGENS_BAIXA, default="manual"); s.add_argument("--arquivo")
    s = sub.add_parser("set"); s.add_argument("id"); s.add_argument("pares", nargs="+")
    s = sub.add_parser("ip"); s.add_argument("id"); s.add_argument("relatorio_extracao")
    s = sub.add_parser("relatorio"); s.add_argument("id"); s.add_argument("--arquivo", required=True)
    s.add_argument("--data"); s.add_argument("--versoes", type=int); s.add_argument("--paginas", type=int)
    s = sub.add_parser("ver"); s.add_argument("id")
    s = sub.add_parser("listar"); s.add_argument("--status")
    a = ap.parse_args()
    try:
        if a.cmd == "novo":
            c = novo(a.os, a.bo, a.ip, a.processo, a.natureza, a.recebido, a.id); print(f"Caso criado: {caminho(c['id'])}")
        elif a.cmd == "status":
            c = status(a.id, a.status, a.data, a.origem, a.arquivo)
            print(f"{a.id}: status={a.status} em {c['datas'][a.status]}" + (f" (baixa: {a.origem})" if a.status == "entregue" else ""))
        elif a.cmd == "set":
            pares = {}
            for p in a.pares:
                if "=" not in p: raise ValueError(f"Use chave=valor: {p}")
                k, v = p.split("=", 1); pares[k] = v
            set_campos(a.id, pares); print(f"{a.id}: atualizado")
        elif a.cmd == "ip":
            c = importar_ip(a.id, a.relatorio_extracao); print(f"{a.id}: {c['ip']['paginas']} págs. em {len(c['documentos'])} documento(s)")
        elif a.cmd == "relatorio":
            c = registrar_relatorio(a.id, a.arquivo, a.data, a.versoes, a.paginas); print(f"{a.id}: relatório registrado ({len(c['relatorios'])})")
        elif a.cmd == "ver":
            print(json.dumps(carregar(a.id), ensure_ascii=False, indent=2))
        elif a.cmd == "listar":
            for c in listar():
                if a.status and c.get("status") != a.status: continue
                print(f"{c['id']:<22} {c.get('status',''):<11} {c.get('modalidade') or '':<18} BO {c.get('bo','')}  IP {c.get('inquerito','')}")
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        raise SystemExit(f"ERRO: {e}")
