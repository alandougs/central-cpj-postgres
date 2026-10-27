"""IV04: resposta negada preservada em HTTP real; somente payloads sinteticos."""
import json,sys,unittest,socket,threading,time,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import Flask,jsonify,request
import web_seguro as W

def aplicar(r):
 return getattr(W,'drenar_corpo_de_erro',lambda r:r)(r)

class Drenagem(unittest.TestCase):
 def setUp(self):self.app=Flask(__name__)
 def test_erro_json_pequeno_drena_bytes_sem_interpretar_json(self):
  with self.app.test_request_context('/',method='POST',data=b'{invalido',content_type='application/json'):
   r=self.app.response_class('negado',status=403);out=aplicar(r)
   self.assertIs(out,r);self.assertEqual(out.status_code,403)
   self.assertEqual(request.stream.read(),b'')
 def test_sucesso_nao_consume_corpo(self):
  with self.app.test_request_context('/',method='POST',data=b'123',content_type='application/json'):
   aplicar(self.app.response_class('ok',status=200));self.assertEqual(request.stream.read(),b'123')
 def test_acima_limite_nao_consume_upload_negado(self):
  with self.app.test_request_context('/',method='POST',data=b'x'*65537,content_type='application/json'):
   aplicar(self.app.response_class('negado',status=403));self.assertEqual(request.stream.read(1),b'x')
 def test_midia_nao_e_consumida_por_erro(self):
  with self.app.test_request_context('/',method='POST',data=b'123',content_type='application/octet-stream'):
   aplicar(self.app.response_class('negado',status=403));self.assertEqual(request.stream.read(),b'123')

class HTTPReal(unittest.TestCase):
 def test_respostas_403_completas_em_conexoes_fechadas(self):
  app=Flask(__name__);app.config['MAX_CONTENT_LENGTH']=2*1024**3
  app.after_request(aplicar)
  @app.route('/saude')
  def saude():return jsonify(ok=True)
  @app.route('/negado',methods=['POST'])
  def negado():return jsonify(erro='Sem permissao.'),403
  with socket.socket() as s:s.bind(('127.0.0.1',0));porta=s.getsockname()[1]
  server=W.criar_servidor_wsgi(app,'127.0.0.1',porta);t=threading.Thread(target=server.start,daemon=True);t.start()
  url=f'http://127.0.0.1:{porta}'
  try:
   for _ in range(100):
    try:
     with urllib.request.urlopen(url+'/saude',timeout=1) as r:r.read()
     break
    except OSError:time.sleep(.03)
   for _ in range(40):
    req=urllib.request.Request(url+'/negado',data=b'{"invalido":true}',headers={'Content-Type':'application/json'})
    with self.assertRaises(urllib.error.HTTPError) as erro:urllib.request.urlopen(req,timeout=5)
    self.assertEqual(erro.exception.code,403)
    self.assertEqual(json.loads(erro.exception.read()),{'erro':'Sem permissao.'})
    erro.exception.close()
  finally:server.stop();t.join(5)

if __name__=='__main__':unittest.main(verbosity=2)
