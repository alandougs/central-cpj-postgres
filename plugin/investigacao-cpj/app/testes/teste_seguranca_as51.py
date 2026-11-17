"""AS51: regressões AS50 de login, auditoria e badge; dados só temporários."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import auth


class AuditoriaAS51(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-as51-auditoria-")
        self.addCleanup(self.tmp.cleanup)
        self.a = auth.Auth(self.tmp.name)

    def test_append_nao_rele_historico_cumulativamente(self):
        original = Path.read_bytes
        lidos = []

        def ler(p):
            raw = original(p)
            if str(p) == self.a.log:
                lidos.append(len(raw))
            return raw

        with patch.object(Path, "read_bytes", ler):
            for n in range(40):
                self.a.auditar("ficticio", "local", "evento", str(n))
        self.assertLessEqual(sum(lidos), Path(self.a.log).stat().st_size * 2,
                             "Append relê e verifica repetidamente o histórico inteiro")
        self.assertEqual(self.a.verificar_auditoria()["registros_protegidos"], 40)

    def test_cache_invalida_edicao_mesmo_tamanho_e_mtime_restaurado(self):
        self.a.auditar("ficticio", "local", "primeiro")
        p = Path(self.a.log)
        antes = p.stat()
        p.write_bytes(p.read_bytes().replace(b"primeiro", b"alterado"))
        os.utime(p, ns=(antes.st_atime_ns, antes.st_mtime_ns))
        adulterado = p.read_bytes()
        with self.assertRaises(RuntimeError):
            self.a.auditar("ficticio", "local", "nao_gravar")
        self.assertEqual(p.read_bytes(), adulterado)

    def test_cache_invalida_truncamento_remocao_troca_log_e_ancora(self):
        import seguranca_local as S
        for ataque in ("truncar", "remover", "trocar_log", "trocar_ancora", "remover_ancora"):
            with self.subTest(ataque=ataque), tempfile.TemporaryDirectory(prefix="cpj-as51-troca-") as ws:
                a = auth.Auth(ws)
                a.auditar("ficticio", "local", "primeiro")
                a.auditar("ficticio", "local", "segundo")
                log = Path(a.log)
                ancora = S.caminho_ancora_auditoria(ws)
                if ataque == "truncar": log.write_bytes(log.read_bytes().splitlines()[0] + b"\n")
                elif ataque == "remover": log.unlink()
                elif ataque == "remover_ancora": ancora.unlink()
                else:
                    with tempfile.TemporaryDirectory(prefix="cpj-as51-outro-") as outro:
                        b = auth.Auth(outro)
                        b.auditar("ficticio", "local", "primeiro")
                        b.auditar("ficticio", "local", "segundo")
                        fonte, destino = ((Path(b.log), log) if ataque == "trocar_log"
                                          else (S.caminho_ancora_auditoria(outro), ancora))
                        temporario = destino.with_suffix(".substituto")
                        temporario.write_bytes(fonte.read_bytes())
                        os.replace(temporario, destino)
                with self.assertRaises(RuntimeError): a.auditar("ficticio", "local", "nao_gravar")
                self.assertFalse(a.verificar_auditoria()["integra"])

    def test_mudanca_por_outro_escritor_invalida_e_continua_cadeia(self):
        self.a.auditar("ficticio", "local", "um")
        b = auth.Auth(self.tmp.name)
        b.auditar("ficticio", "local", "dois")
        self.a.auditar("ficticio", "local", "tres")
        self.assertEqual([r["acao"] for r in self.a.auditoria()], ["tres", "dois", "um"])

    def test_falha_persistir_ancora_nao_reutiliza_cache(self):
        import seguranca_local as S
        self.a.auditar("ficticio", "local", "antes")
        with patch.object(S, "gravar_atomico_restrito", side_effect=OSError("ficticio")):
            with self.assertRaises(RuntimeError): self.a.auditar("ficticio", "local", "falha")
        with self.assertRaises(RuntimeError): self.a.auditar("ficticio", "local", "nao_gravar")
        self.assertFalse(self.a.verificar_auditoria()["integra"])

    def test_sem_marca_confiavel_verifica_cadeia_inteira(self):
        self.a.auditar("ficticio", "local", "primeiro")
        with patch.object(self.a, "_marca_auditoria", return_value=None):
            self.a.auditar("ficticio", "local", "segundo")
            p = Path(self.a.log)
            p.write_bytes(p.read_bytes().replace(b"primeiro", b"alterado"))
            with self.assertRaises(RuntimeError): self.a.auditar("ficticio", "local", "nao_gravar")

    def test_nao_adota_cache_se_log_mudar_durante_gravacao_da_ancora(self):
        import seguranca_local as S
        self.a.auditar("ficticio", "local", "primeiro")
        original = S.proteger

        def proteger(dados):
            p = Path(self.a.log)
            p.write_bytes(p.read_bytes().replace(b"primeiro", b"alterado"))
            return original(dados)

        with patch.object(S, "proteger", proteger):
            with self.assertRaises(RuntimeError): self.a.auditar("ficticio", "local", "segundo")
        with self.assertRaises(RuntimeError): self.a.auditar("ficticio", "local", "nao_gravar")


class LoginAS51(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-as51-http-")
        cls.env = patch.dict(os.environ, {"CPJ_WORKSPACE": cls.tmp.name})
        cls.env.start()
        import rotas.comum as comum
        from rotas.usuarios import bp_usuarios
        from flask import Flask
        if Path(comum.WS).resolve() != Path(cls.tmp.name).resolve():
            raise RuntimeError("Executar AS51 em processo isolado")
        cls.s = comum
        cls.app = Flask(__name__)
        cls.app.config.update(TESTING=True, SECRET_KEY="segredo-ficticio-as51")
        cls.app.register_blueprint(bp_usuarios)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-as51-login-")
        self.addCleanup(self.tmp.cleanup)
        self.a = auth.Auth(self.tmp.name)
        self.a.salvar_usuario("ficticio", "Pessoa Ficticia", "admin", "SenhaFicticia123")
        self.original = self.s._auth_inst
        self.s.auth._inst = self.a
        self.addCleanup(setattr, self.s.auth, "_inst", self.original)
        self.client = self.app.test_client()
        self.sleep = patch.object(auth.time, "sleep", return_value=None)
        self.sleep.start()
        self.addCleanup(self.sleep.stop)

    def entrar(self, dados, origem="192.0.2.1"):
        return self.client.post("/api/entrar", json=dados, headers={"X-CPJ": "1"},
                                environ_overrides={"REMOTE_ADDR": origem})

    def test_login_rejeita_tipos_e_comprimentos_sem_excecao_ou_auditar(self):
        invalidos = [[], ["login"], "texto", 7, {"login": []}, {"login": {}},
                     {"login": 3}, {"login": "x" * 257}, {"login": "ficticio", "senha": []},
                     {"login": "ficticio", "senha": 3}, {"senha": "x" * 1025}]
        for dados in invalidos:
            with self.subTest(dados=repr(dados)[:60]):
                r = self.entrar(dados)
                self.assertEqual(r.status_code, 400)
                self.assertIsInstance(r.json.get("erro"), str)
        self.assertFalse(Path(self.a.log).exists())

    def test_login_rejeita_json_incompleto_e_corpo_excessivo_inclusive_sem_content_length(self):
        import io
        for corpo in (b'{"login":', b"[" * 3000 + b"]" * 3000,
                      b"[" * 4090 + b"]" * 4090,
                      b'{"extra":"' + b"x" * 9000 + b'"}'):
            for sem_tamanho in (False, True):
                with self.subTest(tamanho=len(corpo), sem_tamanho=sem_tamanho):
                    if sem_tamanho:
                        kw = {"environ_overrides": {"wsgi.input": io.BytesIO(corpo),
                                                      "wsgi.input_terminated": True, "CONTENT_LENGTH": ""}}
                    else: kw = {"data": corpo}
                    r = self.client.post("/api/entrar", content_type="application/json", **kw)
                    self.assertEqual(r.status_code, 400)
                    self.assertIsInstance(r.json.get("erro"), str)
        self.assertFalse(Path(self.a.log).exists())

    def test_rotacao_de_login_limitada_por_origem_sem_amplificar_auditoria(self):
        with patch.object(auth.time, "monotonic", return_value=1000):
            respostas = [self.entrar({"login": f"ausente_{n}", "senha": "errada"}) for n in range(80)]
            self.assertIn(429, [r.status_code for r in respostas])
            eventos = self.a.auditoria()
            self.assertLessEqual(len(eventos), 20)
            self.assertGreater(len(eventos), 0)
            r = self.entrar({"login": "ficticio", "senha": "SenhaFicticia123"}, "192.0.2.2")
            self.assertEqual(r.status_code, 200)
        with patch.object(auth.time, "monotonic", return_value=1401):
            self.assertEqual(self.entrar({"login": "ficticio", "senha": "SenhaFicticia123"}).status_code, 200)

    def test_rotacao_de_origem_limitada_globalmente(self):
        with patch.object(auth.time, "monotonic", return_value=1000):
            respostas = [self.entrar({"login": f"ausente_{n}", "senha": "errada"}, f"192.0.2.{n}")
                         for n in range(150)]
        self.assertIn(429, [r.status_code for r in respostas])
        self.assertLessEqual(len(self.a.auditoria()), 100)

    def test_estado_de_falhas_expira_e_tem_capacidade_limitada(self):
        with patch.object(auth.time, "monotonic", return_value=1000):
            for n in range(30):
                with self.assertRaises(PermissionError):
                    self.a.autenticar(f"ausente_{n}", "errada", origem=f"192.0.2.{n}")
        with patch.object(auth.time, "monotonic", return_value=2000):
            with self.assertRaises(PermissionError): self.a.autenticar("outro", "errada")
        self.assertLessEqual(len(self.a._falhas), 1)
        with patch.object(auth, "_MAX_ESTADOS_LOGIN", 8), patch.object(auth.time, "monotonic", return_value=3000):
            for n in range(30):
                with self.assertRaises(PermissionError):
                    self.a.autenticar(f"ausente_{n}", "errada", origem=f"192.0.2.{n}")
            self.assertLessEqual(len(self.a._falhas), 8)
            self.assertLessEqual(len(self.a._origens_login), 8)
            self.assertEqual(self.a.autenticar("ficticio", "SenhaFicticia123", origem="192.0.2.90")["login"], "ficticio")

    def test_cinco_falhas_bloqueiam_conta_e_expiram(self):
        with patch.object(auth.time, "monotonic", return_value=1000):
            for n in range(5):
                with self.assertRaises(PermissionError):
                    self.a.autenticar("ficticio", "errada", origem=f"192.0.2.{n}")
            with self.assertRaises(PermissionError):
                self.a.autenticar("ficticio", "SenhaFicticia123", origem="192.0.2.80")
            bloqueada = self.entrar({"login": "ficticio", "senha": "SenhaFicticia123"}, "192.0.2.81")
            self.assertEqual(bloqueada.status_code, 429)
            self.assertIn("tentativas", bloqueada.json["erro"])
            self.assertFalse(Path(self.a.log).exists(), "Bloqueio não deve gerar mais eventos de login falho")
        with patch.object(auth.time, "monotonic", return_value=1301):
            self.assertEqual(self.a.autenticar("ficticio", "SenhaFicticia123")["login"], "ficticio")

    def test_logins_validos_nao_consumem_cota_de_falhas(self):
        with patch.object(auth.time, "monotonic", return_value=1000):
            for n in range(25):
                self.assertEqual(self.entrar({"login": "ficticio", "senha": "SenhaFicticia123"}).status_code, 200)


class BadgeAS51(unittest.TestCase):
    def test_datas_em_html_escapam_markup_preservando_datas_validas(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node necessário para executar core.js real")
        script = r'''
const fs = require("fs"), vm = require("vm"), assert = require("node:assert/strict");
const el = {addEventListener(){}};
const contexto = {document: {querySelector(){return el}}};
vm.createContext(contexto);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), contexto);
assert.equal(vm.runInContext('dt("<svg>")', contexto), '&lt;svg&gt;');
assert.equal(vm.runInContext('dt("2026-10-30T12:00:00")', contexto), '30/10/2026');
assert.equal(vm.runInContext('dt(null)', contexto), '—');
assert.equal(vm.runInContext('prazoBadge({prazo:"<svg>"})', contexto), '<span class="muted">&lt;svg&gt;</span>');
assert.equal(vm.runInContext('prazoBadge({prazo:"<svg>",situacao_prazo:"proximo"})', contexto), '<span class="badge pz-proximo">⏳ &lt;svg&gt;</span>');
'''
        r = subprocess.run([node, "-e", script, str(APP / "static" / "js" / "core.js")],
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_badge_exibe_status_desconhecido_como_texto(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node necessário para executar core.js real")
        script = r'''
const fs = require("fs"), vm = require("vm"), assert = require("node:assert/strict");
const el = {addEventListener(){}};
const contexto = {document: {querySelector(){return el}}};
vm.createContext(contexto);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), contexto);
vm.runInContext('Object.hasOwn=undefined', contexto); // Compatibilidade com o motor QuickJS dos testes.
const badge = st => vm.runInContext(`badge(${JSON.stringify(st)})`, contexto);
assert.equal(badge('<img src=x onerror="alert(1)">'), '<span class="badge "><i aria-hidden="true"></i>&lt;img src=x onerror=&quot;alert(1)&quot;&gt;</span>');
assert.equal(badge('__proto__'), '<span class="badge "><i aria-hidden="true"></i>__proto__</span>');
assert.equal(badge('concluido'), '<span class="badge b-ok"><i aria-hidden="true"></i>concluído</span>');
'''
        r = subprocess.run([node, "-e", script, str(APP / "static" / "js" / "core.js")],
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__": unittest.main(verbosity=2)
