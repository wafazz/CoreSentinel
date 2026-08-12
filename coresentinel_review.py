#!/usr/bin/env python3
"""
CoreSentinel Static Review Engine
Runs the mechanical half of 35-review-protocol.md over the working diff: anti-pattern
violations, debug residue, unresolved markers and missing test coverage.

This is a STATIC pass over added lines only. It does not judge logic correctness —
that remains the Cato (correctness) and Sage (maintainability) reviewer contracts.
"""

import os
import re
import sys
import json
import importlib.util
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
VALIDATOR_FILE = SCRIPT_DIR / "sentinel-validator.py"

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".rb", ".go", ".rs", ".java"}
TEST_HINTS = ("test", "spec", "__tests__")

# The scanners hold the patterns as literals — scanning them reports their own rules as violations.
SCANNER_FILES = {"coresentinel_review.py", "sentinel-validator.py"}

DEBUG_RESIDUE = [
    (re.compile(r'\bconsole\.log\s*\('), "console.log left in source"),
    (re.compile(r'\bdebugger\b'), "debugger statement left in source"),
    (re.compile(r'\bvar_dump\s*\(|\bdd\s*\('), "PHP debug dump left in source"),
    (re.compile(r'\bprint\s*\(.*(debug|todo|xxx)', re.I), "debug print left in source"),
]

MARKER_PATTERN = re.compile(r'\b(TODO|FIXME|HACK|XXX)\b')

SEVERITY_ICON = {"BLOCK": "✗", "WARN": "!", "INFO": "·"}


def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=60)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.SubprocessError as e:
        return -1, "", str(e)


def load_validator():
    """Reuse the anti-pattern regexes rather than duplicating them."""
    if not VALIDATOR_FILE.exists():
        print(f"[!] sentinel-validator.py not found — anti-pattern scan skipped", file=sys.stderr)
        return None
    spec = importlib.util.spec_from_file_location("sentinel_validator", VALIDATOR_FILE)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except (ImportError, SyntaxError) as e:
        print(f"[!] sentinel-validator.py failed to load ({e}) — anti-pattern scan skipped", file=sys.stderr)
        return None


def get_changed_files(target_dir="."):
    """Union of staged, unstaged and untracked files — a new file is still a reviewable change."""
    files = []
    for cmd in ("git diff --cached --name-only",
                "git diff --name-only",
                "git ls-files --others --exclude-standard"):
        code, out, _ = run_cmd(cmd, cwd=target_dir)
        if code != 0:
            continue
        for line in out.splitlines():
            name = line.strip()
            if name and name not in files:
                files.append(name)
    return files


def get_added_lines(target_dir="."):
    """Map file -> [(line_number, text)] for ADDED lines only, so pre-existing code is not flagged."""
    code, diff, _ = run_cmd("git diff --cached -U0", cwd=target_dir)
    if code != 0 or not diff:
        code, diff, _ = run_cmd("git diff -U0", cwd=target_dir)
    if code != 0 or not diff:
        return {}

    added = {}
    current_file = None
    line_no = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            added.setdefault(current_file, [])
        elif line.startswith("@@"):
            match = re.search(r'\+(\d+)', line)
            line_no = int(match.group(1)) if match else 0
        elif line.startswith("+") and not line.startswith("+++"):
            if current_file:
                added[current_file].append((line_no, line[1:]))
            line_no += 1
    return added


def get_untracked_lines(target_dir="."):
    """An untracked file has no diff — every one of its lines is an added line."""
    code, out, _ = run_cmd("git ls-files --others --exclude-standard", cwd=target_dir)
    if code != 0 or not out:
        return {}

    added = {}
    for line in out.splitlines():
        name = line.strip()
        if not name or Path(name).suffix not in SOURCE_SUFFIXES:
            continue
        path = Path(target_dir) / name
        try:
            content = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as e:
            print(f"[!] Untracked file {name} unreadable ({e}) — skipped", file=sys.stderr)
            continue
        added[name] = list(enumerate(content.splitlines(), start=1))
    return added


def is_test_path(path):
    lowered = path.lower()
    return any(hint in lowered for hint in TEST_HINTS)


