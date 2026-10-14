"""EXPLAIN das consultas reais, sem GET adicional ou execução do SELECT pesado."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys


class PlanoObtido(Exception):
    pass


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--codigo',type=Path,required=True);ap.add_argument('--medicao',type=Path,required=True)
    args=ap.parse_args();base=args.codigo/'plugin/investigacao-cpj/skills/base-cpj/scripts'
    os.environ['CPJ_WORKSPACE']=str(args.medicao/'workspace-100-sparse')
    sys.path.insert(0,str(base));import rag
    planos=[]
    for n in (100,500,1000):
        for densidade in ('sparse','dense'):
            arquivo=args.medicao/f'workspace-{n}-{densidade}/rag/cpj.sqlite'
            hash_antes=hashlib.sha256(arquivo.read_bytes()).hexdigest()
            with closing(sqlite3.connect(arquivo.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                for modo,caso,q in [('general',None,''),('case','OS-1-2099',''),('partial-global',None,'pessoa ficticia'),('partial-case','OS-1-2099','pessoa ficticia')]:
                    class LeitorDePlano:
                        def execute(self,sql,params=()):
                            if sql.startswith('WITH RECURSIVE documentais'):
                                planos.append({'cases':n,'density':densidade,'mode':modo,'sqlTemplateSha256':hashlib.sha256(sql.encode('utf-8')).hexdigest(),
                                               'parameterCount':len(params),'plan':[list(row) for row in db.execute('EXPLAIN QUERY PLAN '+sql,params)]})
                                raise PlanoObtido()
                            return db.execute(sql,params)
                    try:rag.pagina_grafo(LeitorDePlano(),caso,q,(),1,400)
                    except PlanoObtido:pass
                    else:raise AssertionError('Consulta paginada não foi capturada para EXPLAIN.')
            assert hashlib.sha256(arquivo.read_bytes()).hexdigest()==hash_antes
    resultado={'schema':'astra-sql-planos/1','method':'24EXPLAIN QUERY PLAN das consultas atuais via proxy de execute; SELECT principal não executado; sem HTTP, fora das amostras do benchmark.',
               'ragSha256':hashlib.sha256((base/'rag.py').read_bytes()).hexdigest(),'plans':planos}
    (args.medicao/'planos-atuais.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
    print('24 planos obtidos; hashes dos bancos preservados.')


if __name__=='__main__':main()
