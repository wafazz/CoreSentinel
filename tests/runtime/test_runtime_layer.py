"""Runtime layer — configuration precedence, path containment, events, container.

Isolation note: every test that touches configuration must point CORE_CONFIG_FILE
at tmp_path. A test that reads the real coresentinel.config.json would pass or
fail depending on what the developer had set locally.
"""

import json

import pytest

from coresentinel_core.runtime import events as events_module
from coresentinel_core.runtime import paths
from coresentinel_core.runtime.config import Config, DEFAULTS, env_key
from coresentinel_core.runtime.container import Container, Runtime
from coresentinel_core.runtime.errors import (ConfigurationError, PathSecurityError,
                                              ServiceNotRegistered)
from coresentinel_core.runtime.events import EventBus
from coresentinel_core.runtime.logging import Logger, redact


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Configuration rooted in tmp_path, never the developer's real core config."""
    import coresentinel_core.runtime.config as config_module
    monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", tmp_path / "coresentinel.config.json")
    for key in list(DEFAULTS):
        monkeypatch.delenv(env_key(key), raising=False)
    return config_module


@pytest.fixture
def bound_project(tmp_path):
    """A directory bound to CoreSentinel, the way `init` leaves one."""
    root = tmp_path / "project"
    (root / ".coresentinel").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "fixture", "coresentinel_api": "1.0"}), encoding="utf-8")
    return root


class TestConfigurationPrecedence:
    def test_defaults_apply_when_nothing_overrides(self, isolated_config):
        config = Config.load(".")
        assert config.get("storage.backend") == DEFAULTS["storage.backend"]
        assert config.origin("storage.backend") == "default"

    def test_core_config_beats_default(self, isolated_config, tmp_path):
        isolated_config.CORE_CONFIG_FILE.write_text(
            json.dumps({"storage.backend": "sqlite"}), encoding="utf-8")
        config = Config.load(str(tmp_path))
        assert config.get("storage.backend") == "sqlite"
        assert config.origin("storage.backend") == "core-config"

    def test_project_config_beats_core_config(self, isolated_config, bound_project):
        isolated_config.CORE_CONFIG_FILE.write_text(
            json.dumps({"logging.level": "warn"}), encoding="utf-8")
        settings = json.loads((bound_project / ".coresentinel" / "config.json").read_text())
        settings["settings"] = {"logging.level": "debug"}
        (bound_project / ".coresentinel" / "config.json").write_text(json.dumps(settings))

        config = Config.load(str(bound_project))
        assert config.get("logging.level") == "debug"
        assert config.origin("logging.level") == "project-config"

    def test_environment_beats_every_file(self, isolated_config, bound_project, monkeypatch):
        isolated_config.CORE_CONFIG_FILE.write_text(
            json.dumps({"logging.level": "warn"}), encoding="utf-8")
        monkeypatch.setenv(env_key("logging.level"), "error")
        config = Config.load(str(bound_project))
        assert config.get("logging.level") == "error"
        assert config.origin("logging.level") == "environment"

    def test_explicit_override_beats_the_environment(self, isolated_config, monkeypatch):
        monkeypatch.setenv(env_key("logging.level"), "error")
        config = Config.load(".", {"logging.level": "debug"})
        assert config.get("logging.level") == "debug"
        assert config.origin("logging.level") == "override"

    def test_nested_json_is_addressed_by_dotted_key(self, isolated_config, tmp_path):
        isolated_config.CORE_CONFIG_FILE.write_text(
            json.dumps({"storage": {"backend": "sqlite"}}), encoding="utf-8")
        assert Config.load(str(tmp_path)).get("storage.backend") == "sqlite"

    def test_a_v1_project_config_without_settings_still_loads(self, isolated_config, bound_project):
        """Regression: `init` wrote config.json long before settings existed."""
        config = Config.load(str(bound_project))
        assert config.get("storage.backend") == DEFAULTS["storage.backend"]
        assert config.problems == []


