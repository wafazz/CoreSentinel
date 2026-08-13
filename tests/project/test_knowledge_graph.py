"""Knowledge graph — construction from recorded facts, integrity, traversal.

The property that matters most: every edge comes from something somebody
recorded. A graph that infers "this controller probably implements that feature"
answers questions confidently and wrongly, which is the failure mode this whole
system exists to remove.
"""

import json

import pytest

from coresentinel_core.knowledge import entities as E
from coresentinel_core.knowledge import graph as knowledge_graph


@pytest.fixture
def project(tmp_path, monkeypatch):
    import coresentinel_memory as mem

    root = tmp_path / "shop"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "shop"}), encoding="utf-8")
    (root / "composer.json").write_text(
        json.dumps({"require": {"laravel/framework": "^11.0"}}), encoding="utf-8")
    (root / "docker-compose.yml").write_text(
        "services:\n  db:\n    image: postgres:16\n", encoding="utf-8")

    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    return root


@pytest.fixture
def linked(project):
    """A decision wired to a file and an incident, plus a pattern from that incident."""
    import coresentinel_memory as mem
    from coresentinel_core.decisions import ledger

    target = str(project)
    mem.add_fact("failures", "Session store wiped under memory pressure", 0.99,
                 "INC-1024", target)
    mem.add_fact("patterns", "Cache-aside with an explicit TTL", 0.95, "INC-1024", target)
    ledger.add(target, title="Use Redis for session storage",
               reason="MySQL connection saturation", chosen="Redis",
               related_files="src/Session.php", related_incidents="INC-1024")
    return project


class TestConstruction:
    def test_discovery_findings_become_uses_edges(self, project):
        graph = knowledge_graph.build(str(project))
        assert graph.find("Laravel"), "the detected framework is not in the graph"
        assert graph.find("PostgreSQL"), "the detected datastore is not in the graph"

    def test_every_edge_carries_its_evidence(self, linked):
        graph = knowledge_graph.build(str(linked))
        for edge in graph.edges:
            assert edge["evidence"], f"{edge['id']} cites nothing"

    def test_a_decision_links_to_its_files_and_incidents(self, linked):
        graph = knowledge_graph.build(str(linked))
        types = {edge["type"] for edge in graph.edges}
        assert "concerns" in types and "caused_by" in types

    def test_the_project_is_governed_by_its_decisions(self, linked):
        graph = knowledge_graph.build(str(linked))
        assert any(edge["type"] == "governed_by" for edge in graph.edges)

    def test_nothing_is_inferred_from_source_code(self, project):
        """An unrecorded relationship must not appear. Only discovery, decisions
        and memory produce edges."""
        (project / "app" / "Http").mkdir(parents=True)
        (project / "app" / "Http" / "ProductController.php").write_text("<?php", encoding="utf-8")
        graph = knowledge_graph.build(str(project))
        assert not graph.find("ProductController"), \
            "a controller appeared in the graph without anyone recording it"


class TestIntegrity:
    def test_no_dangling_edges_exist(self, linked):
        assert knowledge_graph.build(str(linked)).dangling() == []

    def test_an_edge_to_a_missing_entity_is_refused(self):
        graph = knowledge_graph.Graph()
        graph.ensure(E.PROJECT, "shop")
        assert graph.add_relation("project:shop", "uses", "framework:ghost") is None
        assert graph.edges == []

    def test_relations_are_not_duplicated(self):
        graph = knowledge_graph.Graph()
        source = graph.ensure(E.PROJECT, "shop")
        target = graph.ensure(E.FRAMEWORK, "Laravel")
        graph.add_relation(source, "uses", target)
        graph.add_relation(source, "uses", target)
        assert len(graph.edges) == 1

    def test_every_relation_type_declares_an_inverse(self):
        for name in E.RELATION_TYPES:
            assert name in E.INVERSE and E.INVERSE[name]

    def test_entity_ids_are_type_prefixed_and_reversible(self):
        identifier = E.entity_id(E.DECISION, "ADR-042")
        assert identifier == "decision:ADR-042"
        assert E.split_id(identifier) == ("decision", "ADR-042")

    def test_rebuilding_produces_the_same_graph(self, linked):
        first = knowledge_graph.build(str(linked)).describe()
        second = knowledge_graph.build(str(linked)).describe()
        assert first == second


class TestTraversal:
    def test_a_chain_is_walked_across_entity_types(self, linked):
        """decision -> file and decision -> incident, reached from the project."""
        graph = knowledge_graph.build(str(linked))
        project_id = graph.find("shop")[0]["id"]
        result = graph.traverse(project_id, depth=2)

        reached = {node["type"] for node in result["nodes"]}
        assert {"project", "decision", "file", "incident"} <= reached

    def test_depth_bounds_the_walk(self, linked):
        graph = knowledge_graph.build(str(linked))
        project_id = graph.find("shop")[0]["id"]
        shallow = graph.traverse(project_id, depth=1)
        deep = graph.traverse(project_id, depth=3)
        assert len(shallow["nodes"]) <= len(deep["nodes"])

    def test_traversal_is_walked_from_either_end(self, linked):
        graph = knowledge_graph.build(str(linked))
        decision = next(n for n in graph.nodes.values() if n["type"] == "decision")
        result = graph.traverse(decision["id"], depth=1)
        assert any(edge["type"] == "governs" for edge in result["edges"]), \
            "an inbound edge must be walkable outward from its target"

    def test_an_unknown_entity_is_reported_not_guessed(self, linked):
        graph = knowledge_graph.build(str(linked))
        assert "error" in graph.traverse("decision:ADR-999", depth=1)

    def test_a_cycle_does_not_loop_forever(self):
        graph = knowledge_graph.Graph()
        first = graph.ensure(E.DECISION, "ADR-001")
        second = graph.ensure(E.DECISION, "ADR-002")
        graph.add_relation(first, "relates_to", second)
        graph.add_relation(second, "relates_to", first)
        assert len(graph.traverse(first, depth=5)["nodes"]) == 2

    def test_depth_is_capped(self, linked):
        graph = knowledge_graph.build(str(linked))
        start = graph.find("shop")[0]["id"]
        assert graph.traverse(start, depth=99)["depth"] == knowledge_graph.MAX_DEPTH

    def test_find_matches_an_id_a_key_or_a_label(self, linked):
        graph = knowledge_graph.build(str(linked))
        assert graph.find("framework:Laravel")
        assert graph.find("Laravel")
        assert graph.find("laravel")

    def test_an_isolated_entity_renders_an_honest_message(self, project):
        graph = knowledge_graph.Graph()
        graph.ensure(E.PATTERN, "PAT-0001", label="lonely")
        rendered = knowledge_graph.render(graph.traverse("pattern:PAT-0001", depth=2))
        assert "Nothing is linked" in rendered and "Nothing is inferred" in rendered


class TestPersistence:
    def test_a_snapshot_round_trips_through_the_store(self, linked, tmp_path):
        from coresentinel_core.storage import JsonStore

        graph = knowledge_graph.build(str(linked))
        store = JsonStore(tmp_path / "records")
        for node in graph.nodes.values():
            store.knowledge_entities.append({"entity_key": node["id"],
                                             "entity_type": node["type"],
                                             "label": node["label"]})
        for edge in graph.edges:
            store.knowledge_relations.append({"record_id": edge["id"], "source": edge["source"],
                                              "relation_type": edge["type"],
                                              "target": edge["target"]})

        assert store.knowledge_entities.count() == len(graph.nodes)
        assert store.knowledge_relations.count() == len(graph.edges)
