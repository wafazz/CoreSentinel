"""Confidence — the number, and the arithmetic that has to come with it.

A score whose inputs are not stored beside it is a number nobody can argue with,
which is worse than no number: it looks like a measurement and behaves like an
opinion. So the tests here check the breakdown as much as the total.

The other claim under test is the one the whole safety argument rests on:
repetition moves `success`, never `evidence`. If repeating counted as
corroborating, a flapping check could vote itself to TRUSTED overnight.
"""

import json

import pytest

from coresentinel_core.experience import analysis, capture
from coresentinel_core.learning import candidates, confidence
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


class TestTheTerms:
    def test_evidence_saturates_at_three_sources(self):
        assert confidence.evidence_term(1) == pytest.approx(1 / 3)
        assert confidence.evidence_term(3) == 1.0
        assert confidence.evidence_term(50) == 1.0

    def test_an_unknown_success_rate_is_not_a_verdict(self):
        """Scoring it 1.0 would make "never seen it work" read as "always works".
        Scoring it 0.5 was the other error: a term nobody measured was dragging
        every total down by half its weight. It stands aside instead."""
        assert confidence.success_term(0, 0) is confidence.INDETERMINATE

    def test_a_lesson_from_failures_alone_abstains_rather_than_scores_zero(self):
        """"This keeps breaking" is a reliable observation about a thing that
        never works. The tally counts how often the *operation* failed, so every
        failure corroborates such a lesson — reading them as a 0.0 success rate
        scored the lesson down for being true."""
        assert confidence.success_term(0, 9) is confidence.INDETERMINATE
        result = confidence.score(distinct_sources=3, successes=0, failures=9)
        assert result["confidence"] > 0.5
        assert result["indeterminate"] == ["success"]

    def test_a_real_success_rate_is_still_measured(self):
        assert confidence.success_term(9, 0) == 1.0
        assert confidence.success_term(3, 1) == 0.75
        assert confidence.success_term(0, 1) is confidence.INDETERMINATE

    def test_consistency_falls_as_evidence_disagrees(self):
        assert confidence.consistency_term(0, 10) == 1.0
        assert confidence.consistency_term(5, 10) == 0.5
        assert confidence.consistency_term(10, 10) == 0.0

    def test_recency_is_floored_not_zeroed(self):
        """An old lesson is weaker, not wrong. Zeroing it would quietly delete
        it from every retrieval."""
        assert confidence.recency_term(100000) == confidence.RECENCY_FLOOR
        assert confidence.recency_term(0) == 1.0

    def test_the_weights_sum_to_one(self):
        assert sum(confidence.WEIGHTS.values()) == pytest.approx(1.0)


class TestAnUnmeasuredTermIsNotALowScore:
    """The TRUSTED ceiling bug.

    `success` carried 0.30 and fell back to a fixed 0.5, so a candidate with no
    outcome data topped out at 0.85 against a 0.90 bar — and a failure-derived
    lesson, which is the only kind `experience/analysis.py` ever produces, topped
    out at 0.70. Nothing the system actually recorded could reach the tier it was
    being measured against. The tier looked empty because the store was young; it
    was empty because the arithmetic forbade it.
    """

    def _score(self, sources, successes=0, failures=9, contradicting=0):
        # `last_seen` is left unset on purpose, so `recency` sits at its floor
        # and these assertions do not drift with the wall clock. Trust is being
        # reached here on the *weakest* recency the engine can report.
        return confidence.score(distinct_sources=sources, successes=successes,
                                failures=failures, contradicting=contradicting,
                                total_observations=9)

    def test_a_corroborated_failure_lesson_can_now_reach_trust(self):
        scored = self._score(sources=3)
        assert scored["confidence"] >= confidence.TRUSTED_CONFIDENCE
        assert confidence.qualifies_for_trust(scored, 3) is True

    def test_the_old_ceiling_is_gone(self):
        """Before the fix this configuration maxed at 0.70, however many
        independent sources agreed and however recently they were seen."""
        assert self._score(sources=99)["confidence"] > 0.70
        assert self._score(sources=99)["confidence"] >= confidence.TRUSTED_CONFIDENCE

    def test_the_redistributed_weights_still_sum_to_one(self):
        scored = self._score(sources=3)
        assert sum(scored["weights"].values()) == pytest.approx(1.0)
        assert scored["weights"]["success"] == 0.0
        assert scored["declared_weights"] == confidence.WEIGHTS

    def test_a_measured_term_keeps_its_declared_weight(self):
        scored = self._score(sources=3, successes=9, failures=1)
        assert scored["weights"] == confidence.WEIGHTS
        assert scored["indeterminate"] == []

    def test_repetition_still_buys_nothing(self):
        """The guard the fix must not relax: one source is one source."""
        scored = self._score(sources=1, failures=200)
        assert confidence.qualifies_for_trust(scored, 1) is False

    def test_the_corroboration_floor_still_holds(self):
        scored = self._score(sources=2)
        assert confidence.qualifies_for_trust(scored, 2) is False

    def test_a_contradiction_still_blocks_trust(self):
        scored = self._score(sources=5, contradicting=3)
        assert confidence.qualifies_for_trust(scored, 5, contradicting=3) is False

    def test_explain_names_what_it_could_not_measure(self):
        text = confidence.explain(self._score(sources=3))
        assert "not measured" in text
        assert "success" in text
        assert "redistributed" in text


