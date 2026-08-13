#!/usr/bin/env python3
"""
CoreSentinel System & Project Health Score Engine

Five of the seven dimensions used to be constants — Architecture opened at 90,
Code Quality at 96, Documentation at 88, Reliability at 93, Dependencies at 97,
adjusted by a file-existence check or two. An empty directory scored 89/100.

Every dimension here is the fraction of its named signals that are met, and every
signal states its basis: the command that produced it, or the filesystem
measurement it read. A signal that cannot be evaluated on this machine is
unavailable rather than met, and a dimension with no evaluable signals reports
UNKNOWN and leaves the mean rather than defaulting into it.

'coresentinel score --explain' prints every signal and its basis, so any number
here can be argued with.
"""

import sys
import json
import importlib.util
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import coresentinel_exec as execution

HEALTHY, WARNING, CRITICAL, INDETERMINATE = "HEALTHY", "WARNING", "CRITICAL", "INDETERMINATE"

BADGE = {HEALTHY: "[✓ HEALTHY]", WARNING: "[! WARNING]",
         CRITICAL: "[✗ CRITICAL]", INDETERMINATE: "[? INDETERMINATE]"}

# Below this many evaluable dimensions there is not enough signal to call a project
# healthy or unhealthy, and saying so is more useful than averaging two numbers.
MIN_KNOWN_DIMENSIONS = 3

MAX_MODULE_LINES = 1000
MIN_README_LINES = 40
MIN_COMMITS = 5
MIN_TEST_RATIO = 0.2

SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".rb", ".go", ".rs", ".java"}
TEST_HINTS = ("test", "spec", "__tests__")

MANIFESTS = ["package.json", "pyproject.toml", "requirements.txt", "composer.json",
             "Cargo.toml", "go.mod", "Gemfile", "pom.xml", "requirements-dev.txt"]
LOCKFILES = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
             "poetry.lock", "Pipfile.lock", "Cargo.lock", "go.sum"]
CI_PATHS = [".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml",
            "azure-pipelines.yml"]


def signal(name, basis, met, detail=""):
    return {"signal": name, "basis": basis, "met": met, "detail": detail}


def _exists(target, name):
    return (Path(target) / name).exists()


def _first_present(target, names):
    return next((n for n in names if _exists(target, n)), None)


def _tracked_files(target):
    result = execution.git("ls-files", cwd=target)
    if not result.ok or not result.stdout:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _source_files(target):
    tracked = _tracked_files(target)
    if tracked:
        return [f for f in tracked if Path(f).suffix in SOURCE_SUFFIXES]
    return [str(p.relative_to(target)) for p in Path(target).rglob("*")
            if p.is_file() and p.suffix in SOURCE_SUFFIXES and ".git" not in p.parts][:2000]


def _is_test_path(path):
    lowered = path.lower()
    return any(hint in lowered for hint in TEST_HINTS)


