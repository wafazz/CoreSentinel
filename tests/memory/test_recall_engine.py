"""Recall & briefing — a fact that cannot be found again was never worth recording.

Covers the retrieval half of the memory ecosystem: ranked search across every layer,
the session journal, and the briefing an agent reads before its first action.
"""

import json
from datetime import datetime, timedelta

import pytest

import coresentinel_memory as mem
import coresentinel_recall as recall_engine


@pytest.fixture
def bound_project(tmp_path):
    project = tmp_path / "bound"
    (project / mem.CONFIG_DIRNAME).mkdir(parents=True)
    (project / mem.CONFIG_DIRNAME / "config.json").write_text(
        json.dumps({"project_name": "bound"}), encoding="utf-8")
    return project


@pytest.fixture
def stocked(isolated_memory, bound_project):
    """A project with facts spread across scoped and Core layers."""
    isolated_memory.add_fact("project", "Auth uses JWT with a 15 minute expiry", 0.95,
                             "src/auth.ts", str(bound_project))
    isolated_memory.add_fact("project", "Rate limiting is 100 requests per minute", 0.40,
                             "guessed from nginx.conf", str(bound_project))
    isolated_memory.add_fact("patterns", "Repository pattern isolates the ORM", 0.92,
                             "review", str(bound_project))
    isolated_memory.add_fact("failures", "JWT refresh loop deadlocked the worker", 0.99,
                             "INC-004", str(bound_project))
    return bound_project


class TestTokenizer:
    def test_drops_stop_words_and_single_characters(self):
        assert recall_engine.tokenize("the a is of x auth") == ["auth"]

    def test_keeps_paths_and_identifiers_intact(self):
        assert "src/auth.ts" in recall_engine.tokenize("defined in src/auth.ts")

    def test_empty_query_yields_no_terms(self):
        assert recall_engine.tokenize("") == []


class TestScoring:
    def test_a_record_with_no_matching_term_scores_zero(self):
        score, matched = recall_engine.score_record(["postgres"], "postgres", "auth uses jwt", 0.9)
        assert score == 0.0 and matched == []

    def test_full_coverage_outranks_partial_coverage(self):
        full, _ = recall_engine.score_record(["auth", "jwt"], "auth jwt", "auth uses jwt", 0.9)
        partial, _ = recall_engine.score_record(["auth", "jwt"], "auth jwt", "auth is enabled", 0.9)
        assert full > partial > 0

    def test_exact_phrase_earns_a_bonus(self):
        phrase, _ = recall_engine.score_record(["jwt", "expiry"], "jwt expiry", "the jwt expiry is 15m", 0.9)
        scattered, _ = recall_engine.score_record(["jwt", "expiry"], "jwt expiry", "expiry of the jwt", 0.9)
        assert phrase > scattered

    def test_confidence_weights_but_never_silences_a_fact(self):
        """An Unknown fact you can see is safer than one you cannot."""
        confident, _ = recall_engine.score_record(["auth"], "auth", "auth works", 1.0)
        doubtful, _ = recall_engine.score_record(["auth"], "auth", "auth works", 0.0)
        assert confident > doubtful > 0


