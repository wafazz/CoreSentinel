"""
Shared fixtures for the CoreSentinel self-test suite.

Isolation rules enforced here:
  * No test may read or write the real memory/ directory.
  * No test may write to the user's home directory or host config paths.
  * Tests that mutate state run against a sandbox copy of the Core in tmp_path.
"""

import json
import shutil
import subprocess
import sys
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent

# Copied into every sandbox — everything an engine needs to run standalone.
# VERSION has no extension, so it is listed explicitly rather than matched by a glob.
SANDBOX_GLOBS = ["*.py", "*.json", "*.md", "VERSION"]

# Package directories the sandboxed CLI imports. Only top-level files are matched
# by the globs above, so a package left out here fails every sandboxed command
# with an ImportError rather than the behaviour under test.
SANDBOX_PACKAGES = ["coresentinel_core"]


def load_hyphenated_module(filename, module_name):
    """Import a module whose filename is not a valid identifier (sentinel-validator.py)."""
    path = CORE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def core_dir():
    return CORE_DIR


@pytest.fixture(autouse=True)
def _core_on_path():
    """Engines import each other by bare name; make that work from any test file."""
    if str(CORE_DIR) not in sys.path:
        sys.path.insert(0, str(CORE_DIR))
    yield


@pytest.fixture(autouse=True)
def _quarantine_gate_state(tmp_path, monkeypatch):
    """Gate state is written to the Core's own memory/, so redirect it for every test.

    Individual gate tests already patch GATES_FILE. This exists because the service
    layer reaches the same writer through gate.run, and a surfaces test rewrote the
    repository's real gates.json — the isolation rule held only where somebody had
    remembered to apply it. A test that patches it itself still wins; this is the floor.
    """
    if str(CORE_DIR) not in sys.path:
        sys.path.insert(0, str(CORE_DIR))
    import coresentinel_gates as gates

    quarantined = tmp_path / "gate-state" / "gates.json"
    quarantined.parent.mkdir(parents=True, exist_ok=True)
    real = CORE_DIR / "memory" / "gates.json"
    if real.is_file():
        shutil.copy2(real, quarantined)
    monkeypatch.setattr(gates, "GATES_FILE", quarantined)
    yield


@pytest.fixture(autouse=True)
def _clear_project_root_cache():
    """Resolved project bindings are cached; no test may inherit another's.

    The cache exists because context assembly resolved the binding once per
    fact. It is keyed by directory, and a test that binds a directory a previous
    test saw as unbound would otherwise read the stale answer.
    """
    if str(CORE_DIR) not in sys.path:
        sys.path.insert(0, str(CORE_DIR))
    import coresentinel_memory as mem

    mem.reset_project_root_cache()
    yield
    mem.reset_project_root_cache()


@pytest.fixture
def sandbox(tmp_path):
    """An isolated copy of the CoreSentinel Core. Mutations here never touch the repo."""
    root = tmp_path / "core"
    root.mkdir()
    for pattern in SANDBOX_GLOBS:
        for src in CORE_DIR.glob(pattern):
            shutil.copy2(src, root / src.name)

    for package in SANDBOX_PACKAGES:
        source = CORE_DIR / package
        if source.is_dir():
            shutil.copytree(source, root / package,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    memory = root / "memory"
    memory.mkdir()
    for src in (CORE_DIR / "memory").glob("*.json"):
        shutil.copy2(src, memory / src.name)

    return root


@pytest.fixture
def run_cli(sandbox):
    """Invoke the sandboxed CLI. Returns (exit_code, stdout, stderr)."""
    def _run(*args, cwd=None):
        result = subprocess.run(
            [sys.executable, str(sandbox / "coresentinel.py"), *args],
            cwd=str(cwd or sandbox),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        return result.returncode, result.stdout, result.stderr
    return _run


@pytest.fixture
def run_cli_json(run_cli):
    """Invoke the CLI and parse its --json output, failing loudly on malformed JSON."""
    def _run(*args, cwd=None):
        code, out, err = run_cli(*args, cwd=cwd)
        try:
            return code, json.loads(out)
        except json.JSONDecodeError as exc:
            pytest.fail(f"'{' '.join(args)}' emitted unparseable JSON: {exc}\n"
                        f"stdout head: {out[:400]}\nstderr: {err[:400]}")
    return _run


@pytest.fixture
def isolated_memory(tmp_path, monkeypatch):
    """Point the memory engine at a throwaway directory for the duration of a test."""
    import coresentinel_memory as mem

    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    layers = {name: memory_dir / f"{name}.json" for name in mem.MEMORY_LAYERS}

    monkeypatch.setattr(mem, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(mem, "MEMORY_LAYERS", layers)
    return mem


@pytest.fixture
def git_repo(tmp_path):
    """A real git repository with one commit, for diff-driven engines."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")

    git("init", "-q")
    git("config", "user.email", "test@coresentinel.local")
    git("config", "user.name", "CoreSentinel Test")
    (repo / "README.md").write_text("# fixture\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "initial")

    # Path has __slots__, so the helper travels in a namespace alongside it.
    return SimpleNamespace(path=repo, git=git)


@pytest.fixture
def write_file():
    """Write a file with explicit encoding, creating parents. Returns the path."""
    def _write(path, content, encoding="utf-8"):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return path
    return _write
