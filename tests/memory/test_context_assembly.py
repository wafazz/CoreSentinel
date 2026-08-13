"""Task-relevant context assembly — relevance, budget, and honest truncation.

The v1 pack returned every fact in three layers, unranked and unbounded. These
tests hold the replacement to the two properties that make it worth having:
what comes back is about the task, and what does not fit is declared.
"""

import json

import pytest

from coresentinel_core.memory import assembly


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A bound project whose memory and decision ledger are isolated in tmp_path."""
    import coresentinel_memory as mem

    root = tmp_path / "shop"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "shop", "coresentinel_api": "1.0"}), encoding="utf-8")

    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    return root


@pytest.fixture
def stocked(project):
    """Facts, failures, patterns and a decision — some about Redis, some not."""
    import coresentinel_memory as mem
    from coresentinel_core.decisions import ledger

    target = str(project)
    mem.add_fact("project", "Product listing is served by ProductController", 0.95, "src", target)
    mem.add_fact("project", "Redis runs on port 6379 in docker-compose", 0.98, "compose", target)
    mem.add_fact("project", "Invoices are rendered with mPDF", 0.94, "src", target)
    mem.add_fact("project", "The payroll export runs monthly on the 28th", 0.93, "cron", target)
    mem.add_fact("failures", "Redis eviction wiped the session store under memory pressure",
                 0.99, "INC-1024", target)
    mem.add_fact("failures", "PDF fonts broke on the staging box", 0.9, "INC-0007", target)
    mem.add_fact("patterns", "Cache-aside with an explicit TTL for Redis reads", 0.95,
                 "pattern library", target)

    ledger.add(target, title="Use Redis for session storage",
               reason="MySQL connection saturation observed under production load",
               chosen="Redis", alternatives="Database sessions, Memcached",
               evidence="INC-1024")
    ledger.add(target, title="Render invoices with mPDF", reason="Dual HTML and PDF output",
               chosen="mPDF", alternatives="wkhtmltopdf")
    return project


def texts(pack, key):
    section = next(s for s in pack["sections"] if s["key"] == key)
    return [item["text"] for item in section["items"]]


class TestRelevance:
    def test_the_worked_example_returns_what_the_task_needs(self, stocked):
        """The brief's example: 'Add Redis caching to product listing'."""
        pack = assembly.assemble("Add Redis caching to product listing", str(stocked))

        assert any("Redis runs on port 6379" in t for t in texts(pack, "facts")), \
            "the existing Redis configuration was not retrieved"
        assert any("Redis" in t for t in texts(pack, "decisions")), \
            "the prior Redis decision was not retrieved"
        assert any("Cache-aside" in t for t in texts(pack, "patterns")), \
            "the related pattern was not retrieved"
        assert any("eviction" in t for t in texts(pack, "failures")), \
            "the related incident was not retrieved"
        assert texts(pack, "rules"), "no governance rules were included"

    def test_unrelated_facts_are_excluded(self, stocked):
        pack = assembly.assemble("Add Redis caching to product listing", str(stocked))
        everything = " ".join(t for s in pack["sections"] for t in texts(pack, s["key"]))
        assert "payroll export" not in everything
        assert "mPDF" not in everything.replace("Render invoices with mPDF", "")

    def test_an_unrelated_decision_is_not_included(self, stocked):
        pack = assembly.assemble("Add Redis caching to product listing", str(stocked))
        assert not any("mPDF" in t for t in texts(pack, "decisions"))

    def test_a_contradicting_task_lifts_the_decision_and_flags_it(self, stocked):
        pack = assembly.assemble("switch from Redis to database sessions", str(stocked))
        decisions = texts(pack, "decisions")
        assert decisions and "CONTRADICTS" in decisions[0], \
            "a task reversing a decision must surface it first, flagged"

    def test_project_identity_is_always_present(self, stocked):
        pack = assembly.assemble("something entirely unrelated to anything", str(stocked))
        assert texts(pack, "project"), "the pack must always state what project this is"

    def test_strict_block_rules_apply_even_when_unmentioned(self, stocked):
        """A STRICT_BLOCK rule is the floor, not a suggestion — it is not opt-in."""
        pack = assembly.assemble("rename a variable", str(stocked))
        assert texts(pack, "rules")

    def test_min_confidence_filters_low_confidence_facts(self, project):
        import coresentinel_memory as mem
        mem.add_fact("project", "Redis might be configured somewhere", 0.2, "guess", str(project))
        pack = assembly.assemble("Redis", str(project), min_confidence=0.5)
        assert not any("might be configured" in t for t in texts(pack, "facts"))


class TestBudget:
    @pytest.mark.parametrize("budget", [200, 500, 1500, 4000])
    def test_the_budget_is_never_exceeded(self, stocked, budget):
        pack = assembly.assemble("Add Redis caching to product listing", str(stocked), budget)
        assert pack["estimated_tokens"] <= budget

    def test_the_budget_is_never_exceeded_by_the_rendered_pack(self, stocked):
        """The estimate must bound the text actually handed to an agent."""
        budget = 600
        pack = assembly.assemble("Add Redis caching to product listing", str(stocked), budget)
        rendered_items = sum(item["estimated_tokens"]
                             for section in pack["sections"] for item in section["items"])
        assert rendered_items == pack["estimated_tokens"] <= budget

    def test_truncation_is_declared_not_silent(self, stocked):
        pack = assembly.assemble("Redis", str(stocked), budget_tokens=60)
        assert pack["excluded"]["total"] > 0
        assert pack["excluded"]["highest_scoring"], \
            "the best excluded item must be named so a partial pack cannot read as complete"

    def test_a_generous_budget_excludes_nothing(self, stocked):
        pack = assembly.assemble("Redis", str(stocked), budget_tokens=100000)
        assert pack["excluded"]["total"] == 0

    def test_the_token_figure_is_declared_an_estimate(self, stocked):
        pack = assembly.assemble("Redis", str(stocked))
        assert "approximation" in pack["token_estimate_basis"]

    def test_each_section_reports_what_it_dropped(self, stocked):
        pack = assembly.assemble("Redis", str(stocked), budget_tokens=60)
        for section in pack["sections"]:
            assert section["included"] + section["excluded"] == section["available"]

    def test_a_zero_budget_degrades_rather_than_crashing(self, stocked):
        pack = assembly.assemble("Redis", str(stocked), budget_tokens=0)
        assert pack["estimated_tokens"] <= pack["budget_tokens"]


class TestPackShape:
    def test_the_pack_is_json_serialisable(self, stocked):
        json.dumps(assembly.assemble("Redis", str(stocked)))

    def test_every_section_is_present_even_when_empty(self, project):
        pack = assembly.assemble("anything", str(project))
        assert [s["key"] for s in pack["sections"]] == [k for k, _, _ in assembly.SECTION_SPECS]

    def test_the_task_is_echoed(self, stocked):
        assert assembly.assemble("Add Redis caching", str(stocked))["task"] == "Add Redis caching"

    def test_rendering_produces_the_declared_sections(self, stocked):
        rendered = assembly.render(assembly.assemble("Add Redis caching", str(stocked)))
        assert "Decisions already made" in rendered
        assert "budgeted tokens" in rendered

    def test_an_empty_store_still_produces_a_usable_pack(self, project):
        pack = assembly.assemble("Add Redis caching", str(project))
        assert pack["estimated_tokens"] >= 0
        assert assembly.render(pack)
