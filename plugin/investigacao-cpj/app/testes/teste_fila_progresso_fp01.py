"""FP01: atividade e previsão da fila, exclusivamente com tempos/arquivos fictícios."""
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest
from werkzeug.serving import make_server
from teste_explorer_ex01 import ExplorerFixture

APP = Path(__file__).resolve().parents[1]
RUNTIME = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
NODE = RUNTIME/'bin/node.exe'


def node(script):
    env = dict(os.environ, NODE_PATH=str(RUNTIME/'node_modules'))
    resultado = subprocess.run([str(NODE), '-e', script], env=env,
                               capture_output=True, text=True, encoding='utf-8', timeout=90)
    if resultado.returncode:
        raise AssertionError(resultado.stdout+resultado.stderr)
    return resultado.stdout


class Previsoes(unittest.TestCase):
    def run_js(self, script):
        prefix = "const assert=require('node:assert/strict');const F=require("+json.dumps(str(APP/'static/js/fila-progresso.js'))+");const f=F.criar();\n"
        prefix += "const agora=Date.parse('2099-01-01T12:00:00');const iso=s=>new Date(agora+s*1000).toISOString();\n"
        prefix += "const historico={caso:'OS-FICTICIA',doc:'antes',arquivo:'antes.pdf',modo:'rapido',status:'concluido',inicio:iso(-1200),fim:iso(-600),paginas:100};\n"
        prefix += "const atual={caso:'OS-FICTICIA',doc:'atual',arquivo:'atual.pdf',modo:'rapido',status:'processando',inicio:iso(-120),etapa:'tabelas (CSV)',progresso:91,paginas:100,pagina_atual:100};\n"
        return node(prefix+script)

    def test_descreve_tabelas_sem_apresentar_pagina_antiga_como_progresso_atual(self):
        self.run_js("""
        const v=f.calcular([atual,historico],agora),t=v.itens[0];
        assert.match(t.atividade,/tabelas/i);assert.match(t.descricao,/CSV/);
        assert.equal(t.pagina,null);assert.equal(t.decorrido,120);
        assert.equal(t.etapaNumero,3);assert.equal(t.etapasTotal,6);
        assert.ok(t.restante.min>0&&t.restante.max>=t.restante.min);
        """)

    def test_previsao_acumulada_de_cada_arquivo_e_fila(self):
        self.run_js("""
        const q={...atual,doc:'seguinte',arquivo:'seguinte.pdf',status:'na_fila',inicio:null,paginas:200};
        const v=f.calcular([atual,q,historico],agora),a=v.itens[0],b=v.itens[1];
        assert.equal(v.ativos,1);assert.equal(v.aguardando,1);assert.equal(b.posicao,1);
        assert.deepEqual(b.iniciaEm,a.restante);
        assert.equal(b.terminaEm.min,a.restante.min+b.restante.min);
        assert.equal(b.terminaEm.max,a.restante.max+b.restante.max);
        assert.deepEqual(v.total,b.terminaEm);assert.equal(v.semEstimativa,0);
        assert.equal(v.itens[2].restante,null);
        """)

    def test_sem_base_nao_inventa_zero_e_historico_nao_cruza_modo_ou_formato(self):
        self.run_js("""
        const q={...atual,status:'na_fila',inicio:null,modo:'inteligente'};
        let v=f.calcular([q,historico],agora);
        assert.equal(v.total,null);assert.equal(v.semEstimativa,1);assert.equal(v.itens[0].restante,null);
        v=f.calcular([{...q,modo:'rapido',arquivo:'planilha.csv'},historico],agora);
        assert.equal(v.total,null);assert.equal(v.itens[0].restante,null);
        const ruim={...historico,fim:iso(-1300)};
        assert.equal(f.calcular([q,ruim],agora).total,null);
        """)

    def test_estimativa_superada_recalcula_e_sem_avanco_e_observacao_real(self):
        self.run_js("""
        const a={...atual,inicio:iso(-700)};
        let v=f.calcular([a,historico],agora);assert.equal(v.itens[0].restante,null);
        assert.equal(v.itens[0].recalculando,true);assert.equal(v.itens[0].semAvanco,0);
        v=f.calcular([a,historico],agora+61000);assert.equal(v.itens[0].semAvanco,61);
        v=f.calcular([{...a,etapa:'dados críticos',progresso:94},historico],agora+62000);
        assert.equal(v.itens[0].semAvanco,0);
        """)

    def test_apenas_ocr_mostra_pagina_ia_visual_e_opcional_e_erro_nao_vira_concluido(self):
        self.run_js("""
        let v=f.calcular([{...atual,etapa:'extração/OCR',pagina_atual:40,progresso:39}],agora);
        assert.deepEqual(v.itens[0].pagina,{atual:40,total:100});
        assert.ok(v.itens[0].restante);
        v=f.calcular([{...atual,etapa:'transcrição visual por IA',modo:'inteligente'}],agora);
        assert.equal(v.itens[0].etapaNumero,7);assert.equal(v.itens[0].etapasTotal,7);
        assert.equal(v.itens[0].restante,null);
        v=f.calcular([{...atual,status:'erro',erro:'falha fictícia'}],agora);
        assert.equal(v.ativos+v.aguardando,0);assert.equal(v.erros,1);assert.equal(v.total,null);
        """)

    def test_relogio_invalido_nao_gera_previsao_e_primeiros_segundos_sao_exatos(self):
        self.run_js("""
        const helpers={esc:s=>String(s).replaceAll('<','&lt;'),badge:()=>'',barraHTML:()=>''};
        let v=f.calcular([{...atual,inicio:'data inválida'}],agora);
        assert.equal(v.itens[0].decorrido,null);assert.equal(v.itens[0].restante,null);
        assert.ok(!/NaN|Invalid Date/.test(f.html(v,helpers)));
        v=f.calcular([{...atual,inicio:iso(30)}],agora);assert.equal(v.itens[0].decorrido,null);
        v=f.calcular([{...atual,inicio:iso(0)}],agora);
        assert.match(f.html(v,helpers),/Em processamento há: 0 s/);
        """)

    def test_etapa_nao_catalogada_mantem_atividade_informada_pelo_servidor(self):
        self.run_js("""
        const v=f.calcular([{...atual,etapa:'Validando arquivo fictício'}],agora);
        assert.equal(v.itens[0].atividade,'Validando arquivo fictício');
        assert.equal(v.itens[0].etapaNumero,null);
        """)

    def test_cancelamento_nao_e_anunciado_como_conclusao_da_fila(self):
        self.run_js("""
        const v=f.calcular([{...atual,status:'cancelado'}],agora);
        const helpers={esc:String,badge:()=>'',barraHTML:()=>''};
        assert.equal(v.total,null);assert.ok(!f.html(v,helpers).includes('Fila concluída'));
        """)


