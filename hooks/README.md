# CoreSentinel Enforcement Hooks

Protocol files are advisory — they work only if the model reads them and chooses
to comply. These four hooks make the highest-stakes rules structural instead.

| Hook | Event | Enforces |
|---|---|---|
| `cs_session_start.py` | `SessionStart` | Reports Core drift: untracked protocol files, ahead/behind `origin/main`, uncommitted files, and a `CLAUDE.md` missing its Task Tiering block (i.e. `setup.sh` overwrote it). |
| `cs_guard_large_read.py` | `PreToolUse` / `Read` | Standing Rule 9 — denies whole-file reads of `Planning.md`, `55-self-evolution.md`, `README.md`, `11-pattern-library.md`. A ranged read (`offset`/`limit`) passes. |
| `cs_t2_detect.py` | `PostToolUse` / `Write\|Edit` | Classifies the **edited path** against the T2 surfaces in `02-team-protocol.md`. The tier is otherwise declared from the prompt, so "it's just a small change" could route a payments edit into T0. This reads the diff target instead. |
| `cs_stop_gate.py` | `Stop` | Blocks finishing once when a T2 surface was edited, requiring the Phase 6 security gate or an explicit statement that it was skipped. |

`cs_state.py` holds the shared per-session state and the T2 pattern table.

## Design rules

- **Fail-open.** Every hook exits 0 with no output on any error, including
  malformed stdin. A broken hook must never block real work.
- **Loop-safe.** `cs_stop_gate.py` records that it blocked and blocks **at most
  once per session** — a second `Stop` always passes, so a session can never be
  trapped. This is the property to preserve in any future change.
- **Narrow.** The read guard only fires on the four named files inside a Core
  checkout; `node_modules`, `vendor` and `tests` are excluded from T2 matching.

State lives in `~/.claude/coresentinel-state/<session_id>.json` and is disposable.

## Install

Merge into `~/.claude/settings.json` (this file is personal and not in the repo —
back it up first; do not replace existing keys):

```json
"hooks": {
  "SessionStart": [{"hooks":[{"type":"command","command":"python3 ~/Desktop/CS/hooks/cs_session_start.py","timeout":10}]}],
  "PreToolUse":   [{"matcher":"Read","hooks":[{"type":"command","command":"python3 ~/Desktop/CS/hooks/cs_guard_large_read.py","timeout":10}]}],
  "PostToolUse":  [{"matcher":"Write|Edit","hooks":[{"type":"command","command":"python3 ~/Desktop/CS/hooks/cs_t2_detect.py","timeout":10}]}],
  "Stop":         [{"hooks":[{"type":"command","command":"python3 ~/Desktop/CS/hooks/cs_stop_gate.py","timeout":10}]}]
}
```

Use absolute paths if `~` is not expanded by your host. Review or disable them
any time with `/hooks`. Set `CORESENTINEL_DIR` if the Core is not at `~/Desktop/CS`.
