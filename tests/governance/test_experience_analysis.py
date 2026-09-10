"""Experience analysis — what a recurring failure is allowed to become.

The two claims under test:

  * a failure that happened once is an event, and produces nothing;
  * a failure that keeps happening is one source, not many.

The second is the one that matters. `candidates.observe` refuses to let a single
incident corroborate itself; a flapping gate is the same problem wearing a
different hat, and if repetition counted as independence then any misconfigured
check could vote itself into the rulebook.
"""

import json

import pytest

from coresentinel_core.experience import analysis, capture, records, retention
from coresentinel_core.learning import candidates, observer
from coresentinel_core.storage import JsonStore


@pytest.fixture
def project(tmp_path, monkeypatch):
    import coresentinel_memory as mem

    root = tmp_path / "shop"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "shop"}), encoding="utf-8")

    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    return root


@pytest.fixture(params=["json", "sqlite"])
def store(project, request):
    """Both backends — see the note in test_experience_capture.py."""
    from coresentinel_core.storage.sqlite_store import SqliteStore

    built = (JsonStore(project / ".coresentinel") if request.param == "json"
             else SqliteStore(project / ".coresentinel"))
    yield built
    built.close()


GATE_FAILURE = {"objective": "add checkout", "result": "BLOCKED",
                "blocked_by": "Security", "code": "SECRET_DETECTED",
                "reason": "a hardcoded credential was found"}


def fail(store, times=1, **overrides):
    for _ in range(times):
        capture.store_experience(store, "QualityGateFailed", {**GATE_FAILURE, **overrides})


class TestWhatEarnsACandidate:
    def test_a_single_failure_is_an_event_not_a_lesson(self, store):
        fail(store, times=1)
        assert analysis.recurring_failures(store) == []
        assert analysis.observe(store) == []

    def test_a_repeated_failure_earns_one(self, store):
        fail(store, times=2)
        assert len(analysis.observe(store)) == 1

    def test_a_success_never_starts_a_lesson(self, store):
        for index in range(5):
            capture.store_experience(store, "QualityGatePassed",
                                     {"objective": "clean run", "result": "APPROVED"})
        assert analysis.observe(store) == []

    def test_the_lesson_describes_what_happened(self, store):
        """Descriptive, never prescriptive. A rule is written by whoever proposes
        it, not inferred here from a gate code."""
        fail(store, times=3)
        lesson = analysis.observe(store)[0]["lesson"]
        assert "Security" in lesson
        assert "3" in lesson
        assert "always" not in lesson.lower()
        assert "must" not in lesson.lower()


class TestRepetitionIsNotCorroboration:
    def test_fifty_failures_are_one_source(self, store):
        fail(store, times=50)
        candidate = analysis.observe(store)[0]
        assert len(candidate["sources"]) == 1
        assert candidate["status"] == candidates.OBSERVED, \
            "one signature cannot corroborate itself, however loudly it repeats"

    def test_the_same_failure_in_two_contexts_is_two_sources(self, store, monkeypatch):
        """Independent corroboration is the same lesson arriving from elsewhere."""
        monkeypatch.setattr(capture, "context_key", lambda target_dir=".": "php83.laravel12")
        fail(store, times=2)
        monkeypatch.setattr(capture, "context_key", lambda target_dir=".": None)
        fail(store, times=2)

        observed = analysis.observe(store)
        # Two contexts produce two candidates whose lessons differ by their
        # scope suffix; what matters is that neither invented a second source.
        assert all(len(c["sources"]) == 1 for c in observed)
        assert len({c["sources"][0] for c in observed}) == 2

    def test_observation_is_idempotent(self, store):
        fail(store, times=4)
        first = analysis.observe(store)[0]
        second = analysis.observe(store)[0]
        assert first["id"] == second["id"]
        assert len(second["sources"]) == 1

    def test_an_incident_corroborates_an_experience(self, store, project):
        """The loop that now closes without anybody starting it by hand: the
        system saw the failure, a human wrote down what it meant."""
        fail(store, times=2)
        lesson = analysis.observe(store)[0]["lesson"]

        corroborated = candidates.observe(store, lesson, source="INC-0001", kind="incident")
        assert corroborated["status"] == candidates.CORROBORATED
        assert len(corroborated["sources"]) == 2


class TestEvidence:
    def test_successes_and_failures_are_both_counted(self, store):
        fail(store, times=3)
        row = analysis.recurring_failures(store)[0]
        evidence = analysis.evidence_for(row, store)
        assert evidence["failure_count"] == 3
        assert evidence["success_count"] == 0

    def test_the_detail_records_the_tally(self, store):
        fail(store, times=6)
        candidate = analysis.observe(store)[0]
        assert "6" in candidate["evidence"][0]["detail"]


class TestTheObserverGainsAFourthSource:
    def test_run_collects_experiences(self, store, project):
        fail(store, times=2)
        report = observer.run(store, str(project))
        assert report["observed"] >= 1
        assert any(c["kind"] == "experience" for c in report["candidates"])

    def test_the_three_written_sources_still_work_without_experiences(self, store, project):
        """An older store has no experience collection; that must not break observe."""
        report = observer.run(store, str(project))
        assert report["observed"] == 0
        assert report["candidates"] == []

    def test_a_store_that_cannot_be_read_does_not_break_the_others(self, store, project,
                                                                   monkeypatch):
        def explode(*args, **kwargs):
            raise RuntimeError("no experience collection here")

        monkeypatch.setattr(analysis, "observe", explode)
        report = observer.run(store, str(project))
        assert report["observed"] == 0
