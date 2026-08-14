"""The task store.

Deliberately in-memory. That is a recorded decision, not an oversight — see
ADR-0001 in this project's ledger, which the demo reproduces and then tries to
contradict so you can watch CoreSentinel refuse it.
"""

from datetime import datetime

OPEN, DONE, BLOCKED = "open", "done", "blocked"
STATUSES = (OPEN, DONE, BLOCKED)

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class UnknownTask(KeyError):
    """Raised for an id the store does not hold. Never returns None instead."""


class Task:
    __slots__ = ("id", "title", "status", "owner", "created_at")

    def __init__(self, task_id, title, owner=None, status=OPEN, created_at=None):
        if status not in STATUSES:
            raise ValueError(f"unknown status '{status}'; expected one of {', '.join(STATUSES)}")
        self.id = task_id
        self.title = title
        self.owner = owner
        self.status = status
        self.created_at = created_at or datetime.now().strftime(TIMESTAMP_FORMAT)

    def as_dict(self):
        return {"id": self.id, "title": self.title, "owner": self.owner,
                "status": self.status, "created_at": self.created_at}

    def __repr__(self):
        return f"Task({self.id}, {self.status})"


class TaskStore:
    """Tasks by id, newest first on read."""

    def __init__(self):
        self._tasks = {}
        self._sequence = 0

    def add(self, title, owner=None):
        if not str(title or "").strip():
            raise ValueError("a task needs a title")
        self._sequence += 1
        task_id = f"TASK-{self._sequence:04d}"
        self._tasks[task_id] = Task(task_id, title.strip(), owner)
        return self._tasks[task_id]

    def get(self, task_id):
        if task_id not in self._tasks:
            raise UnknownTask(task_id)
        return self._tasks[task_id]

    def complete(self, task_id):
        task = self.get(task_id)
        task.status = DONE
        return task

    def block(self, task_id, reason):
        if not str(reason or "").strip():
            # A blocked task with no reason is a task nobody can unblock.
            raise ValueError("blocking a task requires a reason")
        task = self.get(task_id)
        task.status = BLOCKED
        return task

    def list(self, status=None, limit=50, offset=0):
        """A bounded page, newest first."""
        if status is not None and status not in STATUSES:
            raise ValueError(f"unknown status '{status}'")
        found = [t for t in reversed(list(self._tasks.values()))
                 if status is None or t.status == status]
        return found[offset:offset + max(0, limit)]

    def counts(self):
        tally = {status: 0 for status in STATUSES}
        for task in self._tasks.values():
            tally[task.status] += 1
        return tally

    def __len__(self):
        return len(self._tasks)
