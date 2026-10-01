CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cases (
    id text PRIMARY KEY,
    data jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id bigserial PRIMARY KEY,
    case_id text REFERENCES cases(id) ON DELETE CASCADE,
    path text NOT NULL,
    kind text NOT NULL,
    sha256 text NOT NULL,
    content text,
    page integer,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, path, page)
);

CREATE TABLE IF NOT EXISTS entities (
    id bigserial PRIMARY KEY,
    case_id text REFERENCES cases(id) ON DELETE CASCADE,
    type text NOT NULL,
    value text NOT NULL,
    normalized_value text NOT NULL,
    page integer,
    source text,
    context text
);

CREATE INDEX IF NOT EXISTS documents_case_idx ON documents(case_id);
CREATE INDEX IF NOT EXISTS entities_normalized_idx ON entities(normalized_value);

INSERT INTO schema_migrations(version) VALUES ('001_initial') ON CONFLICT DO NOTHING;
