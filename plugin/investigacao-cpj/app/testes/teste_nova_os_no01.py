"""NO01: Nova O.S. — gravação tolerante, erro legível, cancelamento, O.S. vigente e botões da fila.

Workspace, documentos, nomes e números integralmente fictícios.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from astra_fixture import AstraFixture

APP = Path(__file__).resolve().parents[1]
S_PDF = APP.parent / "skills" / "pdf-autos-policiais" / "scripts"
for p in (str(APP), str(S_PDF)):
    if p not in sys.path:
        sys.path.insert(0, p)

import dados_os as D_OS  # noqa: E402
import estado_extracao  # noqa: E402
from ordens_servico import extrair_ordens  # noqa: E402

TRANSCRICAO = """# Transcrição fictícia

## Página 3
Termo de declarações fictício.
Delegado: OUTRA PESSOA FICTICIA
Escrivão: OUTRO ESCRIVAO FICTICIO

## Página 40
SECRETARIA FICTICIA
ORDEM DE SERVIÇO Nº 900 / 2099
Natureza: Furto (art. 155)
B.O.Nº: 111/2098 RDO Nº: I.P.: 22 / 2098
Delegado: DELEGADA FICTICIA ANTIGA
Escrivão: ESCRIVAO FICTICIO ANTIGO
Investigador: INVESTIGADOR FICTICIO ANTIGO
NATUREZA DA INVESTIGAÇÃO
Ref.: 6666/2098
BO: AA0001/2098
Conforme determinação da Autoridade Policial, ouvir testemunha
fictícia antiga.
Prazo de Conclusão: 30 Dias
CUMPRA-SE.
CIDADE FICTICIA / SP, 05/03/2099

