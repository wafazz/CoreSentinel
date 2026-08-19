# AgenticCore (MemoryCore OpenSource) â€” Portable memory system for AI coding agents

> **Status**: Active Development â€” Portability release
> **Last Updated**: 2026-08-10

## Business Context
- **Client**: personal project (open source)
- **Status**: active
- **Priority**: medium
- **Revenue Model**: none (MIT licensed)
- **Deployed**: No (GitHub repo)

## Overview
- **Root**: `C:\Users\fakrul.hakim\OneDrive - Daythree Digital Berhad\Desktop\Day3-Project\MemoryCore\AgenticCore`
- **Stack**: Markdown + Bash + PowerShell + Python 3
- **Type**: developer tooling / agent memory framework
- **Auth**: n/a
- **Database**: n/a (flat markdown files)

## Key Patterns
- **Single source of truth â†’ rendered adapters**: `core/AGENT.md` is the only place rules
  are written. `setup.sh` / `setup.ps1` render it into each tool's instruction file with
  `{AGENT_NAME}` / `{USER_NAME}` / `{MEMORY_PATH}` substituted. Never hand-edit an adapter.
- **Tool target table**: one lookup table per script maps tool key â†’ global path + project
  path + optional front matter. Adding a tool = one row in each script.
- **Two-tier install scope**: `global` writes to `~/.<tool>/...`; `project` writes into a
  repo. Tools with no user-wide file (Cursor, Copilot, Cline, Aider) are project-only.
- **Non-destructive re-runs**: install keeps existing memory files; `--sync` only
  regenerates adapters + stats script. Accumulated knowledge is never clobbered.
- **Config-driven sync**: `memorycore.conf` in the memory folder stores agent/user/path/
  tools/scope/project_dir, read by both scripts. A `--sync` naming an explicit scope/dir
  is a one-off render and deliberately does NOT write the config back.

## Completed
1. Moved `.claude/CLAUDE.md` â†’ `core/AGENT.md`, `.claude/agent-stats.py` â†’ `core/agent-stats.py`
2. Multi-tool installers (`setup.sh` + `setup.ps1`) covering 10 tools, with `--sync`,
   `--scope project`, `--list-tools`, `--force-memory`, non-interactive flags
3. De-branded memory files (workflow guide, init protocol, self-evolution)
4. `agent-stats.py` made multi-tool (Claude/Codex/Antigravity/Gemini) and Windows-safe
5. README rewritten with tool support matrix and per-platform install paths

## Remaining
- Verify Antigravity's real global-rules path (`~/.antigravity/AGENTS.md` is best-effort)
- Codex/Gemini session-log parsing is written generically but untested against real logs

## Anti-Patterns (This Project)
- **Never test an installer's `global` scope against the real `$HOME`.** It overwrites
  `~/.claude/CLAUDE.md` and friends. Use `HOME=<sandbox> bash setup.sh ...`, or test with
  `--scope project --dir <tmp>`.
- **Never render a Windows path into a non-raw Python string literal.** `C:\Users\...`
  becomes an invalid `\U` escape. The `{MEMORY_PATH}` placeholder in `agent-stats.py`
  sits inside `r"..."` for this reason, and must stay out of the module docstring.
- **PowerShell variables are case-insensitive.** `$labels = <path>` silently destroyed the
  `$Labels` tool-name hashtable, producing blank output. Distinct names, not distinct case.
- **Bash `for` loop variables are global.** A helper looping on `$t` clobbers the caller's
  `$t`, so error messages named the wrong tool. Use `$_known` style names inside helpers.
- **Handle a flag's action after arg parsing, not inside the loop.** `--list-tools` acted
  immediately, so a later `--scope project` was ignored.
- **When restoring saved config, explicit CLI flags must still win.** Sourcing
  `memorycore.conf` silently overwrote `--tools`, so `--sync --tools claude,codex` could
  not add a tool. Guard *every* restored field with an "was it passed?" flag, not just the
  one you happen to test.
- **Always pass `encoding="utf-8"` when reading JSONL on Windows.** The original stats
  script used bare `open()`; cp1252 choked on the first multi-byte char and the blanket
  bare generic exception handler (`except Exception: ...`) swallowed it, truncating every session file (line 30 of 346)
  and under-reporting totals by ~50x.

## Work Log
### 2026-08-10 - Gemini + Cursor adapters
- TOOLS now `claude codex antigravity gemini cursor`; `~/.gemini/GEMINI.md` rendered
- Cursor has no user-wide instruction file â€” it is project-scope only. Rendered
  `.cursor/rules/memorycore.mdc` into DAISYX with `alwaysApply: true` front matter.
  Every new repo needs its own `-Sync -Scope project -Dir <repo> -Tools cursor`.

### 2026-08-10 - Codex CLI on PATH
- Codex desktop app bundles the CLI at
  `%LOCALAPPDATA%\OpenAI\Codex\bin\<version-hash>\codex.exe` â€” never on PATH, and the
  folder name changes on every update
- Shim `C:\Users\fakrul.hakim\bin\codex.cmd` resolves the newest hashed dir at call time
  (`dir /b /ad /o-d`), so updates don't break it. `~/bin` was already first on PATH.
- `~/.codex/AGENTS.md` already carries the MemoryCore render, so terminal Codex boots
  with the same Iris identity as Claude Code

### 2026-08-10 - Antigravity adapter activated
- `memorycore.conf` TOOLS bumped `claude codex` â†’ `claude codex antigravity`
- Rendered `~/.antigravity/AGENTS.md` (global, still unverified) and a project-scope
  `AGENTS.md` at the DAISYX repo root, which is the reliable read path
- Antigravity constraint: agent is sandboxed to workspace folders, so the CORE folder
  must be added as a second workspace folder or every protocol link resolves to nothing

### 2026-08-10 - Portability release
- Restructured repo so the same agent identity installs into Claude Code, Codex,
  Antigravity, Gemini CLI, Cursor, Windsurf, Copilot, Cline, Aider and generic AGENTS.md
- Added `setup.ps1` for native Windows install; bash and PowerShell renders verified
  byte-identical apart from the platform-specific sync hint
- Fixed 6 bugs found during testing (see Anti-Patterns); stats parser verified against
  ground truth on 12 real session files â€” tokens, tool calls and message counts all match

