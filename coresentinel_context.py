#!/usr/bin/env python3
"""
CoreSentinel Project Context Engine
Assembles the context pack an AI agent needs before touching a repository:
stack, frameworks, test runner, git state, entry points and recorded memory facts.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR / "memory"

FRAMEWORK_MARKERS = {
    "next": "Next.js", "react": "React", "vue": "Vue", "svelte": "Svelte",
    "angular": "Angular", "express": "Express", "nestjs": "NestJS", "fastify": "Fastify",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI", "laravel": "Laravel",
    "symfony": "Symfony", "rails": "Rails", "tailwindcss": "Tailwind CSS",
    "prisma": "Prisma", "typeorm": "TypeORM", "sqlalchemy": "SQLAlchemy",
}

KEY_FILES = ["README.md", "LICENSE", "CLAUDE.md", "AGENTS.md", "Dockerfile",
             "docker-compose.yml", ".env.example", ".github/workflows"]


def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=30)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.SubprocessError as e:
        return -1, "", str(e)


def read_json(path):
    if not Path(path).exists():
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[!] {Path(path).name} unreadable ({e}) — omitted from context pack")
        return None


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        print(f"[!] {Path(path).name} unreadable ({e}) — omitted from context pack")
        return ""


def detect_frameworks(target):
    found = []
    pkg = read_json(target / "package.json")
    if pkg:
        deps = list(pkg.get("dependencies", {})) + list(pkg.get("devDependencies", {}))
        for dep in deps:
            for marker, label in FRAMEWORK_MARKERS.items():
                if marker in dep.lower() and label not in found:
                    found.append(label)

    for filename in ["requirements.txt", "pyproject.toml", "composer.json", "Gemfile"]:
        path = target / filename
        if not path.exists():
            continue
        content = read_text(path).lower()
        for marker, label in FRAMEWORK_MARKERS.items():
            if marker in content and label not in found:
                found.append(label)

    return found


def detect_test_runner(target):
    pkg = read_json(target / "package.json")
    if pkg and pkg.get("scripts", {}).get("test"):
        return f"npm test ({pkg['scripts']['test']})"
    if (target / "pytest.ini").exists() or (target / "conftest.py").exists():
        return "pytest"
    if (target / "pyproject.toml").exists() and "pytest" in read_text(target / "pyproject.toml"):
        return "pytest"
    if (target / "phpunit.xml").exists() or (target / "phpunit.xml.dist").exists():
        return "phpunit"
    if (target / "Cargo.toml").exists():
        return "cargo test"
    if (target / "go.mod").exists():
        return "go test ./..."
    return None


def collect_memory_facts(target_dir="."):
    """Facts visible to this project: its own scoped layers plus the shared Core layers."""
    sys.path.insert(0, str(SCRIPT_DIR))
    import coresentinel_memory as mem

    facts = []
    for layer in ["project", "patterns", "longterm"]:
        path = mem.layer_path(layer, target_dir)
        data = read_json(path)
        if not data:
            continue
        for entry in data.get("facts", []):
            facts.append({
                "layer": layer,
                "scope": mem.layer_scope(layer, target_dir),
                "fact": entry.get("fact"),
                "confidence": entry.get("confidence"),
                "classification": entry.get("classification"),
                "source": entry.get("source"),
            })
    return facts


def build_project_context(target_dir="."):
    sys.path.insert(0, str(SCRIPT_DIR))
    import coresentinel_doctor as doctor

    target = Path(target_dir).resolve()

    _, branch, _ = run_cmd("git rev-parse --abbrev-ref HEAD", cwd=target_dir)
    _, commit, _ = run_cmd("git rev-parse --short HEAD", cwd=target_dir)
    _, dirty, _ = run_cmd("git status --short", cwd=target_dir)
    _, recent, _ = run_cmd("git log --oneline -5", cwd=target_dir)

    key_files = [f for f in KEY_FILES if (target / f).exists()]

    return {
        "coresentinel_api": "1.0",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project": {
            "name": target.name,
            "root": str(target),
            "stack": doctor.detect_stack(target),
            "frameworks": detect_frameworks(target),
            "test_runner": detect_test_runner(target),
            "key_files": key_files,
        },
        "git": {
            "branch": branch or None,
            "commit": commit or None,
            "uncommitted": len(dirty.splitlines()) if dirty else 0,
            "recent_commits": recent.splitlines() if recent else [],
        },
        "memory_facts": collect_memory_facts(target_dir),
    }


def print_context(target_dir=".", emit_json=False):
    ctx = build_project_context(target_dir)

    if emit_json:
        print(json.dumps(ctx, indent=2))
        return ctx

    project = ctx["project"]
    git = ctx["git"]

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Project Context Pack")
    print("=" * 64)
    print(f"  Project        : {project['name']}")
    print(f"  Root           : {project['root']}")
    print(f"  Stack          : {', '.join(project['stack'])}")
    print(f"  Frameworks     : {', '.join(project['frameworks']) or '(none detected)'}")
    print(f"  Test Runner    : {project['test_runner'] or '(none detected)'}")
    print(f"  Key Files      : {', '.join(project['key_files']) or '(none)'}")
    print("  " + "-" * 60)
    print(f"  Git Branch     : {git['branch'] or 'no repository'}")
    print(f"  Head Commit    : {git['commit'] or '-'}")
    print(f"  Uncommitted    : {git['uncommitted']} file(s)")
    if git["recent_commits"]:
        print("  Recent History :")
        for line in git["recent_commits"]:
            print(f"     • {line}")
    print("  " + "-" * 60)

    facts = ctx["memory_facts"]
    if facts:
        print(f"  Recorded Memory Facts ({len(facts)}):")
        for f in facts:
            confidence = f["confidence"]
            marker = "✓" if isinstance(confidence, (int, float)) and confidence >= 0.90 else "~"
            print(f"     [{marker}] ({f['layer']}/{f.get('scope', 'core')}) {f['fact']}")
            print(f"         confidence {confidence} · source: {f['source']}")
    else:
        print("  Recorded Memory Facts : (none — run 'coresentinel memory add')")

    print("  " + "-" * 60)
    print("  Emit machine-readable pack: coresentinel context --json")
    print("=" * 64 + "\n")
    return ctx


if __name__ == "__main__":
    print_context(".", "--json" in sys.argv)
