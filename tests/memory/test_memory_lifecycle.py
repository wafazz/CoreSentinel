"""Memory lifecycle — what happens to a fact after it is recorded.

A store that only grows is a store that eventually lies. These tests hold the line on the
four guarantees the lifecycle engine makes: decay is idempotent, promotion never leaks a
project fact into the shared Core, consolidation never invents confidence, and every
destructive operation is reversible.
"""

import json
from datetime import datetime, timedelta

import pytest

import coresentinel_memory as mem
import coresentinel_lifecycle as lifecycle


@pytest.fixture
def bound_project(tmp_path):
    project = tmp_path / "bound"
    (project / mem.CONFIG_DIRNAME).mkdir(parents=True)
    (project / mem.CONFIG_DIRNAME / "config.json").write_text(
        json.dumps({"project_name": "bound"}), encoding="utf-8")
    return project


@pytest.fixture
def age_fact():
    """Backdate a fact's last verification so age-driven rules engage."""
    def _age(layer, target_dir, days, index=0):
        path = mem.layer_path(layer, str(target_dir))
        data = json.loads(path.read_text(encoding="utf-8"))
        stamp = datetime.now() - timedelta(days=days)
        data["facts"][index]["last_verified"] = stamp.strftime(mem.TIMESTAMP_FORMAT)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data["facts"][index]
    return _age


def facts_in(layer, target_dir):
    return [f["fact"] for f in mem.layer_facts(layer, str(target_dir))]


class TestDecay:
    def test_a_fresh_fact_does_not_decay(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        assert lifecycle.decay(str(bound_project))["changes"] == []

    def test_an_aged_fact_loses_confidence(self, isolated_memory, bound_project, age_fact):
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        age_fact("project", bound_project, 60)

        change = lifecycle.decay(str(bound_project))["changes"][0]
        assert change["to"] == pytest.approx(0.85)

    def test_dry_run_writes_nothing(self, isolated_memory, bound_project, age_fact):
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        age_fact("project", bound_project, 60)

        lifecycle.decay(str(bound_project), apply_changes=False)
        assert mem.layer_facts("project", str(bound_project))[0]["confidence"] == 0.95

    def test_decay_is_idempotent(self, isolated_memory, bound_project, age_fact):
        """Running decay twice in one day must cost a fact one day of trust, not two."""
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        age_fact("project", bound_project, 60)

        lifecycle.decay(str(bound_project), apply_changes=True)
        first = mem.layer_facts("project", str(bound_project))[0]["confidence"]
        lifecycle.decay(str(bound_project), apply_changes=True)
        assert mem.layer_facts("project", str(bound_project))[0]["confidence"] == first

    def test_confidence_never_falls_below_the_floor(self, isolated_memory, bound_project, age_fact):
        isolated_memory.add_fact("project", "Ancient assumption", 0.60, "guess",
                                 str(bound_project))
        age_fact("project", bound_project, 5000)

        lifecycle.decay(str(bound_project), apply_changes=True)
        assert mem.layer_facts("project", str(bound_project))[0]["confidence"] == lifecycle.DECAY_FLOOR

    def test_classification_follows_the_new_confidence(self, isolated_memory, bound_project, age_fact):
        isolated_memory.add_fact("project", "Uses Redis", 0.92, "docker-compose.yml",
                                 str(bound_project))
        age_fact("project", bound_project, 365)

        lifecycle.decay(str(bound_project), apply_changes=True)
        assert "Unknown" in mem.layer_facts("project", str(bound_project))[0]["classification"]

    def test_pinned_facts_are_exempt(self, isolated_memory, bound_project, age_fact):
        isolated_memory.add_fact("project", "Owned by platform", 0.95, "CODEOWNERS",
                                 str(bound_project), pinned=True)
        age_fact("project", bound_project, 900)

        assert lifecycle.decay(str(bound_project))["changes"] == []

    def test_failures_never_decay(self, isolated_memory, bound_project, age_fact):
        """A bug that happened does not become less true with age."""
        isolated_memory.add_fact("failures", "Worker deadlocked on refresh", 0.99, "INC-004",
                                 str(bound_project))
        age_fact("failures", bound_project, 900)

        assert lifecycle.decay(str(bound_project))["changes"] == []


class TestReverification:
    def test_restores_confidence_and_restarts_the_clock(self, isolated_memory, bound_project,
                                                        age_fact):
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        age_fact("project", bound_project, 400)
        lifecycle.decay(str(bound_project), apply_changes=True)

        lifecycle.reverify("node 18", str(bound_project))
        fact = mem.layer_facts("project", str(bound_project))[0]
        assert fact["confidence"] == 0.95
        assert "base_confidence" not in fact
        assert lifecycle.decay(str(bound_project))["changes"] == []

    def test_can_raise_confidence_explicitly(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Rate limit is 100 rpm", 0.40, "guess",
                                 str(bound_project))
        lifecycle.reverify("rate limit", str(bound_project), confidence=0.99)
        assert mem.layer_facts("project", str(bound_project))[0]["confidence"] == 0.99

    def test_refuses_an_empty_match(self, isolated_memory, bound_project):
        """Re-verifying everything at once would launder every guess into a fact."""
        assert "error" in lifecycle.reverify("", str(bound_project))

    def test_reports_nothing_when_no_fact_matches(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        assert lifecycle.reverify("kafka", str(bound_project))["updated"] == []


class TestPromotion:
    def test_a_confident_session_fact_reaches_project(self, isolated_memory, bound_project):
        isolated_memory.add_fact("session", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))
        lifecycle.promote(str(bound_project), apply_changes=True)

        assert facts_in("project", bound_project) == ["Auth uses JWT"]
        assert facts_in("session", bound_project) == []

    def test_an_unproven_session_fact_stays_put(self, isolated_memory, bound_project):
        isolated_memory.add_fact("session", "Probably uses Redis", 0.60, "hunch",
                                 str(bound_project))
        lifecycle.promote(str(bound_project), apply_changes=True)

        assert facts_in("session", bound_project) == ["Probably uses Redis"]
        assert facts_in("project", bound_project) == []

    def test_promotion_records_its_provenance(self, isolated_memory, bound_project):
        isolated_memory.add_fact("session", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))
        lifecycle.promote(str(bound_project), apply_changes=True)

        promoted = mem.layer_facts("project", str(bound_project))[0]
        assert promoted["promoted_from"] == "session" and promoted["promoted_at"]

    def test_a_project_fact_does_not_leak_into_the_core(self, isolated_memory, bound_project,
                                                        age_fact):
        """The regression this rule exists to prevent: one repo's stack becoming global truth."""
        isolated_memory.add_fact("project", "This app uses PostgreSQL 16", 0.99,
                                 "docker-compose.yml", str(bound_project))
        age_fact("project", bound_project, 90)

        lifecycle.promote(str(bound_project), apply_changes=True)
        assert facts_in("longterm", bound_project) == []
        assert facts_in("project", bound_project) == ["This app uses PostgreSQL 16"]

    def test_a_fact_marked_transferable_may_cross_into_the_core(self, isolated_memory,
                                                                bound_project, age_fact):
        isolated_memory.add_fact("project", "Prisma migrations must run before seeding", 0.99,
                                 "incident review", str(bound_project), transferable=True)
        age_fact("project", bound_project, 90)

        lifecycle.promote(str(bound_project), apply_changes=True)
        assert facts_in("longterm", bound_project) == ["Prisma migrations must run before seeding"]

    def test_a_transferable_fact_must_still_serve_its_time(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Freshly learned rule", 0.99, "today",
                                 str(bound_project), transferable=True)
        lifecycle.promote(str(bound_project), apply_changes=True)
        assert facts_in("longterm", bound_project) == []

    def test_dry_run_moves_nothing(self, isolated_memory, bound_project):
        isolated_memory.add_fact("session", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))
        report = lifecycle.promote(str(bound_project), apply_changes=False)

        assert report["promotions"] and facts_in("session", bound_project) == ["Auth uses JWT"]
        assert facts_in("project", bound_project) == []