class TestTheArithmeticIsCarried:
    def test_the_score_returns_its_terms(self):
        result = confidence.score(distinct_sources=3, successes=7, failures=0)
        assert set(result["terms"]) == {"evidence", "success", "consistency", "recency"}
        assert result["weights"] == confidence.WEIGHTS

    def test_the_contributions_add_up_to_the_total(self):
        result = confidence.score(distinct_sources=2, successes=3, failures=1)
        assert sum(result["contributions"].values()) == pytest.approx(
            result["confidence"], abs=1e-4)

    def test_explain_shows_every_term(self):
        text = confidence.explain(confidence.score(distinct_sources=2, successes=1,
                                                   failures=1), lesson="a lesson")
        for term in ("evidence", "success", "consistency", "recency"):
            assert term in text
        assert "repetition does not raise this" in text

    def test_the_bands_match_the_memory_engine(self):
        """The same thresholds, by the same numbers. The memory engine's labels
        are longer ("Known (Empirically Verified)"); what must not diverge is
        where the boundaries fall, or 0.85 means two things in one system."""
        import coresentinel_memory as mem

        for value in (0.99, 0.95, 0.90, 0.89, 0.75, 0.50, 0.49, 0.20):
            assert mem.classify_confidence(value).startswith(confidence.band(value)), \
                f"{value} classified differently by the two engines"


class TestRepetitionMovesSuccessNotEvidence:
    def test_fifty_sightings_score_the_evidence_of_one(self, store):
        for _ in range(50):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        analysis.observe(store)
        candidate = candidates.scored(store)[0]
        # Stored terms are rounded to four places, so compare at that precision.
        assert candidate["confidence_terms"]["terms"]["evidence"] == pytest.approx(
            1 / 3, abs=1e-4)

    def test_and_cannot_reach_the_trusted_bar_alone(self, store):
        for _ in range(200):
            capture.store_experience(store, "QualityGateFailed", GATE_FAILURE)
        analysis.observe(store)
        candidate = candidates.scored(store)[0]
        assert candidate["trustworthy"] is False, \
            "a flapping check must not be able to vote itself into the advisory tier"


class TestTrustRequiresAllThree:
    def _scored(self, sources, successes=9, failures=0, contradicting=0):
        return confidence.score(distinct_sources=sources, successes=successes,
                                failures=failures, contradicting=contradicting,
                                total_observations=10)

    def test_a_high_score_from_one_reporter_is_one_reporter(self):
        scored = self._scored(sources=1)
        assert confidence.qualifies_for_trust(scored, 1) is False

    def test_an_unresolved_contradiction_blocks_trust(self):
        scored = self._scored(sources=5, contradicting=3)
        assert confidence.qualifies_for_trust(scored, 5, contradicting=3) is False

    def test_enough_agreeing_sources_qualify(self):
        scored = self._scored(sources=4)
        assert confidence.qualifies_for_trust(scored, 4) is True


class TestScopeIsEarned:
    def test_one_context_is_not_a_general_claim(self):
        assert candidates.scope_of(["php83.laravel12"]) == "project"

    def test_two_contexts_widen_it(self):
        assert candidates.scope_of(["php83.laravel12", "node20.express"]) == "global"

    def test_no_context_is_global_by_default(self):
        assert candidates.scope_of([]) == "global"


class TestBackwardCompatibility:
    def test_a_v1_record_scores_without_migration(self, store):
        """Written before confidence, context or metrics existed."""
        store.repository(candidates.COLLECTION).append({
            "id": "CAND-legacy0001",
            "lesson": "eager-load relationships queried in a loop",
            "kind": "incident",
            "status": candidates.CORROBORATED,
            "sources": ["INC-0001", "INC-0002"],
            "evidence": [{"source": "INC-0001", "kind": "incident", "detail": None,
                          "at": "2026-01-01 09:00:00"},
                         {"source": "INC-0002", "kind": "incident", "detail": None,
                          "at": "2026-01-02 09:00:00"}],
            "first_seen": "2026-01-01 09:00:00",
            "last_seen": "2026-01-02 09:00:00",
            "rejected_reason": None,
            "proposal": None,
        })
        enriched = candidates.scored(store)[0]
        assert 0.0 <= enriched["confidence"] <= 1.0
        assert enriched["scope"] == "global"
        assert enriched["superseded_by"] is None if "superseded_by" in enriched else True

    def test_observe_still_works_with_the_v1_signature(self, store):
        record = candidates.observe(store, "a lesson", source="INC-0001")
        assert record["status"] == candidates.OBSERVED
        assert "metrics" not in record["evidence"][0]

    def test_the_corroboration_rule_is_unchanged(self, store):
        candidates.observe(store, "a lesson", source="INC-0001")
        second = candidates.observe(store, "a lesson", source="INC-0002")
        assert second["status"] == candidates.CORROBORATED
        assert candidates.MIN_EVIDENCE == 2


class TestTrustedIsNotProposed:
    def test_they_are_distinct_statuses(self):
        assert candidates.TRUSTED != candidates.PROPOSED
        assert candidates.TRUSTED in candidates.ADVISORY_STATUSES
        assert candidates.PROPOSED not in candidates.ADVISORY_STATUSES

    def test_a_superseded_candidate_does_not_gather_more_evidence(self, store):
        candidates.observe(store, "a lesson", source="INC-0001")
        record = candidates.get(store, candidates.fingerprint("a lesson"))
        candidates._replace(store, {**record, "status": candidates.SUPERSEDED,
                                    "superseded_by": "CAND-newer00001"})
        again = candidates.observe(store, "a lesson", source="INC-0002")
        assert again["status"] == candidates.SUPERSEDED
        assert len(again["sources"]) == 1
