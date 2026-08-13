"""
JSON-lines backend.

The default, and the one that honours ADR-001: no dependency beyond the standard
library, one file per collection, readable and diffable in a review. Records are
appended a line at a time, so a truncated write costs the last record rather than
the file.

A line that will not parse is skipped and counted, never allowed to abort a read.
A corrupt tail must not make the whole audit trail unreadable — that is the
failure mode that turns a governance record into a liability.
"""

import json
from pathlib import Path

from coresentinel_core.storage.ports import Repository, Store, COLLECTIONS, now
from coresentinel_core.runtime.errors import StorageError

RECORDS_DIRNAME = "records"


class JsonRepository(Repository):
    def __init__(self, path, name):
        self.path = Path(path)
        self.name = name
        self.skipped = 0

    def _next_id(self):
        return f"{self.name}-{self.count() + 1:06d}"

    def append(self, record):
        if not isinstance(record, dict):
            raise StorageError(f"{self.name} records must be dictionaries, got {type(record).__name__}")

        stored = dict(record)
        stored.setdefault("id", self._next_id())
        stored.setdefault("recorded_at", now())

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(stored, default=str) + "\n")
        except OSError as e:
            raise StorageError(f"could not append to {self.path} ({e})",
                               "Check the directory exists and is writable")
        return stored

    def all(self):
        if not self.path.exists():
            return []
        records = []
        self.skipped = 0
        try:
            with open(self.path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except (json.JSONDecodeError, ValueError):
                        self.skipped += 1
        except OSError as e:
            raise StorageError(f"could not read {self.path} ({e})", None)
        return records

    def recent(self, limit=50):
        records = self.all()
        return list(reversed(records))[:limit] if limit else list(reversed(records))

    def get(self, record_id):
        return next((r for r in self.all() if r.get("id") == record_id), None)

    def count(self):
        return len(self.all())

    def clear(self):
        if self.path.exists():
            self.path.unlink()


class JsonStore(Store):
    backend = "json"

    def __init__(self, root):
        super().__init__(root)
        directory = Path(root) / RECORDS_DIRNAME
        self._repositories = {
            name: JsonRepository(directory / f"{name}.jsonl", name) for name in COLLECTIONS
        }

    def describe(self):
        detail = super().describe()
        detail["skipped_lines"] = {name: repo.skipped
                                   for name, repo in self._repositories.items() if repo.skipped}
        return detail
