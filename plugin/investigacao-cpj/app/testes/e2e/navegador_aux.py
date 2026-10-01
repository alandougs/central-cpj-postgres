"""Gerenciador do navegador Microsoft Edge via Playwright para testes E2E."""
from typing import List, Tuple

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright
    PLAYWRIGHT_INSTALADO = True
except ImportError:
    PLAYWRIGHT_INSTALADO = False


def verificar_playwright_edge() -> Tuple[bool, str]:
    """Verifica se o pacote playwright e o Microsoft Edge estão disponíveis para execução."""
    if not PLAYWRIGHT_INSTALADO:
        return False, "Pacote python 'playwright' não está instalado."
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            browser.close()
        return True, "Playwright e Microsoft Edge disponíveis."
    except Exception as e:
        return False, f"Falha ao inicializar Microsoft Edge via Playwright: {e}"


class SessaoNavegador:
    """Gerencia a sessão de teste do navegador Edge headless com rastreamento de erros."""

    def __init__(self, viewport={"width": 1366, "height": 768}):
        self.viewport = viewport
        self.pw: Playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.erros_console: List[str] = []
        self.erros_pagina: List[str] = []
        self.respostas_5xx: List[str] = []

    def __enter__(self):
        if not PLAYWRIGHT_INSTALADO:
            raise RuntimeError("Playwright não instalado.")
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(channel="msedge", headless=True)
        self.context = self.browser.new_context(viewport=self.viewport)
        self.page = self.context.new_page()

        # Listeners para capturar erros em tempo real
        def on_console(msg):
            if msg.type == "error":
                self.erros_console.append(f"[{msg.type.upper()}] {msg.text}")

        def on_page_error(exc):
            self.erros_pagina.append(str(exc))

        def on_response(resp):
            if resp.status >= 500:
                self.respostas_5xx.append(f"HTTP {resp.status} em {resp.url}")

        self.page.on("console", on_console)
        self.page.on("pageerror", on_page_error)
        self.page.on("response", on_response)

        # Dialog handler automático (ex.: confirmações de "definir FINAL")
        self.page.on("dialog", lambda dialog: dialog.accept())

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.pw:
            try:
                self.pw.stop()
            except Exception:
                pass
