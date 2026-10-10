"""PX06: modos, aviso antes de enfileirar e seleção servidor; somente fixtures."""
import io
import json
import re
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import teste_consentimento_seguro_se01 as fixture
import rotas.comum as comum
import rotas.casos as casos
import executores_llm as EL

class Modos(unittest.TestCase):
    def setUp(self):
        fixture.Consentimento.setUp(self)
        from PIL import Image
        b = io.BytesIO(); Image.new("RGB", (300, 400), "white").save(b, format="PDF", save_all=True, append_images=[Image.new("RGB", (300, 400), "white")])
        self.pdf = b.getvalue()
        self.caminho = Path(self.ws) / "casos" / self.caso
        (self.caminho / "00-originais").mkdir()
        p = patch.object(casos, "WS", self.ws); p.start(); self.addCleanup(p.stop)

    def upload(self, modo="inteligente", consentimento=None):
        d = {"caso_id": self.caso, "modo_processamento": modo, "arquivos": (io.BytesIO(self.pdf), "ficticio.pdf")}
        if consentimento is not None: d["consentimento_externo"] = json.dumps(consentimento)
        return self.cli.post("/api/os", data=d, headers={"X-CPJ": "1"})

    def test_rapido_sem_gate_sem_consentimento(self):
        with patch.object(casos, "enfileirar") as fila:
            r = self.upload("rapido")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("requer_consentimento", r.json)
        self.assertEqual(fila.call_args.kwargs["modo"], "rapido")
        self.assertIsNone(fila.call_args.kwargs["consentimento"])

    def test_inteligente_padrao_e_completa_gate_contagem_antes_original(self):
        for modo in ("inteligente", "ia_completa"):
            with self.subTest(modo=modo), patch.object(casos, "enfileirar") as fila:
                r = self.upload(modo)
                self.assertTrue(r.json["requer_consentimento"])
                self.assertEqual(r.json["paginas"], 2)
                self.assertEqual(r.json["modo"], modo)
                self.assertEqual(r.json["escopo"], "transcricao_visual")
                fila.assert_not_called()
                self.assertEqual(list((self.caminho / "00-originais").iterdir()), [])
                r = self.upload(modo, {"recusado": True})
                self.assertTrue(r.json["recusado"])
                fila.assert_not_called()
        with patch.object(casos, "enfileirar") as fila:
            r = self.upload("ia_completa", {"aceito": True, "escopo": "transcricao_visual", "destinos": ["openai"], "usuario": "FORJADO"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(fila.call_args.kwargs["consentimento"]["usuario"], "operador")
            self.assertEqual(fila.call_args.kwargs["modo"], "ia_completa")

    def test_sem_api_inteligente_local_completa_erro(self):
        (Path(self.ws) / "config/chaves_llm.json").write_text("{}")
        with patch.object(casos, "enfileirar") as fila:
            r = self.upload("ia_completa")
            self.assertEqual(r.status_code, 400); fila.assert_not_called()
            r = self.upload("inteligente")
            self.assertEqual(r.status_code, 200)
            self.assertIn("local", r.json["limitacao"].casefold())
            self.assertIsNone(fila.call_args.kwargs["consentimento"])

    def test_modo_invalido_e_aceite_parcial_nao_grava(self):
        with patch.object(casos, "enfileirar") as fila:
            self.assertEqual(self.upload("turbo").status_code, 400)
            self.assertEqual(self.upload("ia_completa", {"destinos": ["openai"]}).status_code, 400)
            fila.assert_not_called()
            self.assertEqual(list((self.caminho / "00-originais").iterdir()), [])

    def test_fila_registra_modo_identidade_e_retomada(self):
        cons = EL.criar_consentimento("operador", ["openai"], escopo="transcricao_visual")
        with patch.object(comum, "fila") as q:
            comum.enfileirar(self.caso, "ficticio", "ficticio.pdf", modo="ia_completa", usuario="operador", consentimento=cons)
        t = comum.ler_proc(self.caso)["trabalhos"][0]
        self.assertEqual(t["modo"], "ia_completa"); self.assertEqual(t["consentimento"], cons)
        self.assertEqual(q.put.call_args.args[0]["modo"], "ia_completa")
        self.assertIn("ia_completa", (self.caminho / "registro-tratamento.md").read_text(encoding="utf-8"))

    def test_plano_servidor_completa_todas_inteligente_uniao(self):
        p = self.caminho / "01-extracao/ficticio"; p.mkdir(parents=True)
        (p / "relatorio_extracao.json").write_text(json.dumps({"arquivo": "ficticio.pdf", "paginas": 3, "pendentes_transcricao_visual": [2]}))
        (p / "qualidade.json").write_text("{}")
        self.assertEqual(comum.plano_transcricao_visual(self.caso)[0]["paginas"], [2])
        self.assertEqual(comum.plano_transcricao_visual(self.caso, todas=True, documentos=["ficticio"])[0]["paginas"], [1, 2, 3])

    def test_reprocessar_mesmo_aviso_preserva_original(self):
        orig = self.caminho / "00-originais/ficticio.pdf"; orig.write_bytes(self.pdf)
        comum.gravar_proc(self.caso, {"trabalhos": [{"doc": "ficticio", "arquivo": "ficticio.pdf", "modo": "rapido", "status": "concluido"}]})
        with patch.object(casos, "enfileirar") as fila:
            r = self.cli.post(f"/api/casos/{self.caso}/reprocessar/ficticio", json={"modo": "ia_completa"}, headers={"X-CPJ": "1"})
            self.assertTrue(r.json["requer_consentimento"]); self.assertEqual(r.json["paginas"], 2)
            fila.assert_not_called()
        self.assertEqual(orig.read_bytes(), self.pdf)

    def test_worker_real_tres_modos_png_0_1_2_e_metadados(self):
        import hashlib
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from PIL import Image
        (self.caminho / "caso.json").write_text(json.dumps({"id": self.caso, "status": "recebido", "datas": {}, "documentos": []}))
        resposta = {"usage": {"input_tokens": 8, "output_tokens": 4}, "output": [{"type": "message", "content": [{"type": "output_text", "text": "Transcrição fictícia 123? [dígito incerto]"}]}]}
        for modo, chamadas in (("rapido", 0), ("inteligente", 1), ("ia_completa", 2)):
            with self.subTest(modo=modo):
                pdf = self.caminho / "00-originais" / (modo + ".pdf")
                c = canvas.Canvas(str(pdf), pagesize=(400, 600))
                for i in range(30): c.drawString(10, 590-i*17, "Texto ficticio nativo numero %s sem dados pessoais e integral." % i)
                c.showPage(); c.drawImage(ImageReader(Image.new("RGB", (300, 400), "white")), 0, 0, 400, 600); c.save()
                antes = hashlib.sha256(pdf.read_bytes()).hexdigest()
                cons = EL.criar_consentimento("operador", ["openai"], escopo="transcricao_visual") if chamadas else None
                with patch.object(comum, "fila") as q:
                    comum.enfileirar(self.caso, modo, pdf.name, modo=modo, usuario="operador", consentimento=cons)
                trab = q.put.call_args.args[0]
                with patch.object(comum.D_OS, "aplicar"), patch.object(EL, "_http_json", return_value=resposta) as http:
                    comum.processar(trab)
                t = next(x for x in comum.ler_proc(self.caso)["trabalhos"] if x["doc"] == modo)
                self.assertEqual(t["status"], "concluido", t.get("erro"))
                self.assertEqual(http.call_count, chamadas)
                p = self.caminho / "01-extracao" / modo
                self.assertEqual(len(list((p / "transcricoes_visuais").glob("p*.md"))), chamadas)
                self.assertEqual(hashlib.sha256(pdf.read_bytes()).hexdigest(), antes)
                if chamadas:
                    doc = next(d for d in comum.C.carregar(self.caso)["documentos"] if d["pasta"] == modo)
                    self.assertEqual(doc["pendentes"], 0)
                    self.assertIn("transcricao-visual-llm", str(doc["metodos"]))

    def test_interface_processar_com_aceite_recusa_contagem(self):
        from teste_consentimento_interface_se01 import Interface
        html = (Path(__file__).resolve().parents[1] / "static/index.html").read_text(encoding="utf-8")
        m = re.search(r"async function processarPDFComAviso\(enviarPedido\)\{[\s\S]*?\n\}", html)
        self.assertIsNotNone(m)
        for aceitar in (True, False):
            i = Interface(); i.setUp(); i.ctx.eval(m.group(0))
            i.ctx.eval("async function enviarPDF(c){chamadas.push(c);return c?(c.recusado?{recusado:true}:{caso:'ficticio',recebidos:['pdf']}):{requer_consentimento:true,destinos:['openai'],escopo:'transcricao_visual',paginas:2,aviso:'Todas as páginas'}};processarPDFComAviso(enviarPDF).then(r=>resultado=r)")
            i.jobs(); self.assertEqual(len(i.valor("chamadas")), 1)
            self.assertIn("2", i.valor("els['#cons-destinos'].textContent"))
            self.assertIn("Todas", i.valor("els['#cons-destinos'].textContent"))
            i.ctx.eval("els['#b-cons-%s'].onclick()" % ("aceitar" if aceitar else "recusar")); i.jobs()
            self.assertEqual(len(i.valor("chamadas")), 2)
            if aceitar:
                self.assertTrue(i.valor("chamadas[1].aceito")); self.assertEqual(i.valor("chamadas[1].escopo"), "transcricao_visual")
            else: self.assertTrue(i.valor("resultado.recusado"))

    def test_aviso_contraste_texto_temas_escuro_e_claro(self):
        html = (Path(__file__).resolve().parents[1] / "static/index.html").read_text(encoding="utf-8")
        estilo = re.search(r'<div style="([^"]+)">Aviso legal:', html)[1]
        def luminancia(cor):
            rgb = [int(cor[i:i+2], 16) / 255 for i in (1, 3, 5)]
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
            return sum(v * p for v, p in zip(linear, (.2126, .7152, .0722)))
        for tema in ("dark", "light"):
            with self.subTest(tema=tema):
                bloco = re.search(r':root\[data-theme="' + tema + r'"\]\{([^}]+)', html)[1]
                variaveis = dict(re.findall(r'(--[\w-]+):([^;]+)', bloco))
                def resolver(valor):
                    v = re.fullmatch(r'var\((--[\w-]+)(?:,([^)]*))?\)', valor)
                    if v: valor = variaveis.get(v[1], v[2])
                    self.assertIsNotNone(valor, "Variável CSS ausente sem fallback")
                    if re.fullmatch(r'#[0-9a-fA-F]{3}', valor): valor = '#' + ''.join(x * 2 for x in valor[1:])
                    self.assertRegex(valor, r'^#[0-9a-fA-F]{6}$')
                    return valor
                bg = resolver(re.search(r'(?:^|;)background:([^;]+)', estilo)[1])
                texto = re.search(r'(?:^|;)color:([^;]+)', estilo)
                fg = resolver(texto[1] if texto else 'var(--ink)')
                a, b = sorted((luminancia(fg), luminancia(bg)))
                self.assertGreaterEqual((b + .05) / (a + .05), 4.5, "Aviso precisa de contraste legível para texto normal")

if __name__ == "__main__": unittest.main(verbosity=2)
