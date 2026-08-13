"""
The decision ledger, scoped like memory.

v1 kept every ADR in one Core-global file, so ten repositories governed by one
Core shared one decision list — the same failure the memory scoping split exists
to prevent, left in place for decisions.

Scoping now matches the `project` memory layer exactly — the ledger resolves to
one store, not a union:

    bound project   <project>/.coresentinel/memory/decisions.json
    unbound         <core>/memory/decisions.json

Unioning the two was tried and reverted. The Core ledger holds the decisions of
whichever repository was worked on unbound — for this repository, CoreSentinel's
own ADRs about its memory architecture. Surfacing those inside an unrelated
project made `decision verify` fire on changes they had nothing to do with,
which is F-08 in a new guise: one repository's decisions presented as governance
for another. A check that cries wolf is a check people learn to skip.

`include_core=True` remains for a future organization-wide ledger, where
crossing scope is explicit rather than accidental — the same shape as the
`transferable` mark that lets a project fact reach the Core.
"""

import json
import sys
from pathlib import Path

from coresentinel_core.decisions import schema

SCOPE_PROJECT = "project"
SCOPE_CORE = "core"

ID_PREFIX = "ADR"


def _memory():
    import coresentinel_memory as mem
    return mem


def core_path():
    return _memory().MEMORY_LAYERS["decisions"]


def project_path(target_dir="."):
    mem = _memory()
    root = mem.find_project_root(target_dir)
    return (root / mem.CONFIG_DIRNAME / "memory" / "decisions.json") if root else None


def ledger_path(target_dir="."):
    """Where a new decision would be written from this directory."""
    return project_path(target_dir) or core_path()


def _read(path):
    """(records, error). A corrupt ledger is never silently treated as empty —
    that would let the next write overwrite every recorded decision with one."""
    if not path or not Path(path).exists():
        return [], None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return (data if isinstance(data, list) else []), None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return [], str(e)


def _write(path, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    return Path(path)


def load(target_dir=".", include_core=False):
    """Every visible decision. Resolves to one ledger unless the Core is asked for."""
    records, problems = [], []

    project_file = project_path(target_dir)
    if project_file:
        found, error = _read(project_file)
        if error:
            problems.append(f"{project_file}: {error}")
        records += [schema.normalize(r, SCOPE_PROJECT) for r in found]

    if include_core or not project_file:
        found, error = _read(core_path())
        if error:
            problems.append(f"{core_path()}: {error}")
        records += [schema.normalize(r, SCOPE_CORE) for r in found]

    for problem in problems:
        print(f"[!] Decision ledger unreadable ({problem}) — omitted", file=sys.stderr)

    return [r for r in records if r]


def binding(target_dir="."):
    """Only accepted decisions constrain future work."""
    return [r for r in load(target_dir) if schema.is_binding(r)]


def get(decision_id, target_dir="."):
    key = (decision_id or "").strip().lower()
    return next((r for r in load(target_dir) if str(r.get("id", "")).lower() == key), None)


def next_id(target_dir="."):
    """Allocated across both scopes, so an id never means two different decisions.

    The project ledger reads alone, but ids are allocated against both — a
    project ADR-004 and a Core ADR-004 would collide the moment anyone quoted
    one in a commit message.
    """
    highest = 0
    for record in load(target_dir, include_core=True):
        raw = str(record.get("id") or "")
        if not raw.upper().startswith(ID_PREFIX + "-"):
            continue
        digits = raw.split("-", 1)[1]
        if digits.isdigit():
            highest = max(highest, int(digits))
    return f"{ID_PREFIX}-{highest + 1:03d}"


def add(target_dir=".", **fields):
    """Record a decision in the bound project when there is one, else the Core."""
    path = ledger_path(target_dir)
    existing, error = _read(path)
    if error:
        print(f"[!] Refusing to write: {path} is unreadable ({error}).", file=sys.stderr)
        print("    Repair or remove the file first — overwriting it would destroy "
              "every decision it holds.", file=sys.stderr)
        return None

    mem = _memory()
    root = mem.find_project_root(target_dir)
    record = schema.build(decision_id=next_id(target_dir),
                          project=root.name if root else None, **fields)
    record["scope"] = SCOPE_PROJECT if project_path(target_dir) else SCOPE_CORE

    existing.append(record)
    _write(path, existing)
    return record


def update(decision_id, target_dir=".", **changes):
    """Amend a record in whichever scope holds it. Returns the updated record."""
    for path, scope in [(project_path(target_dir), SCOPE_PROJECT), (core_path(), SCOPE_CORE)]:
        if not path:
            continue
        records, error = _read(path)
        if error:
            continue
        for index, record in enumerate(records):
            if str(record.get("id", "")).lower() != decision_id.lower():
                continue
            merged = schema.normalize({**record, **changes}, scope)
            records[index] = merged
            _write(path, records)
            return merged
    return None


def supersede(old_id, new_id, target_dir=".", reason=None):
    """Record that one decision replaces another, in both directions.

    A reversal is legitimate — what is not legitimate is a reversal nobody can
    see. Superseding writes the link at both ends so neither record reads as
    current on its own.
    """
    old = get(old_id, target_dir)
    new = get(new_id, target_dir)
    if not old:
        return {"error": f"decision '{old_id}' not found"}
    if not new:
        return {"error": f"decision '{new_id}' not found"}
    if old["id"] == new["id"]:
        return {"error": "a decision cannot supersede itself"}

    related = list(dict.fromkeys(old.get("related_decisions", []) + [new["id"]]))
    updated_old = update(old["id"], target_dir, status=schema.SUPERSEDED,
                         superseded_by=new["id"], related_decisions=related,
                         supersede_reason=reason)
    updated_new = update(new["id"], target_dir, supersedes=old["id"],
                         related_decisions=list(dict.fromkeys(
                             new.get("related_decisions", []) + [old["id"]])))
    return {"superseded": updated_old, "superseding": updated_new, "reason": reason}
