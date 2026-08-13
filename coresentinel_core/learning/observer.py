"""
The observer — where lessons come from.

Three sources, all of them things somebody already wrote down:

    incidents   a resolved incident's `learning` field, which Phase 7 made
                first-class precisely so this could read it
    failures    the failures memory layer, where a fact recorded twice is a
                mistake made twice
    patterns    a pattern whose occurrence count has risen, meaning the same
                solution keeps being needed

Nothing here reads code and infers a lesson. An observer that invents rules from
source it does not understand produces governance nobody agreed to, which is the
opposite of controlled evolution.
"""

from coresentinel_core.learning import candidates

MIN_PATTERN_OCCURRENCES = 2


def observe_incidents(store, target_dir="."):
    """A resolved incident's learning is the strongest signal there is."""
    from coresentinel_core.incidents import ledger as incidents

    seen = []
    for incident in incidents.load(target_dir):
        learning = (incident.get("learning") or "").strip()
        if not learning:
            continue
        seen.append(candidates.observe(
            store, learning, source=incident["id"], kind="incident",
            detail=incident.get("root_cause")))
    return seen


def observe_failures(store, target_dir="."):
    """The failures layer: a fact recorded there is a mistake that happened."""
    import coresentinel_memory as mem

    seen = []
    for fact in mem.layer_facts("failures", target_dir):
        text = (fact.get("fact") or "").strip()
        if not text:
            continue
        seen.append(candidates.observe(
            store, text, source=fact.get("source") or fact.get("id") or text[:40],
            kind="failure", detail=fact.get("source")))
    return seen


def observe_patterns(store, target_dir="."):
    """A pattern needed repeatedly is a rule waiting to be written."""
    from coresentinel_core.patterns import ledger as patterns

    seen = []
    for pattern in patterns.load(target_dir, include_core=True):
        if pattern.get("occurrences", 1) < MIN_PATTERN_OCCURRENCES:
            continue
        lesson = pattern.get("gotchas") or pattern.get("solution") or pattern.get("name")
        if not lesson:
            continue
        seen.append(candidates.observe(
            store, lesson, source=pattern["id"], kind="pattern",
            detail=f"seen {pattern['occurrences']}×"))
    return seen


def run(store, target_dir="."):
    """One observation pass across every source. Idempotent by construction.

    Re-running does not inflate evidence: `observe` counts a source once, so a
    second pass over the same incidents changes nothing.
    """
    observed = []
    observed += observe_incidents(store, target_dir)
    observed += observe_failures(store, target_dir)
    observed += observe_patterns(store, target_dir)

    unique = {c["id"]: c for c in observed if c}
    return {
        "observed": len(unique),
        "candidates": list(unique.values()),
        "ready": [c for c in unique.values() if c.get("status") == candidates.CORROBORATED],
        "rejected": [c for c in unique.values() if c.get("status") == candidates.REJECTED],
    }
