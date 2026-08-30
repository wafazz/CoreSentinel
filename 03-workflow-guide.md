# Coding Workflow Guide
> How to spend a session. Updated for the current Claude Code harness — skills, subagents, plan mode, background work.

The old version of this file optimised for a fixed pool of "sessions" on Claude Pro
and told you to downgrade the model to save quota. Both assumptions are gone. What
actually costs you now is **context** and **rework**, not session count.

---

## 1. Plan Before You Start

Write the tasks down in priority order before opening Claude Code, and group related
ones into a single run.

```
Bad (three rounds of re-reading the same files):
  Run 1: "add variant to product"
  Run 2: "oh also add variant to checkout"
  Run 3: "fix the stock control for variants too"

Good (one run, files read once):
  "Implement full product variation feature"  + the complete plan upfront
```

The cost is not the request. It is that each new run re-reads the same files cold.

---

## 2. Talk Efficiently

Give full context upfront. One detailed message beats ten small ones.

```
Bad:   "change the button" → "no the other button" → "make it red" → "also add icon"
Good:  "In stock-control.php, change the Add Stock button: make it red,
        add a plus icon, move it below the table"
```

| Do this | Not this |
|---|---|
| Complete requirements in one message | Drip-feed one at a time |
| "Fix all warnings in this file" | Fix them one by one |
| Give the file path | Make Iris search for it |
| "Same pattern as [file]" | Re-explain the pattern |
| Plan mode for big tasks | Let her code it, then redo it |

---

## 3. Pick the Right Mode of Work

| Situation | Use | Why |
|---|---|---|
| Touching 3+ files, or design not settled | **Plan mode** | Research is cheap, rewrites are not. Approve the plan before code exists. |
| A known, bounded edit | Just ask | Plan mode on a one-liner is overhead |
| Answering "where/does this exist?" across many files | **`Explore` agent** | Returns the conclusion, not the file dumps — keeps your context clean |
| A long build/test/deploy | **Background task** | Keeps working across turns; you get notified on exit |
| Repeating a check on an interval | **`loop` skill** | `/loop 5m <cmd>` — do not hand-poll |
| A scheduled or unattended run | **`schedule` skill** | Cron-backed cloud agent |

---

## 4. Use the Skills — They Replace Hand-Walking

The single biggest efficiency change: a host skill already does much of what the
protocols describe in prose. See [Skill Layer Protocol](./18-skills-protocol.md).

| Instead of | Run |
|---|---|
| Reading a diff line by line for bugs | `/code-review` |
| Hunting duplication by hand | `/simplify` |
| Walking the security checklist blind | `/security-review` |
| Guessing a Claude model ID or price | the `claude-api` skill — **always** |
| "From now on, whenever X happens…" | `/update-config` — this needs a **hook**, memory cannot do it |
| Permission prompts interrupting a long run | `/fewer-permission-prompts` |

---

## 5. Model Selection

Switch anytime with `/model`. Current families: **Opus 5** (deepest reasoning),
**Sonnet 5**, **Haiku 4.5** (fastest), **Fable 5**. `/fast` toggles fast mode on
Opus — faster output, *not* a downgrade to a smaller model.

| Task | Model |
|---|---|
| Architecture, multi-file features, hard debugging | Opus 5 |
| Routine feature work, bounded fixes | Sonnet 5 |
| Search, file reads, quick lookups | Haiku 4.5 |

Do not downgrade mid-task to save money on a problem the smaller model will get
wrong — a wrong answer costs a full rerun. Downgrade **between** tasks, not inside one.

---

## 6. Token Economics — Manage Context, Not Sessions

Measured on a real session (Brand New ERP, 2026-08-30):

| | |
|---|---|
| Unique content produced | ~1.3M tokens |
| Cache reads billed | **1,203,276,429 tokens** |
| Amplification | **~900x** |

Context size that session: **22,124** on the first turn, **435,918** median, **997,157** peak.

**~99% of spend is cache re-reads, not new content.** Every turn re-reads the whole
accumulated context. So the true cost of anything you put in context is not its size —
it is **its size multiplied by every turn that follows it**. A turn at 436k costs roughly
20x the same turn at 22k.

Four levers, highest impact first:

1. **Start a fresh conversation for an unrelated task.** This outweighs the other three
   combined. Carrying ERP context into a CSS fix bills the whole ERP transcript on every
   turn of the CSS work. `/clear` between unrelated tasks.
2. **Delegate wide reads to an agent.** The dumps land in the agent's context, not yours,
   so they are never re-billed. Reading 30 files inline costs ~60k that is re-read every
   remaining turn — 500 turns later that is ~30M. The same work delegated costs ~30k once
   plus a ~1k summary: **~530k, roughly 50x cheaper.** Delegation gets *cheaper* the
   longer the session runs.
3. **Do not rewrite whole files.** `tool_use` was 66.9% of unique content — larger than
   all tool results combined — mostly `Write`/`Edit` carrying full file bodies. Prefer a
   narrow `Edit`; use `sed` or a script for mechanical bulk changes.
4. **Cap exploratory output.** The largest single tool results that session were 73k, 72k
   and 56k characters. Each became a permanent context resident, re-billed on every later
   turn. Pipe exploration through `head`/`grep`.

### What this does NOT mean
Do not artificially split one task across conversations. Long work is summarised
automatically and continues across the boundary — chopping a feature in half just pays
to rebuild the same context twice. **Split by topic, never mid-task.**

---
## 7. Daily Shape

```
Morning
  Plan + build the biggest feature      (plan mode → build → Phase 4 tests)
  Batch every bug and tweak from testing into one run

Afternoon
  Continue the feature, or start the next
  Review + security gates before anything ships   (/code-review, /security-review)

End of day
  Phase 8 persistence — Iris writes what the project taught, and says which files
  "show stats" — token usage
```

Phase 8 is the step that gets silently skipped. See
[Team Protocol](./02-team-protocol.md) — "saved to memory" with no file list is not a report.
