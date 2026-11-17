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


def _ler_json(caminho, tentativas=25, pausa=.015):
    p = Path(caminho)
    for i in range(tentativas):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except FileNotFoundError:
            if i >= 2:
                return {}
            time.sleep(.005)
        except (OSError, json.JSONDecodeError):
            if i + 1 < tentativas:
                time.sleep(pausa)
    return {}


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
        if not self.env.get("TESSDATA_PREFIX"):
            for cand in (APP.parents[2] / "ferramentas/tessdata", APP.parents[3] / "CPJ - BACKUP/ferramentas/tessdata",
                         Path(r"C:\Program Files\Tesseract-OCR\tessdata")):
                if (cand / "por.traineddata").is_file():
                    self.env["TESSDATA_PREFIX"] = str(cand)
                    break
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
        return _ler_json(self.ws / "casos" / caso / "processamento.json")

    def concluido(self, caso):
        d = self.ws / "casos" / caso
        trabalhos = self.processamento(caso).get("trabalhos", [])
        return bool(trabalhos) and all(t.get("status") == "concluido" for t in trabalhos) and any(d.glob("01-extracao/*/transcricao.md"))

    def test_morte_do_processo_durante_o_processamento_e_retomada(self):
        from testes.e2e.pdf_aux import gerar_pdf_sintetico_e2e
        pdf = self.ws / "autos-ficticios.pdf"
        gerar_pdf_sintetico_e2e(pdf, paginas_texto=2, paginas_imagem=8)   # várias páginas escaneadas: o OCR leva tempo
        hash_original = hashlib.sha256(pdf.read_bytes()).hexdigest()
        self.iniciar()
        caso = self.enviar(pdf)
        # Espera um checkpoint parcial real, então mata o servidor de forma abrupta (TerminateProcess).
        interrompido = False
        paginas_antes = {}
        fim = time.monotonic() + 60
        while time.monotonic() < fim:
            trabalhos = self.processamento(caso).get("trabalhos", [])
            estados = list((self.ws / "casos" / caso).glob("01-extracao/*/.checkpoint/estado.json"))
            if estados:
                paginas = _ler_json(estados[0]).get("paginas", {})
                if paginas:
                    paginas_antes = paginas
            if trabalhos and any(t.get("status") == "processando" for t in trabalhos) and 2 <= len(paginas_antes) < 10:
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
        estado_final = _ler_json(next((self.ws / "casos" / caso).glob("01-extracao/*/.checkpoint/estado.json")))
        self.assertGreaterEqual(estado_final["relatorio"]["paginas_reaproveitadas"], len(paginas_antes))
        for numero, pagina in paginas_antes.items():
            self.assertEqual(estado_final["paginas"][numero], pagina, "Checkpoint íntegro anterior à queda deve ser preservado.")
        self.assertGreaterEqual(estado_final["relatorio"]["metodos"].get("ocr-tesseract", 0), 8,
                                "As oito páginas escaneadas devem passar por OCR português real.")
        self.assertFalse(list((self.ws / "casos" / caso / "01-extracao").rglob("*.csv")))
        # original intacto, sem caso duplicado, e nenhuma execução órfã no registro de fluxos
        self.assertEqual(hashlib.sha256(originais[0].read_bytes()).hexdigest(), hash_original)
        self.assertEqual([p.name for p in (self.ws / "casos").iterdir() if p.name != "_MODELO-CASO"], [caso])
        itens = self.get("/api/fluxos?limite=100")["itens"]
        self.assertFalse([i for i in itens if i.get("estado") == "em_execucao"], itens)
        self.assertFalse(any(i.get("estado") == "falhou" for i in itens), itens)


def _encerrar_filho_ficticio(pid):
    if os.name == "nt":
        import ctypes
        k=ctypes.WinDLL("kernel32",use_last_error=True); k.OpenProcess.restype=ctypes.c_void_p
        h=k.OpenProcess(0x100001,False,pid)  # SYNCHRONIZE | PROCESS_TERMINATE
        if h:
            try:
                k.TerminateProcess(ctypes.c_void_p(h),1)
                if k.WaitForSingleObject(ctypes.c_void_p(h),5000) != 0:raise RuntimeError("Filho fictício não encerrou.")
            finally:k.CloseHandle(ctypes.c_void_p(h))
    else:
        try:os.kill(pid,__import__('signal').SIGTERM)
        except ProcessLookupError:pass


