"""
What CoreSentinel measures about itself.

`agent-stats.py` reads the transcripts of AI hosts: telemetry about somebody
else's process. Nothing measured this one. The verification engine could take
thirty seconds and no number anywhere would say so — which is how a context pack
over a 10,000-fact store came to take ten seconds without anybody noticing.

Two rules, both inherited from the verification engine and for the same reason:

  * **A series exists because something recorded a sample.** There are no
    zero-initialised counters. A subject nobody instrumented reports as never
    observed, and `metrics coverage` names it. A zero would read as "this
    happened nought times", which is a measurement; "never observed" is the
    truth.

  * **A series costs the same whether it holds one sample or a million.** Each
    keeps count, total, min, max and last — never the samples themselves. The
    number of series is capped. Memory here cannot grow with how much work the
    process does, because an observability layer that leaks is worse than none.
"""

import time
from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# The eleven subjects CoreSentinel measures about itself. They are the
# subsystems that do work worth timing; the audit ledger's twelve subjects are a
# different list because auditing asks "what changed?" and this asks "what did
# it cost?".
COMMAND = "command"
SERVICE = "service"
AGENT = "agent"
TASK = "task"
VERIFICATION = "verification"
GATE = "gate"
MEMORY = "memory"
CONTEXT = "context"
RECALL = "recall"
STORAGE = "storage"
AUDIT = "audit"

SUBJECTS = [COMMAND, SERVICE, AGENT, TASK, VERIFICATION, GATE,
            MEMORY, CONTEXT, RECALL, STORAGE, AUDIT]

COUNTER, TIMER, GAUGE = "counter", "timer", "gauge"

# A cap, not a target. Series are keyed by subject and name, and both come from
# code rather than from user input, so this should never be reached — but an
# unbounded dict keyed by anything derived from a path or a query is how an
# in-memory registry becomes a leak.
MAX_SERIES = 512


class Series:
    """One measured quantity. Fixed size regardless of how many samples it sees."""

    __slots__ = (
        "count",
        "kind",
        "last",
        "maximum",
        "minimum",
        "name",
        "subject",
        "total",
        "unit",
    )

    def __init__(self, subject, name, kind, unit=None):
        self.subject = subject
        self.name = name
        self.kind = kind
        self.unit = unit
        self.count = 0
        self.total = 0.0
        self.minimum = None
        self.maximum = None
        self.last = None

    def record(self, value):
        value = float(value)
        self.count += 1
        self.total += value
        self.last = value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    @property
    def mean(self):
        return (self.total / self.count) if self.count else None

    def snapshot(self):
        return {"subject": self.subject, "name": self.name, "kind": self.kind,
                "unit": self.unit, "count": self.count,
                "total": round(self.total, 3),
                "mean": round(self.mean, 3) if self.mean is not None else None,
                "min": round(self.minimum, 3) if self.minimum is not None else None,
                "max": round(self.maximum, 3) if self.maximum is not None else None,
                "last": round(self.last, 3) if self.last is not None else None}


class Timing:
    """Context manager returned by `Metrics.time`. Records on exit, even on error.

    A call that raised still took time, and excluding failures is how a latency
    number comes to describe only the cases that went well.
    """

    __slots__ = ("_metrics", "_name", "_started", "_subject", "elapsed_ms")

    def __init__(self, metrics, subject, name):
        self._metrics = metrics
        self._subject = subject
        self._name = name
        self._started = None
        self.elapsed_ms = None

    def __enter__(self):
        self._started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed_ms = (time.perf_counter() - self._started) * 1000
        self._metrics.observe(self._subject, self._name, self.elapsed_ms,
                              kind=TIMER, unit="ms")
        return False


