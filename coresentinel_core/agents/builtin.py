"""
Built-in agents — the roles CoreSentinel can already perform itself.

Several squad contracts describe work this system does natively: Security runs
the scanner, Tester runs the suite, Reviewer reads the diff, Scout retrieves
context. Those run here for real, through the sandbox, and return evidence that
came from a command with an exit code.

Every other role needs a model behind it, and those report `UNSUPPORTED` until
Phase 6 wires the vendor adapters. That is the honest answer and it is the same
rule as `UNKNOWN` in verification: a capability that is not there says so rather
than returning a confident nothing.
"""

import time

from coresentinel_core.agents import protocol
from coresentinel_core.agents import permissions as perms
from coresentinel_core.agents.sandbox import PermissionDenied

import coresentinel_exec as execution


def _timed(function):
    def wrapper(task, sandbox, **kwargs):
        started = time.perf_counter()
        stamp = protocol._stamp()
        try:
            result = function(task, sandbox, **kwargs)
        except PermissionDenied as denial:
            result = protocol.build_result(
                task, protocol.DENIED,
                f"blocked: {denial.decision.permission} is {denial.decision.level}")
        except Exception as e:
            result = protocol.build_result(task, protocol.FAILED,
                                           f"{type(e).__name__}: {e}")
        report = sandbox.report()
        for key in ("actions", "commands_run", "files_changed", "denials"):
            merged = list(result.get(key) or [])
            for item in report[key]:
                if item not in merged:
                    merged.append(item)
            result[key] = merged
        result["started_at"] = stamp
        result["duration_ms"] = int((time.perf_counter() - started) * 1000)
        return result
    return wrapper


# ---------------------------------------------------------------- agents

@_timed
def run_scout(task, sandbox, **kwargs):
    """Read-only research: what is already recorded about this objective.

    Scout is the contract the README's claim rests on. It reads, it never writes,
    and the sandbox is what makes that true rather than merely stated.
    """
    from coresentinel_core.memory import assembly

    pack = assembly.assemble(task["objective"], str(sandbox.root),
                             budget_tokens=kwargs.get("budget", 2000))
    found = sum(section["included"] for section in pack["sections"])
    sandbox.actions.append({"action": "recall", "target": task["objective"],
                            "detail": f"{found} relevant item(s)"})

    return protocol.build_result(
        task, protocol.COMPLETED,
        f"retrieved {found} relevant item(s) within {pack['estimated_tokens']} estimated tokens",
        confidence=0.9,
        evidence=[{"check": "Context retrieval", "status": "PASS",
                   "command": None, "detail": pack["token_estimate_basis"],
                   "output_excerpt": ", ".join(
                       item["text"] for section in pack["sections"]
                       for item in section["items"])[:400]}],
        unresolved=([f"{pack['excluded']['total']} item(s) did not fit the budget"]
                    if pack["excluded"]["total"] else []),
        raw_response_ref=pack["task"])


@_timed
def run_security(task, sandbox, **kwargs):
    """The anti-pattern and secret scanner, over the working change set."""
    from coresentinel_core import CORE_ROOT
    import coresentinel_evidence as evidence_engine

    validator = CORE_ROOT / "sentinel-validator.py"
    if not validator.exists():
        return protocol.build_result(task, protocol.UNSUPPORTED,
                                     "sentinel-validator.py is missing from the Core")

    result = sandbox.execute([execution.sys.executable, str(validator)])
    if not result.ran:
        return protocol.build_result(task, protocol.FAILED,
                                     result.error or "the scanner could not be started")

    status = evidence_engine.PASS if result.ok else evidence_engine.FAIL
    return protocol.build_result(
        task, protocol.COMPLETED,
        "scanner reported zero violations" if result.ok else "scanner reported violations",
        confidence=0.95,
        evidence=[protocol.evidence_from_execution("Security & Anti-Pattern Audit",
                                                   result, status)],
        warnings=([] if result.ok else ["the change set contains anti-pattern violations"]))


