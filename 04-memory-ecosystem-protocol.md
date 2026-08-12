# Memory Ecosystem Protocol — Recall, Lifecycle & Journal

> **What happens to a fact after it is recorded.**
> [04-layered-memory-protocol.md](./04-layered-memory-protocol.md) defines *where* memory lives.
> This protocol defines how it is **found again**, how it **ages**, and how it stays **small enough to read**.

A memory store that only ever grows is a memory store that eventually lies. Three failures
kill an agent's memory, and each has an engine here:

| Failure | Symptom | Engine |
| :--- | :--- | :--- |
| Memory nobody can search | The agent re-derives a fact it recorded last week | **Recall** |
| Memory that never expires | A stale fact is presented with the confidence it had a year ago | **Lifecycle** |
| Memory with no narrative | The agent knows *what* is true but not *what was done or why* | **Journal** |

---

## 🔎 Recall — ranked retrieval across everything

```bash
coresentinel recall "postgres migration"
coresentinel recall "auth" --layer project,longterm --min-confidence 0.9
coresentinel recall "rate limit" --json
```

One query searches all six fact layers, the ADR ledger and the session journal — a question
is never asked three times in three different commands.

**Ranking.** `score = (term coverage + phrase bonus) × confidence weight`

- **Term coverage** — the fraction of query terms the record matches, by token or substring,
  so `postgres` still finds `PostgreSQL`.
- **Phrase bonus** — `+0.25` when the exact query phrase appears.
- **Confidence weight** — scaled to `[0.5, 1.0]`, never to zero. A low-confidence fact you can
  see is safer than one you cannot: hiding an Unknown fact just means re-deriving it badly.

Exits `1` when nothing matches, so a shell script can branch on "we have no memory of this".

---

## ⏳ Lifecycle — confidence is a function of time

Every operation below is a **dry run until `--apply`**, and every destructive one takes a
snapshot first.

### Decay

```bash
coresentinel memory decay            # what would erode
coresentinel memory decay --apply
```

A fact loses **0.05 confidence per 30 days** it goes unverified, with a floor of **0.30**.

Decay is computed from `base_confidence` and age — not from the current value — so it is
**idempotent**: running it ten times in one day costs a fact exactly one day of trust.

**Exempt:** the `failures` layer (a bug that happened does not become less true with age) and
any fact marked `pinned`.

### Re-verification

```bash
coresentinel memory verify --match "node 18" --confidence 0.98
coresentinel memory add --layer project --fact "..." --pinned      # never decays
```

The other half of decay. Without it, confidence only ever falls and an agent that actually
re-checked `docker-compose.yml` has no way to say so. Re-verification restores the fact's
confidence, restarts the clock and clears the decay record.

It **requires a match string** — re-verifying everything at once would launder every guess in
the store into a verified fact.

### Promotion

```bash
coresentinel memory promote --apply
```

| Hop | Requirement | Why |
| :--- | :--- | :--- |
| `session` → `project` | confidence ≥ 0.90 | Both are project-scoped. "What I learned this conversation about this repo" becoming "what is true about this repo" is safe and automatic. |
| `project` → `longterm` | confidence ≥ 0.95, 14+ days old, **marked `transferable`** | This hop crosses from project scope into shared Core knowledge. |

The second hop is deliberately opt-in. A project fact is about *this* codebase by definition —
auto-promoting it would leak one repository's stack into every repository the Core governs,
which is the exact failure the scoping split exists to prevent. Mark the genuinely portable
lesson explicitly:

```bash
coresentinel memory add --layer project --transferable \
  --fact "Prisma migrations must run before seeding" --confidence 0.99 --source "INC-011"
```

Promoted facts carry `promoted_from` and `promoted_at`, so provenance survives the move.

### Consolidation

```bash
coresentinel memory consolidate --apply
```

Duplicates merge **within** a layer, then **across** the tier chain
(`working` → `session` → `project` → `longterm`), where the highest tier holding a fact owns it.

Merging keeps the **highest** confidence — never an average, never a boost. Three recordings
of the same guess do not make it a verified fact; they make one guess with `occurrences: 3`.
Sources are unioned into a `sources` list so no provenance is lost.

`failures` and `patterns` are outside the tier chain: identical wording in those layers is two
different claims, not one duplicate.

### Compaction

```bash
coresentinel memory compact --budget 150 --apply
```

Past the budget, a layer stops being readable context and becomes noise. Compaction folds the
**oldest facts below 0.90 confidence** into a single summary entry that keeps the count, the
date range and a five-fact sample.

Summarised, not deleted — and the pre-compaction snapshot makes the whole operation reversible.

### Snapshots

```bash
coresentinel memory snapshot --label "before the refactor"
coresentinel memory snapshots
coresentinel memory restore snap-20260812-170956 --apply
```

The manifest records **absolute** origin paths, so a snapshot restores correctly even though
project-scoped and Core-scoped layers live in different stores.

---

## 📓 Journal — the narrative the fact layers do not keep

```bash
coresentinel journal add --entry "Rewrote the token refresh path" --tags "auth,refactor"
coresentinel journal show --days 7
coresentinel journal archive --older-than 30 --apply
```

Facts record *what is true*. The journal records *what was done and why* — one file per day,
scoped to the bound project like every other project-scoped layer.

Archiving folds old day files into one file per month. Archived entries **stay searchable
through recall**; this compresses the file count, it does not discard history.

---

## 🧠 Session Briefing — read this first

```bash
coresentinel brief
coresentinel brief --json          # for an AI host to consume directly
```

The context an agent needs before its first action of a session:

- **Last task and status** from working memory — where the work stopped
- **Recent journal entries** — what was done and why
- **Established facts** (≥ 0.90) — safe to act on immediately
- **Needs verification** (< 0.50) — Unknown; write mutations stay blocked
- **Stale** (30+ days unverified) — re-verify before trusting
- **Known failures** — do not repeat these
- **Recent decisions** — the ADRs already settled

---

## 🔁 Recommended cadence

| When | Command |
| :--- | :--- |
| Start of every session | `coresentinel brief` |
| Before assuming anything | `coresentinel recall "<topic>"` |
| End of a work block | `coresentinel journal add --entry "..."` |
| Weekly | `coresentinel memory decay --apply && coresentinel memory consolidate --apply` |
| Monthly | `coresentinel memory promote --apply && coresentinel journal archive --apply` |
| When a layer gets noisy | `coresentinel memory compact --apply` |
