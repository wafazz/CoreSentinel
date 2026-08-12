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

def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    for layer, path in MEMORY_LAYERS.items():
        if not path.exists():
            default_content = [] if layer == "decisions" else {"facts": []} if layer != "working" else {"current_task": "Idle", "status": "Ready"}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=2)

def classify_confidence(score):
    if score >= 0.90:
        return "Known (Empirically Verified)"
    elif score >= 0.50:
        return "Assumed (Requires Verification)"
    else:
        return "Unknown (Unverified)"

def add_fact(layer_name, fact, confidence, source):
    ensure_memory_dir()
    if layer_name not in MEMORY_LAYERS or layer_name == "decisions":
        print(f"[!] Invalid layer '{layer_name}'. Valid layers: working, session, project, longterm, failures, patterns")
        return False

    file_path = MEMORY_LAYERS[layer_name]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"facts": []}

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

    print(f"[✓] Added fact to [{layer_name.upper()} MEMORY]: '{fact}' (Confidence: {confidence} - {entry['classification']})")
    return True

def show_memory_summary():
    ensure_memory_dir()
    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Layered Memory Engine & Confidence Index")
    print("=" * 64)

    for layer, path in MEMORY_LAYERS.items():
        if layer == "decisions":
            continue
        print(f"\n  🧠 [{layer.upper()} MEMORY] ({path.name})")
        print("  " + "-" * 56)
        if not path.exists():
            print("     (Empty)")
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
                facts = content.get("facts", [])
                if not facts:
                    if layer == "working":
                        print(f"     Task   : {content.get('current_task', 'None')}")
                        print(f"     Status : {content.get('status', 'Idle')}")
                    else:
                        print("     (No recorded facts)")
                else:
                    for item in facts:
                        status = classify_confidence(item.get("confidence", 0.5))
                        print(f"     • Fact       : {item.get('fact')}")
                        print(f"       Confidence : {item.get('confidence')} [{status}]")
                        print(f"       Source     : {item.get('source')}")
                        print(f"       Verified   : {item.get('last_verified')}")
        except Exception as e:
            print(f"     (Error reading file: {e})")

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
