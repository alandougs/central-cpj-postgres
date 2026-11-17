"""SEC21: arquivos, origem, escuta e WSGI; somente fixtures temporárias."""
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest


APP = Path(__file__).resolve().parents[1]


class WebSEC21(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-web-sec21-")
        cls.ws = Path(cls.temp.name)
        cls.env = {k: os.environ.get(k) for k in ("CPJ_WORKSPACE", "CPJ_SEM_AGENTE_EMBUTIDO")}
        os.environ.update(CPJ_WORKSPACE=str(cls.ws), CPJ_SEM_AGENTE_EMBUTIDO="1")
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({
            "datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []
        }), encoding="utf-8")
        sys.path.insert(0, str(APP))
        import servidor
        cls.s = servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve()
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_sec21", "Administrador fictício", "admin", "Ficticia123")
        cls.id = servidor.C.novo("921/2099")["id"]
        cls.pasta = Path(servidor.C.caminho(cls.id))

    @classmethod
    def tearDownClass(cls):
        for arquivo in cls.ws.rglob("*"):
            if arquivo.is_file():
                arquivo.chmod(0o600)
        cls.temp.cleanup()
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        self.s.app.config.update(REDE_ATIVA=False, CPJ_HOSTS_REDE=(), SESSION_COOKIE_SECURE=False)
        self.client = self.s.app.test_client()
        self.assertEqual(self.client.post("/api/entrar", json={
            "login": "admin_sec21", "senha": "Ficticia123"
        }, headers={"X-CPJ": "1"}).status_code, 200)

    def arquivo(self, nome, conteudo):
        (self.pasta / "00-originais" / nome).write_bytes(conteudo)
        return self.client.get(f"/arquivo/{self.id}/00-originais/{nome}")

    def test_html_svg_e_tipo_desconhecido_baixados_sem_execucao(self):
        for nome in ("ataque.HTML", "ataque.svg", "ataque.xhtml", "ataque.xml", "ataque.bin", "ataque"):
            with self.subTest(nome=nome):
                with self.arquivo(nome, b"<svg onload='fetch(\"/api/sessao\")'></svg>") as r:
                    self.assertEqual(r.status_code, 200)
                    self.assertTrue(r.headers.get("Content-Disposition", "").startswith("attachment"))
                    self.assertEqual(r.mimetype, "application/octet-stream")
                    self.assertIn("sandbox", r.headers.get("Content-Security-Policy", ""))
                    self.assertNotIn("unsafe-inline", r.headers["Content-Security-Policy"])

    def test_texto_e_imagem_raster_continuam_inline_com_mime_fixo(self):
        for nome, conteudo, mime in (("texto.md", b"<script>alert(1)</script>", "text/plain"),
                                      ("imagem.png", b"\x89PNG\r\n\x1a\n", "image/png")):
            with self.subTest(nome=nome):
                with self.arquivo(nome, conteudo) as r:
                    self.assertEqual(r.mimetype, mime)
                    self.assertFalse(r.headers["Content-Disposition"].startswith("attachment"))
                    self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")

    def test_pdf_continua_inline_e_docx_continua_download(self):
        with self.arquivo("relatorio.PDF", b"%PDF-1.4\n%%EOF") as r:
            self.assertEqual(r.mimetype, "application/pdf")
            self.assertTrue(r.headers["Content-Disposition"].startswith("inline"))
        with self.arquivo("relatorio.docx", b"PK") as r:
            self.assertTrue(r.headers["Content-Disposition"].startswith("attachment"))

    def test_pagina_principal_recebe_csp_compativel_com_scripts_existentes(self):
        with self.client.get("/") as r:
            csp = r.headers.get("Content-Security-Policy", "")
            self.assertIn("base-uri 'none'", csp)
            self.assertIn("frame-ancestors 'self'", csp)
            self.assertIn("script-src 'self' 'unsafe-inline'", csp)
            self.assertIn("connect-src 'self'", csp)

    def test_host_de_rebinding_e_encaminhamento_forjado_nao_dao_acesso(self):
        for host in ("evil.example", "localhost.evil.example", "127.0.0.1.evil.example"):
            with self.subTest(host=host):
                r = self.client.get("/api/casos", headers={"Host": host, "X-Forwarded-Host": "localhost"})
                self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.get("/api/casos", headers={"Host": "localhost"}).status_code, 200)

    def test_origin_externo_ou_nulo_rejeitado_mesmo_com_cabecalho_cpj(self):
        for origem in ("https://evil.example", "null", "http://localhost:8888", "http://localhost:0",
                       "http://localhost/ataque"):
            with self.subTest(origem=origem):
                r = self.client.post("/api/sair", headers={"X-CPJ": "1", "Origin": origem})
                self.assertEqual(r.status_code, 403)
                self.assertEqual(self.client.get("/api/casos").status_code, 200)

    def test_origin_correto_e_cliente_sem_origin_preservados(self):
        self.assertEqual(self.client.post("/api/minha-conta", json={"cargo": "Fictício"},
                                         headers={"X-CPJ": "1", "Origin": "http://localhost"}).status_code, 200)
        self.assertEqual(self.client.post("/api/minha-conta", json={"cargo": "Fictício"},
                                         headers={"X-CPJ": "1"}).status_code, 200)
        self.assertEqual(self.client.post("/api/sair", headers={"Origin": "http://localhost"}).status_code, 403)

    def test_compartilhamento_sem_https_rejeitado_antes_de_gravar(self):
        rede = self.ws / "config" / "rede.json"
        antes = rede.read_bytes() if rede.exists() else None
        r = self.client.post("/api/rede", json={"compartilhar": True, "https": False}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("HTTPS", r.json["erro"])
        self.assertEqual(rede.read_bytes() if rede.exists() else None, antes)

    def test_rede_ativa_aceita_somente_host_explicito_e_https(self):
        self.s.app.config.update(REDE_ATIVA=True, CPJ_HOSTS_REDE=("192.0.2.21",))
        remoto = {"REMOTE_ADDR": "192.0.2.22"}
        self.assertEqual(self.client.get("/api/sessao", base_url="http://192.0.2.21:8765",
                                         environ_overrides=remoto).status_code, 403)
        r = self.client.get("/api/sessao", base_url="https://192.0.2.21:8765", environ_overrides=remoto)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/api/sessao", base_url="https://evil.example",
                                         environ_overrides=remoto).status_code, 400)

    def test_configuracao_legada_http_nao_abre_rede_e_senha_temporaria_recua_a_local(self):
        from web_seguro import configurar_escuta
        with self.assertRaises(ValueError):
            configurar_escuta({"compartilhar": True, "https": False}, "127.0.0.1")
        self.assertEqual(configurar_escuta({"compartilhar": True, "https": False}, "127.0.0.1", True),
                         ("127.0.0.1", False))
        self.assertEqual(configurar_escuta({"compartilhar": True, "https": True}, "127.0.0.1"),
                         ("0.0.0.0", True))
        self.assertEqual(configurar_escuta({"compartilhar": True, "https": True}, "127.0.0.1",
                                         senha_temporaria=True), ("127.0.0.1", False))
        with self.assertRaises(ValueError):
            self.s.criar_servidor_wsgi(self.s.app, "0.0.0.0", 0)

    def test_navegador_baixa_html_e_renderiza_pdf_no_iframe(self):
        import threading
        from pypdf import PdfWriter

        runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
        node = shutil.which("node") or str(runtime / "bin/node.exe")
        if not Path(node).is_file():
            self.skipTest("Node/Playwright necessário ao teste de navegador")
        env = dict(os.environ)
        if (runtime / "node_modules/playwright").exists():
            env["NODE_PATH"] = str(runtime / "node_modules")
        pdf = PdfWriter()
        pdf.add_blank_page(width=300, height=300)
        with open(self.pasta / "00-originais" / "previa.pdf", "wb") as destino:
            pdf.write(destino)
        (self.pasta / "00-originais" / "ativo.html").write_text(
            "<script>fetch('/execucao-indevida-sec21')</script>", encoding="utf-8")
        server = self.s.criar_servidor_wsgi(self.s.app, "127.0.0.1", 0)
        server.prepare()
        thread = threading.Thread(target=server.serve, daemon=True)
        thread.start()
        fixture = json.dumps({"url": f"http://127.0.0.1:{server.bind_addr[1]}", "caso": self.id})
        script = r'''
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const f = FIXTURE;
(async () => {
 const browser = await chromium.launch({headless: true, channel: process.env.CPJ_BROWSER_CHANNEL || 'msedge'});
 try {
  const context = await browser.newContext({acceptDownloads: true});
  const login = await context.request.post(f.url+'/api/entrar', {headers: {'X-CPJ':'1'},
    data: {login:'admin_sec21',senha:'Ficticia123'}});
  assert.equal(login.status(), 200);
  const page = await context.newPage(), erros = [], indevidas = [];
  page.on('pageerror', e => erros.push(e.message));
  page.on('console', m => {if (m.type()==='error') erros.push(m.text())});
  page.on('request', r => {if(r.url().includes('execucao-indevida-sec21')) indevidas.push(r.url())});
  await page.goto(f.url+'/#casos');
  await page.waitForLoadState('networkidle');
  const base = '/arquivo/'+f.caso+'/00-originais/';
  const [download] = await Promise.all([page.waitForEvent('download'), page.evaluate(url => {
    const a=document.createElement('a');a.href=url;document.body.append(a);a.click();
  }, base+'ativo.html')]);
  assert.equal(download.suggestedFilename(), 'ativo.html');
  await page.evaluate(url => {const i=document.createElement('iframe');i.id='pdf-sec21';i.src=url;
    document.body.append(i)}, base+'previa.pdf');
  const frame = page.frameLocator('#pdf-sec21');
  await frame.locator('embed[type="application/pdf"]').waitFor({state:'attached',timeout:10000});
  assert.deepEqual(indevidas, []);
  assert.deepEqual(erros, []);
  assert.equal((await context.request.get(f.url+'/api/casos')).status(),200);
  await context.close();
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''.replace("FIXTURE", fixture)
        try:
            r = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8", env=env,
                               capture_output=True, timeout=45)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        finally:
            server.stop()
            thread.join(timeout=5)

    def test_cli_rejeita_host_nao_local_sem_modo_https(self):
        with tempfile.TemporaryDirectory(prefix="cpj-cli-sec21-") as ws:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                porta = listener.getsockname()[1]
            try:
                p = subprocess.run([sys.executable, "-X", "utf8", str(APP / "servidor.py"),
                                    "--workspace", ws, "--host", "0.0.0.0", "--porta", str(porta),
                                    "--somente-local", "--sem-navegador"],
                                   env=dict(os.environ, CPJ_WORKSPACE=ws), capture_output=True, text=True, timeout=8)
            except subprocess.TimeoutExpired:
                self.fail("CLI iniciou escuta de rede sem HTTPS em vez de rejeitar --host")
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("HTTPS", p.stdout + p.stderr)

    def test_wsgi_http_local_e_https_real_preservam_protocolo_e_cookie(self):
        criar = getattr(self.s, "criar_servidor_wsgi", None)
        self.assertTrue(callable(criar), "Entrada WSGI de produção ausente")
        import threading
        for tls in (False, True):
            with self.subTest(tls=tls):
                cert = self.s.certificado() if tls else None
                self.s.app.config.update(REDE_ATIVA=tls, SESSION_COOKIE_SECURE=tls)
                server = criar(self.s.app, "127.0.0.1", 0, cert)
                server.prepare()
                thread = threading.Thread(target=server.serve, daemon=True)
                thread.start()
                port = server.bind_addr[1]
                try:
                    if tls:
                        context = ssl.create_default_context(cafile=cert[0])
                        conn = http.client.HTTPSConnection("127.0.0.1", port, context=context, timeout=4)
                    else:
                        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
                    body = json.dumps({"login": "admin_sec21", "senha": "Ficticia123"})
                    conn.request("POST", "/api/entrar", body, {"Content-Type": "application/json", "X-CPJ": "1"})
                    response = conn.getresponse()
                    self.assertEqual(response.status, 200)
                    cookie = response.getheader("Set-Cookie")
                    self.assertIn("HttpOnly", cookie)
                    self.assertIn("SameSite=Strict", cookie)
                    self.assertEqual("; Secure" in cookie, tls)
                    self.assertIn("Cheroot", response.getheader("Server"))
                    response.read()
                    conn.close()
                    if tls:
                        with socket.create_connection(("127.0.0.1", port), timeout=3) as plain:
                            plain.sendall(b"GET /api/sessao HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
                            try:
                                data = plain.recv(4096)
                            except (OSError, TimeoutError):
                                data = b""
                            self.assertNotIn(b"200 OK", data)
                            self.assertNotIn(b'"usuario"', data)
                finally:
                    server.stop()
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
