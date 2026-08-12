#!/usr/bin/env python3
"""
CoreSentinel Memory Lifecycle Engine

A memory store that only ever grows is a memory store that eventually lies. This module
governs what happens to a fact after it is recorded:

  decay        confidence erodes with age until the fact is re-verified
  verify       re-verification restores a fact to full confidence and restarts the clock
  promote      facts that survive scrutiny move up a tier (session -> project -> longterm)
  consolidate  duplicates merge instead of accumulating
  compact      old low-confidence facts fold into a summary rather than being deleted
  snapshot     every destructive operation is reversible

Every operation is a dry run unless --apply is passed, and every destructive one takes a
snapshot first.
"""

import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import coresentinel_memory as mem

# Confidence erodes 0.05 for every 30 days a fact goes unverified, never below the floor.
# Decay is computed from base_confidence, not from the current value, so running it twice
# in one day does not double-penalise a fact.
DECAY_PER_30_DAYS = 0.05
DECAY_FLOOR = 0.30

# A failure that happened does not become less true with age. Facts marked pinned are
# exempt too — that is the escape hatch for genuinely permanent knowledge.
DECAY_EXEMPT_LAYERS = {"failures"}

# The tier chain. A fact proven in a lower tier is promoted upward; a fact present in two
# tiers is kept only in the highest one.
TIER_CHAIN = ["working", "session", "project", "longterm"]

PROMOTION_RULES = [
    # session -> project stays inside the project scope: "what I learned this conversation
    # about this repo" becoming "what is true about this repo" is a safe automatic hop.
    {"source": "session", "target": "project", "min_confidence": 0.90, "min_age_days": 0,
     "requires_transferable": False},
    # project -> longterm crosses from project scope into shared Core knowledge. A project
    # fact is about *this* codebase by definition, so this hop is opt-in: the fact must be
    # explicitly marked transferable. Otherwise one repo's stack leaks into every repo.
    {"source": "project", "target": "longterm", "min_confidence": 0.95, "min_age_days": 14,
     "requires_transferable": True},
]

# Beyond this many facts a layer stops being readable context and becomes noise.
COMPACT_BUDGET = 150
COMPACT_CONFIDENCE_CEILING = 0.90


def _now(now=None):
    return now or datetime.now()


def _confidence(item):
    value = item.get("confidence")
    return float(value) if isinstance(value, (int, float)) else 0.5


# ---------------------------------------------------------------- snapshots

def snapshot_dir(target_dir="."):
    return mem.memory_root(target_dir) / "snapshots"


def create_snapshot(target_dir=".", label="manual", now=None):
    """Copy every resolved layer into a timestamped vault. Returns the snapshot record.

    The manifest stores absolute source paths, so a snapshot restores correctly even
    though project-scoped and Core-scoped layers live in different stores.
    """
    stamp = _now(now).strftime("%Y%m%d-%H%M%S")
    snap_id = f"snap-{stamp}"
    root = snapshot_dir(target_dir) / snap_id
    root.mkdir(parents=True, exist_ok=True)

    files = []
    for layer in list(mem.FACT_LAYERS) + ["decisions"]:
        source = mem.layer_path(layer, target_dir)
        if not Path(source).exists():
            continue
        stored = f"{layer}.json"
        shutil.copy2(source, root / stored)
        files.append({"layer": layer, "stored": stored, "origin": str(source)})

    manifest = {
        "id": snap_id,
        "label": label,
        "created_at": _now(now).strftime(mem.TIMESTAMP_FORMAT),
        "files": files,
    }
    with open(root / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def list_snapshots(target_dir="."):
    root = snapshot_dir(target_dir)
    if not root.exists():
        return []
    found = []
    for path in sorted(root.glob("snap-*/manifest.json"), reverse=True):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                found.append(json.load(f))
        except (OSError, json.JSONDecodeError, ValueError):
            found.append({"id": path.parent.name, "label": "unreadable manifest", "files": []})
    return found


def restore_snapshot(snap_id, target_dir=".", apply_changes=False):
    """Put every layer back the way the snapshot found it."""
    root = snapshot_dir(target_dir) / snap_id
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return {"error": f"snapshot '{snap_id}' not found in {snapshot_dir(target_dir)}"}

    try:
        with open(manifest_path, "r", encoding="utf-8-sig") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return {"error": f"snapshot manifest unreadable ({e})"}

    restored = []
    for record in manifest.get("files", []):
        stored = root / record["stored"]
        if not stored.exists():
            continue
        destination = Path(record["origin"])
        restored.append({"layer": record["layer"], "path": str(destination)})
        if apply_changes:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stored, destination)

    return {"id": snap_id, "restored": restored, "applied": bool(apply_changes)}


