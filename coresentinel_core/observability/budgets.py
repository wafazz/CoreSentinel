"""
Published performance budgets.

A budget is a number this project will not quietly exceed. Each one below was
set from a measurement on a real store, with headroom for a slower machine — CI
runs on shared hardware, and a budget tight enough to flake is a budget that
gets deleted rather than met.

`headroom` records how much slack the budget carries over what was measured when
it was set. It is documentation, not a threshold: if a change makes something
four times slower and the budget still passes, the headroom column is where that
shows up.

Every budget names the measurement that justifies it. A limit with no measured
basis is a guess wearing a number, and this codebase has spent two phases
removing those.
"""

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"

# key -> budget. `measured` is what the operation cost when the budget was set,
# on the machine named in `basis`. It is not re-derived at runtime.
BUDGETS = {
    "recall.10k_facts_ms": {
        "limit": 200,
        "unit": "ms",
        "measured": 40,
        "what": "Rank a query across a 10,000-fact store",
        "basis": "Planning.md Phase 11; measured 2026-08-14, Windows 11 / Python 3.12, "
                 "median of 5 after warm-up",
    },
    "context.assemble_10k_facts_ms": {
        "limit": 1500,
        "unit": "ms",
        "measured": 213,
        "what": "Assemble a task-relevant context pack over a 10,000-fact store",
        "basis": "Includes four git subprocesses, which dominate the remainder",
    },
    "storage.read_page_of_10k_ms": {
        "limit": 50,
        "unit": "ms",
        "measured": 0.5,
        "what": "Read the newest 20 records out of 10,000",
    },
    "storage.read_page_of_10k_mb": {
        "limit": 1.0,
        "unit": "MB",
        "measured": 0.02,
        "what": "Peak heap while reading the newest 20 records out of 10,000",
    },
    "storage.append_800_records_ms": {
        "limit": 4000,
        "unit": "ms",
        "measured": 465,
        "what": "Append 800 records to an empty collection",
    },
    "audit.emit_audited_event_ms": {
        "limit": 25,
        "unit": "ms",
        "measured": 1.3,
        "what": "Emit one event, persisted and recorded in the hash chain",
    },
    "runtime.bootstrap_ms": {
        "limit": 50,
        "unit": "ms",
        "measured": 1.4,
        "what": "Construct the runtime for a working directory",
        "basis": "Carried forward from Phase 2, where it was first asserted",
    },

    # The one budget that does not describe a duration. Every limit above is in
    # milliseconds and therefore describes the machine as much as the code: a
    # slower CI runner moves all of them at once. This one is a ratio, so it
    # holds on any hardware, and it is the property that actually matters —
    # writing record 4,000 must not cost more than writing record 1.
    #
    # It is the regression guard for the defect this phase existed to remove:
    # the audit trail re-read itself on every append, so the cost per record
    # rose 11.4x between an empty store and one holding 4,000 records, and kept
    # rising. A trail that slows down as it fills is one that gets turned off.
    "audit.append_scaling_ratio": {
        "limit": 3.0,
        "unit": "x",
        "measured": 1.0,
        "what": "Cost of one audited event into a 4,000-record store, over the same "
                "event into an empty one",
        "basis": "Measured 11.4x before Phase 11, 1.0x after. The limit is 3x because "
                 "filesystem and cache effects are not free even when the algorithm "
                 "is flat; anything approaching it means something started re-reading.",
    },
}


def headroom(key):
    """How many times over the measured cost the budget sits. None if unmeasured."""
    budget = BUDGETS.get(key)
    if not budget or not budget.get("measured"):
        return None
    return round(budget["limit"] / budget["measured"], 1)


def check(key, observed):
    """Compare a measurement against its budget.

    An observation of None is UNKNOWN, not a pass. Nothing ran, so nothing is
    known — the same rule the verification engine keeps.
    """
    budget = BUDGETS.get(key)
    if not budget:
        return {"key": key, "status": UNKNOWN, "reason": "no budget is published for this key"}
    if observed is None:
        return {"key": key, "status": UNKNOWN, "limit": budget["limit"],
                "unit": budget["unit"], "what": budget["what"],
                "reason": "nothing measured it on this run"}

    observed = float(observed)
    within = observed <= budget["limit"]
    return {
        "key": key,
        "status": PASS if within else FAIL,
        "observed": round(observed, 3),
        "limit": budget["limit"],
        "unit": budget["unit"],
        "what": budget["what"],
        "headroom_when_set": headroom(key),
        "reason": None if within else
                  f"{observed:.1f}{budget['unit']} exceeds the published "
                  f"{budget['limit']}{budget['unit']} budget",
    }


def report(observations):
    """Check every published budget against a dict of {key: observed}."""
    results = [check(key, (observations or {}).get(key)) for key in sorted(BUDGETS)]
    failed = [r for r in results if r["status"] == FAIL]
    unknown = [r for r in results if r["status"] == UNKNOWN]
    return {
        "coresentinel_api": "1.1",
        "budgets": results,
        "total": len(results),
        "passed": len(results) - len(failed) - len(unknown),
        "failed": len(failed),
        "unknown": len(unknown),
        # A budget nothing measured is not a pass. The verdict says so.
        "verdict": "OVER_BUDGET" if failed else ("INCOMPLETE" if unknown else "WITHIN_BUDGET"),
    }
