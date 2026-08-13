"""Agent protocol validation, planning and orchestration.

CoreSentinel's job is to be the thing that does not take an agent's word for it,
so the load-bearing tests here are the ones that reject a result rather than the
ones that accept it.
"""

import json

import pytest

from coresentinel_core.agents import protocol, orchestrator, builtin, registry
from coresentinel_core.agents.sandbox import AgentSandbox


@pytest.fixture
def repo(tmp_path, monkeypatch):
    import coresentinel_memory as mem

    root = tmp_path / "repo"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "repo"}), encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")

    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    return root


def a_task(agent="Scout", objective="do the thing"):
    return protocol.build_task(objective, agent)


class TestResultValidation:
    def test_a_valid_result_passes(self):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"check": "x", "status": "PASS"}])
        assert protocol.validate_result(result) == []

    def test_a_success_claim_without_evidence_is_rejected(self):
        """Exactly the claim CoreSentinel exists to refuse."""
        result = protocol.build_result(a_task(), protocol.COMPLETED, "all done")
        problems = protocol.validate_result(result)
        assert any("evidence or actions" in p for p in problems)

    def test_a_missing_required_field_is_rejected(self):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"check": "x", "status": "PASS"}])
        result["summary"] = ""
        assert any("summary" in p for p in protocol.validate_result(result))

    def test_an_unknown_status_is_rejected(self):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"check": "x", "status": "PASS"}])
        result["status"] = "FINE_PROBABLY"
        assert any("unknown status" in p for p in protocol.validate_result(result))

    def test_a_non_dictionary_result_is_rejected(self):
        assert protocol.validate_result("done!")

    def test_a_list_field_of_the_wrong_type_is_rejected(self):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"check": "x", "status": "PASS"}])
        result["warnings"] = "not a list"
        assert any("'warnings' must be a list" in p for p in protocol.validate_result(result))

    @pytest.mark.parametrize("confidence", [-0.1, 1.5, "high"])
    def test_an_out_of_range_confidence_is_rejected(self, confidence):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"check": "x", "status": "PASS"}],
                                       confidence=confidence)
        assert any("confidence" in p for p in protocol.validate_result(result))

    def test_evidence_must_say_what_it_checked(self):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"status": "PASS"}])
        assert any("what it checked" in p for p in protocol.validate_result(result))

    def test_evidence_must_state_a_status(self):
        result = protocol.build_result(a_task(), protocol.COMPLETED, "done",
                                       evidence=[{"check": "x"}])
        assert any("does not state a status" in p for p in protocol.validate_result(result))

    def test_task_ids_are_stable_across_identical_plans(self):
        assert protocol.task_id("obj", "Scout", 0) == protocol.task_id("obj", "Scout", 0)
        assert protocol.task_id("obj", "Scout", 0) != protocol.task_id("obj", "Scout", 1)


class TestPlanner:
    def test_the_plan_follows_the_dependency_order(self):
        """Reviewing a change before it is written reviews nothing."""
        agents = [task["agent"] for task in orchestrator.plan("anything")["tasks"]]
        assert agents.index("Builder") < agents.index("Tester")
        assert agents.index("Tester") < agents.index("Reviewer")
        assert agents.index("Security") < agents.index("DevOps")

    def test_every_task_declares_whether_anything_can_run_it(self):
        for task in orchestrator.plan("anything")["tasks"]:
            assert isinstance(task["executable"], bool)

    def test_the_plan_counts_what_awaits_an_adapter(self):
        built = orchestrator.plan("anything")
        assert built["executable"] + built["unsupported"] == len(built["tasks"])
        assert built["executable"] > 0

    def test_roles_can_be_narrowed(self):
        built = orchestrator.plan("anything", roles=["Scout", "Security"])
        assert [t["agent"] for t in built["tasks"]] == ["Scout", "Security"]

    def test_each_task_carries_its_contract_constraints(self):
        task = next(t for t in orchestrator.plan("x")["tasks"] if t["agent"] == "Tester")
        assert task["constraints"], "the contract's constraints did not reach the task"

    def test_tasks_are_chained_by_dependency(self):
        tasks = orchestrator.plan("anything")["tasks"]
        assert tasks[0]["depends_on"] is None
        assert tasks[1]["depends_on"] == tasks[0]["id"]


class TestBuiltinAgents:
    def test_scout_returns_evidence_and_writes_nothing(self, repo):
        task = a_task("Scout", "Add Redis caching")
        result = orchestrator.run_task(task, str(repo))
        assert result["status"] == protocol.COMPLETED
        assert result["evidence"] and result["files_changed"] == []

    def test_security_runs_the_scanner_and_reports_its_exit_code(self, repo):
        result = orchestrator.run_task(a_task("Security", "scan"), str(repo))
        assert result["status"] in (protocol.COMPLETED, protocol.FAILED)
        evidence = result["evidence"][0]
        assert evidence["command"] and evidence["exit_code"] is not None

    def test_an_unsupported_role_says_so_rather_than_succeeding(self, repo):
        result = orchestrator.run_task(a_task("Architect", "design it"), str(repo))
        assert result["status"] == protocol.UNSUPPORTED
        assert "needs a model" in result["summary"]
        assert result["unresolved"]

    def test_the_tester_reports_unsupported_when_no_runner_exists(self, repo):
        result = orchestrator.run_task(a_task("Tester", "run tests"), str(repo))
        assert result["status"] == protocol.UNSUPPORTED

    def test_every_builtin_result_survives_validation(self, repo):
        for name in builtin.BUILTIN:
            result = orchestrator.run_task(a_task(name, "do it"), str(repo))
            assert protocol.validate_result(result) == [], \
                f"{name} returned a result that fails validation: {result}"

    def test_a_result_carries_the_permissions_it_ran_under(self, repo):
        result = orchestrator.run_task(a_task("Scout", "x"), str(repo))
        assert result["permissions"]["filesystem.write"]["level"] == "DENY"


