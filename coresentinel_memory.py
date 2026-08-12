#!/usr/bin/env python3
"""
CoreSentinel Layered Memory Engine & Decision Ledger
Manages 6 memory layers with confidence classification (Known / Assumed / Unknown)
and provides an Architecture Decision Record (ADR) Ledger.
"""

import os
import sys
import json
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

def add_fact(layer_name, fact, confidence, source, target_dir="."):
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

    entry = {
        "fact": fact,
        "confidence": float(confidence),
        "classification": classify_confidence(float(confidence)),
        "source": source,
        "last_verified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
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
