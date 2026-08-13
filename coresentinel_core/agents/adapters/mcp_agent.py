"""
MCP agent adapter — JSON-RPC 2.0 over stdio.

A minimal client: initialize, then tools/call. Enough to invoke an MCP server as
an agent, and small enough to read. A full MCP implementation is not what this
adapter is for — CoreSentinel's own MCP *server* surface is Phase 9.

The server is a subprocess, so invocation consumes `shell.execute` and goes
through the sandbox like any other command.
"""

import json
import time
import subprocess
from pathlib import Path

from coresentinel_core.agents import protocol
from coresentinel_core.agents import permissions as perms
from coresentinel_core.agents.adapters.base import AgentAdapter

import coresentinel_exec as execution

PROTOCOL_VERSION = "2024-11-05"
DEFAULT_TIMEOUT = 120


class McpAgentAdapter(AgentAdapter):
    transport = "mcp"
    permission = perms.SHELL_EXECUTE

    def program(self):
        command = self.profile.get("command") or []
        return command[0] if command else None

    def scope(self):
        program = self.program()
        return Path(program).name if program else self.id

    def available(self):
        if not self.profile.get("command"):
            return False, "no MCP server command is declared in adapters.json"
        if not self.profile.get("tool"):
            return False, "no MCP tool name is declared in adapters.json"
        program = self.program()
        if not execution.available(program):
            return False, f"'{program}' is not on PATH"
        return True, f"MCP server '{program}', tool '{self.profile['tool']}'"

    def _frame(self, message):
        return (json.dumps(message) + "\n").encode("utf-8")

    def _invoke(self, task, sandbox, prompt):
        argv = [str(a) for a in self.profile["command"]]
        resolved = execution.resolve(argv[0])
        if resolved is None:
            return protocol.build_result(task, protocol.FAILED,
                                         f"'{argv[0]}' is not on PATH")

        conversation = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": "CoreSentinel", "version": "1.0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": self.profile["tool"],
                        "arguments": {self.profile.get("argument", "prompt"): prompt}}},
        ]

        started = time.perf_counter()
        timeout = int(self.profile.get("timeout", DEFAULT_TIMEOUT))
        try:
            completed = subprocess.run(
                [resolved, *argv[1:]],
                input=b"".join(self._frame(m) for m in conversation),
                capture_output=True, cwd=str(sandbox.root), timeout=timeout)
        except (subprocess.SubprocessError, OSError) as e:
            return protocol.build_result(task, protocol.FAILED,
                                         f"MCP server failed to run: {e}",
                                         unresolved=[str(e)])

        duration = int((time.perf_counter() - started) * 1000)
        stdout = completed.stdout.decode("utf-8", "replace")
        text, error = self._read_tool_result(stdout)
        ok = completed.returncode == 0 and error is None

        sandbox.commands_run.append({"command": " ".join(argv), "exit_code": completed.returncode,
                                     "duration_ms": duration})

        evidence = {
            "check": f"{self.name} MCP tools/call",
            "command": f"{' '.join(argv)} :: tools/call {self.profile['tool']}",
            "cwd": str(sandbox.root), "started_at": None, "duration_ms": duration,
            "exit_code": completed.returncode, "output_digest": None,
            "output_excerpt": (text or stdout)[:400],
            "error": error, "status": "PASS" if ok else "FAIL",
        }

        return self.normalise(task, text or stdout, evidence, ok,
                              exit_detail=error or f"MCP server exited {completed.returncode}")

    def _read_tool_result(self, stdout):
        """Pull the tools/call response out of the JSON-RPC stream. (text, error)."""
        text, error = None, None
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(message, dict) or message.get("id") != 2:
                continue
            if "error" in message:
                error = str(message["error"].get("message", message["error"]))
                continue
            content = (message.get("result") or {}).get("content") or []
            parts = [item.get("text", "") for item in content
                     if isinstance(item, dict) and item.get("type") == "text"]
            text = "\n".join(p for p in parts if p)
        if text is None and error is None:
            error = "the MCP server returned no tools/call result"
        return text, error
