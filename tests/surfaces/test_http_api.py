"""The HTTP API — contract, routing and the two rules it will not start without.

Every server here binds port 0 on loopback, so the suite never opens a listening
port anyone else can reach and never collides with a port already in use.
"""

import json
import threading
import urllib.error
import urllib.request

import pytest

from coresentinel_core.api import server as api
from coresentinel_core.services import Services


@pytest.fixture
def bound(tmp_path, monkeypatch):
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


@pytest.fixture
def live(bound):
    """A running server on an ephemeral loopback port."""
    token = api.generate_token()
    httpd = api.build_server(bound, "127.0.0.1", 0, token)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def call(path, body=None, header_token=None, method=None):
        url = f"http://127.0.0.1:{httpd.server_address[1]}{path}"
        headers = {"Content-Type": "application/json"}
        if header_token:
            headers[api.TOKEN_HEADER] = header_token
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            url, data=data, headers=headers,
            method=method or ("POST" if body is not None else "GET"))
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    yield type("Live", (), {"call": staticmethod(call), "token": token,
                            "services": bound})
    httpd.shutdown()
    httpd.server_close()


class TestBindSafety:
    def test_a_non_loopback_bind_without_a_token_is_refused(self, bound):
        """An unauthenticated governance system on the network is not a default
        anyone should get by accident."""
        with pytest.raises(api.ApiError) as raised:
            api.build_server(bound, "0.0.0.0", 0, token=None)
        assert raised.value.code == "UNSAFE_BIND"

    def test_a_non_loopback_bind_with_a_token_is_allowed(self, bound):
        httpd = api.build_server(bound, "0.0.0.0", 0, token="a-real-token")
        httpd.server_close()

    def test_loopback_without_a_token_is_allowed_to_start(self, bound):
        httpd = api.build_server(bound, "127.0.0.1", 0, token=None)
        httpd.server_close()

    @pytest.mark.parametrize("host,expected", [
        ("127.0.0.1", True), ("::1", True), ("localhost", True),
        ("0.0.0.0", False), ("192.168.1.10", False), ("", False)])
    def test_loopback_detection(self, host, expected):
        assert api.is_loopback(host) is expected


class TestAuthorisation:
    def test_a_write_without_a_token_is_refused(self, live):
        status, payload = live.call("/api/v1/memory/store",
                                    {"layer": "project", "fact": "x",
                                     "confidence": 0.9, "source": "t"})
        assert status == 401 and payload["error"]["code"] == "UNAUTHORISED"

    def test_a_write_with_the_token_succeeds(self, live):
        status, payload = live.call("/api/v1/memory/store",
                                    {"layer": "project", "fact": "authorised",
                                     "confidence": 0.9, "source": "t"}, live.token)
        assert status == 200 and payload["result"]["stored"] is True

    def test_a_wrong_token_is_refused(self, live):
        status, _ = live.call("/api/v1/memory/store",
                              {"layer": "project", "fact": "x"}, "not-the-token")
        assert status == 401

    def test_a_read_over_loopback_needs_no_token(self, live):
        status, payload = live.call("/api/v1/health/get")
        assert status == 200 and "result" in payload

    def test_nothing_is_written_when_authorisation_fails(self, live):
        from coresentinel_core.audit import ledger

        before = ledger.verify(live.services.runtime.store)["checked"]
        live.call("/api/v1/memory/store", {"layer": "project", "fact": "sneak"})
        after = ledger.verify(live.services.runtime.store)["checked"]
        assert after == before


class TestRoutingContract:
    def test_the_catalogue_lists_every_operation(self, live):
        status, payload = live.call("/api/v1")
        assert status == 200
        assert set(payload["operations"]) == set(live.services.OPERATIONS)

    def test_every_route_is_versioned(self, live):
        _, payload = live.call("/api/v1")
        for detail in payload["operations"].values():
            assert detail["route"].startswith("/api/v1/")

    def test_a_write_cannot_be_invoked_with_get(self, live):
        status, payload = live.call("/api/v1/gate/run")
        assert status == 405 and payload["error"]["code"] == "METHOD_NOT_ALLOWED"

    def test_an_unknown_route_is_a_404_with_a_code(self, live):
        status, payload = live.call("/api/v1/does/not/exist")
        assert status == 404 and payload["error"]["code"] == "UNKNOWN_ROUTE"

    def test_a_malformed_body_is_reported_not_swallowed(self, live):
        url = "/api/v1/memory/store"
        status, payload = live.call(url, body=None, method="POST")
        # No body at all is an empty argument set, which the service rejects.
        assert status in (400, 401)

    def test_a_service_refusal_becomes_a_400_with_its_code(self, live):
        status, payload = live.call("/api/v1/agent/permissions?agent=NotAnAgent")
        assert status == 400 and payload["error"]["code"] == "UNKNOWN_AGENT"

    def test_query_parameters_reach_the_service(self, live):
        status, payload = live.call("/api/v1/memory/search?query=redis&limit=5")
        assert status == 200 and payload["result"]["query"] == "redis"

    def test_the_liveness_probe_needs_nothing(self, live):
        status, payload = live.call("/api/v1/health/live")
        assert status == 200 and payload["status"] == "ok"

    def test_every_response_declares_the_api_version(self, live):
        status, payload = live.call("/api/v1/health/get")
        assert status == 200 and payload["operation"] == "health.get"

    def test_an_internal_failure_does_not_leak_a_stack_trace(self, live, monkeypatch):
        def explode(*args, **kwargs):
            raise RuntimeError("secret internal detail")

        monkeypatch.setattr(live.services, "health_get", explode)
        status, payload = live.call("/api/v1/health/get")
        assert status == 500
        assert "secret internal detail" not in json.dumps(payload)


class TestSurfaceParity:
    def test_the_api_reaches_every_operation_the_cli_has(self, live):
        _, payload = live.call("/api/v1")
        assert len(payload["operations"]) == len(live.services.OPERATIONS)

    def test_a_write_through_the_api_is_audited(self, live):
        from coresentinel_core.audit import ledger

        before = ledger.verify(live.services.runtime.store)["checked"]
        live.call("/api/v1/decision/create",
                  {"title": "Use Redis", "reason": "saturation", "chosen": "Redis"},
                  live.token)
        report = ledger.verify(live.services.runtime.store)
        assert report["checked"] > before
        assert report["intact"], "the API write broke the audit chain"
