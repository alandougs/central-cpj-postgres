"""Checkpoint essencial por documento; leitura compatível com extrações antigas."""
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time


def _sem_reparse(p):
    p = Path(os.path.abspath(p))
    for parte in (*reversed(p.parents), p):
        try:
            info = parte.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024):
            raise ValueError('Checkpoint contém link ou junção.')


def arquivo(pasta):
    p = Path(pasta) / '.checkpoint' / 'estado.json'
    _sem_reparse(p)
    if not p.resolve().is_relative_to(Path(pasta).resolve()):
        raise ValueError('Checkpoint fora da pasta de extração.')
    return p


def _valor(dados, nome):
    chave = {'relatorio_extracao.json': 'relatorio', 'qualidade.json': 'qualidade', '.checkpoint/meta.json': 'meta'}.get(nome)
    if chave:
        return dados.get(chave, {})
    pagina = re.fullmatch(r'\.checkpoint/p(\d+)\.json', nome)
    if pagina:
        return dados.get('paginas', {}).get(str(int(pagina[1])), {})
    raise KeyError(nome)


def ler(pasta, nome):
    estado = arquivo(pasta)
    if estado.exists():
        dados = json.loads(estado.read_text(encoding='utf-8'))
        try:
            return _valor(dados, nome)
        except KeyError:
            pass
    p = Path(pasta) / nome
    _sem_reparse(p)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def gravar(pasta, dados):
    p = arquivo(pasta)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=p.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False)
        # No Windows, antivírus, indexação ou um leitor do progresso podem segurar
        # estado.json por instantes (WinError 5/32); a troca é repetida antes de falhar.
        for tentativa in range(8):
            try:
                os.replace(temp, p)
                break
            except PermissionError:
                if tentativa == 7:
                    raise
                time.sleep(0.05 * 2 ** tentativa)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atualizar(pasta, chave, valor):
    p = arquivo(pasta)
    dados = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    dados[chave] = valor
    gravar(pasta, dados)


def compactar_legado(pasta):
    """Consolida sem apagar; só retorna caminhos com conteúdo equivalente verificado.

    Um estado já existente tem precedência sobre arquivos antigos divergentes.
    A seleção/exclusão e o backup pertencem ao chamador, fora desta função.
    """
    pasta = Path(pasta)
    nomes = ['.checkpoint/meta.json', 'relatorio_extracao.json', 'qualidade.json']
    legados = {}
    try:
        arquivo(pasta)  # Recusar também junções internas antes de ler ou gravar.
        nomes += [p.relative_to(pasta).as_posix() for p in sorted((pasta / '.checkpoint').glob('p*.json'))
                  if re.fullmatch(r'p\d{4,}\.json', p.name)]
        for nome in nomes:
            p = pasta / nome
            _sem_reparse(p)
            if p.exists():
                if p.is_symlink() or not p.resolve().is_relative_to(pasta.resolve()):
                    raise ValueError('Checkpoint fora da pasta de extração.')
                legados[nome] = json.loads(p.read_text(encoding='utf-8-sig'))
        if not arquivo(pasta).exists():
            meta = legados.get('.checkpoint/meta.json', {})
            rel = legados.get('relatorio_extracao.json', {})
            n = rel.get('paginas')
            if meta.get('versao') != 2 or not re.fullmatch('[a-fA-F0-9]{64}', meta.get('sha256', '')) or meta.get('sha256') != rel.get('sha256_original'):
                raise ValueError('Metadados de integridade ausentes ou divergentes.')
            if type(n) is not int or n < 1:
                raise ValueError('Quantidade de páginas inválida.')
            paginas = {}
            for i in range(1, n + 1):
                pagina = legados.get(f'.checkpoint/p{i:04d}.json', {})
                reg = pagina.get('reg', {})
                if reg.get('pagina') != i or not isinstance(reg.get('texto'), str):
                    raise ValueError('Checkpoint de página ausente ou inválido.')
                paginas[str(i)] = pagina
            gravar(pasta, {'meta': meta, 'relatorio': rel, 'qualidade': legados.get('qualidade.json', {}), 'paginas': paginas})
        consolidado = json.loads(arquivo(pasta).read_text(encoding='utf-8'))
        cobertos = [nome for nome, valor in legados.items() if _valor(consolidado, nome) == valor]
        return {'compactado': True, 'cobertos': cobertos}
    except (OSError, ValueError, TypeError, AttributeError) as erro:
        return {'compactado': False, 'cobertos': [], 'motivo': str(erro)}
