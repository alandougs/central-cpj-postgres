#!/usr/bin/env python3
"""RV07 — Preservação de delegado_genero, escrivão, montagem de referência IPe/Processo e títulos em ler_minuta.

Valida:
1. Minuta nova monta referência padrão 'IPe nº … / Processo nº …' a partir de inquerito e processo, sem BO nem IP local.
2. Campos ausentes em inquerito/processo ficam pendentes na referência ('[PENDENTE]').
3. Detecção e inferência de delegado_genero (M/F) a partir de Dr./Dra.
4. Salvar minuta via API preserva delegado_genero e escrivao no YAML frontmatter e na leitura subsequente.
5. ler_minuta reconhece títulos com '##' ou '###', sem distinção de caixa/acento, e preserva subtítulos internos (ex: '### Caminho do dinheiro').
6. index.html contém os campos 'delegado_genero' e 'escrivao' na lista META do editor.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

AQUI = Path(__file__).resolve().parent
APP_DIR = AQUI.parent
PLUGIN_DIR = APP_DIR.parent
sys.path.insert(0, str(PLUGIN_DIR / "skills" / "base-cpj" / "scripts"))
sys.path.insert(0, str(APP_DIR))

import rotas.relatorios as RR  # noqa: E402


class TesteMinutaCamposRV07(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = tempfile.mkdtemp(prefix="cpj-teste-rv07-")
        cls.env_ant = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = cls.ws

        for pasta in ("config", "usuarios", "casos", "producao", "exportacoes", "modelos"):
            os.makedirs(os.path.join(cls.ws, pasta), exist_ok=True)

        modelo = os.path.join(cls.ws, "casos", "_MODELO-CASO")
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            os.makedirs(os.path.join(modelo, pasta), exist_ok=True)
        with open(os.path.join(modelo, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}, f)

        # Caso 1: Caso com BO e IP local no caso.json (padrão antigo a ser saneado na minuta nova)
        caso1 = os.path.join(cls.ws, "casos", "OS-701-2026")
        shutil.copytree(modelo, caso1, dirs_exist_ok=True)
        with open(os.path.join(caso1, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": "OS-701-2026",
                "ordem_servico": "701/2026",
                "bo": "AB0001/2026",
                "inquerito": "0001/2026",
                "processo": "0000701-01.2026.8.26.0000",
                "referencia": "BO AB0001/2026 / IP 0001/2026",
                "natureza": "Estelionato",
                "requisitante": "Dra. Delegada Titular Fictícia",
                "escrivao": "Escrivão Fictício A",
                "status": "recebido",
                "datas": {"recebido": "2026-10-01"},
                "relatorios": []
            }, f)

        # Caso 2: Caso sem inquérito nem processo
        caso2 = os.path.join(cls.ws, "casos", "OS-702-2026")
        shutil.copytree(modelo, caso2, dirs_exist_ok=True)
        with open(os.path.join(caso2, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": "OS-702-2026",
                "ordem_servico": "702/2026",
                "requisitante": "Dr. Delegado Titular Masculino",
                "status": "recebido",
                "datas": {"recebido": "2026-10-01"},
                "relatorios": []
            }, f)

        import servidor as S
        from rotas import comum
        import caso as C_mod
        C_mod.WS = cls.ws
        C_mod.CASOS = os.path.join(cls.ws, "casos")
        C_mod.MODELO = os.path.join(C_mod.CASOS, "_MODELO-CASO")
        comum.WS = cls.ws
        comum.C.WS = cls.ws
        comum.C.CASOS = C_mod.CASOS
        comum.C.MODELO = C_mod.MODELO
        S.WS = cls.ws
        S.auth = S.Auth(cls.ws)
        S.auth.salvar_usuario("admin", "Admin Teste", "admin", "Admin12345")
        cls.servidor = S
        cls.app = S.app
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

        r_login = cls.client.post(
            "/api/entrar",
            json={"login": "admin", "senha": "Admin12345"},
            headers={"X-CPJ": "1"}
        )
        assert r_login.status_code == 200, "Login falhou"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)
        if cls.env_ant is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_ant

    def test_01_minuta_nova_referencia_padrao_sem_bo(self):
        r = self.client.get("/api/casos/OS-701-2026/minuta", headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        meta = r.get_json().get("meta", {})
        ref = meta.get("referencia", "")

        # Deve conter IPe nº e Processo nº
        self.assertIn("IPe nº 0001/2026", ref)
        self.assertIn("Processo nº 0000701-01.2026.8.26.0000", ref)

        # Regra 13: NUNCA deve conter BO nem IP local
        self.assertNotIn("BO", ref)
        self.assertNotIn("IP 0001", ref)

    def test_02_minuta_nova_campos_pendentes(self):
        r = self.client.get("/api/casos/OS-702-2026/minuta", headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        meta = r.get_json().get("meta", {})
        ref = meta.get("referencia", "")
        self.assertIn("IPe nº [PENDENTE]", ref)
        self.assertIn("Processo nº [PENDENTE]", ref)

    def test_03_delegado_genero_inferido(self):
        # Caso 1 tem 'Dra.' -> F
        r1 = self.client.get("/api/casos/OS-701-2026/minuta", headers={"X-CPJ": "1"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.get_json().get("meta", {}).get("delegado_genero"), "F")

        # Caso 2 tem 'Dr.' -> M
        r2 = self.client.get("/api/casos/OS-702-2026/minuta", headers={"X-CPJ": "1"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.get_json().get("meta", {}).get("delegado_genero"), "M")

    def test_04_salvar_minuta_preserva_delegado_genero_e_escrivao(self):
        payload = {
            "meta": {
                "ordem_servico": "701/2026",
                "referencia": "IPe nº 0001/2026 / Processo nº 0000701-01.2026.8.26.0000",
                "natureza": "Estelionato",
                "investigados": "Investigado Teste",
                "vitimas": "Vítima Teste",
                "local": "Presidente Prudente, SP",
                "data_fatos": "01/01/2026",
                "local_data": "Presidente Prudente, SP, 01 de outubro de 2026",
                "data_rodape": "01/10/2026",
                "delegado": "Dra. Delegada Titular Fictícia",
                "delegado_genero": "F",
                "escrivao": "Escrivão Oficial Fictício",
            },
            "secoes": {
                "RESUMO DOS FATOS": "Resumo dos fatos fictício.",
                "DILIGÊNCIAS REALIZADAS": "Diligências realizadas fictícias.",
                "CONCLUSÃO": "Conclusão fictícia."
            },
            "gerar_docx": False
        }

        r = self.client.post("/api/casos/OS-701-2026/minuta", json=payload, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        nome_arq = r.get_json().get("arquivo")
        self.assertTrue(nome_arq.startswith("minuta-v"))

        # Confere o conteúdo salvo no disco
        caminho_md = Path(self.ws) / "casos" / "OS-701-2026" / "03-relatorios" / nome_arq
        self.assertTrue(caminho_md.exists())
        texto_md = caminho_md.read_text(encoding="utf-8")
        self.assertIn("delegado_genero: F", texto_md)
        self.assertIn("escrivao: Escrivão Oficial Fictício", texto_md)

        # Confere leitura subsequente via GET
        r_get = self.client.get(f"/api/casos/OS-701-2026/minuta?arquivo={nome_arq}", headers={"X-CPJ": "1"})
        self.assertEqual(r_get.status_code, 200)
        meta_lida = r_get.get_json().get("meta", {})
        self.assertEqual(meta_lida.get("delegado_genero"), "F")
        self.assertEqual(meta_lida.get("escrivao"), "Escrivão Oficial Fictício")

    def test_05_ler_minuta_reconhece_variacoes_de_titulos(self):
        texto = """---
