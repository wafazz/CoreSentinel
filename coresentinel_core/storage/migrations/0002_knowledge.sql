-- CoreSentinel 0002 — knowledge entities and relations.
--
-- The graph is derived data: it is rebuilt from discovery, the decision ledger
-- and the memory layers in tens of milliseconds. These tables hold a *snapshot*
-- for consumers that cannot rebuild it themselves — the API and the dashboard —
-- never as the source of truth. `knowledge query` always rebuilds, because a
-- stale graph would still show a decision that was superseded yesterday.

CREATE TABLE IF NOT EXISTS knowledge_entities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    entity_type   TEXT    NOT NULL,
    entity_key    TEXT    NOT NULL,
    label         TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_type ON knowledge_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_key ON knowledge_entities (entity_key);

CREATE TABLE IF NOT EXISTS knowledge_relations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    source        TEXT    NOT NULL,
    relation_type TEXT    NOT NULL,
    target        TEXT    NOT NULL,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_relations_source ON knowledge_relations (source);
CREATE INDEX IF NOT EXISTS idx_relations_target ON knowledge_relations (target);
CREATE INDEX IF NOT EXISTS idx_relations_type ON knowledge_relations (relation_type);
