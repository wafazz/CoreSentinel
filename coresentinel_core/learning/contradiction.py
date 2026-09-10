"""
When the evidence disagrees with itself — and when it only looks like it does.

`decisions/contradiction.py` already does this for the decision ledger, and its
tokenizer, reversal-signal list and stopword set are reused here rather than
restated. What is not reused is its record shape: a decision has a `chosen` and
some `alternatives`, and a lesson has neither.

## The distinction the whole module exists for

Three situations look identical in a naive check, and only one of them is a
contradiction:

    same signature, opposite outcomes, SAME context
        -> INCONSISTENT. The evidence genuinely disagrees. Lower consistency,
           and refuse trust until somebody looks.

    same signature, opposite outcomes, DIFFERENT contexts
        -> SCOPED. Not a contradiction at all. It failed on one stack and worked
           on another, which means the lesson was drawn too wide, not that it was
           wrong. Both survive; each narrows to where its evidence actually is.

    two lessons whose statements conflict, one proposing to reverse the other
        -> SUPERSEDES, but only if the newer one outscores the older. Otherwise
           it is a challenge that has not earned anything yet.

The middle row is the one that matters. It is the difference between a system
that learns "Redis is wrong" and one that learns "Redis is wrong *on this host*".
Overriding where it should have narrowed is exactly how a learning system
produces confident nonsense — and it produces it from real evidence, which is
what makes it hard to spot afterwards.

## Nothing is deleted

A superseded candidate keeps its record and gains `superseded_by`. The history
of what the system used to believe, and what changed its mind, is the part a
person needs when the new belief turns out to be wrong too.
"""

from coresentinel_core.decisions import contradiction as decision_rules

INCONSISTENT = "INCONSISTENT"
SCOPED = "SCOPED"
SUPERSEDES = "SUPERSEDES"

VERDICTS = [INCONSISTENT, SCOPED, SUPERSEDES]

# Shared terms two lessons need before they are considered to be about the same
# thing. One word in common is a coincidence; the stopword set already removes
# the words everything shares.
MIN_SHARED_TERMS = 2

# ...and the shared terms must also be most of what the shorter lesson is about.
#
# The decision-ledger detector is deliberately biased toward flagging, because
# there a finding costs one reviewer one glance. Here a SUPERSEDES finding can
# *act* — it marks the loser SUPERSEDED and takes it out of retrieval — so the
# same bias would let vocabulary overlap quietly retire a good lesson. Run
# against a real store, count alone flagged six unrelated pairs that happened to
# share two words.
#
# Overlap is measured against the smaller term set, so a short lesson fully
# contained in a long one still counts.
MIN_OVERLAP_RATIO = 0.5


def json_key(value):
    """A stable, hashable rendering of a tally, for deduplicating findings."""
    import json

    return json.dumps(value, sort_keys=True, default=str)


def terms_of(text):
    """Identifying terms of a lesson, using the decision ledger's tokenizer."""
    return set(decision_rules.tokenize(text))


def reversal_signals(text):
    return decision_rules.reversal_signals(text)


# ------------------------------------------------------------ outcome conflict

