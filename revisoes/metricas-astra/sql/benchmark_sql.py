"""AST14: mesmo gerador e método do baseline; código congelado e índices atuais."""
import argparse
import ast
from contextlib import closing
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import baseline_method as b


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--codigo',type=Path,required=True)
    ap.add_argument('--saida',type=Path,required=True)
    ap.add_argument('--worker',nargs=2)
    args=ap.parse_args()
    code=args.codigo.resolve();saida=args.saida.resolve();saida.mkdir(parents=True,exist_ok=True)
    b.HERE=saida;b.CODE=code;b.APP=code/'plugin/investigacao-cpj/app'
    source=code/'plugin/investigacao-cpj/skills/base-cpj/scripts/rag.py'
    constantes=ast.parse(source.read_text(encoding='utf-8'))
    indices=next(ast.literal_eval(n.value) for n in constantes.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INDICES_GRAFO_SQL' for t in n.targets))
    build=b.build
    def atual(ws,n,density):
        dbp,fixture=build(ws,n,density)
        with closing(sqlite3.connect(dbp)) as db:
            for sql in indices:db.execute(sql)
            db.commit()
            fixture['indicesBefore']=fixture['indices']
            fixture['indices']=[r[1] for r in db.execute("PRAGMA index_list('arestas')")]
            fixture['currentSourceIndexPlan']=[list(r) for r in db.execute('EXPLAIN QUERY PLAN SELECT a_tipo,a_valor,b_tipo,b_valor,relacao FROM arestas WHERE fonte=?',('OS-1-2099',))]
        fixture['databaseBytes']=dbp.stat().st_size
        return dbp,fixture
    b.build=atual
    if args.worker:
        n,density=args.worker
        result=b.worker(int(n),density)
        for outcome in result['outcomes']:
            for sample in [outcome['warmup'],*outcome['samples']]:
                assert sample['reportedCompletenessFields']['total']==outcome['expectedUniqueRelations'],(n,density,outcome['mode'],sample)
                assert sample['reportedCompletenessFields']['limite']==400
                assert sample['returnedRelations']==min(400,outcome['expectedUniqueRelations'])
        b.dump(saida/f'complete-{n}-{density}.json',result)
        return
    files=[b.APP/'rotas/consulta.py',source,source.parent/'indexar.py',b.APP/'grafo_evidencias.py',source.parent/'conferencias_grafo.py']
    result={'schema':'astra-sql-api-after/1','started':datetime.now(timezone.utc).isoformat(),
            'python':sys.version,'platform':platform.platform(),'sqlite':sqlite3.sqlite_version,
            'baselineMethodSha256':b.digest(Path(b.__file__)),'codeFilesSha256':{str(p.relative_to(code)):b.digest(p) for p in files},
            'indicesSQL':indices,'method':'Unchanged baseline generator and worker: 6datasets x4queries x(1warmup+5samples). Current indices applied before timing/hash; explicit total oracle assertions added after measurements.',
            'limitations':['Flask test_client, not TCP/browser; authentication fictitious, real permission decorator.',
                          'SQL trace overhead; warm OS caches; five samples, nearest-rank p95 equals max.',
                          'Baseline predates P0 provenance/review features; response content/size and logical completeness differ.',
                          'Index creation excluded from GET latency; no real data or credentials used.'],
            'datasets':[]}
    b.dump(saida/'results.json',result)
    for n in (100,500,1000):
        for density in ('sparse','dense'):
            proc=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--codigo',str(code),'--saida',str(saida),'--worker',str(n),density],capture_output=True,text=True,encoding='utf-8',timeout=1800)
            (saida/f'run-{n}-{density}.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
            print(proc.stdout,end='',flush=True)
            if proc.returncode:raise RuntimeError(f'Worker {n}/{density}: '+proc.stderr[-2000:])
            result['datasets'].append(json.loads((saida/f'complete-{n}-{density}.json').read_text(encoding='utf-8')))
            b.dump(saida/'results.json',result)
    result.update(finished=datetime.now(timezone.utc).isoformat(),status='complete',measuredRequests=120,warmups=24)
    b.dump(saida/'results.json',result)


if __name__=='__main__':main()
