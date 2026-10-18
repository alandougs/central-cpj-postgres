#!/usr/bin/env python3
"""Motor de coincidências documentadas entre procedimentos e estado humano persistente (Etapa 1).

Regras mandatórias (revisoes/plano-correlacoes-mapa-etapa-1.md §§2.1, 2.2, 4.1–4.4, 6):
- Coincidência exata apenas de identificadores completos documentados em 2+ procedimentos distintos:
  CPF, CNPJ, CHAVE_PIX, CONTA (com banco identificado), TELEFONE, EMAIL, PLACA.
- NUNCA gerar correlação por endereço, nome, município, DDD ou banco isolado.
- Ordens de Serviço diferentes do mesmo IP/procedimento (mesmo IPe/inquérito ou mesmo processo)
  contam como UM único procedimento.
- Quando faltar identificação de procedimento (sem IPe/inquérito e sem processo) ou houver contradição,
  sinalizar limitação ('identidade_procedimento_insuficiente' / 'identidade_procedimento_contraditoria')
  e não afirmar recorrência confirmada entre IPs distintos.
- Preservar valor bruto e normalizado; rejeitar identificadores com '?' / '[dígito incerto]' / parciais.
- Conta bancária exige instituição + agência/conta; contas sem banco ou de bancos distintos não colidem.
- Linguagem estritamente neutra e descritiva: sem score (1-100), sem 'crítico'/'alto', sem 'ORCRIM',
  'laranja', 'empresa de fachada', 'beneficiário final' ou equivalentes.
- Estado humano ('lido' independente de 'estado' ativo/fixado/descartado + 'motivo' obrigatório ao descartar)
  persistido fora do SQLite regenerável com trava de arquivo e escrita atômica (os.replace).
"""
import csv, datetime, hashlib, json, os, re, sqlite3, sys, time, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)

import geo_local as GEO  # noqa: E402

REGRA_VERSAO = "etapa1-1.0"
TIPOS_PERMITIDOS = ("CPF", "CNPJ", "CHAVE_PIX", "CONTA", "TELEFONE", "EMAIL", "PLACA")
ESTADOS_VALIDOS = ("ativo", "fixado", "descartado")

ROTULOS_TIPO = {
    "CPF": "CPF",
    "CNPJ": "CNPJ",
    "CHAVE_PIX": "Chave Pix",
    "CONTA": "Conta bancária",
    "TELEFONE": "Telefone",
    "EMAIL": "E-mail",
    "PLACA": "Placa de veículo",
}

RX_INCERTEZA = re.compile(
    r"(\?|\bd[ií]gito\s+incerto\b|\bileg[ií]vel\b|\bincompleto\b|\bparcial\b|\*{2,}|"
    r"\[pesquisar:|\[obter:|\{preencher:)",
    re.IGNORECASE,
)

MAPA_BANCOS = [
    (re.compile(r"\b(001|banco\s+do\s+brasil|\bbb\b)\b", re.I), "001_bb", "Banco do Brasil (001)"),
    (re.compile(r"\b(104|caixa\s+economica|cef|\bcaixa\b)\b", re.I), "104_cef", "Caixa Econômica Federal (104)"),
    (re.compile(r"\b(237|bradesco)\b", re.I), "237_bradesco", "Bradesco (237)"),
    (re.compile(r"\b(341|itau|ita[uú])\b", re.I), "341_itau", "Itaú (341)"),
    (re.compile(r"\b(033|santander)\b", re.I), "033_santander", "Santander (033)"),
    (re.compile(r"\b(260|nubank|nu\s+pagamentos)\b", re.I), "260_nubank", "Nu Pagamentos / Nubank (260)"),
    (re.compile(r"\b(077|banco\s+inter|\binter\b)\b", re.I), "077_inter", "Banco Inter (077)"),
    (re.compile(r"\b(336|c6\s+bank|\bc6\b)\b", re.I), "336_c6", "C6 Bank (336)"),
    (re.compile(r"\b(290|pagseguro|pagbank)\b", re.I), "290_pagbank", "PagSeguro / PagBank (290)"),
    (re.compile(r"\b(323|mercado\s*pago)\b", re.I), "323_mercadopago", "Mercado Pago (323)"),
    (re.compile(r"\b(380|picpay)\b", re.I), "380_picpay", "PicPay (380)"),
    (re.compile(r"\b(756|sicoob|bancoob)\b", re.I), "756_sicoob", "Sicoob (756)"),
    (re.compile(r"\b(748|sicredi)\b", re.I), "748_sicredi", "Sicredi (748)"),
    (re.compile(r"\b(422|safra)\b", re.I), "422_safra", "Banco Safra (422)"),
    (re.compile(r"\b(208|btg)\b", re.I), "208_btg", "BTG Pactual (208)"),
    (re.compile(r"\b(212|original)\b", re.I), "212_original", "Banco Original (212)"),
    (re.compile(r"\b(655|votorantim|\bbv\b|neon)\b", re.I), "655_bv", "Banco BV / Neon (655)"),
    (re.compile(r"\b(197|stone)\b", re.I), "197_stone", "Stone Pagamentos (197)"),
    (re.compile(r"\b(403|cora)\b", re.I), "403_cora", "Cora (403)"),
    (re.compile(r"\b(364|gerencianet|efi|ef[ií]\s*bank)\b", re.I), "364_efi", "Efí / Gerencianet (364)"),
]


def agora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def norm_ascii(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


def contem_incerteza(valor, contexto=""):
    return bool(RX_INCERTEZA.search(str(valor or "")) or RX_INCERTEZA.search(str(contexto or "")))


def normalizar_banco(banco_bruto):
    """Normaliza nome ou código de instituição financeira. Retorna (slug, rotulo) ou (None, None) se ausente/incerto."""
    b = norm_ascii(banco_bruto)
    if not b or b in ("?", "desconhecido", "nao informado", "n/i", "ni", "s/n", "sem banco", "banco", "-"):
        return None, None
    if "?" in b or "incerto" in b:
        return None, None
    for rx, slug, rotulo in MAPA_BANCOS:
        if rx.search(b):
            return slug, rotulo
    limpo = re.sub(r"[^a-z0-9]+", "_", b).strip("_")
    if len(limpo) < 2:
        return None, None
    return f"inst_{limpo}", str(banco_bruto).strip()


def normalizar_identificador(tipo, valor_bruto, banco_extra=None, contexto=""):
    """Valida e normaliza um identificador para comparação exata.

    Retorna (ok, valor_norm, valor_exibicao, motivo_rejeicao).
    Nunca completa dígitos nem remove marcadores de incerteza.
    """
    t = str(tipo or "").upper().strip()
    bruto = str(valor_bruto or "").strip()
    if t not in TIPOS_PERMITIDOS:
        return False, "", bruto, "tipo_nao_suportado"
    if not bruto:
        return False, "", bruto, "valor_vazio"
    if contem_incerteza(bruto, contexto):
        return False, "", bruto, "identificador_com_incerteza"

    if t == "CPF":
        dig = re.sub(r"\D", "", bruto)
        if len(dig) != 11 or len(set(dig)) == 1:
            return False, "", bruto, "cpf_incompleto_ou_invalido"
        exib = f"{dig[:3]}.{dig[3:6]}.{dig[6:9]}-{dig[9:]}"
        return True, dig, exib, None

    if t == "CNPJ":
        dig = re.sub(r"\D", "", bruto)
        if len(dig) != 14 or len(set(dig)) == 1:
            return False, "", bruto, "cnpj_incompleto_ou_invalido"
        exib = f"{dig[:2]}.{dig[2:5]}.{dig[5:8]}/{dig[8:12]}-{dig[12:]}"
        return True, dig, exib, None

    if t == "TELEFONE":
        dig = re.sub(r"\D", "", bruto)
        if dig.startswith("55") and len(dig) in (12, 13):
            dig = dig[2:]
        if len(dig) not in (10, 11):
            return False, "", bruto, "telefone_sem_ddd_ou_incompleto"
        ddd = dig[:2]
        if int(ddd) < 11 or len(set(dig[2:])) == 1:
            return False, "", bruto, "telefone_invalido"
        resto = dig[2:]
        exib = f"({ddd}) {resto[:-4]}-{resto[-4:]}"
        return True, dig, exib, None

    if t == "EMAIL":
        em = bruto.lower().strip()
        if not re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,15}", em):
            return False, "", bruto, "email_invalido"
        return True, em, em, None

    if t == "PLACA":
        pl = re.sub(r"[^A-Za-z0-9]", "", bruto).upper()
        if not re.fullmatch(r"[A-Z]{3}\d[A-Z0-9]\d{2}", pl):
            return False, "", bruto, "placa_invalida"
        exib = f"{pl[:3]}-{pl[3:]}"
        return True, pl, exib, None

    if t == "CHAVE_PIX":
        # Chave Pix pode ser EVP (UUID), e-mail, CPF, CNPJ ou telefone
        limpo = re.sub(r"^chave\s*pix\s*[:=\-]?\s*", "", bruto, flags=re.I).strip()
        if not limpo or contem_incerteza(limpo, contexto):
            return False, "", bruto, "chave_pix_com_incerteza"
        if "@" in limpo and re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,15}", limpo.lower()):
            return True, f"email:{limpo.lower()}", limpo.lower(), None
        if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", limpo):
            return True, f"evp:{limpo.lower()}", limpo.lower(), None
        dig = re.sub(r"\D", "", limpo)
        if len(dig) == 11:
            return True, f"cpf_tel:{dig}", limpo, None
        if len(dig) == 14:
            return True, f"cnpj:{dig}", limpo, None
        if len(dig) in (10, 12, 13):
            d_norm = dig[2:] if (dig.startswith("55") and len(dig) in (12, 13)) else dig
            if len(d_norm) in (10, 11):
                return True, f"cpf_tel:{d_norm}", limpo, None
        if len(limpo) >= 8:
            return True, f"raw:{norm_ascii(limpo)}", limpo, None
        return False, "", bruto, "chave_pix_incompleta"

    if t == "CONTA":
        banco_cand = banco_extra
        conta_parte = bruto
        if "|" in bruto and not banco_cand:
            b_p, c_p = bruto.split("|", 1)
            banco_cand = b_p
            conta_parte = c_p
        elif not banco_cand:
            # Tentar extrair banco se estiver escrito junto (ex.: "Bradesco Ag 1234 CC 56789-0")
            for rx, slug, rotulo in MAPA_BANCOS:
                if rx.search(bruto):
                    banco_cand = rotulo
                    break
        slug_banco, rotulo_banco = normalizar_banco(banco_cand)
        if not slug_banco:
            return False, "", bruto, "conta_sem_instituicao_bancaria"
        if contem_incerteza(conta_parte, contexto):
            return False, "", bruto, "conta_com_digito_incerto"
        dig = re.sub(r"\D", "", conta_parte)
        if len(dig) < 4:
            return False, "", bruto, "conta_incompleta"
        valor_norm = f"{slug_banco}|{dig}"
        exib = f"{rotulo_banco} — {conta_parte.strip()}" if rotulo_banco.lower() not in conta_parte.lower() else conta_parte.strip()
        return True, valor_norm, exib, None

    return False, "", bruto, "nao_reconhecido"


