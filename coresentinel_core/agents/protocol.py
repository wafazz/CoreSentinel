"""
The agent protocol — the contract every adapter translates to and from.

CoreSentinel's job is to be the thing that does not take an agent's word for it.
So a result is a *structured claim* that has to survive validation before it is
recorded: a status the orchestrator understands, evidence for anything asserted,
and an explicit place to say what is still unresolved.

`UNSUPPORTED` is a first-class status, for the same reason `UNKNOWN` is in
verification and `unknown` is in discovery. A role with no executor behind it
reports that it could not run. It does not report success.
"""

import hashlib
from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

PENDING = "PENDING"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
DENIED = "DENIED"
UNSUPPORTED = "UNSUPPORTED"

STATUSES = [PENDING, RUNNING, COMPLETED, FAILED, DENIED, UNSUPPORTED]

# Statuses that mean the agent actually did the work it was asked to do.
SUCCESSFUL = {COMPLETED}

# Statuses that must not stop a pipeline: nothing went wrong, the capability
# simply is not there yet.
NON_FATAL = {UNSUPPORTED}

REQUIRED_RESULT_FIELDS = ["task_id", "agent", "status", "summary"]

LIST_RESULT_FIELDS = ["actions", "files_changed", "commands_run", "tests",
                      "evidence", "warnings", "unresolved", "denials"]


def _stamp(now=None):
    return (now or datetime.now()).strftime(TIMESTAMP_FORMAT)


def task_id(objective, agent, index=0):
    """Derived from the work, so the same plan re-run produces the same ids."""
    digest = hashlib.sha1(f"{agent}:{objective}:{index}".encode("utf-8")).hexdigest()
    return f"TSK-{digest[:10]}"


def build_task(objective, agent, project=None, inputs=None, context_pack=None,
               constraints=None, parent_task=None, index=0, now=None):
    return {
        "id": task_id(objective, agent, index),
        "project": project,
        "agent": agent,
        "objective": objective,
        "inputs": inputs or {},
        "context_pack": context_pack,
        "constraints": list(constraints or []),
        "parent_task": parent_task,
        "created_at": _stamp(now),
        "status": PENDING,
    }


def build_result(task, status, summary, **fields):
    result = {
        "coresentinel_api": "1.1",
        "task_id": task.get("id") if isinstance(task, dict) else task,
        "agent": task.get("agent") if isinstance(task, dict) else None,
        "status": status if status in STATUSES else FAILED,
        "summary": summary,
        "confidence": fields.get("confidence"),
        "raw_response_ref": fields.get("raw_response_ref"),
        "started_at": fields.get("started_at"),
        "finished_at": fields.get("finished_at", _stamp()),
        "duration_ms": fields.get("duration_ms"),
    }
    for name in LIST_RESULT_FIELDS:
        result[name] = list(fields.get(name) or [])
    return result


def validate_result(result):
    """Reject a malformed result rather than record it.

    An agent that returns something the orchestrator cannot read is an agent
    whose work cannot be audited, and recording it anyway is how an unverifiable
    claim gets into the trail wearing a valid-looking shape.
    """
    problems = []

    if not isinstance(result, dict):
        return [f"result must be a dictionary, got {type(result).__name__}"]

    for field in REQUIRED_RESULT_FIELDS:
        if not result.get(field):
            problems.append(f"missing required field '{field}'")

    status = result.get("status")
    if status and status not in STATUSES:
        problems.append(f"unknown status '{status}'; expected one of {', '.join(STATUSES)}")

    for field in LIST_RESULT_FIELDS:
        if field in result and not isinstance(result[field], list):
            problems.append(f"'{field}' must be a list, got {type(result[field]).__name__}")

    confidence = result.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            problems.append("'confidence' must be a number between 0 and 1")

    # The whole point of the system: a claim of success carries its evidence.
    if status == COMPLETED and not result.get("evidence") and not result.get("actions"):
        problems.append("a COMPLETED result must carry evidence or actions — "
                        "a claim of success with neither is exactly what CoreSentinel exists "
                        "to refuse")

    for index, item in enumerate(result.get("evidence") or []):
        if not isinstance(item, dict):
            problems.append(f"evidence[{index}] must be a dictionary")
            continue
        if not item.get("check"):
            problems.append(f"evidence[{index}] does not say what it checked")
        if item.get("status") is None:
            problems.append(f"evidence[{index}] does not state a status")

    return problems


def evidence_from_execution(check, execution, status):
    """Turn a Phase 1 Execution into an evidence item, keeping the same shape."""
    record = execution.record()
    record.update({"check": check, "status": status})
    return record


def summarise(results):
    counts = {status: 0 for status in STATUSES}
    for result in results:
        counts[result.get("status", FAILED)] = counts.get(result.get("status", FAILED), 0) + 1
    return {
        "total": len(results),
        "counts": counts,
        "completed": counts[COMPLETED],
        "failed": counts[FAILED] + counts[DENIED],
        "unsupported": counts[UNSUPPORTED],
        "evidence": sum(len(r.get("evidence") or []) for r in results),
        "denials": sum(len(r.get("denials") or []) for r in results),
    }
