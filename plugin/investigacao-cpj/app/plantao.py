"""Plantão de agentes da Central CPJ.

Pedidos de IA acionados na Central (Analisar, Gerar relatório, Análise + relatório, Revisar) entram numa fila
persistente (config/plantao.sqlite). Agentes de plantão — sessões de chat (Codex, Claude, Antigravity) guiadas pelo
PROMPT-AGENTE-PLANTAO.md ou executores automáticos (Claude Code / Codex CLI) — ficam de alerta, enviam sinal de vida e
o primeiro OCIOSO e APROVADO reserva o próximo pedido (reserva atômica: dois agentes nunca pegam o mesmo).

Regras de segurança: agente novo entra como "aguardando aprovação" (aprovar no PC da Central); um pedido ativo por caso;
agente que para de responder devolve o pedido à fila (até 2 tentativas); cancelamento pela Central é respeitado.
"""
import datetime, json, os, re, socket, sqlite3, subprocess, sys, threading, time, uuid
from contextlib import contextmanager

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
S_BASE = os.path.join(PLUGIN, "skills", "base-cpj", "scripts")
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TIPOS = ("claude", "codex", "gemini", "antigravity", "outro", "simulado")
MODOS = ("chat", "auto")
SILENCIO_MAX = {"auto": 45, "chat": 20 * 60}   # segundos sem sinal de vida até considerar o agente fora do ar
TENTATIVAS_MAX = 2


def agora(): return datetime.datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------ expediente (economia: IA automática só no horário de trabalho)
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
EXPEDIENTE_PADRAO = {"ativo": True, "dias": [0, 1, 2, 3, 4], "inicio": "09:00", "fim": "18:00", "feriados": []}


def expediente(ws):
    """config/plantao.json → {"expediente": {"ativo", "dias" (0=seg … 6=dom), "inicio", "fim", "feriados": ["AAAA-MM-DD"]}}.
    Fora do expediente nenhum agente reserva pedido sozinho; o pedido espera na fila e o usuário aciona pelo chat."""
    cfg = dict(EXPEDIENTE_PADRAO)
    try:
        j = json.load(open(os.path.join(ws, "config", "plantao.json"), encoding="utf-8"))
        cfg.update({k: v for k, v in (j.get("expediente") or {}).items() if k in EXPEDIENTE_PADRAO})
    except (OSError, ValueError, AttributeError):
        pass
    return cfg


def _hm(s):
    h, m = str(s).split(":"); return datetime.time(int(h), int(m))


def em_expediente(ws, quando=None):
    e = expediente(ws)
    if not e["ativo"]: return True
    q = quando or datetime.datetime.now()
    if q.weekday() not in e["dias"] or q.date().isoformat() in e["feriados"]: return False
    return _hm(e["inicio"]) <= q.time() < _hm(e["fim"])


def proximo_expediente(ws, quando=None):
    """Início do próximo período de expediente (None se o controle estiver desligado ou não houver dias úteis)."""
    e = expediente(ws)
    if not e["ativo"] or not e["dias"]: return None
    q = quando or datetime.datetime.now()
    for n in range(0, 400):
        d = q.date() + datetime.timedelta(days=n)
        ini = datetime.datetime.combine(d, _hm(e["inicio"]))
        if d.weekday() in e["dias"] and d.isoformat() not in e["feriados"] and ini > q: return ini
    return None


def descricao_expediente(ws):
    e = expediente(ws)
    if not e["ativo"]: return "sem restrição de horário"
    dias = sorted(e["dias"])
    txt = (f"{DIAS_SEMANA[dias[0]]}–{DIAS_SEMANA[dias[-1]]}" if dias == list(range(dias[0], dias[-1] + 1)) and len(dias) > 1
           else ", ".join(DIAS_SEMANA[d] for d in dias))
    return f"{txt}, {e['inicio']}–{e['fim']}"


def aviso_fora_expediente(ws, quando=None):
    p = proximo_expediente(ws, quando)
    volta = f"{DIAS_SEMANA[p.weekday()]} {p:%d/%m %H:%M}" if p else "—"
    return (f"fora do expediente ({descricao_expediente(ws)}): os agentes retomam {volta} — "
            "ou acione pelo chat se precisar agora")


def _ts(s):
    try: return datetime.datetime.fromisoformat(s).timestamp()
    except (TypeError, ValueError): return 0


