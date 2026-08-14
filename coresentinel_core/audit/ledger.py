"""
The audit ledger — append-only and tamper-evident.

v1 recorded one subject out of twelve, gave each run a `RUN-#{random 4 digits}`
id, and appended to a JSON list. Two consequences: ids collided and carried no
order, and anyone could edit the file with no trace. An audit trail you can
silently rewrite is a liability rather than a record — it is worse than no trail,
because it looks like one.

Each record carries the hash of the record before it, so the chain detects the
four ways a trail gets falsified:

    mutation    a record's own hash no longer matches its content
    deletion    the next record's prev_hash points at something that is gone
    insertion   sequence numbers collide, and the link breaks either side
    reordering  prev_hash no longer matches the record that now precedes it

This is tamper-*evidence*, not tamper-proofing. Someone with write access can
recompute the whole chain. What they cannot do is change one record and leave the
rest intact, which is what quiet edits actually look like.

v1 records are imported but never retro-signed. They are listed as
`unverified_legacy`, because hashing them now would assert an integrity that
never existed.
"""

import json
import hashlib
from datetime import datetime

from coresentinel_core.audit import subjects
from coresentinel_core.security.redaction import redact

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

GENESIS_HASH = "sha256:" + "0" * 32
HASH_LENGTH = 32

LEGACY = "unverified_legacy"

# Verification problem codes. Machine-readable for the same reason gate codes are.
MUTATED = "RECORD_MUTATED"
CHAIN_BREAK = "CHAIN_BROKEN"
SEQUENCE_BREAK = "SEQUENCE_BROKEN"
MISSING_HASH = "RECORD_UNHASHED"


def _canonical(record):
    """Deterministic serialisation of everything except the hash itself."""
    payload = {k: v for k, v in record.items() if k not in ("hash", "recorded_at_local")}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(record):
    return "sha256:" + hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()[:HASH_LENGTH]


def _is_chained(record):
    return (record.get("chain") != LEGACY
            and record.get("seq") is not None
            and bool(record.get("hash")))


def _chain_records(store):
    """Chained records only, oldest first.

    A record is in the chain if the ledger wrote it — which means it carries a
    sequence number and a hash. Legacy imports and anything written directly to
    the collection are not; they are counted and reported by `verify` rather than
    treated as chain breaks, because a record that was never signed has not been
    tampered with, it was simply never protected.
    """
    return [r for r in store.audit_events.all() if _is_chained(r)]


def _unchained_records(store):
    """Records in the collection that the ledger did not write."""
    return [r for r in store.audit_events.all()
            if r.get("chain") != LEGACY and (r.get("seq") is None or not r.get("hash"))]


# How far back to look for the head of the chain before giving up and reading
# the whole collection. Escalates so the common case — the newest record is
# chained — is a single-record read, while a long tail of legacy imports still
# resolves correctly rather than silently restarting the chain at seq 1.
TAIL_PROBES = (1, 16, 256)


def last(store):
    """The newest chained record, found without reading the whole trail.

    `append` calls this, and reading every record to write one made the trail
    quadratic: 200 events took 26 seconds, and the cost per event grew with the
    trail it was being added to.
    """
    for probe in TAIL_PROBES:
        window = store.audit_events.recent(probe)
        # recent() is newest-first, so the first chained record in the window is
        # the last one in the chain.
        head = next((r for r in window if _is_chained(r)), None)
        if head:
            return head
        if len(window) < probe:
            # The window was not full, so it held the whole collection and
            # there is nothing chained in it.
            return None

    records = _chain_records(store)
    return records[-1] if records else None


def append(store, subject, actor, action, result=None, detail=None, now=None):
    """Add one record to the chain. Returns it, including its hash."""
    if subject not in subjects.SUBJECTS:
        subject = subjects.OTHER

    previous = last(store)
    record = {
        "id": f"AUD-{(previous['seq'] + 1) if previous else 1:06d}",
        "seq": (previous["seq"] + 1) if previous else 1,
        "subject": subject,
        "actor": actor,
        "action": action,
        "result": result,
        # Redacted before it is written, not before it is displayed.
        "detail": redact(detail or {}),
        "recorded_at": (now or datetime.now()).strftime(TIMESTAMP_FORMAT),
        "prev_hash": previous["hash"] if previous else GENESIS_HASH,
    }
    record["hash"] = compute_hash(record)
    store.audit_events.append(record)
    return record


