#!/usr/bin/env python3
"""LC01: busca híbrida local no RAG e roteamento das regras para a memória central.

Workspace sintético em TEMP; nenhum caso real é lido. Os testes de embedding são
pulados explicitamente quando as dependências locais não estão instaladas, para
não declarar cobertura que não houve.
"""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "plugin/investigacao-cpj/skills/base-cpj/scripts"


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, BASE / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


emb = _carregar("embeddings")
TEM_EMBEDDING = emb.disponivel()


class RoteamentoDasRegrasLC01(unittest.TestCase):
    """A entrada única só vale se todo procedimento apontar para ela."""

    COMANDOS = sorted((ROOT / "plugin/investigacao-cpj/commands").glob("*.md"))
    SKILLS = sorted((ROOT / "plugin/investigacao-cpj/skills").glob("*/SKILL.md"))
    ANTIGOS = ["PROMPT-AGENTE-PLANTAO.md", "PROMPT-PIPELINE-PDF.md",
               "PROMPT-RODADA-ENXUTA.md", "PROMPT-RODADA-F.md", "PILOTO-2026.md",
               "REVISAO-TECNICA-2026-09-27.md", "LEIA-ME.md", "APRESENTACAO-SISTEMA.md"]

    def test_comandos_e_skills_citam_a_memoria_central(self):
        self.assertEqual(len(self.COMANDOS), 10)
        self.assertEqual(len(self.SKILLS), 6)
        for caminho in self.COMANDOS + self.SKILLS:
            texto = caminho.read_text(encoding="utf-8")
            self.assertEqual(texto.count("MEMORIA.md"), 1,
                             f"{caminho.name} deve citar MEMORIA.md exatamente uma vez")

    def test_documentos_antigos_apontam_para_a_fonte_vigente(self):
        for nome in self.ANTIGOS:
            texto = (ROOT / nome).read_text(encoding="utf-8")
            self.assertIn("MEMORIA.md", texto, f"{nome} não aponta para a entrada vigente")

    def test_agents_md_sem_caractere_de_controle_em_caminho(self):
        with open(ROOT / "AGENTS.md", encoding="utf-8", newline="") as fh:
            bruto = fh.read()
        achados = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", bruto)
        self.assertEqual(achados, [], "byte de controle corrompe caminho de arquivo nas regras")
        self.assertEqual(re.findall(r"\r(?!\n)", bruto), [], "CR solto quebra caminho nas regras")
        self.assertIn("skills" + chr(92) + "analise-ip-fraude" + chr(92) + "references",
                      bruto, "caminho da regra 17 deve estar legível")


class JanelasLC01(unittest.TestCase):
    """O modelo trunca em 128 tokens; a janela existe para cobrir a página toda."""

    def test_janelas_cobrem_todas_as_palavras(self):
        texto = " ".join(f"palavra{i}" for i in range(250))
        partes = emb.janelas(texto, palavras=100)
        self.assertEqual(len(partes), 3)
        self.assertEqual(" ".join(partes).split(), texto.split())

    def test_janela_limita_custo_de_trecho_enorme(self):
        texto = " ".join(["palavra"] * 10000)
        self.assertLessEqual(len(emb.janelas(texto, palavras=96, maximo=24)), 24)

    def test_texto_vazio_nao_gera_janela(self):
        self.assertEqual(emb.janelas(""), [])
        self.assertEqual(emb.janelas(None), [])


