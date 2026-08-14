"""Performance budgets — published limits, asserted rather than aspired to.

Every budget in `coresentinel_core.observability.budgets` is checked here against
a real store. A budget nothing asserts is a comment.

Two rules these tests follow, because a flaky performance test gets deleted and
then protects nothing:

  * Absolute timings are given generous headroom (4x or more over the measured
    cost) so a loaded CI runner does not fail the build for being busy.
  * The property that actually matters — cost per record not growing with the
    size of the store — is asserted as a RATIO, which is immune to how fast the
    machine is.
"""

import json
import time
import tracemalloc

import pytest

from coresentinel_core.observability import budgets
from coresentinel_core.runtime.container import Runtime
from coresentinel_core.storage.json_store import JsonStore
from coresentinel_core.storage.sqlite_store import SqliteStore

TOPICS = ["redis caching", "postgres migration", "auth token rotation", "webhook retry",
          "rate limit", "payroll export", "pdf renderer", "queue worker", "s3 upload",
          "session store"]


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def time_ms(fn, runs=3, warmup=1):
    """Median wall time. Never measured under tracemalloc — it inflates by ~5x."""
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1000)
    return median(samples)


@pytest.fixture
def bound_project(tmp_path, monkeypatch):
    """A bound project with its own record store, so nothing writes to the Core."""
    import coresentinel_memory as mem

    project = tmp_path / "project"
    (project / ".coresentinel").mkdir(parents=True)
    (project / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "budget-test"}), encoding="utf-8")
    mem.reset_project_root_cache()
    return project


@pytest.fixture
def big_memory_store(tmp_path, monkeypatch):
    """A 10,000-fact memory store. The size Planning.md names for retrieval."""
    import coresentinel_memory as mem

    memory_dir = tmp_path / "big-memory"
    memory_dir.mkdir()
    facts = [{"id": f"f{i:05d}",
              "fact": f"{TOPICS[i % 10]} detail number {i} for the service layer",
              "confidence": 0.5 + (i % 50) / 100.0, "source": "fixture",
              "created_at": "2026-01-01 00:00:00", "last_verified": "2026-01-01 00:00:00"}
             for i in range(10_000)]
    for layer in mem.FACT_LAYERS:
        share = facts if layer == "project" else facts[:200]
        (memory_dir / f"{layer}.json").write_text(json.dumps({"facts": share}), encoding="utf-8")

    monkeypatch.setattr(mem, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {n: memory_dir / f"{n}.json" for n in mem.MEMORY_LAYERS})
    mem.reset_project_root_cache()
    return tmp_path


class TestPublishedBudgets:
    """The budget table itself has to be honest before the numbers mean anything."""

    def test_every_budget_names_what_it_measures_and_its_basis(self):
        for key, budget in budgets.BUDGETS.items():
            assert budget.get("what"), f"{key} does not say what it measures"
            assert budget.get("limit") is not None, f"{key} has no limit"
            assert budget.get("unit"), f"{key} has no unit"
            assert budget.get("measured") is not None, \
                f"{key} publishes a limit with no measurement behind it"

    def test_every_budget_carries_headroom_over_its_measurement(self):
        """A limit at or below what was measured fails the moment anything moves."""
        for key in budgets.BUDGETS:
            assert budgets.headroom(key) >= 1.5, \
                f"{key} has less than 1.5x headroom and will flake"

    def test_an_unmeasured_budget_is_unknown_not_a_pass(self):
        """The rule the verification engine keeps, applied to performance."""
        result = budgets.check("recall.10k_facts_ms", None)
        assert result["status"] == budgets.UNKNOWN
        assert result["status"] != budgets.PASS

    def test_a_report_with_nothing_measured_is_incomplete_not_within_budget(self):
        report = budgets.report({})
        assert report["verdict"] == "INCOMPLETE"
        assert report["passed"] == 0

    def test_exceeding_a_budget_fails_and_says_by_how_much(self):
        result = budgets.check("recall.10k_facts_ms", 100_000)
        assert result["status"] == budgets.FAIL
        assert "exceeds" in result["reason"]

    def test_an_unknown_key_is_not_silently_accepted(self):
        assert budgets.check("nothing.like.this", 1)["status"] == budgets.UNKNOWN


