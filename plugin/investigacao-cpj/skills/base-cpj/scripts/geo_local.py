#!/usr/bin/env python3
"""Resolução geográfica offline de referência para a Central CPJ (Etapa 1).

Regras mandatórias (revisoes/plano-correlacoes-mapa-etapa-1.md §§2.3, 2.4, 4.1):
- Zero requisições externas (100% local, baseado em municipios_br.json).
- Coordenada municipal aproximada ('municipio_aproximado') apenas quando município/UF forem inequívocos.
- Coordenada documentada ('coordenada_documentada') apenas quando houver lat/lon explícitos nos autos,
  com fonte identificável e contexto compatível com a pessoa/empresa (nunca atribuir coordenada de
  'local_fato' automaticamente como endereço da pessoa).
- Município homônimo sem UF, endereço incompleto ou endereços em municípios conflitantes permanecem
  sem coordenada resolvida e entram em 'sem_localizacao' com o respectivo motivo.
- Preservar distinção entre PF e PJ: a presença de CNPJ/empresa na qualificação de uma PF não transforma
  a PF em PJ; ambas são representadas separadamente com vínculo explícito.
- Proibido deslocamento artificial (jitter) de coordenadas nos dados.
"""
import hashlib, json, os, re, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQ_MUNICIPIOS = os.path.join(AQUI, "municipios_br.json")

_CACHE_BASE = None
_CACHE_MTIME = None

UFS_VALIDAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
    "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"
}

# Municípios brasileiros sabidamente homônimos em múltiplas UFs (exigem UF explícita)
HOMONIMOS_MULTI_UF = {
    "bom jesus", "santa ines", "campo grande", "palmas", "rio branco", "boa vista",
    "valenca", "cruzeiro", "santarem", "bonito", "santa luzia", "sao jose",
    "santa maria", "sao francisco", "santo antonio", "vera cruz", "santa helena",
    "santa rita", "sao domingos", "sao joao", "sao miguel", "sao pedro",
    "mundo novo", "nova olinda", "ouro branco", "agua branca", "alto alegre"
}

CONTEXTOS_COORD_VALIDOS_ENTIDADE = {
    "endereco_pessoa", "residencia", "domicilio", "endereco_residencial",
    "sede_empresa", "estabelecimento", "endereco_comercial", "endereco_documentado",
    "qualificacao", "sede_pj"
}

CONTEXTOS_COORD_INCOMPATIVEIS = {
    "local_fato", "fato", "crime", "ocorrencia", "local_crime", "local_ocorrencia",
    "erb", "antena", "antena_erb", "ip_conexao", "cativeiro", "apreensao", "abordagem"
}

RX_INCERTEZA = re.compile(
    r"(\?|\bd[ií]gito\s+incerto\b|\bileg[ií]vel\b|\[pesquisar:|\[obter:|\{preencher:)",
    re.IGNORECASE,
)

RX_SUFIXO_PJ = re.compile(
    r"\b(LTDA|S\.?A\.?|S/A|EIRELI|MEI|EPP|COM[EÉ]RCIO|SERVI[CÇ]OS|PAGAMENTOS|"
    r"INSTITUI[CÇ][AÃ]O\s+DE\s+PAGAMENTO|BANCO|FINANCEIRA|SECURITIZADORA|"
    r"INTERMEDIA[CÇ][AÃ]O|HOLDING|EMPREENDIMENTOS|TRANSPORTES|LOG[IÍ]STICA|"
    r"ASSESSORIA|CONSULTORIA|SOLU[CÇ][OÕ]ES|TECNOLOGIA\s+LTDA|DIGITAL\s+LTDA)\b",
    re.IGNORECASE,
)

RX_COORD_TEXTO = re.compile(
    r"(?:coord(?:enadas?)?|lat(?:itude)?\s*[:=]?\s*)"
    r"(-?\d{1,2}\.\d{3,8})\s*[,;/\s]\s*(?:lon(?:gitude)?\s*[:=]?\s*)?(-?\d{1,2}\.\d{3,8})",
    re.IGNORECASE,
)


def norm_texto(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.lower()).strip()


ABREVIACOES_MUNICIPIO = {
    "pres prudente": "presidente prudente",
    "p prudente": "presidente prudente",
    "pres venceslau": "presidente venceslau",
    "pres epitacio": "presidente epitacio",
    "pres bernardes": "presidente bernardes",
    "s paulo": "sao paulo",
    "sp capital": "sao paulo",
    "s b do campo": "sao bernardo do campo",
    "s bernardo do campo": "sao bernardo do campo",
    "s caetano do sul": "sao caetano do sul",
    "s j do rio preto": "sao jose do rio preto",
    "s jose do rio preto": "sao jose do rio preto",
    "s j dos campos": "sao jose dos campos",
    "s jose dos campos": "sao jose dos campos",
    "b horizonte": "belo horizonte",
    "r de janeiro": "rio de janeiro",
}

