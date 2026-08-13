"""
CoreSentinel Core — runtime and persistence.

The v1 engines are flat `coresentinel_*.py` modules at the Core root, each
resolving its own paths from `__file__`, reading and writing JSON directly, and
printing its report in the same function that computes it. This package is the
layer underneath them: configuration, path safety, events, logging, a service
container, and a persistence port with two interchangeable backends.

Nothing here changes engine behaviour. Phase 3 onward migrates the engines in
behind re-export shims; until then the two coexist and the engines opt in.

Why the name is not `coresentinel`: the Core root already contains `coresentinel`,
the POSIX wrapper script that puts the CLI on PATH, and `coresentinel.py`, the
entry point every wrapper, CI job and test fixture invokes. A directory cannot
share a name with a file in the same directory, and renaming either one would
break the documented command surface.
"""

from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parent.parent

__all__ = ["CORE_ROOT"]
