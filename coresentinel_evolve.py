#!/usr/bin/env python3
"""
CoreSentinel Controlled Self-Evolution (CSE) Engine
Enforces structured, versioned, evidence-backed evolution proposals for AI rule/protocol changes.
Prevents unauthorized autonomous rule/governance mutations.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR / "memory"
EVOLUTION_FILE = MEMORY_DIR / "evolution_proposals.json"

def ensure_evolution_file():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not EVOLUTION_FILE.exists():
        with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

def load_proposals():
    ensure_evolution_file()
    try:
        with open(EVOLUTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading evolution proposals: {e}")
        return []

def save_proposals(proposals):
    ensure_evolution_file()
    with open(EVOLUTION_FILE, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2)

def generate_evo_id(existing_proposals=None):
    """Sequential and collision-free — a duplicate id would make approvals ambiguous."""
    used = {p.get("id") for p in (existing_proposals or [])}
    number = len(used) + 1
    while f"EVO-{number:03d}" in used:
        number += 1
    return f"EVO-{number:03d}"

def propose_evolution(target_protocol, change_description, evidence, impact_analysis="Low risk; non-breaking rule addition"):
    proposals = load_proposals()
    evo_id = generate_evo_id(proposals)

    entry = {
        "id": evo_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_protocol": target_protocol,
        "proposed_change": change_description,
        "evidence": evidence,
        "impact_analysis": impact_analysis,
        "review_status": "PENDING_REVIEW",
        "approver": None,
        "version": f"1.{len(proposals) + 1}.0"
    }

    proposals.append(entry)
    save_proposals(proposals)
    print(f"\n[✓] Controlled Evolution Proposal Registered: [{evo_id}] -> Status: PENDING_REVIEW")
    print(f"    Target Protocol : {target_protocol}")
    print(f"    Proposed Change : {change_description}")
    print(f"    Evidence        : {evidence}")
    return evo_id

def list_proposals():
    proposals = load_proposals()
    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Controlled Self-Evolution (CSE) Proposals")
    print("=" * 64)

    if not proposals:
        print("  (No evolution proposals registered)")
        print("  Use: coresentinel evolve propose --target \"...\" --change \"...\" --evidence \"...\"")
        print("=" * 64 + "\n")
        return

    print(f"  Total Evolution Proposals: {len(proposals)}")
    print("  " + "-" * 60)

    for p in reversed(proposals):
        status = p.get("review_status", "PENDING_REVIEW")
        icon = "[✓ APPROVED]" if status == "APPROVED" else ("[! PENDING]" if status == "PENDING_REVIEW" else "[✗ REJECTED]")
        print(f"\n  {icon} [{p['id']}] Target: {p['target_protocol']} (v{p.get('version', '1.0.0')})")
        print(f"       Change          : {p['proposed_change']}")
        print(f"       Evidence        : {p['evidence']}")
        print(f"       Impact Analysis : {p.get('impact_analysis', 'N/A')}")
        print(f"       Review Status   : {status} (Approver: {p.get('approver') or 'Pending'})")

    print("\n" + "=" * 64 + "\n")

def approve_proposal(evo_id, approver="Fakrul"):
    proposals = load_proposals()
    matched = [p for p in proposals if p["id"].lower() == evo_id.lower()]

    if not matched:
        print(f"[!] Proposal '{evo_id}' not found.")
        return False

    proposal = matched[0]
    proposal["review_status"] = "APPROVED"
    proposal["approver"] = approver
    proposal["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_proposals(proposals)
    print(f"\n[✓] Evolution Proposal [{proposal['id']}] APPROVED by {approver}!")
    print(f"    Versioned Change Released: {proposal['target_protocol']} v{proposal['version']}")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "list":
            list_proposals()
        elif cmd == "propose":
            target = "anti-patterns.json"
            change = "Add rule enforcement check"
            evidence = "Incident empirical evidence"
            impact = "Low risk"
            if "--target" in sys.argv:
                target = sys.argv[sys.argv.index("--target") + 1]
            if "--change" in sys.argv:
                change = sys.argv[sys.argv.index("--change") + 1]
            if "--evidence" in sys.argv:
                evidence = sys.argv[sys.argv.index("--evidence") + 1]
            if "--impact" in sys.argv:
                impact = sys.argv[sys.argv.index("--impact") + 1]
            propose_evolution(target, change, evidence, impact)
        elif cmd == "approve":
            eid = sys.argv[2] if len(sys.argv) > 2 else "EVO-001"
            app = sys.argv[3] if len(sys.argv) > 3 else "Fakrul"
            approve_proposal(eid, app)
    else:
        list_proposals()
