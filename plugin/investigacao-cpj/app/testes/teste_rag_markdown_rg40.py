#!/usr/bin/env python3
"""RG40: CLI real do RAG FTS, com Markdown sintético e workspace TEMP."""
from contextlib import closing
import csv
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "plugin/investigacao-cpj/skills/base-cpj/scripts"


class RagMarkdownRG40(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-rg40-sintetico-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ws = Path(cls.tmp.name)
        cls.env = dict(os.environ, CPJ_WORKSPACE=str(cls.ws),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
                       CPJ_SEM_AGENTE_EMBUTIDO="1")
        (cls.ws / "modelos").mkdir()
        docs = {
            ("OS-9401-2099", "autos-alfa"): (
                "# Transcrição sintética\n\n## Página 1\nFls. 41\n"
                "Âncora abacaxiroxo. Identificador fictício 00000000191. "
                "CPF sintético 000.000.002-72. Marcador compartilhadorg40.\n\n"
                "## Página 2\nFls. 58\n"
                "Chave Pix sintética teste-rg40@example.invalid. "
                "Telefone sintético (00) 00000-0940. "
                "Número incerto 00000000?91 [dígito incerto]. "
                "Vide Fls. 999: remissão, não folha desta página.\n"),
            ("OS-9401-2099", "complemento-beta"): (
                "## Página 1\nComplementorg40 em documento distinto; "
                "vide Fls. 777 como remissão no corpo.\n"),
            ("OS-9402-2099", "autos-gama"): (
                "## Página 7\nFls. 83\nMarcador compartilhadorg40. "
                "Identificador fictício 00000000191. Exclusivogamarg40.\n"),
        }
        for (caso, documento), texto in docs.items():
            pasta = cls.ws / "casos" / caso
            doc = pasta / "01-extracao" / documento
            doc.mkdir(parents=True)
            (doc / "transcricao.md").write_text(texto, encoding="utf-8")
            (pasta / "caso.json").write_text(json.dumps({
                "id": caso, "status": "recebido", "ordem_servico": caso[3:],
            }), encoding="utf-8")
        referencia = cls.ws / "referencias" / "estilo-ficticio"
        referencia.mkdir(parents=True)
        (referencia / "texto.md").write_text(
            "# Estilo sintético\nMarcador compartilhadorg40. Referenciaexclusivarg40.\n",
            encoding="utf-8")
        cls.indexacao = cls.cli("indexar.py", "--tudo")

    @classmethod
    def cli(cls, script, *args):
        result = subprocess.run([sys.executable, str(BASE / script), *args],
                                cwd=cls.ws, env=cls.env, capture_output=True,
                                text=True, encoding="utf-8", timeout=60)
        if result.returncode:
            raise AssertionError(f"CLI {script} falhou ({result.returncode}):\n"
                                 f"{result.stdout}\n{result.stderr}")
        return result.stdout

    def buscar(self, termo, *filtros):
        return self.cli("rag.py", "buscar", termo, *filtros)

    def test_markdown_utf8_tem_caso_documento_pagina_e_folha_reais(self):
        out = self.buscar("abacaxiroxo")
        self.assertIn("OS-9401-2099 | transcricao | pág. 1; fls. 41", out)
        self.assertIn(str(Path("casos/OS-9401-2099/01-extracao/autos-alfa/transcricao.md")), out)
        self.assertIn("Âncora", out)
        self.assertNotIn("OS-9402-2099", out)
        segundo = self.buscar("Complementorg40")
        self.assertIn("complemento-beta", segundo)
        self.assertIn("pág. 1", segundo)
        self.assertNotIn("; fls.", segundo, "Remissão no corpo não é folha física.")

    def test_digitos_identificadores_exatos_e_incertos(self):
        out = self.buscar("00000000191", "--tipo", "transcricao")
        self.assertEqual(out.count("■"), 2)
        self.assertIn("OS-9401-2099", out)
        self.assertIn("OS-9402-2099", out)
        self.assertNotIn("pág. 2", out, "Não completar o dígito incerto.")
        self.assertIn("Nada encontrado", self.buscar("00000000192"))
        self.assertIn("pág. 1; fls. 41", self.buscar("000.000.002-72"))
        self.assertIn("pág. 2; fls. 58", self.buscar("teste-rg40@example.invalid"))

    def test_filtro_caso_tipo_separa_casos_e_referencia(self):
        geral = self.buscar("compartilhadorg40")
        self.assertEqual(geral.count("■"), 3)
        self.assertIn("- | referencia", geral)
        caso = self.buscar("compartilhadorg40", "--caso", "OS-9401-2099",
                           "--tipo", "transcricao")
        self.assertEqual(caso.count("■"), 1)
        self.assertNotIn("OS-9402-2099", caso)
        self.assertNotIn("referencia", caso)
        referencia = self.buscar("Referenciaexclusivarg40", "--tipo", "referencia")
        self.assertIn("- | referencia", referencia)
        self.assertNotIn("OS-9401-2099", referencia)
        self.assertIn("Nada encontrado", self.buscar("Exclusivogamarg40", "--caso", "OS-9401-2099"))

    def test_sem_derivados_documentais_preserva_entidades_candidatas(self):
        extracoes = self.ws / "casos"
        self.assertEqual(list(extracoes.rglob("*.csv")), [])
        self.assertEqual(list(extracoes.rglob("dados_extraidos.json")), [])
        self.assertEqual(sorted(p.name for p in extracoes.rglob("*.json")),
                         ["caso.json", "caso.json"])
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM entidades WHERE tipo='CPF' AND valor_norm='00000000191'").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM trechos WHERE tipo='transcricao'").fetchone()[0], 4)
        out = self.cli("rag.py", "entidade", "00000000191", "--tipo", "CPF")
        self.assertIn("2 ocorrência(s)", out)
        self.assertIn("autos-alfa", out)
        self.assertIn("autos-gama", out)
        self.assertIn("OS-9402-2099", self.cli("rag.py", "cruzar", "OS-9401-2099"))
        self.assertIn("1 ocorrência(s)", self.cli("rag.py", "entidade", "00000000272", "--tipo", "CPF"))

    def test_grafo_candidato_preserva_proveniencia_md_e_exclui_incerto(self):
        with closing(sqlite3.connect(self.ws / "rag/cpj.sqlite")) as db:
            rows = db.execute("SELECT localizador FROM arestas WHERE fonte='OS-9401-2099' AND b_tipo='CPF' AND b_valor='00000000191'").fetchall()
            self.assertEqual(len(rows), 1)
            ev = json.loads(rows[0][0])
            self.assertEqual(ev['tipo'], 'extracao_candidata')
            self.assertEqual(ev['status_fonte'], 'pendente de conferência')
            self.assertEqual(ev['pagina'], 1)
            self.assertEqual(ev['registro_origem']['linha'], 5)
            self.assertTrue(ev['arquivo_derivado'].endswith('autos-alfa/transcricao.md'))
            self.assertEqual(ev['documento'], 'autos-alfa')
            self.assertEqual(db.execute("SELECT count(*) FROM entidades WHERE pagina=2 AND tipo='CPF'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM entidades WHERE tipo='TELEFONE' AND valor_norm='00000000191'").fetchone()[0], 0)

    def test_regeneracao_indice_nao_perde_candidatos_markdown(self):
        antes = self.cli("rag.py", "entidade", "00000000191", "--tipo", "CPF")
        self.assertIn("2 ocorrência(s)", antes)
        (self.ws / "rag/cpj.sqlite").unlink()
        self.cli("indexar.py", "--tudo")
        self.assertEqual(antes, self.cli("rag.py", "entidade", "00000000191", "--tipo", "CPF"))

    def test_legado_csv_prevalece_somente_no_proprio_documento(self):
        legado = self.ws / "casos/OS-9401-2099/01-extracao/autos-alfa/entidades.csv"
        legado.write_text("tipo;valor;pagina_pdf;trecho;status\n"
                          "EMAIL;legado@example.invalid;1;Registro sintético;pendente\n", encoding="utf-8-sig")
        try:
            self.cli("indexar.py", "--tudo")
            self.assertIn("1 ocorrência(s)", self.cli("rag.py", "entidade", "00000000191", "--tipo", "CPF"))
            self.assertIn("entidades.csv", self.cli("rag.py", "entidade", "legado@example.invalid"))
            # Complemento de outro documento/caso continua indexável por Markdown.
            self.assertIn("autos-gama", self.cli("rag.py", "entidade", "00000000191", "--tipo", "CPF"))
        finally:
            legado.unlink()
            self.cli("indexar.py", "--tudo")

    def test_parser_puro_pagina_linha_incerto_e_cli_legada(self):
        script = BASE.parents[1] / "pdf-autos-policiais/scripts/entidades.py"
        spec = importlib.util.spec_from_file_location("entidades_rg40", script)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        texto = ("CPF 00000000191 antes da página não é extraído.\n"
                 "## Página 9\nCPF 00000000353 [dígito incerto]\n"
                 "CPF 00000000434?\nCPF 00000000515\n"
                 "<!-- CPF 00000000606\nCPF 00000000707 -->\n"
                 "CPF 00000000808\n")
        rows = list(modulo.iter_candidatos(texto))
        self.assertEqual([(r['tipo'], r['valor'], r['pagina_pdf'], r['linha']) for r in rows],
                         [('CPF', '00000000515', 9, 5), ('CPF', '00000000808', 9, 8)])
        with tempfile.TemporaryDirectory(prefix="cpj-rg40-legado-") as temp:
            doc = Path(temp) / "transcricao.md"
            doc.write_text(texto, encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), str(doc)],
                                    cwd=temp, env=self.env, capture_output=True,
                                    text=True, encoding="utf-8", timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (Path(temp) / "entidades.csv").open(encoding="utf-8-sig", newline="") as f:
                csv_rows = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual([r['valor'] for r in csv_rows], [r['valor'] for r in rows])
            self.assertEqual(set(csv_rows[0]), {'tipo', 'valor', 'pagina_pdf', 'trecho', 'status'})

    def test_limites_fts_normalizacao_e_retorno_parcial_sao_explicitos(self):
        # Texto formatado e dígitos sem pontuação não são equivalentes no FTS atual.
        self.assertIn("Nada encontrado", self.buscar("00000000272"))
        parcial = self.buscar("abacaxiroxo termoinexistenterg40")
        self.assertIn("Nenhum trecho contém todos os termos", parcial)
        self.assertIn("parte deles", parcial)
        self.assertEqual(parcial.count("■"), 1)

    def test_reindexacao_incremental_preserva_referencias(self):
        antes = self.buscar("compartilhadorg40", "--tipo", "transcricao")
        out = self.cli("indexar.py")
        self.assertIn("RAG: 0 arquivo(s) (re)indexado(s)", out)
        self.assertEqual(antes, self.buscar("compartilhadorg40", "--tipo", "transcricao"))

    def test_manutencao_sem_baixa_preserva_bytes_e_default_continua_baixa(self):
        with tempfile.TemporaryDirectory(prefix="cpj-ri01-manutencao-") as temp:
            ws = Path(temp)
            caso = ws / "casos/OS-9499-2099"
            extracao = caso / "01-extracao/doc-manutencao"
            extracao.mkdir(parents=True)
            (ws / "modelos").mkdir()
            (extracao / "transcricao.md").write_text(
                "## Página 3\nMarcador manutencaori01 CPF 00000000191.\n", encoding="utf-8")
            relatorios = caso / "03-relatorios"
            relatorios.mkdir()
            (relatorios / "RELATORIO-FINAL.md").write_text(
                "# Relatório sintético\nFixture de baixa automática.\n", encoding="utf-8")
            meta = caso / "caso.json"
            meta.write_text(json.dumps({"id": caso.name, "status": "analisado",
                                       "ordem_servico": "9499/2099"}, indent=2) + "\n", encoding="utf-8")
            antes = meta.read_bytes()
            hash_antes = hashlib.sha256(antes).hexdigest()
            env = dict(self.env, CPJ_WORKSPACE=str(ws))

            def rodar(script, *args):
                r = subprocess.run([sys.executable, str(BASE / script), *args], cwd=ws, env=env,
                                   capture_output=True, text=True, encoding="utf-8", timeout=60)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                return r.stdout

            rodar("indexar.py", "--tudo", "--sem-baixa")
            self.assertEqual(meta.read_bytes(), antes)
            self.assertEqual(hashlib.sha256(meta.read_bytes()).hexdigest(), hash_antes)
            self.assertEqual(json.loads(meta.read_text(encoding="utf-8"))['status'], 'analisado')
            self.assertIn("pág. 3", rodar("rag.py", "buscar", "manutencaori01"))
            self.assertIn("1 ocorrência(s)", rodar("rag.py", "entidade", "00000000191", "--tipo", "CPF"))
            rodar("indexar.py", "--so-base", "--sem-baixa")
            self.assertEqual(meta.read_bytes(), antes)
            out = rodar("indexar.py", "--tudo")
            self.assertIn("Baixa automática", out)
            entregue = json.loads(meta.read_text(encoding="utf-8"))
            self.assertEqual(entregue['status'], 'entregue')
            self.assertEqual(entregue['baixa']['origem'], 'automatica-pasta')
            self.assertNotEqual(meta.read_bytes(), antes)

    def test_cache_checkpoint_uma_leitura_por_documento_e_execucao(self):
        with tempfile.TemporaryDirectory(prefix="cpj-rg41-cache-") as temp:
            ws = Path(temp)
            (ws / 'modelos').mkdir()
            caso = ws / 'casos/OS-9441-2099'
            caso.mkdir(parents=True)
            meta = caso / 'caso.json'
            meta.write_text(json.dumps({'id': caso.name, 'status': 'analisado'}), encoding='utf-8')
            antes = meta.read_bytes()
            originais = caso / '00-originais'
            originais.mkdir()
            for nome in ('alfa', 'beta', 'vazio', 'erro'):
                doc = caso / '01-extracao' / nome
                doc.mkdir(parents=True)
                (doc / 'transcricao.md').write_text('## Página 7\n' +
                    ''.join(f'CPF 00000000191 candidato sintético {i}.\n' for i in range(30)), encoding='utf-8')
                if nome in ('alfa', 'beta'):
                    pdf = originais / f'{nome}.pdf'
                    pdf.write_bytes(b'%PDF fixture sintetica RG41')
                    checkpoint = doc / '.checkpoint'
                    checkpoint.mkdir()
                    (checkpoint / 'estado.json').write_text(json.dumps({
                        'relatorio': {'arquivo': pdf.name, 'sha256_original': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                                      'gerado_em': '2099-01-01T00:00:00', 'texto_descartavel': 'X' * 20000},
                        'paginas': {'7': {'reg': {'texto': 'Y' * 20000}}},
                    }), encoding='utf-8')
                elif nome == 'erro':
                    (doc / '.checkpoint').mkdir()
                    (doc / '.checkpoint/estado.json').write_text('{invalido', encoding='utf-8')
            codigo = '''
import collections, json, os, runpy, sys
from pathlib import Path
script = Path(sys.argv[1])
sys.path.insert(0, str(script.parents[2] / 'pdf-autos-policiais/scripts'))
import estado_extracao
real = estado_extracao.ler
calls = collections.Counter()
def contar(pasta, nome):
    calls[Path(pasta).name] += 1
    return real(pasta, nome)
estado_extracao.ler = contar
sys.argv = [str(script), '--tudo', '--sem-baixa']
contexto = runpy.run_path(str(script), run_name='__main__')
print('RG41_COUNTERS=' + json.dumps(dict(calls), sort_keys=True))
cache = contexto.get('_metadados_fontes', {})
print('RG41_CACHE=' + json.dumps(list(cache.values()), sort_keys=True))
'''
            env = dict(self.env, CPJ_WORKSPACE=str(ws))

            def executar():
                result = subprocess.run([sys.executable, '-c', codigo, str(BASE / 'indexar.py')],
                    cwd=ws, env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                counters = next(l for l in result.stdout.splitlines() if l.startswith('RG41_COUNTERS='))
                calls = json.loads(counters.split('=', 1)[1])
                self.assertEqual(calls, {'alfa': 1, 'beta': 1, 'erro': 1, 'vazio': 1})
                cache = json.loads(next(l for l in result.stdout.splitlines() if l.startswith('RG41_CACHE=')).split('=', 1)[1])
                self.assertEqual(len(cache), 4)
                self.assertTrue(all(set(m) <= {'arquivo', 'sha256_original', 'gerado_em'} for m in cache))
                self.assertEqual(meta.read_bytes(), antes)
                with closing(sqlite3.connect(ws / 'rag/cpj.sqlite')) as db:
                    return [json.loads(r[0]) for r in db.execute("SELECT localizador FROM arestas WHERE b_tipo='CPF'")]

            evidencias = executar()
            self.assertEqual(len(evidencias), 120)
            for ev in evidencias:
                self.assertEqual(ev['pagina'], 7)
                self.assertEqual(ev['tipo'], 'extracao_candidata')
                self.assertEqual(ev['status_fonte'], 'pendente de conferência')
                self.assertTrue(ev['arquivo_derivado'].endswith('/transcricao.md'))
                self.assertEqual(ev['sha256_derivado'], hashlib.sha256((ws / ev['arquivo_derivado']).read_bytes()).hexdigest())
                if ev['documento'] in ('alfa', 'beta'):
                    self.assertEqual(ev['arquivo_original'], f'casos/{caso.name}/00-originais/{ev["documento"]}.pdf')
                    self.assertEqual(ev['sha256_original'], hashlib.sha256((ws / ev['arquivo_original']).read_bytes()).hexdigest())
                    self.assertEqual(ev['extraido_em'], '2099-01-01T00:00:00')
                else:
                    self.assertIsNone(ev['arquivo_original'])
                    self.assertIsNone(ev['sha256_original'])
            # Nova execução precisa reler o checkpoint e observar mudança real.
            arquivo = caso / '01-extracao/alfa/.checkpoint/estado.json'
            estado = json.loads(arquivo.read_text(encoding='utf-8'))
            estado['relatorio']['gerado_em'] = '2099-02-01T00:00:00'
            arquivo.write_text(json.dumps(estado), encoding='utf-8')
            novas = executar()
            self.assertTrue(all(ev['extraido_em'] == '2099-02-01T00:00:00'
                                for ev in novas if ev['documento'] == 'alfa'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
