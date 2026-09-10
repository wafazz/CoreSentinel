"""Contradiction — and the far more common case that only looks like one.

The load-bearing test in this file is `test_two_contexts_narrow_rather_than_
contradict`. A system that treats "failed here, worked there" as a contradiction
will override where it should have narrowed, and it will do so from real
evidence — which is what makes the resulting nonsense so hard to spot later.

The second load-bearing test is `test_promotion_stops_at_trusted`. Everything
automatic in this subsystem is safe only because it terminates at a retrieval
tier that compels nothing.
"""

import json

import pytest

from coresentinel_core.learning import candidates, confidence, contradiction
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


def seed(store, lesson, sources, by_context, signature="SIG-test"):
    """A candidate with per-context outcome evidence attached."""
    for index, source in enumerate(sources):
        successes = sum(v.get("success", 0) for v in by_context.values())
        failures = sum(v.get("failure", 0) for v in by_context.values())
        candidates.observe(
            store, lesson, source=source, kind="experience",
            metrics={"signature": signature, "by_context": by_context,
                     "success_count": successes if index == 0 else 0,
                     "failure_count": failures if index == 0 else 0,
                     "occurrences": successes + failures if index == 0 else 0,
                     "contexts": sorted(by_context)})
    return candidates.get(store, candidates.fingerprint(lesson))


class TestScopingComesBeforeOverriding:
    def test_two_contexts_narrow_rather_than_contradict(self, store):
        """Failed on one stack, worked on another. The lesson was drawn too
        wide — it was not wrong."""
        record = seed(store, "queue workers stall", ["s1", "s2"], {
            "ubuntu2404.php83": {"success": 0, "failure": 6},
            "windows.php83": {"success": 5, "failure": 0}})

        findings = contradiction.outcome_findings(record)
        verdicts = {f["verdict"] for f in findings}
        assert contradiction.SCOPED in verdicts
        assert contradiction.INCONSISTENT not in verdicts

    def test_scoping_does_not_count_against_confidence(self, store):
        """Penalising a lesson for becoming more precise is exactly backwards."""
        record = seed(store, "queue workers stall", ["s1", "s2"], {
            "ubuntu2404.php83": {"success": 0, "failure": 6},
            "windows.php83": {"success": 5, "failure": 0}})
        assert contradiction.contradicting_count(record) == 0

    def test_the_finding_names_where_each_way_it_went(self, store):
        record = seed(store, "queue workers stall", ["s1", "s2"], {
            "ubuntu2404.php83": {"success": 0, "failure": 6},
            "windows.php83": {"success": 5, "failure": 0}})
        scoped = [f for f in contradiction.outcome_findings(record)
                  if f["verdict"] == contradiction.SCOPED][0]
        assert scoped["failing_in"] == ["ubuntu2404.php83"]
        assert scoped["succeeding_in"] == ["windows.php83"]


class TestRealDisagreement:
    def test_both_outcomes_in_one_context_is_inconsistent(self, store):
        record = seed(store, "the migration sometimes hangs", ["s1", "s2"], {
            "ubuntu2404.php83": {"success": 4, "failure": 3}})
        findings = contradiction.outcome_findings(record)
        assert findings[0]["verdict"] == contradiction.INCONSISTENT
        assert contradiction.contradicting_count(record) == 1

    def test_an_inconsistency_blocks_trust(self, store):
        seed(store, "the migration sometimes hangs", ["s1", "s2", "s3", "s4"], {
            "ubuntu2404.php83": {"success": 40, "failure": 30}})
        report = contradiction.validate(store)
        assert not report["promoted"]
        blocked = report["blocked"][0]
        assert "contradiction" in blocked["why"]


class TestSupersession:
    def _two_conflicting(self, store):
        seed(store, "use redis for the session store", ["s1", "s2", "s3"],
             {"php83": {"success": 9, "failure": 0}}, signature="SIG-a")
        seed(store, "stop using redis for the session store, it saturates",
             ["s4", "s5", "s6"], {"php83": {"success": 9, "failure": 0}},
             signature="SIG-b")

    def test_a_reversal_is_detected(self, store):
        self._two_conflicting(store)
        findings = [f for f in contradiction.check(store)
                    if f["verdict"] == contradiction.SUPERSEDES]
        assert findings, "a lesson proposing to stop doing what another says to do"

    def test_a_challenger_that_does_not_outscore_wins_nothing(self, store):
        seed(store, "use redis for the session store", ["s1", "s2", "s3", "s4"],
             {"php83": {"success": 20, "failure": 0}}, signature="SIG-a")
        seed(store, "stop using redis for the session store", ["s9"],
             {"php83": {"success": 0, "failure": 1}}, signature="SIG-b")

        contradiction.validate(store)
        incumbent = candidates.get(store, candidates.fingerprint(
            "use redis for the session store"))
        assert incumbent["status"] != candidates.SUPERSEDED, \
            "recency alone must not win, or learning is just forgetting with extra steps"

    def test_nothing_is_deleted_when_something_is_superseded(self, store):
        before = len(candidates.scored(store))
        self._two_conflicting(store)
        contradiction.validate(store)
        after = candidates.scored(store)
        assert len(after) >= before + 2

    def test_a_superseded_record_says_what_replaced_it(self, store):
        self._two_conflicting(store)
        report = contradiction.validate(store)
        if report["superseded"]:
            entry = report["superseded"][0]
            record = candidates.get(store, entry["superseded"])
            assert record["superseded_by"] == entry["by"]
            assert record["status"] == candidates.SUPERSEDED


