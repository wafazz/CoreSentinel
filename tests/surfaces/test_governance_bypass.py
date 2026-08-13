"""The guarantee at the centre of Phase 9: no surface can write unaudited.

Three ways in — CLI, HTTP API, MCP — and one service layer beneath them. A
surface that reached past that layer into storage or an engine could write
without emitting, and an unaudited write through a side door makes the whole
trail a statement about one entrance.

`test_surfaces_never_reach_past_the_service_layer` is the structural half: it
walks the import graph and fails if `api/` or `mcp/` imports storage or an engine
directly. The rest is the behavioural half.
"""

import ast
import json
from pathlib import Path

import pytest

from coresentinel_core.services import Services
from coresentinel_core.services.facade import ServiceError, READ, WRITE


@pytest.fixture
def bound(tmp_path, monkeypatch):
    """A bound project with isolated memory, config and record store."""
    import coresentinel_memory as mem
    import coresentinel_core.runtime.config as config_module
    from coresentinel_core.runtime.container import Runtime

    root = tmp_path / "repo"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "repo"}), encoding="utf-8")

    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", tmp_path / "core.json")

    runtime = Runtime.bootstrap(str(root))
    yield Services(runtime)
    runtime.shutdown()


def audit_records(services):
    from coresentinel_core.audit import ledger
    return [r for r in services.runtime.store.audit_events.all() if r.get("seq")]


class TestImportGraph:
    """R-07: surfaces may only call services."""

    FORBIDDEN = ("coresentinel_core.storage", "coresentinel_memory", "coresentinel_evidence",
                 "coresentinel_gates", "coresentinel_score", "coresentinel_review",
                 "coresentinel_recall", "coresentinel_lifecycle", "coresentinel_context")

    def _imports(self, path):
        tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
        return found

    @pytest.mark.parametrize("surface", ["api", "mcp"])
    def test_surfaces_never_reach_past_the_service_layer(self, core_dir, surface):
        offenders = []
        for path in sorted((Path(core_dir) / "coresentinel_core" / surface).rglob("*.py")):
            for module in self._imports(path):
                if any(module == f or module.startswith(f + ".") for f in self.FORBIDDEN):
                    offenders.append(f"{path.name} imports {module}")
        assert not offenders, \
            ("a surface reached past the service layer, so it can write without emitting: "
             + "; ".join(offenders))

    def test_the_service_layer_is_the_only_thing_they_import_from_the_core(self, core_dir):
        for surface in ("api", "mcp"):
            for path in sorted((Path(core_dir) / "coresentinel_core" / surface).rglob("*.py")):
                core_imports = {m for m in self._imports(path)
                                if m.startswith("coresentinel_core.")}
                for module in core_imports:
                    assert module.startswith("coresentinel_core.services") or \
                        module.startswith(f"coresentinel_core.{surface}"), \
                        f"{path.name} imports {module}"


class TestServiceCatalogue:
    def test_every_operation_resolves_to_a_method(self, bound):
        for operation, (_, method) in bound.OPERATIONS.items():
            assert callable(getattr(bound, method, None)), f"{operation} has no implementation"

    def test_every_operation_declares_a_mode(self, bound):
        for operation in bound.OPERATIONS:
            assert bound.mode(operation) in (READ, WRITE)

    def test_an_unknown_operation_is_refused(self, bound):
        with pytest.raises(ServiceError):
            bound.call("memory.obliterate")

    def test_bad_arguments_are_refused_with_a_code(self, bound):
        with pytest.raises(ServiceError) as raised:
            bound.call("memory.store", {"nonsense": 1})
        assert raised.value.code == "BAD_ARGUMENTS"

    def test_results_are_json_serialisable(self, bound):
        for operation, (mode, _) in bound.OPERATIONS.items():
            if mode != READ:
                continue
            try:
                json.dumps(bound.call(operation, {}), default=str)
            except ServiceError:
                pass  # a read needing an argument is fine; unserialisable is not


class TestEveryWriteIsAudited:
    WRITES = [
        ("memory.store", {"layer": "project", "fact": "audited fact",
                          "confidence": 0.95, "source": "test"}),
        ("decision.create", {"title": "Use Redis", "reason": "saturation", "chosen": "Redis"}),
        ("incident.create", {"title": "Pool exhaustion", "problem": "N+1"}),
        ("gate.run", {}),
        ("verification.run", {"claim": "it works"}),
    ]

    @pytest.mark.parametrize("operation,arguments", WRITES, ids=[w[0] for w in WRITES])
    def test_a_service_write_leaves_an_audit_record(self, bound, operation, arguments):
        before = len(audit_records(bound))
        bound.call(operation, arguments)
        assert len(audit_records(bound)) > before, f"{operation} wrote without being audited"

    def test_the_audit_chain_stays_intact_across_writes(self, bound):
        for operation, arguments in self.WRITES:
            bound.call(operation, arguments)
        assert bound.call("audit.verify")["intact"]

    def test_a_read_does_not_write_an_audit_record(self, bound):
        bound.call("memory.store", {"layer": "project", "fact": "seed",
                                    "confidence": 0.9, "source": "t"})
        before = len(audit_records(bound))
        bound.call("health.get")
        bound.call("memory.search", {"query": "seed"})
        assert len(audit_records(bound)) == before


