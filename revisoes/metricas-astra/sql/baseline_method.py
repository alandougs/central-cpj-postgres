"""ASTRA #14 baseline: frozen code, synthetic data, Flask GET API and SQLite trace."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
CODE=HERE/'source'
APP=CODE/'plugin/investigacao-cpj/app'
REV='f56653cb2c0081f4815d9bccbd0edc1cdfef74fb'

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()

def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def quant(a,p):return sorted(a)[max(0,math.ceil(len(a)*p)-1)]
def stats(a):return {'n':len(a),'p50':quant(a,.5),'p95':quant(a,.95),'min':min(a),'max':max(a)}

def build(ws,n,density):
    cases=ws/'casos';cases.mkdir(parents=True)
    dbp=ws/'rag/cpj.sqlite';dbp.parent.mkdir()
    db=sqlite3.connect(dbp)
    db.executescript('''CREATE TABLE arestas(a_tipo TEXT,a_valor TEXT,b_tipo TEXT,b_valor TEXT,relacao TEXT,origem TEXT,fonte TEXT,localizador TEXT);
    CREATE TABLE rotulos(tipo TEXT,valor TEXT,rotulo TEXT,PRIMARY KEY(tipo,valor));
    CREATE INDEX ix_ar_a ON arestas(a_tipo,a_valor);
    CREATE INDEX ix_ar_b ON arestas(b_tipo,b_valor);''')
    people,degree=(8,2) if density=='sparse' else (70,4)
    for c in range(1,n+1):
        case=f'OS-{c}-2099';folder=cases/case;folder.mkdir()
        dump(folder/'caso.json',{'id':case,'ordem_servico':f'{c}/2099','status':'analisado','vitimas':[],'investigados':[],'documentos':[],'datas':{'recebido':'2099-01-01'}})
        rows=[];labels=[('CASO',case,f'O.S. fictícia {c}/2099')]
        for p in range(people):
            person=f'P:FICTICIO-C{c:04d}-P{p:03d}';name=f'pessoa ficticia c{c:04d} p{p:03d}';account=f'banco ficticio|C{c:04d}A{p:03d}'
            labels.extend([('PESSOA',person,name.title()),('NOME',name,name.title()),('CONTA',account,f'Conta sintética C{c} A{p}')])
            for typ,val,rel in [('CASO',case,'referência cadastral fictícia'),('NOME',name,'nome (homônimos possíveis — conferir)'),('CONTA',account,'titular conforme autos fictícios')]:
                rows.append(('PESSOA',person,typ,val,rel,'caso',case,'ficticio-cadastro.pdf; pág. 1; fls. 1'))
            for k in range(1,degree+1):
                target=f'banco ficticio|C{c:04d}A{(p+k)%people:03d}'
                for evidence in range(2):
                    rows.append(('CONTA',account,'CONTA',target,'transferiu conforme fonte fictícia','caso',case,f'ficticio-extrato-{evidence+1}.pdf; pág. {p+2}; fls. {p+10}'))
        db.executemany('INSERT INTO arestas VALUES(?,?,?,?,?,?,?,?)',rows)
        db.executemany('INSERT INTO rotulos VALUES(?,?,?)',labels)
        if c%100==0:db.commit()
    db.commit()
    real_rows=db.execute('SELECT count(*) FROM arestas').fetchone()[0]
    real_unique=db.execute('SELECT count(*) FROM (SELECT DISTINCT a_tipo,a_valor,b_tipo,b_valor,relacao FROM arestas)').fetchone()[0]
    roots=people*n*2
    out={'cases':n,'density':density,'peoplePerCase':people,'transferNeighbors':degree,'sourceReferencesPerTransfer':2,'rawEvidenceRows':real_rows,'uniqueRelations':real_unique,'realRootsMatchingPartial':roots,'rawEvidenceRowsPerCase':real_rows//n,'uniqueRelationsPerCase':real_unique//n,'databaseBytes':dbp.stat().st_size,'indices':[r[1] for r in db.execute("PRAGMA index_list('arestas')")], 'queryPlans':{}}
    for name,sql,args in [('general',"SELECT DISTINCT a_tipo,a_valor,b_tipo,b_valor,relacao,origem,fonte,localizador FROM arestas WHERE relacao != 'consta nos autos' ORDER BY (CASE WHEN origem='manual' THEN 0 WHEN relacao LIKE '%transferiu%' THEN 1 WHEN a_tipo='PESSOA' OR b_tipo='PESSOA' THEN 2 ELSE 3 END) LIMIT 400",()),('case-source',"SELECT DISTINCT a_tipo,a_valor,b_tipo,b_valor,relacao,origem,fonte,localizador FROM arestas WHERE fonte=? AND (relacao LIKE '%transferiu%' OR relacao LIKE '%Pix%' OR relacao LIKE '%TED%' OR relacao LIKE '%titular%')",('OS-1-2099',))]:
        out['queryPlans'][name]=[list(r) for r in db.execute('EXPLAIN QUERY PLAN '+sql,args)]
    db.close();return dbp,out

def worker(n,density):
    ws=HERE/f'workspace-{n}-{density}';ws.mkdir()
    dbp,fixture=build(ws,n,density)
    os.environ['CPJ_WORKSPACE']=str(ws)
    os.environ['CPJ_SEM_AGENTE_EMBUTIDO']='1'
    os.environ.pop('CPJ_WORKSPACES',None)
    sys.path.insert(0,str(APP))
    import servidor
    import rotas.consulta as api
    import rotas.comum as common
    assert Path(servidor.WS).resolve()==ws.resolve()
    assert Path(api.__file__).resolve().is_relative_to(CODE.resolve())
    assert Path(api.R.__file__).resolve().is_relative_to(CODE.resolve())
    servidor.app.config.update(TESTING=True)
    client=servidor.app.test_client()
    real_connect=api.R.conectar;real_load=api.C.carregar
    counter=Counter();connections=0;loads=0
    def trace(sql):
        flat=' '.join(sql.split()).upper()
        if flat.startswith('SELECT ROTULO FROM ROTULOS'):key='rotulo_select'
        elif flat.startswith('SELECT B_VALOR FROM ARESTAS'):key='fallback_name_select'
        elif flat.startswith('WITH NOS'):key='seed_cte_select'
        elif flat.startswith('SELECT 1 FROM'):key='schema_probe_select'
        elif flat.startswith('SELECT') or flat.startswith('WITH'):key='other_select'
        else:key=flat.split(' ',1)[0].lower()
        counter[key]+=1
    def connect():
        nonlocal connections
        db=real_connect();db.set_trace_callback(trace);connections+=1;return db
    def load(*args,**kw):
        nonlocal loads
        loads+=1;return real_load(*args,**kw)
    outcomes=[]
    db_hash_before=digest(dbp)
    datasets=[('general',{}),('case',{'caso':'OS-1-2099'}),('partial-global',{'q':'pessoa ficticia'}),('partial-case',{'q':'pessoa ficticia','caso':'OS-1-2099'})]
    with patch('rotas.comum.usuario',return_value={'login':'operador_ficticio','perfil':'investigador'}),patch.object(api.R,'conectar',side_effect=connect),patch.object(api.C,'carregar',side_effect=load):
        for mode,query in datasets:
            samples=[];warm=None
            for rep in range(6):
                counter.clear();connections=0;loads=0
                started=time.perf_counter();response=client.get('/api/grafo',query_string=query);raw=response.get_data();elapsed=(time.perf_counter()-started)*1000
                assert response.status_code==200,(response.status_code,raw[:200])
                g=response.get_json();assert g['indice_disponivel'];assert len(g['casos'])==n
                sample={'repeat':rep,'durationMs':elapsed,'httpStatus':response.status_code,'responseBytes':len(raw),'returnedRelations':len(g['arestas']),'returnedNodes':len(g['nos']),'returnedReferences':sum(len(a.get('evidencias',[])) or 1 for a in g['arestas']),'sqlStatements':sum(counter.values()),'sqlCategories':dict(counter),'sqliteConnections':connections,'caseFilesRead':loads,'reportedCompletenessFields':{k:g.get(k,'ABSENT') for k in ('total','limite','truncado','proxima_pagina')}}
                if rep==0:warm=sample
                else:samples.append(sample)
            scope_case='caso' in query
            expected=fixture['uniqueRelationsPerCase'] if scope_case else fixture['uniqueRelations']
            expected_refs=fixture['rawEvidenceRowsPerCase'] if scope_case else fixture['rawEvidenceRows']
            outcome={'mode':mode,'query':query,'expectedUniqueRelations':expected,'expectedReferences':expected_refs,'candidateRoots':fixture['peoplePerCase']*2 if scope_case else fixture['realRootsMatchingPartial'],'oracle':'Every synthetic person matches the partial query; every relation is within two hops of a matching person. Cases are disconnected.','warmup':warm,'samples':samples,'summary':{key:stats([s[key] for s in samples]) for key in ('durationMs','sqlStatements','sqliteConnections','caseFilesRead','returnedRelations','returnedNodes','responseBytes')},'omittedUniqueRelations':expected-samples[0]['returnedRelations'],'omittedReferences':expected_refs-samples[0]['returnedReferences']}
            outcomes.append(outcome)
            dump(HERE/f'partial-{n}-{density}.json',{'fixture':fixture,'outcomes':outcomes})
            print(json.dumps({'cases':n,'density':density,'mode':mode,'p50Ms':outcome['summary']['durationMs']['p50'],'p95Ms':outcome['summary']['durationMs']['p95'],'sql':outcome['summary']['sqlStatements']['p50'],'returned':samples[0]['returnedRelations'],'real':expected}),flush=True)
    db_hash_after=digest(dbp)
    assert db_hash_before==db_hash_after,'GET requests changed synthetic SQLite'
    return {'fixture':fixture,'workspace':str(ws),'dbSha256Before':db_hash_before,'dbSha256After':db_hash_after,'databaseUnchanged':True,'outcomes':outcomes}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worker',nargs=2);args=ap.parse_args()
    if args.worker:
        n,density=args.worker;value=worker(int(n),density);dump(HERE/f'complete-{n}-{density}.json',value);return
    result={'schema':'astra-sql-api-baseline/1','revision':REV,'started':datetime.now(timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,'archiveSha256':digest(HERE/'code-f56653c.zip'),'codeFilesSha256':{str(p.relative_to(CODE)):digest(p) for p in [APP/'rotas/consulta.py',CODE/'plugin/investigacao-cpj/skills/base-cpj/scripts/rag.py']},'limitations':['Flask test_client GET, not TCP; includes route, case-file reads, SQL, JSON serialization, response body.','Authentication is patched to fictitious investigator; route permission decorator still runs, password/session latency excluded.','SQLite trace callback adds overhead; only counts/categories persisted, not expanded SQL values.','One warmup plus five measured repetitions; p95 nearest-rank is maximum of five.','Operating-system and SQLite caches are warm; no controlled cold-cache or concurrent load.','Each case disconnected; sparse8people/2transfer-neighbors, dense70people/4neighbors; two evidence references per transfer.','Schema has original arestas a/b indices and rotulos PK; no new SQL optimizations applied.','Partial query matches every synthetic person/name, so all fixture relations are legitimately reachable; not representative of a selective operational query.','Data generated directly into temporary SQLite and JSON; PDF/OCR/indexing excluded.','Audit/config created only under dedicated synthetic TEMP workspaces; no operational data used.'],'datasets':[]}
    dump(HERE/'results.json',result)
    for n in (100,500,1000):
        for density in ('sparse','dense'):
            proc=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--worker',str(n),density],cwd=str(HERE),text=True,encoding='utf-8',capture_output=True,timeout=900)
            (HERE/f'run-{n}-{density}.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
            print(proc.stdout,flush=True,end='')
            if proc.returncode:raise RuntimeError(f'Worker {n}/{density} failed: {proc.stderr[-2000:]}')
            result['datasets'].append(json.loads((HERE/f'complete-{n}-{density}.json').read_text(encoding='utf-8')))
            dump(HERE/'results.json',result)
    result['finished']=datetime.now(timezone.utc).isoformat();result['measuredRequests']=sum(len(o['samples']) for d in result['datasets'] for o in d['outcomes']);result['status']='complete';dump(HERE/'results.json',result)
    print('COMPLETE '+str(HERE/'results.json'),flush=True)

if __name__=='__main__':main()
