# Layered Memory Engine & Confidence Classification Protocol

> **Persistent, Classified Memory Architecture for AI Agents**  
> CoreSentinel replaces flat markdown logs with a structured 6-layer memory engine backed by explicit confidence scoring.

---

## 🧠 Memory Layers

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Working Memory    (memory/working.json)                  │ -> Current active task state
  ├─────────────────────────────────────────────────────────────┤
  │ 2. Session Memory    (memory/session.json)                  │ -> Current conversation context
  ├─────────────────────────────────────────────────────────────┤
  │ 3. Project Memory    (memory/project.json)                  │ -> Architecture & stack facts
  ├─────────────────────────────────────────────────────────────┤
  │ 4. Long-Term Memory  (memory/longterm.json)                 │ -> Historical codebase knowledge
  ├─────────────────────────────────────────────────────────────┤
  │ 5. Failure Memory   (memory/failures.json)                 │ -> Bugs, incidents & anti-patterns
  ├─────────────────────────────────────────────────────────────┤
  │ 6. Pattern Memory   (memory/patterns.json)                 │ -> Reusable engineering patterns
  └─────────────────────────────────────────────────────────────┘
```

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
```
