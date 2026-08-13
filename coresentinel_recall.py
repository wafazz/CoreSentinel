#!/usr/bin/env python3
"""
CoreSentinel Recall Engine & Session Briefing

Retrieval side of the memory ecosystem. Storing facts is worthless if nothing can find
them again, so this module answers the two questions an agent actually asks:

  "What do I already know about X?"   -> recall  (ranked search across every layer)
  "Where did we leave off?"           -> brief   (session-start context pack)

It also owns the session journal: the narrative record of what was done and why, which
the layered fact store deliberately does not keep.
"""

import re
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import coresentinel_memory as mem

# A fact recorded but never re-verified is a liability, not an asset. Past this age the
# briefing lists it for re-verification rather than presenting it as current truth.
STALE_AFTER_DAYS = 30

# Recall ranks on term coverage, then weights by confidence. The weight floor keeps a
# low-confidence fact findable — an Unknown fact you can see is safer than one you cannot.
CONFIDENCE_WEIGHT_FLOOR = 0.5
PHRASE_BONUS = 0.25

# Records of what happened carry no confidence score; they are not claims about the code.
JOURNAL_WEIGHT = 0.90
DECISION_WEIGHT = 1.00

TOKEN_PATTERN = re.compile(r"[a-z0-9_.\-/]+")
STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on",
              "for", "and", "or", "we", "it", "that", "this", "with", "do", "does"}


# ---------------------------------------------------------------- journal storage

def journal_dir(target_dir="."):
    return mem.memory_root(target_dir) / "journal"


def journal_path(day, target_dir="."):
    return journal_dir(target_dir) / f"{day}.json"


def archive_path(month, target_dir="."):
    return journal_dir(target_dir) / "archive" / f"{month}.json"


def _read_json(path, fallback):
    if not Path(path).exists():
        return fallback, None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return None, str(e)


def _write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return Path(path)


def add_journal_entry(entry, tags=None, agent="Iris", target_dir=".", now=None):
    """Append one narrative entry to today's journal. Returns the path written."""
    now = now or datetime.now()
    day = now.strftime("%Y-%m-%d")
    path = journal_path(day, target_dir)

    data, error = _read_json(path, {"date": day, "entries": []})
    if error:
        print(f"[!] Refusing to write: {path} is unreadable ({error}).", file=sys.stderr)
        print("    Repair or remove the file first — overwriting it would destroy the log.",
              file=sys.stderr)
        return None

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if isinstance(tags, str) else list(tags or [])
    data.setdefault("entries", []).append({
        "time": now.strftime(mem.TIMESTAMP_FORMAT),
        "entry": entry,
        "tags": tag_list,
        "agent": agent,
    })
    _write_json(path, data)

    scope = "project" if mem.find_project_root(target_dir) else "core"
    print(f"[✓] Journal entry recorded for {day} ({scope} scope): '{entry}'")
    return path


def read_journal(target_dir=".", days=None, include_archive=True):
    """Every journal entry, newest day first. `days` limits how far back to read."""
    directory = journal_dir(target_dir)
    collected = []
    cutoff = (datetime.now() - timedelta(days=days)).date() if days else None

    if directory.exists():
        for path in sorted(directory.glob("*.json"), reverse=True):
            day = path.stem
            stamp = mem.parse_timestamp(day)
            if cutoff and stamp and stamp.date() < cutoff:
                continue
            data, error = _read_json(path, None)
            if error or not isinstance(data, dict):
                continue
            for item in data.get("entries", []):
                collected.append({**item, "date": day, "archived": False})

    archive = directory / "archive"
    if include_archive and archive.exists():
        for path in sorted(archive.glob("*.json"), reverse=True):
            data, error = _read_json(path, None)
            if error or not isinstance(data, dict):
                continue
            for day, entries in sorted(data.get("days", {}).items(), reverse=True):
                stamp = mem.parse_timestamp(day)
                if cutoff and stamp and stamp.date() < cutoff:
                    continue
                for item in entries:
                    collected.append({**item, "date": day, "archived": True})

    collected.sort(key=lambda e: (e.get("date", ""), e.get("time", "")), reverse=True)
    return collected


