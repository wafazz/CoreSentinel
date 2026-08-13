"""
Learning candidates — observations that have not earned the right to be proposals.

The loop this closes:

    incident -> root cause -> pattern -> candidate rule -> evidence
             -> human approval -> versioned rule -> future agents

The gap in the middle is deliberate. An observation is not a lesson, and a lesson
is not a rule. A system that turns every incident straight into a governance rule
produces a rulebook nobody reads and a proposal queue nobody reviews — and a
reviewer who rubber-stamps is a reviewer who has stopped being a control.

So a candidate must be **corroborated** before it may be proposed: seen in at
least MIN_EVIDENCE distinct sources, or explicitly promoted by a human who is
willing to say why. And a candidate that was rejected stays rejected; it does not
reappear on the next observation run to be declined again.
"""

import hashlib
import re
from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

OBSERVED = "OBSERVED"
CORROBORATED = "CORROBORATED"
PROPOSED = "PROPOSED"
REJECTED = "REJECTED"

STATUSES = [OBSERVED, CORROBORATED, PROPOSED, REJECTED]

# Distinct sources a candidate needs before it may become a proposal. One
# incident is an anecdote; the second is what makes it worth a rule.
MIN_EVIDENCE = 2

COLLECTION = "learning_candidates"

TOKEN = re.compile(r"[a-z0-9]+")


def fingerprint(text):
    """A stable id derived from the lesson itself.

    Two observations of the same lesson must land on the same candidate, or the
    evidence count never rises and nothing is ever corroborated.
    """
    words = sorted(set(TOKEN.findall(str(text or "").lower())))
    digest = hashlib.sha1(" ".join(words).encode("utf-8")).hexdigest()
    return f"CAND-{digest[:10]}"


def _all(store):
    return store.repository(COLLECTION).all()


def get(store, candidate_id):
    key = str(candidate_id or "").lower()
    return next((c for c in _all(store) if str(c.get("id", "")).lower() == key), None)


def observe(store, lesson, source, kind="incident", detail=None, now=None):
    """Record an observation. Returns the candidate it belongs to.

    Re-observing from the *same* source does not count twice — otherwise a
    single noisy incident could corroborate itself into a rule.
    """
    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)
    candidate_id = fingerprint(lesson)
    existing = get(store, candidate_id)

    if existing is None:
        record = {
            "id": candidate_id,
            "lesson": lesson,
            "kind": kind,
            "status": OBSERVED,
            "sources": [source],
            "evidence": [{"source": source, "kind": kind, "detail": detail, "at": stamp}],
            "first_seen": stamp,
            "last_seen": stamp,
            "rejected_reason": None,
            "proposal": None,
        }
        store.repository(COLLECTION).append(record)
        return record

    if existing["status"] == REJECTED:
        # A rejected candidate stays rejected. Resurfacing it on every run is how
        # a review queue becomes noise, and noise is how a control stops working.
        return existing

    if source in existing["sources"]:
        return existing

    updated = dict(existing)
    updated["sources"] = existing["sources"] + [source]
    updated["evidence"] = existing["evidence"] + [
        {"source": source, "kind": kind, "detail": detail, "at": stamp}]
    updated["last_seen"] = stamp
    if len(updated["sources"]) >= MIN_EVIDENCE and updated["status"] == OBSERVED:
        updated["status"] = CORROBORATED

    _replace(store, updated)
    return updated


def _replace(store, record):
    """The port is append-oriented, so a rewrite is a full rewrite of the collection."""
    repository = store.repository(COLLECTION)
    records = [record if r.get("id") == record["id"] else r for r in repository.all()]
    repository.clear()
    for item in records:
        repository.append(item)
    return record


def reject(store, candidate_id, reason):
    candidate = get(store, candidate_id)
    if not candidate:
        return {"error": f"candidate '{candidate_id}' not found"}
    if not (reason or "").strip():
        return {"error": "a rejection needs a reason — a silent no teaches nothing"}
    return {"candidate": _replace(store, {**candidate, "status": REJECTED,
                                          "rejected_reason": reason})}


def promote(store, candidate_id, reason=None):
    """Force a candidate to CORROBORATED without a second sighting.

    The escape hatch for a lesson obvious enough not to need repeating — and it
    takes a stated reason, so the shortcut is visible in the record.
    """
    candidate = get(store, candidate_id)
    if not candidate:
        return {"error": f"candidate '{candidate_id}' not found"}
    if candidate["status"] == REJECTED:
        return {"error": "a rejected candidate cannot be promoted; observe it afresh"}
    if not (reason or "").strip():
        return {"error": "promoting past the evidence threshold requires a stated reason"}

    updated = dict(candidate)
    updated["status"] = CORROBORATED
    updated["evidence"] = candidate["evidence"] + [
        {"source": "human", "kind": "promotion", "detail": reason,
         "at": datetime.now().strftime(TIMESTAMP_FORMAT)}]
    return {"candidate": _replace(store, updated)}


def mark_proposed(store, candidate_id, proposal_id):
    candidate = get(store, candidate_id)
    if not candidate:
        return None
    return _replace(store, {**candidate, "status": PROPOSED, "proposal": proposal_id})


def ready(store):
    """Candidates that have earned a proposal and do not have one yet."""
    return [c for c in _all(store) if c.get("status") == CORROBORATED]


def summary(store):
    records = _all(store)
    return {
        "total": len(records),
        "by_status": {status: sum(1 for r in records if r.get("status") == status)
                      for status in STATUSES},
        "ready": [c["id"] for c in records if c.get("status") == CORROBORATED],
        "evidence_threshold": MIN_EVIDENCE,
    }
