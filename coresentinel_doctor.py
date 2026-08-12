#!/usr/bin/env python3
"""
CoreSentinel Doctor & Status Engine
Self-diagnostics across the 7 subsystems that must be healthy for CoreSentinel to
govern an AI agent: Configuration, Memory, Governance, Agent Registry, Verification
Engine, Security Rules, and Project Context.
"""

import os
import sys
import json
import importlib
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR / "memory"

STATUS_ICON = {"OK": "✓", "WARN": "!", "FAIL": "✗"}
RULE = "─" * 60

CORE_ASSETS = [
    "coresentinel.py",
    "00-identity.md",
    "anti-patterns.json",
    "squad-contracts.json",
    "adapters.json",
    "sentinel-validator.py",
]

MEMORY_LAYERS = ["working", "session", "project", "longterm", "failures", "patterns", "decisions"]

ENGINE_MODULES = [
    "coresentinel_memory",
    "coresentinel_squad",
    "coresentinel_gates",
    "coresentinel_audit",
    "coresentinel_score",
    "coresentinel_evolve",
    "coresentinel_adapters",
]

CONTRACT_FIELDS = ["name", "role", "input_contract", "output_contract", "authority"]


def read_json(path):
    """Return (data, error_message). Never masks a parse failure."""
    if not Path(path).exists():
        return None, f"missing: {Path(path).name}"
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f), None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return None, f"{Path(path).name}: {e}"


def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=30)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except (subprocess.SubprocessError, OSError) as e:
        # A missing or invalid working directory must degrade the check, not crash the run.
        return -1, "", str(e)


def project_memory_store(target_dir="."):
    """The bound project's own memory directory, if the target sits inside one."""
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import coresentinel_memory as mem
    except ImportError as e:
        print(f"[!] Memory engine unavailable ({e}) — project store not inspected", file=sys.stderr)
        return None

    root = mem.find_project_root(target_dir)
    if not root:
        return None
    store = root / mem.CONFIG_DIRNAME / "memory"
    return store if store.exists() else None


def result(name, status, summary, findings=None, fix=None):
    return {"check": name, "status": status, "summary": summary,
            "findings": findings or [], "fix": fix}


# ---------------------------------------------------------------- checks

def check_configuration():
    missing = [a for a in CORE_ASSETS if not (SCRIPT_DIR / a).exists()]
    findings = [f"{a} present" for a in CORE_ASSETS if a not in missing]
    findings += [f"MISSING: {a}" for a in missing]
    if missing:
        return result("Configuration", "FAIL", f"{len(missing)} core asset(s) missing",
                      findings, "Re-clone CoreSentinel or restore the missing files")
    return result("Configuration", "OK", f"{len(CORE_ASSETS)} core assets present", findings)


def check_memory(target_dir="."):
    if not MEMORY_DIR.exists():
        return result("Memory", "FAIL", "memory/ directory not found", [],
                      "Run: coresentinel init")

    findings, corrupt, absent = [], [], []
    total_entries = 0
    for layer in MEMORY_LAYERS:
        path = MEMORY_DIR / f"{layer}.json"
        if not path.exists():
            absent.append(layer)
            continue
        data, err = read_json(path)
        if err:
            corrupt.append(f"{layer}: {err}")
            continue
        count = len(data) if isinstance(data, list) else len(data.get("facts", []))
        total_entries += count
        findings.append(f"{layer}.json valid ({count} entries)")

    project_store = project_memory_store(target_dir)
    if project_store:
        findings.append(f"project store: {project_store}")
        for path in sorted(project_store.glob("*.json")):
            data, err = read_json(path)
            if err:
                corrupt.append(f"project/{path.name}: {err}")
                continue
            count = len(data) if isinstance(data, list) else len(data.get("facts", []))
            findings.append(f"project/{path.name} valid ({count} entries)")

    findings += [f"absent: {a}.json" for a in absent]
    findings += [f"CORRUPT: {c}" for c in corrupt]

    if corrupt:
        return result("Memory", "FAIL", f"{len(corrupt)} corrupt memory layer(s)", findings,
                      "Repair or delete the corrupt JSON file, then run: coresentinel init")
    if absent:
        return result("Memory", "WARN", f"{len(absent)} memory layer(s) not initialized", findings,
                      "Run: coresentinel init")
    return result("Memory", "OK", f"7 layers valid, {total_entries} recorded entries", findings)


