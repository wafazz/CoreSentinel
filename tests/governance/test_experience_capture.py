"""Experience capture — the input stage the learning loop never had.

The load-bearing tests here are the *limits*. Capture runs unattended on every
event, so the questions that matter are what it refuses to record, what it
refuses to leak, and what it refuses to grow into. A capture stage that records
everything is how a learning store becomes the context bloat CoreSentinel exists
to remove.
"""

import json

import pytest

from coresentinel_core.experience import capture, records, retention
from coresentinel_core.runtime.container import Runtime
from coresentinel_core.runtime.config import DEFAULTS, env_key
from coresentinel_core.storage import JsonStore
from coresentinel_core.storage.sqlite_store import SqliteStore


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "shop"
    (root / ".coresentinel").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "shop", "coresentinel_api": "1.0"}), encoding="utf-8")
    return root


@pytest.fixture(params=["json", "sqlite"])
def store(project, request):
    """Both backends, every test.

    Not optional. A deterministic record id passed on JSON, which has no
    uniqueness constraint, and failed on SQLite, which does — a divergence a
    single-backend suite reported as green.
    """
    built = (JsonStore(project / ".coresentinel") if request.param == "json"
             else SqliteStore(project / ".coresentinel"))
    yield built
    built.close()


@pytest.fixture
def runtime(project, tmp_path, monkeypatch):
    """A runtime with capture on, rooted entirely inside tmp_path."""
    import coresentinel_core.runtime.config as config_module
    monkeypatch.setattr(config_module, "CORE_CONFIG_FILE",
                        tmp_path / "coresentinel.config.json")
    for key in list(DEFAULTS):
        monkeypatch.delenv(env_key(key), raising=False)
    capture.reset_context_cache()
    built = Runtime.bootstrap(str(project))
    yield built
    built.shutdown()


GATE_FAILURE = {"objective": "add checkout", "result": "BLOCKED",
                "blocked_by": "Security", "code": "SECRET_DETECTED",
                "reason": "a hardcoded credential was found"}


class TestWhatBecomesAnExperience:
    def test_a_gate_failure_is_captured(self, store):
        stored = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        assert stored["kind"] == records.GATE
        assert stored["outcome"] == records.FAILURE

    def test_a_gate_pass_is_captured_too(self, store):
        stored = capture.store_experience(
            store, "QualityGatePassed", {"objective": "add checkout", "result": "APPROVED"})
        assert stored["outcome"] == records.SUCCESS

    @pytest.mark.parametrize("event", ["MemoryCreated", "AgentStarted", "TaskStarted",
                                       "DecisionCreated", "VerificationStarted",
                                       "ProjectInitialized", "RuleProposed"])
    def test_a_non_outcome_event_is_not_an_experience(self, store, event):
        """Recording that something *began* supports no lesson about how it went."""
        assert capture.store_experience(store, event, {"detail": "x"}) is None
        assert store.repository(retention.COLLECTION).count() == 0

    def test_the_verdict_decides_the_outcome_when_the_name_does_not(self, store):
        failed = capture.store_experience(
            store, "VerificationCompleted", {"claim": "orders ship", "result": "REFUTED"})
        passed = capture.store_experience(
            store, "VerificationCompleted", {"claim": "orders ship twice", "result": "VERIFIED"})
        assert failed["outcome"] == records.FAILURE
        assert passed["outcome"] == records.SUCCESS

    def test_an_unreadable_outcome_is_mixed_not_success(self, store):
        """An outcome we could not read is not a success. Calling it one teaches
        the wrong lesson from a real event."""
        stored = capture.store_experience(store, "TaskCompleted", {"objective": "ship"})
        assert stored["outcome"] == records.MIXED


