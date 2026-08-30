#!/usr/bin/env python3
"""Detect T2 surfaces from the file actually edited, not from the prompt.

The tier is otherwise declared by the model from the request, so "it's just a
small change" can route a payments edit into T0. This reads the diff target.
Fail-open: any error exits 0 silently.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs_state


def main():
    d = json.load(sys.stdin)
    ti = d.get("tool_input") or {}
    path = ti.get("file_path") or (d.get("tool_response") or {}).get("filePath") or ""
    surface = cs_state.classify(path)
    if not surface:
        return
    sid = d.get("session_id") or ""
    st = cs_state.load(sid)
    entry = f"{surface}: {os.path.basename(path)}"
    if entry in st["t2"]:
        return                      # already reported — do not repeat every edit
    st["t2"].append(entry)
    cs_state.save(sid, st)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"CoreSentinel: this edit touches a T2 surface ({entry}). Per "
            "02-team-protocol.md, T2 surfaces are absolute regardless of diff size — "
            "escalate to the full gates if you are running below T2. Tiers escalate "
            "mid-run and never de-escalate."),
    }}))


try:
    main()
except Exception:
    pass
sys.exit(0)
