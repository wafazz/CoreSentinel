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
from coresentinel_core.observability.metrics import Metrics


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

    def __init__(self, config, logger, events, container, target_dir=".", metrics=None):
        self.config = config
        self.logger = logger
        self.events = events
        self.container = container
        self.target_dir = target_dir
        self.metrics = metrics
        self.bootstrap_ms = 0

    @classmethod
    def bootstrap(cls, target_dir=".", overrides=None):
        started = time.perf_counter()

        config = Config.load(target_dir, overrides)
        logger = Logger(config.get("logging.level"), config.get("logging.format"))
        for problem in config.problems:
            logger.warn(problem)

        events = EventBus(logger, enabled=bool(config.get("events.enabled")),
                          buffer=int(config.get("events.buffer")))
        metrics = Metrics(enabled=bool(config.get("metrics.enabled")),
                          max_series=int(config.get("metrics.max_series")))
        container = Container()
        runtime = cls(config, logger, events, container, target_dir, metrics)

        container.register_instance("config", config)
        container.register_instance("logger", logger)
        container.register_instance("events", events)
        container.register_instance("metrics", metrics)
        # Lazy: opening a store touches the filesystem, and most commands never need one.
        container.register("store", lambda: runtime._build_store())

        if metrics.enabled:
            events.subscribe("*", runtime._count_event)

        if config.get("events.persist"):
            events.subscribe("*", runtime._persist_event)
            # Emitting an event is how something gets audited. A subsystem added
            # later either emits and is recorded, or does not and shows up as an
            # unrecorded subject in `coresentinel audit coverage`.
            from coresentinel_core.audit import subjects
            subjects.install(runtime)

        runtime.bootstrap_ms = (time.perf_counter() - started) * 1000
        # Phase 2 asserted a 50 ms bootstrap budget in a test. Recording it here
        # means the number is also observable in the field, not only in CI.
        from coresentinel_core.observability import metrics as metering
        metrics.observe(metering.COMMAND, "bootstrap", runtime.bootstrap_ms,
                        kind=metering.TIMER, unit="ms")
        return runtime

    def _build_store(self):
        from coresentinel_core.storage import open_store
        return open_store(self.config, self.target_dir)

    def _count_event(self, event):
        # Subscribed like the audit sink, for the same reason: a subsystem that
        # emits is a subsystem that is measured, and one that does not shows up
        # as never-observed in `metrics coverage` rather than as a zero.
        from coresentinel_core.observability import metrics as metering
        self.metrics.count(metering.SERVICE, f"event.{event.name}")

    def _persist_event(self, event):
        # Persistence must never be the reason an operation fails, so a storage
        # problem degrades to a warning rather than propagating to the emitter.
        from coresentinel_core.observability import metrics as metering
        try:
            with self.metrics.time(metering.STORAGE, "append.events"):
                self.store.events.append(event.record())
        except Exception as e:
            self.metrics.count(metering.STORAGE, "append.failed")
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
        # Metrics are flushed before the store closes, and a failure to write
        # them is a warning: losing a measurement must not be able to fail the
        # command that produced it.
        if self.metrics is not None and self.metrics.enabled:
            try:
                self.metrics.flush(self.store)
            except Exception as e:
                self.logger.warn("metrics not persisted", error=str(e))

        for failure in self.container.shutdown():
            self.logger.warn("service did not close cleanly", **failure)
