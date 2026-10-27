#!/usr/bin/env python3
"""Prepara o pacote genérico do plugin investigacao-cpj, sem instalar nada.

  python ferramentas/pacote-plugin.py listar                    # caminhos do pacote (relativos a plugin/)
  python ferramentas/pacote-plugin.py manifesto [--saida ARQ]   # revisão + SHA-256 dos arquivos genéricos
  python ferramentas/pacote-plugin.py preparar --destino PASTA  # copia o pacote para PASTA (nova ou vazia) e confere os hashes

Saída 0 = pacote aceito; 1 = recusado (extensão fora da lista fechada, link simbólico etc.); 2 = erro de uso/ambiente.
O atualizar-plugin.ps1 usa `preparar` e só depois instala; o teste de distribuição usa as funções deste módulo.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = "cpj-pacote/1"
# Lista fechada: .js/.css são a interface local servida por app/static; nenhuma outra extensão é empacotada.
EXTENSOES = frozenset({".py", ".md", ".json", ".html", ".png", ".js", ".css"})
# Nunca vão no pacote: testes, caches e dados/configuração/modelos locais.
DIRETORIOS_EXCLUIDOS = frozenset({"testes", "__pycache__", "casos", "config", "00-originais", "modelos", "node_modules", ".git"})
# Arquivos sensíveis por nome (mesmo com extensão permitida, p.ex. assinatura.png).
NOMES_SENSIVEIS = re.compile(
    r"(^\.env($|\.))|assinatura|signature|rubrica|credenc|\.(sqlite3?|db|key|pem|pfx|p12|docx?|pdf|log|bak|zip|gz)$", re.I)
RAIZ_PACOTE = "investigacao-cpj"
MARKETPLACE = Path(".claude-plugin") / "marketplace.json"


class PacoteRecusado(Exception):
    pass


def raiz_plugin(workspace: Path) -> Path:
    return workspace / "plugin"


def _regra_exclusao(relativo: Path) -> str | None:
    partes = relativo.parts
    for d in partes[:-1]:
        if d in DIRETORIOS_EXCLUIDOS:
            return f"diretório excluído: {d}"
    if NOMES_SENSIVEIS.search(partes[-1]):
        return "nome sensível"
    return None


def selecionar(workspace: Path) -> tuple[dict[str, Path], list[dict], list[str]]:
    """(incluídos {relativo: caminho}, excluídos [{caminho, regra}], recusados [mensagens])."""
    base = raiz_plugin(workspace)
    origem = base / RAIZ_PACOTE
    incluidos: dict[str, Path] = {}
    excluidos: list[dict] = []
    recusados: list[str] = []
    candidatos = [base / MARKETPLACE] + (sorted(p for p in origem.rglob("*") if p.is_file() or p.is_symlink())
                                          if origem.is_dir() else [])
    if not origem.is_dir():
        recusados.append(f"origem ausente: {RAIZ_PACOTE}")
    for caminho in candidatos:
        relativo = caminho.relative_to(base)
        if not (caminho.exists() or caminho.is_symlink()):
            recusados.append(f"ausente: {relativo.as_posix()}")
            continue
        regra = _regra_exclusao(relativo)
        if regra:
            excluidos.append({"caminho": relativo.as_posix(), "regra": regra})
            continue
        if caminho.is_symlink():
            recusados.append(f"link simbólico: {relativo.as_posix()}")
        elif caminho.suffix.lower() not in EXTENSOES:
            recusados.append(f"extensão fora do pacote genérico: {relativo.as_posix()}")
        else:
            incluidos[relativo.as_posix()] = caminho
    # Documento de raiz do pacote; a fonte autoritativa continua no workspace.
    # Não copie uma memória independente para cada skill/agente instalado.
    memoria = workspace / "MEMORIA.md"
    if memoria.is_symlink() or getattr(memoria, "is_junction", lambda: False)():
        recusados.append("link na memória central: MEMORIA.md")
    elif memoria.is_file():
        incluidos["MEMORIA.md"] = memoria
    return incluidos, excluidos, recusados


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _revisao(workspace: Path) -> tuple[str | None, bool | None]:
    """(SHA do commit, árvore do plugin sem alterações?) — None quando não há git."""
    def git(*args):
        try:
            r = subprocess.run(["git", "-C", str(workspace), *args], capture_output=True, text=True, encoding="utf-8", timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None
    sha = git("rev-parse", "HEAD")
    sujo = git("status", "--porcelain", "--", "plugin")
    return sha, (None if sujo is None else sujo == "")


def manifesto(workspace: Path) -> dict:
    incluidos, excluidos, recusados = selecionar(workspace)
    if recusados:
        raise PacoteRecusado("; ".join(recusados))
    sha, limpa = _revisao(workspace)
    return {"schema": SCHEMA, "revisao": sha, "arvore_limpa": limpa, "total": len(incluidos),
            "arquivos": {rel: {"sha256": _sha256(p), "bytes": p.stat().st_size} for rel, p in sorted(incluidos.items())},
            "excluidos": sorted(excluidos, key=lambda e: e["caminho"])}


def preparar(workspace: Path, destino: Path) -> dict:
    """Copia o pacote para uma pasta nova/vazia, confere cada hash contra a fonte e grava o manifesto ao lado."""
    destino = destino.resolve()
    if destino.exists() and (not destino.is_dir() or any(destino.iterdir())):
        raise PacoteRecusado(f"destino deve ser uma pasta nova ou vazia: {destino}")
    m = manifesto(workspace)
    incluidos, _, _ = selecionar(workspace)
    base = raiz_plugin(workspace)
    destino.mkdir(parents=True, exist_ok=True)
    for rel, info in m["arquivos"].items():
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(incluidos[rel], alvo)
        if _sha256(alvo) != info["sha256"]:
            raise PacoteRecusado(f"cópia divergente: {rel}")
    (destino.parent / f"{destino.name}.manifesto.json").write_text(
        json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent.parent)
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar")
    s = sub.add_parser("manifesto")
    s.add_argument("--saida", type=Path)
    s = sub.add_parser("preparar")
    s.add_argument("--destino", type=Path, required=True)
    args = ap.parse_args(argv)
    ws = args.workspace.resolve()
    try:
        if args.comando == "listar":
            incluidos, _, recusados = selecionar(ws)
            if recusados:
                raise PacoteRecusado("; ".join(recusados))
            print("\n".join(sorted(incluidos)))
        elif args.comando == "manifesto":
            texto = json.dumps(manifesto(ws), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            if args.saida:
                args.saida.write_text(texto, encoding="utf-8", newline="\n")
            else:
                sys.stdout.write(texto)
        else:
            m = preparar(ws, args.destino)
            print(f"Pacote genérico preparado: {m['total']} arquivos, {len(m['excluidos'])} excluídos -> {args.destino.resolve()}")
        return 0
    except PacoteRecusado as e:
        print(f"Pacote recusado: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
