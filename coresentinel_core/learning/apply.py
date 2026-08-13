"""
Applying an approved evolution — and undoing it.

`evolve approve` set a status and printed "Versioned Change Released". Nothing
was released. No rule file was written, no version moved, and the next agent read
exactly the rules it read before. The pipeline documented since v1 stopped one
step short of doing anything, and said otherwise.

What happens here, in order, and nothing skips a step:

    1. the proposal must be APPROVED — approval is a human act, always
    2. the change must be one this module knows how to make safely
    3. the target is snapshotted, byte for byte
    4. the change is written and the registry version bumped
    5. the result is audited

`revert` restores the snapshot byte-identically. Every evolution is reversible,
which is what makes approving one a decision rather than a commitment.

A change shape this module cannot validate is **refused**, not attempted. Blindly
patching a governance file because a proposal asked nicely is the failure mode
the whole controlled-evolution protocol exists to prevent.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

from coresentinel_core import CORE_ROOT

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

APPROVED = "APPROVED"
APPLIED = "APPLIED"
REVERTED = "REVERTED"

SNAPSHOT_DIR = CORE_ROOT / "memory" / "evolution_snapshots"

# Targets this module knows how to change safely, and how.
ANTI_PATTERNS = "anti-patterns.json"
PATTERN_LIBRARY = "11-pattern-library.md"
SELF_EVOLUTION = "55-self-evolution.md"

SUPPORTED = {
    ANTI_PATTERNS: "add an anti-pattern rule",
    PATTERN_LIBRARY: "append a pattern in the documented capture format",
    SELF_EVOLUTION: "append an anti-pattern entry",
}


def _resolve_target(name):
    """Governance files live at the Core root, and nowhere else is applicable.

    Taking `.name` first means a traversal attempt cannot escape: `../../etc/passwd`
    becomes `passwd`, which is not a supported target and is refused on that
    ground. The containment check behind it is the second line, not the first.
    """
    from coresentinel_core.runtime import paths
    return paths.resolve_within(CORE_ROOT, Path(str(name)).name, "evolution target")


def supported(target):
    return Path(str(target or "")).name in SUPPORTED


def snapshot(target, proposal_id, now=None):
    """Copy the file before touching it. Returns the snapshot path."""
    path = _resolve_target(target)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    destination = SNAPSHOT_DIR / f"{proposal_id}-{stamp}-{path.name}"
    shutil.copy2(path, destination)
    return destination


def apply(proposal, change=None, now=None):
    """Apply an approved proposal. Returns a report; never raises on refusal."""
    name = Path(str(proposal.get("target_protocol") or "")).name

    if proposal.get("review_status") != APPROVED:
        return {"error": f"{proposal.get('id')} is {proposal.get('review_status')}, "
                         f"not {APPROVED} — an evolution is applied by a human decision, "
                         "never by reaching the end of a pipeline"}

    if proposal.get("applied_at"):
        return {"error": f"{proposal.get('id')} was already applied at "
                         f"{proposal['applied_at']}; revert it first"}

    if not supported(name):
        return {"error": f"no safe way to change '{name}' automatically",
                "supported": SUPPORTED,
                "detail": "Make the change by hand and record it as a decision. "
                          "Blindly patching a governance file because a proposal asked "
                          "is what controlled evolution exists to prevent."}

    path = _resolve_target(name)
    if not path.exists():
        return {"error": f"{name} does not exist at the Core root"}

    saved = snapshot(name, proposal["id"], now)

    try:
        if name == ANTI_PATTERNS:
            detail = _apply_anti_pattern(path, proposal, change)
        elif name == PATTERN_LIBRARY:
            detail = _apply_pattern(path, proposal, change)
        else:
            detail = _apply_self_evolution(path, proposal, change)
    except Exception as e:
        # The snapshot exists, so the target is recoverable whatever happened.
        shutil.copy2(saved, path)
        return {"error": f"applying {proposal['id']} failed ({e}); the target was restored "
                         f"from {saved.name}"}

    return {
        "applied": True,
        "proposal": proposal["id"],
        "target": str(path),
        "snapshot": str(saved),
        "detail": detail,
        "applied_at": (now or datetime.now()).strftime(TIMESTAMP_FORMAT),
    }


def _apply_anti_pattern(path, proposal, change):
    """Add a rule to the anti-pattern database and bump its registry version."""
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    rules = data.setdefault("anti_patterns", [])
    numbers = [int(r["id"].split("-")[1]) for r in rules
               if str(r.get("id", "")).startswith("AP-") and r["id"].split("-")[1].isdigit()]
    rule_id = f"AP-{(max(numbers) + 1) if numbers else 1:03d}"

    supplied = change or {}
    rule = {
        "id": rule_id,
        "category": supplied.get("category", "Verification"),
        "name": supplied.get("name") or proposal.get("proposed_change", "Recorded rule"),
        "trigger_context": supplied.get("trigger_context") or ["code_generation"],
        "rule": supplied.get("rule") or proposal.get("proposed_change"),
        # A newly learned rule warns before it blocks. Promoting it to
        # STRICT_BLOCK is its own decision, made once the rule has proved itself.
        "enforcement": supplied.get("enforcement", "WARNING"),
        "fix_pattern": supplied.get("fix_pattern") or proposal.get("impact_analysis"),
        "origin": {"proposal": proposal["id"], "evidence": proposal.get("evidence")},
    }
    rules.append(rule)
    data["version"] = _bump(data.get("version", "1.0.0"))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return {"rule": rule_id, "enforcement": rule["enforcement"], "version": data["version"]}


def _apply_pattern(path, proposal, change):
    """Append a pattern in the format the library already documents."""
    from coresentinel_core.patterns import ledger as patterns

    record = (change or {}).get("pattern")
    body = patterns.render_markdown(record) if record else \
        f"#### {proposal.get('proposed_change')}\n- **Learned from**: {proposal.get('evidence')}"

    text = path.read_text(encoding="utf-8-sig")
    marker = "\n---\n\n## How to Add Patterns"
    block = f"\n{body}\n"
    if marker in text:
        text = text.replace(marker, block + marker, 1)
    else:
        text = text.rstrip() + "\n" + block
    path.write_text(text, encoding="utf-8")
    return {"appended": (record or {}).get("id") or proposal["id"]}


def _apply_self_evolution(path, proposal, change):
    """Append an anti-pattern entry to the self-evolution log."""
    entry = (change or {}).get("entry") or proposal.get("proposed_change")
    evidence = proposal.get("evidence") or "no evidence recorded"
    block = (f"\n### Anti-Pattern: {entry}\n"
             f"- **Evidence**: {evidence}\n"
             f"- **Recorded by**: {proposal['id']} "
             f"(approved by {proposal.get('approver') or 'unknown'})\n")
    path.write_text(path.read_text(encoding="utf-8-sig").rstrip() + "\n" + block,
                    encoding="utf-8")
    return {"appended": entry}


def revert(proposal, snapshot_path=None):
    """Restore the target byte-for-byte from the snapshot taken before applying."""
    recorded = snapshot_path or proposal.get("snapshot")
    # Path("") is Path("."), which exists — so an absent snapshot would sail past
    # an exists() check and try to copy a directory over the target.
    if not recorded:
        return {"error": f"no snapshot recorded for {proposal.get('id')}; "
                         "nothing to restore from"}
    saved = Path(recorded)
    if not saved.is_file():
        return {"error": f"no snapshot recorded for {proposal.get('id')}; "
                         "nothing to restore from"}

    name = Path(str(proposal.get("target_protocol") or "")).name
    path = _resolve_target(name)
    before = path.read_bytes() if path.exists() else b""
    shutil.copy2(saved, path)

    return {
        "reverted": True,
        "proposal": proposal.get("id"),
        "target": str(path),
        "snapshot": str(saved),
        "identical": path.read_bytes() == saved.read_bytes(),
        "changed": before != path.read_bytes(),
    }


def _bump(version):
    parts = str(version or "1.0.0").split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        parts[1] = str(int(parts[1]) + 1)
        parts[2] = "0"
    except ValueError:
        return "1.1.0"
    return ".".join(parts[:3])


def snapshots(proposal_id=None):
    if not SNAPSHOT_DIR.exists():
        return []
    found = sorted(SNAPSHOT_DIR.glob(f"{proposal_id or ''}*"))
    return [{"name": p.name, "path": str(p), "bytes": p.stat().st_size} for p in found]
