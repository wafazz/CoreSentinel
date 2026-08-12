# Coding Workflow Guide (Claude Pro)

## 1. Plan Before You Start
Write down all tasks in order of priority before opening Claude Code. Group related tasks together into one session.

```
Bad (wastes sessions):
  Session 1: "add variant to product"
  Session 2: "oh also add variant to checkout"
  Session 3: "fix the stock control for variants too"

Good (one session):
  Session 1: "Implement full product variation feature"
  (give the complete plan upfront)
```

## 2. Session Budget Strategy

| Priority | Sessions | Use For |
|---|---|---|
| Main Build | 1-2 | Big features, multi-file changes |
| Bug Fixes | 1 | Group ALL bugs into one session |
| Quick Tasks | 1 | Small UI tweaks, text changes |
| Reserve | 1 | Emergencies only |

## 3. Talk Efficiently
Give full context upfront. One detailed message beats 10 small ones.

```
Bad (burns tokens fast):
  "change the button" → "no the other button" → "make it red" → "also add icon"

Good (1 message):
  "In stock-control.php, change the Add Stock button:
   make it red, add a plus icon, move it below the table"
```

## 4. Use Plan Mode for Big Features
For anything touching 3+ files, say "Plan this feature first before coding."
- Agent researches first (cheaper reads) before writing (expensive outputs)
- You approve the plan before code is written
- No wasted rewrites

## 5. Batch Requests
Collect all small pending items and do them in one message:
> "Do all of these:
> 1. Fix the checkout undefined var warning
> 2. Add variant name to order page
> 3. Sort stock control by ID
> 4. Show dropdown arrow on variant selector"

## 6. Daily Workflow Template

```
Morning:
  Session 1 (Main)  - Plan + build the biggest feature
  Session 2 (Fixes) - Batch all bugs/tweaks from testing

Afternoon:
  Session 3 (Main)  - Continue feature OR start next one
  Session 4 (Reserve) - Only if urgent

End of day:
  Save memory (agent auto-saves)
  "show stats" (check token usage)
```

## 7. Token-Saving Tips

| Do This | Not This |
|---|---|
| Give complete requirements in one message | Drip-feed one requirement at a time |
| Say "fix all warnings in this file" | Fix warnings one by one |
| Provide the file path | Make the agent search for it |
| Say "same pattern as [file]" | Re-explain the same UI pattern |
| Use plan mode for big tasks | Let agent code then redo it |

## 8. Switch Models to Save Quota

| Task Type | Use Model | Why |
|---|---|---|
| Big features, multi-file | Opus | Best quality |
| Bug fixes, small edits | Sonnet | Good enough, saves quota |
| Search, read, quick questions | Haiku | Fastest, cheapest |

Switch model anytime: type `/model` in Claude Code.
