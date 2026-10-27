"""SEC22: executores sem shell amplo, ferramentas limitadas à etapa."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import executores_llm as EL
import plantao as PL


class Isolamento(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-sec22-ia-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        self.caso = "OS-1-2099"
        self.raiz = self.ws / "casos" / self.caso
        (self.raiz / "02-analise").mkdir(parents=True)
        self.job = {"id": "pedido-ficticio", "caso": self.caso, "acao": "analisar", "solicitante": "operador",
                    "consentimento": EL.criar_consentimento("operador", sorted(EL.DESTINOS_EXTERNOS)),
                    "_etapa": {"id": "bloco-a", "tipo": "blocos", "saidas": ["02-analise/bloco-a.md"]}}

    def test_cli_sem_sandbox_bloqueia_antes_de_qualquer_processo(self):
        class Fila: pass
        pl = Fila(); pl.ws = str(self.ws)
        with patch.object(PL.subprocess, "Popen", side_effect=AssertionError("processo inseguro")):
            for tipo in ("codex", "gemini", "copilot"):
                with self.subTest(tipo=tipo), self.assertRaisesRegex(RuntimeError, "isolamento|sandbox"):
                    PL._executar_sessao(pl, self.job, "Agente", tipo)

    def test_ferramenta_grava_apenas_saida_da_etapa(self):
        import execucao_isolada as I
        I.executar_ferramenta(str(self.ws), self.job, "gravar_arquivo", {"caminho": "02-analise/bloco-a.md", "conteudo": "ficticio"})
        self.assertEqual((self.raiz / "02-analise/bloco-a.md").read_text(), "ficticio")
        for alvo in ("02-analise/bloco-b.md", "03-relatorios/minuta-v01.md", "../OS-2-2099/02-analise/outro.md", "00-originais/teste.txt"):
            with self.subTest(alvo=alvo), self.assertRaises(ValueError):
                I.executar_ferramenta(str(self.ws), self.job, "gravar_arquivo", {"caminho": alvo, "conteudo": "invasao"})
        self.assertFalse((self.raiz / "02-analise/bloco-b.md").exists())

    def test_sem_etapa_nao_concede_escrita_geral(self):
        import execucao_isolada as I
        job = {k: v for k, v in self.job.items() if k != "_etapa"}; job["acao"] = "invalida"
        with self.assertRaises(ValueError):
            I.executar_ferramenta(str(self.ws), job, "gravar_arquivo", {"caminho": "02-analise/a.md", "conteudo": "x"})

    def test_sem_shell_ou_credenciais_nem_outro_caso(self):
        import execucao_isolada as I
        for nome, args in (("shell", {"command": "python"}), ("ler_arquivo", {"caminho": "../../config/chaves_llm.json"}),
                           ("ler_arquivo", {"caminho": "../OS-2-2099/caso.json"})):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                I.executar_ferramenta(str(self.ws), self.job, nome, args)

    def test_acao_financeira_direta_deriva_saidas_do_servidor(self):
        import execucao_isolada as I
        job = {k: v for k, v in self.job.items() if k != "_etapa"}; job["acao"] = "financeiro"
        job = I.preparar_job(str(self.ws), job)
        I.executar_ferramenta(str(self.ws), job, "gravar_arquivo", {"caminho": "02-analise/fluxo-financeiro.md", "conteudo": "ficticio"})
        self.assertEqual((self.raiz / "02-analise/fluxo-financeiro.md").read_text(), "ficticio")
        with self.assertRaises(ValueError):
            I.executar_ferramenta(str(self.ws), job, "gravar_arquivo", {"caminho": "02-analise/outro.md", "conteudo": "x"})

    def test_claude_transporta_json_sem_ferramentas_nativas_e_grava_so_pelo_servidor(self):
        import execucao_isolada as I
        class Fila:
            ws = str(self.ws)
            def progresso(self, *args, **kwargs): return True
            def pedido(self, *args): return {}
        job = dict(self.job, _etapa={**self.job["_etapa"], "arg": {}, "etapa": "Bloco ficticio"})
        popen_real = subprocess.Popen
        script = '''import json,os,sys
a=sys.argv
assert a[a.index('--tools')+1] == ''
assert '--strict-mcp-config' in a and '--disable-slash-commands' in a
assert a[a.index('--setting-sources')+1] == ''
assert json.loads(a[a.index('--settings')+1])['disableAllHooks'] is True
assert 'SEGREDO_ENV_SEC22' not in os.environ and 'CPJ_WORKSPACE' not in os.environ
conversa=json.load(sys.stdin)
if len(conversa)==1:
    resposta={'ferramentas':[{'nome':'gravar_arquivo','argumentos':{'caminho':'02-analise/bloco-a.md','conteudo':'analise sintetica'}}]}
else: resposta={'resumo':'concluido'}
print(json.dumps({'type':'system','subtype':'init','tools':[],'mcp_servers':[],'plugins':[]}))
print(json.dumps({'type':'result','subtype':'success','result':json.dumps(resposta)}))
'''
        def iniciar(cmd, **kw):
            self.assertNotEqual(Path(kw["cwd"]), self.ws)
            self.assertFalse(kw.get("shell", False))
            return popen_real([sys.executable, "-c", script, *cmd[1:]], **kw)
        with patch.dict(os.environ, {"SEGREDO_ENV_SEC22": "nao-herdar"}), \
             patch.object(PL, "claude_exe", return_value="claude-ficticio.exe"), \
             patch.object(PL, "montar_prompt", return_value="Texto sintetico"), \
             patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "2.1.304 (Claude Code)", "")), \
             patch.object(subprocess, "Popen", side_effect=iniciar):
            r = PL._executar_sessao(Fila(), job, "Claude", "claude")
        self.assertEqual((self.raiz / "02-analise/bloco-a.md").read_text(), "analise sintetica")
        self.assertEqual(r["resumo"], "concluido")


if __name__ == "__main__": unittest.main()
