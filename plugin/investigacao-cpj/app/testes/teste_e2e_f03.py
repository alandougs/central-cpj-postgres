#!/usr/bin/env python3
"""Teste E2E automatizado com navegador headless (Playwright / Edge) — Tarefa F03.

Valida os 8 fluxos principais da Central CPJ:
1. Abertura da Central em modo solo (bypass de login e restrições solo).
2. Cadastro de Nova O.S. com PDF sintético (gerado com texto, extrato e imagem OCR).
3. Acompanhamento do progresso do OCR em tempo real até conclusão.
4. Abertura do caso com inspeção de transcricao.md e tabelas CSV.
5. Edição e salvamento de minuta investigativa fictícia.
6. Geração de relatório DOCX no modelo oficial CPJ 2026.
7. Definição do relatório como FINAL e baixa na produção.
8. Atualização das métricas no painel de estatísticas.

Restrições monitoradas:
- Zero erros de console (JavaScript / exceções).
- Zero respostas HTTP 5xx em todas as requisições.
- Execução em menos de 5 minutos com Edge headless pré-instalado.
"""
import os
from pathlib import Path
import sys
import time
import unittest

AQUI = Path(__file__).resolve().parent
APP_DIR = AQUI.parent
PLUGIN_DIR = APP_DIR.parent
ROOT_DIR = PLUGIN_DIR.parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from testes.e2e.navegador_aux import (  # noqa: E402
    PLAYWRIGHT_INSTALADO,
    SessaoNavegador,
    verificar_playwright_edge,
)
from testes.e2e.pdf_aux import gerar_pdf_sintetico_e2e  # noqa: E402
from testes.e2e.servidor_aux import ServidorTesteE2E  # noqa: E402


