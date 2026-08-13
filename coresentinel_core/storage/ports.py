"""
Persistence ports.

ADR-001 chose file-based JSON for zero dependencies and portability, and that
choice was right for the knowledge a human reads and commits: memory layers, the
decision ledger, the journal. It is the wrong shape for append-heavy machine
records — audit events, verification runs, health snapshots — which is why every
v1 command re-reads every file on every invocation.

This port is how both can be true at once. Business logic never sees a path or a
SQL string; it sees a repository. The backend is a configuration value, and the
same contract suite runs against each one.

Records are plain dicts. Every repository stamps `id` and `recorded_at` on append
and returns the stored record, so a caller never has to guess what was written.
"""

from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# One collection per record kind. Adding a kind means adding a name here and a
# table to a migration — never a new storage class.
COLLECTIONS = ["events", "audit_events", "verification_runs",
               "health_snapshots", "projects", "tasks",
               "knowledge_entities", "knowledge_relations",
               "agent_sessions", "task_results", "permission_grants",
               "incidents", "incident_links", "learning_candidates"]


def now():
    return datetime.now().strftime(TIMESTAMP_FORMAT)


class Repository:
    """Append-oriented collection of records.

    Deliberately narrow: append, read back newest-first, count, and look up by
    id. Anything richer belongs in a service, not in the persistence port, or
    the two backends stop being interchangeable.
    """

    def append(self, record):
        raise NotImplementedError

    def recent(self, limit=50):
        raise NotImplementedError

    def all(self):
        raise NotImplementedError

    def get(self, record_id):
        raise NotImplementedError

    def count(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class Store:
    """A named set of repositories, plus whatever the backend needs to close."""

    backend = "abstract"

    def __init__(self, root):
        self.root = root
        self._repositories = {}

    def repository(self, name):
        if name not in self._repositories:
            raise KeyError(f"unknown collection '{name}'; known: {', '.join(COLLECTIONS)}")
        return self._repositories[name]

    def __getattr__(self, name):
        # store.events reads better than store.repository("events") at the call site.
        repositories = self.__dict__.get("_repositories", {})
        if name in repositories:
            return repositories[name]
        raise AttributeError(name)

    def collections(self):
        return sorted(self._repositories)

    def describe(self):
        return {"backend": self.backend, "root": str(self.root),
                "collections": {name: repo.count() for name, repo in self._repositories.items()}}

    def close(self):
        pass
