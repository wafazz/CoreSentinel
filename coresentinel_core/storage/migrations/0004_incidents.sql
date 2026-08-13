-- CoreSentinel 0004 — incidents, and the chain columns on the audit trail.
--
-- The audit chain lives in the payload like everything else, but prev_hash, hash
-- and seq are promoted so a verification pass is an indexed walk rather than a
-- full decode of every record.

CREATE TABLE IF NOT EXISTS incidents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    incident_id   TEXT    NOT NULL,
    title         TEXT,
    severity      TEXT,
    status        TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents (severity);

CREATE TABLE IF NOT EXISTS incident_links (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    incident_id   TEXT    NOT NULL,
    link_type     TEXT    NOT NULL,
    target        TEXT    NOT NULL,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_links_incident ON incident_links (incident_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON incident_links (target);
