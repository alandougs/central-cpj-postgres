#!/usr/bin/env python3
"""Verificação de sigilo antes de publicar: somente leitura, sobre uma seleção explícita do Git.

  python ferramentas/verificar-publicacao.py --staged        # o que está no índice, pronto para commit
  python ferramentas/verificar-publicacao.py --ref HEAD      # a árvore inteira de uma revisão (ex.: a candidata do CI)

Saída: 0 = aprovado; 1 = achado proibido; 2 = erro de verificação (repositório/ref inválido, git ausente).
Cada achado mostra apenas regra, caminho e linha — nunca o trecho encontrado. Nada é gravado: lê objetos do Git
(`cat-file`) e não altera índice, árvore de trabalho nem configuração. Não chama publicador nem rede.
"""
import argparse
import gzip
import io
import re
import subprocess
import sys
from pathlib import Path

LIMITE_BYTES = 2 * 1024 * 1024
LIMITE_DESCOMPACTADO = 16 * 1024 * 1024

# --- regras por caminho (espelham .gitignore e a varredura do publicador legado)
EXT_DOCUMENTO = re.compile(r"\.(docx?|pdf|png|jpe?g|tiff?|xlsx?|zip|traineddata|patch)$", re.I)
EXT_BANCO = re.compile(r"\.(sqlite\d?|db|ffs_db)(-wal|-shm)?$|\.sqlite\d?-(wal|shm)$", re.I)
EXT_CHAVE = re.compile(r"\.(pem|key|crt|pfx|p12)$", re.I)
NOME_ENV = re.compile(r"(^|/)\.env(\..+)?$")
NOME_ASSINATURA = re.compile(r"(^|/)[^/]*(assinatura|signature|rubrica)[^/]*$|(^|/)modelos/assinaturas/", re.I)
PASTAS_LOCAIS = re.compile(
    r"^(ordens-de-servico|usuarios|rag|producao|consulta|referencias|exportacoes|acervo|data|Imagens|\.claude|\.gemini)/")
EXCECOES_PASTAS = {"usuarios/.gitkeep", "rag/README.md", "producao/config.json"}
CASO_REAL = re.compile(r"(^|/)casos/(?!_MODELO-CASO/)")
CONFIG_LOCAL = re.compile(r"(^|/)config/(?!\.gitkeep$)")

# --- regras por conteúdo (texto)
SEGREDOS = [
    ("C01", "chave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("C02", "token de provedor", re.compile(
        r"\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-[A-Za-z0-9]{32,}|\bghp_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"
        r"|\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_-]{35}\b|\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("C03", "segredo atribuído", re.compile(
        r"""(?i)\b(?:api[_-]?key|secret|token|senha|password|passwd)\b['"]?\s*[:=]\s*(['"])(?!\1)([^'"\s]{16,})\1""")),
]
PLACEHOLDER = re.compile(r"(?i)x{4,}|exemplo|example|fictic|dummy|changeme|placeholder|sua[_-]|seu[_-]|<[^>]+>|\$\{|\{\{|\*{4,}|\.{4,}")
CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")
# Testes e fixtures usam dados fictícios por regra do projeto; segredos de verdade continuam proibidos em qualquer lugar.
CAMINHO_TESTE = re.compile(r"(^|/)(testes|tests)/|(^|/)teste_[^/]*$|(^|/)fixtures?[^/]*$")


class ErroVerificacao(Exception):
    pass


def git(repo, *args, entrada=None):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, input=entrada, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise ErroVerificacao(f"git indisponível: {e}") from None
    if r.returncode != 0:
        raise ErroVerificacao(r.stderr.decode("utf-8", "replace").strip().splitlines()[-1] if r.stderr else f"git {args[0]} falhou")
    return r.stdout


