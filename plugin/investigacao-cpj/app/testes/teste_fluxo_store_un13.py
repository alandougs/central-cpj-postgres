"""Teste UN13: python -X utf8 app/testes/teste_fluxo_store_un13.py.

Registro durável de fluxos (O.S. -> execução -> etapa -> tentativa) em config/plantao.sqlite.
Somente workspace temporário e dados fictícios.
"""
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import fluxo_execucao as FX  # noqa: E402

CASO = "OS-0001-2099"


def uma_etapa(F, caso=CASO, chave="k1", etapa="extracao", origem_id="o1", documento="doc-a.pdf", **kw):
    ex = F.criar(caso, "op", chave, **kw)
    return ex, F.vincular_etapa(ex["id"], etapa, "processamento", origem_id, documento)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un13-")
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

    def envelhecer(self):
        antigo = "2020-01-01T00:00:00"
        c = sqlite3.connect(self.ws / "config" / "plantao.sqlite")
        try:
            c.execute("UPDATE fluxos_execucoes SET criado_em=?, atualizado_em=?", (antigo, antigo))
            c.execute("UPDATE fluxos_etapas SET criado_em=?, atualizado_em=?", (antigo, antigo))
            c.commit()
        finally:
            c.close()


class TesteCriacaoEVinculo(Base):
    def test_criar_idempotente(self):
        a = self.F.criar(CASO, "op", "k1")
        b = self.F.criar(CASO, "op", "k1")
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(a["versao"], b["versao"])
        c = self.F.criar(CASO, "op", "k2")
        self.assertNotEqual(a["id"], c["id"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM fluxos_execucoes")[0][0], 2)

    def test_criar_concorrente_gera_uma_execucao(self):
        ids, erros = [], []

        def tarefa():
            try:
                ids.append(FX.Fluxos(self.ws).criar(CASO, "op", "mesma-chave")["id"])
            except Exception as e:  # noqa: BLE001
                erros.append(e)
        ts = [threading.Thread(target=tarefa) for _ in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(erros, [])
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM fluxos_execucoes")[0][0], 1)

    def test_vinculo_unico(self):
        ex = self.F.criar(CASO, "op", "k1")
        e1 = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "OS|doc|t1", "doc.pdf")
        e2 = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "OS|doc|t1", "doc.pdf")
        self.assertEqual(e1["id"], e2["id"])
        outra = self.F.criar(CASO, "op", "k2")
        with self.assertRaises(ValueError):
            self.F.vincular_etapa(outra["id"], "extracao", "processamento", "OS|doc|t1", "doc.pdf")
        with self.assertRaises(ValueError):
            self.F.vincular_etapa(ex["id"], "etapa-inexistente", "plantao", "x")
        with self.assertRaises(ValueError):
            self.F.vincular_etapa(ex["id"], "analise", "origem-inexistente", "x")
        with self.assertRaises(KeyError):
            self.F.vincular_etapa("nao-existe", "analise", "plantao", "y")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM fluxos_etapas")[0][0], 1)


class TesteAtualizacao(Base):
    def test_versao_obsoleta_nao_sobrescreve(self):
        ex, e = uma_etapa(self.F)
        r1 = self.F.atualizar(e["id"], e["versao"], "em_execucao", 10, "lendo")
        self.assertGreater(r1["versao"], e["versao"])
        with self.assertRaises(FX.ConflitoVersao):
            self.F.atualizar(e["id"], e["versao"], "em_execucao", 55, "obsoleta")
        atual = self.F.obter(ex["id"])["etapas"][0]
        self.assertEqual((atual["estado"], atual["progresso"], atual["detalhe"]), ("em_execucao", 10.0, "lendo"))
        self.assertEqual(atual["versao"], r1["versao"])

    def test_duas_escritas_concorrentes_uma_vence(self):
        ex, e = uma_etapa(self.F)
        resultados = []
        barreira = threading.Barrier(2)

        def tarefa(pct):
            barreira.wait()
            try:
                FX.Fluxos(self.ws).atualizar(e["id"], e["versao"], "em_execucao", pct)
                resultados.append("ok")
            except FX.ConflitoVersao:
                resultados.append("conflito")
        ts = [threading.Thread(target=tarefa, args=(p,)) for p in (20, 30)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sorted(resultados), ["conflito", "ok"])

    def test_transicoes_validas_e_terminais_imutaveis(self):
        ex, e = uma_etapa(self.F)
        with self.assertRaises(FX.TransicaoInvalida):
            self.F.atualizar(e["id"], e["versao"], "concluida")           # na_fila -> concluida
        with self.assertRaises(ValueError):
            self.F.atualizar(e["id"], e["versao"], "estado-desconhecido")
        r = self.F.atualizar(e["id"], e["versao"], "em_execucao", 5)
        r = self.F.atualizar(e["id"], r["versao"], "em_execucao", 50)       # progresso no mesmo estado
        r = self.F.atualizar(e["id"], r["versao"], "concluida", 100)
        with self.assertRaises(FX.TransicaoInvalida):
            self.F.atualizar(e["id"], r["versao"], "em_execucao")
        with self.assertRaises(FX.TransicaoInvalida):
            self.F.atualizar(e["id"], r["versao"], "concluida", 100)       # terminal nem no mesmo estado
        with self.assertRaises(ValueError):
            self.F.atualizar(e["id"], r["versao"], "concluida", 150)

    def test_aguardando_operador_so_sai_por_reconciliacao_explicita(self):
        ex, e = uma_etapa(self.F)
        r = self.F.atualizar(e["id"], e["versao"], "em_execucao", 40)
        r = self.F.atualizar(e["id"], r["versao"], "aguardando_operador", None, "resultado externo incerto")
        with self.assertRaises(FX.TransicaoInvalida):
            self.F.atualizar(e["id"], r["versao"], "na_fila")
        with self.assertRaises(ValueError):
            self.F.reconciliar(e["id"], r["versao"], "na_fila", "")        # exige motivo
        r = self.F.reconciliar(e["id"], r["versao"], "na_fila", "conferido: resultado não registrado")
        self.assertEqual(r["estado"], "na_fila")

    def test_retentativa_preserva_a_anterior(self):
        ex, e = uma_etapa(self.F)
        r = self.F.atualizar(e["id"], e["versao"], "em_execucao", 10)
        r = self.F.atualizar(e["id"], r["versao"], "falhou", None, "erro de leitura")
        nova = self.F.retentar(e["id"], "o1-t2")
        self.assertEqual(nova["tentativa"], 2)
        self.assertEqual(nova["anterior_id"], e["id"])
        etapas = self.F.obter(ex["id"])["etapas"]
        self.assertEqual([x["tentativa"] for x in etapas], [1, 2])
        self.assertEqual(etapas[0]["estado"], "falhou")
        with self.assertRaises(FX.TransicaoInvalida):
            self.F.retentar(nova["id"], "o1-t3")                            # etapa ativa não admite retentativa


class TesteAgregacao(Base):
    def test_fluxo_so_conclui_com_todas_as_etapas_obrigatorias(self):
        ex = self.F.criar(CASO, "op", "k1")
        ids = []
        for i, etapa in enumerate(FX.ETAPAS):
            e = self.F.vincular_etapa(ex["id"], etapa, "plantao", f"p{i}", None)
            r = self.F.atualizar(e["id"], e["versao"], "em_execucao", 1)
            r = self.F.atualizar(e["id"], r["versao"], "concluida", 100)
            ids.append(r["id"])
            esperado = "concluida" if etapa == FX.ETAPAS[-1] else "na_fila"
            self.assertEqual(self.F.obter(ex["id"])["estado"], esperado, etapa)

    def test_pendente_antigo_nao_expira(self):
        ex = self.F.criar(CASO, "op", "k1")
        e1 = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "OS|doc-a|t1", "doc-a.pdf")
        e2 = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "OS|doc-b|t1", "doc-b.pdf")
        r = self.F.atualizar(e1["id"], e1["versao"], "em_execucao", 3)
        self.F.atualizar(e1["id"], r["versao"], "aguardando_operador", None, "OCR indisponível: sem idioma por")
        self.envelhecer()
        item = self.F.listar([CASO])["itens"][0]
        self.assertEqual(item["execucao_id"], ex["id"])
        self.assertEqual(item["estado"], "aguardando_operador")
        tipos = {(p["tipo"], p.get("documento")) for p in item["pendencias"]}
        self.assertIn(("aguardando_operador", "doc-a.pdf"), tipos)
        self.assertEqual(item["documentos"], ["doc-a.pdf", "doc-b.pdf"])
        self.assertEqual(self.F.obter(ex["id"])["etapas"][1]["estado"], "na_fila")  # doc-b segue visível

    def test_execucao_ativa_mais_recente_e_historico_acessivel(self):
        antiga = self.F.criar(CASO, "op", "antiga")
        for i, etapa in enumerate(FX.ETAPAS):
            e = self.F.vincular_etapa(antiga["id"], etapa, "plantao", f"a{i}")
            r = self.F.atualizar(e["id"], e["versao"], "em_execucao")
            self.F.atualizar(e["id"], r["versao"], "concluida", 100)
        nova = self.F.criar(CASO, "op", "nova")
        self.F.vincular_etapa(nova["id"], "recebimento", "plantao", "n0")
        item = self.F.listar([CASO])["itens"][0]
        self.assertEqual(item["execucao_id"], nova["id"])
        self.assertEqual(self.F.obter(antiga["id"])["estado"], "concluida")   # anterior continua acessível
        self.assertEqual(self.F.obter("inexistente"), None)

    def test_listar_filtra_casos_ordena_e_pagina(self):
        for i in range(5):
            self.F.criar(f"OS-{i:04d}-2099", "op", "k", prioridade=1 if i == 3 else 0)
        self.assertEqual(self.F.listar([])["itens"], [])
        permitidos = [f"OS-{i:04d}-2099" for i in (0, 1, 3, 4)]
        vistos, cursor = [], None
        while True:
            pag = self.F.listar(permitidos, limite=2, cursor=cursor)
            vistos += [x["caso"] for x in pag["itens"]]
            cursor = pag["proximo_cursor"]
            if not cursor:
                break
        self.assertEqual(vistos, ["OS-0003-2099", "OS-0000-2099", "OS-0001-2099", "OS-0004-2099"])
        self.assertNotIn("OS-0002-2099", vistos)
        with self.assertRaises(ValueError):
            self.F.listar(permitidos, cursor="lixo")
        with self.assertRaises(ValueError):
            self.F.listar(permitidos, limite=0)