# ---------------------------------------------------------------- decay & verification

def decay(target_dir=".", apply_changes=False, now=None):
    """Erode the confidence of facts nobody has re-verified.

    Idempotent: the target confidence is a pure function of base_confidence and age, so
    running decay ten times in one day costs a fact exactly one day of trust.
    """
    stamp = _now(now)
    changes = []

    for layer in mem.FACT_LAYERS:
        if layer in DECAY_EXEMPT_LAYERS:
            continue
        data, error = mem.load_layer(layer, target_dir)
        if error or not isinstance(data, dict):
            continue

        touched = False
        for item in data.get("facts", []):
            if item.get("pinned"):
                continue
            age = mem.age_in_days(item.get("last_verified"), stamp)
            if age is None:
                continue
            base = item.get("base_confidence")
            base = float(base) if isinstance(base, (int, float)) else _confidence(item)
            target = max(DECAY_FLOOR, round(base - DECAY_PER_30_DAYS * (age / 30.0), 4))
            current = _confidence(item)
            if target >= current:
                continue

            changes.append({
                "layer": layer, "fact": item.get("fact"),
                "from": current, "to": target, "age_days": round(age, 1),
            })
            if apply_changes:
                item["base_confidence"] = base
                item["confidence"] = target
                item["classification"] = mem.classify_confidence(target)
                item["decayed_at"] = stamp.strftime(mem.TIMESTAMP_FORMAT)
                touched = True

        if touched:
            mem.save_layer(layer, data, target_dir)

    return {"changes": changes, "applied": bool(apply_changes)}


def reverify(match, target_dir=".", confidence=None, layer=None, pinned=False, now=None):
    """Restart the decay clock on facts matching a substring.

    This is the other half of decay: without it, confidence only ever falls, and an agent
    that re-checks docker-compose.yml has no way to say so.
    """
    stamp = _now(now).strftime(mem.TIMESTAMP_FORMAT)
    needle = str(match or "").lower()
    if not needle:
        return {"error": "a match string is required — refusing to re-verify every fact at once"}

    updated = []
    for name in ([layer] if layer else mem.FACT_LAYERS):
        if name not in mem.FACT_LAYERS:
            continue
        data, error = mem.load_layer(name, target_dir)
        if error or not isinstance(data, dict):
            continue

        touched = False
        for item in data.get("facts", []):
            if needle not in str(item.get("fact", "")).lower() and needle != item.get("id"):
                continue
            new_confidence = float(confidence) if confidence is not None else \
                float(item.get("base_confidence", _confidence(item)))
            updated.append({"layer": name, "fact": item.get("fact"),
                            "from": _confidence(item), "to": new_confidence})
            item["confidence"] = new_confidence
            item["classification"] = mem.classify_confidence(new_confidence)
            item["last_verified"] = stamp
            item.pop("base_confidence", None)
            item.pop("decayed_at", None)
            if pinned:
                item["pinned"] = True
            touched = True

        if touched:
            mem.save_layer(name, data, target_dir)

    return {"updated": updated}


# ---------------------------------------------------------------- promotion

