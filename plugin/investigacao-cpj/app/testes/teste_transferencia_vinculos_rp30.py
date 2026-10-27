"""RP30: união validada de vínculos em pacotes; somente fixtures TEMP."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
import zipfile

APP = Path(__file__).resolve().parents[1]
BASE = APP.parent / 'skills/base-cpj/scripts'
sys.path[:0] = [str(APP), str(BASE)]
from tarefas import Tarefas, EXPORT_SCHEMA
import vinculos_manuais as VM


class TransferenciaVinculosRP30(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cpj-rp30-')
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name)
        self.t = Tarefas(str(self.ws), None, None, iniciar_agente=False)
        # O alvo é a confirmação do pacote, anterior ao subprocesso do índice.
        self.t.indexar = lambda: None
        self.dados = dict(caso='OS-930-2099', a_tipo='EMAIL', a_valor='a@example.invalid',
                          b_tipo='EMAIL', b_valor='b@example.invalid', relacao='vínculo fictício')

    def pacote(self, eventos, extras=None):
        arquivos = {'casos/OS-930-2099/caso.json': b'{"id":"OS-930-2099"}'}
        arquivos.update({'consulta/_grafo-manual/eventos/' + nome: conteudo for nome, conteudo in eventos.items()})
        arquivos.update(extras or {})
        path = self.ws / 'entrada-ficticia.zip'
        with zipfile.ZipFile(path, 'w') as z:
            for nome, conteudo in arquivos.items():
                z.writestr('dados/' + nome, conteudo)
            z.writestr('manifest.json', json.dumps({'schema': EXPORT_SCHEMA, 'arquivos': [
                {'caminho': n, 'tamanho': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
                for n, b in arquivos.items()]}))
        return path

    def importar(self, eventos):
        path = self.pacote(eventos)
        return self.t.importar(self.t.nova('importacao', 'Fictícia', 'teste'), str(path), permitir_legado=True)

    def test_mesmo_id_divergente_recusa_antes_de_confirmar_caso(self):
        VM.criar(self.ws, self.dados, 'investigador-ficticio')
        antes = VM.exportar_eventos(self.ws)
        nome, conteudo = next(iter(antes.items()))
        evento = json.loads(conteudo)
        evento['registro']['relacao'] = 'conteúdo divergente fictício'
        with self.assertRaises(VM.Conflito):
            self.importar({nome: json.dumps(evento).encode()})
        self.assertFalse((self.ws / 'casos/OS-930-2099').exists())
        self.assertEqual(VM.exportar_eventos(self.ws), antes)

    def test_evento_malformado_recusa_antes_de_confirmar_caso(self):
        with self.assertRaises(ValueError):
            self.importar({str(uuid.uuid4()) + '.json': b'{}'})
        self.assertFalse((self.ws / 'casos/OS-930-2099').exists())
        self.assertEqual(VM.exportar_eventos(self.ws), {})

    def test_historico_valido_e_reimportacao_preservam_vinculos(self):
        origem = self.ws / 'origem-ficticia'
        registro = VM.criar(origem, self.dados, 'investigador-ficticio')
        VM.atualizar(origem, registro['id'], {'relacao': 'revisado fictício'}, 'investigador-ficticio', 1)
        eventos = VM.exportar_eventos(origem)
        for _ in range(2):
            self.importar(eventos)
            self.assertEqual(VM.exportar_eventos(self.ws), eventos)
            self.assertEqual(VM.listar(self.ws)[0]['relacao'], 'revisado fictício')

    def test_exportacao_nao_inclui_arquivo_de_trava(self):
        VM.criar(self.ws, self.dados, 'investigador-ficticio')
        nomes = [r for _, r in self.t._lista_export('completo', False)]
        self.assertTrue(any('/eventos/' in r for r in nomes))
        self.assertFalse(any(r.endswith('/.vinculos.lock') for r in nomes))

    def test_historicos_divergentes_recusam_sem_apagar_revisao_local(self):
        origem = self.ws / 'origem-ficticia'
        registro = VM.criar(origem, self.dados, 'investigador-ficticio')
        VM.importar_eventos(self.ws, VM.exportar_eventos(origem))
        VM.atualizar(self.ws, registro['id'], {'relacao': 'revisão local'}, 'investigador-local', 1)
        VM.atualizar(origem, registro['id'], {'relacao': 'outra revisão'}, 'investigador-origem', 1)
        antes = VM.exportar_eventos(self.ws)
        with self.assertRaises(VM.Conflito):
            self.importar(VM.exportar_eventos(origem))
        self.assertEqual(VM.exportar_eventos(self.ws), antes)
        self.assertFalse((self.ws / 'casos/OS-930-2099').exists())

    def test_pacote_cifrado_transporta_historico_completo(self):
        registro = VM.criar(self.ws, self.dados, 'investigador-ficticio')
        VM.atualizar(self.ws, registro['id'], {'relacao': 'revisão fictícia'}, 'investigador-ficticio', 1)
        senha = 'senha-ficticia-rp30-2099'
        exportado = self.t.exportar(self.t.nova('exportacao', 'Fictícia', 'teste'), 'completo', False, senha)
        pacote = self.ws / 'exportacoes' / exportado['arquivo']
        destino = self.ws / 'destino-ficticio'
        destino.mkdir()
        t = Tarefas(str(destino), None, None, iniciar_agente=False)
        t.indexar = lambda: None
        entrada = destino / 'entrada.cpjenc'
        entrada.write_bytes(pacote.read_bytes())
        t.importar(t.nova('importacao', 'Fictícia', 'teste'), str(entrada), senha)
        self.assertEqual(VM.exportar_eventos(destino), VM.exportar_eventos(self.ws))

    def test_arquivo_na_raiz_reservada_nao_bloqueia_diretorio_dos_vinculos(self):
        for caminho in ('consulta/_grafo-manual', 'consulta/_GRAFO-MANUAL', 'consulta/_grafo-manual. '):
            with self.subTest(caminho=caminho):
                pacote = self.pacote({}, {caminho: b'arquivo ficticio'})
                with self.assertRaises(ValueError):
                    self.t.importar(self.t.nova('importacao', 'Fictícia', 'teste'), str(pacote), permitir_legado=True)
                self.assertFalse((self.ws / 'casos/OS-930-2099').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
