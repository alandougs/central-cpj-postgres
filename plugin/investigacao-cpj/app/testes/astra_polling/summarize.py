"""Audita coleta sintética AST15 e publica somente evidências fictícias, sem navegador."""
from pathlib import Path
import gzip,hashlib,json,math,sys,shutil

raw=Path(sys.argv[1]);snapshot=Path(sys.argv[2]);out=Path(sys.argv[3]);live=Path(sys.argv[4])
j=json.loads(gzip.decompress(raw.read_bytes()))
assert j.get('finished') and not j.get('fatal'), 'Coleta incompleta'
assert not j['errors'] and not j['externalRequests'], 'Erros ou rede externa'
assert len(j['samples'])==36, 'Esperadas 36 amostras'
meta=json.loads((snapshot/'snapshot.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((snapshot/p).read_bytes()).hexdigest()==h for p,h in meta['files'].items()), 'Snapshot alterado'
assert all(hashlib.sha256((live/'static/js'/f'{n}.js').read_bytes()).hexdigest()==meta['files'][f'app/static/js/{n}.js'] for n in ['polling','sistema','casos','recebimento','sessao']), 'Produto divergiu do snapshot'
expected={'idle-inicio':(4,1),'idle-case':(8,1),'active-case':(8,4),'idle-other-tab-case-open':(8,1),'error-case':(4,2),'hidden-case-emulated':(8,0)}
for r in j['samples']:
    index=0 if r['variant']=='before' else 1
    assert r['counts'].get('/api/tarefas',0)==expected[r['name']][index], r
    assert r['counts'].get('/api/fila',0)==((4,1)[index] if r['name']=='idle-inicio' else 0),r
    assert all(q['method']=='GET' for q in r['requests']), 'Comando inesperado'
    assert all(q['status']==(503 if r['name']=='error-case' else 200) for q in r['responses']), 'Status inesperado'
    assert len(r['responses'])==len(r['requests']), 'Resposta pendente'
    if r['variant']=='after':assert r['steadyMutations']==0, 'DOM mudou sem alteração de dados'
def quant(xs,p):
    xs=sorted(xs)
    return xs[max(0,math.ceil(p*len(xs))-1)] if xs else None
def stats(xs):return {'n':len(xs),'p50':quant(xs,.5),'p95':quant(xs,.95)}
summary={'schema':'astra-polling-summary/1','raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'snapshot':str(snapshot),'browser':j['browser'],'host':j['host'],'limits':j['limits'],'oracles':'36/36 counts, statuses, methods, DOM and source hashes validated','rows':[]}
for name in expected:
    for variant in ('before','after'):
        rows=[r for r in j['samples'] if r['name']==name and r['variant']==variant]
        assert len(rows)==3
        summary['rows'].append({'scenario':name,'variant':variant,'repetitions':3,'tasks':stats([r['counts'].get('/api/tarefas',0) for r in rows]),'fila':stats([r['counts'].get('/api/fila',0) for r in rows]),'steadyMutations':stats([r['steadyMutations'] for r in rows]),'latencyMs':stats([q['latencyMs'] for r in rows for q in r['responses']]),'cdpTaskMs':stats([r['cdp']['TaskDuration']*1000 for r in rows]),'cdpLayoutCount':stats([r['cdp']['LayoutCount'] for r in rows]),'cdpRecalcStyleCount':stats([r['cdp']['RecalcStyleCount'] for r in rows]),'jsHeapBytes':stats([r['cdp']['JSHeapUsedSize'] for r in rows])})
out.mkdir(parents=True,exist_ok=True)
shutil.copyfile(raw,out/'raw.json.gz');shutil.copyfile(snapshot/'snapshot.json',out/'snapshot.json');shutil.copyfile(snapshot/'source-validation.json',out/'source-validation.json')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
for row in summary['rows']:print(row['scenario'],row['variant'],'GET',row['tasks']['p50'],'fila',row['fila']['p50'],'DOM',row['steadyMutations']['p50'],'CDP ms',round(row['cdpTaskMs']['p50'],2))
print(summary['oracles'])
