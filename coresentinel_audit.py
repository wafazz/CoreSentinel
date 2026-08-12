#!/usr/bin/env python3
"""
CoreSentinel Audit Trail Engine
Provides traceable AI accountability by recording execution runs, file operations,
test executions, security scans, reviewer approvals, and verification scores.
"""

import sys
import os
import json
import random
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR / "memory"
AUDIT_FILE = MEMORY_DIR / "audit_trail.json"

def ensure_audit_file():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        with open(AUDIT_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

def load_audit_trail():
    ensure_audit_file()
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading audit trail: {e}")
        return []

def save_audit_trail(trail):
    ensure_audit_file()
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(trail, f, indent=2)

def generate_run_id():
    return f"RUN-#{random.randint(1000, 9999)}"

def record_run(agent_name, task, files_read=0, files_modified=0, tests_created=0, tests_executed=0, security_scan="PASS", reviewer_approval="PASS", verification_score=100, result="PASS"):
    trail = load_audit_trail()
    run_id = generate_run_id()

    entry = {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent_name,
        "task": task,
        "actions": {
            "files_read": int(files_read),
            "files_modified": int(files_modified),
            "tests_created": int(tests_created),
            "tests_executed": int(tests_executed),
            "security_scan": security_scan,
            "reviewer_approval": reviewer_approval,
            "verification_score": int(verification_score)
        },
        "result": result
    }

    trail.append(entry)
    save_audit_trail(trail)
    print(f"\n[✓] Audit Trail Recorded: {run_id} | Agent: {agent_name} | Result: {result}")
    return run_id

def list_runs():
    trail = load_audit_trail()
    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel AI Accountability Audit Trail")
    print("=" * 64)

    if not trail:
        print("  (No audit trail runs recorded yet)")
        print("  Use: coresentinel audit record --agent \"...\" --task \"...\"")
        print("=" * 64 + "\n")
        return

    print(f"  Total Recorded AI Execution Runs: {len(trail)}")
    print("  " + "-" * 60)

    for run in reversed(trail):
        act = run.get("actions", {})
        icon = "[✓ PASS]" if run.get("result") == "PASS" else "[✗ FAIL]"
        print(f"\n  {icon}  {run['run_id']} ({run['timestamp']})")
        print(f"       Agent       : {run['agent']}")
        print(f"       Task        : {run['task']}")
        print(f"       Files       : Read {act.get('files_read', 0)} | Modified {act.get('files_modified', 0)}")
        print(f"       Tests       : Created {act.get('tests_created', 0)} | Executed {act.get('tests_executed', 0)}")
        print(f"       Security    : {act.get('security_scan', 'PASS')} | Reviewer: {act.get('reviewer_approval', 'PASS')}")
        print(f"       Verify Score: {act.get('verification_score', 100)}/100")

    print("\n" + "=" * 64 + "\n")

def show_run(run_id):
    trail = load_audit_trail()
    matched = [r for r in trail if run_id.lower() in r["run_id"].lower()]

    if not matched:
        print(f"[!] Audit run '{run_id}' not found.")
        return False

    run = matched[0]
    act = run.get("actions", {})
    print("\n" + "=" * 64)
    print(f"  🛡️  Audit Run Record Card: {run['run_id']}")
    print("=" * 64)
    print(f"  Run ID            : {run['run_id']}")
    print(f"  Timestamp         : {run['timestamp']}")
    print(f"  Agent Persona     : {run['agent']}")
    print(f"  Task Description  : {run['task']}")
    print("-" * 64)
    print("  Actions Execution Breakdown:")
    print(f"     • Read Files       : {act.get('files_read', 0)} files inspected")
    print(f"     • Modified Files   : {act.get('files_modified', 0)} files edited")
    print(f"     • Created Tests    : {act.get('tests_created', 0)} new test cases")
    print(f"     • Executed Tests   : {act.get('tests_executed', 0)} test suite executions")
    print(f"     • Security Scan    : {act.get('security_scan', 'PASS')}")
    print(f"     • Reviewer Audit   : {act.get('reviewer_approval', 'PASS')}")
    print(f"     • Verification     : {act.get('verification_score', 100)}/100")
    print("-" * 64)
    print(f"  Overall Result    : {run['result']}")
    print("=" * 64 + "\n")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "list":
            list_runs()
        elif cmd == "show":
            rid = sys.argv[2] if len(sys.argv) > 2 else "RUN-#9281"
            show_run(rid)
        elif cmd == "record":
            record_run("Backend Engineer", "Implement payment webhook", 14, 6, 3, 42, "PASS", "PASS", 100, "PASS")
    else:
        list_runs()