class TravaExtracaoReal(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Junction nativa Windows")
    def test_trava_recusa_checkpoint_junction_sem_alterar_destino(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory(prefix="cpj-un17-junction-") as td:
            raiz=Path(td); pdf=raiz/'ficticio.pdf'; saida=raiz/'extracao'; alvo=raiz/'alvo'
            saida.mkdir(); alvo.mkdir(); (alvo/'sentinela.txt').write_text('intacto')
            w=PdfWriter(); w.add_blank_page(width=300,height=400); w.write(pdf)
            r=subprocess.run(['cmd','/c','mklink','/J',str(saida/'.checkpoint'),str(alvo)],capture_output=True)
            self.assertEqual(r.returncode,0,'Fixture de junction não foi criada.')
            try:
                script=APP.parent/'skills/pdf-autos-policiais/scripts/extrair.py'
                r=subprocess.run([sys.executable,'-X','utf8',str(script),str(pdf),'--saida',str(saida),'--ocr','visao'],
                                 capture_output=True,timeout=10)
                self.assertNotEqual(r.returncode,0)
                self.assertIn('junção',r.stderr.decode('utf-8','replace'))
                self.assertEqual([p.name for p in alvo.iterdir()],['sentinela.txt'])
                self.assertEqual((alvo/'sentinela.txt').read_text(),'intacto')
            finally:(saida/'.checkpoint').rmdir()

    def test_filho_orfao_mantem_trava_ate_terminar_e_novo_extrator_nao_escreve(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory(prefix="cpj-un17-trava-") as td:
            raiz = Path(td); pdf = raiz / "ficticio.pdf"; saida = raiz / "extracao"
            w=PdfWriter(); w.add_blank_page(width=300,height=400); w.write(pdf)
            script = APP.parent / "skills/pdf-autos-policiais/scripts/extrair.py"
            # O filho permanece DENTRO da escrita da extração real, com a trava adquirida.
            filho = r"""
import os,runpy,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).parent))
script,pdf,saida=sys.argv[1:]; sys.argv=[script,pdf,'--saida',saida,'--ocr','visao','--sem-reaproveitar']
import estado_extracao as estado
grava=estado.gravar
def escrever(pasta,dados):
 grava(pasta,dados)
 if dados.get('paginas'):
  p=Path(pasta)/'escritor-ficticio.txt'
  while True:
   with p.open('a') as f:f.write('escrita ficticia\n')
   time.sleep(.02)
estado.gravar=escrever
runpy.run_path(script,run_name='__main__')
"""
            pai = r"""
import subprocess,sys
from pathlib import Path
log=(Path(sys.argv[-1]).parent/'filho.log').open('wb')
p=subprocess.Popen([sys.executable,'-X','utf8','-c',sys.argv[1],*sys.argv[2:]],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
print(p.pid,flush=True);sys.stdin.read()
"""
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CPJ_WORKSPACE=str(raiz))
            lancador=subprocess.Popen([sys.executable,'-c',pai,filho,str(script),str(pdf),str(saida)],
                                     stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,env=env)
            pid=int(lancador.stdout.readline()); segundo=None
            try:
                fim=time.monotonic()+15
                marcador=saida/'escritor-ficticio.txt'
                while time.monotonic()<fim and not marcador.exists():time.sleep(.02)
                self.assertTrue(marcador.exists(),(raiz/'filho.log').read_text(encoding='utf-8',errors='replace'))
                lancador.kill();lancador.wait(timeout=10)  # não mata o filho escritor
                estado=saida/'.checkpoint/estado.json'; antes=estado.read_bytes()
                cmd=[sys.executable,'-X','utf8',str(script),str(pdf),'--saida',str(saida),'--ocr','visao','--sem-reaproveitar','--refazer']
                segundo=subprocess.Popen(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                with self.assertRaises(subprocess.TimeoutExpired):segundo.wait(timeout=.7)
                self.assertEqual(estado.read_bytes(),antes,'Novo extrator não pode escrever sobre o filho órfão vivo.')
                self.assertGreater(marcador.stat().st_size,len('escrita ficticia\n'))
                # Timeout conservador não altera estado nem remove a trava do proprietário vivo.
                ocupado=subprocess.run(cmd+['--espera-trava','.15'],env=env,capture_output=True,timeout=10)
                self.assertNotEqual(ocupado.returncode,0)
                self.assertIn('ocupada',ocupado.stderr.decode('utf-8','replace'))
                self.assertEqual(estado.read_bytes(),antes)
                _encerrar_filho_ficticio(pid)  # somente o filho fictício desta fixture
                out,erro=segundo.communicate(timeout=20)
                self.assertEqual(segundo.returncode,0,erro.decode('utf-8','replace'))
                self.assertIn('## Página 1',(saida/'transcricao.md').read_text(encoding='utf-8'))
                self.assertEqual((saida/'.checkpoint/extracao.lock').read_bytes(),b'\0')
            finally:
                if lancador.poll() is None:lancador.kill();lancador.wait(timeout=10)
                lancador.stdin.close();lancador.stdout.close()
                _encerrar_filho_ficticio(pid)
                if segundo is not None:
                    if segundo.poll() is None:segundo.kill();segundo.wait(timeout=10)
                    segundo.stdout.close();segundo.stderr.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
