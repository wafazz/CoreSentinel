"""Quality gates — machine-readable reasons, and the completion report.

A CI job should be able to branch on *why* a gate failed without parsing a
sentence. "The pipeline is red" and "the test runner is not installed on this
machine" are different facts and only one of them is a problem with the change.
"""

import json
import re
from pathlib import Path

import pytest

import coresentinel_gates as gates


@pytest.fixture
def isolated_gates(tmp_path, monkeypatch):
    memory = tmp_path / "memory"
    memory.mkdir()
    monkeypatch.setattr(gates, "MEMORY_DIR", memory)
    monkeypatch.setattr(gates, "GATES_FILE", memory / "gates.json")
    return gates


class TestReasonCodes:
    def test_every_gate_reports_a_code(self, isolated_gates, git_repo, capsys):
        isolated_gates.run_all_gates(str(git_repo.path), emit_json=True)
        report = json.loads(capsys.readouterr().out)
        for name, gate in report["gates"].items():
            assert gate.get("code"), f"{name} reported no reason code"

    def test_every_emitted_code_is_declared(self, isolated_gates, git_repo, capsys):
        isolated_gates.run_all_gates(str(git_repo.path), emit_json=True)
        report = json.loads(capsys.readouterr().out)
        unknown = [c for c in report["codes"].values() if c not in gates.CODES]
        assert not unknown, f"undeclared reason codes emitted: {unknown}"

    def test_codes_are_machine_readable_not_prose(self):
        for code in gates.CODES:
            assert re.fullmatch(r"[A-Z][A-Z0-9_]*", code), \
                f"'{code}' is not a stable identifier"

    def test_a_missing_test_runner_is_distinguishable_from_a_failure(self, tmp_path):
        status, code, _, _ = gates.evaluate_gate("Test", str(tmp_path))
        assert status == gates.UNKNOWN and code == "NO_TEST_RUNNER"

    def test_a_manual_gate_says_it_has_no_automated_check(self, tmp_path):
        for name in gates.MANUAL_GATES:
            status, code, _, _ = gates.evaluate_gate(name, str(tmp_path))
            assert status == gates.UNKNOWN and code == "NO_AUTOMATED_CHECK"

    def test_an_upstream_failure_is_coded(self, isolated_gates, git_repo, capsys, monkeypatch):
        def always_fail(name, target_dir=".", objective=None):
            if name == "Security":
                return gates.FAIL, "SCANNER_VIOLATIONS", "a secret was committed", "scanner"
            return gates.PASS, "REQUIREMENT_STATED", "fine", None

        monkeypatch.setattr(gates, "evaluate_gate", always_fail)
        isolated_gates.run_all_gates(str(git_repo.path), emit_json=True)
        report = json.loads(capsys.readouterr().out)

        assert report["gates"]["Security"]["code"] == "SCANNER_VIOLATIONS"
        assert report["gates"]["Deployment"]["code"] == "UPSTREAM_FAILED"
        assert report["blocked_by"] == "Security"


