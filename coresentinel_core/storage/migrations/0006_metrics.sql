-- CoreSentinel 0006 — metrics about CoreSentinel itself.
--
-- One row per series per process. A CLI command lives for one invocation, so an
-- in-memory registry would only ever show the command you just ran; the runtime
-- flushes its series here on shutdown and `coresentinel metrics` folds them.
--
-- Rows are aggregates, never samples: count, total, min, max and last. A series
-- that saw a million observations is still one row, which is what keeps this
-- table from growing with how much work the tool does.

CREATE TABLE IF NOT EXISTS metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    subject       TEXT,
    name          TEXT,
    kind          TEXT,
    captured_at   TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);

-- The two reads this table serves: everything for one subject, and the recent
-- history of one named series.
CREATE INDEX IF NOT EXISTS idx_metrics_subject ON metrics (subject);
CREATE INDEX IF NOT EXISTS idx_metrics_series ON metrics (subject, name, captured_at);
