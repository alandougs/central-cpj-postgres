"""Perguntas locais, autenticadas, sobre o material já indexado."""
import os
import sqlite3
from flask import Blueprint,jsonify,request
import astra_consultas as AC
from rotas.comum import C,R,WS,auditar,requer

bp_astra=Blueprint('astra',__name__)


@bp_astra.post('/api/astra/perguntar')
@requer('pesquisa')
def perguntar():
    d=request.get_json(silent=True)
    if not isinstance(d,dict) or not {'caso','pergunta'}<=set(d) or set(d)-{'caso','pergunta','entidade'}:
        return jsonify(erro='Informe a pergunta e a O.S.'),400
    if not isinstance(d['pergunta'],str) or not d['pergunta'].strip() or len(d['pergunta'])>2000:
        return jsonify(erro='Pergunta inválida ou muito longa.'),400
    try:
        if not isinstance(d['caso'],str):raise ValueError()
        p=C.caminho(d['caso'])
    except ValueError:return jsonify(erro='O.S. inválida.'),400
    if not os.path.isfile(os.path.join(p,'caso.json')):return jsonify(erro='O.S. não localizada.'),404
    e=d.get('entidade')
    if e is not None and (not isinstance(e,dict) or set(e)!={'tipo','valor'} or e['tipo'] not in R.TIPOS_NO or
                          not isinstance(e['valor'],str) or not e['valor'].strip() or len(e['valor'])>4000):
        return jsonify(erro='Seleção de entidade inválida.'),400
    try:resultado=AC.consultar(d['pergunta'],d['caso'],e,WS,R)
    except (OSError,sqlite3.Error,ValueError):
        return jsonify(erro='Consulta local indisponível. Preserve a pergunta e confira o índice e a integridade das fontes; tente novamente.'),503
    auditar('astra_pergunta',f"caso={d['caso']}; intencao={resultado['intencao']['tipo']}")
    return jsonify(resultado)