def check_governance():
    protocols = sorted(SCRIPT_DIR.glob("[0-9][0-9]-*.md"))
    findings = [f"{len(protocols)} protocol documents indexed"]

    gates_data, gates_err = read_json(MEMORY_DIR / "gates.json")
    if gates_err and "missing" not in gates_err:
        return result("Governance", "FAIL", "quality gate ledger unreadable",
                      findings + [f"CORRUPT: {gates_err}"],
                      "Run: coresentinel gate reset")
    gates = (gates_data or {}).get("gates", {})
    if gates:
        passed = sum(1 for g in gates.values() if g.get("status") == "PASS")
        findings.append(f"quality gates: {passed}/{len(gates)} PASS")
    else:
        findings.append("quality gates: not yet run")

    evo_data, evo_err = read_json(MEMORY_DIR / "evolution_proposals.json")
    if evo_err and "missing" not in evo_err:
        return result("Governance", "FAIL", "evolution ledger unreadable",
                      findings + [f"CORRUPT: {evo_err}"], "Repair memory/evolution_proposals.json")
    pending = [p for p in (evo_data or []) if p.get("review_status") == "PENDING_REVIEW"]
    findings.append(f"evolution proposals: {len(evo_data or [])} total, {len(pending)} pending review")

    if not protocols:
        return result("Governance", "FAIL", "no protocol documents found", findings,
                      "Restore the numbered protocol markdown files")
    if pending:
        return result("Governance", "WARN",
                      f"{len(protocols)} protocols, {len(pending)} proposal(s) awaiting human review",
                      findings, "Review with: coresentinel evolve list")
    return result("Governance", "OK", f"{len(protocols)} protocols, ledgers consistent", findings)


def check_agent_registry():
    data, err = read_json(SCRIPT_DIR / "squad-contracts.json")
    if err:
        return result("Agent Registry", "FAIL", f"contract registry unreadable ({err})", [],
                      "Restore squad-contracts.json")

    squad = data.get("squad", [])
    incomplete = []
    for agent in squad:
        missing = [f for f in CONTRACT_FIELDS if not agent.get(f)]
        if missing:
            incomplete.append(f"{agent.get('name', '<unnamed>')}: missing {', '.join(missing)}")

    findings = [f"{len(squad)} specialist contracts registered"]
    findings += [f"INCOMPLETE: {i}" for i in incomplete]

    if not squad:
        return result("Agent Registry", "FAIL", "no agent contracts registered", findings,
                      "Restore squad-contracts.json")
    if incomplete:
        return result("Agent Registry", "WARN", f"{len(incomplete)} contract(s) incomplete",
                      findings, "Complete the missing contract fields in squad-contracts.json")
    return result("Agent Registry", "OK", f"{len(squad)} contracts complete", findings)


def check_verification_engine():
    findings, broken = [], []

    validator = SCRIPT_DIR / "sentinel-validator.py"
    if validator.exists():
        findings.append("sentinel-validator.py present")
    else:
        broken.append("sentinel-validator.py missing")

    sys.path.insert(0, str(SCRIPT_DIR))
    for module in ENGINE_MODULES:
        try:
            importlib.import_module(module)
            findings.append(f"{module} importable")
        except ImportError as e:
            broken.append(f"{module}: {e}")

    findings += [f"BROKEN: {b}" for b in broken]
    if broken:
        return result("Verification Engine", "FAIL", f"{len(broken)} engine component(s) broken",
                      findings, "Restore the missing engine modules")
    return result("Verification Engine", "OK",
                  f"validator + {len(ENGINE_MODULES)} engines operational", findings)


