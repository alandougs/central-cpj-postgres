"""Relatório administrativo de O.S. cumpridas; sem leitura dos autos ou alteração de dados."""
import collections
import csv
import datetime
import html
import io
import re
from urllib.parse import urlencode


def _data(valor):
    if not isinstance(valor, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        return None
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError:
        return None


def preparar(casos, inicio, fim, usuarios, config):
    di, df = _data(inicio), _data(fim)
    if not di or not df or di > df:
        raise ValueError("Informe datas válidas de início e fim, com início anterior ou igual ao fim.")
    linhas, sem_data = [], 0
    for c in casos:
        if c.get("status") != "entregue":
            continue
        cumprimento = _data((c.get("datas") or {}).get("entregue"))
        if cumprimento is None:
            sem_data += 1
            continue
        if not di <= cumprimento <= df:
            continue
        relatorios = c.get("relatorios") or []
        nome = lambda arq: str(arq or "").replace("\\", "/").rsplit("/", 1)[-1]
        entregue = nome((c.get("baixa") or {}).get("arquivo"))
        rel = next((r for r in reversed(relatorios) if entregue and nome(r.get("arquivo")) == entregue),
                   relatorios[-1] if relatorios else {})
        responsavel = c.get("responsavel") or ""
        policial = (usuarios.get(responsavel) or responsavel) if responsavel else config.get("investigador")
        linhas.append({
            "os": c.get("ordem_servico") or c.get("id") or "Não informada",
            "data_relatorio": (_data(rel.get("data")) or None),
            "cumprimento": cumprimento,
            "natureza": c.get("natureza") or "Não informada",
            "policial": policial or "Não informado",
        })
    linhas.sort(key=lambda r: (r["cumprimento"], r["os"]))
    return {"inicio": di, "fim": df, "linhas": linhas, "total": len(linhas),
            "naturezas": dict(sorted(collections.Counter(r["natureza"] for r in linhas).items())),
            "sem_data": sem_data, "unidade": config.get("unidade") or "Central CPJ"}


def _br(data):
    return data.strftime("%d/%m/%Y") if data else "Não informada"


def html_relatorio(dados):
    e = lambda valor: html.escape(str(valor), quote=True)
    linhas = "".join(
        "<tr>" + "".join(f"<td>{e(v)}</td>" for v in (
            r["os"], _br(r["data_relatorio"]), _br(r["cumprimento"]), r["natureza"], r["policial"]
        )) + "</tr>" for r in dados["linhas"]
    )
    resumo = " · ".join(f"{e(n)}: {v}" for n, v in dados["naturezas"].items())
    aviso = (f'<p class="aviso">Há {dados["sem_data"]} O.S. com status entregue sem data de cumprimento válida; '
             'não entram na contagem do período.</p>') if dados["sem_data"] else ""
    query = urlencode({"inicio": dados["inicio"].isoformat(), "fim": dados["fim"].isoformat(), "formato": "csv"})
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>O.S. cumpridas — {_br(dados["inicio"])} a {_br(dados["fim"])}</title>
<style>
*{{box-sizing:border-box}}body{{font:14px Arial,sans-serif;color:#182332;background:#edf0f3;margin:0;padding:28px}}
main{{max-width:1100px;margin:auto;background:white;padding:32px;border:1px solid #d8dee5}}
h1{{font-size:24px;margin:8px 0 12px}}.unidade{{font-size:13px;color:#455468;margin:0}}
.periodo{{margin:0 0 22px}}.total{{border-top:2px solid #213c5b;padding:16px 0;font-size:17px}}
.total strong{{font-size:26px;margin-left:10px}}.resumo{{margin:0 0 20px;font-size:13px}}
.acoes{{display:flex;gap:10px;margin:0 0 24px}}button,.acoes a{{font:inherit;padding:9px 13px;border:1px solid #213c5b;
border-radius:4px;background:white;color:#213c5b;text-decoration:none;cursor:pointer}}button{{background:#213c5b;color:white}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid #d8dee5;vertical-align:top;overflow-wrap:anywhere}}
th{{background:#f0f3f6;color:#213c5b}}td:nth-child(1),td:nth-child(2),td:nth-child(3){{white-space:nowrap}}
.nota,.aviso{{font-size:12px;line-height:1.5;color:#455468}}.nota{{margin-top:20px}}.aviso{{color:#783e00}}
@page{{size:A4;margin:16mm}}@media print{{body{{background:white;padding:0}}main{{padding:0;border:0;max-width:none}}
.acoes{{display:none}}h1{{font-size:20px}}table{{font-size:10px}}th,td{{padding:8px 5px}}thead{{display:table-header-group}}
tr{{break-inside:avoid}}.total,.resumo{{break-inside:avoid}}}}
</style></head><body><main>
<div class="acoes"><button type="button" onclick="window.print()">Imprimir / salvar PDF</button>
<a href="/api/producao/relatorio?{e(query)}">Baixar CSV</a></div>
<p class="unidade">{e(dados["unidade"])}</p><h1>Ordens de Serviço cumpridas</h1>
<p class="periodo">Período de cumprimento: <b>{_br(dados["inicio"])} a {_br(dados["fim"])}</b></p>
<div class="total">Total de O.S. cumpridas <strong id="total-cumpridas">{dados["total"]}</strong></div>
<p class="resumo">{resumo or "Nenhuma O.S. cumprida no período."}</p>
<table><thead><tr><th>O.S.</th><th>Data do relatório</th><th>Data de cumprimento</th><th>Natureza</th><th>Policial responsável</th></tr></thead>
<tbody>{linhas}</tbody></table>{aviso}
<p class="nota">Critério: O.S. com status entregue e data de cumprimento dentro do intervalo, incluindo início e fim.
A data do relatório é a registrada no cadastro da versão entregue ou, quando não vinculada, na última versão cadastrada.
Campos ausentes permanecem não informados. Quando a O.S. não tem responsável individual, utiliza-se o investigador configurado na produção.</p>
</main></body></html>'''


def csv_relatorio(dados):
    saida = io.StringIO(newline="")
    w = csv.writer(saida, delimiter=";")
    w.writerow(["O.S.", "Data do relatório", "Data de cumprimento", "Natureza", "Policial responsável"])
    for r in dados["linhas"]:
        valores = [r["os"], _br(r["data_relatorio"]), _br(r["cumprimento"]), r["natureza"], r["policial"]]
        w.writerow(["'" + v if v.lstrip().startswith(("=", "+", "-", "@")) else v for v in valores])
    return saida.getvalue()