def outcome_findings(candidate):
    """Where a candidate's own evidence disagrees, split by context.

    Reads the per-context tallies the experience log recorded. A context that
    saw both successes and failures of the same signature is inconsistent; two
    contexts that each saw only one is a scope that was drawn too wide.
    """
    findings = []
    # A finding is about a signature, not about each evidence entry that happens
    # to mention it. Several sources carrying the same tally would otherwise
    # report the same disagreement once per source and inflate the count that
    # decides whether trust is withheld.
    seen = set()
    for entry in candidate.get("evidence", []):
        metrics = entry.get("metrics") or {}
        by_context = metrics.get("by_context") or {}
        signature = metrics.get("signature")
        fingerprint = (signature, json_key(by_context))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        mixed_contexts, failing, succeeding = [], [], []
        for context, tally in by_context.items():
            successes = int(tally.get("success") or 0)
            failures = int(tally.get("failure") or 0)
            if successes and failures:
                mixed_contexts.append((context, successes, failures))
            elif failures:
                failing.append(context)
            elif successes:
                succeeding.append(context)

        for context, successes, failures in mixed_contexts:
            findings.append({
                "verdict": INCONSISTENT,
                "signature": signature,
                "context": context,
                "detail": (f"the same signature both succeeded ({successes}×) and "
                           f"failed ({failures}×) in {context} — the evidence "
                           f"disagrees with itself, which is a reason to look "
                           f"rather than a number to average"),
            })

        if failing and succeeding:
            findings.append({
                "verdict": SCOPED,
                "signature": signature,
                "context": None,
                "failing_in": sorted(failing),
                "succeeding_in": sorted(succeeding),
                "detail": (f"fails in {', '.join(sorted(failing))} and succeeds in "
                           f"{', '.join(sorted(succeeding))} — the lesson is scoped, "
                           f"not wrong"),
            })
    return findings


def contradicting_count(candidate):
    """How much of a candidate's evidence genuinely disagrees with itself.

    Only INCONSISTENT counts. SCOPED deliberately does not: narrowing a lesson
    is not evidence against it, and treating it as such would penalise exactly
    the candidates that are becoming more precise.
    """
    return sum(1 for f in outcome_findings(candidate) if f["verdict"] == INCONSISTENT)


# ---------------------------------------------------------- statement conflict

def statement_findings(candidate, others):
    """Other candidates whose lesson this one proposes to reverse."""
    text = str(candidate.get("lesson") or "")
    my_terms = terms_of(text)
    signals = reversal_signals(text)
    if not signals or not my_terms:
        return []

    findings = []
    for other in others:
        if other.get("id") == candidate.get("id"):
            continue
        if other.get("status") in ("REJECTED", "SUPERSEDED"):
            continue
        their_terms = terms_of(other.get("lesson"))
        shared = my_terms & their_terms
        if len(shared) < MIN_SHARED_TERMS:
            continue
        smaller = min(len(my_terms), len(their_terms)) or 1
        overlap = len(shared) / float(smaller)
        if overlap < MIN_OVERLAP_RATIO:
            continue
        findings.append({
            "verdict": SUPERSEDES,
            "candidate": other["id"],
            "shared_terms": sorted(shared),
            "overlap": round(overlap, 3),
            "reversal_signals": signals,
            "detail": (f"proposes reversing {other['id']}, which says: "
                       f"{other.get('lesson')}"),
        })
    return findings


# --------------------------------------------------------------------- the pass

def check(store, now=None):
    """Every finding across the candidate store. Read-only.

    Returns findings, never writes. `validate` is what acts on them, so a caller
    can look before anything changes.
    """
    from coresentinel_core.learning import candidates

    records = candidates.scored(store, now)
    findings = []
    for record in records:
        for finding in outcome_findings(record):
            findings.append({**finding, "id": record["id"], "lesson": record["lesson"]})
        for finding in statement_findings(record, records):
            findings.append({**finding, "id": record["id"], "lesson": record["lesson"]})

    order = {INCONSISTENT: 0, SUPERSEDES: 1, SCOPED: 2}
    findings.sort(key=lambda f: (order[f["verdict"]], str(f["id"])))
    return findings


