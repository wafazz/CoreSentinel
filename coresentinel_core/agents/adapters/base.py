"""
The agent adapter contract.

v1's adapter layer projected the Core *onto* a host: it rendered a rules file the
assistant would read. That still works and is untouched. This is the other
direction — invoking a host and normalising what comes back.

The rule that shapes every adapter here:

    An adapter proves that an agent ran and what it said.
    It does not prove that what the agent said is true.

So the only evidence an invocation produces is the invocation itself — the
command, its exit code, its duration, a digest of its output. Everything inside
the response is recorded as a **claim**, and claims are what `coresentinel verify`
exists to check against the repository afterwards. An adapter that turned "I
added tests" into evidence of tests would reintroduce, at the vendor boundary,
exactly the fabrication Phase 1 removed from the middle of the product.
"""

import json
import hashlib

from coresentinel_core.agents import protocol
from coresentinel_core.agents import permissions as perms

# Fields a vendor may return that map onto the result contract. Anything else in
# a structured response is kept under `raw` rather than silently dropped.
CLAIM_FIELDS = ["files_changed", "commands_run", "tests", "warnings", "unresolved"]

UNVERIFIED_NOTE = ("the agent's response is its own account of what it did; "
                   "nothing in this result verifies it — run 'coresentinel verify'")


def digest(text):
    return "sha256:" + hashlib.sha256(str(text or "").encode("utf-8", "replace")).hexdigest()[:12]


def build_prompt(task, context_pack=None):
    """What the host is actually asked to do, with its governance attached."""
    lines = [f"Objective: {task['objective']}", ""]
    if task.get("constraints"):
        lines.append("Constraints you must respect:")
        lines += [f"  - {c}" for c in task["constraints"]]
        lines.append("")
    if context_pack:
        lines.append(context_pack)
        lines.append("")
    lines.append("Report what you changed and what you verified. Do not claim a result "
                 "you did not observe.")
    return "\n".join(lines)


class AgentAdapter:
    """One host, invoked. Subclasses implement `_invoke`."""

    transport = "abstract"
    # The permission an invocation over this transport consumes.
    permission = perms.SHELL_EXECUTE

    def __init__(self, descriptor):
        self.descriptor = descriptor or {}
        self.id = self.descriptor.get("id", "unknown")
        self.name = self.descriptor.get("name", self.id)
        self.profile = self.descriptor.get("invoke") or {}

    # ---------------------------------------------------------------- contract

    def available(self):
        """(bool, reason). Never raises — an absent host is a fact, not an error."""
        return False, "this adapter declares no invocation profile"

    def scope(self):
        """What a LIMITED grant is matched against for this adapter."""
        return self.id

    def describe(self):
        installed, reason = self.available()
        return {"id": self.id, "name": self.name, "transport": self.transport,
                "permission": self.permission, "available": installed, "reason": reason,
                "profile": {k: v for k, v in self.profile.items() if k != "headers"}}

    def invoke(self, task, sandbox, context_pack=None):
        """Run the host under the agent's permissions and normalise the response."""
        installed, reason = self.available()
        if not installed:
            return protocol.build_result(task, protocol.UNSUPPORTED,
                                         f"{self.name} cannot be invoked: {reason}",
                                         unresolved=[reason])

        decision = sandbox.allows(self.permission, self.scope())
        if not decision.allowed:
            return protocol.build_result(
                task, protocol.DENIED,
                f"{self.name} invocation blocked: {decision.reason}",
                denials=[decision.record()])

        prompt = build_prompt(task, context_pack)
        return self._invoke(task, sandbox, prompt)

    def _invoke(self, task, sandbox, prompt):
        raise NotImplementedError

    # ---------------------------------------------------------------- normalisation

    def normalise(self, task, raw_text, evidence_item, ok, exit_detail=None):
        """Vendor response -> AgentResult, with claims kept separate from evidence."""
        parsed, structured = self._parse(raw_text)

        summary = (structured.get("summary")
                   or next((line.strip() for line in str(raw_text or "").splitlines()
                            if line.strip()), "")
                   or f"{self.name} returned no output")

        result = protocol.build_result(
            task,
            protocol.COMPLETED if ok else protocol.FAILED,
            summary[:400],
            confidence=structured.get("confidence"),
            evidence=[evidence_item],
            raw_response_ref=digest(raw_text),
            warnings=list(structured.get("warnings") or []) + [UNVERIFIED_NOTE],
            unresolved=list(structured.get("unresolved") or [])
            + ([] if ok else [exit_detail or "the host exited non-zero"]))

        # Claimed, not observed. Kept in their own block so nothing downstream can
        # mistake a vendor's self-report for something CoreSentinel checked.
        result["claims"] = {field: list(structured.get(field) or []) for field in CLAIM_FIELDS}
        result["claims"]["response_format"] = "json" if parsed else "text"
        result["adapter"] = {"id": self.id, "transport": self.transport}
        return result

    def _parse(self, raw_text):
        """(was_json, fields). A host that emits JSON gets structured; text does not."""
        if str(self.profile.get("response", {}).get("format", "text")).lower() != "json":
            return False, {}
        try:
            data = json.loads(str(raw_text or "").strip())
        except (json.JSONDecodeError, ValueError):
            return False, {}
        if not isinstance(data, dict):
            return False, {}

        mapping = self.profile.get("response", {}).get("fields") or {}
        fields = {}
        for target, source in mapping.items():
            if source in data:
                fields[target] = data[source]
        for key in ["summary", "confidence"] + CLAIM_FIELDS:
            if key in data and key not in fields:
                fields[key] = data[key]
        return True, fields


# ---------------------------------------------------------------- conformance

CONFORMANCE_CHECKS = [
    ("declares an id", lambda a: bool(a.id)),
    ("declares a transport", lambda a: a.transport != "abstract"),
    ("declares the permission it consumes", lambda a: a.permission in perms.PERMISSIONS),
    ("reports availability without raising", lambda a: isinstance(a.available(), tuple)),
    ("describes itself as a dictionary", lambda a: isinstance(a.describe(), dict)),
    ("implements invocation", lambda a: a.__class__._invoke is not AgentAdapter._invoke),
    ("declares a scope for LIMITED grants", lambda a: bool(a.scope())),
]


def conformance(adapter):
    """Every adapter answers the same questions. One that cannot is not an adapter."""
    results = []
    for label, check in CONFORMANCE_CHECKS:
        try:
            passed, detail = bool(check(adapter)), None
        except Exception as e:
            passed, detail = False, f"{type(e).__name__}: {e}"
        results.append({"check": label, "passed": passed, "detail": detail})
    return {"adapter": adapter.id, "checks": results,
            "conforms": all(item["passed"] for item in results)}