def check_security_rules():
    data, err = read_json(SCRIPT_DIR / "anti-patterns.json")
    if err:
        return result("Security Rules", "FAIL", f"anti-pattern database unreadable ({err})", [],
                      "Restore anti-patterns.json")

    rules = data.get("anti_patterns", [])
    unenforced = [r.get("id", "<no id>") for r in rules if not r.get("enforcement")]
    blocking = [r for r in rules if r.get("enforcement") == "STRICT_BLOCK"]

    findings = [f"{len(rules)} anti-pattern rules loaded",
                f"{len(blocking)} rules set to STRICT_BLOCK"]
    findings += [f"NO ENFORCEMENT LEVEL: {u}" for u in unenforced]

    gitignore = SCRIPT_DIR / ".gitignore"
    if gitignore.exists():
        findings.append(".gitignore present")
    else:
        findings.append("WARN: .gitignore absent — runtime logs may be committed")

    if not rules:
        return result("Security Rules", "FAIL", "anti-pattern database is empty", findings,
                      "Populate anti-patterns.json")
    if unenforced or not gitignore.exists():
        return result("Security Rules", "WARN", f"{len(rules)} rules loaded with gaps", findings,
                      "Set an enforcement level on every rule and add a .gitignore")
    return result("Security Rules", "OK", f"{len(rules)} rules armed, {len(blocking)} blocking",
                  findings)


def check_project_context(target_dir="."):
    findings = []
    target = Path(target_dir).resolve()

    code, branch, _ = run_cmd("git rev-parse --abbrev-ref HEAD", cwd=target_dir)
    if code == 0 and branch:
        findings.append(f"git repository on branch '{branch}'")
        _, dirty, _ = run_cmd("git status --short", cwd=target_dir)
        findings.append(f"working tree: {len(dirty.splitlines())} uncommitted change(s)"
                        if dirty else "working tree clean")
    else:
        findings.append("not a git repository — diff evidence unavailable")

    stack = detect_stack(target)
    findings.append(f"stack detected: {', '.join(stack)}")

    hosts = []
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import coresentinel_adapters as adapters
        for adapter in adapters.get_adapters():
            installed, active, _ = adapters.detect_adapter(adapter, target_dir)
            if installed or active:
                hosts.append(adapter["id"])
        findings.append(f"AI hosts detected: {', '.join(hosts) if hosts else 'none'}")
    except ImportError as e:
        findings.append(f"adapter layer unavailable: {e}")

    if code != 0:
        return result("Project Context", "WARN", "no git repository in target directory",
                      findings, "Run: git init")
    if not hosts:
        return result("Project Context", "WARN", f"{', '.join(stack)}, no AI host bound",
                      findings, "Run: coresentinel adapter detect")
    return result("Project Context", "OK", f"{', '.join(stack)} on '{branch}', {len(hosts)} host(s)",
                  findings)


