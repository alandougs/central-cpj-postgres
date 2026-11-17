"""Separa páginas de O.S. da transcrição local, sem resumir ou presumir a ordem vigente."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata


def normalizar(texto):
    return ' '.join(unicodedata.normalize('NFKD', texto).encode('ascii','ignore').decode().upper().split())


def cabecalho_os(texto):
    texto=re.sub(r'(?im)^\s*ORDEM\s+DE\s+SERVI[ÇC]O(?=\s|$)','ORDEM DE SERVIÇO',texto)
    for linha in texto.splitlines():
        s=normalizar(linha.lstrip('#* '))
        m=re.match(r'^(?:ORDEM DE SERVICO|O\s*\.\s*S\s*\.)(?:\s|$|[:\-])',s)
        if m:
            resto=s[m.end():].strip(' :-')
            if not resto or re.match(r'^(?:(?:NUMERO|N[O.]?\.?)\s*[:\-]?\s*)?\d',resto):
                return True
    return False


def continuacao(texto):
    linhas=[normalizar(l) for l in texto.splitlines() if l.strip() and not l.strip().startswith('<!--')]
    inicio='\n'.join(linhas[:18])
    if re.search(r'(?m)^(?:DESPACHO|CERTIDAO|TERMO DE |RELATORIO DE |OFICIO|CONCLUSAO|AUTO DE )',inicio):
        return False
    return bool(re.search(r'(?mi)^\s*(?:continua[cç][aã]o|[a-z]\)|[1-9]\d*\.)',texto))


def gravar(caminho, texto):
    if caminho.exists() and caminho.read_text(encoding='utf-8')==texto:
        return
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=caminho.parent,delete=False,suffix='.tmp') as f:
        temp=Path(f.name)
        f.write(texto)
    try:
        os.replace(temp,caminho)
    finally:
        if temp.exists(): temp.unlink()


def extrair_ordens(pasta):
    pasta=Path(pasta)
    fonte=pasta/'transcricao.md'
    if not fonte.is_file():
        return {'situacao':'transcricao_ausente','ordens':[],'vigente':None}
    diretorio=pasta/'ordens-de-servico'
    if not diretorio.resolve().is_relative_to(pasta.resolve()):
        raise ValueError('Pasta de O.S. fora da extração do documento.')
    diretorio.mkdir(exist_ok=True)
    dados=fonte.read_bytes()
    texto=dados.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')
    sha=hashlib.sha256(dados).hexdigest()
    marcas=list(re.finditer(r'(?m)^##\s+P[áa]gina\s+(\d+)\s*\r?$',texto))
    paginas=[(int(m.group(1)),texto[m.end():marcas[i+1].start() if i+1<len(marcas) else len(texto)].strip()) for i,m in enumerate(marcas)]
    if not marcas: paginas=[(None,texto)]
    ordens=[]
    # A busca começa no fim; a vigência será conferida pela data/documento, não pela posição.
    for i in reversed(range(len(paginas))):
        if not cabecalho_os(paginas[i][1]): continue
        selecionadas=[paginas[i]]
        j=i+1
        while j<len(paginas) and not cabecalho_os(paginas[j][1]) and continuacao(paginas[j][1]):
            selecionadas.append(paginas[j]); j+=1
        nums=[p[0] for p in selecionadas]
        chave=f'pag-{nums[0]:04d}' if nums[0] is not None else 'sem-pagina'
        arquivo=f'ordens-de-servico/os-{chave}-{sha[:12]}.md'
        corpo=(f'# Ordem de Serviço — transcrição\n\nFonte: `../transcricao.md`\n\n'
               f'SHA-256 da transcrição: `{sha}`\n\n')
        for numero,conteudo in selecionadas:
            corpo+=f'## Página {numero if numero is not None else "não informada"}\n\n{conteudo}\n\n'
        gravar(pasta/arquivo,corpo)
        ordens.append({'paginas':nums,'arquivo':arquivo,'conferir_integralidade':True})
    info={'schema':'cpj-ordens-extraidas/1','fonte':'transcricao.md','sha256_transcricao':sha,
          'situacao':'localizada' if ordens else 'nao_localizada','ordens':ordens,'vigente':None,
          'criterio':'Candidatas das páginas finais primeiro; conferir datas, integralidade e vigência nos autos.'}
    indice = f"# Índice das Ordens de Serviço\n\nFonte: `../transcricao.md`\n\nSHA-256: `{sha}`\n\nSituação: {info['situacao']}\n\n{info['criterio']}\n\n"
    for ordem in ordens:
        indice += f"- [{Path(ordem['arquivo']).name}]({Path(ordem['arquivo']).name}) — páginas {', '.join(str(n) for n in ordem['paginas'])}; conferir integralidade.\n"
    gravar(diretorio/'indice.md', indice)
    return info


def contexto_caso(base):
    base=Path(base)
    extr=base/'01-extracao'
    arquivos=[]
    if extr.is_dir():
        for pasta in sorted(extr.iterdir()):
            if not pasta.is_dir() or pasta.is_symlink() or not pasta.resolve().is_relative_to(extr.resolve()): continue
            fonte=pasta/'transcricao.md'
            if fonte.is_symlink() or (fonte.exists() and not fonte.resolve().is_relative_to(pasta.resolve())): continue
            for ordem in extrair_ordens(pasta)['ordens']:
                relativo=(pasta/ordem['arquivo']).relative_to(base).as_posix()
                arquivos.append(f"- {relativo} — páginas {', '.join(str(n) if n is not None else 'não informada' for n in ordem['paginas'])}")
    regra=('Leia integralmente as Ordens de Serviço transcritas, começando pelas candidatas nas páginas finais. '
           'Confirme por data e conteúdo qual é a O.S. vigente; a posição no PDF não prova vigência. '
           'Transcreva cada solicitação em 02-analise/solicitacoes-os.md com página/fls. e onde o relatório a responde. '
           'A redação deve responder cada solicitação; a revisão deve conferir cada solicitação contra a O.S. e reprovar omissões. '
           'Confira integralidade e eventuais continuações no PDF. Remissões a uma O.S. não são a própria ordem. ')
    if not arquivos:
        return '\nORDEM DE SERVIÇO NÃO LOCALIZADA: confira especialmente as páginas finais dos autos e o OCR. Não redija o relatório sem localizar a O.S. e registre DADOS FALTANTES — PROVIDENCIAR (OPERADOR).\n'
    return '\nORDENS DE SERVIÇO EM MARKDOWN:\n'+'\n'.join(arquivos)+'\n'+regra+'\n'


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pasta',type=Path,help='Pasta da extração contendo transcricao.md')
    args=ap.parse_args()
    info=extrair_ordens(args.pasta)
    print(json.dumps(info,ensure_ascii=False,indent=2))
