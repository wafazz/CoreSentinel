#!/usr/bin/env python3
"""
CoreSentinel Quality Gates Engine

Ten ordered gates. The original eight keep their names and their order; Phase 6
added Requirement at the front and Documentation before Deployment, because the
two things most often missing at the end of a change are a statement of what it
was for and a record of what it did.

    Requirement -> Plan -> Architecture -> Security -> Implementation
                -> Test -> Review -> Verification -> Documentation -> Deployment

Every gate result carries a machine-readable `code` alongside its prose. A CI job
should be able to branch on *why* a gate failed without parsing a sentence, and
a reason code is the difference between "the pipeline is red" and "the test
runner is not installed on this machine".

A gate resolves to:

  PASS      a check ran and the property holds
  FAIL      a check ran and the property is violated — blocks every later gate
  UNKNOWN   no automated check exists, or none could run — does not block, but is
            not a pass either; clear it with a waiver and a rationale
  BLOCKED   an earlier gate failed
  WAIVED    a human accepted the risk, with the reason recorded
  PENDING   not yet evaluated
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

MEMORY_DIR = SCRIPT_DIR / "memory"
GATES_FILE = MEMORY_DIR / "gates.json"

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
BLOCKED, WAIVED, PENDING = "BLOCKED", "WAIVED", "PENDING"

GATE_PIPELINE = [
    "Requirement",
    "Plan",
    "Architecture",
    "Security",
    "Implementation",
    "Test",
    "Review",
    "Verification",
    "Documentation",
    "Deployment",
]

# Gates with no mechanically checkable property. Reporting them as PASS was the
# single largest source of false confidence in the pipeline; they are UNKNOWN
# until a human waives them with a stated reason.
MANUAL_GATES = {
    "Plan": "no automated check for requirement completeness",
    "Architecture": "no automated check for design adequacy",
    "Deployment": "no automated check without a deployment target",
}

# Machine-readable reasons. A CI job branches on these, never on the prose.
CODES = {
    "NO_AUTOMATED_CHECK": "the gate has no mechanically checkable property",
    "NO_REPOSITORY": "the target is not a git repository",
    "NO_CHANGES": "there is nothing in the working tree to gate",
    "SCANNER_CLEAN": "the security scanner reported no violations",
    "SCANNER_VIOLATIONS": "the security scanner reported violations",
    "TESTS_PASSED": "the test suite exited zero",
    "TESTS_FAILED": "the test suite reported failures",
    "NO_TEST_RUNNER": "no test runner is installed or configured here",
    "REVIEW_CLEAN": "the static review found nothing blocking",
    "REVIEW_BLOCKING": "the static review found blocking findings",
    "EVIDENCE_SUFFICIENT": "the evidence suite scored at or above the threshold",
    "EVIDENCE_BELOW_THRESHOLD": "the evidence suite scored below the threshold",
    "EVIDENCE_INSUFFICIENT": "too little of the evidence budget could be executed to judge",
    "REQUIREMENT_STATED": "an objective or requirement artifact was supplied",
    "REQUIREMENT_MISSING": "no objective was given and no requirement artifact was found",
    "DOCS_UPDATED": "documentation changed alongside the source",
    "DOCS_STALE": "source changed and no documentation changed with it",
    "NO_DOCUMENTATION": "this project has no documentation to keep current",
    "IMPLEMENTATION_PRESENT": "the working tree contains changes to gate",
    "UPSTREAM_FAILED": "an earlier gate failed",
    "WAIVED": "a human accepted the risk",
    "NOT_EVALUATED": "the gate has not been evaluated",
}

STATUS_ICON = {PASS: "[✓ PASS]", FAIL: "[✗ FAIL]", UNKNOWN: "[? UNKN]",
               BLOCKED: "[· BLKD]", WAIVED: "[~ WAIV]", PENDING: "[· PEND]"}

DOC_SUFFIXES = {".md", ".rst", ".adoc", ".txt"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".rb", ".go",
                   ".rs", ".java", ".kt", ".cs", ".swift"}

REQUIREMENT_ARTIFACTS = ["REQUIREMENTS.md", "docs/requirements.md", "Planning.md",
                         "SPEC.md", "docs/spec.md"]

EXIT_OK, EXIT_FAILED = 0, 1


def blank_gate(reason="not yet evaluated"):
    return {"status": PENDING, "code": "NOT_EVALUATED", "reason": reason, "basis": None,
            "timestamp": datetime.now().strftime(execution.TIMESTAMP_FORMAT),
            "waived_reason": None}


def ensure_gates_file():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    if not GATES_FILE.exists():
        save_gates({"gates": {gate: blank_gate() for gate in GATE_PIPELINE}})


def load_gates():
    ensure_gates_file()
    try:
        with open(GATES_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[!] Error reading gates state: {e}", file=sys.stderr)
        return {"gates": {}}


def save_gates(state):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().strftime(execution.TIMESTAMP_FORMAT)
    with open(GATES_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _changed_files(target_dir):
    result = execution.git("status", "--porcelain", cwd=target_dir)
    if not result.ok or not result.stdout:
        return []
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------- evaluation

def evaluate_gate(gate_name, target_dir=".", objective=None):
    """Return (status, code, reason, basis). Never asserts a property it did not check."""
    if gate_name in MANUAL_GATES:
        return (UNKNOWN, "NO_AUTOMATED_CHECK", MANUAL_GATES[gate_name] +
                f" — waive with: coresentinel gate waive --gate {gate_name} --reason \"...\"",
                None)

    import coresentinel_evidence as evidence

    if gate_name == "Requirement":
        if objective:
            return PASS, "REQUIREMENT_STATED", f"objective stated: {objective}", "--objective"
        found = next((name for name in REQUIREMENT_ARTIFACTS
                      if (Path(target_dir) / name).exists()), None)
        if found:
            return PASS, "REQUIREMENT_STATED", f"requirement artifact present: {found}", found
        return (UNKNOWN, "REQUIREMENT_MISSING",
                "no objective given and no requirement artifact found — "
                "pass one with: coresentinel gate run --objective \"...\"", None)

    if gate_name == "Security":
        return _from_finding(evidence.check_security(target_dir),
                             PASS, "SCANNER_CLEAN", "SCANNER_VIOLATIONS")

    if gate_name == "Implementation":
        if not execution.is_git_repository(target_dir):
            return UNKNOWN, "NO_REPOSITORY", "not a git repository — no implementation to inspect", None
        changed = _changed_files(target_dir)
        if not changed:
            return UNKNOWN, "NO_CHANGES", "working tree is clean — no implementation to gate", \
                "git status --porcelain"
        return (PASS, "IMPLEMENTATION_PRESENT",
                f"{len(changed)} file(s) changed in the working tree", "git status --porcelain")

    if gate_name == "Test":
        return _from_finding(evidence.check_tests(target_dir),
                             PASS, "TESTS_PASSED", "TESTS_FAILED", "NO_TEST_RUNNER")

    if gate_name == "Review":
        return _from_finding(evidence.check_diff(target_dir),
                             PASS, "REVIEW_CLEAN", "REVIEW_BLOCKING", "NO_CHANGES")

    if gate_name == "Documentation":
        return _documentation_gate(target_dir)

    if gate_name == "Verification":
        report = evidence.verify(target_dir, objective or "quality gate verification")
        basis = f"coresentinel verify — {report['evidence_coverage']}/100 evidence coverage"
        if report["verdict"] == evidence.INDETERMINATE:
            return UNKNOWN, "EVIDENCE_INSUFFICIENT", report["rationale"], basis
        if report["verdict"] == evidence.VERIFIED:
            return PASS, "EVIDENCE_SUFFICIENT", f"evidence score {report['score']}/100", basis
        return (FAIL, "EVIDENCE_BELOW_THRESHOLD",
                f"evidence score {report['score']}/100 is below the threshold", basis)

    return UNKNOWN, "NO_AUTOMATED_CHECK", "no check is defined for this gate", None


def _documentation_gate(target_dir):
    """Documentation that never changes while the code does is documentation that lies."""
    root = Path(target_dir)
    if not execution.is_git_repository(target_dir):
        return UNKNOWN, "NO_REPOSITORY", "not a git repository — nothing to compare", None

    changed = _changed_files(target_dir)
    if not changed:
        return UNKNOWN, "NO_CHANGES", "working tree is clean — nothing to document", \
            "git status --porcelain"

    has_docs = bool(list(root.glob("*.md")) or (root / "docs").is_dir())
    if not has_docs:
        return (UNKNOWN, "NO_DOCUMENTATION",
                "this project carries no documentation to keep current", None)

    source_changed = [f for f in changed if Path(f).suffix in SOURCE_SUFFIXES]
    docs_changed = [f for f in changed if Path(f).suffix in DOC_SUFFIXES]

    if not source_changed:
        return (PASS, "DOCS_UPDATED", "no source changed, so nothing is out of date",
                "git status --porcelain")
    if docs_changed:
        return (PASS, "DOCS_UPDATED",
                f"{len(docs_changed)} documentation file(s) changed alongside "
                f"{len(source_changed)} source file(s)", "git status --porcelain")
    return (FAIL, "DOCS_STALE",
            f"{len(source_changed)} source file(s) changed and no documentation changed",
            "git status --porcelain")


def _from_finding(finding, pass_status, pass_code, fail_code, unknown_code=None):
    import coresentinel_evidence as evidence

    if finding["status"] == evidence.PASS:
        return pass_status, pass_code, finding["detail"], finding["basis"]
    if finding["status"] == evidence.FAIL:
        return FAIL, fail_code, finding["detail"], finding["basis"]
    return UNKNOWN, unknown_code or "NO_AUTOMATED_CHECK", finding["detail"], finding["basis"]


def run_all_gates(target_dir=".", emit_json=False, objective=None, report_style=False):
    state = load_gates()
    gates = state.setdefault("gates", {})
    blocked_by = None

    for gate_name in GATE_PIPELINE:
        current = gates.get(gate_name) or blank_gate()

        if current.get("status") == WAIVED:
            continue

        if blocked_by:
            gates[gate_name] = {
                "status": BLOCKED, "code": "UPSTREAM_FAILED",
                "reason": f"blocked by an upstream failure at the {blocked_by} gate",
                "basis": None,
                "timestamp": datetime.now().strftime(execution.TIMESTAMP_FORMAT),
                "waived_reason": None}
            continue

        status, code, reason, basis = evaluate_gate(gate_name, target_dir, objective)
        gates[gate_name] = {
            "status": status, "code": code, "reason": reason, "basis": basis,
            "timestamp": datetime.now().strftime(execution.TIMESTAMP_FORMAT),
            "waived_reason": None}
        if status == FAIL:
            blocked_by = gate_name

    save_gates(state)
    report = _report(state, gates, target_dir, objective)

    if emit_json:
        print(json.dumps(report, indent=2))
    elif report_style:
        _render_report(report)
    else:
        _render(report, "Quality Gates Pipeline")
    return EXIT_FAILED if report["verdict"] == "BLOCKED" else EXIT_OK


def _report(state, gates, target_dir, objective=None):
    failed = [n for n, g in gates.items() if g.get("status") in (FAIL, BLOCKED)]
    return {
        "coresentinel_api": "1.1",
        "target": str(Path(target_dir).resolve()),
        "objective": objective,
        "evaluated_at": state.get("last_updated"),
        "pipeline": GATE_PIPELINE,
        "gates": gates,
        "counts": {status: sum(1 for g in gates.values() if g.get("status") == status)
                   for status in (PASS, FAIL, UNKNOWN, BLOCKED, WAIVED, PENDING)},
        "codes": {name: gate.get("code") for name, gate in gates.items()},
        "blocked_by": failed[0] if failed else None,
        "verdict": "BLOCKED" if failed else "CLEAR",
        "final_status": "BLOCKED" if failed else "APPROVED",
    }


def show_status(target_dir=".", emit_json=False, report_style=False):
    state = load_gates()
    gates = state.get("gates", {})
    for gate_name in GATE_PIPELINE:
        gates.setdefault(gate_name, blank_gate())

    report = _report(state, gates, target_dir)
    if emit_json:
        print(json.dumps(report, indent=2))
    elif report_style:
        _render_report(report)
    else:
        _render(report, "Quality Gates Pipeline Status")
    return EXIT_OK


def _render(report, title):
    print("\n" + "=" * 64)
    print(f"  🛡️  CoreSentinel {title}")
    print("=" * 64)
    print(f"  Last Evaluated: {report.get('evaluated_at') or 'never'}")
    if report.get("objective"):
        print(f"  Objective     : {report['objective']}")
    print("")

    for index, gate_name in enumerate(report["pipeline"], 1):
        gate = report["gates"].get(gate_name, blank_gate())
        status = gate.get("status", PENDING)
        waived = f"  [waived: {gate.get('waived_reason')}]" if status == WAIVED else ""
        print(f"  {index:2}. {gate_name:<16} {STATUS_ICON.get(status, status)}"
              f"  {gate.get('code', ''):<26}{waived}")
        print(f"      └─ {gate.get('reason', 'pending execution')}")
        if gate.get("basis"):
            print(f"         basis: {gate['basis']}")

    counts = report["counts"]
    print("\n  " + "-" * 60)
    print(f"  {counts[PASS]} pass · {counts[FAIL]} fail · {counts[UNKNOWN]} unknown · "
          f"{counts[BLOCKED]} blocked · {counts[WAIVED]} waived · {counts[PENDING]} pending")
    if counts[UNKNOWN]:
        print("  An UNKNOWN gate is not a pass. Waive it with a recorded rationale:")
        print("    coresentinel gate waive --gate <name> --reason \"...\"")
    print(f"  FINAL STATUS: {report['final_status']}")
    print("=" * 64 + "\n")


def _render_report(report):
    """The compact completion report: one line per gate, then the verdict."""
    print("\nTASK COMPLETE" if report["final_status"] == "APPROVED" else "\nTASK BLOCKED")
    if report.get("objective"):
        print(f"  {report['objective']}")
    print("")
    for gate_name in report["pipeline"]:
        gate = report["gates"].get(gate_name, blank_gate())
        print(f"  {gate_name:<18} {gate.get('status', PENDING)}")
    print("")
    print(f"FINAL STATUS: {report['final_status']}")
    if report["blocked_by"]:
        blocking = report["gates"][report["blocked_by"]]
        print(f"  blocked at {report['blocked_by']} — {blocking.get('code')}: "
              f"{blocking.get('reason')}")
    print("")


def waive_gate(gate_name, reason):
    state = load_gates()
    gates = state.setdefault("gates", {})

    matched = [g for g in GATE_PIPELINE if g.lower() == (gate_name or "").lower()]
    if not matched:
        print(f"[!] Gate '{gate_name}' not recognized. Valid gates: {', '.join(GATE_PIPELINE)}",
              file=sys.stderr)
        return False

    if not (reason or "").strip():
        print("[!] A waiver requires a rationale. Nothing recorded.", file=sys.stderr)
        return False

    target_gate = matched[0]
    gates[target_gate] = {
        "status": WAIVED, "code": "WAIVED", "reason": "manually waived", "basis": None,
        "timestamp": datetime.now().strftime(execution.TIMESTAMP_FORMAT),
        "waived_reason": reason}

    save_gates(state)
    print(f"[✓] Quality Gate [{target_gate}] set to WAIVED (Reason: '{reason}')")
    return True


def reset_gates():
    save_gates({"gates": {gate: blank_gate() for gate in GATE_PIPELINE}})
    print("[✓] CoreSentinel Quality Gates pipeline reset — every gate is PENDING.")


if __name__ == "__main__":
    argv = sys.argv[1:]
    sub = argv[0].lower() if argv and not argv[0].startswith("-") else "status"
    as_json = "--json" in argv
    if sub == "run":
        sys.exit(run_all_gates(".", as_json, report_style="--report" in argv))
    elif sub == "reset":
        reset_gates()
    elif sub == "waive":
        sys.exit(0 if waive_gate(argv[1] if len(argv) > 1 else "",
                                 argv[2] if len(argv) > 2 else "") else 1)
    else:
        sys.exit(show_status(".", as_json, report_style="--report" in argv))
