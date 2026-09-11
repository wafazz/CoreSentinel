"""
How much a candidate has earned, and the arithmetic that says why.

The rule this module is built around: **a confidence number carries its terms or
it does not ship.** A score whose inputs are not stored beside it is a number
nobody can argue with, which is worse than no number at all — it looks like a
measurement and behaves like an opinion. Everything here returns the breakdown
alongside the result, and `evolve explain` prints it.

Four terms, each independently meaningful:

    evidence      how many *distinct* sources say it
    success       how often the thing actually worked
    consistency   whether the evidence agrees with itself
    recency       whether the newest evidence is recent enough to still hold

Weights are declared, not tuned into a black box. They sum to 1.0 so the result
is readable as a fraction, and the bands they are compared against are the ones
`coresentinel_memory.classify_confidence` already uses — 0.90 Known, 0.50
Assumed. Inventing a second scale would mean two meanings for 0.85 in one
system, and the older meaning is already in every memory layer.

## A term with nothing to say is excluded, not scored against

A term whose input says nothing returns `None`, is dropped from the average, and
its weight is redistributed across the terms that *do* have something to say.
`coresentinel_score.py` already works this way — a signal it cannot evaluate on
this machine is left out of the denominator rather than counted as a failure —
and the same reasoning applies here: an unmeasured term is not a low score.

This was wrong for the first release and the arithmetic said so. `success`
carries 0.30 and fell back to a fixed 0.5, so the most a candidate could reach
without outcome data was 0.85 — against a 0.90 bar. A lesson drawn from failures
alone scored 0.0 on the term and capped at 0.70. Since the only producer of
candidates is `experience/analysis.py`, which records a candidate *only* for a
recurring **failure**, every candidate the system actually produced was capped
below the threshold it was being measured against. `TRUSTED` was unreachable by
arithmetic, not by judgement, and the empty tier looked like a young store
rather than a closed door.

Note what this does **not** relax. Repetition still buys nothing: `evidence`
counts distinct sources, and `qualifies_for_trust` still demands three of them.
A flapping check seen two hundred times is still one source and still cannot
promote itself.

## What repetition buys

Nothing, in the `evidence` term. `evidence` counts distinct sources, so fifty
sightings of one signature score exactly what one sighting scores. Repetition
lands in `success` instead, where it moves the ratio and shows its working.

That is the deliberate answer to the obvious shortcut. If repetition counted as
evidence, any flapping check could vote itself to `TRUSTED` overnight, and the
threshold would measure noise rather than agreement.
"""

WEIGHTS = {
    "evidence": 0.35,
    "success": 0.30,
    "consistency": 0.25,
    "recency": 0.10,
}

# Distinct sources at which the evidence term saturates. Two is the corroboration
# floor (`candidates.MIN_EVIDENCE`); three is where a lesson stops being a
# coincidence between two reporters.
EVIDENCE_TARGET = 3

# Reused from the memory lifecycle rather than re-chosen, so a fact and a lesson
# age at the same rate.
DECAY_PER_30_DAYS = 0.05
RECENCY_FLOOR = 0.30

# What a term returns when its input says nothing about it. Dropped from the
# weighted average by `score`, never averaged in as a middling value: 0.5 reads
# as "half right" and drags a total down, which is a verdict, not an absence.
INDETERMINATE = None

# The band a candidate must reach to be retrieved as advisory knowledge, and the
# distinct-source floor it must clear at the same time. Both, not either: a
# perfect success rate from one reporter is still one reporter.
TRUSTED_CONFIDENCE = 0.90
TRUSTED_MIN_SOURCES = 3


def evidence_term(distinct_sources):
    """Distinct sources, saturating at EVIDENCE_TARGET. Repetition is not counted."""
    return min(1.0, max(0, int(distinct_sources or 0)) / float(EVIDENCE_TARGET))


def success_term(successes, failures):
    """The share of observed outcomes that worked, or INDETERMINATE.

    These counts come from `experience/analysis.evidence_for`, which tallies how
    often the *signature* succeeded or failed in the experience log. That is a
    fact about the operation, not about the lesson drawn from it — and the
    difference decides what zero successes means.

    "This keeps breaking" is a reliable observation about a thing that never
    works. Every failure in the tally *corroborates* such a lesson; reading them
    as a 0.0 success rate scores the lesson down for being true. So with no
    successes there is no rate that says anything about whether the lesson holds,
    and the term stands aside for `evidence` and `consistency` to carry it —
    which is what this function's first version said it was doing, and what the
    weights then prevented.

    Revisit this when reuse outcomes are recorded. Once a lesson can be cited and
    *then* observed to hold or fail, zero successes against real failures becomes
    genuine disconfirmation and the term should score it rather than abstain.
    """
    successes = max(0, int(successes or 0))
    failures = max(0, int(failures or 0))
    if not successes:
        return INDETERMINATE
    return successes / float(successes + failures)


def consistency_term(contradicting, total):
    """1.0 when nothing disagrees; 0.0 when everything does."""
    total = max(0, int(total or 0))
    if not total:
        return 1.0
    contradicting = min(max(0, int(contradicting or 0)), total)
    return 1.0 - (contradicting / float(total))


