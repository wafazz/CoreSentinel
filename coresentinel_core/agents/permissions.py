"""
Agent permissions — declared, then enforced.

The README has claimed since v1 that "a read-only researcher cannot silently
write files". That was a statement about a JSON document: `squad-contracts.json`
records an `authority` string in prose, and nothing read it at runtime. An agent
could do anything the process could do.

A permission here is a capability an agent must be *handed*. The sandbox mediates
every read, write and command, so an ungranted operation fails at the point of
use rather than being trusted not to happen. Denials are recorded on the result
and written to the audit trail — a refusal nobody can see is indistinguishable
from an agent that simply never tried.

Default for every agent: read the filesystem, nothing else.
"""

FILESYSTEM_READ = "filesystem.read"
FILESYSTEM_WRITE = "filesystem.write"
SHELL_EXECUTE = "shell.execute"
NETWORK_ACCESS = "network.access"
GIT_COMMIT = "git.commit"
GIT_PUSH = "git.push"
DEPLOYMENT = "deployment"
PRODUCTION_ACCESS = "production.access"

PERMISSIONS = [FILESYSTEM_READ, FILESYSTEM_WRITE, SHELL_EXECUTE, NETWORK_ACCESS,
               GIT_COMMIT, GIT_PUSH, DEPLOYMENT, PRODUCTION_ACCESS]

DENY = "DENY"
ASK = "ASK"
LIMITED = "LIMITED"
ALLOW = "ALLOW"

LEVELS = [DENY, ASK, LIMITED, ALLOW]

# Deny by default. An agent that needs more says so in its contract, and the
# grant is visible in `coresentinel agent permissions <name>`.
DEFAULT_LEVELS = {name: DENY for name in PERMISSIONS}
DEFAULT_LEVELS[FILESYSTEM_READ] = ALLOW

# Permissions that are never granted by a contract alone. Escalating to these
# takes an explicit, recorded grant — the blast radius is the production system.
ESCALATION_ONLY = {GIT_PUSH, DEPLOYMENT, PRODUCTION_ACCESS}


class Decision:
    def __init__(self, permission, allowed, level, reason, scope=None):
        self.permission = permission
        self.allowed = allowed
        self.level = level
        self.reason = reason
        self.scope = scope

    def record(self):
        return {"permission": self.permission, "allowed": self.allowed,
                "level": self.level, "reason": self.reason, "scope": self.scope}

    def __bool__(self):
        return self.allowed

    def __repr__(self):
        return f"Decision({self.permission}, {'allow' if self.allowed else 'deny'})"


class PermissionSet:
    """What one agent may do, and under what limits."""

    def __init__(self, levels=None, scopes=None, interactive=False):
        self.levels = dict(DEFAULT_LEVELS)
        self.levels.update({k: v for k, v in (levels or {}).items()
                            if k in PERMISSIONS and v in LEVELS})
        # LIMITED without a scope is meaningless, and defaulting it to
        # "everything" would turn the safest-looking level into the widest one.
        self.scopes = {k: list(v) for k, v in (scopes or {}).items()}
        self.interactive = interactive

    @classmethod
    def from_contract(cls, contract, interactive=False):
        block = (contract or {}).get("permissions") or {}
        return cls(block.get("levels"), block.get("scopes"), interactive)

    def level(self, permission):
        return self.levels.get(permission, DENY)

    def check(self, permission, scope=None):
        if permission not in PERMISSIONS:
            return Decision(permission, False, DENY, "unknown permission", scope)

        level = self.level(permission)

        if level == ALLOW:
            return Decision(permission, True, level, "granted by contract", scope)

        if level == LIMITED:
            allowed_scopes = self.scopes.get(permission, [])
            if not allowed_scopes:
                return Decision(permission, False, level,
                                "LIMITED with no scope declared — nothing is in scope", scope)
            if scope is None:
                return Decision(permission, False, level,
                                f"LIMITED to {', '.join(allowed_scopes)}; no scope given", scope)
            if any(str(scope).startswith(prefix) or prefix == scope
                   for prefix in allowed_scopes):
                return Decision(permission, True, level,
                                f"within scope {allowed_scopes}", scope)
            return Decision(permission, False, level,
                            f"outside the granted scope {allowed_scopes}", scope)

        if level == ASK:
            if self.interactive:
                return Decision(permission, True, level, "approved interactively", scope)
            return Decision(permission, False, level,
                            "requires approval and this run is not interactive", scope)

        return Decision(permission, False, DENY, "not granted", scope)

    def grant(self, permission, level=ALLOW, scopes=None, reason=None):
        """Escalate one permission. Returns the record of what was granted."""
        if permission not in PERMISSIONS:
            raise ValueError(f"unknown permission '{permission}'")
        if level not in LEVELS:
            raise ValueError(f"unknown level '{level}'")
        if permission in ESCALATION_ONLY and not reason:
            raise ValueError(f"{permission} requires a stated reason to grant")

        self.levels[permission] = level
        if scopes:
            self.scopes[permission] = list(scopes)
        return {"permission": permission, "level": level,
                "scopes": self.scopes.get(permission), "reason": reason}

    def summary(self):
        return {name: {"level": self.level(name), "scopes": self.scopes.get(name)}
                for name in PERMISSIONS}

    def granted(self):
        return [name for name in PERMISSIONS if self.level(name) != DENY]

    def __repr__(self):
        return f"PermissionSet({', '.join(f'{k}={self.level(k)}' for k in self.granted())})"
