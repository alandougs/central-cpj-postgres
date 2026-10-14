#!/usr/bin/env python3
"""Rotas de bases de consulta, referências, pesquisa textual/relacional e cruzamento de dados."""
import json
import os
import re
import sqlite3
import threading
import time
from flask import Blueprint, abort, jsonify, request
import grafo_evidencias as GE
import conferencias_grafo as CG
from rotas.comum import (
    C,
    Q,
    R,
    RF,
    WS,
    auditar,
    requer,
    salvar_upload,
    tarefas,
)

bp_consulta = Blueprint("consulta", __name__)


def _manuais_grafo(caso=None):
    import vinculos_manuais as VM
    todos = VM.listar(WS, incluir_excluidos=True)
    return GE.fundir_manuais([], todos, caso), todos


def _grafo_sem_indice(vazio, manuais, termo=''):
    if termo:
        busca=R._n(termo)
        chaves={GE.chave(a) for a in manuais if busca in R._n(' '.join(str(a.get(k,'')) for k in
                ('a_valor','b_valor','a_rotulo','b_rotulo','relacao')))}
        manuais=[a for a in manuais if GE.chave(a) in chaves]
    try:grupos = GE.agrupar(manuais, WS)
    except (ValueError,OSError):return jsonify({'erro':'Não foi possível conferir o histórico de revisões. As fontes foram preservadas.'}),503
    corte = len(grupos) > 400
    grupos = grupos[:400]
    nos = {}
    rotulos={(a[lado+'_tipo'],a[lado+'_valor']):a[lado+'_rotulo'] for a in manuais for lado in ('a','b') if a.get(lado+'_rotulo')}
    for a in grupos:
        for lado in ("a", "b"):
            t,v = a[f"{lado}_tipo"],a[f"{lado}_valor"]
            nos[t,v] = {"tipo":t,"valor":v,"nivel":0,"rotulo":rotulos.get((t,v),v)}
    return jsonify({**vazio,"nos":list(nos.values()),"arestas":grupos,
                    "truncado":True if corte else None,"completude":"indice_indisponivel",
                    "limites":{"relacoes":400},
                    "aviso":"Índice indisponível. As anotações preservadas não representam toda a documentação."})


@bp_consulta.get("/api/consulta/bases")
@requer("dados")
def api_bases():
    return jsonify(Q.listar())