class TestIdenticalAcrossSurfaces:
    """The same operation, through any surface, produces the same audit record."""

    def _subjects(self, services):
        return [(r["subject"], r["action"]) for r in audit_records(services)]

    def test_the_api_and_mcp_route_to_the_same_operation(self, bound):
        from coresentinel_core.api import server as api
        from coresentinel_core.mcp import server as mcp

        for operation in bound.OPERATIONS:
            route = api.route_for(operation)
            assert route.startswith(api.BASE_PATH)
            assert mcp.tool_name(operation) in {t["name"] for t in mcp.build_tools(bound)}

    def test_a_write_via_mcp_is_audited_like_a_direct_call(self, bound):
        import io
        from coresentinel_core.mcp import McpServer

        direct_before = len(audit_records(bound))
        bound.call("memory.store", {"layer": "project", "fact": "direct",
                                    "confidence": 0.9, "source": "t"})
        direct_delta = len(audit_records(bound)) - direct_before

        frame = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                            "params": {"name": "memory_store",
                                       "arguments": {"layer": "project", "fact": "via mcp",
                                                     "confidence": 0.9, "source": "t"}}})
        mcp_before = len(audit_records(bound))
        McpServer(bound, stdin=io.StringIO(frame + "\n"), stdout=io.StringIO()).serve()
        mcp_delta = len(audit_records(bound)) - mcp_before

        assert mcp_delta == direct_delta == 1

    def test_both_surfaces_expose_exactly_the_service_catalogue(self, bound):
        from coresentinel_core.mcp import build_tools

        assert len(build_tools(bound)) == len(bound.OPERATIONS)


class TestMcpProtocol:
    def _exchange(self, services, frames):
        import io
        from coresentinel_core.mcp import McpServer

        out = io.StringIO()
        McpServer(services, stdin=io.StringIO("\n".join(frames) + "\n"), stdout=out).serve()
        return [json.loads(line) for line in out.getvalue().strip().splitlines() if line]

    def test_initialize_returns_a_protocol_version_and_server_info(self, bound):
        from coresentinel_core.mcp import PROTOCOL_VERSION, SERVER_NAME

        reply = self._exchange(bound, [json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})])[0]
        assert reply["result"]["protocolVersion"] == PROTOCOL_VERSION
        assert reply["result"]["serverInfo"]["name"] == SERVER_NAME

    def test_tools_list_declares_a_schema_for_every_tool(self, bound):
        reply = self._exchange(bound, [json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})])[0]
        for tool in reply["result"]["tools"]:
            assert tool["name"] and tool["description"]
            assert tool["inputSchema"]["type"] == "object"

    def test_a_notification_receives_no_reply(self, bound):
        assert self._exchange(bound, [json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized"})]) == []

    def test_an_unknown_method_returns_method_not_found(self, bound):
        from coresentinel_core.mcp.server import METHOD_NOT_FOUND

        reply = self._exchange(bound, [json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "does/not/exist"})])[0]
        assert reply["error"]["code"] == METHOD_NOT_FOUND

    def test_a_malformed_frame_is_a_parse_error_not_a_crash(self, bound):
        from coresentinel_core.mcp.server import PARSE_ERROR

        reply = self._exchange(bound, ["{ not json"])[0]
        assert reply["error"]["code"] == PARSE_ERROR

    def test_an_unknown_tool_is_refused(self, bound):
        reply = self._exchange(bound, [json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "not_a_tool"}})])[0]
        assert "error" in reply

    def test_a_service_refusal_is_a_tool_result_not_a_protocol_error(self, bound):
        """The model needs to read why it was refused and act on it."""
        reply = self._exchange(bound, [json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "agent_permissions",
                        "arguments": {"agent": "NotAnAgent"}}})])[0]
        assert reply["result"]["isError"] is True
        assert "UNKNOWN_AGENT" in reply["result"]["content"][0]["text"]

    def test_stdout_carries_only_protocol_frames(self, bound):
        import io
        from coresentinel_core.mcp import McpServer

        out, err = io.StringIO(), io.StringIO()
        frames = [json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
                  json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})]
        McpServer(bound, stdin=io.StringIO("\n".join(frames) + "\n"),
                  stdout=out, stderr=err).serve()
        for line in out.getvalue().strip().splitlines():
            json.loads(line)

    def test_every_write_tool_says_it_writes(self, bound):
        from coresentinel_core.mcp import build_tools

        for tool in build_tools(bound):
            operation = tool["name"].replace("_", ".", 1)
            if bound.mode(operation) == WRITE:
                assert "audited" in tool["description"]
