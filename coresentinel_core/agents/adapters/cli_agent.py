"""
CLI agent adapter — the transport most coding assistants actually offer.

The command comes from the registry as an argv template, so adding a host is a
JSON entry rather than a code change. `{prompt}` is substituted as a single
argument, never interpolated into a string that a shell would then re-split:
an objective containing a quote is a normal objective, not an injection.
"""

from pathlib import Path

from coresentinel_core.agents import protocol
from coresentinel_core.agents import permissions as perms
from coresentinel_core.agents.adapters.base import AgentAdapter

import coresentinel_exec as execution

PROMPT_TOKEN = "{prompt}"
DEFAULT_TIMEOUT = 300


class CliAgentAdapter(AgentAdapter):
    transport = "cli"
    permission = perms.SHELL_EXECUTE

    def program(self):
        command = self.profile.get("command") or []
        return command[0] if command else self.profile.get("detect")

    def scope(self):
        # The basename, matching what the sandbox checks at execute time. Scoping
        # the pre-check on a full path would deny an allowed program purely for
        # being invoked by absolute path.
        program = self.program()
        return Path(program).name if program else self.id

    def available(self):
        command = self.profile.get("command")
        if not command:
            return False, "no invocation command is declared in adapters.json"
        program = self.program()
        if not execution.available(program):
            return False, f"'{program}' is not on PATH"
        return True, f"'{program}' is on PATH"

    def build_argv(self, prompt):
        """Substitute the prompt as one argument. Nothing is shell-interpolated."""
        argv = []
        for part in self.profile.get("command", []):
            if part == PROMPT_TOKEN:
                argv.append(prompt)
            elif PROMPT_TOKEN in part:
                argv.append(part.replace(PROMPT_TOKEN, prompt))
            else:
                argv.append(part)
        return argv

    def _invoke(self, task, sandbox, prompt):
        argv = self.build_argv(prompt)
        timeout = int(self.profile.get("timeout", DEFAULT_TIMEOUT))

        result = sandbox.execute(argv, timeout=timeout)
        if not result.ran:
            return protocol.build_result(
                task, protocol.FAILED,
                f"{self.name} could not be started: {result.error}",
                unresolved=[result.error or "the host did not start"])

        evidence = protocol.evidence_from_execution(
            f"{self.name} invocation", result, "PASS" if result.ok else "FAIL")

        return self.normalise(task, result.stdout, evidence, result.ok,
                              exit_detail=f"{self.name} exited {result.exit_code}")
