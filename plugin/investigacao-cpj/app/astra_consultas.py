"""Intenções locais: consulta referências indexadas, sem criar fatos ou vínculos."""
import re
import unicodedata
import grafo_evidencias as GE
import vinculos_manuais as VM

LIMITE=50


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',texto) if not unicodedata.combining(c)).lower().split())


def interpretar(pergunta):
    t=normalizar(pergunta)
    if 'pix' in t and re.search(r'\bo\.?\s*s\.?\b|ordens|casos',t):return 'ocorrencias_pix'
    if 'candidat' in t or ('vincul' in t and 'confirm' in t):return 'vinculos_candidatos'
    if 'document' in t and any(x in t for x in ('caminho','dinheiro','sustent')):return 'documentos_fluxo'
    if 'conta' in t and any(x in t for x in ('receber','recebeu','recebid')) and any(x in t for x in ('transfer','dinheiro')):return 'contas_recebedoras'
    return None


def _resposta(tipo,caso,status='refinar',texto=None):
    return {'status':status,'intencao':{'tipo':tipo,'entidade':None,'caso':caso,
            'filtros':{'escopo':'todas_os' if tipo=='ocorrencias_pix' else 'caso'},'limite':LIMITE,
            'ordenacao':'a_tipo,a_valor,b_tipo,b_valor,relacao:asc'},
            'resposta':texto or 'Selecione uma pessoa, conta ou chave no grafo, ou informe um identificador entre aspas. Posso localizar contas recebedoras, ocorrências de uma chave Pix, vínculos candidatos ou documentos do fluxo financeiro.',
            'opcoes':[],'grafo':{'nos':[],'arestas':[]},'total':0,'limite':LIMITE,'truncado':False,
            'proxima_pagina':None,'avisos':[]}


def _documentada(a,caso=None):
    return any(e['tipo']=='documental' and e['origem']=='caso' and e['caso'] and
               (not caso or e['caso']==caso) and e['posicao']!='contradiz' and
               (e['documento'] or e['arquivo_derivado'] or e['arquivo_original']) for e in a['evidencias'])


def _financeira(a):
    return a['a_tipo'] in ('CONTA','CHAVE_PIX') and a['b_tipo'] in ('CONTA','CHAVE_PIX') and a['relacao'].startswith('transferiu ')


def _no(a,lado):return a[lado+'_tipo'],a[lado+'_valor']


def _nos(arestas,rotulos):
    chaves=dict.fromkeys(_no(a,l) for a in arestas for l in ('a','b'))
    return [{'tipo':t,'valor':v,'rotulo':rotulos.get((t,v),v),'nivel':0} for t,v in chaves]


