"""
CoreSentinel error hierarchy.

Every engine currently signals failure three different ways: a printed `[!]`
line, a `(data, error)` tuple, or a bare `except Exception`. The tuple form is
good and stays. This hierarchy gives the runtime and storage layers a typed
alternative, so a caller can distinguish "the config is wrong" from "the disk is
broken" from "that path escapes the project".

Every error carries a `remedy` — the same contract `doctor` already keeps, where
a finding that cannot tell you what to do about it is only half a finding.
"""


class CoreSentinelError(Exception):
    """Base for every error the runtime raises deliberately."""

    def __init__(self, message, remedy=None):
        super().__init__(message)
        self.message = message
        self.remedy = remedy

    def __str__(self):
        if self.remedy:
            return f"{self.message}\n  ➔ {self.remedy}"
        return self.message


class ConfigurationError(CoreSentinelError):
    """A setting is missing, malformed, or of the wrong type."""


class PathSecurityError(CoreSentinelError):
    """A path resolved outside the boundary it was required to stay within.

    Raised rather than returned: a containment breach is never something the
    caller should be able to ignore by forgetting to check a return value.
    """


class StorageError(CoreSentinelError):
    """A repository could not read or write."""


class MigrationError(StorageError):
    """A schema migration is missing, out of order, or has changed after being applied."""


class ServiceNotRegistered(CoreSentinelError):
    """A service was requested from the container before anything registered it."""
