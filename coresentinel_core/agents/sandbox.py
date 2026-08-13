"""
The agent sandbox — where a permission stops being a declaration.

An agent is never handed the filesystem or a shell. It is handed this object,
and every operation goes through a check first. That is the difference between
`squad-contracts.json` saying Scout is read-only and Scout actually being unable
to write: the contract states it, the sandbox enforces it.

Two guarantees beyond the permission check:

  * every path is contained inside the project root, reusing the Phase 2
    containment rule, so `filesystem.write` never means "anywhere on disk";
  * every refusal is recorded. A denial nobody can see is indistinguishable from
    an agent that simply never tried, and the audit trail needs to tell those apart.
"""

from pathlib import Path

from coresentinel_core.agents import permissions as perms
from coresentinel_core.runtime import paths
from coresentinel_core.runtime.errors import PathSecurityError, CoreSentinelError

import coresentinel_exec as execution

READ_LIMIT = 400000


class PermissionDenied(CoreSentinelError):
    """An agent attempted something its permission set does not grant."""

    def __init__(self, decision):
        super().__init__(
            f"{decision.permission} denied: {decision.reason}",
            f"Grant it explicitly if intended: the contract currently says "
            f"{decision.level}")
        self.decision = decision


class AgentSandbox:
    """The only surface an agent gets. Everything it does passes through here."""

    def __init__(self, agent, permission_set, root=".", logger=None, on_denial=None):
        self.agent = agent
        self.permissions = permission_set
        self.root = Path(root).resolve()
        self.logger = logger
        self.on_denial = on_denial
        self.denials = []
        self.actions = []
        self.commands_run = []
        self.files_changed = []

    # ---------------------------------------------------------------- checks

    def _record_denial(self, decision, detail=None):
        record = decision.record()
        record.update({"agent": self.agent, "detail": detail})
        self.denials.append(record)
        if self.logger:
            self.logger.warn("permission denied", agent=self.agent,
                             permission=decision.permission, reason=decision.reason)
        if self.on_denial:
            self.on_denial(record)
        return record

    def allows(self, permission, scope=None):
        """Check without raising — for an agent that wants to degrade gracefully."""
        decision = self.permissions.check(permission, scope)
        if not decision.allowed:
            self._record_denial(decision, scope)
        return decision

    def require(self, permission, scope=None):
        decision = self.permissions.check(permission, scope)
        if not decision.allowed:
            self._record_denial(decision, scope)
            raise PermissionDenied(decision)
        return decision

    def _contain(self, path, permission):
        try:
            return paths.resolve_within(self.root, path, f"{self.agent} {permission}")
        except PathSecurityError as e:
            self.denials.append({"permission": permission, "allowed": False,
                                 "level": "CONTAINMENT", "reason": str(e.message),
                                 "agent": self.agent, "detail": str(path)})
            raise

    # ---------------------------------------------------------------- capabilities

    def read(self, path):
        self.require(perms.FILESYSTEM_READ, str(path))
        resolved = self._contain(path, perms.FILESYSTEM_READ)
        try:
            content = resolved.read_text(encoding="utf-8-sig", errors="replace")[:READ_LIMIT]
        except OSError as e:
            raise CoreSentinelError(f"could not read {path} ({e})", None)
        self.actions.append({"action": "read", "target": str(resolved)})
        return content

    def list_files(self, pattern="*"):
        self.require(perms.FILESYSTEM_READ, pattern)
        found = [str(p.relative_to(self.root)) for p in sorted(self.root.glob(pattern))
                 if p.is_file()]
        self.actions.append({"action": "list", "target": pattern, "detail": f"{len(found)} file(s)"})
        return found

    def write(self, path, content):
        self.require(perms.FILESYSTEM_WRITE, str(path))
        resolved = self._contain(path, perms.FILESYSTEM_WRITE)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(str(content), encoding="utf-8")
        relative = str(resolved.relative_to(self.root))
        self.actions.append({"action": "write", "target": relative})
        if relative not in self.files_changed:
            self.files_changed.append(relative)
        return resolved

    def execute(self, argv, timeout=None):
        """Run a command. The program name is the scope a LIMITED grant matches on."""
        argv = [str(a) for a in argv]
        program = Path(argv[0]).name if argv else ""
        self.require(perms.SHELL_EXECUTE, program)

        result = execution.run(argv, cwd=self.root,
                               timeout=timeout or execution.DEFAULT_TIMEOUT)
        self.commands_run.append(result.record())
        self.actions.append({"action": "execute", "target": result.display,
                             "detail": f"exit {result.exit_code}"})
        return result

    def git(self, *args):
        """git reads need only shell.execute; committing and pushing need their own grant."""
        subcommand = args[0] if args else ""
        if subcommand == "commit":
            self.require(perms.GIT_COMMIT, subcommand)
        elif subcommand == "push":
            self.require(perms.GIT_PUSH, subcommand)
        return self.execute(["git", *args])

    # ---------------------------------------------------------------- reporting

    def report(self):
        return {"actions": self.actions, "commands_run": self.commands_run,
                "files_changed": self.files_changed, "denials": self.denials}
