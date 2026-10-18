"""Teste UN15: python -X utf8 app/testes/teste_fila_unificada_un15.py.

Contrato `cpj-fluxos/1` (API) e painel único por O.S. Somente workspace temporário e dados fictícios.
"""
import hashlib
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from astra_fixture import AstraFixture  # noqa: E402

import fluxo_execucao as FX  # noqa: E402

HEADERS = {"X-CPJ": "1"}
HTML = '<img src=x onerror="window.__xss=1"><script>window.__xss=1</script>'


class Base(AstraFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.F = FX.Fluxos(self.ws)
        self.F.migrar()
        with closing(sqlite3.connect(self.ws / "config" / "plantao.sqlite")) as c:
            for t in ("fluxos_intencoes", "fluxos_reservas", "fluxos_etapas", "fluxos_execucoes"):
                c.execute(f"DELETE FROM {t}")
            c.commit()
        self.caso_json = self.ws / "casos" / self.caso / "caso.json"
        self.caso_antes = self.caso_json.read_bytes()
        self.addCleanup(lambda: self.assertEqual(self.caso_json.read_bytes(), self.caso_antes, "caso.json não pode mudar"))
        self.delegado = self.s.app.test_client()
        r = self.delegado.post("/api/entrar", json={"login": "leitor_ficticio", "senha": "Ficticia123"}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)

    def semear_os_com_duas_tentativas(self, caso=None, solicitante="astra_ficticio"):
        caso = caso or self.caso
        ex = self.F.criar(caso, solicitante, "k-un15")
        a = self.F.vincular_etapa(ex["id"], "extracao", "processamento", f"{caso}|doc-a|t1", "doc-a.pdf")
        r = self.F.atualizar(a["id"], a["versao"], "em_execucao", 10)
        self.F.atualizar(a["id"], r["versao"], "concluida", 100)
        b1 = self.F.vincular_etapa(ex["id"], "extracao", "processamento", f"{caso}|doc-b|t1", "doc-b.pdf")
        r = self.F.atualizar(b1["id"], b1["versao"], "em_execucao", 20)
        self.F.atualizar(b1["id"], r["versao"], "falhou", None, "erro de leitura")
        b2 = self.F.retentar(b1["id"], f"{caso}|doc-b|t2")
        r = self.F.atualizar(b2["id"], b2["versao"], "em_execucao", 5)
        r = self.F.atualizar(b2["id"], r["versao"], "aguardando_operador", None, "OCR indisponível: sem idioma por")
        return ex, a, b1, b2

    def get(self, url, cliente=None):
        return (cliente or self.client).get(url)

    def hash_banco(self):
        with closing(sqlite3.connect(self.ws / "config" / "plantao.sqlite")) as c:
            return hashlib.sha256(json.dumps([c.execute(f"SELECT * FROM {t}").fetchall()
                                              for t in ("pedidos", "fluxos_execucoes", "fluxos_etapas", "fluxos_reservas")],
                                             default=str).encode()).hexdigest()


class _Contrato:
    def test_os_com_dois_documentos_e_duas_tentativas_tem_uma_linha_e_detalhes_completos(self):
        ex, a, b1, b2 = self.semear_os_com_duas_tentativas()
        j = self.get("/api/fluxos").get_json()
        self.assertEqual(j["schema"], "cpj-fluxos/1")
        self.assertEqual(len(j["itens"]), 1)
        item = j["itens"][0]
        self.assertEqual((item["caso"], item["execucao_id"], item["estado"]), (self.caso, ex["id"], "aguardando_operador"))
        self.assertEqual(item["documentos"], ["doc-a.pdf", "doc-b.pdf"])
        self.assertIsNone(item["progresso"])                        # sem base mensurável: nada de percentual inventado
        for chave in ("caso", "execucao_id", "versao", "estado", "etapa", "progresso", "atualizado_em", "pendencias", "documentos", "acoes"):
            self.assertIn(chave, item)
        ocr = [p for p in item["pendencias"] if p["tipo"] == "aguardando_operador"]
        self.assertEqual([(p["documento"], p["detalhe"]) for p in ocr], [("doc-b.pdf", "OCR indisponível: sem idioma por")])
        detalhe = self.get(f"/api/fluxos/{ex['id']}").get_json()
        self.assertEqual([(e["documento"], e["tentativa"], e["estado"]) for e in detalhe["etapas"]],
                         [("doc-a.pdf", 1, "concluida"), ("doc-b.pdf", 1, "falhou"), ("doc-b.pdf", 2, "aguardando_operador")])
        self.assertEqual(detalhe["etapas"][2]["anterior_id"], b1["id"])
        self.assertNotIn("origem_id", json.dumps(detalhe))           # identificadores internos não saem
        caso = json.loads(self.caso_json.read_text(encoding="utf-8"))
        self.assertNotIn("entregue", json.dumps(caso).lower().replace("entregue_em_branco", ""))
        self.assertEqual(caso["status"], "recebido")                 # nenhuma entrega automática

    def test_perfil_sem_trabalho_ve_estado_mas_nao_o_texto_operacional(self):
        self.semear_os_com_duas_tentativas()
        item = self.get("/api/fluxos", self.delegado).get_json()["itens"][0]
        self.assertEqual(item["estado"], "aguardando_operador")
        self.assertTrue(all(p["detalhe"] == "" and "etapa_id" not in p for p in item["pendencias"]))
        self.assertEqual(item["acoes"], [])
        det = self.get(f"/api/fluxos/{item['execucao_id']}", self.delegado).get_json()
        self.assertTrue(all(e["detalhe"] == "" for e in det["etapas"]))

    def test_acoes_do_operador(self):
        ex, *_ = self.semear_os_com_duas_tentativas()
        item = self.get("/api/fluxos").get_json()["itens"][0]
        self.assertEqual([a["acao"] for a in item["acoes"]], ["cancelar", "reconciliar"])
        self.assertEqual(item["acoes"][0], {"acao": "cancelar", "execucao_id": ex["id"], "versao": item["versao"]})
        rec = item["acoes"][1]
        etapa = [e for e in self.get(f"/api/fluxos/{ex['id']}").get_json()["etapas"] if e["estado"] == "aguardando_operador"][0]
        self.assertEqual((rec["execucao_id"], rec["etapa_id"], rec["versao"]), (ex["id"], etapa["id"], etapa["versao"]))

    def test_listagem_e_detalhe_nao_executam_nada(self):
        ex, *_ = self.semear_os_com_duas_tentativas()
        antes = self.hash_banco()
        for _ in range(3):
            self.get("/api/fluxos")
            self.get(f"/api/fluxos/{ex['id']}")
        self.assertEqual(self.hash_banco(), antes)

    def test_caso_inacessivel_id_invalido_e_sessao(self):
        fora = self.F.criar("OS-777-2099", "alheio", "k")          # O.S. que não existe na lista autorizada
        self.F.vincular_etapa(fora["id"], "extracao", "processamento", "OS-777-2099|x|t1", "x.pdf")
        self.assertEqual([i["caso"] for i in self.get("/api/fluxos").get_json()["itens"]], [])
        self.assertEqual(self.get(f"/api/fluxos/{fora['id']}").status_code, 404)
        self.assertEqual(self.post(f"/api/fluxos/{fora['id']}/cancelar", {"versao": 1}).status_code, 404)
        self.assertEqual(self.get("/api/fluxos/nao-e-um-id").status_code, 400)
        self.assertEqual(self.get("/api/fluxos/..%2F..%2Fx").status_code in (400, 404), True)
        inexistente = "00000000-0000-4000-8000-000000000000"
        self.assertEqual(self.get(f"/api/fluxos/{inexistente}").status_code, 404)
        anonimo = self.s.app.test_client()
        self.assertEqual(anonimo.get("/api/fluxos").status_code, 401)
        self.assertEqual(anonimo.get(f"/api/fluxos/{inexistente}").status_code, 401)
        self.assertEqual(anonimo.post(f"/api/fluxos/{inexistente}/cancelar", json={"versao": 1}, headers=HEADERS).status_code, 401)

    def test_parametros_invalidos(self):
        self.semear_os_com_duas_tentativas()
        for url in ("/api/fluxos?limite=0", "/api/fluxos?limite=101", "/api/fluxos?limite=abc", "/api/fluxos?limite=-1",
                    "/api/fluxos?cursor=lixo", "/api/fluxos?estado=inexistente", "/api/fluxos?estado=na_fila,xx",
                    "/api/fluxos?cursor=" + "A" * 400):
            self.assertEqual(self.get(url).status_code, 400, url)
        self.assertEqual(self.get("/api/fluxos?limite=100").status_code, 200)
        ex = self.F.listar([self.caso])["itens"][0]["execucao_id"]
        self.assertEqual(self.get(f"/api/fluxos/{ex}?cursor=lixo").status_code, 400)
        self.assertEqual(self.get(f"/api/fluxos/{ex}?limite=0").status_code, 400)

    def test_paginacao_filtro_e_historico_antigo(self):
        self.semear_os_com_duas_tentativas(self.caso)
        outra = self.F.criar("OS-902-2099", "astra_ficticio", "k2")
        self.F.vincular_etapa(outra["id"], "extracao", "processamento", "OS-902-2099|z|t1", "z.pdf")
        with closing(sqlite3.connect(self.ws / "config" / "plantao.sqlite")) as c:     # histórico com mais de 24 h
            c.execute("UPDATE fluxos_execucoes SET criado_em='2020-01-01T00:00:00', atualizado_em='2020-01-01T00:00:00'")
            c.execute("UPDATE fluxos_etapas SET criado_em='2020-01-01T00:00:00', atualizado_em='2020-01-01T00:00:00'")
            c.commit()
        p1 = self.get("/api/fluxos?limite=1").get_json()
        self.assertEqual(len(p1["itens"]), 1)
        self.assertTrue(p1["proximo_cursor"])
        p2 = self.get("/api/fluxos?limite=1&cursor=" + p1["proximo_cursor"]).get_json()
        self.assertEqual(sorted([p1["itens"][0]["caso"], p2["itens"][0]["caso"]]), ["OS-901-2099", "OS-902-2099"])
        self.assertIsNone(p2["proximo_cursor"])
        so_ocr = self.get("/api/fluxos?estado=aguardando_operador").get_json()["itens"]
        self.assertEqual([i["caso"] for i in so_ocr], [self.caso])                # pendência antiga continua visível
        self.assertEqual(self.get("/api/fluxos?estado=falhou").get_json()["itens"], [])
        det = self.get(f"/api/fluxos/{so_ocr[0]['execucao_id']}?limite=2").get_json()
        self.assertEqual(len(det["etapas"]), 2)
        resto = self.get(f"/api/fluxos/{so_ocr[0]['execucao_id']}?limite=2&cursor={det['proximo_cursor']}").get_json()
        self.assertEqual(len(resto["etapas"]), 1)
        self.assertIsNone(resto["proximo_cursor"])

    def test_outras_execucoes_ativas_da_mesma_os_nao_escondem_pendencias(self):
        self.semear_os_com_duas_tentativas()
        nova = self.F.criar(self.caso, "astra_ficticio", "mais-nova")
        self.F.vincular_etapa(nova["id"], "analise", "plantao", "ia-fake0001")
        item = self.get("/api/fluxos").get_json()["itens"][0]
        self.assertEqual(item["execucao_id"], nova["id"])                          # linha principal = execução mais recente
        self.assertEqual(item["estado"], "aguardando_operador")                    # mas a pendência da outra aparece
        self.assertTrue(any(p["tipo"] == "aguardando_operador" and p["documento"] == "doc-b.pdf" for p in item["pendencias"]))
        self.assertEqual(sorted(i["execucao_id"] for i in item["acoes"] if i["acao"] == "cancelar"), sorted([nova["id"], item["acoes"][0]["execucao_id"]]))

    def test_textos_com_html_sao_devolvidos_como_dados(self):
        ex = self.F.criar(self.caso, "astra_ficticio", "k")
        e = self.F.vincular_etapa(ex["id"], "extracao", "processamento", "x|y|t1", HTML + ".pdf")
        r = self.F.atualizar(e["id"], e["versao"], "em_execucao")
        self.F.atualizar(e["id"], r["versao"], "falhou", None, HTML)
        resp = self.get("/api/fluxos")
        self.assertTrue(resp.content_type.startswith("application/json"))
        self.assertEqual(resp.get_json()["itens"][0]["pendencias"][0]["detalhe"], HTML)    # devolvido sem alterar; a tela escapa

    def test_contratos_legados_continuam(self):
        self.assertEqual(self.get("/api/tarefas").status_code, 200)
        self.assertIsInstance(self.get("/api/tarefas").get_json(), list)
        fila = self.get("/api/fila").get_json()
        self.assertIn("trabalhos", fila)
        self.assertIn("idioma_ocr", fila)


class _Acoes:
    def test_acoes_rejeitam_json_que_nao_seja_objeto_sem_alterar_estado(self):
        ex, _, _, alvo = self.semear_os_com_duas_tentativas()
        urls = (f"/api/fluxos/{ex['id']}/cancelar",
                f"/api/fluxos/{ex['id']}/etapas/{alvo['id']}/reconciliar")
        banco_antes = self.hash_banco()
        checkpoint = self.ws / "casos" / self.caso / "processamento.json"
        checkpoint_antes = checkpoint.read_bytes() if checkpoint.exists() else None
        for url in urls:
            for corpo in (None, False, True, 0, 1, "", "invalido", [], [1]):
                with self.subTest(acao=url.rsplit("/", 1)[-1], corpo=corpo):
                    try:
                        resp = self.client.post(url, data=json.dumps(corpo),
                                                content_type="application/json", headers=HEADERS)
                        self.assertEqual(resp.status_code, 400)
                        self.assertIsInstance(resp.get_json().get("erro"), str)
                    finally:
                        self.assertEqual(self.hash_banco(), banco_antes)
                        self.assertEqual(checkpoint.read_bytes() if checkpoint.exists() else None, checkpoint_antes)

    def test_csrf_exige_cabecalho(self):
        ex, *_ = self.semear_os_com_duas_tentativas()
        v = self.get("/api/fluxos").get_json()["itens"][0]["versao"]
        self.assertEqual(self.client.post(f"/api/fluxos/{ex['id']}/cancelar", json={"versao": v}).status_code, 403)
        self.assertEqual(self.F.obter(ex["id"])["estado"], "aguardando_operador")

    def test_cancelamento_obsoleto_conflita_e_correto_cancela_preservando_concluidos(self):
        ex, a, b1, b2 = self.semear_os_com_duas_tentativas()
        v = self.get("/api/fluxos").get_json()["itens"][0]["versao"]
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/cancelar", {"versao": v - 1}).status_code, 409)
        self.assertEqual(self.F.obter(ex["id"])["estado"], "aguardando_operador")           # nada mudou
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/cancelar", {}).status_code, 400)
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/cancelar", {"versao": "1"}).status_code, 400)
        r = self.post(f"/api/fluxos/{ex['id']}/cancelar", {"versao": v})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        etapas = {e["id"]: e["estado"] for e in self.F.obter(ex["id"])["etapas"]}
        self.assertEqual(etapas, {a["id"]: "concluida", b1["id"]: "falhou", b2["id"]: "cancelada"})
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/cancelar", {"versao": v}).status_code, 409)   # versão antiga

    def test_perfil_sem_trabalho_so_cancela_o_que_solicitou(self):
        ex, *_ = self.semear_os_com_duas_tentativas(solicitante="astra_ficticio")
        v = self.get("/api/fluxos").get_json()["itens"][0]["versao"]
        r = self.delegado.post(f"/api/fluxos/{ex['id']}/cancelar", json={"versao": v}, headers=HEADERS)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.F.obter(ex["id"])["estado"], "aguardando_operador")
        proprio = self.F.criar("OS-902-2099", "leitor_ficticio", "k-proprio")
        et = self.F.vincular_etapa(proprio["id"], "extracao", "processamento", "OS-902-2099|p|t1", "p.pdf")
        item = [i for i in self.get("/api/fluxos", self.delegado).get_json()["itens"] if i["caso"] == "OS-902-2099"][0]
        self.assertEqual([a["acao"] for a in item["acoes"]], ["cancelar"])
        r = self.delegado.post(f"/api/fluxos/{proprio['id']}/cancelar", json={"versao": item["versao"]}, headers=HEADERS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.F.obter(proprio["id"])["etapas"][0]["estado"], "cancelada")

    def test_cancelar_extracao_na_fila_marca_o_checkpoint_sem_apagar_nada(self):
        proc = self.ws / "casos" / self.caso / "processamento.json"
        proc.write_text(json.dumps({"trabalhos": [
            {"doc": "doc-q", "arquivo": "q.pdf", "status": "na_fila", "enfileirado": "2099-01-01T10:00:00", "progresso": 0},
            {"doc": "doc-r", "arquivo": "r.pdf", "status": "concluido", "enfileirado": "2099-01-01T09:00:00", "progresso": 100}]}), encoding="utf-8")
        ex = self.F.criar(self.caso, "astra_ficticio", "k")
        self.F.vincular_etapa(ex["id"], "extracao", "processamento", f"{self.caso}|doc-q|2099-01-01T10:00:00", "q.pdf")
        v = self.get("/api/fluxos").get_json()["itens"][0]["versao"]
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/cancelar", {"versao": v}).status_code, 200)
        trabalhos = {t["doc"]: t["status"] for t in json.loads(proc.read_text(encoding="utf-8"))["trabalhos"]}
        self.assertEqual(trabalhos, {"doc-q": "cancelado", "doc-r": "concluido"})

    def test_reconciliar_exige_motivo_perfil_e_versao(self):
        ex, a, b1, b2 = self.semear_os_com_duas_tentativas()
        det = self.get(f"/api/fluxos/{ex['id']}").get_json()
        alvo = [e for e in det["etapas"] if e["estado"] == "aguardando_operador"][0]
        url = f"/api/fluxos/{ex['id']}/etapas/{alvo['id']}/reconciliar"
        corpo = {"versao": alvo["versao"], "estado": "na_fila", "motivo": "conferido no provedor: nenhuma cobrança"}
        r = self.delegado.post(url, json=corpo, headers=HEADERS)
        self.assertEqual(r.status_code, 403)
        for ruim in ({**corpo, "motivo": ""}, {**corpo, "motivo": "x" * 400}, {**corpo, "estado": "concluida"}, {**corpo, "versao": "1"}):
            self.assertEqual(self.post(url, ruim).status_code, 400, ruim)
        self.assertEqual(self.post(url, {**corpo, "versao": alvo["versao"] - 1}).status_code, 409)
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/etapas/{a['id']}/reconciliar", corpo).status_code, 409)   # etapa concluída
        outra = "00000000-0000-4000-8000-000000000000"
        self.assertEqual(self.post(f"/api/fluxos/{ex['id']}/etapas/{outra}/reconciliar", corpo).status_code, 404)
        self.assertEqual(self.F.obter(ex["id"])["etapas"][2]["estado"], "aguardando_operador")
        r = self.post(url, corpo)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(self.F.obter(ex["id"])["etapas"][2]["estado"], "na_fila")


class TesteFilaUnificadaUN15(_Contrato, _Acoes, Base):
    """Uma classe só: o fixture exige um processo por servidor."""


if __name__ == "__main__":
    unittest.main(verbosity=2)