def _resolve_supersessions(store, records, findings, now=None):
    """Apply SUPERSEDES, but only where the challenger actually outscores.

    A newer lesson that contradicts an older one and scores no better has not
    earned anything. Letting recency alone win would mean the last thing
    observed always becomes the truth, which is not learning — it is forgetting
    with extra steps.
    """
    from coresentinel_core.learning import candidates

    by_id = {r["id"]: r for r in records}
    superseded = []
    for finding in findings:
        if finding["verdict"] != SUPERSEDES:
            continue
        challenger = by_id.get(finding["id"])
        incumbent = by_id.get(finding["candidate"])
        if not challenger or not incumbent:
            continue
        if incumbent.get("status") in (candidates.REJECTED, candidates.SUPERSEDED):
            continue
        if challenger["confidence"] <= incumbent["confidence"]:
            continue

        raw = candidates.get(store, incumbent["id"])
        candidates._replace(store, {**raw, "status": candidates.SUPERSEDED,
                                    "superseded_by": challenger["id"]})
        superseded.append({"superseded": incumbent["id"], "by": challenger["id"],
                           "was": round(incumbent["confidence"], 4),
                           "now": round(challenger["confidence"], 4)})
    return superseded


def validate(store, now=None, apply_changes=True):
    """Record contradictions, then promote what has earned the advisory tier.

    Promotion stops at TRUSTED. That is a retrieval tier — a cited line in a
    context pack that an agent may disregard — and it compels nothing, which is
    what makes reaching it without a human safe. PROPOSED is a governance act
    and is not reachable from here at any confidence.
    """
    from coresentinel_core.learning import candidates, confidence as scoring

    findings = check(store, now)
    records = candidates.scored(store, now)

    superseded = (_resolve_supersessions(store, records, findings, now)
                  if apply_changes else [])

    promoted, blocked = [], []
    for record in candidates.scored(store, now):
        # Promotion is only ever from CORROBORATED. An OBSERVED candidate is
        # still explained, though — "1 distinct source, needs 3" is the answer
        # to "why is this not being used?", and withholding it would make the
        # queue look arbitrary.
        if record.get("status") not in (candidates.CORROBORATED, candidates.OBSERVED):
            continue
        promotable = record.get("status") == candidates.CORROBORATED

        raw = candidates.get(store, record["id"])
        disagreements = contradicting_count(record)
        rescored = candidates.enrich({**raw, "contradicting": disagreements}, now)
        eligible = scoring.qualifies_for_trust(
            rescored["confidence_terms"], len(raw.get("sources") or []), disagreements)

        if apply_changes and (raw.get("contradicting") or 0) != disagreements:
            raw = candidates._replace(store, {**raw, "contradicting": disagreements})

        if eligible and promotable:
            if apply_changes:
                candidates._replace(store, {**raw, "status": candidates.TRUSTED})
            promoted.append({"id": record["id"], "lesson": record["lesson"],
                             "confidence": rescored["confidence"]})
        else:
            blocked.append({
                "id": record["id"],
                "status": record.get("status"),
                "confidence": rescored["confidence"],
                "sources": len(raw.get("sources") or []),
                "contradicting": disagreements,
                "why": _why_not(rescored, len(raw.get("sources") or []), disagreements),
            })

    return {
        "coresentinel_api": "1.1",
        "findings": findings,
        "inconsistent": len([f for f in findings if f["verdict"] == INCONSISTENT]),
        "scoped": len([f for f in findings if f["verdict"] == SCOPED]),
        "superseded": superseded,
        "promoted": promoted,
        "blocked": blocked,
        "applied": bool(apply_changes),
    }


def _why_not(rescored, sources, disagreements):
    """The specific reason trust was withheld. A bare 'not eligible' teaches nothing."""
    from coresentinel_core.learning import confidence as scoring

    reasons = []
    if rescored["confidence"] < scoring.TRUSTED_CONFIDENCE:
        reasons.append(f"confidence {rescored['confidence']:.2f} is below "
                       f"{scoring.TRUSTED_CONFIDENCE:.2f}")
    if sources < scoring.TRUSTED_MIN_SOURCES:
        reasons.append(f"{sources} distinct source(s), needs "
                       f"{scoring.TRUSTED_MIN_SOURCES} — repetition does not count")
    if disagreements:
        reasons.append(f"{disagreements} unresolved contradiction(s)")
    return "; ".join(reasons)
