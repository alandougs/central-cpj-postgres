#!/usr/bin/env python3
"""MQ02 — gate da minuta resolve citação só por folhas pelo mapa folha → página da rastreabilidade.

Workspace temporário (CPJ_WORKSPACE) com a transcrição fictícia do V04 (5 páginas). A minuta cita só
"(Fls. N)", como manda a regra 13; o mapa fica em 03-relatorios\\rastreabilidade-vNN.md, seção
"## Mapa de folhas" (| Fls. | Pág. do PDF | Documento |). Confere: folha mapeada com o dado na página
(confirmado), folha mapeada com o dado em outra página (OUTRA_PAGINA), folha sem mapa e mapa ausente
(CITA_SO_FLS), intervalos de folhas, mapa ilegível ou ambíguo (CITA_SO_FLS), citação por página
inalterada e minuta/mapa intactos (SHA-256). Nunca lê casos reais do workspace.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from teste_gate_v04 import LIMPA, RELATORIO_EXTRACAO, TRANSCRICAO  # noqa: E402

SCRIPT = AQUI.parents[1] / "skills" / "relatorio-ip-fraude" / "scripts" / "conferir_minuta.py"
CASO = "OS-902-2026"
DOC = "ip-ficticio"
# fls. dos autos fictícios -> página do PDF (fls. 3 a 6 = págs. 1 a 4)
FOLHAS = {3: 1, 4: 2, 5: 3, 6: 4}


def trocar(texto, antigo, novo):
    assert antigo in texto, antigo
    return texto.replace(antigo, novo)


def so_fls(texto):
    """LIMPA no formato da regra 13: só '(Fls. N)', sem pág."""
    for fl, pg in FOLHAS.items():
        texto = texto.replace(f"(pág. {pg} do PDF; fls. {fl})", f"(Fls. {fl})")
    texto = trocar(texto, "| pág. 2 |", "| Fls. 4 |")
    texto = trocar(texto, "| pág. 3 |", "| Fls. 5 |")
    texto = trocar(texto, "cálculo (págs. 2-3)", "cálculo (Fls. 4-5)")
    assert "pág" not in texto.lower(), texto
    return texto


LIMPA_FLS = so_fls(LIMPA)


def mapa(linhas, cabecalho="| Fls. | Pág. do PDF | Documento |"):
    corpo = "\n".join(f"| {fl} | {pg} | {doc} |" for fl, pg, doc in linhas)
    return ("# Rastreabilidade — minuta fictícia\n\n"
            "| trecho do relatório | fonte (pág./fls.) | natureza | conferido? |\n| --- | --- | --- | --- |\n"
            "| transferência | pág. 2; fls. 4 | fato documentado | sim |\n\n"
            "## Mapa de folhas\n\n" + cabecalho + "\n| --- | --- | --- |\n" + corpo + "\n")


MAPA_OK = mapa([(fl, pg, DOC) for fl, pg in FOLHAS.items()])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class TesteConferirFlsMQ02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-gate-mq02-")
        cls.ws = Path(cls.temp.name)
        (cls.ws / "modelos").mkdir()
        caso = cls.ws / "casos" / CASO
        for sub in ("00-originais", "02-analise", "03-relatorios"):
            (caso / sub).mkdir(parents=True)
        doc = caso / "01-extracao" / DOC
        doc.mkdir(parents=True)
        (doc / "transcricao.md").write_text(TRANSCRICAO, encoding="utf-8")
        (doc / "relatorio_extracao.json").write_text(json.dumps(RELATORIO_EXTRACAO), encoding="utf-8")
        cls.rel = caso / "03-relatorios"
        cls.extracao = caso / "01-extracao"
        cls.env = {**os.environ, "PYTHONUTF8": "1", "CPJ_WORKSPACE": str(cls.ws)}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def rodar(self, versao, minuta_txt, mapa_txt=None, modo="entrega"):
        """Grava minuta-vNN (e rastreabilidade-vNN, se houver), roda o gate como a Central e confere que
        nem a minuta nem o mapa foram alterados. Devolve (código de saída, json da conferência)."""
        minuta = self.rel / f"minuta-v{versao}.md"
        minuta.write_text(minuta_txt, encoding="utf-8")
        rastro = self.rel / f"rastreabilidade-v{versao}.md"
        if mapa_txt is not None:
            rastro.write_text(mapa_txt, encoding="utf-8")
        elif rastro.exists():
            rastro.unlink()
        antes = sha(minuta)
        antes_mapa = sha(rastro) if rastro.exists() else None
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), CASO, "--minuta", str(minuta), "--extracao",
                            str(self.extracao), "--modo", modo], capture_output=True, text=True, encoding="utf-8",
                           env=self.env, cwd=str(self.ws), timeout=60)
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
        self.assertEqual(antes, sha(minuta), "a minuta foi alterada pelo gate")
        if antes_mapa:
            self.assertEqual(antes_mapa, sha(rastro), "a rastreabilidade foi alterada pelo gate")
        res = json.loads((self.rel / f"conferencia-v{versao}.json").read_text(encoding="utf-8"))
        self.assertEqual(res["schema"], "cpj-conferencia/1")
        self.assertEqual(res["sha256_minuta"], antes)
        chaves = {"nivel", "codigo", "linha", "secao", "tipo", "dado", "citado", "paginas_citadas", "localizado_em",
                  "detalhe", "trecho"}
        for a in res["achados"] + res["conferidos"]:
            self.assertEqual(set(a), chaves)
        return r.returncode, res

    @staticmethod
    def codigos(res, nivel=None):
        return {a["codigo"] for a in res["achados"] if nivel is None or a["nivel"] == nivel}

    @staticmethod
    def dump(res):
        return json.dumps(res["achados"], ensure_ascii=False, indent=1)

    def test_folha_mapeada_com_dado_na_pagina_confirma(self):
        cod, res = self.rodar("11", LIMPA_FLS, MAPA_OK)
        self.assertEqual(cod, 0, self.dump(res))
        self.assertTrue(res["aprovado"])
        self.assertNotIn("CITA_SO_FLS", self.codigos(res), self.dump(res))
        tipos = {c["tipo"] for c in res["conferidos"]}
        self.assertTrue({"cpf", "telefone", "chave_pix", "id_transacao", "agencia", "conta", "valor"} <= tipos, tipos)
        id_pix = [c for c in res["conferidos"] if c["tipo"] == "id_transacao"]
        self.assertEqual(id_pix[0]["paginas_citadas"], [2])
        self.assertEqual(id_pix[0]["localizado_em"], [f"{DOC} p. 2"])
        self.assertIn("fls. 4", id_pix[0]["citado"])
        # mesma verificação da citação por página: total = cálculo; pág. 3 (fls. 5) a conferir na imagem
        self.assertIn("CALCULO", self.codigos(res, "REVISAR"))
        self.assertIn("PAGINA_CONFERIR", self.codigos(res, "REVISAR"))
        self.assertEqual(res["mapa_fls"]["estado"], "ok")
        self.assertEqual(res["mapa_fls"]["folhas_mapeadas"], 4)

    def test_folha_mapeada_com_dado_em_outra_pagina_bloqueia(self):
        minuta = trocar(LIMPA_FLS, "7f3c2a10-1b2c-4d5e-8f90-a1b2c3d4e5f6 (Fls. 5)",
                        "7f3c2a10-1b2c-4d5e-8f90-a1b2c3d4e5f6 (Fls. 6)")
        cod, res = self.rodar("12", minuta, MAPA_OK)
        self.assertEqual(cod, 1, self.dump(res))
        outra = [a for a in res["achados"] if a["codigo"] == "OUTRA_PAGINA"]
        self.assertTrue(outra, self.dump(res))
        self.assertTrue(all(a["nivel"] == "BLOQUEIA" for a in outra))
        self.assertIn(f"{DOC} p. 3", outra[0]["localizado_em"])
        self.assertNotIn("CITA_SO_FLS", self.codigos(res))

    def test_dado_inexistente_com_folha_mapeada_nao_localizado(self):
        minuta = trocar(LIMPA_FLS, "R$ 1.500,00 para a chave", "R$ 1.550,00 para a chave")
        cod, res = self.rodar("13", minuta, MAPA_OK)
        self.assertEqual(cod, 1)
        self.assertIn("NAO_LOCALIZADO", self.codigos(res, "BLOQUEIA"))

    def test_folha_sem_mapa_continua_cita_so_fls(self):
        sem_5 = mapa([(fl, pg, DOC) for fl, pg in FOLHAS.items() if fl != 5])
        cod, res = self.rodar("14", LIMPA_FLS, sem_5)
        self.assertEqual(cod, 0, self.dump(res))
        cita = [a for a in res["achados"] if a["codigo"] == "CITA_SO_FLS"]
        self.assertTrue(cita, self.dump(res))
        self.assertTrue(all(a["nivel"] == "REVISAR" for a in cita))
        self.assertTrue(any("fls. 5" in a["detalhe"] for a in cita), self.dump(res))
        self.assertNotIn("OUTRA_PAGINA", self.codigos(res))
        # as folhas mapeadas continuam confirmadas
        self.assertTrue(any(c["tipo"] == "id_transacao" for c in res["conferidos"]))

    def test_mapa_ausente_mantem_comportamento_atual(self):
        cod, res = self.rodar("15", LIMPA_FLS, None)
        self.assertEqual(cod, 0, self.dump(res))
        self.assertEqual(res["resumo"]["confirmados"], 0)
        cita = [a for a in res["achados"] if a["codigo"] == "CITA_SO_FLS"]
        self.assertTrue(cita)
        self.assertTrue(all(a["nivel"] == "REVISAR" for a in cita))
        self.assertIn("rastreabilidade-v15.md", cita[0]["detalhe"])
        self.assertNotIn("OUTRA_PAGINA", self.codigos(res))
        self.assertEqual(res["mapa_fls"]["estado"], "ausente")

    def test_intervalos_de_folhas(self):
        base = LIMPA_FLS.split("## CONCLUSÃO")[0]
        extra = ("A segunda transferência somou R$ 2.300,50 (Fls. 4-5).\n"
                 "O mesmo valor de R$ 2.300,50 consta do comprovante (Fls. 4/5).\n"
                 "Reitero que o valor de R$ 2.300,50 consta das fls. 4 e 5.\n"
                 "Também o valor de R$ 1.500,00 consta das Fls. 30-31 e da Fls. 4 a 5.\n\n")
        minuta = base + extra + "## CONCLUSÃO" + LIMPA_FLS.split("## CONCLUSÃO")[1]
        cod, res = self.rodar("16", minuta, MAPA_OK)
        linhas = {i for i, ln in enumerate(minuta.split("\n"), 1) if "R$ 2.300,50 (Fls. 4" in ln
                  or "R$ 2.300,50 consta" in ln}
        self.assertEqual(len(linhas), 3, linhas)
        confirmadas = {c["linha"] for c in res["conferidos"] if c["dado"] == "R$ 2.300,50"}
        self.assertTrue(linhas <= confirmadas, (linhas, confirmadas, self.dump(res)))
        # fls. 30-31 fora do mapa: a citação inteira continua CITA_SO_FLS, sem aprovar nem bloquear
        fora = [a for a in res["achados"] if a["dado"] == "R$ 1.500,00" and a["codigo"] == "CITA_SO_FLS"]
        self.assertTrue(fora, self.dump(res))
        self.assertEqual(cod, 0, self.dump(res))

    def test_mapa_ilegivel_ou_ambiguo_volta_a_cita_so_fls(self):
        ilegivel = mapa([(3, 1, DOC), (4, "dois", DOC), (5, 3, DOC), (6, 4, DOC)])
        sem_colunas = mapa([(fl, pg, DOC) for fl, pg in FOLHAS.items()], cabecalho="| A | B | C |")
        for versao, texto, estado in (("17", ilegivel, "ilegivel"), ("18", sem_colunas, "ilegivel")):
            with self.subTest(versao=versao):
                cod, res = self.rodar(versao, LIMPA_FLS, texto)
                self.assertEqual(cod, 0, self.dump(res))
                self.assertEqual(res["resumo"]["confirmados"], 0)
                self.assertIn("CITA_SO_FLS", self.codigos(res, "REVISAR"))
                self.assertNotIn("OUTRA_PAGINA", self.codigos(res))
                self.assertEqual(res["mapa_fls"]["estado"], estado)
        # fls. 5 apontada para duas páginas diferentes: ambígua, não confirma nem bloqueia
        ambiguo = mapa([(3, 1, DOC), (4, 2, DOC), (5, 3, DOC), (5, 4, DOC), (6, 4, DOC)])
        # documento inexistente e página inexistente: a folha fica sem mapa
        doc_errado = mapa([(3, 1, DOC), (4, 2, DOC), (5, 3, "outro-doc"), (6, 4, DOC)])
        pag_errada = mapa([(3, 1, DOC), (4, 2, DOC), (5, 9, DOC), (6, 4, DOC)])
        for versao, texto in (("19", ambiguo), ("20", doc_errado), ("21", pag_errada)):
            with self.subTest(versao=versao):
                cod, res = self.rodar(versao, LIMPA_FLS, texto)
                self.assertEqual(cod, 0, self.dump(res))
                cita = [a for a in res["achados"] if a["codigo"] == "CITA_SO_FLS"]
                self.assertTrue(cita and all("fls. 5" in a["detalhe"] for a in cita), self.dump(res))
                self.assertNotIn("OUTRA_PAGINA", self.codigos(res))
                self.assertTrue(any(c["tipo"] == "id_transacao" for c in res["conferidos"]))

    def test_citacao_por_pagina_inalterada(self):
        """LIMPA (pág. + fls.) dá o mesmo resultado com mapa errado, mapa certo ou sem mapa."""
        mapa_errado = mapa([(3, 4, DOC), (4, 4, DOC), (5, 4, DOC), (6, 1, DOC)])
        resultados = []
        for versao, texto in (("22", None), ("23", MAPA_OK), ("24", mapa_errado)):
            cod, res = self.rodar(versao, LIMPA, texto)
            self.assertEqual(cod, 0, self.dump(res))
            resultados.append(([(a["codigo"], a["linha"], a["dado"], a["citado"], a["paginas_citadas"],
                                 a["localizado_em"]) for a in res["achados"]],
                               [(c["linha"], c["dado"], c["citado"], c["paginas_citadas"], c["localizado_em"])
                                for c in res["conferidos"]]))
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(resultados[0], resultados[2])

    def test_mapa_em_link_nao_e_usado(self):
        alvo = self.ws / "mapa-externo.md"
        alvo.write_text(MAPA_OK, encoding="utf-8")
        rastro = self.rel / "rastreabilidade-v25.md"
        try:
            rastro.symlink_to(alvo)
        except OSError as exc:
            if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows sem privilégio para symlink de arquivo")
            raise
        minuta = self.rel / "minuta-v25.md"
        minuta.write_text(LIMPA_FLS, encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), CASO, "--minuta", str(minuta), "--extracao",
                            str(self.extracao), "--modo", "entrega"], capture_output=True, text=True,
                           encoding="utf-8", env=self.env, cwd=str(self.ws), timeout=60)
        res = json.loads((self.rel / "conferencia-v25.json").read_text(encoding="utf-8"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(res["resumo"]["confirmados"], 0)
        self.assertEqual(res["mapa_fls"]["estado"], "ilegivel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
