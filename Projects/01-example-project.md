# CoreSentinel Demo App — Sample Open Source Project Profile

> **Status**: Active Development — Phase 1
> **Last Updated**: 2026-08-12

## Business Context
- **Client**: CoreSentinel Open Source Project
- **Status**: active
- **Priority**: high
- **Revenue Model**: Open Source (MIT)
- **Deployed**: Yes (https://github.com/example/coresentinel)

## Overview
- **Root**: `C:/Users/username/Desktop/CoreSentinel`
- **Stack**: Markdown + Python + Shell/PowerShell
- **Type**: Agent Memory & Protocol System
- **Auth**: None (Local System)
- **Database**: File-based (Markdown & JSON)

## Key Patterns
<!-- Document project-specific patterns and conventions here -->
- Single source of truth in `<CORESENTINEL_PATH>`
- Autonomous squad phase gates (0 to 8)
- Self-evolution tracking anti-patterns and learned skills

## Completed
1. Scaffolding & core protocol migration
2. Setup scripts for multi-tool binding (Claude Code, Antigravity, Gemini, Codex, Cursor, Windsurf)

## Remaining
- Community feature requests & additional tool adapters

## Anti-Patterns (This Project)
- **Never hardcode user home paths in protocol markdown files.** Always use environment variable expansion or template placeholders rendered during `setup.ps1` / `setup.sh`.

## Work Log
### 2026-08-12 — Initial CoreSentinel Repository Setup
- Initialized CoreSentinel memory core from production memory core.
- Packaged 27 core protocols, 17-specialist squad rules, sentinel QA mode, and token stats engine.