# ------------------------------------------------------------------ o que cada botão pede ao agente
ACOES = {
    "analisar": ("Análise do IP (IA)",
                 "Use a skill investigacao-cpj:analisar-ip para o caso {id} (fora do Claude: siga portatil\\02-analisar-ip.md). "
                 "Gere também 02-analise\\pessoas.csv (colunas nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;"
                 "emails;placas;condicao;paginas;documento — somente dados como constam nos autos, múltiplos valores separados por ' | ').",
                 "5 'iniciando'; 10 'inventário concluído'; de 15 a 60 um marco por bloco de páginas analisado; 70 'fluxo financeiro'; "
                 "80 'elementos do tipo e lacunas'; 90 'pessoas.csv e caso.json atualizados'; 100 'concluído'"),
    "relatorio": ("Relatório de investigação (IA)",
                  "Use a skill investigacao-cpj:relatorio-ip para o caso {id} (fora do Claude: siga portatil\\04-relatorio-ip.md). "
                  "Se 02-analise\\ficha-caso.md não existir, faça antes a análise (investigacao-cpj:analisar-ip / "
                  "portatil\\02-analisar-ip.md). Considere a determinação da O.S. registrada em caso.json.",
                  "5 'iniciando'; 20 'análise e exemplos lidos'; 45 'minuta redigida'; 60 'rastreabilidade'; 75 'revisão concluída'; "
                  "90 'DOCX gerado'; 100 'concluído'"),
    "completo": ("Análise + relatório (IA)",
                 "Para o caso {id}: 1) análise (skill investigacao-cpj:analisar-ip ou portatil\\02-analisar-ip.md), gerando também "
                 "02-analise\\pessoas.csv com as colunas nome;mae;pai;cpf;rg;nascimento;telefones;enderecos;empresas;cnpj;emails;placas;"
                 "condicao;paginas;documento; 2) relatório (skill investigacao-cpj:relatorio-ip ou portatil\\04-relatorio-ip.md). "
                 "Considere a determinação da O.S. em caso.json.",
                 "5 'iniciando'; de 10 a 45 marcos da análise (um por bloco); 50 'análise concluída'; 65 'minuta redigida'; "
                 "75 'rastreabilidade'; 85 'revisão'; 95 'DOCX gerado'; 100 'concluído'"),
    "revisar": ("Revisão do relatório (IA)",
                "Revise a minuta mais recente de casos\\{id}\\03-relatorios com as instruções do agente revisor-de-relatorio "
                "(skill investigacao-cpj:revisar-relatorio ou portatil\\05-revisar-relatorio.md) e grave revisao-vNN.md. Não altere a minuta.",
                "10 'iniciando'; 40 'afirmações conferidas até a metade'; 80 'conferência concluída'; 100 'concluído'"),
}


def montar_prompt(job, ws, modo="auto", agente=None):
    """Instrução completa do pedido. modo 'chat': o progresso é informado pelo comando agente-plantao.py."""
    titulo, tarefa, marcos = ACOES[job["acao"]]
    id_ = job["caso"]
    if modo == "chat":
        cli = os.path.join(os.path.dirname(os.path.dirname(PLUGIN)), "ferramentas", "agente-plantao.py")
        prog = f'python "{cli}" progresso {job["id"]} --agente "{agente}" --pct <percentual> --etapa "<etapa>"'
        fim = (f'Ao terminar: python "{cli}" concluir {job["id"]} --agente "{agente}" --resumo "<até 6 linhas: o que foi feito, '
               f'arquivos gerados, pendências>". Se não for possível concluir: python "{cli}" falhar {job["id"]} --agente "{agente}" '
               '--erro "<motivo>". Se o comando de progresso responder CANCELADO, pare imediatamente e não conclua.')
    else:
        prog = f'python "{os.path.join(S_BASE, "progresso.py")}" {id_} <percentual> "<etapa>"'
        fim = ("Ao final, atualize caso.json com caso.py quando a skill indicar e responda com um resumo de até 6 linhas: o que foi "
               "feito, arquivos gerados e pendências para o investigador conferir.")
    return (
        f"PEDIDO {job['id']} — {titulo} — acionado na Central CPJ por '{job['solicitante']}'. Execute sem fazer perguntas: siga as "
        "recomendações padrão dos procedimentos; onde faltar dado, use placeholders {...} e liste as pendências no resumo final.\n"
        f"Workspace: {ws}. Caso: {id_} (pasta casos\\{id_}). Siga AGENTS.md (e CLAUDE.md, se for Claude) deste workspace.\n"
        "Fonte dos fatos: SOMENTE os documentos do próprio caso (IP e peças enviadas). Bases de consulta (consulta\\, Muralha "
        "Paulista) e relatórios de referência (referencias\\) NÃO são fonte de fatos; referências servem só como exemplo de "
        "estrutura e estilo. Não acesse a internet. Não altere 00-originais.\n"
        f"Progresso: registre cada marco executando  {prog}  nos marcos: {marcos}.\n"
        + (f"Observações do investigador: {job['observacoes']}\n" if job.get("observacoes") else "")
        + f"Tarefa: {tarefa.format(id=id_)}\n" + fim
    )


