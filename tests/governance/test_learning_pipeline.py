"""Controlled evolution — the loop, and the controls on it.

    incident -> root cause -> pattern -> candidate -> evidence
             -> human approval -> versioned rule -> future agents

The load-bearing tests here are the refusals. A pipeline that can reach a rule
change without a human saying yes is not controlled evolution, whatever the
documentation calls it.
"""

import json
import shutil
from pathlib import Path

import pytest

from coresentinel_core.learning import candidates, observer, apply as applier
from coresentinel_core.patterns import ledger as patterns
from coresentinel_core.incidents import ledger as incidents
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


LESSON = "Flag repeated relationship queries inside a loop during review"


def seed_incident(project, number, learning=LESSON):
    record = incidents.create(str(project), title=f"N+1 in module {number}",
                              problem="the connection pool was exhausted",
                              root_cause="a repeated relationship query in a loop")
    incidents.resolve(record["id"], str(project), resolution="added eager loading",
                      learning=learning)
    return record


class TestCandidateEvidence:
    def test_one_incident_is_an_anecdote_not_a_lesson(self, project, store):
        seed_incident(project, 1)
        report = observer.run(store, str(project))
        assert report["candidates"][0]["status"] == candidates.OBSERVED
        assert report["ready"] == []

    def test_a_second_source_corroborates_it(self, project, store):
        seed_incident(project, 1)
        seed_incident(project, 2)
        report = observer.run(store, str(project))
        assert report["candidates"][0]["status"] == candidates.CORROBORATED
        assert len(report["ready"]) == 1

    def test_the_same_source_cannot_corroborate_itself(self, project, store):
        """A single noisy incident must not argue itself into a rule."""
        seed_incident(project, 1)
        observer.run(store, str(project))
        observer.run(store, str(project))
        candidate = observer.run(store, str(project))["candidates"][0]
        assert len(candidate["sources"]) == 1
        assert candidate["status"] == candidates.OBSERVED

    def test_observation_is_idempotent(self, project, store):
        seed_incident(project, 1)
        seed_incident(project, 2)
        first = observer.run(store, str(project))
        second = observer.run(store, str(project))
        assert first["observed"] == second["observed"]
        assert store.repository(candidates.COLLECTION).count() == 1

    def test_the_same_lesson_from_two_wordings_shares_a_candidate(self, store):
        first = candidates.observe(store, "Flag repeated queries in a loop", "INC-1")
        second = candidates.observe(store, "flag  repeated queries in a LOOP", "INC-2")
        assert first["id"] == second["id"]
        assert second["status"] == candidates.CORROBORATED

    def test_a_learning_free_incident_produces_no_candidate(self, project, store):
        record = incidents.create(str(project), title="something broke")
        incidents.resolve(record["id"], str(project), resolution="fixed it")
        assert observer.run(store, str(project))["observed"] == 0


class TestRejection:
    def test_a_rejected_candidate_does_not_resurface(self, project, store):
        seed_incident(project, 1)
        seed_incident(project, 2)
        candidate = observer.run(store, str(project))["candidates"][0]
        candidates.reject(store, candidate["id"], "already covered by AP-002")

        again = observer.run(store, str(project))
        assert again["candidates"][0]["status"] == candidates.REJECTED
        assert again["ready"] == []

    def test_rejecting_requires_a_reason(self, store):
        candidate = candidates.observe(store, "some lesson", "INC-1")
        assert "error" in candidates.reject(store, candidate["id"], "")

    def test_a_rejected_candidate_cannot_be_promoted(self, store):
        candidate = candidates.observe(store, "some lesson", "INC-1")
        candidates.reject(store, candidate["id"], "not a real pattern")
        assert "error" in candidates.promote(store, candidate["id"], "changed my mind")

    def test_new_evidence_does_not_revive_a_rejection(self, store):
        candidate = candidates.observe(store, "some lesson", "INC-1")
        candidates.reject(store, candidate["id"], "noise")
        after = candidates.observe(store, "some lesson", "INC-2")
        assert after["status"] == candidates.REJECTED