def detect_stack(path):
    p = Path(path)
    markers = [
        ("package.json", "Node/TypeScript"),
        ("pyproject.toml", "Python"),
        ("requirements.txt", "Python"),
        ("composer.json", "PHP"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
        ("Gemfile", "Ruby"),
        ("pom.xml", "Java"),
    ]
    found = []
    for filename, label in markers:
        if (p / filename).exists() and label not in found:
            found.append(label)
    if not found and list(p.glob("*.py")):
        found.append("Python")
    return found or ["General"]


# ---------------------------------------------------------------- doctor

def run_doctor(target_dir=".", verbose=False, emit_json=False):
    checks = [
        check_configuration(),
        check_memory(target_dir),
        check_governance(),
        check_agent_registry(),
        check_verification_engine(),
        check_security_rules(),
        check_project_context(target_dir),
    ]

    failed = [c for c in checks if c["status"] == "FAIL"]
    warned = [c for c in checks if c["status"] == "WARN"]

    if failed:
        overall = "CRITICAL"
    elif warned:
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    if emit_json:
        print(json.dumps({
            "overall": overall,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "core_dir": str(SCRIPT_DIR),
            "target_dir": str(Path(target_dir).resolve()),
            "checks": checks
        }, indent=2))
        return 1 if failed else 0

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Doctor — Subsystem Diagnostics")
    print("=" * 64)
    print(f"  Core Directory : {SCRIPT_DIR}")
    print(f"  Target Project : {Path(target_dir).resolve()}")
    print("  " + RULE + "\n")

    for c in checks:
        print(f"  {STATUS_ICON[c['status']]} {c['check']:<22} {c['summary']}")
        if verbose:
            for finding in c["findings"]:
                print(f"      · {finding}")
        elif c["status"] != "OK":
            for finding in c["findings"]:
                if finding.split(":")[0] in ("MISSING", "CORRUPT", "BROKEN", "INCOMPLETE", "WARN") \
                        or finding.startswith(("absent", "NO ENFORCEMENT")):
                    print(f"      · {finding}")
        if c["status"] != "OK" and c["fix"]:
            print(f"      ➔ {c['fix']}")

    print("\n  " + RULE)
    print(f"  CoreSentinel: {overall}")
    if not verbose and (failed or warned):
        print("  (run 'coresentinel doctor --verbose' for the full finding list)")
    print("=" * 64 + "\n")

    return 1 if failed else 0


# ---------------------------------------------------------------- status

def run_status(target_dir=".", emit_json=False):
    gates_data, _ = read_json(MEMORY_DIR / "gates.json")
    gates = (gates_data or {}).get("gates", {})
    gate_pass = sum(1 for g in gates.values() if g.get("status") == "PASS")

    audit_data, _ = read_json(MEMORY_DIR / "audit_trail.json")
    runs = audit_data or []
    last_run = runs[-1] if runs else None

    evo_data, _ = read_json(MEMORY_DIR / "evolution_proposals.json")
    pending = [p for p in (evo_data or []) if p.get("review_status") == "PENDING_REVIEW"]

    memory_counts = {}
    for layer in MEMORY_LAYERS:
        data, err = read_json(MEMORY_DIR / f"{layer}.json")
        if err:
            continue
        memory_counts[layer] = len(data) if isinstance(data, list) else len(data.get("facts", []))

    active_host = None
    installed_hosts = []
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        import coresentinel_adapters as adapters
        for adapter in adapters.get_adapters():
            installed, active, _ = adapters.detect_adapter(adapter, target_dir)
            if installed or active:
                installed_hosts.append(adapter["id"])
            if active and not active_host:
                active_host = adapter["id"]
    except ImportError as e:
        print(f"[!] Adapter layer unavailable ({e}) — host status omitted", file=sys.stderr)

    _, branch, _ = run_cmd("git rev-parse --abbrev-ref HEAD", cwd=target_dir)
    _, dirty, _ = run_cmd("git status --short", cwd=target_dir)
    stack = detect_stack(Path(target_dir).resolve())

    snapshot = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project": Path(target_dir).resolve().name,
        "stack": stack,
        "git": {"branch": branch or None, "uncommitted": len(dirty.splitlines()) if dirty else 0},
        "host": {"active": active_host, "installed": installed_hosts},
        "gates": {"passed": gate_pass, "total": len(gates)},
        "memory": memory_counts,
        "audit": {"runs": len(runs), "last": last_run.get("run_id") if last_run else None},
        "evolution": {"pending_review": len(pending)},
    }

    if emit_json:
        print(json.dumps(snapshot, indent=2))
        return snapshot

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Status")
    print("=" * 64)
    uncommitted = snapshot["git"]["uncommitted"]
    git_line = (branch or "no repository")
    if branch:
        git_line += " — {} uncommitted change(s)".format(uncommitted) if uncommitted else " — clean"
    audit_line = "{} recorded".format(len(runs))
    if last_run:
        audit_line += " (latest {})".format(last_run.get("run_id"))

    print(f"  Project        : {snapshot['project']} ({', '.join(stack)})")
    print(f"  Git            : {git_line}")
    print(f"  Active Host    : {active_host or 'none detected'} ({len(installed_hosts)} installed)")
    print("  " + RULE)
    print(f"  Quality Gates  : {gate_pass}/{len(gates)} PASS" if gates
          else "  Quality Gates  : not yet run")
    print(f"  Memory Entries : {sum(memory_counts.values())} across {len(memory_counts)} layers")
    print(f"  Audit Runs     : {audit_line}")
    print(f"  Evolution      : {len(pending)} proposal(s) pending review")
    print("  " + RULE)
    print("  Next: coresentinel doctor | coresentinel verify | coresentinel score")
    print("=" * 64 + "\n")
    return snapshot


if __name__ == "__main__":
    argv = sys.argv[1:]
    cmd = argv[0].lower() if argv else "doctor"
    if cmd == "status":
        run_status(".", "--json" in argv)
    else:
        sys.exit(run_doctor(".", "--verbose" in argv or "-v" in argv, "--json" in argv))