class FilaNavegador(ExplorerFixture, unittest.TestCase):
    def setUp(self):
        pass

    def test_atividade_previsoes_dados_incompletos_e_erro_preservam_fila_no_edge(self):
        server=make_server('127.0.0.1',0,self.s.app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            script=r'''
            const {chromium}=require('playwright'),assert=require('node:assert/strict');
            (async()=>{
             const browser=await chromium.launch({channel:'msedge',headless:true});
             try{
              const context=await browser.newContext({viewport:{width:1200,height:900}});
              const login=await context.request.post(URL+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'admin_ex01',senha:'Ficticia123'}});assert.equal(login.status(),200);
              const page=await context.newPage(),errors=[];page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
              const agora=Date.now(),iso=s=>new Date(agora+s*1000).toISOString();
              let falha=false,jobs=[{caso:'OS-FICTICIA',doc:'atual',arquivo:'atual.pdf',modo:'rapido',status:'processando',inicio:iso(-120),etapa:'tabelas (CSV)',progresso:91,paginas:140,pagina_atual:140},
               {caso:'OS-FICTICIA',doc:'seguinte',arquivo:'<img src=x onerror=alert(1)>.pdf',modo:'rapido',status:'na_fila',progresso:0},
               {caso:'OS-FICTICIA',doc:'antes',arquivo:'antes.pdf',modo:'rapido',status:'concluido',inicio:iso(-1200),fim:iso(-600),paginas:100}];
              await page.route('**/api/fila',r=>falha?r.fulfill({status:503,json:{erro:'Falha fictícia de leitura'}}):r.fulfill({json:{trabalhos:jobs,idioma_ocr:'por'}}));
              await page.goto(URL+'/#nova');await page.waitForLoadState('networkidle');
              await page.locator('[data-fila-resumo]').waitFor();
              let text=await page.locator('#fila').innerText();
              assert.match(text,/Extraindo tabelas/);assert.match(text,/Etapa 3 de 6/);assert.match(text,/Restante da fila/);
              assert.match(text,/Restante aproximado/);assert.match(text,/posição 1/);assert.match(text,/término previsto/);
              assert.ok(!text.includes('página 140 de 140'));assert.equal(await page.locator('#fila img').count(),0);
              await page.screenshot({path:SHOT.replace('.png','-com-previsao.png'),fullPage:true});
              falha=true;await page.evaluate(()=>atualizarFila().catch(()=>{}));
              await page.locator('#fila-aviso').waitFor();assert.match(await page.locator('#fila-aviso').innerText(),/Falha fictícia/);
              assert.match(await page.locator('#fila').innerText(),/Extraindo tabelas/);
              falha=false;jobs=jobs.slice(0,2);await page.evaluate(()=>atualizarFila());
              assert.match(await page.locator('#fila').innerText(),/Previsão total em cálculo/);
              assert.equal(await page.locator('#fila-aviso').innerText(),'');
              await page.screenshot({path:SHOT,fullPage:true});assert.deepEqual(errors,[]);
             }finally{await browser.close()}
            })().catch(e=>{console.error(e);process.exit(1)});
            '''
            import tempfile
            screenshot=str(Path(tempfile.gettempdir())/'cpj-fp01-fila-ficticia.png')
            script=script.replace('URL',json.dumps(f'http://127.0.0.1:{server.server_port}')).replace('SHOT',json.dumps(screenshot))
            node(script)
        finally:
            server.shutdown();thread.join(timeout=5);server.server_close()


if __name__=='__main__':
    unittest.main(verbosity=2)
