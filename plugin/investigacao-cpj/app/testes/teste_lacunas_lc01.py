#!/usr/bin/env python3
"""LC01: busca híbrida local no RAG e roteamento das regras para a memória central.

Workspace sintético em TEMP; nenhum caso real é lido. Os testes de embedding são
pulados explicitamente quando as dependências locais não estão instaladas, para
não declarar cobertura que não houve.
"""
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
    for classe in (RoteamentoDasRegrasLC01, JanelasLC01, BuscaHibridaLC01):
        suite.addTests(loader.loadTestsFromTestCase(classe))
    proprios = set(BuscaSemVetoresLC01.__dict__) - set(BuscaHibridaLC01.__dict__)
    for nome in sorted(n for n in proprios if n.startswith("test_")):
        suite.addTest(BuscaSemVetoresLC01(nome))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