def _normalizar_num_procedimento(val):
    """Normaliza número de IPe/inquérito ou processo judicial para comparação exata de identidade."""
    s = str(val or "").strip()
    if not s or contem_incerteza(s):
        return None
    limpo = norm_ascii(s)
    if limpo in ("-", "s/n", "sn", "nao informado", "pendente", "em apuracao", "desconhecido"):
        return None
    # Ignorar se for explicitamente apenas um BO
    if re.match(r"^(?:bo|b\.o\.|rdo)\b", limpo) and "ip" not in limpo and "proc" not in limpo:
        return None
    dig = re.sub(r"\D", "", s)
    if len(dig) >= 4:
        return dig
    return None


def resolver_identidade_procedimento(caso_meta):
    """Determina a identidade do procedimento de um caso (caso.json).

    Regras (§2.1):
    - O.S. diferentes do mesmo IP/processo compartilham a mesma identidade de procedimento.
    - NUNCA fundir procedimentos por nome, BO ou semelhança textual.
    - Quando faltar IPe/inquérito e processo, ou houver contradição declarada,
      retorna confirmada=False e lista a limitação.
    """
    meta = caso_meta if isinstance(caso_meta, dict) else {}
    cid = str(meta.get("id") or "").strip()
    inq_raw = str(meta.get("inquerito") or meta.get("ipe") or "").strip()
    proc_raw = str(meta.get("processo") or "").strip()

    limitacoes = []
    # Detectar contradição explícita (ex.: múltiplos números conflitantes separados por '|' ou flag de conflito)
    for campo_nome, raw_val in (("inquerito", inq_raw), ("processo", proc_raw)):
        if "|" in raw_val or ";" in raw_val or "conflit" in norm_ascii(raw_val):
            partes = [_normalizar_num_procedimento(p) for p in re.split(r"[|;]", raw_val)]
            partes_validas = [p for p in partes if p]
            if len(set(partes_validas)) > 1:
                limitacoes.append(f"identidade_procedimento_contraditoria:{campo_nome}")

    if meta.get("procedimento_contraditorio") or meta.get("conflito_procedimento"):
        limitacoes.append("identidade_procedimento_contraditoria")

    if limitacoes:
        return {
            "caso": cid,
            "confirmada": False,
            "chaves": [],
            "chave_canonica": f"NC:{cid}",
            "rotulo": f"Procedimento com numeração contraditória ({cid})",
            "inquerito": inq_raw,
            "processo": proc_raw,
            "limitacoes": limitacoes,
        }

    inq_norm = _normalizar_num_procedimento(inq_raw)
    proc_norm = _normalizar_num_procedimento(proc_raw)

    chaves = []
    if inq_norm:
        chaves.append(f"IP:{inq_norm}")
    if proc_norm:
        chaves.append(f"PROC:{proc_norm}")

    if not chaves:
        return {
            "caso": cid,
            "confirmada": False,
            "chaves": [],
            "chave_canonica": f"SEM_PROC:{cid}",
            "rotulo": f"Procedimento sem IPe/Processo identificado ({cid})",
            "inquerito": inq_raw,
            "processo": proc_raw,
            "limitacoes": ["identidade_procedimento_insuficiente"],
        }

    partes_rotulo = []
    if inq_raw:
        partes_rotulo.append(f"IPe {inq_raw}")
    if proc_raw:
        partes_rotulo.append(f"Proc. {proc_raw}")
    return {
        "caso": cid,
        "confirmada": True,
        "chaves": chaves,
        "chave_canonica": chaves[0],
        "rotulo": " / ".join(partes_rotulo),
        "inquerito": inq_raw,
        "processo": proc_raw,
        "limitacoes": [],
    }


def agrupar_casos_por_procedimento(casos_meta):
    """Agrupa O.S./casos que pertencem ao mesmo procedimento (por IPe ou Processo compartilhado)."""
    info_por_caso = {}
    for c in casos_meta:
        cid = str(c.get("id") or "").strip()
        if cid:
            info_por_caso[cid] = resolver_identidade_procedimento(c)

    # Union-Find para unir casos que compartilham qualquer chave confirmada (IP:<n> ou PROC:<n>)
    pai = {cid: cid for cid in info_por_caso}

    def find(x):
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra < rb:
                pai[rb] = ra
            else:
                pai[ra] = rb

    chave_para_caso = {}
    for cid, info in sorted(info_por_caso.items()):
        if not info["confirmada"]:
            continue
        for ch in info["chaves"]:
            if ch in chave_para_caso:
                union(cid, chave_para_caso[ch])
            else:
                chave_para_caso[ch] = cid

    grupos = {}
    for cid, info in sorted(info_por_caso.items()):
        raiz = find(cid) if info["confirmada"] else cid
        g = grupos.setdefault(raiz, {
            "confirmada": info["confirmada"],
            "casos": [],
            "chaves": set(),
            "inqueritos": [],
            "processos": [],
            "limitacoes": [],
        })
        g["casos"].append(cid)
        g["chaves"].update(info["chaves"])
        if info["inquerito"] and info["inquerito"] not in g["inqueritos"]:
            g["inqueritos"].append(info["inquerito"])
        if info["processo"] and info["processo"] not in g["processos"]:
            g["processos"].append(info["processo"])
        for lim in info["limitacoes"]:
            if lim not in g["limitacoes"]:
                g["limitacoes"].append(lim)

    for raiz, g in grupos.items():
        if g["confirmada"]:
            ch_ord = sorted(g["chaves"])
            g["procedimento_id"] = ch_ord[0]
            partes = []
            if g["inqueritos"]:
                partes.append("IPe " + ", ".join(g["inqueritos"]))
            if g["processos"]:
                partes.append("Proc. " + ", ".join(g["processos"]))
            g["rotulo"] = " / ".join(partes) or g["procedimento_id"]
        else:
            g["procedimento_id"] = f"NAO_CONFIRMADO:{raiz}"
            g["rotulo"] = info_por_caso[raiz]["rotulo"]
        g["chaves"] = sorted(g["chaves"])
        info_por_caso[raiz]["procedimento_id"] = g["procedimento_id"]
        for c_membro in g["casos"]:
            info_por_caso[c_membro]["procedimento_id"] = g["procedimento_id"]
            info_por_caso[c_membro]["procedimento_rotulo"] = g["rotulo"]
            info_por_caso[c_membro]["casos_mesmo_procedimento"] = list(g["casos"])

    return info_por_caso, grupos


# ---------------------------------------------------------------- Persistência do estado humano (§4.3)

class _TravaArquivo:
    def __init__(self, lock_path, timeout=5.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        inicio = time.time()
        while True:
            try:
                self.fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, f"{os.getpid()} {agora()}".encode("utf-8"))
                return self
            except FileExistsError:
                # Remover lock órfão se tiver mais de 30s
                try:
                    if time.time() - os.path.getmtime(self.lock_path) > 30:
                        os.remove(self.lock_path)
                        continue
                except OSError:
                    pass
                if time.time() - inicio >= self.timeout:
                    raise TimeoutError("Não foi possível obter trava de estado de correlações.")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        try:
            os.remove(self.lock_path)
        except OSError:
            pass


def caminhos_estado_humano(ws):
    """Retorna (caminho_consulta, caminho_config, caminho_lock).
    Ambos ficam sincronizados: `consulta/_correlacoes-estado.json` entra automaticamente em
    exportação/importação (`tarefas.py`) e `backup.ps1`, e `config/correlacoes-estado.json`
    atende à pasta de configuração local.
    """
    p_con = os.path.join(ws, "consulta", "_correlacoes-estado.json")
    p_cfg = os.path.join(ws, "config", "correlacoes-estado.json")
    p_lock = os.path.join(ws, "config", "correlacoes-estado.lock")
    return p_con, p_cfg, p_lock


