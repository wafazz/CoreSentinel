"""CoreSentinel persistence — one port, two interchangeable backends."""

from coresentinel_core.runtime import paths
from coresentinel_core.runtime.errors import StorageError
from coresentinel_core.storage.ports import Store, Repository, COLLECTIONS
from coresentinel_core.storage.json_store import JsonStore
from coresentinel_core.storage.sqlite_store import SqliteStore

BACKENDS = {"json": JsonStore, "sqlite": SqliteStore}


def open_store(config, target_dir="."):
    """Open the configured backend, rooted at this directory's record store.

    Records follow the same scoping rule as memory: work done on a repository
    belongs to that repository, not to whichever Core happened to drive it.
    """
    name = str(config.get("storage.backend", "json")).lower()
    if name not in BACKENDS:
        raise StorageError(f"unknown storage backend '{name}'",
                           f"Set storage.backend to one of: {', '.join(sorted(BACKENDS))}")
    return BACKENDS[name](paths.store_root(target_dir))


__all__ = ["Store", "Repository", "JsonStore", "SqliteStore",
           "BACKENDS", "COLLECTIONS", "open_store"]
