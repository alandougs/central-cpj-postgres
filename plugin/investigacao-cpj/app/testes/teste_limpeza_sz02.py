"""Limpeza arquivada de derivados fictícios: preservação e limites."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[4]

class LimpezaSZ02(unittest.TestCase):
    def setUp(self):
        script=ROOT/'ferramentas/limpar-derivados.py'
        self.assertTrue(script.is_file(), 'ferramenta de limpeza ainda ausente')
        spec=importlib.util.spec_from_file_location('limpeza_sz02',script)
        self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
        self.tmp=tempfile.TemporaryDirectory(prefix='cpj-sz02-');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.ws=self.base/'ws'
        self.caso=self.ws/'casos/FICTICIO';self.doc=self.caso/'01-extracao/doc'
        (self.doc/'.checkpoint').mkdir(parents=True)
        (self.caso/'00-originais').mkdir();self.pdf=self.caso/'00-originais/original.pdf';self.pdf.write_bytes(b'PDF FICTICIO')
        sha=hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.reg={'reg':{'pagina':1,'texto':'conteudo ficticio','metodo':'texto-nativo'},'flag':None}
        self.estado={'meta':{'versao':2,'sha256':sha,'dpi':200},'relatorio':{'paginas':1,'sha256_original':sha},'paginas':{'1':self.reg},'qualidade':{}}
        (self.doc/'.checkpoint/estado.json').write_text(json.dumps(self.estado))
        (self.doc/'.checkpoint/p0001.json').write_text(json.dumps(self.reg))
        (self.doc/'transcricao.md').write_text('## Página 1\nconteudo ficticio',encoding='utf-8')
        (self.doc/'dados_extraidos.json').write_text('{}')
        (self.doc/'desconhecido.json').write_text('{}')
        (self.doc/'tabelas').mkdir();(self.doc/'tabelas/t001_pag0001.csv').write_text('coluna;valor')
        (self.doc/'tabelas/manual.csv').write_text('manter')
        (self.doc/'paginas_visao').mkdir();(self.doc/'paginas_visao/p0001.png').write_bytes(b'PNG')
        (self.caso/'caso.json').write_text('{}')
        (self.caso/'02-analise').mkdir();(self.caso/'02-analise/entidades.csv').write_text('manter')
        self.zip=self.base/'arquivo.zip'

    def test_arquiva_restauravel_preservando_pdf_markdown_estado_e_desconhecidos(self):
        antes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ws.rglob('*') if p.is_file()}
        plano=self.mod.planejar(self.ws)
        self.assertEqual(len(plano),4)
        self.assertTrue(all(p.exists() for p in antes))
        self.mod.aplicar(self.ws,self.zip,plano)
        self.assertTrue(self.pdf.is_file());self.assertTrue((self.doc/'transcricao.md').is_file())
        self.assertTrue((self.doc/'.checkpoint/estado.json').is_file())
        self.assertTrue((self.doc/'desconhecido.json').is_file());self.assertTrue((self.doc/'tabelas/manual.csv').is_file())
        self.assertTrue((self.caso/'caso.json').is_file());self.assertTrue((self.caso/'02-analise/entidades.csv').is_file())
        self.assertFalse((self.doc/'dados_extraidos.json').exists())
        self.mod.restaurar(self.ws,self.zip)
        self.assertEqual(antes,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.ws.rglob('*') if p.is_file()})

    def test_nao_remove_se_zip_truncado(self):
        plano=self.mod.planejar(self.ws);self.mod.aplicar(self.ws,self.zip,plano)
        self.mod.restaurar(self.ws,self.zip)
        dados=self.zip.read_bytes();self.zip.write_bytes(dados[:len(dados)//2])
        with self.assertRaises((ValueError,OSError)):
            self.mod.restaurar(self.ws,self.zip)
        self.assertTrue((self.doc/'dados_extraidos.json').is_file())

    def test_rejeita_escape_arquivo_mutado_e_zip_dentro_workspace(self):
        with self.assertRaises(ValueError):self.mod.seguro(self.ws,'../fora')
        plano=self.mod.planejar(self.ws)
        with self.assertRaises(ValueError):self.mod.aplicar(self.ws,self.ws/'backup.zip',plano)
        with self.assertRaises(ValueError):self.mod.aplicar(self.ws,self.zip,[{'arquivo':'../fora','sha256':'a','bytes':1}])
        (self.doc/'dados_extraidos.json').write_text('mudou')
        with self.assertRaises(ValueError):self.mod.aplicar(self.ws,self.zip,plano)
        self.assertTrue((self.doc/'dados_extraidos.json').is_file())

    def test_sem_consolidacao_ou_markdown_completo_nao_seleciona(self):
        (self.doc/'.checkpoint/estado.json').unlink()
        self.assertEqual(self.mod.planejar(self.ws),[])

    def test_backup_corrompido_na_verificacao_nao_exclui_fontes(self):
        plano=self.mod.planejar(self.ws);verificar=self.mod.verificar_zip
        def corromper(arquivo):
            arquivo=Path(arquivo);dados=arquivo.read_bytes();arquivo.write_bytes(dados[:len(dados)//2])
            return verificar(arquivo)
        self.mod.verificar_zip=corromper
        with self.assertRaises(ValueError):self.mod.aplicar(self.ws,self.zip,plano)
        self.assertTrue(all(self.mod.seguro(self.ws,r['arquivo']).is_file() for r in plano))

    def test_zip_com_membro_duplicado_e_recusado(self):
        self.mod.aplicar(self.ws,self.zip,self.mod.planejar(self.ws))
        with zipfile.ZipFile(self.zip) as z:manifesto=z.read('_manifesto.json')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(self.zip,'a') as z:z.writestr('_manifesto.json',manifesto)
        with self.assertRaises(ValueError):self.mod.verificar_zip(self.zip)

    def test_markdown_incompleto_ou_pdf_original_divergente_nao_seleciona(self):
        (self.doc/'transcricao.md').write_text('sem pagina',encoding='utf-8')
        self.assertEqual(self.mod.planejar(self.ws),[])
        (self.doc/'transcricao.md').write_text('## Página 1\nconteudo ficticio',encoding='utf-8')
        self.pdf.write_bytes(b'PDF DIVERGENTE')
        self.assertEqual(self.mod.planejar(self.ws),[])

    def test_checkpoint_com_tipo_invalido_nao_seleciona(self):
        self.estado['relatorio']['paginas']=True
        (self.doc/'.checkpoint/estado.json').write_text(json.dumps(self.estado))
        self.assertEqual(self.mod.planejar(self.ws),[])
        self.estado['relatorio']['paginas']=1
        self.estado['paginas']['1']['reg']['texto']=['texto invalido']
        (self.doc/'.checkpoint/estado.json').write_text(json.dumps(self.estado))
        self.assertEqual(self.mod.planejar(self.ws),[])

    def test_junction_nao_atravessada(self):
        fora=self.base/'fora';fora.mkdir();(fora/'dados_extraidos.json').write_text('{}')
        link=self.doc/'atalho'
        if os.name=='nt':
            r=subprocess.run(['cmd','/c','mklink','/J',str(link),str(fora)],capture_output=True)
            if r.returncode:self.skipTest('host sem privilegio de junction')
        else:link.symlink_to(fora,target_is_directory=True)
        self.addCleanup(lambda:os.rmdir(link) if link.exists() else None)
        with self.assertRaises(ValueError):self.mod.seguro(self.ws,link.relative_to(self.ws).as_posix()+'/dados_extraidos.json')
        self.assertEqual(len(self.mod.planejar(self.ws)),4)

if __name__=='__main__':unittest.main()
