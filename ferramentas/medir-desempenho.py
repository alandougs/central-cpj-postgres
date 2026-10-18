#!/usr/bin/env python3
"""Medição comparável de desempenho (baseline × candidato). Não é teste de regressão e não bloqueia nada.

  python ferramentas/medir-desempenho.py --candidato <raiz> [--baseline <raiz>] [--repeticoes 5] [--casos 60] [--saida r.json]

Cada execução usa um workspace fictício novo e idêntico (mesma massa, mesma configuração), um servidor local novo e um
navegador (Edge via Playwright) com perfil novo. Há um par de aquecimento descartado e as demais execuções alternam a ordem
(ABAB...) para que deriva da máquina não favoreça um lado. Mede abertura da aplicação, consulta de tarefas, navegação entre
abas ociosa e durante OCR, tarefas longas do navegador e memória (servidor + filhos e navegador, em working set). Só dados
fictícios; nada é gravado fora de TEMP. Saída: tabela (mediana/mín/máx/dispersão) e JSON opcional. Códigos: 0 medido;
2 erro de medição.
"""
import argparse
import json
import os
import platform
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUNTIME = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
METRICAS = [  # (chave, rótulo, unidade, menor é melhor)
    ("abertura_ms", "abertura da aplicação", "ms"),
    ("tarefas_mediana_ms", "GET /api/tarefas (mediana de 20)", "ms"),
    ("casos_ms", "GET /api/casos", "ms"),
    ("navegacao_ocioso_ms", "navegação entre abas (média, ocioso)", "ms"),
    ("navegacao_durante_ocr_mediana_ms", "navegação durante OCR (mediana)", "ms"),
    ("navegacao_durante_ocr_max_ms", "navegação durante OCR (máximo)", "ms"),
    ("longtasks_max_ms", "maior tarefa longa do navegador", "ms"),
    ("ocr_duracao_s", "autos fictícios até concluir", "s"),
    ("mem_servidor_ocioso_mb", "memória do servidor, ocioso", "MB"),
    ("mem_servidor_ocr_max_mb", "memória do servidor + filhos, durante OCR", "MB"),
    ("pico_servidor_mb", "pico do servidor (SO)", "MB"),
    ("mem_navegador_ocioso_mb", "memória do navegador, ocioso", "MB"),
    ("mem_navegador_ocr_max_mb", "memória do navegador, durante OCR", "MB"),
    ("heap_js_mb", "heap JS ao final", "MB"),
]


def git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None


def identificar(raiz):
    return {"raiz": str(raiz), "revisao": git(raiz, "rev-parse", "--short", "HEAD"),
            "limpo": git(raiz, "status", "--porcelain", "--untracked-files=no") == ""}


def app_de(raiz):
    app = raiz / "plugin/investigacao-cpj/app"
    if not (app / "servidor.py").is_file():
        raise SystemExit(f"servidor.py não encontrado em {app}")
    return app


def montar_workspace(ws, casos, config_origem):
    """Mesma massa para os dois lados: N casos fictícios mínimos e modo solo."""
    modelo = ws / "casos/_MODELO-CASO"
    modelo.mkdir(parents=True)
    (modelo / "caso.json").write_text(json.dumps({"datas": {}, "financeiro": {}, "ip": {}, "resultado": {}, "relatorios": []}), encoding="utf-8")
    for n in range(1, casos + 1):
        d = ws / f"casos/OS-{n:03d}-2026"
        (d / "00-originais").mkdir(parents=True)
        (d / "caso.json").write_text(json.dumps({
            "id": d.name, "ordem_servico": f"{n}/2026", "status": "analise" if n % 3 else "recebido",
            "ip": {"numero": f"{n:04d}/2026"}, "datas": {"recebimento": "2026-10-01"}, "financeiro": {}, "resultado": {}, "relatorios": []}),
            encoding="utf-8")
    shutil.copytree(config_origem, ws / "config")      # mesmo administrador fictício para os dois lados
    (ws / "config/solo.json").write_text('{"ativo":true}', encoding="utf-8")


