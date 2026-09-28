#!/usr/bin/env python3
"""Teste focado para a tarefa E01: localização do Claude CLI."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Garante import do app
AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
if APP not in sys.path:
    sys.path.insert(0, APP)

import plantao


class TesteClaudeExeE01(unittest.TestCase):
    def test_localiza_via_appdata_claude_nativo(self):
        with tempfile.TemporaryDirectory(prefix="cpj-claude-nativo-") as tmp:
            nativo_dir = os.path.join(tmp, "Claude", "claude-code", "v1.2.3")
            os.makedirs(nativo_dir, exist_ok=True)
            exe = os.path.join(nativo_dir, "claude.exe")
            with open(exe, "wb") as f:
                f.write(b"ficticio")
            with patch.dict(os.environ, {"APPDATA": tmp}):
                self.assertEqual(plantao.claude_exe(), exe)

    def test_localiza_via_npm_global(self):
        with tempfile.TemporaryDirectory(prefix="cpj-claude-npm-") as tmp:
            npm_dir = os.path.join(tmp, "npm", "node_modules", "@anthropic-ai", "claude-code", "bin")
            os.makedirs(npm_dir, exist_ok=True)
            exe = os.path.join(npm_dir, "claude.exe")
            with open(exe, "wb") as f:
                f.write(b"ficticio")
            with patch.dict(os.environ, {"APPDATA": tmp}):
                self.assertEqual(plantao.claude_exe(), exe)

    def test_localiza_via_which_path(self):
        with tempfile.TemporaryDirectory(prefix="cpj-claude-which-") as tmp:
            exe = os.path.join(tmp, "claude.exe")
            with open(exe, "wb") as f:
                f.write(b"ficticio")
            # APPDATA vazio para forçar busca via PATH
            with patch.dict(os.environ, {"APPDATA": "", "PATH": tmp}):
                self.assertEqual(plantao.claude_exe(), exe)

    def test_ignora_claude_cmd_e_nao_exe(self):
        with tempfile.TemporaryDirectory(prefix="cpj-claude-cmd-") as tmp:
            cmd = os.path.join(tmp, "claude.cmd")
            with open(cmd, "wb") as f:
                f.write(b"cmd ficticio")
            with patch.dict(os.environ, {"APPDATA": "", "PATH": tmp}):
                self.assertIsNone(plantao.claude_exe())

    def test_retorna_none_quando_nao_encontrado(self):
        with tempfile.TemporaryDirectory(prefix="cpj-claude-vazio-") as tmp:
            with patch.dict(os.environ, {"APPDATA": tmp, "PATH": ""}):
                self.assertIsNone(plantao.claude_exe())


if __name__ == "__main__":
    unittest.main()
