#!/usr/bin/env python3
"""Teste focado na tarefa F01: visual e usabilidade da Central (index.html)."""
import os
import re
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
INDEX = os.path.join(APP, "static", "index.html")


class TesteInterfaceF01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(INDEX, encoding="utf-8") as f:
            cls.html = f.read()

    # ---- sem dependência externa (regra 6 do AGENTS.md / HTML-CSS-JS puros) ----
    def test_sem_url_externa(self):
        urls = re.findall(r'(?:href|src)=["\']https?://[^"\']+["\']', self.html)
        self.assertFalse(urls, f"URLs externas encontradas: {urls}")

    def test_sem_cdn_nem_fonte_externa(self):
        for termo in ("cdn.", "googleapis.com", "fonts.google", "unpkg.com", "jsdelivr.net"):
            self.assertNotIn(termo, self.html, f"referência externa detectada: {termo}")

    def test_sem_framework(self):
        for termo in ("react", "vue.", "angular", "jquery"):
            self.assertNotIn(termo, self.html.lower())

    # ---- elementos-chave preservados (IDs e chamadas de API) ----
    def test_ids_chave_presentes(self):
        ids_obrigatorios = [
            "tela-login", "tela-setup", "tela-trocar", "app", "nav",
            "chip-tarefas", "u-nome", "b-sair", "tema",
            "inicio", "nova", "casos", "pesquisa", "estatisticas", "sistema",
            "f-os", "drop", "arqs", "fila", "t-casos", "detalhe",
            "f-pessoas", "r-pessoas", "editor", "toast",
        ]
        for i in ids_obrigatorios:
            self.assertIn(f'id="{i}"', self.html, f'id ausente: {i}')

    def test_chamadas_api_preservadas(self):
        endpoints = [
            "/api/sessao", "/api/entrar", "/api/configurar", "/api/os",
            "/api/casos", "/api/pesquisa/pessoas", "/api/tarefas",
            "/api/plantao/agentes", "/api/perfis", "/api/usuarios",
        ]
        for e in endpoints:
            self.assertIn(e, self.html, f"endpoint ausente: {e}")

    def test_modo_solo_preservado(self):
        # E02: campo solo da sessão continua condicionando a interface
        self.assertIn("S.solo", self.html)
        self.assertIn('s.solo', self.html)

    # ---- tema claro/escuro ----
    def test_tema_claro_escuro_presente(self):
        self.assertIn('data-theme="dark"', self.html)
        self.assertIn("prefers-color-scheme:dark", self.html)
        self.assertIn('id="tema"', self.html)

    # ---- estados de carregamento/erro/vazio ----
    def test_estados_de_interface_presentes(self):
        self.assertIn("vazio", self.html)  # classe .vazio para estado vazio
        self.assertIn("barraHTML", self.html)  # indicador de carregamento
        self.assertIn("aviso alerta", self.html)  # estado de erro

    # ---- acessibilidade ----
    def test_botao_icone_tem_aria_label(self):
        m = re.search(r'<button[^>]*id="tema"[^>]*>', self.html)
        self.assertIsNotNone(m)
        self.assertIn("aria-label", m.group(0))

    def test_decorativos_tem_aria_hidden(self):
        self.assertNotIn("<i></i>", self.html)
        self.assertIn('<i aria-hidden="true"></i>', self.html)

    def test_campos_de_formulario_tem_label(self):
        # cada <label> aparece antes de um controle de formulário (regra geral do padrão já usado)
        self.assertGreater(self.html.count("<label"), 20)

    def test_mensagens_tem_regiao_viva(self):
        self.assertIn('aria-live="polite"', self.html)

    def test_foco_visivel_definido(self):
        self.assertIn(":focus-visible", self.html)

    def test_meta_theme_color(self):
        self.assertIn('name="theme-color"', self.html)

    # ---- limite de crescimento do arquivo (regra da tarefa: no máx. +15%) ----
    def test_tamanho_dentro_do_limite(self):
        tamanho = len(self.html.encode("utf-8"))
        limite = int(85881 * 1.15)
        self.assertLessEqual(tamanho, limite, f"index.html cresceu além de 15%: {tamanho} bytes (limite {limite})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
