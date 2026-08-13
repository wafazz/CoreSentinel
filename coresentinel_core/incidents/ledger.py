"""
Incidents — the thing that went wrong, recorded so it can stop going wrong.

`61-incident-protocol.md` has described a four-phase incident response since v1:
contain, diagnose, hotfix, post-mortem. It was prose. Nothing recorded an
incident, so the fourth phase — the one that turns a bad afternoon into a rule
nobody has to relearn — had nowhere to write its output.

An incident holds four things, and the last two are the point:

    problem      what was observed
    root_cause   what actually caused it
    resolution   what was done about it
    learning     what should be different next time

`learning` is what Phase 8 turns into a pattern and then a candidate rule. An
incident without one is a war story; an incident with one is governance.

Scoped like decisions and the project memory layers: an incident belongs to the
repository it happened in, not to whichever Core happened to be driving.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

ID_PREFIX = "INC"

OPEN = "Open"
CONTAINED = "Contained"
RESOLVED = "Resolved"
STATUSES = [OPEN, CONTAINED, RESOLVED]

CRITICAL, HIGH, MEDIUM, LOW = "Critical", "High", "Medium", "Low"
SEVERITIES = [CRITICAL, HIGH, MEDIUM, LOW]

# Root-cause classes from 61-incident-protocol.md, kept so incidents can be
# counted by kind rather than only read one at a time.
CLASS_A = "A: application logic"
CLASS_B = "B: third-party or vendor failure"
CLASS_C = "C: resource exhaustion or contention"
CLASS_D = "D: configuration or environment drift"
CLASSES = [CLASS_A, CLASS_B, CLASS_C, CLASS_D]

LINK_FIELDS = ["related_decisions", "related_files", "related_commits",
               "related_tests", "related_patterns", "related_tasks"]

FIELDS = (["id", "title", "problem", "root_cause", "resolution", "learning",
           "severity", "status", "root_cause_class", "detected_by",
           "occurred_at", "resolved_at", "project", "scope"] + LINK_FIELDS)

SCOPE_PROJECT, SCOPE_CORE = "project", "core"


def _memory():
    import coresentinel_memory as mem
    return mem


def core_path():
    return _memory().MEMORY_DIR / "incidents.json"


def project_path(target_dir="."):
    mem = _memory()
    root = mem.find_project_root(target_dir)
    return (root / mem.CONFIG_DIRNAME / "memory" / "incidents.json") if root else None


def ledger_path(target_dir="."):
    return project_path(target_dir) or core_path()


def split_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def normalize(record, scope=None):
    if not isinstance(record, dict):
        return None
    normalized = dict(record)
    for field in FIELDS:
        normalized.setdefault(field, None)
    for field in LINK_FIELDS:
        normalized[field] = split_list(normalized.get(field))
    normalized["status"] = normalized.get("status") or OPEN
    normalized["severity"] = normalized.get("severity") or MEDIUM
    if scope:
        normalized["scope"] = scope
    return normalized


def _read(path):
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
    records, problems = [], []

    project_file = project_path(target_dir)
    if project_file:
        found, error = _read(project_file)
        if error:
            problems.append(f"{project_file}: {error}")
        records += [normalize(r, SCOPE_PROJECT) for r in found]

    if include_core or not project_file:
        found, error = _read(core_path())
        if error:
            problems.append(f"{core_path()}: {error}")
        records += [normalize(r, SCOPE_CORE) for r in found]

    for problem in problems:
        print(f"[!] Incident ledger unreadable ({problem}) — omitted", file=sys.stderr)
    return [r for r in records if r]


def get(incident_id, target_dir="."):
    key = (incident_id or "").strip().lower()
    return next((r for r in load(target_dir) if str(r.get("id", "")).lower() == key), None)


def next_id(target_dir="."):
    highest = 0
    for record in load(target_dir, include_core=True):
        raw = str(record.get("id") or "")
        if not raw.upper().startswith(ID_PREFIX + "-"):
            continue
        digits = raw.split("-", 1)[1]
        if digits.isdigit():
            highest = max(highest, int(digits))
    return f"{ID_PREFIX}-{highest + 1:04d}"


def create(target_dir=".", title=None, problem=None, severity=MEDIUM,
           root_cause=None, resolution=None, learning=None, detected_by=None,
           root_cause_class=None, now=None, **links):
    path = ledger_path(target_dir)
    existing, error = _read(path)
    if error:
        print(f"[!] Refusing to write: {path} is unreadable ({error}).", file=sys.stderr)
        print("    Repair or remove the file first — overwriting it would destroy "
              "every incident it holds.", file=sys.stderr)
        return None

    mem = _memory()
    root = mem.find_project_root(target_dir)
    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)

    record = normalize({
        "id": next_id(target_dir),
        "title": title or "Untitled incident",
        "problem": problem,
        "root_cause": root_cause,
        "resolution": resolution,
        "learning": learning,
        "severity": severity if severity in SEVERITIES else MEDIUM,
        "status": RESOLVED if resolution else OPEN,
        "root_cause_class": root_cause_class,
        "detected_by": detected_by,
        "occurred_at": stamp,
        "resolved_at": stamp if resolution else None,
        "project": root.name if root else None,
        **{field: links.get(field) for field in LINK_FIELDS},
    }, SCOPE_PROJECT if project_path(target_dir) else SCOPE_CORE)

    existing.append(record)
    _write(path, existing)
    return record


def update(incident_id, target_dir=".", **changes):
    for path, scope in [(project_path(target_dir), SCOPE_PROJECT), (core_path(), SCOPE_CORE)]:
        if not path:
            continue
        records, error = _read(path)
        if error:
            continue
        for index, record in enumerate(records):
            if str(record.get("id", "")).lower() != str(incident_id).lower():
                continue
            merged = normalize({**record, **{k: v for k, v in changes.items()
                                             if v is not None}}, scope)
            records[index] = merged
            _write(path, records)
            return merged
    return None


def link(incident_id, target_dir=".", **additions):
    """Attach related decisions, files, commits, tests, patterns or tasks."""
    record = get(incident_id, target_dir)
    if not record:
        return {"error": f"incident '{incident_id}' not found"}

    changes = {}
    for field in LINK_FIELDS:
        added = split_list(additions.get(field))
        if added:
            changes[field] = list(dict.fromkeys(record.get(field, []) + added))
    if not changes:
        return {"error": "nothing to link — name a decision, file, commit, test, "
                         "pattern or task"}
    return {"incident": update(incident_id, target_dir, **changes), "linked": changes}


def resolve(incident_id, target_dir=".", resolution=None, learning=None, now=None):
    """Close an incident.

    A resolution without a learning is accepted but reported: the fix is what
    stops it happening now, the learning is what stops it happening again.
    """
    record = get(incident_id, target_dir)
    if not record:
        return {"error": f"incident '{incident_id}' not found"}
    if not resolution:
        return {"error": "a resolution is required to close an incident"}

    updated = update(incident_id, target_dir, resolution=resolution, learning=learning,
                     status=RESOLVED,
                     resolved_at=(now or datetime.now()).strftime(TIMESTAMP_FORMAT))
    return {"incident": updated,
            "warning": (None if learning else
                        "no learning recorded — the fix stops it now, the learning is "
                        "what stops it recurring")}


def summary(target_dir="."):
    records = load(target_dir)
    return {
        "total": len(records),
        "open": sum(1 for r in records if r["status"] != RESOLVED),
        "by_status": {status: sum(1 for r in records if r["status"] == status)
                      for status in STATUSES},
        "by_severity": {severity: sum(1 for r in records if r["severity"] == severity)
                        for severity in SEVERITIES},
        "without_learning": [r["id"] for r in records
                             if r["status"] == RESOLVED and not r.get("learning")],
    }
