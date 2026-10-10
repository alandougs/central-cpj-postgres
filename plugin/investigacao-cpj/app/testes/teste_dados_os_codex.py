"""N01: prévia, OCR, IA local e edição manual em workspace fictício."""
import io
import gc
import json
import os
import re
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TEXTO = """## Página 3
Ordem de Serviço nº 991/2099
BO: AB1234/2099
Inquérito Policial: 123/2099
Processo: 1234567-89.2099.8.26.0000
Natureza: Fraude fictícia
Delegado de Polícia: DELEGADO FICTICIO
Escrivão do feito: ESCRIVAO FICTICIO
Prazo: 31/12/2099
Determinação: Identificar o titular da conta indicada.
"""


class DadosOS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-dados-os-")
        cls.ws = Path(cls.temp.name)
        cls.env = os.environ.get("CPJ_WORKSPACE")
        cls.env_agente = os.environ.get("CPJ_SEM_AGENTE_EMBUTIDO")
        os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
        os.environ["CPJ_WORKSPACE"] = str(cls.ws)
        modelo = cls.ws / "casos" / "_MODELO-CASO"
        for pasta in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (modelo / pasta).mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({
            "datas": {}, "ip": {}, "financeiro": {}, "resultado": {}, "relatorios": []
        }), encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import servidor
        cls.s = servidor
        cls.d = servidor.D_OS
        assert Path(servidor.WS).resolve() == cls.ws.resolve()
        servidor.app.config.update(TESTING=True)
        servidor.auth.salvar_usuario("admin_teste", "Administrador ficticio", "admin", "SenhaFicticia123")
        servidor.auth.salvar_usuario("escrivao_teste", "CADASTRADOR DIFERENTE", "escrivao", "SenhaFicticia123")
        cls.numero = 0

    @classmethod
    def tearDownClass(cls):
        for p in cls.ws.rglob("*"):
            if p.is_file(): p.chmod(0o600)
        gc.collect()
        cls.temp.cleanup()
        if cls.env is None: os.environ.pop("CPJ_WORKSPACE", None)
        else: os.environ["CPJ_WORKSPACE"] = cls.env
        if cls.env_agente is None: os.environ.pop("CPJ_SEM_AGENTE_EMBUTIDO", None)
        else: os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = cls.env_agente

    def setUp(self):
        type(self).numero += 1
        self.id = self.s.C.novo(f"{self.numero}/2099", natureza="")["id"]
        self.client = self.entrar("admin_teste")

    def entrar(self, login):
        client = self.s.app.test_client()
        self.assertEqual(client.post("/api/entrar", json={"login": login, "senha": "SenhaFicticia123"},
                                     headers={"X-CPJ": "1"}).status_code, 200)
        return client

    def test_script_extrai_campos_e_fontes_sem_confundir_escrivao(self):
        encontrados, conflitos = self.d.extrair(TEXTO, "ip-ficticio.md")
        self.assertFalse(conflitos)
        self.assertEqual(set(encontrados), set(self.d.CAMPOS))
        self.assertEqual(encontrados["escrivao"]["valor"], "ESCRIVAO FICTICIO")
        self.assertEqual(encontrados["escrivao"]["pagina"], 3)
        self.assertEqual(encontrados["prazo"]["valor"], "2099-12-31")

    def test_duvida_divergencia_e_prazo_relativo_ficam_pendentes(self):
        texto = "## Página 1\nBO: AB12?/2099\nPrazo: 30 dias\nEscrivã de Polícia: NOME A\n## Página 2\nEscrivã de Polícia: NOME B"
        encontrados, conflitos = self.d.extrair(texto, "ficticio.md")
        self.assertNotIn("bo", encontrados)
        self.assertNotIn("prazo", encontrados)
        self.assertEqual(len(conflitos["escrivao"]), 2)

    def test_previa_pdf_textual_nao_cria_caso(self):
        from reportlab.pdfgen import canvas
        dados = io.BytesIO(); pdf = canvas.Canvas(dados)
        pdf.drawString(50, 750, "Ordem de Servico: 991/2099")
        pdf.drawString(50, 730, "Escrivao do feito: ESCRIVAO FICTICIO")
        pdf.save(); dados.seek(0)
        antes = len(self.s.C.listar())
        r = self.client.post("/api/os/detectar", data={"arquivos": (dados, "ficticio.pdf")}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["campos"]["ordem_servico"]["valor"], "991/2099")
        self.assertEqual(r.json["campos"]["escrivao"]["valor"], "ESCRIVAO FICTICIO")
        self.assertEqual(len(self.s.C.listar()), antes)

    def test_previa_multiplos_documentos_nao_escolhe_numero_divergente(self):
        r = self.client.post("/api/os/detectar", data={"arquivos": [
            (io.BytesIO(b"BO: AB123/2099"), "a.md"), (io.BytesIO(b"BO: AB999/2099"), "b.md")
        ]}, headers={"X-CPJ": "1"})
        self.assertNotIn("bo", r.json["campos"])
        self.assertEqual(len(r.json["conflitos"]["bo"]), 2)

    def test_upload_sem_os_processa_e_preenche_apos_extracao(self):
        client = self.entrar("escrivao_teste")
        with patch.dict(os.environ, {"CPJ_IA_LOCAL_MODELO": ""}):
            r = client.post("/api/os", data={"arquivos": (io.BytesIO(TEXTO.encode()), "ficticio.md")}, headers={"X-CPJ": "1"})
            self.assertEqual(r.status_code, 200)
            id_ = r.json["caso"]
            self.assertTrue(id_.startswith("RECEBIDO-"))
            trabalho = next(t for t in self.s.ler_proc(id_)["trabalhos"] if t["arquivo"] == "ficticio.md")
            trabalho["caso"] = id_
            self.s.processar(trabalho)
        c = self.s.C.carregar(id_)
        self.assertEqual(c["ordem_servico"], "991/2099")
        self.assertEqual(c["escrivao"], "ESCRIVAO FICTICIO")
        self.assertEqual(c["preenchimento_os"]["pendentes"], [])
        self.assertEqual(self.s.ler_proc(id_)["trabalhos"][0]["status"], "concluido")
        self.assertEqual(client.get(f"/api/casos/{id_}").json["caso"]["escrivao"], "ESCRIVAO FICTICIO")

    def test_texto_ocr_complementa_sem_sobrescrever_manual(self):
        self.s.C.set_campos(self.id, {"escrivao": "NOME CONFERIDO", "bo": "MANUAL/2099"})
        self.d.aplicar(self.s.C, self.id, "", "scan.pdf")
        with patch.dict(os.environ, {"CPJ_IA_LOCAL_MODELO": ""}):
            self.d.aplicar(self.s.C, self.id, TEXTO, "scan.pdf", usar_ia=True)
        c = self.s.C.carregar(self.id)
        self.assertEqual(c["escrivao"], "NOME CONFERIDO")
        self.assertEqual(c["bo"], "MANUAL/2099")
        self.assertEqual(c["inquerito"], "123/2099")

    def test_pdf_imagem_preenche_escrivao_depois_do_ocr_real(self):
        from PIL import Image, ImageDraw, ImageFont
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        imagem = Image.new("RGB", (1700, 900), "white")
        fonte = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 42)
        desenhar = ImageDraw.Draw(imagem)
        for i, linha in enumerate(("Ordem de Servico: 992/2099", "Escrivao do feito: ESCRIVAO FICTICIO", "Natureza: Estelionato ficticio")):
            desenhar.text((80, 100 + 100 * i), linha, font=fonte, fill="black")
        dados = io.BytesIO(); pdf = canvas.Canvas(dados, pagesize=(850,450))
        pdf.drawImage(ImageReader(imagem), 0, 0, width=850, height=450); pdf.save()
        with patch.dict(os.environ, {"CPJ_IA_LOCAL_MODELO": ""}):
            dados.seek(0)
            r = self.client.post("/api/os", data={"arquivos": (dados, "scan-ficticio.pdf")}, headers={"X-CPJ": "1"})
            self.assertEqual(r.status_code, 200)
            id_ = r.json["caso"]
            p = Path(self.s.C.caminho(id_)) / "00-originais" / "scan-ficticio.pdf"
            self.assertFalse(self.d.extrair(self.d.ler_original(str(p)), p.name)[0])
            t = self.s.ler_proc(id_)["trabalhos"][0] | {"caso": id_}
            self.s.processar(t)
        c = self.s.C.carregar(id_)
        self.assertEqual(self.s.ler_proc(id_)["trabalhos"][0]["status"], "concluido")
        self.assertEqual(c["escrivao"], "ESCRIVAO FICTICIO")
        self.assertEqual(c["ordem_servico"], "992/2099")
        self.assertEqual(c["preenchimento_os"]["fontes"]["escrivao"]["pagina"], 1)

    def test_ia_complementa_lacuna_e_preserva_edicao_durante_execucao(self):
        texto = "## Página 1\nO escrivão do feito é NOME FICTICIO."
        item = {"valor": "NOME FICTICIO", "documento": "ficticio.md", "pagina": 1,
                "trecho": "O escrivão do feito é NOME FICTICIO.", "metodo": "ia_local"}
        with patch.object(self.d, "completar_ia", return_value=({"escrivao": item}, "concluida")):
            self.d.aplicar(self.s.C, self.id, texto, "ficticio.md", usar_ia=True)
        self.assertEqual(self.s.C.carregar(self.id)["escrivao"], "NOME FICTICIO")
        self.s.C.set_campos(self.id, {"escrivao": ""})

        def modelo(*args):
            self.s.C.set_campos(self.id, {"escrivao": "CONFERIDO DURANTE IA"})
            return {"escrivao": item}, "concluida"

        with patch.object(self.d, "completar_ia", side_effect=modelo):
            self.d.aplicar(self.s.C, self.id, texto, "ficticio.md", usar_ia=True)
        self.assertEqual(self.s.C.carregar(self.id)["escrivao"], "CONFERIDO DURANTE IA")

    def test_divergencia_entre_documentos_automaticos_exige_conferencia(self):
        self.d.aplicar(self.s.C, self.id, "Escrivão: NOME A", "a.md")
        self.d.aplicar(self.s.C, self.id, "Escrivão: NOME B", "b.md")
        c = self.s.C.carregar(self.id)
        self.assertEqual(c["escrivao"], "")
        self.assertIn("escrivao", c["preenchimento_os"]["conflitos"])
        r = self.client.post(f"/api/casos/{self.id}", json={"escrivao": "NOME CONFERIDO"}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        self.d.aplicar(self.s.C, self.id, "Escrivão: NOME A", "a.md")
        self.assertEqual(self.s.C.carregar(self.id)["escrivao"], "NOME CONFERIDO")

    def test_ia_local_valida_trecho_pagina_e_descarta_inventado(self):
        retorno = {"response": json.dumps({
            "escrivao": {"valor": "ESCRIVAO FICTICIO", "pagina": 3, "trecho": "Escrivão do feito: ESCRIVAO FICTICIO"},
            "bo": {"valor": "INVENTADO/2099", "pagina": 3, "trecho": "BO: INVENTADO/2099"},
            "requisitante": {"valor": "DELEGADO FICTICIO", "pagina": 99, "trecho": "Delegado de Polícia: DELEGADO FICTICIO"}
        })}
        class Resposta(io.BytesIO): pass
        opener = unittest.mock.Mock()
        opener.open.side_effect = [
            Resposta(json.dumps({"models": [{"name": "modelo-ficticio:latest", "size": 1234}]}).encode()),
            Resposta(json.dumps(retorno).encode())
        ]
        with patch.dict(os.environ, {"CPJ_IA_LOCAL_MODELO": "modelo-ficticio"}):
            with patch.object(self.d.urllib.request, "build_opener", return_value=opener):
                valores, estado = self.d.completar_ia(TEXTO, "scan.pdf", ["escrivao", "bo", "requisitante"])
        self.assertEqual(estado, "concluida")
        self.assertEqual(set(valores), {"escrivao"})
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/generate")

    def test_modelo_remoto_no_ollama_bloqueado_antes_de_enviar_documento(self):
        opener = unittest.mock.Mock()
        opener.open.return_value = io.BytesIO(json.dumps({"models": [{
            "name": "modelo-cloud", "remote_host": "https://externo.ficticio", "size": 123
        }]}).encode())
        with patch.dict(os.environ, {"CPJ_IA_LOCAL_MODELO": "modelo-cloud"}):
            with patch.object(self.d.urllib.request, "build_opener", return_value=opener):
                valores, estado = self.d.completar_ia(TEXTO, "scan.pdf", ["escrivao"])
        self.assertFalse(valores)
        self.assertEqual(estado, "modelo_remoto_bloqueado")
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(opener.open.call_args.args[0], "http://127.0.0.1:11434/api/tags")

    def test_ia_indisponivel_deixa_pendencia_manual(self):
        with patch.dict(os.environ, {"CPJ_IA_LOCAL_MODELO": ""}):
            with patch.object(self.d.urllib.request, "build_opener", side_effect=AssertionError("Não chamar IA externa")):
                registro = self.d.aplicar(self.s.C, self.id, "## Página 1\nNatureza: FICTICIA", "scan.pdf", usar_ia=True)
        self.assertEqual(registro["ia"], "ia_local_nao_configurada")
        self.assertIn("escrivao", registro["pendentes"])

    def test_previa_exige_login_e_csrf(self):
        self.assertEqual(self.s.app.test_client().post("/api/os/detectar", headers={"X-CPJ": "1"}).status_code, 401)
        self.assertEqual(self.client.post("/api/os/detectar").status_code, 403)

    def test_salvar_e_atualizar_sem_processar_arquivos(self):
        antes = len(self.s.C.listar())
        fila = self.s.fila.qsize()
        r = self.client.post("/api/os", data={"os": "SALVAR-991/2099", "escrivao": "NOME INICIAL",
                            "somente_cadastro": "1", "arquivos": (io.BytesIO(b"DOCUMENTO FICTICIO"), "nao-processar.md")},
                            headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        id_ = r.json["caso"]
        self.assertTrue(r.json["criado"])
        self.assertEqual(r.json["recebidos"], [])
        self.assertEqual(self.s.fila.qsize(), fila)
        self.assertFalse(list((Path(self.s.C.caminho(id_)) / "00-originais").iterdir()))
        r = self.client.post("/api/os", data={"caso_id": id_, "os": "SALVAR-992/2099", "escrivao": "NOME CORRIGIDO",
                            "somente_cadastro": "1"}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json["criado"])
        self.assertEqual(r.json["caso"], id_)
        self.assertEqual(len(self.s.C.listar()), antes + 1)
        self.assertEqual(self.s.C.carregar(id_)["escrivao"], "NOME CORRIGIDO")
        self.assertEqual(self.s.C.carregar(id_)["ordem_servico"], "SALVAR-992/2099")

    def test_salvar_provisorio_depois_processar_no_mesmo_caso(self):
        r = self.client.post("/api/os", data={"bo": "AB345/2099", "somente_cadastro": "1"}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        id_ = r.json["caso"]
        r = self.client.post("/api/os", data={"caso_id": id_, "arquivos": (io.BytesIO(TEXTO.encode()), "complemento.md")},
                            headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json["criado"])
        self.assertEqual(r.json["caso"], id_)
        self.assertEqual(r.json["recebidos"], ["complemento.md"])

    def test_caso_id_nao_permite_atualizar_cadastro_alheio(self):
        client = self.entrar("escrivao_teste")
        r = client.post("/api/os", data={"caso_id": self.id, "escrivao": "NEGADO", "somente_cadastro": "1"},
                        headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.s.C.carregar(self.id)["escrivao"], "")
        r = self.client.post("/api/os", data={"caso_id": "../fora", "somente_cadastro": "1"}, headers={"X-CPJ": "1"})
        self.assertEqual(r.status_code, 400)

    def test_botoes_salvar_e_processar_preservam_formulario_e_reabilitam_apos_falha(self):
        html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="b-salvar-os">Salvar dados', html)
        self.assertIn('id="b-enviar">Processar PDF', html)
        funcao = re.search(r'(async function salvarRecebimento\(processar\).*?)\n\$\("#f-os"\)\.onsubmit', html, re.S)[1]
        funcao = re.search(r'(async function processarPDFComAviso\(enviarPedido\)\{[\s\S]*?\n\})', html)[1] + '\n' + funcao
        teste = r'''
const assert=require('node:assert/strict');
const f={reportValidity:()=>true,elements:{caso_id:{value:''}},campos:{os:'991/2099',escrivao:'NOME FICTICIO'}};
const dom={'#f-os':f};for(const id of ['#msg-up','#prog-up','#prog-up-tx','#b-enviar','#b-salvar-os','#b-nova-os','#dados-os-auto','#cons-destinos'])dom[id]={disabled:false,textContent:'',innerHTML:''};
const $=id=>dom[id],esc=String;
let arquivos=[{name:'ficticio.pdf'}],autoOS={},deteccaoOS=0,chamadas=[],falhar=false,avisar=false,recusar=false;
class FormData{constructor(form){this.dados={...form.campos,caso_id:form.elements.caso_id.value}}append(k,v){(this.dados[k]??=[]);if(Array.isArray(this.dados[k]))this.dados[k].push(v);else this.dados[k]=v}set(k,v){this.dados[k]=v}}
async function pedirConsentimentoExterno(destinos){return recusar?{recusado:true}:{aceito:true,destinos}}
async function enviar(url,fd){chamadas.push(JSON.parse(JSON.stringify(fd.dados)));if(falhar)throw Error('Falha ficticia');if(avisar){if(!fd.dados.consentimento_externo)return{requer_consentimento:true,escopo:'transcricao_visual',destinos:['openai'],paginas:2};if(JSON.parse(fd.dados.consentimento_externo).recusado)return{recusado:true,mensagem:'Recusado'};}return{caso:'OS-991-2099',criado:!fd.dados.caso_id,recebidos:fd.dados.arquivos?['ficticio.pdf']:[],ignorados:[]}}
function listaArqs(){} async function atualizarFila(){}function toast(){}
'''
        teste += funcao + r'''
(async()=>{
 await salvarRecebimento(false);assert.equal(chamadas.length,1);assert.equal(chamadas[0].arquivos,undefined);assert.deepEqual(chamadas[0].somente_cadastro,['1']);assert.equal(f.elements.caso_id.value,'OS-991-2099');assert.equal(arquivos.length,1);assert.equal(f.campos.escrivao,'NOME FICTICIO');
 await salvarRecebimento(true);assert.equal(chamadas[1].caso_id,'OS-991-2099');assert.equal(chamadas[1].arquivos.length,1);assert.equal(arquivos.length,0);assert.equal(f.campos.escrivao,'NOME FICTICIO');
 await salvarRecebimento(true);assert.equal(chamadas.length,2);assert.match(dom['#msg-up'].textContent,/Selecione o PDF/);
 falhar=true;await salvarRecebimento(false);assert.equal(dom['#msg-up'].textContent,'Falha ficticia');for(const id of ['#b-enviar','#b-salvar-os','#b-nova-os'])assert.equal(dom[id].disabled,false);
 falhar=false;avisar=true;recusar=true;arquivos=[{name:'ficticio.pdf'}];await salvarRecebimento(true);assert.equal(arquivos.length,1);assert.equal(f.campos.escrivao,'NOME FICTICIO');assert.equal(dom['#msg-up'].textContent,'Recusado');assert.equal(f.elements.caso_id.value,'OS-991-2099');for(const id of ['#b-enviar','#b-salvar-os','#b-nova-os'])assert.equal(dom[id].disabled,false);
 recusar=false;await salvarRecebimento(true);const cons=JSON.parse(chamadas.at(-1).consentimento_externo);assert.equal(cons.aceito,true);assert.equal(cons.escopo,'transcricao_visual');assert.equal(chamadas.at(-1).arquivos.length,1);assert.equal(arquivos.length,0);assert.equal(f.campos.escrivao,'NOME FICTICIO');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        import shutil
        if not shutil.which("node"):
            self.skipTest("Node.js não instalado neste ambiente")
        r = subprocess.run(["node", "-"], input=teste, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_configuracao_modelo_so_por_admin_sem_chamar_servico(self):
        with patch.dict(os.environ):
            os.environ.pop("CPJ_IA_LOCAL_MODELO", None)
            with patch.object(self.d.urllib.request, "build_opener", side_effect=AssertionError("Não consultar serviço ao salvar")):
                r = self.client.post("/api/os/ia-local", json={"modelo": "modelo-ficticio:teste"}, headers={"X-CPJ": "1"})
                self.assertEqual(r.status_code, 200)
                self.assertEqual(self.client.get("/api/os/ia-local").json["modelo"], "modelo-ficticio:teste")
                client = self.entrar("escrivao_teste")
                self.assertEqual(client.post("/api/os/ia-local", json={"modelo": "outro"}, headers={"X-CPJ": "1"}).status_code, 403)
                self.assertEqual(self.client.post("/api/os/ia-local", json={"modelo": "http://externo?x=1"}, headers={"X-CPJ": "1"}).status_code, 400)
                self.client.post("/api/os/ia-local", json={"modelo": ""}, headers={"X-CPJ": "1"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
