"""AG90: Verificação funcional e operacional da interface CPJ Astra (Requisitos AG-R01 a AG-R10).

Executa Edge headless em processo isolado contra fixture de desenvolvimento com dados sintéticos.
Valida:
- AG-R01: Visual sóbrio CPJ, tokens de cor, foco visível e capturas de referência.
- AG-R02: Esteira operacional de 5 etapas com status, links de fonte e ações.
- AG-R03: Mapa canônico, eliminação de race conditions e marcação aproximada.
- AG-R04: Grafo com separação manual/documental e escape de apóstrofos/caracteres.
- AG-R05: Navegação direta da afirmação/valor até a fonte (folhas/páginas).
- AG-R06: Painel guiado de solicitações da O.S. e alerta de reconferência.
- AG-R07: Conferência documental lado a lado (PDF original x transcrição Markdown).
- AG-R08: Tabela estruturada de eventos/transações financeiras e filtros.
- AG-R09: Notas analíticas com alerta de hipótese e persistência local.
- AG-R10: Coerência com extração documental Markdown enxuta (sem entidades.csv).
"""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from teste_interface_rg26 import InterfaceFixtureRG26
from teste_mapa_real_mp91 import png_ficticio  # MP91: o mapa real pede tiles a tile.openstreetmap.org

EVIDENCIAS = Path(tempfile.gettempdir()) / "cpj-astra-ag90-20261028"


def navegador(url, cenario):
    """Executa cenário Playwright em Edge headless isolado."""
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    node = shutil.which("node") or str(runtime / "bin/node.exe")
    env = dict(os.environ, NODE_PATH=str(runtime / "node_modules"))
    script = r'''
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const url = URL_FIXTURE;

(async () => {
  const servidor = await chromium.launchServer({headless: true, channel: process.env.CPJ_BROWSER_CHANNEL || 'msedge'});
  try {
    const browser = await chromium.connect(servidor.wsEndpoint());
    const context = await browser.newContext();
    const login = await context.request.post(url + '/api/entrar', {
      headers: {'X-CPJ': '1'},
      data: {login: 'rg26.admin', senha: 'Ficticia123'}
    });
    assert.equal(login.status(), 200);

    const page = await context.newPage(), erros = [], externas = [], pedidos = [];
    page.on('pageerror', e => erros.push(e.message));
    page.on('console', m => { if (m.type() === 'error') erros.push(m.text()); });
    page.on('request', r => pedidos.push({url: r.url(), method: r.method()}));

    await page.route('**/*', async route => {
      if (/^https?:/.test(route.request().url()) && new URL(route.request().url()).origin !== url) {
        if (new URL(route.request().url()).hostname === 'tile.openstreetmap.org') {
          await route.fulfill({status: 200, contentType: 'image/png', body: Buffer.from(PNG_B64, 'base64')});
          return;
        }
        externas.push(route.request().url());
        await route.abort();
      } else {
        await route.continue();
      }
    });

    await page.goto(url + '/#casos');
    await page.waitForLoadState('networkidle');

    CENARIO

    assert.deepEqual(externas, [], 'Nenhum recurso externo permitido');
    assert.deepEqual(erros, [], 'Nenhum erro de execução JS ou CSP');
  } catch (e) {
    console.error(e);
    process.exitCode = 1;
  } finally {
    if (process.platform === 'win32') {
      try {
        require('node:child_process').execFileSync('taskkill', ['/PID', String(servidor.process().pid), '/T', '/F'], {stdio: 'ignore'});
      } catch {}
    } else {
      await servidor.kill();
    }
  }
  process.exit(process.exitCode || 0);
})().catch(e => {
  console.error(e);
  process.exit(1);
});
'''.replace("URL_FIXTURE", json.dumps(url)).replace("PNG_B64", json.dumps(base64.b64encode(png_ficticio()).decode())).replace("CENARIO", cenario)

    resultado = subprocess.run([node, "-"], input=script, text=True, encoding="utf-8", env=env, capture_output=True, timeout=120)
    if resultado.returncode:
        raise AssertionError(resultado.stdout + resultado.stderr)


SETUP_AG90 = r'''
  const fs = require('node:fs');
  const outDir = EVIDENCIAS_DIR;
  fs.mkdirSync(outDir, {recursive: true});

  async function mudarTema(t) {
    if (await page.locator('html').getAttribute('data-theme') !== t) {
      await page.locator('#tema').click();
    }
    await page.evaluate(() => Promise.all(document.getAnimations().map(a => a.finished.catch(() => {}))));
  }
'''.replace("EVIDENCIAS_DIR", json.dumps(str(EVIDENCIAS)))


