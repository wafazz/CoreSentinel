"""
When enough trusted knowledge clusters, draft a skill — and stop there.

A skill is a bigger claim than a lesson. A lesson says "this happened, here is
what we saw"; a skill says "here is how to do this kind of work", and it gets
loaded into an agent's context to shape a whole task. So the bar is higher, and
deliberately so: `MIN_TRUSTED` lessons agreeing, in one context, with
`MIN_EXPERIENCES` observations behind them. One strong lesson is a lesson.

## Where this stops, and why

CoreSentinel does not own a skill runtime. Per `18-skills-protocol.md`, skills
are a **host** surface — they live in `~/.claude/skills/` and the host loads
them. The one CS-authored skill in existence (`landing-design`) was installed by
hand, and did not appear in the host listing until the host restarted.

So this module drafts. It writes a complete `SKILL.md` into
`memory/skill_candidates/`, with the evidence that produced it, and it never
writes into the host's skill directory. That is not a limitation worked around;
it is the correct boundary. Installing a skill changes how an agent approaches
every matching task from then on, which is a governance act with a person's name
on it — and §10's own bar ("skills should require stronger evidence than
ordinary knowledge") points the same way.

`evolve review` reports the drafts. A person reads one, and installs it or does
not.
"""

import re
from datetime import datetime
from pathlib import Path

from coresentinel_core import CORE_ROOT

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

DRAFT_DIR = CORE_ROOT / "memory" / "skill_candidates"

# Trusted lessons that must agree, in one context, before a skill is drafted.
MIN_TRUSTED = 3

# Observations behind them. Three lessons each seen twice is thin; this is the
# difference between a cluster and a coincidence.
MIN_EXPERIENCES = 8

ID_PREFIX = "SKILL"

# Words too general to name a skill. A skill called "the-error-skill" tells a
# reader nothing about when to load it.
GENERIC = {"the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with",
           "at", "as", "is", "are", "be", "was", "were", "it", "this", "that",
           "gate", "quality", "blocked", "failed", "error", "seen", "task",
           "run", "ran", "result", "status", "times", "once", "twice"}

TOKEN = re.compile(r"[a-z0-9]+")

MAX_NAME_TERMS = 4


def _terms(text):
    return [t for t in TOKEN.findall(str(text or "").lower())
            if len(t) > 2 and t not in GENERIC]


def name_for(context, lessons):
    """A name that says when to load the skill, not that it exists.

    Built from the terms the clustered lessons share, because what they have in
    common is what the skill is about.
    """
    counts = {}
    for lesson in lessons:
        for term in set(_terms(lesson)):
            counts[term] = counts.get(term, 0) + 1

    ranked = sorted(counts, key=lambda t: (-counts[t], t))[:MAX_NAME_TERMS]
    parts = [p for p in (str(context or "").split(".")[:2] + ranked) if p]
    return "-".join(dict.fromkeys(parts))[:60] or "unnamed-skill"


def cluster(store, now=None):
    """Groups of trusted lessons that share a context and might be a skill."""
    from coresentinel_core.learning import candidates

    grouped = {}
    for record in candidates.trusted(store, now):
        key = record.get("context") or "global"
        grouped.setdefault(key, []).append(record)

    clusters = []
    for context, records in grouped.items():
        observations = sum(int(r.get("occurrences") or 0) for r in records)
        clusters.append({
            "context": None if context == "global" else context,
            "lessons": records,
            "trusted": len(records),
            "observations": observations,
            "qualifies": (len(records) >= MIN_TRUSTED
                          and observations >= MIN_EXPERIENCES),
            "why_not": _why_not(len(records), observations),
        })
    clusters.sort(key=lambda c: (-c["trusted"], str(c["context"])))
    return clusters


def _why_not(trusted, observations):
    reasons = []
    if trusted < MIN_TRUSTED:
        reasons.append(f"{trusted} trusted lesson(s), needs {MIN_TRUSTED}")
    if observations < MIN_EXPERIENCES:
        reasons.append(f"{observations} observation(s), needs {MIN_EXPERIENCES}")
    return "; ".join(reasons)


