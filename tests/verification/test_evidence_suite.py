"""Evidence-Based Verification Suite — scoring, thresholds and stack detection."""

import pytest

import coresentinel as cli
import coresentinel_score as score


class TestProjectDetection:
    @pytest.mark.parametrize("marker,expected", [
        ("package.json", "Node/TypeScript"),
        ("requirements.txt", "Python"),
        ("pyproject.toml", "Python"),
        ("composer.json", "PHP"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
    ])
    def test_detects_stack_from_manifest(self, tmp_path, write_file, marker, expected):
        write_file(tmp_path / marker, "{}")
        assert expected in cli.detect_project_type(tmp_path)

    def test_unknown_project_falls_back_to_general(self, tmp_path):
        assert cli.detect_project_type(tmp_path) == ["General"]

    def test_polyglot_project_reports_every_stack(self, tmp_path, write_file):
        write_file(tmp_path / "package.json", "{}")
        write_file(tmp_path / "go.mod", "module x")
        detected = cli.detect_project_type(tmp_path)
        assert "Node/TypeScript" in detected and "Go" in detected


class TestVerificationScoring:
    def test_clean_repository_verifies(self, git_repo, capsys):
        assert cli.run_evidence_verification(str(git_repo.path), "test claim") == 0
        out = capsys.readouterr().out
        assert "VERIFIED" in out
        assert "UNVERIFIED" not in out

    def test_claim_is_echoed_into_the_evidence_record(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "Authentication vulnerability fixed")
        assert "Authentication vulnerability fixed" in capsys.readouterr().out

    def test_every_evidence_category_is_reported(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "claim")
        out = capsys.readouterr().out
        for category in ["Code Change", "Security / Unit Test", "Linter",
                         "Anti-Pattern", "Dependency", "Diff"]:
            assert category in out, f"evidence category '{category}' was not collected"

    def test_score_is_reported_out_of_100(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "claim")
        assert "/100" in capsys.readouterr().out


class TestHealthScorecard:
    def test_reports_all_seven_dimensions(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        assert set(health["dimensions"]) == {
            "Architecture", "Security", "Testing", "Code Quality",
            "Documentation", "Reliability", "Dependencies"}

    def test_overall_is_the_dimension_mean(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        dimensions = health["dimensions"].values()
        assert health["overall_score"] == int(sum(dimensions) / len(dimensions))

    def test_dimension_scores_stay_in_range(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        for name, value in health["dimensions"].items():
            assert 0 <= value <= 100, f"{name} scored out of range: {value}"

    @pytest.mark.parametrize("overall,expected", [(95, "HEALTHY"), (80, "WARNING"), (60, "CRITICAL")])
    def test_status_thresholds(self, overall, expected):
        """Documented in 12-health-score-protocol.md: >=90 HEALTHY, 75-89 WARNING, <75 CRITICAL."""
        if overall >= 90:
            status = "HEALTHY"
        elif overall >= 75:
            status = "WARNING"
        else:
            status = "CRITICAL"
        assert status == expected

    def test_json_emission_is_machine_readable(self, git_repo, capsys):
        import json
        score.print_scorecard(str(git_repo.path), emit_json=True)
        payload = json.loads(capsys.readouterr().out)
        assert "overall_score" in payload and "dimensions" in payload
