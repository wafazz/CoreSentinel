#!/usr/bin/env python3
"""
CoreSentinel Specialist Squad Contract Engine
Inspects, validates, and orchestrates explicit Agent Contracts for all 17 specialists.
"""

import os
import sys
import json
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
CONTRACTS_FILE = SCRIPT_DIR / "squad-contracts.json"

def load_contracts():
    if not CONTRACTS_FILE.exists():
        print(f"[!] Squad contracts file missing: {CONTRACTS_FILE}")
        return []
    try:
        with open(CONTRACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("squad", [])
    except Exception as e:
        print(f"[!] Error reading squad contracts: {e}")
        return []

def list_squad():
    squad = load_contracts()
    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel 17-Specialist Squad Agent Contracts")
    print("=" * 64)
    print(f"  Total Active Specialist Contracts: {len(squad)}\n")
    print("  " + "-" * 60)

    for idx, agent in enumerate(squad, 1):
        inputs = ", ".join(agent.get("input_contract", []))
        outputs = ", ".join(agent.get("output_contract", []))
        print(f"  {idx:02d}. [{agent['name']:<12}] Role: {agent['role']}")
        print(f"      Input Contract  : {inputs}")
        print(f"      Output Contract : {outputs}")
        print(f"      Authority       : {agent['authority']}")
        print("  " + "-" * 60)

    print("\n  Use: coresentinel squad show <AgentName> for full contract details.\n" + "=" * 64 + "\n")

def show_agent_contract(agent_name):
    squad = load_contracts()
    matched = [a for a in squad if a["name"].lower() == agent_name.lower()]
    if not matched:
        print(f"\n[!] Specialist agent '{agent_name}' not found in squad contracts.")
        print(f"    Available agents: {', '.join([a['name'] for a in squad])}\n")
        return False

    agent = matched[0]
    print("\n" + "=" * 64)
    print(f"  🛡️  Agent Contract Specification: {agent['name'].upper()}")
    print("=" * 64)
    print(f"  Agent Name        : {agent['name']}")
    print(f"  Specialist Role   : {agent['role']}")
    print(f"  Authority Level   : {agent['authority']}")
    print("-" * 64)

    print("\n  🧠 Capabilities:")
    for cap in agent.get("capability", []):
        print(f"     • {cap}")

    print("\n  📥 Input Contract (Required Inputs):")
    for inp in agent.get("input_contract", []):
        print(f"     ➔ {inp}")

    print("\n  📤 Output Contract (Generated Artifacts):")
    for out in agent.get("output_contract", []):
        print(f"     ➔ {out}")

    print("\n  ⛔ Constraints & Guardrails:")
    for con in agent.get("constraints", []):
        print(f"     ! {con}")

    print("\n  ✓ Verification Gate Requirements:")
    for v in agent.get("verification_gate", []):
        print(f"     [✓] {v}")

    print("\n" + "=" * 64 + "\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        if len(sys.argv) > 2:
            show_agent_contract(sys.argv[2])
        else:
            list_squad()
    else:
        list_squad()
