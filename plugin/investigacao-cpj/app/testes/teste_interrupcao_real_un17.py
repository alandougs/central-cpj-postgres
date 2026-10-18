"""UN17: interrupção real (processo do servidor encerrado à força) durante o processamento e retomada.

Cobre a lacuna deixada pelos testes de UN13/UN14 (queda simulada no banco): aqui o processo `servidor.py` é morto
com TerminateProcess enquanto autos fictícios com páginas escaneadas estão sendo processados; um novo servidor sobre o
mesmo workspace deve concluir o processamento sem alterar o original, sem duplicar o caso e sem deixar execução
"em execução" órfã. Somente dados fictícios, workspace temporário, nenhum executor de IA.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))


def _porta():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _multipart(campos, arquivos):
    limite = "----cpj" + uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (nome, dados) in arquivos.items():
        partes.append((f'--{limite}\r\nContent-Disposition: form-data; name="{k}"; filename="{nome}"\r\n'
                       'Content-Type: application/pdf\r\n\r\n').encode() + dados + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


class InterrupcaoReal(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="cpj-un17-interrupcao-"))
        self.addCleanup(shutil.rmtree, self.ws, True)
        modelo = self.ws / "casos/_MODELO-CASO"
        modelo.mkdir(parents=True)
        (modelo / "caso.json").write_text(json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}), encoding="utf-8")
        (self.ws / "config").mkdir()
        from auth import Auth
        Auth(str(self.ws)).salvar_usuario("un17", "Operador fictício UN17", "admin", "SenhaFicticia123")
        (self.ws / "config/solo.json").write_text('{"ativo":true}', encoding="utf-8")
        self.porta = _porta()
        self.url = f"http://127.0.0.1:{self.porta}"
        self.env = dict(os.environ, CPJ_WORKSPACE=str(self.ws), CPJ_SEM_AGENTE_EMBUTIDO="1", CPJ_IA_LOCAL_MODELO="",
                        PYTHONIOENCODING="utf-8", APPDATA=str(self.ws / "appdata-ficticio"))
        self.env.pop("CPJ_WORKSPACES", None)
        self.processo = None
        self.addCleanup(self.parar)

    def iniciar(self):
        log = (self.ws / "servidor.log").open("a", encoding="utf-8")
        self.addCleanup(log.close)
        self.processo = subprocess.Popen(
            [sys.executable, "-X", "utf8", str(APP / "servidor.py"), "--workspace", str(self.ws), "--porta", str(self.porta),
             "--somente-local", "--sem-navegador"], env=self.env, stdout=log, stderr=subprocess.STDOUT)
        fim = time.monotonic() + 40
        while time.monotonic() < fim:
            self.assertIsNone(self.processo.poll(), (self.ws / "servidor.log").read_text(encoding="utf-8", errors="replace")[-3000:])
            try:
                with urllib.request.urlopen(self.url + "/api/sessao", timeout=1) as r:
                    if json.load(r).get("solo"):
                        return
            except OSError:
                time.sleep(.15)
        self.fail("servidor não iniciou: " + (self.ws / "servidor.log").read_text(encoding="utf-8", errors="replace")[-3000:])

    def parar(self):
        if self.processo is not None and self.processo.poll() is None:
            self.processo.terminate()
            try:
                self.processo.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.processo.kill()
                self.processo.wait(timeout=5)

    def get(self, caminho):
        with urllib.request.urlopen(self.url + caminho, timeout=10) as r:
            return json.load(r)

    def enviar(self, pdf):
        corpo, tipo = _multipart({"os": "917/2026", "modo_processamento": "rapido"}, {"arquivos": (pdf.name, pdf.read_bytes())})
        req = urllib.request.Request(self.url + "/api/os", data=corpo, method="POST", headers={"Content-Type": tipo, "X-CPJ": "1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["caso"]

    def processamento(self, caso):
        return json.loads((self.ws / "casos" / caso / "processamento.json").read_text(encoding="utf-8")) \
            if (self.ws / "casos" / caso / "processamento.json").is_file() else {}

    def concluido(self, caso):
        d = self.ws / "casos" / caso
        trabalhos = self.processamento(caso).get("trabalhos", [])
        return bool(trabalhos) and all(t.get("status") == "concluido" for t in trabalhos) and any(d.glob("01-extracao/*/entidades.csv"))

    def test_morte_do_processo_durante_o_processamento_e_retomada(self):
        from testes.e2e.pdf_aux import gerar_pdf_sintetico_e2e
        pdf = self.ws / "autos-ficticios.pdf"
        gerar_pdf_sintetico_e2e(pdf, paginas_texto=2, paginas_imagem=8)   # várias páginas escaneadas: o OCR leva tempo
        hash_original = hashlib.sha256(pdf.read_bytes()).hexdigest()
        self.iniciar()
        caso = self.enviar(pdf)
        # espera o trabalho existir e NÃO estar concluído; então mata o processo de forma abrupta (TerminateProcess)
        interrompido = False
        fim = time.monotonic() + 60
        while time.monotonic() < fim:
            trabalhos = self.processamento(caso).get("trabalhos", [])
            if trabalhos and any(t.get("status") in ("na_fila", "processando") for t in trabalhos):
                self.processo.kill()
                self.processo.wait(timeout=10)
                interrompido = True
                break
            if self.concluido(caso):
                break
            time.sleep(.03)
        self.assertTrue(interrompido, "o processamento terminou antes de a interrupção real ser possível (aumentar a carga)")
        self.assertFalse(self.concluido(caso), "o caso já estava concluído quando o processo foi morto")
        originais = list((self.ws / "casos" / caso / "00-originais").glob("*.pdf"))
        self.assertEqual(len(originais), 1)
        self.assertEqual(hashlib.sha256(originais[0].read_bytes()).hexdigest(), hash_original)

        self.iniciar()                                                     # novo processo, mesmo workspace
        fim = time.monotonic() + 150
        while time.monotonic() < fim and not self.concluido(caso):
            time.sleep(.5)
        self.assertTrue(self.concluido(caso), json.dumps(self.processamento(caso), ensure_ascii=False)[:1500])
        transcricao = next((self.ws / "casos" / caso).glob("01-extracao/*/transcricao.md")).read_text(encoding="utf-8")
        self.assertIn("## Página 10", transcricao, "todas as páginas (inclusive as escaneadas) devem estar na transcrição")
        # original intacto, sem caso duplicado, e nenhuma execução órfã no registro de fluxos
        self.assertEqual(hashlib.sha256(originais[0].read_bytes()).hexdigest(), hash_original)
        self.assertEqual([p.name for p in (self.ws / "casos").iterdir() if p.name != "_MODELO-CASO"], [caso])
        itens = self.get("/api/fluxos?limite=100")["itens"]
        self.assertFalse([i for i in itens if i.get("estado") == "em_execucao"], itens)
        self.assertFalse(any(i.get("estado") == "falhou" for i in itens), itens)


if __name__ == "__main__":
    unittest.main(verbosity=2)
