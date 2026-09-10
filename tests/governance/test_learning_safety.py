"""The boundary automatic learning must never cross.

CoreSentinel may now learn from experience without being asked. That is only
safe because of one property, and this file is where the property is checked
rather than asserted:

    The automatic path terminates at TRUSTED, which is a retrieval tier. It
    compels nothing — it cannot block a gate, fail a build, or write a file.
    Reaching a governance rule still requires propose -> approve -> apply, and
    no amount of evidence shortens that path.

If any test in this file fails, the correct response is to disable capture, not
to adjust the test. Everything else in the subsystem is a convenience; this is
the reason it is allowed to run at all.
"""

import json
from pathlib import Path

import pytest

from coresentinel_core.experience import capture, retention
from coresentinel_core.learning import apply as applier
from coresentinel_core.learning import candidates, confidence, contradiction, skills
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


@pytest.fixture
def store(project):
    return JsonStore(project / ".coresentinel")


GATE_FAILURE = {"objective": "add checkout", "result": "BLOCKED",
                "blocked_by": "Security", "code": "SECRET_DETECTED"}


def seed_trusted(store, lesson="eager-load relationships queried in a loop",
                 sources=("s1", "s2", "s3"), context="php83.laravel12"):
    for index, source in enumerate(sources):
        candidates.observe(store, lesson, source=source, kind="experience",
                           context=context,
                           metrics={"signature": "SIG-a",
                                    "by_context": {context: {"success": 20, "failure": 0}},
                                    "success_count": 20 if index == 0 else 0,
                                    "failure_count": 0,
                                    "occurrences": 20 if index == 0 else 0,
                                    "contexts": [context]})
    contradiction.validate(store)
    return candidates.get(store, candidates.fingerprint(lesson))


class TestTheAllowlistIsUnchanged:
    def test_apply_still_knows_exactly_three_targets(self):
        """Widening this while adding autonomy is the change the whole
        controlled-evolution protocol exists to prevent."""
        assert set(applier.SUPPORTED) == {
            "anti-patterns.json", "11-pattern-library.md", "55-self-evolution.md"}

    def test_an_unsupported_target_is_still_refused(self):
        report = applier.apply({"id": "EVO-999", "review_status": applier.APPROVED,
                                "target_protocol": "02-team-protocol.md"})
        assert "no safe way to change" in report["error"]

    def test_approval_is_still_mandatory(self):
        for status in ("PENDING_REVIEW", "REJECTED", "TRUSTED", None):
            report = applier.apply({"id": "EVO-999", "review_status": status,
                                    "target_protocol": "anti-patterns.json"})
            assert "error" in report


class TestTrustedIsNotAnApprovalRoute:
    def test_a_trusted_candidate_is_not_a_proposal(self, store):
        record = seed_trusted(store)
        assert record["status"] == candidates.TRUSTED
        assert record["proposal"] is None

    def test_no_confidence_reaches_proposed(self, store):
        seed_trusted(store, sources=("s1", "s2", "s3", "s4", "s5", "s6"))
        contradiction.validate(store)
        statuses = {c["status"] for c in candidates.scored(store)}
        assert candidates.PROPOSED not in statuses

    def test_a_trusted_candidate_cannot_be_applied(self, store):
        """A candidate is not a proposal, whatever it scores."""
        record = seed_trusted(store)
        report = applier.apply({**record, "target_protocol": "anti-patterns.json"})
        assert "error" in report
        assert applier.APPROVED in report["error"]

    def test_validate_writes_no_governance_file(self, store, core_dir):
        before = {name: (core_dir / name).read_bytes()
                  for name in applier.SUPPORTED if (core_dir / name).is_file()}
        seed_trusted(store)
        contradiction.validate(store, apply_changes=True)
        after = {name: (core_dir / name).read_bytes()
                 for name in applier.SUPPORTED if (core_dir / name).is_file()}
        assert after == before