class TestConfigurationTyping:
    @pytest.mark.parametrize("raw,expected", [("true", True), ("false", False),
                                              ("1", True), ("off", False)])
    def test_boolean_env_values_are_coerced(self, isolated_config, monkeypatch, raw, expected):
        monkeypatch.setenv(env_key("events.enabled"), raw)
        assert Config.load(".").get("events.enabled") is expected

    def test_integer_env_values_are_coerced(self, isolated_config, monkeypatch):
        monkeypatch.setenv(env_key("verification.pass_threshold"), "95")
        assert Config.load(".").get("verification.pass_threshold") == 95

    def test_a_malformed_env_value_is_reported_not_silently_used(self, isolated_config, monkeypatch):
        monkeypatch.setenv(env_key("verification.pass_threshold"), "high")
        config = Config.load(".")
        assert config.get("verification.pass_threshold") == DEFAULTS["verification.pass_threshold"]
        assert any("PASS_THRESHOLD" in p for p in config.problems)

    def test_a_corrupt_config_file_is_reported_not_fatal(self, isolated_config, tmp_path):
        isolated_config.CORE_CONFIG_FILE.write_text("{ not json", encoding="utf-8")
        config = Config.load(str(tmp_path))
        assert config.problems, "a corrupt config file must be reported"
        assert config.get("storage.backend") == DEFAULTS["storage.backend"]

    def test_unknown_keys_are_rejected_on_write(self, isolated_config):
        with pytest.raises(ConfigurationError):
            Config.load(".").set("storage.not_a_setting", "x")

    def test_set_persists_and_reloads(self, isolated_config, tmp_path):
        Config.load(str(tmp_path)).set("logging.level", "debug", "core")
        assert Config.load(str(tmp_path)).get("logging.level") == "debug"

    def test_project_scope_requires_a_bound_project(self, isolated_config, tmp_path):
        with pytest.raises(ConfigurationError):
            Config.load(str(tmp_path)).set("logging.level", "debug", "project", str(tmp_path))


class TestPathContainment:
    def test_a_path_inside_the_boundary_resolves(self, tmp_path):
        (tmp_path / "inside").mkdir()
        assert paths.resolve_within(tmp_path, "inside") == (tmp_path / "inside").resolve()

    @pytest.mark.parametrize("escape", ["../outside", "../../etc", "a/../../outside"])
    def test_traversal_is_refused(self, tmp_path, escape):
        with pytest.raises(PathSecurityError):
            paths.resolve_within(tmp_path, escape)

    def test_an_absolute_path_outside_is_refused(self, tmp_path):
        other = tmp_path.parent / "elsewhere"
        other.mkdir(exist_ok=True)
        with pytest.raises(PathSecurityError):
            paths.resolve_within(tmp_path / "base", other)

    def test_a_symlink_pointing_outside_is_refused(self, tmp_path):
        base, outside = tmp_path / "base", tmp_path / "outside"
        base.mkdir()
        outside.mkdir()
        try:
            (base / "link").symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("this platform does not permit symlink creation")
        with pytest.raises(PathSecurityError):
            paths.resolve_within(base, "link")

    def test_the_error_names_the_boundary_it_protected(self, tmp_path):
        with pytest.raises(PathSecurityError) as raised:
            paths.resolve_within(tmp_path, "../outside", "project")
        assert "project" in str(raised.value)


class TestEventBus:
    def test_a_subscriber_receives_its_event(self):
        bus, seen = EventBus(), []
        bus.subscribe(events_module.MEMORY_CREATED, seen.append)
        bus.emit(events_module.MEMORY_CREATED, {"fact": "x"})
        assert len(seen) == 1 and seen[0].payload == {"fact": "x"}

    def test_a_wildcard_subscriber_receives_everything(self):
        bus, seen = EventBus(), []
        bus.subscribe("*", seen.append)
        bus.emit(events_module.TASK_STARTED)
        bus.emit(events_module.TASK_COMPLETED)
        assert [e.name for e in seen] == [events_module.TASK_STARTED,
                                          events_module.TASK_COMPLETED]

    def test_a_failing_handler_never_fails_the_emitter(self):
        """An observer must not be able to break the operation it observed."""
        bus, seen = EventBus(), []

        def explode(event):
            raise RuntimeError("handler is broken")

        bus.subscribe(events_module.DECISION_CREATED, explode)
        bus.subscribe(events_module.DECISION_CREATED, seen.append)
        bus.emit(events_module.DECISION_CREATED)
        assert len(seen) == 1, "a later handler was skipped because an earlier one raised"

    def test_unsubscribe_stops_delivery(self):
        bus, seen = EventBus(), []
        bus.subscribe(events_module.TASK_STARTED, seen.append)
        bus.unsubscribe(events_module.TASK_STARTED, seen.append)
        bus.emit(events_module.TASK_STARTED)
        assert seen == []

    def test_a_disabled_bus_notifies_nobody(self):
        bus, seen = EventBus(enabled=False), []
        bus.subscribe("*", seen.append)
        bus.emit(events_module.TASK_STARTED)
        assert seen == []

    def test_every_declared_event_name_is_unique(self):
        assert len(events_module.KNOWN_EVENTS) == len(set(events_module.KNOWN_EVENTS))

    def test_eighteen_events_are_declared(self):
        assert len(events_module.KNOWN_EVENTS) == 18

    def test_an_event_records_its_name_and_time(self):
        record = EventBus().emit(events_module.PATTERN_DETECTED, {"id": "PAT-1"}).record()
        assert record["event"] == events_module.PATTERN_DETECTED
        assert record["occurred_at"] and record["payload"] == {"id": "PAT-1"}


