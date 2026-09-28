"""Gerenciador do ciclo de vida da Central CPJ para testes E2E."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

AQUI = Path(__file__).resolve().parent
TESTES_DIR = AQUI.parent
APP_DIR = TESTES_DIR.parent
PLUGIN_DIR = APP_DIR.parent
ROOT_DIR = PLUGIN_DIR.parent.parent  # workspace (plugin\investigacao-cpj → plugin → workspace)


def encontrar_porta_livre(porta_base=8766, tentativas=20) -> int:
    """Encontra uma porta TCP livre a partir de porta_base para evitar conflito com outros agentes."""
    for p in range(porta_base, porta_base + tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError(f"Nenhuma porta livre encontrada a partir de {porta_base}.")


class ServidorTesteE2E:
    def __init__(self, porta=8766):
        self.porta_solicitada = porta
        self.porta = None
        self.temp_dir = None
        self.ws = None
        self.processo = None
        self.log_file = None
        self.url = None

    def iniciar(self, timeout=25.0):
        # Seleciona uma porta livre (utiliza 8766 se livre, ou próxima caso outro agente esteja testando na 8766)
        self.porta = encontrar_porta_livre(self.porta_solicitada)
        self.url = f"http://127.0.0.1:{self.porta}"

        self.temp_dir = tempfile.TemporaryDirectory(prefix="cpj-e2e-ws-")
        self.ws = Path(self.temp_dir.name)

        # 1. Cria estrutura necessária do workspace temporário
        for sub in (
            "casos/_MODELO-CASO/00-originais",
            "casos/_MODELO-CASO/01-extracao",
            "casos/_MODELO-CASO/02-analise",
            "casos/_MODELO-CASO/03-relatorios",
            "config",
            "producao",
            "modelos",
            "revisoes",
        ):
            (self.ws / sub).mkdir(parents=True, exist_ok=True)

        (self.ws / "casos/_MODELO-CASO/caso.json").write_text(
            json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}),
            encoding="utf-8",
        )

        # 2. Copia modelos oficiais para que o gerador de DOCX encontre o template
        modelos_orig = ROOT_DIR / "modelos"
        if not any(modelos_orig.glob("*.docx")):
            raise RuntimeError(f"Modelo DOCX oficial não encontrado em {modelos_orig}")
        for item in modelos_orig.iterdir():
            if item.is_file():
                shutil.copy2(item, self.ws / "modelos" / item.name)

        # 3. Configura modo solo ativo
        (self.ws / "config" / "solo.json").write_text(
            json.dumps({"ativo": True}),
            encoding="utf-8",
        )

        # 4. Cadastra usuário administrador único para ativar o modo solo
        if str(APP_DIR) not in sys.path:
            sys.path.insert(0, str(APP_DIR))
        from auth import Auth
        auth = Auth(str(self.ws))
        auth.salvar_usuario(
            "alan",
            "Alan Douglas Silva",
            "admin",
            "SenhaSeguraFicticia123",
            cargo="Investigador de Polícia",
        )

        # 5. Inicia servidor como subprocesso isolado
        cmd = [
            sys.executable,
            "-X", "utf8",
            str(APP_DIR / "servidor.py"),
            "--workspace", str(self.ws),
            "--porta", str(self.porta),
            "--somente-local",
            "--sem-navegador",
        ]
        env = dict(
            os.environ,
            CPJ_WORKSPACE=str(self.ws),
            PYTHONIOENCODING="utf-8",
            PYTHONWARNINGS="ignore",
        )

        log_path = self.ws / "servidor_e2e.log"
        self.log_file = open(log_path, "w", encoding="utf-8", errors="replace")
        self.processo = subprocess.Popen(
            cmd,
            env=env,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
        )

        # 6. Aguarda o servidor próprio estar pronto respondendo na porta com nosso usuário
        t0 = time.monotonic()
        pronto = False
        while time.monotonic() - t0 < timeout:
            if self.processo.poll() is not None:
                self.log_file.flush()
                log_conteudo = log_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(
                    f"Servidor encerrou prematuramente com código {self.processo.returncode}:\n{log_conteudo}"
                )
            try:
                req = urllib.request.Request(
                    f"{self.url}/api/sessao",
                    headers={"X-CPJ": "1"},
                )
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        dados = json.loads(resp.read().decode("utf-8"))
                        if (
                            dados.get("solo") is True
                            and dados.get("usuario", {}).get("nome") == "Alan Douglas Silva"
                        ):
                            pronto = True
                            break
            except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
                time.sleep(0.2)

        if not pronto:
            self.parar()
            raise TimeoutError(f"Servidor não respondeu em {self.url} dentro de {timeout}s.")

    def ler_log(self) -> str:
        if self.ws is None:
            return ""
        log_path = self.ws / "servidor_e2e.log"
        if log_path.exists():
            try:
                if self.log_file is not None and not self.log_file.closed:
                    self.log_file.flush()
                return log_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""
        return ""

    def parar(self):
        if self.processo is not None:
            try:
                self.processo.terminate()
                self.processo.wait(timeout=5)
            except Exception:
                try:
                    self.processo.kill()
                    self.processo.wait(timeout=3)
                except Exception:
                    pass
            self.processo = None

        if self.log_file is not None and not self.log_file.closed:
            self.log_file.close()
            self.log_file = None

        if self.temp_dir is not None:
            try:
                self.temp_dir.cleanup()
            except Exception:
                pass
            self.temp_dir = None
