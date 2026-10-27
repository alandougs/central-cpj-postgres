"""SEC23: somente dados sintéticos e pastas temporárias; nenhuma IA real."""
import importlib.util
from contextlib import closing
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[2]
sys.path.insert(0, str(APP))
from tarefas import Tarefas, EXPORT_SCHEMA

SENHA = "ficticia-segura-2026"


class ExportacaoSegura(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cpj-sec23-")
        self.ws = Path(self.temp.name)
        self.t = Tarefas(str(self.ws), None, None, iniciar_agente=False)
        self.t.indexar = lambda: None  # indexador é subprocesso fora do contrato deste teste
        self.caso = self.ws / "casos/OS-9999-2099"
        self.caso.mkdir(parents=True)
        (self.caso / "caso.json").write_text('{"ficticio":true}', encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def exportar(self):
        tid = self.t.nova("exportacao", "Fictícia", "teste")
        return tid, self.t.exportar(tid, "completo", False, SENHA)

    def test_export_exige_senha_e_nao_deixa_zip_plaintext(self):
        tid = self.t.nova("exportacao", "Fictícia", "teste")
        with self.assertRaises(ValueError):
            self.t.exportar(tid, "completo", False, "curta")
        _, res = self.exportar()
        self.assertTrue(res["arquivo"].endswith(".cpjenc"))
        pacote = self.ws / "exportacoes" / res["arquivo"]
        self.assertFalse(zipfile.is_zipfile(pacote))
        self.assertNotIn(b'"ficticio":true', pacote.read_bytes())
        self.assertNotIn(SENHA, json.dumps(self.t.listar("teste")))
        self.assertFalse(list((self.ws / "exportacoes").glob("*.parcial")))

    def test_roundtrip_e_senha_errada_tamper_nao_gravam(self):
        _, res = self.exportar()
        conteudo = (self.ws / "exportacoes" / res["arquivo"]).read_bytes()
        destino = self.ws / "outro"
        destino.mkdir()
        t = Tarefas(str(destino), None, None, iniciar_agente=False)
        t.indexar = lambda: None
        for modo in ("senha", "tamper", "truncado", "correto"):
            p = destino / "entrada.cpjenc"
            b = bytearray(conteudo)
            if modo == "tamper": b[len(b)//2] ^= 1
            if modo == "truncado": b = b[:-1]
            p.write_bytes(b)
            tid = t.nova("importacao", "Fictícia", "teste")
            if modo == "correto":
                t.importar(tid, str(p), SENHA)
                self.assertEqual((destino / "casos/OS-9999-2099/caso.json").read_text(), '{"ficticio":true}')
            else:
                with self.assertRaises(ValueError): t.importar(tid, str(p), "senha-errada-123" if modo == "senha" else SENHA)
                self.assertFalse((destino / "casos").exists())
            self.assertFalse(p.exists())

    def legado(self, caminho="casos/OS-8888-2099/caso.json"):
        p = self.ws / "entrada.zip"
        b = b"{}"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("dados/" + caminho, b)
            z.writestr("manifest.json", json.dumps({"schema": EXPORT_SCHEMA, "arquivos": [{"caminho": caminho, "tamanho": 2, "sha256": hashlib.sha256(b).hexdigest()}]}))
        return p

    def test_legado_somente_com_aceite_e_traversal_continua_bloqueado(self):
        tid = self.t.nova("importacao", "Fictícia", "teste")
        with self.assertRaisesRegex(ValueError, "legado"):
            self.t.importar(tid, str(self.legado()))
        self.t.importar(tid, str(self.legado()), permitir_legado=True)
        self.assertTrue((self.ws / "casos/OS-8888-2099/caso.json").exists())
        with self.assertRaisesRegex(ValueError, "caminho"):
            self.t.importar(tid, str(self.legado("casos/../fora.txt")), permitir_legado=True)

    def test_cancelamento_remove_export_parcial(self):
        tid = self.t.nova("exportacao", "Fictícia", "teste")
        self.t.cancelar(tid)
        self.assertIsNone(self.t.exportar(tid, "completo", False, SENHA))
        self.assertFalse(list((self.ws / "exportacoes").glob("*.parcial")))
        self.assertFalse(list((self.ws / "exportacoes").glob("*.cpjenc")))

    def test_multiplos_blocos_e_cancelamento_durante_importacao(self):
        b = os.urandom(4 * 1024**2 + 123)
        (self.caso / "arquivo.pdf").write_bytes(b)
        _, res = self.exportar()
        conteudo = (self.ws / "exportacoes" / res["arquivo"]).read_bytes()
        destino = self.ws / "outro"; destino.mkdir()
        t = Tarefas(str(destino), None, None, iniciar_agente=False); t.indexar = lambda: None
        p = destino / "entrada.cpjenc"; p.write_bytes(conteudo)
        tid = t.nova("importacao", "Fictícia", "teste")
        at_original = t.at
        def at(tid, **kw):
            at_original(tid, **kw)
            if kw.get("etapa", "").startswith("preparando"): t.cancelar(tid)
        t.at = at
        self.assertIsNone(t.importar(tid, str(p), SENHA))
        self.assertFalse((destino / "casos").exists())
        self.assertFalse(list((destino / "exportacoes/_importando").glob("*")))
        p.write_bytes(conteudo); t.at = at_original
        t.importar(t.nova("importacao", "Fictícia", "teste"), str(p), SENHA)
        self.assertEqual((destino / "casos/OS-9999-2099/arquivo.pdf").read_bytes(), b)

    def test_reinicio_limpa_preparacao_orfa_preserva_ativa(self):
        base = self.ws / "exportacoes/_importando"
        orfa = base / ("4294967290-" + "a" * 12)
        ativa = base / (str(os.getpid()) + "-" + "b" * 12)
        for d in (orfa, ativa):
            d.mkdir(parents=True)
            (d / "ficticio.txt").write_text("preparação fictícia")
        Tarefas(str(self.ws), None, None, iniciar_agente=False)
        self.assertFalse(orfa.exists())
        self.assertTrue(ativa.exists())

    @unittest.skipUnless(os.name == "nt", "Junções NTFS são específicas do Windows")
    def test_export_import_bloqueiam_junction_raiz_e_intermediaria(self):
        fora = self.ws / "fora"; fora.mkdir()
        (fora / "segredo-ficticio.txt").write_text("nao exportar")
        for base in (self.ws / "referencias", self.caso / "intermediaria"):
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(base), str(fora)], capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            try:
                with self.assertRaisesRegex(ValueError, "link|junção|confin"):
                    self.exportar()
            finally: os.rmdir(base)
        base = self.ws / "referencias"
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(base), str(fora)], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        try:
            tid = self.t.nova("importacao", "Fictícia", "teste")
            with self.assertRaisesRegex(ValueError, "link|junção|confin"):
                self.t.importar(tid, str(self.legado("referencias/fora.txt")), permitir_legado=True)
            self.assertFalse((fora / "fora.txt").exists())
        finally: os.rmdir(base)


from fonte_interface import ler_interface
from teste_interface_rg26 import InterfaceFixtureRG26


class InterfaceSegura(unittest.TestCase):
    def test_falha_do_log_nao_oculta_diagnostico_integridade(self):
        import quickjs
        c = quickjs.Context()
        c.eval('''const mensagens=[];const el={innerHTML:"",append:p=>mensagens.push(p.textContent),prepend:p=>mensagens.push(p.textContent),insertAdjacentHTML:(onde,s)=>mensagens.push(s)};
            const $=()=>el;const document={createElement:()=>({setAttribute:()=>{},textContent:""})};const esc=s=>String(s);
            const api=async(url)=>{if(url.endsWith("/integridade"))return {integra:false};throw new Error("Leitura recusada por integridade")};''')
        html = ler_interface(APP / "static/index.html")
        if "async function carregarAuditoria()" in html:
            a = html.index("async function carregarAuditoria()")
            fonte = html[a:html.index("async function carregarSistema(", a)]
        else:
            a = html.index('   const au=await api("/api/auditoria")')
            fonte = "async function carregarAuditoria(){" + html[a:html.index('   const rd=', a)] + "}"
        c.eval(fonte)
        c.eval("carregarAuditoria().catch(()=>{})")
        while c.execute_pending_job(): pass
        self.assertIn("INTEGRIDADE DA AUDITORIA COMPROMETIDA", c.eval("mensagens.join(' ')").upper())

    def contexto(self):
        import quickjs
        c = quickjs.Context()
        c.eval('''const campos={};const chamadas=[];const avisos=[];let aceita=false;
          const $=s=>campos[s]||(campos[s]={value:"",checked:false,files:[]});
          const document={querySelector:()=>({value:"completo"})};
          const api=async(url,args)=>{chamadas.push({url,...args});return {}};
          const enviar=async(url,fd)=>{chamadas.push({url,form:fd.itens});return {}};
          class FormData{constructor(){this.itens={}}append(k,v){this.itens[k]=v}}
          const toast=m=>avisos.push(m);const atualizarTarefas=()=>{};
          const confirm=()=>aceita;''')
        html = ler_interface(APP / "static/index.html")
        for botao in ("b-exportar", "b-importar"):
            inicio = html.index('$("#' + botao + '").onclick=')
            fim = html.index('\n\n', inicio)
            # importação contém quebra no corpo: incluir até o próximo handler.
            if botao == "b-importar": fim = html.index('$("#b-bc").onclick', inicio)
            c.eval(html[inicio:fim])
        return c

    def executar(self, c, js):
        c.eval(js)
        while c.execute_pending_job(): pass

    def test_export_senha_validada_transmitida_e_campo_limpo(self):
        c = self.contexto()
        self.executar(c, '$("#exp-senha").value="curta";$("#b-exportar").onclick()')
        self.assertEqual(c.eval("chamadas.length"), 0)
        self.executar(c, '$("#exp-senha").value="ficticia-segura-2026";$("#b-exportar").onclick()')
        self.assertEqual(json.loads(c.eval("JSON.stringify(chamadas[0].json)")), {"modo": "completo", "incluir_modelo": False, "senha": SENHA})
        self.assertEqual(c.eval('$("#exp-senha").value'), "")

    def test_import_legado_exige_confirmacao_e_cifrado_senha(self):
        c = self.contexto()
        self.executar(c, '$("#imp-zip").files=[{name:"antigo.zip"}];$("#b-importar").onclick()')
        self.assertEqual(c.eval("chamadas.length"), 0)
        self.executar(c, 'aceita=true;$("#b-importar").onclick()')
        self.assertEqual(c.eval('chamadas[0].form.permitir_legado'), "true")
        self.executar(c, '$("#imp-zip").files=[{name:"novo.cpjenc"}];$("#b-importar").onclick()')
        self.assertEqual(c.eval("chamadas.length"), 1)
        self.executar(c, '$("#imp-senha").value="ficticia-segura-2026";$("#b-importar").onclick()')
        self.assertEqual(c.eval('chamadas[1].form.senha'), SENHA)
        self.assertEqual(c.eval('$("#imp-senha").value'), "")


class InterfaceSeguraServidor(InterfaceFixtureRG26):
    def test_modulos_servidos_preservam_senha_consentimento_e_limpeza(self):
        self.cenario(r'''
  await page.evaluate(()=>abrirAba('sistema'));
  await page.locator('#b-exportar').waitFor();
  const cargas=[];
  await page.route('**/api/exportar',async route=>{cargas.push(route.request().postDataJSON());await route.fulfill({json:{id:'ficticio'}})});
  await page.locator('#exp-senha').fill('ficticia-segura-2026');
  await page.locator('#b-exportar').click();
  await page.waitForFunction(()=>document.querySelector('#exp-senha').value==='');
  assert.equal(cargas.length,1);assert.equal(cargas[0].senha,'ficticia-segura-2026');
  let importacoes=0;
  await page.route('**/api/importar',async route=>{importacoes++;assert.ok(route.request().postData().includes('permitir_legado'));await route.fulfill({json:{id:'ficticio'}})});
  await page.locator('#imp-zip').setInputFiles({name:'legado.zip',mimeType:'application/zip',buffer:Buffer.from('ficticio')});
  page.once('dialog',dialog=>dialog.dismiss());
  await page.locator('#b-importar').click();assert.equal(importacoes,0);
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('#b-importar').click();
  await page.waitForFunction(()=>document.querySelector('#msg-imp').textContent.includes('Enviado'));
  assert.equal(importacoes,1);
''')


class BackupConsistente(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "ferramentas/backup_consistente.py"
        if not path.exists(): raise AssertionError("Backup consistente ainda não implementado")
        spec = importlib.util.spec_from_file_location("backup_sec23", path)
        cls.b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.b)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj-backup-sec23-")
        self.base = Path(self.tmp.name)
        self.ws = self.base / "fonte"
        (self.ws / "casos/OS-9999-2099").mkdir(parents=True)
        (self.ws / "casos/OS-9999-2099/caso.json").write_text("original fictício", encoding="utf-8")
        (self.ws / "config").mkdir()

    def tearDown(self): self.tmp.cleanup()

    def test_snapshot_wal_restauracao_apos_alteracao_exclusao_e_nao_sobrescreve(self):
        conn = sqlite3.connect(self.ws / "config/plantao.sqlite")
        self.addCleanup(conn.close)
        conn.execute("pragma journal_mode=wal")
        conn.execute("create table teste(valor text)")
        conn.execute("insert into teste values ('fictício WAL')")
        conn.commit()
        snap = self.b.criar_snapshot(self.ws, self.base / "midia", offline=True, midia_protegida=True)
        original = self.ws / "casos/OS-9999-2099/caso.json"
        original.write_text("mais novo")
        (self.ws / "config/outro.txt").write_text("novo")
        conn.close()
        (self.ws / "config/plantao.sqlite").unlink()
        restaurado = self.base / "restaurado"
        self.b.restaurar_snapshot(snap, restaurado, midia_protegida=True)
        self.assertEqual((restaurado / "casos/OS-9999-2099/caso.json").read_text(encoding="utf-8"), "original fictício")
        with closing(sqlite3.connect(restaurado / "config/plantao.sqlite")) as c:
            self.assertEqual(c.execute("select valor from teste").fetchone()[0], "fictício WAL")
        with self.assertRaises(ValueError): self.b.restaurar_snapshot(snap, self.ws, midia_protegida=True)
        self.assertEqual(original.read_text(), "mais novo")
        snap2 = self.b.criar_snapshot(self.ws, self.base / "midia", offline=True, midia_protegida=True)
        self.assertNotEqual(snap, snap2)
        self.assertTrue(Path(snap).exists())

    def test_backup_recusa_sem_offline_midia_protegida_e_fonte_em_mudanca(self):
        with self.assertRaises(ValueError): self.b.criar_snapshot(self.ws, self.base / "midia")
        with self.assertRaises(ValueError): self.b.criar_snapshot(self.ws, self.base / "midia", offline=True)
        original = self.b._inventario
        chamadas = 0
        def inventario(raiz):
            nonlocal chamadas
            chamadas += 1
            if chamadas == 2: (self.ws / "casos/OS-9999-2099/caso.json").write_text("mudou")
            return original(raiz)
        self.b._inventario = inventario
        try:
            with self.assertRaisesRegex(ValueError, "mudou"):
                self.b.criar_snapshot(self.ws, self.base / "midia", offline=True, midia_protegida=True)
        finally: self.b._inventario = original
        self.assertFalse(list((self.base / "midia").glob("CPJ-*")))

    @unittest.skipUnless(os.name == "nt", "Entrada BAT é específica do Windows")
    def test_bat_confirma_offline_midia_cancela_e_preserva_destino(self):
        bat = self.base / "Backup.bat"
        bat.write_bytes((ROOT / "ferramentas/Backup.bat").read_bytes())
        # A entrada real chama apenas este alvo sintético, sem executar backup.
        (self.base / "backup.ps1").write_text('param([string]$Destino,[switch]$Offline,[switch]$MidiaProtegida)\n'
            '@{destino=$Destino;offline=$Offline.IsPresent;protegida=$MidiaProtegida.IsPresent}|ConvertTo-Json|Set-Content -LiteralPath $env:CPJ_BACKUP_PROBE', encoding="utf-8")
        probe = self.base / "probe.json"
        destino = str(self.base / "destino & ' ficticio")
        env = dict(os.environ, CPJ_BACKUP_PROBE=str(probe))
        for entrada in ("\n", destino+"\nN\n", destino+"\nS\nN\n"):
            r = subprocess.run(["cmd", "/c", str(bat)], input=entrada, text=True, capture_output=True, env=env, timeout=15)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(probe.exists())
        r = subprocess.run(["cmd", "/c", str(bat)], input=destino+"\nS\nS\n\n", text=True, capture_output=True, env=env, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(probe.read_text()), {"destino": destino, "offline": True, "protegida": True})

    def test_restore_verifica_integridade_antes_de_publicar(self):
        snap = self.b.criar_snapshot(self.ws, self.base / "midia", offline=True, midia_protegida=True)
        (Path(snap) / "dados/casos/OS-9999-2099/caso.json").write_text("adulterado")
        destino = self.base / "restaurado"
        with self.assertRaises(ValueError): self.b.restaurar_snapshot(snap, destino, midia_protegida=True)
        self.assertFalse(destino.exists())

    def test_restauracao_preserva_auditoria_ancorada_fora_do_workspace(self):
        import auth
        import seguranca_local as S
        perfil = self.base / "perfil-privado"; perfil.mkdir()
        suporte_original = S.suporta_acl
        restaurado = self.base / "restaurado"
        def suporta(path):
            p = Path(path).resolve()
            if p == self.ws or self.ws in p.parents or p == restaurado or restaurado in p.parents: return False
            return suporte_original(path)
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(perfil)}), mock.patch.object(S, "suporta_acl", suporta):
            a = auth.Auth(str(self.ws))
            a.auditar("ficticio", "127.0.0.1", "acao_ficticia")
            self.assertTrue(a.verificar_auditoria()["integra"])
            self.assertFalse((self.ws / "config/auditoria.estado").exists())
            snap = self.b.criar_snapshot(self.ws, self.base / "midia", offline=True, midia_protegida=True)
            self.b.restaurar_snapshot(snap, restaurado, midia_protegida=True)
            novo = auth.Auth(str(restaurado))
            self.assertTrue(novo.verificar_auditoria()["integra"])
            novo.auditar("ficticio", "127.0.0.1", "apos_restauracao")
            self.assertEqual(novo.verificar_auditoria()["registros_protegidos"], 2)
            self.assertEqual(a.verificar_auditoria()["registros_protegidos"], 1)


if __name__ == "__main__": unittest.main(verbosity=2)
