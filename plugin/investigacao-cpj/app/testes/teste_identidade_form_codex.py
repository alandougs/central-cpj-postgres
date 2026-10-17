#!/usr/bin/env python3
"""Regressão da identificação nos formulários de conta; somente marcação e JS estático."""
from pathlib import Path
import re
import unittest


HTML = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")


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
            self.assertIn(helper, HTML, f"helper ausente: {helper}")


if __name__ == "__main__":
    unittest.main()
