"""Usuários, perfis, senhas (PBKDF2), bloqueio por tentativas e auditoria da Central CPJ.
Arquivos em <workspace>\\config\\: usuarios.json, segredo.key, auditoria.log (JSON por linha).
"""
import datetime, hashlib, hmac, json, os, re, secrets, threading, time, unicodedata

PERFIS = {
    "admin": "Administrador",
    "investigador": "Investigador de Polícia",
    "delegado": "Delegado de Polícia",
    "escrivao": "Escrivão de Polícia",
}
# Permissões por perfil (o admin tem todas)
PERMISSOES = {
    "investigador": {"os", "casos", "trabalho", "ia", "pesquisa", "estatisticas", "dados", "relatorio_final"},
    "delegado": {"os", "casos", "pesquisa", "estatisticas", "relatorio_final"},
    "escrivao": {"os", "casos", "relatorio_final"},
}
TODAS = {"os", "casos", "trabalho", "ia", "pesquisa", "estatisticas", "dados", "relatorio_final", "usuarios", "rede"}
DESCRICAO = {
    "os": "Cadastrar O.S. e enviar arquivos", "casos": "Ver lista e status das O.S.", "trabalho": "Trabalhar nos casos (análise, minuta, DOCX, FINAL, baixa)",
    "ia": "Acionar agentes de IA", "pesquisa": "Pesquisa relacional e textual", "estatisticas": "Estatísticas e planilha",
    "dados": "Exportar/importar, bases de consulta e referências", "relatorio_final": "Baixar relatório FINAL",
    "usuarios": "Gerenciar usuários e auditoria (só admin)", "rede": "Configurar rede (só admin)",
}
ITERACOES = 240_000
_trava = threading.RLock()
_falhas = {}  # login -> [contagem, bloqueado_ate]