def _ler_json_seguro(caminho):
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _gravar_atomico(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = f"{caminho}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)


def carregar_estado_humano(ws):
    """Carrega o mapa de estados humanos das correlações, mesclando config/ e consulta/ se ambos existirem."""
    p_con, p_cfg, _ = caminhos_estado_humano(ws)
    d_con = _ler_json_seguro(p_con) or {}
    d_cfg = _ler_json_seguro(p_cfg) or {}
    itens_con = d_con.get("itens") if isinstance(d_con.get("itens"), dict) else {}
    itens_cfg = d_cfg.get("itens") if isinstance(d_cfg.get("itens"), dict) else {}

    mesclado = {}
    for cid in set(itens_con) | set(itens_cfg):
        a = itens_con.get(cid)
        b = itens_cfg.get(cid)
        if a and not b:
            mesclado[cid] = a
        elif b and not a:
            mesclado[cid] = b
        else:
            # Escolher o que tiver atualizado_em mais recente ou histórico maior
            ta = str(a.get("atualizado_em") or "")
            tb = str(b.get("atualizado_em") or "")
            mesclado[cid] = a if (ta, len(a.get("historico") or [])) >= (tb, len(b.get("historico") or [])) else b
    return {"schema": "cpj-correlacoes-estado/1", "itens": mesclado}


def salvar_estado_humano_atomico(ws, estado_doc):
    p_con, p_cfg, _ = caminhos_estado_humano(ws)
    estado_doc["schema"] = "cpj-correlacoes-estado/1"
    estado_doc["atualizado_em"] = agora()
    _gravar_atomico(p_cfg, estado_doc)
    _gravar_atomico(p_con, estado_doc)


def atualizar_estado_correlacao(ws, correlacao_id, usuario, estado=None, lido=None, motivo=None, evidencia_hash_atual=None):
    """Atualiza o estado humano de uma correlação com trava de arquivo e escrita atômica.

    Regras (§3.2, §4.3):
    - `lido` é booleano independente de `estado` ('ativo' | 'fixado' | 'descartado').
    - `motivo` é obrigatório quando `estado == 'descartado'`.
    - Registra histórico append-only e atualiza `evidencia_hash` e `requer_revisao=False`.
    """
    cid = str(correlacao_id or "").strip()
    if not cid:
        raise ValueError("ID da correlação é obrigatório.")
    if estado is not None:
        estado = str(estado).lower().strip()
        if estado not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {estado}. Use: {', '.join(ESTADOS_VALIDOS)}.")
    if lido is not None and not isinstance(lido, bool):
        raise ValueError("Campo 'lido' deve ser booleano (true/false).")
    if estado is None and lido is None:
        raise ValueError("Informe 'estado' e/ou 'lido' para atualizar.")

    motivo_limpo = str(motivo or "").strip()
    if estado == "descartado" and len(motivo_limpo) < 3:
        raise ValueError("Motivo é obrigatório para descartar uma coincidência (mínimo de 3 caracteres).")

    _, _, p_lock = caminhos_estado_humano(ws)
    with _TravaArquivo(p_lock):
        doc = carregar_estado_humano(ws)
        itens = doc.setdefault("itens", {})
        atual = itens.get(cid) or {
            "correlacao_id": cid,
            "estado": "ativo",
            "lido": False,
            "motivo": "",
            "usuario": None,
            "atualizado_em": None,
            "evidencia_hash": evidencia_hash_atual,
            "requer_revisao": False,
            "tem_suporte": True,
            "historico": [],
        }

        # Buscar hash atual no SQLite caso não tenha sido informado
        if not evidencia_hash_atual:
            db_path = os.path.join(ws, "rag", "cpj.sqlite")
            if os.path.exists(db_path):
                try:
                    con = sqlite3.connect(db_path)
                    row = con.execute("SELECT revisao_origem_hash FROM correlacoes WHERE id = ?", (cid,)).fetchone()
                    con.close()
                    if row:
                        evidencia_hash_atual = row[0]
                except Exception:
                    pass

        novo_estado = estado if estado is not None else atual.get("estado", "ativo")
        novo_lido = lido if lido is not None else bool(atual.get("lido", False))
        novo_motivo = motivo_limpo if estado == "descartado" else (motivo_limpo if motivo is not None else (atual.get("motivo", "") if novo_estado != "ativo" else ""))

        ts = agora()
        ev_hash = evidencia_hash_atual or atual.get("evidencia_hash")
        evento = {
            "em": ts,
            "usuario": usuario or "operador",
            "estado": novo_estado,
            "lido": novo_lido,
            "motivo": novo_motivo,
            "evidencia_hash": ev_hash,
        }
        hist = list(atual.get("historico") or [])
        hist.append(evento)

        registro = {
            "correlacao_id": cid,
            "estado": novo_estado,
            "lido": novo_lido,
            "motivo": novo_motivo,
            "usuario": usuario or "operador",
            "atualizado_em": ts,
            "evidencia_hash": ev_hash,
            "requer_revisao": False,
            "tem_suporte": bool(atual.get("tem_suporte", True)),
            "historico": hist,
        }
        itens[cid] = registro
        salvar_estado_humano_atomico(ws, doc)

        # Sincronizar colunas de estado na tabela derivada do SQLite se existir
        db_path = os.path.join(ws, "rag", "cpj.sqlite")
        if os.path.exists(db_path):
            try:
                con = sqlite3.connect(db_path)
                con.execute(
                    """UPDATE correlacoes
                       SET estado = ?, lido = ?, motivo = ?, usuario_estado = ?,
                           estado_atualizado_em = ?, requer_revisao = 0, historico_json = ?
                       WHERE id = ?""",
                    (novo_estado, 1 if novo_lido else 0, novo_motivo, registro["usuario"],
                     ts, json.dumps(hist, ensure_ascii=False), cid),
                )
                con.commit()
                con.close()
            except Exception:
                pass

        return registro


# ---------------------------------------------------------------- Coleta de ocorrências e cálculo de coincidências

def _decodificar_localizador(loc_str, caso_id, padrao_origem="extracao"):
    """Converte campo localizador (JSON astra-evidencia/1 ou texto legado) em dicionário padronizado."""
    if not loc_str:
        return {"caso": caso_id, "arquivo": "", "documento": "", "pagina": None, "fls": None, "trecho": "", "status": "documentado", "origem_etapa": padrao_origem}
    if isinstance(loc_str, dict):
        d = loc_str
    else:
        s = str(loc_str).strip()
        if s.startswith("{"):
            try:
                d = json.loads(s)
            except Exception:
                d = {"localizador_texto": s}
        else:
            d = {"localizador_texto": s}

    arq = str(d.get("arquivo") or d.get("caminho") or d.get("localizador_texto") or "").strip()
    doc = str(d.get("documento") or "").strip()
    pag = d.get("pagina") or d.get("pagina_pdf")
    fls = d.get("fls") or d.get("folha")
    trecho = str(d.get("trecho") or d.get("contexto") or "").strip()
    status = str(d.get("status") or "documentado").strip()

    # Tentar extrair página/fls de texto legado se ausentes
    if pag is None and arq:
        m_p = re.search(r"p[aá]g(?:ina)?\.?\s*(\d+)", arq, re.I)
        if m_p:
            pag = int(m_p.group(1))
    if fls is None and (arq or trecho):
        m_f = re.search(r"\bfls?\.?\s*(\d+(?:\s*[-a]\s*\d+)?)", f"{arq} {trecho}", re.I)
        if m_f:
            fls = m_f.group(1)

    origem_etapa = padrao_origem
    if "02-analise" in arq or "pessoas.csv" in arq or "fluxo-financeiro.csv" in arq:
        origem_etapa = "analise"
    elif "03-relatorios" in arq:
        origem_etapa = "relatorio"
    elif "01-extracao" in arq:
        origem_etapa = "extracao"

    return {
        "caso": caso_id,
        "arquivo": arq,
        "documento": doc,
        "pagina": pag,
        "fls": str(fls) if fls is not None else None,
        "trecho": trecho[:240],
        "status": status,
        "origem_etapa": origem_etapa,
    }


def _ler_csv_flex(caminho):
    """Lê CSV suportando delimitador ';' (padrão CPJ) ou ','."""
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8-sig", errors="replace", newline="") as f:
            amostra = f.readline()
            delim = ";" if amostra.count(";") >= amostra.count(",") else ","
            f.seek(0)
            return list(csv.DictReader(f, delimiter=delim))
    except Exception:
        return []


def _coletar_ocorrencias_casos(ws, con, info_procedimentos):
    """Coleta todas as ocorrências de identificadores dos casos (origem='caso'), excluindo bases de consulta."""
    con.row_factory = sqlite3.Row
    ocorrencias_brutas = []
    limitacoes_coleta = []

    # 1) Mapear pessoas do caso (tabela `pessoas` onde origem='caso'; o ID do caso fica em `fonte` ou `caso`)
    rows_pessoas = [dict(r) for r in con.execute("SELECT * FROM pessoas WHERE origem = 'caso'").fetchall()]
    pessoas_por_caso_id = {}
    valores_candidatos_norm = set()

    for rp in rows_pessoas:
        cid = str(rp.get("caso") or rp.get("fonte") or "").strip()
        if not cid or cid not in info_procedimentos:
            continue
        rp["caso"] = cid
        pessoas_por_caso_id.setdefault(cid, []).append(rp)

        nome_p = str(rp.get("nome") or rp.get("empresas") or "").strip()
        papel_p = str(rp.get("condicao") or "qualificado(a)").strip()
        try:
            ext = json.loads(rp.get("extras") or "{}")
            if not isinstance(ext, dict):
                ext = {}
        except Exception:
            ext = {}
        loc_base = ext.get("localizador") or ext.get("fonte") or {
            "arquivo": rp.get("arquivo") or "02-analise/pessoas.csv",
            "trecho": rp.get("localizador") or "",
        }
        fonte_p = _decodificar_localizador(loc_base, cid, "analise")

        # Extrair identificadores da ficha de qualificação (pessoas.csv)
        campos_id = [
            ("CPF", rp.get("cpf")),
            ("CNPJ", rp.get("cnpj")),
            ("TELEFONE", rp.get("telefones")),
            ("EMAIL", rp.get("emails")),
            ("PLACA", rp.get("placas")),
        ]
        for tipo_id, val_campo in campos_id:
            if not val_campo:
                continue
            for item_val in re.split(r"\s*[|;,]\s*", str(val_campo)):
                item_val = item_val.strip()
                if not item_val:
                    continue
                ok, v_norm, v_exib, mot = normalizar_identificador(tipo_id, item_val, contexto=fonte_p.get("trecho", ""))
                if not ok:
                    if mot in ("identificador_com_incerteza", "conta_sem_instituicao_bancaria", "conta_com_digito_incerto"):
                        limitacoes_coleta.append({
                            "caso": cid, "tipo": tipo_id, "valor_bruto": item_val,
                            "motivo": mot, "pessoa": nome_p, "fonte": fonte_p,
                        })
                    continue
                valores_candidatos_norm.add(v_norm)
                ocorrencias_brutas.append({
                    "caso": cid,
                    "tipo": tipo_id,
                    "valor_bruto": item_val,
                    "valor_norm": v_norm,
                    "valor_exibicao": v_exib,
                    "pessoa": nome_p,
                    "papel": papel_p,
                    "fonte": fonte_p,
                })

    # 2) Leitura complementar direta de 02-analise/fluxo-financeiro.csv de cada caso (suporta ';' e ',')
    for cid in info_procedimentos:
        ff_path = os.path.join(ws, "casos", cid, "02-analise", "fluxo-financeiro.csv")
        for idx_l, row_ff in enumerate(_ler_csv_flex(ff_path), 1):
            pag_ff = row_ff.get("fonte_pag") or row_ff.get("pagina")
            fls_ff = row_ff.get("fls")
            fonte_str = str(row_ff.get("fonte") or f"seq {row_ff.get('seq') or idx_l}").strip()
            fonte_ff = _decodificar_localizador(
                {
                    "arquivo": os.path.relpath(ff_path, ws),
                    "pagina": int(pag_ff) if str(pag_ff or "").isdigit() else None,
                    "fls": fls_ff,
                    "trecho": fonte_str,
                    "status": "documentado",
                },
                cid, "analise"
            )
            for lado, papel_lado in (("origem", "remetente/origem financeira"), ("destino", "recebedor/destino financeiro")):
                titular = str(row_ff.get(f"{lado}_titular") or row_ff.get(f"nome_{lado}") or row_ff.get(lado) or "").strip()
                doc_id = str(row_ff.get(f"{lado}_cpf_cnpj") or row_ff.get(f"cpf_cnpj_{lado}") or "").strip()
                pix = str(
                    row_ff.get(f"{lado}_chave")
                    or row_ff.get(f"chave_pix_{lado}")
                    or (row_ff.get("chave_pix") if lado == "destino" else "")
                    or ""
                ).strip()
                banco = str(row_ff.get(f"{lado}_banco") or row_ff.get(f"banco_{lado}") or "").strip()
                ag_cc_junto = str(row_ff.get(f"{lado}_ag_conta") or "").strip()
                ag = str(row_ff.get(f"agencia_{lado}") or "").strip()
                cc = str(row_ff.get(f"conta_{lado}") or "").strip()
                bruto_cc = ag_cc_junto or (f"Ag {ag} CC {cc}".strip() if ag and cc else (cc or ""))

                if doc_id:
                    dig_d = re.sub(r"\D", "", doc_id)
                    t_doc = "CNPJ" if len(dig_d) == 14 else "CPF"
                    ok, vn, vex, mot = normalizar_identificador(t_doc, doc_id, contexto=fonte_str)
                    if ok:
                        valores_candidatos_norm.add(vn)
                        ocorrencias_brutas.append({
                            "caso": cid, "tipo": t_doc, "valor_bruto": doc_id,
                            "valor_norm": vn, "valor_exibicao": vex,
                            "pessoa": titular, "papel": papel_lado, "fonte": fonte_ff,
                        })
                    elif mot == "identificador_com_incerteza":
                        limitacoes_coleta.append({
                            "caso": cid, "tipo": t_doc, "valor_bruto": doc_id,
                            "motivo": mot, "pessoa": titular, "fonte": fonte_ff,
                        })
                if pix:
                    ok, vn, vex, mot = normalizar_identificador("CHAVE_PIX", pix, contexto=fonte_str)
                    if ok:
                        valores_candidatos_norm.add(vn)
                        if ":" in vn:
                            valores_candidatos_norm.add(vn.split(":", 1)[1])
                        ocorrencias_brutas.append({
                            "caso": cid, "tipo": "CHAVE_PIX", "valor_bruto": pix,
                            "valor_norm": vn, "valor_exibicao": vex,
                            "pessoa": titular, "papel": papel_lado, "fonte": fonte_ff,
                        })
                if bruto_cc:
                    ok, vn, vex, mot = normalizar_identificador("CONTA", bruto_cc, banco_extra=banco, contexto=fonte_str)
                    if ok:
                        valores_candidatos_norm.add(vn)
                        ocorrencias_brutas.append({
                            "caso": cid, "tipo": "CONTA", "valor_bruto": f"{banco} {bruto_cc}".strip(),
                            "valor_norm": vn, "valor_exibicao": vex,
                            "pessoa": titular, "papel": papel_lado, "fonte": fonte_ff,
                        })
                    elif mot in ("conta_sem_instituicao_bancaria", "conta_com_digito_incerto"):
                        limitacoes_coleta.append({
                            "caso": cid, "tipo": "CONTA", "valor_bruto": f"{banco} {bruto_cc}".strip(),
                            "motivo": mot, "pessoa": titular, "fonte": fonte_ff,
                        })

    # 3) Tabela `entidades`: pré-filtrar em SQL para evitar varrer 650k+ linhas repetidas do mesmo caso
    cols_ent = {r[1] for r in con.execute("PRAGMA table_info(entidades)").fetchall()}
    col_ctx = "contexto" if "contexto" in cols_ent else ("localizador" if "localizador" in cols_ent else "''")
    col_arq = "arquivo" if "arquivo" in cols_ent else "''"
    col_pag = "pagina" if "pagina" in cols_ent else "NULL"

    # Descobrir quais valor_norm aparecem em >= 2 casos na tabela entidades
    multi_norms = {
        r[0]
        for r in con.execute(
            "SELECT valor_norm FROM entidades WHERE caso IS NOT NULL AND valor_norm != '' GROUP BY tipo, valor_norm HAVING COUNT(DISTINCT caso) >= 2"
        ).fetchall()
        if r[0]
    }
    alvos_norm = multi_norms | {v for v in valores_candidatos_norm if v}

    # Criar tabela temporária em memória com os valores candidatos para JOIN rápido
    con.execute("CREATE TEMP TABLE IF NOT EXISTS _tmp_alvos_norm (v TEXT PRIMARY KEY)")
    con.execute("DELETE FROM _tmp_alvos_norm")
    if alvos_norm:
        con.executemany("INSERT OR IGNORE INTO _tmp_alvos_norm (v) VALUES (?)", [(v,) for v in alvos_norm])

    sql_ent = f"""
        SELECT caso, tipo, valor, valor_norm, {col_pag} AS pagina, {col_arq} AS arquivo, MIN({col_ctx}) AS contexto
        FROM entidades
        WHERE caso IS NOT NULL
          AND tipo IN ('CPF', 'CNPJ', 'CHAVE_PIX', 'CONTA', 'TELEFONE', 'EMAIL', 'PLACA')
          AND (
              valor_norm IN (SELECT v FROM _tmp_alvos_norm)
              OR tipo IN ('CONTA', 'CHAVE_PIX', 'PLACA')
              OR valor LIKE '%?%'
              OR {col_ctx} LIKE '%incerto%'
              OR {col_ctx} LIKE '%ileg%'
          )
        GROUP BY caso, tipo, valor_norm, valor, {col_arq}, {col_pag}
    """
    rows_ent = [dict(r) for r in con.execute(sql_ent).fetchall()]

    for re_row in rows_ent:
        cid = str(re_row.get("caso") or "").strip()
        if not cid or cid not in info_procedimentos:
            continue
        tipo_e = str(re_row.get("tipo") or "").upper().strip()
        if tipo_e not in TIPOS_PERMITIDOS:
            continue
        val_bruto = str(re_row.get("valor") or "").strip()
        val_norm_db = str(re_row.get("valor_norm") or "").strip()
        loc_ent = re_row.get("localizador") or {
            "arquivo": re_row.get("arquivo") or "",
            "pagina": re_row.get("pagina"),
            "trecho": re_row.get("contexto") or "",
        }
        fonte_e = _decodificar_localizador(loc_ent, cid, "extracao")

        status_e = norm_ascii(fonte_e.get("status") or "")
        if "incerto" in status_e or "ilegivel" in status_e:
            limitacoes_coleta.append({
                "caso": cid, "tipo": tipo_e, "valor_bruto": val_bruto,
                "motivo": "identificador_com_incerteza", "pessoa": "", "fonte": fonte_e,
            })
            continue

        banco_hint = None
        if tipo_e == "CONTA" and "|" in val_norm_db:
            b_part, _ = val_norm_db.split("|", 1)
            if b_part and b_part != "?":
                banco_hint = b_part

        ok, v_norm, v_exib, mot = normalizar_identificador(
            tipo_e, val_bruto, banco_extra=banco_hint, contexto=fonte_e.get("trecho", "")
        )
        if not ok:
            if mot in ("identificador_com_incerteza", "conta_sem_instituicao_bancaria", "conta_com_digito_incerto"):
                limitacoes_coleta.append({
                    "caso": cid, "tipo": tipo_e, "valor_bruto": val_bruto,
                    "motivo": mot, "pessoa": "", "fonte": fonte_e,
                })
            continue

        pessoa_assoc, papel_assoc = "", ""
        for rp in pessoas_por_caso_id.get(cid, []):
            campos_rp = " | ".join(str(rp.get(k) or "") for k in ("cpf", "cnpj", "telefones", "emails", "placas"))
            if v_norm in re.sub(r"\D", "", campos_rp) or v_norm in campos_rp.lower():
                pessoa_assoc = str(rp.get("nome") or rp.get("empresas") or "").strip()
                papel_assoc = str(rp.get("condicao") or "").strip()
                break

        ocorrencias_brutas.append({
            "caso": cid,
            "tipo": tipo_e,
            "valor_bruto": val_bruto,
            "valor_norm": v_norm,
            "valor_exibicao": v_exib,
            "pessoa": pessoa_assoc,
            "papel": papel_assoc or "mencionado nos autos",
            "fonte": fonte_e,
        })

    # 4) Mapear referências adicionais nos trechos indexados do mesmo caso (analise, relatorio, minuta e transcricao leve)
    # somente para identificadores que aparecem em >= 2 casos.
    casos_por_chave = {}
    for oc in ocorrencias_brutas:
        casos_por_chave.setdefault((oc["tipo"], oc["valor_norm"]), set()).add(oc["caso"])
    chaves_multicaso = {k for k, cs in casos_por_chave.items() if len(cs) >= 2}

    if chaves_multicaso:
        ids_por_caso = {}
        for oc in list(ocorrencias_brutas):
            ch = (oc["tipo"], oc["valor_norm"])
            if ch in chaves_multicaso:
                ids_por_caso.setdefault(oc["caso"], {})[ch] = oc

        try:
            n_tr_total = con.execute("SELECT COUNT(*) FROM trechos").fetchone()[0]
            tipos_tr = "('transcricao', 'analise', 'relatorio', 'minuta')" if n_tr_total < 5000 else "('analise', 'relatorio', 'minuta')"
            rows_tr = [
                dict(r)
                for r in con.execute(
                    f"SELECT arquivo, caso, tipo, pagina, fls, secao, texto FROM trechos WHERE caso IS NOT NULL AND tipo IN {tipos_tr}"
                ).fetchall()
            ]
        except Exception:
            rows_tr = []

        for tr in rows_tr:
            cid = str(tr.get("caso") or "").strip()
            mapa_c = ids_por_caso.get(cid)
            if not mapa_c:
                continue
            txt_tr = str(tr.get("texto") or "")
            txt_dig = re.sub(r"\D", "", txt_tr)
            txt_low = txt_tr.lower()
            arq_tr = str(tr.get("arquivo") or "")
            etapa_tr = "relatorio" if tr.get("tipo") in ("relatorio", "minuta") else ("analise" if tr.get("tipo") == "analise" else "extracao")

            for (t_id, v_norm), oc_ref in mapa_c.items():
                achou = False
                if oc_ref["valor_bruto"] and oc_ref["valor_bruto"].lower() in txt_low:
                    achou = True
                elif oc_ref["valor_exibicao"] and oc_ref["valor_exibicao"].lower() in txt_low:
                    achou = True
                elif t_id in ("CPF", "CNPJ", "TELEFONE") and len(v_norm) >= 10 and v_norm in txt_dig:
                    achou = True
                elif t_id == "PLACA" and v_norm.lower() in re.sub(r"[^a-z0-9]", "", txt_low):
                    achou = True
                if achou:
                    fonte_tr = {
                        "caso": cid,
                        "arquivo": arq_tr,
                        "documento": str(tr.get("secao") or ""),
                        "pagina": tr.get("pagina"),
                        "fls": str(tr.get("fls")) if tr.get("fls") is not None else None,
                        "trecho": txt_tr[:180],
                        "status": "documentado",
                        "origem_etapa": etapa_tr,
                    }
                    ocorrencias_brutas.append({
                        "caso": cid,
                        "tipo": t_id,
                        "valor_bruto": oc_ref["valor_bruto"],
                        "valor_norm": v_norm,
                        "valor_exibicao": oc_ref["valor_exibicao"],
                        "pessoa": oc_ref["pessoa"],
                        "papel": oc_ref["papel"],
                        "fonte": fonte_tr,
                    })

    return ocorrencias_brutas, limitacoes_coleta


def calcular_correlacoes_workspace(ws, con, casos_meta):
    """Calcula as coincidências documentadas entre procedimentos distintos e os registros geográficos."""
    info_proc, _ = agrupar_casos_por_procedimento(casos_meta)
    ocorrencias_brutas, limitacoes_coleta = _coletar_ocorrencias_casos(ws, con, info_proc)

    # Agrupar ocorrências por (tipo, valor_norm)
    grupos_id = {}
    for oc in ocorrencias_brutas:
        chave = (oc["tipo"], oc["valor_norm"])
        g = grupos_id.setdefault(chave, {
            "tipo": oc["tipo"],
            "valor_norm": oc["valor_norm"],
            "valores_brutos": [],
            "valor_exibicao": oc["valor_exibicao"],
            "por_procedimento": {},
            "por_caso": {},
        })
        if oc["valor_bruto"] and oc["valor_bruto"] not in g["valores_brutos"]:
            g["valores_brutos"].append(oc["valor_bruto"])

        cid = oc["caso"]
        p_info = info_proc.get(cid) or resolver_identidade_procedimento({"id": cid})
        proc_id = p_info["procedimento_id"]

        # Deduplicação por procedimento preservando todas as fontes e papéis
        proc_entry = g["por_procedimento"].setdefault(proc_id, {
            "procedimento_id": proc_id,
            "rotulo": p_info.get("procedimento_rotulo") or p_info.get("rotulo") or proc_id,
            "confirmada": bool(p_info.get("confirmada")),
            "inquerito": p_info.get("inquerito") or "",
            "processo": p_info.get("processo") or "",
            "casos": [],
            "limitacoes": list(p_info.get("limitacoes") or []),
        })
        if cid not in proc_entry["casos"]:
            proc_entry["casos"].append(cid)

        caso_entry = g["por_caso"].setdefault(cid, {
            "caso": cid,
            "procedimento_id": proc_id,
            "procedimento_rotulo": proc_entry["rotulo"],
            "procedimento_confirmado": proc_entry["confirmada"],
            "papeis": [],
            "pessoas_associadas": [],
            "fontes": [],
            "etapas": [],
        })
        if oc["papel"] and oc["papel"] not in caso_entry["papeis"]:
            caso_entry["papeis"].append(oc["papel"])
        if oc["pessoa"] and oc["pessoa"] not in caso_entry["pessoas_associadas"]:
            caso_entry["pessoas_associadas"].append(oc["pessoa"])
        etapa = oc["fonte"].get("origem_etapa") or "extracao"
        if etapa not in caso_entry["etapas"]:
            caso_entry["etapas"].append(etapa)

        # Deduplicar fonte exata dentro do mesmo caso preservando todas as ocorrências distintas
        assinatura_fonte = (
            oc["fonte"].get("arquivo") or "",
            oc["fonte"].get("documento") or "",
            oc["fonte"].get("pagina"),
            oc["fonte"].get("fls") or "",
            oc["fonte"].get("trecho") or "",
            oc["valor_bruto"],
        )
        if not any(
            (f.get("arquivo") or "", f.get("documento") or "", f.get("pagina"), f.get("fls") or "", f.get("trecho") or "", f.get("valor_bruto") or "") == assinatura_fonte
            for f in caso_entry["fontes"]
        ):
            caso_entry["fontes"].append({
                **oc["fonte"],
                "valor_bruto": oc["valor_bruto"],
                "pessoa": oc["pessoa"],
                "papel": oc["papel"],
            })

    # Construir lista de correlações (somente quando envolver >= 2 procedimentos distintos confirmados,
    # ou registrar separadamente quando houver múltiplos casos mas identidade de procedimento insuficiente)
    correlacoes = []
    limitacoes_procedimento = []

    for (tipo, valor_norm), g in sorted(grupos_id.items()):
        procs_todos = list(g["por_procedimento"].values())
        procs_confirmados = [p for p in procs_todos if p["confirmada"]]
        procs_nao_confirmados = [p for p in procs_todos if not p["confirmada"]]
        casos_todos = sorted(g["por_caso"].keys())

        # Se aparece em 2+ O.S., mas tem menos de 2 procedimentos confirmados:
        if len(procs_confirmados) < 2:
            if len(casos_todos) >= 2 and procs_nao_confirmados:
                # Há O.S. sem identidade de procedimento suficiente: registrar limitação e NÃO afirmar recorrência entre IPs
                limitacoes_procedimento.append({
                    "tipo": tipo,
                    "valor_norm": valor_norm,
                    "valor_exibicao": g["valor_exibicao"],
                    "casos": casos_todos,
                    "procedimentos_confirmados": len(procs_confirmados),
                    "motivo": "identidade_procedimento_insuficiente",
                    "mensagem": (
                        f"{ROTULOS_TIPO.get(tipo, tipo)} ({g['valor_exibicao']}) consta nas O.S. {', '.join(casos_todos)}, "
                        "porém falta número de IPe/Processo (ou há numeração contraditória) para confirmar procedimentos distintos."
                    ),
                })
            continue

        # Possui >= 2 procedimentos distintos confirmados!
        corr_id = "corr-" + hashlib.sha1(f"{REGRA_VERSAO}|{tipo}|{valor_norm}".encode("utf-8")).hexdigest()[:16]
        n_procs = len(procs_confirmados)
        rotulo_t = ROTULOS_TIPO.get(tipo, tipo)
        titulo = f"{rotulo_t} registrado em {n_procs} procedimentos"

        # Montar resumo neutro das condições/papéis por caso
        ocorrencias_casos = [g["por_caso"][c] for c in casos_todos]
        pessoas_empresas = []
        papeis_por_caso = {}
        limitacoes_corr = []

        for p_nc in procs_nao_confirmados:
            for lim in p_nc.get("limitacoes", []):
                if lim not in limitacoes_corr:
                    limitacoes_corr.append(lim)

        # Verificar se o mesmo caso tinha deduplicação entre extração/análise/relatório
        for oc_c in ocorrencias_casos:
            c_id = oc_c["caso"]
            papeis_por_caso[c_id] = oc_c["papeis"] or ["mencionado nos autos"]
            if len(oc_c["etapas"]) > 1 and "deduplicado_entre_etapas_do_mesmo_caso" not in limitacoes_corr:
                limitacoes_corr.append("deduplicado_entre_etapas_do_mesmo_caso")
            for nm in oc_c["pessoas_associadas"]:
                if nm and not any(pe["nome"] == nm and pe["caso"] == c_id for pe in pessoas_empresas):
                    pessoas_empresas.append({
                        "caso": c_id,
                        "nome": nm,
                        "papeis": list(oc_c["papeis"]),
                    })

        # Se duas O.S. do mesmo procedimento apareceram juntas, anotar que foram consolidadas em 1 procedimento
        for p_conf in procs_confirmados:
            if len(p_conf["casos"]) > 1 and "os_mesmo_procedimento_consolidadas" not in limitacoes_corr:
                limitacoes_corr.append("os_mesmo_procedimento_consolidadas")

        rotulos_procs = [p["rotulo"] for p in procs_confirmados]
        explicacao = (
            f"Coincidência exata de {rotulo_t.lower()} completo ({g['valor_exibicao']}) "
            f"documentada em {n_procs} procedimentos distintos ({'; '.join(rotulos_procs)})."
        )
        if procs_nao_confirmados:
            explicacao += (
                f" Há também menção em {', '.join(c for p in procs_nao_confirmados for c in p['casos'])} "
                "com identificação de procedimento incompleta/contraditória (não contabilizada como IP distinto)."
            )

        # Hash determinístico das evidências de origem para detectar mudança após revisão humana
        payload_hash = json.dumps({
            "tipo": tipo,
            "valor_norm": valor_norm,
            "procedimentos": [p["procedimento_id"] for p in sorted(procs_confirmados, key=lambda x: x["procedimento_id"])],
            "casos": [
                {
                    "caso": oc_c["caso"],
                    "papeis": sorted(oc_c["papeis"]),
                    "pessoas": sorted(oc_c["pessoas_associadas"]),
                    "fontes": sorted(
                        (f.get("arquivo") or "", str(f.get("pagina") or ""), str(f.get("fls") or ""), f.get("valor_bruto") or "")
                        for f in oc_c["fontes"]
                    ),
                }
                for oc_c in ocorrencias_casos
            ],
        }, ensure_ascii=False, sort_keys=True)
        revisao_origem_hash = hashlib.sha256(payload_hash.encode("utf-8")).hexdigest()[:24]

        correlacoes.append({
            "id": corr_id,
            "regra_versao": REGRA_VERSAO,
            "tipo": tipo,
            "rotulo_tipo": rotulo_t,
            "valor": g["valores_brutos"][0] if g["valores_brutos"] else g["valor_exibicao"],
            "valores_brutos": g["valores_brutos"],
            "valor_norm": valor_norm,
            "valor_exibicao": g["valor_exibicao"],
            "titulo": titulo,
            "explicacao": explicacao,
            "total_procedimentos": n_procs,
            "total_casos": len(casos_todos),
            "procedimentos": procs_confirmados,
            "procedimentos_nao_confirmados": procs_nao_confirmados,
            "casos": casos_todos,
            "papeis_por_caso": papeis_por_caso,
            "ocorrencias": ocorrencias_casos,
            "pessoas_empresas": pessoas_empresas,
            "limitacoes": limitacoes_corr,
            "revisao_origem_hash": revisao_origem_hash,
        })

    return correlacoes, limitacoes_procedimento, limitacoes_coleta


def _calcular_assinatura_fontes_ws(ws, casos_meta):
    """Calcula um hash leve de mtime/tamanho dos arquivos de casos para detectar se o índice derivado está desatualizado."""
    h = hashlib.sha256()
    for c in sorted(casos_meta, key=lambda x: str(x.get("id") or "")):
        cid = str(c.get("id") or "")
        if not cid:
            continue
        pasta = os.path.join(ws, "casos", cid)
        for sub in ("caso.json", "02-analise/pessoas.csv", "02-analise/fluxo-financeiro.csv"):
            p = os.path.join(pasta, sub)
            if os.path.exists(p):
                st = os.stat(p)
                h.update(f"{cid}|{sub}|{int(st.st_mtime)}|{st.st_size}\n".encode("utf-8"))
    return h.hexdigest()[:24]


def verificar_desatualizado(ws, con=None):
    """Verifica se os dados derivados de correlações/mapa estão desatualizados em relação aos casos em disco."""
    fechar = False
    if con is None:
        db_path = os.path.join(ws, "rag", "cpj.sqlite")
        if not os.path.exists(db_path):
            return True, "indice_ausente"
        con = sqlite3.connect(db_path)
        fechar = True
    try:
        tab = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta_inteligencia'").fetchone()
        if not tab:
            return True, "tabela_meta_ausente"
        rows = dict(con.execute("SELECT chave, valor FROM meta_inteligencia").fetchall())
        if rows.get("status") != "ok":
            return True, rows.get("erro") or "status_incompleto"
        hash_idx = rows.get("assinatura_fontes") or ""

        # Comparar com estado atual das pastas casos/
        casos_dir = os.path.join(ws, "casos")
        casos_meta = []
        if os.path.isdir(casos_dir):
            for d in sorted(os.listdir(casos_dir)):
                if d.startswith("_"):
                    continue
                pj = os.path.join(casos_dir, d, "caso.json")
                if os.path.exists(pj):
                    casos_meta.append({"id": d})
        hash_atual = _calcular_assinatura_fontes_ws(ws, casos_meta)
        if hash_idx != hash_atual:
            return True, "arquivos_caso_modificados"
        return False, None
    except Exception as e:
        return True, str(e)
    finally:
        if fechar:
            con.close()


def garantir_esquema(con):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS correlacoes (
            id TEXT PRIMARY KEY,
            regra_versao TEXT,
            tipo TEXT,
            rotulo_tipo TEXT,
            valor TEXT,
            valor_norm TEXT,
            valor_exibicao TEXT,
            titulo TEXT,
            explicacao TEXT,
            total_procedimentos INTEGER,
            total_casos INTEGER,
            procedimentos_json TEXT,
            casos_json TEXT,
            ocorrencias_json TEXT,
            pessoas_empresas_json TEXT,
            limitacoes_json TEXT,
            primeira_identificacao TEXT,
            ultima_atualizacao TEXT,
            revisao_origem_hash TEXT,
            estado TEXT DEFAULT 'ativo',
            lido INTEGER DEFAULT 0,
            motivo TEXT DEFAULT '',
            usuario_estado TEXT,
            estado_atualizado_em TEXT,
            requer_revisao INTEGER DEFAULT 0,
            tem_suporte INTEGER DEFAULT 1,
            historico_json TEXT DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_corr_tipo ON correlacoes(tipo);
        CREATE INDEX IF NOT EXISTS idx_corr_estado ON correlacoes(estado, lido, tem_suporte);

        CREATE TABLE IF NOT EXISTS geo_registros (
            id TEXT PRIMARY KEY,
            caso TEXT,
            pessoa_id INTEGER,
            tipo_pessoa TEXT,
            nome TEXT,
            cpf TEXT,
            cnpj TEXT,
            empresas TEXT,
            papel TEXT,
            telefones TEXT,
            emails TEXT,
            placas TEXT,
            enderecos_bruto TEXT,
            status_geo TEXT,
            precisao TEXT,
            motivo_sem_localizacao TEXT,
            municipio TEXT,
            uf TEXT,
            ibge TEXT,
            lat REAL,
            lon REAL,
            contexto_coordenada TEXT,
            enderecos_json TEXT,
            vinculos_json TEXT,
            fonte_json TEXT,
            limitacoes_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_geo_caso ON geo_registros(caso);
        CREATE INDEX IF NOT EXISTS idx_geo_status ON geo_registros(status_geo, uf, municipio);

        CREATE TABLE IF NOT EXISTS meta_inteligencia (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );
        """
    )


def atualizar_indice(ws, con, casos_meta):
    """Atualiza as tabelas derivadas `correlacoes`, `geo_registros` e `meta_inteligencia` no SQLite,
    preservando integralmente as decisões humanas persistidas em disco."""
    ts = agora()
    garantir_esquema(con)

    # Preservar primeira_identificacao anterior se existir
    primeiras_antigas = {}
    try:
        for r_id, p_id in con.execute("SELECT id, primeira_identificacao FROM correlacoes").fetchall():
            if p_id:
                primeiras_antigas[r_id] = p_id
    except Exception:
        pass

    correlacoes_calc, limitacoes_proc, limitacoes_col = calcular_correlacoes_workspace(ws, con, casos_meta)

    # Sincronizar com estado humano persistente
    _, _, p_lock = caminhos_estado_humano(ws)
    with _TravaArquivo(p_lock):
        estado_doc = carregar_estado_humano(ws)
        itens_estado = estado_doc.setdefault("itens", {})
        ids_ativos = {c["id"] for c in correlacoes_calc}
        alterou_estado_disco = False

        # Marcar correlações que perderam suporte (< 2 procedimentos) sem apagar seu histórico humano
        for cid_est, reg_est in list(itens_estado.items()):
            tinha_sup = bool(reg_est.get("tem_suporte", True))
            tem_agora = cid_est in ids_ativos
            if tinha_sup != tem_agora:
                reg_est["tem_suporte"] = tem_agora
                alterou_estado_disco = True

        con.execute("DELETE FROM correlacoes")

        for c in correlacoes_calc:
            cid = c["id"]
            prim = primeiras_antigas.get(cid) or ts
            est_h = itens_estado.get(cid)
            estado = "ativo"
            lido = False
            motivo = ""
            usuario_est = None
            est_at_em = None
            req_rev = False
            hist = []

            if est_h:
                estado = est_h.get("estado") or "ativo"
                lido = bool(est_h.get("lido", False))
                motivo = str(est_h.get("motivo") or "")
                usuario_est = est_h.get("usuario")
                est_at_em = est_h.get("atualizado_em")
                hist = list(est_h.get("historico") or [])
                hash_rev = est_h.get("evidencia_hash")
                # Se já houve decisão humana e o hash das evidências mudou, sinalizar requer_revisao
                if hash_rev and hash_rev != c["revisao_origem_hash"] and (estado != "ativo" or lido or hist):
                    req_rev = True
                    if not est_h.get("requer_revisao"):
                        est_h["requer_revisao"] = True
                        alterou_estado_disco = True
                else:
                    req_rev = bool(est_h.get("requer_revisao", False))
                if not est_h.get("tem_suporte", True):
                    est_h["tem_suporte"] = True
                    alterou_estado_disco = True

            con.execute(
                """INSERT INTO correlacoes (
                    id, regra_versao, tipo, rotulo_tipo, valor, valor_norm, valor_exibicao,
                    titulo, explicacao, total_procedimentos, total_casos,
                    procedimentos_json, casos_json, ocorrencias_json, pessoas_empresas_json,
                    limitacoes_json, primeira_identificacao, ultima_atualizacao, revisao_origem_hash,
                    estado, lido, motivo, usuario_estado, estado_atualizado_em,
                    requer_revisao, tem_suporte, historico_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cid, c["regra_versao"], c["tipo"], c["rotulo_tipo"], c["valor"], c["valor_norm"], c["valor_exibicao"],
                    c["titulo"], c["explicacao"], c["total_procedimentos"], c["total_casos"],
                    json.dumps(c["procedimentos"], ensure_ascii=False),
                    json.dumps(c["casos"], ensure_ascii=False),
                    json.dumps(c["ocorrencias"], ensure_ascii=False),
                    json.dumps(c["pessoas_empresas"], ensure_ascii=False),
                    json.dumps(c["limitacoes"], ensure_ascii=False),
                    prim, ts, c["revisao_origem_hash"],
                    estado, 1 if lido else 0, motivo, usuario_est, est_at_em,
                    1 if req_rev else 0, 1, json.dumps(hist, ensure_ascii=False),
                ),
            )

        # Inserir também registros sem suporte atual que tinham revisão humana prévia (com tem_suporte = 0)
        for cid_est, reg_est in itens_estado.items():
            if cid_est in ids_ativos:
                continue
            con.execute(
                """INSERT INTO correlacoes (
                    id, regra_versao, tipo, rotulo_tipo, valor, valor_norm, valor_exibicao,
                    titulo, explicacao, total_procedimentos, total_casos,
                    procedimentos_json, casos_json, ocorrencias_json, pessoas_empresas_json,
                    limitacoes_json, primeira_identificacao, ultima_atualizacao, revisao_origem_hash,
                    estado, lido, motivo, usuario_estado, estado_atualizado_em,
                    requer_revisao, tem_suporte, historico_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cid_est, REGRA_VERSAO, reg_est.get("tipo") or "DESCONHECIDO", "Identificador",
                    reg_est.get("valor") or "", reg_est.get("valor_norm") or "", reg_est.get("valor") or cid_est,
                    "Coincidência sem suporte atual no índice (< 2 procedimentos)",
                    "O identificador deixou de constar em 2+ procedimentos após reindexação; histórico humano preservado.",
                    0, 0, "[]", "[]", "[]", "[]", '["sem_suporte_atual"]',
                    reg_est.get("atualizado_em") or ts, ts, reg_est.get("evidencia_hash") or "",
                    reg_est.get("estado") or "ativo", 1 if reg_est.get("lido") else 0,
                    reg_est.get("motivo") or "", reg_est.get("usuario"), reg_est.get("atualizado_em"),
                    1 if reg_est.get("requer_revisao") else 0, 0,
                    json.dumps(reg_est.get("historico") or [], ensure_ascii=False),
                ),
            )

        if alterou_estado_disco:
            salvar_estado_humano_atomico(ws, estado_doc)

    # 2) Atualizar registros geográficos por caso (somente origem='caso')
    con.row_factory = sqlite3.Row
    rows_pessoas = [dict(r) for r in con.execute("SELECT * FROM pessoas WHERE origem = 'caso'").fetchall()]
    por_caso_p = {}
    for rp in rows_pessoas:
        cid_p = str(rp.get("caso") or rp.get("fonte") or "").strip()
        if not cid_p:
            continue
        rp["caso"] = cid_p
        por_caso_p.setdefault(cid_p, []).append(rp)

    # Mesclar colunas extras de 02-analise/pessoas.csv (ex.: lat, lon, contexto_coordenada, endereco_empresa, fls, paginas)
    for cid_p, lista_p in por_caso_p.items():
        pc_path = os.path.join(ws, "casos", cid_p, "02-analise", "pessoas.csv")
        linhas_csv = _ler_csv_flex(pc_path)
        if linhas_csv:
            for i_row, rp in enumerate(lista_p):
                if i_row < len(linhas_csv) and "pessoas.csv" in str(rp.get("arquivo") or ""):
                    for k_extra, v_extra in linhas_csv[i_row].items():
                        if k_extra and v_extra not in (None, "") and not rp.get(k_extra):
                            rp[k_extra] = v_extra

    con.execute("DELETE FROM geo_registros")
    total_geo = 0
    for cid, lista_p in sorted(por_caso_p.items()):
        regs_geo = GEO.extrair_registros_geo_caso(cid, lista_p)
        for rg in regs_geo:
            total_geo += 1
            con.execute(
                """INSERT OR REPLACE INTO geo_registros (
                    id, caso, pessoa_id, tipo_pessoa, nome, cpf, cnpj, empresas, papel,
                    telefones, emails, placas, enderecos_bruto, status_geo, precisao,
                    motivo_sem_localizacao, municipio, uf, ibge, lat, lon, contexto_coordenada,
                    enderecos_json, vinculos_json, fonte_json, limitacoes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rg["id"], rg["caso"], rg["pessoa_id"], rg["tipo_pessoa"], rg["nome"],
                    rg["cpf"], rg["cnpj"], rg["empresas"], rg["papel"],
                    rg["telefones"], rg["emails"], rg["placas"], rg["enderecos_bruto"],
                    rg["status_geo"], rg["precisao"], rg["motivo_sem_localizacao"],
                    rg["municipio"], rg["uf"], rg["ibge"], rg["lat"], rg["lon"], rg["contexto_coordenada"],
                    json.dumps(rg["enderecos_detalhados"], ensure_ascii=False),
                    json.dumps(rg["vinculos"], ensure_ascii=False),
                    json.dumps(rg["fonte"], ensure_ascii=False),
                    json.dumps(rg["limitacoes"], ensure_ascii=False),
                ),
            )

    assinatura = _calcular_assinatura_fontes_ws(ws, casos_meta)
    meta_kv = {
        "status": "ok",
        "erro": "",
        "atualizado_em": ts,
        "regra_versao": REGRA_VERSAO,
        "assinatura_fontes": assinatura,
        "total_correlacoes": str(len(correlacoes_calc)),
        "total_geo_registros": str(total_geo),
        "limitacoes_procedimento_json": json.dumps(limitacoes_proc, ensure_ascii=False),
        "limitacoes_coleta_json": json.dumps(limitacoes_col[:200], ensure_ascii=False),
    }
    con.execute("DELETE FROM meta_inteligencia")
    con.executemany("INSERT INTO meta_inteligencia (chave, valor) VALUES (?, ?)", list(meta_kv.items()))
    con.commit()
    return {
        "correlacoes": len(correlacoes_calc),
        "geo_registros": total_geo,
        "limitacoes_procedimento": len(limitacoes_proc),
    }


def registrar_erro_indice(con, erro_msg):
    """Registra falha na atualização das tabelas de inteligência sem interromper a indexação principal."""
    try:
        garantir_esquema(con)
        con.execute("INSERT OR REPLACE INTO meta_inteligencia (chave, valor) VALUES ('status', 'erro')")
        con.execute("INSERT OR REPLACE INTO meta_inteligencia (chave, valor) VALUES ('erro', ?)", (str(erro_msg)[:500],))
        con.execute("INSERT OR REPLACE INTO meta_inteligencia (chave, valor) VALUES ('atualizado_em', ?)", (agora(),))
        con.commit()
    except Exception:
        pass


# ---------------------------------------------------------------- Consultas somente leitura para a API (§4.4)

def consultar_correlacoes(
    ws, caso=None, tipo=None, estado=None, lido=None,
    incluir_sem_suporte=False, ordem="procedimentos", pagina=1, limite=50
):
    """Consulta coincidências no índice derivado sem mutar estado nem disparar reindexação."""
    db_path = os.path.join(ws, "rag", "cpj.sqlite")
    desatualizado, motivo_desat = verificar_desatualizado(ws)
    if not os.path.exists(db_path):
        return {
            "itens": [], "total": 0, "pagina": pagina, "limite": limite,
            "parcial": False, "desatualizado": True, "motivo_desatualizado": "indice_ausente",
            "resumo": {"ativos": 0, "fixados": 0, "descartados": 0, "nao_lidos": 0, "requer_revisao": 0},
            "limitacoes_procedimento": [], "limitacoes_coleta": [],
        }

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        tab = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='correlacoes'").fetchone()
        if not tab:
            return {
                "itens": [], "total": 0, "pagina": pagina, "limite": limite,
                "parcial": False, "desatualizado": True, "motivo_desatualizado": "tabela_correlacoes_ausente",
                "resumo": {"ativos": 0, "fixados": 0, "descartados": 0, "nao_lidos": 0, "requer_revisao": 0},
                "limitacoes_procedimento": [], "limitacoes_coleta": [],
            }

        estado_disco = carregar_estado_humano(ws).get("itens", {})
        rows = [dict(r) for r in con.execute("SELECT * FROM correlacoes").fetchall()]
        meta_rows = dict(con.execute("SELECT chave, valor FROM meta_inteligencia").fetchall())
    finally:
        con.close()

    limitacoes_proc = []
    limitacoes_col = []
    try:
        limitacoes_proc = json.loads(meta_rows.get("limitacoes_procedimento_json") or "[]")
        limitacoes_col = json.loads(meta_rows.get("limitacoes_coleta_json") or "[]")
    except Exception:
        pass

    itens_todos = []
    resumo = {"ativos": 0, "fixados": 0, "descartados": 0, "nao_lidos": 0, "requer_revisao": 0}

    for r in rows:
        cid = r["id"]
        tem_sup = bool(r.get("tem_suporte", 1))
        if not tem_sup and not incluir_sem_suporte:
            continue

        # Sobrescrever com o estado humano mais recente em disco (fonte autoritativa humana)
        est_h = estado_disco.get(cid)
        est_val = (est_h.get("estado") if est_h else r.get("estado")) or "ativo"
        lido_val = bool(est_h.get("lido") if est_h is not None and "lido" in est_h else r.get("lido"))
        motivo_val = (est_h.get("motivo") if est_h else r.get("motivo")) or ""
        usu_val = (est_h.get("usuario") if est_h else r.get("usuario_estado")) or None
        at_em_val = (est_h.get("atualizado_em") if est_h else r.get("estado_atualizado_em")) or None
        hist_val = (est_h.get("historico") if est_h else None)
        if hist_val is None:
            try:
                hist_val = json.loads(r.get("historico_json") or "[]")
            except Exception:
                hist_val = []

        hash_orig = r.get("revisao_origem_hash") or ""
        req_rev = bool(r.get("requer_revisao"))
        if est_h and est_h.get("evidencia_hash") and hash_orig and est_h["evidencia_hash"] != hash_orig:
            req_rev = True
        elif est_h and "requer_revisao" in est_h:
            req_rev = bool(est_h["requer_revisao"])

        casos_lista = json.loads(r.get("casos_json") or "[]")
        if caso and caso not in casos_lista:
            continue

        # Contabilizar resumo antes dos filtros de estado/lido/tipo
        if tem_sup:
            if est_val == "ativo":
                resumo["ativos"] += 1
            elif est_val == "fixado":
                resumo["fixados"] += 1
            elif est_val == "descartado":
                resumo["descartados"] += 1
            if not lido_val and est_val != "descartado":
                resumo["nao_lidos"] += 1
            if req_rev:
                resumo["requer_revisao"] += 1

        if tipo and r["tipo"] != str(tipo).upper().strip():
            continue
        if estado and estado != "todos":
            if estado == "ativos_e_fixados":
                if est_val not in ("ativo", "fixado"):
                    continue
            elif est_val != estado:
                continue
        if lido is not None:
            if bool(lido) != lido_val:
                continue

        procedimentos = json.loads(r.get("procedimentos_json") or "[]")
        ocorrencias = json.loads(r.get("ocorrencias_json") or "[]")
        pessoas_empresas = json.loads(r.get("pessoas_empresas_json") or "[]")
        limitacoes = json.loads(r.get("limitacoes_json") or "[]")

        itens_todos.append({
            "id": cid,
            "regra_versao": r["regra_versao"],
            "tipo": r["tipo"],
            "rotulo_tipo": r["rotulo_tipo"],
            "valor": r["valor"],
            "valor_norm": r["valor_norm"],
            "valor_exibicao": r["valor_exibicao"],
            "titulo": r["titulo"],
            "explicacao": r["explicacao"],
            "total_procedimentos": int(r["total_procedimentos"] or 0),
            "total_casos": int(r["total_casos"] or 0),
            "procedimentos": procedimentos,
            "casos": casos_lista,
            "ocorrencias": ocorrencias,
            "pessoas_empresas": pessoas_empresas,
            "limitacoes": limitacoes,
            "primeira_identificacao": r["primeira_identificacao"],
            "ultima_atualizacao": r["ultima_atualizacao"],
            "revisao_origem_hash": hash_orig,
            "estado": est_val,
            "lido": lido_val,
            "motivo": motivo_val,
            "usuario_estado": usu_val,
            "estado_atualizado_em": at_em_val,
            "requer_revisao": req_rev,
            "tem_suporte": tem_sup,
            "historico": hist_val,
        })

    # Ordenação determinística (§3.2): quantidade de procedimentos ou última atualização
    if ordem == "recentes":
        itens_todos.sort(key=lambda x: (x["ultima_atualizacao"] or "", x["total_procedimentos"], x["id"]), reverse=True)
    else:
        # Priorizar fixados no topo quando em ordenação padrão, depois maior nº de procedimentos
        itens_todos.sort(
            key=lambda x: (
                1 if x["estado"] == "fixado" else (0 if x["estado"] == "ativo" else -1),
                x["total_procedimentos"],
                x["total_casos"],
                x["ultima_atualizacao"] or "",
                x["id"],
            ),
            reverse=True,
        )

    pagina = max(1, int(pagina or 1))
    limite = max(1, min(500, int(limite or 50)))
    total = len(itens_todos)
    ini = (pagina - 1) * limite
    fim = ini + limite
    paginados = itens_todos[ini:fim]

    if caso:
        limitacoes_proc = [lp for lp in limitacoes_proc if caso in (lp.get("casos") or [])]
        limitacoes_col = [lc for lc in limitacoes_col if lc.get("caso") == caso]

    return {
        "itens": paginados,
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "parcial": fim < total,
        "desatualizado": desatualizado,
        "motivo_desatualizado": motivo_desat,
        "atualizado_em": meta_rows.get("atualizado_em"),
        "resumo": resumo,
        "limitacoes_procedimento": limitacoes_proc,
        "limitacoes_coleta": limitacoes_col,
    }


def consultar_mapa(
    ws, caso=None, tipo_pessoa=None, papel=None,
    municipio=None, uf=None, correlacao_id=None, limite=500
):
    """Consulta pontos e grupos geográficos offline e registros sem localização, sem mutar coordenadas."""
    db_path = os.path.join(ws, "rag", "cpj.sqlite")
    desatualizado, motivo_desat = verificar_desatualizado(ws)
    cartografia = GEO.metadados_cartografia()

    if not os.path.exists(db_path):
        return {
            "pontos": [], "grupos": [], "sem_localizacao": [],
            "resumo": {
                "total_registros": 0, "localizados": 0, "sem_localizacao": 0,
                "pf_localizados": 0, "pj_localizados": 0,
                "precisao_municipio": 0, "precisao_coordenada": 0,
            },
            "correlacao_selecionada": None,
            "limite": limite, "parcial": False,
            "desatualizado": True, "motivo_desatualizado": "indice_ausente",
            "cartografia": cartografia,
        }

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        tab = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='geo_registros'").fetchone()
        if not tab:
            return {
                "pontos": [], "grupos": [], "sem_localizacao": [],
                "resumo": {
                    "total_registros": 0, "localizados": 0, "sem_localizacao": 0,
                    "pf_localizados": 0, "pj_localizados": 0,
                    "precisao_municipio": 0, "precisao_coordenada": 0,
                },
                "correlacao_selecionada": None,
                "limite": limite, "parcial": False,
                "desatualizado": True, "motivo_desatualizado": "tabela_geo_ausente",
                "cartografia": cartografia,
            }

        rows_geo = [dict(r) for r in con.execute("SELECT * FROM geo_registros").fetchall()]
        corr_alvo = None
        if correlacao_id:
            r_c = con.execute("SELECT * FROM correlacoes WHERE id = ?", (correlacao_id,)).fetchone()
            if r_c:
                corr_alvo = dict(r_c)
    finally:
        con.close()

    # Se uma correlação foi selecionada, identificar quais casos e pessoas/identificadores pertencem a ela
    casos_corr = set()
    nomes_corr = set()
    valor_norm_corr = ""
    tipo_corr = ""
    if corr_alvo:
        casos_corr = set(json.loads(corr_alvo.get("casos_json") or "[]"))
        for pe in json.loads(corr_alvo.get("pessoas_empresas_json") or "[]"):
            if pe.get("nome"):
                nomes_corr.add(norm_ascii(pe["nome"]))
        valor_norm_corr = str(corr_alvo.get("valor_norm") or "")
        tipo_corr = str(corr_alvo.get("tipo") or "")

    filtrados = []
    for r in rows_geo:
        if caso and r["caso"] != caso:
            continue
        if tipo_pessoa and str(r["tipo_pessoa"]).upper() != str(tipo_pessoa).upper().strip():
            continue
        if papel and norm_ascii(papel) not in norm_ascii(r.get("papel") or ""):
            continue
        if uf and str(r.get("uf") or "").upper() != str(uf).upper().strip():
            continue
        if municipio and norm_ascii(municipio) not in norm_ascii(r.get("municipio") or ""):
            continue

        item = {
            "id": r["id"],
            "caso": r["caso"],
            "pessoa_id": r["pessoa_id"],
            "tipo_pessoa": r["tipo_pessoa"],
            "nome": r["nome"],
            "cpf": r["cpf"],
            "cnpj": r["cnpj"],
            "empresas": r["empresas"],
            "papel": r["papel"],
            "telefones": r["telefones"],
            "emails": r["emails"],
            "placas": r["placas"],
            "enderecos_bruto": r["enderecos_bruto"],
            "status_geo": r["status_geo"],
            "precisao": r["precisao"],
            "motivo_sem_localizacao": r["motivo_sem_localizacao"],
            "municipio": r["municipio"],
            "uf": r["uf"],
            "ibge": r["ibge"],
            "lat": r["lat"],
            "lon": r["lon"],
            "contexto_coordenada": r["contexto_coordenada"],
            "enderecos": json.loads(r.get("enderecos_json") or "[]"),
            "vinculos": json.loads(r.get("vinculos_json") or "[]"),
            "fonte": json.loads(r.get("fonte_json") or "{}"),
            "limitacoes": json.loads(r.get("limitacoes_json") or "[]"),
            "destacado_correlacao": False,
        }

        if corr_alvo:
            pertence = False
            if item["caso"] in casos_corr:
                if norm_ascii(item["nome"]) in nomes_corr or norm_ascii(item["empresas"]) in nomes_corr:
                    pertence = True
                elif tipo_corr == "CPF" and re.sub(r"\D", "", item["cpf"]) == valor_norm_corr:
                    pertence = True
                elif tipo_corr == "CNPJ" and re.sub(r"\D", "", item["cnpj"]) == valor_norm_corr:
                    pertence = True
                elif tipo_corr == "TELEFONE" and valor_norm_corr in re.sub(r"\D", "", item["telefones"]):
                    pertence = True
                elif tipo_corr == "EMAIL" and valor_norm_corr in (item["emails"] or "").lower():
                    pertence = True
                elif tipo_corr == "PLACA" and valor_norm_corr in re.sub(r"[^A-Z0-9]", "", (item["placas"] or "").upper()):
                    pertence = True
                elif any(norm_ascii(v.get("nome") or "") in nomes_corr for v in item["vinculos"]):
                    pertence = True
            item["destacado_correlacao"] = pertence
            if not pertence:
                continue

        filtrados.append(item)

    if corr_alvo:
        casos_com_geo = {it["caso"] for it in filtrados}
        for oc_c in json.loads(corr_alvo.get("ocorrencias_json") or "[]"):
            c_oc = oc_c.get("caso")
            if not c_oc or c_oc in casos_com_geo:
                continue
            if caso and c_oc != caso:
                continue
            nomes_oc = oc_c.get("pessoas_associadas") or []
            papeis_oc = oc_c.get("papeis") or ["mencionado nos autos"]
            fontes_oc = oc_c.get("fontes") or []
            filtrados.append({
                "id": f"geo-sem-qual-{c_oc}-{corr_alvo['id'][-6:]}",
                "caso": c_oc,
                "pessoa_id": None,
                "tipo_pessoa": "PJ" if corr_alvo.get("tipo") == "CNPJ" else "PF",
                "nome": nomes_oc[0] if nomes_oc else f"{corr_alvo.get('rotulo_tipo')}: {corr_alvo.get('valor_exibicao')}",
                "cpf": corr_alvo.get("valor_exibicao") if corr_alvo.get("tipo") == "CPF" else "",
                "cnpj": corr_alvo.get("valor_exibicao") if corr_alvo.get("tipo") == "CNPJ" else "",
                "empresas": "",
                "papel": ", ".join(papeis_oc),
                "telefones": corr_alvo.get("valor_exibicao") if corr_alvo.get("tipo") == "TELEFONE" else "",
                "emails": corr_alvo.get("valor_exibicao") if corr_alvo.get("tipo") == "EMAIL" else "",
                "placas": corr_alvo.get("valor_exibicao") if corr_alvo.get("tipo") == "PLACA" else "",
                "enderecos_bruto": "",
                "status_geo": "sem_localizacao",
                "precisao": None,
                "motivo_sem_localizacao": "sem_qualificacao_geografica",
                "municipio": None,
                "uf": None,
                "ibge": None,
                "lat": None,
                "lon": None,
                "contexto_coordenada": None,
                "enderecos": [],
                "vinculos": [],
                "fonte": fontes_oc[0] if fontes_oc else {"caso": c_oc},
                "limitacoes": ["sem_qualificacao_geografica"],
                "destacado_correlacao": True,
            })

    limite = max(1, min(2000, int(limite or 500)))
    total_filtrados = len(filtrados)
    parcial = total_filtrados > limite
    recorte = filtrados[:limite]

    pontos = []
    sem_localizacao = []
    grupos_map = {}

    pf_loc, pj_loc, prec_mun, prec_coord = 0, 0, 0, 0

    for item in recorte:
        if item["status_geo"] == "resolvido" and item["lat"] is not None and item["lon"] is not None:
            pontos.append(item)
            if item["tipo_pessoa"] == "PJ":
                pj_loc += 1
            else:
                pf_loc += 1
            if item["precisao"] == "coordenada_documentada":
                prec_coord += 1
            else:
                prec_mun += 1

            # Agrupar pontos na mesma coordenada exata (sem alterar lat/lon!)
            chave_g = (round(float(item["lat"]), 6), round(float(item["lon"]), 6))
            g = grupos_map.setdefault(chave_g, {
                "id": f"grp-{hashlib.sha1(f'{chave_g[0]}|{chave_g[1]}'.encode()).hexdigest()[:10]}",
                "lat": item["lat"],
                "lon": item["lon"],
                "municipio": item["municipio"],
                "uf": item["uf"],
                "precisoes": [],
                "total": 0,
                "pf": 0,
                "pj": 0,
                "casos": [],
                "registros_ids": [],
                "destacado_correlacao": False,
            })
            g["total"] += 1
            if item["tipo_pessoa"] == "PJ":
                g["pj"] += 1
            else:
                g["pf"] += 1
            if item["precisao"] and item["precisao"] not in g["precisoes"]:
                g["precisoes"].append(item["precisao"])
            if item["caso"] not in g["casos"]:
                g["casos"].append(item["caso"])
            g["registros_ids"].append(item["id"])
            if item["destacado_correlacao"]:
                g["destacado_correlacao"] = True
        else:
            sem_localizacao.append(item)

    resumo_corr = None
    if corr_alvo:
        resumo_corr = {
            "correlacao_id": corr_alvo["id"],
            "titulo": corr_alvo["titulo"],
            "valor_exibicao": corr_alvo["valor_exibicao"],
            "localizados": len(pontos),
            "sem_localizacao": len(sem_localizacao),
            "mensagem": (
                f"{len(pontos)} registro(s) localizado(s) no mapa e "
                f"{len(sem_localizacao)} registro(s) sem coordenada resolvida para esta coincidência."
            ),
        }

    return {
        "pontos": pontos,
        "grupos": list(grupos_map.values()),
        "sem_localizacao": sem_localizacao,
        "resumo": {
            "total_registros": total_filtrados,
            "localizados": len(pontos),
            "sem_localizacao": len(sem_localizacao),
            "pf_localizados": pf_loc,
            "pj_localizados": pj_loc,
            "precisao_municipio": prec_mun,
            "precisao_coordenada": prec_coord,
        },
        "correlacao_selecionada": resumo_corr,
        "limite": limite,
        "parcial": parcial,
        "desatualizado": desatualizado,
        "motivo_desatualizado": motivo_desat,
        "cartografia": cartografia,
    }
