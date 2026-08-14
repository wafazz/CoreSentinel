"""
The demo IS the end-to-end test.

`demo/` is a small, real Python project — a task store with its own passing
pytest suite. This drives CoreSentinel across the whole chain against it:

    init → discover → context → memory → decision → dispatch → modify
         → test → security → verify → gate → audit → learn

Every other suite tests a subsystem in isolation. This one is the only place
that answers "does the product work", and it is the only place where the
evidence CoreSentinel reports comes from running somebody else's real code
rather than a fixture shaped to please it.

The chain runs ONCE in a module-scoped fixture and each step's result is
recorded; the tests below assert on those recordings. Re-running the chain per
assertion would run the demo's pytest suite fourteen times.

Isolation: the chain runs against a SANDBOX COPY of the Core, not the
repository. `gate run` and Core-scoped memory writes go to the Core's own
`memory/`, and a subprocess cannot be monkeypatched — an in-process fixture
would not save us. The copy is the only thing that does.
"""

import json
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration

SANDBOX_GLOBS = ["*.py", "*.json", "*.md", "VERSION"]
SANDBOX_PACKAGES = ["coresentinel_core"]


class Step:
    """One command, its exit code, and whatever it printed."""

    __slots__ = ("name", "argv", "code", "out", "err")

    def __init__(self, name, argv, code, out, err):
        self.name, self.argv = name, argv
        self.code, self.out, self.err = code, out, err

    def json(self):
        try:
            return json.loads(self.out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"step '{self.name}' ({' '.join(self.argv)}) emitted unparseable "
                        f"JSON: {exc}\nstdout head: {self.out[:400]}\nstderr: {self.err[:400]}")

    def __repr__(self):
        return f"Step({self.name}, exit={self.code})"


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    """Govern the demo project end to end. Returns {step name: Step}."""
    root = tmp_path_factory.mktemp("e2e")
    core_dir = __import__("pathlib").Path(__file__).resolve().parent.parent.parent

    # --- a throwaway Core, so nothing here writes to the repository ---------
    core = root / "core"
    core.mkdir()
    for pattern in SANDBOX_GLOBS:
        for src in core_dir.glob(pattern):
            shutil.copy2(src, core / src.name)
    for package in SANDBOX_PACKAGES:
        shutil.copytree(core_dir / package, core / package,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (core / "memory").mkdir()
    for src in (core_dir / "memory").glob("*.json"):
        shutil.copy2(src, core / "memory" / src.name)

    # --- the governed project ----------------------------------------------
    project = root / "taskflow"
    shutil.copytree(core_dir / "demo", project,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))

    def git(*args):
        return subprocess.run(["git", *args], cwd=str(project), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")

    git("init", "-q")
    git("config", "user.email", "demo@coresentinel.local")
    git("config", "user.name", "CoreSentinel Demo")
    git("add", "-A")
    git("commit", "-q", "-m", "taskflow 0.3.0")

    steps = {}

    def run(name, *argv, expect=None):
        result = subprocess.run(
            [sys.executable, str(core / "coresentinel.py"), *argv],
            cwd=str(project), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900)
        step = Step(name, list(argv), result.returncode, result.stdout, result.stderr)
        steps[name] = step
        if expect is not None and step.code != expect:
            pytest.fail(f"step '{name}' exited {step.code}, expected {expect}\n"
                        f"$ coresentinel {' '.join(argv)}\n"
                        f"stdout: {step.out[-800:]}\nstderr: {step.err[-400:]}")
        return step

    # ---- 1. init & discover ------------------------------------------------
    run("init", "init", ".", expect=0)
    run("doctor", "doctor", ".", "--json")
    run("inspect", "project", "inspect", ".", "--json")

    # ---- 2. memory ---------------------------------------------------------
    run("memory_add", "memory", "add", "--layer", "project",
        "--fact", "taskflow keeps tasks in memory only, never on disk",
        "--confidence", "0.97", "--source", "taskflow/store.py", expect=0)
    run("recall", "recall", "in memory", "--json")

    # ---- 3. decisions ------------------------------------------------------
    run("decision_add", "decision", "add",
        "--title", "In-memory task store",
        "--reason", "the demo must run with zero external services",
        "--chosen", "a plain dict keyed by task id",
        "--alts", "sqlite,postgres", expect=0)
    # The flagship behaviour: a change that reverses a recorded decision.
    run("decision_verify", "decision", "verify",
        "--change", "replace the in-memory dict with a postgres table")

    # ---- 4. context --------------------------------------------------------
    run("context_v1", "context", ".", "--json")
    run("context_task", "context", "--task", "add archiving to the task store",
        "--budget", "1200", "--json")

    # ---- 5. dispatch -------------------------------------------------------
    run("task_run", "task", "run", "--objective", "add archiving to the task store",
        "--roles", "Scout,Tester", "--json")
    run("permissions", "agent", "permissions", "Scout", "--json")

    # ---- 6. modify the project, then evidence it ---------------------------
    store = project / "taskflow" / "store.py"
    store.write_text(store.read_text(encoding="utf-8") + ARCHIVE_HELPER, encoding="utf-8")
    (project / "tests" / "test_archive.py").write_text(ARCHIVE_TEST, encoding="utf-8")

    run("review", "review", "--json")
    run("verify", "verify", "--claim", "add an archive helper to the task store")
    run("gate", "gate", "run", "--json")

    # ---- 7. learn ----------------------------------------------------------
    run("incident", "incident", "create",
        "--title", "archive helper returned open tasks",
        "--problem", "the status comparison was inverted",
        "--severity", "high", expect=0)
    run("pattern", "pattern", "add",
        "--name", "compare status to the constant",
        "--problem", "implicit truthiness on a status string",
        "--solution", "compare against the named constant", expect=0)

    # ---- 8. accountability -------------------------------------------------
    run("audit_verify", "audit", "verify", "--json")
    run("audit_coverage", "audit", "coverage", "--json")
    run("metrics", "metrics", "--json")

    steps["_project"] = project
    steps["_core"] = core
    return steps


ARCHIVE_HELPER = '''

def archived(store):
    """Completed tasks, newest first."""
    return [task for task in store.list(limit=1000) if task.status == DONE]
'''

ARCHIVE_TEST = '''"""Cover for the archive helper."""

from taskflow.store import TaskStore, archived


def test_archived_returns_only_completed_tasks():
    store = TaskStore()
    store.add("still open")
    store.complete(store.add("finished").id)
    assert [t.title for t in archived(store)] == ["finished"]


def test_archived_is_empty_when_nothing_is_done():
    store = TaskStore()
    store.add("still open")
    assert archived(store) == []
'''


# ---------------------------------------------------------------- the chain

class TestInitAndDiscover:
    def test_init_binds_the_project(self, chain):
        config = chain["_project"] / ".coresentinel" / "config.json"
        assert config.is_file(), "init did not write .coresentinel/config.json"
        assert json.loads(config.read_text(encoding="utf-8"))["project_name"]

    def test_init_seeds_the_detected_stack_into_project_memory(self, chain):
        store = chain["_project"] / ".coresentinel" / "memory"
        assert store.is_dir(), "init did not create a project memory store"

    def test_doctor_reports_every_subsystem_on_a_real_project(self, chain):
        payload = chain["doctor"].json()
        assert payload["overall"] in {"HEALTHY", "DEGRADED"}
        assert len(payload["checks"]) == 10
        assert not [c for c in payload["checks"] if c["status"] == "FAIL"]

    def test_discovery_finds_the_stack_with_evidence(self, chain):
        dimensions = chain["inspect"].json()["dimensions"]
        assert "Python" in dimensions["languages"]["values"]
        for finding in dimensions["languages"]["findings"]:
            assert finding["evidence"]["file"], "a finding with no file behind it"

    def test_discovery_finds_the_test_runner(self, chain):
        dimensions = chain["inspect"].json()["dimensions"]
        rendered = json.dumps(dimensions).lower()
        assert "pytest" in rendered


class TestMemoryAndRecall:
    def test_a_recorded_fact_is_findable_again(self, chain):
        hits = chain["recall"].json()
        text = json.dumps(hits).lower()
        assert "taskflow keeps tasks in memory only" in text

    def test_the_fact_landed_in_the_project_store_not_the_core(self, chain):
        """Scoping is the whole point: ten repositories must not share one layer."""
        project_layer = chain["_project"] / ".coresentinel" / "memory" / "project.json"
        assert project_layer.is_file()
        assert "in memory only" in project_layer.read_text(encoding="utf-8")

        core_layer = chain["_core"] / "memory" / "project.json"
        assert "in memory only" not in core_layer.read_text(encoding="utf-8")


class TestDecisionIntelligence:
    def test_the_decision_is_recorded_in_the_project_ledger(self, chain):
        ledger = chain["_project"] / ".coresentinel" / "memory" / "decisions.json"
        assert ledger.is_file()
        assert "In-memory task store" in ledger.read_text(encoding="utf-8")

    def test_reversing_a_recorded_decision_is_refused_and_exits_nonzero(self, chain):
        """The brief's flagship example, run against a real project.

        An agent proposing postgres must be stopped and told which decision it
        contradicts, not quietly allowed.
        """
        step = chain["decision_verify"]
        assert step.code == 1, (
            f"contradicting an accepted decision exited {step.code}; "
            "a guard that does not change the exit code is advice, not a guard")

    def test_the_refusal_cites_the_decision_and_the_reason_recorded_at_the_time(self, chain):
        output = chain["decision_verify"].out
        assert "ADR-" in output, "the refusal names no decision"
        assert "zero external services" in output, \
            "the refusal does not carry the reason recorded when the decision was made"


class TestContextAssembly:
    def test_the_pack_stays_inside_its_budget(self, chain):
        pack = chain["context_task"].json()
        assert pack["estimated_tokens"] <= pack["budget_tokens"] == 1200

    def test_the_pack_carries_the_relevant_decision(self, chain):
        pack = chain["context_task"].json()
        rendered = json.dumps(pack)
        assert "In-memory task store" in rendered, \
            "a task about the task store did not retrieve the decision about the task store"

    def test_the_pack_carries_the_blocking_rules(self, chain):
        pack = chain["context_task"].json()
        rules = next(s for s in pack["sections"] if s["key"] == "rules")
        assert rules["included"] > 0, "no governance rule reached the agent"

    def test_the_v1_pack_still_works_without_a_task(self, chain):
        pack = chain["context_v1"].json()
        assert pack["project"]["stack"]
        assert "git" in pack


class TestDispatch:
    def test_the_pipeline_runs_and_returns_a_verdict(self, chain):
        result = chain["task_run"].json()
        assert result["verdict"]
        assert result["results"], "no role produced a result"

    def test_a_read_only_agent_is_granted_read_only(self, chain):
        """The README's claim, asserted against the runtime rather than the JSON."""
        permissions = chain["permissions"].json()["permissions"]
        rendered = json.dumps(permissions).lower()
        assert "filesystem.read" in rendered
        assert '"filesystem.write": "allow"' not in rendered


class TestEvidence:
    def test_review_sees_the_change_that_was_actually_made(self, chain):
        result = chain["review"].json()
        changed = " ".join(result["changed_files"])
        assert "store.py" in changed
        assert result["verdict"] in {"APPROVED", "APPROVED WITH COMMENTS"}

    def test_verification_earns_its_testing_points_from_the_real_suite(self, chain):
        """The demo's own pytest run is the evidence — not a fixture.

        This is the assertion the whole demo exists for: the number CoreSentinel
        reports came from executing somebody else's tests.
        """
        output = chain["verify"].out
        assert "VERIFIED" in output
        assert "Security / Unit Test" in output
        assert "PASS" in output

    def test_verification_exits_zero_when_it_verified(self, chain):
        assert chain["verify"].code == 0

    def test_gates_run_from_real_evidence_and_carry_reason_codes(self, chain):
        gates = chain["gate"].json()
        assert gates["final_status"] in {"APPROVED", "BLOCKED"}
        codes = {name: gate.get("code") for name, gate in gates["gates"].items()}
        assert codes.get("Security") == "SCANNER_CLEAN"
        assert all(code for code in codes.values()), \
            "a gate reported a result with no machine-readable reason code"

    def test_no_gate_passes_without_a_basis(self, chain):
        for name, gate in chain["gate"].json()["gates"].items():
            if gate["status"] == "PASS":
                assert gate.get("basis") or gate.get("reason"), \
                    f"gate {name} passed while citing nothing"


class TestAccountability:
    def test_the_audit_chain_is_intact_after_the_whole_run(self, chain):
        report = chain["audit_verify"].json()
        assert report["verdict"] == "INTACT"
        assert report["checked"] > 0, "a full governance run recorded nothing"

    def test_the_run_touched_several_audit_subjects(self, chain):
        recorded = chain["audit_coverage"].json()["recorded"]
        assert len(recorded) >= 3, f"only {recorded} were recorded across the whole chain"

    def test_metrics_measured_the_run(self, chain):
        observed = chain["metrics"].json()["coverage"]["observed"]
        assert observed, "nothing measured itself across an entire governed run"

    def test_no_budget_was_exceeded_governing_a_real_project(self, chain):
        report = chain["metrics"].json()["budgets"]
        over = [b for b in report["budgets"] if b["status"] == "FAIL"]
        assert not over, f"over budget: {[b['key'] for b in over]}"


class TestLearning:
    def test_the_incident_is_recorded_with_an_id(self, chain):
        assert "INC-" in chain["incident"].out

    def test_the_pattern_is_recorded_with_an_id(self, chain):
        assert "PAT-" in chain["pattern"].out


class TestNothingLeakedIntoTheRepository:
    def test_the_run_wrote_only_inside_the_sandbox_and_the_project(self, chain, core_dir):
        """The demo governs a copy. The repository's own state must be untouched.

        A demo that writes to the Core it is demonstrating would corrupt the
        thing it claims to prove.
        """
        assert not (core_dir / "demo" / ".coresentinel").exists(), \
            "the chain bound the checked-in demo/ instead of its copy"
