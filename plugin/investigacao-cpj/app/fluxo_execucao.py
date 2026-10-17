"""Registro durável de fluxos por O.S. (UN13).

Correlaciona O.S. -> execução -> etapa -> tentativa no SQLite de coordenação
existente (`config/plantao.sqlite`), sem criar outro banco ou servidor de filas.

- `caso.json` continua sendo a fonte do estado oficial; entrega nunca é escrita aqui.
- `processamento.json` continua sendo o checkpoint da extração; aqui só há correlação.
- Escritas são transações curtas com versão otimista; falha de escrita é propagada
  (sem tentativa silenciosa de "compensar"), para que o despacho seja impedido.
- Migração aditiva, versionada e idempotente (`fluxos_migracoes`); não usa
  `PRAGMA user_version`, que pode pertencer a outro componente.
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager

ESTADOS = ("na_fila", "em_execucao", "aguardando_operador", "falhou", "cancelada", "concluida")
ETAPAS = ("recebimento", "extracao", "analise", "relatorio", "revisao")
ORIGENS = ("processamento", "tarefa", "plantao")
TERMINAIS = frozenset({"falhou", "cancelada", "concluida"})
TRANSICOES = {
    "na_fila": frozenset({"em_execucao", "aguardando_operador", "cancelada"}),
    "em_execucao": frozenset({"aguardando_operador", "falhou", "cancelada", "concluida"}),
    "aguardando_operador": frozenset(),          # só sai por reconciliar()
}
RECONCILIA_PARA = frozenset({"na_fila", "cancelada"})
PRECEDENCIA = ("falhou", "aguardando_operador", "em_execucao", "na_fila")   # estado que pede atenção primeiro
ACAO_PARA_ETAPA = {"analisar": "analise", "financeiro": "analise", "relatorio": "relatorio", "revisar": "revisao"}
ESTADO_PROCESSAMENTO = {"na_fila": "na_fila", "processando": "em_execucao", "concluido": "concluida",
                        "erro": "falhou", "cancelado": "cancelada"}
ESTADO_PEDIDO = {"pendente": "na_fila", "executando": "em_execucao", "concluida": "concluida",
                 "erro": "falhou", "cancelada": "cancelada"}
LIMITE_MAX = 100


def _ddl_v1(c) -> None:
    c.execute("""CREATE TABLE IF NOT EXISTS fluxos_execucoes(
        seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, caso TEXT NOT NULL,
        solicitante TEXT NOT NULL, chave TEXT NOT NULL, prioridade INTEGER NOT NULL DEFAULT 0,
        tipo TEXT NOT NULL DEFAULT 'fluxo', versao INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL, UNIQUE(caso, solicitante, chave))""")
    c.execute("""CREATE TABLE IF NOT EXISTS fluxos_etapas(
        seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
        execucao_id TEXT NOT NULL REFERENCES fluxos_execucoes(id), etapa TEXT NOT NULL,
        origem TEXT NOT NULL, origem_id TEXT NOT NULL, documento TEXT, estado TEXT NOT NULL,
        versao INTEGER NOT NULL DEFAULT 1, progresso REAL, detalhe TEXT NOT NULL DEFAULT '',
        tentativa INTEGER NOT NULL DEFAULT 1, anterior_id TEXT,
        criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL, UNIQUE(origem, origem_id))""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_fluxos_exec_caso ON fluxos_execucoes(caso, seq)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_fluxos_etapas_exec ON fluxos_etapas(execucao_id, seq)")


MIGRACOES = ((1, _ddl_v1),)   # (versão, função DDL aditiva); novas versões só acrescentam ao final


class ConflitoVersao(Exception):
    """A versão informada está obsoleta; nada foi alterado."""


class TransicaoInvalida(Exception):
    """Transição de estado proibida pelo contrato."""


def agora() -> str:
    return datetime.datetime.now().isoformat(timespec="microseconds")


