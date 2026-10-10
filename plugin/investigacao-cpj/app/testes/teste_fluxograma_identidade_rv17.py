#!/usr/bin/env python3
"""RV17 — identidade dos nós do fluxograma e camada calculada x documentada (dados fictícios, sem rede)."""
import importlib.util
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "plugin" / "investigacao-cpj" / "skills" / "relatorio-ip-fraude" / "scripts" / "gerar_diagrama_financeiro.py"


def modulo():
    spec = importlib.util.spec_from_file_location("diagrama_rv17", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def tx(o, oc, d, dc, valor="100", camada=""):
    return {"origem_titular": o, "origem_ag_conta": oc, "destino_titular": d, "destino_ag_conta": dc,
            "valor": valor, "camada": camada, "_valor": Decimal(valor)}


def tipos(g):
    return sorted(n["tipo"] for n in g["nos"].values())


def bancos(t, origem="BANCO ORIGEM FICTICIO", destino="BANCO B FICTICIO"):
    return dict(t, origem_banco=origem, destino_banco=destino)


class TesteIdentidadeDosNos(unittest.TestCase):
    def setUp(self):
        self.m = modulo()

    def test_homonimos_com_contas_distintas_nao_se_fundem(self):
        g = self.m.montar_grafo([tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "0001/111-1", "100", "1"),
                                 tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "0001/222-2", "50", "1")])
        joaos = [n for n in g["nos"].values() if n["nome"] == "JOAO DA SILVA"]
        self.assertEqual(len(joaos), 2)
        self.assertEqual(sorted(n["entra"] for n in joaos), [Decimal(50), Decimal(100)])

    def test_mesma_conta_com_formatacao_diferente_e_um_no_so(self):
        g = self.m.montar_grafo([tx("VITIMA FICTICIA", "1/1", "João da Silva", "0001/111-1", "100", "1"),
                                 tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "0001 111 1", "40", "1")])
        joaos = [n for n in g["nos"].values() if n["nome"].upper().endswith("SILVA")]
        self.assertEqual(len(joaos), 1)
        self.assertEqual(joaos[0]["entra"], Decimal(140))

    def test_linha_sem_conta_liga_ao_unico_nome_conhecido(self):
        g = self.m.montar_grafo([tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "0001/111-1", "100", "1"),
                                 tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "", "10", "1")])
        self.assertEqual(len([n for n in g["nos"].values() if n["nome"] == "JOAO DA SILVA"]), 1)

    def test_linha_sem_conta_com_duas_contas_conhecidas_fica_separada(self):
        g = self.m.montar_grafo([tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "0001/111-1", "100", "1"),
                                 tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "0001/222-2", "50", "1"),
                                 tx("VITIMA FICTICIA", "1/1", "JOAO DA SILVA", "", "10", "1")])
        joaos = [n for n in g["nos"].values() if n["nome"] == "JOAO DA SILVA"]
        self.assertEqual(len(joaos), 3)  # nenhuma conta é escolhida por dedução
        self.assertIn(Decimal(10), [n["entra"] for n in joaos])

    def test_mesmo_titular_agencia_conta_em_bancos_distintos_nao_se_fundem(self):
        g = self.m.montar_grafo([
            bancos(tx("VITIMA FICTICIA", "1/1", "TITULAR FICTICIO", "2/2", "100", "1")),
            bancos(tx("VITIMA FICTICIA", "1/1", "TITULAR FICTICIO", "2/2", "50", "1"), destino="BANCO C FICTICIO")])
        nos = [n for n in g["nos"].values() if n["nome"] == "TITULAR FICTICIO"]
        self.assertEqual(len(nos), 2)
        self.assertEqual(sorted(n["entra"] for n in nos), [Decimal(50), Decimal(100)])
        self.assertEqual({n["banco"] for n in nos}, {"BANCO B FICTICIO", "BANCO C FICTICIO"})

    def test_banco_normalizado_com_mesma_conta_e_um_no(self):
        g = self.m.montar_grafo([
            bancos(tx("VITIMA", "1/1", "TITULAR", "0001/22-2", "100", "1"), destino="Banco Fictício"),
            bancos(tx("VITIMA", "1/1", "TITULAR", "0001 22 2", "40", "1"), destino="BANCO FICTICIO")])
        nos = [n for n in g["nos"].values() if n["nome"] == "TITULAR"]
        self.assertEqual(len(nos), 1)
        self.assertEqual(nos[0]["entra"], Decimal(140))

    def test_banco_ausente_entre_duas_possibilidades_fica_separado(self):
        for conta in ("2/2", ""):
            with self.subTest(conta_informada=bool(conta)):
                g = self.m.montar_grafo([
                    bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "100", "1")),
                    bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "50", "1"), destino="BANCO C FICTICIO"),
                    bancos(tx("VITIMA", "1/1", "TITULAR", conta, "10", "1"), destino="")])
                nos = [n for n in g["nos"].values() if n["nome"] == "TITULAR"]
                self.assertEqual(len(nos), 3)
                desconhecido = next(n for n in nos if not n["banco"])
                self.assertEqual(desconhecido["entra"], Decimal(10))

    def test_banco_ausente_compativel_com_unica_conta_conhecida(self):
        g = self.m.montar_grafo([
            bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "100", "1")),
            bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "10", "1"), destino="")])
        nos = [n for n in g["nos"].values() if n["nome"] == "TITULAR"]
        self.assertEqual(len(nos), 1)
        self.assertEqual(nos[0]["entra"], Decimal(110))

    def test_conta_ausente_nao_escolhe_entre_duas_do_mesmo_banco(self):
        g = self.m.montar_grafo([
            bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "100", "1")),
            bancos(tx("VITIMA", "1/1", "TITULAR", "3/3", "50", "1")),
            bancos(tx("VITIMA", "1/1", "TITULAR", "", "10", "1"))])
        nos = [n for n in g["nos"].values() if n["nome"] == "TITULAR"]
        self.assertEqual(len(nos), 3)
        self.assertEqual(next(n for n in nos if not n["conta"])["entra"], Decimal(10))

    def test_conta_ausente_liga_so_a_unica_compativel_do_banco_informado(self):
        g = self.m.montar_grafo([
            bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "100", "1")),
            bancos(tx("VITIMA", "1/1", "TITULAR", "2/2", "50", "1"), destino="BANCO C FICTICIO"),
            bancos(tx("VITIMA", "1/1", "TITULAR", "", "10", "1"))])
        nos = [n for n in g["nos"].values() if n["nome"] == "TITULAR"]
        self.assertEqual(len(nos), 2)
        self.assertEqual({n["banco"]: n["entra"] for n in nos},
                         {"BANCO B FICTICIO": Decimal(110), "BANCO C FICTICIO": Decimal(50)})


