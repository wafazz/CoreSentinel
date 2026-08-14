"""Evidence-Based Verification Suite — evidence integrity, scoring and health signals.

CORESENTINEL:SCANNER-FIXTURES — carries a deliberate credential sample, fed to the
security check to prove a failing scan actually lowers the score.

The tests this file replaced asserted shape rather than truth: that six category
names were printed, that "/100" appeared somewhere, that dimensions averaged
correctly. All of that passed while `verify` awarded 45 of its 100 points from
checks that executed nothing, and while five of seven health dimensions were
constants. An empty directory scored 80/100 VERIFIED and 89/100 healthy.

Every test here asserts that a reported result corresponds to something that
actually ran.
"""

import json

import pytest

import coresentinel as cli
import coresentinel_evidence as evidence
import coresentinel_score as score
import coresentinel_gates as gates


SECRET_LINE = 'api_key = "sk_live_a1b2c3d4e5f6g7h8"\n'


@pytest.fixture
def empty_dir(tmp_path):
    """No code, no git repository, no tests — nothing that could evidence anything."""
    target = tmp_path / "void"
    target.mkdir()
    return target


@pytest.fixture
def dirty_repo(git_repo, write_file):
    """A repository with a staged source file that carries a hardcoded secret."""
    write_file(git_repo.path / "charge.py", SECRET_LINE)
    git_repo.git("add", "-A")
    return git_repo


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


class TestEvidenceIntegrity:
    """The defect this phase exists to remove."""

    def test_empty_directory_is_never_verified(self, empty_dir):
        """Regression, F-01.

        An empty directory scored 80/100 VERIFIED on the claim "I fixed the
        authentication vulnerability", because Linter, Dependency Audit and Diff
        Inspection returned a hardcoded PASS worth 45 points between them.
        """
        report = evidence.verify(str(empty_dir), "I fixed the authentication vulnerability")
        assert report["verdict"] == evidence.INDETERMINATE
        assert report["score"] is None

    def test_empty_directory_produces_no_passing_check(self, empty_dir):
        statuses = {c["status"] for c in evidence.collect(str(empty_dir))}
        assert evidence.PASS not in statuses, \
            "a check reported PASS where no command could possibly have run"

    def test_empty_directory_exits_indeterminate(self, empty_dir, capsys):
        code = evidence.print_verification(str(empty_dir), "claim")
        capsys.readouterr()
        assert code == 2, "INDETERMINATE must be distinguishable from a plain failure"

    def test_clean_repository_cannot_evidence_a_claim(self, git_repo):
        """A clean tree supports no claim about a change. It used to score 100/100."""
        report = evidence.verify(str(git_repo.path), "everything works")
        assert report["verdict"] == evidence.INDETERMINATE

    def test_every_passing_check_cites_a_command_or_a_basis(self, dirty_repo):
        for item in evidence.collect(str(dirty_repo.path)):
            if item["status"] != evidence.PASS:
                continue
            assert item["command"] or item["basis"], f"{item['check']} passed citing nothing"
            if item["command"]:
                assert item["exit_code"] == 0, \
                    f"{item['check']} passed while its command exited {item['exit_code']}"

    def test_executed_checks_carry_the_full_evidence_record(self, dirty_repo):
        executed = [c for c in evidence.collect(str(dirty_repo.path)) if c["command"]]
        assert executed, "the fixture should have executed at least one command"
        for item in executed:
            for field in ("check", "command", "exit_code", "duration_ms",
                          "output_digest", "status"):
                assert item[field] is not None, f"{item['check']} is missing {field}"

    def test_unknown_checks_stay_out_of_the_denominator(self, dirty_repo):
        report = evidence.verify(str(dirty_repo.path), "claim")
        scored = [c for c in report["checks"] if c["status"] in (evidence.PASS, evidence.FAIL)]
        assert report["evidence_coverage"] == sum(c["weight"] for c in scored)
        assert all(c["earned"] == 0 for c in report["checks"]
                   if c["status"] == evidence.UNKNOWN)

    def test_a_failing_check_lowers_the_score(self, dirty_repo):
        """The staged file carries a secret, so the security scan must fail."""
        report = evidence.verify(str(dirty_repo.path), "no secrets in this change")
        security = next(c for c in report["checks"] if c["id"] == "security")
        assert security["status"] == evidence.FAIL
        assert report["score"] is not None and report["score"] < 100

    def test_a_secret_in_an_untracked_file_is_still_caught(self, git_repo, write_file):
        """Regression: the scanner read only `git diff`, which cannot see a new file."""
        write_file(git_repo.path / "leak.py", SECRET_LINE)
        security = evidence.check_security(str(git_repo.path))
        assert security["status"] == evidence.FAIL

    def test_thin_evidence_cannot_produce_a_verdict(self, empty_dir, write_file):
        """One passing check out of six must not read as 100/100 VERIFIED."""
        report = evidence.verify(str(empty_dir), "claim")
        assert report["evidence_coverage"] < evidence.MIN_EVIDENCE_WEIGHT
        assert report["verdict"] == evidence.INDETERMINATE


