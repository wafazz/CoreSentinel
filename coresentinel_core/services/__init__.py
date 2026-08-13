"""
The service layer — one implementation of every operation, three ways in.

The CLI, the HTTP API and the MCP server are *surfaces*. They parse a request
and render a response; they do not decide anything. Everything they can do lives
here, which is what makes the guarantee at the centre of this phase possible:

    the same operation, through any surface, produces the same audit record

A surface that reached past this layer into storage or an engine could write
without emitting, and an unaudited write through a side door makes the whole
trail a statement about one entrance. A test walks the import graph and fails the
build if `api/` or `mcp/` imports `storage/` or an engine module directly.

Every mutating method emits an event. Auditing is a subscriber (Phase 7), so
emitting is how a change gets recorded — not something a caller has to remember.
"""

from coresentinel_core.services.facade import Services, open_services

__all__ = ["Services", "open_services"]