class TestRecurrence:
    def test_the_same_failure_twice_shares_one_group(self, store):
        first = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        second = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        assert first["group_id"] == second["group_id"]

    def test_two_sightings_are_two_rows_with_distinct_ids(self, store):
        """Grouping belongs to the record, identity to the row. Conflating them
        made a recurring failure a UNIQUE-constraint error on SQLite."""
        first = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        second = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        assert first["id"] != second["id"]

    def test_recurrence_is_counted_not_duplicated(self, store):
        for _ in range(3):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        folded = retention.group(store)
        assert len(folded) == 1
        assert folded[0]["occurrences"] == 3

    def test_run_to_run_noise_does_not_split_a_signature(self, store):
        """Two runs of one failure differ by timestamps, paths and counts. If
        those reached the signature, nothing would ever be seen twice."""
        a = capture.store_experience(store, "QualityGateFailed", {
            **GATE_FAILURE, "reason": "found at C:\\src\\app\\Http\\a.php line 42 at 2026-09-01 10:00:00"})
        b = capture.store_experience(store, "QualityGateFailed", {
            **GATE_FAILURE, "reason": "found at C:\\src\\app\\Http\\b.php line 91 at 2026-09-08 17:31:04"})
        assert a["signature"] == b["signature"]

    def test_two_different_gates_do_not_collapse(self, store):
        a = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        b = capture.store_experience(store, "QualityGateFailed", {
            **GATE_FAILURE, "blocked_by": "Testing", "code": "TESTS_FAILED"})
        assert a["signature"] != b["signature"]

    def test_a_task_and_a_gate_sharing_wording_stay_apart(self, store):
        """`kind` is hashed in, so unrelated events cannot corroborate each other."""
        gate = records.signature(records.GATE, "add checkout")
        task = records.signature(records.TASK, "add checkout")
        assert gate != task


class TestNoSecretIsStored:
    def test_a_credential_in_a_payload_field_never_lands(self, store):
        capture.store_experience(store, "QualityGateFailed", {
            **GATE_FAILURE, "api_key": "sk-live-4eC39HqLyjWDarjtT1zdp7dc"})
        written = json.dumps(store.repository(retention.COLLECTION).all())
        assert "4eC39HqLyjWDarjtT1zdp7dc" not in written

    def test_a_credential_in_free_text_never_lands(self, store):
        capture.store_experience(store, "QualityGateFailed", {
            **GATE_FAILURE,
            "reason": "committed ghp_16C7e42F292c6912E7710c838347Ae178B4a instead of a env var"})
        written = json.dumps(store.repository(retention.COLLECTION).all())
        assert "ghp_16C7e42F292c6912E7710c838347Ae178B4a" not in written
        assert "[redacted]" in written

    def test_the_context_survives_redaction(self, store, monkeypatch):
        """A field named `context_key` reaches the store as "[redacted]".

        `redaction.SENSITIVE_KEY_WORDS` matches a trailing `_key` as a
        credential name, which is the over-redaction its own comment warns
        about: destroying real data to protect nothing. The field is called
        `context` for exactly this reason, and this pins it — a rename back
        would silently blank every scoped lesson.
        """
        monkeypatch.setattr(capture, "context_key", lambda target_dir=".": "php83.laravel12")
        stored = capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        assert stored["context"] == "php83.laravel12"

    def test_redaction_covers_the_statement_not_only_the_evidence(self, store):
        """A gate reason reaches `statement`, so redacting the payload alone
        would write the secret back out under a different key."""
        capture.store_experience(store, "IncidentCreated", {
            "title": "leaked AKIAIOSFODNN7EXAMPLE in the build log"})
        written = json.dumps(store.repository(retention.COLLECTION).all())
        assert "AKIAIOSFODNN7EXAMPLE" not in written


