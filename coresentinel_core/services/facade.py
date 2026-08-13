"""
Every operation CoreSentinel offers, in one place.

Methods return plain data — dicts and lists, JSON-serialisable, no engine objects
leaking out. A surface renders what it gets; it never has to know which module
produced it.

Mutating methods emit an event before returning. That is not a convention a
caller can forget: auditing subscribes to the bus, so an operation that emits is
an operation that is recorded, through whichever surface invoked it.
"""

from pathlib import Path

from coresentinel_core.runtime.container import Runtime
from coresentinel_core.runtime.errors import CoreSentinelError

READ, WRITE = "read", "write"


class ServiceError(CoreSentinelError):
    """An operation was refused. Carries a machine-readable code for the surfaces."""

    def __init__(self, message, code="SERVICE_ERROR", remedy=None):
        super().__init__(message, remedy)
        self.code = code


class Services:
    """The whole surface area, bound to one working directory."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.target = runtime.target_dir

    # ---------------------------------------------------------------- catalogue

    #: name -> (mode, callable-name). The surfaces build their routes and tools
    #: from this, so a new operation appears everywhere at once or nowhere.
    OPERATIONS = {
        "project.inspect": (READ, "project_inspect"),
        "project.list": (READ, "project_list"),
        "memory.search": (READ, "memory_search"),
        "memory.store": (WRITE, "memory_store"),
        "memory.brief": (READ, "memory_brief"),
        "context.assemble": (READ, "context_assemble"),
        "decision.search": (READ, "decision_search"),
        "decision.create": (WRITE, "decision_create"),
        "decision.verify": (READ, "decision_verify"),
        "agent.list": (READ, "agent_list"),
        "agent.permissions": (READ, "agent_permissions"),
        "agent.dispatch": (WRITE, "agent_dispatch"),
        "agent.status": (READ, "agent_status"),
        "task.run": (WRITE, "task_run"),
        "task.list": (READ, "task_list"),
        "gate.status": (READ, "gate_status"),
        "gate.run": (WRITE, "gate_run"),
        "verification.run": (WRITE, "verification_run"),
        "health.get": (READ, "health_get"),
        "review.run": (READ, "review_run"),
        "incident.create": (WRITE, "incident_create"),
        "incident.list": (READ, "incident_list"),
        "pattern.search": (READ, "pattern_search"),
        "audit.list": (READ, "audit_list"),
        "audit.record": (WRITE, "audit_record"),
        "audit.verify": (READ, "audit_verify"),
        "knowledge.query": (READ, "knowledge_query"),
    }

    def mode(self, operation):
        entry = self.OPERATIONS.get(operation)
        if not entry:
            raise ServiceError(f"unknown operation '{operation}'", "UNKNOWN_OPERATION")
        return entry[0]

    def call(self, operation, arguments=None):
        """Invoke by name. The one entry point the API and MCP use."""
        entry = self.OPERATIONS.get(operation)
        if not entry:
            raise ServiceError(f"unknown operation '{operation}'", "UNKNOWN_OPERATION",
                               f"Known: {', '.join(sorted(self.OPERATIONS))}")
        method = getattr(self, entry[1])
        try:
            return method(**(arguments or {}))
        except TypeError as e:
            raise ServiceError(f"{operation}: {e}", "BAD_ARGUMENTS")

    def _target(self, project=None):
        return project or self.target

    def _emit(self, event, payload):
        self.runtime.events.emit(event, payload or {})

    # ---------------------------------------------------------------- project

    def project_inspect(self, project=None, verbose=False):
        from coresentinel_core.project import discovery
        report = discovery.inspect(self._target(project))
        return report if verbose else {**report, "dimensions": discovery.summary(report)}

    def project_list(self):
        return {"projects": self.runtime.store.projects.all()}

    # ---------------------------------------------------------------- memory

    def memory_search(self, query, project=None, layers=None, min_confidence=0.0, limit=20):
        import coresentinel_recall as recall
        hits = recall.recall(query, self._target(project), layers, float(min_confidence),
                             limit=int(limit))
        return {"query": query, "results": hits, "count": len(hits)}

    def memory_store(self, layer, fact, confidence=0.95, source="service", project=None,
                     pinned=False, transferable=False):
        import coresentinel_memory as mem
        target = self._target(project)
        stored = mem.add_fact(layer, fact, float(confidence), source, target,
                              pinned=bool(pinned), transferable=bool(transferable))
        if not stored:
            raise ServiceError(f"could not record the fact in '{layer}'", "MEMORY_WRITE_FAILED")
        self._emit("MemoryCreated", {"layer": layer, "fact": fact,
                                     "confidence": confidence, "source": source})
        return {"stored": True, "layer": layer, "fact": fact}

    def memory_brief(self, project=None, days=7):
        import coresentinel_recall as recall
        return recall.build_briefing(self._target(project), int(days))

    # ---------------------------------------------------------------- context

    def context_assemble(self, task=None, project=None, budget=None, min_confidence=0.0):
        from coresentinel_core.memory import assembly
        target = self._target(project)
        if not task:
            import coresentinel_context as context
            return context.build_project_context(target)
        return assembly.assemble(task, target,
                                 int(budget or assembly.DEFAULT_BUDGET_TOKENS),
                                 float(min_confidence))

    # ---------------------------------------------------------------- decisions

    def decision_search(self, query=None, project=None):
        from coresentinel_core.decisions import ledger
        records = ledger.load(self._target(project))
        if query:
            needle = str(query).lower()
            records = [r for r in records
                       if needle in " ".join(str(r.get(k, "")).lower()
                                             for k in ("decision", "reason", "chosen", "problem"))]
        return {"decisions": records, "count": len(records)}

    def decision_create(self, title, reason, chosen, project=None, **fields):
        from coresentinel_core.decisions import ledger
        record = ledger.add(self._target(project), title=title, reason=reason,
                            chosen=chosen, **fields)
        if not record:
            raise ServiceError("the decision ledger is unreadable; nothing was written",
                               "LEDGER_UNREADABLE")
        self._emit("DecisionCreated", {"decision": record["id"], "title": record["title"],
                                       "chosen": record["chosen"]})
        return record

    def decision_verify(self, change, project=None):
        from coresentinel_core.decisions import contradiction
        return contradiction.verify(change, self._target(project))

    # ---------------------------------------------------------------- agents

    def agent_list(self):
        from coresentinel_core.agents import registry
        return {"agents": registry.load(), "count": len(registry.names())}

    def agent_permissions(self, agent=None):
        from coresentinel_core.agents import registry
        if not agent:
            return registry.audit()
        contract = registry.get(agent)
        if not contract:
            raise ServiceError(f"unknown agent '{agent}'", "UNKNOWN_AGENT",
                               f"Known: {', '.join(registry.names())}")
        return {"agent": contract["name"], "authority": contract["authority"],
                "permissions": registry.permissions_for(agent).summary()}

    def agent_dispatch(self, agent, objective, project=None):
        from coresentinel_core.agents import registry, orchestrator, protocol
        if not registry.get(agent):
            raise ServiceError(f"unknown agent '{agent}'", "UNKNOWN_AGENT")
        target = self._target(project)
        task = protocol.build_task(objective, registry.get(agent)["name"], project=target)
        return orchestrator.run_task(task, target, self.runtime)

    def agent_status(self, project=None, limit=20):
        return {"tasks": self.runtime.store.tasks.recent(int(limit))}

    # ---------------------------------------------------------------- tasks

    def task_run(self, objective, project=None, roles=None):
        from coresentinel_core.agents import orchestrator
        selected = [r.strip() for r in roles.split(",")] if isinstance(roles, str) else roles
        return orchestrator.execute(objective, self._target(project), selected, self.runtime)

    def task_list(self, project=None, limit=20):
        return {"tasks": self.runtime.store.tasks.recent(int(limit))}

    # ---------------------------------------------------------------- gates

    def gate_status(self, project=None):
        import coresentinel_gates as gates
        state = gates.load_gates()
        collected = state.get("gates", {})
        for name in gates.GATE_PIPELINE:
            collected.setdefault(name, gates.blank_gate())
        return {"pipeline": gates.GATE_PIPELINE, "gates": collected,
                "codes": {n: g.get("code") for n, g in collected.items()}}

    def gate_run(self, project=None, objective=None):
        import coresentinel_gates as gates
        target = self._target(project)
        state = gates.load_gates()
        collected = state.setdefault("gates", {})
        blocked_by = None
        for name in gates.GATE_PIPELINE:
            if (collected.get(name) or {}).get("status") == gates.WAIVED:
                continue
            if blocked_by:
                collected[name] = {"status": gates.BLOCKED, "code": "UPSTREAM_FAILED",
                                   "reason": f"blocked at {blocked_by}", "basis": None,
                                   "waived_reason": None}
                continue
            status, code, reason, basis = gates.evaluate_gate(name, target, objective)
            collected[name] = {"status": status, "code": code, "reason": reason,
                               "basis": basis, "waived_reason": None}
            if status == gates.FAIL:
                blocked_by = name
        gates.save_gates(state)
        self._emit("QualityGateFailed" if blocked_by else "QualityGatePassed",
                   {"objective": objective, "result": "BLOCKED" if blocked_by else "APPROVED"})
        return {"gates": collected, "blocked_by": blocked_by,
                "final_status": "BLOCKED" if blocked_by else "APPROVED"}

    # ---------------------------------------------------------------- verification

    def verification_run(self, project=None, claim=""):
        import coresentinel_evidence as evidence
        target = self._target(project)
        report = evidence.verify(target, claim)
        self._emit("VerificationCompleted", {"claim": claim, "result": report["verdict"]})
        return report

    def health_get(self, project=None):
        import coresentinel_score as score
        return score.evaluate_health_score(self._target(project))

    def review_run(self, project=None, strict=False):
        import coresentinel_review as review
        findings, changed, stats = review.review_diff(self._target(project), bool(strict))
        blocking = [f for f in findings if f["severity"] == "BLOCK"]
        return {"findings": findings, "changed_files": changed, "stats": stats,
                "verdict": "CHANGES REQUIRED" if blocking else
                           ("APPROVED" if changed else "NOTHING TO REVIEW")}

    # ---------------------------------------------------------------- incidents

    def incident_create(self, title, problem=None, project=None, **fields):
        from coresentinel_core.incidents import ledger as incidents
        record = incidents.create(self._target(project), title=title, problem=problem, **fields)
        if not record:
            raise ServiceError("the incident ledger is unreadable; nothing was written",
                               "LEDGER_UNREADABLE")
        self._emit("IncidentCreated", {"incident": record["id"], "title": record["title"],
                                       "severity": record["severity"]})
        return record

    def incident_list(self, project=None):
        from coresentinel_core.incidents import ledger as incidents
        target = self._target(project)
        return {"incidents": incidents.load(target), "summary": incidents.summary(target)}

    # ---------------------------------------------------------------- patterns

    def pattern_search(self, query=None, project=None):
        from coresentinel_core.patterns import ledger as patterns
        records = patterns.load(self._target(project), include_core=True)
        if query:
            needle = str(query).lower()
            records = [r for r in records
                       if needle in " ".join(str(r.get(k, "")).lower()
                                             for k in ("name", "problem", "solution", "gotchas"))]
        return {"patterns": records, "count": len(records)}

    # ---------------------------------------------------------------- audit

    def audit_list(self, limit=20, subject=None):
        from coresentinel_core.audit import ledger as audit
        return {"records": audit.recent(self.runtime.store, int(limit), subject)}

    def audit_record(self, actor, action, subject="agent_action", result=None, detail=None):
        from coresentinel_core.audit import ledger as audit
        return audit.append(self.runtime.store, subject, actor, action, result, detail)

    def audit_verify(self):
        from coresentinel_core.audit import ledger as audit
        return audit.verify(self.runtime.store)

    # ---------------------------------------------------------------- knowledge

    def knowledge_query(self, entity=None, project=None, depth=2):
        from coresentinel_core.knowledge import graph as knowledge
        built = knowledge.build(self._target(project))
        if not entity:
            return {**built.describe(), "dangling": len(built.dangling())}
        matches = built.find(entity)
        if not matches:
            raise ServiceError(f"no entity matches '{entity}'", "UNKNOWN_ENTITY")
        return built.traverse(matches[0]["id"], int(depth))


def open_services(target_dir=".", runtime=None):
    """Bind the services to a working directory. Caller owns the runtime's lifetime."""
    return Services(runtime or Runtime.bootstrap(str(Path(target_dir))))
