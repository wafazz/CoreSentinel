"""
Task-relevant context assembly.

`coresentinel context` returned every fact in the project, patterns and longterm
layers, unranked and unbounded. On a store of any size that is context bloat —
the failure CoreSentinel is supposed to remove, produced by CoreSentinel.

The ranked retrieval that fixes it already existed: `coresentinel_recall` scores
by term coverage, phrase hit and confidence. Nothing called it. This module does.

The question answered here is not "what do we know?" but **"what does the agent
need to know to do *this*?"** — which means a task, a budget, and an explicit
account of what was left out. A pack that silently truncates is a pack that
teaches the reader to trust it when it should not.
"""

import json
import math
from datetime import datetime
from pathlib import Path

from coresentinel_core import CORE_ROOT

DEFAULT_BUDGET_TOKENS = 4000

# Characters per token. A deliberate approximation: a real tokenizer would mean a
# vendor dependency, and this number is only ever used to decide what fits. It is
# reported as an estimate everywhere it appears, never as a measurement.
CHARS_PER_TOKEN = 4

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# Ordered by what costs most to get wrong. A contradicted decision is a worse
# outcome than a missing journal entry, so decisions are filled first.
# The share is a ceiling on the budget a section may consume, not a reservation;
# whatever a section leaves flows to the next. They deliberately sum above 1.
SECTION_SPECS = [
    ("project", "Project", 0.15),
    ("rules", "Governance rules that apply", 0.15),
    ("decisions", "Decisions already made", 0.35),
    ("failures", "Known failures — do not repeat", 0.20),
    ("facts", "Established facts", 0.35),
    ("patterns", "Reusable patterns", 0.20),
    ("journal", "Recent related work", 0.15),
]

FACT_LAYERS_IN_FACTS = {"project", "longterm", "session", "working"}


def estimate_tokens(text):
    return int(math.ceil(len(str(text or "")) / CHARS_PER_TOKEN))


def _item(text, detail=None, score=0.0, source=None):
    body = text if not detail else f"{text} — {detail}"
    return {"text": text, "detail": detail, "score": round(float(score), 4),
            "source": source, "estimated_tokens": estimate_tokens(body)}


# ---------------------------------------------------------------- sources

def project_items(target_dir):
    """Stack, frameworks and test runner. Always relevant, always cheap."""
    import coresentinel_context as context_engine

    try:
        pack = context_engine.build_project_context(target_dir)
    except Exception:
        return []

    project, git = pack.get("project", {}), pack.get("git", {})
    items = []
    if project.get("stack"):
        items.append(_item(f"Stack: {', '.join(project['stack'])}", source="detected"))
    if project.get("frameworks"):
        items.append(_item(f"Frameworks: {', '.join(project['frameworks'])}", source="manifest"))
    if project.get("test_runner"):
        items.append(_item(f"Test runner: {project['test_runner']}", source="test config"))
    if git.get("branch"):
        items.append(_item(f"Branch {git['branch']}, {git.get('uncommitted', 0)} uncommitted "
                           f"change(s)", source="git"))
    return items


def rule_items(task_terms):
    """Anti-pattern rules whose trigger context matches the task.

    The rules already declare what they apply to; nothing read that field before.
    """
    path = CORE_ROOT / "anti-patterns.json"
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            rules = json.load(f).get("anti_patterns", [])
    except (OSError, json.JSONDecodeError, ValueError):
        return []

    items = []
    for rule in rules:
        contexts = [str(c).lower() for c in rule.get("trigger_context", [])]
        hits = [c for c in contexts if any(term in c or c in term for term in task_terms)]
        blocking = rule.get("enforcement") == "STRICT_BLOCK"
        # A STRICT_BLOCK rule applies whether or not the task mentions its context —
        # it is the floor, not a suggestion.
        if not hits and not blocking:
            continue
        items.append(_item(f"[{rule.get('id')}] {rule.get('rule')}",
                           detail=f"enforcement {rule.get('enforcement')}",
                           score=1.0 if hits else 0.5,
                           source=f"anti-patterns.json ({', '.join(contexts) or 'always'})"))
    items.sort(key=lambda i: i["score"], reverse=True)
    return items


def decision_items(task, target_dir):
    """Relevant ADRs, with any the task appears to contradict lifted to the top."""
    from coresentinel_core.decisions import ledger, contradiction, schema

    decisions = ledger.load(target_dir)
    if not decisions:
        return []

    flagged = {f["decision_id"]: f for f in contradiction.check(task, decisions)}

    items = []
    for record in decisions:
        finding = flagged.get(record.get("id"))
        if not finding and not _matches(task, " ".join(
                str(record.get(k, "")) for k in ("decision", "reason", "chosen", "problem"))):
            continue

        marker = ""
        score = 0.5
        if finding:
            score = {"CONTRADICTS": 1.0, "REVISITS": 0.95, "TOUCHES": 0.7}[finding["verdict"]]
            if finding["blocking"]:
                marker = f"⚠ {finding['verdict']} — "

        detail = record.get("reason")
        if not schema.is_binding(record):
            detail = f"[{record.get('status')}] {detail}"

        items.append(_item(f"{marker}[{record.get('id')}] {record.get('title')} → "
                           f"{record.get('chosen')}",
                           detail=detail, score=score,
                           source=f"{record.get('scope', 'core')} ledger"))
    items.sort(key=lambda i: i["score"], reverse=True)
    return items


