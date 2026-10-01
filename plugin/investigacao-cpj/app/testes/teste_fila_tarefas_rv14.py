#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Teste unitário e de integração para ferramentas/fila-tarefas.py (RV14).

Cobre:
1. Normalização de caminhos reservados (app/..., skills/..., commands/..., agents/...).
2. Detecção de sobreposição e conflito entre caminhos abreviados e canônicos.
3. Comportamento do comando 'proxima' (padrão global e por prefixo).
4. Comando 'reabrir' para tarefas concluídas (transição de estado, liberação e registro).
5. Limpeza de dependências obsoletas em DEPENDENCIAS.
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(RAIZ / "ferramentas"))

import importlib
fila_tarefas = importlib.import_module("fila-tarefas")
normalizar_caminho = fila_tarefas.normalizar_caminho
sobrepostos = fila_tarefas.sobrepostos
caminhos = fila_tarefas.caminhos
impedimento = fila_tarefas.impedimento
proxima = fila_tarefas.proxima
linhas_tarefas = fila_tarefas.linhas_tarefas
atualizar = fila_tarefas.atualizar
DEPENDENCIAS = fila_tarefas.DEPENDENCIAS


QUADRO_TESTE = """# Tarefas Compartilhadas (Ambiente de Teste)

| ID | Responsável | Estado | Entrega | Arquivos reservados |
|---|---|---|---|---|
| T01 | Agente-A | concluída | Entrega inicial concluída | `app/rotas/casos.py`, `app/plantao.py` |
| T02 | — | disponível | Tarefa pronta para início | `plugin/investigacao-cpj/app/rotas/casos.py` |
| T03 | Agente-B | em andamento | Tarefa em andamento com path abreviado | `app/static/index.html` |
| T04 | — | disponível | Tarefa tentando mesmo arquivo com path longo | `plugin/investigacao-cpj/app/static/index.html` |
| T05 | — | aguardando dependências | Tarefa dependente de T01 | `plugin/investigacao-cpj/skills/relatorio-ip-fraude/scripts/gerar_docx.py` |
| T06 | — | disponível | Tarefa em outro arquivo independente | `ferramentas/verificar-ambiente.ps1` |

- 2026-10-01T08:00:00 — Agente-A: assumir T01.
- 2026-10-01T08:30:00 — Agente-A: concluir T01.
- 2026-10-01T09:00:00 — Agente-B: assumir T03.
"""