## Página 90
SECRETARIA FICTICIA
ORDEM DE SERVIÇO Nº 901 / 2099
Natureza: Estelionato (art. 171)
B.O.Nº: 112/2098 RDO Nº: I.P.: 23 / 2098
Delegado: DELEGADA FICTICIA ATUAL
Escrivão: ESCRIVAO FICTICIO ATUAL
Investigador: INVESTIGADOR FICTICIO ATUAL
NATUREZA DA INVESTIGAÇÃO
Ref.: 7777/2098
BO: ZZ0001/2098
Conforme determinação da Autoridade Policial, analisar extratos
fictícios do Banco Exemplo, com atenção às transferências.
Prazo para Conclusão: 15 Dias.
CUMPRA-SE.
CIDADE FICTICIA/SP, 01/02/2099
"""
DOCUMENTO = "1234567-89.2099.8.26.0001.pdf"


class OrdemVigente(unittest.TestCase):
    def test_le_campos_da_ordem_e_calcula_prazo(self):
        ordens = D_OS.ordens_de_texto(TRANSCRICAO)
        self.assertEqual([o["numero"] for o in ordens], ["900/2099", "901/2099"])
        o = ordens[1]
        self.assertEqual(o["pagina"], 90)
        self.assertEqual(o["data"], "2099-02-01")
        self.assertEqual(o["campos"]["natureza"], "Estelionato (art. 171)")
        self.assertEqual(o["campos"]["requisitante"], "DELEGADA FICTICIA ATUAL")
        self.assertEqual(o["campos"]["escrivao"], "ESCRIVAO FICTICIO ATUAL")
        self.assertEqual(o["investigador"], "INVESTIGADOR FICTICIO ATUAL")
        self.assertEqual(o["campos"]["bo"], "ZZ0001/2098")
        self.assertEqual(o["campos"]["inquerito"], "7777/2098")
        self.assertEqual(o["prazo_dias"], 15)
        self.assertEqual(o["campos"]["prazo"], "2099-02-16")
        self.assertEqual(o["campos"]["determinacao"],
                         "Conforme determinação da Autoridade Policial, analisar extratos fictícios do Banco Exemplo, "
                         "com atenção às transferências.")
        # Sem Ref./BO após o cabeçalho, usa I.P. e B.O. do bloco de identificação.
        alt = D_OS.ordens_de_texto(TRANSCRICAO.replace("Ref.: 7777/2098\n", "").replace("BO: ZZ0001/2098\n", ""))[1]
        self.assertEqual(alt["campos"]["inquerito"], "23/2098")
        self.assertEqual(alt["campos"]["bo"], "112/2098")

    def test_escolhe_ordem_do_cadastro_ou_a_mais_recente(self):
        ordens = D_OS.ordens_de_texto(TRANSCRICAO)
        self.assertEqual(D_OS.escolher_ordem(ordens, "901/2099")["numero"], "901/2099")
        self.assertEqual(D_OS.escolher_ordem(ordens, "OS-901-2099")["numero"], "901/2099")
        self.assertEqual(D_OS.escolher_ordem(ordens, "")["numero"], "900/2099")  # data mais recente
        self.assertEqual(D_OS.escolher_ordem(ordens, "555/2099")["numero"], "900/2099")
        self.assertIsNone(D_OS.escolher_ordem([], "901/2099"))


class GravacaoTolerante(unittest.TestCase):
    def test_repete_gravacao_bloqueada_pelo_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = os.replace
            falhas = iter([PermissionError(13, "Acesso negado"), PermissionError(13, "Acesso negado")])

            def replace(a, b):
                erro = next(falhas, None)
                if erro:
                    raise erro
                return real(a, b)
            with patch.object(estado_extracao.os, "replace", side_effect=replace), patch.object(estado_extracao.time, "sleep"):
                estado_extracao.gravar(tmp, {"ok": 1})
            self.assertEqual(json.loads(estado_extracao.arquivo(tmp).read_text(encoding="utf-8")), {"ok": 1})
            self.assertEqual([p.name for p in estado_extracao.arquivo(tmp).parent.glob("*.tmp")], [])

    def test_desiste_apos_bloqueio_persistente_sem_deixar_temporario(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(estado_extracao.os, "replace", side_effect=PermissionError(13, "Acesso negado")), \
                    patch.object(estado_extracao.time, "sleep"):
                with self.assertRaises(PermissionError):
                    estado_extracao.gravar(tmp, {"ok": 1})
            self.assertEqual(list(estado_extracao.arquivo(tmp).parent.glob("*.tmp")), [])


class NovaOSCentral(AstraFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from rotas import comum
        self.comum = comum
        self.proc = self.ws / "casos" / self.caso / "processamento.json"
        self.proc.write_text(json.dumps({"trabalhos": []}), encoding="utf-8")

    def item(self, **campos):
        base = {"doc": "autos-ficticios", "arquivo": "autos-ficticios.pdf", "status": "na_fila",
                "enfileirado": "2099-01-01T10:00:00", "progresso": 0, "usuario": "astra_ficticio"}
        base.update(campos)
        self.proc.write_text(json.dumps({"trabalhos": [base]}), encoding="utf-8")
        return base

    def ler(self):
        return json.loads(self.proc.read_text(encoding="utf-8"))["trabalhos"][0]

    # ------------------------------------------------------------ erro legível
    def test_erro_do_script_mostra_causa_legivel(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "extrair.py"
            script.write_text("raise PermissionError(13, 'Acesso negado', 'estado.json')\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                self.comum.rodar([sys.executable, str(script)], dict(os.environ), str(Path(tmp) / "p.log"))
            msg = str(ctx.exception)
            self.assertIn("Extração/OCR", msg)
            self.assertIn("Windows bloqueou", msg)
            self.assertIn("Reprocesse", msg)
            script.write_text("raise MemoryError()\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                self.comum.rodar([sys.executable, str(script)], dict(os.environ), str(Path(tmp) / "p.log"))
            self.assertIn("memória insuficiente", str(ctx.exception))
            script.write_text("raise SystemExit('PDF protegido por senha fictícia')\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                self.comum.rodar([sys.executable, str(script)], dict(os.environ), str(Path(tmp) / "p.log"))
            self.assertIn("PDF protegido por senha fictícia", str(ctx.exception))

    # ------------------------------------------------------------ cancelamento
    def test_cancelar_item_na_fila_e_recusar_concluido(self):
        t = self.item()
        url = f"/api/casos/{self.caso}/processamento/cancelar"
        r = self.post(url, {"doc": t["doc"], "enfileirado": t["enfileirado"]})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(self.ler()["status"], "cancelado")
        self.assertTrue(self.ler().get("fim"))
        self.assertEqual(self.post(url, {"doc": t["doc"], "enfileirado": t["enfileirado"]}).status_code, 409)
        self.item(status="concluido", fim="2099-01-01T10:05:00")
        self.assertEqual(self.post(url, {"doc": t["doc"], "enfileirado": t["enfileirado"]}).status_code, 409)
        self.item()
        self.assertEqual(self.post(url, {"doc": t["doc"], "enfileirado": "2099-01-01T09:00:00"}).status_code, 409)
        self.assertEqual(self.post(url, {"doc": t["doc"]}).status_code, 400)
        leitor = self.s.app.test_client()
        leitor.post("/api/entrar", json={"login": "leitor_ficticio", "senha": "Ficticia123"}, headers={"X-CPJ": "1"})
        self.assertEqual(leitor.post(url, json={"doc": t["doc"], "enfileirado": t["enfileirado"]},
                                     headers={"X-CPJ": "1"}).status_code, 403)
        self.assertEqual(self.ler()["status"], "na_fila")

    def test_item_cancelado_na_fila_nao_e_processado(self):
        self.item(status="cancelado", fim="2099-01-01T10:01:00")
        with patch.object(self.comum, "rodar") as rodar:
            self.comum.processar({"caso": self.caso, "doc": "autos-ficticios", "arquivo": "autos-ficticios.pdf"})
        rodar.assert_not_called()
        self.assertEqual(self.ler()["status"], "cancelado")

    def test_cancelar_em_execucao_interrompe_o_processo_local(self):
        t = self.item(status="processando", inicio="2099-01-01T10:00:01")
        resultado = {}
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [sys.executable, "-c", "import time\nprint('inicio', flush=True)\ntime.sleep(60)"]

            def executar():
                try:
                    self.comum.rodar(cmd, dict(os.environ), str(Path(tmp) / "p.log"), chave=(self.caso, t["doc"]))
                except Exception as e:  # noqa: BLE001
                    resultado["erro"] = e
            th = threading.Thread(target=executar)
            inicio = time.time()
            th.start()
            for _ in range(100):
                if (self.caso, t["doc"]) in self.comum._execucoes:
                    break
                time.sleep(0.05)
            r = self.post(f"/api/casos/{self.caso}/processamento/cancelar", {"doc": t["doc"], "enfileirado": t["enfileirado"]})
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
            th.join(20)
            self.assertFalse(th.is_alive())
            self.assertLess(time.time() - inicio, 20)
        self.assertIsInstance(resultado.get("erro"), self.comum.Cancelado)
        self.assertTrue(self.ler().get("cancelar_pedido"))

    # ------------------------------------------------------------ O.S. vigente
    def test_ordem_vigente_preenche_caso_e_grava_determinacao(self):
        C = self.comum.C
        c = C.carregar(self.caso)
        c.update(natureza="Natureza manual fictícia", requisitante="", escrivao="", bo="", inquerito="",
                 processo="", prazo=None, determinacao="")
        C.salvar(c)
        pasta = self.ws / "casos" / self.caso / "01-extracao" / "autos-ficticios"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "transcricao.md").write_text(TRANSCRICAO, encoding="utf-8")
        extrair_ordens(pasta)
        info = D_OS.aplicar_ordem(C, self.caso, str(pasta), DOCUMENTO)
        self.assertEqual(info["numero"], "901/2099")
        c = C.carregar(self.caso)
        self.assertEqual(c["natureza"], "Natureza manual fictícia")  # valor manual preservado
        self.assertEqual(c["requisitante"], "DELEGADA FICTICIA ATUAL")
        self.assertEqual(c["escrivao"], "ESCRIVAO FICTICIO ATUAL")
        self.assertEqual(c["bo"], "ZZ0001/2098")
        self.assertEqual(c["inquerito"], "7777/2098")
        self.assertEqual(c["processo"], "1234567-89.2099.8.26.0001")
        self.assertEqual(c["prazo"], "2099-02-16")
        self.assertIn("analisar extratos fictícios do Banco Exemplo", c["determinacao"])
        self.assertEqual(c["preenchimento_os"]["fontes"]["determinacao"]["metodo"], "os_vigente")
        md = (self.ws / "casos" / self.caso / "determinacao-autoridade.md").read_text(encoding="utf-8")
        for trecho in ("901/2099", "01/02/2099", "Página 90", "DELEGADA FICTICIA ATUAL", "INVESTIGADOR FICTICIO ATUAL",
                       "analisar extratos", "15 dias", "16/02/2099", "Natureza manual fictícia", "2 Ordens de Serviço"):
            self.assertIn(trecho, md)
        # A leitura genérica do texto inteiro não apaga os dados da O.S. vigente por conflito.
        D_OS.aplicar(C, self.caso, TRANSCRICAO, DOCUMENTO)
        c = C.carregar(self.caso)
        self.assertEqual(c["requisitante"], "DELEGADA FICTICIA ATUAL")
        self.assertEqual(c["escrivao"], "ESCRIVAO FICTICIO ATUAL")

    def test_previa_do_formulario_usa_a_ordem_de_servico(self):
        from io import BytesIO
        r = self.client.post("/api/os/detectar", headers={"X-CPJ": "1"},
                             data={"arquivos": (BytesIO(TRANSCRICAO.encode("utf-8")), "autos-ficticios.md")},
                             content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(j["campos"]["ordem_servico"]["valor"], "900/2099")  # sem cadastro: a mais recente
        self.assertIn("ouvir testemunha fictícia antiga", j["campos"]["determinacao"]["valor"])
        self.assertNotIn("requisitante", j["conflitos"])

    # ------------------------------------------------------------ botões da fila
    def test_botoes_da_fila_por_situacao(self):
        script = r"""
