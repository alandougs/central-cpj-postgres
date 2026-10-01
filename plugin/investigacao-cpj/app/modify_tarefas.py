import os
import re

p = 'plugin/investigacao-cpj/app/tarefas.py'
with open(p, 'r', encoding='utf-8') as f:
    code = f.read()

# 1) Modificar init para ter fila e thread de indexacao, e armazenar erros
init_repl = """    def __init__(self, ws, caso_mod, auth, iniciar_agente=True):
        self.ws, self.C, self.auth = ws, caso_mod, auth
        self.t, self.trava, self.procs = {}, threading.Lock(), {}
        self.plantao = PL.Plantao(ws)
        self.parar_agente = threading.Event()
        self.erro_indexacao = None
        self._fila_idx = queue.Queue()
        threading.Thread(target=self._processar_indexacao, daemon=True).start()
"""
code = re.sub(r'    def __init__\(self, ws, caso_mod, auth, iniciar_agente=True\):.*?self\.parar_agente = threading\.Event\(\)', init_repl, code, flags=re.DOTALL)

# 2) Trocar indexar() para rodar na thread
idx_repl = """    def _processar_indexacao(self):
        while True:
            tid = self._fila_idx.get()
            if tid is None: break
            # Combinar pedidos redundantes: esvaziar fila até o momento
            tids = {tid}
            while not self._fila_idx.empty():
                try: 
                    t = self._fila_idx.get_nowait()
                    if t is None: return
                    tids.add(t)
                except: pass
            
            env = dict(os.environ, CPJ_WORKSPACE=self.ws, PYTHONIOENCODING="utf-8")
            r = subprocess.run([PY, os.path.join(S_BASE, "indexar.py")], env=env, capture_output=True, creationflags=SEM_JANELA)
            if r.returncode != 0:
                self.erro_indexacao = r.stderr.decode("utf-8", "replace")
                # Não falha as tarefas originais aqui porque já podem estar concluídas, o erro_indexacao é lido depois
            else:
                self.erro_indexacao = None

    def indexar(self):
        env = dict(os.environ, CPJ_WORKSPACE=self.ws, PYTHONIOENCODING="utf-8")
        r = subprocess.run([PY, os.path.join(S_BASE, "indexar.py")], env=env, capture_output=True, creationflags=SEM_JANELA)
        if r.returncode != 0:
            raise RuntimeError(f"Erro na indexação (código {r.returncode}): {r.stderr.decode('utf-8', 'replace')}")

    def pedir_indexacao(self, tid):
        self._fila_idx.put(tid)
"""
code = re.sub(r'    def indexar\(self\):.*?creationflags=SEM_JANELA\)', idx_repl, code, flags=re.DOTALL)