def gerar_config(destino):
    """Cria uma única vez o administrador fictício (o modo solo exige exatamente um administrador ativo)."""
    sys.path.insert(0, str(RAIZ / "plugin/investigacao-cpj/app"))
    from auth import Auth
    ws = destino.parent
    Auth(str(ws)).salvar_usuario("medicao", "Operador fictício de medição", "admin", "SenhaFicticia123")
    shutil.copytree(ws / "config", destino)
    shutil.rmtree(ws / "config")


def gerar_pdf(destino):
    sys.path.insert(0, str(RAIZ / "plugin/investigacao-cpj/app"))
    from testes.e2e.pdf_aux import gerar_pdf_sintetico_e2e
    gerar_pdf_sintetico_e2e(destino, paginas_texto=2, paginas_imagem=4)


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def uma_execucao(raiz, casos, pdf_origem, config_origem, node_modules):
    app = app_de(raiz)
    ws = Path(tempfile.mkdtemp(prefix="cpj-desempenho-"))
    processo = None
    try:
        pdf = ws / "autos-ficticios.pdf"
        shutil.copyfile(pdf_origem, pdf)
        montar_workspace(ws, casos, config_origem)
        porta = porta_livre()
        env = dict(os.environ, CPJ_WORKSPACE=str(ws), CPJ_SEM_AGENTE_EMBUTIDO="1", CPJ_IA_LOCAL_MODELO="",
                   PYTHONIOENCODING="utf-8", APPDATA=str(ws / "appdata"), CPJ_NODE_MODULES=str(node_modules))
        env.pop("CPJ_WORKSPACES", None)
        log = (ws / "servidor.log").open("a", encoding="utf-8")
        processo = subprocess.Popen([sys.executable, "-X", "utf8", str(app / "servidor.py"), "--workspace", str(ws),
                                     "--porta", str(porta), "--somente-local", "--sem-navegador"],
                                    env=env, stdout=log, stderr=subprocess.STDOUT)
        url = f"http://127.0.0.1:{porta}"
        fim = time.monotonic() + 40
        while True:
            if processo.poll() is not None:
                raise RuntimeError("servidor encerrou: " + (ws / "servidor.log").read_text(encoding="utf-8")[-2000:])
            try:
                with urllib.request.urlopen(url + "/api/sessao", timeout=1) as r:
                    if json.load(r).get("solo"):
                        break
            except OSError:
                if time.monotonic() > fim:
                    raise RuntimeError("servidor não iniciou")
                time.sleep(.2)
        env_n = dict(env, MD_URL=url, MD_WS=str(ws), MD_PID=str(processo.pid), MD_PDF=str(pdf), MD_PERFIL=str(ws / "perfil-navegador"))
        r = subprocess.run([str(RUNTIME / "bin/node.exe"), str(Path(__file__).with_suffix(".cjs"))], env=env_n,
                           capture_output=True, text=True, encoding="utf-8", timeout=240)
        if r.returncode != 0:
            raise RuntimeError("medição falhou: " + (r.stderr or r.stdout)[-2000:])
        dados = json.loads(r.stdout)
        nav = dados.get("navegacao_ocioso_ms") or {}
        dados["navegacao_ocioso_ms"] = statistics.mean(nav.values()) if nav else None
        return dados
    finally:
        if processo is not None:
            processo.terminate()
            try:
                processo.wait(timeout=8)
            except subprocess.TimeoutExpired:
                processo.kill()
        shutil.rmtree(ws, ignore_errors=True)