def import_legacy(store, trail):
    """Bring v1 records in, marked for what they are.

    They are listed but not chained. Hashing them now would assert an integrity
    that never existed, which is the opposite of what an audit trail is for.
    """
    imported = []
    existing = {r.get("legacy_id") for r in store.audit_events.all()}
    for entry in trail or []:
        run_id = entry.get("run_id")
        if not run_id or run_id in existing:
            continue
        record = {
            "id": run_id, "legacy_id": run_id, "chain": LEGACY,
            "subject": subjects.AGENT_ACTION,
            "actor": entry.get("agent"), "action": entry.get("task"),
            "result": entry.get("result"),
            "detail": redact(entry.get("actions") or {}),
            "recorded_at": entry.get("timestamp"),
            "prev_hash": None, "hash": None,
        }
        store.audit_events.append(record)
        imported.append(record)
    return imported


def verify(store):
    """Walk the chain. Returns every problem found, with the record it belongs to."""
    records = _chain_records(store)
    problems = []
    expected_prev = GENESIS_HASH

    for index, record in enumerate(records, start=1):
        identifier = record.get("id", f"<position {index}>")

        if not record.get("hash"):
            problems.append({"code": MISSING_HASH, "record": identifier,
                             "detail": "the record carries no hash"})
            expected_prev = None
            continue

        if record.get("seq") != index:
            problems.append({
                "code": SEQUENCE_BREAK, "record": identifier,
                "detail": f"expected sequence {index}, found {record.get('seq')} — "
                          "a record was inserted or removed"})

        if expected_prev is not None and record.get("prev_hash") != expected_prev:
            problems.append({
                "code": CHAIN_BREAK, "record": identifier,
                "detail": "prev_hash does not match the record before it — "
                          "the trail was reordered, or something between them is gone"})

        if compute_hash(record) != record["hash"]:
            problems.append({
                "code": MUTATED, "record": identifier,
                "detail": "the record's content no longer matches its hash"})

        expected_prev = record["hash"]

    legacy = [r for r in store.audit_events.all() if r.get("chain") == LEGACY]
    unchained = _unchained_records(store)

    notes = []
    if legacy:
        notes.append(f"{len(legacy)} record(s) predate the chain and are listed as "
                     f"{LEGACY}; they are not verified because they were never signed")
    if unchained:
        notes.append(f"{len(unchained)} record(s) were written straight to the collection "
                     "rather than through the ledger, so they carry no hash and are outside "
                     "the chain")

    return {
        "coresentinel_api": "1.1",
        "checked": len(records),
        "legacy": len(legacy),
        "unchained": len(unchained),
        "problems": problems,
        "intact": not problems,
        "verdict": "INTACT" if not problems else "TAMPERED",
        "note": " · ".join(notes) or None,
    }


def recent(store, limit=20, subject=None, offset=0):
    """The newest records, newest first, in a bounded page.

    The page ceiling is enforced by the service layer, not here: this is called
    with limit+1 to detect a further page, and re-clamping would swallow that
    sentinel at exactly the maximum page size.

    Filtering by subject still walks the collection: the port exposes append and
    read-back, not query-by-column, and pushing a WHERE clause into it would
    make the two backends stop being interchangeable. Unfiltered reads — which
    is what every surface issues by default — touch only the page.
    """
    limit = max(0, int(limit or 0))
    offset = max(0, int(offset or 0))
    if not limit:
        return list(reversed(store.audit_events.all()))[offset:]
    if subject:
        matching = [r for r in store.audit_events.all() if r.get("subject") == subject]
        return list(reversed(matching))[offset:offset + limit]
    return store.audit_events.page(limit, offset)


def get(store, identifier):
    key = str(identifier or "").lower()
    return next((r for r in store.audit_events.all()
                 if key in str(r.get("id", "")).lower()), None)


def coverage(store):
    """Which of the twelve subjects have ever been recorded here."""
    seen = {r.get("subject") for r in store.audit_events.all()}
    return {"recorded": sorted(s for s in subjects.SUBJECTS if s in seen),
            "never_recorded": sorted(s for s in subjects.SUBJECTS if s not in seen),
            "total": len(subjects.SUBJECTS)}