const assert=require('node:assert/strict');
const fila=require(process.argv[2]);
const h={esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),badge:()=>'',barraHTML:()=>'',podeAgir:true};
const jobs=[
 {caso:'OS-1-2099',doc:'a',arquivo:'a.pdf',status:'erro',erro:'Extração/OCR: falha fictícia',enfileirado:'2099-01-01T00:00:00',fim:'2099-01-01T00:01:00'},
 {caso:'OS-1-2099',doc:'b',arquivo:'b.pdf',status:'processando',enfileirado:'2099-01-01T00:00:01'},
 {caso:'OS-1-2099',doc:'c',arquivo:'c.pdf',status:'na_fila',enfileirado:'2099-01-01T00:00:02'},
 {caso:'OS-1-2099',doc:'d',arquivo:'d.pdf',status:'cancelado',enfileirado:'2099-01-01T00:00:03',fim:'2099-01-01T00:02:00'},
 {caso:'OS-1-2099',doc:'e',arquivo:'e.pdf',status:'concluido',enfileirado:'2099-01-01T00:00:04',fim:'2099-01-01T00:03:00'}];
const html=fila.html(fila.criar().calcular(jobs),h);
const acoes=[...html.matchAll(/data-fila-acao="([a-z]+)" data-fila-indice="(\d+)"/g)].map(m=>m[1]+':'+m[2]);
assert.deepEqual(acoes,['reprocessar:0','dispensar:0','cancelar:1','cancelar:2','reprocessar:3','dispensar:3']);
assert.match(html,/Cancelar processamento/);assert.match(html,/Reprocessar/);assert.match(html,/Remover da fila/);
assert.match(html,/1 cancelado/);
assert.doesNotMatch(fila.html(fila.criar().calcular(jobs),{...h,podeAgir:false}),/data-fila-acao=/);
console.log('fila ok');
"""
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "botoes.cjs"
            arquivo.write_text(script, encoding="utf-8")
            r = subprocess.run(["node", str(arquivo), str(APP / "static/js/fila-progresso.js")], text=True,
                               encoding="utf-8", capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