def _longest_module(target, sources):
    longest, longest_name = 0, None
    for name in sources:
        try:
            count = sum(1 for _ in open(Path(target) / name, "r",
                                        encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if count > longest:
            longest, longest_name = count, name
    return longest, longest_name


def _load_validator():
    path = SCRIPT_DIR / "sentinel-validator.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("sentinel_validator_score", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except (ImportError, SyntaxError):
        return None


def _changed_files(target):
    result = execution.git("status", "--porcelain", cwd=target)
    if not result.ok or not result.stdout:
        return []
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------- dimensions

def architecture_signals(target):
    sources = _source_files(target)
    longest, longest_name = _longest_module(target, sources) if sources else (0, None)
    manifest = _first_present(target, MANIFESTS)
    arch_doc = _first_present(target, ["ARCHITECTURE.md", "docs", "doc", "Planning.md"])

    return [
        signal("README present", "filesystem: README.md", _exists(target, "README.md")),
        signal("Architecture documentation present",
               "filesystem: ARCHITECTURE.md | docs/ | Planning.md",
               arch_doc is not None, arch_doc or "none found"),
        signal("Dependency manifest present", f"filesystem: {'|'.join(MANIFESTS[:4])} …",
               manifest is not None, manifest or "none found"),
        signal(f"No module exceeds {MAX_MODULE_LINES} lines",
               f"line count over {len(sources)} source file(s)",
               (longest <= MAX_MODULE_LINES) if sources else None,
               f"longest is {longest_name} at {longest} lines" if longest_name
               else "no source files found"),
    ]


def security_signals(target):
    validator = SCRIPT_DIR / "sentinel-validator.py"
    changed = _changed_files(target)

    if not validator.exists():
        scan = signal("Anti-pattern & secret scan clean", "sentinel-validator.py", None,
                      "validator missing from the Core")
    elif not execution.is_git_repository(target):
        scan = signal("Anti-pattern & secret scan clean", "sentinel-validator.py", None,
                      "not a git repository — the scanner has no change set to read")
    elif not changed:
        scan = signal("Anti-pattern & secret scan clean", "sentinel-validator.py", None,
                      "no changed files — a scan of nothing evidences nothing")
    else:
        result = execution.python(str(validator), cwd=target)
        scan = signal("Anti-pattern & secret scan clean", result.display,
                      result.ok if result.ran else None,
                      f"exit {result.exit_code}" if result.ran else (result.error or ""))

    tracked = _tracked_files(target)
    env_tracked = [f for f in tracked if Path(f).name in (".env", ".env.local", ".env.production")]

    return [
        scan,
        signal(".gitignore present", "filesystem: .gitignore", _exists(target, ".gitignore")),
        signal("No environment file committed", "git ls-files",
               len(env_tracked) == 0 if tracked else None,
               ", ".join(env_tracked) if env_tracked else "none tracked"),
    ]


def testing_signals(target):
    import coresentinel_evidence as evidence

    suite = evidence.check_tests(target)
    met = {evidence.PASS: True, evidence.FAIL: False}.get(suite["status"])

    sources = _source_files(target)
    tests = [f for f in sources if _is_test_path(f)]
    production = [f for f in sources if not _is_test_path(f)]
    ratio = (len(tests) / len(production)) if production else None

    return [
        signal("Test suite passes", suite["basis"], met, suite["detail"]),
        signal("Test files present", f"{len(sources)} source file(s) scanned",
               len(tests) > 0 if sources else None, f"{len(tests)} test file(s)"),
        signal(f"Test-to-source ratio >= {MIN_TEST_RATIO}",
               f"{len(tests)} test / {len(production)} production file(s)",
               (ratio >= MIN_TEST_RATIO) if ratio is not None else None,
               f"ratio {ratio:.2f}" if ratio is not None else "no production source files"),
    ]


def code_quality_signals(target):
    import coresentinel_evidence as evidence

    lint = evidence.check_lint(target)
    lint_met = {evidence.PASS: True, evidence.FAIL: False}.get(lint["status"])

    validator = _load_validator()
    sources = _source_files(target)
    if validator is None or not sources:
        patches = signal("No superficial patches in tracked source",
                         "sentinel-validator anti-pattern rules", None,
                         "validator unavailable" if validator is None else "no source files")
    else:
        absolute = [str(Path(target).resolve() / f) for f in sources]
        violations = validator.check_superficial_patches(absolute)
        patches = signal("No superficial patches in tracked source",
                         f"sentinel-validator anti-pattern rules over {len(sources)} file(s)",
                         len(violations) == 0,
                         f"{len(violations)} violation(s)" if violations else "none found")

    return [
        signal("Linter reports no violations", lint["basis"], lint_met, lint["detail"]),
        patches,
    ]


def documentation_signals(target):
    readme = Path(target) / "README.md"
    readme_lines = None
    if readme.exists():
        try:
            readme_lines = len([l for l in readme.read_text(encoding="utf-8-sig",
                                                            errors="replace").splitlines() if l.strip()])
        except OSError:
            readme_lines = None

    guides = _first_present(target, ["docs", "doc", "GETTING_STARTED.md", "CONTRIBUTING.md"])
    protocols = len(list(Path(target).glob("[0-9][0-9]-*.md")))

    return [
        signal("README present", "filesystem: README.md", readme.exists()),
        signal(f"README has at least {MIN_README_LINES} lines of substance",
               "line count of README.md",
               (readme_lines >= MIN_README_LINES) if readme_lines is not None else None,
               f"{readme_lines} non-blank lines" if readme_lines is not None else "unreadable"),
        signal("LICENSE present", "filesystem: LICENSE", _exists(target, "LICENSE")),
        signal("Additional documentation present",
               "filesystem: docs/ | GETTING_STARTED.md | NN-*.md",
               guides is not None or protocols > 0,
               guides or (f"{protocols} numbered protocol document(s)" if protocols else "none found")),
    ]


def reliability_signals(target):
    is_repo = execution.is_git_repository(target)
    commits = execution.git("rev-list", "--count", "HEAD", cwd=target) if is_repo else None
    count = int(commits.stdout) if commits and commits.ok and commits.stdout.isdigit() else None
    ci = _first_present(target, CI_PATHS)

    return [
        signal("Under version control", "git rev-parse --git-dir", is_repo),
        signal(f"At least {MIN_COMMITS} commits of history",
               "git rev-list --count HEAD",
               (count >= MIN_COMMITS) if count is not None else None,
               f"{count} commit(s)" if count is not None else "no history readable"),
        signal("CI pipeline configured", f"filesystem: {' | '.join(CI_PATHS[:3])} …",
               ci is not None, ci or "none found"),
    ]


def dependency_signals(target):
    import coresentinel_evidence as evidence

    lock = _first_present(target, LOCKFILES)
    audit = evidence.check_dependencies(target)
    audit_met = {evidence.PASS: True, evidence.FAIL: False}.get(audit["status"])

    return [
        signal("Lockfile committed", f"filesystem: {' | '.join(LOCKFILES[:4])} …",
               lock is not None, lock or "none found"),
        signal("Dependency audit reports no advisories", audit["basis"], audit_met, audit["detail"]),
    ]


DIMENSIONS = [
    ("Architecture", architecture_signals),
    ("Security", security_signals),
    ("Testing", testing_signals),
    ("Code Quality", code_quality_signals),
    ("Documentation", documentation_signals),
    ("Reliability", reliability_signals),
    ("Dependencies", dependency_signals),
]


def score_signals(signals):
    determinate = [s for s in signals if s["met"] is not None]
    if not determinate:
        return None
    met = sum(1 for s in determinate if s["met"])
    return int(round(met / len(determinate) * 100))


def evaluate_health_score(target_dir="."):
    dimensions, detail, coverage = {}, {}, {}
    for name, collect in DIMENSIONS:
        signals = collect(target_dir)
        detail[name] = signals
        dimensions[name] = score_signals(signals)
        coverage[name] = {"evaluated": sum(1 for s in signals if s["met"] is not None),
                          "total": len(signals)}

    known = [v for v in dimensions.values() if v is not None]

    if len(known) < MIN_KNOWN_DIMENSIONS:
        overall, status = None, INDETERMINATE
    else:
        overall = int(round(sum(known) / len(known)))
        status = HEALTHY if overall >= 90 else (WARNING if overall >= 75 else CRITICAL)

    return {
        "coresentinel_api": "1.1",
        "target": str(Path(target_dir).resolve()),
        "overall_score": overall,
        "status": status,
        "badge": BADGE[status],
        "dimensions": dimensions,
        "coverage": coverage,
        "known_dimensions": len(known),
        "unknown_dimensions": [n for n, v in dimensions.items() if v is None],
        "signals": detail,
    }


def print_scorecard(target_dir=".", emit_json=False, explain=False):
    health = evaluate_health_score(target_dir)

    if emit_json:
        print(json.dumps(health, indent=2))
        return 0

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel System & Project Health Scorecard")
    print("=" * 64)
    print(f"  Target Directory : {health['target']}")
    print("  " + "-" * 60)

    for name, value in health["dimensions"].items():
        seen = health["coverage"][name]
        # A dimension scored on a subset of its signals says so on the same line —
        # "Testing 100/100" while the suite never ran is exactly the impression
        # this engine exists to stop giving.
        partial = ("" if seen["evaluated"] == seen["total"]
                   else f"  ({seen['evaluated']} of {seen['total']} signals)")
        if value is None:
            print(f"  {name:<18} :  n/a       [{'·' * 20}]  UNKNOWN")
        else:
            filled = int(value / 5)
            bar = "█" * filled + "░" * (20 - filled)
            print(f"  {name:<18} : {value:>3}/100  [{bar}]{partial}")
        if explain:
            for item in health["signals"][name]:
                mark = "✓" if item["met"] else ("·" if item["met"] is None else "✗")
                print(f"      [{mark}] {item['signal']}")
                print(f"          basis: {item['basis']}"
                      + (f" — {item['detail']}" if item["detail"] else ""))

    print("  " + "-" * 60)
    if health["overall_score"] is None:
        print(f"  Overall Score      : n/a — only {health['known_dimensions']} dimension(s) "
              f"could be evaluated, {MIN_KNOWN_DIMENSIONS} required")
    else:
        print(f"  Overall Score      : {health['overall_score']}/100 "
              f"(mean of {health['known_dimensions']} evaluable dimension(s))")
    if health["unknown_dimensions"]:
        print(f"  Not Evaluable      : {', '.join(health['unknown_dimensions'])}")
    print(f"  CoreSentinel Status: {health['status']} {health['badge']}")
    if not explain:
        print("  " + "-" * 60)
        print("  Show the basis for every number: coresentinel score --explain")
    print("=" * 64 + "\n")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    target = argv[0] if argv and not argv[0].startswith("-") else "."
    print_scorecard(target, "--json" in argv, "--explain" in argv)