class TestFilaTarefasRV14(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.quadro_path = Path(self.temp_dir.name) / "TAREFAS-COMPARTILHADAS.md"
        self.quadro_path.write_text(QUADRO_TESTE, encoding="utf-8")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_normalizacao_caminhos(self):
        """Atalhos app, skills, commands, agents devem mapear para plugin/investigacao-cpj/."""
        self.assertEqual(
            normalizar_caminho("app/static/index.html"),
            "plugin/investigacao-cpj/app/static/index.html"
        )
        self.assertEqual(
            normalizar_caminho("plugin/investigacao-cpj/app/static/index.html"),
            "plugin/investigacao-cpj/app/static/index.html"
        )
        self.assertEqual(
            normalizar_caminho("app/rotas/casos.py"),
            "plugin/investigacao-cpj/app/rotas/casos.py"
        )
        self.assertEqual(
            normalizar_caminho("skills/base-cpj/scripts/caso.py"),
            "plugin/investigacao-cpj/skills/base-cpj/scripts/caso.py"
        )
        self.assertEqual(
            normalizar_caminho("commands/fluxo-ip.md"),
            "plugin/investigacao-cpj/commands/fluxo-ip.md"
        )
        self.assertEqual(
            normalizar_caminho("agents/analista.md"),
            "plugin/investigacao-cpj/agents/analista.md"
        )
        self.assertEqual(
            normalizar_caminho("app/rotas/"),
            "plugin/investigacao-cpj/app/rotas"
        )
        self.assertEqual(
            normalizar_caminho("ferramentas/fila-tarefas.py"),
            "ferramentas/fila-tarefas.py"
        )

    def test_02_sobreposicao_caminhos_curtos_e_longos(self):
        """Caminho abreviado deve colidir com caminho canônico correspondente."""
        c1 = normalizar_caminho("app/static/index.html")
        c2 = normalizar_caminho("plugin/investigacao-cpj/app/static/index.html")
        self.assertTrue(sobrepostos(c1, c2))
        self.assertTrue(sobrepostos(c2, c1))

        # Diretório x Arquivo
        dir_norm = normalizar_caminho("app/rotas/")
        arq_norm = normalizar_caminho("plugin/investigacao-cpj/app/rotas/casos.py")
        self.assertTrue(sobrepostos(dir_norm, arq_norm))
        self.assertTrue(sobrepostos(arq_norm, dir_norm))

        # Arquivos independentes
        f1 = normalizar_caminho("ferramentas/fila-tarefas.py")
        f2 = normalizar_caminho("ferramentas/fila-os.py")
        self.assertFalse(sobrepostos(f1, f2))

    def test_03_conflito_reserva_entre_formatos(self):
        """Impedimento deve detectar colisão se uma tarefa em andamento usa app/... e a nova usa plugin/..."""
        tarefas = linhas_tarefas(self.quadro_path.read_text(encoding="utf-8"))
        # T03 está em andamento com `app/static/index.html`.
        # T04 tenta assumir `plugin/investigacao-cpj/app/static/index.html`.
        motivo = impedimento(tarefas, "T04")
        self.assertIsNotNone(motivo)
        self.assertIn("Conflito com T03 (Agente-B)", motivo)
        self.assertIn("plugin/investigacao-cpj/app/static/index.html", motivo)

    def test_04_proxima_sem_prefixo_e_com_prefixo(self):
        """proxima sem prefixo busca tarefas abertas livres; com prefixo filtra."""
        tarefas = linhas_tarefas(self.quadro_path.read_text(encoding="utf-8"))

        # Sem prefixo: primeira disponível livre é T02 (ou T06)
        codigo, tarefa = proxima(tarefas, prefixo=None)
        self.assertEqual(codigo, 0)
        self.assertEqual(tarefa, "T02")

        # Com prefixo T: primeira livre é T02
        codigo_t, tarefa_t = proxima(tarefas, prefixo="T")
        self.assertEqual(codigo_t, 0)
        self.assertEqual(tarefa_t, "T02")

        # Com prefixo inexistente Z: fila concluída
        codigo_z, msg_z = proxima(tarefas, prefixo="Z")
        self.assertEqual(codigo_z, 3)
        self.assertIn("CONCLUÍDA", msg_z)

    def test_05_reabrir_tarefa_concluida(self):
        """reabrir deve retornar tarefa concluída para disponível, limpando responsável."""
        # T01 está concluída por Agente-A
        res = atualizar(self.quadro_path, "reabrir", "T01", "Agente-C", "Entrega de 0 bytes detectada")
        self.assertIn("T01: reaberta (disponível); responsável: —", res)

        conteudo = self.quadro_path.read_text(encoding="utf-8")
        linhas = conteudo.splitlines()
        # Verificar linha da tabela
        linha_t01 = [l for l in linhas if l.startswith("| T01 |")][0]
        campos = [c.strip() for c in linha_t01.strip("|").split("|")]
        self.assertEqual(campos[1], "—")
        self.assertEqual(campos[2], "disponível")

        # Verificar histórico
        self.assertTrue(any("Agente-C: reabrir T01. Entrega de 0 bytes detectada" in l for l in linhas))

        # Agora T01 pode ser reassumida por Agente-C
        res_assumir = atualizar(self.quadro_path, "assumir", "T01", "Agente-C", None)
        self.assertIn("T01: em andamento; responsável: Agente-C", res_assumir)

    def test_06_reabrir_recusa_tarefa_nao_concluida(self):
        """reabrir em tarefa em andamento ou disponível deve falhar."""
        with self.assertRaises(ValueError) as ctx:
            atualizar(self.quadro_path, "reabrir", "T03", "Agente-C", "Tentativa indevida")
        self.assertIn("Só tarefa concluída pode ser reaberta", str(ctx.exception))

    def test_07_dependencias_obsoletas_limpas(self):
        """DEPENDENCIAS não deve conter V01..V10, R01..R10, nem E01..E06."""
        import re
        padrao_obsoleto = re.compile(r"^(?:V\d+|R\d+|E\d+)")
        for pai, filhos in DEPENDENCIAS.items():
            self.assertFalse(padrao_obsoleto.match(pai), f"Dependência obsoleta encontrada: {pai}")
            for filho in filhos:
                self.assertFalse(padrao_obsoleto.match(filho), f"Sub-dependência obsoleta: {filho}")

    def test_08_cli_reabrir_e_proxima(self):
        """Testa invocação CLI dos novos comandos com subprocess."""
        script = str(RAIZ / "ferramentas" / "fila-tarefas.py")

        # CLI: proxima sem prefixo
        proc = subprocess.run(
            [sys.executable, script, "--arquivo", str(self.quadro_path), "proxima"],
            capture_output=True, text=True, check=True
        )
        self.assertEqual(proc.stdout.strip(), "T02")

        # CLI: reabrir com --motivo
        proc_reabrir = subprocess.run(
            [sys.executable, script, "--arquivo", str(self.quadro_path), "reabrir", "T01",
             "--agente", "Gemini-1", "--motivo", "Entrega zerada"],
            capture_output=True, text=True, check=True
        )
        self.assertIn("T01: reaberta (disponível); responsável: —", proc_reabrir.stdout)


if __name__ == "__main__":
    unittest.main()