class TestPromotion:
    def test_promotion_skips_the_threshold_with_a_stated_reason(self, store):
        candidate = candidates.observe(store, "never commit a private key", "INC-1")
        report = candidates.promote(store, candidate["id"], "obvious enough not to repeat")
        assert report["candidate"]["status"] == candidates.CORROBORATED

    def test_promotion_without_a_reason_is_refused(self, store):
        candidate = candidates.observe(store, "some lesson", "INC-1")
        assert "error" in candidates.promote(store, candidate["id"], "")

    def test_the_shortcut_is_visible_in_the_record(self, store):
        candidate = candidates.observe(store, "some lesson", "INC-1")
        report = candidates.promote(store, candidate["id"], "obvious")
        assert any(e["kind"] == "promotion" for e in report["candidate"]["evidence"])


class TestApprovalIsMandatory:
    @pytest.fixture
    def proposal(self):
        return {"id": "EVO-900", "target_protocol": "anti-patterns.json",
                "proposed_change": "Flag repeated relationship queries in a loop",
                "evidence": "INC-0001, INC-0002", "review_status": "PENDING_REVIEW",
                "impact_analysis": "Low risk", "approver": None}

    def test_an_unapproved_proposal_cannot_be_applied(self, proposal):
        """The control this whole subsystem exists to be."""
        report = applier.apply(proposal)
        assert "error" in report
        assert "not APPROVED" in report["error"]

    @pytest.mark.parametrize("status", ["PENDING_REVIEW", "REJECTED", None, ""])
    def test_no_status_other_than_approved_is_accepted(self, proposal, status):
        proposal["review_status"] = status
        assert "error" in applier.apply(proposal)

    def test_nothing_is_written_when_application_is_refused(self, proposal, tmp_path,
                                                            monkeypatch):
        target = tmp_path / "anti-patterns.json"
        shutil.copy2(applier.CORE_ROOT / "anti-patterns.json", target)
        before = target.read_bytes()
        monkeypatch.setattr(applier, "CORE_ROOT", tmp_path)
        applier.apply(proposal)
        assert target.read_bytes() == before

    def test_an_already_applied_proposal_is_not_applied_twice(self, proposal):
        proposal["review_status"] = applier.APPROVED
        proposal["applied_at"] = "2026-08-14 00:00:00"
        assert "already applied" in applier.apply(proposal)["error"]