class TestRetrievalBudgets:
    def test_recall_over_ten_thousand_facts_is_within_budget(self, big_memory_store):
        import coresentinel_recall as recall

        observed = time_ms(lambda: recall.recall("redis caching", str(big_memory_store), limit=20))
        result = budgets.check("recall.10k_facts_ms", observed)
        assert result["status"] == budgets.PASS, result["reason"]

    def test_recall_still_finds_what_it_used_to(self, big_memory_store):
        """The speed-up removed a redundant tokenize. It must not have removed a hit.

        `t in hay_terms or t in hay` was equivalent to `t in hay`, because
        anything tokenize() finds in the haystack is a substring of it. This
        pins that equivalence rather than trusting the argument.
        """
        import coresentinel_recall as recall

        hits = recall.recall("redis caching", str(big_memory_store), limit=50)
        assert hits, "a query matching thousands of facts returned nothing"
        assert all("redis" in h["text"].lower() or "caching" in h["text"].lower()
                   for h in hits)

    def test_score_record_matches_a_token_and_a_substring_alike(self):
        import coresentinel_recall as recall

        terms = recall.tokenize("redis")
        whole_token, _ = recall.score_record(terms, "redis", "we use redis here", 1.0)
        inside_word, _ = recall.score_record(terms, "redis", "rediscovered", 1.0)
        assert whole_token > 0
        # Substring matching was the pre-existing behaviour: `t in hay` already
        # matched inside a word before this phase touched it. Pinned so the
        # optimisation is not later blamed for a looseness it did not introduce.
        assert inside_word > 0

    def test_context_assembly_over_ten_thousand_facts_is_within_budget(self, big_memory_store):
        from coresentinel_core.memory import assembly

        observed = time_ms(
            lambda: assembly.assemble("add redis caching to product listing",
                                      str(big_memory_store), 4000),
            runs=3, warmup=1)
        result = budgets.check("context.assemble_10k_facts_ms", observed)
        assert result["status"] == budgets.PASS, result["reason"]

    def test_context_assembly_never_exceeds_its_token_budget(self, big_memory_store):
        """Planning.md R-05: the pack must not ship more than it was budgeted."""
        from coresentinel_core.memory import assembly

        for budget in (200, 500, 1500, 4000):
            pack = assembly.assemble("add redis caching to product listing",
                                     str(big_memory_store), budget)
            assert pack["estimated_tokens"] <= budget, \
                f"a {budget}-token pack came back with {pack['estimated_tokens']}"

    def test_a_truncated_pack_says_so(self, big_memory_store):
        from coresentinel_core.memory import assembly

        pack = assembly.assemble("redis caching", str(big_memory_store), 200)
        assert pack["excluded"]["total"] > 0
        assert pack["excluded"]["highest_scoring"]


