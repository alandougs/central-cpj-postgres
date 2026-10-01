#!/usr/bin/env python3
"""V04 — gate de entrega da minuta (conferir_minuta.py) com caso e dados fictícios.

Monta um workspace temporário (CPJ_WORKSPACE) com transcrição fictícia de 5 páginas e confere:
minuta limpa -> entrega 0; seis minutas com um defeito cada -> entrega 1 com o código certo;
diagnostico -> sempre 0; minuta intacta (SHA-256 antes/depois); achados REVISAR não bloqueiam.
Nunca lê casos reais do workspace.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parents[1] / "skills" / "relatorio-ip-fraude" / "scripts" / "conferir_minuta.py"
CASO = "OS-900-2026"

TRANSCRICAO = """# Transcrição — ip-ficticio.pdf

- SHA-256 do original: `0000000000000000000000000000000000000000000000000000000000000000`
- Páginas: 5 | Gerado em: 2026-09-28T10:00:00
- Numeração: `Página N` = página do arquivo PDF (não confundir com fls. dos autos).

---
## Página 1
<!-- método: texto-nativo -->

BOLETIM DE OCORRÊNCIA FICTÍCIO Nº XY0001/2026
Vítima: MARIA FICTÍCIA DA SILVA, CPF 321.654.987-10, telefone (18) 99876-5432.
Relata que, em 10/03/2026, recebeu mensagem de pessoa não identificada e fez duas transferências via Pix.

---
## Página 2
<!-- método: texto-nativo -->

COMPROVANTE DE TRANSFERÊNCIA PIX (FICTÍCIO)
Valor: R$ 1.500,00
Data: 10/03/2026 15:30
Chave Pix do recebedor: pagador.ficticio@exemplo.com
Recebedor: JOÃO FICTÍCIO - CPF ***.852.963-**
ID da transação: E12345678202603101530AbCdEfGhIjK

---
## Página 3
<!-- método: ocr | confiança OCR 58% | ⚠ CONFERIR -->

COMPROVANTE PIX (FICTÍCIO)
Valor: R$ 2.300,50
Chave aleatória: 7f3c2a10-1b2c-4d5e-8f90-a1b2c3d4e5f6

---
## Página 4
<!-- método: texto-nativo -->

OFÍCIO RESPOSTA - BANCO FICTÍCIO S.A.
Titular: JOÃO FICTÍCIO
CPF: 741.852.963-00
Agência: 0001  Conta: 12345-6
Telefone cadastrado: (11) 91234-0000

---
## Página 5
<!-- método: pendente-transcricao-visual -->

[PENDENTE: transcrição visual]
"""

RELATORIO_EXTRACAO = {
    "arquivo": "ip-ficticio.pdf", "paginas": 5,
    "metodos": {"texto-nativo": 3, "ocr": 1, "pendente-transcricao-visual": 1},
    "pendentes_transcricao_visual": [5], "conferir_visualmente": [3],
}

FLUXO = ("seq;data;hora;valor;meio;id_transacao;origem_titular;origem_banco;origem_ag_conta;origem_chave;"
         "destino_titular;destino_banco;destino_ag_conta;destino_chave;camada;fonte_pag;fls;status_conferencia\n"
         "1;10/03/2026;15:30;1500.00;pix;;VÍTIMA;;;;RECEBEDOR;;;;1;2;4;pendente\n"
         "2;10/03/2026;16:10;2300.50;pix;;VÍTIMA;;;;RECEBEDOR;;;;1;3;5;pendente\n")

LIMPA = """---
caso: OS-900-2026
versao: 01
ordem_servico: 900/2026
referencia: IPe nº 900001/2026 / Processo nº 0000900-01.2026.8.26.0000
delegado_genero: M
natureza: Estelionato (art. 171, CP)
investigados: JOÃO FICTÍCIO
vitimas: MARIA FICTÍCIA DA SILVA
local: Rua Fictícia, 100, Presidente Prudente/SP
data_fatos: 10/03/2026
local_data: Presidente Prudente, SP, 28 de setembro de 2026
data_rodape: 28/09/2026
delegado: Dra. Delegada Fictícia
---
## RESUMO DOS FATOS

Consta do boletim de ocorrência que a vítima MARIA FICTÍCIA DA SILVA, CPF 321.654.987-10, telefone (18) 99876-5432, relatou ter sido induzida a realizar transferências via Pix (pág. 1 do PDF; fls. 3).

## DILIGÊNCIAS REALIZADAS

Foi analisado o comprovante de transferência de R$ 1.500,00 para a chave Pix pagador.ficticio@exemplo.com, com identificador E12345678202603101530AbCdEfGhIjK (pág. 2 do PDF; fls. 4).
A segunda transferência, de R$ 2.300,50, teve como destino a chave aleatória 7f3c2a10-1b2c-4d5e-8f90-a1b2c3d4e5f6 (pág. 3 do PDF; fls. 5).
Segundo o ofício bancário, a conta recebedora (agência 0001, conta 12345-6) é de titularidade do investigado JOÃO FICTÍCIO, CPF 741.852.963-00, telefone (11) 91234-0000 (pág. 4 do PDF; fls. 6).

