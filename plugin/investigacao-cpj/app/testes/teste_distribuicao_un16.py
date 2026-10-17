"""Teste UN16: python -X utf8 app/testes/teste_distribuicao_un16.py.

Pacote genérico do plugin, portáteis e adaptadores Codex. Tudo em pastas temporárias com arquivos fictícios;
nada é instalado e nenhum diretório pessoal é tocado.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FERRAMENTAS = ROOT / "ferramentas"


def carregar(nome_arquivo, apelido):
    spec = importlib.util.spec_from_file_location(apelido, FERRAMENTAS / nome_arquivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


PACOTE = carregar("pacote-plugin.py", "pacote_plugin_un16")


def executar(*args, cwd=None):
    return subprocess.run([sys.executable, "-X", "utf8", *map(str, args)], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", timeout=120, env=dict(os.environ, PYTHONUTF8="1"))


def escrever(caminho, texto="x"):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


class PacoteReal(unittest.TestCase):
    """O pacote da fonte integrada: tudo que a interface e o servidor usam, e nada além."""

    @classmethod
    def setUpClass(cls):
        cls.incluidos, cls.excluidos, cls.recusados = PACOTE.selecionar(ROOT)

    def test_nada_e_recusado_e_todas_as_extensoes_da_fonte_estao_cobertas(self):
        self.assertEqual(self.recusados, [])
        extensoes = {Path(r).suffix.lower() for r in self.incluidos}
        self.assertEqual(extensoes, {".py", ".md", ".json", ".html", ".png", ".js", ".css"})

    def test_fila_unificada_e_modulos_novos_estao_no_pacote(self):
        base = "investigacao-cpj/app/"
        for rel in ("fluxo_execucao.py", "plantao.py", "static/js/fila-unificada.js", "static/js/polling.js",
                    "static/css/central.css", "static/index.html"):
            self.assertIn(base + rel, self.incluidos, rel)

    def test_todo_python_nao_teste_do_app_esta_incluido_e_nada_de_teste_ou_dado_local(self):
        app = ROOT / "plugin" / "investigacao-cpj" / "app"
        esperados = {("investigacao-cpj/app/" + p.relative_to(app).as_posix()) for p in app.rglob("*.py")
                     if not {"testes", "__pycache__"} & set(p.relative_to(app).parts)}
        faltando = esperados - set(self.incluidos)
        self.assertEqual(faltando, set(), f"módulos da fonte fora do pacote: {sorted(faltando)}")
        proibidos = [r for r in self.incluidos if re.search(r"(^|/)(testes|__pycache__|casos|config|00-originais|modelos)/", r)]
        self.assertEqual(proibidos, [])

    def test_recursos_locais_referenciados_existem_no_pacote(self):
        texto_fonte = [(rel, p.read_text(encoding="utf-8", errors="replace")) for rel, p in self.incluidos.items()
                       if Path(rel).suffix in {".html", ".js", ".css"}]
        padrao = re.compile(r"""["'(=\s]/static/([A-Za-z0-9_./-]+\.(?:js|css|png|json|html))""")
        referencias = {}
        for rel, texto in texto_fonte:
            for m in padrao.finditer(texto):
                referencias.setdefault(m.group(1), rel)
        self.assertIn("js/fila-unificada.js", referencias)
        self.assertIn("css/central.css", referencias)
        ausentes = {r: de for r, de in referencias.items() if f"investigacao-cpj/app/static/{r}" not in self.incluidos}
        self.assertEqual(ausentes, {}, "recurso referenciado e ausente do pacote (ex.: brasão ignorado pelo Git)")

    def test_atualizador_nao_tem_lista_propria_e_tem_sintaxe_valida(self):
        ps1 = (FERRAMENTAS / "atualizar-plugin.ps1").read_text(encoding="utf-8")
        self.assertIn("pacote-plugin.py", ps1)
        self.assertNotIn("'.png')", ps1, "a lista de extensões vive só em pacote-plugin.py")
        self.assertLess(ps1.index("pacote-plugin.py"), ps1.index("plugin install"), "o pacote é preparado antes de instalar")
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if not shell:
            self.skipTest("PowerShell indisponível: sintaxe do atualizador não verificada")
        r = subprocess.run([shell, "-NoProfile", "-Command",
                            "$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                            f"'{FERRAMENTAS / 'atualizar-plugin.ps1'}',[ref]$null,[ref]$e);if($e){{$e|%{{$_.Message}};exit 1}}"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class PacoteFicticio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un16-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name) / "ws"
        p = self.ws / "plugin"
        escrever(p / ".claude-plugin" / "marketplace.json", "{}")
        base = p / "investigacao-cpj"
        escrever(base / ".claude-plugin" / "plugin.json", "{}")
        escrever(base / "app" / "servidor.py", "print(1)")
        escrever(base / "app" / "static" / "index.html", "<script src='/static/js/a.js'></script>")
        escrever(base / "app" / "static" / "js" / "a.js", "1")
        escrever(base / "app" / "static" / "css" / "b.css", "1")
        escrever(base / "app" / "static" / "brasao.png", "png")
        escrever(base / "commands" / "x.md", "# x")
        self.sensiveis = [
            base / "app" / "config" / "plantao.sqlite", base / "casos" / "OS-1-2099" / "caso.json",
            base / "app" / ".env", base / "app" / ".env.local", base / "app" / ".env.example",
            base / "app" / "static" / "assinatura-investigador.png", base / "Assinatura.PNG",
            base / "app" / "modelo-oficial.docx", base / "app" / "credenciais.json", base / "app" / "dados.sqlite",
            base / "app" / "backup.zip", base / "app" / "testes" / "teste_x.py", base / "app" / "__pycache__" / "x.cpython-312.pyc",
            base / "app" / "log.log", base / "app" / "chave.pem", base / "app" / "certificado.pfx",
            base / "modelos" / "MODELO.docx", base / "00-originais" / "autos.pdf"]
        for s in self.sensiveis:
            escrever(s, "SEGREDO-FICTICIO")

    def test_sensiveis_ficticios_nao_entram_no_pacote_nem_no_manifesto(self):
        incluidos, excluidos, recusados = PACOTE.selecionar(self.ws)
        self.assertEqual(recusados, [])
        self.assertEqual(sorted(incluidos), sorted([
            ".claude-plugin/marketplace.json", "investigacao-cpj/.claude-plugin/plugin.json", "investigacao-cpj/app/servidor.py",
            "investigacao-cpj/app/static/index.html", "investigacao-cpj/app/static/js/a.js",
            "investigacao-cpj/app/static/css/b.css", "investigacao-cpj/app/static/brasao.png", "investigacao-cpj/commands/x.md"]))
        for s in self.sensiveis:
            rel = s.relative_to(self.ws / "plugin").as_posix()
            self.assertIn(rel, {e["caminho"] for e in excluidos}, f"deveria constar como excluído: {rel}")
        saida = self.ws.parent / "pacote"
        m = PACOTE.preparar(self.ws, saida)
        copiados = {p.relative_to(saida).as_posix() for p in saida.rglob("*") if p.is_file()}
        self.assertEqual(copiados, set(m["arquivos"]))
        conteudo = "".join(p.read_text(encoding="utf-8") for p in saida.rglob("*") if p.is_file())
        self.assertNotIn("SEGREDO-FICTICIO", conteudo)
        self.assertNotIn("SEGREDO-FICTICIO", json.dumps(m))

    def test_extensao_desconhecida_recusa_o_pacote_sem_criar_destino(self):
        escrever(self.ws / "plugin" / "investigacao-cpj" / "app" / "dados.csv", "a,b")
        escrever(self.ws / "plugin" / "investigacao-cpj" / "app" / "ferramenta.exe", "MZ")
        _, _, recusados = PACOTE.selecionar(self.ws)
        self.assertEqual(sorted(r.split(": ")[1] for r in recusados),
                         ["investigacao-cpj/app/dados.csv", "investigacao-cpj/app/ferramenta.exe"])
        destino = self.ws.parent / "nao-criar"
        r = executar(FERRAMENTAS / "pacote-plugin.py", "--workspace", self.ws, "preparar", "--destino", destino)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("Pacote recusado", r.stderr)
        self.assertFalse(destino.exists())

    def test_link_simbolico_e_recusado(self):
        alvo = escrever(self.ws.parent / "fora.py", "x")
        try:
            os.symlink(alvo, self.ws / "plugin" / "investigacao-cpj" / "app" / "ligacao.py")
        except (OSError, NotImplementedError):
            self.skipTest("link simbólico indisponível neste Windows (sem privilégio)")
        _, _, recusados = PACOTE.selecionar(self.ws)
        self.assertEqual([r.split(": ")[0] for r in recusados], ["link simbólico"])

    def test_preparar_confere_hashes_manifesto_deterministico_e_nao_sobrescreve(self):
        m1, m2 = PACOTE.manifesto(self.ws), PACOTE.manifesto(self.ws)
        self.assertEqual(m1, m2)
        self.assertEqual(m1["schema"], "cpj-pacote/1")
        self.assertEqual(m1["total"], len(m1["arquivos"]))
        destino = self.ws.parent / "pacote-a"
        PACOTE.preparar(self.ws, destino)
        manifesto = json.loads((self.ws.parent / "pacote-a.manifesto.json").read_text(encoding="utf-8"))
        for rel, info in manifesto["arquivos"].items():
            self.assertEqual(PACOTE._sha256(destino / rel), info["sha256"], rel)
            self.assertEqual(PACOTE._sha256(self.ws / "plugin" / rel), info["sha256"], rel)
        antes = {p: p.read_bytes() for p in destino.rglob("*") if p.is_file()}
        with self.assertRaises(PACOTE.PacoteRecusado):
            PACOTE.preparar(self.ws, destino)                         # destino já preenchido
        self.assertEqual({p: p.read_bytes() for p in destino.rglob("*") if p.is_file()}, antes)
        # alterar a fonte muda o hash do manifesto (e só dele)
        escrever(self.ws / "plugin" / "investigacao-cpj" / "commands" / "x.md", "# alterado")
        m3 = PACOTE.manifesto(self.ws)
        mudou = [r for r in m1["arquivos"] if m1["arquivos"][r]["sha256"] != m3["arquivos"][r]["sha256"]]
        self.assertEqual(mudou, ["investigacao-cpj/commands/x.md"])

    def test_cli_listar_e_manifesto(self):
        r = executar(FERRAMENTAS / "pacote-plugin.py", "--workspace", self.ws, "listar")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("investigacao-cpj/app/static/js/a.js", r.stdout.splitlines())
        self.assertNotIn("assinatura", r.stdout.lower())
        saida = self.ws.parent / "m.json"
        r = executar(FERRAMENTAS / "pacote-plugin.py", "--workspace", self.ws, "manifesto", "--saida", saida)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(saida.read_text(encoding="utf-8"))["total"], 8)

    def test_revisao_aparece_quando_ha_git(self):
        if not shutil.which("git"):
            self.skipTest("git indisponível")
        for args in (("init", "-q"), ("add", "-A"), ("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "fictício")):
            subprocess.run(["git", "-C", str(self.ws), *args], check=True, capture_output=True)
        sha = subprocess.run(["git", "-C", str(self.ws), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        m = PACOTE.manifesto(self.ws)
        self.assertEqual((m["revisao"], m["arvore_limpa"]), (sha, True))
        escrever(self.ws / "plugin" / "investigacao-cpj" / "commands" / "x.md", "# sujo")
        self.assertIs(PACOTE.manifesto(self.ws)["arvore_limpa"], False)


class Portateis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un16-port-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        shutil.copytree(ROOT / "plugin" / "investigacao-cpj", self.ws / "plugin" / "investigacao-cpj",
                        ignore=shutil.ignore_patterns("testes", "__pycache__", "static"))
        for nome in ("AGENTS.md", "PRD.md"):
            shutil.copy2(ROOT / nome, self.ws / nome)
        shutil.copytree(ROOT / "calibracao", self.ws / "calibracao", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "portatil", self.ws / "portatil")
        self.exportador = FERRAMENTAS / "exportar-portatil.py"

    def verificar(self, ws=None):
        return executar(self.exportador, "--workspace", ws or self.ws, "--verificar")

    def test_portateis_commitados_conferem_com_a_fonte_atual(self):
        r = executar(self.exportador, "--verificar")
        self.assertEqual(r.returncode, 0, "portatil\\ diverge da fonte; rode exportar-portatil.py:\n" + r.stdout + r.stderr)

    def test_regeneracao_confere_e_so_o_carimbo_de_data_e_ignorado(self):
        r = executar(self.exportador, "--workspace", self.ws)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.verificar().returncode, 0)
        arq = self.ws / "portatil" / "06-entregar.md"
        texto = arq.read_text(encoding="utf-8")
        trocado = re.sub(r"gerado em \d{4}-\d{2}-\d{2} \d{2}:\d{2}", "gerado em 2001-01-01 00:00", texto)
        self.assertNotEqual(trocado, texto)
        arq.write_text(trocado, encoding="utf-8")
        self.assertEqual(self.verificar().returncode, 0, "carimbo antigo não é divergência")
        arq.write_bytes(trocado.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(self.verificar().returncode, 0, "fim de linha do Windows não é divergência")

    def test_divergencias_reais_sao_detectadas_sem_escrever(self):
        executar(self.exportador, "--workspace", self.ws)
        arq = self.ws / "portatil" / "04-relatorio-ip.md"
        original = arq.read_text(encoding="utf-8")
        arq.write_text(original + "\nlinha editada à mão\n", encoding="utf-8")
        r = self.verificar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("desatualizado: 04-relatorio-ip.md", r.stdout)
        self.assertEqual(arq.read_text(encoding="utf-8"), original + "\nlinha editada à mão\n", "--verificar não pode escrever")
        arq.write_text(original, encoding="utf-8")
        (self.ws / "portatil" / "09-painel.md").unlink()
        (self.ws / "portatil" / "sobra.md").write_text("x", encoding="utf-8")
        r = self.verificar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("ausente: 09-painel.md", r.stdout)
        self.assertIn("sobra: sobra.md", r.stdout)
        # a fonte (plugin ou regras) mudou: o portátil gerado antes passa a divergir
        (self.ws / "portatil" / "sobra.md").unlink()
        executar(self.exportador, "--workspace", self.ws)
        agents = self.ws / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8").replace("Trabalhe só com os documentos do caso", "Trabalhe com os documentos do caso", 1), encoding="utf-8")
        self.assertEqual(self.verificar().returncode, 1)

    def test_regras_de_fls_assinatura_os_e_relatorio_chegam_a_todos_os_portateis(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        regras = re.search(r"## 1\. Regras.*?(?=\n## 2\.)", agents, flags=re.S).group(0).strip().split("\n", 1)[1].strip()
        regras = re.sub(r"C:[\\/]CPJ - TRABALHO[\\/]", "", regras)
        for arq in sorted((ROOT / "portatil").glob("[0-9][0-9]-*.md")):
            texto = arq.read_text(encoding="utf-8").replace("\r\n", "\n")
            self.assertIn(regras, texto, f"{arq.name}: regras obrigatórias do AGENTS.md ausentes ou desatualizadas")
            for trecho in ("Assinatura do investigador", "(Fls. 30-31)", "A Ordem de Serviço manda no relatório",
                           "Estilo e formatação do relatório", "Referências no relatório"):
                self.assertIn(trecho, texto, f"{arq.name}: falta '{trecho}'")


class AdaptadoresCodex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un16-codex-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name) / "ws"
        self.ws.mkdir()
        for nome in ("AGENTS.md", "PRD.md"):
            shutil.copy2(ROOT / nome, self.ws / nome)
        shutil.copytree(ROOT / "portatil", self.ws / "portatil")
        (self.ws / ".agents" / "skills").mkdir(parents=True)
        for skill in (ROOT / ".agents" / "skills").glob("cpj-*"):
            shutil.copytree(skill, self.ws / ".agents" / "skills" / skill.name)
        self.script = FERRAMENTAS / "configurar-codex.py"

    def test_adaptadores_do_repositorio_conferem(self):
        r = executar(self.script, "--verificar")
        self.assertEqual(r.returncode, 0, "adaptadores desatualizados; rode configurar-codex.py:\n" + r.stdout)

    def test_entrada_pessoal_em_destino_temporario(self):
        usuario = Path(self.tmp.name) / "usuario" / "skills"
        r = executar(self.script, "--workspace", self.ws, "--instalar-usuario", "--skills-usuario", usuario)
        self.assertEqual(r.returncode, 0, r.stdout)
        entrada = usuario / "cpj-projeto" / "SKILL.md"
        self.assertTrue(entrada.is_file())
        texto = entrada.read_text(encoding="utf-8")
        self.assertIn(str(self.ws.resolve()), texto)     # o gerador grava o caminho resolvido (no CI, TEMP vem em formato 8.3)
        self.assertIn("cpj-desenvolver", texto)
        for nome in ("cpj-processar-ip", "cpj-relatorio-ip", "cpj-fluxo-completo", "cpj-osint-policial"):
            self.assertIn(nome, texto)
            self.assertTrue((self.ws / ".agents" / "skills" / nome / "SKILL.md").is_file())
        self.assertEqual(executar(self.script, "--workspace", self.ws, "--instalar-usuario", "--skills-usuario", usuario, "--verificar").returncode, 0)
        self.assertEqual(sorted(p.name for p in usuario.iterdir()), ["cpj-projeto"])

    def test_cada_adaptador_aponta_para_portatil_existente_e_arquivo_alheio_e_preservado(self):
        for skill in (self.ws / ".agents" / "skills").glob("cpj-*/SKILL.md"):
            texto = skill.read_text(encoding="utf-8")
            for alvo in re.findall(r"\]\((\.\./\.\./\.\./portatil/[^)]+)\)", texto):
                self.assertTrue((skill.parent / alvo).resolve().is_file(), f"{skill.parent.name}: {alvo}")
        alheio = self.ws / ".agents" / "skills" / "cpj-buscar" / "SKILL.md"
        alheio.write_text("escrito à mão, sem a marca do gerador", encoding="utf-8")
        r = executar(self.script, "--workspace", self.ws)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(alheio.read_text(encoding="utf-8"), "escrito à mão, sem a marca do gerador")


if __name__ == "__main__":
    unittest.main(verbosity=2)
