-- CoreSentinel 0007 — the experience log.
--
-- An experience is what happened: a gate that failed, a verification that
-- returned a verdict, a task that finished. It is machine-derived, arrives on
-- every run and is read by range, which is the test migration 0001 set for what
-- belongs here rather than in JSON. The lessons drawn *from* experiences are a
-- different thing and stay where a human can read and commit them.
--
-- `signature` is the column that makes this table worth having. It is the
-- normalised "what happened", so the same failure twice lands on one signature
-- and recurrence becomes a COUNT rather than a judgement call. Everything else
-- beside `payload` exists to be filtered on.
--
-- `occurrences` is folded in place by retention: a signature seen again updates
-- the existing row rather than adding one. Without that, a flapping gate would
-- fill the table with copies of a single fact.

CREATE TABLE IF NOT EXISTS experiences (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    -- The fold key. Deliberately separate from `record_id`, which is UNIQUE and
    -- belongs to the row: a recurring failure is many rows sharing one group.
    group_id      TEXT,
    kind          TEXT    NOT NULL,
    outcome       TEXT    NOT NULL,
    signature     TEXT    NOT NULL,
    context   TEXT,
    occurrences   INTEGER NOT NULL DEFAULT 1,
    occurred_at   TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experiences_group     ON experiences (group_id);
CREATE INDEX IF NOT EXISTS idx_experiences_signature ON experiences (signature);
CREATE INDEX IF NOT EXISTS idx_experiences_outcome   ON experiences (outcome);
CREATE INDEX IF NOT EXISTS idx_experiences_kind      ON experiences (kind);
CREATE INDEX IF NOT EXISTS idx_experiences_context   ON experiences (context);
CREATE INDEX IF NOT EXISTS idx_experiences_recorded  ON experiences (recorded_at);
