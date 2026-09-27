"""Tarefas em segundo plano da Central CPJ com progresso real:
exportação/importação do banco de dados, importação de bases de consulta e referências, e agentes de IA.
"""
import datetime, hashlib, json, os, re, shutil, subprocess, sys, threading, time, uuid, zipfile, queue

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
S_REL = os.path.join(PLUGIN, "skills", "relatorio-ip-fraude", "scripts")
PY = sys.executable
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
EXPORT_SCHEMA = "cpj-export/1"
SEM_COMPRESSAO = (".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".zip", ".sqlite")


def agora(): return datetime.datetime.now().isoformat(timespec="seconds")


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def _apagar(p):
    """Remove arquivo temporário sem derrubar a tarefa (o Windows pode reter o arquivo por instantes)."""
    for _ in range(5):
        try: os.remove(p); return
        except FileNotFoundError: return
        except PermissionError: time.sleep(0.4)


sys.path.insert(0, AQUI)
import plantao as PL  # noqa: E402  (fila de pedidos de IA e agentes de plantão)


def plantao_config(ws):
    """config/plantao.json: {"agente_embutido": true, "tipo_embutido": "claude"}. O agente embutido é a própria Central
    atuando como um agente de plantão (aprovado automaticamente); pode ser desligado quando houver outros agentes."""
    cfg = {"agente_embutido": True, "tipo_embutido": "claude"}
    p = os.path.join(ws, "config", "plantao.json")
    if os.path.exists(p):
        try: cfg.update(json.load(open(p, encoding="utf-8")))
        except ValueError: pass
    return cfg


class Tarefas:
    def __init__(self, ws, caso_mod, auth, iniciar_agente=True):
        self.ws, self.C, self.auth = ws, caso_mod, auth
        self.t, self.trava, self.procs = {}, threading.Lock(), {}
        self.plantao = PL.Plantao(ws)
        self.parar_agente = threading.Event()
        cfg = plantao_config(ws)
        if iniciar_agente and cfg.get("agente_embutido") and os.environ.get("CPJ_SEM_AGENTE_EMBUTIDO") != "1":
            threading.Thread(target=PL.trabalhar, args=(ws, "Central-" + cfg.get("tipo_embutido", "claude").capitalize(),
                                                        cfg.get("tipo_embutido", "claude")),
                             kwargs={"parar": self.parar_agente, "aprovado": True}, daemon=True).start()

    # ------------------------------------------------------------ registro
    def nova(self, tipo, titulo, usuario, caso=None, **extra):
        tid = uuid.uuid4().hex[:12]
        with self.trava:
            self.t[tid] = {"id": tid, "tipo": tipo, "titulo": titulo, "usuario": usuario, "caso": caso, "status": "na_fila",
                           "progresso": 0, "etapa": "na fila", "detalhe": "", "inicio": agora(), "fim": None, "erro": None,
                           "resultado": None, **extra}
        return tid

    def at(self, tid, **kw):
        with self.trava:
            if tid in self.t: self.t[tid].update(kw)

    def listar(self, usuario=None, todas=False):
        limite = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()
        with self.trava:
            out = [dict(v) for v in self.t.values() if (todas or v["usuario"] == usuario)
                   and (v["status"] in ("na_fila", "executando") or (v["fim"] or "") >= limite)]
        out += [self.plantao.como_tarefa(p) for p in self.plantao.pedidos() if todas or p["solicitante"] == usuario]
        return sorted(out, key=lambda v: v["inicio"] or "", reverse=True)

    def obter(self, tid):
        if str(tid).startswith("ia-"):
            p = self.plantao.pedido(tid)
            return self.plantao.como_tarefa(p) if p else None
        with self.trava: return dict(self.t[tid]) if tid in self.t else None

    def rodar(self, tid, fn, *args):
        def alvo():
            self.at(tid, status="executando", etapa="iniciando")
            try:
                res = fn(tid, *args)
                if self.obter(tid)["status"] != "cancelada":
                    self.at(tid, status="concluida", progresso=100, etapa="concluído", fim=agora(), resultado=res)
            except Exception as e:
                self.at(tid, status="erro", erro=str(e), fim=agora())
        threading.Thread(target=alvo, daemon=True).start()
        return tid

    def indexar(self):
        env = dict(os.environ, CPJ_WORKSPACE=self.ws, PYTHONIOENCODING="utf-8")
        subprocess.run([PY, os.path.join(S_BASE, "indexar.py")], env=env, capture_output=True, creationflags=SEM_JANELA)

    # ------------------------------------------------------------ exportação
    def _lista_export(self, modo, incluir_modelo):
        W = self.ws; itens = []
        def add_dir(rel, filtro=None):
            base = os.path.join(W, rel)
            for raiz, dirs, arqs in os.walk(base):
                dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
                for a in arqs:
                    p = os.path.join(raiz, a); r = os.path.relpath(p, W).replace("\\", "/")
                    if a.endswith(".tmp") or a.startswith("~$"): continue
                    if filtro and not filtro(r): continue
                    itens.append((p, r))
        leve = lambda r: not (re.search(r"/00-originais/|/paginas_visao/", r))
        sem_modelo = lambda r: not r.startswith("casos/_MODELO-CASO/")
        add_dir("casos", (lambda r: leve(r) and sem_modelo(r)) if modo == "dados" else sem_modelo)
        for d in ("calibracao", "consulta", "referencias"): add_dir(d)
        for f in ("producao/config.json", "producao/base.csv", "producao/base.json", "modelos/dados-padrao.json"):
            if os.path.exists(os.path.join(W, f)): itens.append((os.path.join(W, f), f))
        if incluir_modelo:
            add_dir("modelos", lambda r: r.lower().endswith(".docx"))
        return itens

    def exportar(self, tid, modo, incluir_modelo):
        self.at(tid, etapa="atualizando a base"); self.indexar()
        itens = self._lista_export(modo, incluir_modelo)
        total = sum(os.path.getsize(p) for p, _ in itens) or 1
        os.makedirs(os.path.join(self.ws, "exportacoes"), exist_ok=True)
        nome = f"CPJ-export-{modo}-{datetime.datetime.now():%Y%m%d-%H%M%S}.zip"
        destino = os.path.join(self.ws, "exportacoes", nome); tmp = destino + ".parcial"
        feito, manifesto = 0, []
        with zipfile.ZipFile(tmp, "w", allowZip64=True) as z:
            for i, (p, r) in enumerate(itens, 1):
                if self.obter(tid)["status"] == "cancelada": break
                comp = zipfile.ZIP_STORED if r.lower().endswith(SEM_COMPRESSAO) else zipfile.ZIP_DEFLATED
                h = hashlib.sha256()
                zi = zipfile.ZipInfo.from_file(p, "dados/" + r); zi.compress_type = comp
                with open(p, "rb") as f, z.open(zi, "w", force_zip64=True) as w:
                    for b in iter(lambda: f.read(1 << 20), b""):
                        w.write(b); h.update(b); feito += len(b)
                        self.at(tid, progresso=min(99, int(98 * feito / total)), etapa=f"compactando {i}/{len(itens)} arquivos",
                                detalhe=f"{feito / 1048576:.1f} de {total / 1048576:.1f} MB")
                manifesto.append({"caminho": r, "tamanho": os.path.getsize(p), "sha256": h.hexdigest()})
            casos = sorted({m["caminho"].split("/")[1] for m in manifesto if m["caminho"].startswith("casos/")} - {"_MODELO-CASO"})
            z.writestr("manifest.json", json.dumps({"schema": EXPORT_SCHEMA, "gerado_em": agora(), "modo": modo,
                       "inclui_modelo_docx": incluir_modelo, "casos": casos, "arquivos": manifesto}, ensure_ascii=False, indent=1))
        if self.obter(tid)["status"] == "cancelada":
            os.remove(tmp); return None
        os.replace(tmp, destino)
        return {"arquivo": nome, "url": f"/exportacoes/{nome}", "casos": len(casos), "mb": round(os.path.getsize(destino) / 1048576, 1)}

    # ------------------------------------------------------------ importação
    def importar(self, tid, zip_path):
        W = self.ws
        with zipfile.ZipFile(zip_path) as z:
            try: man = json.loads(z.read("manifest.json"))
            except KeyError: raise ValueError("Pacote inválido: manifest.json ausente (use um arquivo exportado pela Central CPJ).")
            if man.get("schema") != EXPORT_SCHEMA: raise ValueError(f"Versão de pacote não suportada: {man.get('schema')}")
            arqs = man["arquivos"]; total = sum(a["tamanho"] for a in arqs) or 1; feito = 0
            # 1) integridade
            for i, a in enumerate(arqs, 1):
                h = hashlib.sha256()
                with z.open("dados/" + a["caminho"]) as f:
                    for b in iter(lambda: f.read(1 << 20), b""):
                        h.update(b); feito += len(b)
                        self.at(tid, progresso=int(45 * feito / total), etapa=f"verificando integridade {i}/{len(arqs)}")
                if h.hexdigest() != a["sha256"]: raise ValueError(f"Arquivo corrompido no pacote: {a['caminho']}")
            # 2) decidir o que entra (nunca sobrescreve)
            existentes = {d for d in os.listdir(os.path.join(W, "casos"))} if os.path.isdir(os.path.join(W, "casos")) else set()
            novos, pulados, feito, copiados = set(), set(), 0, 0
            raiz = os.path.normpath(W)
            for i, a in enumerate(arqs, 1):
                r = a["caminho"]; partes = r.split("/")
                destino = os.path.normpath(os.path.join(W, *partes))
                if not destino.startswith(raiz + os.sep): raise ValueError(f"Caminho inseguro no pacote: {r}")
                if partes[0] == "casos" and len(partes) > 2:
                    if partes[1] in existentes and partes[1] not in novos: pulados.add(partes[1]); continue
                    novos.add(partes[1])
                elif os.path.exists(destino):
                    if os.path.isfile(destino) and _sha(destino) == a["sha256"]: continue  # idêntico: nada a fazer
                    if partes[0] == "calibracao":
                        destino = destino.replace(".md", f"-importado-{datetime.date.today():%Y%m%d}.md")
                        if os.path.exists(destino): continue
                    else:
                        continue  # config, modelos, bases e referências já existentes não são sobrescritos
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with z.open("dados/" + r) as f, open(destino, "wb") as w: shutil.copyfileobj(f, w, 1 << 20)
                copiados += 1; feito += a["tamanho"]
                self.at(tid, progresso=45 + int(45 * i / len(arqs)), etapa=f"extraindo {i}/{len(arqs)}")
        self.at(tid, progresso=92, etapa="reindexando a base"); self.indexar()
        _apagar(zip_path)
        return {"casos_novos": sorted(novos - pulados), "casos_ja_existentes": sorted(pulados), "arquivos": copiados}

    # ------------------------------------------------------------ bases de consulta e referências
    def importar_consulta(self, tid, arquivo, nome):
        sys.path.insert(0, S_BASE); import consulta as Q
        Q.WS, Q.BASES = self.ws, os.path.join(self.ws, "consulta")
        meta = Q.importar(arquivo, nome, lambda p, e: self.at(tid, progresso=int(p * 0.8), etapa=e))
        self.at(tid, progresso=85, etapa="indexando para pesquisa"); self.indexar(); _apagar(arquivo)
        return {"base": meta["id"], "registros": meta["registros"], "mapeamento": meta["mapeamento"]}

    def importar_referencia(self, tid, arquivo, dados):
        sys.path.insert(0, S_BASE); import referencias as RF
        RF.WS, RF.REFS = self.ws, os.path.join(self.ws, "referencias")
        self.at(tid, progresso=20, etapa="extraindo texto")
        meta = RF.importar(arquivo, dados.get("autor"), dados.get("modalidade") or None, dados.get("natureza") or "Estelionato",
                           dados.get("peso") or 3, dados.get("obs") or "", dados.get("enviado_por") or "")
        self.at(tid, progresso=70, etapa="indexando"); self.indexar(); _apagar(arquivo)
        return {"referencia": meta["id"], "autor": meta["autor"]}

    # ------------------------------------------------------------ agentes de IA (plantão: app/plantao.py)
    ACOES = PL.ACOES

    @staticmethod
    def claude_exe(): return PL.claude_exe()

    def claude_status(self):
        exe = self.claude_exe()
        if not exe: return {"instalado": False, "logado": False}
        try:
            r = subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True, timeout=30, creationflags=SEM_JANELA)
            j = json.loads(r.stdout or "{}")
            return {"instalado": True, "logado": bool(j.get("loggedIn")), "metodo": j.get("authMethod"), "email": j.get("email")}
        except Exception as e:
            return {"instalado": True, "logado": False, "erro": str(e)}

    def claude_login(self):
        exe = self.claude_exe()
        if not exe: raise ValueError("Claude Code não encontrado neste computador.")
        subprocess.Popen(["cmd", "/c", "start", "Entrar no Claude", "cmd", "/k", exe, "auth", "login"], cwd=self.ws)

    def enfileirar_ia(self, id_, acao, usuario, observacoes="", preferido=None):
        """O botão da Central cria um pedido na fila do plantão; o primeiro agente ocioso e aprovado executa."""
        return self.plantao.enfileirar(id_, acao, usuario, observacoes, preferido)

    def cancelar(self, tid):
        if str(tid).startswith("ia-"): return self.plantao.cancelar(tid)
        t = self.obter(tid)
        if not t or t["status"] not in ("na_fila", "executando"): return False
        self.at(tid, status="cancelada", etapa="cancelada", fim=agora())
        p = self.procs.get(tid)
        if p: subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=SEM_JANELA)
        return True