def archive_journal(older_than_days=30, target_dir=".", apply_changes=False, now=None):
    """Fold day files older than the window into one file per month.

    Archived entries stay searchable — this compresses the file count, it does not
    discard history.
    """
    now = now or datetime.now()
    cutoff = (now - timedelta(days=older_than_days)).date()
    directory = journal_dir(target_dir)
    moved = []

    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            stamp = mem.parse_timestamp(path.stem)
            if stamp is None or stamp.date() >= cutoff:
                continue
            data, error = _read_json(path, None)
            if error or not isinstance(data, dict):
                continue
            entries = data.get("entries", [])
            moved.append({"date": path.stem, "entries": len(entries), "month": path.stem[:7]})

            if apply_changes:
                target = archive_path(path.stem[:7], target_dir)
                bundle, bundle_error = _read_json(target, {"month": path.stem[:7], "days": {}})
                if bundle_error:
                    print(f"[!] Skipping {path.stem}: archive {target} unreadable ({bundle_error}).",
                          file=sys.stderr)
                    moved.pop()
                    continue
                bundle.setdefault("days", {})[path.stem] = entries
                _write_json(target, bundle)
                path.unlink()

    return {"cutoff": cutoff.isoformat(), "archived_days": moved, "applied": bool(apply_changes)}


# ---------------------------------------------------------------- recall

def read_decisions(target_dir="."):
    """The decision ledger visible from this directory.

    Decisions became project-scoped in Phase 3. Reading the Core file directly,
    as this module used to, meant recall and the session briefing silently
    omitted every decision made about the project actually being worked on.
    """
    try:
        from coresentinel_core.decisions import ledger
    except ImportError:
        data, error = _read_json(mem.MEMORY_LAYERS["decisions"], [])
        return data if not error and isinstance(data, list) else []
    return ledger.load(target_dir)


def tokenize(text):
    return [t for t in TOKEN_PATTERN.findall(str(text or "").lower())
            if len(t) > 1 and t not in STOP_WORDS]


def score_record(query_terms, phrase, haystack, weight):
    """Term coverage, bonused for an exact phrase hit, weighted by confidence.

    Returns (score, matched_terms). A score of 0 means the record does not match.
    """
    if not query_terms:
        return weight, []

    hay = str(haystack or "").lower()
    hay_terms = set(tokenize(hay))
    matched = [t for t in query_terms if t in hay_terms or t in hay]
    if not matched:
        return 0.0, []

    coverage = len(matched) / len(query_terms)
    bonus = PHRASE_BONUS if phrase and phrase in hay else 0.0
    scale = CONFIDENCE_WEIGHT_FLOOR + (1 - CONFIDENCE_WEIGHT_FLOOR) * max(0.0, min(1.0, weight))
    return round((coverage + bonus) * scale, 4), matched