class TestRecall:
    def test_finds_a_fact_across_layers(self, stocked):
        hits = recall_engine.recall("jwt", str(stocked))
        layers = {h["layer"] for h in hits}
        assert {"project", "failures"} <= layers

    def test_results_are_ranked_best_first(self, stocked):
        hits = recall_engine.recall("jwt", str(stocked))
        assert hits == sorted(hits, key=lambda h: h["score"], reverse=True)

    def test_unrelated_query_returns_nothing(self, stocked):
        assert recall_engine.recall("kubernetes helm chart", str(stocked)) == []

    def test_layer_filter_is_honoured(self, stocked):
        hits = recall_engine.recall("jwt", str(stocked), layers=["failures"])
        assert {h["layer"] for h in hits} == {"failures"}

    def test_minimum_confidence_excludes_weak_facts(self, stocked):
        hits = recall_engine.recall("rate limiting", str(stocked), min_confidence=0.5)
        assert not hits, "a 0.40-confidence fact must not pass a 0.5 floor"

    def test_every_hit_reports_its_scope(self, stocked):
        hits = recall_engine.recall("jwt", str(stocked))
        assert {h["scope"] for h in hits} <= {"project", "core"}
        assert all(h["scope"] for h in hits)

    def test_limit_caps_the_result_set(self, stocked):
        assert len(recall_engine.recall("jwt", str(stocked), limit=1)) == 1

    def test_searches_the_decision_ledger(self, isolated_memory, tmp_path):
        isolated_memory.ensure_memory_dir()
        isolated_memory.add_decision("Adopt PostgreSQL", "ACID guarantees needed",
                                     "PostgreSQL", "MySQL, SQLite")
        hits = recall_engine.recall("postgresql", str(tmp_path))
        assert any(h["kind"] == "decision" for h in hits)

    def test_searches_the_journal(self, stocked):
        recall_engine.add_journal_entry("Rewrote the token refresh path", tags="auth",
                                        target_dir=str(stocked))
        hits = recall_engine.recall("token refresh", str(stocked))
        assert any(h["kind"] == "journal" for h in hits)


class TestJournal:
    def test_entry_lands_in_the_project_store(self, bound_project):
        recall_engine.add_journal_entry("Shipped the migration", target_dir=str(bound_project))
        day = datetime.now().strftime("%Y-%m-%d")
        stored = bound_project / mem.CONFIG_DIRNAME / "memory" / "journal" / f"{day}.json"
        assert stored.exists()

    def test_entries_accumulate_within_a_day(self, bound_project):
        for text in ("first", "second", "third"):
            recall_engine.add_journal_entry(text, target_dir=str(bound_project))
        assert len(recall_engine.read_journal(str(bound_project))) == 3

    def test_tags_are_split_and_stored(self, bound_project):
        recall_engine.add_journal_entry("Tuned the query", tags="db, perf",
                                        target_dir=str(bound_project))
        assert recall_engine.read_journal(str(bound_project))[0]["tags"] == ["db", "perf"]

    def test_newest_entries_come_first(self, bound_project):
        old = datetime.now() - timedelta(days=3)
        recall_engine.add_journal_entry("older", target_dir=str(bound_project), now=old)
        recall_engine.add_journal_entry("newer", target_dir=str(bound_project))
        assert recall_engine.read_journal(str(bound_project))[0]["entry"] == "newer"

    def test_day_filter_excludes_older_entries(self, bound_project):
        old = datetime.now() - timedelta(days=40)
        recall_engine.add_journal_entry("ancient", target_dir=str(bound_project), now=old)
        recall_engine.add_journal_entry("today", target_dir=str(bound_project))
        entries = recall_engine.read_journal(str(bound_project), days=7)
        assert [e["entry"] for e in entries] == ["today"]

    def test_a_corrupt_day_file_is_never_overwritten(self, bound_project, capsys):
        journal = bound_project / mem.CONFIG_DIRNAME / "memory" / "journal"
        journal.mkdir(parents=True)
        day = journal / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        day.write_text("{ not json", encoding="utf-8")

        assert recall_engine.add_journal_entry("new", target_dir=str(bound_project)) is None
        assert day.read_text(encoding="utf-8") == "{ not json"
        assert "Refusing to write" in capsys.readouterr().err


