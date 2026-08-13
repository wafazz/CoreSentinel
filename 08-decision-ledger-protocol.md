# Architecture Decision Record (ADR) Ledger Protocol

> **Persistent Decision Tracking for AI Coding Squads**
> Records architectural trade-offs, rationale, alternatives considered, and impact, and
> refuses to let an agent reverse one without anybody seeing.

---

## 🎯 Scoping

The ledger resolves to **one** store, exactly like the `project` memory layer:

| Where you are | Ledger |
| :--- | :--- |
| Inside a bound project | `<project>/.coresentinel/memory/decisions.json` |
| Unbound | `<CoreSentinel>/memory/decisions.json` |

The two are **not** unioned. The Core ledger holds the decisions of whichever repository was
worked on unbound, and surfacing those inside an unrelated project made `decision verify` fire
on changes they had nothing to do with — one repository's decisions presented as governance for
another, which is the failure the memory scoping split exists to prevent. A check that cries
wolf is a check people learn to skip.

Ids are allocated across **both** scopes, so a project `ADR-004` and a Core `ADR-004` can never
both exist and mean different things.

---

## 📜 Decision Record Schema

The original eight fields are unchanged. Everything added is optional and defaults to `null` —
a v1 record loads, renders and searches exactly as before, and nothing is inferred to fill a
gap, because an ADR with a fabricated rationale is worse than one with an honest blank.

```json
{
  "id": "ADR-042",
  "decision": "Use Redis for session storage",
  "reason": "MySQL connection saturation was observed under production load",
  "alternatives": ["Database sessions", "Memcached"],
  "chosen": "Redis",
  "impact": "High",
  "status": "Accepted",
  "created_at": "2026-08-14 11:25:00",

  "problem": "Sessions in MySQL exhausted the connection pool at peak",
  "context": "Black Friday traffic, 4x normal concurrency",
  "evidence": "INC-1024 production incident",
  "author": "Fakrul",
  "agent": "Atlas",
  "confidence": 0.95,
  "related_files": ["src/session.ts"],
  "related_incidents": ["INC-1024"],
  "related_decisions": ["ADR-051"],
  "supersedes": null,
  "superseded_by": "ADR-051",
  "scope": "project",
  "project": "payments-api"
}
```

`coresentinel decision show <id>` reports how much of the schema a record actually fills.
Completeness is **reported, never enforced**: refusing to record a thin ADR just means it never
gets recorded at all.

**Statuses:** `Proposed` · `Accepted` · `Superseded` · `Rejected`. Only `Accepted` binds.

---

## 🚧 Contradiction Checking

```bash
coresentinel decision verify --change "switch from Redis to database sessions"
```

| Verdict | Meaning | Blocks |
| :--- | :--- | :--- |
| **`CONTRADICTS`** | The change proposes moving away from what an accepted decision chose | yes, exit 1 |
| **`REVISITS`** | The change proposes an alternative that was considered and rejected | yes, exit 1 |
| **`TOUCHES`** | The change concerns a governed choice without reversing it | no, exit 0 |
| **`CLEAR`** | No recorded decision governs this change | no, exit 0 |

This is a **lexical** check against the ledger, not a semantic reading of intent. It is
deliberately biased toward flagging — a false flag costs one review, a missed contradiction
costs the incident the decision was made to prevent — and every finding cites the ADR, the
reason recorded at the time and the evidence, so a reviewer can dismiss it in seconds.

Words too generic to identify a technology (`database`, `service`, `system`, `store`) never
trigger a finding on their own. Matching on those flags every sentence, which is the fastest
way to make the check worthless.

---

## ♻️ Superseding

Reversing a decision is legitimate. Reversing it invisibly is not.

```bash
coresentinel decision add --title "Move sessions to PostgreSQL" --reason "..." --chosen "PostgreSQL"
coresentinel decision supersede ADR-042 --by ADR-051 --reason "Load profile changed"
```

The link is written at **both** ends, so neither record reads as current on its own. A
superseded decision stops binding but stays in the ledger — the history of what was tried is
the part that stops it being tried again.

---

## ⚡ CLI Commands

```bash
coresentinel decision list [--query PostgreSQL] [--json]
coresentinel decision show ADR-042
coresentinel decision add --title "..." --reason "..." --chosen "..." \
  [--alts "..."] [--problem "..."] [--context "..."] [--evidence "..."] \
  [--author "..."] [--agent "..."] [--confidence 0.95] [--relates-to "src/a.ts,src/b.ts"]
coresentinel decision verify --change "..."
coresentinel decision supersede ADR-042 --by ADR-051 --reason "..."

coresentinel migrate decisions [--apply]   # give v1 records the new fields as explicit nulls
```
