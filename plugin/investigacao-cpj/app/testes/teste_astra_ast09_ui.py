"""AST09: jornada contextual real no Edge, material e fontes inteiramente ficticios."""
import json
from pathlib import Path
import time
import unittest
from astra_fixture import AstraFixture


class Jornada(AstraFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.control = {"delay_case": False, "delay_graph": False, "fail_case": False}
        from flask import request, jsonify

        @cls.s.app.before_request
        def falhas_da_fixture():
            if request.path == "/api/casos/OS-901-2099" and cls.control["delay_case"]:
                cls.control["delay_case"] = False
                time.sleep(.5)
            if request.path == "/api/grafo" and request.args.get("caso") == "OS-901-2099" and cls.control["delay_graph"]:
                cls.control["delay_graph"] = False
                time.sleep(1)
            if request.path == "/api/casos/OS-902-2099" and cls.control["fail_case"]:
                cls.control["fail_case"] = False
                return jsonify(erro="Falha de leitura ficticia"), 503

    def setUp(self):
        super().setUp()
        self.control.update(delay_case=False, delay_graph=False, fail_case=False)
        self.material(self.caso)

    def material(self, cid, status="extraido", erro=False, ativo=False):
        base = self.ws / "casos" / cid
        base.mkdir(exist_ok=True)
        for sub in ("00-originais", "01-extracao", "02-analise", "03-relatorios"):
            (base / sub).mkdir(exist_ok=True)
        case = {"id": cid, "ordem_servico": cid.removeprefix("OS-").replace("-", "/"),
                "status": status, "datas": {}, "ip": {"paginas": 3}, "relatorios": [],
                "documentos": [{"arquivo": "autos-ficticios.md", "paginas": 3}],
                "preenchimento_os": {"pendentes": ["escrivao"], "conflitos": {}, "ia": "aguardando_ocr"}}
        (base / "caso.json").write_text(json.dumps(case), encoding="utf-8")
        for relative, text in {
            "00-originais/autos-ficticios.md": "Documento ficticio.\n",
            "00-originais/complemento-ficticio.md": "Complemento ficticio.\n",
            "01-extracao/autos/transcricao.md": "## Página 1\n\nTranscricao ficticia.\n",
            "01-extracao/autos/entidades.csv": "tipo;valor\nCONTA;conta ficticia\n",
            "02-analise/pessoas.csv": "nome;papel\nPESSOA FICTICIA;declarante\n",
            "02-analise/dados-faltantes.md": "DADOS FALTANTES — PROVIDENCIAR (OPERADOR)\nConferir o extrato ficticio.\n",
            "02-analise/solicitacoes-os.md": "Solicitacao ficticia com fonte.\n",
            "02-analise/fluxo-financeiro.csv": "origem;destino;valor\nCONTA FICTICIA A;CONTA FICTICIA B;10\n",
        }.items():
            target = base / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        jobs = [{"doc": "autos", "arquivo": "autos-ficticios.md", "status": "concluido", "progresso": 100}]
        if erro or ativo:
            jobs.append({"doc": "complemento", "arquivo": "complemento-ficticio.md", "status": "erro" if erro else "processando", "progresso": 20, "erro": "Falha ficticia de extracao" if erro else ""})
        (base / "processamento.json").write_text(json.dumps({"trabalhos": jobs}), encoding="utf-8")

    def test_01_material_exploracao_unica_retorno_filtros_fontes_e_hipotese(self):
        result = self.post("/api/grafo/vinculo", self.payload(b_tipo="CONTA", b_valor="banco ficticio|4321", documento="autos-ficticios.md", pagina=1))
        self.assertEqual(result.status_code, 200)
        self.browser(r'''
        const errors=[],graphs=[];let writes=0;
        page.on('pageerror',e=>errors.push(e.message));
        page.on('request',r=>{if(r.url().includes('/api/grafo?'))graphs.push(new URL(r.url()));if(r.method()==='POST')writes++});
        await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);await page.waitForSelector('#t-casos tr[data-id="OS-901-2099"]');
        await page.locator('#t-casos tr[data-id="OS-901-2099"]').click();
        const summary=page.locator('#astra-material-resumo');await summary.waitFor();
        assert.match(await summary.innerText(),/2 arquivos originais/);
        assert.match(await summary.innerText(),/1 documento/);
        assert.match(await summary.innerText(),/1 campo.*cadastro pendente/i);
        assert.match(await summary.innerText(),/contagens.*não consultad/i);
        assert.equal(graphs.length,0);
        assert.match(await page.locator('#b-caso-proximo').innerText(),/Explorar/);
        const first=page.waitForResponse(r=>r.url().includes('/api/grafo?caso=OS-901-2099'));
        await page.locator('#b-explorar-astra').click();const response=await first;
        await page.waitForFunction(()=>grEstado==='pronto');
        assert.equal(graphs.length,1);assert.equal(graphs[0].searchParams.get('caso'),'OS-901-2099');
        const actual=await response.json();assert.equal(actual.nos.filter(n=>n.tipo==='CONTA').length,2);
        await page.locator('#gf-outros').uncheck();await page.locator('#b-astra-voltar-caso').click();
        await summary.waitFor();assert.match(await summary.innerText(),/2 contas.*retornad/i);
        await page.locator('#b-caso-conferir-fontes').click();
        assert.ok(await page.locator('#astra-fontes a[href*="00-originais/autos-ficticios.md"]').count());
        assert.ok(await page.locator('#astra-fontes a[href*="dados-faltantes.md"]').count());
        await page.locator('#astra-identificador').fill('ficticio');await page.locator('#b-caso-explorar-identificador').click();await page.waitForFunction(()=>grEstado==='pronto');
        assert.equal(graphs.length,2);assert.equal(await page.locator('#gf-outros').isChecked(),false);
        assert.equal(await page.locator('#gr-busca').inputValue(),'ficticio');
        await page.locator('#gr-busca').fill('ficticio');
        const search=page.waitForResponse(r=>r.url().includes('/api/grafo?')&&new URL(r.url()).searchParams.get('q')==='ficticio');
        await page.locator('#b-gr-buscar').click();await search;await page.waitForFunction(()=>grEstado==='pronto');
        await page.locator('#b-astra-voltar-caso').click();await page.locator('#b-explorar-astra').click();
        await page.waitForFunction(()=>grEstado==='pronto');assert.equal(graphs.length,4);
        assert.equal(await page.locator('#gr-caso').inputValue(),'OS-901-2099');assert.equal(await page.locator('#gr-busca').inputValue(),'ficticio');
        await page.locator('#b-astra-voltar-caso').click();
        await page.evaluate(()=>{document.querySelector('#f-vinculo').a_valor.value='Restante ficticio de outro caso'});
        await page.locator('#b-caso-hipotese').click();
        await page.locator('#modal-vinculo').waitFor();assert.equal(await page.locator('#f-vinculo [name="caso_id"]').inputValue(),'OS-901-2099');
        assert.equal(await page.locator('#f-vinculo [name="a_valor"]').inputValue(),'');
        await page.locator('#b-canc-mv').click();await page.locator('#b-astra-voltar-caso').click();
        let flows=0;page.on('request',r=>{if(r.url().endsWith('/api/casos/OS-901-2099/fluxograma'))flows++});
        const money=page.waitForResponse(r=>r.url().endsWith('/api/casos/OS-901-2099/fluxograma'));
        await page.locator('#b-caso-ver-fluxo').click();await money;
        assert.equal(flows,1);assert.equal(await page.locator('#fx-caso-sel').inputValue(),'OS-901-2099');
        await page.locator('#nav [data-a="casos"]').click();await page.locator('#t-casos tr[data-id="OS-902-2099"]').click();
        await page.waitForFunction(()=>casoAberto==='OS-902-2099'&&document.querySelector('#astra-material-resumo'));
        assert.match(await summary.innerText(),/0 arquivos originais/);
        assert.doesNotMatch(await summary.innerText(),/2 contas.*retornad/i);
        assert.equal(writes,0);assert.deepEqual(errors,[]);
        ''')

    def test_02_proximo_passo_erros_progresso_minuta_final_e_sem_posts(self):
        matrix = [("OS-910-2099", "recebido", False, False, "Conferir material"),
                  ("OS-911-2099", "extraido", True, False, "Conferir extração"),
                  ("OS-912-2099", "extraido", False, True, "Acompanhar extração"),
                  ("OS-913-2099", "analisado", False, False, "Preparar relatório"),
                  ("OS-914-2099", "minuta", False, False, "Revisar minuta"),
                  ("OS-915-2099", "entregue", False, False, "Ver relatório FINAL"),
                  ("OS-916-2099", "devolvido", False, False, "Conferir pendências")]
        for cid, status, error, active, _ in matrix:
            self.material(cid, status, error, active)
            if status == "entregue":
                (self.ws / "casos" / cid / "03-relatorios" / f"RELATORIO-{cid}-FINAL.docx").write_bytes(b"Arquivo ficticio, somente para listagem.")
        self.browser("const matrix=" + json.dumps([[r[0], r[4]] for r in matrix]) + r''';
        let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++});
        await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);await page.waitForSelector('#casos.on');
        for(const [id,label]of matrix){await page.evaluate(id=>abrirCaso(id),id);assert.match(await page.locator('#b-caso-proximo').innerText(),new RegExp(label))}
        await page.evaluate(()=>abrirCaso('OS-911-2099'));assert.match(await page.locator('#astra-material-resumo').innerText(),/Falha ficticia de extracao/);
        assert.equal(posts,0);
        ''')

    def test_03_editor_sujo_bloqueia_exploracao_sem_mudar_selecao(self):
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);await page.evaluate(()=>abrirCaso('OS-901-2099'));
        await page.evaluate(()=>abrirEditor('OS-901-2099'));await page.locator('#ed-secoes textarea').first().fill('Rascunho ficticio ainda nao salvo');
        let graphs=0;page.on('request',r=>{if(r.url().includes('/api/grafo?'))graphs++});
        const before=await page.locator('#gr-caso').inputValue();
        page.once('dialog',d=>d.dismiss());await page.evaluate(()=>explorarCasoNoAstra('OS-902-2099','902/2099'));
        assert.equal(await page.locator('#editor').isVisible(),true);
        assert.equal(await page.locator('#ed-secoes textarea').first().inputValue(),'Rascunho ficticio ainda nao salvo');
        assert.equal(await page.locator('#gr-caso').inputValue(),before);assert.equal(graphs,0);
        ''')

    def test_04_resposta_de_ficha_antiga_nao_troca_contexto_e_erro_retenta(self):
        self.control["delay_case"] = True
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);await page.waitForSelector('#casos.on');
        const old=page.evaluate(()=>abrirCaso('OS-901-2099'));await page.waitForTimeout(100);
        await page.evaluate(()=>abrirCaso('OS-902-2099'));await old;
        assert.equal(await page.evaluate(()=>casoAberto),'OS-902-2099');
        assert.match(await page.locator('#astra-material-resumo').innerText(),/0 arquivos originais/);
        assert.equal(await page.locator('#b-explorar-astra').getAttribute('data-caso'),'OS-902-2099');
        ''')
        self.control["fail_case"] = True
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);await page.evaluate(()=>abrirCaso('OS-902-2099'));
        assert.match(await page.locator('#detalhe').innerText(),/Falha de leitura ficticia/);
        await page.locator('#b-caso-retentar').click();await page.locator('#astra-material-resumo').waitFor();
        ''')

    def test_05_sem_indice_nao_inventa_zero_e_leitor_nao_recebe_mutacao(self):
        backup = self.db_path.with_suffix(".guardado")
        self.db_path.replace(backup)
        try:
            self.browser(r'''
            await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);await page.evaluate(()=>abrirCaso('OS-901-2099'));
            await page.locator('#b-explorar-astra').click();await page.waitForFunction(()=>grEstado==='pronto');
            await page.locator('#b-astra-voltar-caso').click();await page.locator('#astra-material-resumo').waitFor();
            assert.match(await page.locator('#astra-material-resumo').innerText(),/índice.*(?:indisponível|não.*disponível)/i);
            assert.doesNotMatch(await page.locator('#astra-material-resumo').innerText(),/0 contas|0 conexões/);
            await context.request.post(url+'/api/sair',{headers:{'X-CPJ':'1'}});
            await context.request.post(url+'/api/entrar',{headers:{'X-CPJ':'1'},data:{login:'leitor_ficticio',senha:'Ficticia123'}});
            await page.reload();await page.evaluate(()=>abrirCaso('OS-901-2099'));
            assert.equal(await page.locator('#b-caso-hipotese').count(),0);
            assert.equal(await page.locator('#b-explorar-astra').count(),1);
            ''')
        finally:
            backup.replace(self.db_path)

    def test_06_grafo_antigo_nao_restaura_filtro_ou_resumo_de_outra_os(self):
        self.control["delay_graph"] = True
        self.browser(r'''
        await page.goto(url+'/#casos');await page.waitForFunction(()=>!document.querySelector('#app').hidden);
        await page.evaluate(()=>abrirCaso('OS-901-2099'));
        const old=page.waitForResponse(r=>r.url().includes('/api/grafo?caso=OS-901-2099'));
        await page.locator('#b-explorar-astra').click();
        await page.locator('#nav [data-a="casos"]').click();await page.evaluate(()=>abrirCaso('OS-902-2099'));
        const current=page.waitForResponse(r=>r.url().includes('/api/grafo?caso=OS-902-2099'));
        await page.locator('#b-explorar-astra').click();await current;await old;
        await page.waitForFunction(()=>grEstado==='pronto');
        assert.equal(await page.locator('#gr-caso').inputValue(),'OS-902-2099');
        assert.match(await page.locator('#b-astra-voltar-caso').innerText(),/902\/2099/);
        await page.locator('#b-astra-voltar-caso').click();await page.locator('#astra-material-resumo').waitFor();
        assert.equal(await page.evaluate(()=>casoAberto),'OS-902-2099');
        assert.match(await page.locator('#astra-material-resumo').innerText(),/0 arquivos originais/);
        assert.doesNotMatch(await page.locator('#astra-material-resumo').innerText(),/2 contas.*retornad/i);
        ''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
