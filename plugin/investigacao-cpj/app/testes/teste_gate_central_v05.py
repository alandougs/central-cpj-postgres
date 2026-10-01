#!/usr/bin/env python3
"""V05 — Gate de entrega do relatório FINAL na Central CPJ.

Valida:
1. DOCX inexistente -> 400.
2. Minuta com itens bloqueantes -> 409 Conflict, com lista de achados, sem criação do FINAL e sem baixa.
3. Forçar entrega com justificativa ausente ou menor que 15 caracteres -> 400 Bad Request.
4. Forçar entrega com justificativa >= 15 caracteres -> 200 OK, gera FINAL, baixa com ressalva e registra em auditoria.log.
5. Minuta limpa -> 200 OK sem necessidade de forçar, gera FINAL, baixa sem ressalva e registra auditoria.
Usa workspace temporário isolado e dados 100% fictícios.
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
sys.path.insert(0, str(PLUGIN_DIR / "skills" / "relatorio-ip-fraude" / "scripts"))
sys.path.insert(0, str(APP_DIR))

TRANSCRICAO_FICTICIA = """# Transcrição — ip-ficticio.pdf

- SHA-256 do original: `0000000000000000000000000000000000000000000000000000000000000000`
- Páginas: 3 | Gerado em: 2026-10-01T10:00:00

---
## Página 1
<!-- método: texto-nativo -->

TERMO DE DECLARAÇÕES (FICTÍCIO)
Vítima: MARIA SILVA FICTÍCIA, CPF 111.222.333-44, telefone (18) 99111-2222.
Declara ter sofrido golpe financeiro em 10/03/2026.

---
## Página 2
<!-- método: texto-nativo -->

COMPROVANTE DE TRANSFERÊNCIA PIX (FICTÍCIO)
Valor: R$ 1.500,00
Data: 10/03/2026 14:00
Chave Pix recebedora: recebedor.ficticio@exemplo.com
Recebedor: JOÃO SILVA FICTÍCIO, CPF ***.444.555-**
ID da transação: E99998888202603101400AbCdEfGhIjK

---
## Página 3
<!-- método: texto-nativo -->

OFÍCIO RESPOSTA BANCÁRIA (FICTÍCIO)
Titular: JOÃO SILVA FICTÍCIO
CPF: 333.444.555-66
Agência: 0001 Conta: 98765-4
"""

MINUTA_COM_BLOQUEIOS = """---
caso: OS-901-2026
versao: 01
ordem_servico: 901/2026
referencia: BO nº 12345/2026
delegado_genero: M
natureza: Estelionato (art. 171 do CP)
investigados: JOÃO SILVA FICTÍCIO
vitimas: MARIA SILVA FICTÍCIA
local: Presidente Prudente/SP
data_fatos: 10/03/2026
local_data: Presidente Prudente, SP, 01 de outubro de 2026
data_rodape: 01/10/2026
delegado: Dr. Delegado Fictício
---
## RESUMO DOS FATOS

[PREENCHER: descrever dinâmica do golpe aqui].
A vítima MARIA SILVA FICTÍCIA realizou transferências.

## DILIGÊNCIAS REALIZADAS

Identificou-se transferência de R$ 9.999,00 sem referência nos autos.

## CONCLUSÃO

O investigado é culpado pelo crime praticado.
"""

MINUTA_LIMPA = """---
caso: OS-902-2026
versao: 01
ordem_servico: 902/2026
referencia: IPe nº 902001/2026 / Processo nº 0000902-01.2026.8.26.0000
delegado_genero: M
natureza: Estelionato (art. 171 do CP)
investigados: JOÃO SILVA FICTÍCIO
vitimas: MARIA SILVA FICTÍCIA
local: Presidente Prudente/SP
data_fatos: 10/03/2026
local_data: Presidente Prudente, SP, 01 de outubro de 2026
data_rodape: 01/10/2026
delegado: Dr. Delegado Fictício
---
## RESUMO DOS FATOS

Consta do termo de declarações que a vítima MARIA SILVA FICTÍCIA, CPF 111.222.333-44, telefone (18) 99111-2222, noticiou ter realizado transferência (pág. 1 do PDF; fls. 1).

## DILIGÊNCIAS REALIZADAS

