#!/usr/bin/env python3
"""Block finishing once when a T2 surface was edited, so the gate is not skipped.

Loop-safe by construction: the block is recorded in session state and this hook
blocks AT MOST ONCE per session. A second Stop always passes, so the session can
never be trapped. Fail-open: any error exits 0 silently.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cs_state


def main():
    d = json.load(sys.stdin)
    sid = d.get("session_id") or ""
    st = cs_state.load(sid)
    if not st.get("t2") or st.get("blocked"):
        return                      # nothing to gate, or already gated once
    st["blocked"] = True
    cs_state.save(sid, st)
    touched = "; ".join(st["t2"][:6])
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"CoreSentinel T2 gate. This session edited T2 surfaces ({touched}). "
            "Per 02-team-protocol.md those require Phase 6 Security (Argus, Cipher, "
            "Aegis) before the work is done. Either run the security gate now "
            "(/security-review) and report what it found, or state plainly to Fakrul "
            "that a T2 surface was changed without it. This gate fires once per "
            "session and will not block you again."),
        "systemMessage": f"CoreSentinel: T2 surface touched ({touched}) — security gate required.",
    }))


try:
    main()
except Exception:
    # Fail open: never block real work. Logged rather than swallowed (AP-001).
    cs_state.log_error("cs_stop_gate")
sys.exit(0)
