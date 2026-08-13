-- CoreSentinel 0005 — learning candidates.
--
-- A candidate is machine-derived, high-churn and read by range, so it belongs
-- here. The pattern *library* deliberately does not: it is knowledge a human
-- reads, commits and diffs, which ADR-001 scoped to JSON alongside decisions,
-- incidents and the memory layers.
--
-- An index table for patterns was written and removed. The boundary test from
-- migration 0001 caught it, which is what that test is for — and nothing needs
-- the index yet. Adding one later is its own decision, recorded as one.

CREATE TABLE IF NOT EXISTS learning_candidates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    lesson        TEXT    NOT NULL,
    kind          TEXT,
    status        TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON learning_candidates (status);
CREATE INDEX IF NOT EXISTS idx_candidates_kind ON learning_candidates (kind);
