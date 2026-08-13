"""
The planner and the orchestrator.

The planner turns an objective into an ordered list of tasks, one per role. The
order is the brief's pipeline, and it is a dependency order rather than a
preference: reviewing a change before it is written reviews nothing, and running
the security scan after deployment finds the problem too late to matter.

The orchestrator runs that plan and is the thing that does not take an agent's
word for it:

  * every agent is handed a sandbox scoped to its contract, so a permission it
    was not granted fails at the point of use;
  * every result is validated before it is recorded — a malformed result is a
    result nobody can audit;
  * a FAILED role stops the pipeline, an UNSUPPORTED one does not. Nothing went
    wrong when a capability simply is not there yet.
"""

import time
from datetime import datetime

from coresentinel_core.agents import protocol, registry, builtin
from coresentinel_core.agents.sandbox import AgentSandbox
from coresentinel_core.agents import permissions as perms

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# The brief's pipeline, mapped onto the contracts that exist. Order is the
# dependency order, not a preference.
PIPELINE = [
    ("Iris", "Plan the work and establish the objective"),
    ("Scout", "Retrieve what is already known about the objective"),
    ("Architect", "Design the change and its boundaries"),
    ("Database", "Design any schema change"),
    ("Builder", "Implement the change"),
    ("API", "Implement or adjust the API surface"),
    ("Tester", "Run the test suite"),
    ("Security", "Scan the change for secrets and anti-patterns"),
    ("Optimizer", "Check for performance regression"),
    ("Reviewer", "Review the working diff"),
    ("Evolver", "Record anything learned"),
    ("DevOps", "Prepare the pipeline and deployment"),
]


def plan(objective, roles=None, project=None, target_dir="."):
    """An ordered plan. Each task states whether anything can actually run it."""
    selected = [(name, description) for name, description in PIPELINE
                if not roles or name in roles]

    tasks = []
    for index, (name, description) in enumerate(selected):
        contract = registry.get(name)
        task = protocol.build_task(f"{description}: {objective}", name,
                                   project=project, index=index,
                                   constraints=(contract or {}).get("constraints", []))
        task["role_description"] = description
        task["executable"] = builtin.supports(name)
        task["depends_on"] = tasks[-1]["id"] if tasks else None
        tasks.append(task)

    return {
        "coresentinel_api": "1.1",
        "objective": objective,
        "project": project,
        "target": target_dir,
        "created_at": datetime.now().strftime(TIMESTAMP_FORMAT),
        "tasks": tasks,
        "executable": sum(1 for t in tasks if t["executable"]),
        "unsupported": sum(1 for t in tasks if not t["executable"]),
    }


def run_task(task, target_dir=".", runtime=None, interactive=False, grants=None):
    """Execute one task under its contract's permissions."""
    permission_set = registry.permissions_for(task["agent"], interactive=interactive)
    for grant in (grants or []):
        permission_set.grant(grant["permission"], grant.get("level", perms.ALLOW),
                             grant.get("scopes"), grant.get("reason"))

    logger = runtime.logger if runtime else None
    audited = []

    sandbox = AgentSandbox(task["agent"], permission_set, target_dir, logger,
                           on_denial=audited.append)

    if runtime:
        runtime.events.emit("AgentStarted", {"agent": task["agent"], "task": task["id"]})

    result = builtin.run(task, sandbox)

    problems = protocol.validate_result(result)
    if problems:
        # A result the orchestrator cannot read is a result nobody can audit.
        result = protocol.build_result(
            task, protocol.FAILED,
            "the agent returned a result that failed validation",
            warnings=problems, denials=sandbox.denials,
            actions=sandbox.actions, commands_run=sandbox.commands_run)

    result["permissions"] = permission_set.summary()

    if runtime:
        runtime.events.emit("AgentCompleted",
                            {"agent": task["agent"], "task": task["id"],
                             "status": result["status"], "denials": len(result["denials"])})
        _record(runtime, task, result)
        _record_side_effects(runtime, task, result)

    return result