| Data | Destino | Valor (R$) | Fonte |
| --- | --- | ---: | --- |
| 10/03/2026 | chave e-mail | R$ 1.500,00 | pág. 2 |
| 10/03/2026 | chave aleatória | R$ 2.300,50 | pág. 3 |
| Total | — | R$ 3.800,50 | cálculo (págs. 2-3) |

## CONCLUSÃO

Há indícios de que os valores transferidos pela vítima tiveram como destino conta de titularidade do investigado, sem elementos, até o momento, para afirmar a autoria (pág. 4 do PDF; fls. 6).
"""


def trocar(texto, antigo, novo):
    assert texto.count(antigo) == 1, antigo
    return texto.replace(antigo, novo)


# versão -> (minuta, código BLOQUEIA esperado)
DEFEITOS = {
    "02": (trocar(LIMPA, "delegado: Dra. Delegada Fictícia", "delegado: {Nome do Delegado}"), "PENDENTE"),
    "03": (trocar(LIMPA, " (pág. 1 do PDF; fls. 3)", ""), "SEM_REFERENCIA"),
    "04": (trocar(LIMPA, "(pág. 2 do PDF; fls. 4)", "(pág. 9 do PDF; fls. 4)"), "PAGINA_INEXISTENTE"),
    "05": (trocar(LIMPA, "R$ 1.500,00 para a chave", "R$ 1.550,00 para a chave"), "NAO_LOCALIZADO"),
    "06": (trocar(LIMPA, "(pág. 3 do PDF; fls. 5)", "(pág. 4 do PDF; fls. 5)"), "OUTRA_PAGINA"),
    "07": (LIMPA.split("## CONCLUSÃO")[0], "SECAO_AUSENTE"),
}
TOTAL_FLUXO = LIMPA + "O prejuízo apurado corresponde a R$ 3.800,50 (pág. 2 do PDF).\n"
REVISAR = trocar(LIMPA, "CPF 741.852.963-00", "CPF 741.852.96?-00 [dígito incerto]") + \
    "JOÃO FICTÍCIO é o autor do golpe (pág. 4 do PDF; fls. 6).\n"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class TesteGateV04(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-gate-v04-")
        cls.ws = Path(cls.temp.name)
        (cls.ws / "modelos").mkdir()
        caso = cls.ws / "casos" / CASO
        for sub in ("00-originais", "02-analise", "03-relatorios"):
            (caso / sub).mkdir(parents=True)
        doc = caso / "01-extracao" / "ip-ficticio"
        doc.mkdir(parents=True)
        (doc / "transcricao.md").write_text(TRANSCRICAO, encoding="utf-8")
        (doc / "relatorio_extracao.json").write_text(json.dumps(RELATORIO_EXTRACAO), encoding="utf-8")
        (caso / "02-analise" / "fluxo-financeiro.csv").write_text(FLUXO, encoding="utf-8-sig")
        cls.rel = caso / "03-relatorios"
        cls.extracao = caso / "01-extracao"
        (cls.rel / "minuta-v01.md").write_text(LIMPA, encoding="utf-8")
        for v, (texto, _) in DEFEITOS.items():
            (cls.rel / f"minuta-v{v}.md").write_text(texto, encoding="utf-8")
        (cls.rel / "minuta-v9.md").write_text(TOTAL_FLUXO, encoding="utf-8")   # testa ordenação numérica (9 < 10)
        (cls.rel / "minuta-v10.md").write_text(REVISAR, encoding="utf-8")
        cls.env = {**os.environ, "PYTHONUTF8": "1", "CPJ_WORKSPACE": str(cls.ws)}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rodar(self, *args, minuta=None):
        """Roda o gate; confere que a minuta não foi alterada e devolve (código, json da conferência)."""
        antes = sha(minuta) if minuta else None
        r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                           encoding="utf-8", env=self.env, cwd=str(self.ws), timeout=60)
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
        if minuta:
            self.assertEqual(antes, sha(minuta), "a minuta foi alterada pelo gate")
        m = [ln for ln in r.stdout.splitlines() if ln.startswith("Conferência: ")]
        self.assertTrue(m, r.stdout + r.stderr)
        caminho_md = Path(m[-1].split(": ", 1)[1])
        self.assertTrue(caminho_md.is_file())
        return r.returncode, json.loads(caminho_md.with_suffix(".json").read_text(encoding="utf-8"))

    @staticmethod
    def codigos(res, nivel):
        return {a["codigo"] for a in res["achados"] if a["nivel"] == nivel}

    def test_minuta_limpa_aprovada(self):
        cod, res = self.rodar(CASO, "--versao", "01", "--modo", "entrega", minuta=self.rel / "minuta-v01.md")
        self.assertEqual(cod, 0, json.dumps(res["achados"], ensure_ascii=False, indent=1))
        self.assertTrue(res["aprovado"])
        self.assertEqual(res["resumo"]["BLOQUEIA"], 0)
        self.assertEqual(res["schema"], "cpj-conferencia/1")
        self.assertEqual(res["minuta"], "minuta-v01.md")
        self.assertTrue((self.rel / "conferencia-v01.md").is_file())
        self.assertTrue((self.rel / "conferencia-v01.json").is_file())
        # CPF, telefone, e-mail Pix, ID, chave aleatória, agência, conta e valores conferidos na página citada
        tipos = {c["tipo"] for c in res["conferidos"]}
        self.assertTrue({"cpf", "telefone", "chave_pix", "id_transacao", "agencia", "conta", "valor"} <= tipos, tipos)
        # total da tabela é cálculo (REVISAR) e a pág. 3 está marcada para conferência visual (REVISAR)
        self.assertIn("CALCULO", self.codigos(res, "REVISAR"))
        self.assertIn("PAGINA_CONFERIR", self.codigos(res, "REVISAR"))
        chaves = {"nivel", "codigo", "linha", "secao", "tipo", "dado", "citado", "paginas_citadas", "localizado_em",
                  "detalhe", "trecho"}
        for a in res["achados"] + res["conferidos"]:
            self.assertEqual(set(a), chaves)

    def test_defeitos_bloqueiam_entrega(self):
        for v, (_, esperado) in DEFEITOS.items():
            with self.subTest(versao=v, codigo=esperado):
                minuta = self.rel / f"minuta-v{v}.md"
                cod, res = self.rodar(CASO, "--versao", v, "--modo", "entrega", minuta=minuta)
                self.assertEqual(cod, 1)
                self.assertFalse(res["aprovado"])
                self.assertIn(esperado, self.codigos(res, "BLOQUEIA"),
                              json.dumps(res["achados"], ensure_ascii=False, indent=1))
                cod_d, res_d = self.rodar(CASO, "--versao", v, minuta=minuta)  # padrão = diagnostico
                self.assertEqual(cod_d, 0)
                self.assertEqual(res_d["modo"], "diagnostico")
                self.assertIn(esperado, self.codigos(res_d, "BLOQUEIA"))

    def test_revisar_nao_bloqueia(self):
        # sem --versao: a mais recente por número (v10, não v9)
        cod, res = self.rodar(CASO, "--modo", "entrega", minuta=self.rel / "minuta-v10.md")
        self.assertEqual(res["minuta"], "minuta-v10.md")
        self.assertEqual(cod, 0, json.dumps(res["achados"], ensure_ascii=False, indent=1))
        self.assertEqual(res["resumo"]["BLOQUEIA"], 0)
        revisar = self.codigos(res, "REVISAR")
        self.assertIn("DIGITO_INCERTO", revisar)
        self.assertIn("AUTORIA_AFIRMATIVA", revisar)

    def test_total_do_fluxo_financeiro(self):
        minuta = self.rel / "minuta-v9.md"
        cod, res = self.rodar(CASO, "--versao", "9", "--modo", "entrega", minuta=minuta)
        self.assertEqual(cod, 0, json.dumps(res["achados"], ensure_ascii=False, indent=1))
        self.assertTrue(any(a["codigo"] == "CALCULO" and a["dado"] == "R$ 3.800,50" and a["linha"] > 30
                            for a in res["achados"]))
        # sem o fluxo-financeiro.csv o mesmo total não tem fonte: bloqueia
        avulsa = self.ws / "avulsa"
        avulsa.mkdir(exist_ok=True)
        copia = avulsa / "minuta-v9.md"
        shutil.copyfile(minuta, copia)
        cod, res = self.rodar("--minuta", str(copia), "--extracao", str(self.extracao), "--modo", "entrega",
                              minuta=copia)
        self.assertEqual(cod, 1)
        self.assertIn("NAO_LOCALIZADO", self.codigos(res, "BLOQUEIA"))
        self.assertTrue((avulsa / "conferencia-v9.json").is_file())

    def test_secao_em_nivel_errado(self):
        avulsa = self.ws / "avulsa-secao"
        avulsa.mkdir(exist_ok=True)
        copia = avulsa / "minuta-v01.md"
        copia.write_text(LIMPA.replace("## RESUMO DOS FATOS", "### RESUMO DOS FATOS"), encoding="utf-8")
        cod, res = self.rodar("--minuta", str(copia), "--extracao", str(self.extracao), "--modo", "entrega",
                              minuta=copia)
        self.assertEqual(cod, 1)
        secao = [a for a in res["achados"] if a["codigo"] == "SECAO_AUSENTE"]
        self.assertTrue(secao and "gerar_docx" in secao[0]["detalhe"])

    def test_erros_de_entrada(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "OS-INEXISTENTE-2026", "--modo", "entrega"],
                           capture_output=True, text=True, encoding="utf-8", env=self.env, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn("caso não encontrado", r.stderr)
        r = subprocess.run([sys.executable, str(SCRIPT), CASO, "--versao", "77"],
                           capture_output=True, text=True, encoding="utf-8", env=self.env, timeout=60)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
