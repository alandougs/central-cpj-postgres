#!/usr/bin/env python
"""Reserva tarefas e arquivos para agentes que trabalham no mesmo workspace.

python ferramentas/fila-tarefas.py listar
python ferramentas/fila-tarefas.py assumir RV14 --agente Gemini-1
python ferramentas/fila-tarefas.py concluir RV14 --agente Gemini-1 --resultado "Arquivos e testes"
    # recusa se um arquivo reservado estiver com 0 bytes; exceção: --sem-conferir-arquivos "motivo (15+ caracteres)"
python ferramentas/fila-tarefas.py liberar RV14 --agente Gemini-1 --resultado "Onde parou"
python ferramentas/fila-tarefas.py reabrir FT01 --agente Gemini-1 --motivo "Entrega com 0 bytes"
python ferramentas/fila-tarefas.py proxima [--prefixo RV|GH] # loop: 0 = ID livre; 3 = fila concluída; 4 = só bloqueadas
"""
import sys
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
    # Novas tarefas de arquitetura, esteira completa e full-time
    "EC01": ["SD01"],        # esteira completa depende da formalização dos papéis e contratos
    "FD01": ["EC01", "H01"], # fluxograma no DOCX após esteira e cabeçalho de escrivão
    "K01": ["EC01"],         # calibração por caso usa a rota compartilhada de casos
    "U01": ["EC01", "K01"], # UI de calibração/navegação após esteira e endpoint
    # Revisão geral de 01/10/2026 (RV = core; GH = GitHub/acervo)
    "RV07": ["RV04"],        # mesmos arquivos (relatorios.py e index.html): gate antes do editor
    "RV15": ["RV01", "RV02", "RV03", "RV04", "RV05", "RV10"],  # PRD só com o estado real
    "GH03": ["GH02"],        # revisar PR #17 com o clone sincronizado
    "GH04": ["GH02"],
    "GH05": ["GH03", "GH04"],
    "GH06": ["GH02"],
    "GH07": ["GH03", "RV02"],
    # Fechamento de pendências de 02/10/2026 (CL = Claude, CX = Codex, AG = Antigravity, GC = Copilot/GitHub)
    "CL03": ["CL01", "CL02", "CX01", "CX02", "AG01"],   # plugin só com a suíte verde
    "CL04": ["CL03", "AG02", "AG04"],                   # PRD por último, com o resultado real
    "CX03": ["AG03", "CL02"],                           # orçamento de IA depois da revisão de segurança e do plantão
    "AG04": ["CL01", "CL02", "CX01", "CX02", "AG01"],   # suíte final depois das correções
    # Pipeline de PDF do ASTRA, 07/10/2026 (PROMPT-PIPELINE-PDF.md)
    "PX01": ["AI02"],                                   # aviso de envio externo depois da ampliação de provedores
    "PX02": ["PX01"],                                   # roteador respeita o aceite
    "PX05": ["PX02", "PX03", "DJ01", "CX01"],           # transcrição visual por API sobre roteador, qualidade e extração estáveis
    "PX06": ["PX05"],                                   # modos dependem da etapa de IA
    "PX07": ["PX05"],                                   # normalização considera a transcrição complementar
    "AI03": ["PX01", "CL04"], # cat?logo atual e escolha padr?o ap?s UI/rotas e PRD livres
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


def normalizar_caminho(p):
    """Versão para comparar sobreposição (sem diferenciar caixa); ver _normalizar."""
    return _normalizar(p).casefold()


def _normalizar(p):
    """Normaliza caminhos reservados, preservando a caixa original.

    Remove barras iniciais/finais, unifica separadores, converte caminhos absolutos
    da raiz em relativos e mapeia atalhos históricos ('app/...', 'skills/...',
    'commands/...', 'agents/...') para 'plugin/investigacao-cpj/...'.
    """
    p = p.replace("\\", "/").strip().strip("/")
    if not p:
        return ""
    try:
        p_obj = Path(p)
        if p_obj.is_absolute():
            try:
                p = str(p_obj.resolve().relative_to(RAIZ.resolve())).replace("\\", "/")
            except ValueError:
                pass
    except Exception:
        pass
    p = p.replace("\\", "/").strip().strip("/")
    if p.startswith("./"):
        p = p[2:].strip("/")

    for prefixo in ("app", "skills", "commands", "agents"):
        if p == prefixo:
            p = f"plugin/investigacao-cpj/{prefixo}"
            break
        elif p.startswith(f"{prefixo}/"):
            p = f"plugin/investigacao-cpj/{p}"
            break

    return p


