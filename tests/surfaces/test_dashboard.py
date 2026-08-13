"""The dashboard — an asset route, an allowlist, and the no-sample-data rule.

The dashboard is the only surface a human reaches with a mouse, which makes it the
one most likely to be trusted without reading. So the tests here are less about
rendering and more about two properties: it cannot reach anything the API does not
expose, and it ships no number that did not come from a running system.
"""

import json
import re
import threading
import urllib.error
import urllib.request

import pytest

from coresentinel_core import web
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
    httpd = api.build_server(bound, "127.0.0.1", 0, api.generate_token())
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def call(path):
        url = f"http://127.0.0.1:{httpd.server_address[1]}{path}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    yield type("Live", (), {"call": staticmethod(call), "services": bound})
    httpd.shutdown()
    httpd.server_close()


def asset(name):
    return (web.ASSET_DIR / name).read_text(encoding="utf-8")


class TestAssetsShip:
    def test_every_declared_asset_exists(self):
        assert web.available()

    def test_resolve_returns_bytes_and_a_content_type(self):
        body, content_type = web.resolve("/app.js")
        assert isinstance(body, bytes) and body
        assert content_type.startswith("application/javascript")

    def test_the_root_resolves_to_the_page(self):
        root, _ = web.resolve("/")
        indexed, _ = web.resolve("/index.html")
        assert root == indexed


class TestAllowlist:
    """The asset route reads files, so the allowlist is the whole defence."""

    @pytest.mark.parametrize("path", [
        "/../coresentinel_core/runtime/config.py",
        "/../../etc/passwd",
        "/app.js/../__init__.py",
        "/__init__.py",
        "/.env",
        "/secret.txt",
        "/api/v1",
    ])
    def test_a_path_off_the_allowlist_does_not_resolve(self, path):
        assert web.resolve(path) is None

    def test_traversal_is_a_404_over_http(self, live):
        status, _, _ = live.call("/../coresentinel_core/runtime/config.py")
        assert status == 404

    def test_a_package_file_is_not_reachable_even_though_it_sits_beside_the_assets(self, live):
        status, _, _ = live.call("/__init__.py")
        assert status == 404

    def test_the_allowlist_names_only_the_three_shipped_files(self):
        assert {name for name, _ in web.ASSETS.values()} == {
            "index.html", "app.css", "app.js"}


class TestServing:
    @pytest.mark.parametrize("path,expected", [
        ("/", "text/html"),
        ("/index.html", "text/html"),
        ("/app.css", "text/css"),
        ("/app.js", "application/javascript"),
    ])
    def test_each_asset_is_served_with_its_type(self, live, path, expected):
        status, headers, body = live.call(path)
        assert status == 200
        assert headers["Content-Type"].startswith(expected)
        assert body

    def test_the_response_forbids_sniffing(self, live):
        _, headers, _ = live.call("/app.js")
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_the_policy_permits_no_remote_origin(self, live):
        _, headers, _ = live.call("/")
        policy = headers["Content-Security-Policy"]
        assert "default-src 'self'" in policy
        assert "connect-src 'self'" in policy
        assert "frame-ancestors 'none'" in policy

    def test_the_api_catalogue_still_answers_at_its_own_path(self, live):
        """The asset route is checked first, so this is the regression that matters."""
        status, headers, body = live.call("/api/v1")
        assert status == 200
        assert headers["Content-Type"].startswith("application/json")
        assert "operations" in json.loads(body)



class TestNoSampleData:
    """A dashboard with a fixture behind a view renders beautifully while the thing
    it claims to show is broken. That is the exact failure this product exists to
    name, so it may not ship one."""

    def test_the_page_declares_no_figures_of_its_own(self):
        html = asset("index.html")
        body = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        panels = re.findall(r'<section class="view".*?</section>', body, flags=re.DOTALL)
        assert panels, "the views should be empty shells filled by the API"
        for panel in panels:
            inner = re.sub(r"<[^>]+>", "", panel).strip()
            assert inner == "", f"a view ships static content: {inner[:80]}"

    def test_the_script_holds_no_fallback_object(self):
        source = asset("app.js")
        for banned in ("SAMPLE", "FIXTURE", "MOCK_", "demoData", "placeholderData"):
            assert banned not in source

    @pytest.mark.parametrize("name", ["index.html", "app.css", "app.js"])
    def test_nothing_loads_from_a_remote_origin(self, name):
        # The one absolute URL in the assets is the SVG namespace in the inline
        # favicon, which is an XML identifier and not a fetch.
        remote = [url for url in re.findall(r'https?://[^\s"\'<>)]+', asset(name))
                  if not url.startswith("http://www.w3.org/2000/svg")]
        assert remote == [], f"{name} reaches outside the origin: {remote}"


class TestSurfaceBoundary:
    """The dashboard consumes the API. It has no other way in, and the operations
    it names must exist — a view wired to a route that was renamed is a view that
    fails in a browser and nowhere else."""

    def declared(self):
        html = asset("index.html")
        names = set()
        for group in re.findall(r'data-endpoints="([^"]+)"', html):
            names.update(group.split())
        return names

    def test_the_page_declares_the_endpoints_its_views_use(self):
        assert self.declared(), "each view should name the operations it reads"

    def test_every_declared_endpoint_is_a_real_operation(self, bound):
        unknown = self.declared() - set(bound.OPERATIONS)
        assert unknown == set(), f"the page names operations that do not exist: {unknown}"

    def test_every_operation_the_script_calls_is_a_real_operation(self, bound):
        called = set(re.findall(r'call\("([a-z_.]+)"', asset("app.js")))
        unknown = called - set(bound.OPERATIONS)
        assert unknown == set(), f"the script calls operations that do not exist: {unknown}"

    def test_the_script_reads_only_through_the_api_base(self):
        """Every request path traces back to one constant, so there is a single
        place where the dashboard's reach is defined."""
        source = asset("app.js")
        assert re.search(r'const API = "/api/v1";', source)

        targets = re.findall(r"fetch\(\s*([A-Za-z_$][\w$]*)", source)
        assert targets, "the dashboard should fetch something"
        for name in targets:
            if name == "API":
                continue
            assigned = re.findall(r"(?:const|let|var)\s+%s\s*=\s*([^;\n]+)" % name, source)
            assert assigned, f"fetch({name}) has no visible assignment"
            assert all("API" in expr for expr in assigned), \
                f"fetch({name}) is built without the API constant: {assigned}"

    def test_every_operation_the_dashboard_uses_is_a_read(self, bound):
        called = set(re.findall(r'call\("([a-z_.]+)"', asset("app.js")))
        writes = {name for name in called if bound.mode(name) != "read"}
        assert writes == set(), f"the dashboard would write through: {writes}"


class TestTheme:
    """A viewer with no explicit preference gets the system default, which means
    bare :root must already carry a complete palette."""

    def test_the_light_palette_is_defined_outside_any_media_query(self):
        css = asset("app.css")
        base = css.split("@media")[0]
        for token in ("--bg", "--surface", "--text", "--border",
                      "--ok", "--warn", "--bad", "--unknown"):
            assert f"{token}:" in base, f"{token} has no unconditional definition"

    def test_dark_is_reachable_by_preference_and_by_attribute(self):
        css = asset("app.css")
        assert "prefers-color-scheme: dark" in css
        assert ':root[data-theme="dark"]' in css
        assert ':root:not([data-theme="light"])' in css

    def test_the_body_paints_its_own_background(self):
        css = asset("app.css")
        body = css.split("body {")[1].split("}")[0]
        assert "background: var(--bg)" in body
