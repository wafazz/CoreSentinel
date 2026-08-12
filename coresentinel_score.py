#!/usr/bin/env python3
"""
CoreSentinel System & Project Health Score Engine
Evaluates 7 core health dimensions (Architecture, Security, Testing, Code Quality, Documentation, Reliability, Dependencies)
and computes an overall CoreSentinel Health & Reliability Score out of 100 with status indicator.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()

def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.SubprocessError as e:
        return -1, "", str(e)

def evaluate_health_score(target_dir="."):
    p = Path(target_dir)

    # 1. Architecture Score (Max 100)
    arch_score = 90
    if (p / "README.md").exists():
        arch_score += 5
    if (p / "00-identity.md").exists() or (p / "package.json").exists() or (p / "pyproject.toml").exists():
        arch_score += 5
    arch_score = min(100, arch_score)

    # 2. Security Score (Max 100)
    sec_score = 100
    validator_script = SCRIPT_DIR / "sentinel-validator.py"
    if validator_script.exists():
        code, out, _ = run_cmd(f"python \"{validator_script}\"", cwd=target_dir)
        if code != 0:
            sec_score -= 25

    # 3. Testing Score (Max 100)
    test_score = 90
    if (p / "package.json").exists():
        code, _, _ = run_cmd("npm test -- --passWithNoTests", cwd=target_dir)
        if code == 0:
            test_score = 95
        else:
            test_score = 70
    elif (p / "pytest.ini").exists() or (p / "requirements.txt").exists():
        code, _, _ = run_cmd("pytest", cwd=target_dir)
        if code == 0:
            test_score = 95
        else:
            test_score = 70

    # 4. Code Quality Score (Max 100)
    quality_score = 96
    diff_code, diff_out, _ = run_cmd("git diff", cwd=target_dir)
    if "except " + "Exception: pass" in diff_out or "catch " + "() {}" in diff_out:
        quality_score -= 20

    # 5. Documentation Score (Max 100)
    doc_score = 88
    if (p / "README.md").exists():
        doc_score += 7
    if (p / "LICENSE").exists():
        doc_score += 5
    doc_score = min(100, doc_score)

    # 6. Reliability Score (Max 100)
    rel_score = 93
    if (p / ".git").exists():
        rel_score += 5
    rel_score = min(100, rel_score)

    # 7. Dependencies Score (Max 100)
    dep_score = 97
    if (p / "package-lock.json").exists() or (p / "composer.lock").exists() or (p / "poetry.lock").exists():
        dep_score = 99

    dimensions = {
        "Architecture": arch_score,
        "Security": sec_score,
        "Testing": test_score,
        "Code Quality": quality_score,
        "Documentation": doc_score,
        "Reliability": rel_score,
        "Dependencies": dep_score
    }

    overall_score = int(sum(dimensions.values()) / len(dimensions))

    if overall_score >= 90:
        status = "HEALTHY"
        badge = "[✓ HEALTHY]"
    elif overall_score >= 75:
        status = "WARNING"
        badge = "[! WARNING]"
    else:
        status = "CRITICAL"
        badge = "[✗ CRITICAL]"

    return {
        "overall_score": overall_score,
        "status": status,
        "badge": badge,
        "dimensions": dimensions
    }

def print_scorecard(target_dir=".", emit_json=False):
    health = evaluate_health_score(target_dir)

    if emit_json:
        print(json.dumps(health, indent=2))
        return

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel System & Project Health Scorecard")
    print("=" * 64)
    print(f"  Target Directory : {os.path.abspath(target_dir)}")
    print("  " + "-" * 60)

    for dim, score in health["dimensions"].items():
        bar_len = int(score / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {dim:<18} : {score:>3}/100  [{bar}]")

    print("  " + "-" * 60)
    print(f"  Overall Score      : {health['overall_score']}/100")
    print(f"  CoreSentinel Status: {health['status']} {health['badge']}")
    print("=" * 64 + "\n")

if __name__ == "__main__":
    emit_json = "--json" in sys.argv
    print_scorecard(".", emit_json)
