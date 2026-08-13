-- CoreSentinel 0003 — agent sessions, task results and permission grants.
--
-- `tasks` already exists (0001). These three record what happened when a task
-- was actually run: which agent, under which permissions, what it returned, and
-- every escalation somebody approved.
--
-- permission_grants is the one that matters for accountability. A contract says
-- what an agent may normally do; a grant says who widened that, when, and why.
-- Without the reason column an escalation is indistinguishable from a default.

CREATE TABLE IF NOT EXISTS agent_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    agent         TEXT    NOT NULL,
    objective     TEXT,
    status        TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON agent_sessions (agent);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON agent_sessions (status);

CREATE TABLE IF NOT EXISTS task_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    task_id       TEXT    NOT NULL,
    agent         TEXT,
    status        TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_task ON task_results (task_id);
CREATE INDEX IF NOT EXISTS idx_results_status ON task_results (status);

CREATE TABLE IF NOT EXISTS permission_grants (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     TEXT    NOT NULL UNIQUE,
    agent         TEXT    NOT NULL,
    permission    TEXT    NOT NULL,
    level         TEXT    NOT NULL,
    reason        TEXT,
    recorded_at   TEXT    NOT NULL,
    payload       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grants_agent ON permission_grants (agent);
CREATE INDEX IF NOT EXISTS idx_grants_permission ON permission_grants (permission);