class TestConsolidation:
    def test_duplicates_within_a_layer_merge(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))
        isolated_memory.add_fact("project", "auth uses jwt.", 0.80, "docs/auth.md",
                                 str(bound_project))

        lifecycle.consolidate(str(bound_project), apply_changes=True)
        assert len(mem.layer_facts("project", str(bound_project))) == 1

    def test_merging_keeps_the_highest_confidence(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Auth uses JWT", 0.80, "docs/auth.md",
                                 str(bound_project))
        isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))

        lifecycle.consolidate(str(bound_project), apply_changes=True)
        assert mem.layer_facts("project", str(bound_project))[0]["confidence"] == 0.95

    def test_repetition_never_manufactures_confidence(self, isolated_memory, bound_project):
        """Three recordings of the same guess do not make it a verified fact."""
        for _ in range(3):
            isolated_memory.add_fact("project", "Probably uses Redis", 0.60, "hunch",
                                     str(bound_project))

        lifecycle.consolidate(str(bound_project), apply_changes=True)
        survivor = mem.layer_facts("project", str(bound_project))[0]
        assert survivor["confidence"] == 0.60 and survivor["occurrences"] == 3

    def test_merging_preserves_every_source(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))
        isolated_memory.add_fact("project", "Auth uses JWT", 0.80, "docs/auth.md",
                                 str(bound_project))

        lifecycle.consolidate(str(bound_project), apply_changes=True)
        sources = mem.layer_facts("project", str(bound_project))[0]["sources"]
        assert set(sources) == {"src/auth.ts", "docs/auth.md"}

    def test_a_higher_tier_supersedes_a_lower_one(self, isolated_memory, bound_project):
        isolated_memory.add_fact("session", "Auth uses JWT", 0.70, "conversation",
                                 str(bound_project))
        isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))

        lifecycle.consolidate(str(bound_project), apply_changes=True)
        assert facts_in("session", bound_project) == []
        assert facts_in("project", bound_project) == ["Auth uses JWT"]

    def test_independent_layers_keep_their_own_copies(self, isolated_memory, bound_project):
        """A failure and a pattern are different claims even with identical wording."""
        isolated_memory.add_fact("failures", "Retry storms overwhelm the queue", 0.99, "INC-1",
                                 str(bound_project))
        isolated_memory.add_fact("patterns", "Retry storms overwhelm the queue", 0.90, "review",
                                 str(bound_project))

        lifecycle.consolidate(str(bound_project), apply_changes=True)
        assert facts_in("failures", bound_project) and facts_in("patterns", bound_project)

    def test_dry_run_changes_nothing(self, isolated_memory, bound_project):
        for _ in range(2):
            isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                     str(bound_project))
        report = lifecycle.consolidate(str(bound_project), apply_changes=False)

        assert report["merged"]
        assert len(mem.layer_facts("project", str(bound_project))) == 2


