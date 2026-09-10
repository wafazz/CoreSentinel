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
TRUSTED = "TRUSTED"
PROPOSED = "PROPOSED"
REJECTED = "REJECTED"
SUPERSEDED = "SUPERSEDED"

STATUSES = [OBSERVED, CORROBORATED, TRUSTED, PROPOSED, REJECTED, SUPERSEDED]

# Distinct sources a candidate needs before it may become a proposal. One
# incident is an anecdote; the second is what makes it worth a rule.
MIN_EVIDENCE = 2

# TRUSTED and PROPOSED are two different things and it is worth being explicit,
# because the whole safety argument for automatic learning rests on the
# difference.
#
#   TRUSTED   is a *retrieval* tier. It means the candidate has earned a line in
#             a context pack, cited, where an agent may read it and disregard it.
#             It cannot block a gate, fail a build or write a file — and because
#             it compels nothing, it is safe to reach without a human.
#
#   PROPOSED  is a *governance* act. It means somebody intends this to become a
#             rule that constrains every future agent. It is reached by a person
#             running `evolve propose`, and no amount of evidence shortens that
#             path.
#
# Confidence promotes to TRUSTED. Nothing promotes to PROPOSED.
ADVISORY_STATUSES = {TRUSTED}

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


def observe(store, lesson, source, kind="incident", detail=None, now=None,
            metrics=None, context=None):
    """Record an observation. Returns the candidate it belongs to.

    Re-observing from the *same* source does not count twice — otherwise a
    single noisy incident could corroborate itself into a rule.

    `metrics` and `context` are optional and additive. A source that watched the
    thing happen — an experience — can say how often it succeeded and where; a
    source that is a sentence somebody wrote cannot, and passes neither. Both
    default to nothing so every v1 caller keeps working unchanged.
    """
    from coresentinel_core.security import redaction

    # Every source funnels through here, and only one of them was ever redacted.
    # Capture cleans what it observes, but an incident learning, a failures-layer
    # fact and a captured pattern are all free text a person typed, and a person
    # who has just debugged a credential leak writes the credential down. From
    # here a lesson reaches the candidate store, a context pack and a drafted
    # SKILL.md on disk, so this is the last place it can be caught once.
    lesson = redaction.redact_text(lesson)
    detail = redaction.redact_text(detail) if detail else detail

    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)
    candidate_id = fingerprint(lesson)
    existing = get(store, candidate_id)
    entry = {"source": source, "kind": kind, "detail": detail, "at": stamp}
    if metrics:
        entry["metrics"] = dict(metrics)
    if context:
        entry["context"] = context

    if existing is None:
        record = {
            "id": candidate_id,
            "lesson": lesson,
            "kind": kind,
            "status": OBSERVED,
            "sources": [source],
            "evidence": [entry],
            "first_seen": stamp,
            "last_seen": stamp,
            "rejected_reason": None,
            "proposal": None,
            # v2 fields. Absent on a v1 record, and `enrich` supplies them on
            # read, so nothing has to be migrated.
            "superseded_by": None,
            "contradicting": 0,
        }
        store.repository(COLLECTION).append(record)
        return record

    if existing["status"] in (REJECTED, SUPERSEDED):
        # A rejected candidate stays rejected. Resurfacing it on every run is how
        # a review queue becomes noise, and noise is how a control stops working.
        # A superseded one is answered by whatever replaced it.
        return existing

    if source in existing["sources"]:
        return existing

    updated = dict(existing)
    updated["sources"] = existing["sources"] + [source]
    updated["evidence"] = existing["evidence"] + [entry]
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


# ------------------------------------------------------------------- scoring

def tally(record):
    """Outcome counts and contexts gathered from a candidate's evidence.

    Read from the evidence entries rather than stored on the record, so the
    numbers cannot drift from the entries that justify them. A source with no
    metrics — a sentence somebody wrote — contributes nothing here and still
    counts as a source, which is the correct weighting for testimony against
    observation.
    """
    successes = failures = occurrences = 0
    contexts = []
    for entry in record.get("evidence", []):
        metrics = entry.get("metrics") or {}
        successes += int(metrics.get("success_count") or 0)
        failures += int(metrics.get("failure_count") or 0)
        occurrences += int(metrics.get("occurrences") or 0)

        # A source names one context; its metrics may name several, when the
        # same signature was seen in more than one place.
        named = [entry.get("context")] + list(metrics.get("contexts") or [])
        for name in named:
            if name and name not in contexts:
                contexts.append(name)

    return {"success_count": successes, "failure_count": failures,
            "occurrences": occurrences, "contexts": contexts}


def scope_of(contexts):
    """How widely a lesson may be claimed to apply.

    A `global` claim needs evidence from more than one context. This is the
    mechanical form of the rule against learning "Laravel always requires X"
    from evidence that only ever saw one Laravel version on one operating
    system — the observation may be right, but nothing observed said it was
    general.
    """
    distinct = [c for c in (contexts or []) if c]
    if not distinct:
        return "global"
    if len(distinct) > 1:
        return "global"
    return "project"


def enrich(record, now=None):
    """A candidate with its confidence and the arithmetic behind it.

    Computed on read, never stored, so a v1 record written before any of this
    existed scores correctly the first time it is looked at and needs no
    migration step.
    """
    from coresentinel_core.learning import confidence as scoring

    counts = tally(record)
    scored = scoring.score(
        distinct_sources=len(record.get("sources") or []),
        successes=counts["success_count"],
        failures=counts["failure_count"],
        contradicting=record.get("contradicting") or 0,
        total_observations=max(len(record.get("evidence") or []),
                               counts["occurrences"]),
        last_seen=record.get("last_seen"),
        now=now)

    return {
        **record,
        **counts,
        "context": counts["contexts"][0] if len(counts["contexts"]) == 1 else None,
        "scope": scope_of(counts["contexts"]),
        "confidence": scored["confidence"],
        "confidence_terms": scored,
        "trustworthy": scoring.qualifies_for_trust(
            scored, len(record.get("sources") or []), record.get("contradicting") or 0),
    }


def scored(store, now=None):
    """Every candidate, enriched. The read surface for reports and retrieval."""
    return [enrich(record, now) for record in _all(store)]


def trusted(store, now=None):
    """Candidates already promoted to the advisory tier."""
    return [c for c in scored(store, now) if c.get("status") == TRUSTED]


def summary(store):
    records = _all(store)
    enriched = [enrich(r) for r in records]
    return {
        "total": len(records),
        "by_status": {status: sum(1 for r in records if r.get("status") == status)
                      for status in STATUSES},
        "ready": [c["id"] for c in records if c.get("status") == CORROBORATED],
        "evidence_threshold": MIN_EVIDENCE,
        "trusted": [c["id"] for c in enriched if c.get("status") == TRUSTED],
        "eligible_for_trust": [c["id"] for c in enriched
                               if c["trustworthy"] and c.get("status") == CORROBORATED],
    }
