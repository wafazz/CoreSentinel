"""
Contradiction detection.

The failure this exists to stop:

    Agent:  "I recommend switching from Redis to database sessions."
    Ledger: ADR-042 — Redis selected because MySQL connection saturation was
            observed under production load.

The agent is not wrong to raise it. It is wrong to act on it without knowing the
decision exists, because the reason it was made is invisible in the code — the
saturation happened in production, months ago, and nothing in the repository
says so.

This is a lexical check, not a semantic one. It reads the ledger, not the model's
intent, so it is deliberately biased toward flagging: a false flag costs one
review, a missed contradiction costs the incident the decision was made to
prevent. Every finding cites the ADR so the reviewer can dismiss it in seconds.
"""

import re

from coresentinel_core.decisions import schema

# Wording that proposes moving away from something already in place.
REVERSAL_SIGNALS = [
    "switch", "switching", "replace", "replacing", "migrate away", "migrating away",
    "move away", "moving away", "instead of", "rather than", "drop", "dropping",
    "remove", "removing", "stop using", "abandon", "abandoning", "deprecate",
    "deprecating", "swap", "swapping", "get rid of", "no longer use", "revert",
    "roll back", "rolling back", "change from", "moving off", "retire",
]

CONTRADICTS = "CONTRADICTS"
REVISITS = "REVISITS"
TOUCHES = "TOUCHES"

BLOCKING = {CONTRADICTS, REVISITS}

TOKEN_PATTERN = re.compile(r"[a-z0-9_.\-/+#]+")

# Words too generic to identify a technology choice. Matching on these produces
# a flag on every sentence, which trains the reader to ignore all of them.
GENERIC = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with", "use",
    "using", "used", "from", "by", "at", "as", "is", "are", "be", "we", "our",
    "it", "this", "that", "new", "old", "add", "adding", "instead", "database",
    "db", "service", "system", "server", "based", "layer", "store", "storage",
    "default", "option", "solution", "approach", "support", "via", "into",
}

MIN_TERM_LENGTH = 3


def tokenize(text):
    return [t for t in TOKEN_PATTERN.findall(str(text or "").lower())
            if len(t) >= MIN_TERM_LENGTH and t not in GENERIC]


def significant_terms(value):
    """Distinct identifying terms of a choice, e.g. 'Redis' from 'Redis cache'."""
    return list(dict.fromkeys(tokenize(value)))


def mentions(haystack_terms, haystack_text, term):
    return term in haystack_terms or term in haystack_text


def reversal_signals(text):
    lowered = " " + " ".join(str(text or "").lower().split()) + " "
    return [signal for signal in REVERSAL_SIGNALS if signal in lowered]


def check(change, decisions):
    """Findings for a proposed change against the binding decisions given.

    Only accepted decisions are considered: a proposal is not yet a rule, and a
    superseded one has already been replaced on the record.
    """
    change_text = " ".join(str(change or "").lower().split())
    change_terms = set(tokenize(change_text))
    signals = reversal_signals(change_text)

    findings = []
    for record in decisions:
        if not schema.is_binding(record):
            continue

        chosen_hits = [t for t in significant_terms(record.get("chosen"))
                       if mentions(change_terms, change_text, t)]
        alternative_hits = []
        for alternative in record.get("alternatives", []):
            hits = [t for t in significant_terms(alternative)
                    if mentions(change_terms, change_text, t)]
            if hits:
                alternative_hits.append(alternative)

        if not chosen_hits and not alternative_hits:
            continue

        if chosen_hits and signals:
            verdict, detail = CONTRADICTS, (
                f"proposes moving away from {record.get('chosen')}, which "
                f"{record.get('id')} selected")
        elif alternative_hits:
            verdict, detail = REVISITS, (
                f"proposes {', '.join(alternative_hits)}, which {record.get('id')} "
                f"considered and rejected in favour of {record.get('chosen')}")
        else:
            verdict, detail = TOUCHES, (
                f"touches {record.get('chosen')}, governed by {record.get('id')}")

        findings.append({
            "verdict": verdict,
            "blocking": verdict in BLOCKING,
            "decision_id": record.get("id"),
            "title": record.get("title") or record.get("decision"),
            "chosen": record.get("chosen"),
            "reason": record.get("reason"),
            "evidence": record.get("evidence"),
            "scope": record.get("scope"),
            "matched_terms": sorted(set(chosen_hits)) or sorted(
                {t for a in alternative_hits for t in significant_terms(a)}),
            "reversal_signals": signals,
            "detail": detail,
        })

    order = {CONTRADICTS: 0, REVISITS: 1, TOUCHES: 2}
    findings.sort(key=lambda f: (order[f["verdict"]], str(f["decision_id"])))
    return findings


def verify(change, target_dir="."):
    """Check a proposed change against the ledger visible from this directory."""
    from coresentinel_core.decisions import ledger

    decisions = ledger.load(target_dir)
    findings = check(change, decisions)
    blocking = [f for f in findings if f["blocking"]]

    return {
        "coresentinel_api": "1.1",
        "change": change,
        "considered": len([d for d in decisions if schema.is_binding(d)]),
        "findings": findings,
        "blocking": len(blocking),
        "verdict": "REVIEW REQUIRED" if blocking else ("RELATED" if findings else "CLEAR"),
    }