class TestBounded:
    def test_folding_collapses_duplicates(self, store):
        for _ in range(10):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        report = retention.fold(store, maximum=100, apply_changes=True)
        assert report["rows_before"] == 10
        assert report["rows_after"] == 1
        assert store.repository(retention.COLLECTION).count() == 1

    def test_a_dry_run_writes_nothing(self, store):
        for _ in range(6):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        report = retention.fold(store, maximum=100)
        assert report["applied"] is False
        assert store.repository(retention.COLLECTION).count() == 6

    def test_the_cap_is_enforced(self, store):
        for index in range(12):
            capture.store_experience(store, "TaskCompleted",
                                     {"objective": f"objective {index} alpha bravo", "result": "OK"})
        retention.enforce(store, maximum=5)
        assert store.repository(retention.COLLECTION).count() <= 5

    def test_enforce_does_nothing_below_the_cap(self, store):
        capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        assert retention.enforce(store, maximum=50) is None

    def test_a_failure_outlives_a_success_when_trimming(self, store):
        capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        for index in range(8):
            capture.store_experience(store, "QualityGatePassed",
                                     {"objective": f"clean run {index} delta echo",
                                      "result": "APPROVED"})
        retention.enforce(store, maximum=3)
        kept = retention.group(store)
        assert any(row["outcome"] == records.FAILURE for row in kept), \
            "a failure teaches more than a success and must survive the trim"


class TestOutcomesBySignature:
    def test_success_and_failure_are_tallied_per_context(self, store):
        capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        signature = retention.group(store)[0]["signature"]
        tally = retention.outcomes_for(signature, store)
        assert sum(bucket["failure"] for bucket in tally.values()) == 2


class TestItNeverBreaksWhatItObserves:
    def test_a_raising_handler_does_not_fail_the_operation(self, runtime, monkeypatch):
        """Capture is a listener. The day it throws must not be the day gates stop."""
        def explode(*args, **kwargs):
            raise RuntimeError("store is on fire")

        monkeypatch.setattr(capture, "store_experience", explode)
        event = runtime.events.emit("QualityGateFailed", GATE_FAILURE)
        assert event.name == "QualityGateFailed"

    def test_capture_is_installed_on_a_bootstrapped_runtime(self, runtime):
        runtime.events.emit("QualityGateFailed", GATE_FAILURE)
        assert runtime.store.repository(retention.COLLECTION).count() >= 1

    def test_capture_can_be_switched_off(self, project, tmp_path, monkeypatch):
        import coresentinel_core.runtime.config as config_module
        monkeypatch.setattr(config_module, "CORE_CONFIG_FILE",
                            tmp_path / "coresentinel.config.json")
        for key in list(DEFAULTS):
            monkeypatch.delenv(env_key(key), raising=False)
        monkeypatch.setenv(env_key("learning.capture"), "false")

        built = Runtime.bootstrap(str(project))
        try:
            built.events.emit("QualityGateFailed", GATE_FAILURE)
            assert built.store.repository(retention.COLLECTION).count() == 0
        finally:
            built.shutdown()


class TestContextScoping:
    def test_an_uninspectable_directory_is_global_not_guessed(self, tmp_path):
        """Guessing a context is worse than admitting to none — a wrongly scoped
        lesson gets retrieved where it does not apply."""
        capture.reset_context_cache()
        assert capture.context_key(str(tmp_path / "does-not-exist")) is None

    def test_the_key_is_cached_per_directory(self, tmp_path, monkeypatch):
        capture.reset_context_cache()
        calls = []

        from coresentinel_core.project.discovery import stack

        def counted(root="."):
            calls.append(root)
            return []

        monkeypatch.setattr(stack, "detect_frameworks", counted)
        capture.context_key(str(tmp_path))
        capture.context_key(str(tmp_path))
        assert len(calls) == 1, "detection reads manifests; capture must not repeat it per event"

    def test_a_declared_stack_becomes_the_key(self, tmp_path):
        capture.reset_context_cache()
        project = tmp_path / "laravel-app"
        project.mkdir()
        (project / "composer.json").write_text(json.dumps(
            {"require": {"php": "^8.3", "laravel/framework": "^12.0"}}), encoding="utf-8")
        key = capture.context_key(str(project))
        assert key and "php" in key and "laravel" in key

    def test_detection_never_walks_the_tree(self, tmp_path, monkeypatch):
        """A listener that scans the project on every event is a tax, not a listener."""
        from coresentinel_core.project.discovery import base

        def forbidden(*args, **kwargs):
            raise AssertionError("capture must not scan the file tree")

        monkeypatch.setattr(base, "scan_files", forbidden)
        capture.reset_context_cache()
        capture.context_key(str(tmp_path))
