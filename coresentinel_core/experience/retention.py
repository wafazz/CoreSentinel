"""
Keeping the experience log bounded.

Capture appends and never rewrites. That is the right shape for the write path —
both backends are built for it, and folding on every append would make observing
a gate run cost a full read of the log.

The consequence is that repetition arrives as repetition: a gate that fails
fifty times is fifty rows. So recurrence is computed by grouping
(`group`, cheap, read-only) and reclaimed by folding (`fold`, which rewrites).

Two things follow, both deliberate:

  * **`occurrences` is derived, not incremented.** A stored counter and the rows
    it counts drift apart the first time a write half-fails. Counting the rows
    cannot disagree with the rows.
  * **Folding is a dry run until `--apply`**, exactly as `memory decay`,
    `promote`, `consolidate` and `compact` already are. A retention pass that
    silently discarded evidence would be a strange thing to have to discover.

`enforce` is the amortised guard on the write path: it does nothing until the
log is over its cap, and only then pays for a fold.
"""

from coresentinel_core.experience import records

COLLECTION = "experiences"

# Rows the log may hold before `enforce` folds and trims. Two thousand
# experiences is far more than any lesson needs — the value exists to bound the
# store, not to be reached.
DEFAULT_MAX = 2000

# Kept when trimming past the cap, in this order. A failure teaches more than a
# success, and the newest evidence is the evidence still true.
KEEP_PRIORITY = {records.FAILURE: 0, records.MIXED: 1, records.SUCCESS: 2}


def _repository(store):
    return store.repository(COLLECTION)


def load(store):
    return _repository(store).all()


def group(store=None, rows=None):
    """Distinct experiences, newest-last, with a real occurrence count.

    The read-only view. Nothing here writes, so it is safe to call on the hot
    path and from a report.
    """
    grouped = {}
    for row in (rows if rows is not None else load(store)):
        key = row.get("group_id")
        if not key:
            continue
        existing = grouped.get(key)
        if existing is None:
            folded = dict(row)
            folded["occurrences"] = int(row.get("occurrences") or 1)
            grouped[key] = folded
            continue
        existing["occurrences"] += int(row.get("occurrences") or 1)
        # The record keeps the newest wording and the earliest sighting, so a
        # report can say both what it looks like now and how long it has been true.
        existing["first_seen"] = min(
            existing.get("first_seen") or existing.get("occurred_at") or "",
            row.get("occurred_at") or "") or None
        if (row.get("occurred_at") or "") >= (existing.get("occurred_at") or ""):
            existing["statement"] = row.get("statement", existing.get("statement"))
            existing["occurred_at"] = row.get("occurred_at", existing.get("occurred_at"))
            existing["evidence"] = row.get("evidence", existing.get("evidence"))
    return list(grouped.values())


def outcomes_for(signature, store=None, rows=None):
    """Success and failure counts for one signature, split by context key.

    This is what Phase 2 analysis and the confidence `success` term read. Split
    by context because the same signature succeeding in one environment and
    failing in another is not an inconsistency — it is a scope that was drawn
    too wide.
    """
    tally = {}
    for row in (rows if rows is not None else load(store)):
        if row.get("signature") != signature:
            continue
        bucket = tally.setdefault(row.get("context") or "global",
                                  {"success": 0, "failure": 0, "mixed": 0})
        count = int(row.get("occurrences") or 1)
        if row.get("outcome") == records.SUCCESS:
            bucket["success"] += count
        elif row.get("outcome") == records.FAILURE:
            bucket["failure"] += count
        else:
            bucket["mixed"] += count
    return tally


def _trim(folded, maximum):
    """Drop the least instructive records once the log is over its cap.

    Ranked by outcome first (a failure teaches more than a success), then by how
    often it recurred, then by recency. Two sorts rather than one composite key:
    recency runs descending and the others ascending, and Python's sort is
    stable, so the second pass keeps the first's order inside each tier.
    """
    if len(folded) <= maximum:
        return folded, []
    by_recency = sorted(folded, key=lambda r: r.get("occurred_at") or "", reverse=True)
    ordered = sorted(by_recency,
                     key=lambda r: (KEEP_PRIORITY.get(r.get("outcome"), 3),
                                    -int(r.get("occurrences") or 1)))
    return ordered[:maximum], ordered[maximum:]


def fold(store, maximum=DEFAULT_MAX, apply_changes=False):
    """Collapse duplicate signatures and trim to the cap.

    A dry run reports exactly what applying would do and writes nothing.
    """
    rows = load(store)
    folded = group(rows=rows)
    kept, dropped = _trim(folded, int(maximum or DEFAULT_MAX))

    report = {
        "coresentinel_api": "1.1",
        "rows_before": len(rows),
        "distinct": len(folded),
        "rows_after": len(kept),
        "reclaimed": len(rows) - len(kept),
        "dropped": [{"id": r.get("group_id"), "statement": r.get("statement"),
                     "outcome": r.get("outcome"), "occurrences": r.get("occurrences")}
                    for r in dropped],
        "cap": int(maximum or DEFAULT_MAX),
        "applied": bool(apply_changes),
    }

    if not apply_changes or len(rows) == len(kept):
        report["applied"] = False
        return report

    repository = _repository(store)
    repository.clear()
    # Oldest first, so the store reads in the order the events happened.
    for row in sorted(kept, key=lambda r: r.get("occurred_at") or ""):
        repository.append(row)
    return report


def enforce(store, maximum=DEFAULT_MAX):
    """The write-path guard: fold only once the log is actually over its cap.

    Returns the fold report, or None when nothing needed doing. Called after an
    append, so the cost is paid once per `maximum` appends rather than on each.
    """
    maximum = int(maximum or DEFAULT_MAX)
    try:
        if _repository(store).count() <= maximum:
            return None
    except Exception:
        # A store that cannot be counted is a store that must not be rewritten.
        return None
    return fold(store, maximum, apply_changes=True)


def summary(store):
    folded = group(store)
    by_kind, by_outcome = {}, {}
    for row in folded:
        by_kind[row.get("kind")] = by_kind.get(row.get("kind"), 0) + 1
        by_outcome[row.get("outcome")] = by_outcome.get(row.get("outcome"), 0) + 1
    return {
        "stored": _repository(store).count(),
        "distinct": len(folded),
        "by_kind": by_kind,
        "by_outcome": by_outcome,
        "recurring": sorted(
            [{"id": r["group_id"], "statement": r.get("statement"),
              "occurrences": r["occurrences"], "outcome": r.get("outcome")}
             for r in folded if r["occurrences"] > 1],
            key=lambda r: r["occurrences"], reverse=True),
    }