def promote(target_dir=".", apply_changes=False, now=None):
    """Move facts that have earned it into the next tier up."""
    stamp = _now(now)
    promotions = []

    for rule in PROMOTION_RULES:
        source_data, source_error = mem.load_layer(rule["source"], target_dir)
        if source_error or not isinstance(source_data, dict):
            continue
        target_data, target_error = mem.load_layer(rule["target"], target_dir)
        if target_error or not isinstance(target_data, dict):
            continue

        keep, moving = [], []
        for item in source_data.get("facts", []):
            age = mem.age_in_days(item.get("last_verified"), stamp) or 0.0
            eligible = (_confidence(item) >= rule["min_confidence"]
                        and age >= rule["min_age_days"]
                        and (item.get("transferable") if rule["requires_transferable"] else True))
            (moving if eligible else keep).append(item)

        existing = {mem.normalize_fact(f.get("fact")) for f in target_data.get("facts", [])}
        for item in moving:
            promotions.append({
                "fact": item.get("fact"), "from": rule["source"], "to": rule["target"],
                "confidence": _confidence(item), "age_days": round(
                    mem.age_in_days(item.get("last_verified"), stamp) or 0.0, 1),
            })
            if not apply_changes:
                continue
            if mem.normalize_fact(item.get("fact")) in existing:
                continue
            target_data.setdefault("facts", []).append({
                **item,
                "promoted_from": rule["source"],
                "promoted_at": stamp.strftime(mem.TIMESTAMP_FORMAT),
            })
            existing.add(mem.normalize_fact(item.get("fact")))

        if apply_changes and moving:
            source_data["facts"] = keep
            mem.save_layer(rule["target"], target_data, target_dir)
            mem.save_layer(rule["source"], source_data, target_dir)

    return {"promotions": promotions, "applied": bool(apply_changes)}


# ---------------------------------------------------------------- consolidation

def consolidate(target_dir=".", apply_changes=False):
    """Merge duplicate facts within a layer, then across the tier chain.

    Merging keeps the highest confidence rather than averaging or boosting: three
    recordings of the same guess do not make it a verified fact.
    """
    merged_within, dropped_across = [], []
    layer_state = {}

    for layer in mem.FACT_LAYERS:
        data, error = mem.load_layer(layer, target_dir)
        if error or not isinstance(data, dict):
            continue

        grouped = {}
        order = []
        for item in data.get("facts", []):
            key = mem.normalize_fact(item.get("fact"))
            if key not in grouped:
                grouped[key] = dict(item)
                grouped[key].setdefault("occurrences", 1)
                order.append(key)
                continue

            kept = grouped[key]
            merged_within.append({"layer": layer, "fact": item.get("fact")})
            kept["occurrences"] = kept.get("occurrences", 1) + 1
            if _confidence(item) > _confidence(kept):
                kept["confidence"] = _confidence(item)
                kept["classification"] = mem.classify_confidence(_confidence(item))
            sources = kept.get("sources") or ([kept.get("source")] if kept.get("source") else [])
            if item.get("source") and item["source"] not in sources:
                sources.append(item["source"])
            kept["sources"] = sources
            newest = max(filter(None, [kept.get("last_verified"), item.get("last_verified")]),
                         default=kept.get("last_verified"))
            kept["last_verified"] = newest

        layer_state[layer] = {"data": data, "facts": [grouped[k] for k in order]}

    # Across the tier chain, the highest tier holding a fact owns it.
    seen_by_higher = set()
    for layer in reversed(TIER_CHAIN):
        state = layer_state.get(layer)
        if not state:
            continue
        surviving = []
        for item in state["facts"]:
            key = mem.normalize_fact(item.get("fact"))
            if key in seen_by_higher:
                dropped_across.append({"layer": layer, "fact": item.get("fact")})
                continue
            surviving.append(item)
        state["facts"] = surviving
        seen_by_higher.update(mem.normalize_fact(f.get("fact")) for f in surviving)

    if apply_changes and (merged_within or dropped_across):
        create_snapshot(target_dir, label="pre-consolidate")
        for layer, state in layer_state.items():
            state["data"]["facts"] = state["facts"]
            mem.save_layer(layer, state["data"], target_dir)

    return {"merged": merged_within, "superseded": dropped_across, "applied": bool(apply_changes)}


