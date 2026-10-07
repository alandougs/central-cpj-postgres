"""Executores de API para os agentes configurados pelo administrador.

As chaves são lidas da configuração local e nunca entram nos logs. As chamadas
de trabalho enviam ao provedor somente o que o agente lê da pasta do caso.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


PROVEDORES_API = {"openai", "anthropic", "gemini", "deepseek", "xai", "openrouter"}
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def configuracao(ws, provedor):
    caminho = os.path.join(ws, "config", "chaves_llm.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            cfg = json.load(f)
        d = cfg.get(provedor) or {}
        if d.get("ativo") and d.get("chave") and d.get("modelo"):
            return {"chave": d["chave"], "modelo": d["modelo"]}
    except (OSError, ValueError, TypeError):
        pass
    return None


def _dentro(raiz, caminho):
    raiz = os.path.realpath(raiz)
    alvo = os.path.realpath(os.path.join(raiz, caminho))
    return alvo == raiz or alvo.startswith(raiz + os.sep)


def _case_path(ws, caso, relativo, escrita=False):
    if not isinstance(caso, str) or caso in (".", "..") or not re.fullmatch(r"[\w.\-]+", caso, re.A):
        raise ValueError("Identificador de caso inválido.")
    if not isinstance(relativo, str) or not relativo or os.path.isabs(relativo) or ":" in relativo:
        raise ValueError("Informe um caminho relativo dentro da pasta do caso.")
    partes = relativo.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in partes) or partes[0].casefold() == "00-originais":
        raise ValueError("Esse caminho não pode ser acessado pelo agente.")
    if not escrita and partes[0] not in ("01-extracao", "02-analise", "03-relatorios", "caso.json", "registro-tratamento.md"):
        raise ValueError("O agente só pode ler extrações, análises e relatórios deste caso.")
    if "ia-logs" in partes or ".git" in partes or "__pycache__" in partes:
        raise ValueError("Esse caminho não pode ser acessado pelo agente.")
    if escrita and (len(partes) < 2 or partes[0] not in ("02-analise", "03-relatorios")):
        raise ValueError("O agente só pode gravar em 02-analise e 03-relatorios.")
    if escrita and os.path.splitext(partes[-1])[1].lower() not in (".md", ".csv", ".json", ".txt"):
        raise ValueError("O agente só pode gravar Markdown, CSV, JSON e texto.")
    if not escrita and os.path.splitext(partes[-1])[1].lower() not in (".md", ".csv", ".json", ".txt"):
        raise ValueError("O agente só pode ler Markdown, CSV, JSON e texto extraídos.")
    raiz = os.path.join(ws, "casos", caso)
    if not _dentro(os.path.join(ws, "casos"), raiz):
        raise ValueError("Pasta do caso fora do workspace.")
    alvo = os.path.realpath(os.path.join(raiz, *partes))
    if not _dentro(raiz, alvo):
        raise ValueError("Caminho fora da pasta do caso.")
    # Verificar também o destino real: um alias dentro do caso pode apontar aos originais.
    resolvido = os.path.relpath(alvo, os.path.realpath(raiz)).split(os.sep)
    permitidos = ("02-analise", "03-relatorios") if escrita else (
        "01-extracao", "02-analise", "03-relatorios", "caso.json", "registro-tratamento.md")
    if resolvido[0] not in permitidos or any(p in ("00-originais", "ia-logs", ".git", "__pycache__") for p in resolvido):
        raise ValueError("Esse destino não pode ser acessado pelo agente.")
    if escrita and len(resolvido) < 2:
        raise ValueError("O agente só pode gravar em análises e relatórios.")
    if os.path.splitext(alvo)[1].lower() not in (".md", ".csv", ".json", ".txt"):
        raise ValueError("O destino deve ser Markdown, CSV, JSON ou texto.")
    return raiz, alvo


def _listar(ws, caso):
    raiz = os.path.join(ws, "casos", caso)
    saida = []
    for pasta, dirs, arquivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in ("00-originais", "ia-logs", ".git", "__pycache__")]
        for nome in arquivos:
            if os.path.splitext(nome)[1].lower() in (".md", ".csv", ".json", ".txt"):
                p = os.path.join(pasta, nome)
                relativo = os.path.relpath(p, raiz).replace("\\", "/")
                try:
                    _case_path(ws, caso, relativo)
                except ValueError:
                    continue
                saida.append(relativo)
                if len(saida) >= 1500:
                    return sorted(saida)
    return sorted(saida)


def _tool(ws, caso, nome, args):
    if nome == "listar_arquivos":
        return _listar(ws, caso)
    if nome == "ler_arquivo":
        _, caminho = _case_path(ws, caso, args.get("caminho"))
        if not os.path.isfile(caminho):
            raise ValueError("Arquivo não encontrado.")
        inicio = max(1, min(10_000_000, int(args.get("linha_inicial", 1))))
        qtd = max(1, min(500, int(args.get("quantidade_linhas", 250))))
        with open(caminho, encoding="utf-8", errors="replace") as f:
            linhas = f.readlines()
        trecho = linhas[inicio - 1:inicio - 1 + qtd]
        return {"total_linhas": len(linhas), "linha_inicial": inicio,
                "conteudo": "".join(f"{inicio+i}: {s}" for i, s in enumerate(trecho))}
    if nome == "gravar_arquivo":
        _, caminho = _case_path(ws, caso, args.get("caminho"), escrita=True)
        conteudo = args.get("conteudo")
        if not isinstance(conteudo, str) or len(conteudo) > 2_000_000:
            raise ValueError("Conteúdo ausente ou maior que 2 MB.")
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        temporario = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=os.path.dirname(caminho), prefix=".cpj-", suffix=".tmp",
                                             delete=False) as f:
                temporario = f.name
                f.write(conteudo)
            os.replace(temporario, caminho)
        finally:
            if temporario and os.path.exists(temporario):
                os.remove(temporario)
        return {"ok": True, "caminho": os.path.relpath(caminho, os.path.join(ws, "casos", caso)).replace("\\", "/")}
    if nome == "gerar_docx":
        minuta = args.get("minuta") or ""
        if not re.fullmatch(r"minuta-v\d+\.md", minuta):
            raise ValueError("Informe o nome de uma minuta-vNN.md existente.")
        pasta = os.path.join(ws, "casos", caso, "03-relatorios")
        _, fonte = _case_path(ws, caso, "03-relatorios/" + minuta)
        if os.path.dirname(fonte) != os.path.abspath(pasta):
            raise ValueError("A pasta de relatórios não pode redirecionar a geração de DOCX.")
        if not os.path.isfile(fonte):
            raise ValueError("Minuta não encontrada em 03-relatorios.")
        from pathlib import Path
        script = Path(__file__).resolve().parents[1] / "skills" / "relatorio-ip-fraude" / "scripts" / "gerar_docx.py"
        destino = os.path.join(pasta, "RELATORIO-" + caso + "-v" + re.search(r"\d+", minuta).group() + ".docx")
        if os.path.realpath(destino) != os.path.abspath(destino):
            raise ValueError("O destino do DOCX não pode ser um link simbólico.")
        r = subprocess.run([sys.executable, str(script), fonte, "--saida", destino], cwd=ws, timeout=180,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=SEM_JANELA,
                           env=dict(os.environ, CPJ_WORKSPACE=ws, PYTHONIOENCODING="utf-8"))
        if r.returncode:
            raise ValueError((r.stderr or r.stdout)[-1200:])
        return {"ok": True, "docx": os.path.relpath(destino, os.path.join(ws, "casos", caso)).replace("\\", "/"),
                "mensagem": (r.stdout or "")[-1000:]}
    raise ValueError("Ferramenta não reconhecida.")


PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_IA_PADRAO = {"modo_padrao": "agente", "provedor_api": "", "prompt_sistema": ""}
AGENTES_POR_ACAO = {
    "analisar": ["analista-documental"], "financeiro": ["analista-financeiro"], "revisar": ["revisor-de-relatorio"],
    "relatorio": [], "completo": ["analista-documental", "analista-financeiro"],
    "esteira": ["analista-documental", "analista-financeiro", "revisor-de-relatorio"],
}
SKILLS_POR_ACAO = {
    "analisar": ["analise-ip-fraude"], "financeiro": ["analise-ip-fraude"], "relatorio": ["relatorio-ip-fraude"],
    "revisar": ["relatorio-ip-fraude"], "completo": ["analise-ip-fraude", "relatorio-ip-fraude"],
    "esteira": ["analise-ip-fraude", "relatorio-ip-fraude"],
}


def config_ia(ws):
    """config/ia.json: modo padrão (agente|api), provedor da API e prompt de sistema do investigador."""
    cfg = dict(CONFIG_IA_PADRAO)
    try:
        with open(os.path.join(ws, "config", "ia.json"), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            cfg.update({k: d[k] for k in CONFIG_IA_PADRAO if isinstance(d.get(k), str)})
    except (OSError, ValueError):
        pass
    return cfg


def salvar_config_ia(ws, dados):
    cfg = config_ia(ws)
    if dados.get("modo_padrao") in ("agente", "api"):
        cfg["modo_padrao"] = dados["modo_padrao"]
    if "provedor_api" in dados:
        prov = str(dados["provedor_api"] or "").strip().lower()
        if prov and prov not in PROVEDORES_API:
            raise ValueError("Provedor de API desconhecido.")
        cfg["provedor_api"] = prov
    if "prompt_sistema" in dados:
        cfg["prompt_sistema"] = str(dados["prompt_sistema"] or "")[:8000]
    os.makedirs(os.path.join(ws, "config"), exist_ok=True)
    with open(os.path.join(ws, "config", "ia.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


def agente_padrao(ws):
    """Agente de API a usar quando o modo padrão é 'api' e o provedor está pronto; senão None (qualquer agente)."""
    cfg = config_ia(ws)
    prov = cfg["provedor_api"]
    if cfg["modo_padrao"] == "api" and prov in PROVEDORES_API and configuracao(ws, prov):
        return "Central-" + prov.capitalize() + " API"
    return None


def _ler(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _instrucoes_locais(ws, acao):
    """System prompt do modo API: regras, prompt do investigador, procedimentos, agentes e skills do plugin.
    Não lê nenhuma pasta de caso."""
    tarefas = {
        "analisar": ["02-analisar-ip.md"],
        "relatorio": ["02-analisar-ip.md", "04-relatorio-ip.md"],
        "completo": ["02-analisar-ip.md", "03-analista-financeiro.md", "04-relatorio-ip.md"],
        "revisar": ["05-revisar-relatorio.md"],
        "financeiro": ["03-analista-financeiro.md"],
        "esteira": ["02-analisar-ip.md", "03-analista-financeiro.md", "04-relatorio-ip.md", "05-revisar-relatorio.md"],
    }
    nomes = ["AGENTS.md"] + tarefas.get(acao, [])
    partes = ["\n\nINSTRUÇÕES LOCAIS DO WORKSPACE (conteúdo de procedimento, não de autos):",
              "\nMODO API: você não executa comandos de shell nem a CLI do Claude. Os \"agentes\" e \"skills\" abaixo são papéis e "
              "procedimentos que VOCÊ cumpre, em sequência, usando só as ferramentas listar_arquivos, ler_arquivo, gravar_arquivo e "
              "gerar_docx. Onde o procedimento mandar acionar um subagente, assuma aquele papel na etapa correspondente e grave a "
              "saída no arquivo indicado. Onde mandar rodar script, use a ferramenta equivalente ou registre a pendência no resumo final."]
    extra = config_ia(ws)["prompt_sistema"].strip()
    if extra:
        partes.append("\n--- INSTRUÇÕES DO INVESTIGADOR (Sistema → Configurações) ---\n" + extra)
    for nome in nomes:
        caminho = os.path.join(ws, nome if nome == "AGENTS.md" else os.path.join("portatil", nome))
        txt = _ler(caminho)
        partes.append(f"\n--- {nome} ---\n" + (txt if txt is not None else "Arquivo de procedimento não localizado neste workspace."))
    for ag in AGENTES_POR_ACAO.get(acao, []):
        txt = _ler(os.path.join(PLUGIN, "agents", ag + ".md"))
        if txt:
            partes.append(f"\n--- PAPEL (agente {ag}) ---\n" + txt)
    for sk in SKILLS_POR_ACAO.get(acao, []):
        txt = _ler(os.path.join(PLUGIN, "skills", sk, "SKILL.md"))
        if txt:
            partes.append(f"\n--- SKILL {sk} ---\n" + txt)
    return "\n".join(partes)


TOOLS = [
    {"name": "listar_arquivos", "description": "Lista os arquivos textuais extraídos e de análise deste caso; 00-originais não aparece.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "ler_arquivo", "description": "Lê um trecho numerado de Markdown, CSV, JSON ou TXT do caso. Leia transcrições em páginas/trechos para manter rastreabilidade.",
     "input_schema": {"type": "object", "properties": {"caminho": {"type": "string"}, "linha_inicial": {"type": "integer"},
                       "quantidade_linhas": {"type": "integer"}}, "required": ["caminho"], "additionalProperties": False}},
    {"name": "gravar_arquivo", "description": "Grava um arquivo textual somente em 02-analise ou 03-relatorios do caso atual.",
     "input_schema": {"type": "object", "properties": {"caminho": {"type": "string"}, "conteudo": {"type": "string"}},
                      "required": ["caminho", "conteudo"], "additionalProperties": False}},
    {"name": "gerar_docx", "description": "Gera o DOCX CPJ a partir de uma minuta-vNN.md já gravada em 03-relatorios.",
     "input_schema": {"type": "object", "properties": {"minuta": {"type": "string"}}, "required": ["minuta"], "additionalProperties": False}},
]


def _openai_tools():
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                   "parameters": t["input_schema"], "strict": False}}
            for t in TOOLS]


def _responses_tools():
    return [{"type": "function", "name": t["name"], "description": t["description"],
             "parameters": t["input_schema"], "strict": False}
            for t in TOOLS]


def _http_json(url, headers, body=None, timeout=90):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read(24 * 1024 * 1024).decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"O provedor recusou o pedido (HTTP {e.code}).") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("Falha de conexão ou resposta inválida do provedor configurado.") from None


def executar(ws, job, nome, provedor, config, pl):
    """Roda uma sessão com chamadas de ferramenta locais limitadas ao caso."""
    import plantao as PL
    prompt = PL.montar_prompt(job, ws, "api", nome) + _instrucoes_locais(ws, job["acao"])
    prompt += ("\n\nVocê está conectado por API. Não existe terminal nem acesso geral ao disco. Use somente as ferramentas "
               "listar_arquivos, ler_arquivo, gravar_arquivo e gerar_docx. Os caminhos de leitura são relativos ao caso; "
               "grave resultados em 02-analise ou 03-relatorios. Não solicite nem tente acesso à internet. As citações devem "
               "apontar às páginas/fls. encontradas na extração. Prossiga até gravar os artefatos pedidos e entregar um resumo.")
    model, key = config["modelo"], config["chave"]
    if provedor == "openai":
        # GPT-6.1 Sol and Astra need Responses API for function/tool calling.
        url = "https://api.openai.com/v1/responses"
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        estilo = "openai_responses"
    elif provedor == "deepseek":
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        estilo = "openai"
    elif provedor == "xai":
        url = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        estilo = "openai"
    elif provedor == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json",
                   "HTTP-Referer": "http://127.0.0.1:8765", "X-Title": "Central CPJ"}
        estilo = "openai"
    elif provedor == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        estilo = "anthropic"
    elif provedor == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        estilo = "gemini"
    else:
        raise RuntimeError("Executor API não reconhecido.")

    logdir = os.path.join(ws, "casos", job["caso"], "ia-logs")
    os.makedirs(logdir, exist_ok=True)
    logpath = os.path.join(logdir, f"{int(time.time())}-{job['acao']}-{provedor}.log")
    log = open(logpath, "w", encoding="utf-8")
    chamadas = [0]
    parar = threading.Event()
    cancelado = threading.Event()

    def vigia():
        while not parar.wait(12):
            if not pl.progresso(job["id"], nome, detalhe=f"API {provedor}/{model} · {chamadas[0]} ferramenta(s)"):
                cancelado.set()
                return

    threading.Thread(target=vigia, daemon=True).start()

    def invoke(tool_name, arguments):
        chamadas[0] += 1
        pl.progresso(job["id"], nome, min(95, 10 + chamadas[0] * 3),
                     f"{provedor}: {tool_name}", f"{chamadas[0]} ferramenta(s)")
        log.write(f"ferramenta {chamadas[0]}: {tool_name}\n"); log.flush()
        try:
            return _tool(ws, job["caso"], tool_name, arguments)
        except Exception as e:
            return {"erro": str(e)}

    try:
        if estilo == "openai_responses":
            previous = None
            entrada = [{"role": "user", "content": "Inicie a tarefa e use ferramentas para consultar as fontes do caso."}]
            for _ in range(80):
                if cancelado.is_set() or (pl.pedido(job["id"]) or {}).get("cancelar"):
                    raise RuntimeError("Cancelado pela Central.")
                payload = {"model": model, "instructions": prompt, "input": entrada, "tools": _responses_tools(),
                           "tool_choice": "auto", "max_output_tokens": 12000}
                if previous: payload["previous_response_id"] = previous
                r = _http_json(url, headers, payload)
                previous = r.get("id")
                itens = r.get("output") or []
                calls = [x for x in itens if x.get("type") == "function_call"]
                if not calls:
                    resumo = "\n".join(part.get("text", "") for item in itens if item.get("type") == "message"
                                        for part in item.get("content", []) if part.get("type") == "output_text")
                    break
                entrada = []
                for call in calls:
                    try: args = json.loads(call.get("arguments") or "{}")
                    except ValueError: args = {}
                    saida = invoke(call.get("name"), args)
                    entrada.append({"type": "function_call_output", "call_id": call.get("call_id"),
                                    "output": json.dumps(saida, ensure_ascii=False)})
            else:
                raise RuntimeError("O agente atingiu o limite de iterações de ferramentas.")
        elif estilo == "openai":
            messages = [{"role": "system", "content": prompt}, {"role": "user", "content": "Inicie a tarefa e use ferramentas para consultar as fontes do caso."}]
            for _ in range(80):
                if cancelado.is_set() or (pl.pedido(job["id"]) or {}).get("cancelar"):
                    raise RuntimeError("Cancelado pela Central.")
                r = _http_json(url, headers, {"model": model, "messages": messages, "tools": _openai_tools(),
                                               "tool_choice": "auto", "max_tokens": 12000})
                msg = r["choices"][0]["message"]
                messages.append(msg)
                calls = msg.get("tool_calls") or []
                if not calls:
                    resumo = msg.get("content") or ""
                    break
                for call in calls:
                    fn = call.get("function") or {}
                    try: args = json.loads(fn.get("arguments") or "{}")
                    except ValueError: args = {}
                    saida = invoke(fn.get("name"), args)
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": json.dumps(saida, ensure_ascii=False)})
            else:
                raise RuntimeError("O agente atingiu o limite de iterações de ferramentas.")
        elif estilo == "anthropic":
            messages = [{"role": "user", "content": "Inicie a tarefa e use ferramentas para consultar as fontes do caso."}]
            anth_tools = [{"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]} for t in TOOLS]
            for _ in range(80):
                if cancelado.is_set() or (pl.pedido(job["id"]) or {}).get("cancelar"):
                    raise RuntimeError("Cancelado pela Central.")
                r = _http_json(url, headers, {"model": model, "max_tokens": 12000, "system": prompt,
                                               "messages": messages, "tools": anth_tools})
                blocks = r.get("content", []); messages.append({"role": "assistant", "content": blocks})
                calls = [b for b in blocks if b.get("type") == "tool_use"]
                if not calls:
                    resumo = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                    break
                results = []
                for call in calls:
                    saida = invoke(call.get("name"), call.get("input") or {})
                    results.append({"type": "tool_result", "tool_use_id": call["id"],
                                    "content": json.dumps(saida, ensure_ascii=False)})
                messages.append({"role": "user", "content": results})
            else:
                raise RuntimeError("O agente atingiu o limite de iterações de ferramentas.")
        else:
            contents = [{"role": "user", "parts": [{"text": "Inicie a tarefa e use ferramentas para consultar as fontes do caso."}]}]
            declarations = [{"name": t["name"], "description": t["description"], "parameters": t["input_schema"]} for t in TOOLS]
            for _ in range(80):
                if cancelado.is_set() or (pl.pedido(job["id"]) or {}).get("cancelar"):
                    raise RuntimeError("Cancelado pela Central.")
                r = _http_json(url, headers, {"systemInstruction": {"parts": [{"text": prompt}]}, "contents": contents,
                                               "tools": [{"functionDeclarations": declarations}],
                                               "generationConfig": {"maxOutputTokens": 12000}})
                cand = (r.get("candidates") or [{}])[0].get("content") or {"parts": []}
                parts = cand.get("parts", []); contents.append({"role": "model", "parts": parts})
                calls = [p.get("functionCall") for p in parts if p.get("functionCall")]
                if not calls:
                    resumo = "\n".join(p.get("text", "") for p in parts if p.get("text"))
                    break
                responses = []
                for call in calls:
                    saida = invoke(call.get("name"), call.get("args") or {})
                    responses.append({"functionResponse": {"name": call["name"], "response": {"result": saida}}})
                contents.append({"role": "user", "parts": responses})
            else:
                raise RuntimeError("O agente atingiu o limite de iterações de ferramentas.")
        if cancelado.is_set():
            raise RuntimeError("Cancelado pela Central.")
        log.write("execução concluída\n")
        return {"resumo": resumo[:1500], "log": os.path.relpath(logpath, ws), "provedor": provedor, "modelo": model}
    finally:
        parar.set()
        log.close()
