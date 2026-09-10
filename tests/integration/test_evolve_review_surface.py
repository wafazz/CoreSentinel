"""The `/evolve` surface in its new role.

`observe` and automatic capture handle the routine. `review` is the periodic
step back — what recurred, what disagrees, what has gone stale, what might be a
skill — and the thing it must never do is change a governance file.

`explain` is the answer to "why does CoreSentinel believe this?", and it has to
be arithmetic rather than assertion.
"""

import json

import pytest

pytestmark = pytest.mark.integration


def read_core_governance(sandbox):
    """Every governance file `apply.py` knows how to write, as bytes."""
    from coresentinel_core.learning import apply as applier

    return {name: (sandbox / name).read_bytes()
            for name in applier.SUPPORTED if (sandbox / name).is_file()}


class TestReviewChangesNoGovernanceFile:
    def test_a_dry_run_leaves_every_target_byte_identical(self, run_cli, sandbox):
        before = read_core_governance(sandbox)
        code, out, err = run_cli("evolve", "review")
        assert code == 0, err
        assert read_core_governance(sandbox) == before

    def test_applying_leaves_every_target_byte_identical(self, run_cli, sandbox):
        """--apply records promotions. It is still not a governance change."""
        before = read_core_governance(sandbox)
        code, out, err = run_cli("evolve", "review", "--apply")
        assert code == 0, err
        assert read_core_governance(sandbox) == before

    def test_it_says_so(self, run_cli):
        code, out, err = run_cli("evolve", "review")
        assert "No governance file was changed" in out

    def test_it_points_at_the_human_step(self, run_cli):
        code, out, err = run_cli("evolve", "review")
        assert "evolve propose" in out

    def test_json_reports_governance_unchanged(self, run_cli_json):
        code, report = run_cli_json("evolve", "review", "--json")
        assert code == 0
        assert report["governance_changed"] is False


class TestReviewReportsEveryCategory:
    def test_the_report_carries_each_section(self, run_cli_json):
        code, report = run_cli_json("evolve", "review", "--json")
        for key in ("experiences", "lessons", "validation", "skill_candidates", "stale"):
            assert key in report

    def test_withheld_candidates_say_why(self, run_cli_json):
        code, report = run_cli_json("evolve", "review", "--json")
        for entry in report["validation"]["blocked"]:
            assert entry["why"], f"{entry['id']} was withheld with no reason given"

    def test_a_dry_run_is_marked_as_one(self, run_cli_json):
        code, report = run_cli_json("evolve", "review", "--json")
        assert report["applied"] is False


class TestExperiences:
    def test_the_log_is_inspectable(self, run_cli):
        code, out, err = run_cli("evolve", "experiences")
        assert code == 0, err
        assert "Experience Log" in out

    def test_it_says_capture_is_automatic(self, run_cli):
        code, out, err = run_cli("evolve", "experiences")
        assert "No command records these" in out

    def test_prune_is_a_dry_run_by_default(self, run_cli_json):
        code, report = run_cli_json("evolve", "experiences", "--prune", "--json")
        assert code == 0
        assert report["applied"] is False

    def test_the_cap_can_be_given(self, run_cli_json):
        code, report = run_cli_json("evolve", "experiences", "--prune", "--max", "5", "--json")
        assert report["cap"] == 5


class TestExplain:
    def _a_candidate(self, run_cli_json):
        code, report = run_cli_json("evolve", "candidates", "--json")
        by_status = report.get("by_status", {})
        return report, sum(by_status.values())

    def test_it_refuses_without_an_id(self, run_cli):
        code, out, err = run_cli("evolve", "explain")
        assert code == 1
        assert "Which candidate" in err

    def test_an_unknown_id_is_reported_not_invented(self, run_cli):
        code, out, err = run_cli("evolve", "explain", "CAND-doesnotexist")
        assert code == 1
        assert "not found" in err

    def test_it_shows_the_arithmetic(self, run_cli, run_cli_json):
        code, report = run_cli_json("evolve", "observe", "--json")
        ids = [c["id"] for c in report.get("candidates", [])]
        if not ids:
            pytest.skip("no candidates in this sandbox to explain")
        code, out, err = run_cli("evolve", "explain", ids[0])
        assert code == 0, err
        for term in ("evidence", "success", "consistency", "recency"):
            assert term in out
        assert "repetition does not raise this" in out


class TestTheHelpMatchesTheSurface:
    def test_the_new_subcommands_are_documented(self, run_cli):
        code, out, err = run_cli("help", "evolve")
        for sub in ("experiences", "explain", "review"):
            assert f"evolve {sub}" in out

    def test_the_help_states_the_trusted_boundary(self, run_cli):
        code, out, err = run_cli("help", "evolve")
        assert "TRUSTED" in out and "PROPOSED" in out
        assert "governance act" in out
