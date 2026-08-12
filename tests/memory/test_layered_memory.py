"""Layered Memory Engine — confidence classification, layer writes, ADR ledger."""

import json

import pytest


class TestConfidenceClassification:
    @pytest.mark.parametrize("score,expected", [
        (1.00, "Known"), (0.98, "Known"), (0.90, "Known"),
        (0.899, "Assumed"), (0.75, "Assumed"), (0.50, "Assumed"),
        (0.499, "Unknown"), (0.10, "Unknown"), (0.0, "Unknown"),
    ])
    def test_boundaries(self, isolated_memory, score, expected):
        assert isolated_memory.classify_confidence(score).startswith(expected)

    def test_known_threshold_is_inclusive(self, isolated_memory):
        """0.90 is Known; anything below it must not claim empirical verification."""
        assert "Known" in isolated_memory.classify_confidence(0.90)
        assert "Known" not in isolated_memory.classify_confidence(0.8999)


class TestLayerInitialization:
    def test_creates_every_layer(self, isolated_memory):
        isolated_memory.ensure_memory_dir()
        for name, path in isolated_memory.MEMORY_LAYERS.items():
            assert path.exists(), f"layer '{name}' was not created"

    def test_layer_default_shapes(self, isolated_memory):
        isolated_memory.ensure_memory_dir()
        layers = isolated_memory.MEMORY_LAYERS

        decisions = json.loads(layers["decisions"].read_text(encoding="utf-8"))
        assert decisions == [], "the ADR ledger must initialize as a list"

        working = json.loads(layers["working"].read_text(encoding="utf-8"))
        assert "current_task" in working and "status" in working

        project = json.loads(layers["project"].read_text(encoding="utf-8"))
        assert project == {"facts": []}

    def test_does_not_clobber_existing_layer(self, isolated_memory):
        isolated_memory.ensure_memory_dir()
        isolated_memory.add_fact("project", "seeded fact", 0.95, "test")
        isolated_memory.ensure_memory_dir()

        data = json.loads(isolated_memory.MEMORY_LAYERS["project"].read_text(encoding="utf-8"))
        assert len(data["facts"]) == 1, "re-initializing must not erase recorded facts"


class TestFactRecording:
    def test_records_all_metadata(self, isolated_memory):
        assert isolated_memory.add_fact("project", "Uses PostgreSQL", 0.98, "docker-compose.yml")

        entry = json.loads(
            isolated_memory.MEMORY_LAYERS["project"].read_text(encoding="utf-8"))["facts"][0]
        assert entry["fact"] == "Uses PostgreSQL"
        assert entry["confidence"] == 0.98
        assert entry["source"] == "docker-compose.yml"
        assert entry["classification"].startswith("Known")
        assert entry["last_verified"], "every fact must carry a verification timestamp"

    def test_low_confidence_is_not_marked_verified(self, isolated_memory):
        isolated_memory.add_fact("project", "Might use Redis", 0.4, "guess")
        entry = json.loads(
            isolated_memory.MEMORY_LAYERS["project"].read_text(encoding="utf-8"))["facts"][0]
        assert "Unknown" in entry["classification"]
        assert "Known" not in entry["classification"]

    def test_facts_append_rather_than_replace(self, isolated_memory):
        isolated_memory.add_fact("patterns", "first", 0.95, "a")
        isolated_memory.add_fact("patterns", "second", 0.95, "b")
        data = json.loads(isolated_memory.MEMORY_LAYERS["patterns"].read_text(encoding="utf-8"))
        assert [f["fact"] for f in data["facts"]] == ["first", "second"]

    def test_rejects_unknown_layer(self, isolated_memory):
        assert isolated_memory.add_fact("nonexistent", "x", 0.9, "s") is False

    def test_rejects_writing_facts_to_the_decision_ledger(self, isolated_memory):
        """decisions.json is an ADR list, not a facts layer."""
        assert isolated_memory.add_fact("decisions", "x", 0.9, "s") is False

    @pytest.mark.parametrize("layer", ["working", "session", "project",
                                       "longterm", "failures", "patterns"])
    def test_every_documented_layer_accepts_facts(self, isolated_memory, layer):
        assert isolated_memory.add_fact(layer, f"fact for {layer}", 0.95, "test") is True


class TestDecisionLedger:
    def test_assigns_sequential_adr_ids(self, isolated_memory):
        first = isolated_memory.add_decision("Use PostgreSQL", "ACID", "PostgreSQL")
        second = isolated_memory.add_decision("Use Redis", "Caching", "Redis")
        assert first == "ADR-001"
        assert second == "ADR-002"

    def test_splits_comma_separated_alternatives(self, isolated_memory):
        isolated_memory.add_decision("Pick a DB", "Consistency", "PostgreSQL",
                                     alternatives="MongoDB, MySQL")
        record = json.loads(
            isolated_memory.MEMORY_LAYERS["decisions"].read_text(encoding="utf-8"))[0]
        assert record["alternatives"] == ["MongoDB", "MySQL"]

    def test_records_rationale_and_timestamp(self, isolated_memory):
        isolated_memory.add_decision("Use Python", "Team expertise", "Python")
        record = json.loads(
            isolated_memory.MEMORY_LAYERS["decisions"].read_text(encoding="utf-8"))[0]
        assert record["reason"] == "Team expertise"
        assert record["status"] == "Accepted"
        assert record["created_at"]

    def test_query_filters_the_listing(self, isolated_memory, capsys):
        isolated_memory.add_decision("Use PostgreSQL", "ACID compliance", "PostgreSQL")
        isolated_memory.add_decision("Use Tailwind", "Utility CSS", "Tailwind")
        capsys.readouterr()

        isolated_memory.list_decisions("postgres")
        out = capsys.readouterr().out
        assert "PostgreSQL" in out
        assert "Tailwind" not in out
        assert "Showing 1 / 2" in out

    def test_empty_ledger_reports_cleanly(self, isolated_memory, capsys):
        isolated_memory.list_decisions()
        assert "No architecture decisions recorded" in capsys.readouterr().out
