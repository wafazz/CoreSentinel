# Session Memory Format

> Reference template for session memory structure. Do NOT modify this file during sessions.
> Use this format when creating/resetting `session-memory.md` in any project.

---

## How It Works
- Each project can have a `session-memory.md` in its root directory
- Iris reads it at session start for instant context restoration
- When session memory exceeds **500 lines**, perform an auto-reset:
  1. Preserve only the `## Session Recap` section
  2. Clear everything else
  3. Rebuild from this template with the recap carried over
- This keeps sessions lightweight and prevents context bloat

---

## Template

```markdown
# Session Memory - [Project Name]
> Last updated: [YYYY-MM-DD HH:MM]

## Session Context
- **Project**: [Project name]
- **Profile**: [Path to MemoryCore profile]
- **Branch**: [Current git branch]
- **Status**: [active / paused / blocked]
- **Focus**: [One-line summary of current work]

## Current Tasks
- [ ] [Task 1 description]
- [ ] [Task 2 description]
- [x] [Completed task]

## Working Memory
### Active Context
- [Key detail the agent needs to remember for current work]
- [File paths currently being modified]
- [Patterns or conventions discovered this session]

### Decisions Made
- [Decision]: [Reason] (so we don't revisit it)

### Blockers / Open Questions
- [Anything unresolved that needs user input]

## Recent Changes
| File | Change | Status |
|---|---|---|
| [path/to/file] | [What changed] | [done/wip] |

## Session Recap
> This section survives resets. Keep it under 30 lines.

### What Was Done
- [Summary of completed work]

### Where We Left Off
- [Exact point to resume from]
- [Any in-progress work state]

### Key Context for Next Session
- [Critical info that must carry over]
- [Any gotchas or things to watch out for]
```

---

## Reset Protocol

When `session-memory.md` exceeds 500 lines:

1. **Save** the current `## Session Recap` content
2. **Clear** the entire file
3. **Rebuild** from this template
4. **Paste** the saved recap back into `## Session Recap`
5. **Fill in** `## Session Context` with current state
6. **Continue** working — no context lost

## When to Update
- **Start of session**: Read existing session memory, update status to `active`
- **After completing a task**: Check off in Current Tasks, add to Recent Changes
- **After a key decision**: Log in Decisions Made
- **End of session**: Update Session Recap with summary
- **At 500 lines**: Trigger reset protocol
