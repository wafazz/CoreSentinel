"""
The agent registry — contracts, and the permissions they carry.

`squad-contracts.json` stays the source of truth and keeps every field it had.
The addition is a `permissions` block per contract, so an agent's authority is
machine-readable rather than a sentence of prose. A contract without one falls
back to the default set: read the filesystem, nothing else. That fallback is
deliberately useless rather than permissive — an undeclared agent should be
unable to do damage, not silently able to do everything.
"""

import json
from pathlib import Path

from coresentinel_core import CORE_ROOT
from coresentinel_core.agents import permissions as perms

CONTRACTS_FILE = CORE_ROOT / "squad-contracts.json"


def load(path=None):
    path = Path(path or CONTRACTS_FILE)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f).get("squad", [])
    except (OSError, json.JSONDecodeError, ValueError):
        return []


def names(path=None):
    return [contract.get("name") for contract in load(path)]


def get(name, path=None):
    key = str(name or "").strip().lower()
    return next((c for c in load(path) if str(c.get("name", "")).lower() == key), None)


def permissions_for(name, path=None, interactive=False):
    contract = get(name, path)
    if not contract:
        return perms.PermissionSet(interactive=interactive)
    return perms.PermissionSet.from_contract(contract, interactive)


def declares_permissions(contract):
    return bool((contract or {}).get("permissions", {}).get("levels"))


def audit(path=None):
    """Which contracts declare permissions, and which fall back to the default."""
    contracts = load(path)
    declared = [c["name"] for c in contracts if declares_permissions(c)]
    return {
        "total": len(contracts),
        "declared": declared,
        "defaulted": [c["name"] for c in contracts if not declares_permissions(c)],
        "escalation_holders": {
            c["name"]: sorted(p for p in perms.ESCALATION_ONLY
                              if c.get("permissions", {}).get("levels", {}).get(p, perms.DENY)
                              != perms.DENY)
            for c in contracts
            if any(c.get("permissions", {}).get("levels", {}).get(p, perms.DENY) != perms.DENY
                   for p in perms.ESCALATION_ONLY)
        },
    }
