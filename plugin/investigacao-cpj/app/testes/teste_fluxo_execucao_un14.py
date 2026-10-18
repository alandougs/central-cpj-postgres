"""Teste UN14: python -X utf8 app/testes/teste_fluxo_execucao_un14.py.

Reservas, encadeamento, cancelamento e recuperação sobre o Plantão e a fila de extração existentes.
Somente workspace temporário, agentes simulados e provedor falso que conta chamadas.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import fluxo_execucao as FX  # noqa: E402
import plantao as PL  # noqa: E402

CASO = "OS-0001-2099"


class Queda(BaseException):
    """Simula a morte do processo: não é capturada por `except Exception`."""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un14-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        self.F = FX.Fluxos(self.ws)
        self.F.migrar()

    def sql(self, q, p=()):
        c = sqlite3.connect(self.ws / "config" / "plantao.sqlite")
        try:
            return c.execute(q, p).fetchall()
        finally:
            c.close()

    def etapa(self, execucao_id, nome):
        return [e for e in self.F.obter(execucao_id)["etapas"] if e["etapa"] == nome][-1]


class Plantao(Base):
    def setUp(self):
        super().setUp()
        self.pl = PL.Plantao(str(self.ws))

    def agente(self, nome, tipo="simulado"):
        self.pl.registrar(nome, tipo, "auto", aprovado=True)

    def execucao_do_pedido(self, pid):
        et = self.F.etapa_do_pedido(pid)
        self.assertIsNotNone(et, "pedido sem etapa correlacionada")
        return et


class TesteReservas(Plantao):
    def test_dois_workers_uma_etapa(self):
        ex = self.F.criar(CASO, "op", "k1")
        e = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "o1", "a.pdf")
        barreira, resultados = threading.Barrier(8), []

        def worker(i):
            barreira.wait()
            resultados.append((i, self.F.reservar(e["id"], f"w{i}", 60)))

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        vencedores = [(i, r) for i, r in resultados if r is not None]
        self.assertEqual(len(vencedores), 1)
        dono = f"w{vencedores[0][0]}"
        self.assertEqual(self.sql("SELECT dono FROM fluxos_reservas"), [(dono,)])
        self.assertEqual(self.etapa(ex["id"], "extracao")["estado"], "em_execucao")
        for i in range(8):
            if f"w{i}" != dono:
                self.assertFalse(self.F.reserva_valida(e["id"], f"w{i}"))
                with self.assertRaises(FX.ReservaPerdida):
                    self.F.atualizar_reservado(e["id"], f"w{i}", 2, "concluida")

    def test_dois_agentes_um_pedido_no_plantao(self):
        self.agente("A1"), self.agente("A2")
        pid = self.pl.enfileirar(CASO, "revisar", "op")
        barreira, jobs = threading.Barrier(2), []

        def worker(nome):
            barreira.wait()
            jobs.append((nome, self.pl.reivindicar(nome)))

        ts = [threading.Thread(target=worker, args=(n,)) for n in ("A1", "A2")]
        [t.start() for t in ts]
        [t.join() for t in ts]
        ganhou = [n for n, j in jobs if j]
        self.assertEqual(len(ganhou), 1)
        et = self.execucao_do_pedido(pid)
        self.assertEqual(et["estado"], "em_execucao")
        self.assertEqual(self.sql("SELECT dono FROM fluxos_reservas WHERE etapa_id=?", (et["id"],)), [(ganhou[0],)])

    def test_reserva_expirada_nao_autoriza_gravar_resultado(self):
        ex = self.F.criar(CASO, "op", "k1")
        e = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "o1", "a.pdf")
        r = self.F.reservar(e["id"], "w1", 0.05)
        time.sleep(0.12)
        self.assertFalse(self.F.reserva_valida(e["id"], "w1"))
        with self.assertRaises(FX.ReservaPerdida):
            self.F.atualizar_reservado(e["id"], "w1", r["versao"], "concluida")
        self.assertEqual(self.etapa(ex["id"], "extracao")["estado"], "em_execucao")


class TesteCancelamento(Plantao):
    def test_cancelar_impede_proxima(self):
        self.agente("A1")
        pid = self.pl.enfileirar(CASO, "completo", "op")
        ids = [r[0] for r in self.sql("SELECT id FROM pedidos ORDER BY ordem")]
        self.assertEqual(len(ids), 4)
        self.assertTrue(self.pl.cancelar(pid))
        self.assertEqual([r[0] for r in self.sql("SELECT estado FROM pedidos ORDER BY ordem")], ["cancelada"] * 4)
        estados = [self.execucao_do_pedido(i)["estado"] for i in ids]
        self.assertEqual(estados, ["cancelada"] * 4)
        self.assertEqual(self.F.proximas(), [])
        self.assertIsNone(self.pl.reivindicar("A1"))

    def test_cancelamento_de_grupo_preserva_resultado_ja_produzido(self):
        self.agente("A1")
        self.pl.enfileirar(CASO, "completo", "op")
        job = self.pl.reivindicar("A1")
        self.pl.concluir(job["id"], "A1", {"resumo": "ficticio"})
        segundo = self.sql("SELECT id FROM pedidos WHERE depende_de=?", (job["id"],))[0][0]
        self.assertTrue(self.pl.cancelar(segundo))
        self.assertEqual(self.sql("SELECT estado FROM pedidos WHERE id=?", (job["id"],)), [("concluida",)])
        self.assertEqual(self.execucao_do_pedido(job["id"])["estado"], "concluida")
        self.assertEqual(self.execucao_do_pedido(segundo)["estado"], "cancelada")
        self.assertIsNone(self.pl.reivindicar("A1"))

    def test_cancelar_execucao_pelo_registro_cancela_o_pedido(self):
        self.agente("A1")
        pid = self.pl.enfileirar(CASO, "revisar", "op")
        et = self.execucao_do_pedido(pid)
        self.F.cancelar_execucao(et["execucao_id"], motivo="operador")
        self.assertEqual(self.sql("SELECT estado, cancelar FROM pedidos WHERE id=?", (pid,)), [("cancelada", 1)])
        self.assertIsNone(self.pl.reivindicar("A1"))


class TesteFalhaDeGravacao(Plantao):
    def test_falha_na_gravacao_nao_despacha(self):
        self.agente("A1")
        with mock.patch.object(FX.Fluxos, "espelhar_pedido", side_effect=sqlite3.OperationalError("disco cheio")):
            with self.assertRaises(Exception):
                self.pl.enfileirar(CASO, "completo", "op")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM pedidos WHERE estado IN ('pendente','executando')"), [(0,)])
        self.assertIsNone(self.pl.reivindicar("A1"))

    def test_falha_ao_reservar_devolve_o_pedido_sem_despachar(self):
        self.agente("A1")
        pid = self.pl.enfileirar(CASO, "revisar", "op")
        antes = self.sql("SELECT tentativas FROM pedidos WHERE id=?", (pid,))
        with mock.patch.object(FX.Fluxos, "espelhar_pedido", side_effect=sqlite3.OperationalError("bloqueado")):
            self.assertIsNone(self.pl.reivindicar("A1"))
        self.assertEqual(self.sql("SELECT estado, agente, tentativas FROM pedidos WHERE id=?", (pid,)),
                         [("pendente", None, antes[0][0])])
        self.assertIn("coordenação", self.pl.pedido(pid)["detalhe"] or "")
        self.assertEqual(self.sql("SELECT estado FROM agentes WHERE nome='A1'"), [("ocioso",)])
        job = self.pl.reivindicar("A1")      # recuperado o registro, o despacho acontece
        self.assertEqual(job["id"], pid)


class TesteQuedaNaoRepeteApi(Plantao):
    def _preparar(self):
        rel = self.ws / "casos" / CASO / "03-relatorios"
        rel.mkdir(parents=True)
        (rel / "minuta-v01.md").write_text("Minuta fictícia", encoding="utf-8")
        self.agente("API-1", "openai-api")
        self.pid = self.pl.enfileirar(CASO, "revisar", "op")
        self.job = self.pl.reivindicar("API-1")
        self.chamadas = []

        def provedor(pl, job, nome, tipo):
            self.chamadas.append(job["_etapa"]["id"])
            (rel / "revisao-v01.md").write_text("Resultado: 1 sustentadas · 0 parciais · 0 não localizadas · 0 contraditórias",
                                                encoding="utf-8")
            return {"resumo": "ficticio", "log": ""}
        return provedor

    def test_queda_apos_resposta_nao_repete_api(self):
        provedor = self._preparar()
        with mock.patch.object(PL, "_executar_sessao", provedor), \
                mock.patch.object(FX.Fluxos, "registrar_resultado", side_effect=Queda()):
            with self.assertRaises(Queda):
                PL.executar_pedido(self.pl, self.job, "API-1", "openai-api")
        self.assertEqual(len(self.chamadas), 1)
        # o agente deixou de responder: o Plantão recolhe o pedido
        self.sql("SELECT 1")
        c = sqlite3.connect(self.ws / "config" / "plantao.sqlite")
        c.execute("UPDATE agentes SET visto_em='2000-01-01T00:00:00' WHERE nome='API-1'")
        c.commit(), c.close()
        self.agente("API-2", "openai-api")
        self.assertIsNone(self.pl.reivindicar("API-2"))        # nada é redistribuído
        p = self.pl.pedido(self.pid)
        self.assertEqual(p["estado"], "erro")
        self.assertIn("incert", p["erro"].lower())
        et = self.execucao_do_pedido(self.pid)
        self.assertEqual(et["estado"], "aguardando_operador")
        self.assertEqual(len(self.chamadas), 1)                # a API nunca foi chamada de novo
        pend = [x for x in self.F.listar([CASO])["itens"][0]["pendencias"] if x["tipo"] == "aguardando_operador"]
        self.assertEqual(len(pend), 1)

    def test_nova_execucao_do_mesmo_pedido_com_intencao_aberta_nao_chama_api(self):
        provedor = self._preparar()
        et = self.execucao_do_pedido(self.pid)
        plano = PL.plano_etapas(str(self.ws), self.job)
        chave = f"{self.pid}:{plano[0]['id']}:openai-api"
        self.F.registrar_intencao(et["id"], "API-1", chave)
        with mock.patch.object(PL, "_executar_sessao", provedor):
            with self.assertRaises(FX.ResultadoIncerto):
                PL.executar_pedido(self.pl, self.job, "API-1", "openai-api")
        self.assertEqual(self.chamadas, [])

    def test_resultado_registrado_e_reaproveitado_sem_nova_chamada(self):
        provedor = self._preparar()
        with mock.patch.object(PL, "_executar_sessao", provedor):
            PL.executar_pedido(self.pl, self.job, "API-1", "openai-api")
            self.assertEqual(len(self.chamadas), 1)
            c = sqlite3.connect(self.ws / "config" / "plantao.sqlite")
            c.execute("DELETE FROM etapas_pedido")     # checkpoint do plano perdido; resultado externo ficou registrado
            c.commit(), c.close()
            PL.executar_pedido(self.pl, self.job, "API-1", "openai-api")
        self.assertEqual(len(self.chamadas), 1)


class TesteInicializacao(Plantao):
    def test_reconciliacao_na_inicializacao(self):
        ex = self.F.criar(CASO, "op", "k1")
        a = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "o1", "a.pdf")
        b = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "o2", "b.pdf")
        ra, rb = self.F.reservar(a["id"], "morto-1", 60), self.F.reservar(b["id"], "morto-2", 60)
        self.F.registrar_intencao(b["id"], "morto-2", "chamada-externa-b")        # sem resultado
        self.sql("SELECT 1")
        c = sqlite3.connect(self.ws / "config" / "plantao.sqlite")
        c.execute("DELETE FROM fluxos_reservas")                                   # processo caiu: reservas perdidas
        c.commit(), c.close()
        res = self.F.reconciliar_inicializacao()
        self.assertEqual(res, {"incertas": 1, "retomadas": 1, "alinhadas": 0})
        etapas = self.F.obter(ex["id"])["etapas"]
        por_doc = {}
        for e in etapas:
            por_doc.setdefault(e["documento"], []).append((e["tentativa"], e["estado"]))
        self.assertEqual(sorted(por_doc["a.pdf"]), [(1, "falhou"), (2, "na_fila")])
        self.assertEqual(por_doc["b.pdf"], [(1, "aguardando_operador")])
        self.assertEqual(self.F.reconciliar_inicializacao(), {"incertas": 0, "retomadas": 0, "alinhadas": 0})   # idempotente
        # só o operador libera a etapa incerta
        eb = [e for e in etapas if e["documento"] == "b.pdf"][0]
        with self.assertRaises(FX.TransicaoInvalida):
            self.F.atualizar(eb["id"], eb["versao"], "na_fila")
        self.F.reconciliar(eb["id"], eb["versao"], "na_fila", "conferido no provedor: sem cobrança")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM fluxos_intencoes WHERE etapa_id=? AND resultado IS NULL", (eb["id"],)), [(0,)])


class TesteDependencia(Plantao):
    def test_prioridade_respeita_dependencia(self):
        baixa = self.F.criar("OS-0002-2099", "op", "k", prioridade=1)
        alta = self.F.criar(CASO, "op", "k", prioridade=9)
        b_an = self.F.vincular_etapa(baixa["id"], "analise", "tarefa", "b1")
        a_an = self.F.vincular_etapa(alta["id"], "analise", "tarefa", "a1")
        a_rel = self.F.vincular_etapa(alta["id"], "relatorio", "tarefa", "a2")
        ordem = [e["id"] for e in self.F.proximas()]
        self.assertEqual(ordem, [a_an["id"], b_an["id"]])          # relatório da prioridade alta ainda não é elegível
        self.assertIsNone(self.F.reservar(a_rel["id"], "w", 60))
        r = self.F.reservar(a_an["id"], "w", 60)
        self.F.atualizar_reservado(a_an["id"], "w", r["versao"], "concluida", 100)
        ordem = [e["id"] for e in self.F.proximas()]
        self.assertEqual(ordem, [a_rel["id"], b_an["id"]])         # liberado, e passa à frente da prioridade baixa

    def test_dependencia_do_plantao_continua_valendo(self):
        self.agente("A1")
        self.pl.enfileirar(CASO, "completo", "op")
        j1 = self.pl.reivindicar("A1")
        self.assertEqual(j1["acao"], "analisar")
        self.pl.sinal("A1", "ocioso")
        self.assertIsNone(self.pl.reivindicar("A1"))               # ocupado e dependentes bloqueados
        self.pl.concluir(j1["id"], "A1", {})
        j2 = self.pl.reivindicar("A1")
        self.assertEqual(j2["acao"], "financeiro")


SCRIPT_EXTRACAO = textwrap.dedent(r'''
    import hashlib, json, os, sys, threading, time
    ws = sys.argv[1]
    os.environ["CPJ_WORKSPACE"] = ws
    os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
    sys.path.insert(0, sys.argv[2])
    from rotas import comum as K
    chamadas = []
    def falso(trab, app_logger=None):
        chamadas.append(trab["doc"])
        K.atualizar_trabalho(trab["caso"], trab["doc"], status="concluido", etapa="concluído", progresso=100)
    K.processar = falso
    threading.Thread(target=K.trabalhador, daemon=True).start()
    K.retomar_pendentes()
    K.fila.join()
    time.sleep(0.2)
    proc = K.ler_proc("OS-0001-2099")
    print(json.dumps({"chamadas": sorted(chamadas), "status": {t["doc"]: t["status"] for t in proc["trabalhos"]}}))
''')


class TesteCheckpointExtracao(Base):
    def test_checkpoint_retoma_sem_reextrair_pronto(self):
        caso = self.ws / "casos" / CASO
        (caso / "00-originais").mkdir(parents=True)
        (caso / "01-extracao" / "pronto").mkdir(parents=True)
        (caso / "caso.json").write_text(json.dumps({"id": CASO, "status": "em_analise"}), encoding="utf-8")
        saida = caso / "01-extracao" / "pronto" / "transcricao.md"
        saida.write_text("## Página 1\nTexto fictício já extraído", encoding="utf-8")
        hash_antes = saida.read_bytes()
        trabalhos = [
            {"doc": "pronto", "arquivo": "pronto.pdf", "status": "concluido", "progresso": 100, "enfileirado": "2099-01-01T10:00:00"},
            {"doc": "caiu", "arquivo": "caiu.pdf", "status": "processando", "progresso": 40, "enfileirado": "2099-01-01T10:01:00"},
            {"doc": "espera", "arquivo": "espera.pdf", "status": "na_fila", "progresso": 0, "enfileirado": "2099-01-01T10:02:00"},
        ]
        (caso / "processamento.json").write_text(json.dumps({"trabalhos": trabalhos}), encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", "-c", SCRIPT_EXTRACAO, str(self.ws), str(APP)],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dados = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(dados["chamadas"], ["caiu", "espera"])                # o pronto não é extraído de novo
        self.assertEqual(dados["status"], {"pronto": "concluido", "caiu": "concluido", "espera": "concluido"})
        self.assertEqual(saida.read_bytes(), hash_antes)
        etapas = {e["documento"]: e for e in self._etapas_extracao()}
        self.assertEqual({d: e["estado"] for d, e in etapas.items() if d != "pronto.pdf"},
                         {"caiu.pdf": "concluida", "espera.pdf": "concluida"})
        self.assertNotIn("pronto.pdf", {d for d, e in etapas.items() if e["tentativa"] > 1})

    def _etapas_extracao(self):
        itens = self.F.listar([CASO])["itens"]
        out = []
        for it in itens:
            out += [e for e in self.F.obter(it["execucao_id"])["etapas"] if e["etapa"] == "extracao"]
        return out


if __name__ == "__main__":
    unittest.main(verbosity=2)