def consultar(pergunta,caso,entidade,ws,rag):
    tipo=interpretar(pergunta);res=_resposta(tipo,caso)
    if tipo is None:return res
    db=rag.conectar()
    try:
        # Literais do usuário são sempre parâmetros; a consulta não escreve no índice.
        db.execute('SELECT 1 FROM arestas LIMIT 1')
        escopo,params=rag.escopo_grafo(caso)
        linhas=[dict(zip(rag.COLUNAS_GRAFO,row)) for row in db.execute(
            'SELECT '+','.join(rag.COLUNAS_GRAFO)+' FROM arestas WHERE '+escopo+' ORDER BY rowid',params)]
        registros=VM.listar(ws,incluir_excluidos=True)
        manuais=GE.fundir_manuais([],registros,caso)
        linhas=GE.fundir_manuais(linhas,registros,caso)
        grupos=GE.agrupar(linhas,ws,caso)
        rotulos=rag.rotulos_em_lote(db,(_no(a,l) for a in grupos for l in ('a','b')),manuais)
        if tipo!='vinculos_candidatos':
            literal=re.search(r'["“]([^"”]{1,200})["”]',pergunta)
            if tipo=='ocorrencias_pix' and literal:
                # A pergunta explicita a chave; uma seleção antiga não a substitui.
                entidade={'tipo':'CHAVE_PIX','valor':literal.group(1)}
            if entidade is None or (literal and tipo!='ocorrencias_pix'):
                m=literal
                if not m:return res
                termo=normalizar(m.group(1));opcoes={}
                for a in grupos:
                    for l in ('a','b'):
                        t,v=_no(a,l)
                        if t not in ('PESSOA','CONTA','CHAVE_PIX','NOME'):continue
                        if termo not in normalizar(rotulos.get((t,v),v)) and termo!=normalizar(v):continue
                        opcoes.setdefault((t,v),{'tipo':t,'valor':v,'rotulo':rotulos.get((t,v),v),'fontes':[]})['fontes'].extend(a['evidencias'])
                pessoas=[o for o in opcoes.values() if o['tipo']=='PESSOA']
                candidatos=pessoas or [o for o in opcoes.values() if o['tipo']!='NOME']
                compativeis=[o for o in candidatos if entidade and o['tipo']==entidade['tipo'] and
                             rag.chave_no(o['tipo'],o['valor'])==rag.chave_no(entidade['tipo'],entidade['valor'])]
                if len(compativeis)==1:candidatos=compativeis
                if len(candidatos)!=1:
                    res.update(opcoes=candidatos[:LIMITE],resposta='Há registros distintos ou identificação insuficiente. Confira as fontes e selecione um registro; coincidência de nome não confirma identidade.' if candidatos else 'Identificador não localizado nos materiais indexados deste caso. Selecione o registro correto no grafo.')
                    if len(candidatos)>LIMITE:res['avisos'].append(f'Exibidos {LIMITE} de {len(candidatos)} registros candidatos; refine o identificador.')
                    return res
                entidade={k:candidatos[0][k] for k in ('tipo','valor')}
            t=entidade['tipo'];v=rag.chave_no(t,entidade['valor']);semente=(t,v)
            res['intencao']['entidade']={'tipo':t,'valor':v}
            if t=='NOME':
                res['resposta']='Nome candidato: selecione um registro de pessoa ou uma conta após conferir a fonte. Não uni identidades por nome.'
                return res
        selecionadas=[]
        if tipo=='ocorrencias_pix':
            if t!='CHAVE_PIX':
                res['resposta']='Selecione uma chave Pix para consultar suas ocorrências nas O.S.';return res
            rows=db.execute('SELECT '+','.join(rag.COLUNAS_GRAFO)+
                " FROM arestas WHERE (a_tipo='CHAVE_PIX' AND a_valor=?) OR (b_tipo='CHAVE_PIX' AND b_valor=?) ORDER BY rowid",(v,v))
            todas=[dict(zip(rag.COLUNAS_GRAFO,row)) for row in rows]
            todas=GE.fundir_manuais(todas,registros)
            todas=[a for a in todas if any(a[l+'_tipo']=='CHAVE_PIX' and rag.chave_no('CHAVE_PIX',a[l+'_valor'])==v for l in ('a','b'))]
            selecionadas=[a for a in GE.agrupar(todas,ws) if any(e['caso'] for e in a['evidencias'])]
            rotulos.update(rag.rotulos_em_lote(db,(_no(a,l) for a in selecionadas for l in ('a','b')),GE.fundir_manuais([],registros)))
            res['avisos'].append('Consulta explícita às O.S. indexadas que contêm exatamente esta chave. A presença em extração candidata ou hipótese manual permanece assim classificada; isso não confirma transferência, identidade nem autoria.')
        elif tipo=='vinculos_candidatos':
            selecionadas=[a for a in grupos if 'correspondencia_candidata' in a['naturezas'] or
                any(e['tipo']=='extracao_candidata' or e.get('revisao',{}).get('candidato') for e in a['evidencias'])]
            res['avisos'].append('Recorte de correspondências por nome, extrações candidatas e referências marcadas como candidatas pelo operador. Precisam de conferência; não são identidades ou autoria confirmadas.')
        elif tipo=='contas_recebedoras':
            contas={semente} if t in ('CONTA','CHAVE_PIX') else set()
            titulares=[]
            if t=='PESSOA':
                titulares=[a for a in grupos if _no(a,'a')==semente and a['b_tipo'] in ('CONTA','CHAVE_PIX') and
                    a['relacao'].startswith('titular') and _documentada(a,caso)]
                contas.update(_no(a,'b') for a in titulares)
            transferencias=[a for a in grupos if _financeira(a) and _no(a,'a') in contas and _documentada(a,caso)]
            usadas={_no(a,'a') for a in transferencias}
            selecionadas=[a for a in titulares if _no(a,'b') in usadas]+transferencias
            res['avisos'].append('Só relações direcionadas documentais e titularidade explicitamente ligada ao registro; não há junção de pessoas por nome.')
        elif tipo=='documentos_fluxo':
            if t not in ('CONTA','CHAVE_PIX'):
                res['resposta']='Selecione uma conta ou chave Pix do caminho financeiro para localizar as referências desse recorte.';return res
            fronteira={semente};vistos=set(fronteira);por_id={}
            for _ in range(2):
                proximos=set()
                for a in grupos:
                    if not _financeira(a) or not _documentada(a,caso):continue
                    extremos={_no(a,'a'),_no(a,'b')}
                    if extremos&fronteira:
                        por_id[a['relacao_id']]=a;proximos.update(extremos-vistos)
                vistos.update(proximos);fronteira=proximos
            selecionadas=list(por_id.values())
            res['avisos'].append('Recorte de até duas conexões financeiras da conta/chave selecionada; não representa toda a investigação.')
        selecionadas.sort(key=GE.chave)
        res['total']=len(selecionadas);res['truncado']=len(selecionadas)>LIMITE
        selecionadas=selecionadas[:LIMITE]
        res['grafo']={'nos':_nos(selecionadas,rotulos),'arestas':selecionadas}
        res['status']='ok' if selecionadas else 'nao_localizado'
        res['resposta']=(f'Localizadas {res["total"]} relações neste escopo. Confira abaixo cada relação e suas referências; a classificação das fontes permanece visível.' if selecionadas else
                        'Não localizado nos materiais indexados deste recorte. Isso não demonstra inexistência; confira a extração, as fontes e o identificador selecionado.')
        if res['truncado']:res['avisos'].append(f'Exibidas as primeiras {LIMITE} relações de {res["total"]}; refine a pergunta ou o identificador. Todas as referências das relações exibidas foram mantidas.')
        return res
    finally:db.close()
