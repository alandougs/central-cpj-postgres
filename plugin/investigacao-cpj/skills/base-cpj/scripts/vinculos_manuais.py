"""Fonte local dos vínculos manuais; o SQLite é apenas uma projeção regenerável.

Eventos são imutáveis e entram nos pacotes/backup de consulta. Cada operação
serializa escritores entre processos; nenhum acesso ao índice é necessário.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
import unicodedata
import uuid

SCHEMA = 'astra-manual-evento/1'
PASTA = '_grafo-manual'
TIPOS = ('PESSOA', 'NOME', 'CPF', 'RG', 'TELEFONE', 'PLACA', 'CNPJ', 'EMPRESA',
         'EMAIL', 'ENDERECO', 'PROCESSO', 'BO', 'CONTA', 'CHAVE_PIX', 'CASO')
_travas = {}
_guard = threading.Lock()


class Conflito(ValueError):
    """Duplicata, revisão desatualizada ou histórico divergente."""


def _agora():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def _pasta(ws):
    raiz = Path(ws).resolve()
    atual = raiz
    for parte in ('consulta', PASTA, 'eventos'):
        atual = atual / parte
        if atual.is_symlink() or (hasattr(atual, 'is_junction') and atual.is_junction()):
            raise ValueError('Pasta dos vínculos não pode ser um atalho.')
    return atual


@contextmanager
def trava(ws):
    pasta = _pasta(ws)
    pasta.mkdir(parents=True, exist_ok=True)
    chave = str(pasta)
    with _guard:
        local = _travas.setdefault(chave, threading.RLock())
    with local:
        with open(pasta.parent / '.vinculos.lock', 'a+b') as arq:
            arq.seek(0, os.SEEK_END)
            if not arq.tell():
                arq.write(b'\0'); arq.flush()
            fim = time.monotonic() + 30
            while True:
                try:
                    arq.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(arq.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(arq.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (OSError, BlockingIOError):
                    if time.monotonic() >= fim:
                        raise TimeoutError('Fonte dos vínculos ocupada. Tente novamente.')
                    time.sleep(.02)
            try:
                yield pasta
            finally:
                arq.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(arq.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(arq.fileno(), fcntl.LOCK_UN)


def _texto(valor, nome, obrigatorio=False):
    if not isinstance(valor, str) or len(valor) > 4000:
        raise ValueError(f'Campo {nome} inválido ou muito longo.')
    valor = valor.strip()
    if obrigatorio and not valor:
        raise ValueError(f'Informe {nome}.')
    return valor


def _chave(tipo, valor):
    if tipo in ('CPF', 'CNPJ', 'TELEFONE', 'RG'):
        return re.sub(r'\D', '', valor)
    if tipo == 'PLACA':
        return re.sub(r'[^A-Z0-9]', '', valor.upper())
    if tipo in ('CASO', 'PESSOA'):
        return valor
    if tipo in ('PROCESSO', 'BO'):
        m = re.search(r'\d[\d./-]{4,}\d', valor)
        return re.sub(r'\D', '', m.group(0)) if m else ''
    if tipo == 'CONTA':
        return valor if '|' in valor else re.sub(r'\D', '', valor)
    if tipo in ('EMAIL', 'CHAVE_PIX'):
        if tipo == 'EMAIL' or '@' in valor:
            return valor.lower()
        return re.sub(r'\D', '', valor) if re.fullmatch(r'[\d.\-/() +]+', valor) else re.sub(r'\s+', '', valor.lower())
    valor = unicodedata.normalize('NFKD', valor).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9@/ -]+', ' ', valor).replace('-', ' ').strip()


def _dados(dados):
    if not isinstance(dados, dict):
        raise ValueError('Informe os campos do vínculo.')
    resultado = {'caso': _texto(dados.get('caso', ''), 'caso', True),
                 'relacao': _texto(dados.get('relacao', ''), 'relação', True)}
    for lado in ('a', 'b'):
        tipo = _texto(dados.get(lado+'_tipo', ''), 'tipo', True).upper()
        valor = _texto(dados.get(lado+'_valor', ''), 'valor', True)
        if tipo not in TIPOS or (tipo == 'PESSOA' and not valor.startswith('P:')):
            raise ValueError('Tipo inválido ou Pessoa sem identificador de registro.')
        valor = _chave(tipo, valor)
        if not valor:
            raise ValueError('Identificador vazio após normalização.')
        resultado.update({lado+'_tipo': tipo, lado+'_valor': valor,
                          lado+'_rotulo': _texto(dados.get(lado+'_rotulo', ''), 'rótulo')})
    evidencia = dados.get('evidencia', {})
    if not isinstance(evidencia, dict):
        raise ValueError('Evidência inválida.')
    pagina = evidencia.get('pagina')
    if pagina is not None and (type(pagina) is not int or pagina < 1):
        raise ValueError('Página deve ser um inteiro positivo.')
    resultado['evidencia'] = {k: _texto(evidencia.get(k, ''), k) for k in ('documento', 'fls', 'observacao')}
    resultado['evidencia']['pagina'] = pagina
    return resultado


def _decodificar(conteudo, nome):
    try:
        evento = json.loads(conteudo)
        if not isinstance(evento, dict) or evento.get('schema') != SCHEMA:
            raise ValueError('Versão de evento inválida.')
        if str(uuid.UUID(evento['event_id'])) + '.json' != nome:
            raise ValueError('Identidade de evento inválida.')
        if str(uuid.UUID(evento['vinculo_id'])) != evento['vinculo_id']:
            raise ValueError('Identidade do vínculo inválida.')
        versao, registro = evento['versao'], evento['registro']
        if type(versao) is not int or versao < 1 or not isinstance(registro, dict):
            raise ValueError('Revisão inválida.')
        if registro['id'] != evento['vinculo_id'] or type(registro['versao']) is not int or registro['versao'] != versao:
            raise ValueError('Registro diverge do evento.')
        if type(registro['excluido']) is not bool or registro['status'] not in ('hipotese', 'conferido'):
            raise ValueError('Estado inválido.')
        if evento['acao'] not in ('criar', 'migrar', 'atualizar', 'excluir'):
            raise ValueError('Operação inválida.')
        if registro['excluido'] != (evento['acao'] == 'excluir'):
            raise ValueError('Exclusão divergente.')
        if 'legado' not in registro:
            _dados(registro)
        elif (not isinstance(registro['legado'], dict) or not isinstance(registro['evidencia'], dict)
              or any(not isinstance(registro[k], str) for k in
                     ('caso','relacao','a_tipo','a_valor','b_tipo','b_valor','a_rotulo','b_rotulo'))):
            raise ValueError('Snapshot legado inválido.')
        if any(k not in registro for k in ('criado_em','usuario')):
            raise ValueError('Metadados de origem ausentes.')
        return evento
    except (ValueError, KeyError, TypeError, UnicodeError, AttributeError) as e:
        raise ValueError(f'Histórico de vínculos inválido: {nome}') from e


def _ler(pasta):
    eventos = []
    for p in sorted(pasta.glob('*.json')):
        if p.is_symlink():
            raise ValueError('Evento não pode ser um atalho.')
        eventos.append(_decodificar(p.read_bytes(), p.name))
    return eventos


def _estados(eventos):
    atuais = {}
    for evento in sorted(eventos, key=lambda e: (e['versao'], e['event_id'])):
        id_ = evento['vinculo_id']
        anterior = atuais.get(id_)
        if evento['versao'] != (anterior['versao'] + 1 if anterior else 1) or evento.get('anterior') != (anterior['event_id'] if anterior else None):
            raise Conflito('Histórico divergente; nenhum evento foi descartado.')
        if (not anterior and evento['acao'] not in ('criar','migrar')) or (anterior and
                (evento['acao'] not in ('atualizar','excluir') or anterior['registro']['excluido'])):
            raise Conflito('Sequência de operações divergente.')
        if anterior and any(evento['registro'].get(k) != anterior['registro'].get(k)
                            for k in ('criado_em','usuario','legado')):
            raise Conflito('Metadados de origem divergentes; histórico preservado.')
        atuais[id_] = evento
    return atuais


def _gravar(pasta, evento):
    destino = pasta / (evento['event_id'] + '.json')
    conteudo = (json.dumps(evento, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    _publicar(destino, conteudo)


def _publicar(destino, conteudo):
    if destino.exists():
        if destino.read_bytes() != conteudo:
            raise Conflito('Evento com mesmo ID e conteúdo divergente.')
        return
    tmp = destino.parent / ('.' + uuid.uuid4().hex + '.tmp')
    try:
        with open(tmp, 'xb') as f:
            f.write(conteudo); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, destino)
    finally:
        if tmp.exists():
            tmp.unlink()


def _importados(pasta, arquivos):
    atuais = _ler(pasta)
    ids = {e['event_id'] for e in atuais}
    novos = []
    for nome, conteudo in arquivos.items():
        if not isinstance(nome, str) or Path(nome).name != nome or not isinstance(conteudo, bytes):
            raise ValueError('Arquivo de evento inválido.')
        evento = _decodificar(conteudo, nome)
        if evento['event_id'] in ids:
            if (pasta / nome).read_bytes() != conteudo:
                raise Conflito('Evento com mesmo ID e conteúdo divergente.')
        else:
            novos.append((evento, nome, conteudo))
    _estados(atuais + [e for e, _, _ in novos])
    return sorted(novos, key=lambda item: (item[0]['versao'], item[0]['event_id']))


def _pasta_legados(pasta):
    legados = pasta.parent / 'legados'
    if legados.is_symlink() or (hasattr(legados,'is_junction') and legados.is_junction()):
        raise ValueError('Legados não podem ser um atalho.')
    return legados


def _ler_legado(conteudo, nome):
    try:
        registro = json.loads(conteudo)
        if (registro['schema'] != 'astra-manual-legado/1' or registro['proveniencia'] != 'desconhecida'
                or registro['origem'] != 'rag/cpj.sqlite' or not registro['capturado_em']):
            raise ValueError('Metadados legados inválidos.')
        dados = registro['conteudo']
        if not isinstance(dados,dict) or not isinstance(dados['rotulos'],list) or not isinstance(dados['arestas_manuais'],list):
            raise ValueError('Snapshot legado inválido.')
        serial = json.dumps(dados,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
        digest = hashlib.sha256(serial).hexdigest()
        if registro['sha256'] != digest or nome != digest+'.json':
            raise ValueError('Hash legado divergente.')
        return registro
    except (KeyError,TypeError,ValueError,UnicodeError) as e:
        raise ValueError(f'Snapshot legado inválido: {nome}') from e


def _validar_legados(pasta, arquivos):
    legados = _pasta_legados(pasta)
    for nome, conteudo in arquivos.items():
        if not isinstance(nome,str) or Path(nome).name != nome or not isinstance(conteudo,bytes):
            raise ValueError('Arquivo legado inválido.')
        _ler_legado(conteudo,nome)
        destino = legados/nome
        if destino.is_symlink():
            raise ValueError('Snapshot legado não pode ser atalho.')
        if destino.exists() and destino.read_bytes() != conteudo:
            raise Conflito('Snapshot legado com mesmo ID e conteúdo divergente.')


def validar_importacao(ws, arquivos, legados=None):
    """Valida a união antes de confirmar qualquer arquivo operacional do pacote."""
    if not arquivos and not legados:
        return
    with trava(ws) as pasta:
        _importados(pasta, arquivos)
        _validar_legados(pasta, legados or {})


def importar_eventos(ws, arquivos, legados=None):
    """Acrescenta eventos completos; retomada/reimportação não sobrescreve IDs."""
    if not arquivos and not legados:
        return 0
    with trava(ws) as pasta:
        novos = _importados(pasta, arquivos)
        _validar_legados(pasta, legados or {})
        if legados:
            destino = _pasta_legados(pasta); destino.mkdir(exist_ok=True)
            for nome, conteudo in legados.items():
                _publicar(destino/nome,conteudo)
        for _, nome, conteudo in novos:
            _publicar(pasta / nome, conteudo)
        return len(novos)


def exportar_eventos(ws):
    """Snapshot imutável; o ZIP pode ler documentos grandes após soltar o lock."""
    if not _pasta(ws).exists():
        return {}
    with trava(ws) as pasta:
        eventos = _ler(pasta)
        _estados(eventos)
        return {e['event_id']+'.json': (pasta/(e['event_id']+'.json')).read_bytes() for e in eventos}


def exportar_legados(ws):
    if not _pasta_legados(_pasta(ws)).exists():
        return {}
    with trava(ws) as pasta:
        legados = _pasta_legados(pasta)
        arquivos = {p.name:p.read_bytes() for p in legados.glob('*.json')}
        _validar_legados(pasta,arquivos)
        return arquivos


def _preservar_legado(pasta, linhas, rotulos, campos):
    conteudo = {'arestas_manuais':[dict(zip(campos,r)) for r in linhas],
                'rotulos':[{'tipo':t,'valor':v,'rotulo':r} for (t,v),r in
                           sorted(rotulos.items(),key=lambda item:json.dumps(item[0],ensure_ascii=False))]}
    serial = json.dumps(conteudo,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    digest = hashlib.sha256(serial).hexdigest()
    destino = _pasta_legados(pasta); destino.mkdir(exist_ok=True)
    arquivo = destino/(digest+'.json')
    if arquivo.exists():
        _ler_legado(arquivo.read_bytes(),arquivo.name)
        return
    snapshot = {'schema':'astra-manual-legado/1','sha256':digest,'capturado_em':_agora(),
                'origem':'rag/cpj.sqlite','proveniencia':'desconhecida','conteudo':conteudo}
    _publicar(arquivo,(json.dumps(snapshot,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))


def _evento(registro, acao, usuario, anterior=None, event_id=None):
    return {'schema': SCHEMA, 'event_id': event_id or str(uuid.uuid4()),
            'vinculo_id': registro['id'], 'versao': registro['versao'],
            'acao': acao, 'anterior': anterior, 'usuario': usuario,
            'registrado_em': _agora(), 'registro': registro}


def _duplicado(registro, estados, ignorar=None):
    campos = ('caso', 'relacao', 'a_tipo', 'a_valor', 'b_tipo', 'b_valor', 'evidencia')
    for id_, evento in estados.items():
        outro = evento['registro']
        if id_ != ignorar and not outro['excluido'] and all(outro.get(k) == registro.get(k) for k in campos):
            raise Conflito('Este vínculo com esta fonte já foi registrado.')


def criar(ws, dados, usuario):
    usuario = _texto(usuario, 'usuário', True)
    registro = _dados(dados)
    registro.update(id=str(uuid.uuid4()), versao=1, status='hipotese', excluido=False,
                    criado_em=_agora(), usuario=usuario)
    with trava(ws) as pasta:
        _duplicado(registro, _estados(_ler(pasta)))
        _gravar(pasta, _evento(registro, 'criar', usuario))
    return copy.deepcopy(registro)


def listar(ws, incluir_excluidos=False):
    if not _pasta(ws).exists():
        return []
    with trava(ws) as pasta:
        estados = _estados(_ler(pasta))
        return [copy.deepcopy(e['registro']) for _, e in sorted(estados.items())
                if incluir_excluidos or not e['registro']['excluido']]


def _atual(ws, id_, estados, versao):
    if id_ not in estados:
        raise KeyError(id_)
    anterior = estados[id_]
    if versao is not None and (type(versao) is not int or versao != anterior['versao']):
        raise Conflito('Versão desatualizada. Reabra o vínculo antes de alterar.')
    if anterior['registro']['excluido']:
        raise Conflito('Vínculo excluído; seu histórico foi preservado.')
    return anterior, copy.deepcopy(anterior['registro'])


def atualizar(ws, id_, dados, usuario, versao):
    usuario = _texto(usuario, 'usuário', True)
    if type(versao) is not int or not isinstance(dados, dict):
        raise ValueError('Informe a versão e os campos a atualizar.')
    permitidos = {'caso', 'relacao', 'a_tipo', 'a_valor', 'b_tipo', 'b_valor',
                  'a_rotulo', 'b_rotulo', 'evidencia', 'status'}
    if set(dados) - permitidos:
        raise ValueError('Campo de identidade ou histórico não pode ser alterado.')
    with trava(ws) as pasta:
        estados = _estados(_ler(pasta))
        anterior, registro = _atual(ws, id_, estados, versao)
        combinado = dict(registro, **dados)
        if 'evidencia' in dados:
            if not isinstance(dados['evidencia'], dict):
                raise ValueError('Evidência inválida.')
            combinado['evidencia'] = dict(registro['evidencia'], **dados['evidencia'])
        registro.update(_dados(combinado))
        status = combinado.get('status', 'hipotese')
        if status not in ('hipotese', 'conferido'):
            raise ValueError('Conferência não transforma uma hipótese manual em fato documentado.')
        registro.update(status=status, versao=versao+1, atualizado_em=_agora(), atualizado_por=usuario)
        if dados.get('status') == 'conferido':
            registro.update(revisado_por=usuario, revisado_em=_agora())
        _duplicado(registro, estados, ignorar=id_)
        _gravar(pasta, _evento(registro, 'atualizar', usuario, anterior['event_id']))
        return copy.deepcopy(registro)


def excluir(ws, id_, usuario, versao=None):
    usuario = _texto(usuario, 'usuário', True)
    with trava(ws) as pasta:
        estados = _estados(_ler(pasta))
        anterior, registro = _atual(ws, id_, estados, versao)
        registro.update(excluido=True, versao=registro['versao']+1,
                        excluido_em=_agora(), excluido_por=usuario)
        _gravar(pasta, _evento(registro, 'excluir', usuario, anterior['event_id']))
        return copy.deepcopy(registro)


def historico(ws, id_):
    if not _pasta(ws).exists():
        raise KeyError(id_)
    with trava(ws) as pasta:
        eventos = _ler(pasta)
        if id_ not in _estados(eventos):
            raise KeyError(id_)
        return [copy.deepcopy(e) for e in sorted(eventos, key=lambda e: e['versao']) if e['vinculo_id'] == id_]


def migrar_legados(ws, db):
    """Captura antes de apagar o índice; requer BEGIN IMMEDIATE do chamador.

    O ordinal conserva duplicatas antigas. IDs derivados da linha original tornam
    a retomada idempotente, mesmo se a projeção falhar depois da captura.
    """
    if not db.in_transaction:
        raise ValueError('Migração requer transação do chamador.')
    campos = ('a_tipo', 'a_valor', 'b_tipo', 'b_valor', 'relacao', 'origem', 'fonte', 'localizador')
    linhas = []
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='arestas'").fetchone():
        linhas = db.execute("SELECT a_tipo,a_valor,b_tipo,b_valor,relacao,origem,fonte,localizador FROM arestas WHERE origem='manual' ORDER BY rowid").fetchall()
    rotulos = {}
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='rotulos'").fetchone():
        rotulos = {(t, v): r for t, v, r in db.execute('SELECT tipo,valor,rotulo FROM rotulos')}
    with trava(ws) as pasta:
        estados = _estados(_ler(pasta))
        if linhas or rotulos:
            _preservar_legado(pasta,linhas,rotulos,campos)
        repetidos, novos = {}, 0
        for linha in linhas:
            original = dict(zip(campos, linha))
            try:
                loc = json.loads(original['localizador'] or '')
            except (ValueError, TypeError):
                loc = {}
            if not isinstance(loc, dict) or loc.get('schema') != 'astra-manual/1':
                loc = {}
            # Uma projeção identificada nunca ressuscita registro excluído.
            if loc.get('id') in estados:
                continue
            serial = json.dumps(original, ensure_ascii=False, sort_keys=True)
            digest = hashlib.sha256(serial.encode('utf-8')).hexdigest()
            ordinal = repetidos.get(digest, 0)
            repetidos[digest] = ordinal + 1
            id_ = str(uuid.uuid5(uuid.NAMESPACE_URL, 'astra-legado:'+digest+':'+str(ordinal)))
            if loc.get('id'):
                try:
                    id_ = str(uuid.UUID(str(loc['id'])))
                except (ValueError, TypeError, AttributeError):
                    pass
            if id_ in estados:
                continue
            evidencia = loc.get('evidencia')
            if not isinstance(evidencia, dict):
                evidencia = {'documento':'', 'pagina':None, 'fls':'',
                             'observacao':original['localizador'] or ''}
            registro = {'id':id_, 'versao':1, 'caso':original['fonte'] or '',
                        'relacao':original['relacao'] or '', 'evidencia':copy.deepcopy(evidencia),
                        'status':'hipotese', 'excluido':False, 'criado_em':None, 'usuario':None,
                        'legado':original}
            for lado in ('a', 'b'):
                tipo = original[lado+'_tipo'] or ''
                valor = original[lado+'_valor'] or ''
                registro[lado+'_tipo'] = tipo
                registro[lado+'_valor'] = _chave(tipo, valor) if tipo in TIPOS else valor
                registro[lado+'_rotulo'] = rotulos.get((tipo, valor), '') or ''
            event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, 'astra-legado-evento:'+id_))
            evento = _evento(registro, 'migrar', None, event_id=event_id)
            _gravar(pasta, evento)
            estados[id_] = evento
            novos += 1
        return novos


def projetar(ws, db):
    """Substitui somente manuais/rótulos sobrepostos, sem BEGIN nem commit.

    A tabela auxiliar registra o rótulo documental coberto pela anotação. O
    indexador a descarta ao reconstruir os rótulos documentais integralmente.
    """
    if not db.in_transaction:
        raise ValueError('Projeção requer transação do chamador.')
    with trava(ws) as pasta:
        registros = [e['registro'] for e in _estados(_ler(pasta)).values() if not e['registro']['excluido']]
        db.execute('CREATE TABLE IF NOT EXISTS grafo_rotulos_manuais(tipo TEXT,valor TEXT,anterior TEXT,rotulo TEXT,PRIMARY KEY(tipo,valor))')
        for tipo, valor, anterior, manual in db.execute('SELECT tipo,valor,anterior,rotulo FROM grafo_rotulos_manuais').fetchall():
            atual = db.execute('SELECT rotulo FROM rotulos WHERE tipo=? AND valor=?',(tipo,valor)).fetchone()
            if atual and atual[0] == manual:
                if anterior is None:
                    db.execute('DELETE FROM rotulos WHERE tipo=? AND valor=?',(tipo,valor))
                else:
                    db.execute('UPDATE rotulos SET rotulo=? WHERE tipo=? AND valor=?',(anterior,tipo,valor))
        db.execute('DELETE FROM grafo_rotulos_manuais')
        db.execute("DELETE FROM arestas WHERE origem='manual'")
        for r in sorted(registros, key=lambda r: (r.get('atualizado_em') or r.get('criado_em') or '', r['id'])):
            localizador = json.dumps({'schema':'astra-manual/1','id':r['id'],'versao':r['versao'],
                                      'evidencia':r['evidencia']},ensure_ascii=False,sort_keys=True)
            db.execute('INSERT INTO arestas(a_tipo,a_valor,b_tipo,b_valor,relacao,origem,fonte,localizador) VALUES(?,?,?,?,?,?,?,?)',
                       (r['a_tipo'],r['a_valor'],r['b_tipo'],r['b_valor'],r['relacao'],'manual',r['caso'],localizador))
            for lado in ('a', 'b'):
                tipo, valor, rotulo = r[lado+'_tipo'], r[lado+'_valor'], r.get(lado+'_rotulo')
                if not rotulo:
                    continue
                atual = db.execute('SELECT rotulo FROM rotulos WHERE tipo=? AND valor=?',(tipo,valor)).fetchone()
                db.execute('INSERT INTO grafo_rotulos_manuais VALUES(?,?,?,?) ON CONFLICT(tipo,valor) DO UPDATE SET rotulo=excluded.rotulo',
                           (tipo,valor,atual[0] if atual else None,rotulo))
                db.execute('INSERT OR REPLACE INTO rotulos(tipo,valor,rotulo) VALUES(?,?,?)',(tipo,valor,rotulo))
        return len(registros)
