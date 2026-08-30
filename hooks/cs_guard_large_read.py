#!/usr/bin/env python3
"""CoreSentinel Standing Rule 9 — block whole-file reads of the oversized files.

These four cost more context than the rest of the Core combined, and context is
re-billed on every later turn. Denies with a reason pointing at grep / ranged
read. Fail-open: any error exits 0 silently (the read proceeds).
"""
import json, os, sys

OVERSIZED = {"Planning.md", "55-self-evolution.md", "README.md", "11-pattern-library.md"}


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs_state


def main():
    d = json.load(sys.stdin)
    ti = d.get("tool_input") or {}
    path = ti.get("file_path") or ""
    if not path or os.path.basename(path) not in OVERSIZED:
        return
    if "/Desktop/CS/" not in path and "/CoreSentinel/" not in path:
        return          # only guard the Core's own copies
    if ti.get("offset") is not None or ti.get("limit") is not None:
        return          # already a ranged read — that is the desired behaviour
    try:
        kb = os.path.getsize(path) // 1024
    except OSError:
        kb = 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"CoreSentinel Standing Rule 9: {os.path.basename(path)} is ~{kb} KB — "
            "more context than the rest of the Core combined, re-billed on every "
            "later turn. Grep it, or re-read with offset/limit for just the section "
            "you need."),
    }}))


try:
    main()
except Exception:
    # Fail open: never block real work. Logged rather than swallowed (AP-001).
    cs_state.log_error("cs_guard_large_read")
sys.exit(0)
