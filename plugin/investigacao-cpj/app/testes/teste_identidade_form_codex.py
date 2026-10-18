#!/usr/bin/env python3
"""Regressão da identificação; marcação e navegador com dados fictícios."""
from pathlib import Path
import re
import unittest
from astra_fixture import AstraFixture


HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
JS = (Path(__file__).resolve().parents[1] / "static" / "js" / "sessao.js").read_text(encoding="utf-8")


def form(id_: str) -> str:
    match = re.search(rf'<form\b[^>]*\bid="{re.escape(id_)}"[^>]*>(.*?)</form>', HTML, re.S)
    if not match:
        raise AssertionError(f"form #{id_} não encontrado")
    return match.group(1)


class IdentidadeFormTests(unittest.TestCase):
    def test_nome_usa_autopreenchimento_do_navegador(self):
        for form_id in ("f-setup", "f-usuario"):
            with self.subTest(form=form_id):
                self.assertRegex(form(form_id), r'<input\b[^>]*name="nome"[^>]*autocomplete="name"', form_id)

    def test_cargos_comuns_e_outro_editavel_nos_formularios(self):
        cargos = ("Delegado de Polícia", "Escrivão de Polícia", "Investigador de Polícia", "Agente de Polícia")
        for form_id in ("f-setup", "f-usuario", "f-conta"):
            with self.subTest(form=form_id):
                conteudo = form(form_id)
                self.assertRegex(conteudo, r'<select\b[^>]*data-cargo-select', form_id)
                self.assertRegex(conteudo, r'<input\b[^>]*data-cargo-outro', form_id)
                for cargo in cargos:
                    self.assertIn(cargo, conteudo, f"{form_id}: cargo ausente: {cargo}")

    def test_cpf_tem_marcacao_para_mascara(self):
        for form_id in ("f-setup", "f-usuario"):
            with self.subTest(form=form_id):
                self.assertRegex(form(form_id), r'<input\b[^>]*name="cpf"[^>]*data-cpf-format', form_id)

    def test_script_aplica_formatacao_e_le_cargo_selecionado_ou_personalizado(self):
        for helper in ("function formatarCpf", "function valorCargo", "function selecionarCargo"):
            self.assertIn(helper, JS, f"helper ausente: {helper}")


class IdentidadeBrowserTests(AstraFixture, unittest.TestCase):
    def test_cpf_cargo_personalizado_e_reset_preservam_valores(self):
        self.browser(r'''
        await page.goto(url);await page.waitForSelector('#app:not([hidden])');
        const result=await page.evaluate(()=>{
          const valores=[];
          for(const id of ['f-setup','f-usuario','f-conta']){
            const f=document.getElementById(id),s=f.querySelector('[data-cargo-select]'),o=f.querySelector('[data-cargo-outro]');
            selecionarCargo(f,'Cargo fictício personalizado');
            valores.push([s.value,o.hidden,o.disabled,valorCargo(f)]);
            s.value='Investigador de Polícia';s.dispatchEvent(new Event('change'));
            valores.push([o.hidden,o.disabled,valorCargo(f)]);
            selecionarCargo(f,'Cargo fictício personalizado');f.reset();
            valores.push([o.hidden,o.disabled,valorCargo(f)]);
          }
          for(const id of ['f-setup','f-usuario']){
            const c=document.getElementById(id).elements.cpf;
            c.value='00000000000';c.dispatchEvent(new Event('input'));
            valores.push(c.value);
            c.value='000.000.000-00EXCESSO';c.dispatchEvent(new Event('input'));
            valores.push(c.value);
          }
          return valores;
        });
        assert.deepEqual(result,[
          ...Array.from({length:3},()=>[
            ['outro',false,false,'Cargo fictício personalizado'],[true,true,'Investigador de Polícia'],[true,true,'']
          ]).flat(),...Array(4).fill('000.000.000-00')
        ]);
        ''')

    def test_envio_dos_tres_formularios_usa_cargo_selecionado_ou_personalizado(self):
        self.browser(r'''
        const enviados=[];
        for(const endpoint of ['/api/configurar','/api/usuarios','/api/minha-conta']){
          await page.route('**'+endpoint,async route=>{
            if(route.request().method()!=='POST')return route.continue();
            enviados.push([endpoint,route.request().postDataJSON()]);
            await route.fulfill({status:200,contentType:'application/json',body:'{}'});
          });
        }
        await page.goto(url);await page.waitForSelector('#app:not([hidden])');
        await page.evaluate(async()=>{
          for(const id of ['f-setup','f-usuario','f-conta']){
            const f=document.getElementById(id);
            if(f.elements.nome)f.elements.nome.value='Operador fictício';
            if(f.elements.login)f.elements.login.value='operador_ficticio';
            if(f.elements.senha)f.elements.senha.value='Ficticia123';
            if(f.elements.senha2)f.elements.senha2.value='Ficticia123';
            selecionarCargo(f,id==='f-conta'?'Cargo fictício personalizado':'Investigador de Polícia');
            await f.onsubmit({preventDefault(){},target:f});
          }
        });
        assert.equal(enviados.length,3);
        assert.deepEqual(enviados.map(([p,d])=>[p,d.cargo]),[
          ['/api/configurar','Investigador de Polícia'],['/api/usuarios','Investigador de Polícia'],['/api/minha-conta','Cargo fictício personalizado']
        ]);
        ''')


if __name__ == "__main__":
    unittest.main()
