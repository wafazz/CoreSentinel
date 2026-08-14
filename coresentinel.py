#!/usr/bin/env python3
"""
CoreSentinel CLI — Universal AI Agent Governance, Memory & Verification Engine

The command surface is defined by the COMMANDS registry at the bottom of this file.
Run 'coresentinel help' for the grouped index, or 'coresentinel help <command>' for
usage on any single command.

  Setup & Diagnostics    init · doctor · status
  Context & Memory       context · memory · decision
  Verification & Review  verify · review · gate · check
  Squad & Governance     agent · audit · score · evolve
  Integration            adapter · stats · hooks
"""

import sys
import json
import platform
import subprocess
from pathlib import Path
import coresentinel_memory as mem

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORESENTINEL_DIR = Path(__file__).parent.resolve()

VERSION_FILE = CORESENTINEL_DIR / "VERSION"

def read_version():
    """Single source of truth for the product version. Never guesses a number."""
    try:
        version = VERSION_FILE.read_text(encoding="utf-8-sig").strip()
    except OSError as e:
        print(f"[!] VERSION file unreadable ({e}) — version reported as 'unknown'", file=sys.stderr)
        return "unknown"
    if not version:
        print("[!] VERSION file is empty — version reported as 'unknown'", file=sys.stderr)
        return "unknown"
    return version

def print_header(title):
    print("\n" + "=" * 64)
    print(f"  🛡️  CoreSentinel Engine — {title}")
    print("=" * 64)

def detect_project_type(target_dir):
    p = Path(target_dir)
    types = []
    if (p / "package.json").exists():
        types.append("Node/TypeScript")
    if (p / "pytest.ini").exists() or (p / "requirements.txt").exists() or (p / "pyproject.toml").exists():
        types.append("Python")
    if (p / "composer.json").exists():
        types.append("PHP")
    if (p / "Cargo.toml").exists():
        types.append("Rust")
    if (p / "go.mod").exists():
        types.append("Go")
    return types if types else ["General"]

def run_evidence_verification(target_dir=".", claim="Code changes and protocol execution verified",
                              emit_json=False, base=None):
    """Delegates to the evidence engine.

    The implementation that lived here awarded 45 of its 100 points from three
    checks that executed nothing, so an empty directory verified a claim about a
    fixed authentication vulnerability. Scoring now lives in
    coresentinel_evidence.py, where every point traces to a command and its exit
    code, and a check that could not run reports UNKNOWN instead of a pass.
    """
    import coresentinel_evidence as evidence
    return evidence.print_verification(target_dir, claim, emit_json, base)

def handle_memory_cmd(args):
    sub = args[0].lower() if args else "show"
    # Project-scoped layers resolve against this directory; --project overrides it.
    target = flag_value(args, "--project")
    if target is None:
        target = args[1] if len(args) > 1 and not args[1].startswith("--") and sub == "show" else "."

    emit_json = "--json" in args
    apply_changes = "--apply" in args

    if sub in ("add", "fact"):
        layer = flag_value(args, "--layer", "project")
        fact = flag_value(args, "--fact", "New fact")
        src = flag_value(args, "--source", "User input")
        confidence = flag_value(args, "--confidence", "0.95")
        try:
            conf = float(confidence)
        except (TypeError, ValueError):
            print(f"[!] --confidence expects a number between 0 and 1, got '{confidence}'.",
                  file=sys.stderr)
            return 1
        recorded = mem.add_fact(layer, fact, conf, src, target,
                                pinned="--pinned" in args, transferable="--transferable" in args)
        if recorded:
            emit_audited("MemoryCreated", target,
                         {"layer": layer, "fact": fact, "confidence": conf, "source": src})
        return 0 if recorded else 1

    if sub == "recall":
        return handle_recall_cmd(args[1:])

    import coresentinel_lifecycle as lifecycle

    if sub == "decay":
        return lifecycle.print_decay(target, apply_changes, emit_json)
    if sub == "promote":
        return lifecycle.print_promote(target, apply_changes, emit_json)
    if sub == "consolidate":
        return lifecycle.print_consolidate(target, apply_changes, emit_json)
    if sub == "compact":
        budget = int(flag_value(args, "--budget", lifecycle.COMPACT_BUDGET))
        return lifecycle.print_compact(target, budget, apply_changes, emit_json)
    if sub in ("verify", "reverify"):
        match = flag_value(args, "--match") or free_arg(args, 1)
        confidence = flag_value(args, "--confidence")
        report = lifecycle.reverify(match, target,
                                    float(confidence) if confidence else None,
                                    flag_value(args, "--layer"), "--pinned" in args)
        if report.get("error"):
            print(f"[!] {report['error']}", file=sys.stderr)
            return 1
        for item in report["updated"]:
            print(f"[✓] Re-verified ({item['layer']}) {item['fact']}: "
                  f"{item['from']} -> {item['to']}")
        if not report["updated"]:
            print(f"[!] No fact matches '{match}' — nothing re-verified.", file=sys.stderr)
            return 1
        return 0
    if sub == "snapshot":
        manifest = lifecycle.create_snapshot(target, flag_value(args, "--label", "manual"))
        print(f"[✓] Snapshot {manifest['id']} captured {len(manifest['files'])} layer(s)")
        return 0
    if sub == "snapshots":
        return lifecycle.print_snapshots(target, emit_json)
    if sub == "restore":
        snap_id = free_arg(args, 1)
        report = lifecycle.restore_snapshot(snap_id, target, apply_changes)
        if report.get("error"):
            print(f"[!] {report['error']}", file=sys.stderr)
            return 1
        for item in report["restored"]:
            print(f"  {'restored' if apply_changes else 'would restore'} {item['layer']} -> {item['path']}")
        if not apply_changes:
            print(f"  Dry run — apply with: coresentinel memory restore {snap_id} --apply")
        return 0

    if sub == "journal":
        return handle_journal_cmd(args[1:])

    mem.show_memory_summary(target)


# Flags that consume the token after them. Needed so a query like
# `recall "auth" --layer project` does not swallow "project" as a search term.
VALUE_FLAGS = {"--project", "--layer", "--min-confidence", "--limit", "--label",
               "--budget", "--match", "--confidence", "--tags", "--agent",
               "--entry", "--days", "--older-than", "--source", "--fact",
               "--title", "--reason", "--chosen", "--alts", "--query", "--claim",
               "--host", "--scope", "--gate", "--target", "--change", "--evidence",
               "--impact", "--approver", "--task", "--read", "--modified",
               "--created-tests", "--executed-tests", "--result",
               "--by", "--problem", "--context", "--author", "--relates-to", "--status",
               "--objective", "--roles", "--depth", "--as",
               "--root-cause", "--resolution", "--learning", "--severity",
               "--detected-by", "--class", "--decision", "--file", "--commit",
               "--test", "--pattern", "--subject",
               "--candidate", "--name", "--solution", "--stack", "--gotchas",
               "--category", "--first-used-in", "--incident",
               "--host", "--port", "--offset", "--base"}

# Every flag read with flag_value() must appear above, or free_args() treats its
# value as a positional argument — which is how `verify --claim "fixed the login
# bug"` came to verify a directory named after the claim. A test enforces it.


def dangling_flag(args):
    """A value-flag used as the final token, e.g. `memory add --fact x --layer`.

    These used to reach `args[args.index(flag) + 1]` and raise IndexError, so the
    user got a traceback where a usage error belonged.
    """
    return args[-1] if args and args[-1] in VALUE_FLAGS else None


def free_args(args):
    """Positional arguments, with flags and the values they consume removed."""
    values, skip = [], False
    for token in args:
        if skip:
            skip = False
            continue
        if token.startswith("-"):
            skip = token in VALUE_FLAGS
            continue
        values.append(token)
    return values


def free_arg(args, index=0, default=""):
    values = free_args(args)
    return values[index] if len(values) > index else default


def handle_recall_cmd(args):
    import coresentinel_recall as recall_engine
    query = " ".join(free_args(args))
    target = flag_value(args, "--project", ".")
    layers = flag_value(args, "--layer")
    minimum = float(flag_value(args, "--min-confidence", 0.0))
    limit = int(flag_value(args, "--limit", 20))
    return recall_engine.print_recall(query, target,
                                      [l.strip() for l in layers.split(",")] if layers else None,
                                      minimum, limit, "--json" in args)


