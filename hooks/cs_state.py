#!/usr/bin/env python3
"""Shared per-session state for the CoreSentinel hooks."""
import json, os, re

DIR = os.path.expanduser("~/.claude/coresentinel-state")

# T2 surfaces from 02-team-protocol.md. Absolute, never a judgment call.
T2 = [
    (r"(^|/)(database/)?migrations?/", "schema/migrations"),
    (r"(^|/)(auth|guard|policies|policy|middleware)", "auth/authz"),
    (r"payment|billing|invoice|checkout|gateway|toyyibpay|bayarcash|billplz|stripe", "payments"),
    (r"tenant|landlord_id|scope", "tenant scoping"),
    (r"upload|storage/app|filesystem", "file upload"),
    (r"(^|/)(deploy|docker|nginx|\.github/workflows|\.env|supervisor|caddy)", "deploy config"),
    (r"routes/api|api/v\d|openapi|swagger", "public API"),
]


def path_for(session_id):
    sid = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "nosession")[:64] or "nosession"
    return os.path.join(DIR, sid + ".json")


def load(session_id):
    try:
        with open(path_for(session_id), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"t2": [], "blocked": False}


def save(session_id, state):
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(path_for(session_id), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except Exception:
        pass


def classify(path):
    """Return the T2 surface a path touches, or None."""
    p = (path or "").lower()
    if not p or "/node_modules/" in p or "/vendor/" in p or "/tests/" in p:
        return None
    for pattern, label in T2:
        if re.search(pattern, p):
            return label
    return None