class TesteMigracao(Base):
    def test_migracao_interrompida_reexecutavel(self):
        tmp = tempfile.TemporaryDirectory(prefix="cpj-un13-mig-")
        self.addCleanup(tmp.cleanup)
        ws = Path(tmp.name)
        (ws / "config").mkdir()
        db = ws / "config" / "plantao.sqlite"
        c = sqlite3.connect(db)
        c.execute("CREATE TABLE pedidos(id TEXT PRIMARY KEY, caso TEXT, estado TEXT, criado_em TEXT)")
        c.execute("INSERT INTO pedidos VALUES('ia-1','OS-1-2099','pendente','2026-01-01T00:00:00')")
        c.commit()
        c.close()
        F = FX.Fluxos(ws)
        original = FX.Fluxos._registrar_migracao

        def falha(self_, con, versao):
            raise RuntimeError("queda simulada antes de registrar a migração")
        FX.Fluxos._registrar_migracao = falha
        try:
            with self.assertRaises(RuntimeError):
                F.migrar()
        finally:
            FX.Fluxos._registrar_migracao = original
        c = sqlite3.connect(db)
        try:
            tabelas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("fluxos_execucoes", tabelas, "migração parcial deve ser desfeita")
            self.assertEqual(c.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 1)
        finally:
            c.close()
        F.migrar()
        F.migrar()  # idempotente
        c = sqlite3.connect(db)
        try:
            self.assertEqual([r[0] for r in c.execute("SELECT versao FROM fluxos_migracoes ORDER BY versao")],
                             [v for v, _ in FX.MIGRACOES])
            self.assertEqual(c.execute("SELECT estado FROM pedidos").fetchone()[0], "pendente")
        finally:
            c.close()


