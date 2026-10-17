"""Teste UN17: python -X utf8 app/testes/teste_publicacao_un17.py.

Verificador de sigilo (somente leitura) e fiscalização do workflow de CI. Repositórios Git temporários,
com segredos montados em tempo de execução (nenhum literal de segredo no código-fonte) e dados fictícios.
"""
import gzip
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VERIFICADOR = ROOT / "ferramentas" / "verificar-publicacao.py"
WORKFLOW = ROOT / ".github" / "workflows" / "validacao.yml"

# Montados por concatenação: este arquivo não pode conter um segredo literal que o próprio verificador acusaria.
CHAVE_PRIVADA = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIB" + "A" * 40 + "\n-----END " + "RSA PRIVATE KEY-----\n"
TOKEN_ANT = "sk-" + "ant-" + "api03-" + "Zx9Qv" * 8
TOKEN_GH = "gh" + "p_" + "A1b2C3d4E5" * 3 + "F6g7H8"
CHAVE_AWS = "AK" + "IA" + "ABCDEFGH12345678"
SEGREDO_ATRIBUIDO = "R7vQ2mXk9LpT4wZn8cYb3HfJ"
CPF_VALIDO = "529.982.247-25"
SEGREDOS_DO_TESTE = (CHAVE_PRIVADA.splitlines()[1], TOKEN_ANT, TOKEN_GH, CHAVE_AWS, SEGREDO_ATRIBUIDO, CPF_VALIDO)


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return r.stdout


def verificar(repo, *args):
    return subprocess.run([sys.executable, "-X", "utf8", str(VERIFICADOR), "-C", str(repo), *args], capture_output=True,
                          text=True, encoding="utf-8", timeout=120, env=dict(os.environ, PYTHONUTF8="1"))


def escrever(repo, rel, conteudo="fictício\n"):
    caminho = Path(repo) / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, bytes):
        caminho.write_bytes(conteudo)
    else:
        caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def achados(saida):
    return {tuple(m.groups()) for m in re.finditer(r"^(\w\d\d) [^:\n]+: (.+?)(?::\d+)?$", saida, flags=re.M)}