class TestStorageBudgets:
    @pytest.mark.parametrize("store_cls", [JsonStore, SqliteStore])
    def test_reading_a_page_out_of_ten_thousand_is_within_budget(self, tmp_path, store_cls):
        store = store_cls(str(tmp_path / store_cls.backend))
        repo = store.repository("audit_events")
        for i in range(10_000):
            repo.append({"subject": "verification", "actor": "fixture", "action": f"a{i}"})

        observed = time_ms(lambda: repo.page(20, 0), runs=5)
        result = budgets.check("storage.read_page_of_10k_ms", observed)
        assert result["status"] == budgets.PASS, f"{store_cls.backend}: {result['reason']}"
        store.close()

    @pytest.mark.parametrize("store_cls", [JsonStore, SqliteStore])
    def test_reading_a_page_holds_memory_bounded_by_the_page(self, tmp_path, store_cls):
        """Planning.md: memory footprint bounded regardless of store size.

        Reading twenty records used to load ten thousand and reverse them, which
        is 7 MB of heap to answer a question about 20 records.
        """
        store = store_cls(str(tmp_path / store_cls.backend))
        repo = store.repository("audit_events")
        for i in range(10_000):
            repo.append({"subject": "verification", "actor": "fixture", "action": f"a{i}"})

        repo.page(20, 0)  # warm any lazily-built state before measuring
        tracemalloc.start()
        page = repo.page(20, 0)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()

        assert len(page) == 20
        result = budgets.check("storage.read_page_of_10k_mb", peak)
        assert result["status"] == budgets.PASS, f"{store_cls.backend}: {result['reason']}"
        store.close()

    @pytest.mark.parametrize("store_cls", [JsonStore, SqliteStore])
    def test_appending_eight_hundred_records_is_within_budget(self, tmp_path, store_cls):
        def run():
            store = store_cls(str(tmp_path / f"{store_cls.backend}-{time.perf_counter_ns()}"))
            repo = store.repository("audit_events")
            for i in range(800):
                repo.append({"subject": "verification", "actor": "fixture", "action": f"a{i}"})
            store.close()

        observed = time_ms(run, runs=1, warmup=0)
        result = budgets.check("storage.append_800_records_ms", observed)
        assert result["status"] == budgets.PASS, f"{store_cls.backend}: {result['reason']}"


class TestScalingIsFlat:
    """The property that survives a change of machine.

    Every other budget here is in milliseconds and so describes the hardware as
    much as the code. This one is a ratio.
    """

    def _cost_per_event(self, project, preload):
        runtime = Runtime.bootstrap(str(project))
        store = runtime.store

        if preload:
            for i in range(preload):
                store.audit_events.append({
                    "id": f"AUD-{i + 1:06d}", "seq": i + 1, "subject": "verification",
                    "actor": "seed", "action": f"a{i}", "detail": {},
                    "prev_hash": "sha256:" + "0" * 32, "hash": "sha256:" + f"{i:032d}"})

        samples = []
        for _ in range(3):
            start = time.perf_counter()
            for i in range(60):
                runtime.events.emit("MemoryCreated", {"layer": "project", "fact": f"f{i}"})
            samples.append((time.perf_counter() - start) * 1000 / 60)
        runtime.shutdown()
        return median(samples)

    def test_writing_an_audited_event_does_not_slow_down_as_the_trail_fills(self, tmp_path):
        """Regression for the defect this phase existed to remove.

        `ledger.append` called `last()`, which read every record in the trail to
        find the newest one, and the repository's id generator read the file
        again to count it. Two full reads per write: the cost per event rose
        11.4x between an empty store and one holding 4,000 records, and was
        still climbing.
        """
        import coresentinel_memory as mem

        empty_project = tmp_path / "empty"
        (empty_project / ".coresentinel").mkdir(parents=True)
        (empty_project / ".coresentinel" / "config.json").write_text("{}", encoding="utf-8")
        full_project = tmp_path / "full"
        (full_project / ".coresentinel").mkdir(parents=True)
        (full_project / ".coresentinel" / "config.json").write_text("{}", encoding="utf-8")
        mem.reset_project_root_cache()

        on_empty = self._cost_per_event(empty_project, 0)
        on_full = self._cost_per_event(full_project, 2_000)

        ratio = on_full / on_empty if on_empty else 0
        result = budgets.check("audit.append_scaling_ratio", ratio)
        assert result["status"] == budgets.PASS, (
            f"writing into a 2,000-record trail cost {on_full:.2f} ms/event against "
            f"{on_empty:.2f} ms/event into an empty one ({ratio:.1f}x) — "
            "something is re-reading the trail on every append")

    def test_runtime_bootstrap_is_within_budget(self, tmp_path):
        observed = median([Runtime.bootstrap(str(tmp_path)).bootstrap_ms for _ in range(5)])
        result = budgets.check("runtime.bootstrap_ms", observed)
        assert result["status"] == budgets.PASS, result["reason"]