# 3) Modificar importar()
importar_repl = """    def importar(self, tid, zip_path):
        W = self.ws
        import tempfile
        with zipfile.ZipFile(zip_path) as z:
            try: man = json.loads(z.read("manifest.json"))
            except KeyError: raise ValueError("Pacote inválido: manifest.json ausente (use um arquivo exportado pela Central CPJ).")
            if man.get("schema") != EXPORT_SCHEMA: raise ValueError(f"Versão de pacote não suportada: {man.get('schema')}")
            arqs = man["arquivos"]; total = sum(a["tamanho"] for a in arqs) or 1; feito = 0
            
            permitidos = {"casos", "calibracao", "consulta", "referencias", "producao", "modelos"}
            for a in arqs:
                r = a["caminho"]; partes = r.split("/")
                if ".." in partes: raise ValueError(f"Caminho inseguro no pacote: {r}")
                if not partes or partes[0] not in permitidos: raise ValueError(f"Pacote com caminho não permitido: {r}")

            # 1) integridade
            for i, a in enumerate(arqs, 1):
                if self.obter(tid)["status"] == "cancelada": raise ValueError("Tarefa cancelada.")
                h = hashlib.sha256()
                with z.open("dados/" + a["caminho"]) as f:
                    for b in iter(lambda: f.read(1 << 20), b""):
                        h.update(b); feito += len(b)
                        self.at(tid, progresso=int(45 * feito / total), etapa=f"verificando integridade {i}/{len(arqs)}")
                if h.hexdigest() != a["sha256"]: raise ValueError(f"Arquivo corrompido no pacote: {a['caminho']}")
            
            # 2) decidir o que entra (nunca sobrescreve) e extração temporária atômica
            existentes = {d for d in os.listdir(os.path.join(W, "casos"))} if os.path.isdir(os.path.join(W, "casos")) else set()
            novos, pulados, feito, copiados = set(), set(), 0, 0
            raiz = os.path.normpath(W)
            
            with tempfile.TemporaryDirectory(prefix="cpj-import-") as tmpdir:
                raiz_tmp = os.path.normpath(tmpdir)
                for i, a in enumerate(arqs, 1):
                    if self.obter(tid)["status"] == "cancelada": raise ValueError("Tarefa cancelada.")
                    r = a["caminho"]; partes = r.split("/")
                    destino_final = os.path.normpath(os.path.join(W, *partes))
                    
                    if not destino_final.startswith(raiz + os.sep): raise ValueError(f"Caminho inseguro no pacote: {r}")
                    
                    if partes[0] == "casos" and len(partes) > 2:
                        if partes[1] in existentes and partes[1] not in novos: pulados.add(partes[1]); continue
                        novos.add(partes[1])
                    elif os.path.exists(destino_final):
                        if os.path.isfile(destino_final) and _sha(destino_final) == a["sha256"]: continue
                        if partes[0] == "calibracao":
                            destino_final = destino_final.replace(".md", f"-importado-{datetime.date.today():%Y%m%d}.md")
                            if os.path.exists(destino_final): continue
                        else:
                            continue
                            
                    destino_tmp = os.path.normpath(os.path.join(raiz_tmp, *partes))
                    os.makedirs(os.path.dirname(destino_tmp), exist_ok=True)
                    with z.open("dados/" + r) as f, open(destino_tmp, "wb") as w: shutil.copyfileobj(f, w, 1 << 20)
                    copiados += 1; feito += a["tamanho"]
                    self.at(tid, progresso=45 + int(45 * i / len(arqs)), etapa=f"extraindo {i}/{len(arqs)}")
                
                # Cópia final
                if self.obter(tid)["status"] == "cancelada": raise ValueError("Tarefa cancelada.")
                for b in os.listdir(raiz_tmp):
                    src_d = os.path.join(raiz_tmp, b)
                    if b == "casos":
                        os.makedirs(os.path.join(W, "casos"), exist_ok=True)
                        for c in os.listdir(src_d):
                            src_c = os.path.join(src_d, c)
                            dst_c = os.path.join(W, "casos", c)
                            if not os.path.exists(dst_c): os.rename(src_c, dst_c)
                    else:
                        for raiz_w, dirs, files in os.walk(src_d):
                            for arq in files:
                                p_src = os.path.join(raiz_w, arq)
                                rel = os.path.relpath(p_src, raiz_tmp)
                                p_dst = os.path.join(W, rel)
                                os.makedirs(os.path.dirname(p_dst), exist_ok=True)
                                if not os.path.exists(p_dst): os.rename(p_src, p_dst)
                                
        self.at(tid, progresso=92, etapa="reindexando a base")
        try:
            self.indexar()
        except Exception as e:
            _apagar(zip_path)
            return {"casos_novos": sorted(novos - pulados), "casos_ja_existentes": sorted(pulados), "arquivos": copiados, "alerta": "Arquivo importado; indexação pendente/falhou."}
            
        _apagar(zip_path)
        return {"casos_novos": sorted(novos - pulados), "casos_ja_existentes": sorted(pulados), "arquivos": copiados}
"""
code = re.sub(r'    def importar\(self, tid, zip_path\):.*?return \{"casos_novos": sorted\(novos - pulados\), "casos_ja_existentes": sorted\(pulados\), "arquivos": copiados\}', importar_repl, code, flags=re.DOTALL)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
