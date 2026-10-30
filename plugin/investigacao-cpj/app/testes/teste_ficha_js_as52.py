"""Executa casos.js com DOM mínimo e entradas sintéticas, sem navegador/rede."""
import json
from pathlib import Path
import subprocess
import unittest


class FichaJSAS52(unittest.TestCase):
    def test_renderizacao_literal_e_patch_com_cas(self):
        fonte = Path(__file__).resolve().parents[1] / "static/js/casos.js"
        harness = r"""
const fs=require('fs'),vm=require('vm');
const elementos=new Map(),enviados=[];
const fields=[{dataset:{k:'status'},value:'recebido',disabled:false},{dataset:{k:'observacoes'},value:'',disabled:false}];
fields.map=undefined; // querySelectorAll devolve NodeList, que não oferece Array.map.
const $=k=>{if(!elementos.has(k))elementos.set(k,{innerHTML:'',value:'',hidden:false,checked:false,style:{},dataset:{},classList:{toggle(){},contains(){return false}},scrollIntoView(){}});return elementos.get(k)};
const malPagina='<img src=x onerror=alert(1)>',malFonte='<svg onload=alert(2)>';
const j={caso:{id:'OS-FAKE-2099',status:'recebido',revisao:7,documentos:[{arquivo:'teste.pdf',paginas:malPagina}],preenchimento_os:{ia:'dispensada',pendentes:[],fontes:{bo:{documento:'teste.pdf',pagina:malFonte,trecho:'ficticio',metodo:'texto'}}}},
 resumo:{},processamento:{trabalhos:[]},relatorios:[],arquivos:[],trabalho:true,local:true};
const ctx={$, $$:k=>k==='#detalhe [data-k]'?fields:[],window:{},document:{addEventListener(){}},S:{usuario:{login:'ficticio',perfil:'admin'}},edCaso:null,MOD:[],ST:[],
 enc:encodeURIComponent,esc:s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 api:async(url,op)=>{if(op?.json){enviados.push(op.json);return {revisao:8}}if(url==='/api/responsaveis')return [];if(url.includes('?'))return [];return j},
 toast(){},confirmarSaidaEditor:()=>true,requestAnimationFrame:fn=>fn(),prazoBadge:()=>'',badge:()=>'',dt:()=>'',hoje:()=>'',kb:()=>'',
 carregarAgentes:async()=>null,localStorage:{getItem:()=>null},setTimeout,clearTimeout};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
vm.runInContext('painelInvestigativo=()=>""; atualizarIA=()=>{};',ctx);
(async()=>{await ctx.abrirCaso('OS-FAKE-2099',false);const html=$('#detalhe').innerHTML;fields[1].value='anotacao';await $('#b-salvar').onclick();
 console.log(JSON.stringify({html,enviados}));})().catch(e=>{console.error(e);process.exit(1)});
"""
        r = subprocess.run(["node", "-", str(fonte)], input=harness, text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        resultado = json.loads(r.stdout)
        with self.subTest("CAS e patch"):
            self.assertEqual(resultado["enviados"], [{"origem_edicao": "ficha", "revisao": 7, "observacoes": "anotacao"}])
        self.assertNotIn("<img src=x", resultado["html"])
        self.assertNotIn("<svg onload", resultado["html"])
        self.assertIn("&lt;img src=x", resultado["html"])
        self.assertIn("&lt;svg onload", resultado["html"])

    def test_modal_docx_exige_aceite_e_envia_hash_conferido(self):
        fonte = Path(__file__).resolve().parents[1] / "static/js/casos.js"
        harness = r"""
const fs=require('fs'),vm=require('vm'),elementos=new Map(),enviados=[];
const $=k=>{if(!elementos.has(k))elementos.set(k,{innerHTML:'',value:'',hidden:false,checked:false});return elementos.get(k)};
const ctx={$,window:{},document:{addEventListener(){}},enc:encodeURIComponent,esc:s=>String(s??''),alert(){},toast(){},api:async(u,op)=>enviados.push(op.json)};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
ctx.abrirCaso=()=>{};ctx.carregarCasos=()=>{};
(async()=>{ctx.mostrarModalFinalRessalva('OS-FAKE-2099','ficticio.docx',{achados:[],artefato:{exige_aceite_docx:true,sha256_docx:'a'.repeat(64)}});
 $('#final-ressalva-texto').value='Conferi o documento editado no Word.';
 await $('#b-confirmar-final-ressalva').onclick();const antes=enviados.length;
 $('#final-aceite-docx').checked=true;await $('#b-confirmar-final-ressalva').onclick();console.log(JSON.stringify({antes,enviados}));})();
"""
        r = subprocess.run(["node", "-", str(fonte)], input=harness, text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        resultado = json.loads(r.stdout)
        self.assertEqual(resultado["antes"], 0)
        self.assertEqual(resultado["enviados"][0]["confirmar_docx_sha256"], "a" * 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