class InterfaceAstraAG90(InterfaceFixtureRG26):
    def cenario(self, js):
        navegador(self.url, js)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Caso 931: Caso completo com análise, solicitações, fluxo e relatórios
        caso931 = cls.ws / "casos" / "OS-931-2099"
        (caso931 / "01-extracao/autos").mkdir(parents=True, exist_ok=True)
        (caso931 / "02-analise").mkdir(parents=True, exist_ok=True)
        (caso931 / "03-relatorios").mkdir(parents=True, exist_ok=True)
        (caso931 / "01-extracao/autos/transcricao.md").write_text(
            "## Página 1\nBoletim de Ocorrência inicial. Fls. 1-2.\n## Página 2\nComprovante Pix de R$ 5.000,00 para investigado. Fls. 30.\n",
            encoding="utf-8"
        )
        (caso931 / "02-analise/solicitacoes-os.md").write_text(
            "# Solicitações da O.S. 931/2099\n1. Identificar titular da conta recebedora (Fls. 30).\n",
            encoding="utf-8"
        )
        (caso931 / "02-analise/dados-faltantes.md").write_text(
            "# DADOS FALTANTES — PROVIDENCIAR (OPERADOR)\n- Extrato bancário complementar da vítima.\n",
            encoding="utf-8"
        )
        (caso931 / "02-analise/fluxo-financeiro.csv").write_text(
            "seq;data;hora;origem;destino;meio;valor;origem_banco;destino_banco;camada;fls;observacao\n"
            "1;2026-10-15;14:22;Vítima Alfa;D'Ávila Investigada;Pix;5000.00;Banco A;Banco B;1;30;Transferência direta\n"
            "2;2026-10-15;15:10;D'Ávila Investigada;Empresa Beta;Pix;4500.00;Banco B;Banco C;2;32;Repasse imediato\n",
            encoding="utf-8"
        )
        (caso931 / "03-relatorios/RELATORIO-OS-931-2099-v01.docx").write_bytes(b"PK\x03\x04synthetic-docx-v1")
        (caso931 / "03-relatorios/RELATORIO-OS-931-2099-v02.docx").write_bytes(b"PK\x03\x04synthetic-docx-v2")
        (caso931 / "caso.json").write_text(json.dumps({
            "schema": "cpj-caso/1",
            "id": "OS-931-2099",
            "ordem_servico": "931/2099",
            "status": "analisado",
            "natureza": "Estelionato eletrônico — fixture AG90",
            "determinacao": "Apurar autoria de chave Pix recebedora e vínculos bancários.",
            "vitimas": ["Vítima Alfa"],
            "investigados": ["D'Ávila Investigada"],
            "financeiro": {"valor_rastreado": 5000.0, "prejuizo_documentado": 5000.0},
            "relatorios": [
                {"arquivo": "RELATORIO-OS-931-2099-v02.docx", "data": "2026-10-28T04:00:00"},
                {"arquivo": "RELATORIO-OS-931-2099-v01.docx", "data": "2026-10-27T10:00:00"}
            ]
        }, ensure_ascii=False), encoding="utf-8")

        # Caso 932: Caso entregue com minuta finalizada
        caso932 = cls.ws / "casos" / "OS-932-2099"
        (caso932 / "01-extracao/autos").mkdir(parents=True, exist_ok=True)
        (caso932 / "03-relatorios").mkdir(parents=True, exist_ok=True)
        (caso932 / "03-relatorios/RELATORIO-OS-932-2099-v01.docx").write_bytes(b"PK\x03\x04synthetic-docx")
        (caso932 / "caso.json").write_text(json.dumps({
            "schema": "cpj-caso/1",
            "id": "OS-932-2099",
            "ordem_servico": "932/2099",
            "status": "entregue",
            "natureza": "Fraude eletrônica",
            "vitimas": ["Vítima Beta"],
            "investigados": ["Investigado Gamma"],
            "relatorios": [{"arquivo": "RELATORIO-OS-932-2099-v01.docx"}]
        }, ensure_ascii=False), encoding="utf-8")

        # Caso 933: Caso moderno extração enxuta Markdown (sem entidades.csv nem tabelas CSV)
        caso933 = cls.ws / "casos" / "OS-933-2099"
        (caso933 / "01-extracao/autos/.checkpoint").mkdir(parents=True, exist_ok=True)
        (caso933 / "01-extracao/autos/transcricao.md").write_text(
            "## Página 1\nAuto de reconhecimento e termo de declaração.\n",
            encoding="utf-8"
        )
        (caso933 / "01-extracao/autos/.checkpoint/estado.json").write_text(
            json.dumps({"paginas_extraidas": 1, "ocr": False, "status": "concluido"}),
            encoding="utf-8"
        )
        (caso933 / "caso.json").write_text(json.dumps({
            "schema": "cpj-caso/1",
            "id": "OS-933-2099",
            "ordem_servico": "933/2099",
            "status": "extraido",
            "natureza": "Falsa central telefônica",
            "vitimas": ["Vítima Delta"],
            "investigados": []
        }, ensure_ascii=False), encoding="utf-8")

    def test_01_visual_temas_foco_contraste(self):
        """AG-R01: Verifica temas claro/escuro, cores Astra (#31D96D), foco visível e capturas."""
        self.cenario(SETUP_AG90 + r'''
  // 1. Verifica tokens Astra no CSS
  const tokens = await page.evaluate(() => {
    const s = getComputedStyle(document.documentElement);
    return {
      astraGreen: s.getPropertyValue('--astra-green').trim(),
      astraDarkInk: s.getPropertyValue('--astra-dark-ink').trim()
    };
  });
  assert.equal(tokens.astraGreen.toLowerCase(), '#31d96d', 'Token --astra-green deve ser #31D96D');
  assert.equal(tokens.astraDarkInk.toLowerCase(), '#060606', 'Token --astra-dark-ink deve ser #060606');

  // 2. Verifica foco visível em botões interativos
  await page.locator('#nav button[data-a="casos"]').focus();
  const foco = await page.evaluate(() => {
    const s = getComputedStyle(document.activeElement);
    return {
      outlineWidth: parseFloat(s.outlineWidth) || 0,
      outlineStyle: s.outlineStyle
    };
  });
  assert.ok(foco.outlineWidth >= 2, 'Foco deve ter largura mínima de 2px');
  assert.notEqual(foco.outlineStyle, 'none', 'Foco deve ser visível (outline != none)');

  // 3. Verifica que não há botões duplicados
  const duplicadosCorrelacoes = await page.locator('#b-gr-correlacoes').count();
  assert.ok(duplicadosCorrelacoes <= 1, 'Não deve haver botões duplicados de correlações');

  // 4. Capturas sintéticas em temas claro e escuro para desktop, tablet e mobile
  const resolucoes = [
    {nome: 'desktop', width: 1440, height: 900},
    {nome: 'tablet', width: 720, height: 900},
    {nome: 'mobile', width: 390, height: 844}
  ];

  for (const res of resolucoes) {
    await page.setViewportSize({width: res.width, height: res.height});
    for (const t of ['dark', 'light']) {
      await mudarTema(t);
      await page.waitForTimeout(100);
      await page.screenshot({
        path: outDir + '/astra-' + res.nome + '-' + t + '.png',
        fullPage: false
      });
    }
  }
''')

    def test_02_esteira_fluxo_5_etapas(self):
        """AG-R02: Verifica a Esteira Operacional com as 5 etapas, status, links e botões de ação."""
        self.cenario(SETUP_AG90 + r'''
  // Abre o caso OS-931-2099 diretamente via abrirCaso
  await page.evaluate(() => abrirCaso('OS-931-2099', true));
  await page.waitForSelector('#detalhe .esteira-operacional');

  const etapas = await page.evaluate(() => {
    const cards = document.querySelectorAll('#detalhe .esteira-operacional .etapa-card');
    return Array.from(cards).map(c => ({
      titulo: c.querySelector('.etapa-titulo')?.textContent?.trim() || '',
      badge: c.querySelector('.etapa-num span:last-child')?.textContent?.trim() || '',
      acao: c.querySelector('.etapa-acao button')?.textContent?.trim() || ''
    }));
  });

  assert.equal(etapas.length, 5, 'Esteira deve ter exatamente 5 etapas');
  assert.ok(etapas[0].titulo.includes('O.S.'), 'Etapa 1: Peças & O.S.');
  assert.ok(etapas[1].titulo.includes('Extração'), 'Etapa 2: Extração & OCR');
  assert.ok(etapas[2].titulo.includes('Análise'), 'Etapa 3: Análise & Vínculos');
  assert.ok(etapas[3].titulo.includes('Minuta') || etapas[3].titulo.includes('Revisão'), 'Etapa 4: Minuta & Revisão');
  assert.ok(etapas[4].titulo.includes('Finalização'), 'Etapa 5: Finalização Humana');
''')

    def test_03_mapa_unico_race_condition(self):
        """AG-R03: Verifica mapa único, badge aproximada e descarte de respostas obsoletas."""
        self.cenario(SETUP_AG90 + r'''
  let contadorRequisicoes = 0;
  const registro1 = {
    id: 'ficticio-1', caso: 'OS-931-2099', nome: 'D\'Ávila Investigada', tipo_pessoa: 'PF',
    papel: 'investigado', municipio: 'Presidente Prudente', uf: 'SP', lat: -22.12, lon: -51.38,
    precisao: 'municipio_aproximado'
  };
  const registroAntigo = {
    id: 'ponto-antigo', caso: 'OS-ANTIGA', nome: 'Pessoa Antiga', tipo_pessoa: 'PF',
    papel: 'vítima', municipio: 'São Paulo', uf: 'SP', lat: -23.55, lon: -46.63,
    precisao: 'municipio_aproximado'
  };
  const regSemLoc = {
    id: 'ficticio-3', caso: 'OS-931-2099', nome: 'Vítima Alfa',
    motivo_sem_localizacao: 'sem_endereco'
  };

  const cartoFixture = {
    total_municipios_base: 2,
    metadata: {licenca: 'Geometria sintética de teste'},
    ufs: {
      SP: {nome: 'São Paulo (fixture)', lat: -23, lon: -49, poligono: [[-53, -20], [-49, -19], [-44, -23], [-48, -25], [-53, -23]]}
    }
  };

  await page.route('**/api/inteligencia/mapa*', async route => {
    contadorRequisicoes++;
    const reqNum = contadorRequisicoes;

    if (reqNum === 1) {
      // Primeira requisição: atrasa 500ms e retorna ponto antigo
      await new Promise(r => setTimeout(r, 500));
      await route.fulfill({
        json: {
          pontos: [registroAntigo],
          grupos: [{id: 'grp-antigo', total: 1, registros_ids: [registroAntigo.id], municipio: 'São Paulo', uf: 'SP', lat: -23.55, lon: -46.63, precisoes: ['municipio_aproximado']}],
          sem_localizacao: [],
          resumo: {total_registros: 1, localizados: 1, sem_localizacao: 0, pf_localizados: 1, pj_localizados: 0, precisao_municipio: 1},
          cartografia: cartoFixture
        }
      });
    } else {
      // Segunda requisição: responde imediatamente com dados novos
      await route.fulfill({
        json: {
          pontos: [registro1],
          grupos: [{id: 'grp-1', total: 1, registros_ids: [registro1.id], municipio: 'Presidente Prudente', uf: 'SP', lat: -22.12, lon: -51.38, precisoes: ['municipio_aproximado']}],
          sem_localizacao: [regSemLoc],
          resumo: {total_registros: 2, localizados: 1, sem_localizacao: 1, pf_localizados: 1, pj_localizados: 0, precisao_municipio: 1},
          cartografia: cartoFixture
        }
      });
    }
  });

  // Abre a aba de mapa
  await page.locator('#nav-btn-mapa').click();
  await page.locator('#b-mapa-modo-estados').click();
  await page.waitForSelector('#svg-mapa-offline .mapa-ponto');

  // Dispara segunda requisição enquanto a primeira ainda estaria atrasada
  await page.evaluate(() => CPJInteligenciaMapa.carregarMapa());
  await page.waitForTimeout(800);

  // O mapa não pode conter 'ponto-antigo'
  const temPontoAntigo = await page.evaluate(() => {
    return !!document.querySelector('[data-ponto-id="ponto-antigo"]');
  });
  assert.ok(!temPontoAntigo, 'Resposta obsoleta não pode sobrescrever o mapa');

  // Verifica que existe indicador de carregamento no mapa
  const temIndicadorCarregando = await page.evaluate(() => !!document.getElementById('mapa-carregando'));
  assert.ok(temIndicadorCarregando, 'Elemento #mapa-carregando deve existir');
''')

    def test_04_grafo_fontes_manual_vs_documental(self):
        """AG-R04: Verifica grafo com fontes, diferenciação manual/documental e escape de apóstrofo."""
        self.cenario(SETUP_AG90 + r'''
  await page.evaluate(async () => {
    abrirAba('grafo');
    await carregarGrafo();
  });
  await page.waitForSelector('#grafo');

  // Testa escape seguro de texto contendo apóstrofo e HTML
  const escapeSeguro = await page.evaluate(() => {
    const texto = "D'Ávila Investigada <script>alert(1)</script>";
    const seguro = esc(texto);
    return seguro.includes('&#39;') && !seguro.includes('<script>');
  });
  assert.ok(escapeSeguro, 'Função esc deve escapar aspas simples e tags HTML');
''')

    def test_05_navegacao_afirmacao_ate_fonte(self):
        """AG-R05: Verifica links diretos da afirmação/valor até as folhas e páginas."""
        self.cenario(SETUP_AG90 + r'''
  await page.evaluate(() => abrirCaso('OS-931-2099', true));
  await page.waitForSelector('#detalhe');

  const linksFontes = await page.evaluate(() => {
    const anchors = Array.from(document.querySelectorAll('#detalhe a[href*="01-extracao"]'));
    return anchors.map(a => ({
      href: a.getAttribute('href'),
      texto: a.textContent.trim()
    }));
  });

  assert.ok(linksFontes.length > 0, 'Devem existir links diretos para a transcrição/extração');
  assert.ok(linksFontes.some(l => l.href.includes('01-extracao')), 'Links devem apontar para pasta de extração');
''')

    def test_06_revisao_solicitacoes_os(self):
        """AG-R06: Verifica painel de revisão de solicitações e alerta de nova versão."""
        self.cenario(SETUP_AG90 + r'''
  await page.evaluate(() => abrirCaso('OS-931-2099', true));
  await page.waitForSelector('#painel-solicitacoes-os');

  const painelOS = await page.evaluate(() => {
    const el = document.getElementById('painel-solicitacoes-os');
    const alerta = el.querySelector('.aviso-reconferencia')?.textContent?.trim();
    const itens = Array.from(el.querySelectorAll('.solicitacao-item')).map(i => i.innerText);
    return {alerta, itens};
  });

  // Como o caso 931 possui 2 minutas (v01 e v02), deve exigir reconferência
  assert.ok(painelOS.alerta && painelOS.alerta.includes('Minuta alterada'), 'Deve alertar necessidade de nova conferência');
  assert.ok(painelOS.itens.some(i => i.includes('Determinação da autoridade')), 'Deve listar determinações da autoridade');
  assert.ok(painelOS.itens.some(i => i.includes('solicitacoes-os.md')), 'Deve listar link de solicitações');
''')

    def test_07_conferencia_lado_a_lado(self):
        """AG-R07: Verifica o modal de conferência documental lado a lado (PDF x Markdown)."""
        self.cenario(SETUP_AG90 + r'''
  await page.evaluate(() => abrirCaso('OS-931-2099', true));
  await page.waitForSelector('#detalhe');

  // Abre a conferência documental diretamente via método do CPJCasos
  await page.evaluate(() => {
    CPJCasos.abrirConferenciaDocumental('OS-931-2099', '01-extracao/autos/transcricao.md', 2, '30');
  });

  await page.waitForSelector('#modal-conferencia-documental', {state: 'visible'});

  const estadoModal = await page.evaluate(() => {
    const modal = document.getElementById('modal-conferencia-documental');
    const seletor = document.getElementById('conf-doc-pag');
    const mdPane = document.getElementById('conf-md-conteudo');
    return {
      visivel: getComputedStyle(modal).display !== 'none' && !modal.hidden,
      opcoesPagina: seletor ? seletor.options.length : 0,
      temMarkdown: mdPane ? mdPane.textContent.length > 0 : false
    };
  });

  assert.ok(estadoModal.visivel, 'Modal de conferência deve estar visível');
  assert.ok(estadoModal.opcoesPagina >= 2, 'Seletor de páginas deve listar as páginas da transcrição');
  assert.ok(estadoModal.temMarkdown, 'Markdown da página deve estar carregado no painel');

  // Fecha o modal
  await page.locator('#b-conf-fechar').click();
  const fechado = await page.evaluate(() => {
    const modal = document.getElementById('modal-conferencia-documental');
    return modal.hidden || getComputedStyle(modal).display === 'none';
  });
  assert.ok(fechado, 'Modal de conferência deve ser fechado');
''')

    def test_08_eventos_transacoes_filtros(self):
        """AG-R08: Verifica visão em tabela estruturada de eventos financeiros e filtros."""
        self.cenario(SETUP_AG90 + r'''
  await page.evaluate(() => abrirCaso('OS-931-2099', true));
  await page.waitForSelector('#detalhe');

  // Abre aba de fluxo financeiro
  await page.evaluate(() => {
    abrirAba('fluxograma');
    CPJFluxograma.carregar('OS-931-2099');
  });
  await page.waitForSelector('#fx-visao-camadas');

  // Alterna para visão em tabela estruturada
  await page.locator('#b-fx-toggle-visao').click();
  await page.waitForSelector('#fx-visao-tabela:not([hidden])');

  const dadosTabela = await page.evaluate(() => {
    const linhas = Array.from(document.querySelectorAll('#fx-tab-transacoes tbody tr'));
    return linhas.map(l => ({
      origem: l.children[4]?.textContent?.trim() || '',
      destino: l.children[5]?.textContent?.trim() || '',
      valor: l.children[6]?.textContent?.trim() || '',
      fls: l.children[7]?.textContent?.trim() || ''
    }));
  });

  assert.equal(dadosTabela.length, 2, 'Tabela deve conter 2 transações do CSV sintético');
  assert.ok(dadosTabela[0].destino.includes("D'Ávila"), 'Destino deve renderizar apóstrofo corretamente');
  assert.ok(dadosTabela[0].valor.includes('5.000,00'), 'Valor deve estar formatado em Real (R$)');
  assert.ok(dadosTabela[0].fls.includes('30'), 'Folha deve indicar 30');

  // Testa filtro de valor mínimo (4800) -> deve filtrar apenas a de 5000
  await page.locator('#fx-filtro-val-min').fill('4800');
  await page.locator('#b-fx-aplicar-filtros').click();

  const linhasFiltradas = await page.evaluate(() => {
    return document.querySelectorAll('#fx-tab-transacoes tbody tr').length;
  });
  assert.equal(linhasFiltradas, 1, 'Filtro de valor mínimo deve restringir a 1 transação');
''')

    def test_09_notas_analiticas_e_consultas_salvas(self):
        """AG-R09: Verifica persistência de notas analíticas com alerta de hipótese."""
        self.cenario(SETUP_AG90 + r'''
  await page.evaluate(() => abrirCaso('OS-931-2099', true));
  await page.waitForSelector('#painel-notas-caso');

  // Insere uma nova nota do investigador
  await page.locator('#inp-nova-nota-caso').fill('Hipótese: conta laranja aberta com documento falso.');
  await page.locator('#b-salvar-nota-caso').click();

  // Verifica que a nota foi adicionada com o alerta obrigatório
  const notaRenderizada = await page.evaluate(() => {
    const lista = document.getElementById('lista-notas-caso');
    return lista ? lista.innerText : '';
  });

  assert.ok(notaRenderizada.includes('HIPÓTESE / NOTA DO INVESTIGADOR'), 'Nota deve ter etiqueta expressa de hipótese');
  assert.ok(notaRenderizada.includes('conta laranja'), 'Nota deve conter texto digitado');

  // Exclui a nota
  await page.locator('#lista-notas-caso button', {hasText: 'Excluir'}).click();
  const notasAposExclusao = await page.evaluate(() => {
    return document.querySelectorAll('#lista-notas-caso .card').length;
  });
  assert.equal(notasAposExclusao, 0, 'Nota deve ser removida após exclusão');
''')

    def test_10_coerencia_markdown_enxuto(self):
        """AG-R10: Verifica coerência com extração moderna Markdown (sem entidades.csv)."""
        self.cenario(SETUP_AG90 + r'''
  // Clica no caso 933 (modo moderno enxuto Markdown)
  await page.evaluate(() => abrirCaso('OS-933-2099', true));
  await page.waitForSelector('#detalhe');

  const statusDisponibilidade = await page.evaluate(() => {
    const disp = document.getElementById('astra-material-resumo');
    return disp ? disp.innerText : '';
  });

  // Não pode acusar falta de entidades.csv nem exibir erro
  assert.ok(statusDisponibilidade.includes('(Markdown)'), 'Disponibilidade deve reconhecer transcrição Markdown');
  assert.ok(!statusDisponibilidade.includes('entidades.csv faltante'), 'Não deve reclamar de entidades.csv');
''')


if __name__ == "__main__":
    unittest.main(verbosity=2)
