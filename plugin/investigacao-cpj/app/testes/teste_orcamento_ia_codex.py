"""CX03: executores reais com HTTP simulado e ledger em workspace fictício."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import executores_llm as EL
import plantao as PL


def resposta(entrada=4, saida=2, ferramenta=False, uso=True):
    r = {"id": "res-ficticia", "output": [{"type": "message", "content": [{"type": "output_text", "text": "feito"}]}]}
    if ferramenta:
        r["output"] = [{"type": "function_call", "name": "listar_arquivos", "arguments": "{}", "call_id": "ficticio"}]
    if uso:
        r["usage"] = {"input_tokens": entrada, "output_tokens": saida, "total_tokens": entrada + saida}
    return r


class Orcamento(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-cx03-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = self.tmp.name
        self.pl = PL.Plantao(self.ws)
        self.pl.registrar("Teste", "simulado", "auto", aprovado=True)
        self.pl.enfileirar("OS-777-2099", "financeiro", "teste", consentimento=json.dumps(EL.criar_consentimento("teste", sorted(EL.DESTINOS_EXTERNOS))))
        self.job = self.pl.reivindicar("Teste")
        self.cfg = {"modelo": "modelo-ficticio", "chave": "SEGREDO-FICTICIO"}
        self.pasta = Path(self.ws) / "casos" / self.job["caso"]
        self.pasta.mkdir(parents=True)

    def configurar(self, limites=None, tarifas=None):
        (Path(self.ws) / "config" / "ia.json").write_text(json.dumps({
            "orcamento_por_pedido": limites or {}, "tarifas_usd_por_milhao": tarifas or {}
        }), encoding="utf-8")

    def executar(self, job=None):
        return EL.executar(self.ws, job or self.job, "Teste", "openai", self.cfg, self.pl)

    def uso(self):
        return json.loads(self.pl.pedido(self.job["id"])["uso_ia"])

    def test_tokens_ultrapassados_parada_sem_terceira_chamada(self):
        self.configurar({"tokens": 10})
        with patch.object(EL, "_http_json", side_effect=[resposta(5, 1, True), resposta(5, 1, True)]) as http:
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "tokens"):
                self.executar()
        self.assertEqual(http.call_count, 2)
        self.assertEqual(self.uso()["tokens"], 12)
        self.assertIn("tokens", self.uso()["interrompido"])
        self.assertIn("tokens", self.pl.como_tarefa(self.pl.pedido(self.job["id"]))["uso_ia"]["interrompido"])

    def test_limite_exato_bloqueia_proxima_chamada(self):
        self.configurar({"tokens": 6})
        with patch.object(EL, "_http_json", return_value=resposta(4, 2, True)) as http:
            with self.assertRaises(EL.OrcamentoExcedido): self.executar()
        self.assertEqual(http.call_count, 1)

    def test_custo_tarifa_ficticia_e_auditoria_sem_segredos(self):
        self.configurar({"custo_usd": 0.0005}, {"openai": {"modelo-ficticio": {"entrada": 100, "saida": 0}}})
        with patch.object(EL, "_http_json", return_value=resposta(10, 0)) as http:
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "custo"):
                self.executar()
        self.assertEqual(http.call_count, 1)
        self.assertAlmostEqual(self.uso()["custo_usd"], 0.001)
        audit = (Path(self.ws) / "config" / "auditoria.log").read_text(encoding="utf-8")
        self.assertNotIn("SEGREDO-FICTICIO", audit)
        self.assertNotIn("instructions", audit)
        self.assertIn(self.job["id"], audit)

    def test_custo_sem_tarifa_bloqueia_antes_da_rede(self):
        self.configurar({"custo_usd": 1})
        with patch.object(EL, "_http_json") as http:
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "tarifa"):
                self.executar()
        http.assert_not_called()

    def test_uso_desconhecido_nao_finge_zero(self):
        self.configurar()
        with patch.object(EL, "_http_json", return_value=resposta(uso=False)):
            self.executar()
        self.assertIsNone(self.uso()["tokens"])
        self.assertIsNone(self.uso()["custo_usd"])
        self.assertFalse(self.uso()["medicao_completa"])

    def test_tokens_sem_medicao_interrompem(self):
        self.configurar({"tokens": 100})
        with patch.object(EL, "_http_json", return_value=resposta(uso=False)) as http:
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "medição"):
                self.executar()
        self.assertEqual(http.call_count, 1)

    def test_tempo_e_timeout_respeitam_saldo(self):
        self.configurar({"segundos": 1})
        agora = [1000.0]
        timeouts = []
        def http(*args, **kw):
            timeouts.append(kw["timeout"])
            agora[0] += 2
            return resposta()
        with patch.object(EL.time, "time", side_effect=lambda: agora[0]), patch.object(EL, "_http_json", side_effect=http):
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "tempo"):
                self.executar()
        self.assertLessEqual(timeouts[0], 1)
        self.assertEqual(self.uso()["tokens"], 6)

    def test_uso_acumulado_sobrevive_retomada(self):
        self.configurar({"tokens": 10})
        with patch.object(EL, "_http_json", return_value=resposta()) as http:
            self.executar(dict(self.job, _etapa={"id": "a", "tipo": "financeiro", "etapa": "a", "arg": {}, "saidas": []}))
            self.pl = PL.Plantao(self.ws)
            with self.assertRaises(EL.OrcamentoExcedido): self.executar()
        self.assertEqual(http.call_count, 2)
        self.assertEqual(self.uso()["tokens"], 12)
        with patch.object(EL, "_http_json") as http:
            with self.assertRaises(EL.OrcamentoExcedido): self.executar()
        http.assert_not_called()

    def test_etapas_limitadas_compartilham_saldo_sem_corrida(self):
        self.configurar({"tokens": 6})
        def http(*a, **k): time.sleep(0.1); return resposta()
        def rodar(n):
            try: return self.executar()
            except EL.OrcamentoExcedido: return "parado"
        with patch.object(EL, "_http_json", side_effect=http) as chamada, ThreadPoolExecutor(2) as pool:
            rs = list(pool.map(rodar, [1, 2]))
        self.assertEqual(chamada.call_count, 1)
        self.assertEqual(rs.count("parado"), 1)
        self.assertEqual(self.uso()["tokens"], 6)

    def test_sem_limites_mantem_paralelismo(self):
        self.configurar()
        barreira = threading.Barrier(2)
        def http(*a, **k): barreira.wait(3); return resposta()
        with patch.object(EL, "_http_json", side_effect=http), ThreadPoolExecutor(2) as pool:
            list(pool.map(lambda n: self.executar(), [1, 2]))
        self.assertEqual(self.uso()["tokens"], 12)
        self.assertEqual(self.uso()["chamadas"], 2)

    def test_retomada_le_ledger_durante_chamada_sem_bloquear_init(self):
        self.configurar({"tokens": 100})
        iniciou, liberar = threading.Event(), threading.Event()
        terminou = threading.Event()
        EL.OrcamentoIA(self.ws, self.job, self.pl)
        def http(*a, **k): iniciou.set(); liberar.wait(3); return resposta()
        def ler(): EL.OrcamentoIA(self.ws, self.job, self.pl); terminou.set()
        with patch.object(EL, "_http_json", side_effect=http), ThreadPoolExecutor(2) as pool:
            trabalho = pool.submit(self.executar)
            self.assertTrue(iniciou.wait(2))
            leitura = pool.submit(ler)
            try: self.assertTrue(terminou.wait(0.5))
            finally: liberar.set()
            trabalho.result(); leitura.result()

    def test_usage_dos_provedores_e_cache_tarifado(self):
        self.configurar({}, {"anthropic": {"modelo-ficticio": {"entrada": 100, "saida": 200, "cache_leitura": 10, "cache_gravacao": 120}}})
        fixtures = [
            ("deepseek", {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}}, 6),
            ("anthropic", {"content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 4, "output_tokens": 2, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 1}}, 10),
            ("gemini", {"candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2, "thoughtsTokenCount": 3, "totalTokenCount": 9}}, 9)
        ]
        anterior = 0
        for prov, r, tokens in fixtures:
            with self.subTest(prov=prov), patch.object(EL, "_http_json", return_value=r):
                EL.executar(self.ws, self.job, "Teste", prov, self.cfg, self.pl)
            self.assertEqual(self.uso()["tokens"], anterior + tokens)
            anterior += tokens

    def test_custo_cache_sem_tarifa_nao_inventa_desconto(self):
        self.configurar({"custo_usd": 1}, {"openai": {"modelo-ficticio": {"entrada": 100, "saida": 100}}})
        r = resposta(); r["usage"]["input_tokens_details"] = {"cached_tokens": 3}
        with patch.object(EL, "_http_json", return_value=r):
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "medição desconhecida de custo"):
                self.executar()
        self.assertIsNone(self.uso()["custo_usd"])

    def test_cli_tempo_interrompe_processo_silencioso(self):
        self.configurar({"segundos": 0.2})
        with patch.dict(os.environ, {"CPJ_PLANTAO_SIMULADO_CMD": "import time;time.sleep(30)"}):
            inicio = time.monotonic()
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "tempo"):
                PL._executar_sessao(self.pl, self.job, "Teste", "simulado")
        self.assertLess(time.monotonic() - inicio, 8)

    def test_config_salva_limites_sem_mudar_pedido_existente(self):
        EL.salvar_config_ia(self.ws, {"orcamento_por_pedido": {"tokens": 10}})
        with patch.object(EL, "_http_json", return_value=resposta()): self.executar()
        EL.salvar_config_ia(self.ws, {"orcamento_por_pedido": {"tokens": 1000}})
        with patch.object(EL, "_http_json", return_value=resposta()):
            with self.assertRaises(EL.OrcamentoExcedido): self.executar()

    def test_cadeia_completa_tem_orcamento_unico_de_grupo(self):
        self.pl.falhar(self.job["id"], "Teste", "troca de fixture")
        pid = self.pl.enfileirar(self.job["caso"], "completo", "teste", orcamento={"tokens": 10}, consentimento=json.dumps(EL.criar_consentimento("teste", sorted(EL.DESTINOS_EXTERNOS))))
        self.job = self.pl.reivindicar("Teste")
        with patch.object(EL, "_http_json", return_value=resposta()):
            self.executar()
            self.pl.concluir(self.job["id"], "Teste", {"resumo": "análise fictícia"})
            self.job = self.pl.reivindicar("Teste")
            with self.assertRaises(EL.OrcamentoExcedido): self.executar()
        self.assertEqual(json.loads(self.pl.pedido(pid)["uso_ia"])["tokens"], 12)
        self.assertEqual(self.uso()["tokens"], 12)
        self.assertEqual(json.loads(self.pl.pedido(pid)["resultado"])["resumo"], "análise fictícia")

    def test_falha_http_nao_perde_medicao_nem_reabre_limite(self):
        self.configurar({"tokens": 100})
        with patch.object(EL, "_http_json", side_effect=RuntimeError("Timeout fictício")):
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "medição"):
                self.executar()
        self.assertIsNone(self.uso()["tokens"])
        self.assertEqual(self.uso()["chamadas"], 1)

    def test_orcamento_nao_abre_fallback(self):
        self.configurar({"tokens": 5})
        tentados = []
        def executor(prov, cfg):
            tentados.append(prov)
            return EL.executar(self.ws, self.job, "Teste", prov, self.cfg, self.pl)
        with patch.object(EL, "provedores_api_configurados", return_value=[("openai", self.cfg), ("deepseek", self.cfg)]), patch.object(EL, "verificar_saude", return_value=True), patch.object(EL, "_http_json", return_value=resposta()):
            with self.assertRaises(EL.OrcamentoExcedido):
                EL.executar_com_fallback(self.ws, "openai", executor, destinos_aceitos=["openai", "deepseek"])
        self.assertEqual(tentados, ["openai"])

    def test_cli_com_tokens_sem_medicao_bloqueia(self):
        self.configurar({"tokens": 100})
        with patch.object(PL.subprocess, "Popen") as proc:
            with self.assertRaisesRegex(EL.OrcamentoExcedido, "CLI"):
                PL._executar_sessao(self.pl, self.job, "Teste", "simulado")
        proc.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