class TesteImportacaoLegado(Base):
    def _legado(self):
        from plantao import Plantao
        Plantao(str(self.ws))      # cria as tabelas; o pedido legado é gravado direto, como uma versão anterior faria
        pid = "ia-legado0001"
        c = sqlite3.connect(self.ws / "config" / "plantao.sqlite")
        try:
            c.execute("INSERT INTO pedidos(id,caso,acao,solicitante,estado,criado_em,grupo,ordem) VALUES(?,?,?,?,?,?,?,1)",
                      (pid, CASO, "analisar", "op", "pendente", "2099-01-01T09:59:00", "fluxo-legado"))
            c.commit()
        finally:
            c.close()
        caso = self.ws / "casos" / CASO
        caso.mkdir(parents=True)
        proc = {"trabalhos": [
            {"doc": "d1", "arquivo": "a.pdf", "status": "concluido", "enfileirado": "2099-01-01T10:00:00", "progresso": 100},
            {"doc": "d2", "arquivo": "b.pdf", "status": "processando", "enfileirado": "2099-01-01T10:01:00", "progresso": 40},
            {"doc": "d3", "arquivo": "c.pdf", "status": "erro", "enfileirado": "2099-01-01T10:02:00", "erro": "falha"},
        ]}
        (caso / "processamento.json").write_text(json.dumps(proc), encoding="utf-8")
        return pid, caso / "processamento.json"

    def test_importar_correlaciona_sem_disparar_nem_inventar_termino(self):
        pid, arq = self._legado()
        bytes_antes = arq.read_bytes()
        pedidos_antes = self.sql("SELECT * FROM pedidos ORDER BY id")
        res = self.F.importar_legado()
        self.assertEqual(res["etapas_importadas"], 4)
        self.assertEqual(arq.read_bytes(), bytes_antes)                       # checkpoint intocado
        self.assertEqual(self.sql("SELECT * FROM pedidos ORDER BY id"), pedidos_antes)
        item = self.F.listar([CASO])["itens"][0]
        estados = {e["documento"]: e["estado"] for e in self.F.obter(item["execucao_id"])["etapas"] if e["origem"] == "processamento"}
        self.assertEqual(estados, {"a.pdf": "concluida", "b.pdf": "em_execucao", "c.pdf": "falhou"})
        ped = [e for e in self.F.obter(item["execucao_id"])["etapas"] if e["origem"] == "plantao"][0]
        self.assertEqual(ped["estado"], "na_fila")                           # pedido pendente não vira concluído
        self.assertEqual(ped["origem_id"], pid)
        # idempotente
        res2 = self.F.importar_legado()
        self.assertEqual(res2["etapas_importadas"], 0)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM fluxos_etapas")[0][0], 4)