class TestContainer:
    def test_a_factory_is_built_once(self):
        container, built = Container(), []
        container.register("thing", lambda: built.append(1) or object())
        first, second = container.get("thing"), container.get("thing")
        assert first is second and len(built) == 1

    def test_a_non_singleton_is_rebuilt(self):
        container = Container()
        container.register("thing", object, singleton=False)
        assert container.get("thing") is not container.get("thing")

    def test_an_unregistered_service_names_what_is_available(self):
        container = Container()
        container.register_instance("config", {})
        with pytest.raises(ServiceNotRegistered) as raised:
            container.get("missing")
        assert "config" in str(raised.value)

    def test_shutdown_closes_what_it_built(self):
        class Closable:
            closed = False

            def close(self):
                self.closed = True

        container = Container()
        container.register("thing", Closable)
        instance = container.get("thing")
        container.shutdown()
        assert instance.closed

    def test_shutdown_survives_a_failing_close(self):
        class Hostile:
            def close(self):
                raise RuntimeError("no")

        container = Container()
        container.register("thing", Hostile)
        container.get("thing")
        container.shutdown()


class TestRuntimeBootstrap:
    def test_bootstrap_registers_the_core_services(self, isolated_config, tmp_path):
        runtime = Runtime.bootstrap(str(tmp_path))
        assert {"config", "logger", "events"}.issubset(set(runtime.container.names()))
        runtime.shutdown()

    def test_bootstrap_is_fast(self, isolated_config, tmp_path):
        """Budget is 50 ms: CoreSentinel must reduce overhead, not add it."""
        runtime = Runtime.bootstrap(str(tmp_path))
        assert runtime.bootstrap_ms < 50, f"bootstrap took {runtime.bootstrap_ms:.1f} ms"
        runtime.shutdown()

    def test_the_store_is_not_opened_until_it_is_asked_for(self, isolated_config, tmp_path):
        runtime = Runtime.bootstrap(str(tmp_path))
        assert "store" not in runtime.container._instances
        runtime.shutdown()

    def test_a_storage_failure_does_not_break_event_emission(self, isolated_config, tmp_path):
        runtime = Runtime.bootstrap(str(tmp_path))
        runtime.container.register("store", lambda: (_ for _ in ()).throw(RuntimeError("no disk")))
        runtime.events.emit(events_module.MEMORY_CREATED, {"fact": "x"})
        runtime.shutdown()


class TestLogRedaction:
    @pytest.mark.parametrize("field", ["password", "api_key", "AUTH_TOKEN", "client_secret"])
    def test_sensitive_field_names_are_redacted(self, field):
        assert redact({field: "hunter2xxxxxxxxxxxx"})[field] == "[redacted]"

    def test_credential_shapes_inside_free_text_are_redacted(self):
        cleaned = redact("token is sk_live_abcdefghijklmnop1234 ok")
        assert "sk_live_abcdefghijklmnop1234" not in cleaned

    def test_ordinary_values_survive(self):
        assert redact({"stack": "Python"})["stack"] == "Python"

    def test_nested_structures_are_redacted(self):
        cleaned = redact({"outer": [{"secret": "abcdefghijklmnopqrst"}]})
        assert cleaned["outer"][0]["secret"] == "[redacted]"

    def test_logs_go_to_stderr_not_stdout(self, capsys):
        Logger().info("diagnostic")
        captured = capsys.readouterr()
        assert captured.out == "" and "diagnostic" in captured.err