class TestApplyAndRevert:
    @pytest.fixture
    def core(self, tmp_path, monkeypatch):
        """An isolated Core so applying never touches the real governance files."""
        root = tmp_path / "core"
        root.mkdir()
        shutil.copy2(applier.CORE_ROOT / "anti-patterns.json", root / "anti-patterns.json")
        shutil.copy2(applier.CORE_ROOT / "11-pattern-library.md", root / "11-pattern-library.md")
        monkeypatch.setattr(applier, "CORE_ROOT", root)
        monkeypatch.setattr(applier, "SNAPSHOT_DIR", root / "snapshots")

        import coresentinel_core.runtime.paths as runtime_paths
        monkeypatch.setattr(runtime_paths, "CORE_ROOT", root)
        return root

    @pytest.fixture
    def approved(self):
        return {"id": "EVO-901", "target_protocol": "anti-patterns.json",
                "proposed_change": "Flag repeated relationship queries in a loop",
                "evidence": "INC-0001, INC-0002", "review_status": applier.APPROVED,
                "impact_analysis": "add a review check", "approver": "Fakrul"}

    def test_applying_adds_the_rule(self, core, approved):
        before = len(json.loads((core / "anti-patterns.json").read_text())["anti_patterns"])
        report = applier.apply(approved)
        after = json.loads((core / "anti-patterns.json").read_text())

        assert report["applied"] is True
        assert len(after["anti_patterns"]) == before + 1
        assert after["anti_patterns"][-1]["rule"] == approved["proposed_change"]

    def test_a_new_rule_warns_before_it_blocks(self, core, approved):
        """Promotion to STRICT_BLOCK is its own decision, once the rule has proved itself."""
        applier.apply(approved)
        rule = json.loads((core / "anti-patterns.json").read_text())["anti_patterns"][-1]
        assert rule["enforcement"] == "WARNING"

    def test_the_rule_records_where_it_came_from(self, core, approved):
        applier.apply(approved)
        rule = json.loads((core / "anti-patterns.json").read_text())["anti_patterns"][-1]
        assert rule["origin"]["proposal"] == "EVO-901"
        assert rule["origin"]["evidence"] == "INC-0001, INC-0002"

    def test_the_registry_version_is_bumped(self, core, approved):
        before = json.loads((core / "anti-patterns.json").read_text())["version"]
        applier.apply(approved)
        after = json.loads((core / "anti-patterns.json").read_text())["version"]
        assert after != before

    def test_a_snapshot_is_taken_before_the_change(self, core, approved):
        report = applier.apply(approved)
        assert applier.Path(report["snapshot"]).exists()

    def test_revert_restores_byte_identically(self, core, approved):
        original = (core / "anti-patterns.json").read_bytes()
        report = applier.apply(approved)
        assert (core / "anti-patterns.json").read_bytes() != original

        approved["snapshot"] = report["snapshot"]
        reverted = applier.revert(approved)
        assert reverted["identical"] is True
        assert (core / "anti-patterns.json").read_bytes() == original

    def test_revert_without_a_snapshot_is_refused(self, core, approved):
        assert "error" in applier.revert(approved)

    def test_a_pattern_is_appended_in_the_documented_format(self, core, approved):
        approved["target_protocol"] = "11-pattern-library.md"
        record = {"id": "PAT-0001", "name": "Cache-aside with an explicit TTL",
                  "stack": "Node", "problem": "repeated reads", "solution": "cache aside",
                  "occurrences": 1, "related_incidents": ["INC-0001"]}
        applier.apply(approved, change={"pattern": record})

        text = (core / "11-pattern-library.md").read_text(encoding="utf-8")
        assert "#### Cache-aside with an explicit TTL" in text
        assert "- **Stack**: Node" in text

    def test_an_unsupported_target_is_refused_not_attempted(self, core, approved):
        approved["target_protocol"] = "40-security-protocol.md"
        report = applier.apply(approved)
        assert "error" in report and "no safe way" in report["error"]
        assert report["supported"]

    @pytest.mark.parametrize("escape", ["../../etc/passwd", "/etc/passwd",
                                       "../anti-patterns.json", "/tmp/anti-patterns.json"])
    def test_a_target_outside_the_core_cannot_be_written(self, core, approved, escape):
        """Traversal is neutralised by taking the basename first.

        `../../etc/passwd` becomes `passwd`, which is not a supported target and is
        refused. `../anti-patterns.json` becomes the Core's own file, which is the
        correct resolution — the property under test is that nothing OUTSIDE the
        Core is ever written, not that every path containing `..` errors.
        """
        approved["target_protocol"] = escape
        report = applier.apply(approved)

        if "error" not in report:
            assert Path(report["target"]).parent == core, \
                f"{escape} resolved outside the Core to {report['target']}"
        assert not (core.parent / "passwd").exists()
        assert not Path("/tmp/anti-patterns.json").exists()