class TestePlantaoMigra(Base):
    def test_pedido_novo_ja_nasce_correlacionado(self):
        from plantao import Plantao
        pid = Plantao(str(self.ws)).enfileirar(CASO, "analisar", "op")
        et = self.F.etapa_do_pedido(pid)
        self.assertEqual((et["etapa"], et["estado"], et["origem_id"]), ("analise", "na_fila", pid))
        self.assertEqual(self.F.importar_legado()["etapas_importadas"], 0)      # nada a importar: já está registrado

    def test_plantao_aplica_migracao_e_preserva_pedidos(self):
        from plantao import Plantao
        pl = Plantao(str(self.ws))
        pid = pl.enfileirar(CASO, "analisar", "op")
        antes = self.sql("SELECT * FROM pedidos ORDER BY id")
        Plantao(str(self.ws))            # nova instância sobre banco já migrado: idempotente
        self.assertEqual(self.sql("SELECT * FROM pedidos ORDER BY id"), antes)
        self.assertEqual([r[0] for r in self.sql("SELECT versao FROM fluxos_migracoes ORDER BY versao")],
                         [v for v, _ in FX.MIGRACOES])
        self.assertEqual(self.sql("SELECT estado FROM pedidos WHERE id=?", (pid,))[0][0], "pendente")


if __name__ == "__main__":
    unittest.main(verbosity=2)
