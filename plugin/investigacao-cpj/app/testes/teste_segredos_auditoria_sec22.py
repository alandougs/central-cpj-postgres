"""SEC22: segredos e evidência de adulteração, somente dados sintéticos."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auth


class SegredosAuditoria(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-sec22-")
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        self.cfg = self.ws / "config" / "chaves_llm.json"
        self.cfg.parent.mkdir()
        self.dados = {"openai": {"chave": "SEGREDO-SINTETICO-SEC22", "modelo": "ficticio", "ativo": True}}

    def test_salvar_e_carregar_sem_plaintext(self):
        import seguranca_local as S
        S.salvar_cfg_llm(self.cfg, self.dados)
        self.assertNotIn("SEGREDO-SINTETICO-SEC22", self.cfg.read_text())
        self.assertEqual(S.carregar_cfg_llm(self.cfg), self.dados)

    def test_migrar_legado_sem_perder_modelo_ou_segredo(self):
        import seguranca_local as S
        self.cfg.write_text(json.dumps(self.dados))
        self.assertEqual(S.carregar_cfg_llm(self.cfg), self.dados)
        self.assertNotIn("SEGREDO-SINTETICO-SEC22", self.cfg.read_text())

    def test_falha_protecao_preserva_legado_e_nao_expoe_segredo(self):
        import seguranca_local as S
        original = json.dumps(self.dados)
        self.cfg.write_text(original)
        with patch.object(S, "proteger", side_effect=OSError("falha")):
            with self.assertRaises(S.SegurancaLocalErro) as erro:
                S.carregar_cfg_llm(self.cfg)
        self.assertEqual(self.cfg.read_text(), original)
        self.assertNotIn("SEGREDO", str(erro.exception))

    def test_envelope_corrompido_bloqueia_sem_regravar(self):
        import seguranca_local as S
        S.salvar_cfg_llm(self.cfg, self.dados)
        raw = json.loads(self.cfg.read_text())
        raw["openai"]["chave"]["dados"] = "invalido"
        self.cfg.write_text(json.dumps(raw))
        with self.assertRaises(S.SegurancaLocalErro): S.carregar_cfg_llm(self.cfg)

    def test_auditoria_compativel_e_verificada(self):
        a = auth.Auth(self.ws)
        a.auditar("ficticio", "local", "teste", "OS-1-2099")
        self.assertEqual(a.auditoria()[0]["acao"], "teste")
        self.assertTrue(a.verificar_auditoria()["integra"])

    def test_edicao_truncamento_e_remocao_detectados(self):
        for ataque in ("editar", "truncar", "remover"):
            with self.subTest(ataque=ataque), tempfile.TemporaryDirectory(prefix="cpj-sec22-audit-") as ws:
                a = auth.Auth(ws)
                a.auditar("ficticio", "local", "primeiro")
                a.auditar("ficticio", "local", "segundo")
                p = Path(a.log)
                if ataque == "editar": p.write_text(p.read_text().replace("primeiro", "alterado"))
                elif ataque == "truncar": p.write_text(p.read_text().splitlines()[0] + "\n")
                else: p.unlink()
                self.assertFalse(a.verificar_auditoria()["integra"])
                with self.assertRaises(RuntimeError): a.auditar("ficticio", "local", "nao_reancorar")

    def test_legado_preservado_e_sinalizado(self):
        a = auth.Auth(self.ws)
        legado = b'{"acao":"legado","usuario":"ficticio"}\n'
        Path(a.log).write_bytes(legado)
        a.auditar("ficticio", "local", "novo")
        self.assertTrue(Path(a.log).read_bytes().startswith(legado))
        estado = a.verificar_auditoria()
        self.assertTrue(estado["integra"])
        self.assertTrue(estado["legado_sem_assinatura"])
        self.assertEqual(len(a.auditoria()), 2)

    def test_ancora_removida_nao_reinicia_cadeia(self):
        a = auth.Auth(self.ws)
        a.auditar("ficticio", "local", "teste")
        (self.cfg.parent / "auditoria.estado").unlink()
        self.assertFalse(a.verificar_auditoria()["integra"])
        with self.assertRaises(RuntimeError): a.auditar("ficticio", "local", "novo")

    def test_sem_acl_ancora_fica_em_perfil_seguro_e_cifra_permanece_local(self):
        import seguranca_local as S
        perfil = self.ws / "perfil-sintetico"
        # Simula só o volume de dados sem ACL; o perfil continua no NTFS real.
        def acl(caminho):
            return str(caminho).startswith(str(perfil))
        with patch.object(S, "suporta_acl", side_effect=acl), patch.dict(os.environ, {"LOCALAPPDATA": str(perfil)}):
            S.salvar_cfg_llm(self.cfg, self.dados)
            self.assertEqual(S.carregar_cfg_llm(self.cfg), self.dados)
            a = auth.Auth(self.ws)
            a.auditar("ficticio", "local", "teste")
            ancora = S.caminho_ancora_auditoria(self.ws)
            self.assertTrue(str(ancora).startswith(str(perfil)))
            self.assertFalse((self.cfg.parent / "auditoria.estado").exists())
            self.assertTrue(a.verificar_auditoria()["integra"])
            Path(a.log).write_text("")
            self.assertFalse(a.verificar_auditoria()["integra"])

    @unittest.skipUnless(os.name == "nt", "Ensaio específico dos volumes Windows")
    def test_volume_sem_acl_real_com_perfil_sintetico_ntfs(self):
        import seguranca_local as S
        exigir = (
            os.environ.get("CPJ_SEC22_EXIGIR_VOLUME_SEM_ACL") == "1"
            or os.environ.get("CPJ_SEC22_REQUIRE_VOLUME") == "1"
        )
        volume_env = (
            os.environ.get("CPJ_SEC22_VOLUME_SEM_ACL_DIR")
            or os.environ.get("CPJ_SEC22_VOLUME_DIR")
            or ""
        ).strip()
        perfil_env = (
            os.environ.get("CPJ_SEC22_PERFIL_NTFS_DIR")
            or os.environ.get("CPJ_SEC22_PROFILE_DIR")
            or ""
        ).strip()
        if volume_env:
            volume = Path(volume_env)
            self.assertTrue(volume.is_dir(), f"Fixture explícita de volume sem ACL não é diretório existente: {volume}")
            self.assertFalse(S.suporta_acl(volume), f"Fixture explícita precisa estar em volume sem ACL: {volume}")
        else:
            if exigir:
                self.fail("Fixture obrigatória CPJ_SEC22_VOLUME_SEM_ACL_DIR / CPJ_SEC22_VOLUME_DIR não informada.")
            if S.suporta_acl(self.ws):
                self.skipTest("Volume do código possui ACL; exFAT não disponível")
            volume = self.ws
        if perfil_env:
            perfil_base = Path(perfil_env)
            self.assertTrue(perfil_base.is_dir(), f"Perfil explícito não é diretório existente: {perfil_base}")
            self.assertTrue(S.suporta_acl(perfil_base), f"Perfil explícito exige volume com ACL: {perfil_base}")
            perfil = perfil_base / "perfil"
        else:
            self.assertTrue(S.suporta_acl(self.ws), "Perfil sintético exige volume com ACL.")
            perfil = self.ws / "perfil"
        perfil.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="cpj-sec22-volume-", dir=volume) as ws, \
             patch.dict(os.environ, {"LOCALAPPDATA": str(perfil)}):
            cfg = Path(ws) / "config" / "chaves_llm.json"
            S.salvar_cfg_llm(cfg, self.dados)
            self.assertFalse(S.restringir_arquivo(cfg))
            self.assertNotIn("SEGREDO-SINTETICO-SEC22", cfg.read_text())
            self.assertEqual(S.carregar_cfg_llm(cfg), self.dados)
            a = auth.Auth(ws)
            a.auditar("ficticio", "local", "volume_sem_acl")
            self.assertTrue(a.verificar_auditoria()["integra"])
            self.assertFalse((Path(ws) / "config" / "auditoria.estado").exists())
            self.assertTrue(str(S.caminho_ancora_auditoria(ws)).startswith(str(perfil)))

    def test_snapshot_remapeia_ancora_preserva_historico_e_continua(self):
        import seguranca_local as S
        a = auth.Auth(self.ws)
        a.auditar("ficticio", "local", "origem")
        estado = S.exportar_estado_auditoria(self.ws)
        self.assertNotIn('"chave"', json.dumps(estado))
        with tempfile.TemporaryDirectory(prefix="cpj-sec22-restaurado-") as destino:
            b = auth.Auth(destino)
            Path(b.log).write_bytes(Path(a.log).read_bytes())
            S.restaurar_estado_auditoria(destino, estado)
            self.assertTrue(b.verificar_auditoria()["integra"])
            b.auditar("ficticio", "local", "restaurado")
            self.assertEqual([x["acao"] for x in b.auditoria()], ["restaurado", "origem"])
            self.assertEqual(a.verificar_auditoria()["registros_protegidos"], 1)

    def test_snapshot_nao_substitui_ancora_existente_divergente(self):
        import seguranca_local as S
        a = auth.Auth(self.ws)
        a.auditar("ficticio", "local", "origem")
        estado = S.exportar_estado_auditoria(self.ws)
        a.auditar("ficticio", "local", "posterior")
        with self.assertRaises(S.SegurancaLocalErro): S.restaurar_estado_auditoria(self.ws, estado)
        self.assertTrue(a.verificar_auditoria()["integra"])

    def test_snapshot_falha_outra_conta_sem_criar_ancora(self):
        import seguranca_local as S
        a = auth.Auth(self.ws); a.auditar("ficticio", "local", "origem")
        estado = S.exportar_estado_auditoria(self.ws)
        with tempfile.TemporaryDirectory(prefix="cpj-sec22-outra-conta-") as destino:
            b = auth.Auth(destino); Path(b.log).write_bytes(Path(a.log).read_bytes())
            with patch.object(S, "desproteger", side_effect=S.SegurancaLocalErro("outra conta")):
                with self.assertRaises(S.SegurancaLocalErro): S.restaurar_estado_auditoria(destino, estado)
            self.assertFalse(S.caminho_ancora_auditoria(destino).exists())

    def test_processos_concorrentes_preservam_cadeia(self):
        app = str(Path(__file__).resolve().parents[1])
        script = ("import sys;sys.path.insert(0,sys.argv[1]);import auth;"
                  "a=auth.Auth(sys.argv[2]);"
                  "[a.auditar(sys.argv[3],'local','concorrente',str(i)) for i in range(25)]")
        processos = [subprocess.Popen([sys.executable, "-c", script, app, str(self.ws), nome],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE) for nome in ("a", "b")]
        resultados = [(p, p.communicate(timeout=40)) for p in processos]
        for p, (_, erro) in resultados:
            self.assertEqual(p.returncode, 0, erro.decode(errors="replace"))
        a = auth.Auth(self.ws)
        self.assertTrue(a.verificar_auditoria()["integra"])
        self.assertEqual(a.verificar_auditoria()["registros_protegidos"], 50)
        self.assertEqual({x["usuario"] for x in a.auditoria()}, {"a", "b"})


if __name__ == "__main__": unittest.main()
