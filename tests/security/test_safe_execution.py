"""Safe command execution — no shell, no assumed interpreter, no silent failure.

Six engines each carried their own run_cmd() built on shell=True with paths
interpolated into the command string. Two things followed, both observed rather
than theorised:

  * a path containing shell metacharacters was an injection surface;
  * five call sites invoked the interpreter as bare `python`, which is absent on
    macOS and on Linux installs that ship only python3, so the Security, Review
    and Verification gates failed for a reason unrelated to the code under test.

These tests hold both doors shut.
"""

import ast
import sys
from pathlib import Path

import pytest

import coresentinel_exec as execution


ENGINE_GLOB = "coresentinel*.py"


def engine_sources(core_dir):
    return sorted(Path(core_dir).glob(ENGINE_GLOB)) + [Path(core_dir) / "sentinel-validator.py"]


def parsed(path):
    return ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path))


class TestNoShellExecution:
    def test_no_engine_passes_shell_true(self, core_dir):
        """Regression, F-06. shell=True plus an interpolated path is command injection."""
        offenders = []
        for path in engine_sources(core_dir):
            for node in ast.walk(parsed(path)):
                if not isinstance(node, ast.Call):
                    continue
                for keyword in node.keywords:
                    if keyword.arg == "shell" and \
                            isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        offenders.append(f"{path.name}:{node.lineno}")
        assert not offenders, f"shell=True found at {', '.join(offenders)}"

    def test_arguments_containing_shell_metacharacters_are_literal(self):
        result = execution.run([sys.executable, "-c",
                                "import sys; print(sys.argv[1])", "; echo pwned"])
        assert result.ok
        assert result.stdout == "; echo pwned", \
            "an argument was interpreted by a shell instead of passed through"

    def test_a_path_with_metacharacters_is_not_split(self, tmp_path):
        awkward = tmp_path / "a;b&c d"
        awkward.mkdir()
        result = execution.run([sys.executable, "-c",
                                "import sys; print(sys.argv[1])", str(awkward)])
        assert result.stdout == str(awkward)


class TestInterpreterResolution:
    def test_no_engine_invokes_a_bare_interpreter(self, core_dir):
        """Regression, F-04. `python` does not exist on macOS or on python3-only Linux."""
        offenders = []
        for path in engine_sources(core_dir):
            tree = parsed(path)
            # "python" as a mapping key is a label, not a command line.
            keys = {id(k) for node in ast.walk(tree) if isinstance(node, ast.Dict)
                    for k in node.keys if k is not None}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if id(node) in keys:
                    continue
                text = node.value
                # A command line names a script; a long string is prose.
                if len(text) > 120 or " " not in text:
                    continue
                if text.split(" ")[0] in ("python", "python3", "py"):
                    offenders.append(f"{path.name}:{node.lineno} -> {text[:40]!r}")
        assert not offenders, f"bare interpreter command found at {', '.join(offenders)}"

    def test_python_helper_uses_the_running_interpreter(self):
        result = execution.python("-c", "import sys; print(sys.executable)")
        assert result.ok
        assert result.stdout == sys.executable

    def test_module_importable_reports_absence_rather_than_guessing(self):
        assert execution.module_importable("json") is True
        assert execution.module_importable("a_module_that_does_not_exist_anywhere") is False


class TestExecutionRecord:
    def test_a_successful_run_is_marked_as_having_run(self):
        result = execution.run([sys.executable, "-c", "print('ok')"])
        assert result.ran and result.ok and result.exit_code == 0
        assert result.stdout == "ok"

    def test_a_nonzero_exit_is_recorded_not_swallowed(self):
        result = execution.run([sys.executable, "-c", "import sys; sys.exit(3)"])
        assert result.ran and not result.ok and result.exit_code == 3

    def test_a_missing_command_never_ran(self):
        result = execution.run(["a-command-that-is-not-installed-anywhere"])
        assert not result.ran, "a command that does not exist must not report an exit code"
        assert result.exit_code is None
        assert "not found" in (result.error or "")

    def test_a_missing_working_directory_is_reported_not_raised(self, tmp_path):
        result = execution.run([sys.executable, "-c", "print(1)"], cwd=tmp_path / "nope")
        assert not result.ran
        assert "working directory" in (result.error or "")

    def test_a_timeout_is_recorded_as_not_having_run(self):
        result = execution.run([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
        assert not result.ran
        assert "timed out" in (result.error or "")

    def test_the_record_carries_every_evidence_field(self):
        record = execution.run([sys.executable, "-c", "print('x')"]).record()
        for field in ("command", "cwd", "started_at", "duration_ms",
                      "exit_code", "output_digest", "output_excerpt", "error"):
            assert field in record

    def test_digest_is_absent_when_nothing_ran(self):
        record = execution.run(["a-command-that-is-not-installed-anywhere"]).record()
        assert record["output_digest"] is None
        assert record["output_excerpt"] is None

    def test_digest_is_stable_for_identical_output(self):
        first = execution.run([sys.executable, "-c", "print('same')"])
        second = execution.run([sys.executable, "-c", "print('same')"])
        assert first.digest == second.digest

    def test_excerpt_is_bounded(self):
        result = execution.run([sys.executable, "-c",
                                "print('\\n'.join(str(n) for n in range(500)))"])
        assert len(result.excerpt.splitlines()) <= execution.EXCERPT_LINES

    @pytest.mark.parametrize("argv", [[], [""]])
    def test_a_degenerate_command_is_rejected_cleanly(self, argv):
        result = execution.run(argv)
        assert not result.ran and result.error


class TestCoreSentinelObeysItsOwnRules:
    """The scanner is pointed at the shipped source, not only at user projects.

    Caught for real: Container.shutdown() swallowed every close() failure silently,
    which is AP-001 at STRICT_BLOCK — the exact rule CoreSentinel refuses to let a
    user commit. It now collects the failures and hands them to the caller to log.
    """

    def test_no_shipped_source_trips_the_anti_pattern_scanner(self, core_dir):
        from tests.conftest import load_hyphenated_module
        validator = load_hyphenated_module("sentinel-validator.py", "sentinel_validator_selfcheck")

        sources = [str(p) for p in sorted(Path(core_dir).glob("*.py"))]
        sources += [str(p) for p in sorted(Path(core_dir).glob("coresentinel_core/**/*.py"))]

        violations = validator.check_superficial_patches(sources)
        assert not violations, "shipped source violates a rule CoreSentinel enforces: " + \
            "; ".join(f"{Path(p).name}: {d}" for p, d in violations)

    def test_no_shipped_source_carries_a_credential(self, core_dir):
        from tests.conftest import load_hyphenated_module
        validator = load_hyphenated_module("sentinel-validator.py", "sentinel_validator_selfcheck")

        sources = [str(p) for p in sorted(Path(core_dir).glob("*.py"))]
        sources += [str(p) for p in sorted(Path(core_dir).glob("coresentinel_core/**/*.py"))]

        assert not validator.check_secrets_and_security(sources)


class TestGitHelpers:
    def test_detects_a_repository(self, git_repo):
        assert execution.is_git_repository(str(git_repo.path)) is True

    def test_reports_a_non_repository_without_raising(self, tmp_path):
        assert execution.is_git_repository(str(tmp_path)) is False

    def test_run_cmd_tuple_contract_is_preserved(self):
        code, out, err = execution.run_cmd([sys.executable, "-c", "print('t')"])
        assert (code, out) == (0, "t") and err == ""

    def test_run_cmd_reports_minus_one_when_nothing_launched(self):
        code, out, err = execution.run_cmd(["a-command-that-is-not-installed-anywhere"])
        assert code == -1 and err
