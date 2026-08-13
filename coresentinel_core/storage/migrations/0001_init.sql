-- CoreSentinel 0001 — initial schema.
--
-- Machine-facing, append-heavy records only. Memory layers, the decision ledger
-- and the journal stay in JSON: they are read by humans, committed to git and
-- diffed in review, which ADR-001 chose deliberately and this migration does
-- not revisit.
--
-- Every table carries `payload` as JSON text. The columns beside it exist to be
-- indexed and filtered on; the payload is the record. That keeps the schema
-- stable while the shape of a verification report or a health snapshot is still
-- moving.

CREATE TABLE IF NOT EXISTS projects (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    root          TEXT    NOT NULL UNIQUE,
    name          TEXT,
    stack         TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    event         TEXT    NOT NULL,
    occurred_at   TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_name ON events (event);
CREATE INDEX IF NOT EXISTS idx_events_recorded ON events (recorded_at);

CREATE TABLE IF NOT EXISTS audit_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    subject       TEXT,
    actor         TEXT,
    action        TEXT,
    result        TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_events (subject);
CREATE INDEX IF NOT EXISTS idx_audit_recorded ON audit_events (recorded_at);

CREATE TABLE IF NOT EXISTS verification_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    target        TEXT,
    claim         TEXT,
    verdict       TEXT,
    score         INTEGER,
    coverage      INTEGER,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verification_verdict ON verification_runs (verdict);
CREATE INDEX IF NOT EXISTS idx_verification_recorded ON verification_runs (recorded_at);

CREATE TABLE IF NOT EXISTS health_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    target        TEXT,
    status        TEXT,
    overall_score INTEGER,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_health_recorded ON health_snapshots (recorded_at);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    objective     TEXT,
    status        TEXT,
    agent         TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
