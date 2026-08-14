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

# Bytes read per step when walking backwards for the tail of a file. Large
# enough that a page of records is usually one read, small enough that reading
# the newest 20 of 10,000 records never loads the other 9,980.
TAIL_CHUNK_BYTES = 8192


class JsonRepository(Repository):
    def __init__(self, path, name):
        self.path = Path(path)
        self.name = name
        self.skipped = 0
        # Number of lines written, or None until something needs to know. Held
        # here because deriving it cost a full parse of the file on every
        # append: appending record N re-read records 1..N-1, so 800 appends took
        # 3.2 seconds and the cost per record grew with the file.
        self._lines = None

    def _line_count(self):
        """Lines in the file, counted as bytes rather than parsed as records."""
        if not self.path.exists():
            return 0
        total = 0
        try:
            with open(self.path, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    total += chunk.count(b"\n")
        except OSError as e:
            raise StorageError(f"could not read {self.path} ({e})", None)
        return total

    def _next_id(self):
        if self._lines is None:
            self._lines = self._line_count()
        return f"{self.name}-{self._lines + 1:06d}"

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
            # The counter advances only on a write that happened. Bumping it
            # first would leave a failed append having consumed an id.
            raise StorageError(f"could not append to {self.path} ({e})",
                               "Check the directory exists and is writable")
        if self._lines is not None:
            self._lines += 1
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

    def _tail_lines(self, wanted):
        """The last `wanted` lines, read by seeking backwards from the end.

        Reading the newest twenty of ten thousand records used to load and
        reverse all ten thousand — 296 ms and 7 MB for twenty records. The
        memory this holds is bounded by the tail, not by the file.
        """
        if not self.path.exists() or wanted <= 0:
            return []
        try:
            with open(self.path, "rb") as f:
                f.seek(0, 2)
                position = f.tell()
                block = b""
                while position > 0 and block.count(b"\n") <= wanted:
                    step = min(TAIL_CHUNK_BYTES, position)
                    position -= step
                    f.seek(position)
                    block = f.read(step) + block
        except OSError as e:
            raise StorageError(f"could not read {self.path} ({e})", None)

        lines = [line for line in block.split(b"\n") if line.strip()]
        return lines[-wanted:]

    def _decode(self, lines):
        decoded = []
        for line in lines:
            try:
                decoded.append(json.loads(line))
            except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
                self.skipped += 1
        return decoded

    def recent(self, limit=50):
        if not limit:
            return list(reversed(self.all()))
        self.skipped = 0
        return list(reversed(self._decode(self._tail_lines(int(limit)))))

    def page(self, limit=50, offset=0):
        """A window of records, newest first. Bounded by `limit`, never by the file."""
        limit, offset = max(0, int(limit)), max(0, int(offset))
        if not limit:
            return []
        # Reading offset+limit from the tail and discarding the offset keeps the
        # common case (page one) a tail read rather than a full parse.
        self.skipped = 0
        window = list(reversed(self._decode(self._tail_lines(offset + limit))))
        return window[offset:offset + limit]

    def get(self, record_id):
        return next((r for r in self.all() if r.get("id") == record_id), None)

    def count(self):
        return len(self.all())

    def clear(self):
        if self.path.exists():
            self.path.unlink()
        self._lines = 0


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