class TestFailureHandling:
    def test_a_raising_agent_becomes_a_failed_result_not_a_crash(self, repo, monkeypatch):
        def explode(task, sandbox, **kwargs):
            raise RuntimeError("the agent broke")

        monkeypatch.setitem(builtin.BUILTIN, "Scout", builtin._timed(explode))
        result = orchestrator.run_task(a_task("Scout", "x"), str(repo))
        assert result["status"] == protocol.FAILED
        assert "the agent broke" in result["summary"]

    def test_a_malformed_agent_result_is_rejected(self, repo, monkeypatch):
        def sloppy(task, sandbox, **kwargs):
            return {"status": "COMPLETED"}

        monkeypatch.setitem(builtin.BUILTIN, "Scout", sloppy)
        result = orchestrator.run_task(a_task("Scout", "x"), str(repo))
        assert result["status"] == protocol.FAILED
        assert result["warnings"], "the validation problems were not reported"

    def test_a_denied_agent_reports_denied_not_failed(self, repo, monkeypatch):
        from coresentinel_core.agents.sandbox import PermissionDenied

        def overreach(task, sandbox, **kwargs):
            sandbox.write("anywhere.txt", "x")

        monkeypatch.setitem(builtin.BUILTIN, "Scout", builtin._timed(overreach))
        result = orchestrator.run_task(a_task("Scout", "x"), str(repo))
        assert result["status"] == protocol.DENIED
        assert result["denials"]


class TestPipeline:
    def test_the_full_pipeline_runs_end_to_end(self, repo):
        run = orchestrator.execute("Add Redis caching to product listing", str(repo))
        assert len(run["results"]) == len(orchestrator.PIPELINE)
        assert run["summary"]["completed"] > 0

    def test_unsupported_roles_do_not_stop_the_pipeline(self, repo):
        """Nothing went wrong when a capability is simply not there yet."""
        run = orchestrator.execute("anything", str(repo))
        assert run["summary"]["unsupported"] > 0
        assert run["verdict"] == "CLEAR"
        assert all(r["status"] != protocol.PENDING for r in run["results"])

    def test_a_failing_role_stops_the_pipeline(self, repo, monkeypatch):
        def fail(task, sandbox, **kwargs):
            return protocol.build_result(task, protocol.FAILED, "it went wrong")

        monkeypatch.setitem(builtin.BUILTIN, "Scout", fail)
        run = orchestrator.execute("anything", str(repo))
        assert run["verdict"] == "BLOCKED"
        assert run["summary"]["blocked_by"] == "Scout"
        assert any(r["status"] == protocol.PENDING for r in run["results"])

    def test_a_stopped_pipeline_leaves_later_tasks_pending_not_failed(self, repo, monkeypatch):
        def fail(task, sandbox, **kwargs):
            return protocol.build_result(task, protocol.FAILED, "it went wrong")

        monkeypatch.setitem(builtin.BUILTIN, "Scout", fail)
        run = orchestrator.execute("anything", str(repo))
        later = [r for r in run["results"] if r["status"] == protocol.PENDING]
        assert later and all("stopped at Scout" in r["summary"] for r in later)

    def test_the_run_is_json_serialisable(self, repo):
        json.dumps(orchestrator.execute("anything", str(repo), roles=["Scout", "Security"]))

    def test_the_summary_counts_evidence_and_denials(self, repo):
        run = orchestrator.execute("anything", str(repo), roles=["Scout", "Security"])
        assert run["summary"]["evidence"] >= 1
        assert "denials" in run["summary"]


class TestAuditIntegration:
    def test_a_run_records_a_task_and_an_audit_event(self, repo, monkeypatch):
        import coresentinel_core.runtime.config as config_module
        from coresentinel_core.runtime.container import Runtime

        monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", repo / "core.config.json")
        runtime = Runtime.bootstrap(str(repo))
        orchestrator.run_task(a_task("Scout", "x"), str(repo), runtime)

        assert runtime.store.tasks.count() == 1
        audit = runtime.store.audit_events.recent(1)[0]
        assert audit["actor"] == "Scout"
        assert audit["subject"] == "agent_action", \
            "the subject must be one of the twelve, not an ad-hoc string"
        assert audit["hash"] and audit["seq"], \
            "the record bypassed the ledger and is outside the chain"
        runtime.shutdown()

    def test_a_denial_reaches_the_audit_trail(self, repo, monkeypatch):
        import coresentinel_core.runtime.config as config_module
        from coresentinel_core.runtime.container import Runtime

        def overreach(task, sandbox, **kwargs):
            sandbox.write("anywhere.txt", "x")

        monkeypatch.setitem(builtin.BUILTIN, "Scout", builtin._timed(overreach))
        monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", repo / "core.config.json")
        runtime = Runtime.bootstrap(str(repo))
        orchestrator.run_task(a_task("Scout", "x"), str(repo), runtime)

        audit = runtime.store.audit_events.recent(1)[0]
        assert audit["detail"]["denials"], "a denied write left no audit record"
        runtime.shutdown()

    def test_agent_events_are_emitted(self, repo, monkeypatch):
        import coresentinel_core.runtime.config as config_module
        from coresentinel_core.runtime.container import Runtime

        monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", repo / "core.config.json")
        runtime = Runtime.bootstrap(str(repo))
        seen = []
        runtime.events.subscribe("*", seen.append)
        orchestrator.run_task(a_task("Scout", "x"), str(repo), runtime)

        names = [event.name for event in seen]
        assert "AgentStarted" in names and "AgentCompleted" in names
        runtime.shutdown()
