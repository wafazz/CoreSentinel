#!/usr/bin/env python3
"""
CoreSentinel Layered Memory Engine & Decision Ledger
Manages 6 memory layers with confidence classification (Known / Assumed / Unknown)
and provides an Architecture Decision Record (ADR) Ledger.
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR / "memory"

MEMORY_LAYERS = {
    "working": MEMORY_DIR / "working.json",
    "session": MEMORY_DIR / "session.json",
    "project": MEMORY_DIR / "project.json",
    "longterm": MEMORY_DIR / "longterm.json",
    "failures": MEMORY_DIR / "failures.json",
    "patterns": MEMORY_DIR / "patterns.json",
    "decisions": MEMORY_DIR / "decisions.json"
}

# Layers describing *this* codebase and *this* task belong to the project, not to the
# shared Core. Without this split, running init across ten repositories piles ten
# projects' facts into one global layer.
PROJECT_SCOPED_LAYERS = {"working", "session", "project"}
CONFIG_DIRNAME = ".coresentinel"

# Layers that hold confidence-scored facts. 'decisions' is an append-only ledger with a
# different shape, so every fact-walking engine iterates this list instead of MEMORY_LAYERS.
FACT_LAYERS = ["working", "session", "project", "longterm", "failures", "patterns"]

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

def find_project_root(start_dir="."):
    """Walk up for a CoreSentinel-bound project, the way git looks for .git."""
    try:
        current = Path(start_dir).resolve()
    except OSError:
        return None
    for candidate in [current, *current.parents]:
        if (candidate / CONFIG_DIRNAME / "config.json").exists():
            return candidate
    return None

def layer_path(layer_name, target_dir="."):
    """Resolve a layer to the project store when bound, else to the Core store."""
    if layer_name in PROJECT_SCOPED_LAYERS:
        root = find_project_root(target_dir)
        if root:
            return root / CONFIG_DIRNAME / "memory" / f"{layer_name}.json"
    return MEMORY_LAYERS[layer_name]

def layer_scope(layer_name, target_dir="."):
    """'project' when the layer resolves into a bound project, otherwise 'core'."""
    if layer_name in PROJECT_SCOPED_LAYERS and find_project_root(target_dir):
        return "project"
    return "core"

def memory_root(target_dir="."):
    """The memory store this directory writes to: the bound project's, else the Core's.

    Journals and snapshots follow the same rule as project-scoped layers — work done on a
    repository belongs to that repository, not to whichever Core happened to be driving it.
    """
    root = find_project_root(target_dir)
    return root / CONFIG_DIRNAME / "memory" if root else MEMORY_DIR


def fact_id(text):
    """A stable identifier derived from the fact itself, so the same fact recorded twice
    in two layers is recognisably the same fact to the consolidator."""
    digest = hashlib.sha1(normalize_fact(text).encode("utf-8")).hexdigest()
    return f"MEM-{digest[:10]}"


def normalize_fact(text):
    """Case- and whitespace-insensitive form used for duplicate detection only."""
    return " ".join(str(text or "").lower().split()).rstrip(".")


def parse_timestamp(value):
    """Read any timestamp CoreSentinel has ever written. Returns None if unparseable —
    callers treat that as 'age unknown' rather than guessing a date."""
    if not value:
        return None
    for fmt in (TIMESTAMP_FORMAT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except (TypeError, ValueError):
            continue
    return None


def age_in_days(value, now=None):
    """Days since a timestamp, or None when the timestamp cannot be read."""
    stamp = parse_timestamp(value)
    if stamp is None:
        return None
    delta = (now or datetime.now()) - stamp
    return max(0.0, delta.total_seconds() / 86400.0)


def load_layer(layer_name, target_dir="."):
    """Read a layer as (data, error). A corrupt file yields (None, reason) — never a
    silent empty layer, which would let a caller overwrite recorded facts with nothing."""
    path = layer_path(layer_name, target_dir)
    if not path.exists():
        return default_layer_content(layer_name), None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return None, str(e)


def save_layer(layer_name, data, target_dir="."):
    """Write a layer wherever it resolves. Returns the path written."""
    path = ensure_layer(layer_name, target_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def layer_facts(layer_name, target_dir="."):
    """Facts in one layer, or [] when the layer is absent or unreadable."""
    data, error = load_layer(layer_name, target_dir)
    if error or not isinstance(data, dict):
        return []
    facts = data.get("facts", [])
    return facts if isinstance(facts, list) else []


def default_layer_content(layer_name):
    if layer_name == "decisions":
        return []
    if layer_name == "working":
        return {"current_task": "Idle", "status": "Ready"}
    return {"facts": []}

def ensure_layer(layer_name, target_dir="."):
    """Create a single layer file wherever it resolves. Returns its path."""
    path = layer_path(layer_name, target_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_layer_content(layer_name), f, indent=2)
    return path

def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    for layer, path in MEMORY_LAYERS.items():
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_layer_content(layer), f, indent=2)

def classify_confidence(score):
    if score >= 0.90:
        return "Known (Empirically Verified)"
    elif score >= 0.50:
        return "Assumed (Requires Verification)"
    else:
        return "Unknown (Unverified)"

def add_fact(layer_name, fact, confidence, source, target_dir=".",
             pinned=False, transferable=False):
    if layer_name not in MEMORY_LAYERS or layer_name == "decisions":
        print(f"[!] Invalid layer '{layer_name}'. Valid layers: working, session, project, longterm, failures, patterns", file=sys.stderr)
        return False

    file_path = ensure_layer(layer_name, target_dir)
    scope = layer_scope(layer_name, target_dir)
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[!] Refusing to write: {file_path} is unreadable ({e}).", file=sys.stderr)
        print("    Repair or remove the file first — overwriting it would destroy the recorded facts.",
              file=sys.stderr)
        return False

    if "facts" not in data:
        data["facts"] = []

    now = datetime.now().strftime(TIMESTAMP_FORMAT)
    entry = {
        "id": fact_id(fact),
        "fact": fact,
        "confidence": float(confidence),
        "classification": classify_confidence(float(confidence)),
        "source": source,
        "created_at": now,
        "last_verified": now
    }
    # Only recorded when set, so an ordinary fact keeps the schema it has always had.
    if pinned:
        entry["pinned"] = True          # exempt from confidence decay
    if transferable:
        entry["transferable"] = True    # eligible to leave project scope for the Core
    data["facts"].append(entry)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    scope_note = f"project scope: {find_project_root(target_dir)}" if scope == "project" else "core scope"
    print(f"[✓] Added fact to [{layer_name.upper()} MEMORY] ({scope_note}): '{fact}' (Confidence: {confidence} - {entry['classification']})")
    return True

def show_memory_summary(target_dir="."):
    ensure_memory_dir()
    project_root = find_project_root(target_dir)

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Layered Memory Engine & Confidence Index")
    print("=" * 64)
    if project_root:
        print(f"  Bound Project : {project_root}")
        print(f"  Core Store    : {MEMORY_DIR}")
    else:
        print(f"  Core Store    : {MEMORY_DIR}")
        print("  Bound Project : (none — run 'coresentinel init' to scope project memory)")

    for layer in MEMORY_LAYERS:
        if layer == "decisions":
            continue
        path = layer_path(layer, target_dir)
        scope = layer_scope(layer, target_dir)
        print(f"\n  🧠 [{layer.upper()} MEMORY] ({path.name}) — {scope} scope")
        print("  " + "-" * 56)
        if not path.exists():
            print("     (Empty)")
            continue
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = json.load(f)
        except (OSError, json.JSONDecodeError, ValueError) as e:
            print(f"     (Error reading file: {e})")
            continue

        facts = content.get("facts", [])
        if not facts:
            if layer == "working":
                print(f"     Task   : {content.get('current_task', 'None')}")
                print(f"     Status : {content.get('status', 'Idle')}")
            else:
                print("     (No recorded facts)")
            continue

        for item in facts:
            status = classify_confidence(item.get("confidence", 0.5))
            print(f"     • Fact       : {item.get('fact')}")
            print(f"       Confidence : {item.get('confidence')} [{status}]")
            print(f"       Source     : {item.get('source')}")
            print(f"       Verified   : {item.get('last_verified')}")

    print("\n" + "=" * 64 + "\n")

# Decision Ledger Engine
def add_decision(title, reason, chosen, alternatives=None, impact="High", status="Accepted"):
    ensure_memory_dir()
    file_path = MEMORY_LAYERS["decisions"]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            decisions = json.load(f)
    except Exception:
        decisions = []

    decision_id = f"ADR-{len(decisions) + 1:03d}"
    alt_list = [a.strip() for a in alternatives.split(",")] if isinstance(alternatives, str) else (alternatives or [])

    entry = {
        "id": decision_id,
        "decision": title,
        "reason": reason,
        "alternatives": alt_list,
        "chosen": chosen,
        "impact": impact,
        "status": status,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    decisions.append(entry)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2)

    print(f"\n[✓] Registered Decision [{decision_id}]: '{title}' -> Chosen: '{chosen}'")
    return decision_id

def list_decisions(query=None):
    ensure_memory_dir()
    file_path = MEMORY_LAYERS["decisions"]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            decisions = json.load(f)
    except Exception:
        decisions = []

    print("\n" + "=" * 64)
    print("  📜 CoreSentinel Architecture Decision Ledger (ADR)")
    print("=" * 64)

    if not decisions:
        print("  (No architecture decisions recorded yet)")
        print("  Use: coresentinel decision add --title \"...\" --reason \"...\" --chosen \"...\"")
        print("=" * 64 + "\n")
        return

    filtered = decisions
    if query:
        q = query.lower()
        filtered = [d for d in decisions if q in d["decision"].lower() or q in d["reason"].lower() or q in d["chosen"].lower()]

    print(f"  Showing {len(filtered)} / {len(decisions)} Architecture Decisions:")
    print("  " + "-" * 56)

    for d in filtered:
        alts = ", ".join(d.get("alternatives", [])) if d.get("alternatives") else "None"
        print(f"\n  [{d['id']}] {d['decision']}")
        print(f"     Reason       : {d['reason']}")
        print(f"     Chosen       : {d['chosen']}")
        print(f"     Alternatives : {alts}")
        print(f"     Impact       : {d.get('impact', 'High')} | Status: {d.get('status', 'Accepted')}")
        print(f"     Recorded     : {d['created_at']}")

    print("\n" + "=" * 64 + "\n")

if __name__ == "__main__":
    ensure_memory_dir()
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_memory_summary()
    elif len(sys.argv) > 1 and sys.argv[1] == "decisions":
        list_decisions()
