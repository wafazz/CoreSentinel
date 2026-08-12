#!/usr/bin/env python3
"""
CoreSentinel Project Init Engine
Binds a project to the CoreSentinel Core: writes .coresentinel/ project config,
seeds the detected stack as project memory facts, and optionally binds an AI host.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_DIRNAME = ".coresentinel"


def run_init(target_dir=".", host=None, apply_host=False, force=False):
    sys.path.insert(0, str(SCRIPT_DIR))
    import coresentinel_context as context

    target = Path(target_dir).resolve()
    config_dir = target / CONFIG_DIRNAME
    config_file = config_dir / "config.json"

    print("\n" + "=" * 64)
    print("  🛡️  CoreSentinel Init — Bind Project to Core")
    print("=" * 64)
    print(f"  Project        : {target.name}")
    print(f"  Project Root   : {target}")
    print(f"  Core Directory : {SCRIPT_DIR}")
    print("  " + "-" * 60)

    if not target.exists():
        print(f"  [✗] Target directory does not exist: {target}")
        print("=" * 64 + "\n")
        return 1

    if config_file.exists() and not force:
        print(f"  [✗] BLOCKED — {CONFIG_DIRNAME}/config.json already exists.")
        print("      This project is already bound to CoreSentinel.")
        print("      Re-run with --force to regenerate it, or inspect with: coresentinel status")
        print("=" * 64 + "\n")
        return 1

    ctx = context.build_project_context(str(target))
    project = ctx["project"]

    print(f"  Stack Detected : {', '.join(project['stack'])}")
    print(f"  Frameworks     : {', '.join(project['frameworks']) or '(none detected)'}")
    print(f"  Test Runner    : {project['test_runner'] or '(none detected)'}")
    print("  " + "-" * 60)

    config = {
        "coresentinel_api": "1.0",
        "project_name": project["name"],
        "core_dir": str(SCRIPT_DIR),
        "initialized_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stack": project["stack"],
        "frameworks": project["frameworks"],
        "test_runner": project["test_runner"],
        "verification": {"command": "coresentinel verify", "pass_threshold": 80},
        "bound_hosts": [],
    }

    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"  [✓] Wrote {CONFIG_DIRNAME}/config.json")

    context_file = config_dir / "context.json"
    with open(context_file, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)
    print(f"  [✓] Wrote {CONFIG_DIRNAME}/context.json (project context pack)")

    seeded = seed_stack_facts(project, str(target))
    for fact in seeded:
        print(f"  [✓] Seeded project memory: {fact}")
    if not seeded:
        print("  [·] Project memory already holds the detected stack facts")
    print(f"  [·] Project memory store: {config_dir / 'memory'}")

    if host:
        import coresentinel_adapters as adapters
        print("  " + "-" * 60)
        adapter = adapters.find_adapter(host)
        if not adapter:
            print(f"  [!] Unknown host '{host}' — skipped. Run: coresentinel adapter list")
        else:
            scope = "project" if adapter.get("project_path") else "global"
            bound = adapters.sync_adapter(adapter["id"], scope, apply_host, False, str(target))
            if bound and apply_host:
                config["bound_hosts"] = [adapter["id"]]
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)

    print("  " + "-" * 60)
    print("  Next steps:")
    print("     1. coresentinel doctor     — verify all subsystems are healthy")
    print("     2. coresentinel context    — review the assembled project context")
    print("     3. coresentinel adapter sync <host> --apply   — bind your AI assistant")
    print("=" * 64 + "\n")
    return 0


def seed_stack_facts(project, target_dir):
    """Record the detected stack into the *project's* memory store, skipping facts already held.

    target_dir must be the bound project, so the facts land in its .coresentinel/memory
    rather than in the Core store shared by every repository.
    """
    import coresentinel_memory as mem

    candidates = []
    if project["stack"] and project["stack"] != ["General"]:
        candidates.append((f"{project['name']} stack: {', '.join(project['stack'])}",
                           0.95, "coresentinel init stack detection"))
    if project["frameworks"]:
        candidates.append((f"{project['name']} frameworks: {', '.join(project['frameworks'])}",
                           0.92, "dependency manifest"))
    if project["test_runner"]:
        candidates.append((f"{project['name']} test runner: {project['test_runner']}",
                           0.95, "test configuration file"))

    existing = set()
    project_layer = mem.layer_path("project", target_dir)
    if project_layer.exists():
        try:
            with open(project_layer, "r", encoding="utf-8-sig") as f:
                existing = {e.get("fact") for e in json.load(f).get("facts", [])}
        except (OSError, json.JSONDecodeError, ValueError) as e:
            print(f"  [!] Existing project memory unreadable ({e}) — seeding without dedupe")

    seeded = []
    for fact, confidence, source in candidates:
        if fact in existing:
            continue
        if mem.add_fact("project", fact, confidence, source, target_dir):
            seeded.append(fact)
    return seeded


if __name__ == "__main__":
    argv = sys.argv[1:]
    tgt = argv[0] if argv and not argv[0].startswith("--") else "."
    h = argv[argv.index("--host") + 1] if "--host" in argv else None
    sys.exit(run_init(tgt, h, "--apply" in argv, "--force" in argv))
