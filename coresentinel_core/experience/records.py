"""
What an experience is, and how an event becomes one.

An experience is a single observed outcome: a gate that failed, a verification
that returned a verdict, a task that finished. It is deliberately *not* a
lesson. "Redis configuration caused queue failure" is an experience; "always
configure Redis this way" is a claim that has to earn itself downstream.

Two fields carry the design.

**`signature`** is the normalised "what happened", and it is what makes
recurrence a count rather than a judgement call. It gets the same treatment
`learning/candidates.fingerprint()` gives a lesson — sorted token set, hashed —
plus the removal of the things that differ between two runs of the same event:
digits, paths, hex blobs, timestamps. Two runs of one failing gate must collapse
to one signature, or nothing is ever seen "repeatedly" and the loop never starts.

**`context_key`** is where it happened. A lesson learned under Laravel 12 /
PHP 8.3 / Ubuntu 24.04 is stored at that key and never as `global`, because the
alternative is learning "Laravel always requires X" from evidence that showed
nothing of the kind. Widening is something evidence earns later, by appearing
under more than one key.

Nothing here writes. Building a record and storing one are separate so the
mapping can be tested without a store, and so `capture` owns every write.
"""

import hashlib
import re
from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# --------------------------------------------------------------------- kinds

GATE = "gate"
VERIFICATION = "verification"
TASK = "task"
AGENT = "agent"
INCIDENT = "incident"
DEPLOYMENT = "deployment"
CORRECTION = "correction"

KINDS = [GATE, VERIFICATION, TASK, AGENT, INCIDENT, DEPLOYMENT, CORRECTION]

SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
MIXED = "MIXED"

OUTCOMES = [SUCCESS, FAILURE, MIXED]

# --------------------------------------------------------------- event mapping

# Only outcome events become experiences. `MemoryCreated` and `AgentStarted` are
# not outcomes — one records that something was written, the other that
# something began. Capturing them is how a learning store fills with facts that
# support no lesson, which §4 of the brief warns against by name.
#
# `DeploymentCompleted` is listed and is currently never emitted. That is
# deliberate: when it is wired, it is already a learning source, and until then
# `audit coverage` reports the same gap it always did.
CAPTURED_EVENTS = {
    "QualityGateFailed": (GATE, FAILURE),
    "QualityGatePassed": (GATE, SUCCESS),
    "VerificationCompleted": (VERIFICATION, None),
    "TaskCompleted": (TASK, None),
    "AgentCompleted": (AGENT, None),
    "IncidentCreated": (INCIDENT, FAILURE),
    "DeploymentCompleted": (DEPLOYMENT, None),
}

# Payload keys read to decide an outcome when the event name does not settle it.
RESULT_KEYS = ["result", "status", "verdict", "final_status", "outcome"]

# Values that mean the thing did not work. Compared case-insensitively against
# whichever of RESULT_KEYS is present.
FAILURE_VALUES = {"blocked", "failed", "fail", "failure", "error", "rejected",
                  "refuted", "unverified", "insufficient", "denied", "timeout"}
SUCCESS_VALUES = {"approved", "passed", "pass", "ok", "success", "succeeded",
                  "verified", "confirmed", "complete", "completed", "clean"}
MIXED_VALUES = {"partial", "mixed", "degraded", "warning", "review required",
                "review_required", "unknown"}

# Payload keys that identify *what* happened, in the order they best describe it.
# The first one present becomes the basis of the signature.
SUBJECT_KEYS = ["gate", "blocked_by", "claim", "objective", "title", "problem",
                "agent", "target", "detail"]

# --------------------------------------------------------------- normalisation

TOKEN = re.compile(r"[a-z0-9]+")

# Stripped before tokenising, because they differ between two runs of the same
# event and would give one recurring failure a fresh signature every time.
VOLATILE = [
    re.compile(r"[a-fA-F0-9]{7,}"),                       # hashes, ids, hex blobs
    re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?"),  # timestamps
    re.compile(r"[A-Za-z]:[\\/][^\s'\"]+"),               # windows paths
    re.compile(r"(?:/[^\s'\"/]+){2,}"),                   # posix paths
    re.compile(r"\b\d+(?:\.\d+)*\b"),                     # numbers and versions
]

# Words that describe every event equally and so identify none of them.
GENERIC = {"the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with",
           "at", "as", "is", "are", "be", "was", "were", "it", "this", "that",
           "run", "ran", "result", "status", "none", "null", "true", "false"}

MIN_TERM_LENGTH = 2


