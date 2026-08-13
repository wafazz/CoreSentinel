"""CoreSentinel memory — task-relevant context assembly.

The layered store, lifecycle and recall engines remain the flat
`coresentinel_memory` / `coresentinel_lifecycle` / `coresentinel_recall` modules
at the Core root. Relocating them behind a re-export shim would break the test
isolation those engines depend on: the fixtures patch `MEMORY_DIR` and
`MEMORY_LAYERS` on the module object, and a function living in a different module
reads its own globals, not the patched ones. The suite would then write to the
real `memory/` directory — the incident `30-selftest-protocol.md` records the
fixtures as existing to prevent.

Moving them needs `sys.modules` aliasing or a fixture rewrite, neither of which
belongs in the same change as new behaviour.
"""

from coresentinel_core.memory import assembly

__all__ = ["assembly"]