def _record_side_effects(runtime, task, result):
    """Audit what the agent actually touched, separately from what it claimed.

    Commands and file writes are their own audit subjects. Folding them into the
    agent's record would mean "what ran" and "what changed" were only ever
    visible through the agent that happened to do them.
    """
    from coresentinel_core.audit import ledger as audit_ledger
    from coresentinel_core.audit import subjects as audit_subjects

    try:
        store = runtime.store
        for command in result.get("commands_run") or []:
            audit_ledger.append(store, audit_subjects.COMMAND_EXECUTION, task["agent"],
                                command.get("command") or "(command)",
                                f"exit {command.get('exit_code')}", command)
        for path in result.get("files_changed") or []:
            audit_ledger.append(store, audit_subjects.FILE_CHANGE, task["agent"],
                                path, "written", {"task": task["id"]})
    except Exception as e:
        runtime.logger.warn("side effects not audited", task=task["id"], error=str(e))


def _record(runtime, task, result):
    """Persist the task and its result. Storage must never fail the run.

    The audit entry goes through the ledger, not straight to the collection —
    a record written around the chain carries no hash and sits outside the
    integrity guarantee, which is the gap Phase 7 closed.
    """
    from coresentinel_core.audit import ledger as audit_ledger
    from coresentinel_core.audit import subjects as audit_subjects

    try:
        store = runtime.store
        store.tasks.append({"id": task["id"], "objective": task["objective"],
                            "agent": task["agent"], "status": result["status"]})
        audit_ledger.append(store, audit_subjects.AGENT_ACTION, task["agent"],
                            task["objective"], result["status"],
                            {"evidence": len(result["evidence"]),
                             "denials": result["denials"],
                             "files_changed": result["files_changed"]})
    except Exception as e:
        runtime.logger.warn("task not persisted", task=task["id"], error=str(e))


def execute(objective, target_dir=".", roles=None, runtime=None, interactive=False,
            stop_on_failure=True):
    """Run a whole plan. Returns the plan, every result, and a summary."""
    started = time.perf_counter()
    built = plan(objective, roles, target_dir=target_dir)
    results, blocked_by = [], None

    if runtime:
        runtime.events.emit("TaskStarted", {"objective": objective,
                                            "tasks": len(built["tasks"])})

    for task in built["tasks"]:
        if blocked_by:
            results.append(protocol.build_result(
                task, protocol.PENDING,
                f"not run: the pipeline stopped at {blocked_by}"))
            continue

        result = run_task(task, target_dir, runtime, interactive)
        results.append(result)

        # UNSUPPORTED is not a failure. A role with no executor behind it has
        # not gone wrong; it simply has nothing to run yet.
        if stop_on_failure and result["status"] in (protocol.FAILED, protocol.DENIED):
            blocked_by = task["agent"]

    summary = protocol.summarise(results)
    summary["blocked_by"] = blocked_by
    summary["duration_ms"] = int((time.perf_counter() - started) * 1000)

    if runtime:
        runtime.events.emit("TaskCompleted", {"objective": objective, **summary})

    return {"plan": built, "results": results, "summary": summary,
            "verdict": "BLOCKED" if blocked_by else "CLEAR"}


def render(run):
    summary = run["summary"]
    lines = ["", "=" * 64,
             f"  👥 CoreSentinel Agent Run — {run['plan']['objective']}",
             "=" * 64,
             f"  Roles     : {summary['total']}  "
             f"({run['plan']['executable']} executable, "
             f"{run['plan']['unsupported']} awaiting an adapter)",
             "  " + "-" * 60]

    icons = {protocol.COMPLETED: "✓", protocol.FAILED: "✗", protocol.DENIED: "⛔",
             protocol.UNSUPPORTED: "?", protocol.PENDING: "·"}

    for result in run["results"]:
        icon = icons.get(result["status"], "·")
        lines.append(f"  [{icon}] {result['agent']:<12} {result['status']:<12} {result['summary']}")
        for item in result["evidence"]:
            command = item.get("command")
            lines.append(f"        evidence: {item['check']} — {item['status']}"
                         + (f"  $ {command} → exit {item.get('exit_code')}" if command else ""))
        for denial in result["denials"]:
            lines.append(f"        ⛔ {denial['permission']} denied — {denial['reason']}")
        for unresolved in result["unresolved"]:
            lines.append(f"        unresolved: {unresolved}")

    lines.append("  " + "-" * 60)
    lines.append(f"  {summary['completed']} completed · {summary['failed']} failed · "
                 f"{summary['unsupported']} unsupported · {summary['evidence']} evidence item(s) "
                 f"· {summary['denials']} denial(s)")
    if summary["blocked_by"]:
        lines.append(f"  Pipeline stopped at {summary['blocked_by']}.")
    lines.append(f"  Verdict   : {run['verdict']}")
    lines.append("=" * 64)
    return "\n".join(lines)
