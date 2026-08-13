"""
Architecture Decision Record schema.

v1 recorded eight fields: id, decision, reason, alternatives, chosen, impact,
status, created_at. Enough to remember *what* was chosen, not enough to stop an
agent quietly reversing it — that needs the problem it solved, the evidence
behind it, and what it is connected to.

Every added field is optional and defaults to null. A v1 record loads, renders
and searches exactly as before; nothing is invented to fill a gap, because an
ADR with a fabricated rationale is worse than one with an honest blank.
"""

from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

PROPOSED = "Proposed"
ACCEPTED = "Accepted"
SUPERSEDED = "Superseded"
REJECTED = "Rejected"

STATUSES = [PROPOSED, ACCEPTED, SUPERSEDED, REJECTED]

# Only an accepted decision constrains future work. A proposal is not yet a rule,
# and a superseded or rejected one is history.
BINDING_STATUSES = {ACCEPTED}

# v1 field -> kept as-is. New fields are appended, never renamed, so a v1 reader
# and a v2 reader see the same record.
V1_FIELDS = ["id", "decision", "reason", "alternatives", "chosen",
             "impact", "status", "created_at"]

V2_FIELDS = ["problem", "context", "evidence", "author", "agent", "confidence",
             "related_files", "related_incidents", "related_decisions",
             "supersedes", "superseded_by", "scope", "project"]

ALL_FIELDS = V1_FIELDS + V2_FIELDS

LIST_FIELDS = {"alternatives", "related_files", "related_incidents", "related_decisions"}


def split_list(value):
    """Accept a comma-separated string or a list. Empty means empty, never None."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def normalize(record, scope=None):
    """Fill every absent field with null, so no consumer has to guess a shape.

    `decision` is the v1 name for the title and is kept. `title` is exposed
    alongside it so v2 callers do not have to know that history.
    """
    if not isinstance(record, dict):
        return None

    normalized = dict(record)
    for field in ALL_FIELDS:
        normalized.setdefault(field, None)
    for field in LIST_FIELDS:
        normalized[field] = split_list(normalized.get(field))

    normalized["title"] = record.get("decision") or record.get("title") or "(untitled decision)"
    normalized["status"] = normalized.get("status") or ACCEPTED
    if scope:
        normalized["scope"] = scope
    return normalized


def build(title, reason, chosen, alternatives=None, problem=None, context=None,
          evidence=None, author=None, agent=None, confidence=None, impact="High",
          status=ACCEPTED, related_files=None, related_incidents=None,
          related_decisions=None, decision_id=None, project=None, now=None):
    """A new record. Absent detail stays null rather than being filled with a guess."""
    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)
    return normalize({
        "id": decision_id,
        "decision": title,
        "reason": reason,
        "chosen": chosen,
        "alternatives": split_list(alternatives),
        "problem": problem,
        "context": context,
        "evidence": evidence,
        "author": author,
        "agent": agent,
        "confidence": float(confidence) if confidence is not None else None,
        "impact": impact,
        "status": status if status in STATUSES else ACCEPTED,
        "created_at": stamp,
        "related_files": split_list(related_files),
        "related_incidents": split_list(related_incidents),
        "related_decisions": split_list(related_decisions),
        "supersedes": None,
        "superseded_by": None,
        "project": project,
    })


def is_binding(record):
    return (record or {}).get("status") in BINDING_STATUSES


def completeness(record):
    """How much of the schema a record actually fills, and what is missing.

    Reported rather than enforced: a thin ADR is still worth having, and refusing
    to record one because a field is blank just means it never gets recorded.
    """
    normalized = normalize(record)
    present = [f for f in ALL_FIELDS
               if normalized.get(f) not in (None, "", [], "None")]
    missing = [f for f in ALL_FIELDS if f not in present]
    return {"present": len(present), "total": len(ALL_FIELDS),
            "percent": int(round(len(present) / len(ALL_FIELDS) * 100)),
            "missing": missing}