class TestNewStages:
    def test_the_pipeline_has_ten_ordered_stages(self):
        assert len(gates.GATE_PIPELINE) == 10
        assert gates.GATE_PIPELINE[0] == "Requirement"

    def test_a_stated_objective_satisfies_the_requirement_gate(self, tmp_path):
        status, code, _, _ = gates.evaluate_gate("Requirement", str(tmp_path),
                                                 objective="Add Redis caching")
        assert status == gates.PASS and code == "REQUIREMENT_STATED"

    def test_a_requirement_artifact_satisfies_it_too(self, tmp_path):
        (tmp_path / "Planning.md").write_text("# plan\n", encoding="utf-8")
        status, code, _, _ = gates.evaluate_gate("Requirement", str(tmp_path))
        assert status == gates.PASS and code == "REQUIREMENT_STATED"

    def test_no_objective_and_no_artifact_is_unknown_not_pass(self, tmp_path):
        status, code, _, _ = gates.evaluate_gate("Requirement", str(tmp_path))
        assert status == gates.UNKNOWN and code == "REQUIREMENT_MISSING"

    def test_documentation_fails_when_source_changed_alone(self, git_repo, write_file):
        write_file(git_repo.path / "README.md", "# docs\n")
        git_repo.git("add", "-A")
        git_repo.git("commit", "-q", "-m", "docs")
        write_file(git_repo.path / "app.py", "x = 1\n")

        status, code, _, _ = gates.evaluate_gate("Documentation", str(git_repo.path))
        assert status == gates.FAIL and code == "DOCS_STALE"

    def test_documentation_passes_when_docs_changed_alongside(self, git_repo, write_file):
        write_file(git_repo.path / "app.py", "x = 1\n")
        write_file(git_repo.path / "GUIDE.md", "# guide\n")
        status, code, _, _ = gates.evaluate_gate("Documentation", str(git_repo.path))
        assert status == gates.PASS and code == "DOCS_UPDATED"

    def test_a_project_without_documentation_is_unknown_not_failed(self, git_repo, write_file):
        for path in git_repo.path.glob("*.md"):
            path.unlink()
        git_repo.git("add", "-A")
        git_repo.git("commit", "-q", "-m", "drop docs")
        write_file(git_repo.path / "app.py", "x = 1\n")

        status, code, _, _ = gates.evaluate_gate("Documentation", str(git_repo.path))
        assert status == gates.UNKNOWN and code == "NO_DOCUMENTATION"


class TestCompletionReport:
    def test_the_report_states_a_final_status(self, isolated_gates, git_repo, capsys):
        isolated_gates.run_all_gates(str(git_repo.path), report_style=True,
                                     objective="Add Redis caching")
        out = capsys.readouterr().out
        assert "FINAL STATUS:" in out
        assert "Add Redis caching" in out

    def test_an_approved_run_reports_task_complete(self, isolated_gates, git_repo, capsys):
        isolated_gates.run_all_gates(str(git_repo.path), report_style=True,
                                     objective="x")
        assert "TASK COMPLETE" in capsys.readouterr().out

    def test_a_blocked_run_names_the_gate_and_its_code(self, isolated_gates, git_repo,
                                                       capsys, monkeypatch):
        def fail_security(name, target_dir=".", objective=None):
            if name == "Security":
                return gates.FAIL, "SCANNER_VIOLATIONS", "a secret was committed", "scanner"
            return gates.PASS, "REQUIREMENT_STATED", "fine", None

        monkeypatch.setattr(gates, "evaluate_gate", fail_security)
        code = isolated_gates.run_all_gates(str(git_repo.path), report_style=True)
        out = capsys.readouterr().out

        assert code == 1
        assert "TASK BLOCKED" in out
        assert "FINAL STATUS: BLOCKED" in out
        assert "SCANNER_VIOLATIONS" in out

    def test_every_gate_appears_in_the_report(self, isolated_gates, git_repo, capsys):
        isolated_gates.run_all_gates(str(git_repo.path), report_style=True)
        out = capsys.readouterr().out
        for name in gates.GATE_PIPELINE:
            assert name in out

    def test_the_json_report_carries_the_final_status(self, isolated_gates, git_repo, capsys):
        isolated_gates.run_all_gates(str(git_repo.path), emit_json=True)
        report = json.loads(capsys.readouterr().out)
        assert report["final_status"] in ("APPROVED", "BLOCKED")
        assert report["verdict"] in ("CLEAR", "BLOCKED")


class TestCliFlagRegistration:
    def test_every_value_flag_is_registered(self, core_dir):
        """Regression, F-20 and its recurrence in Phase 6.

        A flag read with flag_value() but absent from VALUE_FLAGS has its value
        treated as a positional argument. That is how `verify --claim "fixed the
        login bug"` came to verify a directory named after the claim, and how
        `gate run --objective "..."` came to gate a directory named after the
        objective.
        """
        import ast

        source = (Path(core_dir) / "coresentinel.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        read = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "flag_value" and len(node.args) >= 2):
                flag = node.args[1]
                if isinstance(flag, ast.Constant) and isinstance(flag.value, str):
                    read.add(flag.value)

        import coresentinel as cli
        missing = sorted(read - cli.VALUE_FLAGS)
        assert not missing, \
            f"flags read but not registered in VALUE_FLAGS (their values become " \
            f"positional arguments): {missing}"
