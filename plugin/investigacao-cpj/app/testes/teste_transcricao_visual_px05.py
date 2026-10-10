"""PX05: PNG por página, consentimento, checkpoints; nenhum serviço real."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
IMPORT = tempfile.TemporaryDirectory(prefix="cpj-px05-import-")
os.environ.update(CPJ_WORKSPACE=IMPORT.name, CPJ_SEM_AGENTE_EMBUTIDO="1")
import executores_llm as EL

SCRIPT = APP.parent / "skills/pdf-autos-policiais/scripts/transcrever_visual.py"

def visual():
    spec = importlib.util.spec_from_file_location("visual_px05", SCRIPT)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

class Visual(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-px05-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        self.pasta = self.ws / "casos/OS-888-2099/01-extracao/doc"
        self.pasta.mkdir(parents=True)
        (self.pasta / "relatorio_extracao.json").write_text(json.dumps({"paginas": 4, "arquivo": "ficticio.pdf", "pendentes_transcricao_visual": [2], "conferir_visualmente": [3]}))
        (self.pasta / "qualidade.json").write_text(json.dumps({"3": {"precisa_ia": True}, "4": {"precisa_ia": True}}))
        self.no_http = patch.object(EL, "_http_json", side_effect=AssertionError("HTTP real proibido"))
        self.no_http.start(); self.addCleanup(self.no_http.stop)
        self.saude = patch.object(EL, "verificar_saude", return_value=True)
        self.saude.start(); self.addCleanup(self.saude.stop)

    def test_uniao_apenas_reprovadas_preserva_existente(self):
        m = visual()
        self.assertEqual(m.paginas_pendentes(self.pasta), [2, 3, 4])
        dest = self.pasta / "transcricoes_visuais"; dest.mkdir()
        (dest / "p0003.md").write_text("texto humano existente")
        for n in (2, 4):
            d = self.pasta / "paginas_visao"; d.mkdir(exist_ok=True)
            (d / f"p{n:04d}.png").write_bytes(b"\x89PNG\r\n\x1a\nFICTICIO" + bytes([n]))
        enviados = []
        def api(png):
            enviados.append(png)
            return {"texto": "Conta 12? [dígito incerto]", "provedor": "openai", "modelo": "ficticio"}
        out = m.transcrever(self.pasta, api)
        self.assertEqual(len(enviados), 2)
        self.assertEqual((dest / "p0003.md").read_text(), "texto humano existente")
        self.assertEqual(out["gravadas"], [2, 4])
        self.assertIn("CONFERIR", (dest / "p0002.md").read_text(encoding="utf-8"))
        self.assertIn("openai", (dest / "p0002.md").read_text(encoding="utf-8"))
        self.assertIn("12?", (dest / "p0002.md").read_text(encoding="utf-8"))
        self.assertEqual(m.transcrever(self.pasta, api)["gravadas"], [])
        self.assertEqual(len(enviados), 2)

    def test_pagina_fora_intervalo_e_symlink_nao_le(self):
        m = visual()
        (self.pasta / "qualidade.json").write_text(json.dumps({"999": {"precisa_ia": True}}))
        with self.assertRaises(ValueError): m.paginas_pendentes(self.pasta)

    def test_publicacao_preserva_gravacao_concorrente(self):
        m = visual()
        (self.pasta / "qualidade.json").write_text("{}")
        (self.pasta / "relatorio_extracao.json").write_text(json.dumps({"paginas": 1, "pendentes_transcricao_visual": [1]}))
        png = self.pasta / "paginas_visao/p0001.png"; png.parent.mkdir(); png.write_bytes(b"\x89PNG\r\n\x1a\nFICTICIO")
        def api(_):
            p = self.pasta / "transcricoes_visuais/p0001.md"; p.parent.mkdir(); p.write_text("Revisão humana concorrente")
            return {"texto": "Texto API", "provedor": "openai", "modelo": "ficticio"}
        self.assertEqual(m.transcrever(self.pasta, api)["gravadas"], [])
        self.assertEqual((self.pasta / "transcricoes_visuais/p0001.md").read_text(), "Revisão humana concorrente")

    def test_wire_formats_seis_provedores_e_rejeita_text_only(self):
        j = {"id": "ficticio", "solicitante": "operador", "consentimento": EL.criar_consentimento("operador", ["openai", "anthropic", "gemini", "xai", "openrouter", "nvidia"], escopo="transcricao_visual")}
        bodies = []
        class Ledger:
            def chamar(_, p, model, url, headers, body, timeout):
                bodies.append(body)
                if p == "openai": return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "FICTÍCIO ?"}]}]}
                if p == "anthropic": return {"content": [{"type": "text", "text": "FICTÍCIO ?"}]}
                if p == "gemini": return {"candidates": [{"content": {"parts": [{"text": "FICTÍCIO ?"}]}}]}
                return {"choices": [{"message": {"content": "FICTÍCIO ?"}}]}
        for p in j["consentimento"]["destinos"]:
            r = EL.transcrever_png(self.ws, j, p, {"modelo": "ficticio", "chave": "FICTICIA"}, b"\x89PNG\r\n\x1a\nFICTICIO", Ledger())
            self.assertEqual(r["texto"], "FICTÍCIO ?")
        for b in bodies:
            self.assertNotIn("tools", b)
            self.assertIn("dígito incerto", json.dumps(b, ensure_ascii=False))
        j["consentimento"] = EL.criar_consentimento("operador", ["deepseek"], escopo="transcricao_visual")
        with self.assertRaisesRegex(RuntimeError, "vision"):
            EL.transcrever_png(self.ws, j, "deepseek", {"modelo": "ficticio", "chave": "FICTICIA"}, b"\x89PNG\r\n\x1a\nFICTICIO", Ledger())

    def test_executor_gate_scope_e_payload_so_png_sem_tools(self):
        cfg = {"modelo": "modelo-visual-ficticio", "chave": "CHAVE-TESTE"}
        png = b"\x89PNG\r\n\x1a\nFICTICIO"
        j = {"id": "visual-test", "solicitante": "operador", "caso": "DADO-NAO-ENVIAR"}
        class Ledger:
            def chamar(_, prov, model, url, headers, body, timeout):
                self.assertNotIn("DADO-NAO-ENVIAR", json.dumps(body))
                self.assertNotIn("tools", body)
                self.assertIn(base64.b64encode(png).decode(), json.dumps(body))
                return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Transcrição fictícia ?"}]}]}
        with self.assertRaises(EL.ConsentimentoNecessario):
            EL.transcrever_png(self.ws, j, "openai", cfg, png, Ledger())
        j["consentimento"] = EL.criar_consentimento("operador", ["openai"])
        with self.assertRaises(EL.ConsentimentoNecessario):
            EL.transcrever_png(self.ws, j, "openai", cfg, png, Ledger())
        j["consentimento"] = EL.criar_consentimento("operador", ["openai"], escopo="transcricao_visual")
        self.assertEqual(EL.transcrever_png(self.ws, j, "openai", cfg, png, Ledger())["texto"], "Transcrição fictícia ?")

    def test_route_gate_recusa_e_atomicidade_tarefa(self):
        import auth, rotas.comum as comum, rotas.sistema as sistema, servidor, tarefas as T
        caso = "OS-888-2099"
        (self.ws / "casos" / caso / "caso.json").write_text(json.dumps({"id": caso, "status": "recebido"}))
        a = auth.Auth(str(self.ws)); a.salvar_usuario("operador", "Operador fictício", "admin", "Senha1234", temporaria=False)
        t = T.Tarefas(str(self.ws), comum.C, a, iniciar_agente=False)
        for obj, campo, valor in ((comum, "WS", str(self.ws)), (sistema, "WS", str(self.ws)),
            (comum.C, "CASOS", str(self.ws / "casos")), (comum, "tarefas", t), (sistema, "tarefas", t), (comum, "_auth_inst", a)):
            p = patch.object(obj, campo, valor); p.start(); self.addCleanup(p.stop)
        (self.ws / "config/chaves_llm.json").write_text(json.dumps({p: {"ativo": True, "chave": "ficticia", "modelo": "ficticio"} for p in ("openai", "deepseek")}))
        servidor.app.config["TESTING"] = True
        cli = servidor.app.test_client(); cli.post("/api/entrar", json={"login": "operador", "senha": "Senha1234"}, headers={"X-CPJ": "1"})
        def post(d): return cli.post(f"/api/casos/{caso}/transcricao-visual", json=d, headers={"X-CPJ": "1"})
        with patch.object(t, "rodar") as worker:
            r = post({}); self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json["destinos"], ["openai"])
            self.assertEqual(r.json["escopo"], "transcricao_visual")
            self.assertEqual(r.json["paginas"], 3)
            self.assertEqual(t.listar(), [])
            self.assertNotIn("tarefa", post({"consentimento_externo": {"recusado": True}}).json)
            self.assertEqual(t.listar(), [])
            self.assertEqual(post({"paginas": [1], "consentimento_externo": {"destinos": ["openai"]}}).status_code, 400)
            for aceite in ({}, {"aceito": None}, {"aceito": 0}, {"aceito": "sim"}):
                r = post({"consentimento_externo": {"destinos": ["openai"], "escopo": "transcricao_visual", **aceite}})
                self.assertEqual(r.status_code, 400)
            r = post({"consentimento_externo": {"aceito": True, "destinos": ["openai"], "escopo": "transcricao_visual", "usuario": "FORJADO"}})
            self.assertEqual(r.status_code, 200)
            j = t.obter(r.json["tarefa"])
            self.assertEqual(j["consentimento"]["usuario"], "operador")
            self.assertEqual(j["consentimento"]["escopo"], "transcricao_visual")
            worker.assert_called_once()
        with patch.object(a, "pode", side_effect=lambda perfil, perm: perm != "casos"), patch.object(comum, "plano_transcricao_visual") as plano:
            self.assertEqual(post({}).status_code, 403)
            plano.assert_not_called()

    def test_interface_usa_escopo_visual_retornado_servidor(self):
        sys.path.insert(0, str(APP / "testes"))
        from teste_consentimento_interface_se01 import Interface
        i = Interface(); i.setUp()
        i.ctx.eval("post=async function(u,d){chamadas.push(d);return d.consentimento_externo?{tarefa:'visual-ficticia'}:{requer_consentimento:true,destinos:['openai'],escopo:'transcricao_visual',paginas:3}}")
        i.iniciar(); i.ctx.eval("els['#b-cons-aceitar'].onclick()"); i.jobs()
        self.assertEqual(i.valor("chamadas[1].consentimento_externo.escopo"), "transcricao_visual")

    def test_replay_real_sem_ocr_e_original_preservado(self):
        import hashlib, runpy
        from PIL import Image
        import pypdfium2 as pdfium
        pdf = self.ws / "ficticio.pdf"
        # Duas páginas rasterizadas fictícias, sem qualquer conteúdo de caso.
        imgs = [Image.new("RGB", (300, 400), "white") for _ in range(2)]
        imgs[0].save(pdf, save_all=True, append_images=imgs[1:])
        extrair = SCRIPT.with_name("extrair.py")
        args = [str(extrair), str(pdf), "--saida", str(self.pasta), "--ocr", "visao", "--sem-reaproveitar"]
        env = dict(os.environ, CPJ_WORKSPACE=str(self.ws), PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, *args], env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        (self.pasta / "qualidade.json").write_text("{}")
        antes = hashlib.sha256(pdf.read_bytes()).hexdigest()
        visual().transcrever(self.pasta, lambda _: {"texto": "VALOR FICTÍCIO 12? [dígito incerto]", "provedor": "openai", "modelo": "ficticio"})
        with patch("pytesseract.image_to_data", side_effect=AssertionError("Novo OCR proibido")), patch.object(sys, "argv", args):
            runpy.run_path(str(extrair), run_name="__main__")
        t = (self.pasta / "transcricao.md").read_text(encoding="utf-8")
        self.assertIn("CONFERIR", t); self.assertIn("12?", t)
        self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(), antes)
        rel = json.loads((self.pasta / "relatorio_extracao.json").read_text(encoding="utf-8"))
        self.assertEqual(rel["paginas"], 2)
        self.assertEqual(rel["pendentes_transcricao_visual"], [])

    def test_worker_real_budget_checkpoint_derivados_e_cancelamento(self):
        import rotas.comum as comum
        from PIL import Image
        orig = self.ws / "casos/OS-888-2099/00-originais/ficticio.pdf"; orig.parent.mkdir()
        Image.new("RGB", (300, 400), "white").save(orig)
        r = subprocess.run([sys.executable, str(SCRIPT.with_name("extrair.py")), str(orig), "--saida", str(self.pasta), "--ocr", "visao", "--sem-reaproveitar"], env=dict(os.environ, CPJ_WORKSPACE=str(self.ws)), capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        meta_file = self.pasta / ".checkpoint/meta.json"
        meta = json.loads(meta_file.read_text(encoding="utf-8")); incompleto = dict(meta); incompleto.pop("dpi")
        meta_file.write_text(json.dumps(incompleto))
        with self.assertRaisesRegex(RuntimeError, "checkpoint|Checkpoint"):
            visual().validar_replay(self.pasta, orig)
        meta_file.write_text(json.dumps(meta))
        auto = dict(meta, ocr="auto", tesseract=True)
        meta_file.write_text(json.dumps(auto))
        ambiente = {"PATH": "TESSERACT-FICTICIO", "TESSDATA_PREFIX": "IDIOMA-FICTICIO"}
        with patch("pytesseract.get_languages", side_effect=AssertionError("Não consultar ambiente pai")), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout="true", stderr="")) as consulta:
            self.assertTrue(visual().validar_replay(self.pasta, orig, ambiente=ambiente)["tesseract"])
            self.assertEqual(consulta.call_args.kwargs["env"], ambiente)
            self.assertNotIn("image_to_data", str(consulta.call_args))
        meta_file.write_text(json.dumps(meta))
        (self.pasta / "qualidade.json").write_text("{}")
        (self.ws / "casos/OS-888-2099/caso.json").write_text('{"id":"OS-888-2099","status":"recebido","datas":{}}')
        (self.ws / "config").mkdir(exist_ok=True)
        (self.ws / "config/chaves_llm.json").write_text(json.dumps({"openai": {"ativo": True, "chave": "FICTICIA", "modelo": "ficticio"}}))
        class Tasks:
            def __init__(self): self.estado = {"status": "executando"}; self.indexado = False
            def obter(self, tid): return self.estado
            def at(self, tid, **kw): self.estado.update(kw)
            def indexar(self): self.indexado = True
        tasks = Tasks()
        for obj, campo, valor in ((comum, "WS", str(self.ws)), (comum, "tarefas", tasks), (comum.C, "CASOS", str(self.ws / "casos"))):
            p = patch.object(obj, campo, valor); p.start(); self.addCleanup(p.stop)
        plano = comum.plano_transcricao_visual("OS-888-2099")
        cons = EL.criar_consentimento("operador", ["openai"], escopo="transcricao_visual")
        resposta = {"usage": {"input_tokens": 8, "output_tokens": 4}, "output": [{"type": "message", "content": [{"type": "output_text", "text": "Conta fictícia 123? [dígito incerto]"}]}]}
        with patch.object(EL, "_http_json", return_value=resposta) as http:
            out = comum.transcricao_visual("visual-real-test", "OS-888-2099", plano, cons)
        self.assertEqual(http.call_count, 1)
        self.assertEqual(out["documentos"][0]["gravadas"], [1])
        self.assertTrue(tasks.indexado)
        self.assertEqual(tasks.estado["uso_ia"]["tokens"], 12)
        self.assertIn("123?", (self.pasta / "transcricao.md").read_text(encoding="utf-8"))
        self.assertTrue((self.pasta / "dados_extraidos.json").exists())
        self.assertEqual(json.loads((self.pasta / "relatorio_extracao.json").read_text(encoding="utf-8"))["ocr_workers"], 0)
        # Arquivo já gravado é retomado sem novo envio.
        with patch.object(EL, "_http_json", side_effect=AssertionError("API repetida")):
            comum.transcricao_visual("visual-retomada-test", "OS-888-2099", plano, cons)
        (self.pasta / "transcricoes_visuais/p0001.md").unlink()
        tasks.estado["status"] = "cancelada"
        self.assertTrue(comum.transcricao_visual("visual-cancelado-test", "OS-888-2099", plano, cons)["cancelada"])
        tasks.estado["status"] = "executando"
        (self.ws / "config/ia.json").write_text(json.dumps({"orcamento_por_pedido": {"tokens": 1}}))
        with patch.object(EL, "_http_json", return_value=resposta) as http:
            with self.assertRaises(EL.OrcamentoExcedido):
                comum.transcricao_visual("visual-teto-test", "OS-888-2099", plano, cons)
            self.assertEqual(http.call_count, 1)
            self.assertFalse((self.pasta / "transcricoes_visuais/p0001.md").exists())
        (self.ws / "config/ia.json").write_text("{}")
        atual = json.loads(meta_file.read_text(encoding="utf-8"))
        def altera_checkpoint(*a, **kw):
            meta_file.write_text(json.dumps(dict(atual, min_chars=atual["min_chars"] + 1)))
            return resposta
        with patch.object(EL, "_http_json", side_effect=altera_checkpoint), patch.object(comum, "rodar") as replay:
            with self.assertRaisesRegex(RuntimeError, "checkpoint|Checkpoint"):
                comum.transcricao_visual("visual-corrida-test", "OS-888-2099", plano, cons)
            replay.assert_not_called()
        meta_file.write_text(json.dumps(atual))
        (self.pasta / "transcricoes_visuais/p0001.md").unlink()
        orig.write_bytes(orig.read_bytes() + b"\n%MODIFICADO-FICTICIO")
        with patch.object(EL, "_http_json", return_value=resposta) as http:
            with self.assertRaisesRegex(RuntimeError, "original|SHA|checkpoint"):
                comum.transcricao_visual("visual-hash-test", "OS-888-2099", plano, cons)
            http.assert_not_called()

if __name__ == "__main__": unittest.main(verbosity=2)
