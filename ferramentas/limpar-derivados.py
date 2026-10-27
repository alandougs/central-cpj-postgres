"""Arquiva derivados reconhecidos antes de removê-los. Padrão: simulação sem escrita."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile


def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for bloco in iter(lambda:f.read(1<<20),b''):h.update(bloco)
    return h.hexdigest()


def sem_link(p):
    for parte in (p,*p.parents):
        if parte.exists() or parte.is_symlink():
            s=parte.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):
                raise ValueError('Link/junction recusado')


def seguro(raiz,rel):
    raiz=Path(os.path.abspath(raiz));rel=str(rel)
    pp=PurePosixPath(rel)
    if pp.is_absolute() or '..' in pp.parts or '\\' in rel or ':' in rel:
        raise ValueError('Caminho relativo inválido')
    p=raiz.joinpath(*pp.parts)
    sem_link(p)
    if not p.resolve().is_relative_to(raiz.resolve()):raise ValueError('Caminho fora da raiz')
    return p


def caminhar(pasta):
    sem_link(pasta)
    if not pasta.is_dir():return
    for base,dirs,files in os.walk(pasta,followlinks=False):
        validos=[]
        for nome in dirs:
            try:sem_link(Path(base)/nome)
            except ValueError:continue
            validos.append(nome)
        dirs[:]=validos
        for nome in files:
            p=Path(base)/nome
            try:sem_link(p)
            except ValueError:continue
            yield p


def reconhecido(rel):
    partes=PurePosixPath(rel).parts
    if len(partes)<5 or partes[0]!='casos' or partes[2]!='01-extracao':return False
    local='/'.join(partes[4:])
    if local in {'entidades.csv','dados_extraidos.json','diagnostico.json','relatorio_extracao.json','qualidade.json','.checkpoint/meta.json'}:return True
    return bool(re.fullmatch(r'(?:tabelas/(?:t\d+_pag\d+|indice_tabelas)\.csv|\.checkpoint/p\d+\.json|paginas_visao/p\d+\.png)',local))


def planejar(raiz):
    raiz=Path(os.path.abspath(raiz));sem_link(raiz)
    resultado=[];originais={}
    for p in caminhar(raiz/'casos'):
        if p.name!='estado.json' or p.parent.name!='.checkpoint':continue
        doc=p.parent.parent;rel=doc.relative_to(raiz).parts
        if len(rel)!=4 or rel[0]!='casos' or rel[2]!='01-extracao':continue
        try:
            dados=json.loads(p.read_text(encoding='utf-8'))
            meta=dados['meta'];r=dados['relatorio'];n=r['paginas'];paginas=dados['paginas']
            if type(n) is not int or n<1 or meta.get('versao')!=2:continue
            digest=meta['sha256']
            if not re.fullmatch('[0-9a-f]{64}',digest) or r.get('sha256_original')!=digest:continue
            md=seguro(raiz,(doc/'transcricao.md').relative_to(raiz).as_posix())
            texto=md.read_text(encoding='utf-8-sig')
            nums={int(x) for x in re.findall(r'^## P[áa]gina (\d+)\b',texto,re.M)}
            if not set(range(1,n+1)).issubset(nums):continue
            if any(paginas[str(i)]['reg']['pagina']!=i or not isinstance(paginas[str(i)]['reg'].get('texto'),str) for i in range(1,n+1)):continue
            caso=doc.parent.parent
            if caso not in originais:
                originais[caso]={sha256(f) for f in caminhar(caso/'00-originais') if f.suffix.lower()=='.pdf'}
            if digest not in originais[caso]:continue
        except (OSError,ValueError,KeyError,TypeError):continue
        for candidato in caminhar(doc):
            relativo=candidato.relative_to(raiz).as_posix()
            if not reconhecido(relativo):continue
            local=candidato.relative_to(doc).as_posix();chave={'relatorio_extracao.json':'relatorio','qualidade.json':'qualidade','.checkpoint/meta.json':'meta'}.get(local)
            match=re.fullmatch(r'\.checkpoint/p(\d+)\.json',local)
            if chave or match:
                esperado=dados.get(chave) if chave else paginas.get(str(int(match[1])))
                try:
                    if json.loads(candidato.read_text(encoding='utf-8'))!=esperado:continue
                except (OSError,ValueError):continue
            if candidato.suffix=='.png':
                numero=int(candidato.stem[1:]);reg=paginas.get(str(numero),{})
                if not reg.get('reg',{}).get('texto') or reg.get('flag') in ('pendente','conferir'):continue
                if 'pendente' in reg.get('reg',{}).get('metodo',''):continue
            resultado.append({'arquivo':relativo,'bytes':candidato.stat().st_size,'sha256':sha256(candidato)})
    return sorted(resultado,key=lambda x:x['arquivo'])


def verificar_zip(arquivo):
    try:
        with zipfile.ZipFile(arquivo) as z:
            if z.testzip():raise ValueError('ZIP corrompido')
            man=json.loads(z.read('_manifesto.json'))
            rows=man['arquivos']
            if man.get('schema')!='cpj-limpeza/1' or not isinstance(rows,list):raise ValueError('Manifesto inválido')
            nomes=[r['arquivo'] for r in rows]
            if len(set(nomes))!=len(nomes) or len(z.namelist())!=len(nomes)+1 or set(z.namelist())!=set(nomes)|{'_manifesto.json'}:raise ValueError('ZIP divergente do manifesto')
            for row in rows:
                if not reconhecido(row['arquivo']) or '..' in PurePosixPath(row['arquivo']).parts or '\\' in row['arquivo'] or ':' in row['arquivo']:raise ValueError('Membro inválido')
                h=hashlib.sha256();size=0
                with z.open(row['arquivo']) as f:
                    for bloco in iter(lambda:f.read(1<<20),b''):h.update(bloco);size+=len(bloco)
                if h.hexdigest()!=row['sha256'] or size!=row['bytes']:raise ValueError('SHA-256 divergente no ZIP')
        return rows
    except (zipfile.BadZipFile,KeyError,TypeError,json.JSONDecodeError) as exc:raise ValueError('ZIP/manifesto inválido') from exc


def aplicar(raiz,arquivo,plano):
    raiz=Path(os.path.abspath(raiz));arquivo=Path(os.path.abspath(arquivo));sem_link(raiz);sem_link(arquivo)
    if arquivo.resolve().is_relative_to(raiz.resolve()):raise ValueError('ZIP deve ficar fora do workspace')
    if arquivo.exists():raise ValueError('Arquivo ZIP já existe; não sobrescrever')
    atual={r['arquivo']:r for r in planejar(raiz)}
    for row in plano:
        if atual.get(row['arquivo'])!=row:raise ValueError('Plano inválido ou arquivo alterado')
        seguro(raiz,row['arquivo'])
    if not plano:return {'arquivos':0,'bytes':0}
    if not arquivo.parent.is_dir():raise ValueError('Pasta externa do ZIP deve existir')
    fd,temp=tempfile.mkstemp(prefix='cpj-limpeza-',suffix='.zip',dir=arquivo.parent);os.close(fd)
    try:
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as z:
            for row in plano:z.write(seguro(raiz,row['arquivo']),row['arquivo'])
            z.writestr('_manifesto.json',json.dumps({'schema':'cpj-limpeza/1','arquivos':plano},ensure_ascii=False))
        verificar_zip(Path(temp))
        # Não substituir arquivo criado por outra execução durante o arquivamento.
        with arquivo.open('xb') as destino,Path(temp).open('rb') as origem:
            for bloco in iter(lambda:origem.read(1<<20),b''):destino.write(bloco)
            destino.flush();os.fsync(destino.fileno())
        verificar_zip(arquivo)
        for row in plano:
            if sha256(seguro(raiz,row['arquivo']))!=row['sha256']:raise ValueError('Fonte mudou após backup; nenhuma exclusão iniciada')
        removidos=0;total=0
        for row in plano:
            p=seguro(raiz,row['arquivo'])
            if sha256(p)!=row['sha256']:raise ValueError('Fonte mudou durante limpeza; restaurar pelo ZIP se necessário')
            p.unlink();removidos+=1;total+=row['bytes']
        return {'arquivos':removidos,'bytes':total,'zip_sha256':sha256(arquivo)}
    finally:
        Path(temp).unlink(missing_ok=True)


def restaurar(raiz,arquivo):
    raiz=Path(os.path.abspath(raiz));arquivo=Path(arquivo);sem_link(raiz);sem_link(arquivo)
    rows=verificar_zip(arquivo)
    # Valide todos os destinos antes de escrever o primeiro.
    for row in rows:
        p=seguro(raiz,row['arquivo'])
        if p.exists() and sha256(p)!=row['sha256']:raise ValueError('Restauração não sobrescreve arquivo alterado')
    with zipfile.ZipFile(arquivo) as z:
        for row in rows:
            p=seguro(raiz,row['arquivo'])
            if p.exists():continue
            p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(row['arquivo']) as fonte,p.open('xb') as destino:
                for bloco in iter(lambda:fonte.read(1<<20),b''):destino.write(bloco)
            if sha256(p)!=row['sha256']:raise ValueError('Restauração SHA-256 divergente')
    return {'arquivos':len(rows),'bytes':sum(r['bytes'] for r in rows)}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workspace',type=Path,required=True)
    ap.add_argument('--aplicar',action='store_true');ap.add_argument('--restaurar',action='store_true');ap.add_argument('--zip',type=Path)
    a=ap.parse_args()
    if a.aplicar and a.restaurar:ap.error('Escolha aplicar ou restaurar')
    if (a.aplicar or a.restaurar) and not a.zip:ap.error('--zip externo é obrigatório')
    if a.restaurar:result=restaurar(a.workspace,a.zip)
    else:
        plano=planejar(a.workspace)
        result=aplicar(a.workspace,a.zip,plano) if a.aplicar else {'simulacao':True,'arquivos':len(plano),'bytes':sum(r['bytes'] for r in plano)}
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