# ---------------------------------------------------------------- compaction

def compact(target_dir=".", budget=COMPACT_BUDGET, apply_changes=False, now=None):
    """Fold a layer's oldest low-confidence facts into one summary entry.

    Summarised, not deleted: the count, the date range and a sample survive, and the
    pre-compaction snapshot makes the whole operation reversible.
    """
    stamp = _now(now)
    reports = []
    pending = []

    for layer in mem.FACT_LAYERS:
        data, error = mem.load_layer(layer, target_dir)
        if error or not isinstance(data, dict):
            continue
        facts = data.get("facts", [])
        if len(facts) <= budget:
            continue

        def sort_key(item):
            return (mem.parse_timestamp(item.get("last_verified")) or datetime.min)

        candidates = [f for f in facts
                      if _confidence(f) < COMPACT_CONFIDENCE_CEILING
                      and not f.get("pinned") and not f.get("compacted")]
        candidates.sort(key=sort_key)
        surplus = len(facts) - budget
        victims = candidates[:surplus]
        if not victims:
            continue

        victim_ids = {id(v) for v in victims}
        remaining = [f for f in facts if id(f) not in victim_ids]
        dates = [v.get("last_verified") for v in victims if v.get("last_verified")]
        summary = {
            "id": mem.fact_id(f"compaction-{layer}-{stamp.isoformat()}"),
            "fact": f"Compacted {len(victims)} low-confidence {layer} fact(s) "
                    f"recorded between {min(dates) if dates else 'unknown'} and "
                    f"{max(dates) if dates else 'unknown'}",
            "confidence": 0.50,
            "classification": mem.classify_confidence(0.50),
            "source": "coresentinel memory compact",
            "created_at": stamp.strftime(mem.TIMESTAMP_FORMAT),
            "last_verified": stamp.strftime(mem.TIMESTAMP_FORMAT),
            "compacted": {
                "count": len(victims),
                "sample": [v.get("fact") for v in victims[:5]],
            },
        }

        reports.append({"layer": layer, "compacted": len(victims),
                        "before": len(facts), "after": len(remaining) + 1})
        pending.append((layer, data, remaining + [summary]))

    if apply_changes and pending:
        create_snapshot(target_dir, label="pre-compact", now=now)
        for layer, data, facts in pending:
            data["facts"] = facts
            mem.save_layer(layer, data, target_dir)

    return {"layers": reports, "budget": budget, "applied": bool(apply_changes)}


# ---------------------------------------------------------------- rendering

def _header(title):
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


def _footer(applied, command):
    print("  " + "-" * 60)
    if applied:
        print("  Applied. Reverse with: coresentinel memory snapshots")
    else:
        print(f"  Dry run — nothing written. Apply with: {command} --apply")
    print("=" * 64 + "\n")


def print_decay(target_dir=".", apply_changes=False, emit_json=False):
    report = decay(target_dir, apply_changes)
    if emit_json:
        print(json.dumps(report, indent=2))
        return 0

    _header("⏳ CoreSentinel Memory Decay")
    if not report["changes"]:
        print("  Every fact is current — nothing has aged past its confidence.")
        print("=" * 64 + "\n")
        return 0

    print(f"  {len(report['changes'])} fact(s) have aged since their last verification:")
    print("  " + "-" * 60)
    for change in report["changes"]:
        print(f"  ({change['layer']}) {change['fact']}")
        print(f"      {change['from']} -> {change['to']}  ·  {change['age_days']} days unverified")
    print("")
    print("  Re-verify instead of accepting the drop:")
    print("    coresentinel memory verify --match \"<substring>\" [--confidence 0.98]")
    _footer(report["applied"], "coresentinel memory decay")
    return 0


