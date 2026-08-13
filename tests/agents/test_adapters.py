"""Agent adapters — conformance, normalisation, and the line between claim and evidence.

The property that matters most is the one that is easiest to lose at a vendor
boundary: an adapter proves that an agent ran and what it said, never that what
it said is true. A vendor reporting "I added tests" must not become evidence of
tests, or the fabrication Phase 1 removed from the middle of the product walks
back in at the edge.

No test here requires a vendor CLI to be installed. Normalisation is proved with
a mock CLI agent and a mock HTTP server.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from coresentinel_core.agents import adapters, protocol, registry
from coresentinel_core.agents import permissions as perms
from coresentinel_core.agents.adapters import base
from coresentinel_core.agents.sandbox import AgentSandbox


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    return root


def open_sandbox(root, agent="Builder", extra=None):
    permission_set = registry.permissions_for(agent)
    for permission in (extra or []):
        permission_set.grant(permission, perms.ALLOW, reason="granted for this test")
    return AgentSandbox(agent, permission_set, root)


def mock_cli_descriptor(tmp_path, payload, exit_code=0, fmt="json"):
    """A CLI 'agent' that echoes a canned response. No vendor required."""
    script = tmp_path / "mock_agent.py"
    script.write_text(
        "import sys\n"
        f"sys.stdout.write({payload!r})\n"
        f"sys.exit({exit_code})\n", encoding="utf-8")
    return {"id": "mock-cli", "name": "Mock CLI",
            "invoke": {"transport": "cli",
                       "command": [sys.executable, str(script), "{prompt}"],
                       "response": {"format": fmt}, "timeout": 30}}


class TestConformance:
    def test_every_registered_adapter_conforms(self):
        report = adapters.conformance_report()
        assert report, "no host declares an invocation profile"
        failing = [item["adapter"] for item in report if not item["conforms"]]
        assert not failing, f"adapters failing conformance: {failing}"

    @pytest.mark.parametrize("transport", sorted(adapters.TRANSPORTS))
    def test_each_transport_has_a_conforming_implementation(self, transport):
        implementation = adapters.TRANSPORTS[transport]
        adapter = implementation({"id": f"probe-{transport}", "invoke": {}})
        report = adapters.conformance(adapter)
        assert report["conforms"], report

    def test_the_base_adapter_does_not_pretend_to_invoke(self):
        adapter = base.AgentAdapter({"id": "abstract"})
        assert adapters.conformance(adapter)["conforms"] is False

    def test_an_absent_host_reports_unavailable_without_raising(self):
        adapter = adapters.TRANSPORTS["cli"]({
            "id": "ghost", "invoke": {"command": ["definitely-not-installed"]}})
        available, reason = adapter.available()
        assert available is False and "not on PATH" in reason

    def test_resolving_an_unknown_host_returns_none(self):
        assert adapters.resolve("not-a-host") is None

    def test_a_projection_only_host_is_not_invocable(self):
        """copilot ships rules files and has no CLI. That is a fact, not a gap."""
        assert adapters.resolve("copilot") is None


class TestPermissionGating:
    def test_a_read_only_agent_cannot_invoke_a_cli_host(self, repo, tmp_path):
        adapter = adapters.for_descriptor(mock_cli_descriptor(tmp_path, "{}"))
        sandbox = open_sandbox(repo, "Scout")
        result = adapter.invoke(protocol.build_task("do it", "Scout"), sandbox)
        assert result["status"] == protocol.DENIED
        assert result["denials"]

    def test_an_http_host_needs_network_access(self, repo):
        adapter = adapters.TRANSPORTS["http"]({
            "id": "remote", "invoke": {"endpoint": "http://127.0.0.1:1/agent"}})
        sandbox = open_sandbox(repo, "Builder")
        result = adapter.invoke(protocol.build_task("do it", "Builder"), sandbox)
        assert result["status"] == protocol.DENIED

    def test_no_contract_grants_network_access_by_default(self):
        for name in registry.names():
            assert registry.permissions_for(name).level(perms.NETWORK_ACCESS) in \
                (perms.DENY, perms.ASK), f"{name} can reach the network unattended"

    def test_only_declared_contracts_may_delegate_to_a_coding_assistant(self):
        allowed = [name for name in registry.names()
                   if registry.permissions_for(name).check(perms.SHELL_EXECUTE, "claude").allowed]
        assert "Scout" not in allowed
        assert allowed, "no contract may delegate, which makes invocation unusable"


class TestCliNormalisation:
    def test_a_json_response_is_parsed_into_claims(self, repo, tmp_path):
        payload = json.dumps({"summary": "added a cache layer",
                              "files_changed": ["src/cache.py"],
                              "tests": ["test_cache"], "confidence": 0.8})
        adapter = adapters.for_descriptor(mock_cli_descriptor(tmp_path, payload))
        result = adapter.invoke(protocol.build_task("add caching", "Builder"),
                                open_sandbox(repo))

        assert result["status"] == protocol.COMPLETED
        assert result["summary"] == "added a cache layer"
        assert result["claims"]["files_changed"] == ["src/cache.py"]
        assert result["claims"]["response_format"] == "json"

    def test_a_text_response_still_normalises(self, repo, tmp_path):
        descriptor = mock_cli_descriptor(tmp_path, "I updated the handler.\nDone.", fmt="text")
        adapter = adapters.for_descriptor(descriptor)
        result = adapter.invoke(protocol.build_task("fix it", "Builder"), open_sandbox(repo))
        assert result["status"] == protocol.COMPLETED
        assert result["summary"] == "I updated the handler."
        assert result["claims"]["response_format"] == "text"

    def test_a_claim_never_becomes_evidence(self, repo, tmp_path):
        """The line this whole layer exists to hold."""
        payload = json.dumps({"summary": "all tests pass",
                              "tests": ["suite passed"], "files_changed": ["a.py"]})
        adapter = adapters.for_descriptor(mock_cli_descriptor(tmp_path, payload))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))

        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["check"].endswith("invocation"), \
            "something other than the invocation was recorded as evidence"
        assert result["files_changed"] == [], \
            "a claimed file change was recorded as an observed one"

    def test_the_response_is_marked_unverified(self, repo, tmp_path):
        adapter = adapters.for_descriptor(mock_cli_descriptor(tmp_path, "done", fmt="text"))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))
        assert any("verifies it" in warning for warning in result["warnings"])

    def test_a_nonzero_exit_fails_the_result(self, repo, tmp_path):
        adapter = adapters.for_descriptor(
            mock_cli_descriptor(tmp_path, "broke", exit_code=3, fmt="text"))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))
        assert result["status"] == protocol.FAILED
        assert result["evidence"][0]["exit_code"] == 3

    def test_malformed_json_degrades_to_text_rather_than_crashing(self, repo, tmp_path):
        adapter = adapters.for_descriptor(mock_cli_descriptor(tmp_path, "{not json"))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))
        assert result["status"] == protocol.COMPLETED
        assert result["claims"]["response_format"] == "text"

    def test_the_prompt_is_passed_as_one_argument(self):
        adapter = adapters.TRANSPORTS["cli"]({
            "id": "probe", "invoke": {"command": ["agent", "--prompt", "{prompt}"]}})
        argv = adapter.build_argv('do "this"; rm -rf /')
        assert argv == ["agent", "--prompt", 'do "this"; rm -rf /'], \
            "the prompt was split or interpolated instead of passed through"

    def test_every_adapter_result_survives_validation(self, repo, tmp_path):
        payload = json.dumps({"summary": "ok", "files_changed": []})
        adapter = adapters.for_descriptor(mock_cli_descriptor(tmp_path, payload))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))
        assert protocol.validate_result(result) == []


class TestHttpNormalisation:
    @pytest.fixture
    def server(self):
        """A mock HTTP agent. No network beyond loopback."""
        state = {"body": json.dumps({"summary": "remote agent replied",
                                     "files_changed": ["remote.py"]}), "status": 200}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                state["received"] = json.loads(self.rfile.read(length) or b"{}")
                payload = state["body"].encode("utf-8")
                self.send_response(state["status"])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        httpd = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        state["url"] = f"http://127.0.0.1:{httpd.server_port}/agent"
        yield state
        httpd.shutdown()

    def _adapter(self, server):
        return adapters.TRANSPORTS["http"]({
            "id": "mock-http", "name": "Mock HTTP",
            "invoke": {"transport": "http", "endpoint": server["url"],
                       "response": {"format": "json"}, "timeout": 10}})

    def test_a_remote_agent_response_is_normalised(self, repo, server):
        result = self._adapter(server).invoke(
            protocol.build_task("do it", "Builder"),
            open_sandbox(repo, extra=[perms.NETWORK_ACCESS]))
        assert result["status"] == protocol.COMPLETED
        assert result["summary"] == "remote agent replied"
        assert result["claims"]["files_changed"] == ["remote.py"]

    def test_the_prompt_reaches_the_endpoint(self, repo, server):
        self._adapter(server).invoke(
            protocol.build_task("add caching", "Builder"),
            open_sandbox(repo, extra=[perms.NETWORK_ACCESS]))
        assert "add caching" in server["received"]["prompt"]

    def test_an_error_status_fails_the_result(self, repo, server):
        server["status"] = 500
        server["body"] = json.dumps({"summary": "upstream exploded"})
        result = self._adapter(server).invoke(
            protocol.build_task("x", "Builder"),
            open_sandbox(repo, extra=[perms.NETWORK_ACCESS]))
        assert result["status"] == protocol.FAILED
        assert result["evidence"][0]["exit_code"] == 500

    def test_an_unreachable_endpoint_fails_without_raising(self, repo):
        adapter = adapters.TRANSPORTS["http"]({
            "id": "dead", "invoke": {"endpoint": "http://127.0.0.1:1/agent", "timeout": 2}})
        result = adapter.invoke(protocol.build_task("x", "Builder"),
                                open_sandbox(repo, extra=[perms.NETWORK_ACCESS]))
        assert result["status"] == protocol.FAILED

    def test_the_credential_never_reaches_the_evidence(self, repo, server, monkeypatch):
        monkeypatch.setenv("MOCK_AGENT_TOKEN", "sk_live_supersecrettoken1234")
        adapter = adapters.TRANSPORTS["http"]({
            "id": "mock-http",
            "invoke": {"endpoint": server["url"], "auth_env": "MOCK_AGENT_TOKEN",
                       "response": {"format": "json"}, "timeout": 10}})
        result = adapter.invoke(protocol.build_task("x", "Builder"),
                                open_sandbox(repo, extra=[perms.NETWORK_ACCESS]))
        assert "supersecrettoken" not in json.dumps(result)


class TestMcpNormalisation:
    def _descriptor(self, tmp_path, response):
        """A mock MCP server: reads JSON-RPC frames, answers tools/call."""
        script = tmp_path / "mock_mcp.py"
        script.write_text(
            "import sys, json\n"
            "for line in sys.stdin:\n"
            "    line = line.strip()\n"
            "    if not line:\n"
            "        continue\n"
            "    message = json.loads(line)\n"
            "    if message.get('id') == 1:\n"
            "        print(json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': {}}), flush=True)\n"
            "    elif message.get('id') == 2:\n"
            "        print(json.dumps({'jsonrpc': '2.0', 'id': 2, 'result': {'content': "
            f"[{{'type': 'text', 'text': {response!r}}}]}}}}), flush=True)\n",
            encoding="utf-8")
        return {"id": "mock-mcp", "name": "Mock MCP",
                "invoke": {"transport": "mcp",
                           "command": [sys.executable, str(script)],
                           "tool": "run_agent", "response": {"format": "json"},
                           "timeout": 30}}

    def test_a_tool_result_is_normalised(self, repo, tmp_path):
        payload = json.dumps({"summary": "mcp agent replied", "files_changed": ["m.py"]})
        adapter = adapters.for_descriptor(self._descriptor(tmp_path, payload))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))
        assert result["status"] == protocol.COMPLETED
        assert result["summary"] == "mcp agent replied"
        assert result["claims"]["files_changed"] == ["m.py"]

    def test_a_server_without_a_tool_declaration_is_unavailable(self):
        adapter = adapters.TRANSPORTS["mcp"]({
            "id": "probe", "invoke": {"command": [sys.executable]}})
        available, reason = adapter.available()
        assert available is False and "tool" in reason

    def test_the_invocation_is_the_only_evidence(self, repo, tmp_path):
        payload = json.dumps({"summary": "done", "tests": ["all green"]})
        adapter = adapters.for_descriptor(self._descriptor(tmp_path, payload))
        result = adapter.invoke(protocol.build_task("x", "Builder"), open_sandbox(repo))
        assert len(result["evidence"]) == 1
        assert result["claims"]["tests"] == ["all green"]


class TestRegistryIntegration:
    def test_the_rules_file_projection_is_untouched(self):
        """Invocation is a new capability on the same registry, not a replacement."""
        import coresentinel_adapters as v1

        for descriptor in v1.get_adapters():
            assert descriptor.get("transport") == "rules_file"
            assert descriptor.get("global_path") or descriptor.get("project_path")

    def test_at_least_three_hosts_declare_invocation(self):
        assert len(adapters.invocable()) >= 3

    def test_every_invoke_profile_declares_a_known_transport(self):
        import coresentinel_adapters as v1

        for descriptor in v1.get_adapters():
            profile = descriptor.get("invoke")
            if profile:
                assert profile["transport"] in adapters.TRANSPORTS, \
                    f"{descriptor['id']} declares an unknown transport"