def _matches(task, haystack):
    import coresentinel_recall as recall_engine
    score, _ = recall_engine.score_record(recall_engine.tokenize(task),
                                          " ".join(str(task or "").lower().split()),
                                          haystack, 1.0)
    return score > 0


def recall_items(task, target_dir, min_confidence=0.0):
    """Facts, failures, patterns and journal entries, ranked by the recall engine."""
    import coresentinel_recall as recall_engine

    hits = recall_engine.recall(task, target_dir, min_confidence=min_confidence,
                                include_decisions=False, limit=None)

    grouped = {"facts": [], "failures": [], "patterns": [], "journal": []}
    for hit in hits:
        if hit["kind"] == "journal":
            bucket = "journal"
        elif hit["layer"] == "failures":
            bucket = "failures"
        elif hit["layer"] == "patterns":
            bucket = "patterns"
        elif hit["layer"] in FACT_LAYERS_IN_FACTS:
            bucket = "facts"
        else:
            continue

        confidence = hit.get("confidence")
        detail = hit.get("source")
        if isinstance(confidence, (int, float)):
            detail = f"confidence {confidence}" + (f", {detail}" if detail else "")
        grouped[bucket].append(_item(hit["text"], detail=detail, score=hit["score"],
                                     source=f"{hit['layer']}/{hit.get('scope', 'core')}"))
    return grouped


# ---------------------------------------------------------------- assembly

def assemble(task, target_dir=".", budget_tokens=DEFAULT_BUDGET_TOKENS, min_confidence=0.0):
    """Build a bounded, task-relevant context pack.

    Sections are filled in priority order under a shared budget. Anything that
    does not fit is counted and its best candidate named, so the reader knows the
    pack is partial and can raise the budget deliberately.
    """
    import coresentinel_recall as recall_engine

    budget_tokens = max(1, int(budget_tokens))
    task_terms = recall_engine.tokenize(task)

    available = {
        "project": project_items(target_dir),
        "rules": rule_items(task_terms),
        "decisions": decision_items(task, target_dir),
    }
    available.update(recall_items(task, target_dir, min_confidence))

    sections, used, excluded_total, best_excluded = [], 0, 0, None

    for key, title, share in SECTION_SPECS:
        candidates = available.get(key, [])
        section_ceiling = int(budget_tokens * share)
        included, section_used, dropped = [], 0, 0

        for candidate in candidates:
            cost = candidate["estimated_tokens"]
            if section_used + cost > section_ceiling or used + cost > budget_tokens:
                dropped += 1
                if best_excluded is None or candidate["score"] > best_excluded["score"]:
                    best_excluded = {**candidate, "section": key}
                continue
            included.append(candidate)
            section_used += cost
            used += cost

        excluded_total += dropped
        sections.append({"key": key, "title": title, "items": included,
                         "included": len(included), "excluded": dropped,
                         "available": len(candidates), "estimated_tokens": section_used})

    return {
        "coresentinel_api": "1.1",
        "task": task,
        "generated_at": datetime.now().strftime(TIMESTAMP_FORMAT),
        "target": str(Path(target_dir).resolve()),
        "budget_tokens": budget_tokens,
        "estimated_tokens": used,
        "token_estimate_basis": f"characters / {CHARS_PER_TOKEN} — an approximation, "
                                "not a tokenizer measurement",
        "sections": sections,
        "excluded": {
            "total": excluded_total,
            "highest_scoring": best_excluded["text"] if best_excluded else None,
            "section": best_excluded["section"] if best_excluded else None,
        },
    }


def render(pack):
    """The pack as text an agent can be handed directly."""
    lines = []
    lines.append("=" * 64)
    lines.append(f"  CoreSentinel Context Pack — {pack['task']}")
    lines.append("=" * 64)

    for section in pack["sections"]:
        if not section["items"]:
            continue
        lines.append("")
        lines.append(f"## {section['title']}")
        for item in section["items"]:
            lines.append(f"  - {item['text']}")
            if item["detail"]:
                lines.append(f"      {item['detail']}")

    lines.append("")
    lines.append("-" * 64)
    lines.append(f"  ~{pack['estimated_tokens']} of {pack['budget_tokens']} budgeted tokens "
                 f"({pack['token_estimate_basis']})")
    if pack["excluded"]["total"]:
        lines.append(f"  {pack['excluded']['total']} item(s) did not fit. Highest scoring: "
                     f"{pack['excluded']['highest_scoring']}")
        lines.append("  Raise it with: coresentinel context --task \"...\" --budget "
                     f"{pack['budget_tokens'] * 2}")
    lines.append("=" * 64)
    return "\n".join(lines)