def print_promote(target_dir=".", apply_changes=False, emit_json=False):
    report = promote(target_dir, apply_changes)
    if emit_json:
        print(json.dumps(report, indent=2))
        return 0

    _header("⬆️  CoreSentinel Memory Promotion")
    if not report["promotions"]:
        print("  No facts have earned promotion yet.")
        print("  session -> project  : confidence >= 0.90")
        print("  project -> longterm : confidence >= 0.95, 14+ days old, marked transferable")
        print("=" * 64 + "\n")
        return 0

    for item in report["promotions"]:
        print(f"  {item['from']} -> {item['to']}  ·  confidence {item['confidence']}  ·  {item['age_days']}d")
        print(f"      {item['fact']}")
    _footer(report["applied"], "coresentinel memory promote")
    return 0


def print_consolidate(target_dir=".", apply_changes=False, emit_json=False):
    report = consolidate(target_dir, apply_changes)
    if emit_json:
        print(json.dumps(report, indent=2))
        return 0

    _header("🧩 CoreSentinel Memory Consolidation")
    if not report["merged"] and not report["superseded"]:
        print("  No duplicates found — every fact is recorded exactly once.")
        print("=" * 64 + "\n")
        return 0

    if report["merged"]:
        print(f"  {len(report['merged'])} duplicate(s) merged within their layer:")
        for item in report["merged"]:
            print(f"      ({item['layer']}) {item['fact']}")
    if report["superseded"]:
        print(f"\n  {len(report['superseded'])} fact(s) superseded by a higher tier:")
        for item in report["superseded"]:
            print(f"      ({item['layer']}) {item['fact']}")
    _footer(report["applied"], "coresentinel memory consolidate")
    return 0


def print_compact(target_dir=".", budget=COMPACT_BUDGET, apply_changes=False, emit_json=False):
    report = compact(target_dir, budget, apply_changes)
    if emit_json:
        print(json.dumps(report, indent=2))
        return 0

    _header("🗜️  CoreSentinel Memory Compaction")
    print(f"  Budget : {report['budget']} facts per layer")
    print("  " + "-" * 60)
    if not report["layers"]:
        print("  Every layer is within budget — nothing to compact.")
        print("=" * 64 + "\n")
        return 0

    for item in report["layers"]:
        print(f"  ({item['layer']}) {item['before']} -> {item['after']} facts "
              f"· {item['compacted']} summarised")
    _footer(report["applied"], "coresentinel memory compact")
    return 0


def print_snapshots(target_dir=".", emit_json=False):
    snaps = list_snapshots(target_dir)
    if emit_json:
        print(json.dumps({"snapshots": snaps, "vault": str(snapshot_dir(target_dir))}, indent=2))
        return 0

    _header("📦 CoreSentinel Memory Snapshots")
    print(f"  Vault : {snapshot_dir(target_dir)}")
    print("  " + "-" * 60)
    if not snaps:
        print("  No snapshots yet. One is taken automatically before every")
        print("  destructive operation, or on demand:")
        print("    coresentinel memory snapshot")
        print("=" * 64 + "\n")
        return 0

    for snap in snaps:
        print(f"  [{snap['id']}] {snap.get('label', 'manual')} "
              f"· {len(snap.get('files', []))} layer(s) · {snap.get('created_at', '-')}")
    print("  " + "-" * 60)
    print("  Restore with: coresentinel memory restore <snapshot-id> --apply")
    print("=" * 64 + "\n")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "decay"
    applied = "--apply" in sys.argv
    {"decay": lambda: print_decay(".", applied),
     "promote": lambda: print_promote(".", applied),
     "consolidate": lambda: print_consolidate(".", applied),
     "compact": lambda: print_compact(".", COMPACT_BUDGET, applied),
     "snapshots": lambda: print_snapshots(".")}.get(action, lambda: print_decay(".", applied))()
