"""Teste UN10: python -X utf8 app/testes/teste_recuperacao_un10.py.

Backup consistente e restauração em workspace sintético (dados fictícios).
Cobre: fontes e estado preservados, SQLite com WAL aberto, retorno sem
sobrescrever trabalho posterior e recusa de backup adulterado.
"""
import hashlib
import importlib.util
import json
import os
import base64
from unittest.mock import patch
import sqlite3
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]


def carregar_ferramenta():
    spec = importlib.util.spec_from_file_location("backup_consistente", RAIZ / "ferramentas" / "backup_consistente.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class WorkspaceSintetico:
    """Workspace fictício com originais, caso, processamento, vínculo manual, relatório e banco em WAL."""

    def __init__(self, base: Path):
        self.ws = base / "ws"
        caso = self.ws / "casos" / "OS-0001-2026"
        for sub in ("00-originais", "01-extracao/doc1", "02-analise", "03-relatorios"):
            (caso / sub).mkdir(parents=True)
        for p in ("calibracao", "producao", "modelos", "consulta", "referencias", "config", "usuarios"):
            (self.ws / p).mkdir(parents=True, exist_ok=True)
        (caso / "00-originais" / "autos.pdf").write_bytes(b"%PDF-1.4 ficticio\x00\xff" * 50)
        (caso / "caso.json").write_text(json.dumps({"id": "OS-0001-2026", "status": "em_analise"}), encoding="utf-8")
        (caso / "processamento.json").write_text(json.dumps({"etapas": {"extracao": "ok"}}), encoding="utf-8")
        (caso / "01-extracao" / "doc1" / "transcricao.md").write_text("## Página 1\ntexto fictício\n", encoding="utf-8")
        (caso / "02-analise" / "vinculos-manuais.json").write_text(
            json.dumps([{"id": "vm-1", "a": "cpf:111", "b": "conta:222", "relacao": "manual"}]), encoding="utf-8")
        (caso / "03-relatorios" / "RELATORIO-OS-0001-2026-v01.docx").write_bytes(b"PK\x03\x04docx-ficticio" * 20)
        self.caso = caso
        self.db = self.ws / "config" / "plantao.sqlite"
        # Conexão mantida aberta: as linhas ficam no -wal, sem checkpoint no arquivo principal.
        self.con = sqlite3.connect(self.db)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("CREATE TABLE pedidos(id INTEGER PRIMARY KEY, caso TEXT, estado TEXT)")
        self.con.commit()
        self.con.execute("PRAGMA wal_autocheckpoint=0")
        for i in range(100):
            self.con.execute("INSERT INTO pedidos(caso, estado) VALUES (?, 'na_fila')", ("OS-0001-2026",))
        self.con.commit()

    def arquivos_fonte(self) -> dict:
        return {str(p.relative_to(self.ws)): sha(p) for p in sorted(self.ws.rglob("*"))
                if p.is_file() and p.suffix not in ("", ) and not p.name.endswith(("-wal", "-shm"))
                and p.suffix != ".sqlite"}

    def fechar(self):
        self.con.close()


class TesteRecuperacaoUN10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-un10-")
        self.base = Path(self.tmp.name)
        self.f = carregar_ferramenta()
        # Isolar também o armazenamento externo da âncora; nenhuma conta real.
        perfil = self.base / "perfil-ficticio"
        perfil.mkdir()
        ambiente = patch.dict(os.environ, {"LOCALAPPDATA": str(perfil),
            "CPJ_LOCAL_SECRET_KEY": base64.b64encode(b"F" * 32).decode()})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.s = WorkspaceSintetico(self.base)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.s.fechar)
        # Somente a primitiva DPAPI é simulada; exportação, vínculo ao log,
        # verificação e restauração da âncora continuam executando o código real.
        def dpapi_ficticia(dados, desfazer=False):
            prefixo = b"UN10-DPAPI-FICTICIA\x00"
            if desfazer:
                if not dados.startswith(prefixo): raise ValueError("envelope ficticio invalido")
                return dados[len(prefixo):]
            return prefixo + dados
        dpapi = patch.object(self.f.SEGURANCA, "_dpapi", dpapi_ficticia)
        dpapi.start()
        self.addCleanup(dpapi.stop)
        import auth
        self.auth = auth.Auth(str(self.s.ws))
        self.auth.auditar("ficticio", "127.0.0.1", "acao_ficticia")

    def test_restauracao_preserva_fontes_e_estado(self):
        antes = self.s.arquivos_fonte()
        db_antes = sha(self.s.db)
        bkp = self.f.criar_snapshot(self.s.ws, self.base / "destino-backup", offline=True, midia_protegida=True)
        manifesto = self.f.verificar_snapshot(bkp)
        self.assertEqual(manifesto["schema"], "cpj-backup/1")
        self.assertTrue(manifesto["arquivos"])
        self.assertIsNotNone(manifesto["auditoria"]["envelope"])

        # Fonte intacta: arquivos e banco principal não foram alterados pelo backup.
        self.assertEqual(self.s.arquivos_fonte(), antes)
        self.assertEqual(sha(self.s.db), db_antes)

        res = self.f.restaurar_snapshot(bkp, self.base / "restaurado", midia_protegida=True)
        self.assertEqual(res, self.base / "restaurado")
        rest = self.base / "restaurado"
        for rel, h in antes.items():
            self.assertEqual(sha(rest / rel), h, f"conteúdo divergente: {rel}")

        con = sqlite3.connect(rest / "config" / "plantao.sqlite")
        try:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 100)
        finally:
            con.close()
        import auth
        restaurada = auth.Auth(str(rest))
        self.assertTrue(restaurada.verificar_auditoria()["integra"])
        self.assertEqual(restaurada.verificar_auditoria()["registros_protegidos"], 1)
        vinculos = json.loads((rest / "casos/OS-0001-2026/02-analise/vinculos-manuais.json").read_text(encoding="utf-8"))
        self.assertEqual(vinculos[0]["id"], "vm-1")

    def test_backup_inclui_linhas_do_wal_e_nao_copia_wal_cru(self):
        self.assertTrue(Path(str(self.s.db) + "-wal").stat().st_size > 0)
        bkp = self.f.criar_snapshot(self.s.ws, self.base / "destino-backup", offline=True, midia_protegida=True)
        copia = bkp / "dados" / "config" / "plantao.sqlite"
        self.assertFalse((bkp / "dados" / "config" / "plantao.sqlite-wal").exists())
        self.assertFalse((bkp / "dados" / "config" / "plantao.sqlite-shm").exists())
        con = sqlite3.connect(copia)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 100)
        finally:
            con.close()

    def test_restauracao_nao_sobrescreve_trabalho_posterior(self):
        bkp = self.f.criar_snapshot(self.s.ws, self.base / "destino-backup", offline=True, midia_protegida=True)
        # Trabalho posterior ao backup, no próprio workspace vivo.
        relatorio = self.s.caso / "03-relatorios" / "RELATORIO-OS-0001-2026-v01.docx"
        relatorio.write_bytes(b"versao-posterior")
        novo = self.s.caso / "03-relatorios" / "RELATORIO-OS-0001-2026-v02.docx"
        novo.write_bytes(b"v02-criado-depois")
        self.s.con.execute("INSERT INTO pedidos(caso, estado) VALUES ('OS-0001-2026', 'posterior')")
        self.s.con.commit()
        (self.s.caso / "caso.json").unlink()  # recuperação ocorre somente em pasta nova

        posteriores = self.s.arquivos_fonte()
        with self.assertRaisesRegex(ValueError, "NOVA"):
            self.f.restaurar_snapshot(bkp, self.s.ws, midia_protegida=True)
        self.assertEqual(self.s.arquivos_fonte(), posteriores)

        self.assertEqual(relatorio.read_bytes(), b"versao-posterior")
        self.assertEqual(novo.read_bytes(), b"v02-criado-depois")
        self.assertFalse((self.s.caso / "caso.json").exists(), "recusa não pode escrever no workspace vivo")
        con = sqlite3.connect(self.s.db)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 101)
        finally:
            con.close()
        # Recuperação integral disponível numa pasta nova, sem mesclar o vivo.
        rest = self.f.restaurar_snapshot(bkp, self.base / "restaurado-separado", midia_protegida=True)
        self.assertTrue((rest / "casos/OS-0001-2026/caso.json").exists())
        self.assertFalse((rest / novo.relative_to(self.s.ws)).exists())
        self.assertNotEqual((rest / relatorio.relative_to(self.s.ws)).read_bytes(), b"versao-posterior")
        con = sqlite3.connect(rest / "config/plantao.sqlite")
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 100)
        finally:
            con.close()
        self.assertEqual(self.s.arquivos_fonte(), posteriores)

    def test_backup_adulterado_e_recusado_sem_escrever(self):
        bkp = self.f.criar_snapshot(self.s.ws, self.base / "destino-backup", offline=True, midia_protegida=True)
        alvo = bkp / "dados/casos/OS-0001-2026/caso.json"
        adulterado = bytearray(alvo.read_bytes())
        adulterado[-2] ^= 1  # mesmo tamanho: a detecção depende do hash
        alvo.write_bytes(adulterado)
        with self.assertRaisesRegex(ValueError, "integridade"):
            self.f.verificar_snapshot(bkp)
        destino = self.base / "restaurado-recusado"
        with self.assertRaisesRegex(ValueError, "integridade"):
            self.f.restaurar_snapshot(bkp, destino, midia_protegida=True)
        self.assertFalse(destino.exists())

    def test_backup_nao_sobrescreve_backup_anterior(self):
        a = self.f.criar_snapshot(self.s.ws, self.base / "destino-backup", offline=True, midia_protegida=True)
        b = self.f.criar_snapshot(self.s.ws, self.base / "destino-backup", offline=True, midia_protegida=True)
        self.assertNotEqual(a, b)
        self.assertTrue(a.exists() and b.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
