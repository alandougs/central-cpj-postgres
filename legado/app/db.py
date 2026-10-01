"""Acesso minimo ao PostgreSQL principal da Central CPJ.

O adaptador fica separado do fluxo legado para permitir a migracao gradual.
Documentos fisicos continuam no workspace; dados estruturados sao persistidos
em JSONB e podem ser consultados sem depender de SQLite.
"""
import json
import os

import psycopg
from psycopg.rows import dict_row


class Database:
    def __init__(self, url=None):
        self.url = url or os.environ.get("DATABASE_URL")
        if not self.url:
            raise RuntimeError("DATABASE_URL nao configurada")

    def connect(self):
        return psycopg.connect(self.url, row_factory=dict_row)

    def health(self):
        with self.connect() as conn:
            return conn.execute("SELECT 1 AS ok").fetchone()["ok"] == 1

    def upsert_case(self, case):
        case_id = case.get("id")
        if not case_id:
            raise ValueError("Caso sem id")
        payload = json.dumps(case, ensure_ascii=False)
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO cases (id, data, updated_at)
                   VALUES (%s, %s::jsonb, now())
                   ON CONFLICT (id) DO UPDATE
                   SET data = EXCLUDED.data, updated_at = now()""",
                (case_id, payload),
            )
            conn.commit()

    def get_case(self, case_id):
        with self.connect() as conn:
            row = conn.execute("SELECT data FROM cases WHERE id = %s", (case_id,)).fetchone()
        return row["data"] if row else None

    def upsert_document(self, case_id, path, kind, sha256, content, page=0, metadata=None):
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO documents
                   (case_id, path, kind, sha256, content, page, metadata, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, now())
                   ON CONFLICT (case_id, path, page) DO UPDATE SET
                     kind = EXCLUDED.kind, sha256 = EXCLUDED.sha256,
                     content = EXCLUDED.content, metadata = EXCLUDED.metadata,
                     updated_at = now()""",
                (case_id, path, kind, sha256, content, page,
                 json.dumps(metadata or {}, ensure_ascii=False)),
            )
            conn.commit()
