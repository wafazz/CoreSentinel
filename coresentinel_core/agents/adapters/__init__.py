"""
Agent adapters — the same Core, invoked through whichever host you have.

`adapters.json` stays the one registry. A host that only receives a rendered
rules file needs nothing new; a host that can be *invoked* declares an `invoke`
block, and adding one is a JSON entry rather than a code change.

The v1 projection (`coresentinel adapter sync`) is untouched. Invocation is a
separate capability on the same registry, not a replacement for it.
"""

from coresentinel_core.agents.adapters.base import (AgentAdapter, conformance,
                                                    build_prompt, UNVERIFIED_NOTE)
from coresentinel_core.agents.adapters.cli_agent import CliAgentAdapter
from coresentinel_core.agents.adapters.http_agent import HttpAgentAdapter
from coresentinel_core.agents.adapters.mcp_agent import McpAgentAdapter

TRANSPORTS = {
    "cli": CliAgentAdapter,
    "http": HttpAgentAdapter,
    "mcp": McpAgentAdapter,
}


def _registry():
    import coresentinel_adapters as adapters
    return adapters.get_adapters()


def for_descriptor(descriptor):
    """The adapter class a descriptor asks for, or None when it declares no invocation."""
    profile = (descriptor or {}).get("invoke") or {}
    implementation = TRANSPORTS.get(str(profile.get("transport", "")).lower())
    return implementation(descriptor) if implementation else None


def resolve(host_id):
    """The invocable adapter for a host id, or None."""
    import coresentinel_adapters as adapters
    descriptor = adapters.find_adapter(host_id)
    return for_descriptor(descriptor) if descriptor else None


def invocable():
    """Every host that declares an invocation profile."""
    return [adapter for adapter in (for_descriptor(d) for d in _registry()) if adapter]


def available():
    """Every invocable host that is actually present on this machine."""
    return [adapter for adapter in invocable() if adapter.available()[0]]


def describe_all():
    return [adapter.describe() for adapter in invocable()]


def conformance_report():
    return [conformance(adapter) for adapter in invocable()]


__all__ = ["AgentAdapter", "CliAgentAdapter", "HttpAgentAdapter", "McpAgentAdapter",
           "TRANSPORTS", "resolve", "invocable", "available", "describe_all",
           "conformance", "conformance_report", "build_prompt", "UNVERIFIED_NOTE"]
