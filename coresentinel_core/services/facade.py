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
from coresentinel_core.observability.metrics import Metrics
from coresentinel_core.observability import metrics as metering
from coresentinel_core.storage.ports import MAX_PAGE_SIZE, clamp_page

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
        "metrics.get": (READ, "metrics_get"),
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
        # Timed here rather than in each surface: this is the one path the CLI,
        # the API and MCP all take, so an operation is measured once however it
        # was invoked. The timer records on the way out even when the call
        # raised — a refused operation still cost time.
        with self._metrics().time(metering.SERVICE, operation):
            try:
                return method(**(arguments or {}))
            except TypeError as e:
                raise ServiceError(f"{operation}: {e}", "BAD_ARGUMENTS")

    def _metrics(self):
        return getattr(self.runtime, "metrics", None) or Metrics(enabled=False)

    def _timed(self, subject, name):
        """Time one subsystem's work. Nests inside the per-operation timer above:
        `service.gate.run` says how long the call took, `gate.run` says how much
        of that was the gate rather than the surface around it."""
        return self._metrics().time(subject, name)

    @staticmethod
    def _paging(limit, offset, returned, clamped, total, has_more):
        """The paging block every list operation returns beside its items.

        `total` is None when the collection was never counted. That is not the
        same as zero, and the two must not render the same way: a surface that
        prints "0 of 0" for "we did not count" is inventing a measurement.
        """
        return {
            "limit": limit,
            "offset": offset,
            "returned": returned,
            "total": total,
            "has_more": has_more,
            "next_offset": (offset + returned) if has_more else None,
            # Say so rather than silently returning fewer than were asked for.
            "clamped": clamped,
            "max_page_size": MAX_PAGE_SIZE,
        }

    @classmethod
    def _page(cls, items, limit, offset, clamped):
        """Page a collection already held in memory, so the total is known."""
        items = list(items)
        window = items[offset:offset + limit]
        return window, cls._paging(limit, offset, len(window), clamped,
                                   total=len(items),
                                   has_more=(offset + len(window)) < len(items))

    @classmethod
    def _window(cls, window, limit, offset, clamped):
        """Page a pre-fetched window of unknown total.

        The caller fetched one more than the page to learn whether another page
        exists. Reporting a total would mean scoring or reading the whole
        collection, which is the cost paging exists to avoid.
        """
        window = list(window)
        has_more = len(window) > limit
        return window[:limit], cls._paging(limit, offset, min(len(window), limit), clamped,
                                           total=None, has_more=has_more)

    def _target(self, project=None):
        return project or self.target

    def _emit(self, event, payload):
        self.runtime.events.emit(event, payload or {})

    # ---------------------------------------------------------------- project

    def project_inspect(self, project=None, verbose=False):
        from coresentinel_core.project import discovery
        report = discovery.inspect(self._target(project))
        return report if verbose else {**report, "dimensions": discovery.summary(report)}

    def project_list(self, limit=None, offset=0):
        limit, offset, clamped = clamp_page(limit, offset)
        projects, page = self._page(self.runtime.store.projects.all(), limit, offset, clamped)
        return {"projects": projects, "page": page}

    # ---------------------------------------------------------------- memory

    def memory_search(self, query, project=None, layers=None, min_confidence=0.0,
                      limit=None, offset=0):
        import coresentinel_recall as recall
        limit, offset, clamped = clamp_page(limit, offset)
        # Ranked retrieval has to score everything before it knows what the top
        # of the list is, so the offset is applied after ranking. One extra is
        # requested so the caller learns whether a further page exists without
        # anyone counting the whole store.
        with self._timed(metering.RECALL, "query"):
            ranked = recall.recall(query, self._target(project), layers, float(min_confidence),
                                   limit=offset + limit + 1)
        results, page = self._window(ranked[offset:], limit, offset, clamped)
        return {"query": query, "results": results, "count": len(results), "page": page}

    def memory_store(self, layer, fact, confidence=0.95, source="service", project=None,
                     pinned=False, transferable=False):
        import coresentinel_memory as mem
        target = self._target(project)
        with self._timed(metering.MEMORY, "store"):
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
            with self._timed(metering.CONTEXT, "project_pack"):
                return context.build_project_context(target)
        with self._timed(metering.CONTEXT, "assemble"):
            pack = assembly.assemble(task, target,
                                     int(budget or assembly.DEFAULT_BUDGET_TOKENS),
                                     float(min_confidence))
        # Recorded so a pack that creeps toward its ceiling is visible before it
        # starts truncating: this is the number R-05 says to watch.
        self._metrics().observe(metering.CONTEXT, "pack_tokens",
                                pack.get("estimated_tokens", 0), unit="tokens")
        return pack

    # ---------------------------------------------------------------- decisions

    def decision_search(self, query=None, project=None, limit=None, offset=0):
        from coresentinel_core.decisions import ledger
        limit, offset, clamped = clamp_page(limit, offset)
        records = ledger.load(self._target(project))
        if query:
            needle = str(query).lower()
            records = [r for r in records
                       if needle in " ".join(str(r.get(k, "")).lower()
                                             for k in ("decision", "reason", "chosen", "problem"))]
        # The ledger is a JSON file read whole, by ADR-001. Paging bounds the
        # response, not the read; a decision ledger is human-scale by design.
        decisions, page = self._page(records, limit, offset, clamped)
        return {"decisions": decisions, "count": len(decisions), "page": page}

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

    def agent_list(self, limit=None, offset=0):
        from coresentinel_core.agents import registry
        limit, offset, clamped = clamp_page(limit, offset)
        agents, page = self._page(registry.load(), limit, offset, clamped)
        return {"agents": agents, "count": len(agents), "page": page}

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
        with self._timed(metering.AGENT, f"dispatch.{agent}"):
            return orchestrator.run_task(task, target, self.runtime)

    def agent_status(self, project=None, limit=None, offset=0):
        return self.task_list(project, limit, offset)

    # ---------------------------------------------------------------- tasks

    def task_run(self, objective, project=None, roles=None):
        from coresentinel_core.agents import orchestrator
        selected = [r.strip() for r in roles.split(",")] if isinstance(roles, str) else roles
        with self._timed(metering.TASK, "run"):
            return orchestrator.execute(objective, self._target(project), selected, self.runtime)

    def task_list(self, project=None, limit=None, offset=0):
        limit, offset, clamped = clamp_page(limit, offset)
        # page() reads only the window: the backend never loads the collection.
        window = self.runtime.store.tasks.page(limit + 1, offset)
        tasks, page = self._window(window, limit, offset, clamped)
        return {"tasks": tasks, "page": page}

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
            with self._timed(metering.GATE, f"evaluate.{name}"):
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
        with self._timed(metering.VERIFICATION, "run"):
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

    def incident_list(self, project=None, limit=None, offset=0):
        from coresentinel_core.incidents import ledger as incidents
        limit, offset, clamped = clamp_page(limit, offset)
        target = self._target(project)
        records, page = self._page(incidents.load(target), limit, offset, clamped)
        # The summary describes every incident, not the page — a count of open
        # incidents that shrank because you asked for page two would be a lie.
        return {"incidents": records, "summary": incidents.summary(target), "page": page}

    # ---------------------------------------------------------------- patterns

    def pattern_search(self, query=None, project=None, limit=None, offset=0):
        from coresentinel_core.patterns import ledger as patterns
        limit, offset, clamped = clamp_page(limit, offset)
        records = patterns.load(self._target(project), include_core=True)
        if query:
            needle = str(query).lower()
            records = [r for r in records
                       if needle in " ".join(str(r.get(k, "")).lower()
                                             for k in ("name", "problem", "solution", "gotchas"))]
        found, page = self._page(records, limit, offset, clamped)
        return {"patterns": found, "count": len(found), "page": page}

    # ---------------------------------------------------------------- audit

    def audit_list(self, limit=None, subject=None, offset=0):
        from coresentinel_core.audit import ledger as audit
        limit, offset, clamped = clamp_page(limit, offset)
        window = audit.recent(self.runtime.store, limit + 1, subject, offset)
        records, page = self._window(window, limit, offset, clamped)
        return {"records": records, "page": page}

    def audit_record(self, actor, action, subject="agent_action", result=None, detail=None):
        from coresentinel_core.audit import ledger as audit
        with self._timed(metering.AUDIT, "append"):
            return audit.append(self.runtime.store, subject, actor, action, result, detail)

    def audit_verify(self):
        from coresentinel_core.audit import ledger as audit
        return audit.verify(self.runtime.store)

    # ---------------------------------------------------------------- metrics

    def metrics_get(self, subject=None, limit=None, offset=0):
        """Measurements across runs, plus the published budgets they are held to."""
        from coresentinel_core.observability import budgets, metrics as metering

        limit, offset, clamped = clamp_page(limit, offset)
        persisted = metering.aggregate(self.runtime.store.metrics.all())
        if subject:
            persisted = [s for s in persisted if s["subject"] == subject]
        series, page = self._page(persisted, limit, offset, clamped)

        observed = {s["subject"] for s in persisted}
        return {
            "coresentinel_api": "1.1",
            "series": series,
            "page": page,
            "live": self._metrics().snapshot(),
            "coverage": {
                "observed": sorted(s for s in metering.SUBJECTS if s in observed),
                "never_observed": sorted(s for s in metering.SUBJECTS if s not in observed),
                "total": len(metering.SUBJECTS),
            },
            "budgets": budgets.report(self._budget_observations(persisted)),
        }

    @staticmethod
    def _budget_observations(series):
        """Map recorded series onto published budget keys.

        Only budgets something actually measured get a number. The rest stay
        UNKNOWN rather than defaulting to a pass — the same rule the health
        scorecard keeps for a dimension nothing could evidence.
        """
        by_name = {(s["subject"], s["name"]): s for s in series}
        found = {}
        for key, (subject, name) in {
            "runtime.bootstrap_ms": (metering.COMMAND, "bootstrap"),
            "context.assemble_10k_facts_ms": (metering.CONTEXT, "assemble"),
            "recall.10k_facts_ms": (metering.RECALL, "query"),
        }.items():
            entry = by_name.get((subject, name))
            if entry and entry.get("mean") is not None:
                found[key] = entry["mean"]
        return found

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
