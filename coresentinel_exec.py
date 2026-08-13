#!/usr/bin/env python3
"""
CoreSentinel Safe Execution Layer

Every engine used to carry its own run_cmd() — six of them, at three different
timeouts, all with shell=True and paths interpolated into the command string.
Two consequences, both observed rather than theorised:

  * a path containing a quote was a command injection surface;
  * five call sites invoked the interpreter as bare `python`, which does not
    exist on macOS or on Linux installs that ship only python3, so the Security,
    Review and Verification gates failed for a reason that had nothing to do
    with the code being checked.

Commands here are argv lists. There is no shell. Python is always sys.executable.
Every run returns an Execution — the record the verification engine turns into
evidence, so a claim can never outrun the command that supports it.
"""

import sys
import json
import shlex
import shutil
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_TIMEOUT = 120
GIT_TIMEOUT = 30
EXCERPT_LINES = 12
DIGEST_LENGTH = 12

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class Execution:
    """One command: what ran, where, for how long, and what it said.

    `exit_code` is None when the command never started. That distinction is the
    whole point — a check that could not run is UNKNOWN, never a pass.
    """

    def __init__(self, argv, cwd=None, exit_code=None, stdout="", stderr="",
                 duration_ms=0, started_at=None, error=None):
        self.argv = [str(a) for a in argv]
        self.cwd = str(cwd) if cwd else None
        self.exit_code = exit_code
        self.stdout = stdout or ""
        self.stderr = stderr or ""
        self.duration_ms = duration_ms
        self.started_at = started_at or datetime.now().strftime(TIMESTAMP_FORMAT)
        self.error = error

    @property
    def display(self):
        return " ".join(shlex.quote(a) for a in self.argv)

    @property
    def ran(self):
        return self.exit_code is not None

    @property
    def ok(self):
        return self.exit_code == 0

    @property
    def output(self):
        return "\n".join(part for part in (self.stdout, self.stderr) if part)

    @property
    def digest(self):
        if not self.ran:
            return None
        raw = self.output.encode("utf-8", "replace")
        return "sha256:" + hashlib.sha256(raw).hexdigest()[:DIGEST_LENGTH]

    @property
    def excerpt(self):
        if not self.ran:
            return None
        lines = [line for line in self.output.splitlines() if line.strip()]
        return "\n".join(lines[-EXCERPT_LINES:])

    def record(self):
        """The evidence payload. Never omits a field — a null exit code is information."""
        return {
            "command": self.display,
            "cwd": self.cwd,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
            "output_digest": self.digest,
            "output_excerpt": self.excerpt,
            "error": self.error,
        }


def resolve(program):
    """Absolute path to an executable, or None. Also how npm.cmd is found on Windows."""
    return shutil.which(str(program))


def available(program):
    return resolve(program) is not None


def run(argv, cwd=None, timeout=DEFAULT_TIMEOUT):
    """Execute an argv list. Never raises — a failure to launch is a recorded Execution."""
    argv = [str(a) for a in argv]
    started = datetime.now()
    stamp = started.strftime(TIMESTAMP_FORMAT)

    if not argv:
        return Execution(argv, cwd, error="empty command", started_at=stamp)

    if cwd is not None and not Path(cwd).is_dir():
        return Execution(argv, cwd, error=f"working directory does not exist: {cwd}",
                         started_at=stamp)

    executable = resolve(argv[0])
    if executable is None:
        return Execution(argv, cwd, error=f"command not found on PATH: {argv[0]}",
                         started_at=stamp)

    try:
        completed = subprocess.run([executable, *argv[1:]],
                                   cwd=str(cwd) if cwd else None,
                                   capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return Execution(argv, cwd, error=f"timed out after {timeout}s", started_at=stamp,
                         duration_ms=int(timeout * 1000))
    except (OSError, subprocess.SubprocessError) as e:
        return Execution(argv, cwd, error=str(e), started_at=stamp)

    duration = int((datetime.now() - started).total_seconds() * 1000)
    return Execution(argv, cwd, completed.returncode,
                     (completed.stdout or "").strip(), (completed.stderr or "").strip(),
                     duration, stamp)


def python(*args, **kwargs):
    """Run a Python script under the interpreter that is actually running CoreSentinel."""
    return run([sys.executable, *args], kwargs.get("cwd"),
               kwargs.get("timeout", DEFAULT_TIMEOUT))


def python_module(module, *args, **kwargs):
    return python("-m", module, *args, **kwargs)


def git(*args, **kwargs):
    return run(["git", *args], kwargs.get("cwd"), kwargs.get("timeout", GIT_TIMEOUT))


def is_git_repository(cwd="."):
    return git("rev-parse", "--git-dir", cwd=cwd).ok


def module_importable(module, cwd=None):
    """Whether `python -m <module>` will work, rather than whether a config file mentions it.

    A pytest.ini proves intent, not installation. Reporting a configured-but-absent
    runner as a passing test suite is the failure this whole phase exists to remove.
    """
    return python("-c", f"import {module}", cwd=cwd).ok


def run_cmd(argv, cwd=None, timeout=DEFAULT_TIMEOUT):
    """(exit_code, stdout, stderr) for engines that only need the text.

    exit_code is -1 when the command never launched, matching the tuple contract
    the engines were already written against.
    """
    result = run(argv, cwd, timeout)
    return ((result.exit_code if result.ran else -1),
            result.stdout,
            result.stderr or result.error or "")


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        print("usage: coresentinel_exec.py <command> [args...]", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(run(argv).record(), indent=2))
