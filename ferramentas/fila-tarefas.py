#!/usr/bin/env python
"""Reserva tarefas e arquivos para agentes que trabalham no mesmo workspace.

python ferramentas/fila-tarefas.py listar
python ferramentas/fila-tarefas.py assumir L04 --agente Gemini-1
python ferramentas/fila-tarefas.py concluir L04 --agente Gemini-1 --resultado "Arquivos e testes"
"""
import argparse
from contextlib import contextmanager
import datetime
import os
from pathlib import Path
import re
import tempfile


RAIZ = Path(__file__).resolve().parent.parent
DEPENDENCIAS = {
    "I01": ["C03", "C04", "C05", "L01", "L02", "L03", "L04", "L05", "L06", "A01", "S01", "M01"],
    "A01": ["C04", "C05"],   # servidor.py: modularizar só depois das tarefas que editam o servidor
    "S01": ["C03"],          # tarefas.py: executor de IA depois da correção de importação
    "P01": ["I01"],          # piloto com o sistema integrado
    "D02": ["N01", "D01"],   # painel do plantão: servidor/interface livres e núcleo pronto
}


def linhas_tarefas(texto):
    tarefas = {}
    for numero, linha in enumerate(texto.splitlines()):
        if not re.match(r"^\| [A-Z]{1,3}\d+ \|", linha): continue
        campos = [campo.strip() for campo in linha.strip("|").split("|")]
        if len(campos) != 5: raise ValueError(f"Linha de tarefa inválida: {linha}")
        if campos[0] in tarefas: raise ValueError(f"ID duplicado: {campos[0]}")
        tarefas[campos[0]] = (numero, campos)
    if not tarefas: raise ValueError("Quadro de tarefas não encontrado.")
    return tarefas


def caminhos(campos):
    # Os caminhos explícitos da coluna final são o escopo reservado.
    return [p.replace("\\", "/").strip("/").casefold()
            for p in re.findall(r"`([^`]+)`", campos[4])]


def sobrepostos(a, b):
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


@contextmanager
def trava(arquivo, agente):
    lock = arquivo.with_name(arquivo.name + ".lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError(f"Fila em atualização: {lock}. Tente novamente após o outro comando terminar. "
                         "Se houve interrupção, confirme que não há atualização em curso antes de remover a trava.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()} agente={agente} inicio={datetime.datetime.now().isoformat()}\n")
        yield
    finally:
        lock.unlink()


def atualizar(arquivo, acao, id_, agente, resultado):
    with trava(arquivo, agente):
        original = arquivo.read_bytes()
        texto = original.decode("utf-8")
        tarefas = linhas_tarefas(texto)
        if id_ not in tarefas: raise ValueError(f"Tarefa desconhecida: {id_}")
        numero, campos = tarefas[id_]
        if acao == "assumir":
            if campos[2] not in ("disponível", "aguardando dependências"):
                raise ValueError(f"{id_}: {campos[2]}, responsável {campos[1]}; reserva recusada.")
            pendentes = [d for d in DEPENDENCIAS.get(id_, [])
                         if d not in tarefas or tarefas[d][1][2] != "concluída"]
            if pendentes: raise ValueError("Dependências não concluídas: " + ", ".join(pendentes))
            for outro, (_, ativos) in tarefas.items():
                if outro == id_ or ativos[2] != "em andamento": continue
                comuns = sorted({p for p in caminhos(campos) for q in caminhos(ativos) if sobrepostos(p, q)})
                if comuns:
                    raise ValueError(f"Conflito com {outro} ({ativos[1]}): {', '.join(comuns)}. Reserva recusada.")
            campos[1:3] = [agente, "em andamento"]
        else:
            if campos[2] != "em andamento" or campos[1] != agente:
                raise ValueError(f"Só o responsável atual pode {acao}: {id_}, {campos[1]}, {campos[2]}.")
            campos[2] = "concluída" if acao == "concluir" else "disponível"
            if acao == "liberar": campos[1] = "—"
        linhas = texto.splitlines()
        linhas[numero] = "| " + " | ".join(campos) + " |"
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        registro = f"- {timestamp} — {agente}: {acao} {id_}."
        if resultado: registro += " " + " ".join(resultado.split())
        novo = "\n".join(linhas).rstrip() + "\n" + registro + "\n"
        fd, nome = tempfile.mkstemp(prefix=arquivo.name + ".", suffix=".tmp", dir=arquivo.parent)
        tmp = Path(nome)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f: f.write(novo)
            if arquivo.read_bytes() != original:
                raise ValueError("Fila mudou fora do comando; alteração preservada. Releia e tente novamente.")
            os.replace(tmp, arquivo)
        finally:
            if tmp.exists(): tmp.unlink()
        return f"{id_}: {campos[2]}; responsável: {campos[1]}."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", type=Path, default=RAIZ / "TAREFAS-COMPARTILHADAS.md")
    sub = parser.add_subparsers(dest="acao", required=True)
    sub.add_parser("listar")
    for acao in ("assumir", "concluir", "liberar"):
        p = sub.add_parser(acao)
        p.add_argument("id")
        p.add_argument("--agente", required=True)
        p.add_argument("--resultado", required=acao != "assumir")
    args = parser.parse_args()
    try:
        arquivo = args.arquivo.resolve(strict=True)
        if args.acao == "listar":
            for _, campos in linhas_tarefas(arquivo.read_text(encoding="utf-8")).values():
                print(f"{campos[0]} | {campos[2]} | {campos[1]} | {campos[3]}")
        else:
            if not re.fullmatch(r"[\w.\- ]{1,60}", args.agente) or not args.agente.strip():
                raise ValueError("Use um nome de sessão com letras, números, espaço, ponto ou hífen.")
            print(atualizar(arquivo, args.acao, args.id, args.agente.strip(), args.resultado))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