# ------------------------------------------------------------ relatório: DOCX / PDF
def gerar_docx(ws, id_, minuta_nome, sem_assinatura=False):
    d = os.path.join(ws, "casos", id_, "03-relatorios")
    v = re.findall(r"\d+", minuta_nome)[0]
    saida = os.path.join(d, f"RELATORIO-{id_}-v{v}.docx")
    cmd = [PY, os.path.join(S_REL, "gerar_docx.py"), os.path.join(d, minuta_nome), "--saida", saida]
    if sem_assinatura: cmd.append("--sem-assinatura")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=SEM_JANELA,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if r.returncode != 0: raise RuntimeError((r.stderr or r.stdout)[-400:])
    pend = re.search(r"preencher\):\s*(.+)", r.stdout)
    return {"docx": os.path.basename(saida), "pendentes": pend.group(1).strip() if pend else ""}


def soffice():
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(p): return p
    return None


def gerar_pdf(ws, id_, docx_nome):
    exe = soffice()
    if not exe:
        raise RuntimeError("Conversão automática para PDF requer o LibreOffice (gratuito). Alternativa: Abrir no Word → "
                           "Imprimir → impressora 'Microsoft Print to PDF'.")
    d = os.path.join(ws, "casos", id_, "03-relatorios")
    r = subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", d, os.path.join(d, docx_nome)],
                       capture_output=True, text=True, timeout=180, creationflags=SEM_JANELA)
    pdf = os.path.splitext(docx_nome)[0] + ".pdf"
    if not os.path.exists(os.path.join(d, pdf)): raise RuntimeError("Falha na conversão: " + (r.stderr or r.stdout)[-300:])
    return {"pdf": pdf}
