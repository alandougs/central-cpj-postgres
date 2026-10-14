"""Revisões humanas por referência; fonte append-only independente do índice."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import uuid
import vinculos_manuais as VM

SCHEMA='astra-conferencia-evento/1'
CAMPOS=('caso','a_tipo','a_valor','b_tipo','b_valor','relacao','evidencia_id')
ACOES=('conferir_fonte','marcar_candidato','registrar_observacao')
Conflito=VM.Conflito


class Integridade(ValueError):
    """Fonte histórica inválida; não pode ser tratada como revisão ausente."""


def _serial(dados):
    return json.dumps(dados,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def alvo(dados):
    if not isinstance(dados,dict) or set(dados)!=set(CAMPOS):raise ValueError('Identificação de evidência inválida.')
    if any(not isinstance(dados[k],str) or not dados[k].strip() or len(dados[k])>4000 for k in CAMPOS):
        raise ValueError('Identificação de evidência inválida.')
    if not re.fullmatch(r'[\w-]+',dados['caso'],flags=re.A):raise ValueError('Caso inválido.')
    if any(dados[k] not in VM.TIPOS for k in ('a_tipo','b_tipo')):raise ValueError('Tipo de nó inválido.')
    return {k:dados[k] for k in CAMPOS}


def padrao(dados):
    try:id_='rev-'+hashlib.sha256(_serial(alvo(dados)).encode('utf-8')).hexdigest()
    except ValueError:id_=None
    return {'id':id_,'versao':0,'acao':None,'fonte_conferida':False,'recurso_conferido':None,
            'fonte_usuario':None,'fonte_data':None,'candidato':False,'observacao':'','usuario':None,'data':None}


def _pasta(eventos):
    pasta=eventos.parent/'conferencias'
    if pasta.is_symlink() or (hasattr(pasta,'is_junction') and pasta.is_junction()):
        raise ValueError('Conferências não podem ser um atalho.')
    return pasta


def _snapshot(ref):
    # Disponibilidade/URLs e overlays humanos não são conteúdo da referência.
    return {k:copy.deepcopy(v) for k,v in ref.items() if k not in
            ('revisao','conferencia','url_original','url_derivado','original_disponivel',
             'derivado_disponivel','fonte_disponivel','avisos')}


def _proximo(anterior,acao,observacao,recurso,usuario,data):
    if acao not in ACOES:raise ValueError('Ação de revisão inválida.')
    if not isinstance(observacao,str) or len(observacao)>4000:raise ValueError('Observação inválida ou muito longa.')
    if acao=='registrar_observacao' and not observacao.strip():raise ValueError('Informe a observação.')
    if acao!='registrar_observacao' and observacao:raise ValueError('Observação somente na ação correspondente.')
    if (acao=='conferir_fonte' and recurso not in ('original','derivado')) or (acao!='conferir_fonte' and recurso is not None):
        raise ValueError('Informe somente o recurso correspondente à conferência.')
    revisao={**anterior,'versao':anterior['versao']+1,'acao':acao,'usuario':usuario,'data':data}
    if acao=='conferir_fonte':revisao.update(fonte_conferida=True,recurso_conferido=recurso,fonte_usuario=usuario,fonte_data=data)
    if acao=='marcar_candidato':revisao['candidato']=True
    if acao=='registrar_observacao':revisao['observacao']=observacao
    return revisao


def _decodificar(conteudo,nome):
    try:
        e=json.loads(conteudo)
        if not isinstance(e,dict) or set(e)!={'schema','event_id','anterior','alvo','referencia','acao','observacao','recurso','versao','usuario','data','revisao'}:
            raise ValueError('Campos de conferência inválidos.')
        if e['schema']!=SCHEMA or str(uuid.UUID(e['event_id']))+'.json'!=nome:raise ValueError('Evento inválido.')
        if e['anterior'] is not None and str(uuid.UUID(e['anterior']))!=e['anterior']:raise ValueError('Anterior inválido.')
        alvo(e['alvo'])
        if not isinstance(e['referencia'],dict) or e['referencia'].get('id')!=e['alvo']['evidencia_id'] or e['referencia'].get('caso')!=e['alvo']['caso']:
            raise ValueError('Referência divergente.')
        if type(e['versao']) is not int or e['versao']<1:raise ValueError('Versão inválida.')
        r=e['revisao']
        if (not isinstance(r,dict) or set(r)!=set(padrao(e['alvo'])) or type(r['versao']) is not int
                or any(type(r[k]) is not bool for k in ('fonte_conferida','candidato'))):
            raise ValueError('Estado de revisão inválido.')
        if VM._texto(e['usuario'],'usuário',True)!=e['usuario']:raise ValueError('Usuário inválido.')
        if not isinstance(e['data'],str) or datetime.fromisoformat(e['data']).tzinfo is None:raise ValueError('Data inválida.')
        _serial(e)
        return e
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeError) as erro:
        raise Integridade('Histórico de conferências inválido: '+str(nome)) from erro


def _ler(eventos):
    pasta=_pasta(eventos);resultado=[]
    for p in sorted(pasta.glob('*.json')):
        if p.is_symlink():raise ValueError('Conferência não pode ser um atalho.')
        resultado.append(_decodificar(p.read_bytes(),p.name))
    return resultado


def _estados(eventos):
    estados={}
    for e in sorted(eventos,key=lambda x:(x['versao'],x['event_id'])):
        id_=padrao(e['alvo'])['id'];anterior=estados.get(id_)
        if e['anterior']!=(anterior['event_id'] if anterior else None):raise Integridade('Histórico de conferências divergente.')
        previo=anterior['revisao'] if anterior else padrao(e['alvo'])
        if e['versao']!=previo['versao']+1:raise Integridade('Versões de conferência divergentes.')
        if anterior and (e['alvo']!=anterior['alvo'] or e['referencia']!=anterior['referencia']):
            raise Integridade('Fonte histórica divergente; revisões preservadas.')
        try:esperado=_proximo(previo,e['acao'],e['observacao'],e['recurso'],e['usuario'],e['data'])
        except ValueError as erro:raise Integridade('Ação histórica inválida.') from erro
        if e['revisao']!=esperado:raise Integridade('Estado de conferência divergente.')
        estados[id_]=e
    return estados


def listar(ws):
    eventos=VM._pasta(ws)
    if not _pasta(eventos).exists():return {}
    with VM.trava(ws) as pasta:
        return {id_:copy.deepcopy(e['revisao']) for id_,e in _estados(_ler(pasta)).items()}


def historico(ws,dados):
    dados=alvo(dados);id_=padrao(dados)['id'];eventos=VM._pasta(ws)
    if not _pasta(eventos).exists():return []
    with VM.trava(ws) as pasta:
        eventos=_ler(pasta);_estados(eventos)
        return copy.deepcopy(sorted((e for e in eventos if padrao(e['alvo'])['id']==id_),key=lambda e:e['versao']))


def revisar(ws,dados,resolver,acao,usuario,versao,observacao='',recurso=None):
    """Resolver executa sob a trava comum e deve consultar a referência atual sem adquirir outra trava."""
    dados=alvo(dados);usuario=VM._texto(usuario,'usuário',True)
    if type(versao) is not int or versao<0:raise ValueError('Versão de revisão inválida.')
    # Valida a ação antes de criar diretórios ou chamar o resolvedor.
    _proximo(padrao(dados),acao,observacao,recurso,usuario,VM._agora())
    with VM.trava(ws) as pasta:
        estados=_estados(_ler(pasta));id_=padrao(dados)['id'];anterior=estados.get(id_)
        previo=anterior['revisao'] if anterior else padrao(dados)
        if versao!=previo['versao']:raise Conflito('Revisão alterada; reabra a evidência.')
        try:referencia=resolver(pasta)
        except KeyError:
            if anterior:raise Conflito('Referência alterada ou removida; consulte a fonte atual.')
            raise
        snapshot=_snapshot(referencia)
        if snapshot.get('id')!=dados['evidencia_id'] or snapshot.get('caso')!=dados['caso']:raise Conflito('Fonte alterada.')
        if anterior and snapshot!=anterior['referencia']:raise Conflito('Conteúdo de fonte alterado; confira a referência atual.')
        if acao=='conferir_fonte' and not referencia.get(recurso+'_disponivel'):raise Conflito('Recurso da fonte indisponível para conferência.')
        data=VM._agora();revisao=_proximo(previo,acao,observacao,recurso,usuario,data)
        evento={'schema':SCHEMA,'event_id':str(uuid.uuid4()),'anterior':anterior['event_id'] if anterior else None,
                'alvo':dados,'referencia':snapshot,'acao':acao,'observacao':observacao,'recurso':recurso,
                'versao':revisao['versao'],'usuario':usuario,'data':data,'revisao':revisao}
        destino=_pasta(pasta);destino.mkdir(exist_ok=True)
        VM._publicar(destino/(evento['event_id']+'.json'),(_serial(evento)+'\n').encode('utf-8'))
        return copy.deepcopy(revisao)


def _importados(pasta,arquivos):
    atuais=_ler(pasta);ids={e['event_id'] for e in atuais};novos=[];destino=_pasta(pasta)
    for nome,conteudo in arquivos.items():
        if not isinstance(nome,str) or Path(nome).name!=nome or not isinstance(conteudo,bytes):raise ValueError('Arquivo de conferência inválido.')
        e=_decodificar(conteudo,nome)
        if e['event_id'] in ids:
            if (destino/nome).read_bytes()!=conteudo:raise Conflito('Conferência com mesmo ID e conteúdo divergente.')
        else:novos.append((e,nome,conteudo))
    _estados(atuais+[e for e,_,_ in novos])
    return sorted(novos,key=lambda item:(item[0]['versao'],item[0]['event_id']))


def exportar(ws):
    pasta=VM._pasta(ws)
    if not _pasta(pasta).exists():return {}
    with VM.trava(ws) as pasta:
        eventos=_ler(pasta);_estados(eventos)
        return {e['event_id']+'.json':(_pasta(pasta)/(e['event_id']+'.json')).read_bytes() for e in eventos}