def _normalizar(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


class Auth:
    def __init__(self, ws):
        self.dir = os.path.join(ws, "config"); os.makedirs(self.dir, exist_ok=True)
        self.arq = os.path.join(self.dir, "usuarios.json")
        self.log = os.path.join(self.dir, "auditoria.log")

    # ---------------------------------------------------------------- persistência
    def segredo(self):
        p = os.path.join(self.dir, "segredo.key")
        if not os.path.exists(p):
            with open(p, "w") as f: f.write(secrets.token_hex(32))
        with open(p, encoding="utf-8") as f: return f.read().strip()

    def _ler(self):
        if not os.path.exists(self.arq): return {"usuarios": {}}
        with open(self.arq, encoding="utf-8") as f: return json.load(f)

    def _gravar(self, d):
        tmp = self.arq + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.arq)

    def tem_usuarios(self): return bool(self._ler()["usuarios"])

    # ---------------------------------------------------------------- senhas
    @staticmethod
    def _hash(senha, sal=None):
        sal = sal or secrets.token_hex(16)
        return sal, hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), ITERACOES).hex()

    @staticmethod
    def senha_valida(s):
        if len(s or "") < 8: return "A senha deve ter ao menos 8 caracteres."
        if s.isdigit() or s.isalpha(): return "Use letras e números na senha."
        return None

    # ---------------------------------------------------------------- usuários
    def salvar_usuario(self, login, nome, perfil, senha=None, ativo=True, cpf=None, email=None, cargo=None, temporaria=False):
        """temporaria=True: aceita senha fora da política e obriga a troca no primeiro acesso."""
        login = (login or "").strip().lower()
        if not login.replace(".", "").replace("_", "").isalnum(): raise ValueError("Login inválido (letras, números, ponto).")
        if perfil not in PERFIS: raise ValueError("Perfil inválido.")
        cpf_d = re.sub(r"\D", "", cpf or "") if cpf is not None else None
        if cpf_d and len(cpf_d) != 11: raise ValueError("CPF deve ter 11 dígitos.")
        email = (email or "").strip().lower() if email is not None else None
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): raise ValueError("E-mail inválido.")
        with _trava:
            d = self._ler(); u = d["usuarios"].get(login, {})
            if not u and not senha: raise ValueError("Informe a senha do novo usuário.")
            for k, v in d["usuarios"].items():
                if k == login: continue
                if cpf_d and v.get("cpf") == cpf_d: raise ValueError("CPF já cadastrado para outro usuário.")
                if email and v.get("email") == email: raise ValueError("E-mail já cadastrado para outro usuário.")
            if senha:
                if not temporaria:
                    erro = self.senha_valida(senha)
                    if erro: raise ValueError(erro)
                u["sal"], u["hash"] = self._hash(senha); u["trocar_senha"] = bool(temporaria)
                u["sessao_id"] = secrets.token_hex(32)
            if u.get("perfil") == "admin" and (perfil != "admin" or not ativo):
                admins = [k for k, v in d["usuarios"].items() if v.get("perfil") == "admin" and v.get("ativo", True)]
                if admins == [login]: raise ValueError("Não é possível remover o único administrador ativo.")
            if u.get("ativo", True) != bool(ativo):
                u["sessao_id"] = secrets.token_hex(32)
            u.update(nome=(nome or u.get("nome") or login).strip(), perfil=perfil, ativo=bool(ativo))
            if cpf_d is not None: u["cpf"] = cpf_d
            if email is not None: u["email"] = email
            if cargo is not None: u["cargo"] = cargo.strip()
            u.setdefault("criado_em", datetime.datetime.now().isoformat(timespec="seconds"))
            d["usuarios"][login] = u; self._gravar(d)
        return self.publico(login, u)

    def atualizar_contato(self, login, email=None, cargo=None):
        u = self._ler()["usuarios"][login]
        return self.salvar_usuario(login, u["nome"], u["perfil"], None, u.get("ativo", True), email=email, cargo=cargo)

    def ha_senha_temporaria(self):
        return [k for k, v in self._ler()["usuarios"].items() if v.get("ativo", True) and v.get("trocar_senha")]

    def resolver(self, identificador):
        """Login por usuário, CPF, e-mail institucional ou nome completo (quando único)."""
        i = (identificador or "").strip(); il = i.lower(); dig = re.sub(r"\D", "", i)
        us = self._ler()["usuarios"]
        if il in us: return il
        if len(dig) == 11 and re.fullmatch(r"[\d.\-\s]+", i):
            for k, v in us.items():
                if v.get("cpf") == dig: return k
        if "@" in il:
            for k, v in us.items():
                if v.get("email") == il: return k
        nn = _normalizar(i)
        achados = [k for k, v in us.items() if nn and _normalizar(v.get("nome")) == nn]
        return achados[0] if len(achados) == 1 else il

    def remover_usuario(self, login):
        with _trava:
            d = self._ler(); u = d["usuarios"].get(login)
            if not u: raise ValueError("Usuário inexistente.")
            if u.get("perfil") == "admin" and u.get("ativo", True) and not any(
                k != login and v.get("perfil") == "admin" and v.get("ativo", True)
                for k, v in d["usuarios"].items()
            ):
                raise ValueError("Não é possível remover o único administrador ativo.")
            del d["usuarios"][login]; self._gravar(d)

    @staticmethod
    def publico(login, u):
        cpf = u.get("cpf") or ""
        return {"login": login, "nome": u.get("nome"), "perfil": u.get("perfil"), "perfil_nome": PERFIS.get(u.get("perfil")),
                "cargo": u.get("cargo") or PERFIS.get(u.get("perfil")), "email": u.get("email") or "",
                "cpf_mascarado": f"***.{cpf[3:6]}.{cpf[6:9]}-**" if len(cpf) == 11 else "",
                "ativo": u.get("ativo", True), "trocar_senha": bool(u.get("trocar_senha")),
                "criado_em": u.get("criado_em"), "ultimo_acesso": u.get("ultimo_acesso")}

    def listar(self): return [self.publico(k, v) for k, v in sorted(self._ler()["usuarios"].items())]

    def obter(self, login):
        u = self._ler()["usuarios"].get(login)
        return self.publico(login, u) if u and u.get("ativo", True) else None

    def usuario_solo(self, login=None):
        """Administrador ativo escolhido; sem escolha, exige administrador ativo único."""
        if login is not None:
            u = self.obter(login) if isinstance(login, str) else None
            return u if u and u["perfil"] == "admin" else None
        admins = [(k, v) for k, v in self._ler()["usuarios"].items() if v.get("perfil") == "admin" and v.get("ativo", True)]
        return self.publico(*admins[0]) if len(admins) == 1 else None

    def obter_sessao(self, login, sessao_id):
        """O vínculo interno muda ao trocar senha, ativação ou recriar a conta."""
        u = self._ler()["usuarios"].get(login)
        atual = u.get("sessao_id") if u else None
        if (u and u.get("ativo", True) and isinstance(atual, str)
                and isinstance(sessao_id, str) and atual and sessao_id
                and hmac.compare_digest(atual, sessao_id)):
            return self.publico(login, u)
        return None

    def autenticar(self, identificador, senha):
        login = self.resolver(identificador)
        f = _falhas.get(login, [0, 0])
        if f[1] > time.time(): raise PermissionError(f"Muitas tentativas. Tente novamente em {int(f[1] - time.time()) // 60 + 1} min.")
        d = self._ler(); u = d["usuarios"].get(login)
        ok = bool(u and u.get("ativo", True) and hmac.compare_digest(self._hash(senha or "", u["sal"])[1], u["hash"]))
        if not ok:
            f[0] += 1
            if f[0] >= 5: f[:] = [0, time.time() + 300]
            _falhas[login] = f
            time.sleep(0.6)
            raise PermissionError("Usuário ou senha incorretos.")
        _falhas.pop(login, None)
        with _trava:
            d = self._ler(); atual = d["usuarios"].get(login)
            # Não vincular uma senha validada antes de uma redefinição concorrente.
            if (not atual or not atual.get("ativo", True)
                    or atual.get("sal") != u.get("sal") or atual.get("hash") != u.get("hash")):
                raise PermissionError("Conta alterada durante o login. Entre novamente.")
            atual.setdefault("sessao_id", secrets.token_hex(32))
            atual["ultimo_acesso"] = datetime.datetime.now().isoformat(timespec="seconds")
            self._gravar(d)
            return {**self.publico(login, atual), "_sessao_id": atual["sessao_id"]}

    def trocar_senha(self, login, atual, nova):
        self.autenticar(login, atual)
        if hmac.compare_digest(atual or "", nova or ""): raise ValueError("A nova senha deve ser diferente da atual.")
        u = self._ler()["usuarios"][login]
        self.salvar_usuario(login, u["nome"], u["perfil"], nova, u.get("ativo", True))
        return self.autenticar(login, nova)

    # ---------------------------------------------------------------- permissões (editáveis pelo admin) e auditoria
    def matriz(self):
        """Permissões por perfil: padrão do código sobrescrito por config\\perfis.json (editável na Central)."""
        p = os.path.join(self.dir, "perfis.json")
        m = {k: set(v) for k, v in PERMISSOES.items()}
        if os.path.exists(p):
            try:
                for perfil, perms in json.load(open(p, encoding="utf-8")).items():
                    if perfil in m: m[perfil] = set(perms) & TODAS
            except ValueError:
                pass
        return m

    def salvar_matriz(self, dados):
        limpo = {perfil: sorted(set(perms) & (TODAS - {"usuarios", "rede"})) for perfil, perms in dados.items() if perfil in PERMISSOES}
        with _trava:
            tmp = os.path.join(self.dir, "perfis.json.tmp")
            json.dump(limpo, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            os.replace(tmp, os.path.join(self.dir, "perfis.json"))
        return limpo

    def pode(self, perfil, perm): return perfil == "admin" or perm in self.matriz().get(perfil, set())

    def permissoes(self, perfil): return sorted(TODAS if perfil == "admin" else self.matriz().get(perfil, set()))

    def por_permissao(self, perm):
        return [u for u in self.listar() if u["ativo"] and self.pode(u["perfil"], perm)]

    def auditar(self, usuario, ip, acao, alvo=""):
        self.auditar_registro({"ts": datetime.datetime.now().isoformat(timespec="seconds"), "usuario": usuario,
                              "ip": ip, "acao": acao, "alvo": alvo})

    def _estado_auditoria(self, criar=False, estado_importado=None):
        import seguranca_local as S
        from pathlib import Path
        ancora = S.caminho_ancora_auditoria(os.path.dirname(self.dir))
        raw = Path(self.log).read_bytes() if os.path.exists(self.log) else b""
        if estado_importado is not None:
            estado = estado_importado
        elif ancora.exists():
            estado = json.loads(S.desproteger(json.loads(ancora.read_text(encoding="utf-8"))))
        else:
            registros = [json.loads(x) for x in raw.splitlines() if x.strip()]
            if any("_integridade" in x for x in registros):
                raise RuntimeError("Âncora de auditoria ausente; não reiniciar a cadeia.")
            if not criar:
                if raw: raise RuntimeError("Histórico legado ainda não ancorado.")
                return None
            if raw and not raw.endswith(b"\n"):
                raise RuntimeError("Histórico legado incompleto; arquivo preservado.")
            estado = {"schema": "cpj-auditoria/1", "chave": secrets.token_hex(32), "seq": 0,
                      "cabeca": "0" * 64, "legado_bytes": len(raw), "legado_sha256": hashlib.sha256(raw).hexdigest(),
                      "legado_registros": len(registros)}
            S.gravar_atomico_restrito(ancora, json.dumps(S.proteger(json.dumps(estado).encode())).encode())
        if estado.get("schema") != "cpj-auditoria/1": raise RuntimeError("Âncora de auditoria inválida.")
        legado = raw[:estado["legado_bytes"]]
        if len(legado) != estado["legado_bytes"] or hashlib.sha256(legado).hexdigest() != estado["legado_sha256"]:
            raise RuntimeError("Histórico legado alterado ou removido.")
        anterior, seq = "0" * 64, 0
        resto = raw[estado["legado_bytes"]:]
        if resto and not resto.endswith(b"\n"): raise RuntimeError("Auditoria truncada.")
        for linha in resto.splitlines():
            registro = json.loads(linha)
            assinatura = registro.pop("_integridade")
            seq += 1
            if assinatura.get("seq") != seq or assinatura.get("anterior") != anterior:
                raise RuntimeError("Sequência da auditoria alterada.")
            payload = json.dumps({"registro": registro, "seq": seq, "anterior": anterior}, ensure_ascii=False,
                                 sort_keys=True, separators=(",", ":")).encode("utf-8")
            mac = hmac.new(bytes.fromhex(estado["chave"]), payload, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, assinatura.get("hmac", "")):
                raise RuntimeError("Registro de auditoria alterado.")
            anterior = mac
        if seq != estado["seq"] or anterior != estado["cabeca"]:
            raise RuntimeError("Auditoria removida ou truncada em relação à âncora.")
        return estado

    def verificar_auditoria(self):
        import seguranca_local as S
        with _trava:
            try:
                with S.trava_auditoria(os.path.dirname(self.dir)):
                    estado = self._estado_auditoria()
                return {"integra": True, "registros_protegidos": estado["seq"] if estado else 0,
                        "legado_sem_assinatura": bool(estado and estado["legado_bytes"]),
                        "limite": "Proteção local; não resiste a quem controla a conta ou o computador inteiro."}
            except Exception:
                return {"integra": False, "erro": "Integridade da auditoria não confirmada; preserve o log e a âncora."}

    def auditar_registro(self, registro):
        """Registros extras (uso de IA) também pertencem à mesma cadeia HMAC."""
        import seguranca_local as S
        with _trava, S.trava_auditoria(os.path.dirname(self.dir)):
            try:
                estado = self._estado_auditoria(criar=True)
                registro = dict(registro)
                registro.pop("_integridade", None)
                seq, anterior = estado["seq"] + 1, estado["cabeca"]
                payload = json.dumps({"registro": registro, "seq": seq, "anterior": anterior}, ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")).encode("utf-8")
                mac = hmac.new(bytes.fromhex(estado["chave"]), payload, hashlib.sha256).hexdigest()
                registro["_integridade"] = {"seq": seq, "anterior": anterior, "hmac": mac}
                fd = os.open(self.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                try:
                    S.restringir_arquivo(self.log)
                    with os.fdopen(fd, "ab") as f:
                        fd = None
                        f.write((json.dumps(registro, ensure_ascii=False) + "\n").encode("utf-8"))
                        f.flush(); os.fsync(f.fileno())
                finally:
                    if fd is not None: os.close(fd)
                estado.update(seq=seq, cabeca=mac)
                S.gravar_atomico_restrito(S.caminho_ancora_auditoria(os.path.dirname(self.dir)),
                                         json.dumps(S.proteger(json.dumps(estado).encode())).encode())
            except Exception:
                raise RuntimeError("Falha na integridade/persistência da auditoria; log e âncora preservados para conferência.") from None

    def auditoria(self, n=200):
        import seguranca_local as S
        with _trava, S.trava_auditoria(os.path.dirname(self.dir)):
            if not self.verificar_auditoria()["integra"]:
                raise RuntimeError("Integridade da auditoria não confirmada.")
            if not os.path.exists(self.log): return []
            with open(self.log, encoding="utf-8") as f: linhas = f.read().splitlines()[-n:]
            return [json.loads(x) for x in reversed(linhas)]
