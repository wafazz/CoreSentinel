"""
Layered configuration.

`memorycore.conf` was written by both installers and read by no engine — dead
config carrying another machine's absolute paths. Every engine instead hardcoded
its own constants: three different subprocess timeouts, a compaction budget, a
decay rate, a pass threshold, none of them adjustable without editing source.

Precedence, lowest to highest:

    defaults  <  core config file  <  project config file  <  environment  <  explicit override

Every resolved value remembers which layer produced it. `coresentinel config get`
prints that provenance, because a setting whose origin you cannot see is a
setting you will eventually misattribute.
"""

import os
import json
from pathlib import Path

from coresentinel_core import CORE_ROOT
from coresentinel_core.runtime.errors import ConfigurationError
from coresentinel_core.runtime import paths

CORE_CONFIG_FILE = CORE_ROOT / "coresentinel.config.json"

# Project settings live under the "settings" key of the existing
# .coresentinel/config.json, so binding data written by `init` is untouched and a
# v1 project config (which has no such key) still loads.
PROJECT_SETTINGS_KEY = "settings"

ENV_PREFIX = "CORESENTINEL_"

DEFAULTS = {
    "storage.backend": "json",
    "storage.sqlite.enabled": True,

    "verification.pass_threshold": 80,
    "verification.min_evidence_weight": 50,
    "verification.test_timeout": 600,
    "verification.audit_timeout": 180,

    "exec.default_timeout": 120,
    "exec.git_timeout": 30,

    "memory.compact_budget": 150,
    "memory.decay_per_30_days": 0.05,
    "memory.decay_floor": 0.30,
    "memory.stale_after_days": 30,

    "health.min_known_dimensions": 3,

    "logging.level": "info",
    "logging.format": "text",

    "events.enabled": True,
    "events.persist": True,
    # The in-memory tail of emitted events. Bounded so a long-running server
    # does not retain every event it has ever seen.
    "events.buffer": 256,

    "metrics.enabled": True,
    "metrics.max_series": 512,

    # Every list surface pages. A caller asking for more than the maximum gets
    # the maximum and is told the result was clamped.
    "api.page_size": 50,
    "api.max_page_size": 200,

    # Loopback by default. Binding wider without a token is refused at startup,
    # not at the first request.
    "api.host": "127.0.0.1",
    "api.port": 7878,
    "api.token": "",
    "api.threaded": False,
}

LAYER_DEFAULT = "default"
LAYER_CORE = "core-config"
LAYER_PROJECT = "project-config"
LAYER_ENV = "environment"
LAYER_OVERRIDE = "override"

SCOPES = {"core": LAYER_CORE, "project": LAYER_PROJECT}


def env_key(dotted):
    return ENV_PREFIX + dotted.replace(".", "_").upper()


def _coerce(value, reference):
    """Environment variables arrive as strings; keep a setting's declared type."""
    if reference is None or isinstance(value, type(reference)):
        return value
    if isinstance(reference, bool):
        lowered = str(value).strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
        raise ConfigurationError(f"expected a boolean, got '{value}'",
                                 "Use one of: true, false, 1, 0, yes, no, on, off")
    if isinstance(reference, int):
        try:
            return int(str(value).strip())
        except ValueError:
            raise ConfigurationError(f"expected an integer, got '{value}'", None)
    if isinstance(reference, float):
        try:
            return float(str(value).strip())
        except ValueError:
            raise ConfigurationError(f"expected a number, got '{value}'", None)
    return value


def _flatten(data, prefix=""):
    """Nested config objects addressed by dotted key."""
    flat = {}
    for key, value in (data or {}).items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, dotted + "."))
        else:
            flat[dotted] = value
    return flat


def _read_json(path):
    if not path or not Path(path).exists():
        return {}, None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return (data if isinstance(data, dict) else {}), None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return {}, str(e)


class Config:
    """Resolved settings plus the layer each value came from."""

    def __init__(self, values, origins, problems=None, project_root=None):
        self._values = values
        self._origins = origins
        self.problems = problems or []
        self.project_root = project_root

    @classmethod
    def load(cls, target_dir=".", overrides=None):
        values = dict(DEFAULTS)
        origins = {key: LAYER_DEFAULT for key in DEFAULTS}
        problems = []

        core_data, error = _read_json(CORE_CONFIG_FILE)
        if error:
            problems.append(f"{CORE_CONFIG_FILE.name} unreadable ({error}) — ignored")
        for key, value in _flatten(core_data).items():
            values[key], origins[key] = value, LAYER_CORE

        project_root = paths.find_project_root(target_dir)
        if project_root:
            directory = project_root / paths.CONFIG_DIRNAME
            project_data, error = _read_json(directory / "config.json")
            if error:
                problems.append(f"{directory / 'config.json'} unreadable ({error}) — ignored")
            for key, value in _flatten(project_data.get(PROJECT_SETTINGS_KEY, {})).items():
                values[key], origins[key] = value, LAYER_PROJECT

        for key in list(values):
            raw = os.environ.get(env_key(key))
            if raw is None:
                continue
            try:
                values[key] = _coerce(raw, DEFAULTS.get(key))
                origins[key] = LAYER_ENV
            except ConfigurationError as e:
                problems.append(f"{env_key(key)}: {e.message} — ignored")

        for key, value in (overrides or {}).items():
            values[key], origins[key] = value, LAYER_OVERRIDE

        return cls(values, origins, problems, project_root)

    def get(self, key, default=None):
        return self._values.get(key, DEFAULTS.get(key, default))

    def origin(self, key):
        return self._origins.get(key, LAYER_DEFAULT)

    def keys(self):
        return sorted(self._values)

    def as_dict(self):
        return dict(self._values)

    def explain(self, key):
        if key not in self._values and key not in DEFAULTS:
            raise ConfigurationError(f"unknown setting '{key}'",
                                     "Run 'coresentinel config list' for every known key")
        return {"key": key, "value": self.get(key), "origin": self.origin(key),
                "default": DEFAULTS.get(key)}

    def set(self, key, value, scope="core", target_dir="."):
        """Persist a setting to the core or project config file. Returns the path written."""
        if key not in DEFAULTS:
            raise ConfigurationError(f"unknown setting '{key}'",
                                     "Run 'coresentinel config list' for every known key")
        if scope not in SCOPES:
            raise ConfigurationError(f"unknown scope '{scope}'",
                                     "Use --scope core or --scope project")

        typed = _coerce(value, DEFAULTS.get(key))

        if scope == "core":
            path = CORE_CONFIG_FILE
            data, error = _read_json(path)
            if error:
                raise ConfigurationError(f"{path} is unreadable ({error})",
                                         "Repair or delete the file — overwriting it would "
                                         "discard the settings it holds")
            data[key] = typed
        else:
            root = paths.find_project_root(target_dir)
            if not root:
                raise ConfigurationError("no bound project in this directory",
                                         "Run 'coresentinel init' first, or use --scope core")
            path = root / paths.CONFIG_DIRNAME / "config.json"
            data, error = _read_json(path)
            if error:
                raise ConfigurationError(f"{path} is unreadable ({error})",
                                         "Repair or delete the file — overwriting it would "
                                         "discard the project binding")
            data.setdefault(PROJECT_SETTINGS_KEY, {})[key] = typed

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self._values[key] = typed
        self._origins[key] = SCOPES[scope]
        return path
