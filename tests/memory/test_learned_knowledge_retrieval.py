"""Learned knowledge in the context pack.

The pack is the only place trusted knowledge ever reaches an agent, so the rules
about what may appear there are the rules that make automatic learning safe:

  * TRUSTED only — a corroborated candidate is worth a person's attention and
    not an agent's, and mixing the two makes the weakest content in the pack
    indistinguishable from the strongest;
  * every line cites its candidate, so a reader who doubts one can see the
    arithmetic rather than take it on faith;
  * the budget is not negotiable. A learning subsystem that grows the context
    pack has become the problem CoreSentinel exists to remove.
"""

import json

import pytest

from coresentinel_core.learning import candidates, contradiction
from coresentinel_core.memory import assembly
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


LESSON = "eager-load relationships queried inside a loop"


def seed_trusted(store, lesson=LESSON, sources=("s1", "s2", "s3"), context="php83.laravel12"):
    for index, source in enumerate(sources):
        candidates.observe(store, lesson, source=source, kind="experience",
                           context=context,
                           metrics={"signature": "SIG-a",
                                    "by_context": {context: {"success": 12, "failure": 0}},
                                    "success_count": 12 if index == 0 else 0,
                                    "failure_count": 0, "occurrences": 12 if index == 0 else 0,
                                    "contexts": [context]})
    contradiction.validate(store)
    return candidates.get(store, candidates.fingerprint(lesson))


class TestOnlyTrustedAppears:
    def test_a_trusted_lesson_is_offered(self, store, project):
        seed_trusted(store)
        items = assembly.knowledge_items("fix the N+1 relationships loop", str(project), store)
        assert any("eager-load" in item["text"] for item in items)

    def test_a_corroborated_one_is_not(self, store, project):
        """Enough evidence for a person to look at, not enough for an agent to act on."""
        candidates.observe(store, LESSON, source="s1")
        candidates.observe(store, LESSON, source="s2")
        record = candidates.get(store, candidates.fingerprint(LESSON))
        assert record["status"] == candidates.CORROBORATED

        items = assembly.knowledge_items("fix the relationships loop", str(project), store)
        assert items == []

    def test_a_superseded_one_is_not(self, store, project):
        record = seed_trusted(store)
        candidates._replace(store, {**record, "status": candidates.SUPERSEDED,
                                    "superseded_by": "CAND-newer"})
        items = assembly.knowledge_items("fix the relationships loop", str(project), store)
        assert items == []

    def test_an_unrelated_lesson_is_not_offered(self, store, project):
        seed_trusted(store)
        items = assembly.knowledge_items("rotate the TLS certificate", str(project), store)
        assert items == []


class TestEveryLineIsTraceable:
    def test_the_candidate_id_is_cited(self, store, project):
        record = seed_trusted(store)
        items = assembly.knowledge_items("fix the relationships loop", str(project), store)
        assert record["id"] in items[0]["detail"]

    def test_the_explain_command_is_offered(self, store, project):
        seed_trusted(store)
        items = assembly.knowledge_items("fix the relationships loop", str(project), store)
        assert "evolve explain" in items[0]["detail"]

    def test_the_confidence_and_source_count_are_shown(self, store, project):
        seed_trusted(store)
        detail = assembly.knowledge_items("fix the relationships loop",
                                          str(project), store)[0]["detail"]
        assert "confidence" in detail
        assert "3 source(s)" in detail


class TestRanking:
    def test_a_scoped_lesson_outranks_a_general_one_on_the_same_subject(self, store, project):
        """It was evidenced where the work actually is."""
        seed_trusted(store, lesson="eager-load relationships queried inside a loop",
                     context="php83.laravel12")
        seed_trusted(store, lesson="eager-load relationships queried inside a loop always",
                     sources=("g1", "g2", "g3"), context=None)

        items = assembly.knowledge_items("relationships queried inside a loop",
                                         str(project), store)
        assert len(items) >= 2
        assert items[0]["source"].endswith("project")


class TestTheBudgetHolds:
    def test_the_pack_stays_within_budget(self, store, project):
        for index in range(40):
            seed_trusted(store, lesson=f"lesson {index} about relationships in a loop",
                         sources=(f"a{index}", f"b{index}", f"c{index}"))
        pack = assembly.assemble("relationships in a loop", str(project), budget_tokens=800)
        assert pack["estimated_tokens"] <= 800

    def test_knowledge_has_its_own_section(self, project):
        keys = [key for key, _, _ in assembly.SECTION_SPECS]
        assert "knowledge" in keys

    def test_a_pack_builds_without_a_store(self, project):
        """Learned knowledge is an addition to context assembly, never a
        dependency of it. An older Core has no experience collection at all."""
        pack = assembly.assemble("anything at all", str(project), budget_tokens=500)
        assert pack["sections"]

    def test_a_broken_store_does_not_break_the_pack(self, project, monkeypatch):
        def explode(*args, **kwargs):
            raise RuntimeError("no store here")

        monkeypatch.setattr(candidates, "trusted", explode)
        assert assembly.knowledge_items("anything", str(project)) == []
