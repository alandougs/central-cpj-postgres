#!/usr/bin/env python3
"""Suíte de testes da Operação Full-Time 24/7 (Tarefa FT01 / RV01).

Valida:
1. Presença e sintaxe dos utilitários de background (central-daemon.py, VBS, .bat).
2. Ciclo de vida completo: iniciar supervisor -> checagem de saúde HTTP -> controle PID -> parada limpa.
3. Resiliência do Watchdog: reinício automático do servidor após término inesperado (crash).
4. Instalação e remoção do atalho no Startup do Windows.
"""
import json
import os
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(AQUI)
PLUGIN = os.path.dirname(APP_DIR)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN))
DAEMON_PY = os.path.join(RAIZ, "ferramentas", "central-daemon.py")
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def achar_porta_livre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TesteFullTime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cpj-teste-ft01-")
        os.environ["CPJ_WORKSPACE"] = self.tmp
        self.porta = achar_porta_livre()

    def tearDown(self):
        # Garante parada do daemon se ficou ativo
        subprocess.run(
            [sys.executable, DAEMON_PY, "parar", "--workspace", self.tmp],
            capture_output=True,
            creationflags=SEM_JANELA,
        )
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_01_arquivos_existentes(self):
        """Utilitários do supervisor e scripts batch devem existir na pasta ferramentas."""
        self.assertTrue(os.path.isfile(DAEMON_PY))
        self.assertTrue(os.path.isfile(os.path.join(RAIZ, "ferramentas", "iniciar-central-24-7.vbs")))
        self.assertTrue(os.path.isfile(os.path.join(RAIZ, "ferramentas", "Central Full-Time.bat")))
        self.assertTrue(os.path.isfile(os.path.join(RAIZ, "ferramentas", "Status Central.bat")))
        self.assertTrue(os.path.isfile(os.path.join(RAIZ, "ferramentas", "Parar Central.bat")))

    def test_02_status_parado(self):
        """Quando não houver daemon rodando, status deve retornar código 1 e JSON inativo."""
        r = subprocess.run(
            [sys.executable, DAEMON_PY, "status", "--workspace", self.tmp, "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertNotEqual(r.returncode, 0)
        dados = json.loads(r.stdout)
        self.assertFalse(dados["ativo"])

    def test_03_ciclo_iniciar_status_parar(self):
        """Ciclo completo: disparo do supervisor, estabilização HTTP e parada limpa."""
        proc = subprocess.Popen(
            [sys.executable, DAEMON_PY, "iniciar", "--porta", str(self.porta), "--workspace", self.tmp],
            creationflags=SEM_JANELA,
        )
        try:
            # Aguarda inicialização HTTP
            ativo = False
            for _ in range(30):
                r = subprocess.run(
                    [sys.executable, DAEMON_PY, "status", "--workspace", self.tmp, "--json"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if r.returncode == 0:
                    dados = json.loads(r.stdout)
                    if dados["ativo"] and dados["http_ok"]:
                        ativo = True
                        break
                time.sleep(1.0)

            self.assertTrue(ativo, "Central CPJ não inicializou a tempo no teste do supervisor.")

            # Para a Central
            r_parar = subprocess.run(
                [sys.executable, DAEMON_PY, "parar", "--workspace", self.tmp],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(r_parar.returncode, 0)

            # Confere se o status agora é parado
            r_pos = subprocess.run(
                [sys.executable, DAEMON_PY, "status", "--workspace", self.tmp, "--json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            dados_pos = json.loads(r_pos.stdout)
            self.assertFalse(dados_pos["ativo"])
        finally:
            if proc.poll() is None:
                proc.terminate()

    def test_04_watchdog_auto_restart(self):
        """Watchdog deve detectar processo servidor morto e reiniciá-lo automaticamente."""
        proc = subprocess.Popen(
            [sys.executable, DAEMON_PY, "iniciar", "--porta", str(self.porta), "--workspace", self.tmp],
            creationflags=SEM_JANELA,
        )
        try:
            # Aguarda primeiro PID do servidor
            server_pid_1 = None
            for _ in range(30):
                r = subprocess.run(
                    [sys.executable, DAEMON_PY, "status", "--workspace", self.tmp, "--json"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if r.returncode == 0:
                    dados = json.loads(r.stdout)
                    if dados["ativo"]:
                        server_pid_1 = dados["server_pid"]
                        break
                time.sleep(1.0)

            self.assertIsNotNone(server_pid_1, "Servidor não subiu inicialmente.")

            # Mata intencionalmente o processo do servidor via taskkill (simula crash)
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(server_pid_1)], capture_output=True, creationflags=SEM_JANELA)
            else:
                os.kill(server_pid_1, signal.SIGKILL)

            # O supervisor deve detectar e subir um novo processo do servidor com PID diferente
            server_pid_2 = None
            for _ in range(30):
                time.sleep(1.0)
                r = subprocess.run(
                    [sys.executable, DAEMON_PY, "status", "--workspace", self.tmp, "--json"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if r.returncode == 0:
                    dados = json.loads(r.stdout)
                    if dados["ativo"] and dados["server_pid"] != server_pid_1:
                        server_pid_2 = dados["server_pid"]
                        break

            self.assertIsNotNone(server_pid_2, "Watchdog falhou ao reiniciar o servidor após crash.")
            self.assertNotEqual(server_pid_1, server_pid_2)

        finally:
            subprocess.run([sys.executable, DAEMON_PY, "parar", "--workspace", self.tmp], capture_output=True, creationflags=SEM_JANELA)
            if proc.poll() is None:
                proc.terminate()

    def test_05_instalacao_remocao_atalho_boot(self):
        """Valida que instalar-boot cria o atalho no Startup e remover-boot o remove de forma limpa."""
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            self.skipTest("Variável APPDATA não encontrada.")

        atalho = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "Central-CPJ-24-7.lnk")

        r_inst = subprocess.run([sys.executable, DAEMON_PY, "instalar-boot"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r_inst.returncode, 0)
        self.assertTrue(os.path.isfile(atalho))

        r_rem = subprocess.run([sys.executable, DAEMON_PY, "remover-boot"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r_rem.returncode, 0)
        self.assertFalse(os.path.isfile(atalho))


if __name__ == "__main__":
    unittest.main()
