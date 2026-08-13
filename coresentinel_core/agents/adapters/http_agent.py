"""
HTTP agent adapter — for hosts that expose an endpoint rather than a binary.

stdlib `urllib` only; adding `requests` for one POST would not earn its place.

Invocation consumes `network.access`, which no contract grants by default. That
is deliberate: reaching the network is the one thing an agent can do whose blast
radius leaves the machine entirely, and it should take an explicit grant.

Credentials come from the environment by name — the registry records *which*
variable holds the token, never the token.
"""

import os
import json
import time
import urllib.error
import urllib.request

from coresentinel_core.agents import protocol
from coresentinel_core.agents import permissions as perms
from coresentinel_core.agents.adapters.base import AgentAdapter

DEFAULT_TIMEOUT = 120


class HttpAgentAdapter(AgentAdapter):
    transport = "http"
    permission = perms.NETWORK_ACCESS

    def endpoint(self):
        return self.profile.get("endpoint")

    def scope(self):
        endpoint = self.endpoint() or ""
        return endpoint.split("//", 1)[-1].split("/", 1)[0] or self.id

    def available(self):
        if not self.endpoint():
            return False, "no endpoint is declared in adapters.json"
        variable = self.profile.get("auth_env")
        if variable and not os.environ.get(variable):
            return False, f"{variable} is not set in the environment"
        return True, f"endpoint {self.endpoint()}"

    def _headers(self):
        headers = {"Content-Type": "application/json",
                   "User-Agent": "CoreSentinel"}
        headers.update(self.profile.get("headers") or {})
        variable = self.profile.get("auth_env")
        if variable and os.environ.get(variable):
            template = self.profile.get("auth_header", "Bearer {token}")
            headers["Authorization"] = template.replace("{token}", os.environ[variable])
        return headers

    def _invoke(self, task, sandbox, prompt):
        payload = dict(self.profile.get("body") or {})
        payload[self.profile.get("prompt_field", "prompt")] = prompt

        request = urllib.request.Request(
            self.endpoint(), data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(), method=self.profile.get("method", "POST"))

        started = time.perf_counter()
        status, body, error = None, "", None
        try:
            with urllib.request.urlopen(
                    request, timeout=int(self.profile.get("timeout", DEFAULT_TIMEOUT))) as response:
                status = response.status
                body = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read().decode("utf-8", "replace")
            error = f"HTTP {e.code}"
        except (urllib.error.URLError, OSError, ValueError) as e:
            error = str(e)

        duration = int((time.perf_counter() - started) * 1000)
        ok = status is not None and 200 <= status < 300

        sandbox.actions.append({"action": "http", "target": self.endpoint(),
                                "detail": f"status {status}" if status else error})

        if status is None:
            return protocol.build_result(
                task, protocol.FAILED,
                f"{self.name} could not be reached: {error}",
                unresolved=[error or "no response"])

        evidence = {
            "check": f"{self.name} invocation",
            # The endpoint, never the credential that reached it.
            "command": f"{self.profile.get('method', 'POST')} {self.endpoint()}",
            "cwd": None, "started_at": None, "duration_ms": duration,
            "exit_code": status, "output_digest": None,
            "output_excerpt": body[:400], "error": error,
            "status": "PASS" if ok else "FAIL",
        }

        return self.normalise(task, body, evidence, ok,
                              exit_detail=f"{self.name} responded {status}")
