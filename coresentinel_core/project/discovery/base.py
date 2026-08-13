"""
Discovery primitives — findings, evidence, and structured manifest readers.

v1 detected frameworks by substring-matching dependency names against a marker
table. Measured, not argued:

    a Laravel project           ->  ['Laravel', 'Symfony']
    next-auth + eslint-plugin-vue + @types/react  ->  ['Next.js', 'Vue', 'React']

Laravel depends on `symfony/console`, so *every* Laravel project reported
Symfony. `next-auth` is an auth library, `eslint-plugin-vue` is a lint plugin and
`@types/react` is a type stub — none of them mean the framework is in use.

So detection here reads **structured keys**, never raw file text, and every
finding carries the file and locator that proves it. A signal that is absent
produces nothing at all; it never produces a guess.
"""

import json
import re
from pathlib import Path

# Directories that are never the project's own source, and are large enough that
# walking them is the difference between a fast scan and a slow one.
IGNORED_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv",
                "dist", "build", "target", ".next", ".nuxt", "coverage", ".tox",
                ".pytest_cache", ".mypy_cache", ".gradle", "Pods", ".idea", ".vscode"}

# A scan is bounded: discovery must stay fast on a large repository, and a
# truncated file list is reported rather than presented as complete.
MAX_SCANNED_FILES = 20000


def finding(kind, value, evidence_file, locator=None, detail=None, confidence=0.95):
    """One detected fact plus the thing that proves it."""
    return {
        "kind": kind,
        "value": value,
        "confidence": confidence,
        "evidence": {"file": str(evidence_file), "locator": locator, "detail": detail},
    }


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def read_text(path, limit=200000):
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")[:limit]
    except OSError:
        return ""


def normalize_package(name):
    """PyPI treats '_' and '-' as equivalent and is case-insensitive."""
    return str(name or "").strip().lower().replace("_", "-")


# ---------------------------------------------------------------- manifest readers

def node_dependencies(root):
    """Every declared package name from package.json, dev and runtime alike."""
    manifest = read_json(Path(root) / "package.json")
    names = {}
    for section in ("dependencies", "devDependencies", "peerDependencies",
                    "optionalDependencies"):
        block = manifest.get(section)
        if isinstance(block, dict):
            for name, version in block.items():
                names[str(name).lower()] = {"section": section, "version": version}
    return names


def php_dependencies(root):
    manifest = read_json(Path(root) / "composer.json")
    names = {}
    for section in ("require", "require-dev"):
        block = manifest.get(section)
        if isinstance(block, dict):
            for name, version in block.items():
                names[str(name).lower()] = {"section": section, "version": version}
    return names


REQUIREMENT_SPLIT = re.compile(r"[<>=!~;\[\s]")


def python_dependencies(root):
    """requirements*.txt and the dependency tables of pyproject.toml."""
    root = Path(root)
    names = {}

    for path in sorted(root.glob("requirements*.txt")):
        for line in read_text(path).splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-r", "--", "-e", "git+")):
                continue
            name = normalize_package(REQUIREMENT_SPLIT.split(line, 1)[0])
            if name:
                names.setdefault(name, {"section": path.name, "version": line})

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = read_text(pyproject)
        for name, raw in _toml_table(text, "tool.poetry.dependencies").items():
            names.setdefault(normalize_package(name), {"section": "pyproject.toml", "version": raw})
        for name, raw in _toml_table(text, "tool.poetry.group.dev.dependencies").items():
            names.setdefault(normalize_package(name), {"section": "pyproject.toml", "version": raw})
        for entry in _toml_array(text, "dependencies"):
            name = normalize_package(REQUIREMENT_SPLIT.split(entry, 1)[0])
            if name:
                names.setdefault(name, {"section": "pyproject.toml", "version": entry})

    return names


def rust_dependencies(root):
    text = read_text(Path(root) / "Cargo.toml")
    names = {}
    for table in ("dependencies", "dev-dependencies"):
        for name, raw in _toml_table(text, table).items():
            names.setdefault(name.lower(), {"section": table, "version": raw})
    return names


GO_REQUIRE = re.compile(r"^\s*([\w.\-]+(?:/[\w.\-]+)+)\s+v[\w.\-+]+", re.M)


def go_dependencies(root):
    text = read_text(Path(root) / "go.mod")
    return {match.group(1).lower(): {"section": "go.mod", "version": None}
            for match in GO_REQUIRE.finditer(text)}


GEM_LINE = re.compile(r"^\s*gem\s+['\"]([^'\"]+)['\"]", re.M)


def ruby_dependencies(root):
    text = read_text(Path(root) / "Gemfile")
    return {match.group(1).lower(): {"section": "Gemfile", "version": None}
            for match in GEM_LINE.finditer(text)}


# ---------------------------------------------------------------- minimal TOML

# Deliberately not a TOML parser. tomllib arrived in Python 3.11 and CoreSentinel
# supports 3.9, and a dependency for one table would not earn its place. This
# reads the two shapes that actually carry dependencies and ignores everything
# else — including inline tables spanning lines, which are reported by neither
# shape and so simply do not appear.
TOML_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
TOML_PAIR = re.compile(r"^\s*([A-Za-z0-9_.\-\"']+)\s*=\s*(.+?)\s*$")


def _toml_table(text, table):
    """key = value pairs under [table], as raw strings."""
    found, inside = {}, False
    for line in str(text or "").splitlines():
        section = TOML_SECTION.match(line)
        if section:
            inside = section.group(1).strip() == table
            continue
        if not inside:
            continue
        pair = TOML_PAIR.match(line)
        if pair:
            key = pair.group(1).strip().strip("\"'")
            found[key] = pair.group(2).strip()
    return found


def _toml_array(text, key):
    """A top-level `key = [ "a", "b" ]`, possibly spanning lines."""
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*\[(.*?)\]", re.S | re.M)
    match = pattern.search(str(text or ""))
    if not match:
        return []
    return [item.strip().strip("\"'") for item in match.group(1).split(",") if item.strip()]


# ---------------------------------------------------------------- file scanning

def scan_files(root, git_first=True):
    """Repository files, cheaply. Returns (relative_paths, truncated).

    Prefers `git ls-files`: it is one process and already excludes everything
    ignored, where walking the tree opens every directory including the ones
    that make a large repository slow.
    """
    root = Path(root)

    if git_first:
        from coresentinel_core.runtime import paths as runtime_paths
        import coresentinel_exec as execution
        if runtime_paths and execution.is_git_repository(root):
            result = execution.git("ls-files", cwd=root)
            if result.ok:
                files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                return files[:MAX_SCANNED_FILES], len(files) > MAX_SCANNED_FILES

    collected = []
    for path in root.rglob("*"):
        if len(collected) >= MAX_SCANNED_FILES:
            return collected, True
        if not path.is_file():
            continue
        if IGNORED_DIRS & set(path.relative_to(root).parts):
            continue
        collected.append(str(path.relative_to(root)))
    return collected, False
