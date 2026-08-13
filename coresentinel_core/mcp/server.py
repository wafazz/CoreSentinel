"""
CoreSentinel as an MCP server — JSON-RPC 2.0 over stdio.

Phase 6 built an MCP *client*, so CoreSentinel could invoke an MCP agent. This is
the other direction: an MCP-capable host mounts CoreSentinel and calls its
operations as tools.

Tools are generated from the service catalogue, which is the point. An operation
cannot exist on the CLI and be missing here, and it cannot be reachable here
without going through the layer that emits the event that gets it audited. The
brief's requirement — *"MCP must not bypass governance"* — is structural rather
than a rule somebody has to remember.

stdout carries JSON-RPC frames and nothing else. Every diagnostic goes to stderr,
because one stray print corrupts the stream and the host sees a protocol error
rather than the message that caused it. That is the same contract the CLI has
kept since v1, for the same reason.
"""

import json
import sys

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "coresentinel"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# A short description per operation. MCP hosts show these to a model, so they say
# what the tool does and — where it matters — what it does not.
DESCRIPTIONS = {
    "project.inspect": "Inspect a project: languages, frameworks, datastores, CI, tests. "
                       "Every value cites the file that proves it; unevidenced dimensions "
                       "report 'unknown' rather than a guess.",
    "project.list": "List projects CoreSentinel has been bound to.",
    "memory.search": "Search every memory layer, decision and journal entry, ranked.",
    "memory.store": "Record a fact with a confidence score and its source.",
    "memory.brief": "Session-start briefing: last task, recent work, established facts, "
                    "stale facts, known failures, recent decisions.",
    "context.assemble": "Assemble only the context a stated task needs, inside a token "
                        "budget. Without a task, returns the whole project pack.",
    "decision.search": "Search recorded architecture decisions.",
    "decision.create": "Record an architecture decision and the alternatives rejected.",
    "decision.verify": "Check whether a proposed change contradicts an accepted decision. "
                       "Use this BEFORE reversing an architectural choice.",
    "agent.list": "List the specialist agent contracts.",
    "agent.permissions": "What an agent may actually do. Permissions are enforced by a "
                         "sandbox, not merely declared.",
    "agent.dispatch": "Run one agent against an objective, under its contract's permissions.",
    "agent.status": "Recent agent task records.",
    "task.run": "Run an objective across the specialist pipeline.",
    "task.list": "Recent tasks.",
    "gate.status": "Current quality gate states with machine-readable reason codes.",
    "gate.run": "Evaluate the quality gate pipeline.",
    "verification.run": "Run the evidence suite against a claim. Checks that cannot run "
                        "report UNKNOWN and are excluded rather than counted as passes.",
    "health.get": "Project health across seven dimensions, each citing its basis.",
    "review.run": "Static review of the working diff.",
    "incident.create": "Record an incident: problem, root cause, resolution, learning.",
    "incident.list": "List incidents and their summary.",
    "pattern.search": "Search the reusable pattern library.",
    "audit.list": "Read the audit trail.",
    "audit.record": "Append a record to the tamper-evident audit chain.",
    "audit.verify": "Verify the audit chain has not been altered.",
    "knowledge.query": "Traverse the knowledge graph from an entity. Edges come only from "
                       "recorded relationships; nothing is inferred from source code.",
}

# Arguments each tool accepts, as JSON Schema. Kept deliberately loose — the
# service layer validates, and duplicating that here would give two answers.
SCHEMAS = {
    "memory.store": {"required": ["layer", "fact"],
                     "properties": {"layer": {"type": "string"}, "fact": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "source": {"type": "string"}}},
    "memory.search": {"required": ["query"], "properties": {"query": {"type": "string"},
                                                            "limit": {"type": "integer"}}},
    "context.assemble": {"properties": {"task": {"type": "string"},
                                        "budget": {"type": "integer"}}},
    "decision.create": {"required": ["title", "reason", "chosen"],
                        "properties": {"title": {"type": "string"},
                                       "reason": {"type": "string"},
                                       "chosen": {"type": "string"},
                                       "alternatives": {"type": "string"}}},
    "decision.verify": {"required": ["change"], "properties": {"change": {"type": "string"}}},
    "decision.search": {"properties": {"query": {"type": "string"}}},
    "agent.dispatch": {"required": ["agent", "objective"],
                       "properties": {"agent": {"type": "string"},
                                      "objective": {"type": "string"}}},
    "agent.permissions": {"properties": {"agent": {"type": "string"}}},
    "task.run": {"required": ["objective"],
                 "properties": {"objective": {"type": "string"}, "roles": {"type": "string"}}},
    "verification.run": {"properties": {"claim": {"type": "string"}}},
    "incident.create": {"required": ["title"],
                        "properties": {"title": {"type": "string"},
                                       "problem": {"type": "string"},
                                       "root_cause": {"type": "string"},
                                       "severity": {"type": "string"}}},
    "pattern.search": {"properties": {"query": {"type": "string"}}},
    "audit.record": {"required": ["actor", "action"],
                     "properties": {"actor": {"type": "string"}, "action": {"type": "string"},
                                    "subject": {"type": "string"}}},
    "audit.list": {"properties": {"limit": {"type": "integer"}}},
    "knowledge.query": {"properties": {"entity": {"type": "string"},
                                       "depth": {"type": "integer"}}},
    "gate.run": {"properties": {"objective": {"type": "string"}}},
    "project.inspect": {"properties": {"verbose": {"type": "boolean"}}},
}