class Metrics:
    """The registry. One per runtime."""

    def __init__(self, enabled=True, max_series=MAX_SERIES):
        self.enabled = enabled
        self.max_series = max_series
        self.started_at = datetime.now().strftime(TIMESTAMP_FORMAT)
        self._series = {}
        self.dropped_series = 0

    # ------------------------------------------------------------- recording

    def observe(self, subject, name, value, kind=GAUGE, unit=None):
        """Record one sample. Returns the series, or None if metrics are off."""
        if not self.enabled:
            return None
        key = (subject, name)
        series = self._series.get(key)
        if series is None:
            if len(self._series) >= self.max_series:
                # Refuse rather than grow. Losing a series is visible in
                # `dropped_series`; an unbounded registry is not visible at all.
                self.dropped_series += 1
                return None
            series = Series(subject, name, kind, unit)
            self._series[key] = series
        series.record(value)
        return series

    def count(self, subject, name, amount=1):
        return self.observe(subject, name, amount, kind=COUNTER, unit="events")

    def time(self, subject, name):
        return Timing(self, subject, name)

    # ------------------------------------------------------------- reading

    def series(self, subject=None):
        found = [s for s in self._series.values() if subject is None or s.subject == subject]
        return sorted(found, key=lambda s: (s.subject, s.name))

    def observed_subjects(self):
        return sorted({s.subject for s in self._series.values()})

    def coverage(self):
        """Which subjects have been measured, and which never have.

        Modelled on `audit coverage` deliberately: a subject nobody has
        instrumented is reported, not omitted. Absence that is visible is a
        gap; absence that is silent reads as a zero.
        """
        seen = set(self.observed_subjects())
        return {"observed": sorted(s for s in SUBJECTS if s in seen),
                "never_observed": sorted(s for s in SUBJECTS if s not in seen),
                "total": len(SUBJECTS),
                "unknown_subjects": sorted(s for s in seen if s not in SUBJECTS)}

    def snapshot(self):
        return {
            "coresentinel_api": "1.1",
            "started_at": self.started_at,
            "captured_at": datetime.now().strftime(TIMESTAMP_FORMAT),
            "enabled": self.enabled,
            "series": [s.snapshot() for s in self.series()],
            "series_count": len(self._series),
            "max_series": self.max_series,
            "dropped_series": self.dropped_series,
            "coverage": self.coverage(),
        }

    def reset(self):
        self._series.clear()
        self.dropped_series = 0

    # ------------------------------------------------------------- persistence

    def flush(self, store):
        """Persist this process's series so `metrics` can report across runs.

        A CLI process lives for one command, so an in-memory registry would show
        nothing but the command you just ran. One record per series, appended at
        shutdown — bounded by the series cap, not by how much work was done.
        """
        if not self.enabled or not self._series:
            return []
        written = []
        for series in self.series():
            record = dict(series.snapshot())
            record["captured_at"] = datetime.now().strftime(TIMESTAMP_FORMAT)
            written.append(store.metrics.append(record))
        return written


def aggregate(records):
    """Fold persisted series records into one view per (subject, name).

    Counts and totals add. Minima and maxima extend. Means are recomputed from
    the totals rather than averaged, because averaging two means weights a
    thousand samples the same as one.
    """
    folded = {}
    for record in records or []:
        key = (record.get("subject"), record.get("name"))
        current = folded.get(key)
        count = record.get("count") or 0
        total = record.get("total") or 0.0
        if current is None:
            folded[key] = {"subject": key[0], "name": key[1],
                           "kind": record.get("kind"), "unit": record.get("unit"),
                           "count": count, "total": total,
                           "min": record.get("min"), "max": record.get("max"),
                           "last": record.get("last"),
                           "last_seen": record.get("captured_at")}
            continue
        current["count"] += count
        current["total"] += total
        for field, chooser in (("min", min), ("max", max)):
            value = record.get(field)
            if value is not None:
                current[field] = value if current[field] is None else chooser(current[field], value)
        if (record.get("captured_at") or "") >= (current["last_seen"] or ""):
            current["last_seen"] = record.get("captured_at")
            current["last"] = record.get("last")

    for entry in folded.values():
        entry["mean"] = round(entry["total"] / entry["count"], 3) if entry["count"] else None
        entry["total"] = round(entry["total"], 3)
    return sorted(folded.values(), key=lambda e: (e["subject"] or "", e["name"] or ""))
