"""
Path resolution and containment.

CoreSentinel takes directory arguments from the command line (`--project`,
`init <dir>`, adapter bind targets) and writes files at those paths. Nothing
previously checked that a resolved path stayed inside the boundary it was
supposed to, so `--project ../../etc` resolved wherever it pointed.

`resolve_within` raises instead of returning a flag, because a containment
breach must not be ignorable by forgetting to check a return value.
"""

import os
from pathlib import Path

from coresentinel_core import CORE_ROOT
from coresentinel_core.runtime.errors import PathSecurityError

CONFIG_DIRNAME = ".coresentinel"
DB_FILENAME = "coresentinel.db"


def core_root():
    return CORE_ROOT


def expand(candidate):
    """User and environment expansion, then absolute resolution. Never raises."""
    text = os.path.expandvars(os.path.expanduser(str(candidate)))
    return Path(text).resolve()


def is_within(base, candidate):
    """Whether `candidate` resolves inside `base`. Symlinks are resolved first."""
    base_resolved = Path(base).resolve()
    try:
        Path(candidate).resolve().relative_to(base_resolved)
    except (ValueError, OSError):
        return False
    return True


def resolve_within(base, candidate, label="path"):
    """Resolve `candidate` and require it to stay inside `base`.

    Accepts absolute paths that are already inside the boundary; rejects
    traversal (`../`), absolute escapes, and symlinks that point outside.
    """
    base_resolved = Path(base).resolve()
    raw = Path(os.path.expandvars(os.path.expanduser(str(candidate))))
    target = raw if raw.is_absolute() else base_resolved / raw

    try:
        resolved = target.resolve()
    except OSError as e:
        raise PathSecurityError(f"{label} could not be resolved: {candidate} ({e})",
                                "Check the path exists and is readable")

    if not is_within(base_resolved, resolved):
        raise PathSecurityError(
            f"{label} escapes its boundary: {candidate} resolves to {resolved}, "
            f"which is outside {base_resolved}",
            f"Use a path inside {base_resolved}")
    return resolved


def find_project_root(start="."):
    """The nearest ancestor bound to CoreSentinel, the way git looks for .git.

    Delegates to the memory engine rather than reimplementing the walk — two
    copies of this rule would eventually disagree about which store a fact
    belongs to.
    """
    import coresentinel_memory as mem
    return mem.find_project_root(start)


def config_dir(start="."):
    root = find_project_root(start)
    return (root / CONFIG_DIRNAME) if root else None


def core_db_path():
    return CORE_ROOT / DB_FILENAME


def project_db_path(start="."):
    directory = config_dir(start)
    return (directory / DB_FILENAME) if directory else None


def store_root(start="."):
    """Where records for this working directory belong: the bound project, else the Core.

    Mirrors how the memory engine scopes working/session/project layers, so a
    verification run recorded against a repository stays with that repository.
    """
    directory = config_dir(start)
    return directory if directory else CORE_ROOT
