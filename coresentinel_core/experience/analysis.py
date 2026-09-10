"""
Turning experiences into candidate lessons — and refusing to turn most of them.

The rule this module exists to keep is `observer.py`'s, and it is quoted here
because it is easy to lose:

    Nothing here reads code and infers a lesson. An observer that invents rules
    from source it does not understand produces governance nobody agreed to.

So a candidate's text is a *description of what happened*, never a prescription.
"Quality gate 'Security' blocked (SECRET_DETECTED), seen 6×" is an observation a
human can act on. "Always scan for secrets before committing" is a rule, and a
rule is written by whoever proposes it, not inferred here from a gate code.

## Repetition is not corroboration

The hardest decision in this module, and the one most worth stating plainly.

One signature recurring in one context is **one source**, however many times it
recurs. It is not N sources. `candidates.observe` already refuses to let a
single source corroborate itself (`candidates.py:93`) precisely so one noisy
incident cannot reach the evidence threshold alone, and a flapping gate is the
same problem wearing a different hat: fifty failures of one misconfigured check
is one fact observed fifty times, not fifty facts.

What repetition *is* is strength — it feeds the frequency and success terms of
the confidence score, where its weight is visible and arguable. What it is not
is independence.

Independent corroboration therefore still means what it always meant: the same
lesson arriving from somewhere else. A gate failure that recurs (experience) and
an incident somebody resolved with a matching learning (incident) are two
sources and reach the threshold. That is a real loop, and it is a better one
than the store had, because the experience half of it now happens on its own.
"""

from coresentinel_core.experience import records, retention

# Occurrences before a failure is treated as recurring rather than as a one-off.
# Matches `observer.MIN_PATTERN_OCCURRENCES`, and for the same reason: the first
# time is an event, the second is a pattern.
MIN_OCCURRENCES = 2

# Outcomes that can start a lesson. A success is evidence *about* a lesson —
# it raises the success rate of a signature already known — but on its own it
# proposes nothing. "The gate passed" is not something to learn.
LESSON_OUTCOMES = {records.FAILURE}


def _source_id(row):
    """The origin of an observation, for the evidence threshold.

    One per signature *and* context, so the same failure in two environments is
    two sources and the same failure twice in one environment is one.
    """
    return f"experience:{row.get('signature')}@{row.get('context') or 'global'}"


def lesson_for(row):
    """The candidate text for one folded experience. Descriptive, never prescriptive."""
    statement = (row.get("statement") or "").strip()
    if not statement:
        return None
    occurrences = int(row.get("occurrences") or 1)
    if occurrences > 1:
        statement = f"{statement}, seen {occurrences}×"
    context = row.get("context")
    return f"{statement} [{context}]" if context else statement


def recurring_failures(store=None, rows=None, minimum=MIN_OCCURRENCES):
    """Folded experiences that have earned a candidate.

    A failure that happened once is an event. This returns the ones that came
    back, which is the difference between something that went wrong and
    something that keeps going wrong.
    """
    folded = retention.group(store=store, rows=rows)
    return [row for row in folded
            if row.get("outcome") in LESSON_OUTCOMES
            and int(row.get("occurrences") or 1) >= minimum]


def evidence_for(row, store=None, rows=None):
    """The success/failure tally behind one experience, for the confidence terms.

    Phase 3 reads this. It is computed here because the split by context is a
    property of the experience log, not of the candidate record.
    """
    tally = retention.outcomes_for(row.get("signature"), store=store, rows=rows)
    successes = sum(bucket["success"] for bucket in tally.values())
    failures = sum(bucket["failure"] for bucket in tally.values())
    return {
        "occurrences": int(row.get("occurrences") or 1),
        "success_count": successes,
        "failure_count": failures,
        "contexts": sorted(tally),
        "by_context": tally,
    }


def observe(store, minimum=MIN_OCCURRENCES):
    """Record a candidate for every recurring failure. Idempotent by construction.

    Re-running does not inflate evidence: the source id is derived from the
    signature and context, and `candidates.observe` counts a source once.
    """
    from coresentinel_core.learning import candidates

    rows = retention.load(store)
    seen = []
    for row in recurring_failures(rows=rows, minimum=minimum):
        lesson = lesson_for(row)
        if not lesson:
            continue
        evidence = evidence_for(row, rows=rows)
        detail = (f"{evidence['occurrences']}× "
                  f"({evidence['failure_count']} failed, {evidence['success_count']} succeeded)")
        seen.append(candidates.observe(store, lesson, source=_source_id(row),
                                       kind="experience", detail=detail))
    return [c for c in seen if c]


def summary(store):
    rows = retention.load(store)
    recurring = recurring_failures(rows=rows)
    return {
        "experiences": len(rows),
        "distinct": len(retention.group(rows=rows)),
        "recurring_failures": len(recurring),
        "lessons": [lesson_for(row) for row in recurring],
        "threshold": MIN_OCCURRENCES,
    }
