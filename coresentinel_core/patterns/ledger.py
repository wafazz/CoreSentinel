"""
The pattern library, as data.

`11-pattern-library.md` has documented a capture format since v1 — stack,
problem, solution, gotchas, first used in — and the patterns were prose in a
markdown file. Prose is fine to read and impossible to link: nothing could say
"this pattern came from that incident", and nothing could count how often the
same lesson had been relearned.

The fields here are exactly the documented ones, so a record renders back into
the library's markdown format without loss. What is added is identity (`PAT-NNNN`),
provenance (which incident taught it), and an occurrence count — because a
pattern seen three times is a different claim from one seen once.

Scoped like decisions and incidents: a pattern learned in a repository belongs to
that repository until somebody marks it transferable, the same rule the memory
layers use to stop one project's truth leaking into every other.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

ID_PREFIX = "PAT"

SCOPE_PROJECT, SCOPE_CORE = "project", "core"

# The documented capture format, field for field.
CAPTURE_FIELDS = ["name", "category", "stack", "problem", "solution", "gotchas",
                  "first_used_in"]

LINK_FIELDS = ["related_incidents", "related_decisions", "related_files"]

FIELDS = (["id", "confidence", "occurrences", "source", "transferable",
           "created_at", "last_seen", "project", "scope"]
          + CAPTURE_FIELDS + LINK_FIELDS)


def _memory():
    import coresentinel_memory as mem
    return mem


def core_path():
    return _memory().MEMORY_DIR / "patterns_library.json"


def project_path(target_dir="."):
    mem = _memory()
    root = mem.find_project_root(target_dir)
    return (root / mem.CONFIG_DIRNAME / "memory" / "patterns_library.json") if root else None


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
    normalized["occurrences"] = int(normalized.get("occurrences") or 1)
    normalized["transferable"] = bool(normalized.get("transferable"))
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

    # A transferable Core pattern applies everywhere — that is what the mark means.
    # An unmarked one stays with the repository that learned it.
    if include_core or not project_file:
        found, error = _read(core_path())
        if error:
            problems.append(f"{core_path()}: {error}")
        records += [normalize(r, SCOPE_CORE) for r in found
                    if include_core or not project_file or r.get("transferable")]
    elif project_file:
        found, _ = _read(core_path())
        records += [normalize(r, SCOPE_CORE) for r in found if r.get("transferable")]

    for problem in problems:
        print(f"[!] Pattern library unreadable ({problem}) — omitted", file=sys.stderr)
    return [r for r in records if r]


def get(pattern_id, target_dir="."):
    key = (pattern_id or "").strip().lower()
    return next((r for r in load(target_dir, include_core=True)
                 if str(r.get("id", "")).lower() == key), None)


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


def find_similar(name, target_dir="."):
    """A pattern already recorded under the same name, if there is one."""
    needle = " ".join(str(name or "").lower().split())
    if not needle:
        return None
    return next((r for r in load(target_dir, include_core=True)
                 if " ".join(str(r.get("name", "")).lower().split()) == needle), None)


def add(target_dir=".", name=None, problem=None, solution=None, stack=None,
        gotchas=None, category=None, first_used_in=None, source=None,
        confidence=None, transferable=False, now=None, **links):
    """Record a pattern, or count another occurrence of one already known.

    Re-recording does not raise confidence. Three sightings of the same guess
    make one guess seen three times — the same rule the memory consolidator uses.
    """
    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)

    existing = find_similar(name, target_dir)
    if existing:
        return _count_occurrence(existing, target_dir, stamp, links)

    path = ledger_path(target_dir)
    records, error = _read(path)
    if error:
        print(f"[!] Refusing to write: {path} is unreadable ({error}).", file=sys.stderr)
        print("    Repair or remove the file first — overwriting it would destroy "
              "every pattern it holds.", file=sys.stderr)
        return None

    mem = _memory()
    root = mem.find_project_root(target_dir)
    record = normalize({
        "id": next_id(target_dir),
        "name": name or "Untitled pattern",
        "category": category,
        "stack": stack,
        "problem": problem,
        "solution": solution,
        "gotchas": gotchas,
        "first_used_in": first_used_in or (root.name if root else None),
        "source": source,
        "confidence": float(confidence) if confidence is not None else 0.7,
        "occurrences": 1,
        "transferable": bool(transferable),
        "created_at": stamp,
        "last_seen": stamp,
        "project": root.name if root else None,
        **{field: links.get(field) for field in LINK_FIELDS},
    }, SCOPE_PROJECT if project_path(target_dir) else SCOPE_CORE)

    records.append(record)
    _write(path, records)
    return record


def _count_occurrence(existing, target_dir, stamp, links):
    additions = {}
    for field in LINK_FIELDS:
        added = split_list(links.get(field))
        if added:
            additions[field] = list(dict.fromkeys(existing.get(field, []) + added))
    return update(existing["id"], target_dir,
                  occurrences=existing["occurrences"] + 1, last_seen=stamp, **additions)


def update(pattern_id, target_dir=".", **changes):
    for path, scope in [(project_path(target_dir), SCOPE_PROJECT), (core_path(), SCOPE_CORE)]:
        if not path:
            continue
        records, error = _read(path)
        if error:
            continue
        for index, record in enumerate(records):
            if str(record.get("id", "")).lower() != str(pattern_id).lower():
                continue
            merged = normalize({**record, **{k: v for k, v in changes.items()
                                             if v is not None}}, scope)
            records[index] = merged
            _write(path, records)
            return merged
    return None


def render_markdown(record):
    """Back into the library's documented format, field for field."""
    lines = [f"#### {record.get('name')}"]
    for label, key in [("Stack", "stack"), ("Problem", "problem"),
                       ("Solution", "solution"), ("Gotchas", "gotchas"),
                       ("First used in", "first_used_in")]:
        value = record.get(key)
        if value:
            lines.append(f"- **{label}**: {value}")
    provenance = record.get("related_incidents") or []
    if provenance:
        lines.append(f"- **Learned from**: {', '.join(provenance)}")
    lines.append(f"- **Pattern id**: {record.get('id')}"
                 + (f" (seen {record['occurrences']}×)"
                    if record.get("occurrences", 1) > 1 else ""))
    return "\n".join(lines)


def summary(target_dir="."):
    records = load(target_dir, include_core=True)
    return {
        "total": len(records),
        "transferable": sum(1 for r in records if r.get("transferable")),
        "repeated": [r["id"] for r in records if r.get("occurrences", 1) > 1],
        "from_incidents": [r["id"] for r in records if r.get("related_incidents")],
        "by_category": {c: sum(1 for r in records if r.get("category") == c)
                        for c in sorted({r.get("category") for r in records if r.get("category")})},
    }
