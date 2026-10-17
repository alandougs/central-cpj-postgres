#!/usr/bin/env python3
"""Executa um comando do CI e, se falhar, publica o final da saída como anotação de erro do GitHub Actions.

  python ferramentas/ci-executar.py <rótulo> -- <comando> [args...]

A saída completa continua indo ao log do job. A anotação (`::error`) repete só as últimas linhas, para que o motivo da falha
apareça no resumo da execução e na API de check-runs sem exigir abrir o log. Sem segredos no CI; não faz rede nem grava arquivos.
Código de saída: o do comando (127 se não puder iniciá-lo).
"""
import os
import subprocess
import sys

LINHAS = 40
LIMITE = 6000


def escapar(texto):
    return texto.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def anotacao(rotulo, saida):
    final = "\n".join(saida.splitlines()[-LINHAS:])[-LIMITE:]
    return f"::error title={escapar(rotulo).replace(',', '%2C').replace(':', '%3A')}::{escapar(final)}"


def main(argv=None):
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv or argv.index("--") == 0 or argv.index("--") == len(argv) - 1:
        print("uso: ci-executar.py <rótulo> -- <comando> [args...]", file=sys.stderr)
        return 2
    corte = argv.index("--")
    rotulo, comando = " ".join(argv[:corte]), argv[corte + 1:]
    try:
        proc = subprocess.Popen(comando, env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
    except OSError as erro:
        print(anotacao(rotulo, f"não foi possível iniciar {comando[0]}: {erro}"))
        return 127
    saida = []
    for linha in proc.stdout:
        sys.stdout.write(linha)
        saida.append(linha)
    sys.stdout.flush()
    codigo = proc.wait()
    if codigo != 0:
        print(anotacao(f"{rotulo} (saída {codigo})", "".join(saida)))
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