class TestVerificationReporting:
    def test_claim_is_echoed_into_the_evidence_record(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "Authentication vulnerability fixed")
        assert "Authentication vulnerability fixed" in capsys.readouterr().out

    def test_every_evidence_category_is_reported(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "claim")
        out = capsys.readouterr().out
        for category in ["Code Change", "Security / Unit Test", "Linter",
                         "Anti-Pattern", "Dependency", "Diff"]:
            assert category in out, f"evidence category '{category}' was not collected"

    def test_coverage_is_reported_out_of_100(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "claim")
        assert "/100" in capsys.readouterr().out

    def test_json_output_is_machine_readable(self, git_repo, capsys):
        cli.run_evidence_verification(str(git_repo.path), "claim", emit_json=True)
        payload = json.loads(capsys.readouterr().out)
        assert payload["verdict"] in (evidence.VERIFIED, evidence.UNVERIFIED,
                                      evidence.INDETERMINATE)
        assert len(payload["checks"]) == len(evidence.CHECKS)

    def test_exit_code_matches_the_verdict(self):
        assert evidence.EXIT_CODE[evidence.VERIFIED] == 0
        assert evidence.EXIT_CODE[evidence.UNVERIFIED] == 1
        assert evidence.EXIT_CODE[evidence.INDETERMINATE] == 2


