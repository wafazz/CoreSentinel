"""Static review engine — diff parsing, finding severities and verdict mapping.

CORESENTINEL:SCANNER-FIXTURES — contains deliberate violation samples fed to the
review engine to prove it flags them.
"""

import pytest

import coresentinel_review as review


@pytest.fixture
def repo_with_change(git_repo):
    """Return a helper that stages a file and returns the repo path."""
    def _change(filename, content, commit=False):
        path = git_repo.path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        git_repo.git("add", "-A")
        if commit:
            git_repo.git("commit", "-q", "-m", f"add {filename}")
        return git_repo.path
    return _change


class TestDiffParsing:
    def test_added_lines_carry_correct_line_numbers(self, repo_with_change):
        repo = repo_with_change("app.js", "line one\nline two\nconsole.log('x')\nline four\n")
        findings, _, _ = review.review_diff(str(repo))

        residue = [f for f in findings if "console.log" in f["detail"]]
        assert residue, "console.log on an added line was not detected"
        assert residue[0]["line"] == 3, f"expected line 3, got {residue[0]['line']}"

    def test_untracked_files_are_reviewed(self, git_repo):
        """A brand-new file has no diff, but it is still a reviewable change."""
        (git_repo.path / "fresh.js").write_text("debugger\n", encoding="utf-8")
        findings, changed, _ = review.review_diff(str(git_repo.path))

        assert "fresh.js" in changed
        assert any("debugger" in f["detail"] for f in findings)

    def test_untracked_and_tracked_changes_are_both_covered(self, git_repo):
        (git_repo.path / "tracked.js").write_text("console.log('a')\n", encoding="utf-8")
        git_repo.git("add", "-A")
        (git_repo.path / "untracked.js").write_text("debugger\n", encoding="utf-8")

        _, changed, _ = review.review_diff(str(git_repo.path))
        assert "tracked.js" in changed and "untracked.js" in changed

    def test_preexisting_code_is_not_flagged(self, repo_with_change):
        """Only added lines are in scope — committed debt is not this pass's business."""
        repo = repo_with_change("legacy.js", "console.log('old')\n", commit=True)
        (repo / "other.js").write_text("const x = 1\n", encoding="utf-8")

        findings, _, _ = review.review_diff(str(repo))
        assert not any("console.log" in f["detail"] for f in findings)

    def test_clean_repository_yields_nothing_to_review(self, git_repo):
        findings, changed, stats = review.review_diff(str(git_repo.path))
        assert changed == []
        assert findings == []
        assert stats["changed"] == 0


class TestFindingDetection:
    @pytest.mark.parametrize("line,expected", [
        ("console.log('debug')", "console.log"),
        ("debugger", "debugger"),
        ("var_dump($user);", "debug dump"),
        ("dd($request);", "debug dump"),
    ])
    def test_debug_residue_is_flagged(self, git_repo, line, expected):
        (git_repo.path / "code.php").write_text(f"<?php\n{line}\n", encoding="utf-8")
        findings, _, _ = review.review_diff(str(git_repo.path))
        assert any(expected in f["detail"] for f in findings), f"missed residue: {line}"

    @pytest.mark.parametrize("marker", ["TODO", "FIXME", "HACK", "XXX"])
    def test_unresolved_markers_are_reported_as_info(self, git_repo, marker):
        (git_repo.path / "code.py").write_text(f"# {marker}: finish this\n", encoding="utf-8")
        findings, _, _ = review.review_diff(str(git_repo.path))

        marker_findings = [f for f in findings if marker in f["detail"]]
        assert marker_findings
        assert marker_findings[0]["severity"] == "INFO"

    def test_non_source_files_are_not_scanned_for_residue(self, git_repo):
        (git_repo.path / "notes.md").write_text("console.log('in docs')\n", encoding="utf-8")
        findings, _, _ = review.review_diff(str(git_repo.path))
        assert not any("console.log" in f["detail"] for f in findings)

    def test_scanner_files_do_not_report_their_own_patterns(self, git_repo, core_dir):
        """Copying the review engine into a repo must not produce findings from its own regexes."""
        source = (core_dir / "coresentinel_review.py").read_text(encoding="utf-8")
        (git_repo.path / "coresentinel_review.py").write_text(source, encoding="utf-8")

        findings, _, _ = review.review_diff(str(git_repo.path))
        assert not any(f["file"] == "coresentinel_review.py" for f in findings)


class TestTestCoverageRule:
    def test_source_change_without_tests_warns(self, git_repo):
        (git_repo.path / "service.py").write_text("def handler(): return 1\n", encoding="utf-8")
        findings, _, _ = review.review_diff(str(git_repo.path))

        coverage = [f for f in findings if f["rule"] == "AP-002"]
        assert coverage and coverage[0]["severity"] == "WARN"

    def test_strict_mode_promotes_missing_tests_to_blocking(self, git_repo):
        (git_repo.path / "service.py").write_text("def handler(): return 1\n", encoding="utf-8")
        findings, _, _ = review.review_diff(str(git_repo.path), strict=True)

        coverage = [f for f in findings if f["rule"] == "AP-002"]
        assert coverage and coverage[0]["severity"] == "BLOCK"

    def test_accompanying_test_change_clears_the_rule(self, git_repo):
        (git_repo.path / "service.py").write_text("def handler(): return 1\n", encoding="utf-8")
        (git_repo.path / "test_service.py").write_text("def test_handler(): assert True\n",
                                                       encoding="utf-8")
        findings, _, _ = review.review_diff(str(git_repo.path))
        assert not [f for f in findings if f["rule"] == "AP-002"]

    @pytest.mark.parametrize("test_file", ["test_service.py", "service_test.py",
                                           "service.spec.ts", "__tests__/service.js"])
    def test_recognizes_common_test_naming_conventions(self, git_repo, test_file):
        path = git_repo.path / test_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// test\n", encoding="utf-8")
        (git_repo.path / "service.py").write_text("def handler(): return 1\n", encoding="utf-8")

        findings, _, _ = review.review_diff(str(git_repo.path))
        assert not [f for f in findings if f["rule"] == "AP-002"], \
            f"{test_file} was not recognized as a test file"


class TestVerdicts:
    def test_secret_leak_blocks_the_review(self, git_repo, capsys):
        (git_repo.path / "config.py").write_text('api_key = "sk_live_a1b2c3d4e5f6g7h8"\n',
                                                 encoding="utf-8")
        exit_code = review.print_review(str(git_repo.path))
        assert exit_code == 1
        assert "CHANGES REQUIRED" in capsys.readouterr().out

    def test_clean_diff_is_approved(self, git_repo, capsys):
        (git_repo.path / "service.py").write_text("def handler(): return 1\n", encoding="utf-8")
        (git_repo.path / "test_service.py").write_text("def test_handler(): assert True\n",
                                                       encoding="utf-8")
        exit_code = review.print_review(str(git_repo.path))
        assert exit_code == 0
        assert "APPROVED" in capsys.readouterr().out

    def test_warnings_do_not_block(self, git_repo, capsys):
        (git_repo.path / "service.py").write_text("def handler(): return 1\n", encoding="utf-8")
        exit_code = review.print_review(str(git_repo.path))
        assert exit_code == 0
        assert "APPROVED WITH COMMENTS" in capsys.readouterr().out

    def test_empty_diff_reports_nothing_to_review(self, git_repo, capsys):
        assert review.print_review(str(git_repo.path)) == 0
        assert "No staged, unstaged or untracked changes" in capsys.readouterr().out
