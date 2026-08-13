"""
Service container and runtime bootstrap.

Every v1 command constructs its own world: resolves paths from `__file__`,
re-reads the same JSON, and imports whatever engine it needs by bare name. There
is no object representing "CoreSentinel, configured, for this directory".

`Runtime.bootstrap()` is that object. Services are registered as factories and
built on first use, so bootstrapping stays cheap — the storage backend opens no
file and the database connects no socket until something asks for them.
"""

import time

from coresentinel_core.runtime import paths
from coresentinel_core.runtime.config import Config
from coresentinel_core.runtime.events import EventBus
from coresentinel_core.runtime.logging import Logger
from coresentinel_core.runtime.errors import ServiceNotRegistered


class Container:
    def __init__(self):
        self._factories = {}
        self._instances = {}

    def register(self, name, factory, singleton=True):
        self._factories[name] = (factory, singleton)
        self._instances.pop(name, None)
        return self

    def register_instance(self, name, instance):
        self._factories[name] = (lambda: instance, True)
        self._instances[name] = instance
        return self

    def has(self, name):
        return name in self._factories

    def get(self, name):
        if name in self._instances:
            return self._instances[name]
        if name not in self._factories:
            raise ServiceNotRegistered(
                f"no service registered as '{name}'",
                f"Registered services: {', '.join(sorted(self._factories)) or 'none'}")
        factory, singleton = self._factories[name]
        instance = factory()
        if singleton:
            self._instances[name] = instance
        return instance

    def names(self):
        return sorted(self._factories)

    def shutdown(self):
        """Close anything that knows how to close itself, newest first.

        One service failing to close must not leave the rest open, so the loop
        continues — but the failures are returned rather than swallowed. The
        caller logs them; discarding them here would hide a leaked handle behind
        a clean-looking shutdown.
        """
        failures = []
        for name in reversed(list(self._instances)):
            closer = getattr(self._instances[name], "close", None)
            if not callable(closer):
                continue
            try:
                closer()
            except Exception as e:
                failures.append({"service": name, "error": str(e)})
        self._instances.clear()
        return failures


class Runtime:
    """CoreSentinel, configured, for one working directory."""

    def __init__(self, config, logger, events, container, target_dir="."):
        self.config = config
        self.logger = logger
        self.events = events
        self.container = container
        self.target_dir = target_dir
        self.bootstrap_ms = 0

    @classmethod
    def bootstrap(cls, target_dir=".", overrides=None):
        started = time.perf_counter()

        config = Config.load(target_dir, overrides)
        logger = Logger(config.get("logging.level"), config.get("logging.format"))
        for problem in config.problems:
            logger.warn(problem)

        events = EventBus(logger, enabled=bool(config.get("events.enabled")))
        container = Container()
        runtime = cls(config, logger, events, container, target_dir)

        container.register_instance("config", config)
        container.register_instance("logger", logger)
        container.register_instance("events", events)
        # Lazy: opening a store touches the filesystem, and most commands never need one.
        container.register("store", lambda: runtime._build_store())

        if config.get("events.persist"):
            events.subscribe("*", runtime._persist_event)
            # Emitting an event is how something gets audited. A subsystem added
            # later either emits and is recorded, or does not and shows up as an
            # unrecorded subject in `coresentinel audit coverage`.
            from coresentinel_core.audit import subjects
            subjects.install(runtime)

        runtime.bootstrap_ms = (time.perf_counter() - started) * 1000
        return runtime

    def _build_store(self):
        from coresentinel_core.storage import open_store
        return open_store(self.config, self.target_dir)

    def _persist_event(self, event):
        # Persistence must never be the reason an operation fails, so a storage
        # problem degrades to a warning rather than propagating to the emitter.
        try:
            self.store.events.append(event.record())
        except Exception as e:
            self.logger.warn("event not persisted", event=event.name, error=str(e))

    @property
    def store(self):
        return self.container.get("store")

    @property
    def project_root(self):
        return self.config.project_root

    def store_root(self):
        return paths.store_root(self.target_dir)

    def shutdown(self):
        for failure in self.container.shutdown():
            self.logger.warn("service did not close cleanly", **failure)