class TestHealthScorecard:
    def test_reports_all_seven_dimensions(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        assert set(health["dimensions"]) == {
            "Architecture", "Security", "Testing", "Code Quality",
            "Documentation", "Reliability", "Dependencies"}

    def test_overall_is_the_mean_of_evaluable_dimensions(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        known = [v for v in health["dimensions"].values() if v is not None]
        if len(known) < score.MIN_KNOWN_DIMENSIONS:
            assert health["overall_score"] is None
        else:
            assert health["overall_score"] == int(round(sum(known) / len(known)))

    def test_dimension_scores_stay_in_range_or_are_unknown(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        for name, value in health["dimensions"].items():
            assert value is None or 0 <= value <= 100, \
                f"{name} scored out of range: {value}"

    def test_unknown_dimensions_are_named_not_defaulted(self, empty_dir):
        health = score.evaluate_health_score(str(empty_dir))
        for name, value in health["dimensions"].items():
            if value is None:
                assert name in health["unknown_dimensions"]
        assert all(health["dimensions"][n] is None for n in health["unknown_dimensions"])

    def test_empty_directory_is_not_reported_healthy(self, empty_dir):
        """Regression, F-02. An empty directory scored 89/100 with Architecture 90,
        Code Quality 96, Documentation 88, Reliability 93 and Dependencies 97."""
        health = score.evaluate_health_score(str(empty_dir))
        assert health["status"] != score.HEALTHY
        assert health["overall_score"] is None or health["overall_score"] < 75

    def test_no_dimension_is_a_baseline_constant(self, empty_dir):
        """Every dimension of an empty directory must be UNKNOWN or driven to its floor."""
        health = score.evaluate_health_score(str(empty_dir))
        for name, value in health["dimensions"].items():
            assert value is None or value == 0, \
                f"{name} scored {value} on an empty directory — that is a baseline, not a measurement"

    def test_every_signal_states_its_basis(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        for name, signals in health["signals"].items():
            for item in signals:
                assert item["basis"], f"{name}/{item['signal']} reports no basis"

    def test_coverage_is_reported_per_dimension(self, git_repo):
        health = score.evaluate_health_score(str(git_repo.path))
        for name, seen in health["coverage"].items():
            assert seen["evaluated"] <= seen["total"]
            assert seen["total"] == len(health["signals"][name])

    def test_status_thresholds_come_from_the_engine(self, monkeypatch, git_repo):
        """The test this replaces reimplemented the banding inside itself and
        asserted it against its own copy — it would have passed with the engine deleted."""
        for overall, expected in ((95, score.HEALTHY), (80, score.WARNING), (60, score.CRITICAL)):
            monkeypatch.setattr(score, "score_signals", lambda signals, v=overall: v)
            health = score.evaluate_health_score(str(git_repo.path))
            assert health["overall_score"] == overall
            assert health["status"] == expected

    def test_json_emission_is_machine_readable(self, git_repo, capsys):
        score.print_scorecard(str(git_repo.path), emit_json=True)
        payload = json.loads(capsys.readouterr().out)
        assert "overall_score" in payload and "dimensions" in payload

    def test_json_stays_parseable_while_the_scanner_reports(self, dirty_repo, capsys):
        """Regression: the scanner logged to stdout, landing inside this payload."""
        score.print_scorecard(str(dirty_repo.path), emit_json=True)
        json.loads(capsys.readouterr().out)


class TestQualityGateIntegrity:
    def test_manual_gates_never_report_pass(self, tmp_path):
        """Regression, F-03. Plan, Architecture and Deployment returned PASS with no check."""
        for gate_name in gates.MANUAL_GATES:
            status, code, reason, basis = gates.evaluate_gate(gate_name, str(tmp_path))
            assert status == gates.UNKNOWN, f"{gate_name} still asserts a result it never checked"
            assert reason, f"{gate_name} gives no reason for being unknown"

    def test_no_gate_passes_on_an_empty_directory(self, empty_dir):
        for gate_name in gates.GATE_PIPELINE:
            status, _, _, _ = gates.evaluate_gate(gate_name, str(empty_dir))
            assert status != gates.PASS, \
                f"{gate_name} passed against a directory containing nothing"

    def test_implementation_gate_requires_an_actual_change(self, git_repo):
        status, _, reason, _ = gates.evaluate_gate("Implementation", str(git_repo.path))
        assert status == gates.UNKNOWN
        assert "clean" in reason.lower()

    def test_a_waiver_still_requires_a_rationale(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gates, "MEMORY_DIR", tmp_path)
        monkeypatch.setattr(gates, "GATES_FILE", tmp_path / "gates.json")
        assert gates.waive_gate("Security", "") is False
        assert gates.load_gates()["gates"]["Security"]["status"] != gates.WAIVED


@pytest.fixture
def merged_branch(git_repo, write_file):
    """A branch whose change is committed and whose working tree is clean.

    This is the shape of every CI checkout: the change exists as a commit range,
    not as a working-tree modification. Verification that only reads the tree
    sees nothing here and says so, which is honest but useless — CI is precisely
    where a change most needs evidencing.
    """
    git_repo.git("checkout", "-q", "-b", "feature")
    write_file(git_repo.path / "charge.py", "def charge():\n    return 1\n")
    git_repo.git("add", "-A")
    git_repo.git("commit", "-q", "-m", "add charge")
    assert not git_repo.git("status", "--porcelain").stdout.strip(), \
        "the fixture must leave a clean tree or it proves nothing"
    return git_repo


class TestCommittedRangeEvidence:
    """A committed change must be evidenceable. Regression for the CI stage that
    returned INDETERMINATE on every pull request because it read the tree."""

    def test_a_clean_tree_still_evidences_nothing_without_a_base(self, merged_branch):
        finding = evidence.check_code_change(str(merged_branch.path))
        assert finding["status"] == evidence.UNKNOWN
        assert "clean" in finding["detail"]

    def test_the_same_commit_is_evidence_against_its_base(self, merged_branch):
        finding = evidence.check_code_change(str(merged_branch.path), base="master")
        if finding["status"] == evidence.UNKNOWN and "cannot be resolved" in finding["detail"]:
            finding = evidence.check_code_change(str(merged_branch.path), base="main")
        assert finding["status"] == evidence.PASS, finding["detail"]
        assert "charge.py" in finding["detail"]

    def test_an_unresolvable_base_is_unknown_and_never_a_pass(self, merged_branch):
        """The dangerous failure: falling back to the clean tree would report
        'nothing changed' about a branch that changed plenty, and score it."""
        finding = evidence.check_code_change(str(merged_branch.path), base="origin/does-not-exist")
        assert finding["status"] == evidence.UNKNOWN
        assert "cannot be resolved" in finding["detail"]
        assert finding["earned"] == 0

    def test_the_report_declares_which_change_source_it_read(self, merged_branch):
        assert evidence.verify(str(merged_branch.path))["change_source"] == "working tree"
        report = evidence.verify(str(merged_branch.path), base="HEAD~1")
        assert report["change_source"] == "HEAD~1...HEAD"

    def test_a_secret_committed_on_the_branch_is_caught(self, git_repo, write_file):
        """Without a base this scan reads a clean tree, reports zero violations
        and scores 20 points for looking at nothing."""
        git_repo.git("checkout", "-q", "-b", "leaky")
        write_file(git_repo.path / "charge.py", SECRET_LINE)
        git_repo.git("add", "-A")
        git_repo.git("commit", "-q", "-m", "leak")

        finding = evidence.check_security(str(git_repo.path), base="HEAD~1")
        assert finding["status"] == evidence.FAIL, finding["detail"]
        assert finding["earned"] == 0

    def test_review_reads_the_committed_range_too(self, merged_branch):
        import coresentinel_review as review
        assert review.get_changed_files(str(merged_branch.path)) == []
        changed = review.get_changed_files(str(merged_branch.path), base="HEAD~1")
        assert "charge.py" in changed