# ------------------------------------------------------------------ fila persistente
class Plantao:
    def __init__(self, ws):
        self.ws = ws
        os.makedirs(os.path.join(ws, "config"), exist_ok=True)
        self.db = os.path.join(ws, "config", "plantao.sqlite")
        with self._c() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS agentes(nome TEXT PRIMARY KEY, tipo TEXT, modo TEXT, aprovado INTEGER DEFAULT 0,
              estado TEXT, detalhe TEXT, job TEXT, host TEXT, pid INTEGER, registrado_em TEXT, visto_em TEXT);
            CREATE TABLE IF NOT EXISTS pedidos(id TEXT PRIMARY KEY, caso TEXT, acao TEXT, observacoes TEXT, solicitante TEXT,
              preferido TEXT, estado TEXT, agente TEXT, tentativas INTEGER DEFAULT 0, cancelar INTEGER DEFAULT 0,
              progresso INTEGER DEFAULT 0, etapa TEXT, detalhe TEXT, resultado TEXT, erro TEXT,
              criado_em TEXT, iniciado_em TEXT, fim TEXT);
            CREATE INDEX IF NOT EXISTS ix_ped_estado ON pedidos(estado, criado_em);
            """)

    @contextmanager
    def _c(self):
        """Conexão curta, SEMPRE fechada ao sair (no Windows, conexão aberta prende o arquivo)."""
        c = sqlite3.connect(self.db, timeout=30, isolation_level=None)
        try:
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA busy_timeout=30000")
            yield c
        finally:
            c.close()

    # ---------------------------------------------------------------- agentes
    def registrar(self, nome, tipo, modo, aprovado=None):
        if not re.fullmatch(r"[\w.\- ]{1,60}", nome or ""): raise ValueError("Nome de agente inválido.")
        if tipo not in TIPOS or modo not in MODOS: raise ValueError("Tipo ou modo de agente inválido.")
        with self._c() as c:
            c.execute("INSERT OR IGNORE INTO agentes(nome,tipo,modo,aprovado,estado,registrado_em,visto_em,host,pid) "
                      "VALUES(?,?,?,?,?,?,?,?,?)", (nome, tipo, modo, 1 if aprovado else 0, "ocioso", agora(), agora(),
                                                    socket.gethostname(), os.getpid()))
            c.execute("UPDATE agentes SET tipo=?, modo=?, visto_em=?, host=?, pid=? WHERE nome=?",
                      (tipo, modo, agora(), socket.gethostname(), os.getpid(), nome))
            if aprovado: c.execute("UPDATE agentes SET aprovado=1 WHERE nome=?", (nome,))
            return dict(c.execute("SELECT * FROM agentes WHERE nome=?", (nome,)).fetchone())

    def sinal(self, nome, estado, detalhe="", job=None):
        with self._c() as c:
            c.execute("UPDATE agentes SET estado=?, detalhe=?, job=?, visto_em=? WHERE nome=?", (estado, detalhe[:300], job, agora(), nome))

    def aprovar(self, nome, sim=True):
        with self._c() as c:
            n = c.execute("UPDATE agentes SET aprovado=? WHERE nome=?", (1 if sim else 0, nome)).rowcount
        if not n: raise ValueError(f"Agente não registrado: {nome}")

    def agentes(self):
        out = []
        with self._c() as c:
            for a in c.execute("SELECT * FROM agentes ORDER BY nome"):
                a = dict(a); silencio = time.time() - _ts(a["visto_em"])
                if silencio > SILENCIO_MAX.get(a["modo"], 60): a["estado"] = "fora do ar"
                elif not a["aprovado"]: a["estado"] = "aguardando aprovação"
                a["silencio_s"] = int(silencio); out.append(a)
        return out

    # ---------------------------------------------------------------- pedidos
    def enfileirar(self, caso, acao, solicitante, observacoes="", preferido=None):
        if acao not in ACOES: raise ValueError("Ação de IA inválida.")
        with self._c() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM pedidos WHERE caso=? AND estado IN ('pendente','executando')", (caso,)).fetchone():
                c.execute("ROLLBACK"); raise ValueError("Já existe uma tarefa de IA em andamento para este caso.")
            pid = "ia-" + uuid.uuid4().hex[:10]
            c.execute("INSERT INTO pedidos(id,caso,acao,observacoes,solicitante,preferido,estado,etapa,criado_em) "
                      "VALUES(?,?,?,?,?,?,?,?,?)", (pid, caso, acao, (observacoes or "")[:2000], solicitante, preferido or None,
                                                    "pendente", "aguardando agente de plantão", agora()))
            c.execute("COMMIT")
        return pid

    def _recolher_abandonados(self, c):
        """Pedidos em execução cujo agente parou de responder voltam à fila (ou falham após TENTATIVAS_MAX)."""
        for p in c.execute("SELECT p.id, p.tentativas, a.modo, a.visto_em FROM pedidos p LEFT JOIN agentes a ON a.nome=p.agente "
                           "WHERE p.estado='executando'").fetchall():
            if time.time() - _ts(p["visto_em"]) <= SILENCIO_MAX.get(p["modo"] or "auto", 60): continue
            if p["tentativas"] >= TENTATIVAS_MAX:
                c.execute("UPDATE pedidos SET estado='erro', erro='O agente parou de responder (tentativas esgotadas).', fim=? "
                          "WHERE id=?", (agora(), p["id"]))
            else:
                # volta à fila liberado para qualquer agente (inclusive se estava direcionado ao que parou)
                c.execute("UPDATE pedidos SET estado='pendente', agente=NULL, preferido=NULL, "
                          "etapa='devolvido à fila: agente parou de responder' WHERE id=?", (p["id"],))

    def reivindicar(self, nome):
        """O agente ocioso e aprovado reserva o pedido pendente mais antigo (ou o que foi direcionado a ele)."""
        with self._c() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                self._recolher_abandonados(c)
                a = c.execute("SELECT aprovado FROM agentes WHERE nome=?", (nome,)).fetchone()
                ocupado = c.execute("SELECT 1 FROM pedidos WHERE estado='executando' AND agente=?", (nome,)).fetchone()
                if not a or not a["aprovado"] or ocupado: c.execute("COMMIT"); return None
                p = c.execute("SELECT * FROM pedidos WHERE estado='pendente' AND cancelar=0 AND (preferido IS NULL OR preferido=?) "
                              "ORDER BY (preferido IS NULL), criado_em LIMIT 1", (nome,)).fetchone()
                if not p: c.execute("COMMIT"); return None
                c.execute("UPDATE pedidos SET estado='executando', agente=?, tentativas=tentativas+1, iniciado_em=?, progresso=1, "
                          "etapa='iniciando', detalhe=? WHERE id=? AND estado='pendente'", (nome, agora(), f"agente {nome}", p["id"]))
                c.execute("UPDATE agentes SET estado='ocupado', job=?, visto_em=? WHERE nome=?", (p["id"], agora(), nome))
                c.execute("COMMIT")
                return self.pedido(p["id"])
            except Exception:
                c.execute("ROLLBACK"); raise

    def pedido(self, pid):
        with self._c() as c:
            r = c.execute("SELECT * FROM pedidos WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None

    def _do_agente(self, pid, nome):
        p = self.pedido(pid)
        if not p: raise ValueError(f"Pedido inexistente: {pid}")
        if p["agente"] != nome: raise ValueError(f"O pedido {pid} está com {p['agente'] or 'ninguém'}, não com {nome}.")
        return p

    def progresso(self, pid, nome, pct=None, etapa=None, detalhe=None):
        """Atualiza o pedido e o sinal de vida. Retorna False se a Central pediu cancelamento."""
        p = self._do_agente(pid, nome)
        if p["cancelar"] or p["estado"] != "executando": return False
        with self._c() as c:
            c.execute("UPDATE pedidos SET progresso=?, etapa=COALESCE(?,etapa), detalhe=COALESCE(?,detalhe) WHERE id=?",
                      (max(p["progresso"] or 0, min(99, int(pct if pct is not None else p["progresso"] or 0))), etapa, detalhe, pid))
            c.execute("UPDATE agentes SET estado='ocupado', job=?, visto_em=? WHERE nome=?", (pid, agora(), nome))
        return True

    def concluir(self, pid, nome, resultado):
        p = self._do_agente(pid, nome)
        if p["estado"] != "executando": raise ValueError(f"Pedido {pid} está '{p['estado']}'.")
        with self._c() as c:
            c.execute("UPDATE pedidos SET estado='concluida', progresso=100, etapa='concluído', resultado=?, fim=? WHERE id=?",
                      (json.dumps(resultado, ensure_ascii=False), agora(), pid))
            c.execute("UPDATE agentes SET estado='ocioso', job=NULL, visto_em=? WHERE nome=?", (agora(), nome))

    def falhar(self, pid, nome, erro):
        self._do_agente(pid, nome)
        with self._c() as c:
            c.execute("UPDATE pedidos SET estado=CASE WHEN cancelar=1 THEN 'cancelada' ELSE 'erro' END, erro=?, fim=? WHERE id=?",
                      (str(erro)[:1000], agora(), pid))
            c.execute("UPDATE agentes SET estado='ocioso', job=NULL, visto_em=? WHERE nome=?", (agora(), nome))

    def cancelar(self, pid):
        with self._c() as c:
            p = c.execute("SELECT estado FROM pedidos WHERE id=?", (pid,)).fetchone()
            if not p or p["estado"] not in ("pendente", "executando"): return False
            c.execute("UPDATE pedidos SET cancelar=1, estado=CASE WHEN estado='pendente' THEN 'cancelada' ELSE estado END, "
                      "etapa='cancelamento solicitado', fim=CASE WHEN estado='pendente' THEN ? ELSE fim END WHERE id=?", (agora(), pid))
        return True

    def pedidos(self, horas=24):
        limite = (datetime.datetime.now() - datetime.timedelta(hours=horas)).isoformat()
        with self._c() as c:
            self._recolher_abandonados(c)
            return [dict(r) for r in c.execute("SELECT * FROM pedidos WHERE estado IN ('pendente','executando') OR criado_em >= ? "
                                               "ORDER BY criado_em DESC", (limite,))]

    def como_tarefa(self, p):
        """Formato das tarefas da Central (a interface atual mostra os pedidos sem alteração)."""
        estado = {"pendente": "na_fila", "executando": "executando"}.get(p["estado"], p["estado"])
        etapa = p["etapa"] or ""
        if p["estado"] == "pendente":
            livres = [a["nome"] for a in self.agentes() if a["estado"] == "ocioso"]
            etapa = ("na fila — " + aviso_fora_expediente(self.ws) if not em_expediente(self.ws)
                     else f"aguardando agente de plantão ({len(livres)} ocioso(s))" if livres
                     else "aguardando agente de plantão — nenhum agente ativo no momento")
        res = json.loads(p["resultado"]) if p.get("resultado") else None
        return {"id": p["id"], "tipo": "ia", "titulo": f"{ACOES[p['acao']][0]} — {p['caso']}", "usuario": p["solicitante"],
                "caso": p["caso"], "acao": p["acao"], "status": estado, "progresso": p["progresso"] or 0, "etapa": etapa,
                "detalhe": ((f"agente {p['agente']} · " if p["agente"] else "") + (p["detalhe"] or "")).strip(" ·"),
                "inicio": p["iniciado_em"] or p["criado_em"], "fim": p["fim"], "erro": p["erro"], "resultado": res,
                "observacoes": p["observacoes"], "agente": p["agente"]}


# ------------------------------------------------------------------ executores automáticos
def claude_exe():
    base = os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude-code")
    try:
        vs = sorted((d for d in os.listdir(base) if os.path.exists(os.path.join(base, d, "claude.exe"))),
                    key=lambda v: [int(x) for x in re.findall(r"\d+", v)])
        return os.path.join(base, vs[-1], "claude.exe") if vs else None
    except OSError:
        return None


def codex_exe():
    for p in (os.path.join(os.environ.get("USERPROFILE", ""), ".codex", ".sandbox-bin", "codex.exe"),):
        if os.path.exists(p): return p
    from shutil import which
    return which("codex")


def provedor_pronto(tipo):
    """(pronto, motivo). Só reserva pedido quem está instalado e logado."""
    try:
        if tipo == "simulado":
            return (os.environ.get("CPJ_PLANTAO_SIMULADO") == "1", "somente em teste")
        if tipo == "claude":
            exe = claude_exe()
            if not exe: return False, "Claude Code não instalado"
            j = json.loads(subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True, timeout=30,
                                          creationflags=SEM_JANELA).stdout or "{}")
            return (True, "") if j.get("loggedIn") else (False, "Claude sem login (Sistema → Entrar no Claude)")
        if tipo == "codex":
            exe = codex_exe()
            if not exe: return False, "Codex CLI não encontrado"
            r = subprocess.run([exe, "login", "status"], capture_output=True, text=True, timeout=30, creationflags=SEM_JANELA)
            return (True, "") if "logged in" in (r.stdout + r.stderr).lower() else (False, "Codex sem login")
    except Exception as e:
        return False, f"verificação falhou: {e}"
    return False, f"tipo {tipo} não tem modo automático (use o modo chat)"


def _matar(p):
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, creationflags=SEM_JANELA)


def executar_pedido(pl, job, nome, tipo):
    """Executa um pedido com o CLI do agente (modo automático). Lança exceção em falha."""
    ws, id_, acao = pl.ws, job["caso"], job["acao"]
    prompt = montar_prompt(job, ws, "auto")
    dlog = os.path.join(ws, "casos", id_, "ia-logs"); os.makedirs(dlog, exist_ok=True)
    log = os.path.join(dlog, f"{datetime.datetime.now():%Y%m%d-%H%M%S}-{acao}-{tipo}.jsonl")
    ultima = os.path.join(dlog, f"{os.path.basename(log)}.resposta.txt")
    pfile = os.path.join(ws, "casos", id_, "ia-progresso.json")
    if os.path.exists(pfile): os.remove(pfile)
    if tipo == "claude":
        cmd = [claude_exe(), "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits",
               "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Task", "TodoWrite",
               "Bash(python *)", "Bash(python.exe *)", "PowerShell(python *)", "PowerShell(python.exe *)",
               "--disallowedTools", "WebFetch", "WebSearch", "--strict-mcp-config"]
    elif tipo == "codex":
        # sandbox workspace-write: comandos escrevem só no workspace e sem rede
        cmd = [codex_exe(), "exec", "-C", ws, "-s", "workspace-write", "--skip-git-repo-check", "--json", "-o", ultima, prompt]
    elif tipo == "simulado":   # somente testes automatizados (CPJ_PLANTAO_SIMULADO=1)
        cmd = [sys.executable, "-c", os.environ.get("CPJ_PLANTAO_SIMULADO_CMD", "import time; time.sleep(2); print('{\"type\": \"result\", \"subtype\": \"success\", \"result\": \"ok\"}')")]
    else:
        raise RuntimeError(f"Tipo {tipo} sem modo automático.")
    env = dict(os.environ, CPJ_WORKSPACE=ws, PYTHONIOENCODING="utf-8")
    inicio = time.time()
    p = subprocess.Popen(cmd, cwd=ws, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace", creationflags=SEM_JANELA)
    acoes, ultimo, resultado, cancelado = 0, "", None, [False]

    def vigia():   # sinal de vida + cancelamento mesmo quando o CLI fica em silêncio
        while p.poll() is None:
            pct, etapa = None, None
            if os.path.exists(pfile):
                try: pj = json.load(open(pfile, encoding="utf-8")); pct, etapa = int(pj["pct"]), pj["etapa"]
                except Exception: pass
            det = f"{acoes} ações · {int(time.time() - inicio) // 60} min" + (f" · última: {ultimo}" if ultimo else "")
            if not pl.progresso(job["id"], nome, pct, etapa, det):
                cancelado[0] = True; _matar(p); return
            time.sleep(4)
    threading.Thread(target=vigia, daemon=True).start()
    with open(log, "w", encoding="utf-8") as lg:
        for ln in p.stdout:
            lg.write(ln)
            try: ev = json.loads(ln)
            except ValueError: continue
            msg = ev.get("msg") if isinstance(ev.get("msg"), dict) else {}
            t = str(ev.get("type") or msg.get("type") or "")
            if ev.get("type") == "assistant":
                for c in ev.get("message", {}).get("content", []):
                    if c.get("type") == "tool_use":
                        acoes += 1; inp = c.get("input") or {}
                        alvo = inp.get("file_path") or inp.get("command") or inp.get("skill") or inp.get("description") or ""
                        ultimo = f"{c.get('name')}: {str(alvo)[:70]}"
            elif ev.get("type") == "result":
                resultado = ev
            elif re.search(r"command|exec|tool|patch|file", t or "", re.I):
                acoes += 1; ultimo = (t or "")[:60]
    p.wait()
    if cancelado[0] or (pl.pedido(job["id"]) or {}).get("cancelar"): raise RuntimeError("Cancelado pela Central.")
    if tipo in ("claude", "simulado"):
        if not resultado or resultado.get("is_error") or resultado.get("subtype") != "success":
            raise RuntimeError(f"Agente não concluiu: {str((resultado or {}).get('result') or p.returncode)[:300]} "
                               f"(log: {os.path.relpath(log, ws)})")
        resumo = resultado.get("result") or ""
    else:
        if p.returncode != 0: raise RuntimeError(f"Codex terminou com código {p.returncode} (log: {os.path.relpath(log, ws)})")
        resumo = open(ultima, encoding="utf-8", errors="replace").read() if os.path.exists(ultima) else ""
    return {"resumo": resumo[:1500], "log": os.path.relpath(log, ws)}


def pos_processar(ws, id_, acao):
    """Garantia: DOCX da minuta mais recente e reindexação — não depende do agente."""
    extra = {}
    if acao in ("relatorio", "completo"):
        sys.path.insert(0, AQUI)
        from tarefas import gerar_docx
        d = os.path.join(ws, "casos", id_, "03-relatorios")
        mins = sorted((f for f in os.listdir(d) if re.match(r"minuta-v\d+\.md$", f)), key=lambda f: int(re.findall(r"\d+", f)[0])) \
            if os.path.isdir(d) else []
        if mins:
            m = mins[-1]; v = re.findall(r"\d+", m)[0]; docx = os.path.join(d, f"RELATORIO-{id_}-v{v}.docx")
            if not os.path.exists(docx) or os.path.getmtime(docx) < os.path.getmtime(os.path.join(d, m)):
                gerar_docx(ws, id_, m)
            extra = {"minuta": m, "docx": os.path.basename(docx)}
        else:
            extra = {"aviso": "nenhuma minuta encontrada"}
    subprocess.run([sys.executable, os.path.join(S_BASE, "indexar.py")], env=dict(os.environ, CPJ_WORKSPACE=ws, PYTHONIOENCODING="utf-8"),
                   capture_output=True, creationflags=SEM_JANELA)
    return extra


def trabalhar(ws, nome, tipo, parar=None, aprovado=None, intervalo=3):
    """Laço do agente automático: sinal de vida, reserva quando ocioso e pronto, executa, devolve o resultado."""
    pl = Plantao(ws)
    pl.registrar(nome, tipo, "auto", aprovado=aprovado)
    ultimo_teste, pronto, motivo = 0, False, ""
    while not (parar and parar.is_set()):
        if not em_expediente(ws):   # não reserva nada fora do horário (um pedido já iniciado termina normalmente)
            pl.sinal(nome, "fora do expediente", aviso_fora_expediente(ws))
            (parar.wait(max(intervalo, 30)) if parar else time.sleep(max(intervalo, 30)))
            continue
        if time.time() - ultimo_teste > 60:
            pronto, motivo = provedor_pronto(tipo); ultimo_teste = time.time()
        job = None
        if pronto:
            pl.sinal(nome, "ocioso", "")
            job = pl.reivindicar(nome)
        else:
            pl.sinal(nome, "indisponível", motivo)
        if job:
            try:
                res = executar_pedido(pl, job, nome, tipo)
                res.update(pos_processar(ws, job["caso"], job["acao"]))
                pl.concluir(job["id"], nome, res)
            except Exception as e:
                pl.falhar(job["id"], nome, str(e))
            continue
        (parar.wait(intervalo) if parar else time.sleep(intervalo))
