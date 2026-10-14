"""Agrupamento de referências do grafo. Sem Flask, escrita ou inferência de identidade."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote

CAMPOS = ('a_tipo','a_valor','b_tipo','b_valor','relacao','origem','fonte','localizador')


def chave(aresta):
    return tuple(aresta[k] for k in CAMPOS[:5])


def _serial(valor):
    return json.dumps(valor,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def _hash(valor):
    return hashlib.sha256(_serial(valor).encode('utf-8')).hexdigest()


def _json(texto, schema):
    try:
        meta=json.loads(texto)
        return meta if isinstance(meta,dict) and meta.get('schema')==schema else {}
    except (TypeError,ValueError):
        return {}


def fundir_manuais(arestas,registros,caso=None):
    """Fonte autoritativa prevalece sobre cache, inclusive migração parcial.

    Cada snapshot legado cobre apenas uma ocorrência igual da projeção antiga.
    O ordinal conserva duplicatas reais ainda não migradas, sem criar evento em GET.
    """
    ids={r['id'] for r in registros}
    legados=Counter(tuple(r['legado'].get(k) for k in CAMPOS) for r in registros if isinstance(r.get('legado'),dict))
    resultado=[]
    for a in arestas:
        if a['origem']=='manual':
            if _json(a.get('localizador'),'astra-manual/1').get('id') in ids:
                continue
            original=tuple(a.get(k) for k in CAMPOS)
            if legados[original]:
                legados[original]-=1
                continue
        resultado.append(a)
    for r in registros:
        if not r['excluido'] and (not caso or r.get('caso')==caso):
            e=r.get('evidencia') or {}
            loc=' · '.join(str(x) for x in (e.get('documento'),f"pág. {e['pagina']}" if e.get('pagina') else None,
                    f"fls. {e['fls']}" if e.get('fls') else None,e.get('observacao')) if x)
            resultado.append({**r,'origem':'manual','fonte':r.get('caso'),'localizador':loc})
    return resultado


def _pagina(valor):
    return valor if type(valor) is int and valor>0 else None


def _caso_cadastrado(ws,valor):
    if not isinstance(valor,str) or not re.fullmatch(r'[\w.\-]+',valor,flags=re.A):return None
    raiz=Path(ws).resolve()/'casos';base=raiz/valor
    try:
        if raiz.is_symlink() or base.is_symlink():return None
        if hasattr(base,'is_junction') and (base.is_junction() or raiz.is_junction()):return None
        if base.resolve().is_relative_to(raiz.resolve()) and (base/'caso.json').is_file():return valor
    except (OSError,ValueError):pass
    return None


def _legado(a,ws):
    loc=a.get('localizador') or ''
    origem=a['origem']
    caso=a.get('fonte') if origem in ('caso','manual') else None
    if origem not in ('caso','manual','consulta'):caso=_caso_cadastrado(ws,a.get('fonte'))
    meta={'localizador_original':loc,'caso':caso,
          'tipo':{'consulta':'consulta','caso':'documental'}.get(origem,'origem_desconhecida'), 'documento':None}
    # Caminho literal no início do localizador; nenhum PDF é escolhido por proximidade.
    caminho=re.split(r';|\s+p[áa]g\.?\s|\s+seq\s',loc,maxsplit=1,flags=re.I)[0].strip()
    if caminho.replace('\\','/').startswith('casos/'):
        meta['arquivo_original' if '/00-originais/' in caminho.replace('\\','/') else 'arquivo_derivado']=caminho
    pg=re.search(r'\bp[áa]g(?:ina)?s?\.?\s*(\d+(?:\s*[|,]\s*\d+)*)',loc,re.I)
    if pg and not re.match(r'\s*[-–]',loc[pg.end():]):
        paginas=[int(n) for n in re.findall(r'\d+',pg.group(1)) if int(n)>0]
        meta['paginas']=paginas or None
        meta['pagina']=paginas[0] if len(paginas)==1 else None
    fls=re.search(r'\bfls?\.?\s*([^;·\n]+)',loc,re.I)
    if fls:meta['fls']=fls.group(1).strip()
    return meta


def _url(ws,caso,caminho,pagina=None):
    if not caminho:return None,None,None
    if not isinstance(caminho,str) or not isinstance(caso,str) or not re.fullmatch(r'[\w.\-]+',caso,flags=re.A):
        return None,False,'CAMINHO DE FONTE REJEITADO'
    partes=caminho.replace('\\','/').split('/')
    if any(not p or p in ('.','..') or ':' in p for p in partes):return None,False,'CAMINHO DE FONTE REJEITADO'
    if partes[0]=='casos':
        if len(partes)<3 or partes[1]!=caso:return None,False,'CAMINHO DE OUTRA O.S. REJEITADO'
        partes=partes[2:]
    if not partes or partes[0] not in ('00-originais','01-extracao','02-analise','03-relatorios','caso.json','registro-tratamento.md'):
        return None,False,'CAMINHO DE FONTE REJEITADO'
    raiz=Path(ws).resolve(); base=raiz/'casos'/caso; alvo=base.joinpath(*partes)
    try:
        for p in (raiz/'casos',base,*[base.joinpath(*partes[:n]) for n in range(1,len(partes)+1)]):
            if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()):return None,False,'ATALHO DE FONTE REJEITADO'
        if not alvo.resolve().is_relative_to(base.resolve()) or not base.resolve().is_relative_to(raiz):
            return None,False,'CAMINHO DE FONTE REJEITADO'
        if not alvo.is_file():return None,False,'ARQUIVO DE FONTE INDISPONÍVEL'
    except (OSError,ValueError):return None,False,'ARQUIVO DE FONTE INDISPONÍVEL'
    url='/arquivo/'+quote(caso,safe='')+'/'+('/'.join(quote(p,safe='') for p in partes))
    if pagina and alvo.suffix.lower()=='.pdf':url+='#page='+str(pagina)
    return url,True,None


def referencia(a,ws,ordinal=0):
    manual=a['origem']=='manual'
    if manual:
        # Observação do operador é texto, nunca um envelope JSON ou caminho de arquivo.
        nativo=_json(a.get('localizador'),'astra-manual/1') if 'evidencia' not in a else {}
        dados=a.get('evidencia') if isinstance(a.get('evidencia'),dict) else nativo.get('evidencia',{})
        if not isinstance(dados,dict):dados={}
        meta={'caso':a.get('caso',a.get('fonte')),'documento':dados.get('documento'),
              'pagina':dados.get('pagina'),'fls':dados.get('fls'),'observacao':dados.get('observacao'),
              'localizador_original':a.get('legado',{}).get('localizador',a.get('localizador'))}
        doc=meta.get('documento')
        if isinstance(doc,str) and doc.replace('\\','/').startswith(('00-originais/','casos/')):
            meta['arquivo_original']=doc
        tipo='hipotese_manual'
    else:
        meta=_json(a.get('localizador'),'astra-evidencia/1') or _legado(a,ws)
        tipo=meta.get('tipo') if meta.get('tipo') in ('documental','cadastro','consulta','extracao_candidata') else 'origem_desconhecida'
    caso=meta.get('caso') if isinstance(meta.get('caso'),str) else None
    pagina=_pagina(meta.get('pagina'))
    paginas=meta.get('paginas')
    paginas=[p for p in paginas if _pagina(p)] if isinstance(paginas,list) else None
    if not paginas and pagina:paginas=[pagina]
    e={k:meta.get(k) for k in ('documento','arquivo_derivado','arquivo_original','fls','trecho','data_fato',
                             'sha256_original','sha256_derivado','extraido_em','status_fonte')}
    e.update(origem=a['origem'],tipo=tipo,caso=caso,pagina=pagina,paginas=paginas or None,
             localizador_original=meta.get('localizador_original',a.get('localizador')),
             registro_origem=meta.get('registro_origem') if isinstance(meta.get('registro_origem'),dict) else {'linha':None,'seq':None},
             posicao=meta.get('posicao') if meta.get('posicao') in ('sustenta','contradiz') else 'nao_classificada',
             manual_id=a.get('id') if manual else None,manual_versao=a.get('versao') if manual else None,
             observacao=meta.get('observacao') if manual else None,
             conferencia={'estado':'nao_conferida','usuario':None,'data':None})
    if manual and a.get('status')=='conferido' and a.get('revisado_por') and a.get('revisado_em'):
        e['conferencia']={'estado':'conferida_pelo_operador','usuario':a['revisado_por'],'data':a['revisado_em']}
    e['id']=('manual:'+a['id']+':'+str(a['versao'])) if manual and a.get('id') else 'ev-'+_hash([tuple(a.get(k) for k in CAMPOS),ordinal])
    avisos=[]
    if meta.get('caso') is not None and caso is None:avisos.append('IDENTIFICADOR DE CASO INVÁLIDO NA FONTE')
    if tipo=='origem_desconhecida':avisos.append('ORIGEM LEGADA NÃO CLASSIFICADA')
    for lado in ('original','derivado'):
        url,disponivel,aviso=_url(ws,caso,e['arquivo_'+lado],pagina if lado=='original' else None)
        e['url_'+lado]=url;e[lado+'_disponivel']=disponivel
        if aviso:avisos.append(aviso)
    e['fonte_disponivel']=bool(e['url_original'] or e['url_derivado'])
    if not e['fls']:avisos.append('FLS. NÃO INFORMADAS')
    if not e['arquivo_original']:avisos.append('DOCUMENTO ORIGINAL NÃO IDENTIFICADO POR CAMINHO EXPLÍCITO')
    if manual:e['trecho']=None
    e['avisos']=list(dict.fromkeys(avisos))
    return e


def agrupar(arestas,ws,caso=None,conferencias=None):
    import conferencias_grafo as CG
    if conferencias is None:conferencias=CG.listar(ws)
    grupos={};ordinais=Counter()
    for a in arestas:
        assinatura=_serial(tuple(a.get(k) for k in CAMPOS))
        ordinal=ordinais[assinatura];ordinais[assinatura]+=1
        e=referencia(a,ws,ordinal)
        if caso and e['caso']!=caso:continue
        k=chave(a)
        alvo={'caso':e['caso'],**dict(zip(CAMPOS[:5],k)),'evidencia_id':e['id']}
        revisao=CG.padrao(alvo)
        e['revisao']=conferencias.get(revisao['id'],revisao)
        if e['revisao']['versao'] and e['revisao']['fonte_conferida']:
            e['conferencia']={'estado':'conferida_pelo_operador','usuario':e['revisao']['fonte_usuario'],
                              'data':e['revisao']['fonte_data'],'recurso':e['revisao']['recurso_conferido']}
        if k not in grupos:
            grupos[k]={**dict(zip(CAMPOS[:5],k)),'relacao_id':'rel-'+_hash(k),'evidencias':[],
                       'naturezas':[],'evidencias_truncadas':False}
        g=grupos[k];g['evidencias'].append(e)
        if e['tipo'] not in g['naturezas']:g['naturezas'].append(e['tipo'])
        if 'NOME' in (a['a_tipo'],a['b_tipo']) and 'correspondencia_candidata' not in g['naturezas']:
            g['naturezas'].append('correspondencia_candidata')
    for g in grupos.values():
        es=g['evidencias'];g['total_evidencias']=len(es)
        origens={e['origem'] for e in es};fontes={e['caso'] for e in es}
        g['origem']=next(iter(origens)) if len(origens)==1 else 'mista'
        g['fonte']=next(iter(fontes)) if len(fontes)==1 else 'múltiplas fontes'
        g['localizador']=es[0]['localizador_original'] if len(es)==1 else str(len(es))+' referências'
        manuais=[e for e in es if e['tipo']=='hipotese_manual']
        if len(manuais)==1 and manuais[0]['manual_id']:
            m=manuais[0]
            g.update(id=m['manual_id'],versao=m['manual_versao'],caso=m['caso'],
                     evidencia={'documento':m['documento'] or '', 'pagina':m['pagina'],
                                'fls':m['fls'] or '', 'observacao':m['observacao'] or ''})
    return list(grupos.values())


def subgrafo(arestas,seeds,niveis,limite):
    """Alcance direcionalmente neutro; nomes não propagam identidade entre registros."""
    vistos={s:0 for s in seeds};fronteira=list(vistos);selecionadas={};corte=False
    adj={}
    for a in arestas:
        for no in ((a['a_tipo'],a['a_valor']),(a['b_tipo'],a['b_valor'])):adj.setdefault(no,[]).append(a)
    for nivel in range(1,niveis+1):
        prox=[]
        for no in fronteira:
            if no[0]=='NOME' and vistos[no]!=0:continue
            for a in adj.get(no,[]):
                novos={n for n in ((a['a_tipo'],a['a_valor']),(a['b_tipo'],a['b_valor'])) if n not in vistos}
                if len(vistos)+len(novos)>limite:corte=True;continue
                selecionadas[chave(a)]=None
                for n in novos:vistos[n]=nivel;prox.append(n)
        fronteira=prox
    return [a for a in arestas if chave(a) in selecionadas],vistos,corte
