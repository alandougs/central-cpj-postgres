#!/usr/bin/env python3
"""Rotas de bases de consulta, referências, pesquisa textual/relacional e cruzamento de dados."""
import hashlib
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


_cadastro_grafo = {}
_cadastro_guard = threading.Lock()


class GrafoAlterado(ValueError):
    pass


def _stat_grafo(p):
    try:
        s=os.stat(p)
        return [s.st_mtime_ns,s.st_ctime_ns,s.st_size,s.st_ino]
    except FileNotFoundError:return None


def _ordens_servico_grafo():
    # A listagem/stat é refeita em todo GET; só o JSON inalterado é reutilizado.
    raiz=os.path.abspath(C.CASOS);ordens=[]
    with _cadastro_guard:
        cache=_cadastro_grafo.setdefault(raiz,{})
        atuais=set()
        if os.path.isdir(raiz):
            for d in os.scandir(raiz):
                if d.name.startswith('_') or not d.is_dir():continue
                assinatura=_stat_grafo(os.path.join(d.path,'caso.json'))
                if assinatura is None:continue
                atuais.add(d.name);anterior=cache.get(d.name)
                if anterior is None or anterior[0]!=assinatura:
                    try:
                        c=C.carregar(d.name)
                        item={'id':c['id'],'ordem_servico':c.get('ordem_servico') or c['id']} if c.get('id') else None
                    except (OSError,ValueError,TypeError,AttributeError):item=None
                    cache[d.name]=(assinatura,item)
                if cache[d.name][1]:ordens.append(dict(cache[d.name][1]))
        for nome in list(cache):
            if nome not in atuais:del cache[nome]
    def ordem(c):
        ns=re.findall(r'\d+',str(c['ordem_servico']))
        return (0,tuple(int(n) for n in ns),c['id']) if ns else (1,(),c['id'])
    return sorted(ordens,key=ordem)


def _paginacao_grafo():
    valores=[]
    for nome,padrao,maximo in (('pagina','1',None),('limite','400',400)):
        texto=request.args.get(nome,padrao)
        if len(request.args.getlist(nome))>1 or not re.fullmatch(r'[0-9]+',texto):raise ValueError('Página/limite inválidos.')
        numero=int(texto)
        if numero<1 or (maximo and numero>maximo):raise ValueError('Página/limite fora do intervalo permitido.')
        valores.append(numero)
    if (valores[0]-1)*valores[1]>2**63-1:raise ValueError('Página fora do intervalo permitido.')
    if len(request.args.getlist('revisao'))>1:raise ValueError('Revisão repetida.')
    revisao=request.args.get('revisao')
    if revisao is not None and not re.fullmatch(r'[0-9a-f]{64}',revisao):raise ValueError('Revisão de consulta inválida.')
    return valores


def _estado_grafo():
    wal=_stat_grafo(R.DB+'-wal')
    # Abrir um banco WAL para ler pode criar só o cabeçalho, sem alteração de dados.
    estado=[_stat_grafo(R.DB),wal if wal and wal[2]>32 else None]
    for sub in ('eventos','conferencias'):
        pasta=os.path.join(WS,'consulta','_grafo-manual',sub)
        estado.append(sorted((d.name,_stat_grafo(d.path)) for d in os.scandir(pasta) if d.name.endswith('.json')) if os.path.isdir(pasta) else [])
    return estado


def _resposta_grafo(arestas,db,caso=None,niveis=None,manuais=None):
    grupos=GE.agrupar(arestas,WS,caso)
    chaves=list(dict.fromkeys((a[l+'_tipo'],a[l+'_valor']) for a in grupos for l in ('a','b')))
    rot=R.rotulos_em_lote(db,chaves,manuais) if db is not None else {}
    for a in manuais or arestas:
        for lado in ('a','b'):
            if a.get(lado+'_rotulo'):rot[a[lado+'_tipo'],a[lado+'_valor']]=a[lado+'_rotulo']
    nos=[{'tipo':t,'valor':v,'nivel':(niveis or {}).get((t,v),0),'rotulo':rot.get((t,v),v)} for t,v in chaves]
    return {'nos':nos,'arestas':grupos}


def _pagina_manuais(manuais,termo,pagina,limite,seed,niveis):
    chaves=list(dict.fromkeys(GE.chave(a) for a in manuais))
    niveis_nos={}
    if termo or seed is not None:
        if seed is None:
            busca=R._n(termo)
            seeds=[(a[l+'_tipo'],a[l+'_valor']) for a in manuais for l in ('a','b') if busca in R._n(' '.join(str(a.get(k,'')) for k in ('a_valor','b_valor','a_rotulo','b_rotulo','relacao')))]
        else:
            t,v=seed
            seeds=[(a[l+'_tipo'],a[l+'_valor']) for a in manuais for l in ('a','b') if a[l+'_tipo']==t and
                   (a[l+'_valor'].endswith('|'+v) if t=='CONTA' and '|' not in v else a[l+'_valor']==v)]
        linhas,niveis_nos,_=GE.subgrafo(manuais,seeds,niveis,max(1,len(manuais)*2+len(seeds)))
        chaves=list(dict.fromkeys(GE.chave(a) for a in linhas))
    chaves.sort(key=lambda k:tuple((v is not None,v or '') for v in k))
    selecionadas=chaves[(pagina-1)*limite:pagina*limite]
    meta=R.metadados_pagina(len(chaves),pagina,limite,len(selecionadas))
    meta.update(total=None,total_disponivel=len(chaves),truncado=True if len(chaves)>len(selecionadas) else None,
                completude='nao_aferida',niveis_nos=niveis_nos)
    return selecionadas,meta


