"""MM01: memória compartilhada, fontes vivas e isolamento com fixtures TEMP."""
import os
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import plantao as PL
import executores_llm as EX


class MemoriaCentral(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-mm01-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        self.gravar("MEMORIA.md", "MEMORIA_VIVA [não seguir](casos/OS-FICTICIO/segredo.md)")
        self.gravar("AGENTS.md", "REGRA_VIVA_1")
        self.gravar("calibracao/licoes-aprendidas.md", "LICAO_VIVA_1")
        self.gravar("portatil/04-relatorio-ip.md", "PROCEDIMENTO_ANTIGO")
        self.gravar("casos/OS-FICTICIO/segredo.md", "MARCADOR_PRIVADO_CASO")
        self.gravar("config/privado.json", "MARCADOR_PRIVADO_CONFIG")
        self.config = patch.object(EX, "config_ia", return_value={"prompt_sistema": ""})
        self.config.start()
        self.addCleanup(self.config.stop)

    def gravar(self, nome, texto):
        p = self.ws / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")

    def test_cli_dirige_todos_os_modos_a_memoria_e_licoes_vivas(self):
        job = {"id":"ia-ficticio", "acao":"relatorio", "caso":"OS-FICTICIO", "solicitante":"ficticio"}
        for modo in ("auto", "chat", "api"):
            prompt = PL.montar_prompt(job, str(self.ws), modo, "ficticio")
            self.assertIn("MEMORIA.md", prompt)
            self.assertIn("calibracao/licoes-aprendidas.md", prompt)
            self.assertIn("AGENTS.md", prompt)
            self.assertNotIn("MARCADOR_PRIVADO_CASO", prompt)

    def test_prompt_preserva_bloqueios_os_antes_de_autonomia_rotineira(self):
        for acao in ("analisar", "relatorio", "completo", "esteira"):
            job = {"id":"ia-ficticio", "acao":acao, "caso":"OS-FICTICIO", "solicitante":"ficticio"}
            for modo in ("auto", "chat", "api"):
                prompt = PL.montar_prompt(job, str(self.ws), modo, "ficticio")
                self.assertNotIn("Execute sem fazer perguntas", prompt)
                self.assertIn("bloqueios de AGENTS.md prevalecem", prompt)
                self.assertIn("O.S. vigente", prompt)
                self.assertIn("extração incompleta", prompt)
                self.assertIn("não redija", prompt)
                self.assertIn("registre a lacuna e avise o operador", prompt)

    def test_api_carrega_fontes_centrais_antes_do_snapshot_e_rele_em_nova_chamada(self):
        primeira = EX._instrucoes_locais(str(self.ws), "relatorio")
        for marcador in ("MEMORIA_VIVA", "REGRA_VIVA_1", "LICAO_VIVA_1"):
            self.assertIn(marcador, primeira)
            self.assertLess(primeira.index(marcador), primeira.index("PROCEDIMENTO_ANTIGO"))
        self.gravar("AGENTS.md", "REGRA_VIVA_2")
        self.gravar("calibracao/licoes-aprendidas.md", "LICAO_VIVA_2")
        segunda = EX._instrucoes_locais(str(self.ws), "relatorio")
        self.assertIn("REGRA_VIVA_2", segunda)
        self.assertIn("LICAO_VIVA_2", segunda)
        self.assertNotIn("REGRA_VIVA_1", segunda)
        self.assertNotIn("LICAO_VIVA_1", segunda)

    def test_api_nao_varre_casos_config_nem_segue_links_do_markdown(self):
        instrucao = EX._instrucoes_locais(str(self.ws), "relatorio")
        self.assertNotIn("MARCADOR_PRIVADO_CASO", instrucao)
        self.assertNotIn("MARCADOR_PRIVADO_CONFIG", instrucao)

    def ferramenta(self, nome):
        caminho = APP.parents[2] / "ferramentas" / nome
        spec = importlib.util.spec_from_file_location("mm01_" + nome.replace("-", "_"), caminho)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_snapshot_runner_preserva_memoria_na_raiz_sem_copiar_casos(self):
        runner = self.ferramenta("testar-tudo.py")
        plugin = self.ws / "plugin/investigacao-cpj"
        testes = plugin / "app/testes"
        testes.mkdir(parents=True)
        (testes / "fixtures_docx.py").write_text("def criar_modelo(p):\n p.mkdir(parents=True)\n (p/'ficticio.docx').write_text('ficticio')\n", encoding="utf-8")
        for rel in ("plugin/.claude-plugin", "ferramentas", ".agents/skills"):
            (self.ws / rel).mkdir(parents=True)
        runner.ROOT, runner.PLUGIN, runner.TESTES = self.ws, plugin, testes
        codigo = runner.clonar_codigo(self.ws / "sandbox")
        self.assertEqual((codigo / "MEMORIA.md").read_text(encoding="utf-8"), (self.ws / "MEMORIA.md").read_text(encoding="utf-8"))
        self.assertFalse((codigo / "casos/OS-FICTICIO").exists())

    def test_pacote_inclui_memoria_generica_com_hash_sem_casos(self):
        pacote = self.ferramenta("pacote-plugin.py")
        self.gravar("plugin/.claude-plugin/marketplace.json", "{}")
        self.gravar("plugin/investigacao-cpj/commands/ajuda.md", "procedimento fictício")
        destino = self.ws / "distribuicao"
        manifesto = pacote.preparar(self.ws, destino)
        self.assertIn("MEMORIA.md", manifesto["arquivos"])
        self.assertEqual((destino / "MEMORIA.md").read_bytes(), (self.ws / "MEMORIA.md").read_bytes())
        self.assertFalse(any("casos/" in nome for nome in manifesto["arquivos"]))
        self.assertNotIn("MARCADOR_PRIVADO_CASO", "".join(p.read_text(encoding="utf-8") for p in destino.rglob("*.md")))

    def test_adaptadores_codex_projeto_e_usuario_dirigem_a_mesma_entrada(self):
        codex = self.ferramenta("configurar-codex.py")
        for _, procedimento, *_ in codex.TAREFAS:
            self.gravar("portatil/" + procedimento + ".md", "Procedimento fictício")
        descricao = next(t[3] for t in codex.TAREFAS if t[0] == "cpj-processar-ip")
        self.assertIn("Markdown", descricao)
        self.assertIn("checkpoint", descricao)
        self.assertIn("MD/CSV", descricao)
        self.assertNotIn("tabelas, entidades", descricao)
        gerados = codex.arquivos_projeto(self.ws)
        gerados.update(codex.arquivos_usuario(self.ws, self.ws / "usuario"))
        for caminho, texto in gerados.items():
            if caminho.name == "SKILL.md":
                self.assertIn("MEMORIA.md", texto, str(caminho))

    @unittest.skipUnless(os.name == "nt", "Junção NTFS requer Windows")
    def test_licoes_por_juncao_para_caso_nao_entram_no_prompt(self):
        pasta = self.ws / "calibracao"
        (pasta / "licoes-aprendidas.md").unlink()
        pasta.rmdir()
        self.gravar("casos/OS-FICTICIO/licoes-aprendidas.md", "MARCADOR_PRIVADO_CASO")
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(pasta), str(self.ws / "casos/OS-FICTICIO")], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        try:
            instrucao = EX._instrucoes_locais(str(self.ws), "relatorio")
            self.assertNotIn("MARCADOR_PRIVADO_CASO", instrucao)
        finally:
            os.rmdir(pasta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