NOMES_ESTADOS_UF = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA",
    "ceara": "CE", "distrito federal": "DF", "espirito santo": "ES", "goias": "GO",
    "maranhao": "MA", "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
    "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE", "piaui": "PI",
    "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS",
    "rondonia": "RO", "roraima": "RR", "santa catarina": "SC", "sao paulo": "SP",
    "sergipe": "SE", "tocantins": "TO",
}


def norm_municipio(s):
    s = norm_texto(s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ABREVIACOES_MUNICIPIO.get(s, s)


def carregar_base_geo():
    global _CACHE_BASE, _CACHE_MTIME
    try:
        mtime = os.path.getmtime(ARQ_MUNICIPIOS)
    except OSError:
        mtime = None
    if _CACHE_BASE is not None and mtime == _CACHE_MTIME:
        return _CACHE_BASE
    with open(ARQ_MUNICIPIOS, encoding="utf-8") as f:
        bruto = json.load(f)
    por_nome_uf = {}
    por_nome = {}
    por_ibge = {}
    for m in bruto.get("municipios", []):
        nm = norm_municipio(m["municipio"])
        uf = str(m["uf"]).upper().strip()
        item = {
            "ibge": str(m.get("ibge") or ""),
            "municipio": m["municipio"],
            "uf": uf,
            "lat": float(m["lat"]),
            "lon": float(m["lon"]),
        }
        por_nome_uf[(nm, uf)] = item
        por_nome.setdefault(nm, []).append(item)
        if item["ibge"]:
            por_ibge[item["ibge"]] = item
    _CACHE_BASE = {
        "metadata": bruto.get("metadata", {}),
        "ufs": bruto.get("ufs", {}),
        "municipios": bruto.get("municipios", []),
        "por_nome_uf": por_nome_uf,
        "por_nome": por_nome,
        "por_ibge": por_ibge,
    }
    _CACHE_MTIME = mtime
    return _CACHE_BASE


def metadados_cartografia():
    base = carregar_base_geo()
    return {
        "metadata": base["metadata"],
        "ufs": base["ufs"],
        "total_municipios_base": len(base["municipios"]),
    }


def _extrair_contexto_endereco(trecho):
    t = norm_texto(trecho)
    if any(k in t for k in ("local do fato", "local do crime", "local da ocorrencia", "local da apreensao", "contexto: local_fato", "contexto=local_fato")):
        return "local_fato"
    if any(k in t for k in ("erb", "estacao radio base", "antena")):
        return "erb"
    if any(k in t for k in ("sede", "estabelecimento", "endereco comercial", "matriz", "filial")):
        return "sede_empresa"
    if any(k in t for k in ("residencia", "residencial", "domicilio", "morador", "residente")):
        return "endereco_pessoa"
    return "endereco_documentado"


def _extrair_data_ref(trecho):
    m = re.search(r"\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b", str(trecho or ""))
    return m.group(1) if m else None


def _tentar_extrair_municipio_uf(trecho, base=None):
    """Extrai (municipio_cand, uf_cand) de um texto de endereço brasileiro."""
    base = base or carregar_base_geo()
    txt = str(trecho or "").strip()
    if not txt:
        return None, None

    # Remover CEP, parênteses informativos de fls/pág e marcadores de contexto no final
    limpo = re.sub(r"\((?:fls?\.?|p[aá]g\.?)[^)]*\)", " ", txt, flags=re.IGNORECASE)
    limpo = re.sub(r"\[[^\]]*\]", " ", limpo)
    limpo = re.sub(r"\bCEP\s*[:.]?\s*\d{2}\.?\d{3}-?\d{3}\b", " ", limpo, flags=re.IGNORECASE)
    limpo = re.sub(r"\b\d{5}-?\d{3}\b", " ", limpo)
    limpo = limpo.strip(" ,;:-.")

    # 1) Padrão explícito: "Município: X / UF: Y" ou "Cidade: X - Y"
    m_exp = re.search(
        r"(?:munic[ií]pio|cidade|comarca)\s*[:=]\s*([^,;/|-]+?)(?:\s*[/|-]\s*([A-Za-z]{2})\b|(?:[,;]\s*(?:uf|estado)\s*[:=]\s*([A-Za-z]{2})\b)|$)",
        limpo,
        re.IGNORECASE,
    )
    if m_exp:
        cid = m_exp.group(1).strip()
        uf = (m_exp.group(2) or m_exp.group(3) or "").upper().strip()
        if uf in UFS_VALIDAS:
            return cid, uf
        return cid, None

    # 2) Padrão clássico final ou intermediário: "<Cidade>/<UF>" ou "<Cidade> - <UF>" ou "<Cidade>, <UF>"
    padroes_uf = [
        re.compile(r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'`.-]{1,45}?)\s*[/\-]\s*([A-Za-z]{2})(?:\b|$)"),
        re.compile(r"(?:,\s*)([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'`.-]{2,45}?)\s+([A-Za-z]{2})\s*(?:[,;.\-]|$)"),
    ]
    for rx in padroes_uf:
        for m in reversed(list(rx.finditer(limpo))):
            uf = m.group(2).upper()
            if uf not in UFS_VALIDAS:
                continue
            bruto_cid = m.group(1).strip(" ,;:-.")
            partes_cid = [p.strip(" -.") for p in re.split(r"[,;]", bruto_cid) if p.strip(" -.")]
            if not partes_cid:
                continue
            cid = partes_cid[-1]
            if " - " in cid:
                cid = cid.split(" - ")[-1].strip()
            nm = norm_municipio(cid)
            if nm and not any(nm.startswith(p) for p in ("rua ", "av ", "avenida ", "travessa ", "alameda ", "rodovia ", "estrada ", "cep ")):
                return cid, uf

    # 2b) Padrão "<Cidade>-<Nome do Estado por extenso>" (ex.: "AUGUSTO CORRÊA-PARÁ")
    m_est = re.search(r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s'`.-]{2,40}?)\s*[/\-]\s*([A-Za-zÀ-ÿ\s]{4,22})$", limpo)
    if m_est:
        uf_ext = NOMES_ESTADOS_UF.get(norm_texto(m_est.group(2)))
        if uf_ext:
            partes_cid = [p.strip(" -.") for p in re.split(r"[,;]", m_est.group(1)) if p.strip(" -.")]
            if partes_cid:
                return partes_cid[-1], uf_ext

    # 3) Procurar menção sem UF nos segmentos separados por vírgula
    segmentos = [p.strip(" .;-") for p in re.split(r"[,;/]", limpo) if p.strip(" .;-")]
    for seg in reversed(segmentos):
        nm = norm_municipio(seg)
        if not nm:
            continue
        if nm in UFS_VALIDAS or nm.upper() in UFS_VALIDAS:
            continue
        if nm in base["por_nome"] or nm in HOMONIMOS_MULTI_UF:
            return seg, None

    # 4) Se o próprio texto curto for apenas uma UF (ex.: "SP")
    if norm_municipio(limpo).upper() in UFS_VALIDAS:
        return None, norm_municipio(limpo).upper()

    return None, None


def resolver_endereco_texto(texto, fonte=None, coord_doc=None, contexto_coord=None):
    """Resolve um único endereço textual ou coordenada documentada.

    Retorna dicionário estruturado com:
      texto, fonte, contexto, data_ref, status ('resolvido' | 'sem_localizacao'),
      precisao ('coordenada_documentada' | 'municipio_aproximado' | None),
      motivo (quando sem_localizacao), municipio, uf, ibge, lat, lon, limitacoes.
    """
    base = carregar_base_geo()
    txt = str(texto or "").strip()
    limitacoes = []
    data_ref = _extrair_data_ref(txt)
    contexto_end = contexto_coord or _extrair_contexto_endereco(txt)

    if RX_INCERTEZA.search(txt):
        limitacoes.append("endereco_com_incerteza_documental")

    # 1) Verificar coordenada documentada explícita (via objeto coord_doc ou embutida no texto)
    lat_doc, lon_doc = None, None
    ctx_doc = contexto_coord
    fonte_doc = fonte
    if isinstance(coord_doc, dict) and coord_doc.get("lat") is not None and coord_doc.get("lon") is not None:
        try:
            lat_doc = float(coord_doc["lat"])
            lon_doc = float(coord_doc["lon"])
            ctx_doc = coord_doc.get("contexto") or contexto_coord
            fonte_doc = coord_doc.get("fonte") or fonte
        except (TypeError, ValueError):
            lat_doc, lon_doc = None, None
    elif txt:
        m_c = RX_COORD_TEXTO.search(txt)
        if m_c:
            try:
                lat_doc = float(m_c.group(1))
                lon_doc = float(m_c.group(2))
                ctx_doc = ctx_doc or _extrair_contexto_endereco(txt)
            except ValueError:
                lat_doc, lon_doc = None, None

    if lat_doc is not None and lon_doc is not None:
        ctx_norm = norm_texto(ctx_doc or "").replace(" ", "_")
        tem_fonte = bool(fonte_doc and str(fonte_doc).strip())
        coord_valida_br = (-35.0 <= lat_doc <= 6.0) and (-75.0 <= lon_doc <= -28.0)
        if not coord_valida_br:
            limitacoes.append("coordenada_fora_intervalo_br")
        elif not tem_fonte:
            limitacoes.append("coordenada_sem_fonte_identificavel")
        elif not ctx_norm or ctx_norm in CONTEXTOS_COORD_INCOMPATIVEIS or ctx_norm not in CONTEXTOS_COORD_VALIDOS_ENTIDADE:
            limitacoes.append(f"coordenada_contexto_incompativel:{ctx_norm or 'sem_contexto'}")
        else:
            # Coordenada documentada válida e compatível com a pessoa/empresa
            mun_c, uf_c = _tentar_extrair_municipio_uf(txt, base)
            mun_info = base["por_nome_uf"].get((norm_municipio(mun_c), (uf_c or "").upper())) if (mun_c and uf_c) else None
            return {
                "texto": txt,
                "fonte": fonte_doc,
                "contexto": ctx_norm,
                "data_ref": data_ref,
                "status": "resolvido",
                "precisao": "coordenada_documentada",
                "motivo": None,
                "municipio": mun_info["municipio"] if mun_info else (mun_c or None),
                "uf": mun_info["uf"] if mun_info else (uf_c or None),
                "ibge": mun_info["ibge"] if mun_info else None,
                "lat": round(lat_doc, 6),
                "lon": round(lon_doc, 6),
                "limitacoes": limitacoes,
            }

    if not txt:
        motivo = "coordenada_contexto_incompativel" if any(l.startswith("coordenada_contexto_incompativel") for l in limitacoes) else "sem_endereco"
        return {
            "texto": "",
            "fonte": fonte,
            "contexto": contexto_end,
            "data_ref": None,
            "status": "sem_localizacao",
            "precisao": None,
            "motivo": motivo,
            "municipio": None,
            "uf": None,
            "ibge": None,
            "lat": None,
            "lon": None,
            "limitacoes": limitacoes,
        }

    # Se o endereço contém incerteza explícita no nome do município/UF, não resolver
    mun_cand, uf_cand = _tentar_extrair_municipio_uf(txt, base)
    if not mun_cand:
        motivo = "coordenada_contexto_incompativel" if any(l.startswith("coordenada_contexto_incompativel") for l in limitacoes) else "endereco_incompleto"
        return {
            "texto": txt,
            "fonte": fonte,
            "contexto": contexto_end,
            "data_ref": data_ref,
            "status": "sem_localizacao",
            "precisao": None,
            "motivo": motivo,
            "municipio": None,
            "uf": uf_cand,
            "ibge": None,
            "lat": None,
            "lon": None,
            "limitacoes": limitacoes,
        }

    nm_mun = norm_municipio(mun_cand)
    if "?" in str(mun_cand) or "incerto" in nm_mun:
        limitacoes.append("municipio_incerto")
        return {
            "texto": txt,
            "fonte": fonte,
            "contexto": contexto_end,
            "data_ref": data_ref,
            "status": "sem_localizacao",
            "precisao": None,
            "motivo": "municipio_incerto",
            "municipio": mun_cand,
            "uf": uf_cand,
            "ibge": None,
            "lat": None,
            "lon": None,
            "limitacoes": limitacoes,
        }

    if uf_cand:
        info = base["por_nome_uf"].get((nm_mun, uf_cand.upper()))
        if info:
            return {
                "texto": txt,
                "fonte": fonte,
                "contexto": contexto_end,
                "data_ref": data_ref,
                "status": "resolvido",
                "precisao": "municipio_aproximado",
                "motivo": None,
                "municipio": info["municipio"],
                "uf": info["uf"],
                "ibge": info["ibge"],
                "lat": info["lat"],
                "lon": info["lon"],
                "limitacoes": limitacoes,
            }
        return {
            "texto": txt,
            "fonte": fonte,
            "contexto": contexto_end,
            "data_ref": data_ref,
            "status": "sem_localizacao",
            "precisao": None,
            "motivo": "municipio_nao_encontrado_na_base_local",
            "municipio": mun_cand,
            "uf": uf_cand.upper(),
            "ibge": None,
            "lat": None,
            "lon": None,
            "limitacoes": limitacoes,
        }

    # Município sem UF: verificar se é homônimo ou ambíguo
    candidatos = base["por_nome"].get(nm_mun, [])
    if nm_mun in HOMONIMOS_MULTI_UF or len(candidatos) > 1:
        ufs_disp = sorted({c["uf"] for c in candidatos})
        limitacoes.append(f"municipio_ambiguo_sem_uf:{mun_cand}")
        return {
            "texto": txt,
            "fonte": fonte,
            "contexto": contexto_end,
            "data_ref": data_ref,
            "status": "sem_localizacao",
            "precisao": None,
            "motivo": "municipio_ambiguo",
            "detalhe_motivo": f"Município '{mun_cand}' sem UF documentada (homônimos em {', '.join(ufs_disp) or 'múltiplas UFs'}).",
            "municipio": mun_cand,
            "uf": None,
            "ibge": None,
            "lat": None,
            "lon": None,
            "limitacoes": limitacoes,
        }

    if len(candidatos) == 1:
        info = candidatos[0]
        return {
            "texto": txt,
            "fonte": fonte,
            "contexto": contexto_end,
            "data_ref": data_ref,
            "status": "resolvido",
            "precisao": "municipio_aproximado",
            "motivo": None,
            "municipio": info["municipio"],
            "uf": info["uf"],
            "ibge": info["ibge"],
            "lat": info["lat"],
            "lon": info["lon"],
            "limitacoes": limitacoes,
        }

    return {
        "texto": txt,
        "fonte": fonte,
        "contexto": contexto_end,
        "data_ref": data_ref,
        "status": "sem_localizacao",
        "precisao": None,
        "motivo": "endereco_incompleto",
        "municipio": mun_cand,
        "uf": None,
        "ibge": None,
        "lat": None,
        "lon": None,
        "limitacoes": limitacoes,
    }


def _dividir_enderecos(enderecos_bruto):
    """Divide campo de endereços preservando múltiplos endereços distintos."""
    if not enderecos_bruto:
        return []
    if isinstance(enderecos_bruto, list):
        return [str(x).strip() for x in enderecos_bruto if str(x).strip()]
    txt = str(enderecos_bruto).strip()
    if not txt:
        return []
    # Separadores usuais de múltiplos endereços no CPJ: ' | ', '; ', quebra de linha
    partes = [p.strip() for p in re.split(r"\s*\|\s*|\s*;\s*|\r?\n+", txt) if p.strip()]
    return partes


def resolver_localizacao_entidade(enderecos_bruto, fonte=None, extras=None, tipo_pessoa="PF"):
    """Resolve a localização de uma entidade (PF ou PJ) preservando múltiplos endereços e limitações."""
    extras = extras if isinstance(extras, dict) else {}
    fonte_efetiva = extras.get("fonte") or extras.get("localizador") or fonte

    # Verificar se há coordenada documentada estruturada em extras
    coord_doc = None
    if extras.get("lat") is not None and extras.get("lon") is not None:
        coord_doc = {
            "lat": extras.get("lat"),
            "lon": extras.get("lon"),
            "contexto": extras.get("contexto_coordenada") or extras.get("contexto"),
            "fonte": extras.get("fonte_coordenada") or fonte_efetiva,
        }

    lista_textos = _dividir_enderecos(enderecos_bruto)
    if extras.get("enderecos_lista") and isinstance(extras["enderecos_lista"], list):
        for item in extras["enderecos_lista"]:
            if isinstance(item, str) and item.strip() not in lista_textos:
                lista_textos.append(item.strip())

    enderecos_detalhados = []
    limitacoes = []

    if not lista_textos and coord_doc:
        r = resolver_endereco_texto("", fonte=fonte_efetiva, coord_doc=coord_doc)
        enderecos_detalhados.append(r)
        limitacoes.extend(r.get("limitacoes", []))
    else:
        for i, t in enumerate(lista_textos):
            c_doc = coord_doc if i == 0 else None
            r = resolver_endereco_texto(t, fonte=fonte_efetiva, coord_doc=c_doc)
            enderecos_detalhados.append(r)
            for lim in r.get("limitacoes", []):
                if lim not in limitacoes:
                    limitacoes.append(lim)

    if not enderecos_detalhados:
        return {
            "status_geo": "sem_localizacao",
            "precisao": None,
            "motivo_sem_localizacao": "sem_endereco",
            "municipio": None,
            "uf": None,
            "ibge": None,
            "lat": None,
            "lon": None,
            "contexto_coordenada": None,
            "enderecos_detalhados": [],
            "limitacoes": limitacoes,
        }

    resolvidos = [e for e in enderecos_detalhados if e["status"] == "resolvido"]
    if not resolvidos:
        # Priorizar motivo mais específico
        motivos = [e.get("motivo") for e in enderecos_detalhados if e.get("motivo")]
        prioridade = [
            "coordenada_contexto_incompativel",
            "municipio_ambiguo",
            "municipio_incerto",
            "endereco_incompleto",
            "municipio_nao_encontrado_na_base_local",
            "sem_endereco",
        ]
        motivo_escolhido = next((m for p in prioridade for m in motivos if m == p), motivos[0] if motivos else "sem_endereco")
        return {
            "status_geo": "sem_localizacao",
            "precisao": None,
            "motivo_sem_localizacao": motivo_escolhido,
            "municipio": enderecos_detalhados[0].get("municipio"),
            "uf": enderecos_detalhados[0].get("uf"),
            "ibge": None,
            "lat": None,
            "lon": None,
            "contexto_coordenada": None,
            "enderecos_detalhados": enderecos_detalhados,
            "limitacoes": limitacoes,
        }

    # Verificar se há múltiplos endereços resolvidos em municípios distintos (conflito de localização)
    municipios_distintos = {(e.get("municipio"), e.get("uf")) for e in resolvidos if e.get("municipio") or e.get("uf")}
    coords_distintas = {(e.get("lat"), e.get("lon")) for e in resolvidos if e.get("lat") is not None}

    if len(municipios_distintos) > 1 or (len(coords_distintas) > 1 and len(municipios_distintos) > 1):
        if "localizacao_conflitante" not in limitacoes:
            limitacoes.append("localizacao_conflitante")
        if "multiplos_enderecos" not in limitacoes:
            limitacoes.append("multiplos_enderecos")
        return {
            "status_geo": "sem_localizacao",
            "precisao": None,
            "motivo_sem_localizacao": "localizacao_conflitante",
            "municipio": None,
            "uf": None,
            "ibge": None,
            "lat": None,
            "lon": None,
            "contexto_coordenada": None,
            "enderecos_detalhados": enderecos_detalhados,
            "limitacoes": limitacoes,
        }

    if len(enderecos_detalhados) > 1 and "multiplos_enderecos" not in limitacoes:
        limitacoes.append("multiplos_enderecos")

    # Preferir coordenada_documentada se houver entre os resolvidos do mesmo município
    principal = next((e for e in resolvidos if e["precisao"] == "coordenada_documentada"), resolvidos[0])
    return {
        "status_geo": "resolvido",
        "precisao": principal["precisao"],
        "motivo_sem_localizacao": None,
        "municipio": principal["municipio"],
        "uf": principal["uf"],
        "ibge": principal["ibge"],
        "lat": principal["lat"],
        "lon": principal["lon"],
        "contexto_coordenada": principal["contexto"] if principal["precisao"] == "coordenada_documentada" else None,
        "enderecos_detalhados": enderecos_detalhados,
        "limitacoes": limitacoes,
    }


def _eh_registro_pf(row, extras):
    """Determina se um registro de pessoas representa primariamente uma Pessoa Física (PF).

    Regra §2.4: A simples presença de CNPJ ou empresa em registro de qualificação
    não transforma automaticamente uma PF em PJ.
    """
    tipo_exp = str(extras.get("tipo_pessoa") or "").upper().strip()
    if tipo_exp in ("PF", "PJ"):
        # Se tiver CPF ou filiação/RG/nascimento e nome não for claramente PJ, permanece PF
        cpf_dig = re.sub(r"\D", "", str(row.get("cpf") or ""))
        if tipo_exp == "PJ" and (len(cpf_dig) == 11 or row.get("mae") or row.get("pai") or row.get("rg") or row.get("nascimento")):
            return True
        return tipo_exp == "PF"

    cpf_dig = re.sub(r"\D", "", str(row.get("cpf") or ""))
    tem_atributos_pf = bool(
        len(cpf_dig) == 11
        or str(row.get("cpf") or "").strip()
        or str(row.get("mae") or "").strip()
        or str(row.get("pai") or "").strip()
        or str(row.get("rg") or "").strip()
        or str(row.get("nascimento") or "").strip()
    )
    if tem_atributos_pf:
        return True

    nome = str(row.get("nome") or "").strip()
    empresas = str(row.get("empresas") or "").strip()
    cnpj = str(row.get("cnpj") or "").strip()

    if RX_SUFIXO_PJ.search(nome):
        return False
    if cnpj and not nome:
        return False
    if cnpj and empresas and norm_texto(nome) == norm_texto(empresas):
        return False
    if not nome and empresas:
        return False
    return True


def extrair_registros_geo_caso(caso_id, rows_pessoas):
    """Converte linhas da tabela `pessoas` (origem='caso') em registros geográficos PF e PJ separados.

    Garante que uma PF com `empresas` ou `cnpj` associado na qualificação continue sendo PF,
    e gera um registro PJ vinculado separado caso essa PJ ainda não exista autonomamente no caso.
    """
    registros = []
    pjs_existentes = set()
    pendentes_pj_vinculada = []

    for idx, row in enumerate(rows_pessoas):
        if str(row.get("origem") or "caso") != "caso":
            continue
        try:
            extras_raw = row.get("extras")
            if isinstance(extras_raw, dict):
                extras = dict(extras_raw)
            elif isinstance(extras_raw, str) and extras_raw.strip().startswith("{"):
                extras = json.loads(extras_raw)
            else:
                extras = {}
        except Exception:
            extras = {}

        # Mesclar colunas diretas do CSV/tabela em extras caso presentes na linha
        for k_dir in ("lat", "lon", "contexto_coordenada", "fonte_coordenada", "tipo_pessoa", "endereco_empresa", "endereco_pj", "fls", "paginas", "documento"):
            if row.get(k_dir) not in (None, "") and k_dir not in extras:
                extras[k_dir] = row.get(k_dir)

        nome = str(row.get("nome") or "").strip()
        cpf = str(row.get("cpf") or "").strip()
        cnpj = str(row.get("cnpj") or "").strip()
        empresas = str(row.get("empresas") or "").strip()
        condicao = str(row.get("condicao") or "").strip()
        enderecos = str(row.get("enderecos") or "").strip()
        telefones = str(row.get("telefones") or "").strip()
        emails = str(row.get("emails") or "").strip()
        placas = str(row.get("placas") or "").strip()

        arq_row = str(row.get("arquivo") or "02-analise/pessoas.csv").strip()
        loc_row = str(row.get("localizador") or "").strip()
        pag_row = row.get("pagina") or row.get("paginas")
        fls_row = row.get("fls")
        if not pag_row and loc_row:
            m_p = re.search(r"p[aá]g(?:ina)?\.?\s*(\d+)", loc_row, re.I)
            if m_p:
                pag_row = int(m_p.group(1))
        if not fls_row and loc_row:
            m_f = re.search(r"\bfls?\.?\s*(\d+(?:\s*[-a]\s*\d+)?)", loc_row, re.I)
            if m_f:
                fls_row = m_f.group(1)

        fonte_padrao = {
            "caso": caso_id,
            "arquivo": arq_row,
            "documento": str(row.get("documento") or ""),
            "pagina": int(pag_row) if str(pag_row or "").isdigit() else None,
            "fls": str(fls_row) if fls_row else None,
            "localizador": loc_row,
        }
        fonte = extras.get("localizador") if isinstance(extras.get("localizador"), dict) else (
            extras.get("fonte") if isinstance(extras.get("fonte"), dict) else fonte_padrao
        )

        eh_pf = _eh_registro_pf(row, extras)
        tipo_pessoa = "PF" if eh_pf else "PJ"

        if tipo_pessoa == "PJ":
            nome_pj = nome or empresas or (f"PJ {cnpj}" if cnpj else f"PJ #{idx + 1}")
            chave_pj = (re.sub(r"\D", "", cnpj), norm_texto(nome_pj))
            pjs_existentes.add(chave_pj)
            if cnpj:
                pjs_existentes.add((re.sub(r"\D", "", cnpj), ""))
            if nome_pj:
                pjs_existentes.add(("", norm_texto(nome_pj)))

            loc = resolver_localizacao_entidade(enderecos, fonte=fonte, extras=extras, tipo_pessoa="PJ")
            reg_id = hashlib.sha1(f"{caso_id}|PJ|{nome_pj}|{cnpj}|{idx}".encode("utf-8")).hexdigest()[:16]
            registros.append({
                "id": f"geo-{reg_id}",
                "caso": caso_id,
                "pessoa_id": row.get("id"),
                "tipo_pessoa": "PJ",
                "nome": nome_pj,
                "cpf": "",
                "cnpj": cnpj,
                "empresas": empresas or nome_pj,
                "papel": condicao or "empresa mencionada",
                "telefones": telefones,
                "emails": emails,
                "placas": placas,
                "enderecos_bruto": enderecos,
                "vinculos": [],
                "fonte": fonte,
                **loc,
            })
        else:
            nome_pf = nome or (f"PF {cpf}" if cpf else f"PF #{idx + 1}")
            vinculos = []
            if empresas or cnpj:
                nomes_emp = [e.strip() for e in re.split(r"\s*\|\s*|\s*;\s*", empresas) if e.strip()] or ([f"Empresa CNPJ {cnpj}"] if cnpj else [])
                cnpjs_emp = [c.strip() for c in re.split(r"\s*\|\s*|\s*;\s*", cnpj) if c.strip()]
                for i_e, nm_emp in enumerate(nomes_emp):
                    c_emp = cnpjs_emp[i_e] if i_e < len(cnpjs_emp) else (cnpjs_emp[0] if len(cnpjs_emp) == 1 else "")
                    vinculos.append({
                        "tipo": "PJ_ASSOCIADA",
                        "nome": nm_emp,
                        "cnpj": c_emp,
                        "relacao": "empresa_associada_na_qualificacao",
                    })
                    pendentes_pj_vinculada.append({
                        "nome_pj": nm_emp,
                        "cnpj": c_emp,
                        "pf_nome": nome_pf,
                        "pf_cpf": cpf,
                        "pf_id": row.get("id"),
                        "papel": f"PJ associada a {nome_pf}" + (f" ({condicao})" if condicao else ""),
                        "endereco_pj": extras.get("endereco_empresa") or extras.get("endereco_pj") or "",
                        "fonte": fonte,
                    })

            loc = resolver_localizacao_entidade(enderecos, fonte=fonte, extras=extras, tipo_pessoa="PF")
            reg_id = hashlib.sha1(f"{caso_id}|PF|{nome_pf}|{cpf}|{idx}".encode("utf-8")).hexdigest()[:16]
            registros.append({
                "id": f"geo-{reg_id}",
                "caso": caso_id,
                "pessoa_id": row.get("id"),
                "tipo_pessoa": "PF",
                "nome": nome_pf,
                "cpf": cpf,
                "cnpj": "",
                "empresas": empresas,
                "papel": condicao or "qualificado(a)",
                "telefones": telefones,
                "emails": emails,
                "placas": placas,
                "enderecos_bruto": enderecos,
                "vinculos": vinculos,
                "fonte": fonte,
                **loc,
            })

    # Emitir registros PJ autônomos para empresas vinculadas a PFs que não tinham linha própria como PJ
    for idx_v, pv in enumerate(pendentes_pj_vinculada):
        cnpj_limpo = re.sub(r"\D", "", pv["cnpj"])
        nm_limpo = norm_texto(pv["nome_pj"])
        if (cnpj_limpo and (cnpj_limpo, "") in pjs_existentes) or (nm_limpo and ("", nm_limpo) in pjs_existentes):
            continue
        if cnpj_limpo:
            pjs_existentes.add((cnpj_limpo, ""))
        if nm_limpo:
            pjs_existentes.add(("", nm_limpo))

        # Nota: endereço residencial da PF não é copiado automaticamente para a PJ vinculada
        loc_pj = resolver_localizacao_entidade(pv["endereco_pj"], fonte=pv["fonte"], extras={}, tipo_pessoa="PJ")
        if not pv["endereco_pj"]:
            loc_pj["motivo_sem_localizacao"] = "sem_endereco_pj_associada"
            if "endereco_pj_nao_documentado_separadamente" not in loc_pj["limitacoes"]:
                loc_pj["limitacoes"].append("endereco_pj_nao_documentado_separadamente")

        reg_id = hashlib.sha1(f"{caso_id}|PJ-VINC|{pv['nome_pj']}|{pv['cnpj']}|{idx_v}".encode("utf-8")).hexdigest()[:16]
        registros.append({
            "id": f"geo-{reg_id}",
            "caso": caso_id,
            "pessoa_id": pv["pf_id"],
            "tipo_pessoa": "PJ",
            "nome": pv["nome_pj"],
            "cpf": "",
            "cnpj": pv["cnpj"],
            "empresas": pv["nome_pj"],
            "papel": pv["papel"],
            "telefones": "",
            "emails": "",
            "placas": "",
            "enderecos_bruto": pv["endereco_pj"],
            "vinculos": [{
                "tipo": "PF_ASSOCIADA",
                "nome": pv["pf_nome"],
                "cpf": pv["pf_cpf"],
                "relacao": "pessoa_associada_na_qualificacao",
            }],
            "fonte": pv["fonte"],
            **loc_pj,
        })

    return registros
