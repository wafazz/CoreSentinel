# Layered Memory Engine & Confidence Classification Protocol

> **Persistent, Classified Memory Architecture for AI Agents**  
> CoreSentinel replaces flat markdown logs with a structured 6-layer memory engine backed by explicit confidence scoring.

---

## 🧠 Memory Layers

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Working Memory    (working.json)    [PROJECT]            │ -> Current active task state
  ├─────────────────────────────────────────────────────────────┤
  │ 2. Session Memory    (session.json)    [PROJECT]            │ -> Current conversation context
  ├─────────────────────────────────────────────────────────────┤
  │ 3. Project Memory    (project.json)    [PROJECT]            │ -> Architecture & stack facts
  ├─────────────────────────────────────────────────────────────┤
  │ 4. Long-Term Memory  (longterm.json)   [CORE]               │ -> Historical codebase knowledge
  ├─────────────────────────────────────────────────────────────┤
  │ 5. Failure Memory    (failures.json)   [CORE]               │ -> Bugs, incidents & anti-patterns
  ├─────────────────────────────────────────────────────────────┤
  │ 6. Pattern Memory    (patterns.json)   [CORE]               │ -> Reusable engineering patterns
  └─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Memory Scoping

CoreSentinel governs many repositories from one Core. Layers describing **this codebase and this task** belong to the project; layers holding knowledge that **transfers between projects** stay in the Core.

| Scope | Layers | Location |
| :--- | :--- | :--- |
| **Project** | `working`, `session`, `project` | `<project>/.coresentinel/memory/` |
| **Core** | `longterm`, `failures`, `patterns`, `decisions` | `<CoreSentinel>/memory/` |

**Resolution.** A project-scoped layer resolves by walking up from the working directory looking for `.coresentinel/config.json` — the same way git looks for `.git`. If a bound project is found, the layer lives there. If not, it falls back to the Core store, so an unbound directory behaves exactly as before.

```bash
coresentinel memory show                 # scope resolved from the current directory
coresentinel memory show ~/code/api      # scope resolved from a specific project
coresentinel memory add --layer project --fact "..." --project ~/code/api
```

Every write reports which store it used, and `coresentinel memory show` labels each layer `project scope` or `core scope`. Scope is never silent.

> **Why this matters:** without the split, running `coresentinel init` across ten repositories piles ten projects' stack facts into one global `project.json`. The agent then reads another project's framework list as though it described the one in front of it.

A project's memory lives inside the repository, so committing `.coresentinel/memory/` shares verified project facts with your team. Add it to `.gitignore` instead if you would rather keep it local.

---

## 📊 Confidence Classification Rules

Every fact recorded in CoreSentinel carries a confidence score from `0.00` to `1.00`:

| Confidence Score | Category | Meaning & Action Protocol |
| :--- | :--- | :--- |
| **0.90 – 1.00** | **Known** | Empirically verified from config files (`package.json`, `git status`). Can be acted upon immediately. |
| **0.50 – 0.89** | **Assumed** | Inferred hypothesis based on surrounding code. Requires verification before modifying core interfaces. |
| **0.00 – 0.49** | **Unknown** | Unverified assumption. Blocked from write mutations until verified. |

---

## ⚡ Commands

```bash
# Display Layered Memory & Confidence Matrix
coresentinel memory show

# Add a verified fact
coresentinel memory add --layer project --fact "Project uses PostgreSQL" --confidence 0.98 --source "docker-compose.yml"

# A fact that must never decay, or one portable enough to leave project scope
coresentinel memory add --layer project --fact "..." --confidence 0.99 --source "..." --pinned
coresentinel memory add --layer project --fact "..." --confidence 0.99 --source "..." --transferable
```

---

## ♻️ What happens next

This protocol defines **where** memory lives. What happens to a fact *after* it is recorded —
how it is searched, how its confidence ages, when it is promoted, merged or compacted, and how
every one of those operations is reversed — is governed by
[04-memory-ecosystem-protocol.md](./04-memory-ecosystem-protocol.md).

```bash
coresentinel brief                       # where the work left off
coresentinel recall "<topic>"            # search every layer, decision and journal entry
coresentinel memory decay --apply        # confidence erodes until re-verified
coresentinel memory promote --apply      # facts that survive scrutiny move up a tier
```
