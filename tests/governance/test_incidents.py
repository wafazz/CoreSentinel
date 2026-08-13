"""Incidents — the record, its links, and the learning that makes it worth keeping.

`61-incident-protocol.md` described a four-phase response since v1 and nothing
recorded an incident, so the phase that turns a bad afternoon into a rule had
nowhere to write its output.
"""

import json

import pytest

from coresentinel_core.incidents import ledger as incidents


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
def worked_example(project):
    """The brief's INC-1024, recorded end to end."""
    incidents.create(
        str(project),
        title="Database connection exhaustion",
        problem="The connection pool was exhausted under peak load",
        root_cause="An agent introduced an N+1 query in the listing endpoint",
        severity=incidents.HIGH,
        root_cause_class=incidents.CLASS_A,
        related_files="src/ProductController.php")
    return project


class TestRecording:
    def test_an_incident_is_recorded_with_an_id(self, project):
        record = incidents.create(str(project), title="Pool exhaustion",
                                  problem="connections ran out")
        assert record["id"].startswith("INC-")
        assert record["status"] == incidents.OPEN

    def test_ids_are_sequential(self, project):
        first = incidents.create(str(project), title="one")
        second = incidents.create(str(project), title="two")
        assert int(second["id"].split("-")[1]) == int(first["id"].split("-")[1]) + 1

    def test_an_incident_belongs_to_its_project(self, project):
        record = incidents.create(str(project), title="x")
        assert record["scope"] == incidents.SCOPE_PROJECT
        assert incidents.ledger_path(str(project)).is_relative_to(project)

    def test_recording_a_resolution_closes_it_immediately(self, project):
        record = incidents.create(str(project), title="x", resolution="reverted the change")
        assert record["status"] == incidents.RESOLVED and record["resolved_at"]

    def test_a_corrupt_ledger_is_never_overwritten(self, project):
        path = incidents.ledger_path(str(project))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")
        assert incidents.create(str(project), title="x") is None
        assert path.read_text(encoding="utf-8") == "{ not json"

    def test_an_unknown_severity_falls_back_rather_than_being_invented(self, project):
        record = incidents.create(str(project), title="x", severity="Apocalyptic")
        assert record["severity"] == incidents.MEDIUM


class TestTheFourFields:
    def test_the_worked_example_records_problem_and_root_cause(self, worked_example):
        record = incidents.get("INC-0001", str(worked_example))
        assert "pool was exhausted" in record["problem"]
        assert "N+1" in record["root_cause"]

    def test_resolving_requires_a_resolution(self, worked_example):
        report = incidents.resolve("INC-0001", str(worked_example))
        assert "error" in report

    def test_resolving_without_a_learning_is_allowed_but_reported(self, worked_example):
        report = incidents.resolve("INC-0001", str(worked_example),
                                   resolution="Added eager loading")
        assert report["incident"]["status"] == incidents.RESOLVED
        assert "stops it recurring" in report["warning"]

    def test_a_learning_silences_the_warning(self, worked_example):
        report = incidents.resolve(
            "INC-0001", str(worked_example),
            resolution="Added eager loading",
            learning="Flag repeated relationship queries inside a loop during review")
        assert report["warning"] is None

    def test_the_summary_names_resolutions_without_a_learning(self, worked_example):
        incidents.resolve("INC-0001", str(worked_example), resolution="reverted")
        assert "INC-0001" in incidents.summary(str(worked_example))["without_learning"]

    def test_resolving_an_unknown_incident_is_refused(self, project):
        assert "error" in incidents.resolve("INC-9999", str(project), resolution="x")


class TestLinks:
    def test_an_incident_links_to_a_decision_and_a_pattern(self, worked_example):
        report = incidents.link("INC-0001", str(worked_example),
                                related_decisions="ADR-042", related_patterns="PAT-0032")
        assert report["incident"]["related_decisions"] == ["ADR-042"]
        assert report["incident"]["related_patterns"] == ["PAT-0032"]

    def test_links_accumulate_without_duplicating(self, worked_example):
        incidents.link("INC-0001", str(worked_example), related_files="src/a.php")
        incidents.link("INC-0001", str(worked_example), related_files="src/a.php,src/b.php")
        record = incidents.get("INC-0001", str(worked_example))
        assert record["related_files"] == ["src/ProductController.php", "src/a.php", "src/b.php"]

    def test_linking_nothing_is_refused(self, worked_example):
        assert "error" in incidents.link("INC-0001", str(worked_example))

    def test_linking_an_unknown_incident_is_refused(self, project):
        assert "error" in incidents.link("INC-9999", str(project), related_files="a.py")

    @pytest.mark.parametrize("field", incidents.LINK_FIELDS)
    def test_every_link_type_is_supported(self, worked_example, field):
        report = incidents.link("INC-0001", str(worked_example), **{field: "TARGET-1"})
        assert "TARGET-1" in report["incident"][field]


class TestKnowledgeGraphIntegration:
    def test_an_incident_reaches_the_graph(self, worked_example):
        from coresentinel_core.knowledge import graph as knowledge_graph

        built = knowledge_graph.build(str(worked_example))
        assert built.find("INC-0001"), "the incident is not in the graph"

    def test_a_linked_file_becomes_an_edge(self, worked_example):
        from coresentinel_core.knowledge import graph as knowledge_graph

        built = knowledge_graph.build(str(worked_example))
        result = built.traverse("incident:INC-0001", depth=1)
        assert any(node["type"] == "file" for node in result["nodes"])

    def test_a_pattern_is_learned_from_its_incident(self, worked_example):
        """The edge runs pattern -> incident: the pattern was extracted from it."""
        from coresentinel_core.knowledge import graph as knowledge_graph

        incidents.link("INC-0001", str(worked_example), related_patterns="PAT-0032")
        built = knowledge_graph.build(str(worked_example))
        assert any(edge["type"] == "learned_from" for edge in built.edges)

    def test_the_graph_has_no_dangling_edges_after_linking(self, worked_example):
        from coresentinel_core.knowledge import graph as knowledge_graph

        incidents.link("INC-0001", str(worked_example),
                       related_decisions="ADR-042", related_patterns="PAT-0032")
        assert knowledge_graph.build(str(worked_example)).dangling() == []


class TestSummary:
    def test_counts_by_status_and_severity(self, project):
        incidents.create(str(project), title="one", severity=incidents.CRITICAL)
        incidents.create(str(project), title="two", severity=incidents.LOW,
                         resolution="fixed")
        overview = incidents.summary(str(project))
        assert overview["total"] == 2 and overview["open"] == 1
        assert overview["by_severity"][incidents.CRITICAL] == 1

    def test_root_cause_classes_come_from_the_protocol(self):
        assert len(incidents.CLASSES) == 4
        assert all(cls[0] in "ABCD" for cls in incidents.CLASSES)
