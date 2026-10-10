"""TS06: contrato e gate reais, CLI somente simulado em workspace fictício."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plantao as PL


class ContratoEtapas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-ts06-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = self.tmp.name
        self.base = Path(self.ws) / "casos/OS-1-2026/02-analise"
        self.base.mkdir(parents=True)
        self.pl = PL.Plantao(self.ws)
        self.pl.registrar("Teste", "simulado", "auto", aprovado=True)
        for name in ("fluxo-financeiro.md", "fluxo-financeiro.csv"):
            (self.base / name).write_text("produto anterior ficticio", encoding="utf-8")
        self.pl.enfileirar("OS-1-2026", "financeiro", "usuario-ficticio")
        self.job = self.pl.reivindicar("Teste")

    def executar_simulado(self, escrever):
        script = "import json,os;from pathlib import Path;"
        if escrever:
            script += ("b=Path(os.environ['CPJ_WORKSPACE'])/'casos/OS-1-2026/02-analise';"
                       "[ (b/n).write_text('conferido e regenerado nesta execucao ficticia',encoding='utf-8') "
                       "for n in ('fluxo-financeiro.md','fluxo-financeiro.csv') ];")
        script += "print(json.dumps({'type':'result','subtype':'success','is_error':False,'result':'sessao ficticia concluida'}))"
        with patch.dict(os.environ, {"CPJ_PLANTAO_SIMULADO": "1", "CPJ_PLANTAO_SIMULADO_CMD": script}):
            return PL.executar_pedido(self.pl, self.job, "Teste", "simulado")

    def test_prompt_exige_regeneracao_nesta_execucao_com_saidas_dinamicas(self):
        etapa = {"tipo": "financeiro", "etapa": "Ficticia", "arg": {},
                 "saidas": ["02-analise/produto-dinamico.md", "02-analise/produto-dinamico.csv"]}
        prompt = PL.prompt_etapa(self.job, self.ws, etapa)
        self.assertIn("produto-dinamico.md", prompt)
        self.assertIn("produto-dinamico.csv", prompt)
        self.assertRegex(prompt, r"(?i)nesta execução.*grave.*todas.*saídas")
        self.assertIn("mesmo que já existam", prompt)
        self.assertRegex(prompt, r"(?i)não.*timestamps")

    def test_success_sem_escrever_bloqueia_e_preserva_log_e_retorno(self):
        with self.assertRaisesRegex(RuntimeError, "arquivo não atualizado"):
            self.executar_simulado(False)
        etapa = self.pl.etapas(self.job["id"])[0]
        self.assertEqual(etapa["estado"], "erro")
        self.assertIn("arquivo não atualizado", etapa["erro"])
        self.assertEqual(etapa.get("resumo"), "sessao ficticia concluida")
        self.assertTrue(etapa.get("log"), "Sessão consumida não pode sumir após o gate")
        log = Path(self.ws) / etapa["log"]
        self.assertTrue(log.is_file())
        self.assertIn('"subtype": "success"', log.read_text(encoding="utf-8"))
        self.assertEqual((self.base / "fluxo-financeiro.md").read_text(encoding="utf-8"), "produto anterior ficticio")

    def test_sessao_regenera_produtos_e_conclui_normalmente(self):
        resultado = self.executar_simulado(True)
        etapa = self.pl.etapas(self.job["id"])[0]
        self.assertEqual(etapa["estado"], "concluida")
        self.assertEqual(etapa["log"], resultado["log"])
        for name in ("fluxo-financeiro.md", "fluxo-financeiro.csv"):
            self.assertIn("regenerado nesta execucao", (self.base / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
