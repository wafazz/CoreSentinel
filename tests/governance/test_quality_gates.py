"""Quality Gates pipeline — ordering, waivers, reset and ledger persistence."""

import json

import pytest


@pytest.fixture
def gates(tmp_path, monkeypatch):
    import coresentinel_gates as engine

    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    monkeypatch.setattr(engine, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(engine, "GATES_FILE", memory_dir / "gates.json")
    return engine


class TestPipelineDefinition:
    def test_declares_ten_ordered_gates(self, gates):
        assert len(gates.GATE_PIPELINE) == 10

    def test_the_original_eight_keep_their_names_and_order(self, gates):
        """Requirement and Documentation were added; nothing was renamed or reordered."""
        original = ["Plan", "Architecture", "Security", "Implementation",
                    "Test", "Review", "Verification", "Deployment"]
        kept = [name for name in gates.GATE_PIPELINE if name in original]
        assert kept == original

    def test_requirement_comes_first_and_documentation_precedes_deployment(self, gates):
        pipeline = gates.GATE_PIPELINE
        assert pipeline[0] == "Requirement"
        assert pipeline.index("Documentation") < pipeline.index("Deployment")

    def test_security_precedes_implementation(self, gates):
        """Security review must gate implementation, not trail it."""
        pipeline = gates.GATE_PIPELINE
        assert pipeline.index("Security") < pipeline.index("Implementation")

    def test_verification_precedes_deployment(self, gates):
        pipeline = gates.GATE_PIPELINE
        assert pipeline.index("Verification") < pipeline.index("Deployment")

    def test_deployment_is_the_final_gate(self, gates):
        assert gates.GATE_PIPELINE[-1] == "Deployment"

    def test_gate_names_are_unique(self, gates):
        assert len(gates.GATE_PIPELINE) == len(set(gates.GATE_PIPELINE))


class TestGateLedger:
    def test_initializes_every_gate(self, gates):
        gates.ensure_gates_file()
        state = gates.load_gates()
        assert len(state["gates"]) == 10

    def test_save_and_load_roundtrip(self, gates):
        gates.ensure_gates_file()
        state = gates.load_gates()
        state["gates"]["Plan"]["status"] = "FAIL"
        gates.save_gates(state)
        assert gates.load_gates()["gates"]["Plan"]["status"] == "FAIL"

    def test_reset_clears_prior_results(self, gates):
        gates.ensure_gates_file()
        state = gates.load_gates()
        state["gates"]["Plan"]["status"] = "FAIL"
        gates.save_gates(state)

        gates.reset_gates()
        assert gates.load_gates()["gates"]["Plan"]["status"] != "FAIL"


class TestWaivers:
    def test_waiver_records_the_rationale(self, gates):
        gates.ensure_gates_file()
        gates.waive_gate("Security", "Sandbox environment, approved by Fakrul")

        gate = gates.load_gates()["gates"]["Security"]
        assert gate["status"] == "WAIVED"
        assert "Sandbox environment" in (gate.get("waived_reason") or gate.get("reason") or "")

    def test_waiver_never_silently_reports_pass(self, gates):
        """A waived gate must stay distinguishable from a genuinely passed one."""
        gates.ensure_gates_file()
        gates.waive_gate("Test", "No test suite in this repository")
        assert gates.load_gates()["gates"]["Test"]["status"] == "WAIVED"

    def test_unknown_gate_is_rejected(self, gates, capsys):
        gates.ensure_gates_file()
        gates.waive_gate("NotAGate", "should not apply")
        assert "NotAGate" not in gates.load_gates()["gates"]


class TestGateStateIsolation:
    """The suite once rewrote the repository's own memory/gates.json through
    gate.run on the service layer. The rule was stated in conftest and enforced
    only where a test author had remembered it."""

    def test_the_engine_never_points_at_the_real_core_state(self):
        import coresentinel_gates as engine
        from tests.conftest import CORE_DIR

        assert engine.GATES_FILE != CORE_DIR / "memory" / "gates.json"

    def test_a_write_through_the_service_layer_leaves_the_real_file_alone(self, tmp_path):
        import coresentinel_memory as mem
        import coresentinel_core.runtime.config as config_module
        from coresentinel_core.runtime.container import Runtime
        from coresentinel_core.services import Services
        from tests.conftest import CORE_DIR
        import json as json_module

        real = CORE_DIR / "memory" / "gates.json"
        before = real.read_bytes() if real.is_file() else None

        root = tmp_path / "repo"
        (root / ".coresentinel" / "memory").mkdir(parents=True)
        (root / ".coresentinel" / "config.json").write_text(
            json_module.dumps({"project_name": "repo"}), encoding="utf-8")

        runtime = Runtime.bootstrap(str(root))
        try:
            Services(runtime).call("gate.run", {})
        finally:
            runtime.shutdown()

        after = real.read_bytes() if real.is_file() else None
        assert after == before, "gate.run rewrote the repository's own gate state"