class TestJournalArchive:
    def test_dry_run_moves_nothing(self, bound_project):
        old = datetime.now() - timedelta(days=60)
        recall_engine.add_journal_entry("ancient", target_dir=str(bound_project), now=old)

        report = recall_engine.archive_journal(30, str(bound_project), apply_changes=False)
        assert report["archived_days"] and not report["applied"]
        assert (bound_project / mem.CONFIG_DIRNAME / "memory" / "journal" /
                f"{old.strftime('%Y-%m-%d')}.json").exists()

    def test_apply_folds_old_days_into_a_month_file(self, bound_project):
        old = datetime.now() - timedelta(days=60)
        recall_engine.add_journal_entry("ancient", target_dir=str(bound_project), now=old)

        recall_engine.archive_journal(30, str(bound_project), apply_changes=True)
        journal = bound_project / mem.CONFIG_DIRNAME / "memory" / "journal"
        assert not (journal / f"{old.strftime('%Y-%m-%d')}.json").exists()
        assert (journal / "archive" / f"{old.strftime('%Y-%m')}.json").exists()

    def test_archived_entries_stay_readable(self, bound_project):
        """Archiving compresses the file count; it must not lose history."""
        old = datetime.now() - timedelta(days=60)
        recall_engine.add_journal_entry("ancient", target_dir=str(bound_project), now=old)
        recall_engine.archive_journal(30, str(bound_project), apply_changes=True)

        entries = recall_engine.read_journal(str(bound_project))
        assert [e["entry"] for e in entries] == ["ancient"]
        assert entries[0]["archived"] is True

    def test_recent_days_are_left_alone(self, bound_project):
        recall_engine.add_journal_entry("today", target_dir=str(bound_project))
        report = recall_engine.archive_journal(30, str(bound_project), apply_changes=True)
        assert report["archived_days"] == []


class TestBriefing:
    def test_reports_the_bound_project(self, stocked):
        brief = recall_engine.build_briefing(str(stocked))
        assert brief["scope"]["bound_project"] == str(stocked)

    def test_separates_established_facts_from_unverified_ones(self, stocked):
        brief = recall_engine.build_briefing(str(stocked))
        established = [f["fact"] for f in brief["established"]]
        unverified = [f["fact"] for f in brief["needs_verification"]]
        assert any("JWT" in f for f in established)
        assert any("Rate limiting" in f for f in unverified)
        assert not set(established) & set(unverified)

    def test_lists_stale_facts_for_re_verification(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Runs on Node 18", 0.95, "package.json",
                                 str(bound_project))
        path = isolated_memory.layer_path("project", str(bound_project))
        data = json.loads(path.read_text(encoding="utf-8"))
        aged = datetime.now() - timedelta(days=recall_engine.STALE_AFTER_DAYS + 5)
        data["facts"][0]["last_verified"] = aged.strftime(mem.TIMESTAMP_FORMAT)
        path.write_text(json.dumps(data), encoding="utf-8")

        brief = recall_engine.build_briefing(str(bound_project))
        assert [f["fact"] for f in brief["stale"]] == ["Runs on Node 18"]

    def test_a_pinned_fact_is_never_called_stale(self, isolated_memory, bound_project):
        isolated_memory.add_fact("project", "Owned by the platform team", 0.95, "CODEOWNERS",
                                 str(bound_project), pinned=True)
        path = isolated_memory.layer_path("project", str(bound_project))
        data = json.loads(path.read_text(encoding="utf-8"))
        aged = datetime.now() - timedelta(days=recall_engine.STALE_AFTER_DAYS + 200)
        data["facts"][0]["last_verified"] = aged.strftime(mem.TIMESTAMP_FORMAT)
        path.write_text(json.dumps(data), encoding="utf-8")

        assert recall_engine.build_briefing(str(bound_project))["stale"] == []

    def test_surfaces_known_failures(self, stocked):
        brief = recall_engine.build_briefing(str(stocked))
        assert any("deadlocked" in f["fact"] for f in brief["open_failures"])

    def test_counts_every_fact_layer(self, stocked):
        brief = recall_engine.build_briefing(str(stocked))
        assert set(brief["fact_counts"]) == set(mem.FACT_LAYERS)

    def test_survives_an_empty_store(self, isolated_memory, tmp_path):
        brief = recall_engine.build_briefing(str(tmp_path))
        assert brief["working"]["current_task"] == "Idle"
        assert brief["established"] == []