def normalise(text):
    """Strip what varies between two runs, keep what identifies the event."""
    lowered = str(text or "").lower()
    for pattern in VOLATILE:
        lowered = pattern.sub(" ", lowered)
    terms = [t for t in TOKEN.findall(lowered)
             if len(t) >= MIN_TERM_LENGTH and t not in GENERIC]
    return sorted(set(terms))


def signature(kind, subject):
    """A stable id for "this happened again".

    `kind` is hashed in, so a task and a gate failure that share wording do not
    collapse into one signature and corroborate each other. An empty subject
    still produces a signature — for a bare `QualityGatePassed` with nothing but
    a result, "this kind of thing happened" is the honest grouping.
    """
    terms = normalise(subject)
    basis = f"{kind}|{' '.join(terms)}"
    return "SIG-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def group_id(kind, sig, context_key):
    """Deterministic, so the same experience in the same context is one group.

    Retention folds on this. Two identical gate failures a week apart are one
    fact seen twice, and a store that cannot tell that is a store that cannot
    tell repetition from volume.

    Deliberately *not* the record's `id`. The persistence port stamps `id` on
    append and both backends own it — SQLite enforces it UNIQUE, so a
    deterministic id makes the second sighting of a recurring failure a hard
    write error rather than a second row. Grouping is a property of the record;
    identity is a property of the row, and conflating them broke on the backend
    that actually checks.
    """
    basis = f"{kind}|{sig}|{context_key or 'global'}"
    return "EXP-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


# --------------------------------------------------------------------- outcome

def classify_outcome(payload, default=None):
    """SUCCESS / FAILURE / MIXED from whatever the emitter put in the payload.

    Returns `default` when nothing in the payload settles it, and MIXED when
    even the default is absent — an outcome we could not read is not a success,
    and calling it one would teach the wrong lesson from a real event.
    """
    for key in RESULT_KEYS:
        if key not in (payload or {}):
            continue
        value = str((payload or {}).get(key) or "").strip().lower()
        if not value:
            continue
        if value in FAILURE_VALUES:
            return FAILURE
        if value in SUCCESS_VALUES:
            return SUCCESS
        if value in MIXED_VALUES:
            return MIXED
    return default or MIXED


def subject_of(payload):
    """The best available description of what happened, for the signature."""
    for key in SUBJECT_KEYS:
        value = (payload or {}).get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
    return ""


def statement_for(kind, outcome, payload):
    """One human-readable sentence. This is what a reader sees in a report."""
    subject = subject_of(payload)
    verb = {SUCCESS: "succeeded", FAILURE: "failed", MIXED: "was inconclusive"}[outcome]
    if kind == GATE and outcome == FAILURE:
        gate = (payload or {}).get("blocked_by") or (payload or {}).get("gate")
        code = (payload or {}).get("code")
        if gate:
            return f"Quality gate '{gate}' blocked" + (f" ({code})" if code else "")
    if not subject:
        return f"{kind.capitalize()} {verb}"
    return f"{kind.capitalize()} {verb}: {subject}"


# ------------------------------------------------------------------ the record

def build(event_name, payload, context_key=None, occurred_at=None, links=None):
    """An experience from an event, or None when the event is not an outcome.

    Returns a plain dict. Redaction happens in `capture`, on the way to the
    store, so that a caller cannot construct a record that skips it by calling
    this directly.
    """
    mapping = CAPTURED_EVENTS.get(event_name)
    if not mapping:
        return None

    kind, fixed_outcome = mapping
    payload = dict(payload or {})
    outcome = fixed_outcome or classify_outcome(payload)
    subject = subject_of(payload)
    sig = signature(kind, subject or event_name)

    return {
        # No `id` — the repository stamps one per row. See `group_id`.
        "group_id": group_id(kind, sig, context_key),
        "kind": kind,
        "outcome": outcome,
        "signature": sig,
        # Stored as `context`, not `context_key`. `redaction.SENSITIVE_KEY_WORDS`
        # matches a trailing `_key` as a credential name, so a field called
        # `context_key` reaches the store as "[redacted]" — the over-redaction
        # its own comment warns about, destroying real data to protect nothing.
        # Renaming the field is the fix; weakening the shared redactor is not.
        "context": context_key,
        "scope": "project" if context_key else "global",
        "statement": statement_for(kind, outcome, payload),
        "subject": subject,
        "occurrences": 1,
        "event": event_name,
        "evidence": payload,
        "links": links or {},
        "occurred_at": occurred_at or datetime.now().strftime(TIMESTAMP_FORMAT),
    }


def is_captured(event_name):
    return event_name in CAPTURED_EVENTS
