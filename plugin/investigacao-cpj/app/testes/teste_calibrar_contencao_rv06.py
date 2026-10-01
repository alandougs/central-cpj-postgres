#!/usr/bin/env python3
"""RV06 — Contenção de calibração fática (Regra 7 de Governança).

Valida:
1. POST /api/casos/<id>/calibrar exige relatório FINAL markdown (não aceita minuta nem pasta vazia -> 400).
2. Devolve proposta de lições com 'ok: True', 'proposta: True', 'gravado: False'.
3. NÃO grava nem altera calibracao/licoes-aprendidas.md nem calibracao/historico-calibracao.md.
4. Nenhum ID de caso nem nome de investigador é persistido na pasta de calibração.
5. Operação é auditada em auditoria.log como 'calibracao_proposta'.
"""
import hashlib
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

RELATORIO_FINAL_TEXTO = """---
caso: OS-601-2026
tipo: relatorio-final
---

# RELATÓRIO DE INVESTIGAÇÃO POLICIAL

## RESUMO DOS FATOS
Consta dos autos do inquérito policial que a vítima noticiou transferência via Pix.

## DILIGÊNCIAS REALIZADAS
Identificou-se que os valores foram recebidos, em tese, pela conta do investigado (fls. 12 dos autos).
[DILIGÊNCIA POLICIAL: PESQUISAR ENDEREÇO ATUALIZADO DO INVESTIGADO]
Incluído fluxograma financeiro com o percurso das camadas bancárias.

## CONCLUSÃO
Em tese, há indícios de materialidade e autoria delitiva a serem aprofundados.
"""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


class TesteCalibrarContencaoRV06(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = tempfile.mkdtemp(prefix="cpj-teste-rv06-")
        cls.env_ant = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = cls.ws

        for pasta in ("config", "usuarios", "casos", "producao", "exportacoes", "modelos", "calibracao"):
            os.makedirs(os.path.join(cls.ws, pasta), exist_ok=True)

        modelo = os.path.join(cls.ws, "casos", "_MODELO-CASO")
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            os.makedirs(os.path.join(modelo, pasta), exist_ok=True)
        with open(os.path.join(modelo, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}, f)

        # Baseline de calibracao
        cls.licoes_path = os.path.join(cls.ws, "calibracao", "licoes-aprendidas.md")
        with open(cls.licoes_path, "w", encoding="utf-8") as f:
            f.write("# Lições Aprendidas Base\n- Regra genérica 1.\n")
        cls.hash_licoes_base = sha256(cls.licoes_path)

        cls.hist_path = os.path.join(cls.ws, "calibracao", "historico-calibracao.md")
        with open(cls.hist_path, "w", encoding="utf-8") as f:
            f.write("# Histórico Base\n| Data | Caso | Aprovado |\n")
        cls.hash_hist_base = sha256(cls.hist_path)

        # Caso 1: Apenas minuta, sem relatório final
        caso1 = os.path.join(cls.ws, "casos", "OS-601-2026")
        shutil.copytree(modelo, caso1, dirs_exist_ok=True)
        with open(os.path.join(caso1, "caso.json"), "w", encoding="utf-8") as f:
            json.dump({
                "id": "OS-601-2026", "ordem_servico": "601/2026", "status": "minuta",
                "datas": {"recebido": "2026-10-01"}, "relatorios": []
            }, f)
        with open(os.path.join(caso1, "03-relatorios", "minuta-v01.md"), "w", encoding="utf-8") as f:
            f.write("Apenas minuta preliminar.")

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

    def test_01_calibrar_sem_relatorio_final_rejeita_400(self):
        r = self.client.post("/api/casos/OS-601-2026/calibrar", json={}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Nenhum relatório final", r.get_json().get("erro", ""))

        # Garante que nenhum arquivo de calibração foi alterado
        self.assertEqual(sha256(self.licoes_path), self.hash_licoes_base)
        self.assertEqual(sha256(self.hist_path), self.hash_hist_base)

    def test_02_calibrar_com_final_retorna_proposta_sem_gravar_calibracao(self):
        # Adiciona o relatório final no caso
        caminho_final = Path(self.ws) / "casos" / "OS-601-2026" / "03-relatorios" / "RELATORIO-OS-601-2026-FINAL.md"
        caminho_final.write_text(RELATORIO_FINAL_TEXTO, encoding="utf-8")

        r = self.client.post("/api/casos/OS-601-2026/calibrar", json={}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        dados = r.get_json()

        self.assertTrue(dados.get("ok"))
        self.assertTrue(dados.get("proposta"))
        self.assertFalse(dados.get("gravado"))
        self.assertEqual(dados.get("caso"), "OS-601-2026")
        self.assertIsInstance(dados.get("licoes"), list)
        self.assertGreater(len(dados.get("licoes")), 0)

        # Regra 7 de governança: arquivos em calibracao/ NÃO devem ser modificados
        self.assertEqual(sha256(self.licoes_path), self.hash_licoes_base)
        self.assertEqual(sha256(self.hist_path), self.hash_hist_base)

        conteudo_licoes = Path(self.licoes_path).read_text(encoding="utf-8")
        conteudo_hist = Path(self.hist_path).read_text(encoding="utf-8")
        self.assertNotIn("OS-601-2026", conteudo_licoes)
        self.assertNotIn("OS-601-2026", conteudo_hist)

    def test_03_auditoria_registrada(self):
        audit_log = Path(self.ws) / "config" / "auditoria.log"
        self.assertTrue(audit_log.exists())
        self.assertIn("calibracao_proposta", audit_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