class BuscaHibridaLC01(unittest.TestCase):
    TRANSFERENCIA = ("A vítima efetuou a transferência bancária do valor "
                     "para a conta bancária indicada durante o atendimento.")
    VEICULO = ("O veículo utilitário permaneceu recolhido no pátio sob "
               "guarda, aguardando perícia mecânica e laudo do motor.")
    # Nenhuma destas palavras aparece no trecho da transferência.
    CONSULTA_SEMANTICA = "remessa de quantia em dinheiro pelo banco"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-lc01-sintetico-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ws = Path(cls.tmp.name)
        cls.env = dict(os.environ, CPJ_WORKSPACE=str(cls.ws),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
                       CPJ_SEM_AGENTE_EMBUTIDO="1",
                       CPJ_EMBEDDINGS_CACHE=str(ROOT / "rag" / "modelos"))
        (cls.ws / "modelos").mkdir()
        docs = {
            ("OS-9801-2099", "autos-lc01"): (
                f"# Transcrição sintética\n\n## Página 1\nFls. 11\n{cls.TRANSFERENCIA}\n\n"
                f"## Página 2\nFls. 12\n{cls.VEICULO}\n"),
        }
        for (caso, documento), texto in docs.items():
            doc = cls.ws / "casos" / caso / "01-extracao" / documento
            doc.mkdir(parents=True)
            (doc / "transcricao.md").write_text(texto, encoding="utf-8")
            (cls.ws / "casos" / caso / "caso.json").write_text(json.dumps({
                "id": caso, "status": "recebido", "ordem_servico": caso[3:],
            }), encoding="utf-8")
        cls.cli("indexar.py", "--tudo")

    @classmethod
    def cli(cls, script, *args, timeout=900):
        r = subprocess.run([sys.executable, str(BASE / script), *args], cwd=cls.ws,
                           env=cls.env, capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
        if r.returncode:
            raise AssertionError(f"CLI {script} falhou ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r.stdout

    def banco(self):
        return sqlite3.connect(str(self.ws / "rag" / "cpj.sqlite"))

    def test_consulta_semantica_nao_tem_resposta_lexical(self):
        out = self.cli("rag.py", "buscar", self.CONSULTA_SEMANTICA, "--modo", "lexical")
        self.assertIn("Nada encontrado", out,
                      "a consulta foi escolhida justamente por não casar por palavra")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_indexar_embeddings_grava_vetor_por_trecho(self):
        self.cli("indexar.py", "--embeddings")
        db = self.banco()
        linhas = db.execute("SELECT tipo, embedding FROM trechos").fetchall()
        db.close()
        self.assertTrue(linhas)
        for tipo, blob in linhas:
            self.assertIsNotNone(blob, f"trecho {tipo} ficou sem vetor")
            self.assertEqual(len(blob), emb.DIM * 4, "vetor deve ter DIM floats de 4 bytes")
        v = emb.desempacotar(linhas[0][1])
        self.assertAlmostEqual(float((v * v).sum()), 1.0, places=3,
                               msg="vetor gravado deve estar normalizado")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_hibrida_acha_trecho_sem_termo_literal_e_ranqueia_na_frente(self):
        self.cli("indexar.py", "--embeddings")
        out = self.cli("rag.py", "buscar", self.CONSULTA_SEMANTICA, "--modo", "hibrido", "-n", "2")
        self.assertIn("OS-9801-2099", out)
        self.assertIn("pág. 1", out, "o trecho da transferência deveria aparecer")
        primeiro = out.split("■")[1]
        self.assertIn("pág. 1", primeiro, "a transferência deve vir antes do veículo")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_filtro_de_caso_vale_tambem_na_parte_semantica(self):
        self.cli("indexar.py", "--embeddings")
        out = self.cli("rag.py", "buscar", self.CONSULTA_SEMANTICA, "--modo", "hibrido",
                       "--caso", "OS-0000-2099")
        self.assertIn("Nada encontrado", out, "filtro de caso não pode ser contornado pelo vetor")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_similaridade_separa_tema_proximo_de_tema_distante(self):
        a, b, c = emb.vetores([self.TRANSFERENCIA, self.CONSULTA_SEMANTICA, self.VEICULO])
        self.assertGreater(emb.similaridade(a, b), emb.similaridade(c, b),
                           "pagamento deve ficar mais perto de remessa de dinheiro que de veículo")


class RegressaoDefeitosLC01(unittest.TestCase):
    """Trava os defeitos que a revisão independente achou e reprovou (D1, D3, D4, D6, D10)
    e o cache da matriz. Cada teste reproduz a condição que quebrava antes."""

    # Contém os termos da consulta.
    LEXICAL = ("A vítima efetuou a transferência bancária do valor para a conta "
               "bancária indicada durante o atendimento presencial.")
    # Mesmo assunto, nenhum dos termos da consulta.
    PARAFRASE = ("Houve remessa de quantia em espécie por meio de instituição "
                 "financeira, mediante ordem de pagamento ao destinatário.")
    # Assunto sem nenhuma relação: é quem não pode aparecer.
    ALHEIO = ("Receita de bolo de cenoura com cobertura de chocolate meio amargo "
              "e castanhas picadas por cima da massa.")
    CONSULTA = "transferência bancária"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-lc01-regressao-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ws = Path(cls.tmp.name)
        cls.env = dict(os.environ, CPJ_WORKSPACE=str(cls.ws),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
                       CPJ_SEM_AGENTE_EMBUTIDO="1",
                       CPJ_EMBEDDINGS_CACHE=str(ROOT / "rag" / "modelos"))
        (cls.ws / "modelos").mkdir()
        casos = {
            "OS-7001-2099": f"## Página 1\nFls. 11\n{cls.LEXICAL}\n\n## Página 2\nFls. 12\n{cls.PARAFRASE}\n\n## Página 3\nFls. 13\n{cls.ALHEIO}\n",
            "OS-7002-2099": f"## Página 1\nFls. 21\n{cls.LEXICAL} Documento do segundo caso.\n",
        }
        for caso, texto in casos.items():
            doc = cls.ws / "casos" / caso / "01-extracao" / "autos"
            doc.mkdir(parents=True)
            (doc / "transcricao.md").write_text(texto, encoding="utf-8")
            (cls.ws / "casos" / caso / "caso.json").write_text(
                json.dumps({"id": caso, "status": "recebido", "ordem_servico": caso[3:]}), encoding="utf-8")
        cls.cli("indexar.py", "--tudo")

    @classmethod
    def cli(cls, script, *args, timeout=900):
        r = subprocess.run([sys.executable, str(BASE / script), *args], cwd=cls.ws,
                           env=cls.env, capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
        return r

    @classmethod
    def ok(cls, script, *args):
        r = cls.cli(script, *args)
        if r.returncode:
            raise AssertionError(f"{script} falhou ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r.stdout

    def banco(self):
        return sqlite3.connect(str(self.ws / "rag" / "cpj.sqlite"))

    def id_do_trecho(self, fragmento):
        with closing(self.banco()) as db:
            linha = db.execute("SELECT id FROM trechos WHERE texto LIKE ?", (f"%{fragmento}%",)).fetchone()
        self.assertIsNotNone(linha, f"trecho com {fragmento!r} não foi indexado")
        return linha[0]

    def vetorizar(self, apenas=None):
        """Gera todos os vetores e, se `apenas` vier, anula os demais (cobertura parcial)."""
        self.ok("indexar.py", "--embeddings")
        if apenas is not None:
            with closing(self.banco()) as db:
                db.execute("UPDATE trechos SET embedding = NULL WHERE id <> ?", (apenas,))
                db.commit()

    def limpar_vetores(self):
        with closing(self.banco()) as db:
            db.execute("UPDATE trechos SET embedding = NULL")
            db.commit()

    # ------------------------------------------------------------------ D1
    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d1_cobertura_parcial_nao_promove_trecho_alheio_no_auto(self):
        """O defeito: com um único vetor na base, o `auto` virava híbrido e punha o
        trecho vetorizado à frente de trechos que continham os termos."""
        alheio = self.id_do_trecho("bolo de cenoura")
        self.vetorizar(apenas=alheio)
        saida = self.ok("rag.py", "buscar", self.CONSULTA, "--modo", "auto", "-n", "5")
        self.assertIn("pág. 1", saida, "o trecho com os termos deve aparecer")
        self.assertNotIn("bolo", saida.lower(),
                         "trecho sem os termos não pode entrar só porque é o único vetorizado")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d1_cobertura_parcial_avisa_a_porcentagem(self):
        alheio = self.id_do_trecho("bolo de cenoura")
        self.vetorizar(apenas=alheio)
        saida = self.ok("rag.py", "buscar", self.CONSULTA, "--modo", "semantico")
        self.assertIn("A base tem vetor em", saida)
        self.assertIn("dos trechos", saida)

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d1_limiar_corta_trecho_sem_relacao(self):
        """Sem limiar, o modo semântico devolvia a base toda ordenada, inclusive o alheio."""
        self.vetorizar()
        saida = self.ok("rag.py", "buscar", self.CONSULTA, "--modo", "semantico", "-n", "10")
        self.assertNotIn("bolo", saida.lower(), "cosseno abaixo de SIMILARIDADE_MINIMA deve ser descartado")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d1_avisa_quando_parte_do_resultado_e_so_semantica(self):
        self.vetorizar()
        saida = self.ok("rag.py", "buscar", self.CONSULTA, "--modo", "hibrido", "-n", "5")
        self.assertIn("proximidade de sentido", saida,
                      "resultado que entrou sem conter os termos tem de ser declarado")

    # ------------------------------------------------------------------ D3
    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d3_blob_de_tamanho_impossivel_nao_derruba_a_busca(self):
        """5 bytes não é múltiplo de 4: antes virava ValueError e matava a busca inteira."""
        self.vetorizar()
        alvo = self.id_do_trecho("bolo de cenoura")
        with closing(self.banco()) as db:
            db.execute("UPDATE trechos SET embedding = ? WHERE id = ?", (b"12345", alvo))
            db.commit()
        r = self.cli("rag.py", "buscar", self.CONSULTA, "--modo", "hibrido")
        self.assertEqual(r.returncode, 0, f"a busca caiu: {r.stderr}")
        self.assertIn("pág. 1", r.stdout)

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d3_texto_no_lugar_do_blob_nao_derruba_a_busca(self):
        """Antes virava TypeError e, pela web, HTTP 500."""
        self.vetorizar()
        alvo = self.id_do_trecho("bolo de cenoura")
        with closing(self.banco()) as db:
            db.execute("UPDATE trechos SET embedding = 'nao sou blob' WHERE id = ?", (alvo,))
            db.commit()
        r = self.cli("rag.py", "buscar", self.CONSULTA, "--modo", "hibrido")
        self.assertEqual(r.returncode, 0, f"a busca caiu: {r.stderr}")
        self.assertIn("pág. 1", r.stdout)

    # ------------------------------------------------------------------ D4
    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_d4_fts_impoe_textual_mesmo_com_modo_hibrido(self):
        """A expressão FTS crua existe para delimitar o resultado; o modo não pode diluí-la."""
        self.vetorizar()
        expressao = "NEAR(transferência conta, 5)"
        puro = self.ok("rag.py", "buscar", expressao, "--fts", "-n", "10")
        forcado = self.ok("rag.py", "buscar", expressao, "--fts", "--modo", "hibrido", "-n", "10")
        self.assertEqual(puro.count("■"), forcado.count("■"),
                         "--fts com --modo hibrido não pode trazer acerto a mais")
        self.assertIn("impõe busca textual", forcado, "o modo ignorado tem de ser declarado")

    # ------------------------------------------------------------------ D6
    def test_d6_semantico_sem_vetores_diz_a_causa(self):
        """Antes dizia só 'Nada encontrado', indistinguível de base sem o assunto."""
        self.limpar_vetores()
        saida = self.ok("rag.py", "buscar", self.CONSULTA, "--modo", "semantico")
        self.assertIn("Busca semântica indisponível", saida)
        self.assertIn("indexar.py --embeddings", saida)

    def test_d6_auto_sem_vetores_continua_textual_sem_ruido(self):
        self.limpar_vetores()
        saida = self.ok("rag.py", "buscar", self.CONSULTA, "--modo", "auto")
        self.assertIn("pág. 1", saida)
        self.assertNotIn("indisponível", saida, "o auto cai para textual sem alarmar o operador")

    # ------------------------------------------------------------------ D10
    def test_d10_sys_path_nao_cresce_a_cada_busca(self):
        """Antes crescia uma entrada por consulta, e a pasta tem módulos homônimos
        aos do app (consulta.py, metricas.py), que poderiam sombrear imports."""
        self.vetorizar()
        # `hibrido` explícito: o modo `auto` poderia cair no caminho lexical e
        # nunca tocar em sys.path, e o teste passaria sem exercitar nada.
        codigo = (
            "import importlib.util, sys, json\n"
            f"spec = importlib.util.spec_from_file_location('ragmod', r'{BASE / 'rag.py'}')\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "antes = len(sys.path)\n"
            "for _ in range(5): m.buscar('transferência bancária', n=3, modo='hibrido')\n"
            f"pasta = r'{BASE}'\n"
            "repetidas = sum(1 for p in sys.path if p and p.rstrip('\\\\/').lower() == pasta.rstrip('\\\\/').lower())\n"
            "print(json.dumps({'antes': antes, 'depois': len(sys.path), 'repetidas': repetidas}))\n"
        )
        r = subprocess.run([sys.executable, "-c", codigo], cwd=self.ws, env=self.env,
                           capture_output=True, text=True, encoding="utf-8", timeout=600)
        self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
        medida = json.loads(r.stdout.strip().splitlines()[-1])
        # Inserir a pasta uma vez é legítimo; o defeito era inserir a cada consulta.
        self.assertLessEqual(medida["repetidas"], 1,
                             f"a pasta de scripts aparece {medida['repetidas']}x em sys.path")
        self.assertLessEqual(medida["depois"] - medida["antes"], 1,
                             f"sys.path cresceu de {medida['antes']} para {medida['depois']} em 5 buscas")

    # ------------------------------------------------- cache da matriz
    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_cache_invalida_quando_o_banco_muda(self):
        """Servir matriz velha num instrumento de investigação é pior que recarregar."""
        self.vetorizar()
        codigo = (
            "import importlib.util, sqlite3, sys, json, os\n"
            f"spec = importlib.util.spec_from_file_location('ragmod', r'{BASE / 'rag.py'}')\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "m.buscar('transferência bancária', n=3, modo='hibrido')\n"
            "ids1 = list(m._CACHE['ids'] or []); ch1 = m._CACHE['chave']\n"
            "db = sqlite3.connect(m.DB)\n"
            "db.execute(\"INSERT INTO trechos (caso, arquivo, tipo, texto) VALUES ('OS-7003-2099','x.md','analise','texto novo sintetico')\")\n"
            "db.commit(); db.close()\n"
            "m.buscar('transferência bancária', n=3, modo='hibrido')\n"
            "print(json.dumps({'mudou': m._CACHE['chave'] != ch1, 'tinha': len(ids1) > 0}))\n"
        )
        r = subprocess.run([sys.executable, "-c", codigo], cwd=self.ws, env=self.env,
                           capture_output=True, text=True, encoding="utf-8", timeout=600)
        self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
        medida = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(medida["tinha"], "a primeira busca deveria ter populado o cache")
        self.assertTrue(medida["mudou"], "gravação no banco tem de invalidar o cache")

    @unittest.skipUnless(TEM_EMBEDDING, "fastembed/numpy ausentes no ambiente")
    def test_filtro_de_caso_nao_vaza_com_cache_quente(self):
        """O cache é da base inteira: o filtro por caso não pode ser contornado por ele."""
        self.vetorizar()
        codigo = (
            "import importlib.util, sys, json\n"
            f"spec = importlib.util.spec_from_file_location('ragmod', r'{BASE / 'rag.py'}')\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "m.buscar('transferência bancária', n=10, modo='hibrido')\n"
            "a, _ = m.buscar('transferência bancária', n=10, modo='hibrido', caso='OS-7002-2099')\n"
            "b, _ = m.buscar('transferência bancária', n=10, modo='semantico', caso='OS-7002-2099')\n"
            "inj, _ = m.buscar('transferência bancária', n=10, modo='hibrido', caso=\"x'; DROP TABLE trechos; --\")\n"
            "print(json.dumps({'casos_a': sorted({r['caso'] for r in a}), "
            "'casos_b': sorted({r['caso'] for r in b}), 'injecao': len(inj)}))\n"
        )
        r = subprocess.run([sys.executable, "-c", codigo], cwd=self.ws, env=self.env,
                           capture_output=True, text=True, encoding="utf-8", timeout=600)
        self.assertEqual(r.returncode, 0, f"{r.stdout}\n{r.stderr}")
        medida = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(medida["casos_a"], ["OS-7002-2099"], "híbrido com filtro vazou outro caso")
        self.assertEqual(medida["casos_b"], ["OS-7002-2099"], "semântico com filtro vazou outro caso")
        self.assertEqual(medida["injecao"], 0, "filtro com injeção de SQL devia devolver nada")
        with closing(self.banco()) as db:
            self.assertGreater(db.execute("SELECT COUNT(*) FROM trechos").fetchone()[0], 0,
                               "a tabela trechos tem de continuar intacta")


class BuscaSemVetoresLC01(BuscaHibridaLC01):
    """Workspace próprio: aqui `--embeddings` nunca roda, para provar a queda limpa
    para a busca textual numa base sem vetores (é o estado de quem não gerou)."""

    def test_base_sem_vetor_e_busca_textual_intacta(self):
        db = self.banco()
        nulos = db.execute("SELECT COUNT(*) FROM trechos WHERE embedding IS NULL").fetchone()[0]
        total = db.execute("SELECT COUNT(*) FROM trechos").fetchone()[0]
        db.close()
        self.assertEqual(nulos, total, "indexar.py sem --embeddings não deve gravar vetor")
        out = self.cli("rag.py", "buscar", "transferência bancária")
        self.assertIn("OS-9801-2099", out)
        self.assertIn("pág. 1; fls. 11", out)

    def test_modo_auto_sem_vetor_nao_quebra(self):
        out = self.cli("rag.py", "buscar", "transferência bancária", "--modo", "auto")
        self.assertIn("OS-9801-2099", out)


def load_tests(loader, tests, pattern):
    """Só os testes próprios de BuscaSemVetoresLC01: os herdados geram vetores
    e contaminariam o workspace que esta classe precisa manter sem eles."""
    suite = unittest.TestSuite()
    for classe in (RoteamentoDasRegrasLC01, JanelasLC01, BuscaHibridaLC01, RegressaoDefeitosLC01):
        suite.addTests(loader.loadTestsFromTestCase(classe))
    proprios = set(BuscaSemVetoresLC01.__dict__) - set(BuscaHibridaLC01.__dict__)
    for nome in sorted(n for n in proprios if n.startswith("test_")):
        suite.addTest(BuscaSemVetoresLC01(nome))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
