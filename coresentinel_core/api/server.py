"""
The HTTP API — stdlib only, versioned from birth, loopback by default.

Routes are generated from the service catalogue, so an operation appears here the
moment it exists there and never drifts out of step with the CLI.

Two rules the server will not start without:

  * **A non-loopback bind requires a token.** Binding to 0.0.0.0 without one puts
    an unauthenticated governance system on the network, and the refusal is at
    startup rather than at the first request.
  * **Every write requires the token, on any interface.** A local server is
    reachable by every process on the machine, and "it's only localhost" is how
    a control becomes a formality.

Reads over loopback are open, because that is the case where the caller already
has the files.

`http.server` is single-threaded and is not a production web server. It is here
because CoreSentinel is local-first and a dependency for one JSON endpoint would
not earn its place. `serve --threaded` is available when a dashboard needs
concurrent reads.
"""

import json
import re
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

API_VERSION = "v1"
BASE_PATH = f"/api/{API_VERSION}"

LOOPBACK = {"127.0.0.1", "::1", "localhost"}

TOKEN_HEADER = "X-CoreSentinel-Token"
TOKEN_ENV = "CORESENTINEL_API_TOKEN"

# operation -> URL segment. Dots read badly in a path.
def route_for(operation):
    return f"{BASE_PATH}/" + operation.replace(".", "/")


class ApiError(Exception):
    def __init__(self, status, code, message, remedy=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.remedy = remedy


def generate_token():
    return secrets.token_urlsafe(24)


def resolve_token(config):
    """Configured token, else the environment, else None."""
    import os
    return config.get("api.token") or os.environ.get(TOKEN_ENV) or None


def is_loopback(host):
    return str(host or "").strip("[]") in LOOPBACK


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "CoreSentinel"
    sys_version = ""

    # Injected by build_server.
    services = None
    token = None
    logger = None

    # ---------------------------------------------------------------- plumbing

    def log_message(self, fmt, *args):
        if self.logger:
            self.logger.debug("api request", request=fmt % args)

    def _send(self, status, payload):
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-CoreSentinel-Api", API_VERSION)
        self.end_headers()
        self.wfile.write(body)

    def _fail(self, error):
        self._send(error.status, {"error": {"code": error.code, "message": error.message,
                                            "remedy": error.remedy}})

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw or b"{}")
        except (json.JSONDecodeError, ValueError) as e:
            raise ApiError(400, "MALFORMED_JSON", f"the request body is not JSON ({e})")
        if not isinstance(data, dict):
            raise ApiError(400, "MALFORMED_JSON", "the request body must be a JSON object")
        return data

    def _authorise(self, mode):
        """Writes always need the token. Reads need it off loopback."""
        supplied = self.headers.get(TOKEN_HEADER)
        client = self.client_address[0] if self.client_address else ""

        if mode == "read" and is_loopback(client):
            return
        if not self.token:
            raise ApiError(503, "NO_TOKEN_CONFIGURED",
                           "this server has no token, so it cannot authorise the request",
                           "Restart with 'coresentinel serve' — it generates one")
        if not supplied or not secrets.compare_digest(str(supplied), str(self.token)):
            raise ApiError(401, "UNAUTHORISED",
                           "a valid token is required",
                           f"Send it as the {TOKEN_HEADER} header. Writes always require "
                           "it; reads require it from anywhere but loopback")

    # ---------------------------------------------------------------- routing

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = re.sub(r"/+$", "", parsed.path) or "/"

        if path == BASE_PATH:
            return self._send(200, self._index())
        if path == f"{BASE_PATH}/health/live":
            return self._send(200, {"status": "ok", "api": API_VERSION})

        # The dashboard. Static bytes from a fixed allowlist — a browser has no
        # way into this process except through /api/v1, which is the point.
        if method == "GET" and self._serve_asset(path):
            return None

        operation = next((name for name in self.services.OPERATIONS
                          if route_for(name) == path), None)
        if operation is None:
            raise ApiError(404, "UNKNOWN_ROUTE", f"no route for {path}",
                           f"See {BASE_PATH} for the catalogue")

        mode = self.services.mode(operation)
        if mode == "write" and method != "POST":
            raise ApiError(405, "METHOD_NOT_ALLOWED",
                           f"{operation} changes state and must be POSTed")
        if mode == "read" and method not in ("GET", "POST"):
            raise ApiError(405, "METHOD_NOT_ALLOWED", f"{operation} is a read")

        self._authorise(mode)

        arguments = {k: (v[0] if len(v) == 1 else v)
                     for k, v in parse_qs(parsed.query).items()}
        if method == "POST":
            arguments.update(self._body())

        from coresentinel_core.services.facade import ServiceError
        try:
            result = self.services.call(operation, arguments)
        except ServiceError as e:
            raise ApiError(400, e.code, e.message, e.remedy)

        self._send(200, {"operation": operation, "result": result})

    def _serve_asset(self, path):
        """Send a dashboard asset if this path names one. True when handled."""
        from coresentinel_core import web

        asset = web.resolve(path)
        if asset is None:
            return False
        body, content_type = asset
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # The dashboard fetches only same-origin JSON and loads no remote asset,
        # so the policy can be this tight.
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
                         "style-src 'self'; script-src 'self'; base-uri 'none'; "
                         "form-action 'none'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)
        return True

    def _index(self):
        return {
            "coresentinel_api": API_VERSION,
            "operations": {name: {"mode": mode, "route": route_for(name)}
                           for name, (mode, _) in sorted(self.services.OPERATIONS.items())},
            "auth": {"header": TOKEN_HEADER,
                     "writes": "always require the token",
                     "reads": "open over loopback, token required from anywhere else"},
        }

    def do_GET(self):
        self._guarded("GET")

    def do_POST(self):
        self._guarded("POST")

    def _guarded(self, method):
        try:
            self._dispatch(method)
        except ApiError as e:
            self._fail(e)
        except Exception as e:
            # An unexpected failure must not leak a stack trace to a caller.
            if self.logger:
                self.logger.error("api request failed", error=str(e))
            self._fail(ApiError(500, "INTERNAL_ERROR", "the request could not be completed"))


def build_server(services, host="127.0.0.1", port=7878, token=None, threaded=False):
    """Construct the server, refusing an unsafe bind before it listens."""
    if not is_loopback(host) and not token:
        raise ApiError(400, "UNSAFE_BIND",
                       f"refusing to bind {host} without a token",
                       "Binding beyond loopback without auth puts an unauthenticated "
                       "governance system on the network. Set api.token, or bind 127.0.0.1")

    handler = type("BoundApiHandler", (ApiHandler,),
                   {"services": services, "token": token,
                    "logger": getattr(services.runtime, "logger", None)})
    server_class = ThreadingHTTPServer if threaded else HTTPServer
    return server_class((host, int(port)), handler)


def serve(services, host="127.0.0.1", port=7878, token=None, threaded=False):
    server = build_server(services, host, port, token, threaded)
    try:
        server.serve_forever()
    finally:
        server.server_close()