class TestCompaction:
    def _fill(self, isolated_memory, project, count, confidence=0.60):
        for index in range(count):
            isolated_memory.add_fact("project", f"Observation {index}", confidence,
                                     "scan", str(project))

    def test_a_layer_within_budget_is_untouched(self, isolated_memory, bound_project):
        self._fill(isolated_memory, bound_project, 5)
        assert lifecycle.compact(str(bound_project), budget=10)["layers"] == []

    def test_overflow_is_summarised_not_deleted(self, isolated_memory, bound_project):
        self._fill(isolated_memory, bound_project, 12)
        lifecycle.compact(str(bound_project), budget=10, apply_changes=True)

        facts = mem.layer_facts("project", str(bound_project))
        summary = [f for f in facts if f.get("compacted")]
        assert len(summary) == 1
        assert summary[0]["compacted"]["count"] == 2
        assert summary[0]["compacted"]["sample"]

    def test_high_confidence_facts_are_never_compacted(self, isolated_memory, bound_project):
        self._fill(isolated_memory, bound_project, 12, confidence=0.99)
        assert lifecycle.compact(str(bound_project), budget=10)["layers"] == []

    def test_compaction_takes_a_snapshot_first(self, isolated_memory, bound_project):
        self._fill(isolated_memory, bound_project, 12)
        lifecycle.compact(str(bound_project), budget=10, apply_changes=True)
        assert lifecycle.list_snapshots(str(bound_project))

    def test_dry_run_writes_nothing(self, isolated_memory, bound_project):
        self._fill(isolated_memory, bound_project, 12)
        lifecycle.compact(str(bound_project), budget=10, apply_changes=False)
        assert len(mem.layer_facts("project", str(bound_project))) == 12


class TestSnapshots:
    def test_snapshot_captures_every_populated_layer(self, isolated_memory, bound_project):
        isolated_memory.ensure_memory_dir()
        isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))

        manifest = lifecycle.create_snapshot(str(bound_project))
        assert "project" in {f["layer"] for f in manifest["files"]}

    def test_the_manifest_records_absolute_origins(self, isolated_memory, bound_project):
        """Project and Core layers live in different stores; restore must find both."""
        isolated_memory.ensure_memory_dir()
        isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                 str(bound_project))

        manifest = lifecycle.create_snapshot(str(bound_project))
        origins = {f["layer"]: f["origin"] for f in manifest["files"]}
        assert str(bound_project) in origins["project"]
        assert str(isolated_memory.MEMORY_DIR) in origins["patterns"]

    def test_restore_undoes_a_consolidation(self, isolated_memory, bound_project):
        for _ in range(2):
            isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                     str(bound_project))
        lifecycle.consolidate(str(bound_project), apply_changes=True)
        assert len(mem.layer_facts("project", str(bound_project))) == 1

        snap_id = lifecycle.list_snapshots(str(bound_project))[0]["id"]
        lifecycle.restore_snapshot(snap_id, str(bound_project), apply_changes=True)
        assert len(mem.layer_facts("project", str(bound_project))) == 2

    def test_restore_dry_run_changes_nothing(self, isolated_memory, bound_project):
        for _ in range(2):
            isolated_memory.add_fact("project", "Auth uses JWT", 0.95, "src/auth.ts",
                                     str(bound_project))
        lifecycle.consolidate(str(bound_project), apply_changes=True)

        snap_id = lifecycle.list_snapshots(str(bound_project))[0]["id"]
        report = lifecycle.restore_snapshot(snap_id, str(bound_project), apply_changes=False)
        assert report["restored"] and not report["applied"]
        assert len(mem.layer_facts("project", str(bound_project))) == 1

    def test_an_unknown_snapshot_is_reported_not_guessed(self, isolated_memory, bound_project):
        assert "error" in lifecycle.restore_snapshot("snap-does-not-exist", str(bound_project))
