# AutomationSentinel — QA automation expansion pack for MemoryCore

> **Status**: Delivered — installers verified
> **Last Updated**: 2026-08-10

## Business Context
- **Client**: personal project
- **Status**: maintenance
- **Priority**: medium
- **Revenue Model**: n/a (internal tooling)
- **Deployed**: No — installed locally into `CORE/`

## Overview
- **Root**: `C:\Users\fakrul.hakim\OneDrive - Daythree Digital Berhad\Desktop\Day3-Project\MemoryCore\AutomationSentinel`
- **Stack**: Markdown protocol templates + Bash / PowerShell installers
- **Type**: agent-memory expansion pack (add-on, sits beside AgenticCore)
- **Auth**: n/a
- **Database**: n/a

## Key Patterns
- Templates carry `{AGENT_NAME}` / `{USER_NAME}` / `{MEMORY_PATH}` placeholders; both
  installers read `memorycore.conf` for the values and render into the memory folder.
- `README.md` is repo documentation and is explicitly excluded from what gets installed —
  both installers filter it by name.
- Existing destination files are **kept**, never overwritten, unless `-Force` / `--force`.
  This is load-bearing: the pattern library ships near-empty and fills up over time.
- The installer prints the `00-identity.md` protocol lines but does **not** write them.
  That last step is manual and easy to forget — see Anti-Patterns.

## Completed
1. Six protocol files authored (sentinel identity, test, flaky, test review, test data,
   pattern library).
2. Both installers written and installed into `CORE/`.
3. 2026-08-10 — installer verification battery (11 checks, both shells). Two real bugs
   found and fixed in `install.sh`; `install.ps1` passed clean.
4. 2026-08-10 — the six protocols registered in `CORE/00-identity.md` (entries 13–18) and
   `"Iris test"` added to the Commands list in global `CLAUDE.md`.

## Remaining
- Pattern library and framework-gotcha sections are intentionally near-empty — fill from
  real project work, not speculation.
- `02-team-protocol.md` and `40-security-protocol.md` are referenced by `CLAUDE.md`
  but still missing from the `00-identity.md` protocol list (same drift class, unfixed).

## Anti-Patterns (This Project)
- **Never trust "installed" to mean "wired up".** The pack was fully copied into `CORE/`
  with placeholders correctly rendered, yet no loaded context referenced it, so Sentinel
  mode was unreachable. The installer's final instruction is printed to a terminal that
  nobody re-reads. If a protocol is not listed in `00-identity.md` or `CLAUDE.md`, it does
  not exist as far as the agent is concerned.
- **Never interpolate `MEMORY_PATH` into `sed`.** `memorycore.conf` stores a Windows path,
  and GNU sed reads `\U` in a replacement as "uppercase the rest of the line". See the
  matching entry in `55-self-evolution.md`.
- **Do not verify only one installer.** `install.ps1` passing said nothing about
  `install.sh`; both bugs were bash-only.

## Work Log
### 2026-08-10 — Installer verification (Sentinel mode)
- Ran 11 checks against throwaway memory folders: fresh install, placeholder rendering,
  BOM check, idempotence, user-content survival, `--force` reset, README exclusion,
  bad-flag rejection, `--help`, POSIX path, Windows backslash path.
- **Fixed** `install.sh` sed corruption: escape `\ & |` in replacements via `esc_repl()`,
  and switched all three substitutions to the `|` delimiter.
- **Fixed** `install.sh` conf discovery: added `"$HOME"/OneDrive*/Desktop/CORE/` so a
  OneDrive-redirected Desktop is found (bare `./install.sh` previously always failed here).
- Confirmed the real `CORE/` was untouched by the test runs (mtimes unchanged, no-overwrite
  guard held).
