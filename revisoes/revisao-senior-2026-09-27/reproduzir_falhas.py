import os, sys, json, tempfile, hashlib, zipfile, subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path.cwd(); OUT=ROOT/'revisoes/revisao-senior-2026-09-27'
W=Path(tempfile.mkdtemp(prefix='cpj-repros-senior-'));os.environ['CPJ_WORKSPACE']=str(W);os.environ['CPJ_SEM_AGENTE_EMBUTIDO']='1'
sys.path.insert(0,str(ROOT/'plugin/investigacao-cpj/app'))
import servidor as S
M=W/'casos/_MODELO-CASO';M.mkdir(parents=True)
for f in ['00-originais','01-extracao','02-analise','03-relatorios']:(M/f).mkdir()
(M/'caso.json').write_text(json.dumps({'datas':{},'financeiro':{},'ip':{},'resultado':{},'relatorios':[]}))
S.auth.salvar_usuario('admin_ficticio','ADMIN FICTICIO','admin','TesteFicticio9876')
c=S.app.test_client();c.post('/api/entrar',json={'login':'admin_ficticio','senha':'TesteFicticio9876'},headers={'X-CPJ':'1'})
results={}
def record(k,v):results[k]=v;print(k,json.dumps(v,ensure_ascii=False),flush=True)
# Cancelamento seguido de conclusão, diretamente no contrato de persistência.
p=S.tarefas.plantao;p.registrar('ficticio','outro','chat',aprovado=True)
j=p.enfileirar('OS-1-2099','revisar','admin_ficticio');p.reivindicar('ficticio');p.cancelar(j)
p.concluir(j,'ficticio',{'resumo':'simulado'});record('cancelado_concluido',{'estado':p.pedido(j)['estado'],'cancelar':p.pedido(j)['cancelar']})
j=p.enfileirar('OS-2-2099','revisar','admin_ficticio');p.reivindicar('ficticio');p.cancelar(j)
with p._c() as db:db.execute("UPDATE agentes SET visto_em='2000-01-01T00:00:00' WHERE nome='ficticio'")
p.pedidos();got=p.reivindicar('ficticio');record('cancelado_abandonado',{'estado':p.pedido(j)['estado'],'cancelar':p.pedido(j)['cancelar'],'reivindicado':got is not None})
try:p.enfileirar('OS-2-2099','revisar','admin_ficticio')
except ValueError as ex:record('caso_bloqueado_apos_cancelar',str(ex))
# Importador com pacote integralmente fictício, escopo inadequado e cancelado.
r='config/arquivo-injetado-ficticio.txt';data=b'FICTICIO';zpath=W/'pacote.zip'
with zipfile.ZipFile(zpath,'w') as z:
 z.writestr('dados/'+r,data);z.writestr('manifest.json',json.dumps({'schema':'cpj-export/1','arquivos':[{'caminho':r,'tamanho':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}))
t=S.tarefas.nova('importar','FICTICIO','admin_ficticio');S.tarefas.cancelar(t)
with patch.object(S.tarefas,'indexar',return_value=None):result=S.tarefas.importar(t,str(zpath))
record('importacao_cancelada_fora_escopo',{'gravou':(W/r).exists(),'arquivos':result['arquivos'],'status':S.tarefas.obter(t)['status']})
with patch('tarefas.subprocess.run',return_value=subprocess.CompletedProcess([],1,'','FALHA SIMULADA')):
 record('erro_indexacao_ignorado',S.tarefas.indexar() is None)
# Atualizações sobre duas leituras do mesmo caso.
id=S.C.novo('3/2099')['id'];a=S.C.carregar(id);b=S.C.carregar(id);a['determinacao']='NOVO TEXTO FICTICIO';S.C.salvar(a);b['prazo']='2099-12-31';S.C.salvar(b)
record('atualizacao_perdida',{'determinacao':S.C.carregar(id)['determinacao'],'prazo':S.C.carregar(id)['prazo']})
# Contrato HTTP descarta os dois estados.
with patch.object(S.R,'pesquisa_relacional',return_value=([],[])) as mock:
 resp=c.get('/api/pesquisa/pessoas?mandado_estado=confirmado&cautelar_estado=historico');record('filtros_descartados',{'http':resp.status_code,'filtros_repassados':mock.call_args.args[0]})
# Reproduzir limite antes do filtro via banco real com 201 registros negados e 1 confirmado.
text='\n\n'.join('Nome: FICTICIO A%03d\nSem mandado de prisão'%i for i in range(201))+'\n\nNome: FICTICIO ZULTIMO\nMandado de prisão em aberto nº 123/2099'
f=W/'pessoas.txt';f.write_text(text,encoding='utf-8');S.Q.importar(str(f),'Base ficticia')
subprocess.run([sys.executable,str(ROOT/'plugin/investigacao-cpj/skills/base-cpj/scripts/indexar.py')],capture_output=True,check=True)
direct=S.R.pesquisa_relacional({'nome':'FICTICIO','mandado_estado':'confirmado'})[0]
api=c.get('/api/pesquisa/pessoas?nome=FICTICIO&mandado_estado=confirmado').get_json()['pessoas']
solo=c.get('/api/pesquisa/pessoas?mandado_estado=confirmado').get_json()['pessoas']
record('filtro_incompleto',{'banco_confirmados':len(direct),'api_retornados':len(api),'apos_filtro_browser':len([p for p in api if p['mandado_estado']=='confirmado']),'somente_situacao':len(solo)})
# Sucesso de pipeline sem minuta / indexador falhando.
with patch('plantao.subprocess.run',return_value=subprocess.CompletedProcess([],1,'','ERRO FICTICIO')):
 record('pos_processamento_sem_entrega',S.tarefas.plantao is not None and __import__('plantao').pos_processar(str(W),id,'relatorio'))
(OUT/'reproducoes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('Fixtures isoladas:',W)
# Autorizacao de arquivos deve avaliar caminho normalizado, e ID nao pode ser '..'.
S.auth.salvar_usuario('invest_ficticio','INVESTIGADOR FICTICIO','investigador','TesteFicticio9876')
S.auth.salvar_usuario('deleg_ficticio','DELEGADO FICTICIO','delegado','TesteFicticio9876')
(W/'config/marcador-ficticio.txt').write_text('APENAS MARCADOR FICTICIO',encoding='utf-8')
(Path(S.C.caminho(id))/'02-analise/marcador-ficticio.txt').write_text('ANALISE FICTICIA RESTRITA',encoding='utf-8')
def client(login):
 x=S.app.test_client();x.post('/api/entrar',json={'login':login,'senha':'TesteFicticio9876'},headers={'X-CPJ':'1'});return x
iv=client('invest_ficticio');dg=client('deleg_ficticio')
a=iv.get('/arquivo/%2E%2E/config/marcador-ficticio.txt')
b=dg.get(f'/arquivo/{id}/02-analise/marcador-ficticio.txt')
d=dg.get(f'/arquivo/{id}/00-originais/%2E%2E/02-analise/marcador-ficticio.txt')
record('download_fora_permissao',{'investigador_config_http':a.status_code,'investigador_leu_marcador':a.data==b'APENAS MARCADOR FICTICIO','delegado_direto_http':b.status_code,'delegado_via_originais_http':d.status_code,'delegado_leu_analise':d.data==b'ANALISE FICTICIA RESTRITA'})
(OUT/'reproducoes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
