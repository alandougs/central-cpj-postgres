#!/usr/bin/env python3
"""Agente de plantão da Central CPJ — fica de alerta e executa os pedidos de IA acionados pelo painel.

MODO SESSÃO DE CHAT (Codex, Claude, Antigravity etc. guiados pelo PROMPT-AGENTE-PLANTAO.md):
  python ferramentas/agente-plantao.py aguardar  --agente Codex-1 --tipo codex [--minutos 10]
      -> espera até um pedido ser reservado para este agente e imprime o PEDIDO com as instruções completas.
  python ferramentas/agente-plantao.py progresso <PEDIDO> --agente Codex-1 --pct 45 --etapa "minuta redigida"
      -> sinal de vida + progresso na Central. Responde CANCELADO (código 3) se a Central cancelou.
  python ferramentas/agente-plantao.py concluir  <PEDIDO> --agente Codex-1 --resumo "o que foi feito..."
  python ferramentas/agente-plantao.py falhar    <PEDIDO> --agente Codex-1 --erro "motivo"

MODO AUTOMÁTICO (sem sessão de chat; usa o CLI do agente em modo não interativo):
  python ferramentas/agente-plantao.py executar --agente Codex-Auto --tipo codex     (Ctrl+C para parar)

ADMINISTRAÇÃO (somente no computador da Central):
  python ferramentas/agente-plantao.py agentes | pedidos | aprovar <NOME> | revogar <NOME>

EXPEDIENTE (economia): os agentes só reservam pedidos no horário de trabalho de config/plantao.json (padrão seg–sex 9h–18h).
Fora dele, 'aguardar' encerra com código 5 e 'executar' fica em espera; o pedido continua na fila. Para atender mesmo assim,
por decisão do usuário no chat:  aguardar ... --forcar   (vale só para aquela espera).

Agente novo fica "aguardando aprovação" até o administrador aprová-lo. Códigos de saída: 0 ok; 1 sem pedido (tempo esgotado);
2 agente não aprovado; 3 pedido cancelado pela Central; 4 erro; 5 fora do expediente.
"""
import argparse, json, os, sys, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # instalação (código do plugin)
WS = os.environ.get("CPJ_WORKSPACE") or RAIZ                          # dados (padrão: a própria pasta CPJ)
sys.path.insert(0, os.path.join(RAIZ, "plugin", "investigacao-cpj", "app"))
import plantao as PL  # noqa: E402

try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass


def main():
    ap = argparse.ArgumentParser(description="Agente de plantão da Central CPJ")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("aguardar"); s.add_argument("--agente", required=True); s.add_argument("--tipo", default="outro", choices=PL.TIPOS)
    s.add_argument("--minutos", type=float, default=10)
    s.add_argument("--forcar", action="store_true", help="atender fora do expediente (somente quando o usuário pedir no chat)")
    s = sub.add_parser("progresso"); s.add_argument("pedido"); s.add_argument("--agente", required=True)
    s.add_argument("--pct", type=int); s.add_argument("--etapa"); s.add_argument("--detalhe")
    s = sub.add_parser("concluir"); s.add_argument("pedido"); s.add_argument("--agente", required=True); s.add_argument("--resumo", required=True)
    s = sub.add_parser("falhar"); s.add_argument("pedido"); s.add_argument("--agente", required=True); s.add_argument("--erro", required=True)
    s = sub.add_parser("executar"); s.add_argument("--agente", required=True); s.add_argument("--tipo", required=True, choices=("claude", "codex"))
    sub.add_parser("agentes"); sub.add_parser("pedidos"); sub.add_parser("expediente")
    s = sub.add_parser("aprovar"); s.add_argument("nome")
    s = sub.add_parser("revogar"); s.add_argument("nome")
    a = ap.parse_args()
    pl = PL.Plantao(WS)

    if a.cmd == "aguardar":
        ag = pl.registrar(a.agente, a.tipo, "chat")
        if not ag["aprovado"]:
            print(f"AGENTE NÃO APROVADO: '{a.agente}' foi registrado e aguarda aprovação do administrador.\n"
                  f"No computador da Central: python ferramentas/agente-plantao.py aprovar \"{a.agente}\"")
            return 2
        def fora():
            if a.forcar or PL.em_expediente(WS): return False
            pl.sinal(a.agente, "fora do expediente", PL.aviso_fora_expediente(WS))
            print(f"FORA DO EXPEDIENTE: {PL.aviso_fora_expediente(WS)}.\nNão reserve pedidos agora. Encerre o plantão e aguarde o "
                  "usuário; só use --forcar se ele pedir expressamente no chat.")
            return True
        if fora(): return 5
        fim = time.time() + a.minutos * 60
        print(f"De plantão como '{a.agente}' ({a.tipo}) por até {a.minutos:g} min"
              + (" (FORA DO EXPEDIENTE, a pedido do usuário)" if a.forcar and not PL.em_expediente(WS) else "")
              + " — aguardando pedidos da Central…", flush=True)
        while time.time() < fim:
            if fora(): return 5
            pl.sinal(a.agente, "ocioso", "sessão de chat aguardando")
            job = pl.reivindicar(a.agente)
            if job:
                print("=" * 78)
                print(f"PEDIDO: {job['id']}\nCASO: {job['caso']}\nAÇÃO: {job['acao']}\nSOLICITANTE: {job['solicitante']}")
                print("-" * 78)
                print(PL.montar_prompt(job, WS, "chat", a.agente))
                print("=" * 78)
                return 0
            time.sleep(3)
        pl.sinal(a.agente, "ocioso", "tempo de espera esgotado")
        print("NENHUM PEDIDO no período. Rode 'aguardar' novamente para continuar de plantão.")
        return 1

    if a.cmd == "progresso":
        ok = pl.progresso(a.pedido, a.agente, a.pct, a.etapa, a.detalhe)
        if not ok:
            print("CANCELADO: a Central cancelou este pedido (ou ele não está mais em execução). Pare o trabalho e não conclua.")
            return 3
        print(f"OK: {a.pedido} {a.pct if a.pct is not None else ''}% {a.etapa or ''}".strip()); return 0

    if a.cmd == "concluir":
        p = pl.pedido(a.pedido)
        if p and p["cancelar"]:
            pl.falhar(a.pedido, a.agente, "Cancelado pela Central."); print("CANCELADO: pedido encerrado sem conclusão."); return 3
        extra = PL.pos_processar(WS, p["caso"], p["acao"]) if p else {}
        pl.concluir(a.pedido, a.agente, {"resumo": a.resumo[:1500], **extra})
        print(f"CONCLUÍDO: {a.pedido}" + (f" · DOCX {extra['docx']}" if extra.get("docx") else "")); return 0

    if a.cmd == "falhar":
        pl.falhar(a.pedido, a.agente, a.erro); print(f"REGISTRADO: {a.pedido} com erro."); return 0

    if a.cmd == "executar":
        pl.registrar(a.agente, a.tipo, "auto")
        if not [x for x in pl.agentes() if x["nome"] == a.agente][0]["aprovado"]:
            print(f"AGENTE NÃO APROVADO: aprove no computador da Central: python ferramentas/agente-plantao.py aprovar \"{a.agente}\"")
            return 2
        pronto, motivo = PL.provedor_pronto(a.tipo)
        print(f"De plantão (automático) como '{a.agente}' ({a.tipo}). Provedor: {'pronto' if pronto else motivo}. "
              f"Expediente: {PL.descricao_expediente(WS)}"
              + ("" if PL.em_expediente(WS) else f" — agora {PL.aviso_fora_expediente(WS)}") + ". Ctrl+C para parar.", flush=True)
        try: PL.trabalhar(WS, a.agente, a.tipo)
        except KeyboardInterrupt:
            pl.sinal(a.agente, "fora do ar", "encerrado pelo usuário"); print("Plantão encerrado.")
        return 0

    if a.cmd == "expediente":
        dentro = PL.em_expediente(WS)
        print(f"Expediente: {PL.descricao_expediente(WS)} (config/plantao.json). Agora: "
              + ("DENTRO — agentes atendem a fila." if dentro else PL.aviso_fora_expediente(WS) + "."))
        return 0 if dentro else 5

    if a.cmd == "agentes":
        for x in pl.agentes():
            print(f"{x['nome']:<22} {x['tipo']:<11} {x['modo']:<5} {x['estado']:<22} {'aprovado' if x['aprovado'] else 'NÃO aprovado':<13}"
                  f" {x['job'] or ''} {x['detalhe'] or ''}")
        return 0
    if a.cmd == "pedidos":
        for p in pl.pedidos():
            print(f"{p['id']:<14} {p['estado']:<11} {p['caso']:<16} {p['acao']:<10} {p['agente'] or '-':<18} {p['progresso'] or 0:>3}% {p['etapa'] or ''}")
        return 0
    if a.cmd in ("aprovar", "revogar"):
        pl.aprovar(a.nome, a.cmd == "aprovar"); print(f"{a.nome}: {'aprovado' if a.cmd == 'aprovar' else 'aprovação revogada'}."); return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except ValueError as e:
        print(f"ERRO: {e}"); raise SystemExit(4)
