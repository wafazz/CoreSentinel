"""Telemetry — session log parsing must count tokens once and attribute files correctly."""

import json

import pytest

from conftest import load_hyphenated_module


@pytest.fixture(scope="module")
def stats():
    return load_hyphenated_module("agent-stats.py", "agent_stats")


def write_session(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


class TestUsageExtraction:
    def test_finds_usage_at_any_depth(self, stats):
        record = {"message": {"usage": {"input_tokens": 100, "output_tokens": 50}}}
        assert stats.first_usage(record)["input_tokens"] == 100

    def test_takes_the_shallowest_usage_block(self, stats):
        """Some tools embed a cumulative total deeper in the record — counting both double-counts."""
        record = {
            "usage": {"input_tokens": 10},
            "nested": {"deeper": {"usage": {"input_tokens": 9999}}},
        }
        assert stats.first_usage(record)["input_tokens"] == 10

    def test_returns_none_when_no_usage_present(self, stats):
        assert stats.first_usage({"type": "user", "text": "hello"}) is None

    def test_tolerates_deeply_nested_records(self, stats):
        record = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"usage": {"input_tokens": 1}}}}}}}}}
        stats.first_usage(record)

    @pytest.mark.parametrize("key", ["input_tokens", "prompt_tokens", "promptTokenCount"])
    def test_recognizes_each_vendor_token_key(self, stats, key):
        assert stats.first_usage({"usage": {key: 42}}) is not None

    def test_num_falls_back_across_vendor_keys(self, stats):
        assert stats.num({"prompt_tokens": 7}, "input_tokens", "prompt_tokens") == 7
        assert stats.num({}, "input_tokens", "prompt_tokens") == 0

    def test_num_ignores_non_numeric_values(self, stats):
        assert stats.num({"input_tokens": "lots"}, "input_tokens") == 0


class TestSessionParsing:
    def test_accumulates_tokens_across_records(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "assistant", "usage": {"input_tokens": 100, "output_tokens": 20}},
            {"type": "assistant", "usage": {"input_tokens": 50, "output_tokens": 10}},
        ])
        totals = stats.parse_session(str(session))
        assert totals["input_tokens"] == 150
        assert totals["output_tokens"] == 30

    def test_counts_user_and_assistant_messages(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "user"}, {"type": "assistant"}, {"type": "user"},
        ])
        totals = stats.parse_session(str(session))
        assert totals["messages"] == 3
        assert totals["user_messages"] == 2

    def test_attributes_files_to_read_and_edit(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "assistant", "content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/app/a.py"}},
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/app/b.py"}},
            ]},
        ])
        totals = stats.parse_session(str(session))
        assert totals["files_read_count"] == 1
        assert totals["files_edited_count"] == 1
        assert "/app/b.py" in totals["files_edited_list"]
        assert totals["tool_calls"] == 2

    def test_deduplicates_repeated_file_touches(self, stats, tmp_path):
        """Editing one file twice is one hot file, not two."""
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "assistant", "content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/app/a.py"}},
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/app/a.py"}},
            ]},
        ])
        assert stats.parse_session(str(session))["files_edited_count"] == 1

    def test_session_duration_is_derived_from_timestamps(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "user", "timestamp": "2026-08-12T10:00:00Z"},
            {"type": "assistant", "timestamp": "2026-08-12T10:30:00Z"},
        ])
        assert stats.parse_session(str(session))["duration_min"] == 30

    def test_unparseable_timestamps_do_not_crash(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "user", "timestamp": "not-a-timestamp"},
            {"type": "assistant", "timestamp": "also-not-one"},
        ])
        assert stats.parse_session(str(session))["duration_min"] == 0

    def test_malformed_lines_are_skipped_not_fatal(self, stats, tmp_path):
        session = tmp_path / "s.jsonl"
        session.write_text('{"type": "user"}\nnot json at all\n\n{"type": "assistant"}\n',
                           encoding="utf-8")
        assert stats.parse_session(str(session))["messages"] == 2

    def test_missing_file_reports_a_read_error(self, stats, tmp_path):
        totals = stats.parse_session(str(tmp_path / "absent.jsonl"))
        assert "read_error" in totals

    def test_captures_working_directory(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [{"type": "user", "cwd": "/home/project"}])
        assert stats.parse_session(str(session))["cwd"] == "/home/project"


class TestAggregation:
    @pytest.fixture
    def session_data(self, stats, tmp_path):
        session = write_session(tmp_path / "s.jsonl", [
            {"type": "user", "timestamp": "2026-08-12T10:00:00Z"},
            {"type": "assistant", "timestamp": "2026-08-12T10:05:00Z",
             "usage": {"input_tokens": 100, "output_tokens": 20},
             "content": [{"type": "tool_use", "name": "Edit",
                          "input": {"file_path": "/app/a.py"}}]},
        ])
        return stats.parse_session(str(session))

    def test_blank_stats_start_at_zero(self, stats):
        blank = stats.blank_stats()
        assert blank["total_input_tokens"] == 0
        assert blank["session_count"] == 0
        assert blank["sessions"] == []

    def test_accumulate_sums_one_session(self, stats, session_data):
        total = stats.blank_stats()
        stats.accumulate(total, session_data)

        assert total["total_input_tokens"] == 100
        assert total["total_output_tokens"] == 20
        assert total["session_count"] == 1
        assert total["total_files_edited"] == 1

    def test_accumulate_is_additive(self, stats, session_data):
        total = stats.blank_stats()
        stats.accumulate(total, session_data)
        stats.accumulate(total, session_data)

        assert total["total_input_tokens"] == 200
        assert total["session_count"] == 2

    def test_hot_files_are_ranked_by_touch_count(self, stats, session_data):
        total = stats.blank_stats()
        stats.accumulate(total, session_data)
        stats.accumulate(total, session_data)
        assert total["hot_files"]["a.py"] == 2

    def test_formats_large_numbers_readably(self, stats):
        assert stats.fmt(1500) != "1500", "large token counts should be humanized"

    def test_duration_formatting_handles_hours(self, stats):
        assert stats.dur(125)


class TestProjectLabels:
    def test_derives_a_readable_label(self, stats):
        assert stats.auto_label("my-project-name") == "My Project Name"

    def test_underscores_are_normalized(self, stats):
        assert stats.auto_label("my_project") == "My Project"

    def test_empty_input_does_not_crash(self, stats):
        stats.auto_label("")