def caminhos(campos):
    # Os caminhos explícitos da coluna final são o escopo reservado.
    return [normalizar_caminho(p)
            for p in re.findall(r"`([^`]+)`", campos[4])
            if normalizar_caminho(p)]


ARQUIVOS_VAZIOS_OK = {"__init__.py", ".gitkeep", ".keep"}


def conferir_entrega(campos):
    """(vazios, ausentes) entre os ARQUIVOS reservados. Pasta, padrão (*?[) e nome sem extensão não entram; 0 bytes é
    o defeito que fez tarefas constarem concluídas sem entrega (FT01, FD01, SD01, RV03–RV05)."""
    vazios, ausentes = [], []
    for p in re.findall(r"`([^`]+)`", campos[4]):
        rel = _normalizar(p)
        if not rel or any(c in rel for c in "*?[") or not Path(rel).suffix:
            continue
        alvo = RAIZ / rel
        if alvo.is_dir():
            continue
        if not alvo.exists():
            ausentes.append(rel)
        elif alvo.stat().st_size == 0 and alvo.name not in ARQUIVOS_VAZIOS_OK:
            vazios.append(rel)
    return vazios, ausentes


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


def impedimento(tarefas, id_):
    """Motivo que impede assumir a tarefa agora (None = pode assumir)."""
    campos = tarefas[id_][1]
    if campos[2] not in ("disponível", "aguardando dependências"):
        return f"{id_}: {campos[2]}, responsável {campos[1]}; reserva recusada."
    pendentes = [d for d in DEPENDENCIAS.get(id_, [])
                 if d not in tarefas or tarefas[d][1][2] != "concluída"]
    if pendentes: return "Dependências não concluídas: " + ", ".join(pendentes)
    for outro, (_, ativos) in tarefas.items():
        if outro == id_ or ativos[2] != "em andamento": continue
        comuns = sorted({p for p in caminhos(campos) for q in caminhos(ativos) if sobrepostos(p, q)})
        if comuns:
            return f"Conflito com {outro} ({ativos[1]}): {', '.join(comuns)}. Reserva recusada."
    return None


def proxima(tarefas, prefixo=None):
    """Primeira tarefa livre (do prefixo se informado, ou de todo o quadro), na ordem do quadro."""
    if prefixo:
        ids = [i for i in tarefas if i.startswith(prefixo)]
        rotulo = f"FILA {prefixo} CONCLUÍDA"
    else:
        ids = list(tarefas.keys())
        rotulo = "QUADRO CONCLUÍDO"
    abertas = [i for i in ids if tarefas[i][1][2] != "concluída"]
    if not abertas: return 3, f"{rotulo} ({len(ids)} tarefas)."
    for i in sorted(abertas, key=lambda i: tarefas[i][0]):
        if impedimento(tarefas, i) is None: return 0, i
    return 4, "AGUARDANDO: " + "; ".join(f"{i} ({tarefas[i][1][2]}, {tarefas[i][1][1]})" for i in abertas)