def selecionar(repo, staged, ref):
    """[(caminho, sha-do-blob, tamanho)] da seleção explícita, sem tocar no repositório."""
    if staged:
        nomes = [n for n in git(repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode("utf-8", "replace").split("\0") if n]
        if not nomes:
            return []
        indice = {}
        for linha in git(repo, "ls-files", "-s", "-z").decode("utf-8", "replace").split("\0"):
            if linha:
                meta, caminho = linha.split("\t", 1)
                indice[caminho] = meta.split()[1]
        return [(n, indice[n], None) for n in nomes if n in indice]
    saida = git(repo, "ls-tree", "-r", "-z", "--long", ref).decode("utf-8", "replace")
    itens = []
    for linha in saida.split("\0"):
        if not linha:
            continue
        meta, caminho = linha.split("\t", 1)
        modo, tipo, sha, tamanho = meta.split(None, 3)
        if tipo == "blob" and modo != "160000":
            itens.append((caminho, sha, int(tamanho.strip()) if tamanho.strip().isdigit() else None))
    return itens


def regra_de_caminho(caminho):
    if CASO_REAL.search(caminho):
        return "P01", "pasta de caso real"
    if CONFIG_LOCAL.search(caminho):
        return "P02", "configuração local"
    if EXT_BANCO.search(caminho):
        return "P03", "banco de dados"
    if NOME_ENV.search(caminho) and not caminho.endswith(".env.example"):
        return "P04", "arquivo de ambiente/credenciais"
    if EXT_CHAVE.search(caminho):
        return "P04", "chave/certificado"
    if NOME_ASSINATURA.search(caminho):
        return "P05", "assinatura"
    if PASTAS_LOCAIS.search(caminho) and caminho not in EXCECOES_PASTAS:
        return "P06", "pasta de dados locais"
    if EXT_DOCUMENTO.search(caminho):
        return "P07", "documento/mídia (modelo operacional, autos ou imagem)"
    return None


def cpf_valido(texto):
    d = [int(c) for c in re.sub(r"\D", "", texto)]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for j in (9, 10):
        soma = sum(d[i] * (j + 1 - i) for i in range(j))
        dv = (soma * 10) % 11 % 10
        if dv != d[j]:
            return False
    return True


def achados_de_conteudo(caminho, bruto):
    if caminho.lower().endswith(".gz"):          # métricas compactadas: inspeciona o conteúdo descompactado
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(bruto)) as g:
                bruto = g.read(LIMITE_DESCOMPACTADO + 1)
        except (OSError, EOFError):
            return [("P09", "binário não inspecionável", caminho, None)]
        if len(bruto) > LIMITE_DESCOMPACTADO:
            return [("P09", "binário não inspecionável", caminho, None)]
    if b"\0" in bruto[:8192]:
        return []
    texto = bruto.decode("utf-8", "replace")
    teste = bool(CAMINHO_TESTE.search(caminho))
    achados = []
    for numero, linha in enumerate(texto.splitlines(), 1):
        achou = False
        for regra, descricao, padrao in SEGREDOS:       # um achado por linha: a regra mais específica vence
            for m in padrao.finditer(linha):
                valor = m.group(2) if regra == "C03" else m.group(0)
                if regra == "C03" and (teste or PLACEHOLDER.search(valor)):
                    continue
                achados.append((regra, descricao, caminho, numero))
                achou = True
                break
            if achou:
                break
        if not teste:
            for m in CPF.finditer(linha):
                if cpf_valido(m.group(0)):
                    achados.append(("C04", "CPF com dígitos válidos", caminho, numero))
                    break
    return achados


def conteudos(repo, itens):
    """Lê os blobs com um único `git cat-file --batch` (somente leitura)."""
    if not itens:
        return
    entrada = "".join(f"{sha}\n" for _, sha, _ in itens).encode()
    saida = git(repo, "cat-file", "--batch", entrada=entrada)
    pos = 0
    for caminho, sha, _ in itens:
        fim = saida.index(b"\n", pos)
        cab = saida[pos:fim].split()
        if len(cab) != 3 or cab[1] != b"blob":
            raise ErroVerificacao(f"objeto inesperado para {caminho}")
        tamanho = int(cab[2])
        yield caminho, saida[fim + 1:fim + 1 + tamanho]
        pos = fim + 1 + tamanho + 1


def verificar(repo, staged=False, ref=None):
    itens = selecionar(repo, staged, ref)
    achados = []
    para_ler = []
    for caminho, sha, tamanho in itens:
        regra = regra_de_caminho(caminho)
        if regra:
            achados.append((regra[0], regra[1], caminho, None))
        elif tamanho is not None and tamanho > LIMITE_BYTES:
            achados.append(("P08", "arquivo grande (>2 MB)", caminho, None))
        else:
            para_ler.append((caminho, sha, tamanho))
    for caminho, bruto in conteudos(repo, para_ler):
        if len(bruto) > LIMITE_BYTES:
            achados.append(("P08", "arquivo grande (>2 MB)", caminho, None))
        else:
            achados += achados_de_conteudo(caminho, bruto)
    return len(itens), sorted(achados, key=lambda a: (a[2], a[3] or 0, a[0]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--staged", action="store_true", help="arquivos adicionados/modificados no índice")
    grupo.add_argument("--ref", help="árvore completa de uma revisão (ex.: HEAD)")
    ap.add_argument("-C", dest="repo", type=Path, default=Path(__file__).resolve().parent.parent, help="raiz do repositório")
    args = ap.parse_args(argv)
    try:
        total, achados = verificar(args.repo, args.staged, args.ref)
    except ErroVerificacao as e:
        print(f"Erro de verificação: {e}", file=sys.stderr)
        return 2
    for regra, descricao, caminho, linha in achados:
        print(f"{regra} {descricao}: {caminho}{f':{linha}' if linha else ''}")
    alvo = "índice" if args.staged else args.ref
    print(f"verificar-publicacao: {total} arquivo(s) em {alvo}; {len(achados)} achado(s) proibido(s).")
    return 1 if achados else 0


if __name__ == "__main__":
    raise SystemExit(main())
