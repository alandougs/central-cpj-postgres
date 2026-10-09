#!/usr/bin/env python3
"""RV18 — o gate da entrega só aceita conferência NOVA, da minuta ATUAL (sha256), em modo entrega, e falha fechado.
Reproduz: JSON antigo lido quando o verificador falha; JSON ilegível + saída 0 aprovando sem achados.
Workspace temporário, dados fictícios, sem rede."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from teste_gate_v04 import LIMPA, RELATORIO_EXTRACAO, TRANSCRICAO  # noqa: E402

RUIM = LIMPA.replace("R$ 1.500,00 para a chave", "R$ 7.777,77 para a chave")


def sha(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


class GateConferenciaRV18(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-gate-rv18-", ignore_cleanup_errors=True)
        cls.ws = Path(cls.temp.name)
        cls.env = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True, exist_ok=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}),
                                          encoding="utf-8")
        sys.path.insert(0, str(AQUI.parent))
        import servidor
        from rotas import relatorios
        cls.s, cls.rel = servidor, relatorios

    @classmethod
    def tearDownClass(cls):
        import time
        time.sleep(1.0)
        for a in cls.ws.rglob("*"):
            if a.is_file():
                a.chmod(0o600)
        cls.temp.cleanup()
        if cls.env is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = cls.env

    def novo_caso(self, minuta):
        self.__class__.n = getattr(self.__class__, "n", 0) + 1
        id_ = self.s.C.novo(f"{920 + self.n}/2099")["id"]
        p = Path(self.s.C.caminho(id_))
        ext = p / "01-extracao" / "ip-ficticio"
        ext.mkdir(parents=True)
        (ext / "transcricao.md").write_text(TRANSCRICAO, encoding="utf-8")
        (ext / "relatorio_extracao.json").write_text(json.dumps(RELATORIO_EXTRACAO), encoding="utf-8")
        (p / "03-relatorios" / "minuta-v01.md").write_text(minuta, encoding="utf-8")
        return id_, p

    def gate(self, id_):
        return self.rel.conferir_minuta_gate(id_, "minuta-v01.md")

    def codigos(self, conf):
        return [a.get("codigo") for a in conf.get("achados", [])]

    # --- linha de base: o caminho feliz continua funcionando
    def test_01_minuta_limpa_aprova_e_devolve_o_hash_da_minuta(self):
        id_, p = self.novo_caso(LIMPA)
        conf = self.gate(id_)
        self.assertTrue(conf["aprovado"], conf)
        self.assertEqual(conf.get("sha256_minuta"), sha(p / "03-relatorios" / "minuta-v01.md"))

    def test_02_minuta_ruim_bloqueia(self):
        id_, _ = self.novo_caso(RUIM)
        conf = self.gate(id_)
        self.assertFalse(conf["aprovado"])
        self.assertTrue(any(a["nivel"] == "BLOQUEIA" for a in conf["achados"]))

    # --- reproduções
    def test_03_json_antigo_aprovado_nao_vale_quando_o_verificador_falha(self):
        id_, p = self.novo_caso(RUIM)
        antigo = {"schema": "cpj-conferencia/1", "minuta": "minuta-v01.md", "versao": "01", "modo": "entrega", "aprovado": True,
                  "sha256_minuta": sha(p / "03-relatorios" / "minuta-v01.md"), "achados": [], "conferidos": [],
                  "gerado_em": "2020-01-01T00:00:00"}
        (p / "03-relatorios" / "conferencia-v01.json").write_text(json.dumps(antigo), encoding="utf-8")
        shutil.rmtree(p / "01-extracao")  # o verificador sai com erro (pasta de extração inexistente) e não regrava o JSON
        conf = self.gate(id_)
        self.assertFalse(conf["aprovado"], "JSON antigo não pode aprovar a entrega")
        self.assertIn("ERRO_EXECUCAO", self.codigos(conf))

    def test_04_json_ilegivel_com_saida_zero_nao_aprova(self):
        id_, p = self.novo_caso(LIMPA)
        falso = subprocess.CompletedProcess([], 0, stdout="APROVADA", stderr="")

        def executa(*a, **k):
            (p / "03-relatorios" / "conferencia-v01.json").write_text("{ isso nao e json", encoding="utf-8")
            return falso
        with mock.patch.object(self.rel.subprocess, "run", side_effect=executa):
            conf = self.gate(id_)
        self.assertFalse(conf["aprovado"], "JSON ilegível não pode virar aprovação")
        self.assertIn("ERRO_EXECUCAO", self.codigos(conf))

    def test_05_json_de_outra_versao_da_minuta_nao_vale(self):
        id_, p = self.novo_caso(LIMPA)
        outro = {"schema": "cpj-conferencia/1", "minuta": "minuta-v01.md", "modo": "entrega", "aprovado": True,
                 "sha256_minuta": "0" * 64, "achados": [], "conferidos": []}

        def executa(*a, **k):  # o "verificador" devolve resultado de OUTRO conteúdo
            (p / "03-relatorios" / "conferencia-v01.json").write_text(json.dumps(outro), encoding="utf-8")
            return subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(self.rel.subprocess, "run", side_effect=executa):
            conf = self.gate(id_)
        self.assertFalse(conf["aprovado"])
        self.assertIn("CONFERENCIA_DESATUALIZADA", self.codigos(conf))

    def test_06_json_em_modo_diagnostico_nao_vale_para_entrega(self):
        id_, p = self.novo_caso(LIMPA)
        diag = {"schema": "cpj-conferencia/1", "minuta": "minuta-v01.md", "modo": "diagnostico", "aprovado": True,
                "sha256_minuta": sha(p / "03-relatorios" / "minuta-v01.md"), "achados": [], "conferidos": []}

        def executa(*a, **k):
            (p / "03-relatorios" / "conferencia-v01.json").write_text(json.dumps(diag), encoding="utf-8")
            return subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(self.rel.subprocess, "run", side_effect=executa):
            conf = self.gate(id_)
        self.assertFalse(conf["aprovado"])
        self.assertIn("CONFERENCIA_DESATUALIZADA", self.codigos(conf))

    def test_07_json_nao_regravado_nesta_execucao_nao_vale(self):
        id_, p = self.novo_caso(LIMPA)
        velho = {"schema": "cpj-conferencia/1", "minuta": "minuta-v01.md", "modo": "entrega", "aprovado": True,
                 "sha256_minuta": sha(p / "03-relatorios" / "minuta-v01.md"), "achados": [], "conferidos": []}
        jp = p / "03-relatorios" / "conferencia-v01.json"
        jp.write_text(json.dumps(velho), encoding="utf-8")
        os.utime(jp, (1_500_000_000, 1_500_000_000))  # arquivo de 2017
        with mock.patch.object(self.rel.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")):
            conf = self.gate(id_)  # o verificador "rodou" mas não gravou nada
        self.assertFalse(conf["aprovado"])
        self.assertIn("CONFERENCIA_DESATUALIZADA", self.codigos(conf))

    def test_08_json_aprovado_com_bloqueio_dentro_nao_aprova(self):
        id_, p = self.novo_caso(LIMPA)
        incoerente = {"schema": "cpj-conferencia/1", "minuta": "minuta-v01.md", "modo": "entrega", "aprovado": True,
                      "sha256_minuta": sha(p / "03-relatorios" / "minuta-v01.md"),
                      "achados": [{"nivel": "BLOQUEIA", "codigo": "VALOR_NAO_LOCALIZADO", "linha": 3, "dado": "R$ 1,00", "detalhe": "x"}],
                      "conferidos": []}

        def executa(*a, **k):
            (p / "03-relatorios" / "conferencia-v01.json").write_text(json.dumps(incoerente), encoding="utf-8")
            return subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(self.rel.subprocess, "run", side_effect=executa):
            conf = self.gate(id_)
        self.assertFalse(conf["aprovado"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
