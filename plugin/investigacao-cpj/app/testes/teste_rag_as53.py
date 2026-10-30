#!/usr/bin/env python3
"""AS53: regressões do RAG em Markdown/SQLite fictícios, sem modelo ou rede."""
from contextlib import closing
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "plugin/investigacao-cpj/skills/base-cpj/scripts"
TEM_NUMPY = importlib.util.find_spec("numpy") is not None


def indexar(ws):
    env = dict(os.environ, CPJ_WORKSPACE=str(ws), CPJ_SEM_AGENTE_EMBUTIDO="1",
               PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-B", str(BASE / "indexar.py"),
                        "--sem-baixa"], cwd=ws, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)


def criar_caso(ws, numero, texto, encoding="utf-8"):
    caso = ws / "casos" / f"OS-{numero}-2099"
    doc = caso / "01-extracao/autos-sinteticos"
    doc.mkdir(parents=True)
    (doc / "transcricao.md").write_text(texto, encoding=encoding)
    (caso / "caso.json").write_text(json.dumps({
        "id": caso.name, "status": "analisado", "ordem_servico": f"{numero}/2099",
    }), encoding="utf-8")
    return caso


class RagAS53(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="cpj-rag-as53-")
        self.addCleanup(temp.cleanup)
        self.ws = Path(temp.name)
        (self.ws / "modelos").mkdir()
        self.env = patch.dict(os.environ, CPJ_WORKSPACE=str(self.ws),
                              CPJ_SEM_AGENTE_EMBUTIDO="1")
        self.env.start()
        self.addCleanup(self.env.stop)
        spec = importlib.util.spec_from_file_location("rag_as53", BASE / "rag.py")
        self.rag = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rag)
        self.addCleanup(self.fechar_cache)

    def fechar_cache(self):
        conexao = self.rag._CACHE.get("sentinela")
        if conexao is not None:
            conexao.close()

    def test_markdown_bom_preserva_primeira_pagina_folha_e_identificador(self):
        # Ler como UTF-8 puro faz o BOM impedir ambos os parsers de reconhecer ## Página.
        caso = criar_caso(self.ws, 9531,
                          "## Página 4\nFls. 30\nmarcadorbomas53 CPF 00000000191.\n\n"
                          "## Página 8\nFls. 42\nSegunda página sintética.\n",
                          encoding="utf-8-sig")
        antes = {p: p.read_bytes() for p in caso.rglob("*") if p.is_file()}
        indexar(self.ws)
        res, aviso = self.rag.buscar("marcadorbomas53", modo="lexical")
        self.assertEqual(len(res), 1, "a primeira página do Markdown com BOM sumiu do FTS")
        self.assertEqual((res[0]["caso"], res[0]["pagina"], res[0]["fls"]),
                         ("OS-9531-2099", 4, "30"))
        self.assertIsNone(aviso)
        ents = self.rag.entidade("00000000191", tipo="CPF")
        self.assertEqual([(r["caso"], r["pagina"]) for r in ents], [("OS-9531-2099", 4)])
        self.assertEqual({p: p.read_bytes() for p in antes}, antes)
        self.assertEqual(list(caso.rglob("*.csv")), [])
        self.assertEqual(list(caso.rglob("*.json")), [caso / "caso.json"])

    def test_indice_legado_repara_so_bom_uma_vez_sem_reindexacao_total(self):
        afetado = criar_caso(self.ws, 9539,
                            "## Página 4\nFls. 34\nreparobomas53 CPF 00000000191.\n\n"
                            "## Página 8\nFls. 38\nSegunda página do documento legado.\n",
                            encoding="utf-8-sig")
        normal = criar_caso(self.ws, 9540, "## Página 6\nFls. 36\nnormalpreservadoas53.\n")
        metadados = {p: (p / "caso.json").read_bytes() for p in (afetado, normal)}
        # Reproduz a leitura antiga e seu índice sem coluna de versão, em processo isolado.
        codigo = '''
import builtins, runpy, sys
script = sys.argv[1]
original = builtins.open
def abrir_legado(arquivo, *args, **kwargs):
    if str(arquivo).endswith('transcricao.md') and kwargs.get('encoding') == 'utf-8-sig':
        kwargs['encoding'] = 'utf-8'
    return original(arquivo, *args, **kwargs)
builtins.open = abrir_legado
sys.argv = [script, '--sem-baixa']
runpy.run_path(script, run_name='__main__')
'''
        r = subprocess.run([sys.executable, "-B", "-c", codigo, str(BASE / "indexar.py")],
                           cwd=self.ws, env=dict(os.environ, CPJ_WORKSPACE=str(self.ws),
                               PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8"),
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        vetor = struct.pack("<384f", 1.0, *([0.0] * 383))
        with closing(sqlite3.connect(self.rag.DB)) as db:
            db.executescript("""
                CREATE TABLE docs_legados(arquivo TEXT PRIMARY KEY, caso TEXT, tipo TEXT, sha TEXT, indexado_em TEXT);
                INSERT INTO docs_legados SELECT arquivo, caso, tipo, sha, indexado_em FROM docs;
                DROP TABLE docs;
                ALTER TABLE docs_legados RENAME TO docs;
            """)
            db.execute("UPDATE trechos SET embedding=?", (vetor,))
            db.commit()
            normal_antes = db.execute("SELECT id, arquivo, texto, embedding FROM trechos WHERE caso='OS-9540-2099'").fetchall()
            doc_normal_antes = db.execute("SELECT * FROM docs WHERE caso='OS-9540-2099'").fetchall()
        self.assertEqual(self.rag.buscar("reparobomas53", modo="lexical")[0], [])

        indexar(self.ws)  # Sem --tudo: SHA cru do Markdown continua igual.
        res, _ = self.rag.buscar("reparobomas53", modo="lexical")
        self.assertEqual([(t["pagina"], t["fls"]) for t in res], [(4, "34")])
        self.assertEqual([(e["caso"], e["pagina"]) for e in self.rag.entidade("00000000191", tipo="CPF")],
                         [("OS-9539-2099", 4)])
        with closing(sqlite3.connect(self.rag.DB)) as db:
            self.assertEqual(db.execute("SELECT id, arquivo, texto, embedding FROM trechos WHERE caso='OS-9540-2099'").fetchall(), normal_antes)
            self.assertEqual(db.execute("SELECT arquivo, caso, tipo, sha, indexado_em FROM docs WHERE caso='OS-9540-2099'").fetchall(), doc_normal_antes)
            bruto = (afetado / "01-extracao/autos-sinteticos/transcricao.md").read_bytes()
            self.assertEqual(db.execute("SELECT sha FROM docs WHERE caso='OS-9539-2099'").fetchone()[0], hashlib.sha256(bruto).hexdigest())
            # Um vetor gerado depois do reparo deve sobreviver à próxima indexação normal.
            db.execute("UPDATE trechos SET embedding=?", (vetor,))
            db.commit()
            reparado = db.execute("SELECT id, arquivo, texto, embedding FROM trechos ORDER BY id").fetchall()
        indexar(self.ws)
        with closing(sqlite3.connect(self.rag.DB)) as db:
            self.assertEqual(db.execute("SELECT id, arquivo, texto, embedding FROM trechos ORDER BY id").fetchall(), reparado)
        self.assertEqual({p: (p / "caso.json").read_bytes() for p in metadados}, metadados)

    def test_dependencia_opcional_ausente_preserva_fts_sem_carregar_modelo(self):
        criar_caso(self.ws, 9535, "## Página 6\nFls. 36\nMarcador lexicalas53.\n")
        indexar(self.ws)
        with closing(sqlite3.connect(self.rag.DB)) as db:
            db.execute("UPDATE trechos SET embedding=?", (bytes(1536),))
            db.commit()

        class SemDependencias:
            disponivel = staticmethod(lambda: False)

            @staticmethod
            def vetor(texto):
                raise AssertionError("não pode carregar modelo sem dependência opcional")

        with patch.object(self.rag, "_modulo_embeddings", return_value=SemDependencias):
            for modo in ("auto", "hibrido"):
                res, _ = self.rag.buscar("lexicalas53", modo=modo)
                self.assertEqual([(r["caso"], r["pagina"]) for r in res], [("OS-9535-2099", 6)])
            res, aviso = self.rag.buscar("lexicalas53", modo="semantico")
            self.assertEqual(res, [])
            self.assertIn("fastembed/numpy", aviso)

    def encoder_sintetico(self):
        import numpy as np

        class Encoder:
            DIM = 384
            disponivel = staticmethod(lambda: True)
            modelo_em_cache = staticmethod(lambda: True)
            desempacotar = staticmethod(lambda b: np.frombuffer(b, dtype="float32"))
            vetor = staticmethod(lambda texto: np.array([1.0] + [0.0] * 383, dtype="float32").tobytes())

        return Encoder

    @unittest.skipUnless(TEM_NUMPY, "fastembed/numpy ausentes no ambiente")
    def test_hibrida_funde_sem_duplicar_e_respeita_filtros_e_proveniencia(self):
        import numpy as np
        caso = criar_caso(self.ws, 9536,
                          "## Página 1\nFls. 11\nÂncoraas53 documento lexical.\n\n"
                          "## Página 2\nFls. 12\nRemessa sintética de valores [dígito incerto].\n\n"
                          "## Página 3\nFls. 13\nÂncoraas53 registro que coincide nos dois caminhos.\n")
        meta = caso / "caso.json"
        dados = json.loads(meta.read_text(encoding="utf-8"))
        dados["modalidade"] = "as53-a"
        meta.write_text(json.dumps(dados), encoding="utf-8")
        criar_caso(self.ws, 9537, "## Página 5\nFls. 25\nÂncoraas53 outro caso sintético.\n")
        (caso / "02-analise").mkdir()
        (caso / "02-analise/exemplo.md").write_text("# Análise\nÂncoraas53 análise sintética.\n", encoding="utf-8")
        indexar(self.ws)
        with closing(sqlite3.connect(self.rag.DB)) as db:
            for pagina, a, b in ((1, 0.0, 1.0), (2, 1.0, 0.0), (3, 0.8, 0.6), (5, 1.0, 0.0), (None, 1.0, 0.0)):
                blob = np.array([a, b] + [0.0] * 382, dtype="float32").tobytes()
                db.execute("UPDATE trechos SET embedding=? WHERE pagina IS ?", (blob, pagina))
            db.commit()
        with patch.object(self.rag, "_modulo_embeddings", return_value=self.encoder_sintetico()):
            # Aquece a matriz global; o recorte posterior não pode reaproveitá-la sem filtros.
            self.rag.buscar("âncoraas53", modo="hibrido")
            res, aviso = self.rag.buscar("âncoraas53", modo="hibrido", caso="OS-9536-2099",
                                        tipo="transcricao", modalidade="as53-a")
            self.assertEqual(res[0]["pagina"], 3, "acerto nas duas listas deve receber os dois postos RRF")
            self.assertEqual(sorted(r["pagina"] for r in res), [1, 2, 3])
            self.assertEqual({r["caso"] for r in res}, {"OS-9536-2099"})
            self.assertEqual({r["tipo"] for r in res}, {"transcricao"})
            self.assertIn("proximidade de sentido", aviso)
            por_pagina = {r["pagina"]: r for r in res}
            self.assertEqual(por_pagina[2]["fls"], "12")
            self.assertIn("[dígito incerto]", por_pagina[2]["trecho"])
            self.assertEqual(por_pagina[2]["marcas"], [])
            self.assertTrue(por_pagina[1]["marcas"])
            vazio, _ = self.rag.buscar("âncoraas53", modo="hibrido", caso="OS-9536-2099", modalidade="as53-b")
            self.assertEqual(vazio, [])

    @unittest.skipUnless(TEM_NUMPY, "fastembed/numpy ausentes no ambiente")
    def test_reindexar_descarta_vetor_antigo_sem_alterar_caso_ou_servir_cache_velho(self):
        import numpy as np
        caso = criar_caso(self.ws, 9538, "## Página 2\nFls. 22\nTexto original sintético.\n")
        meta_antes = (caso / "caso.json").read_bytes()
        indexar(self.ws)
        blob = np.array([1.0] + [0.0] * 383, dtype="float32").tobytes()
        with closing(sqlite3.connect(self.rag.DB)) as db:
            db.execute("UPDATE trechos SET embedding=?", (blob,))
            db.commit()
        with patch.object(self.rag, "_modulo_embeddings", return_value=self.encoder_sintetico()):
            antes, _ = self.rag.buscar("consulta sintética", modo="semantico")
            self.assertEqual([r["pagina"] for r in antes], [2])
            indexar(self.ws)  # Sem mudança no arquivo, mantém o vetor gerado.
            igual, _ = self.rag.buscar("consulta sintética", modo="semantico")
            self.assertEqual(igual, antes)
            doc = caso / "01-extracao/autos-sinteticos/transcricao.md"
            doc.write_text("## Página 9\nFls. 39\nTexto novo marcadoratualas53.\n", encoding="utf-8")
            indexar(self.ws)
            semantico, aviso = self.rag.buscar("consulta sintética", modo="semantico")
            self.assertEqual(semantico, [], "vetor da versão anterior não pode casar com o texto novo")
            self.assertIn("não tem vetores", aviso)
            lexical, _ = self.rag.buscar("marcadoratualas53", modo="auto")
            self.assertEqual([(r["pagina"], r["fls"]) for r in lexical], [(9, "39")])
            self.assertEqual((caso / "caso.json").read_bytes(), meta_antes)

    @unittest.skipUnless(TEM_NUMPY, "fastembed/numpy ausentes no ambiente")
    def test_encoder_opcional_falha_sem_derrubar_busca_textual(self):
        # O encoder é a única dependência substituída; FTS, matriz e banco são reais.
        import numpy as np
        criar_caso(self.ws, 9532, "## Página 7\nFls. 57\nTransferência bancária sintética.\n")
        indexar(self.ws)
        blob = np.array([1.0] + [0.0] * 383, dtype="float32").tobytes()
        with closing(sqlite3.connect(self.rag.DB)) as db:
            db.execute("UPDATE trechos SET embedding=?", (blob,))
            db.commit()

        class EncoderIndisponivel:
            DIM = 384
            disponivel = staticmethod(lambda: True)
            modelo_em_cache = staticmethod(lambda: True)
            desempacotar = staticmethod(lambda b: np.frombuffer(b, dtype="float32"))

            @staticmethod
            def vetor(texto):
                raise RuntimeError("Modelo sintético ilegível; não há download neste teste.")

        with patch.object(self.rag, "_modulo_embeddings", return_value=EncoderIndisponivel):
            for modo in ("auto", "hibrido"):
                with self.subTest(modo=modo):
                    try:
                        res, aviso = self.rag.buscar("transferência bancária", modo=modo)
                    except RuntimeError as erro:
                        self.fail(f"encoder opcional derrubou busca {modo}: {erro}")
                    self.assertEqual([(r["caso"], r["pagina"]) for r in res],
                                     [("OS-9532-2099", 7)])
                    self.assertIsNotNone(aviso, "falha da parte semântica ficou silenciosa")
                    self.assertIn("falha", aviso)
                    self.assertIn("busca textual", aviso)
                with self.subTest(modo=modo, acerto_lexical=False):
                    res, aviso = self.rag.buscar("termoinexistenteas53", modo=modo)
                    self.assertEqual(res, [])
                    self.assertIsNotNone(aviso, "falha semântica pareceu ausência de documento")
                    self.assertIn("falha", aviso)
                    self.assertIn("busca textual", aviso)
            try:
                res, aviso = self.rag.buscar("transferência bancária", modo="semantico")
            except RuntimeError as erro:
                self.fail(f"busca semântica não informou indisponibilidade: {erro}")
            self.assertEqual(res, [])
            self.assertIn("Busca semântica indisponível", aviso)


class BuscaAPICASOAS53(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cpj-busca-api-as53-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.ws = Path(cls.temp.name)
        cls.env = patch.dict(os.environ, CPJ_WORKSPACE=str(cls.ws),
                             CPJ_SEM_AGENTE_EMBUTIDO="1")
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        (cls.ws / "modelos").mkdir()
        for numero, pagina in ((9533, 3), (9534, 9)):
            criar_caso(cls.ws, numero,
                       f"## Página {pagina}\nFls. {pagina + 20}\nCPF sintético 00000000191.\n")
        indexar(cls.ws)
        sys.path.insert(0, str(ROOT / "plugin/investigacao-cpj/app"))
        import servidor
        cls.s = servidor
        assert Path(servidor.WS).resolve() == cls.ws.resolve(), "Execute em processo isolado."
        cls.s.app.config.update(TESTING=True)
        cls.addClassCleanup(cls.fechar_cache)

    @classmethod
    def fechar_cache(cls):
        conexao = cls.s.R._CACHE.get("sentinela")
        if conexao is not None:
            conexao.close()

    def setUp(self):
        self.cliente = self.s.app.test_client()
        auth = patch("rotas.comum.usuario", return_value={"login": "ficticio", "perfil": "investigador"})
        auth.start()
        self.addCleanup(auth.stop)

    def test_caso_restringe_trechos_e_entidades_do_mesmo_identificador(self):
        r = self.cliente.get("/api/busca", query_string={"q": "00000000191", "caso": "OS-9533-2099"})
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual({t["caso"] for t in j["trechos"]}, {"OS-9533-2099"})
        self.assertEqual({e["caso"] for e in j["entidades"]}, {"OS-9533-2099"})

    def test_caso_sem_acerto_nao_devolve_entidade_de_outro_caso(self):
        r = self.cliente.get("/api/busca", query_string={"q": "00000000191", "caso": "OS-0000-2099"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["trechos"], [])
        self.assertEqual(r.get_json()["entidades"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
