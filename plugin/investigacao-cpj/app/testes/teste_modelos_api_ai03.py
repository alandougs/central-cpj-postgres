"""AI03: catálogos e escolha de modelo, somente mocks/workspace fictício."""
import importlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import quickjs
from flask import Flask

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
BASE = tempfile.TemporaryDirectory(prefix="cpj-ai03-import-")
_ambiente = {k: os.environ.get(k) for k in ("CPJ_WORKSPACE", "CPJ_SEM_AGENTE_EMBUTIDO", "APPDATA")}
os.environ.update(CPJ_WORKSPACE=BASE.name, CPJ_SEM_AGENTE_EMBUTIDO="1", APPDATA=BASE.name)
try:
    sistema = importlib.import_module("rotas.sistema")
    comum = importlib.import_module("rotas.comum")
finally:
    for _k, _v in _ambiente.items():
        if _v is None: os.environ.pop(_k, None)
        else: os.environ[_k] = _v

EQUILIBRADOS = {
    "openai": "gpt-6.1-sol", "anthropic": "claude-sonnet-5-5", "gemini": "gemini-3.8-flash",
    "deepseek": "deepseek-flash", "xai": "grok-4.7", "groq": "openai/gpt-oss-120b",
    "nvidia": "nvidia/llama-3.3-nemotron-super-49b-v1.5", "openrouter": "openai/gpt-6.1-sol",
}