def atualizar(arquivo, acao, id_, agente, resultado, sem_conferir=None):
    with trava(arquivo, agente):
        original = arquivo.read_bytes()
        texto = original.decode("utf-8")
        tarefas = linhas_tarefas(texto)
        if id_ not in tarefas: raise ValueError(f"Tarefa desconhecida: {id_}")
        numero, campos = tarefas[id_]
        nota_entrega = ""
        if acao == "assumir":
            erro = impedimento(tarefas, id_)
            if erro: raise ValueError(erro)
            campos[1:3] = [agente, "em andamento"]
        elif acao == "reabrir":
            if campos[2] != "concluída":
                raise ValueError(f"Só tarefa concluída pode ser reaberta: {id_} está {campos[2]}.")
            pendentes = [d for d in DEPENDENCIAS.get(id_, [])
                         if d not in tarefas or tarefas[d][1][2] != "concluída"]
            campos[1] = "—"
            campos[2] = "aguardando dependências" if pendentes else "disponível"
        else:
            if campos[2] != "em andamento" or campos[1] != agente:
                raise ValueError(f"Só o responsável atual pode {acao}: {id_}, {campos[1]}, {campos[2]}.")
            if acao == "concluir":
                vazios, ausentes = conferir_entrega(campos)
                motivo = " ".join((sem_conferir or "").split())
                if vazios and not sem_conferir:
                    raise ValueError(f"Entrega com arquivo(s) vazio(s) (0 bytes): {', '.join(vazios)}. Conclua a entrega ou use "
                                     "--sem-conferir-arquivos \"motivo\" (15+ caracteres) se o arquivo vazio for intencional.")
                if sem_conferir is not None and len(motivo) < 15:
                    raise ValueError("--sem-conferir-arquivos exige justificativa de 15 caracteres ou mais.")
                if vazios:
                    nota_entrega = f" Conferência de arquivos dispensada ({motivo}); vazios: {', '.join(vazios)}."
                elif ausentes:
                    nota_entrega = f" Aviso: arquivos reservados ausentes: {', '.join(ausentes)}."
            campos[2] = "concluída" if acao == "concluir" else "disponível"
            if acao == "liberar": campos[1] = "—"
        linhas = texto.splitlines()
        linhas[numero] = "| " + " | ".join(campos) + " |"
        timestamp = datetime.datetime.now().isoformat(timespec="seconds")
        registro = f"- {timestamp} — {agente}: {acao} {id_}."
        if resultado: registro += " " + " ".join(resultado.split())
        registro += nota_entrega
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
        if acao == "reabrir":
            return f"{id_}: reaberta ({campos[2]}); responsável: {campos[1]}."
        return f"{id_}: {campos[2]}; responsável: {campos[1]}."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arquivo", type=Path, default=RAIZ / "TAREFAS-COMPARTILHADAS.md")
    sub = parser.add_subparsers(dest="acao", required=True)
    sub.add_parser("listar")
    sub.add_parser("proxima").add_argument("--prefixo", default=None, help="Filtrar por prefixo (ex: RV, GH). Padrão: qualquer prefixo")
    for acao in ("assumir", "concluir", "liberar"):
        p = sub.add_parser(acao)
        p.add_argument("id")
        p.add_argument("--agente", required=True)
        p.add_argument("--resultado", required=acao != "assumir")
        if acao == "concluir":
            p.add_argument("--sem-conferir-arquivos", dest="sem_conferir", default=None, metavar="MOTIVO",
                           help="Conclui mesmo com arquivo reservado vazio (0 bytes); o motivo vai para o registro")
    p_reabrir = sub.add_parser("reabrir", help="Reabre tarefa concluída cuja entrega se perdeu")
    p_reabrir.add_argument("id")
    p_reabrir.add_argument("--agente", required=True)
    p_reabrir.add_argument("--motivo", "--resultado", dest="resultado", required=True,
                           help="Motivo da reabertura da tarefa")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        arquivo = args.arquivo.resolve(strict=True)
        if args.acao == "listar":
            for _, campos in linhas_tarefas(arquivo.read_text(encoding="utf-8")).values():
                print(f"{campos[0]} | {campos[2]} | {campos[1]} | {campos[3]}")
        elif args.acao == "proxima":
            codigo, texto = proxima(linhas_tarefas(arquivo.read_text(encoding="utf-8")), args.prefixo)
            print(texto)
            return codigo
        else:
            if not re.fullmatch(r"[\w.\- ]{1,60}", args.agente) or not args.agente.strip():
                raise ValueError("Use um nome de sessão com letras, números, espaço, ponto ou hífen.")
            print(atualizar(arquivo, args.acao, args.id, args.agente.strip(), getattr(args, "resultado", None),
                             getattr(args, "sem_conferir", None)))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