class TesteE2EF03CentralCPJ(unittest.TestCase):
    servidor: ServidorTesteE2E = None
    pdf_teste: Path = None

    @classmethod
    def setUpClass(cls):
        ok, motivo = verificar_playwright_edge()
        if not ok:
            raise unittest.SkipTest(motivo)

        cls.porta = 8766
        cls.servidor = ServidorTesteE2E(porta=cls.porta)
        cls.servidor.iniciar(timeout=25.0)

        # Gera PDF sintético de teste (3 páginas texto + 1 escaneada para OCR)
        cls.pdf_teste = cls.servidor.ws / "inquerito_ficticio_e2e.pdf"
        cls.total_paginas = gerar_pdf_sintetico_e2e(cls.pdf_teste, paginas_texto=3, paginas_imagem=1)

    @classmethod
    def tearDownClass(cls):
        if cls.servidor is not None:
            cls.servidor.parar()

    def test_fluxo_completo_e2e_central_cpj(self):
        t_inicio = time.monotonic()

        with SessaoNavegador() as sessao:
            page = sessao.page

            # -------------------------------------------------------------
            # 1. Abertura da Central em modo solo
            # -------------------------------------------------------------
            page.goto(self.servidor.url, wait_until="networkidle")

            # Verifica que o app principal está visível e a tela de login oculta
            page.wait_for_selector("#app:not([hidden])", timeout=10000)
            self.assertTrue(page.locator("#tela-login").is_hidden())

            # Verifica dados do usuário solo no cabeçalho
            texto_usuario = page.locator("#u-nome").inner_text()
            self.assertIn("Alan Douglas Silva", texto_usuario)
            self.assertIn("Investigador de Polícia", texto_usuario)

            # Verifica que botões e cartões proibidos no modo solo estão ocultos
            self.assertTrue(page.locator("#b-sair").is_hidden())
            self.assertTrue(page.locator("#card-usuarios").is_hidden())
            self.assertTrue(page.locator("#card-perfis").is_hidden())
            self.assertTrue(page.locator("#card-rede").is_hidden())

            # -------------------------------------------------------------
            # 2. Nova O.S. com PDF sintético
            # -------------------------------------------------------------
            page.locator("#nav button[data-a='nova']").click()
            page.wait_for_selector("#nova.on", timeout=5000)

            # Upload do PDF pelo input de arquivos
            page.set_input_files("#arqs", str(self.pdf_teste))
            page.wait_for_selector("#lista-arq li", timeout=5000)

            # Aguarda a detecção inicial da O.S. estabilizar antes do envio
            page.wait_for_timeout(1500)

            # Envia para processamento
            page.locator("#b-enviar").click()

            # Aguarda mensagem de sucesso e captura o ID do caso criado
            page.wait_for_selector("#msg-up b", timeout=15000)
            caso_id = page.locator("#msg-up b").inner_text().strip()
            self.assertTrue(
                caso_id.startswith("OS-") or caso_id.startswith("RECEBIDO-"),
                f"ID de caso inesperado: {caso_id}",
            )

            # -------------------------------------------------------------
            # 3. Acompanhamento do progresso do OCR em tempo real
            # -------------------------------------------------------------
            # Aguarda a fila processar o arquivo até concluir (ou sair da fila)
            # O trabalhador em background roda OCR, extração de texto, tabelas e entidades.
            limite_ocr = time.monotonic() + 90.0
            concluido = False
            ultimo_texto = ""
            while time.monotonic() < limite_ocr:
                page.wait_for_timeout(2000)
                ultimo_texto = page.locator("#fila").inner_text()
                badges_ok = page.locator("#fila .badge.b-ok").count()
                badges_err = page.locator("#fila .badge.b-err").count()

                self.assertEqual(badges_err, 0, f"Erro detectado no processamento do OCR: {ultimo_texto}")

                if badges_ok > 0 or "concluído" in ultimo_texto.lower() or "nada na fila" in ultimo_texto.lower():
                    concluido = True
                    break

            log_servidor = self.servidor.ler_log()
            self.assertTrue(
                concluido,
                f"Timeout aguardando processamento do OCR na fila. Último estado: '{ultimo_texto}'. Log:\n{log_servidor[-2000:]}",
            )

            # -------------------------------------------------------------
            # 4. Abertura do caso: inspeção de transcricao.md e CSV
            # -------------------------------------------------------------
            page.locator("#nav button[data-a='casos']").click()
            page.wait_for_selector("#casos.on", timeout=5000)

            # Clica no caso na tabela de casos
            page.wait_for_selector(f"#t-casos tr[data-id='{caso_id}']", timeout=10000)
            page.locator(f"#t-casos tr[data-id='{caso_id}']").click()

            # Detalhes do caso carregados
            page.wait_for_selector("#detalhe h3", timeout=10000)
            detalhe_h3 = page.locator("#detalhe h3").inner_text()
            self.assertIn(caso_id, detalhe_h3)

            # Verifica links dos arquivos de extração (transcricao.md e tabelas CSV)
            links_arquivos = page.locator("#detalhe .arqs a").all_inner_texts()
            tem_transcricao = any(l.endswith("transcricao.md") for l in links_arquivos)
            tem_csv = any(l.endswith(".csv") for l in links_arquivos)

            self.assertTrue(tem_transcricao, f"transcricao.md não listada nos arquivos: {links_arquivos}")
            self.assertTrue(tem_csv, f"Nenhum arquivo CSV gerado na extração: {links_arquivos}")

            # Verifica conteúdo do transcricao.md via requisição do navegador
            link_transcricao = [l for l in links_arquivos if l.endswith("transcricao.md")][0]
            resp_md = page.request.get(f"{self.servidor.url}/arquivo/{caso_id}/{link_transcricao}")
            self.assertEqual(resp_md.status, 200)
            conteudo_md = resp_md.text()
            self.assertIn("## Página 1", conteudo_md)
            self.assertIn("## Página", conteudo_md)

            # -------------------------------------------------------------
            # 5. Edição e salvamento de minuta fictícia
            # -------------------------------------------------------------
            page.locator("#b-nova-minuta").click()
            page.locator("#editor").wait_for(state="visible", timeout=5000)

            # Preenche seções da minuta
            page.locator("#ed-secoes textarea[data-s='RESUMO DOS FATOS']").fill(
                "Inquérito policial instaurado para apurar suposto golpe do Pix com prejuízo financeiro."
            )
            page.locator("#ed-secoes textarea[data-s='DILIGÊNCIAS REALIZADAS']").fill(
                "Análise documental dos extratos bancários e identificação da titularidade da conta recebedora."
            )
            page.locator("#ed-secoes textarea[data-s='CONCLUSÃO']").fill(
                "Apurados indícios suficientes de autoria e materialidade em face do titular da conta."
            )

            # Salva minuta e solicita geração do DOCX
            page.locator("#ed-salvar").click()
            page.locator("#editor").wait_for(state="hidden", timeout=15000)

            # -------------------------------------------------------------
            # 6. Verificação do DOCX gerado no modelo CPJ 2026
            # -------------------------------------------------------------
            page.wait_for_selector("#detalhe table a[href$='.docx']", timeout=10000)
            link_docx = page.locator("#detalhe table a[href$='.docx']").first
            href_docx = link_docx.get_attribute("href")
            self.assertTrue(href_docx.endswith(".docx"))

            # Valida download do DOCX gerado
            resp_docx = page.request.get(f"{self.servidor.url}{href_docx}")
            self.assertEqual(resp_docx.status, 200)
            self.assertGreater(len(resp_docx.body()), 5000, "Arquivo DOCX gerado está vazio ou truncado.")

            # -------------------------------------------------------------
            # 7. Definir relatório como FINAL e baixa na produção
            # -------------------------------------------------------------
            # O handler de diálogo em SessaoNavegador aceita automaticamente o confirm()
            page.locator("#detalhe button[data-final]").first.click()

            # Aguarda a atualização da tela com o relatório final e baixa
            page.wait_for_selector(f"#detalhe a:has-text('RELATORIO-{caso_id}-FINAL.docx')", timeout=30000)

            texto_detalhe = page.locator("#detalhe").inner_text()
            self.assertIn("Baixa em", texto_detalhe)
            self.assertIn("concluído", texto_detalhe.lower())

            # -------------------------------------------------------------
            # 8. Conferir o painel de estatísticas
            # -------------------------------------------------------------
            page.locator("#nav button[data-a='estatisticas']").click()
            page.wait_for_selector("#estatisticas.on", timeout=5000)

            # Verifica carregamento do iframe do painel
            page.wait_for_selector("#if-painel[src]", timeout=5000)

            # Valida que o endpoint /painel responde com HTTP 200. O painel é gerado em segundo plano:
            # enquanto isso a rota devolve a página "Atualizando as estatísticas…" (C04); aguarda até 30 s.
            limite = time.time() + 30
            while True:
                resp_painel = page.request.get(f"{self.servidor.url}/painel")
                self.assertEqual(resp_painel.status, 200)
                texto_painel = resp_painel.text()
                if "Atualizando as estatísticas" not in texto_painel or time.time() > limite:
                    break
                time.sleep(1)
            self.assertIn("Painel de Produção", texto_painel)
            self.assertIn(f'"id": "{caso_id}"', texto_painel, "Caso fictício com baixa não aparece no painel")

            # -------------------------------------------------------------
            # Restrições obrigatórias: zero console errors e zero HTTP 5xx
            # -------------------------------------------------------------
            self.assertEqual(
                sessao.erros_console,
                [],
                f"Erros de console detectados durante os testes: {sessao.erros_console}",
            )
            self.assertEqual(
                sessao.erros_pagina,
                [],
                f"Exceções não tratadas na página: {sessao.erros_pagina}",
            )
            self.assertEqual(
                sessao.respostas_5xx,
                [],
                f"Respostas HTTP 5xx detectadas: {sessao.respostas_5xx}",
            )

        tempo_total = time.monotonic() - t_inicio
        print(f"\n[E2E F03] Suíte completa executada com sucesso em {tempo_total:.2f}s (< 300s).")
        self.assertLess(tempo_total, 300.0, f"Tempo de execução excedeu 5 minutos: {tempo_total}s")


if __name__ == "__main__":
    unittest.main()
