#!/usr/bin/env python3
"""CoreSentinel SessionStart gate.

Reports Core drift into the model's context at session start, so the failures
55-self-evolution.md is meant to catch surface automatically instead of waiting
to be noticed. Fail-open: any error exits 0 silently.
"""
import json, os, subprocess, sys

CS = os.environ.get("CORESENTINEL_DIR", os.path.expanduser("~/Desktop/CS"))


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs_state


def git(*a):
    try:
        return subprocess.run(["git", "-C", CS, *a], capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except subprocess.TimeoutExpired:
        cs_state.log_error(f"cs_session_start.git({a[0]}) timed out")
        return ""
    except OSError:                      # git absent or CS unreadable
        cs_state.log_error(f"cs_session_start.git({a[0]})")
        return ""


def main():
    if not os.path.isdir(os.path.join(CS, ".git")):
        return
    notes = []

    # Scan every untracked file, not just *.md. An earlier version filtered to
    # markdown and so reported none of this directory's own .py hooks — a check
    # for "operative file outside version control" that was blind to code.
    # --exclude-standard already honours .gitignore; NOISE covers what it misses.
    NOISE = ("__pycache__/", ".pyc", ".DS_Store", ".pytest_cache/", ".egg-info/")
    untracked = [f for f in git("ls-files", "--others", "--exclude-standard").splitlines()
                 if f and not any(n in f for n in NOISE)]
    if untracked:
        shown = ", ".join(untracked[:6])
        more = f" (+{len(untracked) - 6} more)" if len(untracked) > 6 else ""
        notes.append(f"{len(untracked)} UNTRACKED file(s) — in use but NOT in git, "
                     f"so not recoverable: {shown}{more}")

    counts = git("rev-list", "--left-right", "--count", "origin/main...HEAD").split()
    if len(counts) == 2:
        behind, ahead = counts
        branch = git("branch", "--show-current") or "HEAD"
        if behind.isdigit() and int(behind) > 0:
            notes.append(f"Core is {behind} commit(s) BEHIND origin/main on {branch}")
        if ahead.isdigit() and int(ahead) > 0:
            notes.append(f"Core has {ahead} unpushed commit(s) on {branch}")

    dirty = [l for l in git("status", "--short").splitlines() if l]
    if dirty:
        notes.append(f"{len(dirty)} uncommitted file(s) in the Core")

    try:
        md = open(os.path.expanduser("~/.claude/CLAUDE.md"), encoding="utf-8").read()
    except FileNotFoundError:
        md = None                        # no global rule file on this host
    except OSError:
        md = None
        cs_state.log_error("cs_session_start.read_claude_md")
    if md is not None and "Task Tiering" not in md:
        notes.append("CLAUDE.md carries NO Task Tiering block — setup.sh likely "
                     "overwrote it; re-render from the current Core")

    if not notes:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "CoreSentinel drift check:\n- " + "\n- ".join(notes),
    }}))


try:
    main()
except Exception:
    # Fail open: never block real work. Logged rather than swallowed (AP-001).
    cs_state.log_error("cs_session_start")
sys.exit(0)