def review_diff(target_dir=".", strict=False):
    findings = []
    changed = get_changed_files(target_dir)

    if not changed:
        return [], [], {"changed": 0, "source": 0, "tests": 0}

    added = get_added_lines(target_dir)
    for name, lines in get_untracked_lines(target_dir).items():
        added.setdefault(name, lines)

    validator = load_validator()
    if validator:
        abs_files = [str(Path(target_dir).resolve() / f) for f in changed]
        for path, desc in validator.check_secrets_and_security(abs_files):
            findings.append({"severity": "BLOCK", "file": os.path.relpath(path, target_dir),
                             "line": None, "rule": "AP-004", "detail": desc})
        for path, desc in validator.check_superficial_patches(abs_files):
            findings.append({"severity": "BLOCK", "file": os.path.relpath(path, target_dir),
                             "line": None, "rule": "AP-001", "detail": desc})

    for file_path, lines in added.items():
        if Path(file_path).suffix not in SOURCE_SUFFIXES or Path(file_path).name in SCANNER_FILES:
            continue
        for line_no, text in lines:
            for pattern, desc in DEBUG_RESIDUE:
                if pattern.search(text):
                    findings.append({"severity": "WARN", "file": file_path, "line": line_no,
                                     "rule": "AP-003", "detail": desc})
            marker = MARKER_PATTERN.search(text)
            if marker:
                findings.append({"severity": "INFO", "file": file_path, "line": line_no,
                                 "rule": "REVIEW", "detail": f"unresolved {marker.group(1)} marker added"})

    source_files = [f for f in changed if Path(f).suffix in SOURCE_SUFFIXES and not is_test_path(f)]
    test_files = [f for f in changed if is_test_path(f)]
    if source_files and not test_files:
        findings.append({"severity": "WARN" if not strict else "BLOCK", "file": None, "line": None,
                         "rule": "AP-002",
                         "detail": f"{len(source_files)} source file(s) changed with no test file changed"})

    stats = {"changed": len(changed), "source": len(source_files), "tests": len(test_files)}
    return findings, changed, stats


def print_review(target_dir=".", strict=False, emit_json=False):
    findings, changed, stats = review_diff(target_dir, strict)

    blocking = [f for f in findings if f["severity"] == "BLOCK"]
    warnings = [f for f in findings if f["severity"] == "WARN"]

    if blocking:
        verdict = "CHANGES REQUIRED"
    elif warnings:
        verdict = "APPROVED WITH COMMENTS"
    elif changed:
        verdict = "APPROVED"
    else:
        verdict = "NOTHING TO REVIEW"

    if emit_json:
        print(json.dumps({
            "verdict": verdict,
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scope": "static pass over added lines",
            "stats": stats,
            "changed_files": changed,
            "findings": findings,
        }, indent=2))
        return 1 if blocking else 0

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Static Review — Working Diff")
    print("=" * 64)
    print(f"  Target Directory : {Path(target_dir).resolve()}")
    print(f"  Changed Files    : {stats['changed']} ({stats['source']} source, {stats['tests']} test)")
    print(f"  Review Scope     : static pass over added lines only")
    print("  " + "-" * 60)

    if not changed:
        print("  (No staged, unstaged or untracked changes to review)")
        print("=" * 64 + "\n")
        return 0

    if findings:
        print(f"  Findings ({len(blocking)} blocking, {len(warnings)} warning, "
              f"{len(findings) - len(blocking) - len(warnings)} info):")
        print("  " + "-" * 60)
        for f in sorted(findings, key=lambda x: ["BLOCK", "WARN", "INFO"].index(x["severity"])):
            location = f["file"] or "(diff-wide)"
            if f["line"]:
                location += f":{f['line']}"
            print(f"  [{SEVERITY_ICON[f['severity']]}] {f['severity']:<5} {f['rule']:<8} {location}")
            print(f"      └─ {f['detail']}")
    else:
        print("  No static review findings.")

    print("  " + "-" * 60)
    print(f"  Verdict          : {verdict}")
    print("  Note             : logic correctness & maintainability remain human/reviewer-agent scope")
    print("=" * 64 + "\n")
    return 1 if blocking else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    tgt = argv[0] if argv and not argv[0].startswith("--") else "."
    sys.exit(print_review(tgt, "--strict" in argv, "--json" in argv))