class TestCaptureCannotReachGovernance:
    def test_capture_writes_only_to_its_own_collection(self, store, core_dir):
        before = {name: (core_dir / name).read_bytes()
                  for name in applier.SUPPORTED if (core_dir / name).is_file()}
        for _ in range(20):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        after = {name: (core_dir / name).read_bytes()
                 for name in applier.SUPPORTED if (core_dir / name).is_file()}
        assert after == before

    def test_retention_writes_only_to_its_own_collection(self, store, core_dir):
        for _ in range(20):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        before = {name: (core_dir / name).read_bytes()
                  for name in applier.SUPPORTED if (core_dir / name).is_file()}
        retention.fold(store, maximum=1, apply_changes=True)
        after = {name: (core_dir / name).read_bytes()
                 for name in applier.SUPPORTED if (core_dir / name).is_file()}
        assert after == before

    def test_a_capture_failure_never_fails_the_operation(self, store, monkeypatch):
        """The day capture throws must not be the day gates stop."""
        from coresentinel_core.runtime.events import EventBus

        def explode(event):
            raise RuntimeError("the learning store is on fire")

        bus = EventBus()
        bus.subscribe("*", explode)
        event = bus.emit("QualityGateFailed", GATE_FAILURE)
        assert event.name == "QualityGateFailed"


class TestConfidenceCannotBeAsserted:
    def test_confidence_is_computed_not_stored(self, store):
        """A record claiming a confidence it did not earn must not keep it."""
        candidates.observe(store, "a thin lesson", source="s1")
        raw = candidates.get(store, candidates.fingerprint("a thin lesson"))
        candidates._replace(store, {**raw, "confidence": 0.99})

        enriched = candidates.scored(store)[0]
        assert enriched["confidence"] < 0.99

    def test_a_forged_confidence_does_not_grant_trust(self, store):
        candidates.observe(store, "a thin lesson", source="s1")
        raw = candidates.get(store, candidates.fingerprint("a thin lesson"))
        candidates._replace(store, {**raw, "confidence": 1.0, "trustworthy": True})

        report = contradiction.validate(store)
        assert not report["promoted"]

    def test_trust_needs_sources_not_just_a_score(self):
        perfect = confidence.score(distinct_sources=1, successes=999, failures=0)
        assert confidence.qualifies_for_trust(perfect, 1) is False


class TestSkillDraftsAreNotInstalled:
    def test_the_host_skills_directory_is_never_written(self, store, tmp_path, monkeypatch):
        fake_home = tmp_path / "home"
        (fake_home / ".claude" / "skills").mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

        for index in range(4):
            seed_trusted(store, lesson=f"deployment step {index} restarts the worker",
                         sources=(f"a{index}", f"b{index}", f"c{index}"))
        skills.draft(store, tmp_path / "drafts", apply_changes=True)
        assert list((fake_home / ".claude" / "skills").iterdir()) == []


class TestNoSecretSurvivesTheLearningPath:
    def test_a_credential_does_not_reach_a_candidate(self, store):
        from coresentinel_core.experience import analysis

        secret = "ghp_16C7e42F292c6912E7710c838347Ae178B4a"
        for _ in range(3):
            capture.store_experience(store, "QualityGateFailed", {
                **GATE_FAILURE, "reason": f"committed {secret} to the repo"})
        analysis.observe(store)

        written = json.dumps(candidates.scored(store), default=str)
        assert secret not in written

    def test_a_credential_does_not_reach_a_skill_draft(self, store, tmp_path):
        secret = "AKIAIOSFODNN7EXAMPLE"
        for index in range(4):
            seed_trusted(store,
                         lesson=f"deployment step {index} leaked {secret} in the log",
                         sources=(f"a{index}", f"b{index}", f"c{index}"))
        report = skills.draft(store, tmp_path / "drafts", apply_changes=True)
        for entry in report["drafted"]:
            assert secret not in Path(entry["path"]).read_text(encoding="utf-8")