Constatou-se transferência via Pix no valor de R$ 1.500,00 para a chave recebedor.ficticio@exemplo.com com o identificador E99998888202603101400AbCdEfGhIjK (pág. 2 do PDF; fls. 2).
Segundo ofício bancário, a conta indicada (agência 0001, conta 98765-4) pertence ao investigado JOÃO SILVA FICTÍCIO, CPF 333.444.555-66 (pág. 3 do PDF; fls. 3).

## CONCLUSÃO

Em tese, há indícios de que os valores foram recebidos pela conta do investigado, demandando aprofundamento das apurações.
"""


class TesteGateCentralV05(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = tempfile.mkdtemp(prefix="cpj-teste-v05-")
        cls.env_ant = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = cls.ws

        for pasta in ("config", "usuarios", "casos", "producao", "exportacoes", "modelos"):
            os.makedirs(os.path.join(cls.ws, pasta), exist_ok=True)

        modelo = os.path.join(cls.ws, "casos", "_MODELO-CASO")
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            os.makedirs(os.path.join(modelo, pasta), exist_ok=True)
        with open(os.path.join(modelo, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}, f)

        # Configura caso com bloqueios OS-901-2026
        caso1 = os.path.join(cls.ws, "casos", "OS-901-2026")
        shutil.copytree(modelo, caso1, dirs_exist_ok=True)
        with open(os.path.join(caso1, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": "OS-901-2026", "ordem_servico": "901/2026", "status": "minuta",
                "datas": {"recebido": "2026-10-01", "minuta": "2026-10-01"},
                "relatorios": []
            }, f)
        doc1 = os.path.join(caso1, "01-extracao", "ip-ficticio")
        os.makedirs(doc1, exist_ok=True)
        with open(os.path.join(doc1, "transcricao.md"), "w", encoding="utf-8") as f:
            f.write(TRANSCRICAO_FICTICIA)
        with open(os.path.join(caso1, "03-relatorios", "minuta-v01.md"), "w", encoding="utf-8") as f:
            f.write(MINUTA_COM_BLOQUEIOS)
        # Cria docx simulado
        with open(os.path.join(caso1, "03-relatorios", "RELATORIO-OS-901-2026-v01.docx"), "wb") as f:
            f.write(b"PK\x03\x04simulado")

        # Configura caso limpo OS-902-2026
        caso2 = os.path.join(cls.ws, "casos", "OS-902-2026")
        shutil.copytree(modelo, caso2, dirs_exist_ok=True)
        with open(os.path.join(caso2, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": "OS-902-2026", "ordem_servico": "902/2026", "status": "minuta",
                "datas": {"recebido": "2026-10-01", "minuta": "2026-10-01"},
                "relatorios": []
            }, f)
        doc2 = os.path.join(caso2, "01-extracao", "ip-ficticio")
        os.makedirs(doc2, exist_ok=True)
        with open(os.path.join(doc2, "transcricao.md"), "w", encoding="utf-8") as f:
            f.write(TRANSCRICAO_FICTICIA)
        with open(os.path.join(caso2, "03-relatorios", "minuta-v01.md"), "w", encoding="utf-8") as f:
            f.write(MINUTA_LIMPA)
        with open(os.path.join(caso2, "03-relatorios", "RELATORIO-OS-902-2026-v01.docx"), "wb") as f:
            f.write(b"PK\x03\x04simulado")

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

        # Autentica o cliente de teste como admin
        r_login = cls.client.post(
            "/api/entrar",
            json={"login": "admin", "senha": "Admin12345"},
            headers={"X-CPJ": "1"}
        )
        assert r_login.status_code == 200, f"Falha no login de teste: {r_login.get_json()}"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ws, ignore_errors=True)
        if cls.env_ant is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env_ant

    def test_01_final_sem_docx_retorna_400(self):
        r = self.client.post("/api/casos/OS-901-2026/final", json={}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("DOCX não encontrado", r.get_json().get("erro", ""))

    def test_02_final_minuta_com_bloqueios_reprova_409(self):
        payload = {"docx": "RELATORIO-OS-901-2026-v01.docx"}
        r = self.client.post("/api/casos/OS-901-2026/final", json=payload, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 409)
        j = r.get_json()
        self.assertFalse(j.get("ok"))
        self.assertTrue(j.get("bloqueado"))
        self.assertGreater(j.get("bloqueios", 0), 0)
        self.assertIsInstance(j.get("achados"), list)
        self.assertGreater(len(j.get("achados")), 0)

        # Garante que não criou o relatório final nem deu baixa
        final_docx = Path(self.ws) / "casos" / "OS-901-2026" / "03-relatorios" / "RELATORIO-OS-901-2026-FINAL.docx"
        self.assertFalse(final_docx.exists())

        caso_data = json.loads((Path(self.ws) / "casos" / "OS-901-2026" / "caso.json").read_text(encoding="utf-8"))
        self.assertNotEqual(caso_data.get("status"), "entregue")
        self.assertNotIn("baixa", caso_data)

    def test_03_final_forcar_sem_justificativa_retorna_400(self):
        # Sem justificativa
        r1 = self.client.post(
            "/api/casos/OS-901-2026/final",
            json={"docx": "RELATORIO-OS-901-2026-v01.docx", "forcar": True, "justificativa": ""},
            headers={"X-CPJ": "1"}
        )
        self.assertEqual(r1.status_code, 400)
        self.assertIn("15 caracteres", r1.get_json().get("erro", ""))

        # Justificativa curta (< 15 caracteres)
        r2 = self.client.post(
            "/api/casos/OS-901-2026/final",
            json={"docx": "RELATORIO-OS-901-2026-v01.docx", "forcar": True, "justificativa": "curto demais"},
            headers={"X-CPJ": "1"}
        )
        self.assertEqual(r2.status_code, 400)
        self.assertIn("15 caracteres", r2.get_json().get("erro", ""))

    def test_04_final_forcar_com_justificativa_aprova_200(self):
        justificativa = "Ressalva formal autorizada pelo delegado para prosseguimento"
        r = self.client.post(
            "/api/casos/OS-901-2026/final",
            json={"docx": "RELATORIO-OS-901-2026-v01.docx", "forcar": True, "justificativa": justificativa},
            headers={"X-CPJ": "1"}
        )
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get("ok"))
        self.assertEqual(j.get("final"), "RELATORIO-OS-901-2026-FINAL.docx")
        self.assertEqual(j.get("ressalva"), justificativa)

        # Arquivo final criado
        final_docx = Path(self.ws) / "casos" / "OS-901-2026" / "03-relatorios" / "RELATORIO-OS-901-2026-FINAL.docx"
        self.assertTrue(final_docx.exists())

        # Baixa registrada com ressalva
        caso_data = json.loads((Path(self.ws) / "casos" / "OS-901-2026" / "caso.json").read_text(encoding="utf-8"))
        self.assertEqual(caso_data.get("status"), "entregue")
        self.assertIn("baixa", caso_data)
        self.assertEqual(caso_data["baixa"].get("ressalva"), justificativa)

        # Auditoria gravada
        audit_log = Path(self.ws) / "config" / "auditoria.log"
        self.assertTrue(audit_log.exists())
        self.assertIn("relatorio_final_ressalva", audit_log.read_text(encoding="utf-8"))

    def test_05_final_minuta_limpa_aprova_200_sem_forcar(self):
        r = self.client.post(
            "/api/casos/OS-902-2026/final",
            json={"docx": "RELATORIO-OS-902-2026-v01.docx"},
            headers={"X-CPJ": "1"}
        )
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertTrue(j.get("ok"))
        self.assertEqual(j.get("final"), "RELATORIO-OS-902-2026-FINAL.docx")
        self.assertNotIn("ressalva", j)

        # Arquivo final criado
        final_docx = Path(self.ws) / "casos" / "OS-902-2026" / "03-relatorios" / "RELATORIO-OS-902-2026-FINAL.docx"
        self.assertTrue(final_docx.exists())

        # Baixa registrada sem ressalva
        caso_data = json.loads((Path(self.ws) / "casos" / "OS-902-2026" / "caso.json").read_text(encoding="utf-8"))
        self.assertEqual(caso_data.get("status"), "entregue")
        self.assertIn("baixa", caso_data)
        self.assertIsNone(caso_data["baixa"].get("ressalva"))

        # Auditoria gravada
        audit_log = Path(self.ws) / "config" / "auditoria.log"
        self.assertTrue(audit_log.exists())
        self.assertIn("relatorio_final", audit_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