def _consultar_grafo_paginado(caso,termo,pagina,limite,ordens,seed=None,niveis=2):
    inicial=_estado_grafo()
    revisao=hashlib.sha256(json.dumps([ordens,inicial,caso,termo,seed,niveis,limite],ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
    if request.args.get('revisao') not in (None,revisao):raise GrafoAlterado('O grafo foi alterado; recarregue a primeira página.')
    _,registros=_manuais_grafo(caso);db=None;disponivel=False
    try:
        try:
            db=R.conectar();db.execute('BEGIN')
            db.execute('SELECT 1 FROM arestas LIMIT 1');db.execute('SELECT 1 FROM rotulos LIMIT 1')
            disponivel=True
        except (FileNotFoundError,sqlite3.OperationalError):
            if db is not None:db.close();db=None
        if disponivel:
            escopo,params=R.escopo_grafo(caso)
            rows=db.execute('SELECT '+','.join(GE.CAMPOS)+" FROM arestas WHERE origem='manual' AND "+escopo,params).fetchall()
            manuais=GE.fundir_manuais([dict(zip(GE.CAMPOS,r)) for r in rows],registros,caso)
            manuais=[a for a in manuais if not caso or a.get('caso',a.get('fonte'))==caso]
            meta=R.pagina_grafo(db,caso,termo,manuais,pagina,limite,seed,niveis,any(c['id']==caso for c in ordens))
            chaves=meta.pop('chaves')
            linhas=R.referencias_relacoes(db,chaves,caso)
            linhas=[a for a in GE.fundir_manuais(linhas,registros,caso) if GE.chave(a) in set(chaves)]
        else:
            manuais=GE.fundir_manuais([],registros,caso)
            chaves,meta=_pagina_manuais(manuais,termo,pagina,limite,seed,niveis)
            linhas=[a for a in manuais if GE.chave(a) in set(chaves)]
        saida=_resposta_grafo(linhas,db,caso,niveis=meta.pop('niveis_nos',{}),manuais=manuais)
        por_chave={GE.chave(a):a for a in saida['arestas']}
        saida['arestas']=[por_chave[k] for k in chaves if k in por_chave]
        if _estado_grafo()!=inicial:raise GrafoAlterado('O grafo mudou durante a leitura; recarregue a primeira página.')
        saida.update(meta,indice_disponivel=disponivel,revisao=revisao)
        if not disponivel:saida['aviso']='Índice indisponível. As anotações preservadas não representam toda a documentação.'
        return saida
    finally:
        if db is not None:db.close()


@bp_consulta.get('/api/grafo')
@requer('pesquisa')
def api_grafo():
    try:
        pagina,limite=_paginacao_grafo()
    except ValueError as erro:return jsonify({'erro':str(erro)}),400
    caso=request.args.get('caso') or '';termo=(request.args.get('q') or '').strip()
    ordens=_ordens_servico_grafo()
    try:
        saida=_consultar_grafo_paginado(caso,termo,pagina,limite,ordens)
    except GrafoAlterado as erro:return jsonify({'erro':str(erro),'recarregar':True}),409
    except (OSError,sqlite3.Error,ValueError):return jsonify({'erro':'Não foi possível conferir o índice e as fontes. Os arquivos foram preservados.'}),503
    saida.update(casos=[c['id'] for c in ordens],ordens_servico=ordens)
    auditar('grafo_consultado',f'caso={caso}; q={termo}; pagina={pagina}')
    return jsonify(saida)


@bp_consulta.get('/api/vinculos')
@requer('pesquisa')
def api_vinculos():
    try:pagina,limite=_paginacao_grafo()
    except ValueError as erro:return jsonify({'erro':str(erro)}),400
    tipo=request.args.get('tipo') or 'PESSOA';valor=request.args.get('valor') or ''
    t=tipo.upper()
    if t=='PESSOA' and not valor.startswith('P:'):t='NOME'
    try:niveis=max(1,min(3,int(request.args.get('niveis') or 2)))
    except ValueError:niveis=2
    try:
        saida=_consultar_grafo_paginado(request.args.get('caso') or '', '',pagina,limite,_ordens_servico_grafo(),(t,R.chave_no(t,valor)),niveis)
    except GrafoAlterado as erro:return jsonify({'erro':str(erro),'recarregar':True}),409
    except (OSError,sqlite3.Error,ValueError):return jsonify({'erro':'Não foi possível conferir o índice e as fontes. Os arquivos foram preservados.'}),503
    saida['limites']['niveis']=niveis
    auditar('pesquisa_vinculos',f'{tipo}: {valor[:80]}; pagina={pagina}')
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


# ------------------------------------------------------------ Inteligência Etapa 1: Correlações e Mapa Offline
import correlacoes as CORR  # noqa: E402


def _ws_inteligencia():
    return os.environ.get("CPJ_WORKSPACE") or getattr(C, "WS", None) or WS


@bp_consulta.get("/api/inteligencia/correlacoes")
@requer("pesquisa")
def api_inteligencia_correlacoes():
    caso = (request.args.get("caso") or "").strip() or None
    tipo = (request.args.get("tipo") or "").strip().upper() or None
    if tipo and tipo not in CORR.TIPOS_PERMITIDOS:
        return jsonify({"erro": f"Tipo de identificador inválido: {tipo}. Permitidos: {', '.join(CORR.TIPOS_PERMITIDOS)}."}), 400

    estado = (request.args.get("estado") or "").strip().lower() or None
    if estado and estado not in ("ativo", "fixado", "descartado", "ativos_e_fixados", "todos"):
        return jsonify({"erro": f"Filtro de estado inválido: {estado}."}), 400

    lido_arg = (request.args.get("lido") or "").strip().lower()
    lido = None
    if lido_arg in ("1", "true", "sim"):
        lido = True
    elif lido_arg in ("0", "false", "nao", "não"):
        lido = False
    elif lido_arg:
        return jsonify({"erro": "Parâmetro 'lido' inválido (use 1/0 ou true/false)."}), 400

    inc_sem_sup = (request.args.get("incluir_sem_suporte") or "").strip().lower() in ("1", "true", "sim")
    ordem = (request.args.get("ordem") or "procedimentos").strip().lower()
    if ordem not in ("procedimentos", "recentes"):
        return jsonify({"erro": "Parâmetro 'ordem' inválido (use 'procedimentos' ou 'recentes')."}), 400

    try:
        pagina = max(1, int(request.args.get("pagina") or 1))
        limite = max(1, min(500, int(request.args.get("limite") or 50)))
    except ValueError:
        return jsonify({"erro": "Parâmetros 'pagina' e 'limite' devem ser inteiros."}), 400

    res = CORR.consultar_correlacoes(
        _ws_inteligencia(),
        caso=caso,
        tipo=tipo,
        estado=estado,
        lido=lido,
        incluir_sem_suporte=inc_sem_sup,
        ordem=ordem,
        pagina=pagina,
        limite=limite,
    )
    auditar("inteligencia_correlacoes", f"caso={caso or '*'} tipo={tipo or '*'} estado={estado or '*'} p={pagina}")
    return jsonify(res)


@bp_consulta.get("/api/inteligencia/mapa")
@requer("pesquisa")
def api_inteligencia_mapa():
    caso = (request.args.get("caso") or "").strip() or None
    tipo_pessoa = (request.args.get("tipo_pessoa") or "").strip().upper() or None
    if tipo_pessoa and tipo_pessoa not in ("PF", "PJ"):
        return jsonify({"erro": "Parâmetro 'tipo_pessoa' inválido (use 'PF' ou 'PJ')."}), 400

    papel = (request.args.get("papel") or "").strip() or None
    municipio = (request.args.get("municipio") or "").strip() or None
    uf = (request.args.get("uf") or "").strip().upper() or None
    if uf and len(uf) != 2:
        return jsonify({"erro": "Parâmetro 'uf' deve ter 2 letras."}), 400

    correlacao_id = (request.args.get("correlacao_id") or "").strip() or None
    try:
        limite = max(1, min(2000, int(request.args.get("limite") or 500)))
    except ValueError:
        return jsonify({"erro": "Parâmetro 'limite' deve ser inteiro."}), 400

    res = CORR.consultar_mapa(
        _ws_inteligencia(),
        caso=caso,
        tipo_pessoa=tipo_pessoa,
        papel=papel,
        municipio=municipio,
        uf=uf,
        correlacao_id=correlacao_id,
        limite=limite,
    )
    auditar("inteligencia_mapa", f"caso={caso or '*'} tipo={tipo_pessoa or '*'} corr={correlacao_id or '-'}")
    return jsonify(res)


@bp_consulta.post("/api/inteligencia/correlacoes/estado")
@requer("pesquisa")
def api_inteligencia_correlacoes_estado():
    if not request.headers.get("X-CPJ"):
        return jsonify({"erro": "Cabeçalho X-CPJ obrigatório."}), 400
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({"erro": "Corpo JSON inválido."}), 400

    cid = (d.get("id") or d.get("correlacao_id") or "").strip()
    estado = d.get("estado")
    lido = d.get("lido")
    motivo = d.get("motivo")

    try:
        reg = CORR.atualizar_estado_correlacao(
            _ws_inteligencia(),
            correlacao_id=cid,
            usuario=request.usuario["login"],
            estado=estado,
            lido=lido,
            motivo=motivo,
        )
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except TimeoutError as e:
        return jsonify({"erro": str(e)}), 503

    auditar(
        "correlacao_estado_atualizado",
        f"id={cid} estado={reg['estado']} lido={reg['lido']} motivo={reg.get('motivo', '')[:80]}",
    )
    return jsonify({"ok": True, "item": reg})