class TesteCamadaCalculada(unittest.TestCase):
    def setUp(self):
        self.m = modulo()

    def test_camada_do_csv_e_documentada_e_origem_e_vitima(self):
        g = self.m.montar_grafo([tx("VITIMA FICTICIA", "1/1", "RECEBEDOR", "2/2", "100", "1")])
        self.assertFalse(g["calculada"])
        self.assertEqual(g["cams"], [1])
        self.assertIn("vitima", tipos(g))

    def test_sem_camada_no_csv_marca_calculada_e_nao_afirma_vitima(self):
        g = self.m.montar_grafo([tx("ORIGEM X", "1/1", "RECEBEDOR", "2/2", "100"),
                                 tx("RECEBEDOR", "2/2", "DESTINO Y", "3/3", "90")])
        self.assertTrue(g["calculada"])
        self.assertEqual(g["cams"], [1, 2])
        self.assertNotIn("vitima", tipos(g))
        self.assertIn("origem", tipos(g))

    def test_camada_parcial_tambem_e_calculada(self):
        g = self.m.montar_grafo([tx("ORIGEM X", "1/1", "RECEBEDOR", "2/2", "100", "1"),
                                 tx("RECEBEDOR", "2/2", "DESTINO Y", "3/3", "90", "")])
        self.assertTrue(g["calculada"])
        self.assertNotIn("vitima", tipos(g))

    def test_encadeamento_calculado_nao_liga_homonimos_de_contas_distintas(self):
        # JOAO (conta 111) recebe de A; quem repassa a B é outro JOAO (conta 222): não há elo documentado
        cams, calculada = self.m._camadas([tx("A", "1/1", "JOAO DA SILVA", "0001/111-1", "100"),
                                           tx("JOAO DA SILVA", "0001/222-2", "B", "9/9", "30")])
        self.assertTrue(calculada)
        self.assertEqual(cams, [1, 1])

    def test_encadeamento_calculado_liga_mesma_conta(self):
        cams, _ = self.m._camadas([tx("A", "1/1", "JOAO DA SILVA", "0001/111-1", "100"),
                                   tx("JOAO DA SILVA", "0001/111-1", "B", "9/9", "30")])
        self.assertEqual(cams, [1, 2])

    def test_calculo_nao_encadeia_conta_igual_em_banco_diferente(self):
        g = self.m.montar_grafo([
            bancos(tx("ORIGEM FICTICIA", "1/1", "TITULAR FICTICIO", "2/2", "100")),
            bancos(tx("TITULAR FICTICIO", "2/2", "DESTINO FICTICIO", "3/3", "90"), origem="BANCO C FICTICIO")])
        self.assertTrue(g["calculada"])
        self.assertEqual(g["cams"], [1, 1])
        self.assertNotIn("vitima", tipos(g))

    def test_calculo_encadeia_banco_conta_iguais(self):
        cams, calculada = self.m._camadas([
            bancos(tx("ORIGEM", "1/1", "TITULAR", "2/2", "100")),
            bancos(tx("TITULAR", "2/2", "DESTINO", "3/3", "90"), origem="BANCO B FICTICIO")])
        self.assertTrue(calculada)
        self.assertEqual(cams, [1, 2])

    def test_calculo_banco_ausente_ambiguo_nao_inventa_encadeamento(self):
        cams, calculada = self.m._camadas([
            bancos(tx("ORIGEM", "1/1", "TITULAR", "2/2", "100")),
            bancos(tx("ORIGEM", "1/1", "TITULAR", "2/2", "50"), destino="BANCO C FICTICIO"),
            bancos(tx("TITULAR", "2/2", "DESTINO", "3/3", "10"), origem="")])
        self.assertTrue(calculada)
        self.assertEqual(cams, [1, 1, 1])

    def test_png_e_gerado_nos_dois_modos(self):
        with tempfile.TemporaryDirectory(prefix="cpj-rv17-") as tmp:
            for nome, camada in (("doc.png", "1"), ("calc.png", "")):
                saida = Path(tmp) / nome
                self.m.desenhar_diagrama([tx("ORIGEM X", "1/1", "RECEBEDOR", "2/2", "100", camada)], saida, dpi=100)
                with Image.open(saida) as im:
                    self.assertEqual(im.format, "PNG")
                    self.assertGreater(im.height, 300)
            self.assertGreater((Path(tmp) / "calc.png").stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