class TestPatternLibrary:
    def test_a_pattern_is_recorded_with_an_id(self, project):
        record = patterns.add(str(project), name="Cache-aside", problem="repeated reads",
                              solution="read through a cache")
        assert record["id"].startswith("PAT-")

    def test_recording_the_same_pattern_counts_an_occurrence(self, project):
        patterns.add(str(project), name="Cache-aside", problem="p", solution="s")
        again = patterns.add(str(project), name="Cache-aside", problem="p", solution="s")
        assert again["occurrences"] == 2

    def test_recording_again_does_not_raise_confidence(self, project):
        """Three sightings of a guess make one guess seen three times."""
        first = patterns.add(str(project), name="Cache-aside", problem="p", solution="s")
        again = patterns.add(str(project), name="Cache-aside", problem="p", solution="s")
        assert again["confidence"] == first["confidence"]

    def test_a_core_pattern_stays_out_of_a_project_unless_transferable(self, project,
                                                                      tmp_path):
        import coresentinel_memory as mem

        core_library = mem.MEMORY_DIR / "patterns_library.json"
        core_library.parent.mkdir(parents=True, exist_ok=True)
        core_library.write_text(json.dumps([
            {"id": "PAT-9001", "name": "local only", "transferable": False},
            {"id": "PAT-9002", "name": "portable", "transferable": True}]), encoding="utf-8")

        visible = [p["id"] for p in patterns.load(str(project))]
        assert "PAT-9002" in visible and "PAT-9001" not in visible

    def test_it_renders_back_into_the_documented_format(self, project):
        record = patterns.add(str(project), name="Cache-aside", stack="Node",
                              problem="repeated reads", solution="read through a cache",
                              gotchas="set an explicit TTL", related_incidents="INC-0001")
        rendered = patterns.render_markdown(record)
        for label in ("Stack", "Problem", "Solution", "Gotchas", "Learned from"):
            assert f"**{label}**" in rendered

    def test_a_corrupt_library_is_never_overwritten(self, project):
        path = patterns.ledger_path(str(project))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")
        assert patterns.add(str(project), name="x") is None
        assert path.read_text(encoding="utf-8") == "{ not json"

    def test_a_repeated_pattern_becomes_a_learning_candidate(self, project, store):
        patterns.add(str(project), name="Cache-aside", problem="p", solution="s",
                     gotchas="set an explicit TTL")
        patterns.add(str(project), name="Cache-aside", problem="p", solution="s")
        report = observer.run(store, str(project))
        assert any("TTL" in c["lesson"] for c in report["candidates"])


class TestEndToEnd:
    def test_the_full_loop_from_incident_to_applied_rule(self, project, store, tmp_path,
                                                         monkeypatch):
        """incident -> learning -> candidate -> proposal -> approval -> rule -> revert."""
        core = tmp_path / "core"
        core.mkdir()
        shutil.copy2(applier.CORE_ROOT / "anti-patterns.json", core / "anti-patterns.json")
        monkeypatch.setattr(applier, "CORE_ROOT", core)
        monkeypatch.setattr(applier, "SNAPSHOT_DIR", core / "snapshots")
        import coresentinel_core.runtime.paths as runtime_paths
        monkeypatch.setattr(runtime_paths, "CORE_ROOT", core)

        seed_incident(project, 1)
        seed_incident(project, 2)

        ready = observer.run(store, str(project))["ready"]
        assert len(ready) == 1, "two incidents teaching one lesson did not corroborate"

        proposal = {"id": "EVO-902", "target_protocol": "anti-patterns.json",
                    "proposed_change": ready[0]["lesson"],
                    "evidence": ", ".join(ready[0]["sources"]),
                    "review_status": "PENDING_REVIEW", "impact_analysis": "review check"}

        assert "error" in applier.apply(proposal), "it applied without approval"

        proposal["review_status"] = applier.APPROVED
        proposal["approver"] = "Fakrul"
        original = (core / "anti-patterns.json").read_bytes()

        report = applier.apply(proposal)
        assert report["applied"]
        rule = json.loads((core / "anti-patterns.json").read_text())["anti_patterns"][-1]
        assert rule["rule"] == LESSON
        assert "INC-0001" in rule["origin"]["evidence"]

        proposal["snapshot"] = report["snapshot"]
        assert applier.revert(proposal)["identical"]
        assert (core / "anti-patterns.json").read_bytes() == original
