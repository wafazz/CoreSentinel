"""
SQLite backend.

For records that arrive continuously and are read by range: audit events,
verification runs, health snapshots, tasks. Every v1 command re-reads every JSON
file it touches, which is fine for six memory facts and wrong for ten thousand
audit entries.

sqlite3 ships with Python, so this adds no dependency and does not reopen
ADR-001 — it scopes it. Deleting the database file loses no memory, no decision
and no journal entry, because none of those live here.
"""

import json
import sqlite3
from pathlib import Path

from coresentinel_core.storage.ports import Repository, Store, COLLECTIONS, now
from coresentinel_core.storage import migrations
from coresentinel_core.runtime.errors import StorageError

# Columns each collection promotes out of the payload so they can be indexed.
# Anything not listed still round-trips, inside the payload.
PROMOTED = {
    "projects": ["root", "name", "stack"],
    "events": ["event", "occurred_at"],
    "audit_events": ["subject", "actor", "action", "result"],
    "incidents": ["incident_id", "title", "severity", "status"],
    "incident_links": ["incident_id", "link_type", "target"],
    "learning_candidates": ["lesson", "kind", "status"],
    "verification_runs": ["target", "claim", "verdict", "score", "coverage"],
    "health_snapshots": ["target", "status", "overall_score"],
    "tasks": ["objective", "status", "agent"],
    "knowledge_entities": ["entity_type", "entity_key", "label"],
    "knowledge_relations": ["source", "relation_type", "target"],
    "agent_sessions": ["agent", "objective", "status"],
    "task_results": ["task_id", "agent", "status"],
    "permission_grants": ["agent", "permission", "level", "reason"],
    "metrics": ["subject", "name", "kind", "captured_at"],
}

# Collections whose natural key must not produce duplicates on re-append.
UPSERT_KEY = {"projects": "root", "knowledge_entities": "entity_key",
              "knowledge_relations": "record_id", "learning_candidates": "id"}


class SqliteRepository(Repository):
    def __init__(self, connection, name):
        self.connection = connection
        self.name = name
        self.columns = PROMOTED.get(name, [])

    def _next_id(self):
        # MAX over the primary key, not COUNT over the table: COUNT scans every
        # row, and this runs on the write path of an append-only ledger. It also
        # stops reusing an id after a delete, which COUNT+1 did.
        try:
            highest = self.connection.execute(
                f"SELECT COALESCE(MAX(id), 0) FROM {self.name}").fetchone()[0]
        except sqlite3.Error as e:
            raise StorageError(f"could not read the sequence for {self.name} ({e})", None)
        return f"{self.name}-{highest + 1:06d}"

    def append(self, record):
        if not isinstance(record, dict):
            raise StorageError(f"{self.name} records must be dictionaries, got {type(record).__name__}")

        stored = dict(record)
        stored.setdefault("id", self._next_id())
        stored.setdefault("recorded_at", now())

        key = UPSERT_KEY.get(self.name)
        if key and stored.get(key) is not None:
            existing = self.connection.execute(
                f"SELECT record_id FROM {self.name} WHERE {key} = ?", (stored[key],)).fetchone()
            if existing:
                stored["id"] = existing[0]
                self._update(stored)
                return stored

        fields = ["record_id", "recorded_at", "payload"] + self.columns
        values = [stored["id"], stored["recorded_at"], json.dumps(stored, default=str)]
        values += [stored.get(c) for c in self.columns]

        placeholders = ", ".join("?" for _ in fields)
        try:
            self.connection.execute(
                f"INSERT INTO {self.name} ({', '.join(fields)}) VALUES ({placeholders})", values)
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise StorageError(f"could not append to {self.name} ({e})", None)
        return stored

    def _update(self, stored):
        assignments = ["recorded_at = ?", "payload = ?"] + [f"{c} = ?" for c in self.columns]
        values = [stored["recorded_at"], json.dumps(stored, default=str)]
        values += [stored.get(c) for c in self.columns] + [stored["id"]]
        try:
            self.connection.execute(
                f"UPDATE {self.name} SET {', '.join(assignments)} WHERE record_id = ?", values)
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise StorageError(f"could not update {self.name} ({e})", None)

    def _rows(self, sql, params=()):
        try:
            rows = self.connection.execute(sql, params).fetchall()
        except sqlite3.Error as e:
            raise StorageError(f"could not read {self.name} ({e})", None)
        decoded = []
        for row in rows:
            try:
                decoded.append(json.loads(row[0]))
            except (json.JSONDecodeError, ValueError):
                continue
        return decoded

    def all(self):
        return self._rows(f"SELECT payload FROM {self.name} ORDER BY id ASC")

    def recent(self, limit=50):
        if not limit:
            return self._rows(f"SELECT payload FROM {self.name} ORDER BY id DESC")
        return self._rows(f"SELECT payload FROM {self.name} ORDER BY id DESC LIMIT ?", (limit,))

    def page(self, limit=50, offset=0):
        """A window of records, newest first."""
        limit, offset = max(0, int(limit)), max(0, int(offset))
        if not limit:
            return []
        return self._rows(
            f"SELECT payload FROM {self.name} ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset))

    def get(self, record_id):
        found = self._rows(f"SELECT payload FROM {self.name} WHERE record_id = ?", (record_id,))
        return found[0] if found else None

    def count(self):
        try:
            return self.connection.execute(f"SELECT COUNT(*) FROM {self.name}").fetchone()[0]
        except sqlite3.Error as e:
            raise StorageError(f"could not count {self.name} ({e})", None)

    def clear(self):
        try:
            self.connection.execute(f"DELETE FROM {self.name}")
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise StorageError(f"could not clear {self.name} ({e})", None)


class SqliteStore(Store):
    backend = "sqlite"

    def __init__(self, root, filename="coresentinel.db"):
        super().__init__(root)
        self.path = Path(root) / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.connection = sqlite3.connect(str(self.path))
        except sqlite3.Error as e:
            raise StorageError(f"could not open {self.path} ({e})",
                               "Check the directory is writable, or switch to the json backend")
        self.connection.execute("PRAGMA foreign_keys = ON")
        # Write-ahead logging with synchronous=NORMAL. Every append commits, and
        # the default (rollback journal + synchronous=FULL) makes that an fsync
        # per record: 8 ms each, so 800 audit events took 6.4 seconds — slower
        # than the JSON backend it exists to outrun. Under WAL a commit survives
        # a process crash; only an OS-level crash can lose the last commits, and
        # that is the trade a local governance tool should take rather than
        # batching commits and losing the record of what it was doing when it died.
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = NORMAL")
        self.applied = migrations.migrate(self.connection)
        self._repositories = {name: SqliteRepository(self.connection, name)
                              for name in COLLECTIONS}

    def describe(self):
        detail = super().describe()
        detail["path"] = str(self.path)
        detail["schema"] = sorted(migrations.applied(self.connection))
        return detail

    def close(self):
        # sqlite3 permits closing an already-closed connection, so there is
        # nothing to guard against here. A genuine failure propagates to the
        # container, which reports it rather than losing it.
        self.connection.close()