class Fluxos:
    def __init__(self, ws):
        self.ws = str(ws)
        os.makedirs(os.path.join(self.ws, "config"), exist_ok=True)
        self.db = os.path.join(self.ws, "config", "plantao.sqlite")

    # ------------------------------------------------------------ infraestrutura
    @contextmanager
    def _c(self):
        c = sqlite3.connect(self.db, timeout=30, isolation_level=None)
        try:
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA busy_timeout=30000")
            yield c
        finally:
            c.close()

    @contextmanager
    def _tx(self):
        """Transação curta e imediata; desfaz tudo se algo falhar."""
        with self._c() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            else:
                c.execute("COMMIT")

    def migrar(self) -> None:
        """Aplica as migrações pendentes, cada uma tudo-ou-nada: falha antes do registro desfaz o DDL."""
        for versao, ddl in MIGRACOES:
            with self._c() as c:
                existe = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='fluxos_migracoes'").fetchone()
                if existe and c.execute("SELECT 1 FROM fluxos_migracoes WHERE versao=?", (versao,)).fetchone():
                    continue
            with self._tx() as c:
                c.execute("CREATE TABLE IF NOT EXISTS fluxos_migracoes(versao INTEGER PRIMARY KEY, aplicada_em TEXT NOT NULL)")
                if c.execute("SELECT 1 FROM fluxos_migracoes WHERE versao=?", (versao,)).fetchone():
                    continue
                ddl(c)
                self._registrar_migracao(c, versao)

    def _registrar_migracao(self, c, versao: int) -> None:
        c.execute("INSERT INTO fluxos_migracoes(versao, aplicada_em) VALUES(?,?)", (versao, agora()))

    # ------------------------------------------------------------ escrita
    def criar(self, caso: str, solicitante: str, chave: str, prioridade: int = 0, tipo: str = "fluxo") -> dict:
        for nome, v in (("caso", caso), ("solicitante", solicitante), ("chave", chave)):
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"{nome} obrigatório.")
        if type(prioridade) is not int:
            raise ValueError("prioridade deve ser inteiro.")
        with self._tx() as c:
            r = c.execute("SELECT * FROM fluxos_execucoes WHERE caso=? AND solicitante=? AND chave=?",
                          (caso, solicitante, chave)).fetchone()
            if r is None:
                t = agora()
                c.execute("INSERT INTO fluxos_execucoes(id,caso,solicitante,chave,prioridade,tipo,versao,criado_em,atualizado_em) "
                          "VALUES(?,?,?,?,?,?,1,?,?)", (str(uuid.uuid4()), caso, solicitante, chave, prioridade, tipo, t, t))
                r = c.execute("SELECT * FROM fluxos_execucoes WHERE caso=? AND solicitante=? AND chave=?",
                              (caso, solicitante, chave)).fetchone()
        return {k: r[k] for k in ("id", "caso", "solicitante", "chave", "prioridade", "tipo", "versao")}

    def vincular_etapa(self, execucao_id: str, etapa: str, origem: str, origem_id: str, documento: str | None = None,
                       _estado: str = "na_fila", _progresso: float | None = None, _detalhe: str = "") -> dict:
        if etapa not in ETAPAS:
            raise ValueError(f"Etapa inválida: {etapa}")
        if origem not in ORIGENS:
            raise ValueError(f"Origem inválida: {origem}")
        if not isinstance(origem_id, str) or not origem_id.strip():
            raise ValueError("origem_id obrigatório.")
        with self._tx() as c:
            if c.execute("SELECT 1 FROM fluxos_execucoes WHERE id=?", (execucao_id,)).fetchone() is None:
                raise KeyError(f"Execução inexistente: {execucao_id}")
            r = c.execute("SELECT * FROM fluxos_etapas WHERE origem=? AND origem_id=?", (origem, origem_id)).fetchone()
            if r is not None:
                if (r["execucao_id"], r["etapa"]) != (execucao_id, etapa):
                    raise ValueError("Esta origem já está vinculada a outra execução ou etapa.")
                return self._resumo_etapa(r)
            t, eid = agora(), str(uuid.uuid4())
            c.execute("INSERT INTO fluxos_etapas(id,execucao_id,etapa,origem,origem_id,documento,estado,versao,progresso,detalhe,"
                      "tentativa,criado_em,atualizado_em) VALUES(?,?,?,?,?,?,?,1,?,?,1,?,?)",
                      (eid, execucao_id, etapa, origem, origem_id, documento, _estado, _progresso, _detalhe, t, t))
            self._tocar(c, execucao_id, t)
            r = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (eid,)).fetchone()
        return self._resumo_etapa(r)

    @staticmethod
    def _tocar(c, execucao_id: str, t: str) -> None:
        c.execute("UPDATE fluxos_execucoes SET versao=versao+1, atualizado_em=? WHERE id=?", (t, execucao_id))

    @staticmethod
    def _resumo_etapa(r) -> dict:
        return {k: r[k] for k in ("id", "execucao_id", "etapa", "origem", "origem_id", "documento", "estado", "versao",
                                  "progresso", "detalhe", "tentativa", "anterior_id", "criado_em", "atualizado_em")}

    def _mudar(self, etapa_id: str, versao: int, estado: str, progresso, detalhe: str, *, reconciliando: bool) -> dict:
        if estado not in ESTADOS:
            raise ValueError(f"Estado inválido: {estado}")
        if progresso is not None:
            if isinstance(progresso, bool) or not isinstance(progresso, (int, float)) or not 0 <= progresso <= 100:
                raise ValueError("progresso deve estar entre 0 e 100 (ou None).")
        with self._tx() as c:
            r = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (etapa_id,)).fetchone()
            if r is None:
                raise KeyError(f"Etapa inexistente: {etapa_id}")
            if r["versao"] != versao:
                raise ConflitoVersao(f"versão {versao} obsoleta; atual {r['versao']}")
            atual = r["estado"]
            if atual in TERMINAIS:
                raise TransicaoInvalida(f"estado terminal '{atual}' é imutável")
            if reconciliando:
                if atual != "aguardando_operador" or estado not in RECONCILIA_PARA:
                    raise TransicaoInvalida(f"reconciliação inválida: {atual} -> {estado}")
            elif estado != atual and estado not in TRANSICOES.get(atual, ()):
                raise TransicaoInvalida(f"{atual} -> {estado} não permitido")
            t = agora()
            novo_prog = progresso if progresso is not None else (None if estado in ("na_fila",) else r["progresso"])
            c.execute("UPDATE fluxos_etapas SET estado=?, progresso=?, detalhe=?, versao=versao+1, atualizado_em=? "
                      "WHERE id=? AND versao=?", (estado, novo_prog, detalhe or "", t, etapa_id, versao))
            self._tocar(c, r["execucao_id"], t)
            r = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (etapa_id,)).fetchone()
        return self._resumo_etapa(r)

    def atualizar(self, etapa_id: str, versao: int, estado: str, progresso: float | None = None, detalhe: str = "") -> dict:
        return self._mudar(etapa_id, versao, estado, progresso, detalhe, reconciliando=False)

    def reconciliar(self, etapa_id: str, versao: int, estado: str, detalhe: str) -> dict:
        """Única saída de `aguardando_operador`: exige motivo explícito."""
        if not isinstance(detalhe, str) or not detalhe.strip():
            raise ValueError("Reconciliação exige o motivo/resultado conferido.")
        return self._mudar(etapa_id, versao, estado, None, detalhe, reconciliando=True)

    def retentar(self, etapa_id: str, origem_id: str) -> dict:
        """Nova tentativa vinculada à anterior (terminal `falhou`/`cancelada`); a anterior é preservada."""
        with self._tx() as c:
            r = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (etapa_id,)).fetchone()
            if r is None:
                raise KeyError(f"Etapa inexistente: {etapa_id}")
            if r["estado"] not in ("falhou", "cancelada"):
                raise TransicaoInvalida("só etapas falhas ou canceladas admitem nova tentativa")
            if c.execute("SELECT 1 FROM fluxos_etapas WHERE anterior_id=?", (etapa_id,)).fetchone():
                raise TransicaoInvalida("esta tentativa já foi seguida por outra")
            if c.execute("SELECT 1 FROM fluxos_etapas WHERE origem=? AND origem_id=?", (r["origem"], origem_id)).fetchone():
                raise ValueError("origem_id já vinculado.")
            t, eid = agora(), str(uuid.uuid4())
            c.execute("INSERT INTO fluxos_etapas(id,execucao_id,etapa,origem,origem_id,documento,estado,versao,detalhe,tentativa,"
                      "anterior_id,criado_em,atualizado_em) VALUES(?,?,?,?,?,?, 'na_fila',1,'',?,?,?,?)",
                      (eid, r["execucao_id"], r["etapa"], r["origem"], origem_id, r["documento"], r["tentativa"] + 1,
                       etapa_id, t, t))
            self._tocar(c, r["execucao_id"], t)
            n = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (eid,)).fetchone()
        return self._resumo_etapa(n)

    # ------------------------------------------------------------ leitura
    @staticmethod
    def _vigentes(etapas: list[dict]) -> list[dict]:
        """Última tentativa de cada (etapa, documento); as anteriores permanecem só no histórico."""
        por = {}
        for e in etapas:
            k = (e["etapa"], e["documento"] or "")
            if k not in por or e["tentativa"] > por[k]["tentativa"]:
                por[k] = e
        return list(por.values())

    @staticmethod
    def _agregar(exe: dict, etapas: list[dict]) -> dict:
        vig = Fluxos._vigentes(etapas)
        estados = {e["estado"] for e in vig}
        obrigatorias_ok = exe["tipo"] == "legado" or all(
            any(e["etapa"] == o and e["estado"] == "concluida" for e in vig) for o in ETAPAS)
        estado = next((s for s in PRECEDENCIA if s in estados), None)
        if estado is None:   # nada ativo: tudo concluído/cancelado (ou sem etapas)
            if not vig:
                estado = "na_fila"
            elif "cancelada" in estados:
                estado = "cancelada"          # cancelamento interrompe o fluxo; resultados já produzidos ficam
            else:
                estado = "concluida" if obrigatorias_ok else "na_fila"   # na_fila: aguardando a próxima etapa
        pend = []
        for e in sorted(vig, key=lambda x: (ETAPAS.index(x["etapa"]), x["documento"] or "")):
            if e["estado"] in ("aguardando_operador", "falhou"):
                pend.append({"tipo": e["estado"], "etapa": e["etapa"], "documento": e["documento"],
                             "detalhe": e["detalhe"], "etapa_id": e["id"]})
        if exe["tipo"] != "legado" and estado not in ("cancelada", "concluida") and vig:
            for o in ETAPAS:
                if not any(e["etapa"] == o for e in vig):
                    pend.append({"tipo": "etapa_ausente", "etapa": o, "documento": None, "detalhe": "", "etapa_id": None})
        atual = next((e for e in sorted(vig, key=lambda x: ETAPAS.index(x["etapa"]))
                      if e["estado"] not in ("concluida", "cancelada")), None)
        if atual is None and vig:
            atual = sorted(vig, key=lambda x: ETAPAS.index(x["etapa"]))[-1]
        return {"estado": estado, "etapa": atual["etapa"] if atual else None,
                "progresso": atual["progresso"] if atual and atual["estado"] == "em_execucao" else None,
                "pendencias": pend, "documentos": sorted({e["documento"] for e in vig if e["documento"]})}

    def _execucao(self, c, r) -> dict:
        etapas = [self._resumo_etapa(e) for e in
                  c.execute("SELECT * FROM fluxos_etapas WHERE execucao_id=? ORDER BY seq", (r["id"],))]
        exe = {k: r[k] for k in ("seq", "id", "caso", "solicitante", "chave", "prioridade", "tipo", "versao", "criado_em", "atualizado_em")}
        exe.update(self._agregar(exe, etapas))
        exe["execucao_id"] = exe["id"]
        exe["etapas"] = etapas
        return exe

    def obter(self, execucao_id: str) -> dict | None:
        with self._c() as c:
            r = c.execute("SELECT * FROM fluxos_execucoes WHERE id=?", (execucao_id,)).fetchone()
            return self._execucao(c, r) if r else None

    @staticmethod
    def _codificar(chave) -> str:
        return base64.urlsafe_b64encode(json.dumps(chave).encode()).decode().rstrip("=")

    @staticmethod
    def _decodificar(cursor: str):
        try:
            v = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
            if not (isinstance(v, list) and len(v) == 2 and all(type(x) is int for x in v)):
                raise ValueError
            return v
        except Exception:
            raise ValueError("Cursor inválido.") from None

    def listar(self, casos_permitidos: list[str], limite: int = 50, cursor: str | None = None) -> dict:
        """Um item por O.S. autorizada: a execução ativa mais recente (ou, sem ativa, a mais recente)."""
        if type(limite) is not int or not 1 <= limite <= LIMITE_MAX:
            raise ValueError(f"limite deve estar entre 1 e {LIMITE_MAX}.")
        apos = self._decodificar(cursor) if cursor else None
        casos = sorted({c for c in casos_permitidos if isinstance(c, str) and c})
        escolhidas = []
        with self._c() as c:
            for i in range(0, len(casos), 500):
                lote = casos[i:i + 500]
                marcas = ",".join("?" * len(lote))
                por_caso = {}
                for r in c.execute(f"SELECT * FROM fluxos_execucoes WHERE caso IN ({marcas}) ORDER BY seq", lote):
                    por_caso.setdefault(r["caso"], []).append(r)
                for caso, execs in por_caso.items():
                    todas = [self._execucao(c, r) for r in execs]
                    ativas = [e for e in todas if e["estado"] not in ("concluida", "cancelada")]
                    escolhidas.append((ativas or todas)[-1])
        escolhidas.sort(key=lambda e: (-e["prioridade"], e["seq"]))
        if apos is not None:
            escolhidas = [e for e in escolhidas if (-e["prioridade"], e["seq"]) > (-apos[0], apos[1])]
        pagina, resto = escolhidas[:limite], escolhidas[limite:]
        itens = []
        for e in pagina:
            itens.append({"caso": e["caso"], "execucao_id": e["id"], "versao": e["versao"], "estado": e["estado"],
                          "etapa": e["etapa"], "progresso": e["progresso"], "atualizado_em": e["atualizado_em"],
                          "prioridade": e["prioridade"], "pendencias": e["pendencias"], "documentos": e["documentos"]})
        prox = self._codificar([pagina[-1]["prioridade"], pagina[-1]["seq"]]) if resto and pagina else None
        return {"itens": itens, "proximo_cursor": prox}

    # ------------------------------------------------------------ importação do legado
    def importar_legado(self) -> dict:
        """Correlaciona pedidos do plantão e checkpoints de extração já existentes, sem executar nada.

        Não altera `pedidos` nem `processamento.json`; não infere término: cada etapa recebe o estado
        correspondente ao registro de origem. Idempotente por (origem, origem_id)."""
        novas = 0
        with self._c() as c:
            tem = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pedidos'").fetchone()
            pedidos = [dict(r) for r in c.execute("SELECT * FROM pedidos ORDER BY criado_em, id")] if tem else []
        por_caso: dict[str, list] = {}
        for p in pedidos:
            etapa = ACAO_PARA_ETAPA.get(p["acao"])
            if etapa:
                por_caso.setdefault(p["caso"], []).append(
                    (etapa, "plantao", p["id"], None, ESTADO_PEDIDO.get(p["estado"], "aguardando_operador"),
                     p.get("progresso") if p["estado"] == "executando" else None,
                     p.get("erro") or ("estado legado desconhecido: " + str(p["estado"]) if p["estado"] not in ESTADO_PEDIDO else "")))
        raiz = os.path.join(self.ws, "casos")
        if os.path.isdir(raiz):
            for nome in sorted(os.listdir(raiz)):
                arq = os.path.join(raiz, nome, "processamento.json")
                if not os.path.isfile(arq):
                    continue
                try:
                    with open(arq, encoding="utf-8") as f:
                        trabs = json.load(f).get("trabalhos", [])
                except (OSError, ValueError):
                    continue
                for t in trabs:
                    if not isinstance(t, dict) or not t.get("doc"):
                        continue
                    st = t.get("status")
                    por_caso.setdefault(nome, []).append(
                        ("extracao", "processamento", f"{nome}|{t['doc']}|{t.get('enfileirado', '')}", t.get("arquivo") or t["doc"],
                         ESTADO_PROCESSAMENTO.get(st, "aguardando_operador"),
                         t.get("progresso") if st == "processando" and isinstance(t.get("progresso"), (int, float)) else None,
                         t.get("erro") or ("estado legado desconhecido: " + str(st) if st not in ESTADO_PROCESSAMENTO else "")))
        for caso, itens in por_caso.items():
            exe = self.criar(caso, "legado", "legado-importado", tipo="legado")
            for etapa, origem, oid, doc, estado, prog, det in itens:
                with self._c() as c:
                    ja = c.execute("SELECT 1 FROM fluxos_etapas WHERE origem=? AND origem_id=?", (origem, oid)).fetchone()
                if ja:
                    continue
                self.vincular_etapa(exe["id"], etapa, origem, oid, doc, _estado=estado,
                                    _progresso=min(100.0, float(prog)) if prog is not None else None,
                                    _detalhe=("importado do registro legado" + (": " + str(det) if det else "")))
                novas += 1
        return {"etapas_importadas": novas, "casos": len(por_caso)}
