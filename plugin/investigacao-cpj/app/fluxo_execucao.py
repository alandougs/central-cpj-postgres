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


def _ddl_v2(c) -> None:
    """UN14: reservas duráveis por etapa e intenção de despacho externo (chave única por operação)."""
    c.execute("""CREATE TABLE IF NOT EXISTS fluxos_reservas(
        etapa_id TEXT PRIMARY KEY REFERENCES fluxos_etapas(id), dono TEXT NOT NULL,
        ate TEXT NOT NULL, criado_em TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS fluxos_intencoes(
        chave TEXT PRIMARY KEY, etapa_id TEXT NOT NULL REFERENCES fluxos_etapas(id), dono TEXT NOT NULL,
        registrada_em TEXT NOT NULL, resultado TEXT, resultado_em TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_fluxos_intencoes_etapa ON fluxos_intencoes(etapa_id)")


MIGRACOES = ((1, _ddl_v1), (2, _ddl_v2))   # (versão, função DDL aditiva); novas versões só acrescentam ao final


class ConflitoVersao(Exception):
    """A versão informada está obsoleta; nada foi alterado."""


class TransicaoInvalida(Exception):
    """Transição de estado proibida pelo contrato."""


class ReservaPerdida(Exception):
    """O chamador não detém (mais) uma reserva válida da etapa; o resultado não deve ser gravado."""


class ResultadoIncerto(Exception):
    """Há uma chamada externa registrada sem resultado: nunca repetir sem reconciliação explícita."""


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
        with self._tx() as c:
            r = self._criar_c(c, caso, solicitante, chave, prioridade, tipo)
        return {k: r[k] for k in ("id", "caso", "solicitante", "chave", "prioridade", "tipo", "versao")}

    @staticmethod
    def _criar_c(c, caso, solicitante, chave, prioridade=0, tipo="fluxo"):
        for nome, v in (("caso", caso), ("solicitante", solicitante), ("chave", chave)):
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"{nome} obrigatório.")
        if type(prioridade) is not int:
            raise ValueError("prioridade deve ser inteiro.")
        r = c.execute("SELECT * FROM fluxos_execucoes WHERE caso=? AND solicitante=? AND chave=?",
                      (caso, solicitante, chave)).fetchone()
        if r is None:
            t = agora()
            c.execute("INSERT INTO fluxos_execucoes(id,caso,solicitante,chave,prioridade,tipo,versao,criado_em,atualizado_em) "
                      "VALUES(?,?,?,?,?,?,1,?,?)", (str(uuid.uuid4()), caso, solicitante, chave, prioridade, tipo, t, t))
            r = c.execute("SELECT * FROM fluxos_execucoes WHERE caso=? AND solicitante=? AND chave=?",
                          (caso, solicitante, chave)).fetchone()
        return r

    def vincular_etapa(self, execucao_id: str, etapa: str, origem: str, origem_id: str, documento: str | None = None,
                       _estado: str = "na_fila", _progresso: float | None = None, _detalhe: str = "") -> dict:
        with self._tx() as c:
            r = self._vincular_c(c, execucao_id, etapa, origem, origem_id, documento, _estado, _progresso, _detalhe)
        return self._resumo_etapa(r)

    def _vincular_c(self, c, execucao_id, etapa, origem, origem_id, documento=None, estado="na_fila", progresso=None,
                    detalhe="", tentativa=1, anterior_id=None):
        if etapa not in ETAPAS:
            raise ValueError(f"Etapa inválida: {etapa}")
        if origem not in ORIGENS:
            raise ValueError(f"Origem inválida: {origem}")
        if not isinstance(origem_id, str) or not origem_id.strip():
            raise ValueError("origem_id obrigatório.")
        if c.execute("SELECT 1 FROM fluxos_execucoes WHERE id=?", (execucao_id,)).fetchone() is None:
            raise KeyError(f"Execução inexistente: {execucao_id}")
        r = c.execute("SELECT * FROM fluxos_etapas WHERE origem=? AND origem_id=?", (origem, origem_id)).fetchone()
        if r is not None:
            if (r["execucao_id"], r["etapa"]) != (execucao_id, etapa):
                raise ValueError("Esta origem já está vinculada a outra execução ou etapa.")
            return r
        t, eid = agora(), str(uuid.uuid4())
        c.execute("INSERT INTO fluxos_etapas(id,execucao_id,etapa,origem,origem_id,documento,estado,versao,progresso,detalhe,"
                  "tentativa,anterior_id,criado_em,atualizado_em) VALUES(?,?,?,?,?,?,?,1,?,?,?,?,?,?)",
                  (eid, execucao_id, etapa, origem, origem_id, documento, estado, progresso, detalhe, tentativa, anterior_id, t, t))
        self._tocar(c, execucao_id, t)
        return c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (eid,)).fetchone()

    @staticmethod
    def _tocar(c, execucao_id: str, t: str) -> None:
        c.execute("UPDATE fluxos_execucoes SET versao=versao+1, atualizado_em=? WHERE id=?", (t, execucao_id))

    @staticmethod
    def _resumo_etapa(r) -> dict:
        return {k: r[k] for k in ("id", "execucao_id", "etapa", "origem", "origem_id", "documento", "estado", "versao",
                                  "progresso", "detalhe", "tentativa", "anterior_id", "criado_em", "atualizado_em")}

    def _mudar(self, etapa_id: str, versao: int, estado: str, progresso, detalhe: str, *, reconciliando: bool,
               dono: str | None = None) -> dict:
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
            if dono is not None:
                self._exigir_reserva(c, etapa_id, dono)
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
            if estado != "em_execucao":
                c.execute("DELETE FROM fluxos_reservas WHERE etapa_id=?", (etapa_id,))
            if reconciliando and estado in RECONCILIA_PARA:
                c.execute("DELETE FROM fluxos_intencoes WHERE etapa_id=? AND resultado IS NULL", (etapa_id,))
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

    # ------------------------------------------------------------ UN14: reservas, intenção, cancelamento
    @staticmethod
    def _exigir_reserva(c, etapa_id: str, dono: str) -> None:
        r = c.execute("SELECT dono, ate FROM fluxos_reservas WHERE etapa_id=?", (etapa_id,)).fetchone()
        if r is None or r["dono"] != dono or r["ate"] <= agora():
            raise ReservaPerdida(f"reserva da etapa {etapa_id} não pertence a {dono} ou expirou")

    def _elegivel(self, c, e) -> bool:
        """Etapa só é elegível quando todas as etapas anteriores (vigentes) da execução estão concluídas."""
        exe = c.execute("SELECT tipo FROM fluxos_execucoes WHERE id=?", (e["execucao_id"],)).fetchone()
        if exe["tipo"] == "legado":
            return True
        todas = [self._resumo_etapa(x) for x in c.execute("SELECT * FROM fluxos_etapas WHERE execucao_id=?", (e["execucao_id"],))]
        idx = ETAPAS.index(e["etapa"])
        return all(v["estado"] == "concluida" for v in self._vigentes(todas) if ETAPAS.index(v["etapa"]) < idx)

    @staticmethod
    def _expiracao(validade_s: float) -> str:
        if not isinstance(validade_s, (int, float)) or isinstance(validade_s, bool) or validade_s <= 0:
            raise ValueError("validade_s deve ser positiva.")
        return (datetime.datetime.now() + datetime.timedelta(seconds=validade_s)).isoformat(timespec="microseconds")

    def reservar(self, etapa_id: str, dono: str, validade_s: float = 300) -> dict | None:
        """Reserva atômica: só um proprietário vence. Move na_fila -> em_execucao. None = não obtida."""
        if not isinstance(dono, str) or not dono.strip():
            raise ValueError("dono obrigatório.")
        ate = self._expiracao(validade_s)
        with self._tx() as c:
            e = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (etapa_id,)).fetchone()
            if e is None:
                raise KeyError(f"Etapa inexistente: {etapa_id}")
            if e["estado"] != "na_fila" or c.execute("SELECT 1 FROM fluxos_reservas WHERE etapa_id=?", (etapa_id,)).fetchone():
                return None
            if not self._elegivel(c, e):
                return None
            t = agora()
            c.execute("INSERT INTO fluxos_reservas(etapa_id,dono,ate,criado_em) VALUES(?,?,?,?)", (etapa_id, dono, ate, t))
            c.execute("UPDATE fluxos_etapas SET estado='em_execucao', versao=versao+1, atualizado_em=? WHERE id=?", (t, etapa_id))
            self._tocar(c, e["execucao_id"], t)
            r = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (etapa_id,)).fetchone()
        return self._resumo_etapa(r)

    def renovar(self, etapa_id: str, dono: str, validade_s: float = 300) -> None:
        ate = self._expiracao(validade_s)
        with self._tx() as c:
            self._exigir_reserva(c, etapa_id, dono)
            c.execute("UPDATE fluxos_reservas SET ate=? WHERE etapa_id=?", (ate, etapa_id))

    def reserva_valida(self, etapa_id: str, dono: str) -> bool:
        with self._c() as c:
            try:
                self._exigir_reserva(c, etapa_id, dono)
                return True
            except ReservaPerdida:
                return False

    def atualizar_reservado(self, etapa_id: str, dono: str, versao: int, estado: str,
                            progresso: float | None = None, detalhe: str = "") -> dict:
        """Como atualizar(), mas valida dono/validade da reserva na mesma transação do resultado."""
        return self._mudar(etapa_id, versao, estado, progresso, detalhe, reconciliando=False, dono=dono)

    def deve_cancelar(self, etapa_id: str) -> bool:
        with self._c() as c:
            r = c.execute("SELECT estado FROM fluxos_etapas WHERE id=?", (etapa_id,)).fetchone()
        return r is None or r["estado"] == "cancelada"

    def registrar_intencao(self, etapa_id: str, dono: str, chave: str) -> dict:
        """Grava a intenção ANTES da chamada externa. Mesma chave: devolve o resultado já conhecido ou
        levanta ResultadoIncerto (chamada feita sem resultado registrado)."""
        if not isinstance(chave, str) or not chave.strip():
            raise ValueError("chave obrigatória.")
        with self._tx() as c:
            self._exigir_reserva(c, etapa_id, dono)
            r = c.execute("SELECT * FROM fluxos_intencoes WHERE chave=?", (chave,)).fetchone()
            if r is None:
                c.execute("INSERT INTO fluxos_intencoes(chave,etapa_id,dono,registrada_em) VALUES(?,?,?,?)",
                          (chave, etapa_id, dono, agora()))
                return {"nova": True, "resultado": None}
            if r["resultado"] is None:
                raise ResultadoIncerto(f"chamada externa '{chave}' já iniciada sem resultado registrado")
            return {"nova": False, "resultado": json.loads(r["resultado"])}

    def registrar_resultado(self, etapa_id: str, dono: str, chave: str, resultado) -> None:
        with self._tx() as c:
            self._exigir_reserva(c, etapa_id, dono)
            n = c.execute("UPDATE fluxos_intencoes SET resultado=?, resultado_em=? WHERE chave=? AND etapa_id=? AND resultado IS NULL",
                          (json.dumps(resultado, ensure_ascii=False, default=str), agora(), chave, etapa_id)).rowcount
            if not n:
                raise ValueError("intenção inexistente ou resultado já registrado.")

    def cancelar_execucao(self, execucao_id: str, versao: int | None = None, motivo: str = "") -> dict:
        """Cancela etapas ainda não terminadas (inclusive a em execução) e preserva as já concluídas."""
        with self._tx() as c:
            ex = c.execute("SELECT * FROM fluxos_execucoes WHERE id=?", (execucao_id,)).fetchone()
            if ex is None:
                raise KeyError(f"Execução inexistente: {execucao_id}")
            if versao is not None and ex["versao"] != versao:
                raise ConflitoVersao(f"versão {versao} obsoleta; atual {ex['versao']}")
            t, canceladas, preservadas, lista = agora(), 0, 0, []
            for e in c.execute("SELECT * FROM fluxos_etapas WHERE execucao_id=?", (execucao_id,)).fetchall():
                if e["estado"] in TERMINAIS:
                    preservadas += 1
                    continue
                c.execute("UPDATE fluxos_etapas SET estado='cancelada', detalhe=?, versao=versao+1, atualizado_em=? WHERE id=?",
                          ("cancelada: " + (motivo or "solicitação do operador"), t, e["id"]))
                c.execute("DELETE FROM fluxos_reservas WHERE etapa_id=?", (e["id"],))
                if e["origem"] == "plantao":      # o pedido é a autoridade da execução: o cancelamento é pedido a ele
                    c.execute("UPDATE pedidos SET cancelar=1, estado=CASE WHEN estado='pendente' THEN 'cancelada' ELSE estado END, "
                              "etapa='cancelamento solicitado', fim=CASE WHEN estado='pendente' THEN ? ELSE fim END "
                              "WHERE id=? AND estado IN ('pendente','executando')", (t, e["origem_id"].split("#t")[0]))
                canceladas += 1
                lista.append({"id": e["id"], "origem": e["origem"], "origem_id": e["origem_id"], "documento": e["documento"],
                              "estado_anterior": e["estado"]})
            self._tocar(c, execucao_id, t)
        return {"execucao_id": execucao_id, "canceladas": canceladas, "preservadas": preservadas, "etapas_canceladas": lista}

    def proximas(self, limite: int = 10) -> list[dict]:
        """Etapas na fila elegíveis e sem reserva, por prioridade (maior primeiro), entrada e ID."""
        if type(limite) is not int or limite < 1:
            raise ValueError("limite inválido.")
        out = []
        with self._c() as c:
            q = ("SELECT e.* FROM fluxos_etapas e JOIN fluxos_execucoes x ON x.id=e.execucao_id "
                 "WHERE e.estado='na_fila' AND NOT EXISTS (SELECT 1 FROM fluxos_reservas r WHERE r.etapa_id=e.id) "
                 "ORDER BY x.prioridade DESC, x.seq ASC, e.seq ASC")
            for e in c.execute(q):
                if self._elegivel(c, e):
                    out.append(self._resumo_etapa(e))
                    if len(out) >= limite:
                        break
        return out

    # ------------------------------------------------------------ UN14: tentativas, plantão e extração
    def _set_c(self, c, e, estado: str, detalhe: str, progresso=None) -> None:
        """Escrita interna do espelhamento: a autoridade do estado é o executor (pedido/extração), não o chamador."""
        t = agora()
        c.execute("UPDATE fluxos_etapas SET estado=?, detalhe=?, progresso=COALESCE(?,progresso), versao=versao+1, atualizado_em=? WHERE id=?",
                  (estado, detalhe or "", progresso, t, e["id"]))
        if estado != "em_execucao":
            c.execute("DELETE FROM fluxos_reservas WHERE etapa_id=?", (e["id"],))
        self._tocar(c, e["execucao_id"], t)

    @staticmethod
    def _incerta_c(c, etapa_id: str) -> bool:
        return c.execute("SELECT 1 FROM fluxos_intencoes WHERE etapa_id=? AND resultado IS NULL", (etapa_id,)).fetchone() is not None

    def _interromper_c(self, c, e, motivo: str = "interrompida por queda/reinício; retomada em nova tentativa"):
        """Tentativa sem executor vivo. Chamada externa sem resultado -> operador; senão nova tentativa na fila."""
        if self._incerta_c(c, e["id"]):
            self._set_c(c, e, "aguardando_operador",
                        "resultado externo incerto: chamada iniciada sem resultado registrado; conferir antes de repetir")
            return c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (e["id"],)).fetchone()
        self._set_c(c, e, "falhou", motivo)
        base = e["origem_id"].split("#t")[0]
        return self._vincular_c(c, e["execucao_id"], e["etapa"], e["origem"], f"{base}#t{e['tentativa'] + 1}", e["documento"],
                                "na_fila", None, "", e["tentativa"] + 1, e["id"])

    @staticmethod
    def _etapa_pedido_c(c, pid: str):
        return c.execute("SELECT * FROM fluxos_etapas WHERE origem='plantao' AND (origem_id=? OR origem_id LIKE ?) "
                         "ORDER BY tentativa DESC, seq DESC LIMIT 1", (pid, pid + "#t%")).fetchone()

    def etapa_do_pedido(self, pid: str) -> dict | None:
        with self._c() as c:
            r = self._etapa_pedido_c(c, pid)
        return self._resumo_etapa(r) if r else None

    def pedido_com_resultado_incerto(self, pid: str) -> bool:
        with self._c() as c:
            return c.execute("SELECT 1 FROM fluxos_intencoes i JOIN fluxos_etapas e ON e.id=i.etapa_id WHERE e.origem='plantao' "
                             "AND (e.origem_id=? OR e.origem_id LIKE ?) AND i.resultado IS NULL", (pid, pid + "#t%")).fetchone() is not None

    def espelhar_pedido(self, pid: str, validade_s: float = 3600) -> dict | None:
        """Alinha a etapa do pedido de plantão ao estado do pedido (idempotente; lê `pedidos`, nunca o altera)."""
        ate = self._expiracao(validade_s)
        with self._tx() as c:
            return self._espelhar_c(c, pid, ate)

    def _espelhar_c(self, c, pid: str, ate: str) -> dict | None:
        p = c.execute("SELECT * FROM pedidos WHERE id=?", (pid,)).fetchone()
        etapa = ACAO_PARA_ETAPA.get(p["acao"]) if p else None
        if etapa is None:
            return None
        e = self._etapa_pedido_c(c, pid)
        if e is None:
            exe = self._criar_c(c, p["caso"], p["solicitante"] or "legado", p["grupo"] or pid)
            e = self._vincular_c(c, exe["id"], etapa, "plantao", pid)
        ps, ee = p["estado"], e["estado"]
        if ee == "aguardando_operador" or ee in TERMINAIS:
            return self._resumo_etapa(e)
        if ps == "pendente" and ee == "em_execucao":
            e = self._interromper_c(c, e)
        elif ps == "executando":
            ag = p["agente"] or "?"
            if ee == "em_execucao":
                r = c.execute("SELECT dono FROM fluxos_reservas WHERE etapa_id=?", (e["id"],)).fetchone()
                if r is not None and r["dono"] != ag:       # outro agente assumiu: a tentativa anterior morreu
                    e = self._interromper_c(c, e)
            if e["estado"] == "na_fila":
                self._set_c(c, e, "em_execucao", p["etapa"] or "")
            if e["estado"] != "aguardando_operador":
                c.execute("INSERT INTO fluxos_reservas(etapa_id,dono,ate,criado_em) VALUES(?,?,?,?) "
                          "ON CONFLICT(etapa_id) DO UPDATE SET ate=excluded.ate", (e["id"], ag, ate, agora()))
                c.execute("UPDATE fluxos_etapas SET progresso=?, detalhe=? WHERE id=?",
                          (p["progresso"], p["etapa"] or "", e["id"]))
            e = c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (e["id"],)).fetchone()
        elif ps == "concluida":
            self._set_c(c, e, "concluida", "", 100)
        elif ps == "erro":
            if ee == "em_execucao" and self._incerta_c(c, e["id"]):
                self._set_c(c, e, "aguardando_operador", "resultado externo incerto: " + (p["erro"] or ""))
            elif ee == "em_execucao":
                self._set_c(c, e, "falhou", p["erro"] or "")
            else:
                self._set_c(c, e, "cancelada", "pedido encerrado com erro antes de iniciar: " + (p["erro"] or ""))
        elif ps == "cancelada":
            self._set_c(c, e, "cancelada", p["etapa"] or "cancelada")
        return self._resumo_etapa(c.execute("SELECT * FROM fluxos_etapas WHERE id=?", (e["id"],)).fetchone())

    def registrar_extracao(self, caso: str, usuario: str, doc: str, arquivo: str, enfileirado: str) -> dict:
        """Vincula o trabalho de extração (processamento.json) ao fluxo da O.S. Uma tentativa por enfileiramento;
        retomada após queda reaproveita a tentativa que já está na fila."""
        with self._tx() as c:
            r = c.execute("SELECT e.* FROM fluxos_etapas e JOIN fluxos_execucoes x ON x.id=e.execucao_id WHERE x.caso=? "
                          "AND e.etapa='extracao' AND e.documento=? ORDER BY e.tentativa DESC, e.seq DESC LIMIT 1",
                          (caso, arquivo)).fetchone()
            if r is not None and r["estado"] == "em_execucao" and c.execute(
                    "SELECT 1 FROM fluxos_reservas WHERE etapa_id=? AND ate>?", (r["id"], agora())).fetchone() is None:
                r = self._interromper_c(c, r)                      # executor anterior morreu
            if r is not None and r["estado"] in ("na_fila", "em_execucao", "aguardando_operador"):
                return self._resumo_etapa(r)
            oid = f"{caso}|{doc}|{enfileirado}"
            if r is None:
                exe = self._criar_c(c, caso, usuario or "local", "extracao")
                n = self._vincular_c(c, exe["id"], "extracao", "processamento", oid, arquivo)
            else:
                n = self._vincular_c(c, r["execucao_id"], "extracao", "processamento", oid, arquivo, "na_fila", None, "",
                                     r["tentativa"] + 1, r["id"])
        return self._resumo_etapa(n)

    def reconciliar_inicializacao(self) -> dict:
        """Na inicialização: etapas em execução sem reserva válida. Chamada externa sem resultado -> operador;
        caso contrário a tentativa é encerrada como interrompida e outra é criada. Etapas de plantão seguem o
        estado do pedido (o Plantão decide o abandono pelo silêncio do agente). Não executa nada."""
        incertas = retomadas = alinhadas = 0
        ate = self._expiracao(3600)
        with self._tx() as c:
            t = agora()
            for e in c.execute("SELECT * FROM fluxos_etapas WHERE estado IN ('na_fila','em_execucao') AND origem='plantao'").fetchall():
                novo = self._espelhar_c(c, e["origem_id"].split("#t")[0], ate)
                if novo is not None and novo["estado"] != e["estado"]:
                    alinhadas += 1
            orfas = c.execute("SELECT e.* FROM fluxos_etapas e LEFT JOIN fluxos_reservas r ON r.etapa_id=e.id "
                              "WHERE e.estado='em_execucao' AND e.origem!='plantao' AND (r.etapa_id IS NULL OR r.ate <= ?)", (t,)).fetchall()
            for e in orfas:
                c.execute("DELETE FROM fluxos_reservas WHERE etapa_id=?", (e["id"],))
                if self._interromper_c(c, e)["estado"] == "aguardando_operador":
                    incertas += 1
                else:
                    retomadas += 1
        return {"incertas": incertas, "retomadas": retomadas, "alinhadas": alinhadas}

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
                             "detalhe": e["detalhe"], "etapa_id": e["id"], "etapa_versao": e["versao"]})
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

    def listar(self, casos_permitidos: list[str], limite: int = 50, cursor: str | None = None,
               estados: list[str] | None = None) -> dict:
        """Um item por O.S. autorizada: a execução ativa mais recente (ou, sem ativa, a mais recente). Pendências,
        documentos e estado consideram todas as execuções ativas da O.S., para que nada fique escondido por outra mais nova."""
        if type(limite) is not int or not 1 <= limite <= LIMITE_MAX:
            raise ValueError(f"limite deve estar entre 1 e {LIMITE_MAX}.")
        if estados is not None and (not isinstance(estados, (list, tuple, set)) or not set(estados) <= set(ESTADOS)):
            raise ValueError("estado inválido.")
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
                    principal = dict((ativas or todas)[-1])
                    grupo = ativas or [principal]
                    if ativas:
                        principal["estado"] = next((s for s in PRECEDENCIA if any(e["estado"] == s for e in ativas)), principal["estado"])
                    principal["pendencias"] = [dict(p, execucao_id=e["id"]) for e in grupo for p in e["pendencias"]]
                    principal["documentos"] = sorted({d for e in grupo for d in e["documentos"]})
                    principal["execucoes"] = [{"execucao_id": e["id"], "versao": e["versao"], "estado": e["estado"],
                                               "solicitante": e["solicitante"]} for e in ativas]
                    escolhidas.append(principal)
        if estados is not None:
            escolhidas = [e for e in escolhidas if e["estado"] in set(estados)]
        escolhidas.sort(key=lambda e: (-e["prioridade"], e["seq"]))
        if apos is not None:
            escolhidas = [e for e in escolhidas if (-e["prioridade"], e["seq"]) > (-apos[0], apos[1])]
        pagina, resto = escolhidas[:limite], escolhidas[limite:]
        itens = []
        for e in pagina:
            itens.append({"caso": e["caso"], "execucao_id": e["id"], "versao": e["versao"], "estado": e["estado"],
                          "etapa": e["etapa"], "progresso": e["progresso"], "atualizado_em": e["atualizado_em"],
                          "prioridade": e["prioridade"], "pendencias": e["pendencias"], "documentos": e["documentos"],
                          "execucoes": e["execucoes"]})
        prox = self._codificar([pagina[-1]["prioridade"], pagina[-1]["seq"]]) if resto and pagina else None
        return {"itens": itens, "proximo_cursor": prox}

    def etapas_paginadas(self, execucao_id: str, limite: int = 50, cursor: str | None = None) -> dict | None:
        """Histórico completo de etapas/tentativas da execução, em ordem de criação, com cursor opaco."""
        if type(limite) is not int or not 1 <= limite <= LIMITE_MAX:
            raise ValueError(f"limite deve estar entre 1 e {LIMITE_MAX}.")
        apos = 0
        if cursor:
            try:
                v = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
                if type(v) is not int or v < 0:
                    raise ValueError
                apos = v
            except Exception:
                raise ValueError("Cursor inválido.") from None
        with self._c() as c:
            exe = c.execute("SELECT * FROM fluxos_execucoes WHERE id=?", (execucao_id,)).fetchone()
            if exe is None:
                return None
            linhas = c.execute("SELECT * FROM fluxos_etapas WHERE execucao_id=? AND seq>? ORDER BY seq LIMIT ?",
                               (execucao_id, apos, limite + 1)).fetchall()
            resumo = self._execucao(c, exe)
        pagina = linhas[:limite]
        etapas = [dict(self._resumo_etapa(r), seq=r["seq"]) for r in pagina]
        prox = self._codificar(pagina[-1]["seq"]) if len(linhas) > limite and pagina else None
        return {"execucao": {k: resumo[k] for k in ("id", "caso", "solicitante", "versao", "estado", "etapa", "progresso",
                                                    "atualizado_em", "pendencias", "documentos")},
                "etapas": etapas, "proximo_cursor": prox}

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
