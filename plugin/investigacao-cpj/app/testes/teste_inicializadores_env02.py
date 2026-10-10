"""Inicializadores reais, executados apenas em raiz e servidor fictícios."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

RAIZ = Path(__file__).resolve().parents[4]


@unittest.skipUnless(os.name == "nt", "Entradas Windows")
class InicializadoresENV02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cpj-env02-test-")
        cls.base = Path(cls.tmp.name)
        cls.venv = cls.base / "venv-modelo"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(cls.venv)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        # O VBS inicia de forma assíncrona: o stub pode terminar de escrever
        # antes de o Windows liberar seu executável. Não ocultar falha real.
        for tentativa in range(25):
            try:
                cls.tmp.cleanup()
                return
            except PermissionError:
                if tentativa == 24:
                    raise
                time.sleep(.2)

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="raiz ficticia ", dir=self.base))
        (self.ws / "ferramentas").mkdir()
        (self.ws / "plugin/investigacao-cpj/app").mkdir(parents=True)
        for rel in ["Central CPJ.bat", "ferramentas/iniciar-central-24-7.vbs", "ferramentas/Central Full-Time.bat", "ferramentas/Status Central.bat", "ferramentas/Parar Central.bat"]:
            shutil.copy2(RAIZ / rel, self.ws / rel)
        stub = ('import json,os,sys,subprocess\nfrom pathlib import Path\n'
                'p=Path(os.environ["ENV02_RESULTADO"])\n'
                # cmd.exe representa o processo não Python (ex.: Claude) que
                # resolve ferramentas pelo PATH, sem busca pelo exe do pai.
                'child=subprocess.run(["cmd.exe","/d","/c","python --version"],capture_output=True,text=True)\n'
                'p.mkdir(exist_ok=True)\n'
                'q=p/(str(os.getpid())+".tmp")\n'
                'q.write_text(json.dumps({"exe":sys.executable,"args":sys.argv[1:],"cwd":os.getcwd(),"ws":os.environ.get("CPJ_WORKSPACE"),"multi":os.environ.get("CPJ_WORKSPACES"),"child_code":child.returncode,"child_version":child.stdout}),encoding="utf-8")\n'
                'os.replace(q,q.with_suffix(".json"))\n')
        (self.ws / "plugin/investigacao-cpj/app/servidor.py").write_text(stub, encoding="utf-8")
        (self.ws / "ferramentas/central-daemon.py").write_text(stub, encoding="utf-8")
        self.out = self.ws / "resultados"
        self.path = self.ws / "path"
        self.path.mkdir()
        (self.path / "python.cmd").write_text('@echo off\nexit /b 37\n', encoding="ascii")
        self.env = dict(os.environ, PATH=str(self.path) + os.pathsep + os.environ.get("PATH", ""),
                        ENV02_RESULTADO=str(self.out), CPJ_WORKSPACE="workspace-herdado-invalido",
                        CPJ_WORKSPACES="outro-workspace", APPDATA=str(self.ws / "appdata-ficticio"))

    def instalar_venv(self):
        dst = self.ws / ".venv"
        (dst / "Scripts").mkdir(parents=True)
        shutil.copy2(self.venv / "pyvenv.cfg", dst / "pyvenv.cfg")
        for exe in ["python.exe", "pythonw.exe"]:
            shutil.copy2(self.venv / "Scripts" / exe, dst / "Scripts" / exe)

    def executar(self, rel, vbs=False):
        command = (["cscript.exe", "//nologo", str(self.ws / rel)] if vbs else
                   ["cmd.exe", "/d", "/c", str(self.ws / rel)])
        result = subprocess.run(command, env=self.env, cwd=self.base, input="\n", capture_output=True,
                                text=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        deadline = time.monotonic() + 5
        esperado = 2 if rel == "ferramentas/Central Full-Time.bat" else 1
        while len(self.ler_resultados()) < esperado and time.monotonic() < deadline:
            time.sleep(.05)
        rows = self.ler_resultados()
        self.assertEqual(len(rows), esperado, result.stdout + result.stderr)
        return rows

    def ler_resultados(self):
        return [json.loads(p.read_text(encoding="utf-8")) for p in self.out.glob("*.json")]

    def conferir(self, rows, args, local=True):
        self.assertEqual([r["args"] for r in rows], args)
        for row in rows:
            self.assertEqual(Path(row["cwd"]).resolve(), self.ws.resolve())
            self.assertEqual(Path(row["ws"]).resolve(), self.ws.resolve())
            self.assertFalse(row["multi"])
            if local:
                self.assertEqual(Path(row["exe"]).resolve(), (self.ws / ".venv/Scripts/python.exe").resolve())
        self.assertFalse((self.ws / "config").exists())
        self.assertFalse((self.ws / "appdata-ficticio").exists())

    def test_central_prefere_venv_com_path_python_invalido(self):
        self.instalar_venv()
        self.conferir(self.executar("Central CPJ.bat"), [[]])

    def test_subprocessos_python_herdam_venv_nas_cinco_entradas(self):
        self.instalar_venv()
        for rel, vbs in [("Central CPJ.bat", False), ("ferramentas/Status Central.bat", False),
                         ("ferramentas/Parar Central.bat", False), ("ferramentas/Central Full-Time.bat", False),
                         ("ferramentas/iniciar-central-24-7.vbs", True)]:
            with self.subTest(entrada=rel):
                if self.out.exists():
                    shutil.rmtree(self.out)
                rows = self.executar(rel, vbs=vbs)
                for row in rows:
                    self.assertEqual(row["child_code"], 0, "Filho ainda usa Python inválido do PATH")
                    self.assertIn("Python 3.", row["child_version"])

    def test_status_e_parada_usam_venv_e_workspace_da_entrada(self):
        self.instalar_venv()
        for rel, arg in [("ferramentas/Status Central.bat", "status"), ("ferramentas/Parar Central.bat", "parar")]:
            with self.subTest(arg=arg):
                if self.out.exists():
                    shutil.rmtree(self.out)
                self.conferir(self.executar(rel), [[arg]])

    def test_vbs_silencioso_usando_venv_sem_startup(self):
        self.instalar_venv()
        self.conferir(self.executar("ferramentas/iniciar-central-24-7.vbs", vbs=True), [["iniciar", "--porta", "8765"]])

    def test_full_time_inicia_e_consulta_mesmo_workspace(self):
        self.instalar_venv()
        rows = self.executar("ferramentas/Central Full-Time.bat")
        self.conferir(sorted(rows, key=lambda r: r["args"]), [["iniciar", "--porta", "8765"], ["status"]])

    def test_fallback_python_existente_sem_venv(self):
        (self.path / "python.cmd").write_text('@echo off\n"' + sys.executable + '" %*\n', encoding="utf-8")
        self.conferir(self.executar("Central CPJ.bat"), [[]], local=False)


if __name__ == "__main__":
    unittest.main()