def render(candidate):
    """The draft SKILL.md, in the shape `18-skills-protocol.md` documents.

    Deliberately written as a draft and labelled as one. A generated skill that
    reads like a finished one invites installation without review, which is the
    single thing this module is arranged to prevent.
    """
    from coresentinel_core.security import redaction

    context = candidate["context"] or "any stack"
    lessons = candidate["lessons"]

    lines = [
        "---",
        f"name: {candidate['name']}",
        f"description: DRAFT — patterns CoreSentinel observed while working on "
        f"{context}. Not reviewed by a human. Read the evidence before relying on this.",
        "---",
        "",
        f"# {candidate['name']}",
        "",
        "> **This is a draft.** CoreSentinel assembled it from what it watched "
        "happen; nobody has reviewed it. It is not installed and will not be "
        "loaded by any host until a person moves it into the skills directory.",
        "",
        "## When this applies",
        "",
        f"Work on **{context}**.",
        "",
        f"Drawn from {candidate['trusted']} trusted lesson(s) across "
        f"{candidate['observations']} observation(s).",
        "",
        "## What was observed",
        "",
    ]

    for record in sorted(lessons, key=lambda r: -float(r.get("confidence") or 0)):
        lines.append(f"### {record.get('lesson')}")
        lines.append("")
        lines.append(f"- **Confidence**: {record.get('confidence'):.2f} "
                     f"({record.get('confidence_terms', {}).get('band', 'unknown')})")
        lines.append(f"- **Sources**: {len(record.get('sources') or [])} distinct")
        lines.append(f"- **Outcomes**: {record.get('success_count', 0)} succeeded, "
                     f"{record.get('failure_count', 0)} failed")
        lines.append(f"- **Candidate**: `{record['id']}` — "
                     f"`coresentinel evolve explain {record['id']}`")
        lines.append("")

    lines += [
        "## What this draft does not contain",
        "",
        "Instructions. Every line above describes something that happened; none "
        "of it prescribes what to do about it. Turning an observation into "
        "guidance is the review this draft is waiting for — and it is the step "
        "that needs somebody who understands the system, not a higher "
        "confidence score.",
        "",
        "---",
        "",
        f"Drafted {candidate['drafted_at']} by CoreSentinel. "
        f"Id `{candidate['id']}`.",
        "",
    ]
    # Redacted again on the way out. A draft leaves the store and becomes a file
    # somebody may read, paste or commit, and the second pass costs nothing
    # against the one time a lesson reached here from a source that predates the
    # redaction at `candidates.observe`.
    return redaction.redact_text("\n".join(lines))


def next_id(existing=None):
    used = {c.get("id") for c in (existing or [])}
    number = len(used) + 1
    while f"{ID_PREFIX}-{number:03d}" in used:
        number += 1
    return f"{ID_PREFIX}-{number:03d}"


def existing_drafts(directory=None):
    root = Path(directory or DRAFT_DIR)
    if not root.exists():
        return []
    found = []
    for path in sorted(root.glob("*/SKILL.md")):
        found.append({"name": path.parent.name, "path": str(path),
                      "bytes": path.stat().st_size})
    return found


def draft(store, directory=None, apply_changes=False, now=None):
    """Draft a SKILL.md for every qualifying cluster.

    A dry run by default, like every other lifecycle pass in CoreSentinel.
    Returns what it would write, or what it wrote.
    """
    root = Path(directory or DRAFT_DIR)
    stamp = (now or datetime.now()).strftime(TIMESTAMP_FORMAT)
    clusters = cluster(store, now)
    already = existing_drafts(root)

    drafted, skipped = [], []
    for index, group in enumerate(clusters):
        if not group["qualifies"]:
            skipped.append({"context": group["context"], "trusted": group["trusted"],
                            "observations": group["observations"],
                            "why_not": group["why_not"]})
            continue

        candidate = {
            **group,
            "id": f"{ID_PREFIX}-{len(already) + index + 1:03d}",
            "name": name_for(group["context"], [r["lesson"] for r in group["lessons"]]),
            "drafted_at": stamp,
        }
        body = render(candidate)
        target = root / candidate["name"] / "SKILL.md"

        if apply_changes:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

        drafted.append({"id": candidate["id"], "name": candidate["name"],
                        "context": group["context"], "trusted": group["trusted"],
                        "observations": group["observations"],
                        "path": str(target), "bytes": len(body.encode("utf-8"))})

    return {
        "coresentinel_api": "1.1",
        "drafted": drafted,
        "skipped": skipped,
        "thresholds": {"trusted": MIN_TRUSTED, "experiences": MIN_EXPERIENCES},
        "directory": str(root),
        "applied": bool(apply_changes),
        "installed": False,
        "note": ("Drafts are never installed. Moving one into the host's skills "
                 "directory is a human act — see 18-skills-protocol.md."),
    }