@bp_consulta.post("/api/consulta/importar")
@requer("dados")
def api_bases_importar():
    try:
        p, nome = salvar_upload("arquivo", Q.FORMATOS)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    rotulo = (request.form.get("nome") or os.path.splitext(nome)[0]).strip()
    tid = tarefas.nova("consulta", f"Base de consulta: {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo)
    auditar("base_consulta_importada", rotulo)
    return jsonify({"tarefa": tid})


@bp_consulta.post("/api/consulta/colar")
@requer("dados")
def api_bases_colar():
    d = request.get_json(force=True) or {}
    texto = (d.get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "Cole o texto a importar."}), 400
    if len(texto) > 2_000_000:
        return jsonify({"erro": "Texto grande demais; envie como arquivo."}), 400
    rotulo = (d.get("nome") or "Texto colado").strip()
    dest = os.path.join(WS, "exportacoes", "_recebidos")
    os.makedirs(dest, exist_ok=True)
    p = os.path.join(dest, f"{time.time_ns()}-colado.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(texto)
    tid = tarefas.nova("consulta", f"Base de consulta (texto colado): {rotulo}", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_consulta, p, rotulo)
    auditar("base_consulta_colada", rotulo)
    return jsonify({"tarefa": tid})


@bp_consulta.get("/api/vinculos")
@requer("pesquisa")
def api_vinculos():
    tipo = request.args.get("tipo") or "PESSOA"
    valor = request.args.get("valor") or ""
    caso = request.args.get("caso") or None
    try:
        niveis = max(1, min(3, int(request.args.get("niveis") or 2)))
    except ValueError:
        niveis = 2
    try:
        manuais,todos = _manuais_grafo(caso)
    except (OSError,ValueError):
        return jsonify({"erro":"Não foi possível conferir a fonte dos vínculos manuais."}),503
    try:
        g = R.vinculos(tipo,valor,niveis,caso=caso,interno=True)
        db = None if g.get('completude')=='indice_indisponivel' else R.conectar()
    except FileNotFoundError:
        g={"nos":[],"arestas":[],"truncado":None,"completude":"indice_indisponivel"}
        db=None
    except (OSError,sqlite3.Error):
        return jsonify({"erro":"Não foi possível consultar o índice. As fontes foram preservadas."}),503
    t=(tipo or '').upper()
    if t=='PESSOA' and not valor.startswith('P:'):t='NOME'
    k=R.chave_no(t,valor)
    seeds=[(t,k)] if k else []
    if t=='CONTA' and '|' not in k:
        seeds=[(t,a[side+'_valor']) for a in g['arestas']+manuais for side in ('a','b')
               if a[side+'_tipo']=='CONTA' and a[side+'_valor'].endswith('|'+k)] or seeds
    linhas=GE.fundir_manuais(g['arestas'],todos,caso)
    linhas,niveis_nos,corte=GE.subgrafo(linhas,seeds,niveis,400)
    chaves=list(dict.fromkeys(GE.chave(a) for a in linhas))
    try:
        if db is not None:
            linhas=R.referencias_relacoes(db,chaves,caso)
            linhas=[a for a in GE.fundir_manuais(linhas,todos,caso) if GE.chave(a) in set(chaves)]
        saida=_resposta_grafo(linhas,db,caso,niveis_nos)
    except (OSError,sqlite3.Error,ValueError):
        return jsonify({"erro":"Consulta incompleta por falha no índice; tente novamente."}),503
    finally:
        if db is not None:db.close()
    truncado=True if corte or g.get('truncado') else None if g.get('truncado') is None or manuais else False
    saida.update(indice_disponivel=db is not None,truncado=truncado,
                 completude='parcial' if truncado else 'nao_aferida' if truncado is None else 'completa_no_escopo',
                 limites={**g.get('limites',{}),'nos':400,'niveis':niveis})
    auditar("pesquisa_vinculos", f"{tipo}: {valor[:80]}")
    return jsonify(saida)


def _ordens_servico_grafo():
    ordens = [{"id": c["id"], "ordem_servico": c.get("ordem_servico") or c["id"]}
              for c in C.listar() if c.get("id")]

    def ordem(c):
        numeros = re.findall(r"\d+", str(c["ordem_servico"]))
        return (0, tuple(int(n) for n in numeros), c["id"]) if numeros else (1, (), c["id"])

    return sorted(ordens, key=ordem)


def _arestas_busca_grafo(db, termo, caso, registros):
    tipos=[t for t in R.TIPOS_NO if t!='CASO' and (t!='PESSOA' or termo.startswith('P:'))]
    numerico=bool(re.fullmatch(r"[\d.\-/() +]+",termo))
    tipos=[t for t in tipos if t not in ('CPF','CNPJ','TELEFONE','RG','PROCESSO','BO','CONTA')
           or numerico or (t=='CONTA' and '|' in termo)]
    chaves=[(t,R.chave_no(t,termo).lower()) for t in tipos if R.chave_no(t,termo)]
    filtros=' OR '.join('(n.tipo=? AND instr(lower(n.valor),?)>0)' for _ in chaves)
    escopo,params=R.escopo_grafo(caso)
    seeds=db.execute(f"""WITH nos AS (
        SELECT a_tipo tipo,a_valor valor FROM arestas WHERE {escopo}
        UNION SELECT b_tipo,b_valor FROM arestas WHERE {escopo})
        SELECT n.tipo,n.valor FROM nos n LEFT JOIN rotulos r ON r.tipo=n.tipo AND r.valor=n.valor
        WHERE ({filtros or '0'}) OR (n.tipo!='CASO' AND instr(lower(coalesce(r.rotulo,'')),?)>0)
        ORDER BY n.tipo,n.valor LIMIT 31""",params+params+[v for par in chaves for v in par]+[termo.lower()]).fetchall()
    manuais=GE.fundir_manuais([],registros,caso)
    busca=R._n(termo)
    manuais_seeds=[]
    for a in manuais:
        if busca in R._n(' '.join(str(a.get(k,'')) for k in ('a_valor','b_valor','a_rotulo','b_rotulo','relacao'))):
            manuais_seeds.extend((a[lado+'_tipo'],a[lado+'_valor']) for lado in ('a','b'))
    seeds=list(dict.fromkeys(manuais_seeds+[tuple(s) for s in seeds]))
    linhas={};corte=len(seeds)>30
    for tipo,valor in seeds[:30]:
        g=R.vinculos(tipo,valor,niveis=2,limite=300,caso=caso,interno=True)
        corte=corte or bool(g.get('truncado'))
        for a in g['arestas']:linhas[a['_rowid']]=a
    combinadas=GE.fundir_manuais(list(linhas.values()),registros,caso)
    combinadas,_,corte_fonte=GE.subgrafo(combinadas,seeds[:30],2,400)
    return list(dict.fromkeys(GE.chave(a) for a in combinadas)),corte or corte_fonte


def _resposta_grafo(arestas,db,caso=None,niveis=None):
    grupos=GE.agrupar(arestas,WS,caso)
    nos={}
    for a in grupos:
        for lado in ('a','b'):
            t,v=a[lado+'_tipo'],a[lado+'_valor']
            if (t,v) in nos:continue
            rotulo=v
            if db is not None:
                r=db.execute('SELECT rotulo FROM rotulos WHERE tipo=? AND valor=?',(t,v)).fetchone()
                if r and r[0]:rotulo=r[0]
                elif t=='PESSOA':
                    r=db.execute("SELECT b_valor FROM arestas WHERE a_tipo='PESSOA' AND a_valor=? AND b_tipo='NOME' LIMIT 1",(v,)).fetchone()
                    if r and r[0]:rotulo=r[0].title()
            for origem in arestas:
                for side in ('a','b'):
                    if (origem[side+'_tipo'],origem[side+'_valor'])==(t,v) and origem.get(side+'_rotulo'):
                        rotulo=origem[side+'_rotulo']
            nos[t,v]={'tipo':t,'valor':v,'nivel':(niveis or {}).get((t,v),0),'rotulo':rotulo}
    return {'nos':list(nos.values()),'arestas':grupos}


@bp_consulta.get("/api/grafo")
@requer("pesquisa")
def api_grafo():
    caso=request.args.get('caso') or ''
    termo=(request.args.get('q') or '').strip()
    ordens=_ordens_servico_grafo()
    vazio={'nos':[],'arestas':[],'casos':[c['id'] for c in ordens],
           'ordens_servico':ordens,'indice_disponivel':False}
    try:manuais,todos=_manuais_grafo(caso)
    except (OSError,ValueError):
        return jsonify({'erro':'Não foi possível ler a fonte de vínculos manuais. Preserve os arquivos e confira a integridade.'}),503
    db=None
    try:
        db=R.conectar()
        db.execute('SELECT 1 FROM arestas LIMIT 1');db.execute('SELECT 1 FROM rotulos LIMIT 1')
    except (FileNotFoundError,sqlite3.OperationalError):
        if db is not None:db.close()
        return _grafo_sem_indice(vazio,manuais,termo)
    except (OSError,sqlite3.Error):
        if db is not None:db.close()
        return jsonify({'erro':'Índice indisponível por falha de leitura; as fontes foram preservadas.'}),503
    try:
        if termo:
            chaves,corte=_arestas_busca_grafo(db,termo,caso,todos)
            lim={'relacoes':400,'seeds':30,'nos':400,'nos_por_expansao':300,'niveis':2}
        else:
            escopo,params=R.escopo_grafo(caso)
            campos=','.join(R.COLUNAS_GRAFO[:5])
            filtro='' if caso else " AND relacao!='consta nos autos'"
            rows=db.execute(f'SELECT {campos} FROM arestas WHERE {escopo}{filtro} GROUP BY {campos} '
                            f"ORDER BY min(CASE WHEN origem='manual' THEN 0 ELSE 1 END),{campos} LIMIT 401",params).fetchall()
            chaves=[tuple(r) for r in rows[:400]];corte=len(rows)>400;lim={'relacoes':400}
        busca=R._n(termo)
        manuais_chaves=[GE.chave(a) for a in manuais if not termo or busca in R._n(' '.join(str(a.get(k,'')) for k in
                        ('a_valor','b_valor','a_rotulo','b_rotulo','relacao')))]
        selecionadas=list(dict.fromkeys(manuais_chaves+chaves))
        corte=corte or len(selecionadas)>400;selecionadas=selecionadas[:400]
        arestas=R.referencias_relacoes(db,selecionadas,caso)
        conjunto=set(selecionadas)
        arestas=[a for a in GE.fundir_manuais(arestas,todos,caso) if GE.chave(a) in conjunto]
        saida=_resposta_grafo(arestas,db,caso)
    except (OSError,sqlite3.Error,ValueError):
        return jsonify({'erro':'Consulta incompleta por falha no índice; tente novamente.'}),503
    finally:db.close()
    saida.update(casos=vazio['casos'],ordens_servico=ordens,indice_disponivel=True,
                 limites=lim,truncado=True if corte else None if termo else False,
                 completude='parcial' if corte else 'nao_aferida' if termo else 'completa_no_escopo')
    auditar('grafo_consultado',f'caso={caso}; q={termo}')
    return jsonify(saida)


def _alvo_revisao(dados):
    alvo=CG.alvo(dados)
    if not os.path.isfile(os.path.join(C.caminho(alvo['caso']),'caso.json')):raise KeyError('Caso ausente.')
    return alvo


def _referencia_revisao(alvo,pasta=None):
    """Resolve a tupla exata sem os cortes da visualização; nunca migra ou reindexa."""
    import vinculos_manuais as VM
    registros=([e['registro'] for e in VM._estados(VM._ler(pasta)).values()] if pasta is not None
               else VM.listar(WS,incluir_excluidos=True))
    k=tuple(alvo[c] for c in GE.CAMPOS[:5]);linhas=[]
    try:db=R.conectar()
    except FileNotFoundError:db=None
    if db is not None:
        try:linhas=R.referencias_relacoes(db,[k],alvo['caso'])
        except sqlite3.OperationalError:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='arestas'").fetchone():raise
        finally:db.close()
    linhas=[a for a in GE.fundir_manuais(linhas,registros,alvo['caso']) if GE.chave(a)==k]
    grupos=GE.agrupar(linhas,WS,alvo['caso'],conferencias={})
    for g in grupos:
        for e in g['evidencias']:
            if e['id']==alvo['evidencia_id']:return e
    if alvo['evidencia_id'].startswith('manual:'):
        id_=alvo['evidencia_id'].split(':')[1]
        if any(r['id']==id_ and r['caso']==alvo['caso'] for r in registros):
            raise CG.Conflito('Anotação manual alterada ou excluída; reabra a evidência.')
    raise KeyError('Referência não localizada neste caso e relação.')


@bp_consulta.post('/api/grafo/evidencia/revisar')
@requer('trabalho')
def api_grafo_revisar_evidencia():
    dados=request.get_json(silent=True)
    if not isinstance(dados,dict):return jsonify({'erro':'Informe a identificação e ação de revisão.'}),400
    acao=dados.get('acao')
    campos=set(CG.CAMPOS)|{'acao','versao'}
    if acao=='conferir_fonte':campos.add('fonte')
    if acao=='registrar_observacao':campos.add('observacao')
    if set(dados)!=campos or acao not in CG.ACOES or type(dados.get('versao')) is not int or dados['versao']<0:
        return jsonify({'erro':'Campos ou versão de revisão inválidos.'}),400
    try:
        alvo=_alvo_revisao({k:dados[k] for k in CG.CAMPOS})
        revisao=CG.revisar(WS,alvo,lambda pasta:_referencia_revisao(alvo,pasta),acao,
                          request.usuario['login'],dados['versao'],dados.get('observacao',''),dados.get('fonte'))
    except KeyError:return jsonify({'erro':'Referência não localizada neste caso e relação.'}),404
    except CG.Integridade:return jsonify({'erro':'Histórico de revisões inválido. Preserve os arquivos para recuperação.'}),503
    except CG.Conflito as erro:return jsonify({'erro':str(erro)}),409
    except ValueError as erro:return jsonify({'erro':str(erro)}),400
    except (OSError,sqlite3.Error):return jsonify({'erro':'Falha ao preservar a revisão. Tente novamente.'}),503
    auditar('grafo_evidencia_revisada',f"id={revisao['id']}; caso={alvo['caso']}; acao={acao}")
    return jsonify({'ok':True,'evidencia_id':alvo['evidencia_id'],'revisao':revisao})


@bp_consulta.get('/api/grafo/evidencia/historico')
@requer('pesquisa')
def api_grafo_historico_evidencia():
    if set(request.args)!=set(CG.CAMPOS) or any(len(request.args.getlist(k))!=1 for k in request.args):
        return jsonify({'erro':'Identificação de evidência inválida.'}),400
    try:
        alvo=_alvo_revisao(dict(request.args))
        historico=CG.historico(WS,alvo)
        atual=True
        try:_referencia_revisao(alvo)
        except (KeyError,CG.Conflito):
            if not historico:raise
            atual=False
        revisao=historico[-1]['revisao'] if historico else CG.padrao(alvo)
        return jsonify({'historico':historico,'revisao':revisao,'referencia_atual':atual})
    except KeyError:return jsonify({'erro':'Referência não localizada neste caso e relação.'}),404
    except CG.Integridade:return jsonify({'erro':'Histórico de revisões inválido. Preserve os arquivos para recuperação.'}),503
    except CG.Conflito as erro:return jsonify({'erro':str(erro)}),409
    except ValueError as erro:return jsonify({'erro':str(erro)}),400
    except (OSError,sqlite3.Error):return jsonify({'erro':'Não foi possível ler o histórico de revisões.'}),503


@bp_consulta.post("/api/grafo/vinculo")
@requer("trabalho")
def api_grafo_adicionar_vinculo():
    dados = request.get_json(force=True) or {}
    if not isinstance(dados, dict):
        return jsonify({"erro": "Informe os campos do vínculo."}), 400
    def texto(chave, alias=None):
        valor = dados.get(chave, dados.get(alias, "") if alias else "")
        if not isinstance(valor, str) or len(valor) > 4000:
            raise ValueError("Campo textual inválido ou muito longo.")
        if alias and chave in dados and alias in dados and dados[chave] != dados[alias]:
            raise ValueError("Campos atual e legado divergem; confira os dados.")
        return valor.strip()
    try:
        a_tipo, b_tipo = texto("a_tipo").upper(), texto("b_tipo").upper()
        a_valor, b_valor = texto("a_valor"), texto("b_valor")
        relacao, caso = texto("relacao"), texto("caso", "caso_id")
        evidencia = {"documento": texto("documento", "fonte"), "pagina": dados.get("pagina"),
                     "fls": texto("fls"), "observacao": texto("observacao", "obs")}
        pagina = evidencia["pagina"]
        if pagina is not None and (type(pagina) is not int or pagina < 1):
            raise ValueError("Página deve ser um número inteiro positivo.")
        for tipo, valor in ((a_tipo,a_valor),(b_tipo,b_valor)):
            if tipo not in R.TIPOS_NO or (tipo == "PESSOA" and not valor.startswith("P:")):
                raise ValueError("Use um identificador de registro para Pessoa; para nome sem identidade confirmada, selecione Nome candidato.")
        a_valor, b_valor = R.chave_no(a_tipo,a_valor), R.chave_no(b_tipo,b_valor)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    if not (a_valor and b_valor and relacao and caso):
        return jsonify({"erro": "Informe origem, destino, relação e O.S. associada."}), 400
    try:
        existente = os.path.isfile(os.path.join(C.caminho(caso), "caso.json"))
    except ValueError:
        existente = False
    if not existente:
        return jsonify({"erro": "O.S. não localizada no cadastro."}), 404
    import vinculos_manuais as VM
    # Capture a projeção legada antes de criar a nova fonte; falha de cache não impede salvar.
    db = None
    try:
        db = R.conectar()
    except (OSError, sqlite3.Error):
        pass
    if db is not None:
        try:
            db.execute("BEGIN IMMEDIATE")
            VM.migrar_legados(WS, db)
            db.commit()
        except (OSError, sqlite3.Error, ValueError):
            db.rollback()
            return jsonify({"erro":"Não foi possível preservar integralmente os vínculos anteriores. Nenhum vínculo novo foi salvo. Tente novamente; os dados anteriores foram mantidos."}),503
        finally:
            db.close()
    try:
        registro = VM.criar(WS, {"a_tipo":a_tipo,"a_valor":a_valor,"b_tipo":b_tipo,"b_valor":b_valor,
                                "relacao":relacao,"caso":caso,"evidencia":evidencia,
                                "a_rotulo":texto("a_rotulo"),"b_rotulo":texto("b_rotulo")}, request.usuario["login"])
    except VM.Conflito:
        return jsonify({"erro":"Este vínculo com esta fonte já foi registrado ou sofreu alteração concorrente."}),409
    except ValueError as e:
        return jsonify({"erro":str(e)}),400
    except OSError:
        return jsonify({"erro":"Falha ao salvar vínculo; tente novamente sem fechar o formulário."}),503
    pendente = _projetar_manuais()
    auditar("grafo_vinculo_criado", f"id={registro['id']}; caso={caso}")
    return jsonify({"ok":True,"id":registro["id"],"versao":registro["versao"],"indexacao_pendente":pendente,
                    "aviso":"Vínculo salvo. Índice pendente de atualização." if pendente else ""})


def _projetar_manuais():
    import vinculos_manuais as VM
    db = None
    try:
        db = R.conectar()
        db.execute("BEGIN IMMEDIATE")
        VM.projetar(WS, db)
        db.commit()
        return False
    except (OSError, sqlite3.Error, ValueError):
        if db is not None: db.rollback()
        return True
    finally:
        if db is not None: db.close()


@bp_consulta.post("/api/grafo/vinculo/remover")
@requer("trabalho")
def api_grafo_remover_vinculo():
    dados = request.get_json(force=True, silent=True)
    if not isinstance(dados, dict) or set(dados) != {"id", "caso", "versao"}:
        return jsonify({"erro": "Informe somente ID, O.S. e versão do vínculo manual."}), 400
    id_, caso, versao = dados["id"], dados["caso"], dados["versao"]
    if (not isinstance(id_, str) or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", id_)
            or not isinstance(caso, str) or not caso or len(caso) > 4000
            or type(versao) is not int or versao < 1):
        return jsonify({"erro": "ID, O.S. ou versão inválidos."}), 400
    try:
        caminho = C.caminho(caso)
    except ValueError:
        return jsonify({"erro": "ID da O.S. inválido."}), 400
    if not os.path.isfile(os.path.join(caminho, "caso.json")):
        return jsonify({"erro": "Vínculo manual não localizado nesta O.S."}), 404
    import vinculos_manuais as VM
    try:
        registro = next((r for r in VM.listar(WS, incluir_excluidos=True)
                         if r["id"] == id_ and r["caso"] == caso), None)
    except (OSError, ValueError):
        return jsonify({"erro": "Não foi possível conferir a fonte dos vínculos. Nenhum vínculo foi excluído."}), 503
    if registro is None:
        return jsonify({"erro": "Vínculo manual não localizado nesta O.S."}), 404
    if registro["excluido"] or registro["versao"] != versao:
        return jsonify({"erro": "Vínculo já excluído ou alterado. Atualize o grafo antes de tentar novamente."}), 409
    try:
        excluido = VM.excluir(WS, id_, request.usuario["login"], versao=versao)
    except VM.Conflito:
        return jsonify({"erro": "Vínculo já excluído ou alterado. Atualize o grafo antes de tentar novamente."}), 409
    except KeyError:
        return jsonify({"erro": "Vínculo manual não localizado nesta O.S."}), 404
    except (OSError, ValueError):
        return jsonify({"erro": "Falha ao preservar a exclusão. Tente novamente; os dados anteriores foram mantidos."}), 503
    pendente = _projetar_manuais()
    auditar("grafo_vinculo_removido", f"id={id_}; caso={caso}")
    return jsonify({"ok": True, "id": id_, "versao": excluido["versao"],
                    "indexacao_pendente": pendente,
                    "aviso": "Vínculo excluído. Índice pendente de atualização." if pendente else ""})



@bp_consulta.post("/api/consulta/bases/<bid>/remover")
@requer("dados")
def api_bases_remover(bid):
    try:
        Q.remover(bid)
    except FileNotFoundError:
        abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    auditar("base_consulta_removida", bid)
    return jsonify({"ok": True})


@bp_consulta.get("/api/referencias")
@requer("dados")
def api_refs():
    return jsonify(RF.listar(request.args.get("autor") or None))


@bp_consulta.post("/api/referencias/importar")
@requer("dados")
def api_refs_importar():
    try:
        p, nome = salvar_upload("arquivo", (".docx", ".pdf", ".md"))
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    f = request.form
    if not (f.get("autor") or "").strip():
        return jsonify({"erro": "Informe o autor."}), 400
    dados = {k: f.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")} | {
        "enviado_por": request.usuario["login"]
    }
    tid = tarefas.nova("referencia", f"Referência: {nome} ({dados['autor']})", request.usuario["login"])
    tarefas.rodar(tid, tarefas.importar_referencia, p, dados)
    auditar("referencia_importada", f"{nome} — {dados['autor']}")
    return jsonify({"tarefa": tid})


@bp_consulta.post("/api/referencias/<rid>")
@requer("dados")
def api_refs_atualizar(rid):
    d = request.get_json(force=True) or {}
    try:
        m = RF.atualizar(rid, **{k: d.get(k) for k in ("autor", "modalidade", "natureza", "peso", "obs")})
    except FileNotFoundError:
        abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    auditar("referencia_atualizada", rid)
    return jsonify(m)


@bp_consulta.post("/api/referencias/<rid>/remover")
@requer("dados")
def api_refs_remover(rid):
    try:
        RF.remover(rid)
    except FileNotFoundError:
        abort(404)
    threading.Thread(target=tarefas.indexar, daemon=True).start()
    auditar("referencia_removida", rid)
    return jsonify({"ok": True})


@bp_consulta.get("/api/pesquisa/pessoas")
@requer("pesquisa")
def api_pesquisa_pessoas():
    f = {
        k: request.args.get(k)
        for k in (
            "nome", "mae", "pai", "cpf", "rg", "telefone", "cnpj", "empresa", "endereco", "texto",
            "processo", "bo", "placa", "mandado", "cautelar", "mandado_estado", "cautelar_estado",
            "objeto", "local", "data"
        )
    }
    try:
        ps, oc = R.pesquisa_relacional(f, origem=request.args.get("origem") or None)
    except FileNotFoundError:
        return jsonify({"pessoas": [], "ocorrencias": [], "aviso": "Base ainda vazia."})
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    auditar("pesquisa_pessoas", json.dumps({k: v for k, v in f.items() if v}, ensure_ascii=False)[:300])
    return jsonify({"pessoas": ps, "ocorrencias": oc, "aviso": None if ps or oc else "Nenhum resultado."})


@bp_consulta.get("/api/busca")
@requer("pesquisa")
def api_busca():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"trechos": [], "entidades": [], "aviso": None})
    try:
        tipo = request.args.get("tipo") or None
        trechos, aviso = R.buscar(q, caso=request.args.get("caso") or None, tipo=tipo, n=int(request.args.get("n") or 25))
        ents = (
            R.entidade(q)
            if (len(re.sub(r"\D", "", q)) >= 6 or "@" in q or re.fullmatch(r"[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}", q))
            else []
        )
        auditar("pesquisa_texto", q[:200])
        return jsonify({"trechos": trechos, "entidades": ents, "aviso": aviso})
    except FileNotFoundError:
        return jsonify({"trechos": [], "entidades": [], "aviso": "Índice ainda não criado — processe um caso primeiro."})
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400


@bp_consulta.get("/api/cruzar/<id_>")
@requer("trabalho")
def api_cruzar(id_):
    try:
        return jsonify(R.cruzar(id_))
    except FileNotFoundError:
        return jsonify([])