@unittest.skipUnless(shutil.which("git"), "git é requisito do verificador; sem git este teste não prova nada")
class VerificadorDePublicacao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un17-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        escrever(self.repo, "README.md", "# projeto fictício\n")
        escrever(self.repo, "plugin/app/servidor.py", "print('ok')\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")

    def preparar(self, **arquivos):
        for rel, conteudo in arquivos.items():
            escrever(self.repo, rel.replace("__", "/"), conteudo)

    def test_repositorio_limpo_e_aprovado(self):
        r = verificar(self.repo, "--ref", "HEAD")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 achado(s)", r.stdout)

    def test_caminhos_proibidos_sao_acusados_e_permitidos_passam(self):
        proibidos = {
            "casos/OS-1-2099/caso.json": ("P01", "{}"), "config/usuarios.json": ("P02", "{}"), "banco/plantao.sqlite": ("P03", "x"),
            "app/dados.db": ("P03", "x"), ".env": ("P04", "FICTICIO=1\n"), "app/.env.local": ("P04", "FICTICIO=1\n"),
            "chaves/servidor.pem": ("P04", "x"), "modelos/assinaturas/a.txt": ("P05", "x"), "modelos/assinatura-final.txt": ("P05", "x"),
            "rag/cpj.txt": ("P06", "x"), "producao/dados.csv": ("P06", "a,b\n"), "ordens-de-servico/os.txt": ("P06", "x"),
            "modelos/MODELO.docx": ("P07", b"PK\x03\x04"), "autos/ip.pdf": ("P07", b"%PDF-1.4\n"), "static/brasao.png": ("P07", b"\x89PNG")}
        permitidos = {
            ".env.example": "CPJ_PORTA=8765\n", "casos/_MODELO-CASO/caso.json": "{}", "rag/README.md": "# rag\n",
            "producao/config.json": "{}", "config/.gitkeep": "", "docs/arquitetura.md": "# ok\n"}
        for rel, (_, c) in proibidos.items():
            escrever(self.repo, rel, c)
        for rel, c in permitidos.items():
            escrever(self.repo, rel, c)
        git(self.repo, "add", "-A", "-f")
        r = verificar(self.repo, "--staged")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(achados(r.stdout), {(regra, rel) for rel, (regra, _) in proibidos.items()})
        for rel in permitidos:
            self.assertNotIn(rel, r.stdout)

    def test_segredos_no_conteudo_sao_acusados_sem_imprimir_o_valor(self):
        escrever(self.repo, "deploy/id.txt", CHAVE_PRIVADA)
        escrever(self.repo, "app/cliente.py", f'TOKEN = "{TOKEN_ANT}"\n')
        escrever(self.repo, "app/git.py", f'x = "{TOKEN_GH}"\n')
        escrever(self.repo, "app/aws.py", f'chave = "{CHAVE_AWS}"\n')
        escrever(self.repo, "app/config.py", f'API_KEY = "{SEGREDO_ATRIBUIDO}"\n')
        escrever(self.repo, "docs/relato.md", f"Investigado CPF {CPF_VALIDO}\n")
        git(self.repo, "add", "-A")
        r = verificar(self.repo, "--staged")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(achados(r.stdout), {("C01", "deploy/id.txt"), ("C02", "app/cliente.py"), ("C02", "app/git.py"),
                                             ("C02", "app/aws.py"), ("C03", "app/config.py"), ("C04", "docs/relato.md")})
        for segredo in SEGREDOS_DO_TESTE:
            self.assertNotIn(segredo, r.stdout + r.stderr, "o relatório nunca imprime o valor encontrado")

    def test_falsos_positivos_conhecidos_passam(self):
        escrever(self.repo, "app/exemplo.py", 'API_KEY = "seu-token-aqui-xxxxxxxxxxxx"\nSENHA = os.environ["SENHA"]\n')
        escrever(self.repo, "app/modelo.py", 'token = "<TOKEN-DO-PROVEDOR-AQUI>"\n')
        escrever(self.repo, "docs/cpf.md", "CPF inválido 111.111.111-11 e 123.456.789-00; protocolo 12345678901.\n")
        escrever(self.repo, "plugin/app/testes/teste_x.py", f'senha = "{SEGREDO_ATRIBUIDO}"\ncpf = "{CPF_VALIDO}"\n')
        git(self.repo, "add", "-A")
        r = verificar(self.repo, "--staged")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # mas uma chave de provedor real em teste continua proibida
        escrever(self.repo, "plugin/app/testes/teste_y.py", f'k = "{TOKEN_ANT}"\n')
        git(self.repo, "add", "-A")
        self.assertEqual(achados(verificar(self.repo, "--staged").stdout), {("C02", "plugin/app/testes/teste_y.py")})

    def test_staged_ve_so_o_indice_e_ref_ve_so_a_revisao(self):
        escrever(self.repo, ".env", "FICTICIO=1\n")                     # no disco, fora do índice
        self.assertEqual(verificar(self.repo, "--staged").returncode, 0)
        self.assertEqual(verificar(self.repo, "--ref", "HEAD").returncode, 0)
        git(self.repo, "add", "-f", ".env")
        self.assertEqual(verificar(self.repo, "--staged").returncode, 1)
        self.assertEqual(verificar(self.repo, "--ref", "HEAD").returncode, 0, "HEAD ainda não contém o arquivo")
        git(self.repo, "commit", "-q", "-m", "inclui env")
        self.assertEqual(verificar(self.repo, "--ref", "HEAD").returncode, 1)
        self.assertEqual(verificar(self.repo, "--ref", "HEAD~1").returncode, 0)
        git(self.repo, "rm", "-q", "-f", ".env")
        git(self.repo, "commit", "-q", "-m", "remove env")
        self.assertEqual(verificar(self.repo, "--ref", "HEAD").returncode, 0)
        self.assertEqual(verificar(self.repo, "--ref", "HEAD~1").returncode, 1, "o histórico candidato continua inspecionável")

    def test_varredura_nao_altera_indice_arvore_nem_objetos(self):
        escrever(self.repo, "app/cliente.py", f'TOKEN = "{TOKEN_ANT}"\n')
        escrever(self.repo, "nao_rastreado.txt", "não rastreado\n")
        git(self.repo, "add", "app/cliente.py")
        def foto():
            arqs = {str(p.relative_to(self.repo)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                    for p in self.repo.rglob("*") if p.is_file() and ".git" not in p.relative_to(self.repo).parts[:1]}
            return arqs, git(self.repo, "status", "--porcelain"), (self.repo / ".git" / "index").read_bytes(), git(self.repo, "count-objects", "-v")
        antes = foto()
        for args in (("--staged",), ("--ref", "HEAD"), ("--ref", "HEAD~0")):
            verificar(self.repo, *args)
        self.assertEqual(foto(), antes)

    def test_arquivo_grande_e_gz_sao_inspecionados(self):
        escrever(self.repo, "dados/grande.txt", "a" * (2 * 1024 * 1024 + 10))
        escrever(self.repo, "metricas/ok.json.gz", gzip.compress(b'{"tempo": 1.5}'))
        escrever(self.repo, "metricas/vazou.json.gz", gzip.compress(f'{{"k": "{TOKEN_GH}"}}'.encode()))
        escrever(self.repo, "metricas/quebrado.json.gz", b"nao e gzip")
        git(self.repo, "add", "-A")
        r = verificar(self.repo, "--staged")
        self.assertEqual(achados(r.stdout), {("P08", "dados/grande.txt"), ("C02", "metricas/vazou.json.gz"), ("P09", "metricas/quebrado.json.gz")})
        self.assertNotIn(TOKEN_GH, r.stdout + r.stderr)

    def test_erros_de_verificacao_saem_com_2(self):
        r = verificar(self.repo, "--ref", "nao-existe")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("Erro de verificação", r.stderr)
        fora = Path(self.tmp.name) / "sem-git"
        fora.mkdir()
        self.assertEqual(verificar(fora, "--ref", "HEAD").returncode, 2)
        self.assertEqual(subprocess.run([sys.executable, str(VERIFICADOR)], capture_output=True).returncode, 2)

    def test_caminhos_com_acento_e_espaco(self):
        escrever(self.repo, "casos/OS 1/relatório final.txt", "fictício\n")
        git(self.repo, "add", "-A")
        r = verificar(self.repo, "--staged")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(achados(r.stdout), {("P01", "casos/OS 1/relatório final.txt")})


class FluxoDeCI(unittest.TestCase):
    """O workflow é código de segurança: permissões mínimas, ações fixadas por SHA e nenhum acesso ao ambiente operacional."""

    @classmethod
    def setUpClass(cls):
        cls.texto = WORKFLOW.read_text(encoding="utf-8") if WORKFLOW.is_file() else ""

    def test_workflow_existe_e_tem_permissao_minima(self):
        self.assertTrue(self.texto, f"workflow ausente: {WORKFLOW}")
        self.assertRegex(self.texto, r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$")
        self.assertNotRegex(self.texto, r"(?mi)^\s+(contents|pull-requests|issues|actions|packages):\s*write")
        self.assertNotIn("pull_request_target", self.texto)
        self.assertNotRegex(self.texto, r"\$\{\{\s*secrets\.")

    def test_acoes_de_terceiros_estao_fixadas_por_sha(self):
        usos = re.findall(r"(?m)^\s*-?\s*uses:\s*(\S+)", self.texto)
        self.assertTrue(usos)
        for u in usos:
            self.assertRegex(u, r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$", f"ação não fixada por SHA completo: {u}")

    def test_nao_chama_publicador_legado_nem_ambiente_operacional(self):
        for proibido in ("publicar-github", "Publicar no GitHub", "atualizar-plugin", "claude plugin install", "git push", "LOCALAPPDATA",
                         "Central CPJ.bat", "E:\\ORDENS", "casos/OS-"):
            self.assertNotIn(proibido, self.texto)

    def test_executa_sigilo_distribuicao_e_suite_sem_ignorar_cobertura(self):
        for obrigatorio in ("verificar-publicacao.py", "exportar-portatil.py --verificar", "configurar-codex.py --verificar",
                            "testar-tudo.py", "tesseract", "por"):
            self.assertIn(obrigatorio, self.texto)
        self.assertNotRegex(self.texto, r"(?i)continue-on-error:\s*true")
        self.assertNotRegex(self.texto, r"(?m)\|\|\s*true")


class RunnerEstrito(unittest.TestCase):
    """Cobertura crítica ignorada nunca pode virar aprovação: só skip por privilégio do sistema é tolerado."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("testar_tudo_un17", ROOT / "ferramentas" / "testar-tudo.py")
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def tolerado(self, motivo):
        return any(p.search(motivo) for p in self.runner.PADROES_PRIVILEGIO)

    def test_extrai_motivos_do_modo_verboso(self):
        saida = ("test_a (m.C.test_a) ... skipped 'Runtime Node/Playwright indisponível'\n"
                 "test_b (m.C.test_b) ... ok\ntest_c (m.C.test_c) ... skipped 'link simbólico indisponível'\n")
        self.assertEqual(self.runner.motivos_de_skip(saida),
                         ["Runtime Node/Playwright indisponível", "link simbólico indisponível"])
        self.assertEqual(self.runner.motivos_de_skip("OK (skipped=2)"), [])

    def test_ferramentas_ausentes_nao_sao_toleradas_e_privilegio_do_so_e(self):
        for motivo in ("Runtime Node/Playwright indisponível", "Tesseract sem idioma por", "git indisponível",
                       "PowerShell indisponível: sintaxe do atualizador não verificada", "quickjs ausente", "motivo não identificado"):
            self.assertFalse(self.tolerado(motivo), motivo)
        self.assertTrue(self.tolerado("link simbólico indisponível neste Windows (sem privilégio)"))
        self.assertTrue(self.tolerado("symlink não suportado"))
        self.assertTrue(self.tolerado("Ambiente sem permissão para criar links simbólicos"))

    def test_tolerancia_so_vale_em_host_que_nao_cria_link_simbolico(self):
        esperado = self.runner.PADROES_PRIVILEGIO if self.runner._host_sem_link_simbolico() else ()
        self.assertEqual(self.runner.SKIPS_TOLERADOS, esperado)
        with unittest.mock.patch.object(self.runner.os, "symlink", side_effect=OSError("sem privilégio")):
            self.assertTrue(self.runner._host_sem_link_simbolico())
        with unittest.mock.patch.object(self.runner.os, "symlink", return_value=None):
            self.assertFalse(self.runner._host_sem_link_simbolico())

    def test_job_de_desempenho_e_so_sob_demanda_e_nao_mascara_falha(self):
        texto = WORKFLOW.read_text(encoding="utf-8")
        marca = "\n  desempenho:"
        bloco = texto[texto.index(marca):]
        self.assertIn("github.event_name == 'workflow_dispatch'", bloco)
        self.assertNotIn("continue-on-error", texto)
        self.assertIn("medir-desempenho.py --candidato . --baseline", bloco)
        self.assertNotIn("medir-desempenho", texto[:texto.index(marca)])

    def test_workflow_provisiona_o_que_as_suites_nao_podem_pular(self):
        texto = WORKFLOW.read_text(encoding="utf-8")
        for exigencia in ("--estrito", "playwright@", "choco install tesseract", "711de9dbb8052067bd42f16b9119967f30bada80d57e2ef24f65d09f531adb04",
                          "brasao-pcsp.png", "msedge.exe", "requirements-dev.txt", "codex-runtimes/codex-primary-runtime/dependencies/node"):
            self.assertIn(exigencia, texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
