#!/usr/bin/env python3
"""MQ01 — medir_entrega.py mede quanto da minuta foi mantido no PDF entregue (o PDF é a versão entregue).
Cobre: texto idêntico = 100 %; texto editado em faixa esperada; escolha do PDF mais recente; minuta gravada depois do
PDF não conta como "antes"; sem PDF = código 2; --gravar cria o JSON sem texto do relatório; sem --gravar nada é criado.
Workspace temporário, dados fictícios, sem rede, sem tocar em casos reais."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent.parent / "skills" / "relatorio-ip-fraude" / "scripts" / "medir_entrega.py"
SENTINELA = "zumbaquelimbo"
N = 300  # palavras do corpo fictício


def corpo(n=N, troca=0, sentinela=False):
    """RESUMO DOS FATOS + n palavras distintas; troca=k substitui uma a cada k palavras."""
    pal = [f"termo{i}" if not (troca and i % troca == 0) else f"outro{i}" for i in range(n)]
    if sentinela:
        pal[5] = SENTINELA
    return "RESUMO DOS FATOS\n" + " ".join(pal) + "\n"


def minuta(texto):
    return "---\nid: fictício\nversao: 1\n---\n" + texto


def gerar_pdf(destino, texto, paginas_extra=0, titulo="RELATÓRIO DE INVESTIGAÇÃO"):
    c = canvas.Canvas(str(destino), pagesize=A4)
    palavras = (titulo + " " + texto).split()
    y = 800
    for i in range(0, len(palavras), 10):
        c.drawString(40, y, " ".join(palavras[i:i + 10]))
        y -= 14
        if y < 60:
            c.showPage()
            y = 800
    for _ in range(paginas_extra):
        c.showPage()
        c.drawString(40, 800, "pagina de enchimento")
    c.save()


class MedirEntregaMQ01(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-mq01-", ignore_cleanup_errors=True)
        self.ws = Path(self.tmp.name) / "ws"
        self.pasta_os = Path(self.tmp.name) / "os"
        (self.ws / "casos").mkdir(parents=True)
        (self.ws / "modelos").mkdir()
        self.pasta_os.mkdir()
        self.env = {**os.environ, "CPJ_WORKSPACE": str(self.ws), "CPJ_PASTA_OS": str(self.pasta_os), "PYTHONUTF8": "1"}

    def tearDown(self):
        self.tmp.cleanup()

    def caso(self, id_="OS-2716-2099", minutas=(), pdfs=()):
        """minutas: [(texto, mtime)]; pdfs: [(nome, texto, mtime)]. Devolve a pasta 03-relatorios."""
        rel = self.ws / "casos" / id_ / "03-relatorios"
        rel.mkdir(parents=True, exist_ok=True)
        for i, (texto, mt) in enumerate(minutas, 1):
            p = rel / f"minuta-v{i:02d}.md"
            p.write_text(minuta(texto), encoding="utf-8")
            os.utime(p, (mt, mt))
        for nome, texto, mt in pdfs:
            p = rel / nome
            gerar_pdf(p, texto)
            os.utime(p, (mt, mt))
        return rel

    def roda(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], env=self.env, capture_output=True,
                              text=True, encoding="utf-8")

    def lido(self, rel):
        return json.loads((rel / "medicao-entrega.json").read_text(encoding="utf-8"))

    def test_01_texto_identico_da_100_por_cento(self):
        self.caso(minutas=[(corpo(), 1000)], pdfs=[("relatorio.pdf", corpo(), 2000)])
        r = self.roda("OS-2716-2099")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(r.stdout.strip().splitlines()), 1, r.stdout)
        self.assertIn("1ª v01 mantida 100.0%", r.stdout)
        self.assertIn("última antes do PDF v01 mantida 100.0%, novo no PDF 0.0%", r.stdout)

    def test_02_texto_editado_cai_na_faixa_esperada(self):
        rel = self.caso(minutas=[(corpo(), 1000)], pdfs=[("relatorio.pdf", corpo(troca=10), 2000)])
        r = self.roda("OS-2716-2099", "--gravar")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = self.lido(rel)
        # 30 de 303 palavras trocadas: ~90 % mantido; ~10 % do PDF é novo
        self.assertTrue(88.0 <= d["primeira"]["mantido"] <= 92.0, d)
        self.assertTrue(88.0 <= d["ultima"]["mantido"] <= 92.0, d)
        self.assertTrue(8.0 <= d["ultima"]["novo"] <= 12.0, d)

    def test_03_escolhe_o_pdf_mais_recente(self):
        rel = self.caso(minutas=[(corpo(), 1000)],
                        pdfs=[("antigo.pdf", corpo(), 1500), ("recente.pdf", corpo(troca=10), 2500)])
        self.assertEqual(self.roda("OS-2716-2099", "--gravar").returncode, 0)
        d = self.lido(rel)
        self.assertEqual(d["pdf"]["nome"], "recente.pdf")
        self.assertLess(d["primeira"]["mantido"], 95.0)

    def test_03b_pedido_de_dilacao_de_prazo_nao_e_relatorio_entregue(self):
        # PDF mais recente, mas é pedido de dilação de prazo: não é a versão entregue do relatório.
        rel = self.caso(minutas=[(corpo(), 1000)],
                        pdfs=[("relatorio.pdf", corpo(), 1500),
                              ("PEDIDO-DILACAO-PRAZO-OS-2716-2099.pdf", corpo(troca=2), 2500)])
        self.assertEqual(self.roda("OS-2716-2099", "--gravar").returncode, 0)
        self.assertEqual(self.lido(rel)["pdf"]["nome"], "relatorio.pdf")
        # caso que só tem o pedido de dilação: sem PDF de relatório
        self.caso(id_="OS-2717-2099", minutas=[(corpo(), 1000)],
                  pdfs=[("Pedido de Dilação de Prazo - OS 2717.pdf", corpo(), 2000)])
        r = self.roda("OS-2717-2099")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("sem PDF", r.stderr)

    def test_04_minuta_gravada_depois_do_pdf_nao_conta_como_antes(self):
        rel = self.caso(minutas=[(corpo(), 1000), (corpo(troca=10), 5000)], pdfs=[("relatorio.pdf", corpo(), 2000)])
        self.assertEqual(self.roda("OS-2716-2099", "--gravar").returncode, 0)
        d = self.lido(rel)
        self.assertEqual(d["versoes_antes_da_entrega"], 1)
        self.assertEqual(d["ultima"]["versao"], 1)
        self.assertEqual(d["primeira"]["versao"], 1)
        self.assertEqual(d["ultima"]["mantido"], 100.0)

    def test_05_so_minutas_depois_do_pdf_deixa_ultima_nula(self):
        rel = self.caso(minutas=[(corpo(), 5000)], pdfs=[("relatorio.pdf", corpo(), 2000)])
        self.assertEqual(self.roda("OS-2716-2099", "--gravar").returncode, 0)
        d = self.lido(rel)
        self.assertEqual(d["versoes_antes_da_entrega"], 0)
        self.assertIsNone(d["ultima"])

    def test_06_sem_pdf_ou_sem_minuta_sai_com_codigo_2(self):
        self.caso(minutas=[(corpo(), 1000)])
        r = self.roda("OS-2716-2099")
        self.assertEqual(r.returncode, 2)
        self.assertIn("sem PDF", r.stderr)
        self.caso("OS-1111-2099", pdfs=[("relatorio.pdf", corpo(), 2000)])
        r = self.roda("OS-1111-2099")
        self.assertEqual(r.returncode, 2)
        self.assertIn("sem minuta", r.stderr)
        self.assertEqual(self.roda("OS-9999-2099").returncode, 2)

    def test_07_gravar_cria_json_sem_texto_do_relatorio(self):
        rel = self.caso(minutas=[(corpo(sentinela=True), 1000)], pdfs=[("relatorio.pdf", corpo(sentinela=True), 2000)])
        r = self.roda("OS-2716-2099", "--gravar")
        self.assertEqual(r.returncode, 0, r.stderr)
        bruto = (rel / "medicao-entrega.json").read_text(encoding="utf-8")
        d = json.loads(bruto)
        self.assertEqual(d["schema"], "cpj-medicao-entrega/1")
        self.assertEqual(d["caso"], "OS-2716-2099")
        self.assertEqual(len(d["pdf"]["sha256"]), 64)
        self.assertEqual(d["pdf"]["nome"], "relatorio.pdf")
        for chave in ("paginas", "palavras", "data"):
            self.assertIn(chave, d["pdf"])
        self.assertIn("gerado_em", d)
        self.assertNotIn(SENTINELA, bruto)
        self.assertNotIn(SENTINELA, r.stdout + r.stderr)
        self.assertEqual([p.name for p in rel.glob("*.tmp")], [])

    def test_08_sem_gravar_nao_cria_arquivo(self):
        rel = self.caso(minutas=[(corpo(), 1000)], pdfs=[("relatorio.pdf", corpo(), 2000)])
        antes = sorted(p.name for p in rel.iterdir())
        self.assertEqual(self.roda("OS-2716-2099").returncode, 0)
        self.assertEqual(sorted(p.name for p in rel.iterdir()), antes)
        self.assertFalse((rel / "medicao-entrega.json").exists())

    def test_09_pdf_da_pasta_da_os_exige_titulo_e_ignora_os_autos(self):
        rel = self.caso(minutas=[(corpo(), 1000)])
        pasta = self.pasta_os / "OS 2716_99 IP 4321_99 PESSOA FICTICIA"
        pasta.mkdir()
        for nome, kw, mt in (("entregue.pdf", {}, 2000), ("outro.pdf", {"titulo": "OFICIO"}, 3000),
                             ("autos.pdf", {"paginas_extra": 41}, 4000)):
            gerar_pdf(pasta / nome, corpo(troca=10), **kw)
            os.utime(pasta / nome, (mt, mt))
        self.assertEqual(self.roda("OS-2716-2099", "--gravar").returncode, 0)
        self.assertEqual(self.lido(rel)["pdf"]["nome"], "entregue.pdf")

    def test_10_todos_lista_os_casos_e_faz_o_agregado(self):
        self.caso("OS-1111-2099", minutas=[(corpo(), 1000)], pdfs=[("r.pdf", corpo(), 2000)])
        self.caso("OS-2222-2099", minutas=[(corpo(), 1000)], pdfs=[("r.pdf", corpo(troca=2), 2000)])
        self.caso("OS-3333-2099", minutas=[(corpo(), 1000)])
        self.caso("OS-4444-2099", pdfs=[("r.pdf", corpo(), 2000)])
        r = self.roda("--todos")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("casos com minuta e PDF: 2 | casos com minuta e sem PDF: 1", r.stdout)
        self.assertIn(">= 80%: 1 de 2", r.stdout)
        self.assertEqual(sum(l.startswith("OS-") for l in r.stdout.splitlines()), 2)
        self.assertFalse((self.ws / "casos" / "OS-1111-2099" / "03-relatorios" / "medicao-entrega.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
