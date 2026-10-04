#!/usr/bin/env python3
"""Teste da tarefa F12: regressões dos 4 apontamentos P1 da revisão do PR #1.
Workspace temporário, dados fictícios, sem IA real.

Uso: python -X utf8 plugin/investigacao-cpj/app/testes/teste_revisao_pr1_f12.py
"""
import json, os, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(AQUI, ".."))
RAIZ = os.path.normpath(os.path.join(APP, "..", "..", ".."))
S_BASE = os.path.normpath(os.path.join(APP, "..", "skills", "base-cpj", "scripts"))
EXTRAIR = os.path.normpath(os.path.join(APP, "..", "skills", "pdf-autos-policiais", "scripts", "extrair.py"))
WS = tempfile.mkdtemp(prefix="cpj-f12-")
os.environ["CPJ_WORKSPACE"] = WS
os.environ["CPJ_PLANTAO_SIMULADO"] = "1"
os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"
sys.path.insert(0, APP); sys.path.insert(0, S_BASE)
falhas = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALHA ") + msg)
    if not cond: falhas.append(msg)


try:
    shutil.copytree(os.path.join(RAIZ, "casos", "_MODELO-CASO"), os.path.join(WS, "casos", "_MODELO-CASO"))
    os.makedirs(os.path.join(WS, "config"), exist_ok=True)

    print("F12.1 Importação rejeita componente com unidade de disco ou ':'")
    from tarefas import _caminho_importavel  # noqa: E402
    ok(_caminho_importavel("casos/OS-1-2026/00-originais/ip.pdf"), "caminho oficial continua aceito")
    ok(not _caminho_importavel("casos/D:/fora.txt"), "casos/D:/fora.txt rejeitado")
    ok(not _caminho_importavel("casos/OS-1-2026/C:fora.txt"), "componente 'C:fora.txt' rejeitado")
    ok(not _caminho_importavel("calibracao/nota.md:oculto"), "fluxo alternativo NTFS rejeitado")

    print("F12.2 Caso antigo sem 'revisao' avança para 2 no primeiro salvamento")
    subprocess.run([sys.executable, os.path.join(S_BASE, "caso.py"), "novo", "--os", "12/2026"],
                   env=dict(os.environ), capture_output=True, check=True)
    import caso as C  # noqa: E402
    p = os.path.join(WS, "casos", "OS-12-2026", "caso.json")
    d = json.load(open(p, encoding="utf-8")); d.pop("revisao", None)
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    salvo = C.salvar(C.carregar("OS-12-2026"), revisao_esperada=1)
    ok(salvo["revisao"] == 2, f"revisão após o 1º salvamento = {salvo['revisao']} (esperado 2)")
    try:
        C.salvar(C.carregar("OS-12-2026") | {"revisao": 1}, revisao_esperada=1); ok(False, "pedido velho (revisão 1) rejeitado")
    except C.ConcorrenciaErro:
        ok(True, "pedido velho (revisão 1) rejeitado com conflito")

    print("F12.3 Correção visual substitui página de OCR a conferir que estava em cache")
    from PIL import Image  # noqa: E402
    pdf = os.path.join(WS, "branco.pdf"); Image.new("RGB", (600, 800), "white").save(pdf)
    saida = os.path.join(WS, "extracao")
    cmd = [sys.executable, EXTRAIR, pdf, "--saida", saida, "--ocr", "visao"]
    subprocess.run(cmd, capture_output=True, check=True)
    ck = os.path.join(saida, ".checkpoint", "p0001.json"); est = json.load(open(ck, encoding="utf-8"))
    est["flag"] = "conferir"
    est["reg"] = {"pagina": 1, "metodo": "ocr-tesseract", "confianca_media": 40.0, "texto": "OCR DUVIDOSO 12?45", "conferir": True}
    json.dump(est, open(ck, "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(saida, "transcricoes_visuais", "p0001.md"), "w", encoding="utf-8").write("TEXTO CONFERIDO 12345")
    subprocess.run(cmd, capture_output=True, check=True)
    md = open(os.path.join(saida, "transcricao.md"), encoding="utf-8").read()
    ok("TEXTO CONFERIDO 12345" in md and "OCR DUVIDOSO" not in md, "transcricao.md usa a correção visual")
    ok("transcricao-visual-llm" in md, "método registrado como transcrição visual")

    print("F12.4 Erro numa etapa do fluxo completo encerra as etapas seguintes")
    import plantao as PL  # noqa: E402
    pl = PL.Plantao(WS)
    pl.registrar("Agente-F12", "claude", "auto", aprovado=True)
    pl.enfileirar("OS-12-2026", "completo", "teste")
    p1 = pl.reivindicar("Agente-F12")
    ok(p1 and p1["acao"] == "analisar", "1ª etapa (analisar) reservada")
    pl.falhar(p1["id"], "Agente-F12", "falha simulada")
    grupo = [x for x in pl.pedidos() if x["grupo"] == p1["grupo"]]
    ok(all(x["estado"] in ("erro", "cancelada") for x in grupo), f"nenhuma etapa pendente: {[x['estado'] for x in grupo]}")
    ok(pl.reivindicar("Agente-F12") is None, "nada mais a reservar do fluxo que falhou")
    try:
        pl.enfileirar("OS-12-2026", "completo", "teste"); ok(True, "novo pedido para o caso aceito após a falha")
    except ValueError as e:
        ok(False, f"novo pedido para o caso aceito após a falha ({e})")
finally:
    shutil.rmtree(WS, ignore_errors=True)

print(f"\n{len(falhas)} FALHA(S)" if falhas else "\nTUDO OK")
sys.exit(1 if falhas else 0)