caso: OS-701-2026
delegado_genero: M
---

### Resumo dos Fatos

Texto de fatos do inquérito.

## Diligencias Realizadas

### Caminho do dinheiro
| Data | Valor |
| 01/01/2026 | R$ 100,00 |

## Conclusao

Texto de conclusão dos fatos apurados.
"""
        meta, secoes = RR.ler_minuta(texto)
        self.assertEqual(meta.get("delegado_genero"), "M")
        self.assertIn("Texto de fatos do inquérito.", secoes.get("RESUMO DOS FATOS", ""))
        # Subtítulo interno mantido em Diligências
        self.assertIn("### Caminho do dinheiro", secoes.get("DILIGÊNCIAS REALIZADAS", ""))
        self.assertIn("R$ 100,00", secoes.get("DILIGÊNCIAS REALIZADAS", ""))
        # Sem acento reconhecido
        self.assertIn("Texto de conclusão", secoes.get("CONCLUSÃO", ""))

    def test_06_index_html_contem_meta_delegado_genero_e_escrivao(self):
        caminho_html = PLUGIN_DIR / "app" / "static" / "index.html"
        self.assertTrue(caminho_html.exists())
        conteudo = caminho_html.read_text(encoding="utf-8")
        self.assertIn('"delegado_genero"', conteudo)
        self.assertIn('"escrivao"', conteudo)


if __name__ == "__main__":
    unittest.main()