def recency_term(age_days):
    """Decay on the age of the newest evidence, floored.

    Floored rather than zeroed: an old lesson is weaker, not wrong. Something
    learned two years ago that nothing has contradicted since is still the best
    answer available, and scoring it to nothing would quietly delete it from
    every retrieval.
    """
    if age_days is None:
        return RECENCY_FLOOR
    periods = max(0.0, float(age_days)) / 30.0
    return max(RECENCY_FLOOR, 1.0 - (DECAY_PER_30_DAYS * periods))


def age_of(last_seen, now=None):
    """Days since a candidate was last corroborated; None when unparseable."""
    try:
        import coresentinel_memory as mem

        return mem.age_in_days(last_seen, now)
    except Exception:
        return None


def score(distinct_sources, successes=0, failures=0, contradicting=0,
          total_observations=0, last_seen=None, now=None):
    """The weighted confidence, and every term that produced it.

    Returns a dict, never a bare float. A caller that wants only the number can
    take `["confidence"]`; a caller that has to justify it has the rest.
    """
    terms = {
        "evidence": evidence_term(distinct_sources),
        "success": success_term(successes, failures),
        "consistency": consistency_term(contradicting, total_observations),
        "recency": recency_term(age_of(last_seen, now)),
    }

    # Terms that said nothing are dropped and their weight is shared out across
    # the rest, in the declared proportions. The total stays readable as a
    # fraction of what was actually measured, rather than a fraction of what
    # could have been measured if more had been recorded.
    measured = {name: value for name, value in terms.items() if value is not None}
    declared_total = sum(WEIGHTS[name] for name in measured)
    effective = ({name: WEIGHTS[name] / declared_total for name in measured}
                 if declared_total else {})

    contributions = {name: round(value * effective[name], 4)
                     for name, value in measured.items()}
    total = round(sum(contributions.values()), 4)

    return {
        "confidence": total,
        "terms": {name: (round(value, 4) if value is not None else None)
                  for name, value in terms.items()},
        "weights": {name: round(effective.get(name, 0.0), 4) for name in terms},
        "declared_weights": dict(WEIGHTS),
        "indeterminate": sorted(name for name in terms if terms[name] is None),
        "contributions": contributions,
        "inputs": {
            "distinct_sources": int(distinct_sources or 0),
            "successes": int(successes or 0),
            "failures": int(failures or 0),
            "contradicting": int(contradicting or 0),
            "total_observations": int(total_observations or 0),
            "last_seen": last_seen,
        },
        "band": band(total),
    }


def band(confidence):
    """The same three bands the memory engine uses, by the same numbers."""
    if confidence >= 0.90:
        return "Known"
    if confidence >= 0.50:
        return "Assumed"
    return "Unknown"


def qualifies_for_trust(scored, distinct_sources, contradicting=0):
    """Whether a candidate may be promoted to TRUSTED.

    Three conditions, all of them. A high score from one reporter is one
    reporter, and an unresolved contradiction is a reason to look, not a rounding
    error to average away.
    """
    return (scored["confidence"] >= TRUSTED_CONFIDENCE
            and int(distinct_sources or 0) >= TRUSTED_MIN_SOURCES
            and not int(contradicting or 0))


def explain(scored, lesson=None):
    """The arithmetic as text. This is the answer to "why does it believe this?"."""
    lines = []
    if lesson:
        lines.append(f"  Lesson       : {lesson}")
    lines.append(f"  Confidence   : {scored['confidence']:.4f}  ({scored['band']})")
    lines.append("  " + "-" * 60)
    lines.append(f"  {'term':<14}{'value':>8}{'weight':>9}{'contributes':>14}")
    for name in ("evidence", "success", "consistency", "recency"):
        value = scored["terms"][name]
        if value is None:
            lines.append(f"  {name:<14}{'—':>8}{'—':>9}{'not measured':>14}")
            continue
        lines.append(f"  {name:<14}{value:>8.4f}"
                     f"{scored['weights'][name]:>9.2f}"
                     f"{scored['contributions'][name]:>14.4f}")
    lines.append("  " + "-" * 60)
    lines.append(f"  {'total':<14}{'':>8}{'':>9}{scored['confidence']:>14.4f}")

    unmeasured = scored.get("indeterminate") or []
    if unmeasured:
        declared = scored.get("declared_weights") or WEIGHTS
        share = sum(declared[name] for name in unmeasured)
        lines.append("")
        lines.append(f"  Not measured : {', '.join(unmeasured)}"
                     f" — {share:.2f} of the declared weight")
        lines.append("                 redistributed across the terms above, so an")
        lines.append("                 unrecorded term is not counted as a low score.")

    inputs = scored["inputs"]
    lines.append("")
    lines.append(f"  Drawn from   : {inputs['distinct_sources']} distinct source(s)"
                 f" — repetition does not raise this")
    lines.append(f"  Outcomes     : {inputs['successes']} succeeded, "
                 f"{inputs['failures']} failed")
    if inputs["contradicting"]:
        lines.append(f"  Contradicted : {inputs['contradicting']} of "
                     f"{inputs['total_observations']} observation(s)")
    lines.append(f"  Last seen    : {inputs['last_seen'] or 'unknown'}")
    return "\n".join(lines)
