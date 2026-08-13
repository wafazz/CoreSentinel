"""
Project discovery — every detector, one pass, one report.

The contract every detector keeps: a finding names the file and locator that
proves it, and an absent signal produces nothing. `inspect()` turns "produced
nothing" into an explicit `unknown` for that dimension, because there is a real
difference between a project with no database and a project whose database we
could not determine — and only one of them is safe to act on.
"""

import time
from pathlib import Path
from datetime import datetime

from coresentinel_core.project.discovery import base, stack, infrastructure, surface

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

UNKNOWN = "unknown"

# dimension -> the finding kinds that populate it.
DIMENSIONS = [
    ("languages", ["language"]),
    ("runtimes", ["runtime"]),
    ("package_managers", ["package_manager"]),
    ("frameworks", ["framework"]),
    ("datastores", ["datastore"]),
    ("containers", ["container"]),
    ("ci", ["ci"]),
    ("environment", ["environment"]),
    ("testing", ["test_tool", "test_command", "tests", "test_location"]),
    ("api", ["api_spec", "api_routes", "api_handlers"]),
]


def collect(root="."):
    """Every finding, unsorted. Cheap: manifests are read, the tree is walked once."""
    root = Path(root).resolve()
    files, truncated = base.scan_files(root)

    findings = []
    findings += stack.detect_languages(root, files)
    findings += stack.detect_runtime_versions(root)
    findings += stack.detect_package_managers(root)
    findings += stack.detect_frameworks(root)
    findings += infrastructure.detect_databases(root)
    findings += infrastructure.detect_containers(root)
    findings += infrastructure.detect_ci(root)
    findings += infrastructure.detect_environment(root)
    findings += surface.detect_test_tooling(root)
    findings += surface.detect_test_layout(root, files)
    findings += surface.detect_api_surface(root, files)
    return findings, files, truncated


def inspect(root="."):
    """The project as CoreSentinel understands it, with evidence for every claim."""
    started = time.perf_counter()
    root = Path(root).resolve()
    findings, files, truncated = collect(root)

    by_kind = {}
    for item in findings:
        by_kind.setdefault(item["kind"], []).append(item)

    dimensions = {}
    for name, kinds in DIMENSIONS:
        collected = [item for kind in kinds for item in by_kind.get(kind, [])]
        # One value may be evidenced twice (a manifest and a config file); the
        # summary shows it once, while every finding is kept for --verbose.
        dimensions[name] = {
            "values": list(dict.fromkeys(item["value"] for item in collected)),
            "findings": collected,
            "known": bool(collected),
        }

    return {
        "coresentinel_api": "1.1",
        "generated_at": datetime.now().strftime(TIMESTAMP_FORMAT),
        "project": {"name": root.name, "root": str(root)},
        "dimensions": dimensions,
        "unknown_dimensions": [name for name, detail in dimensions.items()
                               if not detail["known"]],
        "scanned_files": len(files),
        "scan_truncated": truncated,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "finding_count": len(findings),
    }


def summary(report):
    """One line per dimension, `unknown` where nothing was evidenced."""
    return {name: ", ".join(detail["values"]) if detail["known"] else UNKNOWN
            for name, detail in report["dimensions"].items()}


def render(report, verbose=False):
    lines = ["", "=" * 64,
             f"  🧠 CoreSentinel Project Brain — {report['project']['name']}",
             "=" * 64,
             f"  Root          : {report['project']['root']}",
             f"  Scanned       : {report['scanned_files']} file(s) in {report['duration_ms']} ms"
             + ("  (truncated)" if report["scan_truncated"] else ""),
             "  " + "-" * 60]

    for name, detail in report["dimensions"].items():
        label = name.replace("_", " ").title()
        if not detail["known"]:
            lines.append(f"  {label:<18}: {UNKNOWN}")
            continue
        lines.append(f"  {label:<18}: {', '.join(detail['values'])}")
        if verbose:
            for item in detail["findings"]:
                evidence = item["evidence"]
                suffix = f" — {evidence['detail']}" if evidence.get("detail") else ""
                lines.append(f"      └─ {item['value']}: {evidence['file']}"
                             f" ({evidence['locator']}){suffix}")

    lines.append("  " + "-" * 60)
    if report["unknown_dimensions"]:
        lines.append(f"  Not evidenced : {', '.join(report['unknown_dimensions'])}")
        lines.append("  An unknown dimension is not an empty one — nothing proved it either way.")
    if not verbose:
        lines.append("  Show the evidence for every value: coresentinel project inspect --verbose")
    lines.append("=" * 64)
    return "\n".join(lines)