def tool_name(operation):
    """MCP tool names conventionally use underscores."""
    return operation.replace(".", "_")


def operation_for(name):
    return str(name or "").replace("_", ".", 1) if "_" in str(name or "") else name


def build_tools(services):
    tools = []
    for operation, (mode, _) in sorted(services.OPERATIONS.items()):
        schema = SCHEMAS.get(operation, {})
        description = DESCRIPTIONS.get(operation, operation)
        if mode == "write":
            description += " (writes state; the change is audited)"
        tools.append({
            "name": tool_name(operation),
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": {**(schema.get("properties") or {}),
                               "project": {"type": "string",
                                           "description": "target directory; defaults to the "
                                                          "server's working directory"}},
                "required": schema.get("required", []),
            },
        })
    return tools


class McpServer:
    def __init__(self, services, stdin=None, stdout=None, stderr=None):
        self.services = services
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.tools = build_tools(services)
        # Derived from the operation itself, not from two sorted lists lining up.
        self._by_name = {tool_name(operation): operation for operation in services.OPERATIONS}

    # ---------------------------------------------------------------- framing

    def _write(self, message):
        self.stdout.write(json.dumps(message, default=str) + "\n")
        self.stdout.flush()

    def _error(self, request_id, code, message):
        self._write({"jsonrpc": "2.0", "id": request_id,
                     "error": {"code": code, "message": message}})

    def _result(self, request_id, result):
        self._write({"jsonrpc": "2.0", "id": request_id, "result": result})

    # ---------------------------------------------------------------- methods

    def handle(self, message):
        """Route one JSON-RPC message. Notifications get no reply, by spec."""
        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if method == "initialize":
            return self._result(request_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": self._version()},
                "instructions": (
                    "CoreSentinel is the governance layer beneath you. Call "
                    "context_assemble before starting work and decision_verify before "
                    "reversing an architectural choice. A verification result of UNKNOWN "
                    "means the check could not run — it is not a pass."),
            })

        if method in ("notifications/initialized", "initialized"):
            return None

        if method == "tools/list":
            return self._result(request_id, {"tools": self.tools})

        if method == "tools/call":
            return self._call(request_id, params)

        if method == "ping":
            return self._result(request_id, {})

        if request_id is None:
            return None
        return self._error(request_id, METHOD_NOT_FOUND, f"unknown method '{method}'")

    def _call(self, request_id, params):
        from coresentinel_core.services.facade import ServiceError

        name = params.get("name")
        operation = self._by_name.get(name)
        if not operation:
            return self._error(request_id, INVALID_PARAMS, f"unknown tool '{name}'")

        try:
            result = self.services.call(operation, params.get("arguments") or {})
        except ServiceError as e:
            # A refusal is a tool result, not a protocol error: the model needs to
            # read why it was refused and act on it.
            return self._result(request_id, {
                "isError": True,
                "content": [{"type": "text",
                             "text": f"{e.code}: {e.message}"
                                     + (f"\n{e.remedy}" if e.remedy else "")}]})
        except Exception as e:
            return self._error(request_id, INTERNAL_ERROR, f"{type(e).__name__}: {e}")

        return self._result(request_id, {
            "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]})

    def _version(self):
        try:
            from coresentinel_core import CORE_ROOT
            return (CORE_ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
        except OSError:
            return "unknown"

    # ---------------------------------------------------------------- loop

    def serve(self):
        """Read frames until stdin closes. Never raises out of the loop."""
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                self._error(None, PARSE_ERROR, "the frame is not valid JSON")
                continue
            if not isinstance(message, dict):
                self._error(None, INVALID_REQUEST, "a frame must be a JSON object")
                continue
            try:
                self.handle(message)
            except Exception as e:
                print(f"[!] mcp handler failed: {e}", file=self.stderr)
                self._error(message.get("id"), INTERNAL_ERROR, "the request failed")
        return 0
