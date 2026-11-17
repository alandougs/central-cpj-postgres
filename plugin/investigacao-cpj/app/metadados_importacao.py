"""Validação dos metadados consumidos pela ficha antes de publicar uma importação."""
import json
import math
import re


def _exigir(condicao, campo):
    if not condicao:
        raise ValueError(f"Metadados de importação inválidos: {campo}.")


def _objeto(valor, campo):
    _exigir(isinstance(valor, dict), campo)
    return valor


def _textos(dados, campos):
    for campo in campos.split():
        if campo in dados:
            _exigir(dados[campo] is None or isinstance(dados[campo], str), campo)


def _numero(valor, campo, inteiro=False):
    # Alguns pacotes antigos registram páginas e valores como texto numérico.
    if valor is None:
        return
    if isinstance(valor, str):
        _exigir(bool(re.fullmatch(r"\d+" if inteiro else r"-?\d+(?:[.,]\d+)?", valor)), campo)
        return
    _exigir(type(valor) in ((int,) if inteiro else (int, float)) and math.isfinite(valor), campo)
    if inteiro:
        _exigir(valor >= 0, campo)


def _lista(dados, campo):
    valor = dados.get(campo, [])
    _exigir(isinstance(valor, list), campo)
    return valor


def _fonte(fonte):
    _objeto(fonte, "fonte")
    _textos(fonte, "documento trecho metodo valor arquivo caminho fls")
    _numero(fonte.get("pagina"), "fonte.pagina", inteiro=True)


def validar_caso(caso, id_):
    _objeto(caso, "caso.json")
    _exigir("id" not in caso or caso["id"] == id_, "id")
    _textos(caso, "ordem_servico bo inquerito ipe processo referencia natureza modalidade status prazo requisitante "
            "delegado delegado_genero escrivao prioridade determinacao criado_por responsavel observacoes criado_em atualizado_em baixa_ignorar")
    for campo in ("vitimas", "investigados"):
        _exigir(all(isinstance(v, str) for v in _lista(caso, campo)), campo)
    for campo in ("visto",):
        if campo in caso:
            _exigir(type(caso[campo]) is bool, campo)
    if "revisao" in caso:
        _exigir(type(caso["revisao"]) is int and caso["revisao"] >= 1, "revisao")
    for campo in ("datas", "financeiro", "ip", "resultado"):
        if campo not in caso:
            continue
        dados = _objeto(caso[campo], campo)
        if campo == "datas":
            _exigir(all(v is None or isinstance(v, str) for v in dados.values()), campo)
        elif campo == "financeiro":
            for chave in ("prejuizo_declarado", "prejuizo_documentado", "valor_rastreado"):
                _numero(dados.get(chave), campo + "." + chave)
        elif campo == "ip":
            _numero(dados.get("paginas"), "ip.paginas", inteiro=True)
        else:
            _textos(dados, "autoria")
    _numero(caso.get("horas_trabalho"), "horas_trabalho")
    for doc in _lista(caso, "documentos"):
        _objeto(doc, "documentos")
        _textos(doc, "arquivo pasta tipo sha256 extraido_em")
        _numero(doc.get("paginas"), "documentos.paginas", inteiro=True)
        if "metodos" in doc:
            for valor in _objeto(doc["metodos"], "documentos.metodos").values():
                _numero(valor, "documentos.metodos", inteiro=True)
    for rel in _lista(caso, "relatorios"):
        _objeto(rel, "relatorios")
        _textos(rel, "arquivo data tipo")
        _numero(rel.get("versoes"), "relatorios.versoes", inteiro=True)
    if caso.get("baixa") is not None:
        _textos(_objeto(caso["baixa"], "baixa"), "data origem arquivo registrado_em ressalva")
    if caso.get("preenchimento_os") is not None:
        registro = _objeto(caso["preenchimento_os"], "preenchimento_os")
        _textos(registro, "ia")
        _exigir(all(isinstance(v, str) for v in _lista(registro, "pendentes")), "pendentes")
        for fonte in _objeto(registro.get("fontes", {}), "fontes").values():
            _fonte(fonte)
        for fontes in _objeto(registro.get("conflitos", {}), "conflitos").values():
            _exigir(isinstance(fontes, list), "conflitos")
            for fonte in fontes:
                _fonte(fonte)


def validar_processamento(proc):
    _objeto(proc, "processamento.json")
    for trabalho in _lista(proc, "trabalhos"):
        _objeto(trabalho, "trabalhos")
        _textos(trabalho, "doc arquivo status etapa erro modo usuario inicio fim enfileirado limitacao")
        _numero(trabalho.get("progresso"), "trabalhos.progresso")


def validar_casos_preparados(pasta, novos):
    for id_ in novos:
        caso = pasta / id_ / "caso.json"
        _exigir(caso.is_file(), id_ + "/caso.json ausente")
        try:
            validar_caso(json.loads(caso.read_text(encoding="utf-8-sig")), id_)
            proc = caso.with_name("processamento.json")
            if proc.exists():
                validar_processamento(json.loads(proc.read_text(encoding="utf-8-sig")))
        except (OSError, UnicodeError, json.JSONDecodeError) as erro:
            raise ValueError(f"Metadados ilegíveis no caso importado {id_}.") from erro