def recall(query, target_dir=".", layers=None, min_confidence=0.0,
           include_journal=True, include_decisions=True, limit=20):
    """Rank everything the memory ecosystem holds against a query.

    Searches fact layers, the decision ledger and the session journal in one pass, so a
    question never has to be asked three times in three different commands.
    """
    terms = tokenize(query)
    phrase = " ".join(str(query or "").lower().split())
    wanted = [l for l in (layers or mem.FACT_LAYERS) if l in mem.FACT_LAYERS]
    results = []

    for layer in wanted:
        scope = mem.layer_scope(layer, target_dir)
        for item in mem.layer_facts(layer, target_dir):
            confidence = item.get("confidence")
            confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.5
            if confidence < min_confidence:
                continue
            haystack = f"{item.get('fact', '')} {item.get('source', '')} {layer}"
            score, matched = score_record(terms, phrase, haystack, confidence)
            if score <= 0:
                continue
            results.append({
                "kind": "fact",
                "layer": layer,
                "scope": scope,
                "text": item.get("fact"),
                "confidence": confidence,
                "classification": item.get("classification") or mem.classify_confidence(confidence),
                "source": item.get("source"),
                "when": item.get("last_verified"),
                "matched": matched,
                "score": score,
            })

    if include_decisions:
        for entry in read_decisions(target_dir):
            haystack = " ".join(str(entry.get(k, "")) for k in ("decision", "reason", "chosen"))
            haystack += " " + " ".join(entry.get("alternatives", []) or [])
            score, matched = score_record(terms, phrase, haystack, DECISION_WEIGHT)
            if score <= 0:
                continue
            results.append({
                "kind": "decision",
                "layer": "decisions",
                "scope": entry.get("scope", "core"),
                "text": f"{entry.get('id')}: {entry.get('decision')} -> {entry.get('chosen')}",
                "confidence": None,
                "classification": entry.get("status", "Accepted"),
                "source": entry.get("reason"),
                "when": entry.get("created_at"),
                "matched": matched,
                "score": score,
            })

    if include_journal:
        for entry in read_journal(target_dir):
            haystack = f"{entry.get('entry', '')} {' '.join(entry.get('tags', []) or [])}"
            score, matched = score_record(terms, phrase, haystack, JOURNAL_WEIGHT)
            if score <= 0:
                continue
            results.append({
                "kind": "journal",
                "layer": "journal",
                "scope": "project" if mem.find_project_root(target_dir) else "core",
                "text": entry.get("entry"),
                "confidence": None,
                "classification": ", ".join(entry.get("tags", []) or []) or "note",
                "source": entry.get("agent"),
                "when": entry.get("time") or entry.get("date"),
                "matched": matched,
                "score": score,
            })

    results.sort(key=lambda r: (r["score"], r.get("when") or ""), reverse=True)
    return results[:limit] if limit else results