def resumo(valores):
    v = [x for x in valores if isinstance(x, (int, float))]
    if not v:
        return None
    med = statistics.median(v)
    return {"n": len(v), "mediana": round(med, 2), "min": round(min(v), 2), "max": round(max(v), 2),
            "dispersao_pct": round((max(v) - min(v)) / med * 100, 1) if med else 0.0}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--candidato", type=Path, default=RAIZ, help="raiz do código candidato (padrão: este repositório)")
    ap.add_argument("--baseline", type=Path, help="raiz do código de referência (ex.: worktree na revisão anterior)")
    ap.add_argument("--repeticoes", type=int, default=5)
    ap.add_argument("--casos", type=int, default=60, help="casos fictícios por workspace")
    ap.add_argument("--limite", type=float, default=10.0, help="variação percentual que marca 'investigar' (padrão 10)")
    ap.add_argument("--saida", type=Path)
    args = ap.parse_args(argv)
    if not (RUNTIME / "bin/node.exe").is_file():
        print("Node do runtime local não encontrado.", file=sys.stderr)
        return 2
    lados = [("candidato", args.candidato.resolve())] + ([("baseline", args.baseline.resolve())] if args.baseline else [])
    node_modules = RUNTIME / "node_modules"
    # PDF gerado uma única vez e copiado: a entrada é byte a byte a mesma para todas as execuções.
    base = Path(tempfile.mkdtemp(prefix="cpj-desempenho-base-"))
    try:
        pdf_origem = base / "autos-ficticios.pdf"
        gerar_pdf(pdf_origem)
        config_origem = base / "config-origem"
        gerar_config(config_origem)
        resultados = {n: [] for n, _ in lados}
        try:
            for i in range(args.repeticoes + 1):                 # 0 = aquecimento, descartado
                ordem = lados if i % 2 == 0 else lados[::-1]
                for nome, raiz in ordem:
                    d = uma_execucao(raiz, args.casos, pdf_origem, config_origem, node_modules)
                    print(f"[{'aquecimento' if i == 0 else f'{i}/{args.repeticoes}'}] {nome}: abertura={d.get('abertura_ms')} ms, "
                          f"ocr={d.get('ocr_duracao_s')} s, concluiu={d.get('ocr_concluiu')}", flush=True)
                    if i > 0:
                        resultados[nome].append(d)
        except (RuntimeError, subprocess.SubprocessError, OSError, ValueError) as e:
            print(f"Erro de medição: {e}", file=sys.stderr)
            return 2
    finally:
        shutil.rmtree(base, ignore_errors=True)
    agregado = {n: {c: resumo([d.get(c) for d in ds]) for c, _, _ in METRICAS} for n, ds in resultados.items()}
    sem_ocr = {n: sum(1 for d in ds if not d.get("ocr_concluiu")) for n, ds in resultados.items()}
    saida = {"gerado_em": time.strftime("%Y-%m-%d %H:%M:%S"), "repeticoes": args.repeticoes, "casos": args.casos,
             "ambiente": {"sistema": platform.system(), "versao": platform.release(), "python": platform.python_version(),
                          "maquina": platform.machine(), "cpus": os.cpu_count()},
             "lados": {n: identificar(r) for n, r in lados}, "agregado": agregado, "execucoes": resultados,
             "execucoes_sem_ocr_concluido": sem_ocr, "limite_investigar_pct": args.limite, "marcados": []}
    print(f"\n{'métrica':46} {'':10}" + "".join(f"{n:>34}" for n, _ in lados) + ("      Δ mediana" if args.baseline else ""))
    for chave, rotulo, un in METRICAS:
        linha = f"{rotulo + ' [' + un + ']':46} "
        celulas = []
        for n, _ in lados:
            a = agregado[n][chave]
            celulas.append("—".rjust(34) if not a else f"{a['mediana']:>9} ({a['min']}–{a['max']}; ±{a['dispersao_pct']}%)".rjust(34))
        delta = ""
        if args.baseline and agregado["candidato"][chave] and agregado["baseline"][chave] and agregado["baseline"][chave]["mediana"]:
            b, c = agregado["baseline"][chave]["mediana"], agregado["candidato"][chave]["mediana"]
            pct = (c - b) / b * 100
            delta = f"  {pct:+.1f}%"
            if pct > args.limite:
                disp = max(agregado["baseline"][chave]["dispersao_pct"], agregado["candidato"][chave]["dispersao_pct"])
                delta += " INVESTIGAR" + (" (dentro da dispersão)" if pct <= disp else "")
                saida["marcados"].append({"metrica": chave, "variacao_pct": round(pct, 1), "dispersao_pct": disp})
        print(linha + "".join(celulas) + delta)
    for n, k in sem_ocr.items():
        if k:
            print(f"AVISO: {n} teve {k} execução(ões) sem OCR concluído no prazo — as métricas de OCR dessas execuções não são comparáveis.")
    if args.saida:
        args.saida.write_text(json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON: {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
