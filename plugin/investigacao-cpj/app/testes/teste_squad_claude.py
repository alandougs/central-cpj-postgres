#!/usr/bin/env python3
"""Fluxo atual: quatro pedidos encadeados, sessões independentes e entregas verificadas.

O teste S01 antigo referenciava uma API de oito subetapas ausente do histórico
versionado. Esta suíte verifica o contrato usado por enfileirar/completo/esteira;
não declara suporte a blocos de análise paralelos nem ajuste automático.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plantao as PL

SIM = r'''
import json,os
from pathlib import Path
c=Path(os.environ["CPJ_WORKSPACE"])/"casos"/os.environ["CPJ_CASO"]
a=os.environ["CPJ_ACAO"]
if a=="analisar":
    (c/"02-analise/ficha-caso.md").write_text("Análise fictícia sem autoria atribuída.")
    (c/"02-analise/pessoas.csv").write_text("nome;mae;cpf\n")
elif a=="financeiro":
    (c/"02-analise/fluxo-financeiro.md").write_text("Sem transações nos autos fictícios.")
    (c/"02-analise/fluxo-financeiro.csv").write_text("seq;data;valor;fonte_pag\n")
elif a=="relatorio":
    (c/"03-relatorios/minuta-v01.md").write_text("## RESUMO DOS FATOS\nFatos fictícios.\n## DILIGÊNCIAS REALIZADAS\nConferência fictícia.\n## CONCLUSÃO\nSem autoria atribuída.\n")
elif a=="revisar":
    (c/"03-relatorios/revisao-v01.md").write_text("Revisão independente: fatos fictícios conferidos.")
print(json.dumps({"type":"result","subtype":"success","result":"sessão "+a}))
'''


class SquadAtual(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-squad-atual-")
        self.ws = Path(self.tmp.name)
        self.caso = "OS-777-2099"
        self.base = self.ws / "casos" / self.caso
        for p in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (self.base / p).mkdir(parents=True)
        (self.base / "caso.json").write_text(json.dumps({"id": self.caso, "status": "recebido", "datas": {}, "relatorios": []}))
        root = Path(__file__).resolve().parents[4]
        shutil.copytree(root / "modelos", self.ws / "modelos")
        self.env = patch.dict(os.environ, {"CPJ_WORKSPACE": str(self.ws), "CPJ_PLANTAO_SIMULADO": "1", "CPJ_PLANTAO_SIMULADO_CMD": SIM})
        self.env.start()
        self.pl = PL.Plantao(str(self.ws))
        self.pl.registrar("Sim", "simulado", "auto", aprovado=True)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def executar(self, job):
        antes = PL.snapshot_entregas(str(self.ws), self.caso)
        res = PL.executar_pedido(self.pl, job, "Sim", "simulado")
        res.update(PL.pos_processar(str(self.ws), self.caso, job["acao"], antes))
        self.pl.concluir(job["id"], "Sim", res)
        return res

    def test_fluxo_completo_quatro_sessoes_e_docx(self):
        pid = self.pl.enfileirar(self.caso, "completo", "teste")
        grupo = self.pl.pedido(pid)["grupo"]
        jobs = sorted(self.pl.pedidos(), key=lambda j: j["ordem"])
        self.assertEqual([j["acao"] for j in jobs], ["analisar", "financeiro", "relatorio", "revisar"])
        self.assertTrue(all(j["grupo"] == grupo for j in jobs))
        for anterior, seguinte in zip(jobs, jobs[1:]):
            self.assertEqual(seguinte["depende_de"], anterior["id"])
        logs = []
        for esperado in jobs:
            job = self.pl.reivindicar("Sim")
            self.assertEqual(job["id"], esperado["id"])
            self.assertIsNone(self.pl.reivindicar("Sim"))
            res = self.executar(job)
            logs.append(res["log"])
        self.assertEqual(len(set(logs)), 4)
        self.assertIsNone(self.pl.reivindicar("Sim"))
        self.assertTrue(all(j["estado"] == "concluida" and j["iniciado_em"] and j["fim"] for j in self.pl.pedidos()))
        self.assertTrue((self.base / "03-relatorios" / f"RELATORIO-{self.caso}-v01.docx").is_file())
        self.assertTrue((self.base / "03-relatorios/revisao-v01.md").is_file())

    def test_prompts_separam_redacao_e_revisao(self):
        job = {"id": "ia-teste", "caso": self.caso, "acao": "relatorio", "solicitante": "teste", "observacoes": ""}
        autor = PL.montar_prompt(job, str(self.ws))
        revisor = PL.montar_prompt(dict(job, acao="revisar"), str(self.ws))
        self.assertIn("NÃO revise a própria minuta", autor)
        self.assertIn("Não altere a minuta", revisor)
        self.assertIn("revisor-de-relatorio", revisor)
        self.assertIn("NÃO são fonte de fatos", revisor)

    def test_falha_sem_entrega_cancela_dependencias_e_libera_novo_fluxo(self):
        self.pl.enfileirar(self.caso, "esteira", "teste")
        job = self.pl.reivindicar("Sim")
        with self.assertRaisesRegex(RuntimeError, "ficha-caso.md"):
            PL.pos_processar(str(self.ws), self.caso, "analisar")
        self.pl.falhar(job["id"], "Sim", "ficha-caso.md ausente")
        self.assertEqual(sorted(j["estado"] for j in self.pl.pedidos()), ["cancelada"] * 3 + ["erro"])
        self.assertIsNone(self.pl.reivindicar("Sim"))
        self.pl.enfileirar(self.caso, "esteira", "teste")

    def test_entrega_antiga_nao_comprova_execucao_atual(self):
        for n in ("ficha-caso.md", "pessoas.csv"):
            (self.base / "02-analise" / n).write_text("arquivo anterior")
        antes = PL.snapshot_entregas(str(self.ws), self.caso)
        with self.assertRaisesRegex(RuntimeError, "não atualizou"):
            PL.pos_processar(str(self.ws), self.caso, "analisar", antes)

    def test_retomada_na_etapa_pendente_preserva_a_concluida(self):
        pid = self.pl.enfileirar(self.caso, "completo", "teste")
        self.executar(self.pl.reivindicar("Sim"))
        financeiro = self.pl.reivindicar("Sim")
        with self.pl._c() as c:
            c.execute("UPDATE agentes SET visto_em='2000-01-01T00:00:00' WHERE nome='Sim'")
        self.pl.registrar("Retoma", "simulado", "auto", aprovado=True)
        retomado = self.pl.reivindicar("Retoma")
        self.assertEqual(retomado["id"], financeiro["id"])
        self.assertEqual(retomado["tentativas"], 2)
        self.assertEqual(self.pl.pedido(pid)["estado"], "concluida")

    def test_cancelamento_nao_pode_concluir_e_encerra_grupo(self):
        self.pl.enfileirar(self.caso, "completo", "teste")
        job = self.pl.reivindicar("Sim")
        self.assertTrue(self.pl.cancelar(job["id"]))
        with self.assertRaisesRegex(ValueError, "cancelado"):
            self.pl.concluir(job["id"], "Sim", {"resumo": "não deve concluir"})
        self.pl.falhar(job["id"], "Sim", "cancelado")
        self.assertTrue(all(j["estado"] == "cancelada" for j in self.pl.pedidos()))

    def test_indexacao_falha_explicitamente(self):
        with patch.object(PL.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "falha fictícia")):
            with self.assertRaisesRegex(RuntimeError, "Indexação falhou"):
                PL.pos_processar(str(self.ws), self.caso, "outro")

    def test_cli_com_saida_success_e_retorno_de_erro_nao_conclui(self):
        self.pl.enfileirar(self.caso, "analisar", "teste")
        job = self.pl.reivindicar("Sim")
        cmd = "import sys;print('{\"type\":\"result\",\"subtype\":\"success\",\"result\":\"ok\"}');sys.exit(7)"
        with patch.dict(os.environ, {"CPJ_PLANTAO_SIMULADO_CMD": cmd}):
            with self.assertRaisesRegex(RuntimeError, "Agente não concluiu"):
                PL.executar_pedido(self.pl, job, "Sim", "simulado")

    def test_perda_da_reserva_interrompe_cli_silencioso(self):
        self.pl.enfileirar(self.caso, "analisar", "teste")
        job = self.pl.reivindicar("Sim")
        with patch.dict(os.environ, {"CPJ_PLANTAO_SIMULADO_CMD": "import time;time.sleep(30)"}):
            with patch.object(self.pl, "progresso", side_effect=ValueError("reserva transferida")):
                with self.assertRaisesRegex(RuntimeError, "Cancelado"):
                    PL.executar_pedido(self.pl, job, "Sim", "simulado")

    def test_agente_antigo_nao_sobrescreve_reserva_transferida(self):
        pid = self.pl.enfileirar(self.caso, "analisar", "teste")
        self.pl.reivindicar("Sim")
        original = self.pl._do_agente
        def transferir(*args):
            p = original(*args)
            with self.pl._c() as c:
                c.execute("UPDATE pedidos SET agente='Novo' WHERE id=?", (pid,))
            return p
        with patch.object(self.pl, "_do_agente", side_effect=transferir):
            with self.assertRaises(ValueError):
                self.pl.concluir(pid, "Sim", {"resumo": "antigo"})
        self.assertEqual(self.pl.pedido(pid)["estado"], "executando")
        self.assertEqual(self.pl.pedido(pid)["agente"], "Novo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