def handle_journal_cmd(args):
    import coresentinel_recall as recall_engine
    sub = args[0].lower() if args and not args[0].startswith("-") else "show"
    target = flag_value(args, "--project", ".")

    if sub == "add":
        entry = flag_value(args, "--entry") or free_arg(args, 1)
        if not entry:
            print("[!] An entry is required: coresentinel journal add --entry \"...\"", file=sys.stderr)
            return 1
        written = recall_engine.add_journal_entry(entry, flag_value(args, "--tags"),
                                                  flag_value(args, "--agent", "Iris"), target)
        return 0 if written else 1

    if sub == "archive":
        days = int(flag_value(args, "--older-than", 30))
        report = recall_engine.archive_journal(days, target, "--apply" in args)
        for item in report["archived_days"]:
            verb = "archived" if report["applied"] else "would archive"
            print(f"  {verb} {item['date']} ({item['entries']} entries) -> {item['month']}.json")
        if not report["archived_days"]:
            print(f"  No journal days older than {days} days.")
        elif not report["applied"]:
            print(f"  Dry run — apply with: coresentinel journal archive --older-than {days} --apply")
        return 0

    days = flag_value(args, "--days")
    entries = recall_engine.read_journal(target, int(days) if days else None)
    if "--json" in args:
        print(json.dumps({"entries": entries, "count": len(entries)}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  📓 CoreSentinel Session Journal")
    print("=" * 64)
    if not entries:
        print("  No entries recorded yet.")
        print("  Record one: coresentinel journal add --entry \"...\" --tags \"refactor,api\"")
        print("=" * 64 + "\n")
        return 0

    current_day = None
    for item in entries:
        if item["date"] != current_day:
            current_day = item["date"]
            print(f"\n  {current_day}{'  (archived)' if item.get('archived') else ''}")
            print("  " + "-" * 60)
        tags = ", ".join(item.get("tags", []) or [])
        print(f"     • {item.get('entry')}")
        print(f"       {item.get('time', '-')} · {item.get('agent', '-')}{' · ' + tags if tags else ''}")
    print("\n" + "=" * 64 + "\n")
    return 0

def handle_decision_cmd(args):
    from coresentinel_core.decisions import ledger, contradiction, schema

    sub = args[0].lower() if args and not args[0].startswith("-") else "list"
    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args

    if sub == "add":
        record = ledger.add(
            target,
            title=flag_value(args, "--title", "Architectural decision"),
            reason=flag_value(args, "--reason", "Engineering requirement"),
            chosen=flag_value(args, "--chosen", "Selected solution"),
            alternatives=flag_value(args, "--alts"),
            problem=flag_value(args, "--problem"),
            context=flag_value(args, "--context"),
            evidence=flag_value(args, "--evidence"),
            author=flag_value(args, "--author"),
            agent=flag_value(args, "--agent"),
            confidence=flag_value(args, "--confidence"),
            impact=flag_value(args, "--impact", "High"),
            status=flag_value(args, "--status", schema.ACCEPTED),
            related_files=flag_value(args, "--relates-to"))
        if not record:
            return 1
        emit_audited("DecisionCreated", target,
                     {"decision": record["id"], "title": record["title"],
                      "chosen": record["chosen"], "scope": record["scope"]})
        filled = schema.completeness(record)
        print(f"\n[✓] Recorded [{record['id']}] ({record['scope']} scope): "
              f"'{record['title']}' → chosen: '{record['chosen']}'")
        print(f"    Schema {filled['percent']}% complete"
              + (f"; not recorded: {', '.join(filled['missing'][:6])}" if filled["missing"] else ""))
        print(f"    Ledger: {ledger.ledger_path(target)}\n")
        return 0

    if sub == "verify":
        change = flag_value(args, "--change") or free_arg(args, 1)
        if not change:
            print("[!] What change? e.g. coresentinel decision verify "
                  "--change \"switch from Redis to database sessions\"", file=sys.stderr)
            return 1
        report = contradiction.verify(change, target)
        if emit_json:
            print(json.dumps(report, indent=2))
            return 1 if report["blocking"] else 0

        print("\n" + "=" * 64)
        print("  📜 CoreSentinel Decision Check")
        print("=" * 64)
        print(f"  Proposed  : {change}")
        print(f"  Checked   : {report['considered']} accepted decision(s)")
        print("  " + "-" * 60)
        if not report["findings"]:
            print("  No recorded decision governs this change.")
            print("=" * 64 + "\n")
            return 0
        for finding in report["findings"]:
            mark = "✗" if finding["blocking"] else "·"
            print(f"  [{mark}] {finding['verdict']}  {finding['decision_id']}: {finding['title']}")
            print(f"      {finding['detail']}")
            if finding["reason"]:
                print(f"      Reason recorded : {finding['reason']}")
            if finding["evidence"]:
                print(f"      Evidence        : {finding['evidence']}")
        print("  " + "-" * 60)
        print(f"  Verdict   : {report['verdict']}")
        if report["blocking"]:
            print("  This change reverses a recorded decision. Get review, then record the")
            print("  reversal so it stays visible:")
            print("    coresentinel decision add --title \"...\" --reason \"...\" --chosen \"...\"")
            print(f"    coresentinel decision supersede {report['findings'][0]['decision_id']} "
                  "--by <new-id> --reason \"...\"")
        print("=" * 64 + "\n")
        return 1 if report["blocking"] else 0

    if sub == "supersede":
        old_id = free_arg(args, 1)
        new_id = flag_value(args, "--by")
        if not old_id or not new_id:
            print("[!] Usage: coresentinel decision supersede ADR-042 --by ADR-050 "
                  "[--reason \"...\"]", file=sys.stderr)
            return 1
        report = ledger.supersede(old_id, new_id, target, flag_value(args, "--reason"))
        if report.get("error"):
            print(f"[!] {report['error']}", file=sys.stderr)
            return 1
        emit_audited("DecisionChanged", target,
                     {"decision": report["superseded"]["id"],
                      "superseded_by": report["superseding"]["id"],
                      "reason": flag_value(args, "--reason")})
        print(f"\n[✓] {report['superseded']['id']} is now SUPERSEDED by "
              f"{report['superseding']['id']}")
        if report.get("reason"):
            print(f"    Reason: {report['reason']}")
        print("")
        return 0

    if sub == "show":
        record = ledger.get(free_arg(args, 1), target)
        if not record:
            print(f"[!] Decision '{free_arg(args, 1)}' not found.", file=sys.stderr)
            return 1
        if emit_json:
            print(json.dumps(record, indent=2))
            return 0
        filled = schema.completeness(record)
        print("\n" + "=" * 64)
        print(f"  📜 {record['id']} — {record['title']}")
        print("=" * 64)
        for label, key in [("Status", "status"), ("Scope", "scope"), ("Chosen", "chosen"),
                           ("Problem", "problem"), ("Context", "context"), ("Reason", "reason"),
                           ("Evidence", "evidence"), ("Impact", "impact"),
                           ("Confidence", "confidence"), ("Author", "author"),
                           ("Agent", "agent"), ("Recorded", "created_at"),
                           ("Supersedes", "supersedes"), ("Superseded by", "superseded_by")]:
            if record.get(key) not in (None, "", []):
                print(f"  {label:<14}: {record[key]}")
        for label, key in [("Alternatives", "alternatives"), ("Related files", "related_files"),
                           ("Related incidents", "related_incidents"),
                           ("Related decisions", "related_decisions")]:
            if record.get(key):
                print(f"  {label:<14}: {', '.join(record[key])}")
        print("  " + "-" * 60)
        print(f"  Schema {filled['percent']}% complete ({filled['present']}/{filled['total']} fields)")
        if filled["missing"]:
            print(f"  Not recorded  : {', '.join(filled['missing'])}")
        print("=" * 64 + "\n")
        return 0

    query = flag_value(args, "--query") or (free_arg(args, 1) if sub == "list" else None)
    # A bound project reads its own ledger alone, deliberately: unioning the
    # scopes surfaced one repository's decisions as governance for another, and
    # the noise trained people to skip the check. But the Core ledger was then
    # unreachable from inside a project — an install that recorded every
    # decision at Core scope before binding its first project could not see any
    # of them. --core asks for them explicitly without changing the default.
    records = ledger.load(target, include_core="--core" in args)
    if query:
        needle = query.lower()
        records = [r for r in records
                   if needle in " ".join(str(r.get(k, "")).lower()
                                         for k in ("decision", "reason", "chosen", "problem"))]

    if emit_json:
        print(json.dumps({"decisions": records, "count": len(records)}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  📜 CoreSentinel Architecture Decision Ledger")
    print("=" * 64)
    print(f"  Ledger : {ledger.ledger_path(target)}")
    if not records:
        print("  (No architecture decisions recorded yet)")
        print("  Record one: coresentinel decision add --title \"...\" --reason \"...\" "
              "--chosen \"...\"")
        print("=" * 64 + "\n")
        return 0

    print(f"  Showing {len(records)} decision(s)")
    print("  " + "-" * 60)
    for record in records:
        flag = "" if schema.is_binding(record) else f"  [{record.get('status')}]"
        print(f"\n  [{record['id']}] {record['title']}{flag}")
        print(f"     Chosen       : {record.get('chosen')}")
        print(f"     Reason       : {record.get('reason')}")
        if record.get("alternatives"):
            print(f"     Alternatives : {', '.join(record['alternatives'])}")
        if record.get("evidence"):
            print(f"     Evidence     : {record['evidence']}")
        print(f"     Scope        : {record.get('scope')} · Recorded: {record.get('created_at')}")
    print("\n  " + "-" * 60)
    print("  Before reversing one: coresentinel decision verify --change \"...\"")
    print("=" * 64 + "\n")
    return 0

def flag_value(args, flag, default=None):
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return default


def positional(args, index=0, default="."):
    """Positional arguments only — flags and the values they consume are skipped.

    It used to drop flags but keep their values, so `verify --claim "fixed the
    login bug"` read the claim text as the target directory and verified a
    directory that did not exist. Delegating to free_args() applies the one
    definition of what a flag consumes, rather than a second, weaker copy of it.
    """
    values = free_args(args)
    return values[index] if len(values) > index else default


def emit_audited(event, target=".", payload=None):
    """Emit an event so the audit sink records it.

    Auditing is wired through the event bus rather than by calling the ledger
    from a dozen places: a subsystem added later either emits and is recorded,
    or does not and shows up as an unrecorded subject in `audit coverage`.
    Never fails the operation it is recording.
    """
    try:
        from coresentinel_core.runtime.container import Runtime
        runtime = Runtime.bootstrap(target)
        runtime.events.emit(event, payload or {})
        runtime.shutdown()
    except Exception as e:
        print(f"[!] {event} not audited ({e})", file=sys.stderr)


def cmd_init(args):
    import coresentinel_init as initializer
    return initializer.run_init(positional(args), flag_value(args, "--host"),
                                "--apply" in args, "--force" in args)


def cmd_doctor(args):
    import coresentinel_doctor as doctor
    return doctor.run_doctor(positional(args), "--verbose" in args or "-v" in args, "--json" in args)


def cmd_status(args):
    import coresentinel_doctor as doctor
    doctor.run_status(positional(args), "--json" in args)


def cmd_context(args):
    task = flag_value(args, "--task")
    if not task:
        import coresentinel_context as context
        context.print_context(positional(args), "--json" in args)
        return 0

    from coresentinel_core.memory import assembly
    budget = flag_value(args, "--budget", assembly.DEFAULT_BUDGET_TOKENS)
    try:
        budget = int(budget)
    except (TypeError, ValueError):
        print(f"[!] --budget expects a whole number of tokens, got '{budget}'.", file=sys.stderr)
        return 1

    pack = assembly.assemble(task, positional(args), budget,
                             float(flag_value(args, "--min-confidence", 0.0)))
    if "--json" in args:
        print(json.dumps(pack, indent=2))
        return 0
    print("\n" + assembly.render(pack) + "\n")
    return 0


def cmd_review(args):
    import coresentinel_review as review
    return review.print_review(positional(args), "--strict" in args, "--json" in args,
                               flag_value(args, "--base"))


def cmd_verify(args):
    claim = flag_value(args, "--claim", "Code changes and protocol execution verified")
    target = positional(args)
    base = flag_value(args, "--base")
    code = run_evidence_verification(target, claim, "--json" in args, base)
    emit_audited("VerificationCompleted", target,
                 {"claim": claim,
                  "change_source": f"{base}...HEAD" if base else "working tree",
                  "result": {0: "VERIFIED", 1: "UNVERIFIED", 2: "INDETERMINATE"}.get(code)})
    return code


def cmd_memory(args):
    return handle_memory_cmd(args)


def cmd_recall(args):
    return handle_recall_cmd(args)


def cmd_brief(args):
    import coresentinel_recall as recall_engine
    days = flag_value(args, "--days")
    return recall_engine.print_briefing(flag_value(args, "--project", positional(args)),
                                        "--json" in args, int(days) if days else 7)


def cmd_journal(args):
    return handle_journal_cmd(args)


def cmd_decision(args):
    # The exit code used to be discarded here, so `decision verify` reported a
    # contradiction and still exited 0 — invisible to any CI step branching on it.
    return handle_decision_cmd(args)


def cmd_agent(args):
    import coresentinel_squad as squad
    sub = args[0].lower() if args and not args[0].startswith("--") else "list"

    if sub in ("permissions", "perms"):
        return show_agent_permissions(free_arg(args, 1), "--json" in args)
    if sub == "run":
        return run_agent(free_arg(args, 1), args)

    if sub == "list":
        squad.list_squad()
    elif sub == "show":
        squad.show_agent_contract(args[1] if len(args) > 1 else "Architect")
    else:
        squad.show_agent_contract(args[0])
    return 0


def show_agent_permissions(name, emit_json=False):
    from coresentinel_core.agents import registry, permissions as perms

    if not name:
        overview = registry.audit()
        if emit_json:
            print(json.dumps(overview, indent=2))
            return 0
        print("\n" + "=" * 64)
        print("  🔐 CoreSentinel Agent Permissions")
        print("=" * 64)
        print(f"  {len(overview['declared'])}/{overview['total']} contracts declare "
              "permissions explicitly")
        if overview["defaulted"]:
            print(f"  Defaulted to read-only: {', '.join(overview['defaulted'])}")
        if overview["escalation_holders"]:
            print("  " + "-" * 60)
            print("  Contracts that can escalate beyond the sandbox:")
            for agent, granted in overview["escalation_holders"].items():
                print(f"      {agent:<12} {', '.join(granted)}")
        print("  " + "-" * 60)
        print("  Inspect one: coresentinel agent permissions Scout")
        print("=" * 64 + "\n")
        return 0

    contract = registry.get(name)
    if not contract:
        print(f"[!] Unknown agent '{name}'. Known: {', '.join(registry.names())}",
              file=sys.stderr)
        return 1

    permission_set = registry.permissions_for(name)
    summary = permission_set.summary()
    if emit_json:
        print(json.dumps({"agent": contract["name"], "authority": contract["authority"],
                          "permissions": summary}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print(f"  🔐 {contract['name']} — enforced permissions")
    print("=" * 64)
    print(f"  Authority : {contract['authority']}")
    print("  " + "-" * 60)
    for permission in perms.PERMISSIONS:
        detail = summary[permission]
        scopes = f"  scope: {', '.join(detail['scopes'])}" if detail["scopes"] else ""
        print(f"  {permission:<20} {detail['level']:<8}{scopes}")
    print("  " + "-" * 60)
    print("  These are enforced by the sandbox, not merely declared: an operation")
    print("  outside this set fails at the point of use and the denial is audited.")
    print("=" * 64 + "\n")
    return 0


def run_agent(name, args):
    from coresentinel_core.agents import registry, orchestrator, protocol
    from coresentinel_core.runtime.container import Runtime

    if not name:
        print("[!] Which agent? e.g. coresentinel agent run Security --objective \"...\"",
              file=sys.stderr)
        return 1
    if not registry.get(name):
        print(f"[!] Unknown agent '{name}'. Known: {', '.join(registry.names())}",
              file=sys.stderr)
        return 1

    objective = flag_value(args, "--objective") or flag_value(args, "--task") \
        or "Run the agent's standing responsibility"
    target = flag_value(args, "--project", ".")

    runtime = Runtime.bootstrap(target)
    task = protocol.build_task(objective, registry.get(name)["name"], project=target)
    result = orchestrator.run_task(task, target, runtime,
                                   interactive="--interactive" in args)
    runtime.shutdown()

    if "--json" in args:
        print(json.dumps(result, indent=2))
    else:
        print(orchestrator.render({"plan": {"objective": objective, "executable": 0,
                                            "unsupported": 0},
                                   "results": [result],
                                   "summary": protocol.summarise([result]),
                                   "verdict": result["status"]}) + "\n")
    return 0 if result["status"] in (protocol.COMPLETED, protocol.UNSUPPORTED) else 1


def cmd_task(args):
    from coresentinel_core.agents import orchestrator
    from coresentinel_core.runtime.container import Runtime

    sub = args[0].lower() if args and not args[0].startswith("-") else "run"
    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args

    if sub == "list":
        runtime = Runtime.bootstrap(target)
        recorded = runtime.store.tasks.recent(int(flag_value(args, "--limit", 20)))
        runtime.shutdown()
        if emit_json:
            print(json.dumps({"tasks": recorded, "count": len(recorded)}, indent=2))
            return 0
        print("\n" + "=" * 64)
        print("  📋 CoreSentinel Tasks")
        print("=" * 64)
        if not recorded:
            print("  Nothing recorded yet. Run one:")
            print("    coresentinel task run --objective \"Add Redis caching\"")
        for item in recorded:
            print(f"  [{item.get('status', '?'):<11}] {item.get('agent', '?'):<12} "
                  f"{item.get('objective', '')[:60]}")
        print("=" * 64 + "\n")
        return 0

    objective = flag_value(args, "--objective") or free_arg(args, 1)
    if not objective:
        print("[!] What is the objective? e.g. coresentinel task run "
              "--objective \"Add Redis caching to product listing\"", file=sys.stderr)
        return 1

    roles = flag_value(args, "--roles")
    if sub == "plan":
        built = orchestrator.plan(objective, [r.strip() for r in roles.split(",")] if roles else None,
                                  target_dir=target)
        if emit_json:
            print(json.dumps(built, indent=2))
            return 0
        print("\n" + "=" * 64)
        print(f"  📋 Plan — {objective}")
        print("=" * 64)
        for index, task in enumerate(built["tasks"], 1):
            mark = "▶" if task["executable"] else "·"
            print(f"  {index:2}. [{mark}] {task['agent']:<12} {task['role_description']}")
        print("  " + "-" * 60)
        print(f"  {built['executable']} role(s) can run now; "
              f"{built['unsupported']} await an agent adapter.")
        print("=" * 64 + "\n")
        return 0

    runtime = Runtime.bootstrap(target)
    run = orchestrator.execute(objective, target,
                               [r.strip() for r in roles.split(",")] if roles else None,
                               runtime, "--interactive" in args)
    runtime.shutdown()

    if emit_json:
        print(json.dumps(run, indent=2))
    else:
        print(orchestrator.render(run) + "\n")
    return 1 if run["verdict"] == "BLOCKED" else 0


def cmd_gate(args):
    import coresentinel_gates as gates
    sub = args[0].lower() if args and not args[0].startswith("--") else "status"
    emit_json = "--json" in args
    report_style = "--report" in args
    if sub == "run":
        target = positional(args, 1)
        code = gates.run_all_gates(target, emit_json, flag_value(args, "--objective"),
                                   report_style)
        emit_audited("QualityGateFailed" if code else "QualityGatePassed", target,
                     {"objective": flag_value(args, "--objective"),
                      "result": "BLOCKED" if code else "APPROVED"})
        return code
    if sub == "reset":
        gates.reset_gates()
        return 0
    if sub == "waive":
        gate_name = flag_value(args, "--gate") or positional(args, 1, "")
        reason = flag_value(args, "--reason") or positional(args, 2, "")
        return 0 if gates.waive_gate(gate_name, reason) else 1
    return gates.show_status(positional(args, 1), emit_json, report_style)


def handle_learning(sub, args):
    """Observation, candidates, and the apply/revert half of controlled evolution."""
    import coresentinel_evolve as evolve
    from coresentinel_core.learning import candidates, observer, apply as applier
    from coresentinel_core.runtime.container import Runtime

    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args
    runtime = Runtime.bootstrap(target)
    store = runtime.store

    try:
        if sub == "observe":
            report = observer.run(store, target)
            if emit_json:
                print(json.dumps(report, indent=2))
                return 0
            print("\n" + "=" * 64)
            print("  🔬 CoreSentinel Learning Observation")
            print("=" * 64)
            print(f"  {report['observed']} candidate(s) from incidents, failures and patterns")
            print("  " + "-" * 60)
            for candidate in report["candidates"]:
                mark = {"CORROBORATED": "▶", "PROPOSED": "·",
                        "REJECTED": "✗"}.get(candidate["status"], " ")
                print(f"  [{mark}] {candidate['id']}  {candidate['status']:<13} "
                      f"{len(candidate['sources'])} source(s)")
                print(f"      {candidate['lesson'][:70]}")
            print("  " + "-" * 60)
            print(f"  {len(report['ready'])} ready to propose "
                  f"(needs {candidates.MIN_EVIDENCE} distinct sources).")
            print("  An observation is not a lesson, and a lesson is not a rule.")
            print("  Propose one: coresentinel evolve propose --candidate <id> --target ...")
            print("=" * 64 + "\n")
            return 0

        if sub == "candidates":
            overview = candidates.summary(store)
            if emit_json:
                print(json.dumps(overview, indent=2))
                return 0
            print("\n" + "=" * 64)
            print("  🔬 CoreSentinel Learning Candidates")
            print("=" * 64)
            for status, count in overview["by_status"].items():
                print(f"  {status:<14} {count}")
            print("  " + "-" * 60)
            print(f"  Evidence threshold: {overview['evidence_threshold']} distinct sources")
            print("=" * 64 + "\n")
            return 0

        if sub == "reject":
            report = candidates.reject(store, free_arg(args, 1), flag_value(args, "--reason"))
            if report.get("error"):
                print(f"[!] {report['error']}", file=sys.stderr)
                return 1
            print(f"[✓] {report['candidate']['id']} rejected. It will not resurface.")
            return 0

        if sub == "promote":
            report = candidates.promote(store, free_arg(args, 1), flag_value(args, "--reason"))
            if report.get("error"):
                print(f"[!] {report['error']}", file=sys.stderr)
                return 1
            print(f"[✓] {report['candidate']['id']} promoted past the evidence threshold.")
            return 0

        proposal = evolve.get_proposal(free_arg(args, 1))
        if not proposal:
            print(f"[!] Proposal '{free_arg(args, 1)}' not found.", file=sys.stderr)
            return 1

        if sub == "apply":
            report = applier.apply(proposal)
            if report.get("error"):
                print(f"\n[!] {report['error']}", file=sys.stderr)
                if report.get("supported"):
                    print("    Changes that can be applied automatically:", file=sys.stderr)
                    for name, how in report["supported"].items():
                        print(f"      {name:<24} {how}", file=sys.stderr)
                if report.get("detail"):
                    print(f"    {report['detail']}", file=sys.stderr)
                return 1

            evolve.update_proposal(proposal["id"], review_status=applier.APPLIED,
                                   applied_at=report["applied_at"],
                                   snapshot=report["snapshot"])
            runtime.events.emit("RuleProposed",
                                {"proposal": proposal["id"], "result": "APPLIED",
                                 "target": report["target"], "detail": report["detail"]})
            print(f"\n[✓] {proposal['id']} applied to {Path(report['target']).name}")
            print(f"    Change   : {report['detail']}")
            print(f"    Snapshot : {Path(report['snapshot']).name}")
            print(f"    Reverse it any time: coresentinel evolve revert {proposal['id']}\n")
            return 0

        report = applier.revert(proposal)
        if report.get("error"):
            print(f"[!] {report['error']}", file=sys.stderr)
            return 1
        evolve.update_proposal(proposal["id"], review_status=applier.REVERTED,
                               applied_at=None)
        runtime.events.emit("RuleProposed",
                            {"proposal": proposal["id"], "result": "REVERTED"})
        print(f"\n[✓] {proposal['id']} reverted from {Path(report['snapshot']).name}")
        print(f"    Restored byte-identically: {report['identical']}\n")
        return 0
    finally:
        runtime.shutdown()


def cmd_pattern(args):
    from coresentinel_core.patterns import ledger as patterns

    sub = args[0].lower() if args and not args[0].startswith("-") else "list"
    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args

    if sub == "add":
        record = patterns.add(
            target,
            name=flag_value(args, "--name"),
            problem=flag_value(args, "--problem"),
            solution=flag_value(args, "--solution"),
            stack=flag_value(args, "--stack"),
            gotchas=flag_value(args, "--gotchas"),
            category=flag_value(args, "--category"),
            first_used_in=flag_value(args, "--first-used-in"),
            source=flag_value(args, "--source", "manual"),
            transferable="--transferable" in args,
            related_incidents=flag_value(args, "--incident"))
        if not record:
            return 1
        repeated = record["occurrences"] > 1
        print(f"\n[✓] {'Counted' if repeated else 'Recorded'} [{record['id']}]: {record['name']}")
        if repeated:
            print(f"    Seen {record['occurrences']}× now. Re-recording does not raise")
            print("    confidence — three sightings of a guess make one guess seen thrice.")
        print(f"    Library: {patterns.ledger_path(target)}\n")
        return 0

    if sub == "show":
        record = patterns.get(free_arg(args, 1), target)
        if not record:
            print(f"[!] Pattern '{free_arg(args, 1)}' not found.", file=sys.stderr)
            return 1
        if emit_json:
            print(json.dumps(record, indent=2))
            return 0
        print("\n" + "=" * 64)
        print(f"  ♻️  {record['id']} — {record['name']}")
        print("=" * 64)
        print(patterns.render_markdown(record))
        print("  " + "-" * 60)
        print(f"  scope {record['scope']} · confidence {record['confidence']} · "
              f"{'transferable' if record['transferable'] else 'project-local'}")
        print("=" * 64 + "\n")
        return 0

    records = patterns.load(target, include_core=True)
    overview = patterns.summary(target)
    if emit_json:
        print(json.dumps({"patterns": records, "summary": overview}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  ♻️  CoreSentinel Pattern Library")
    print("=" * 64)
    print(f"  Library : {patterns.ledger_path(target)}")
    if not records:
        print("  No patterns recorded yet.")
        print("  Record one: coresentinel pattern add --name \"...\" --problem \"...\" "
              "--solution \"...\"")
        print("=" * 64 + "\n")
        return 0
    print(f"  {overview['total']} pattern(s), {overview['transferable']} transferable")
    print("  " + "-" * 60)
    for record in records:
        seen = f"  ({record['occurrences']}×)" if record["occurrences"] > 1 else ""
        print(f"  [{record['id']}] {record['name']}{seen}")
        if record.get("problem"):
            print(f"      problem : {record['problem']}")
        if record.get("related_incidents"):
            print(f"      learned from: {', '.join(record['related_incidents'])}")
    print("=" * 64 + "\n")
    return 0


def cmd_evolve(args):
    import coresentinel_evolve as evolve
    sub = args[0].lower() if args and not args[0].startswith("--") else "list"

    if sub in ("observe", "candidates", "apply", "revert", "reject", "promote"):
        return handle_learning(sub, args)
    if sub == "propose":
        proposal = evolve.propose_evolution(
            flag_value(args, "--target", "anti-patterns.json"),
            flag_value(args, "--change", "Proposed rule change"),
            flag_value(args, "--evidence", "Empirical evidence"),
            flag_value(args, "--impact", "Low risk"),
            flag_value(args, "--candidate"))
        emit_audited("RuleProposed", ".",
                     {"proposal": proposal, "target": flag_value(args, "--target"),
                      "change": flag_value(args, "--change")})
    elif sub == "approve":
        identifier = positional(args, 1, "EVO-001")
        approver = flag_value(args, "--approver", "Fakrul")
        evolve.approve_proposal(identifier, approver)
        emit_audited("RuleProposed", ".",
                     {"proposal": identifier, "approved_by": approver,
                      "result": "APPROVED"})
    else:
        evolve.list_proposals()


def cmd_incident(args):
    from coresentinel_core.incidents import ledger as incidents
    from coresentinel_core.runtime.container import Runtime

    sub = args[0].lower() if args and not args[0].startswith("-") else "list"
    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args

    if sub == "create":
        runtime = Runtime.bootstrap(target)
        record = incidents.create(
            target,
            title=flag_value(args, "--title", "Untitled incident"),
            problem=flag_value(args, "--problem"),
            root_cause=flag_value(args, "--root-cause"),
            resolution=flag_value(args, "--resolution"),
            learning=flag_value(args, "--learning"),
            severity=flag_value(args, "--severity", incidents.MEDIUM),
            detected_by=flag_value(args, "--detected-by"),
            root_cause_class=flag_value(args, "--class"),
            related_decisions=flag_value(args, "--decision"),
            related_files=flag_value(args, "--file"),
            related_commits=flag_value(args, "--commit"),
            related_tests=flag_value(args, "--test"),
            related_patterns=flag_value(args, "--pattern"))
        if not record:
            runtime.shutdown()
            return 1
        runtime.events.emit("IncidentCreated",
                            {"incident": record["id"], "severity": record["severity"],
                             "title": record["title"]})
        runtime.shutdown()
        print(f"\n[✓] Recorded [{record['id']}] ({record['scope']} scope): {record['title']}")
        print(f"    Severity : {record['severity']} · Status: {record['status']}")
        if not record.get("learning"):
            print("    No learning recorded yet. The fix stops it now; the learning is")
            print("    what stops it recurring — add one with 'incident resolve'.")
        print(f"    Ledger   : {incidents.ledger_path(target)}\n")
        return 0

    if sub == "link":
        report = incidents.link(
            free_arg(args, 1), target,
            related_decisions=flag_value(args, "--decision"),
            related_files=flag_value(args, "--file"),
            related_commits=flag_value(args, "--commit"),
            related_tests=flag_value(args, "--test"),
            related_patterns=flag_value(args, "--pattern"),
            related_tasks=flag_value(args, "--task"))
        if report.get("error"):
            print(f"[!] {report['error']}", file=sys.stderr)
            return 1
        for field, values in report["linked"].items():
            print(f"[✓] {field}: {', '.join(values)}")
        return 0

    if sub == "resolve":
        report = incidents.resolve(free_arg(args, 1), target,
                                   flag_value(args, "--resolution"),
                                   flag_value(args, "--learning"))
        if report.get("error"):
            print(f"[!] {report['error']}", file=sys.stderr)
            return 1
        print(f"\n[✓] {report['incident']['id']} resolved.")
        if report.get("warning"):
            print(f"    [!] {report['warning']}")
        print("")
        return 0

    if sub == "show":
        record = incidents.get(free_arg(args, 1), target)
        if not record:
            print(f"[!] Incident '{free_arg(args, 1)}' not found.", file=sys.stderr)
            return 1
        if emit_json:
            print(json.dumps(record, indent=2))
            return 0
        print("\n" + "=" * 64)
        print(f"  🚨 {record['id']} — {record['title']}")
        print("=" * 64)
        for label, key in [("Severity", "severity"), ("Status", "status"),
                           ("Class", "root_cause_class"), ("Detected by", "detected_by"),
                           ("Occurred", "occurred_at"), ("Resolved", "resolved_at"),
                           ("Scope", "scope")]:
            if record.get(key):
                print(f"  {label:<14}: {record[key]}")
        print("  " + "-" * 60)
        for label, key in [("Problem", "problem"), ("Root cause", "root_cause"),
                           ("Resolution", "resolution"), ("Learning", "learning")]:
            print(f"  {label:<14}: {record.get(key) or '(not recorded)'}")
        linked = {k: v for k, v in record.items()
                  if k in incidents.LINK_FIELDS and v}
        if linked:
            print("  " + "-" * 60)
            for field, values in linked.items():
                print(f"  {field.replace('related_', ''):<14}: {', '.join(values)}")
        print("=" * 64 + "\n")
        return 0

    records = incidents.load(target)
    overview = incidents.summary(target)
    if emit_json:
        print(json.dumps({"incidents": records, "summary": overview}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  🚨 CoreSentinel Incident Ledger")
    print("=" * 64)
    print(f"  Ledger : {incidents.ledger_path(target)}")
    if not records:
        print("  No incidents recorded.")
        print("  Record one: coresentinel incident create --title \"...\" --problem \"...\"")
        print("=" * 64 + "\n")
        return 0
    print(f"  {overview['total']} incident(s), {overview['open']} still open")
    print("  " + "-" * 60)
    for record in records:
        print(f"  [{record['id']}] {record['severity']:<8} {record['status']:<10} "
              f"{record['title']}")
        if record.get("root_cause"):
            print(f"      root cause: {record['root_cause']}")
        if record.get("learning"):
            print(f"      learning  : {record['learning']}")
    if overview["without_learning"]:
        print("  " + "-" * 60)
        print(f"  Resolved with no learning recorded: "
              f"{', '.join(overview['without_learning'])}")
        print("  A fix stops it now. A learning is what stops it recurring.")
    print("=" * 64 + "\n")
    return 0


def cmd_audit(args):
    import coresentinel_audit as audit
    sub = args[0].lower() if args and not args[0].startswith("--") else "list"
    if sub in ("verify", "chain"):
        return verify_audit_chain(positional(args, 1), "--json" in args)
    if sub == "coverage":
        return audit_coverage(positional(args, 1), "--json" in args)
    if sub == "show":
        audit.show_run(positional(args, 1, "RUN-#9281"))
    elif sub == "record":
        audit.record_run(
            flag_value(args, "--agent", "Backend Engineer"),
            flag_value(args, "--task", "Feature implementation"),
            int(flag_value(args, "--read", "0")),
            int(flag_value(args, "--modified", "0")),
            int(flag_value(args, "--created-tests", "0")),
            int(flag_value(args, "--executed-tests", "0")),
            "PASS", "PASS", 100,
            flag_value(args, "--result", "PASS"))
    else:
        audit.list_runs()


def cmd_metrics(args):
    from coresentinel_core.services.facade import open_services

    sub = args[0].lower() if args and not args[0].startswith("-") else "show"
    emit_json = "--json" in args
    target = positional(args, 1 if sub in ("show", "coverage", "budgets") else 0)

    if sub == "budgets":
        return print_budgets(emit_json)

    services = open_services(target)
    try:
        report = services.call("metrics.get", {
            "subject": flag_value(args, "--subject"),
            "limit": flag_value(args, "--limit"),
            "offset": flag_value(args, "--offset", 0),
        })
    finally:
        services.runtime.shutdown()

    if emit_json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    coverage = report["coverage"]
    if sub == "coverage":
        print("\n" + "=" * 64)
        print("  📈 CoreSentinel Metrics Coverage")
        print("=" * 64)
        print(f"  {len(coverage['observed'])}/{coverage['total']} subjects have been measured here")
        print("  " + "-" * 60)
        for subject in coverage["observed"]:
            print(f"  [✓] {subject}")
        for subject in coverage["never_observed"]:
            print(f"  [ ] {subject}")
        print("  " + "-" * 60)
        print("  A subject with no series has never been exercised in this store, or")
        print("  nothing measures it. Neither is reported as a zero.")
        print("=" * 64 + "\n")
        return 0

    print("\n" + "=" * 64)
    print("  📈 CoreSentinel Metrics")
    print("=" * 64)
    if not report["series"]:
        print("  Nothing has been measured in this store yet.")
        print("  Run any command, then look again — series are written at shutdown.")
        print("=" * 64 + "\n")
        return 0

    print(f"  {'SUBJECT':<14} {'SERIES':<26} {'N':>7} {'MEAN':>10} {'MAX':>10}")
    print("  " + "-" * 60)
    for entry in report["series"]:
        mean = f"{entry['mean']:.2f}" if entry["mean"] is not None else "—"
        peak = f"{entry['max']:.2f}" if entry["max"] is not None else "—"
        print(f"  {entry['subject']:<14} {entry['name'][:26]:<26} "
              f"{entry['count']:>7} {mean:>10} {peak:>10}")

    page = report["page"]
    print("  " + "-" * 60)
    print(f"  {page['returned']} of {page['total']} series"
          + (f" — next: --offset {page['next_offset']}" if page["next_offset"] else ""))
    print(f"  {len(coverage['observed'])}/{coverage['total']} subjects measured "
          f"({', '.join(coverage['never_observed']) or 'none'} never observed)")

    verdict = report["budgets"]["verdict"]
    print(f"  Budgets: {verdict} — {report['budgets']['passed']} within, "
          f"{report['budgets']['failed']} over, {report['budgets']['unknown']} unmeasured")
    print("=" * 64 + "\n")
    return 1 if verdict == "OVER_BUDGET" else 0


def print_budgets(emit_json=False):
    """The published budgets themselves, measured or not."""
    from coresentinel_core.observability import budgets as budget_engine

    if emit_json:
        print(json.dumps({"budgets": budget_engine.BUDGETS}, indent=2, default=str))
        return 0

    print("\n" + "=" * 64)
    print("  📐 CoreSentinel Published Performance Budgets")
    print("=" * 64)
    for key in sorted(budget_engine.BUDGETS):
        budget = budget_engine.BUDGETS[key]
        slack = budget_engine.headroom(key)
        print(f"  {key}")
        print(f"      {budget['what']}")
        print(f"      limit {budget['limit']}{budget['unit']}"
              f" · measured {budget['measured']}{budget['unit']}"
              + (f" · {slack}x headroom" if slack else ""))
        if budget.get("basis"):
            print(f"      {budget['basis']}")
    print("  " + "-" * 60)
    print("  Every budget is asserted by the self-test suite. A change that")
    print("  exceeds one fails the build rather than being noticed later.")
    print("=" * 64 + "\n")
    return 0


def cmd_project(args):
    from coresentinel_core.project import discovery

    sub = args[0].lower() if args and not args[0].startswith("-") else "inspect"
    emit_json = "--json" in args
    verbose = "--verbose" in args or "-v" in args

    if sub == "list":
        from coresentinel_core.runtime.container import Runtime
        runtime = Runtime.bootstrap(positional(args, 1))
        known = runtime.store.projects.all()
        runtime.shutdown()
        if emit_json:
            print(json.dumps({"projects": known, "count": len(known)}, indent=2))
            return 0
        print("\n" + "=" * 64)
        print("  🧠 CoreSentinel Known Projects")
        print("=" * 64)
        if not known:
            print("  None registered yet. Register the current one:")
            print("    coresentinel project inspect --save")
        for record in known:
            print(f"  {record.get('name', '?'):<24} {record.get('stack') or 'unknown'}")
            print(f"      {record.get('root')}")
        print("=" * 64 + "\n")
        return 0

    target = positional(args, 1) if sub in ("inspect", "context") else positional(args)
    report = discovery.inspect(target)

    if "--save" in args:
        from coresentinel_core.runtime.container import Runtime
        runtime = Runtime.bootstrap(target)
        runtime.store.projects.append({
            "root": report["project"]["root"], "name": report["project"]["name"],
            "stack": ", ".join(report["dimensions"]["languages"]["values"]) or None,
            "summary": discovery.summary(report)})
        runtime.events.emit("ProjectInitialized", {"root": report["project"]["root"]})
        runtime.shutdown()

    if emit_json:
        print(json.dumps(report, indent=2))
        return 0
    print(discovery.render(report, verbose) + "\n")
    return 0


def cmd_knowledge(args):
    from coresentinel_core.knowledge import graph as knowledge_graph

    sub = args[0].lower() if args and not args[0].startswith("-") else "describe"
    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args
    built = knowledge_graph.build(target)

    if sub in ("query", "show"):
        needle = free_arg(args, 1)
        if not needle:
            print("[!] Which entity? e.g. coresentinel knowledge query ADR-042",
                  file=sys.stderr)
            return 1
        matches = built.find(needle)
        if not matches:
            print(f"[!] No entity matches '{needle}'.", file=sys.stderr)
            print(f"    The graph holds {built.describe()['entities']} entity(s). "
                  "List them: coresentinel knowledge describe --json", file=sys.stderr)
            return 1
        result = built.traverse(matches[0]["id"], int(flag_value(args, "--depth", 2)))
        if emit_json:
            print(json.dumps(result, indent=2))
            return 0
        print(knowledge_graph.render(result) + "\n")
        return 0

    if sub == "build":
        from coresentinel_core.runtime.container import Runtime
        runtime = Runtime.bootstrap(target)
        store = runtime.store
        store.knowledge_entities.clear()
        store.knowledge_relations.clear()
        for node in built.nodes.values():
            store.knowledge_entities.append({
                "entity_key": node["id"], "entity_type": node["type"],
                "label": node["label"], "attributes": node["attributes"]})
        for edge in built.edges:
            store.knowledge_relations.append({
                "record_id": edge["id"], "source": edge["source"],
                "relation_type": edge["type"], "target": edge["target"],
                "evidence": edge["evidence"]})
        detail = store.describe()
        runtime.shutdown()
        print(f"\n[✓] Snapshot written to the {detail['backend']} store: "
              f"{len(built.nodes)} entity(s), {len(built.edges)} relation(s)")
        print("    The graph is derived data — 'knowledge query' always rebuilds it,")
        print("    so a superseded decision can never linger in an answer.\n")
        return 0

    detail = built.describe()
    if emit_json:
        print(json.dumps({**detail, "graph": built.as_dict()}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  🕸️  CoreSentinel Knowledge Graph")
    print("=" * 64)
    print(f"  Entities  : {detail['entities']}")
    for entity_type, count in sorted(detail["by_type"].items()):
        print(f"      {entity_type:<14} {count}")
    print(f"  Relations : {detail['relations']}")
    for relation_type, count in sorted(detail["by_relation"].items()):
        print(f"      {relation_type:<14} {count}")
    dangling = built.dangling()
    print("  " + "-" * 60)
    print(f"  Dangling edges: {len(dangling)}"
          + ("" if dangling else "  (an edge cannot outlive its endpoints)"))
    print("  Traverse one: coresentinel knowledge query <entity> [--depth 2]")
    print("=" * 64 + "\n")
    return 0


def cmd_config(args):
    from coresentinel_core.runtime.config import Config, CORE_CONFIG_FILE, DEFAULTS, env_key
    from coresentinel_core.runtime.errors import ConfigurationError
    from coresentinel_core.runtime import paths

    sub = args[0].lower() if args and not args[0].startswith("-") else "list"
    target = flag_value(args, "--project", ".")
    emit_json = "--json" in args
    config = Config.load(target)

    if sub == "path":
        root = paths.find_project_root(target)
        project_file = (root / paths.CONFIG_DIRNAME / "config.json") if root else None
        payload = {"core": str(CORE_CONFIG_FILE), "core_exists": CORE_CONFIG_FILE.exists(),
                   "project": str(project_file) if project_file else None,
                   "project_exists": bool(project_file and project_file.exists())}
        if emit_json:
            print(json.dumps(payload, indent=2))
            return 0
        print(f"\n  Core config    : {payload['core']}"
              f"{'' if payload['core_exists'] else '  (not created yet)'}")
        print(f"  Project config : {payload['project'] or '(no bound project here)'}"
              f"{'' if payload['project_exists'] else '  (no settings recorded)'}\n")
        return 0

    if sub == "get":
        key = free_arg(args, 1)
        if not key:
            print("[!] Which setting? e.g. coresentinel config get storage.backend", file=sys.stderr)
            return 1
        try:
            detail = config.explain(key)
        except ConfigurationError as e:
            print(f"[!] {e}", file=sys.stderr)
            return 1
        if emit_json:
            print(json.dumps(detail, indent=2))
            return 0
        print(f"\n  {detail['key']} = {detail['value']}")
        print(f"  source  : {detail['origin']}")
        print(f"  default : {detail['default']}")
        print(f"  env var : {env_key(key)}\n")
        return 0

    if sub == "set":
        key, value = free_arg(args, 1), free_arg(args, 2)
        if not key or value == "":
            print("[!] Usage: coresentinel config set <key> <value> [--scope core|project]",
                  file=sys.stderr)
            return 1
        try:
            written = config.set(key, value, flag_value(args, "--scope", "core"), target)
        except ConfigurationError as e:
            print(f"[!] {e}", file=sys.stderr)
            return 1
        emit_audited("ConfigurationChanged", target,
                     {"setting": key, "value": config.get(key),
                      "scope": flag_value(args, "--scope", "core"), "file": str(written)})
        print(f"[✓] {key} = {config.get(key)}  →  {written}")
        return 0

    rows = [config.explain(key) for key in config.keys()]
    if emit_json:
        print(json.dumps({"settings": rows}, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  ⚙️  CoreSentinel Configuration")
    print("=" * 64)
    print("  Precedence: default < core config < project config < environment < flag")
    print("  " + "-" * 60)
    width = max(len(r["key"]) for r in rows)
    for row in rows:
        marker = " " if row["origin"] == "default" else "*"
        print(f"  {marker} {row['key']:<{width}} = {str(row['value']):<12} [{row['origin']}]")
    for problem in config.problems:
        print(f"  [!] {problem}", file=sys.stderr)
    print("  " + "-" * 60)
    print("  * overrides a default.  Inspect one: coresentinel config get <key>")
    print("=" * 64 + "\n")
    return 0


def cmd_migrate(args):
    from coresentinel_core.runtime.container import Runtime
    from coresentinel_core.runtime.errors import CoreSentinelError

    if args and args[0].lower() in ("decision", "decisions"):
        return migrate_decisions(positional(args, 1), "--apply" in args, "--json" in args)

    target = positional(args)
    try:
        runtime = Runtime.bootstrap(target)
        store = runtime.store
        detail = store.describe()
    except CoreSentinelError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 1

    payload = {"backend": detail["backend"], "root": detail["root"],
               "schema": detail.get("schema", []),
               "applied_now": [m["version"] for m in getattr(store, "applied", [])],
               "collections": detail["collections"]}
    runtime.shutdown()

    if "--json" in args:
        print(json.dumps(payload, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  🗄️  CoreSentinel Storage Migration")
    print("=" * 64)
    print(f"  Backend  : {payload['backend']}")
    print(f"  Root     : {payload['root']}")
    if payload["backend"] == "json":
        print("  Schema   : not applicable — the json backend needs no migration")
    else:
        print(f"  Schema   : {', '.join(payload['schema']) or 'none'}")
        print(f"  Applied  : {', '.join(payload['applied_now']) or 'nothing pending'}")
    print("  " + "-" * 60)
    print("  Memory layers, decisions and the journal are NOT stored here and are")
    print("  unaffected by migration — deleting the database loses none of them.")
    print("=" * 64 + "\n")
    return 0


def migrate_decisions(target=".", apply_changes=False, emit_json=False):
    """Give v1 records the v2 fields as explicit nulls.

    Nothing is inferred. A v1 ADR records no problem statement and no evidence,
    so those stay null — filling them from the reason would manufacture a
    rationale nobody wrote, which is the failure the ledger exists to prevent.
    """
    from coresentinel_core.decisions import ledger, schema

    upgraded = []
    for path in [p for p in (ledger.project_path(target), ledger.core_path()) if p]:
        records, error = ledger._read(path)
        if error or not records:
            continue
        rewritten, changed = [], 0
        for record in records:
            missing = [f for f in schema.ALL_FIELDS if f not in record]
            if missing:
                changed += 1
                upgraded.append({"id": record.get("id"), "path": str(path),
                                 "added": missing})
            rewritten.append(schema.normalize(record))
        if changed and apply_changes:
            ledger._write(path, rewritten)

    report = {"upgraded": upgraded, "count": len(upgraded), "applied": bool(apply_changes)}
    if emit_json:
        print(json.dumps(report, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  📜 CoreSentinel Decision Schema Migration")
    print("=" * 64)
    if not upgraded:
        print("  Every recorded decision already carries the full schema.")
        print("=" * 64 + "\n")
        return 0
    for item in upgraded:
        print(f"  {item['id']}: +{len(item['added'])} field(s) — {', '.join(item['added'][:8])}")
    print("  " + "-" * 60)
    print("  Added as null. Nothing is inferred: a v1 record states no problem and no")
    print("  evidence, and inventing them would manufacture a rationale nobody wrote.")
    if apply_changes:
        print(f"  Applied to {len(upgraded)} record(s).")
    else:
        print("  Dry run — apply with: coresentinel migrate decisions --apply")
    print("=" * 64 + "\n")
    return 0


def verify_audit_chain(target=".", emit_json=False):
    from coresentinel_core.audit import ledger as audit_ledger
    from coresentinel_core.runtime.container import Runtime

    runtime = Runtime.bootstrap(target)
    report = audit_ledger.verify(runtime.store)
    runtime.shutdown()

    if emit_json:
        print(json.dumps(report, indent=2))
        return 0 if report["intact"] else 1

    print("\n" + "=" * 64)
    print("  🔗 CoreSentinel Audit Chain Verification")
    print("=" * 64)
    print(f"  Chained records : {report['checked']}")
    if report["legacy"]:
        print(f"  Legacy records  : {report['legacy']} (listed, never signed)")
    print("  " + "-" * 60)
    if report["intact"]:
        print("  Every record's hash matches its content, and every link matches the")
        print("  record before it. Nothing has been inserted, removed or altered.")
    else:
        for problem in report["problems"]:
            print(f"  [✗] {problem['code']:<18} {problem['record']}")
            print(f"      {problem['detail']}")
    if report.get("note"):
        print("  " + "-" * 60)
        print(f"  {report['note']}")
    print("  " + "-" * 60)
    print(f"  Verdict : {report['verdict']}")
    print("  This is tamper-evidence, not tamper-proofing: anyone with write access")
    print("  can recompute the chain. What they cannot do is change one record and")
    print("  leave the rest intact — which is what a quiet edit looks like.")
    print("=" * 64 + "\n")
    return 0 if report["intact"] else 1


def audit_coverage(target=".", emit_json=False):
    from coresentinel_core.audit import ledger as audit_ledger
    from coresentinel_core.runtime.container import Runtime

    runtime = Runtime.bootstrap(target)
    report = audit_ledger.coverage(runtime.store)
    runtime.shutdown()

    if emit_json:
        print(json.dumps(report, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  📋 CoreSentinel Audit Coverage")
    print("=" * 64)
    print(f"  {len(report['recorded'])}/{report['total']} subjects have been recorded here")
    print("  " + "-" * 60)
    for subject in report["recorded"]:
        print(f"  [✓] {subject}")
    for subject in report["never_recorded"]:
        print(f"  [ ] {subject}")
    print("  " + "-" * 60)
    print("  A subject with no records has either never happened in this store, or")
    print("  nothing emits an event for it. Both are worth knowing.")
    print("=" * 64 + "\n")
    return 0


def cmd_score(args):
    import coresentinel_score as score_engine
    return score_engine.print_scorecard(positional(args), "--json" in args, "--explain" in args)


def cmd_adapter(args):
    import coresentinel_adapters as adapters
    sub = args[0].lower() if args and not args[0].startswith("--") else "list"
    if sub == "invoke":
        return invoke_adapter(free_arg(args, 1), args)
    if sub == "conformance":
        return adapter_conformance("--json" in args)
    if sub == "detect":
        adapters.detect_hosts(positional(args, 1))
    elif sub == "show":
        adapters.show_adapter(positional(args, 1, "claude-code"))
    elif sub == "sync":
        adapters.sync_adapter(positional(args, 1, "claude-code"),
                              flag_value(args, "--scope", "global"),
                              "--apply" in args, "--force" in args)
    elif sub == "export":
        adapters.export_context(".", "--json" in args)
    else:
        adapters.list_adapters()


def adapter_conformance(emit_json=False):
    from coresentinel_core.agents import adapters as agent_adapters

    report = agent_adapters.conformance_report()
    if emit_json:
        print(json.dumps({"adapters": report,
                          "conforming": sum(1 for r in report if r["conforms"])}, indent=2))
        return 0 if all(r["conforms"] for r in report) else 1

    print("\n" + "=" * 64)
    print("  🔌 CoreSentinel Adapter Conformance")
    print("=" * 64)
    if not report:
        print("  No host declares an invocation profile.")
        print("=" * 64 + "\n")
        return 0
    for item in report:
        print(f"  {'✓' if item['conforms'] else '✗'} {item['adapter']}")
        for check in item["checks"]:
            if not check["passed"]:
                print(f"      ✗ {check['check']}"
                      + (f" — {check['detail']}" if check["detail"] else ""))
    print("  " + "-" * 60)
    print(f"  {sum(1 for r in report if r['conforms'])}/{len(report)} adapters conform")
    print("  Every adapter answers the same questions; one that cannot is not an adapter.")
    print("=" * 64 + "\n")
    return 0 if all(r["conforms"] for r in report) else 1


def invoke_adapter(host, args):
    from coresentinel_core.agents import adapters as agent_adapters
    from coresentinel_core.agents import protocol, registry, permissions as perms
    from coresentinel_core.agents.sandbox import AgentSandbox
    from coresentinel_core.runtime.container import Runtime

    if not host:
        installed = [a.id for a in agent_adapters.available()]
        print("[!] Which host? e.g. coresentinel adapter invoke claude-code "
              "--objective \"...\"", file=sys.stderr)
        print(f"    Available here: {', '.join(installed) or 'none'}", file=sys.stderr)
        return 1

    adapter = agent_adapters.resolve(host)
    if not adapter:
        print(f"[!] '{host}' declares no invocation profile.", file=sys.stderr)
        print(f"    Invocable hosts: {', '.join(a.id for a in agent_adapters.invocable())}",
              file=sys.stderr)
        return 1

    objective = flag_value(args, "--objective") or flag_value(args, "--task")
    if not objective:
        print("[!] What should it do? --objective \"...\"", file=sys.stderr)
        return 1

    target = flag_value(args, "--project", ".")
    agent_name = flag_value(args, "--as", "Builder")
    contract = registry.get(agent_name)
    if not contract:
        print(f"[!] Unknown agent '{agent_name}'. Known: {', '.join(registry.names())}",
              file=sys.stderr)
        return 1

    runtime = Runtime.bootstrap(target)
    permission_set = registry.permissions_for(agent_name,
                                              interactive="--interactive" in args)
    if "--allow-network" in args:
        permission_set.grant(perms.NETWORK_ACCESS, perms.ALLOW,
                             reason="granted on the command line for this invocation")

    task = protocol.build_task(objective, contract["name"], project=target)
    sandbox = AgentSandbox(contract["name"], permission_set, target, runtime.logger)

    context_pack = None
    if "--with-context" in args:
        from coresentinel_core.memory import assembly
        context_pack = assembly.render(assembly.assemble(objective, target))

    runtime.events.emit("AgentStarted", {"agent": contract["name"], "host": adapter.id})
    result = adapter.invoke(task, sandbox, context_pack)
    problems = protocol.validate_result(result)
    if problems:
        result = protocol.build_result(task, protocol.FAILED,
                                       f"{adapter.name} returned an invalid result",
                                       warnings=problems)
    runtime.events.emit("AgentCompleted", {"agent": contract["name"], "host": adapter.id,
                                           "status": result["status"]})
    runtime.shutdown()

    if "--json" in args:
        print(json.dumps(result, indent=2))
        return 0 if result["status"] in (protocol.COMPLETED, protocol.UNSUPPORTED) else 1

    print("\n" + "=" * 64)
    print(f"  🔌 {adapter.name} — invoked as {contract['name']}")
    print("=" * 64)
    print(f"  Objective : {objective}")
    print(f"  Transport : {adapter.transport} · permission {adapter.permission}")
    print(f"  Status    : {result['status']}")
    print("  " + "-" * 60)
    print(f"  {result['summary']}")
    for item in result["evidence"]:
        print(f"      evidence: {item['check']} — {item['status']}"
              + (f"  $ {item['command']} → exit {item.get('exit_code')}"
                 if item.get("command") else ""))
    claims = result.get("claims") or {}
    claimed = {k: v for k, v in claims.items() if isinstance(v, list) and v}
    if claimed:
        print("  " + "-" * 60)
        print("  Claimed by the agent (NOT verified):")
        for field, entries in claimed.items():
            print(f"      {field}: {', '.join(str(e) for e in entries[:5])}")
    for denial in result["denials"]:
        print(f"      ⛔ {denial['permission']} denied — {denial['reason']}")
    print("  " + "-" * 60)
    print("  An invocation proves the agent ran and what it said — not that it is true.")
    print("  Check the claims against the repository: coresentinel verify")
    print("=" * 64 + "\n")
    return 0 if result["status"] in (protocol.COMPLETED, protocol.UNSUPPORTED) else 1


def cmd_serve(args):
    from coresentinel_core.api import server as api
    from coresentinel_core.runtime.container import Runtime
    from coresentinel_core.services import Services

    target = positional(args)
    runtime = Runtime.bootstrap(target)
    services = Services(runtime)

    host = flag_value(args, "--host") or runtime.config.get("api.host")
    port = int(flag_value(args, "--port") or runtime.config.get("api.port"))
    token = api.resolve_token(runtime.config)
    generated = False

    # Loopback may generate a token on the spot: a write still needs it, and the
    # operator is right there to read it. A wider bind may NOT — generating one
    # would satisfy the check while leaving a server on the network whose token
    # nobody had a chance to distribute, which is the refusal defeating itself.
    if not token and api.is_loopback(host):
        token = api.generate_token()
        generated = True

    try:
        httpd = api.build_server(services, host, port, token,
                                 "--threaded" in args or runtime.config.get("api.threaded"))
    except api.ApiError as e:
        print(f"\n[!] {e.message}", file=sys.stderr)
        if e.remedy:
            print(f"    {e.remedy}", file=sys.stderr)
        runtime.shutdown()
        return 1

    print("\n" + "=" * 64)
    print(f"  🌐 CoreSentinel API {api.API_VERSION}")
    print("=" * 64)
    print(f"  Listening : http://{host}:{port}{api.BASE_PATH}")
    print(f"  Catalogue : http://{host}:{port}{api.BASE_PATH}  "
          f"({len(services.OPERATIONS)} operations)")
    from coresentinel_core import web
    if web.available():
        print(f"  Dashboard : http://{host}:{port}/   (read-only, reads this API)")
    print(f"  Bind      : {'loopback' if api.is_loopback(host) else host + ' (non-loopback)'}")
    print("  " + "-" * 60)
    print(f"  Token     : {token}")
    if generated:
        print("              generated for this run — set api.token to keep it:")
        print(f"                coresentinel config set api.token {token}")
    print(f"  Header    : {api.TOKEN_HEADER}")
    print("  " + "-" * 60)
    print("  Writes always require the token. Reads are open over loopback only.")
    print("  Every surface calls the same services, so an operation is audited")
    print("  identically whether it arrived here, over MCP, or on the CLI.")
    print("  Stop with Ctrl-C.")
    print("=" * 64 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[·] Stopped.")
    finally:
        httpd.server_close()
        runtime.shutdown()
    return 0


def cmd_mcp(args):
    from coresentinel_core.mcp import McpServer, build_tools
    from coresentinel_core.runtime.container import Runtime
    from coresentinel_core.services import Services

    target = positional(args)
    runtime = Runtime.bootstrap(target)
    services = Services(runtime)

    if "--tools" in args or "--list" in args:
        tools = build_tools(services)
        if "--json" in args:
            print(json.dumps({"tools": tools}, indent=2))
        else:
            print("\n" + "=" * 64)
            print("  🔌 CoreSentinel MCP Tools")
            print("=" * 64)
            for tool in tools:
                print(f"  {tool['name']:<24} {tool['description'][:60]}")
            print("  " + "-" * 60)
            print(f"  {len(tools)} tool(s), generated from the service catalogue.")
            print("  Mount this server with: coresentinel mcp")
            print("=" * 64 + "\n")
        runtime.shutdown()
        return 0

    # stdout carries JSON-RPC frames and nothing else from here on.
    try:
        return McpServer(services).serve()
    finally:
        runtime.shutdown()


def cmd_stats(args):
    stats_script = CORESENTINEL_DIR / "agent-stats.py"
    if not stats_script.exists():
        print("[!] agent-stats.py not found.", file=sys.stderr)
        return 1
    return subprocess.run([sys.executable, str(stats_script)] + args).returncode


def cmd_hooks(args):
    if sys.platform == "win32":
        script = CORESENTINEL_DIR / "install-hooks.ps1"
        return subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)]).returncode
    script = CORESENTINEL_DIR / "install-hooks.sh"
    return subprocess.run(["bash", str(script)]).returncode


def cmd_check(args):
    return subprocess.run([sys.executable, str(CORESENTINEL_DIR / "sentinel-validator.py")]).returncode


def component_versions():
    """Registry versions, so a bug report says which rule sets were loaded."""
    components = {}
    for label, filename in [("adapter registry", "adapters.json"),
                            ("squad contracts", "squad-contracts.json"),
                            ("anti-pattern database", "anti-patterns.json")]:
        path = CORESENTINEL_DIR / filename
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                components[label] = json.load(f).get("version", "unversioned")
        except (OSError, json.JSONDecodeError, ValueError) as e:
            components[label] = f"unreadable ({e})"
    return components


def cmd_version(args):
    version = read_version()
    components = component_versions()
    protocols = len(list(CORESENTINEL_DIR.glob("[0-9][0-9]-*.md")))

    if "--json" in args:
        print(json.dumps({
            "coresentinel": version,
            "core_dir": str(CORESENTINEL_DIR),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "protocols": protocols,
            "components": components,
        }, indent=2))
        return 0

    width = max(len(label) for label in components) + 1
    width = max(width, len("Core Directory"))

    print(f"\n  🛡️  CoreSentinel {version}")
    print("  " + "-" * 52)
    print(f"  {'Core Directory':<{width}} : {CORESENTINEL_DIR}")
    print(f"  {'Python':<{width}} : {platform.python_version()}")
    print(f"  {'Platform':<{width}} : {platform.system()} {platform.release()}")
    print(f"  {'Protocols':<{width}} : {protocols} documents")
    for label, value in components.items():
        rendered = value if value.startswith("unreadable") else f"v{value}"
        print(f"  {label.title():<{width}} : {rendered}")
    print("")
    return 0


def cmd_help(args):
    if args and not args[0].startswith("--"):
        return print_command_help(args[0])
    print_help()
    return 0


COMMANDS = [
    {"name": "init", "aliases": [], "group": "Setup & Diagnostics", "handler": cmd_init,
     "summary": "Bind a project to the CoreSentinel Core",
     "usage": ["coresentinel init [target-dir] [--host <id>] [--apply] [--force]"],
     "detail": "Writes .coresentinel/config.json and context.json, seeds the detected stack into\n"
               "project memory, and optionally binds an AI host. Refuses to overwrite an existing\n"
               "config without --force."},
    {"name": "doctor", "aliases": ["diagnose"], "group": "Setup & Diagnostics", "handler": cmd_doctor,
     "summary": "Diagnose the 10 CoreSentinel subsystems",
     "usage": ["coresentinel doctor [target-dir] [--verbose] [--json]"],
     "detail": "Checks Configuration, Runtime, Storage, Memory, Governance, Agent Registry,\n"
               "Verification Engine, Security Rules, Observability and Project Context.\n"
               "Exits 1 on any FAIL."},
    {"name": "project", "aliases": ["brain"], "group": "Context & Memory", "handler": cmd_project,
     "summary": "Inspect what CoreSentinel understands about a project",
     "usage": ["coresentinel project inspect [target-dir] [--verbose] [--json]",
               "coresentinel project inspect --save",
               "coresentinel project list"],
     "detail": "Ten dimensions: languages, runtimes, package managers, frameworks, datastores,\n"
               "containers, CI, environment, testing and API surface.\n"
               "\n"
               "Every value names the file and locator that proves it — --verbose prints them.\n"
               "A dimension nothing evidenced reports 'unknown', which is not the same as\n"
               "empty: one means there is no database, the other means we could not tell.\n"
               "\n"
               "Frameworks are matched on the exact package that means the framework is in\n"
               "use, never a substring. symfony/framework-bundle means Symfony;\n"
               "symfony/console does not, and Laravel depends on it."},
    {"name": "knowledge", "aliases": ["graph"], "group": "Context & Memory", "handler": cmd_knowledge,
     "summary": "Traverse the relationships between what CoreSentinel knows",
     "usage": ["coresentinel knowledge describe [--json]",
               "coresentinel knowledge query ADR-042 [--depth 2]",
               "coresentinel knowledge build"],
     "detail": "Entities are project, language, framework, datastore, container, ci, test tool,\n"
               "file, decision, incident and pattern. Edges come only from what was recorded:\n"
               "a discovery finding and its evidence, a decision's related files and incidents,\n"
               "a supersession. Nothing is inferred from source code.\n"
               "\n"
               "The graph is derived data and is rebuilt on every query, so a superseded\n"
               "decision can never linger in an answer. 'build' persists a snapshot for\n"
               "consumers that cannot rebuild it themselves."},
    {"name": "config", "aliases": ["settings"], "group": "Setup & Diagnostics", "handler": cmd_config,
     "summary": "Inspect and change resolved settings",
     "usage": ["coresentinel config list [--json]",
               "coresentinel config get storage.backend",
               "coresentinel config set storage.backend sqlite [--scope core|project]",
               "coresentinel config path"],
     "detail": "Precedence, lowest to highest:\n"
               "  default < core config < project config < environment < flag\n"
               "\n"
               "Every value reports which layer produced it, so a setting's origin is never\n"
               "a guess. Environment variables are CORESENTINEL_<KEY_IN_UPPER_SNAKE>.\n"
               "Core settings live in coresentinel.config.json; project settings live under\n"
               "the 'settings' key of <project>/.coresentinel/config.json."},
    {"name": "migrate", "aliases": [], "group": "Setup & Diagnostics", "handler": cmd_migrate,
     "summary": "Create or upgrade the record store",
     "usage": ["coresentinel migrate [target-dir] [--json]"],
     "detail": "Applies pending schema migrations to the sqlite backend, in numeric order,\n"
               "recording each with a checksum. Re-running is a no-op. Editing a migration\n"
               "that has already been applied is refused.\n"
               "\n"
               "Memory layers, the decision ledger and the journal are NOT stored here.\n"
               "Deleting the database loses none of them."},
    {"name": "status", "aliases": [], "group": "Setup & Diagnostics", "handler": cmd_status,
     "summary": "At-a-glance governance dashboard",
     "usage": ["coresentinel status [target-dir] [--json]"],
     "detail": "Fast file-only snapshot: git state, active host, gate results, memory volume,\n"
               "audit runs and pending evolution proposals."},

    {"name": "context", "aliases": ["ctx"], "group": "Context & Memory", "handler": cmd_context,
     "summary": "Assemble the project context pack",
     "usage": ["coresentinel context [target-dir] [--json]",
               "coresentinel context --task \"Add Redis caching to product listing\"",
               "coresentinel context --task \"...\" --budget 8000 --min-confidence 0.5"],
     "detail": "Without --task: stack, frameworks, test runner, key files, git history and every\n"
               "recorded fact — the v1 pack, unchanged.\n"
               "\n"
               "With --task: only what the task needs. Facts, decisions, failures, patterns and\n"
               "journal entries are ranked by the recall engine, the anti-pattern rules whose\n"
               "trigger context matches are included, and any decision the task appears to\n"
               "contradict is lifted to the top.\n"
               "\n"
               "The pack is bounded by --budget (default 4000 tokens, estimated as characters/4).\n"
               "Whatever does not fit is counted and its best candidate named, so a partial pack\n"
               "never reads as a complete one."},
    {"name": "memory", "aliases": ["mem"], "group": "Context & Memory", "handler": cmd_memory,
     "summary": "Inspect or extend the 6-layer memory engine",
     "usage": ["coresentinel memory show [project-dir]",
               "coresentinel memory add --layer project --fact \"...\" --confidence 0.98 --source \"...\"",
               "coresentinel memory add --layer project --fact \"...\" --project ~/code/api"],
     "detail": "Layers: working, session, project, longterm, failures, patterns.\n"
               "Confidence >= 0.90 is Known, >= 0.50 Assumed, below that Unknown.\n"
               "working, session and project are PROJECT-scoped: inside a bound project they\n"
               "resolve to <project>/.coresentinel/memory/. The rest are shared Core layers.\n"
               "\n"
               "Lifecycle subcommands (every one is a dry run until --apply):\n"
               "  decay        erode confidence of facts nobody has re-verified\n"
               "  verify       restart the decay clock on facts matching a substring\n"
               "  promote      move earned facts up a tier (session -> project -> longterm)\n"
               "  consolidate  merge duplicates within a layer and across the tier chain\n"
               "  compact      fold old low-confidence facts into a summary entry\n"
               "  snapshot     capture every layer; snapshots / restore manage the vault"},
    {"name": "recall", "aliases": ["search", "remember"], "group": "Context & Memory", "handler": cmd_recall,
     "summary": "Search every memory layer, decision and journal entry",
     "usage": ["coresentinel recall \"postgres migration\"",
               "coresentinel recall \"auth\" --layer project,longterm --min-confidence 0.9",
               "coresentinel recall \"rate limit\" --json"],
     "detail": "Ranks by term coverage, bonuses an exact phrase hit and weights by confidence.\n"
               "Low-confidence facts stay findable — an Unknown fact you can see is safer\n"
               "than one you cannot. Exits 1 when nothing matches."},
    {"name": "brief", "aliases": ["briefing"], "group": "Context & Memory", "handler": cmd_brief,
     "summary": "Session-start briefing: where the work left off",
     "usage": ["coresentinel brief [target-dir] [--days 7] [--json]"],
     "detail": "Last task and status, recent journal entries, established facts, facts still\n"
               "unverified, facts gone stale, known failures and the latest decisions.\n"
               "Run this before the first action of a session."},
    {"name": "journal", "aliases": ["diary", "log"], "group": "Context & Memory", "handler": cmd_journal,
     "summary": "Narrative session journal",
     "usage": ["coresentinel journal add --entry \"...\" [--tags \"api,refactor\"]",
               "coresentinel journal show [--days 7] [--json]",
               "coresentinel journal archive [--older-than 30] [--apply]"],
     "detail": "The record of what was done and why, which the fact layers deliberately do not\n"
               "keep. Archiving folds old day files into one file per month; archived entries\n"
               "stay searchable through recall."},
    {"name": "decision", "aliases": ["decisions", "adr"], "group": "Context & Memory", "handler": cmd_decision,
     "summary": "Architecture Decision Record ledger",
     "usage": ["coresentinel decision list [--query \"...\"] [--core] [--json]",
               "coresentinel decision show ADR-042",
               "coresentinel decision add --title \"...\" --reason \"...\" --chosen \"...\"\n"
               "        [--alts \"...\"] [--problem \"...\"] [--context \"...\"] [--evidence \"...\"]\n"
               "        [--author \"...\"] [--agent \"...\"] [--confidence 0.9] [--relates-to \"a.py,b.py\"]",
               "coresentinel decision verify --change \"switch from Redis to database sessions\"",
               "coresentinel decision supersede ADR-042 --by ADR-050 --reason \"...\""],
     "detail": "Decisions are scoped like memory: the bound project's ledger lives in\n"
               "<project>/.coresentinel/memory/decisions.json.\n"
               "\n"
               "Inside a bound project the project ledger reads ALONE — Core decisions do not\n"
               "appear, because unioning the scopes surfaced one repository's decisions as\n"
               "governance for another and the noise taught people to skip the check. Ask for\n"
               "them with --core. Ids are allocated across both, so ADR-004 never means two\n"
               "things.\n"
               "\n"
               "If you recorded decisions before binding your first project, they are at Core\n"
               "scope: 'decision list --core' shows them, and they are unchanged on disk.\n"
               "\n"
               "'verify' checks a proposed change against every accepted decision and exits 1 if\n"
               "it reverses one, citing the ADR and the reason recorded at the time. Reversing a\n"
               "decision is allowed; doing it without anyone seeing is not — record the new\n"
               "decision and 'supersede' the old one, which links them in both directions.\n"
               "\n"
               "v1 records with only the original 8 fields load and render unchanged; the added\n"
               "fields stay null rather than being filled with a guess."},

    {"name": "verify", "aliases": ["evidence"], "group": "Verification & Review", "handler": cmd_verify,
     "summary": "Run the Evidence-Based Verification Suite",
     "usage": ["coresentinel verify [target-dir] [--claim \"...\"] [--base <ref>] [--json]"],
     "detail": "Runs 6 checks and scores only the ones that executed. Each check reports\n"
               "PASS, FAIL or UNKNOWN, and every PASS carries the command, exit code,\n"
               "duration and output digest that produced it.\n"
               "\n"
               "UNKNOWN means nothing could be run — no test runner, no linter, not a git\n"
               "repository. It is excluded from the denominator, never counted as a pass.\n"
               "At least 50 of the 100 evidence points must execute before any verdict.\n"
               "\n"
               "Exit 0 VERIFIED (>= 80/100) · 1 UNVERIFIED · 2 INDETERMINATE (too little\n"
               "evidence could be gathered to judge the claim either way)."},
    {"name": "review", "aliases": [], "group": "Verification & Review", "handler": cmd_review,
     "summary": "Static review pass over the working diff",
     "usage": ["coresentinel review [target-dir] [--strict] [--json]"],
     "detail": "Scans ADDED lines for anti-patterns, debug residue, unresolved markers and missing\n"
               "test coverage. --strict promotes the missing-test warning to blocking.\n"
               "Logic correctness stays with the reviewer agents (Cato / Sage)."},
    {"name": "gate", "aliases": ["gates"], "group": "Verification & Review", "handler": cmd_gate,
     "summary": "Drive the 8-stage Quality Gates pipeline",
     "usage": ["coresentinel gate run [target-dir] [--objective \"...\"] [--report] [--json]",
               "coresentinel gate status [--report] [--json]",
               "coresentinel gate reset",
               "coresentinel gate waive --gate Security --reason \"...\""],
     "detail": "Ten ordered gates. The original eight keep their names and order; Requirement\n"
               "was added at the front and Documentation before Deployment.\n"
               "\n"
               "  Requirement -> Plan -> Architecture -> Security -> Implementation\n"
               "              -> Test -> Review -> Verification -> Documentation -> Deployment\n"
               "\n"
               "Each gate resolves to PASS, FAIL, UNKNOWN, BLOCKED, WAIVED or PENDING, and\n"
               "carries a machine-readable reason code alongside its prose — so CI can branch\n"
               "on why a gate failed without parsing a sentence.\n"
               "\n"
               "UNKNOWN means the gate has no automated check, or none could run. It does not\n"
               "block, but it is not a pass. Clear it with a waiver, which always requires a\n"
               "rationale. A FAIL blocks every gate after it.\n"
               "\n"
               "--report prints the compact completion report and FINAL STATUS."},
    {"name": "check", "aliases": ["scan"], "group": "Verification & Review", "handler": cmd_check,
     "summary": "Run the anti-pattern & secret scanner",
     "usage": ["coresentinel check"],
     "detail": "The same validator the git pre-commit hook runs."},

    {"name": "agent", "aliases": ["squad", "contracts", "contract"], "group": "Squad & Governance", "handler": cmd_agent,
     "summary": "Inspect and run the 17 specialist agent contracts",
     "usage": ["coresentinel agent list", "coresentinel agent show Architect",
               "coresentinel agent permissions [name] [--json]",
               "coresentinel agent run Security --objective \"...\" [--json]"],
     "detail": "Each contract declares input artifacts, output artifacts, authority and\n"
               "constraints — and now an explicit permission set that is enforced rather\n"
               "than described.\n"
               "\n"
               "An agent is handed a sandbox, never the filesystem or a shell. Every read,\n"
               "write and command is checked against its contract, denials are recorded on\n"
               "the result and written to the audit trail, and every path is contained inside\n"
               "the project root. Default for every agent: read the filesystem, nothing else.\n"
               "\n"
               "Roles CoreSentinel can perform itself (Scout, Security, Tester, Reviewer,\n"
               "Evolver) run for real and return evidence. The rest need a model behind them\n"
               "and report UNSUPPORTED until an agent adapter is bound."},
    {"name": "task", "aliases": ["tasks"], "group": "Squad & Governance", "handler": cmd_task,
     "summary": "Plan and run an objective across the specialist pipeline",
     "usage": ["coresentinel task plan --objective \"Add Redis caching\"",
               "coresentinel task run --objective \"...\" [--roles Scout,Security,Tester]",
               "coresentinel task list [--limit 20] [--json]"],
     "detail": "The pipeline order is a dependency order, not a preference: reviewing a change\n"
               "before it is written reviews nothing.\n"
               "\n"
               "Every result is validated before it is recorded — a COMPLETED result with\n"
               "neither evidence nor actions is rejected, because that is exactly the claim\n"
               "CoreSentinel exists to refuse. A FAILED or DENIED role stops the pipeline;\n"
               "an UNSUPPORTED one does not, since nothing went wrong when a capability is\n"
               "simply not there yet.\n"
               "\n"
               "Exits 1 when the pipeline was blocked."},
    {"name": "audit", "aliases": ["trail"], "group": "Squad & Governance", "handler": cmd_audit,
     "summary": "AI accountability audit trail",
     "usage": ["coresentinel audit list", "coresentinel audit show AUD-000001",
               "coresentinel audit verify [--json]", "coresentinel audit coverage [--json]",
               "coresentinel audit record --agent \"...\" --task \"...\" [--read N] [--modified N]"],
     "detail": "An append-only, hash-chained trail. Each record carries the hash of the one\n"
               "before it, so the chain detects the four ways a trail gets falsified:\n"
               "mutation, deletion, insertion and reordering.\n"
               "\n"
               "'verify' walks the chain and exits 1 if anything was altered. This is\n"
               "tamper-EVIDENCE, not tamper-proofing: anyone with write access can recompute\n"
               "the whole chain. What they cannot do is change one record and leave the rest\n"
               "intact, which is what a quiet edit actually looks like.\n"
               "\n"
               "'coverage' reports which of the 12 audit subjects have ever been recorded.\n"
               "Records written before chaining existed are listed as unverified_legacy and\n"
               "are never retro-signed — that would assert an integrity they never had."},
    {"name": "incident", "aliases": ["incidents", "inc"], "group": "Squad & Governance",
     "handler": cmd_incident,
     "summary": "Record what went wrong, and what should be different",
     "usage": ["coresentinel incident list [--json]",
               "coresentinel incident create --title \"...\" --problem \"...\"\n"
               "        [--root-cause \"...\"] [--severity Critical|High|Medium|Low]\n"
               "        [--class \"A: application logic\"] [--decision ADR-042] [--file src/x.py]",
               "coresentinel incident show INC-0001",
               "coresentinel incident link INC-0001 --decision ADR-042 --pattern PAT-0032",
               "coresentinel incident resolve INC-0001 --resolution \"...\" --learning \"...\""],
     "detail": "An incident holds four things, and the last two are the point:\n"
               "  problem      what was observed\n"
               "  root_cause   what actually caused it\n"
               "  resolution   what was done about it\n"
               "  learning     what should be different next time\n"
               "\n"
               "The fix is what stops it now; the learning is what stops it recurring, and\n"
               "it is what the learning engine turns into a pattern and then a candidate\n"
               "rule. Resolving without one is allowed and reported.\n"
               "\n"
               "Incidents are scoped like decisions and project memory: an incident belongs\n"
               "to the repository it happened in. Links to decisions, files, commits, tests\n"
               "and patterns appear in the knowledge graph."},
    {"name": "score", "aliases": ["health"], "group": "Squad & Governance", "handler": cmd_score,
     "summary": "7-dimension health scorecard",
     "usage": ["coresentinel score [target-dir] [--explain] [--json]"],
     "detail": "Every dimension is the fraction of its named signals that are met, and every\n"
               "signal states its basis — the command that produced it or the filesystem\n"
               "measurement it read. --explain prints all of them.\n"
               "\n"
               "A signal that cannot be evaluated on this machine is not counted as met, and\n"
               "a dimension with no evaluable signals reports UNKNOWN and stays out of the\n"
               "mean. Fewer than 3 evaluable dimensions yields INDETERMINATE.\n"
               "\n"
               "HEALTHY >= 90, WARNING 75-89, CRITICAL < 75."},
    {"name": "evolve", "aliases": ["evolution", "cse"], "group": "Squad & Governance", "handler": cmd_evolve,
     "summary": "Controlled Self-Evolution proposal pipeline",
     "usage": ["coresentinel evolve observe [--json]", "coresentinel evolve candidates",
               "coresentinel evolve reject CAND-abc123 --reason \"...\"",
               "coresentinel evolve promote CAND-abc123 --reason \"...\"",
               "coresentinel evolve propose --target \"...\" --change \"...\" --evidence \"...\"\n"
               "        [--candidate CAND-abc123] [--impact \"...\"]",
               "coresentinel evolve approve EVO-014 --approver \"Fakrul\"",
               "coresentinel evolve apply EVO-014", "coresentinel evolve revert EVO-014"],
     "detail": "The loop, and nothing skips a step:\n"
               "  incident -> root cause -> pattern -> candidate -> evidence\n"
               "           -> human approval -> versioned rule -> future agents\n"
               "\n"
               "'observe' derives candidates from incident learnings, the failures layer and\n"
               "repeated patterns. A candidate needs 2 distinct sources before it may be\n"
               "proposed — one incident is an anecdote. 'promote' skips that with a stated\n"
               "reason; 'reject' is permanent, so a declined lesson does not resurface.\n"
               "\n"
               "'approve' records a human decision and changes NO file. 'apply' makes the\n"
               "change: it refuses anything not APPROVED, snapshots the target first, bumps\n"
               "the registry version and audits the result. 'revert' restores the snapshot\n"
               "byte-identically, which is what makes approving one a decision rather than a\n"
               "commitment.\n"
               "\n"
               "A change shape CoreSentinel cannot make safely is refused, not attempted."},

    {"name": "pattern", "aliases": ["patterns"], "group": "Squad & Governance",
     "handler": cmd_pattern,
     "summary": "The pattern library, as data rather than prose",
     "usage": ["coresentinel pattern list [--json]", "coresentinel pattern show PAT-0001",
               "coresentinel pattern add --name \"...\" --problem \"...\" --solution \"...\"\n"
               "        [--stack \"...\"] [--gotchas \"...\"] [--incident INC-0001] [--transferable]"],
     "detail": "The fields are exactly those the pattern library has documented since v1, so\n"
               "a record renders back into its markdown format without loss. What is added is\n"
               "identity, provenance (which incident taught it) and an occurrence count.\n"
               "\n"
               "Recording the same pattern again counts an occurrence; it does not raise\n"
               "confidence. Three sightings of a guess make one guess seen three times.\n"
               "\n"
               "Scoped like decisions and incidents. A Core pattern is visible inside a project\n"
               "only when marked --transferable, the same rule that stops one repository's\n"
               "truth leaking into every other."},
    {"name": "adapter", "aliases": ["adapters", "host"], "group": "Integration & Telemetry", "handler": cmd_adapter,
     "summary": "Bind the Core to any AI coding host",
     "usage": ["coresentinel adapter list", "coresentinel adapter detect",
               "coresentinel adapter show claude-code",
               "coresentinel adapter sync cursor [--scope global|project] [--apply] [--force]",
               "coresentinel adapter export [--json]",
               "coresentinel adapter conformance [--json]",
               "coresentinel adapter invoke claude-code --objective \"...\"\n"
               "        [--as Builder] [--with-context] [--allow-network] [--json]"],
     "detail": "Two directions on one registry.\n"
               "\n"
               "  sync    projects the Core INTO a host's native rules file. A dry run unless\n"
               "          --apply; an unmanaged target file is never overwritten.\n"
               "  invoke  runs the host as an agent and normalises what comes back.\n"
               "\n"
               "An invocation runs under the named agent's contract, so it is permission-gated\n"
               "like any other agent action: a CLI or MCP host consumes shell.execute, an HTTP\n"
               "host consumes network.access, which nothing grants by default.\n"
               "\n"
               "An invocation proves the agent ran and what it said. It does NOT prove that\n"
               "what it said is true — the response is recorded under 'claims', the only\n"
               "evidence is the invocation itself, and 'coresentinel verify' is what checks\n"
               "the claims against the repository."},
    {"name": "serve", "aliases": ["api"], "group": "Integration & Telemetry",
     "handler": cmd_serve,
     "summary": "Serve the versioned HTTP API",
     "usage": ["coresentinel serve [target-dir] [--host 127.0.0.1] [--port 7878] [--threaded]"],
     "detail": "One service layer, three surfaces: the CLI, this API and the MCP server all\n"
               "call the same operations, so the same action produces the same audit record\n"
               "whichever way it arrived.\n"
               "\n"
               "Routes are generated from the service catalogue at /api/v1/<area>/<verb>, so\n"
               "an operation cannot exist on the CLI and be missing here.\n"
               "\n"
               "Loopback by default. A non-loopback bind without a configured token is\n"
               "REFUSED at startup — an unauthenticated governance system on the network is\n"
               "not a default anyone should get by accident. Writes require the token on any\n"
               "interface; reads are open over loopback only.\n"
               "\n"
               "stdlib http.server: local-first, no dependency. --threaded when a dashboard\n"
               "needs concurrent reads."},
    {"name": "mcp", "aliases": [], "group": "Integration & Telemetry", "handler": cmd_mcp,
     "summary": "Run CoreSentinel as an MCP server",
     "usage": ["coresentinel mcp", "coresentinel mcp --tools [--json]"],
     "detail": "JSON-RPC 2.0 over stdio: initialize, tools/list, tools/call. An MCP-capable\n"
               "host mounts CoreSentinel and calls its operations as tools.\n"
               "\n"
               "Tools are generated from the service catalogue, so MCP cannot reach an\n"
               "operation that skips governance — the bypass is structurally impossible\n"
               "rather than forbidden by a rule somebody has to remember.\n"
               "\n"
               "stdout carries protocol frames and nothing else; diagnostics go to stderr.\n"
               "One stray print corrupts the stream and the host sees a protocol error\n"
               "instead of the message that caused it.\n"
               "\n"
               "--tools lists the surface without starting the server."},
    {"name": "metrics", "aliases": ["perf"], "group": "Integration & Telemetry",
     "handler": cmd_metrics,
     "summary": "What CoreSentinel measures about itself",
     "usage": ["coresentinel metrics [target-dir] [--subject recall] [--limit 50] [--json]",
               "coresentinel metrics coverage [--json]",
               "coresentinel metrics budgets [--json]"],
     "detail": "Eleven subjects: command, service, agent, task, verification, gate, memory,\n"
               "context, recall, storage, audit. Each series keeps count, total, min, max and\n"
               "last — never the samples — so a series costs the same at one observation as at\n"
               "a million.\n"
               "\n"
               "There are no zero-initialised counters. A subject nothing has exercised reports\n"
               "as never observed, because a zero would claim it happened nought times.\n"
               "\n"
               "'budgets' prints the published performance limits and the measurement behind\n"
               "each one. Exits 1 if any measured series is over its budget.\n"
               "\n"
               "stats reads the transcripts of AI hosts; this measures CoreSentinel."},
    {"name": "stats", "aliases": [], "group": "Integration & Telemetry", "handler": cmd_stats,
     "summary": "Token usage & session telemetry",
     "usage": ["coresentinel stats"],
     "detail": "Input/output token counts, tool breakdown and hot files across detected AI tools."},
    {"name": "hooks", "aliases": [], "group": "Integration & Telemetry", "handler": cmd_hooks,
     "summary": "Install git pre-commit & pre-push hooks",
     "usage": ["coresentinel hooks"],
     "detail": "Binds the validator into git so unverified work cannot be committed or pushed."},
    {"name": "version", "aliases": ["--version", "-v"], "group": "Integration & Telemetry",
     "handler": cmd_version,
     "summary": "Print the CoreSentinel version and build context",
     "usage": ["coresentinel version", "coresentinel --version", "coresentinel version --json"],
     "detail": "Reads the VERSION file at the Core root — the single source of truth. Also\n"
               "reports Python, platform, protocol count and the registry versions loaded."},
    {"name": "help", "aliases": ["--help", "-h"], "group": "Integration & Telemetry", "handler": cmd_help,
     "summary": "Show this help, or detail for one command",
     "usage": ["coresentinel help", "coresentinel help doctor"],
     "detail": "Every command also accepts --help."},
]


def find_command(name):
    key = (name or "").lower()
    for command in COMMANDS:
        if key == command["name"] or key in command["aliases"]:
            return command
    return None


def print_help():
    print("\n" + "=" * 64)
    print(f"  🛡️  CoreSentinel {read_version()} — AI Agent Governance CLI")
    print("=" * 64)
    print("  Usage: coresentinel <command> [options]\n")

    groups = []
    for command in COMMANDS:
        if command["group"] not in groups:
            groups.append(command["group"])

    for group in groups:
        print(f"  {group}")
        for command in COMMANDS:
            if command["group"] == group:
                print(f"    {command['name']:<12} {command['summary']}")
        print("")

    print("  Run 'coresentinel help <command>' for usage and options.")
    print("=" * 64 + "\n")


def print_command_help(name):
    command = find_command(name)
    if not command:
        return suggest_command(name)

    print("\n" + "=" * 64)
    print(f"  🛡️  CoreSentinel — {command['name']}")
    print("=" * 64)
    print(f"  {command['summary']}")
    if command["aliases"]:
        print(f"  Aliases: {', '.join(command['aliases'])}")
    print("  " + "-" * 60)
    print("  Usage:")
    for line in command["usage"]:
        print(f"    {line}")
    if command.get("detail"):
        print("  " + "-" * 60)
        for line in command["detail"].splitlines():
            print(f"  {line}")
    print("=" * 64 + "\n")
    return 0


def suggest_command(name):
    """An unknown command is a diagnostic, so it goes to stderr.

    It used to print to stdout, which put prose in front of anything reading a
    --json payload — the same class of break as a scanner logging to stdout.
    """
    import difflib
    names = [c["name"] for c in COMMANDS]
    close = difflib.get_close_matches(name, names + [a for c in COMMANDS for a in c["aliases"]], n=3, cutoff=0.5)
    print(f"\n[!] Unknown command: '{name}'", file=sys.stderr)
    if close:
        print(f"    Did you mean: {', '.join(close)}?", file=sys.stderr)
    print("    Run 'coresentinel help' to list all commands.\n", file=sys.stderr)
    return 1


def main():
    args = sys.argv[1:]

    if not args:
        print_help()
        sys.exit(0)

    name = args[0].lower()
    rest = args[1:]

    command = find_command(name)
    if not command:
        sys.exit(suggest_command(name))

    if "--help" in rest or "-h" in rest:
        sys.exit(print_command_help(command["name"]))

    orphan = dangling_flag(rest)
    if orphan:
        print(f"\n[!] {orphan} expects a value but none was given.", file=sys.stderr)
        print(f"    Run 'coresentinel help {command['name']}' for usage.\n", file=sys.stderr)
        sys.exit(1)

    exit_code = command["handler"](rest)
    sys.exit(exit_code if isinstance(exit_code, int) else 0)


if __name__ == "__main__":
    main()