class TestPromotionStopsAtTrusted:
    def test_a_strong_candidate_reaches_trusted(self, store):
        seed(store, "eager-load relationships queried in a loop", ["s1", "s2", "s3"],
             {"php83.laravel12": {"success": 12, "failure": 0}})
        report = contradiction.validate(store)
        assert report["promoted"]
        record = candidates.get(store, report["promoted"][0]["id"])
        assert record["status"] == candidates.TRUSTED

    def test_promotion_stops_at_trusted(self, store):
        """The whole safety argument. TRUSTED is a retrieval tier that compels
        nothing; PROPOSED is a governance act and is not reachable from here."""
        seed(store, "eager-load relationships queried in a loop",
             ["s1", "s2", "s3", "s4", "s5"],
             {"php83.laravel12": {"success": 40, "failure": 0}})
        contradiction.validate(store)
        statuses = {c["status"] for c in candidates.scored(store)}
        assert candidates.PROPOSED not in statuses

    def test_one_source_never_reaches_trusted_however_strong(self, store):
        seed(store, "a lesson from a single very loud source", ["only-one"],
             {"php83": {"success": 500, "failure": 0}})
        report = contradiction.validate(store)
        assert not report["promoted"]
        assert "distinct source" in report["blocked"][0]["why"]

    def test_the_refusal_says_why(self, store):
        seed(store, "a thin lesson", ["s1", "s2"], {"php83": {"success": 1, "failure": 0}})
        report = contradiction.validate(store)
        assert report["blocked"][0]["why"]

    def test_a_dry_run_writes_nothing(self, store):
        seed(store, "eager-load relationships queried in a loop", ["s1", "s2", "s3"],
             {"php83.laravel12": {"success": 12, "failure": 0}})
        report = contradiction.validate(store, apply_changes=False)
        assert report["promoted"]
        statuses = {c["status"] for c in candidates.scored(store)}
        assert candidates.TRUSTED not in statuses

    def test_check_never_writes(self, store):
        seed(store, "eager-load relationships queried in a loop", ["s1", "s2", "s3"],
             {"php83.laravel12": {"success": 12, "failure": 0}})
        before = json.dumps(candidates.scored(store), sort_keys=True, default=str)
        contradiction.check(store)
        after = json.dumps(candidates.scored(store), sort_keys=True, default=str)
        assert before == after


class TestItReusesTheDecisionLedgerRules:
    def test_the_tokenizer_is_shared(self):
        from coresentinel_core.decisions import contradiction as decisions

        assert contradiction.terms_of("Use Redis for sessions") == \
            set(decisions.tokenize("Use Redis for sessions"))

    def test_the_reversal_signals_are_shared(self):
        from coresentinel_core.decisions import contradiction as decisions

        assert contradiction.reversal_signals("stop using redis") == \
            decisions.reversal_signals("stop using redis")

    def test_one_shared_word_is_a_coincidence_not_a_conflict(self, store):
        seed(store, "use redis for sessions", ["s1", "s2"],
             {"php83": {"success": 5, "failure": 0}}, signature="SIG-a")
        seed(store, "stop using postgres for analytics", ["s3", "s4"],
             {"php83": {"success": 5, "failure": 0}}, signature="SIG-b")
        findings = [f for f in contradiction.check(store)
                    if f["verdict"] == contradiction.SUPERSEDES]
        assert not findings

    def test_vocabulary_overlap_is_not_a_conflict(self, store):
        """Run against a real store, a bare shared-term count flagged six
        unrelated pairs. A SUPERSEDES finding *acts*, so the bar is overlap,
        not coincidence."""
        seed(store, "the deployment checklist mentions the queue worker and redis",
             ["s1", "s2"], {"php83": {"success": 5, "failure": 0}}, signature="SIG-a")
        seed(store, "stop the queue worker before running migrations, unrelated to redis "
                    "caching or the deployment checklist ordering or anything else here",
             ["s3", "s4"], {"php83": {"success": 5, "failure": 0}}, signature="SIG-b")
        findings = [f for f in contradiction.check(store)
                    if f["verdict"] == contradiction.SUPERSEDES]
        assert all(f["overlap"] >= contradiction.MIN_OVERLAP_RATIO for f in findings)
