#!/usr/bin/env python3
"""
CoreSentinel Evidence-Based Verification Engine

The previous implementation awarded 45 of its 100 points from three checks that
executed nothing at all — Linter, Dependency Audit and Diff Inspection each
returned a hardcoded PASS with an invented justification string. An empty
directory containing no code, no git repository and no tests scored 80/100
VERIFIED on the claim "I fixed the authentication vulnerability".

That is the exact failure CoreSentinel exists to prevent, committed by
CoreSentinel. Every check here runs a command, or reports UNKNOWN.

Three states, and the third is the one that matters:

  PASS      a command ran and its exit code says the property holds
  FAIL      a command ran and its exit code says the property is violated
  UNKNOWN   nothing could be run, so nothing is known

UNKNOWN is excluded from the denominator rather than defaulted to a pass. A
verdict additionally requires MIN_EVIDENCE_WEIGHT of the 100-point budget to
have actually executed, so a claim can never be VERIFIED on one trivial check
while five others stayed silent.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import coresentinel_exec as execution

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
INDETERMINATE = "INDETERMINATE"

PASS_THRESHOLD = 80

# Half the evidence budget must have executed before any verdict is issued.
# Without this floor a repository with only a clean lockfile would score 100/100
# from a single 10-point check while the other five reported UNKNOWN.
MIN_EVIDENCE_WEIGHT = 50

EXIT_CODE = {VERIFIED: 0, UNVERIFIED: 1, INDETERMINATE: 2}

STATUS_ICON = {PASS: "[✓]", FAIL: "[✗]", UNKNOWN: "[?]"}

TEST_TIMEOUT = 600
AUDIT_TIMEOUT = 180


def _finding(check_id, label, weight, status, detail, run=None, basis=None):
    record = {
        "id": check_id,
        "check": label,
        "weight": weight,
        "status": status,
        "earned": weight if status == PASS else 0,
        "detail": detail,
        "basis": basis or (run.display if run else "no command available"),
    }
    record.update(run.record() if run else {
        "command": None, "cwd": None, "started_at": None, "duration_ms": None,
        "exit_code": None, "output_digest": None, "output_excerpt": None, "error": None,
    })
    return record


def _changed_files(target_dir):
    """Staged, unstaged and untracked paths. Empty when the tree is clean or not a repo."""
    result = execution.git("status", "--porcelain", cwd=target_dir)
    if not result.ok or not result.stdout:
        return []
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------- checks

def check_code_change(target_dir="."):
    """Evidence that anything was changed at all. A clean tree evidences nothing."""
    label, weight = "Code Change", 20

    if not execution.is_git_repository(target_dir):
        return _finding("code_change", label, weight, UNKNOWN,
                        "not a git repository — no change evidence is obtainable",
                        basis="git rev-parse --git-dir")

    result = execution.git("status", "--porcelain", cwd=target_dir)
    if not result.ran:
        return _finding("code_change", label, weight, UNKNOWN,
                        result.error or "git could not be queried", result)

    files = [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]
    if not files:
        return _finding("code_change", label, weight, UNKNOWN,
                        "working tree is clean — there is no change to evidence", result)

    sample = ", ".join(files[:5]) + (" …" if len(files) > 5 else "")
    return _finding("code_change", label, weight, PASS,
                    f"{len(files)} file(s) changed: {sample}", result)


def check_tests(target_dir="."):
    """Run whatever test runner this project actually has installed."""
    label, weight = "Security / Unit Test", 25
    target = Path(target_dir)

    if (target / "package.json").exists() and execution.available("npm"):
        try:
            scripts = json.loads((target / "package.json").read_text(encoding="utf-8-sig")).get("scripts", {})
        except (OSError, json.JSONDecodeError, ValueError):
            scripts = {}
        if scripts.get("test"):
            result = execution.run(["npm", "test"], cwd=target_dir, timeout=TEST_TIMEOUT)
            return _test_verdict("tests", label, weight, result)

    if _has_pytest_config(target):
        if not execution.module_importable("pytest", cwd=target_dir):
            return _finding("tests", label, weight, UNKNOWN,
                            f"pytest is configured but not importable by {sys.executable}",
                            basis=f"{sys.executable} -c 'import pytest'")
        result = execution.python("-m", "pytest", "-q", cwd=target_dir, timeout=TEST_TIMEOUT)
        return _test_verdict("tests", label, weight, result)

    phpunit = target / "vendor" / "bin" / "phpunit"
    if phpunit.exists():
        result = execution.run([str(phpunit), "--no-coverage"], cwd=target_dir, timeout=TEST_TIMEOUT)
        return _test_verdict("tests", label, weight, result)

    if (target / "Cargo.toml").exists() and execution.available("cargo"):
        return _test_verdict("tests", label, weight,
                             execution.run(["cargo", "test"], cwd=target_dir, timeout=TEST_TIMEOUT))

    if (target / "go.mod").exists() and execution.available("go"):
        return _test_verdict("tests", label, weight,
                             execution.run(["go", "test", "./..."], cwd=target_dir, timeout=TEST_TIMEOUT))

    return _finding("tests", label, weight, UNKNOWN,
                    "no test runner detected for this project")


def _has_pytest_config(target):
    if (target / "pytest.ini").exists() or (target / "conftest.py").exists():
        return True
    pyproject = target / "pyproject.toml"
    if pyproject.exists():
        try:
            return "pytest" in pyproject.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return False
    return False


def _test_verdict(check_id, label, weight, result):
    if not result.ran:
        return _finding(check_id, label, weight, UNKNOWN,
                        result.error or "the test runner could not be started", result)
    if result.ok:
        return _finding(check_id, label, weight, PASS,
                        f"test suite exited 0 in {result.duration_ms} ms", result)
    return _finding(check_id, label, weight, FAIL,
                    f"test suite exited {result.exit_code}", result)


def check_lint(target_dir="."):
    """Whatever linter the project actually has. No linter is UNKNOWN, not clean."""
    label, weight = "Linter & Formatting", 15
    target = Path(target_dir)

    if (target / "package.json").exists() and execution.available("npm"):
        try:
            scripts = json.loads((target / "package.json").read_text(encoding="utf-8-sig")).get("scripts", {})
        except (OSError, json.JSONDecodeError, ValueError):
            scripts = {}
        if scripts.get("lint"):
            return _exit_verdict("lint", label, weight,
                                 execution.run(["npm", "run", "lint"], cwd=target_dir),
                                 "linter reported no violations", "linter reported violations")

    if list(target.glob("*.py")) or _has_pytest_config(target):
        if execution.available("ruff"):
            return _exit_verdict("lint", label, weight,
                                 execution.run(["ruff", "check", "."], cwd=target_dir),
                                 "ruff reported no violations", "ruff reported violations")
        if execution.available("flake8"):
            return _exit_verdict("lint", label, weight,
                                 execution.run(["flake8"], cwd=target_dir),
                                 "flake8 reported no violations", "flake8 reported violations")

    if (target / "go.mod").exists() and execution.available("gofmt"):
        # gofmt -l exits 0 either way and lists unformatted files on stdout.
        result = execution.run(["gofmt", "-l", "."], cwd=target_dir)
        if not result.ran:
            return _finding("lint", label, weight, UNKNOWN, result.error or "gofmt failed", result)
        if result.stdout:
            return _finding("lint", label, weight, FAIL,
                            f"{len(result.stdout.splitlines())} file(s) are not gofmt-clean", result)
        return _finding("lint", label, weight, PASS, "every file is gofmt-clean", result)

    if (target / "Cargo.toml").exists() and execution.available("cargo"):
        return _exit_verdict("lint", label, weight,
                             execution.run(["cargo", "clippy", "--", "-D", "warnings"],
                                           cwd=target_dir, timeout=TEST_TIMEOUT),
                             "clippy reported no warnings", "clippy reported warnings")

    return _finding("lint", label, weight, UNKNOWN,
                    "no linter is configured for this project or installed on this machine")


def check_security(target_dir="."):
    """The anti-pattern and secret scanner, over the files this change actually touches."""
    label, weight = "Security & Anti-Pattern Audit", 20
    validator = SCRIPT_DIR / "sentinel-validator.py"

    if not validator.exists():
        return _finding("security", label, weight, UNKNOWN,
                        "sentinel-validator.py is missing from the Core")

    if not execution.is_git_repository(target_dir):
        return _finding("security", label, weight, UNKNOWN,
                        "not a git repository — the scanner has no change set to read",
                        basis="git rev-parse --git-dir")

    if not _changed_files(target_dir):
        return _finding("security", label, weight, UNKNOWN,
                        "no changed files — a scan of nothing evidences nothing",
                        basis="git status --porcelain")

    result = execution.python(str(validator), cwd=target_dir, timeout=AUDIT_TIMEOUT)
    return _exit_verdict("security", label, weight, result,
                         "scanner reported zero violations",
                         "scanner reported violations")


def check_dependencies(target_dir="."):
    """A real advisory audit, or nothing. Lockfile presence is not a vulnerability check."""
    label, weight = "Dependency Vulnerability Audit", 10
    target = Path(target_dir)

    if (target / "package-lock.json").exists() and execution.available("npm"):
        return _exit_verdict("dependencies", label, weight,
                             execution.run(["npm", "audit", "--audit-level=high"],
                                           cwd=target_dir, timeout=AUDIT_TIMEOUT),
                             "no high or critical advisories", "high or critical advisories found")

    if (target / "composer.lock").exists() and execution.available("composer"):
        return _exit_verdict("dependencies", label, weight,
                             execution.run(["composer", "audit"], cwd=target_dir, timeout=AUDIT_TIMEOUT),
                             "no advisories reported", "advisories reported")

    if (target / "Cargo.lock").exists() and execution.available("cargo-audit"):
        return _exit_verdict("dependencies", label, weight,
                             execution.run(["cargo-audit", "audit"], cwd=target_dir, timeout=AUDIT_TIMEOUT),
                             "no advisories reported", "advisories reported")

    python_locked = any((target / name).exists() for name in
                        ("requirements.txt", "poetry.lock", "Pipfile.lock", "pyproject.toml"))
    if python_locked and execution.available("pip-audit"):
        return _exit_verdict("dependencies", label, weight,
                             execution.run(["pip-audit"], cwd=target_dir, timeout=AUDIT_TIMEOUT),
                             "no advisories reported", "advisories reported")

    return _finding("dependencies", label, weight, UNKNOWN,
                    "no dependency audit tool is available for this stack on this machine")


def check_diff(target_dir="."):
    """Static review of added lines — debug residue, unresolved markers, missing tests.

    Validator-sourced rules are filtered out: check_security already scores those,
    and counting one secret twice would distort the weighting rather than sharpen it.
    """
    label, weight = "Git Diff Inspection", 10
    basis = "coresentinel review — static pass over added lines"

    if not execution.is_git_repository(target_dir):
        return _finding("diff", label, weight, UNKNOWN,
                        "not a git repository — there is no diff to inspect", basis=basis)

    try:
        import coresentinel_review as review
    except ImportError as e:
        return _finding("diff", label, weight, UNKNOWN,
                        f"static review engine unavailable ({e})", basis=basis)

    findings, changed, stats = review.review_diff(target_dir)
    if not changed:
        return _finding("diff", label, weight, UNKNOWN,
                        "no staged, unstaged or untracked changes to inspect", basis=basis)

    owned = [f for f in findings if f["rule"] not in ("AP-001", "AP-004")]
    blocking = [f for f in owned if f["severity"] == "BLOCK"]
    warnings = [f for f in owned if f["severity"] == "WARN"]

    if blocking:
        return _finding("diff", label, weight, FAIL,
                        f"{len(blocking)} blocking finding(s) across {stats['changed']} changed file(s)",
                        basis=basis)
    return _finding("diff", label, weight, PASS,
                    f"{stats['changed']} file(s) inspected, no blocking findings"
                    + (f", {len(warnings)} warning(s)" if warnings else ""),
                    basis=basis)


def _exit_verdict(check_id, label, weight, result, pass_detail, fail_detail):
    if not result.ran:
        return _finding(check_id, label, weight, UNKNOWN,
                        result.error or "the command could not be started", result)
    if result.ok:
        return _finding(check_id, label, weight, PASS, pass_detail, result)
    return _finding(check_id, label, weight, FAIL,
                    f"{fail_detail} (exit {result.exit_code})", result)


CHECKS = [check_code_change, check_tests, check_lint,
          check_security, check_dependencies, check_diff]


# ---------------------------------------------------------------- engine

def collect(target_dir="."):
    return [check(target_dir) for check in CHECKS]


def summarise(findings, claim="", target_dir="."):
    scored = [f for f in findings if f["status"] in (PASS, FAIL)]
    unknown = [f for f in findings if f["status"] == UNKNOWN]

    covered = sum(f["weight"] for f in scored)
    earned = sum(f["earned"] for f in scored)

    if covered < MIN_EVIDENCE_WEIGHT:
        score, verdict = None, INDETERMINATE
        rationale = (f"only {covered}/100 of the evidence budget could be executed; "
                     f"{MIN_EVIDENCE_WEIGHT} is the minimum for any verdict")
    else:
        score = int(round(earned / covered * 100))
        verdict = VERIFIED if score >= PASS_THRESHOLD else UNVERIFIED
        rationale = (f"{earned}/{covered} weighted points earned from {len(scored)} "
                     f"executed check(s); threshold {PASS_THRESHOLD}")

    return {
        "coresentinel_api": "1.1",
        "claim": claim,
        "target": str(Path(target_dir).resolve()),
        "verified_at": datetime.now().strftime(execution.TIMESTAMP_FORMAT),
        "verdict": verdict,
        "score": score,
        "evidence_coverage": covered,
        "minimum_coverage": MIN_EVIDENCE_WEIGHT,
        "rationale": rationale,
        "counts": {
            "pass": sum(1 for f in scored if f["status"] == PASS),
            "fail": sum(1 for f in scored if f["status"] == FAIL),
            "unknown": len(unknown),
        },
        "checks": findings,
    }


def verify(target_dir=".", claim=""):
    return summarise(collect(target_dir), claim, target_dir)


def print_verification(target_dir=".", claim="", emit_json=False):
    report = verify(target_dir, claim)

    if emit_json:
        print(json.dumps(report, indent=2))
        return EXIT_CODE[report["verdict"]]

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Evidence-Based Verification")
    print("=" * 64)
    print(f"  Target Directory  : {report['target']}")
    print(f"  Submitted Claim   : {claim or '(none stated)'}")
    print("  " + "-" * 60)
    print("  Evidence Collected:")
    print("  " + "-" * 60)

    for item in report["checks"]:
        icon = STATUS_ICON[item["status"]]
        points = f"{item['earned']}/{item['weight']}" if item["status"] != UNKNOWN else "  n/a"
        print(f"  {icon} {item['check']:<30} {item['status']:<8} {points:>6} pts")
        print(f"      └─ {item['detail']}")
        if item["command"]:
            print(f"         $ {item['command']}  → exit {item['exit_code']}"
                  f"  ({item['duration_ms']} ms, {item['output_digest']})")
        else:
            print(f"         basis: {item['basis']}")

    counts = report["counts"]
    print("  " + "-" * 60)
    print(f"  Executed          : {counts['pass']} pass, {counts['fail']} fail, "
          f"{counts['unknown']} unknown")
    print(f"  Evidence Coverage : {report['evidence_coverage']}/100 weight "
          f"(minimum {report['minimum_coverage']})")
    print("\n" + "=" * 64)
    if report["score"] is None:
        print(f"  Status : {report['verdict']}")
        print("  Score  : n/a — not enough of the evidence budget could be executed")
    else:
        print(f"  Status : {report['verdict']}")
        print(f"  Score  : {report['score']}/100")
    print(f"  Why    : {report['rationale']}")
    print("=" * 64 + "\n")

    return EXIT_CODE[report["verdict"]]


if __name__ == "__main__":
    argv = sys.argv[1:]
    target = argv[0] if argv and not argv[0].startswith("-") else "."
    stated = argv[argv.index("--claim") + 1] if "--claim" in argv and \
        argv.index("--claim") + 1 < len(argv) else ""
    sys.exit(print_verification(target, stated, "--json" in argv))
