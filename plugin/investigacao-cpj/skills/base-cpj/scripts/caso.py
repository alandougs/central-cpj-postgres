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
import argparse, contextlib, datetime, json, os, re, shutil, threading, time, uuid

WS = os.environ.get("CPJ_WORKSPACE", r"C:\CPJ - TRABALHO")
CASOS = os.path.join(WS, "casos")
MODELO = os.path.join(CASOS, "_MODELO-CASO")
STATUS = ["recebido", "extraido", "em_analise", "analisado", "minuta", "entregue", "devolvido", "arquivado"]
LISTAS = {"vitimas", "investigados"}


class ConcorrenciaErro(Exception):
    """Exceção levantada quando há conflito de gravação ou versão concorrente."""
    pass


class BloqueioTimeoutErro(Exception):
    """Exceção levantada quando não foi possível adquirir o lock do caso a tempo."""
    pass


_locks = {}
_locks_guard = threading.Lock()
_local = threading.local()


def _get_casos_ativos():
    if not hasattr(_local, "casos"):
        _local.casos = {}
    return _local.casos


class ReentrantFileLock:
    def __init__(self, id_, timeout=10.0):
        self.id_ = id_
        self.pasta = caminho(id_)
        self.timeout = timeout
        self.lock_file = None
        with _locks_guard:
            if id_ not in _locks:
                _locks[id_] = threading.RLock()
            self.rlock = _locks[id_]

    def __enter__(self):
        if not self.rlock.acquire(timeout=self.timeout):
            raise BloqueioTimeoutErro(f"Timeout ao aguardar trava de thread para caso {self.id_}")
        casos = _get_casos_ativos()
        depth = casos.get(self.id_, 0)
        casos[self.id_] = depth + 1
        if depth > 0:
            return self
        fim = time.time() + self.timeout
        os.makedirs(self.pasta, exist_ok=True)
        lock_path = os.path.join(self.pasta, ".caso.lock")
        self.lock_file = open(lock_path, "a+b")
        bloqueado = False
        while time.time() < fim:
            try:
                if os.name == "nt":
                    import msvcrt
                    self.lock_file.seek(0)
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                bloqueado = True
                break
            except (BlockingIOError, OSError, PermissionError):
                time.sleep(0.02)
        if not bloqueado:
            self.lock_file.close()
            self.lock_file = None
            casos[self.id_] = depth
            self.rlock.release()
            raise BloqueioTimeoutErro(f"Timeout ao aguardar trava de processo para caso {self.id_}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        casos = _get_casos_ativos()
        depth = casos.get(self.id_, 1) - 1
        if depth <= 0:
            casos.pop(self.id_, None)
            if self.lock_file:
                try:
                    if os.name == "nt":
                        import msvcrt
                        self.lock_file.seek(0)
                        msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
                finally:
                    self.lock_file.close()
                    self.lock_file = None
        else:
            casos[self.id_] = depth
        self.rlock.release()


def trava_caso(id_, timeout=10.0):
    """Context manager para trava exclusiva de leitura/alteração/escrita por caso (thread e processo)."""
    return ReentrantFileLock(id_, timeout=timeout)


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


def salvar(c, revisao_esperada=None):
    with trava_caso(c["id"]):
        p = os.path.join(caminho(c["id"]), "caso.json")
        if revisao_esperada is not None and os.path.exists(p):
            atual = json.load(open(p, encoding="utf-8"))
            rev_atual = atual.get("revisao", 1)
            if rev_atual != revisao_esperada:
                raise ConcorrenciaErro(
                    f"Conflito de versão no caso {c['id']}: revisão no disco é {rev_atual}, esperava {revisao_esperada}."
                )
        c["revisao"] = c.get("revisao", 0) + 1
        c["atualizado_em"] = datetime.datetime.now().isoformat(timespec="seconds")
        tmp = os.path.join(caminho(c["id"]), f".caso.{os.getpid()}_{uuid.uuid4().hex}.tmp")
        with open(tmp, "w", encoding="utf-8") as f: json.dump(c, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
        return c


def atualizar(id_, mutador_fn, revisao_esperada=None, timeout=10.0):
    with trava_caso(id_, timeout=timeout):
        c = carregar(id_)
        if revisao_esperada is not None:
            rev_atual = c.get("revisao", 1)
            if rev_atual != revisao_esperada:
                raise ConcorrenciaErro(
                    f"Conflito de versão no caso {id_}: revisão no disco é {rev_atual}, esperava {revisao_esperada}."
                )
        res = mutador_fn(c)
        if res is not None: c = res
        return salvar(c)


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


def status(id_, st, data=None, origem=None, arquivo=None, revisao_esperada=None):
    """Troca o status gravando a data. 'entregue' = baixa na produção, com origem registrada;
    sair de 'entregue' desfaz a baixa."""
    if st not in STATUS: raise ValueError(f"status inválido: {st}")
    def _mutar(c):
        anterior = c.get("status")
        c["status"] = st; c["datas"][st] = data or hoje()
        if st == "entregue":
            c["baixa"] = {"data": c["datas"]["entregue"], "origem": origem if origem in ORIGENS_BAIXA else "manual",
                          "arquivo": arquivo, "registrado_em": datetime.datetime.now().isoformat(timespec="seconds")}
        elif anterior == "entregue":
            c["baixa_ignorar"] = (c.get("baixa") or {}).get("arquivo")  # não refazer baixa automática pelo mesmo arquivo
            c["baixa"] = None; c["datas"]["entregue"] = None
        return c
    return atualizar(id_, _mutar, revisao_esperada=revisao_esperada)


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


def set_campos(id_, pares, revisao_esperada=None):
    """pares: dict {'financeiro.valor_rastreado': '100.5', 'vitimas': 'A, B'}"""
    def _mutar(c):
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
        return c
    return atualizar(id_, _mutar, revisao_esperada=revisao_esperada)


def importar_ip(id_, rel_json):
    def _mutar(c):
        r = json.load(open(rel_json, encoding="utf-8"))
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
        return c
    return atualizar(id_, _mutar)


def registrar_relatorio(id_, arquivo, data=None, versoes=None, paginas=None):
    def _mutar(c):
        c["relatorios"].append({"arquivo": arquivo, "data": data or hoje(), "versoes": versoes, "paginas": paginas})
        return c
    return atualizar(id_, _mutar)


def reservar_proxima_minuta(id_, texto_formatador_fn, versao_base=None):
    """Reserva de forma atômica e exclusiva a próxima versão da minuta (minuta-vNN.md).
    texto_formatador_fn pode ser uma string com o texto ou uma função fn(versao_int, nome_arq) -> str.
    Se versao_base for informada e já houver uma versão maior no disco, lança ConcorrenciaErro.
    Retorna dict com versao (int), arquivo (str) e caminho (str)."""
    with trava_caso(id_):
        d = os.path.join(caminho(id_), "03-relatorios")
        os.makedirs(d, exist_ok=True)
        ms = [f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f, re.I)]
        num_versoes = [int(re.findall(r"\d+", f)[0]) for f in ms]
        ult_v = max(num_versoes) if num_versoes else 0
        if versao_base is not None and ult_v > int(versao_base):
            raise ConcorrenciaErro(
                f"A minuta já foi atualizada para a versão v{ult_v:02d} por outro usuário ou processo "
                f"(sua base era v{int(versao_base):02d})."
            )
        prox_v = ult_v + 1
        nome = f"minuta-v{prox_v:02d}.md"
        p = os.path.join(d, nome)
        txt = texto_formatador_fn(prox_v, nome) if callable(texto_formatador_fn) else str(texto_formatador_fn)
        tmp = os.path.join(d, f".{nome}.{os.getpid()}_{uuid.uuid4().hex}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(txt)
        os.replace(tmp, p)
        return {"versao": prox_v, "arquivo": nome, "caminho": p, "ult_anterior": ult_v}


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
