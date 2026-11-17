"""AS54: resultado externo incerto e cancelamento após queda; somente fixtures locais."""
import io
import http.client
import json
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import executores_llm as EL
import fluxo_execucao as FX
import plantao as PL


class ExecucaoExterna(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-as54-")
        self.addCleanup(self.temp.cleanup)
        self.ws = self.temp.name
        self.candidatos = [(p, {"chave": "ficticia", "modelo": "ficticio"})
                           for p in ("deepseek", "anthropic")]

    def rotear(self, executar):
        with patch.object(EL, "provedores_api_configurados", return_value=self.candidatos), \
             patch.object(EL, "verificar_saude", return_value=True), patch.object(EL.time, "sleep"):
            return EL.executar_com_fallback(self.ws, "deepseek", executar, ["deepseek", "anthropic"])

    def test_resultado_http_incerto_nao_repete_nem_troca_provedor(self):
        erros = [urllib.error.HTTPError("https://ficticio.invalid", 503, "erro", {}, None),
                 urllib.error.URLError("falha de transporte"), TimeoutError(),
                 ConnectionResetError("conexão interrompida"), http.client.IncompleteRead(b"parcial")]
        for erro in erros:
            with self.subTest(erro=type(erro).__name__):
                tentativas = []
                def executar(provedor, _cfg):
                    tentativas.append(provedor)
                    return EL._http_json("https://ficticio.invalid", {}, {"ficticio": True})
                with patch.object(EL.urllib.request, "urlopen", side_effect=erro):
                    with self.assertRaises(FX.ResultadoIncerto):
                        self.rotear(executar)
                self.assertEqual(tentativas, ["deepseek"])

    def test_resposta_ilegivel_nao_abre_outra_sessao(self):
        resposta = Mock()
        resposta.__enter__ = Mock(return_value=resposta)
        resposta.__exit__ = Mock(return_value=False)
        resposta.read.return_value = b"nao e JSON"
        with patch.object(EL.urllib.request, "urlopen", return_value=resposta):
            with self.assertRaises(FX.ResultadoIncerto):
                EL._http_json("https://ficticio.invalid", {}, {})

    def test_recusa_definitiva_inicial_preserva_fallback(self):
        tentativas = []
        def executar(provedor, _cfg):
            tentativas.append(provedor)
            if provedor == "deepseek":
                with patch.object(EL.urllib.request, "urlopen", side_effect=
                                  urllib.error.HTTPError("https://ficticio.invalid", 402, "sem saldo", {}, None)):
                    return EL._http_json("https://ficticio.invalid", {}, {})
            return "ok"
        self.assertEqual(self.rotear(executar), "ok")
        self.assertEqual(tentativas, ["deepseek", "anthropic"])

    def test_falha_apos_rodada_com_ferramenta_nao_reinicia_sessao(self):
        job = {"id": "ia-ficticia", "caso": "OS-0001-2099", "acao": "revisar", "solicitante": "op",
               "consentimento": EL.criar_consentimento("op", ["deepseek", "anthropic"]),
               "_etapa": {"tipo": "revisao", "saidas": ["03-relatorios/revisao-v01.md"]}}
        pl = Mock()
        pl.pedido.return_value = {"cancelar": False}
        pl.progresso.return_value = True
        rodada = {"choices": [{"message": {"tool_calls": [{"id": "call-1", "type": "function",
                   "function": {"name": "listar_arquivos", "arguments": "{}"}}]}}]}
        tentativas = []
        budget = Mock()
        budget.chamar.side_effect = [rodada, RuntimeError("O provedor recusou o pedido (HTTP 402).")]
        def executar(provedor, cfg):
            tentativas.append(provedor)
            return EL.executar(self.ws, job, "agente-ficticio", provedor, cfg, pl)
        with patch.object(PL, "montar_prompt", return_value="fixture"), \
             patch.object(EL, "_instrucoes_locais", return_value=""), \
             patch.object(EL, "OrcamentoIA", return_value=budget):
            with self.assertRaises(FX.ResultadoIncerto):
                self.rotear(executar)
        self.assertEqual(tentativas, ["deepseek"])
        self.assertEqual(budget.chamar.call_count, 2)

    def test_cancelamento_durante_http_impede_ferramentas_da_resposta(self):
        job = {"id": "ia-cancelada", "caso": "OS-0001-2099", "acao": "revisar", "solicitante": "op",
               "consentimento": EL.criar_consentimento("op", ["deepseek"]),
               "_etapa": {"tipo": "revisao", "saidas": ["03-relatorios/revisao-v01.md"]}}
        pl = Mock()
        pl.pedido.return_value = {"cancelar": False}
        pl.progresso.return_value = True
        def responder(*args, **kwargs):
            pl.pedido.return_value = {"cancelar": True}
            return {"choices": [{"message": {"tool_calls": [{"id": "call-1", "type": "function",
                    "function": {"name": "gravar_arquivo", "arguments": json.dumps({
                        "caminho": "03-relatorios/revisao-v01.md", "conteudo": "nao gravar"})}}]}}]}
        budget = Mock()
        budget.chamar.side_effect = responder
        with patch.object(PL, "montar_prompt", return_value="fixture"), \
             patch.object(EL, "_instrucoes_locais", return_value=""), \
             patch.object(EL, "OrcamentoIA", return_value=budget):
            with self.assertRaisesRegex(RuntimeError, "Cancelado pela Central"):
                EL.executar(self.ws, job, "agente-ficticio", "deepseek", self.candidatos[0][1], pl)
        self.assertFalse((Path(self.ws) / "casos" / job["caso"] / "03-relatorios/revisao-v01.md").exists())

    def test_docx_do_broker_usa_geracao_com_vinculo(self):
        pasta = Path(self.ws) / "casos" / "OS-0001-2099" / "03-relatorios"
        pasta.mkdir(parents=True)
        (pasta / "minuta-v01.md").write_text("fonte fictícia", encoding="utf-8")
        with patch("tarefas.gerar_docx", return_value={"docx": "RELATORIO-OS-0001-2099-v01.docx", "pendentes": ""}) as gerar:
            with patch.object(EL.subprocess, "run", side_effect=AssertionError("broker não deve gerar DOCX sem registrar vínculo")):
                resposta = EL._tool(self.ws, "OS-0001-2099", "gerar_docx", {"minuta": "minuta-v01.md"})
        gerar.assert_called_once_with(self.ws, "OS-0001-2099", "minuta-v01.md")
        self.assertTrue(resposta["ok"])
        self.assertEqual(resposta["docx"], "03-relatorios/RELATORIO-OS-0001-2099-v01.docx")

    def test_falha_auditoria_apos_http_nao_abre_fallback(self):
        job = {"id": "ia-auditoria", "caso": "OS-0001-2099", "acao": "revisar", "solicitante": "op",
               "consentimento": EL.criar_consentimento("op", ["deepseek", "anthropic"]),
               "_etapa": {"tipo": "revisao", "saidas": ["03-relatorios/revisao-v01.md"]}}
        pl = Mock()
        pl.pedido.return_value = {"cancelar": False}
        pl.progresso.return_value = True
        chamadas = []
        def http(url, *args, **kwargs):
            chamadas.append(url)
            return {"usage": {"input_tokens": 1, "output_tokens": 1},
                    "choices": [{"message": {"content": "resposta fictícia"}}],
                    "content": [{"type": "text", "text": "resposta fictícia"}]}
        def publicar(self_, estado, provedor, modelo):
            if provedor == "deepseek":
                raise RuntimeError("auditoria indisponível após HTTP")
        with patch.object(PL, "montar_prompt", return_value="fixture"), \
             patch.object(EL, "_instrucoes_locais", return_value=""), \
             patch.object(EL, "_http_json", side_effect=http), \
             patch.object(EL.OrcamentoIA, "_publicar", publicar):
            with self.assertRaises(FX.ResultadoIncerto):
                self.rotear(lambda prov, cfg: EL.executar(self.ws, job, "ficticio", prov, cfg, pl))
        self.assertEqual(len(chamadas), 1)

    def test_ledger_protege_tambem_consumidor_fora_da_sessao(self):
        pl = Mock()
        pl.pedido.return_value = {"cancelar": False}
        job = {"id": "ia-ledger", "solicitante": "op"}
        budget = EL.OrcamentoIA(self.ws, job, pl)
        chamadas = []
        def http(url, *args, **kwargs):
            chamadas.append(url)
            return {"usage": {"input_tokens": 1, "output_tokens": 1}}
        def publicar(estado, provedor, modelo):
            if provedor == "deepseek":
                raise RuntimeError("falha ao persistir resposta recebida")
        with patch.object(EL, "_http_json", side_effect=http), patch.object(budget, "_publicar", side_effect=publicar):
            with self.assertRaises(FX.ResultadoIncerto):
                self.rotear(lambda prov, cfg: budget.chamar(prov, "ficticio", "https://ficticio.invalid", {}, {}, 1))
        self.assertEqual(len(chamadas), 1)


class RecuperacaoCancelada(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-as54-cancel-")
        self.addCleanup(self.temp.cleanup)
        self.ws = self.temp.name
        self.pl = PL.Plantao(self.ws)
        self.fx = FX.Fluxos(self.ws)
        self.pl.registrar("morto", "simulado", "auto", aprovado=True)
        self.pl.registrar("novo", "simulado", "auto", aprovado=True)

    def envelhecer(self):
        with self.pl._c() as c:
            c.execute("UPDATE agentes SET visto_em='2000-01-01T00:00:00' WHERE nome='morto'")

    def test_cancelar_queda_recuperar_libera_caso_sem_novo_cancelamento(self):
        pid = self.pl.enfileirar("OS-0001-2099", "completo", "op")
        self.assertEqual(self.pl.reivindicar("morto")["id"], pid)
        self.assertTrue(self.pl.cancelar(pid))
        self.envelhecer()
        self.assertIsNone(self.pl.reivindicar("novo"))
        self.assertEqual(self.pl.pedido(pid)["estado"], "cancelada")
        self.assertEqual(self.fx.etapa_do_pedido(pid)["estado"], "cancelada")
        with self.pl._c() as c:
            estados = [r[0] for r in c.execute("SELECT estado FROM pedidos")]
        self.assertEqual(estados, ["cancelada"] * 4)
        novo = self.pl.enfileirar("OS-0001-2099", "revisar", "op")
        self.assertEqual(self.pl.reivindicar("novo")["id"], novo)

    def test_cancelamento_nao_apaga_intencao_externa_incerta(self):
        pid = self.pl.enfileirar("OS-0001-2099", "revisar", "op")
        self.pl.reivindicar("morto")
        etapa = self.fx.etapa_do_pedido(pid)
        self.fx.registrar_intencao(etapa["id"], "morto", "chamada-ficticia")
        self.pl.cancelar(pid)
        self.envelhecer()
        self.assertIsNone(self.pl.reivindicar("novo"))
        self.assertEqual(self.fx.etapa_do_pedido(pid)["estado"], "aguardando_operador")
        with self.pl._c() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fluxos_intencoes WHERE resultado IS NULL").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