def print_recall(query, target_dir=".", layers=None, min_confidence=0.0,
                 limit=20, emit_json=False):
    hits = recall(query, target_dir, layers, min_confidence, limit=limit)

    if emit_json:
        print(json.dumps({"query": query, "results": hits, "count": len(hits)}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  🔎 CoreSentinel Memory Recall")
    print("=" * 64)
    print(f"  Query : {query or '(everything)'}")
    print(f"  Hits  : {len(hits)}")
    print("  " + "-" * 60)

    if not hits:
        print("  Nothing recorded matches that query.")
        print("  Record it once and it is never re-derived:")
        print("    coresentinel memory add --layer project --fact \"...\" --confidence 0.95 --source \"...\"")
        print("=" * 64 + "\n")
        return 1

    icons = {"fact": "🧠", "decision": "📜", "journal": "📓"}
    for hit in hits:
        confidence = hit["confidence"]
        marker = "✓" if isinstance(confidence, (int, float)) and confidence >= 0.90 else "~"
        print(f"\n  {icons.get(hit['kind'], '•')} [{marker}] {hit['text']}")
        detail = f"{hit['layer']}/{hit['scope']}"
        if isinstance(confidence, (int, float)):
            detail += f" · confidence {confidence} [{hit['classification']}]"
        print(f"      {detail}")
        print(f"      source: {hit['source'] or '-'} · recorded: {hit['when'] or '-'} · score {hit['score']}")

    print("\n" + "=" * 64 + "\n")
    return 0


# ---------------------------------------------------------------- session briefing

def build_briefing(target_dir=".", journal_days=7, now=None):
    """The context an agent needs before its first action of a session."""
    now = now or datetime.now()
    project_root = mem.find_project_root(target_dir)

    working, working_error = mem.load_layer("working", target_dir)
    working = working if isinstance(working, dict) and not working_error else {}

    stale, unverified, high_confidence, open_failures = [], [], [], []
    counts = {}

    for layer in mem.FACT_LAYERS:
        facts = mem.layer_facts(layer, target_dir)
        counts[layer] = len(facts)
        for item in facts:
            confidence = item.get("confidence")
            confidence = float(confidence) if isinstance(confidence, (int, float)) else 0.5
            age = mem.age_in_days(item.get("last_verified"), now)
            record = {
                "layer": layer,
                "fact": item.get("fact"),
                "confidence": confidence,
                "source": item.get("source"),
                "age_days": round(age, 1) if age is not None else None,
            }
            if layer == "failures":
                open_failures.append(record)
            if confidence < 0.50:
                unverified.append(record)
            elif age is not None and age >= STALE_AFTER_DAYS and not item.get("pinned"):
                stale.append(record)
            if confidence >= 0.90 and layer in ("project", "longterm", "patterns"):
                high_confidence.append(record)

    high_confidence.sort(key=lambda r: r["confidence"], reverse=True)
    stale.sort(key=lambda r: r["age_days"] or 0, reverse=True)

    recent_decisions = list(reversed(read_decisions(target_dir)))[:3]

    return {
        "coresentinel_api": "1.0",
        "generated_at": now.strftime(mem.TIMESTAMP_FORMAT),
        "scope": {
            "bound_project": str(project_root) if project_root else None,
            "core_store": str(mem.MEMORY_DIR),
        },
        "working": {
            "current_task": working.get("current_task", "Idle"),
            "status": working.get("status", "Ready"),
        },
        "journal": read_journal(target_dir, days=journal_days)[:8],
        "fact_counts": counts,
        "established": high_confidence[:8],
        "needs_verification": unverified[:8],
        "stale": stale[:8],
        "open_failures": open_failures[:5],
        "recent_decisions": [
            {"id": d.get("id"), "decision": d.get("decision"), "chosen": d.get("chosen")}
            for d in recent_decisions
        ],
    }


def print_briefing(target_dir=".", emit_json=False, journal_days=7):
    brief = build_briefing(target_dir, journal_days)

    if emit_json:
        print(json.dumps(brief, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  🧠 CoreSentinel Session Briefing")
    print("=" * 64)
    print(f"  Generated : {brief['generated_at']}")
    print(f"  Project   : {brief['scope']['bound_project'] or '(unbound — core scope)'}")
    print("  " + "-" * 60)
    print(f"  Last Task : {brief['working']['current_task']}")
    print(f"  Status    : {brief['working']['status']}")

    total = sum(brief["fact_counts"].values())
    layers = ", ".join(f"{k} {v}" for k, v in brief["fact_counts"].items() if v)
    print(f"  Memory    : {total} fact(s) — {layers or 'empty'}")

    def section(title, rows, render):
        print("  " + "-" * 60)
        print(f"  {title}")
        if not rows:
            print("     (none)")
            return
        for row in rows:
            print(f"     {render(row)}")

    section("Recent Activity", brief["journal"],
            lambda e: f"• [{e.get('date')}] {e.get('entry')}")
    section("Established Facts (confidence >= 0.90)", brief["established"],
            lambda f: f"✓ ({f['layer']}) {f['fact']}  · {f['confidence']}")
    section("Needs Verification (Unknown — writes blocked)", brief["needs_verification"],
            lambda f: f"! ({f['layer']}) {f['fact']}  · {f['confidence']}")
    section(f"Stale (unverified for {STALE_AFTER_DAYS}+ days)", brief["stale"],
            lambda f: f"~ ({f['layer']}) {f['fact']}  · {f['age_days']}d old")
    section("Known Failures", brief["open_failures"],
            lambda f: f"✗ {f['fact']}")
    section("Recent Decisions", brief["recent_decisions"],
            lambda d: f"📜 [{d['id']}] {d['decision']} -> {d['chosen']}")

    print("  " + "-" * 60)
    print("  Search everything : coresentinel recall \"<query>\"")
    print("  Re-verify stale   : coresentinel memory decay --apply")
    print("=" * 64 + "\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "brief":
        print_briefing(".", "--json" in sys.argv)
    else:
        print_recall(" ".join(sys.argv[1:]) or "", ".", emit_json="--json" in sys.argv)
