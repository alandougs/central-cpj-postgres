"""Dispensa de falha encerrada, em workspace integralmente fictício."""
import json
import unittest
from unittest.mock import patch

from astra_fixture import AstraFixture


class DispensaFila(AstraFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.proc = self.ws / 'casos' / self.caso / 'processamento.json'
        self.tentativa = {
            'doc': 'autos-ficticios', 'arquivo': 'autos-ficticios.pdf',
            'status': 'erro', 'etapa': 'extração', 'erro': 'falha fictícia',
            'enfileirado': '2099-01-01T10:00:00', 'fim': '2099-01-01T10:05:00',
            'progresso': 25, 'usuario': 'astra_ficticio',
        }
        self.proc.write_text(json.dumps({'trabalhos': [self.tentativa]}), encoding='utf-8')
        self.endpoint = f'/api/casos/{self.caso}/processamento/dispensar'
        self.identidade = {k: self.tentativa[k] for k in ('doc', 'enfileirado', 'fim')}

    def ler(self):
        return json.loads(self.proc.read_text(encoding='utf-8'))['trabalhos'][0]

    def test_dispensa_persistente_idempotente_preserva_dados(self):
        self.assertEqual(len(self.client.get('/api/fila').get_json()['trabalhos']), 1)
        r = self.post(self.endpoint, self.identidade)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['ja_dispensado'])
        registro = self.ler()
        self.assertEqual({k: registro[k] for k in self.tentativa}, self.tentativa)
        self.assertEqual(registro['dispensa']['usuario'], 'astra_ficticio')
        self.assertEqual(self.client.get('/api/fila').get_json()['trabalhos'], [])
        r = self.post(self.endpoint, self.identidade)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()['ja_dispensado'])
        self.assertEqual(self.ler(), registro)
        self.assertEqual(self.client.get('/api/fila').get_json()['trabalhos'], [])

    def test_recusa_ativa_e_identidade_alterada_sem_modificar(self):
        t = dict(self.tentativa, status='processando')
        self.proc.write_text(json.dumps({'trabalhos': [t]}), encoding='utf-8')
        self.assertEqual(self.post(self.endpoint, self.identidade).status_code, 409)
        self.assertEqual(self.ler(), t)
        t.update(status='erro', enfileirado='2099-01-01T10:10:00')
        self.proc.write_text(json.dumps({'trabalhos': [t]}), encoding='utf-8')
        self.assertEqual(self.post(self.endpoint, self.identidade).status_code, 409)
        self.assertEqual(self.ler(), t)
        self.assertEqual(len(self.client.get('/api/fila').get_json()['trabalhos']), 1)

    def test_identidade_obrigatoria_e_trabalho_inexistente(self):
        self.assertEqual(self.post(self.endpoint, {'doc': self.tentativa['doc']}).status_code, 400)
        self.assertEqual(self.post(self.endpoint, dict(self.identidade, doc='outro')).status_code, 404)
        self.assertEqual(self.ler(), self.tentativa)

    def test_permissao_e_csrf(self):
        self.assertIn(self.client.post(self.endpoint, json=self.identidade).status_code, (400, 403))
        leitor = self.s.app.test_client()
        self.assertEqual(leitor.post('/api/entrar', json={'login': 'leitor_ficticio', 'senha': 'Ficticia123'}, headers={'X-CPJ': '1'}).status_code, 200)
        self.assertEqual(leitor.post(self.endpoint, json=self.identidade, headers={'X-CPJ': '1'}).status_code, 403)
        self.assertEqual(self.ler(), self.tentativa)

    def test_falha_de_auditoria_nao_oculta_ocorrencia(self):
        with patch('rotas.casos.auditar', side_effect=RuntimeError('auditoria fictícia indisponível')):
            with self.assertRaises(RuntimeError):
                self.post(self.endpoint, self.identidade)
        self.assertEqual(self.ler(), self.tentativa)
        self.assertEqual(len(self.client.get('/api/fila').get_json()['trabalhos']), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