@_timed
def run_tester(task, sandbox, **kwargs):
    """Run whatever test runner the project actually has installed."""
    import coresentinel_evidence as evidence_engine

    finding = evidence_engine.check_tests(str(sandbox.root))
    if finding["status"] == evidence_engine.UNKNOWN:
        return protocol.build_result(task, protocol.UNSUPPORTED,
                                     finding["detail"],
                                     evidence=[{"check": finding["check"],
                                                "status": "UNKNOWN",
                                                "command": finding["command"],
                                                "detail": finding["detail"]}])

    sandbox.commands_run.append({k: finding.get(k) for k in
                                 ("command", "exit_code", "duration_ms", "output_digest")})
    return protocol.build_result(
        task,
        protocol.COMPLETED if finding["status"] == evidence_engine.PASS else protocol.FAILED,
        finding["detail"], confidence=0.95,
        evidence=[{"check": finding["check"], "status": finding["status"],
                   "command": finding["command"], "exit_code": finding["exit_code"],
                   "output_digest": finding["output_digest"],
                   "output_excerpt": finding["output_excerpt"]}])


@_timed
def run_reviewer(task, sandbox, **kwargs):
    """Static review of the working diff — the mechanical half of the review protocol."""
    import coresentinel_review as review

    findings, changed, stats = review.review_diff(str(sandbox.root))
    if not changed:
        return protocol.build_result(task, protocol.UNSUPPORTED,
                                     "no staged, unstaged or untracked changes to review")

    blocking = [f for f in findings if f["severity"] == "BLOCK"]
    warnings = [f for f in findings if f["severity"] == "WARN"]
    sandbox.actions.append({"action": "review", "target": f"{stats['changed']} file(s)",
                            "detail": f"{len(findings)} finding(s)"})

    return protocol.build_result(
        task, protocol.FAILED if blocking else protocol.COMPLETED,
        f"{stats['changed']} file(s) reviewed, {len(blocking)} blocking, "
        f"{len(warnings)} warning(s)",
        confidence=0.9,
        evidence=[{"check": "Static review of added lines",
                   "status": "FAIL" if blocking else "PASS",
                   "command": None, "detail": f"{len(findings)} finding(s)",
                   "output_excerpt": "; ".join(f"{f['rule']} {f['detail']}"
                                               for f in findings[:6])}],
        warnings=[f"{f['rule']}: {f['detail']}" for f in warnings],
        unresolved=[f"{f['rule']}: {f['detail']}" for f in blocking])


@_timed
def run_evolver(task, sandbox, **kwargs):
    """Record a learning candidate. Writes are scoped; approval stays human."""
    decision = sandbox.allows(perms.FILESYSTEM_WRITE, "memory/")
    if not decision.allowed:
        return protocol.build_result(task, protocol.DENIED,
                                     f"cannot record a learning: {decision.reason}")
    sandbox.actions.append({"action": "propose", "target": task["objective"]})
    return protocol.build_result(
        task, protocol.COMPLETED,
        "learning candidate prepared; approval remains human",
        confidence=0.7,
        evidence=[{"check": "Learning candidate recorded", "status": "PASS",
                   "command": None, "detail": task["objective"]}],
        unresolved=["requires 'coresentinel evolve approve' before it changes any rule"])


# Contract name -> the executor that can actually perform it. Everything else in
# the registry needs a model, and Phase 6 gives those an adapter.
BUILTIN = {
    "Scout": run_scout,
    "Security": run_security,
    "Tester": run_tester,
    "Reviewer": run_reviewer,
    "Evolver": run_evolver,
}


def supports(agent_name):
    return agent_name in BUILTIN


def run(task, sandbox, **kwargs):
    executor = BUILTIN.get(task.get("agent"))
    if not executor:
        return protocol.build_result(
            task, protocol.UNSUPPORTED,
            f"no executor for '{task.get('agent')}' — this role needs a model behind it",
            unresolved=["bind an agent adapter (Phase 6) to run this role"])
    return executor(task, sandbox, **kwargs)