class Catalogos(unittest.TestCase):
    def consultar(self, prov, resposta):
        with patch.object(sistema, "_get_json_modelos", return_value=resposta):
            return sistema._consultar_modelos(prov, "CHAVE FICTICIA")

    def test_01_equilibrado_precisa_constar_catalogo_textual(self):
        for prov, modelo in EQUILIBRADOS.items():
            with self.subTest(provedor=prov):
                item = {"id": modelo, "architecture": {"output_modalities": ["text"]}}
                resposta = {"data": [item]}
                if prov == "gemini":
                    resposta = {"models": [{"name": "models/" + modelo, "supportedGenerationMethods": ["generateContent"]}]}
                r = self.consultar(prov, resposta)
                self.assertEqual(r.get("modelo_equilibrado"), modelo)
                vazio = self.consultar(prov, {"data": [], "models": []})
                self.assertEqual(vazio.get("modelo_equilibrado"), "")

    def test_02_desconhecido_nao_vira_padrao_por_ser_recente(self):
        r = self.consultar("openai", {"data": [{"id": "modelo-novo-ficticio", "created": 9999999999},
            {"id": "gpt-6.1-sol-audio"}, {"id": "modelo-image"}]})
        self.assertEqual([m["id"] for m in r["modelos"]], ["modelo-novo-ficticio"])
        self.assertEqual(r.get("modelo_equilibrado"), "")
        gem = self.consultar("gemini", {"models": [
            {"name": "models/gemini-3.8-flash-tts", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embedding", "supportedGenerationMethods": ["embedContent"]}]})
        self.assertEqual(gem["modelos"], [])

    def test_03_paginas_anthropic_gemini_com_cursor_codificado(self):
        for prov, resposta1, resposta2, parametro in (
            ("anthropic", {"data": [{"id": "outro"}], "has_more": True, "last_id": "cursor & ficticio"},
             {"data": [{"id": "claude-sonnet-5-5"}], "has_more": False}, "after_id=cursor+%26+ficticio"),
            ("gemini", {"models": [], "nextPageToken": "cursor & ficticio"},
             {"models": [{"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"]}]},
             "pageToken=cursor+%26+ficticio"),
        ):
            with self.subTest(provedor=prov), patch.object(sistema, "_get_json_modelos", side_effect=[resposta1, resposta2]) as rede:
                r = sistema._consultar_modelos(prov, "FICTICIA")
                self.assertEqual(rede.call_count, 2)
                self.assertIn(parametro, rede.call_args.args[0])
                self.assertEqual(r.get("modelo_equilibrado"), EQUILIBRADOS[prov])

    def test_04_paginacao_repetida_incompleta_e_limitada_falha_sem_catalogo_parcial(self):
        for resposta in ({"data": [], "has_more": True},
                         {"data": [], "has_more": True, "last_id": "repetido"}):
            with patch.object(sistema, "_get_json_modelos", return_value=resposta) as rede:
                with self.assertRaises(ValueError): sistema._consultar_modelos("anthropic", "FICTICIA")
                self.assertLessEqual(rede.call_count, 10)
        n = iter(range(100))
        with patch.object(sistema, "_get_json_modelos", side_effect=lambda *a: {"models": [], "nextPageToken": str(next(n))}) as rede:
            with self.assertRaises(ValueError): sistema._consultar_modelos("gemini", "FICTICIA")
            self.assertEqual(rede.call_count, 10)

    def test_05_catalogo_copilot_documental_nao_prova_acesso(self):
        with patch.object(sistema, "_get_json_modelos", side_effect=AssertionError("Rede proibida")):
            r = sistema._consultar_modelos("copilot", "")
        self.assertIn("claude-sonnet-5.5", [m["id"] for m in r["modelos"]])
        self.assertFalse(r["dinamico"])
        self.assertEqual(r.get("modelo_equilibrado"), "")
        self.assertIn("conta", r.get("aviso", ""))

    def test_06_rota_catalogo_somente_metadados_nao_salva_config_nem_sincroniza(self):
        app = Flask(__name__); app.register_blueprint(sistema.bp_sistema)
        with tempfile.TemporaryDirectory(prefix="cpj-ai03-rota-") as pasta:
            cfg = Path(pasta) / "chaves_llm.json"
            cfg.write_text(json.dumps({"openai": {"chave": "FICTICIA", "modelo": "escolha-manual", "ativo": False}}), encoding="utf-8")
            antes = cfg.read_bytes()
            with patch.object(sistema, "CONFIG_LLM", str(cfg)), \
                 patch.object(comum, "usuario", return_value={"login": "ficticio", "perfil": "admin"}), \
                 patch.object(sistema, "_get_json_modelos", return_value={"data": [{"id": "gpt-6.1-sol"}]}) as rede, \
                 patch.object(sistema, "tarefas") as tarefas:
                r = app.test_client().post("/api/sistema/llm/modelos", json={"provedor": "openai"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(cfg.read_bytes(), antes)
            tarefas.sincronizar_provedor.assert_not_called()
            self.assertEqual(rede.call_args.args[0], "https://api.openai.com/v1/models")
            self.assertIn("Bearer FICTICIA", rede.call_args.args[1].values())
            self.assertNotIn("FICTICIA", r.get_data(as_text=True))

    def test_11_metadados_inativos_nao_textuais_sem_tools_e_malformados(self):
        for prov, dados in (("groq", {"id": EQUILIBRADOS["groq"], "active": False}),
                            ("anthropic", {"id": EQUILIBRADOS["anthropic"], "lifecycle": "deprecated"}),
                            ("deepseek", {"id": EQUILIBRADOS["deepseek"], "output_modalities": ["audio"]}),
                            ("openrouter", {"id": EQUILIBRADOS["openrouter"], "architecture": {"output_modalities": ["text"]}, "supported_parameters": ["temperature"]}),
                            ("xai", {"id": EQUILIBRADOS["xai"], "tool_calling": False})):
            with self.subTest(provedor=prov):
                r = self.consultar(prov, {"data": [dados]})
                self.assertEqual(r["modelo_equilibrado"], "")
        with patch.object(sistema, "_get_json_modelos", return_value={"data": "inválido"}):
            with self.assertRaises(ValueError): sistema._consultar_modelos("openai", "FICTICIA")
        gem = self.consultar("gemini", {"models": [{"name": "models/gemini-3.8-flash",
            "supportedGenerationMethods": ["generateContent"], "output_modalities": ["audio"]}]})
        self.assertEqual(gem["modelo_equilibrado"], "")


class Interface(unittest.TestCase):
    def setUp(self):
        self.html = (APP / "static/index.html").read_text(encoding="utf-8")
        bloco = self.html.split("// ---------------- chaves LLM", 1)[1].split("// ---------------- fluxograma financeiro", 1)[0]
        self.ctx = quickjs.Context()
        self.ctx.eval('''
        var chamadas=[], cfg={}, resposta={modelos:[{id:'gpt-6.1-sol',nome:'Sol ficticio'}],modelo_equilibrado:'gpt-6.1-sol',dinamico:true};
        var erro=false, resolver=null, adiar=false, resultado=null, els={};
        function el(){return {value:'',checked:false,textContent:'',dataset:{},children:[],replaceChildren(){this.children=[]},appendChild(o){this.children.push(o)}}}
        ['openai','anthropic','gemini','deepseek','xai','groq','openrouter','nvidia','copilot'].forEach(p=>{
          ['modelo','chave','ativo'].forEach(f=>els['#llm-'+p+'-'+f]=el()); els['#modelos-'+p]=el(); els['#msg-modelos-'+p]=el(); els['#msg-llm-'+p]=el();
        });
        function $(k){return els[k]} var document={createElement:t=>el()}; function toast(){} function setTimeout(){}
        async function api(u,o){chamadas.push({u:u,body:o&&o.json});if(u==='/api/sistema/llm')return cfg;if(erro)throw new Error('FALHA FICTICIA');if(adiar)return new Promise(r=>resolver=r);return resposta}
        ''')
        self.ctx.eval(bloco)
        self.assertIn("async function atualizarModelosLLM", bloco)

    def jobs(self):
        for _ in range(100):
            if not self.ctx.execute_pending_job(): return
        self.fail("Promises não estabilizaram")

    def valor(self, expressao): return json.loads(self.ctx.eval("JSON.stringify(" + expressao + ")"))

    def atualizar(self):
        self.ctx.eval("atualizarModelosLLM('openai').then(r=>resultado=r)"); self.jobs()

    def test_07_cards_nove_provedores_com_entrada_manual_e_catalogo(self):
        for p in (*EQUILIBRADOS, "copilot"):
            self.assertRegex(self.html, rf'id="llm-{p}-modelo"[^>]*list="modelos-{p}"')
            self.assertIn(f'id="modelos-{p}"', self.html)
            self.assertIn(f"atualizarModelosLLM('{p}')", self.html)

    def test_08_escolha_equilibrada_no_formulario_sem_salvar_ativar_ou_executar(self):
        self.atualizar()
        self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "gpt-6.1-sol")
        self.assertFalse(self.valor("els['#llm-openai-ativo'].checked"))
        self.assertEqual(self.valor("chamadas"), [{"u": "/api/sistema/llm/modelos", "body": {"provedor": "openai"}}])
        self.assertIn("Salvar", self.valor("els['#msg-modelos-openai'].textContent"))

    def test_09_modelo_salvo_manual_e_editado_durante_resposta_preservados(self):
        self.ctx.eval("els['#llm-openai-modelo'].value='legado-manual'"); self.atualizar()
        self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "legado-manual")
        self.ctx.eval("els['#llm-openai-modelo'].value='';adiar=true"); self.atualizar()
        self.ctx.eval("els['#llm-openai-modelo'].value='digitado-durante';resolver(resposta)"); self.jobs()
        self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "digitado-durante")

    def test_10_erro_vazio_padrao_ausente_estatico_nao_sobrepoem(self):
        for r in ({"modelos": [], "modelo_equilibrado": "gpt-6.1-sol", "dinamico": True},
                  {"modelos": [{"id": "outro"}], "modelo_equilibrado": "gpt-6.1-sol", "dinamico": True},
                  {"modelos": [{"id": "gpt-6.1-sol"}], "modelo_equilibrado": "gpt-6.1-sol", "dinamico": False}):
            self.ctx.eval("els['#llm-openai-modelo'].value='';resposta=" + json.dumps(r)); self.atualizar()
            self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "")
        self.ctx.eval("erro=true;els['#llm-openai-modelo'].value='manual'"); self.atualizar()
        self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "manual")
        self.assertIn("FALHA FICTICIA", self.valor("els['#msg-modelos-openai'].textContent"))

    def test_12_recarregar_config_preserva_edicao_manual_e_scripts_compilam(self):
        self.ctx.eval("cfg={openai:{modelo:'salvo-antigo',ativo:false}};els['#llm-openai-modelo'].value='edicao-manual';els['#llm-openai-modelo'].dataset.manual='1';carregarLLM()")
        self.jobs()
        self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "edicao-manual")
        for script in re.findall(r"<script[^>]*>([\s\S]*?)</script>", self.html):
            quickjs.Context().eval("new Function(" + json.dumps(script) + ")")

    def test_13_limpeza_manual_durante_consulta_preserva_vazio(self):
        self.ctx.eval("els['#llm-openai-modelo'].value='salvo-ficticio';adiar=true")
        self.atualizar()
        self.ctx.eval("els['#llm-openai-modelo'].value='';els['#llm-openai-modelo'].dataset.manual='1';resolver(resposta)")
        self.jobs()
        self.assertEqual(self.valor("els['#llm-openai-modelo'].value"), "")


if __name__ == "__main__": unittest.main(verbosity=2)
