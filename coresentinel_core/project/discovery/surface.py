"""
Test and API surface detection.

Both answer "what can be verified here?", and both report nothing rather than a
guess. A project with no API specification and no routes file has an unknown API
surface — which is a useful thing to know, and quite different from having none.
"""

import re
from pathlib import Path

from coresentinel_core.project.discovery.base import (
    finding, read_json, read_text, node_dependencies, python_dependencies,
    php_dependencies, scan_files)

TEST_DEPENDENCIES = {
    "jest": "jest", "vitest": "vitest", "mocha": "mocha", "@playwright/test": "Playwright",
    "cypress": "Cypress", "ava": "AVA", "jasmine": "Jasmine",
    "pytest": "pytest", "nose2": "nose2", "tox": "tox",
    "phpunit/phpunit": "PHPUnit", "pestphp/pest": "Pest",
}

API_SPEC_FILES = ["openapi.json", "openapi.yaml", "openapi.yml", "swagger.json",
                  "swagger.yaml", "swagger.yml", "api-spec.yaml",
                  "docs/openapi.yaml", "docs/openapi.json"]

ROUTE_FILES = [
    ("routes/api.php", "Laravel API routes"),
    ("routes/web.php", "Laravel web routes"),
    ("config/routes.rb", "Rails routes"),
    ("urls.py", "Django URLconf"),
    ("app/urls.py", "Django URLconf"),
]

TEST_DIR_NAMES = {"test", "tests", "spec", "specs", "__tests__", "e2e"}
TEST_FILE_HINT = re.compile(r"(^|[/_.\-])(test|spec)([/_.\-]|$)", re.I)

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".rb", ".go",
                   ".rs", ".java", ".kt", ".cs", ".swift", ".ex", ".dart"}


def detect_test_tooling(root):
    root = Path(root)
    found, seen = [], set()

    for dependencies, manifest in ((node_dependencies(root), "package.json"),
                                   (python_dependencies(root), "python dependencies"),
                                   (php_dependencies(root), "composer.json")):
        for package, meta in dependencies.items():
            label = TEST_DEPENDENCIES.get(package)
            if label and label not in seen:
                seen.add(label)
                found.append(finding("test_tool", label, manifest,
                                     locator=f"{meta['section']}['{package}']", confidence=0.97))

    scripts = read_json(root / "package.json").get("scripts", {})
    if isinstance(scripts, dict) and scripts.get("test"):
        found.append(finding("test_command", f"npm test", "package.json",
                             locator="scripts.test", detail=scripts["test"], confidence=0.98))

    for marker, command in [("pytest.ini", "pytest"), ("conftest.py", "pytest"),
                            ("phpunit.xml", "phpunit"), ("phpunit.xml.dist", "phpunit"),
                            ("Cargo.toml", "cargo test"), ("go.mod", "go test ./...")]:
        if (root / marker).exists():
            found.append(finding("test_command", command, marker,
                                 locator="configuration present", confidence=0.95))
            break
    else:
        # A [tool.pytest.ini_options] table is pytest's own configuration and
        # means the same thing pytest.ini does. Projects that declare pytest
        # only under optional-dependencies were reported as having no runner —
        # correct by the evidence rule, but the evidence was there and unread.
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding="utf-8-sig")
            except OSError:
                text = ""
            if "[tool.pytest.ini_options]" in text:
                found.append(finding("test_command", "pytest", "pyproject.toml",
                                     locator="[tool.pytest.ini_options]", confidence=0.95))

    return found


def detect_test_layout(root, files=None):
    """Where the tests are and how many, relative to production source."""
    root = Path(root)
    if files is None:
        files, _ = scan_files(root)

    sources = [f for f in files if Path(f).suffix in SOURCE_SUFFIXES]
    tests = [f for f in sources
             if TEST_FILE_HINT.search(f) or TEST_DIR_NAMES & set(Path(f).parts)]
    production = [f for f in sources if f not in set(tests)]

    if not sources:
        return []

    directories = sorted({Path(f).parts[0] for f in tests if len(Path(f).parts) > 1})
    ratio = round(len(tests) / len(production), 2) if production else None

    found = [finding("tests", f"{len(tests)} test file(s), {len(production)} production file(s)",
                     "source tree", locator=f"{len(sources)} source files scanned",
                     detail=f"ratio {ratio}" if ratio is not None else None,
                     confidence=0.9)]
    if directories:
        found.append(finding("test_location", ", ".join(directories[:5]), "source tree",
                             locator="directories containing tests", confidence=0.9))
    return found


def detect_api_surface(root, files=None):
    root = Path(root)
    found = []

    for name in API_SPEC_FILES:
        path = root / name
        if not path.exists():
            continue
        text = read_text(path)
        # Counting path keys is a lower bound, not a parse — reported as such.
        paths = len(re.findall(r"^\s{2,4}/[\w{}/.\-]*:\s*$", text, re.M)) or \
            len(re.findall(r'"/[\w{}/.\-]*"\s*:\s*\{', text))
        found.append(finding("api_spec", name, name, locator="specification present",
                             detail=f"~{paths} path(s) declared" if paths else None,
                             confidence=0.98))

    for name, label in ROUTE_FILES:
        if (root / name).exists():
            found.append(finding("api_routes", label, name,
                                 locator="routes file present", confidence=0.95))

    if files is None:
        files, _ = scan_files(root)
    controllers = [f for f in files if "controller" in f.lower()
                   and Path(f).suffix in SOURCE_SUFFIXES]
    if controllers:
        found.append(finding("api_handlers", f"{len(controllers)} controller file(s)",
                             "source tree", locator="filename contains 'controller'",
                             detail=", ".join(sorted(controllers)[:4]), confidence=0.85))

    return found
