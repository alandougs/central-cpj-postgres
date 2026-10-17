"""RP01: relatório de cumprimento por período, somente cadastros fictícios em TEMP."""
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))


class ProducaoRP01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-rp01-")
        cls.ws = Path(cls.temp.name)
        cls.old_env = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
        (cls.ws / "casos").mkdir()
        (cls.ws / "producao").mkdir()
        (cls.ws / "producao/config.json").write_text(json.dumps({
            "investigador": "Policial Fictício", "unidade": "Unidade Fictícia"
        }), encoding="utf-8")
        import servidor
        cls.s = servidor
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("rp.admin", "Admin Fictício", "admin", "Ficticia123")
        servidor.auth.salvar_usuario("rp.inv", "Investigadora Fictícia", "investigador", "Ficticia123")
        servidor.auth.salvar_usuario("rp.esc", "Escrivão Fictício", "escrivao", "Ficticia123")
        (cls.ws / "config/solo.json").write_text('{"ativo": true}', encoding="utf-8")
        cls.snapshot = {}
        for n in range(1, 16):
            cls.gravar(n, "2026-10-14", natureza="Estelionato", responsavel="rp.inv" if n == 1 else "")
        cls.gravar(16, "2026-10-01", natureza="Furto")
        cls.gravar(17, "2026-09-30")
        cls.gravar(18, "2026-10-15")
        cls.gravar(19, "2026-10-14", status="minuta")
        cls.gravar(20, None)

    @classmethod
    def gravar(cls, n, entregue, natureza="Estelionato", responsavel="", status="entregue"):
        cid = f"OS-{n}-2026"
        p = cls.ws / "casos" / cid / "caso.json"
        p.parent.mkdir()
        content = json.dumps({
            "id": cid, "ordem_servico": f"{n}/2026", "natureza": natureza,
            "status": status, "responsavel": responsavel,
            "datas": {"entregue": entregue},
            "baixa": {"arquivo": "RELATORIO.docx", "data": entregue},
            "relatorios": [{"arquivo": "C:\\FICTICIO\\RELATORIO.docx", "data": "2026-10-01"},
                           {"arquivo": "outra-minuta.docx", "data": "2026-10-13"}],
            "vitimas": ["NOME SIGILOSO FICTICIO"], "investigados": ["CPF SIGILOSO FICTICIO"],
            "financeiro": {"valor_rastreado": 12345}
        }, ensure_ascii=False)
        p.write_text(content, encoding="utf-8")
        cls.snapshot[p] = p.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
        if cls.old_env is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.old_env

    def get(self, query="inicio=2026-10-01&fim=2026-10-14", login=None):
        with self.s.app.test_client() as client:
            if login:
                r = client.post("/api/entrar", headers={"X-CPJ": "1"},
                                json={"login": login, "senha": "Ficticia123"})
                self.assertEqual(r.status_code, 200)
            return client.get("/api/producao/relatorio?" + query)

    def test_intervalo_inclusivo_lista_completa_e_total_sem_dados_dos_autos(self):
        r = self.get()
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn('id="total-cumpridas">16<', html)
        for n in range(1, 17):
            self.assertIn(f">{n}/2026<", html)
        for n in range(17, 21):
            self.assertNotIn(f">{n}/2026<", html)
        self.assertIn("Data do relatório", html)
        self.assertIn("Data de cumprimento", html)
        self.assertIn("Investigadora Fictícia", html)
        self.assertIn("Policial Fictício", html)
        for sigilo in ["NOME SIGILOSO", "CPF SIGILOSO", "12345"]:
            self.assertNotIn(sigilo, html)
        self.assertIn("Estelionato: 15", html)
        self.assertIn("Furto: 1", html)
        self.assertIn("sem data de cumprimento", html)
        for p, original in self.snapshot.items():
            self.assertEqual(p.read_bytes(), original, "GET não deve alterar o cadastro")

    def test_csv_mesmo_periodo_e_data_relatorio_da_versao_entregue(self):
        r = self.get("inicio=2026-10-14&fim=2026-10-14&formato=csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r.headers.get("Content-Disposition", ""))
        rows = list(csv.DictReader(io.StringIO(r.data.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[0], {"O.S.": "1/2026", "Data do relatório": "01/10/2026",
                                  "Data de cumprimento": "14/10/2026", "Natureza": "Estelionato",
                                  "Policial responsável": "Investigadora Fictícia"})

    def test_periodo_vazio_tem_total_zero(self):
        r = self.get("inicio=2026-11-01&fim=2026-11-30")
        self.assertEqual(r.status_code, 200)
        self.assertIn('id="total-cumpridas">0<', r.get_data(as_text=True))

    def test_rejeita_periodos_invalidos_e_formato_desconhecido(self):
        for q in ["", "inicio=2026-10-14", "inicio=2026-10-15&fim=2026-10-14",
                  "inicio=2026-02-30&fim=2026-10-14", "inicio=20261001&fim=2026-10-14",
                  "inicio=2026-10-01&fim=2026-10-14&formato=exe"]:
            with self.subTest(query=q):
                self.assertEqual(self.get(q).status_code, 400)

    def test_exige_permissao_estatisticas(self):
        self.assertEqual(self.get(login="rp.esc").status_code, 403)

    def test_dados_ausentes_e_conteudo_cadastral_escapado(self):
        from relatorio_producao import preparar, html_relatorio, csv_relatorio
        d = preparar([{"id": "OS-99-2026", "ordem_servico": "99/2026", "status": "entregue",
                       "datas": {"entregue": "2026-10-14"}, "natureza": "<script>alert(1)</script>",
                       "responsavel": "=usuario", "relatorios": []}],
                     "2026-10-14", "2026-10-14", {}, {})
        html = html_relatorio(d)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Não informada", html)
        row = list(csv.reader(io.StringIO(csv_relatorio(d)), delimiter=";"))[1]
        self.assertEqual(row[1], "Não informada")
        self.assertEqual(row[-1], "'=usuario")

    def test_interface_emite_periodo_escolhido_e_pdf_completo(self):
        from werkzeug.serving import make_server
        runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
        node = shutil.which("node") or str(runtime / "bin/node.exe")
        env = dict(os.environ, NODE_PATH=str(runtime / "node_modules"))
        server = make_server("127.0.0.1", 0, self.s.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        script = r'''
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const context=await browser.newContext();
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(__BASE__+'/#estatisticas');
  await page.locator('#prod-inicio').fill('2026-10-01');
  await page.locator('#prod-fim').fill('2026-10-14');
  const popupPromise=page.waitForEvent('popup');
  await page.getByRole('button',{name:'Gerar relatório',exact:true}).click();
  const report=await popupPromise;await report.waitForLoadState();
  assert.equal(new URL(report.url()).searchParams.get('inicio'),'2026-10-01');
  assert.equal(new URL(report.url()).searchParams.get('fim'),'2026-10-14');
  assert.equal(await report.locator('#total-cumpridas').innerText(),'16');
  assert.equal(await report.locator('tbody tr').count(),16);
  assert.ok(await report.getByRole('button',{name:'Imprimir / salvar PDF'}).isVisible());
  await report.emulateMedia({media:'print'});
  assert.equal(await report.locator('.acoes').isVisible(),false);
  const pdf=await report.pdf({format:'A4',printBackground:true});
  assert.ok(pdf.length>5000);
  require('node:fs').writeFileSync(PDF,pdf);
  await report.emulateMedia({media:'screen'});
  await report.screenshot({path:SCREEN,fullPage:true});
  assert.deepEqual(errors,[]);
  await context.close();console.log('UI RP01: período, 16 linhas, impressão e PDF verificados.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''.replace("__BASE__", json.dumps(f"http://127.0.0.1:{server.server_port}"))
        script = script.replace("PDF,pdf", json.dumps(str(self.ws / "relatorio-teste.pdf")) + ",pdf")
        script = script.replace("SCREEN", json.dumps(str(self.ws / "relatorio-teste.png")))
        try:
            r = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8", env=env,
                               capture_output=True, timeout=90)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            from pypdf import PdfReader
            text = "\n".join(p.extract_text() for p in PdfReader(self.ws / "relatorio-teste.pdf").pages)
            self.assertIn("16/2026", text)
            self.assertIn("Policial Fictício", text)
            self.assertIn("Total de O.S. cumpridas", text)
            print(r.stdout.strip())
            if os.environ.get("CPJ_RP01_PREVIEW"):
                shutil.copyfile(self.ws / "relatorio-teste.png", os.environ["CPJ_RP01_PREVIEW"])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
