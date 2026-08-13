"""
Internal event bus.

Nothing in v1 could observe anything else. Recording an audit entry, updating
memory and evaluating a gate were three unrelated code paths, which is why the
audit trail covers one of the twelve subjects it claims to.

An event is a fact that something happened. Handlers are observers: a handler
that raises is logged and skipped, never allowed to fail the operation that
emitted the event. Governance must not break because a listener did.
"""

from datetime import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

PROJECT_INITIALIZED = "ProjectInitialized"
MEMORY_CREATED = "MemoryCreated"
MEMORY_UPDATED = "MemoryUpdated"
DECISION_CREATED = "DecisionCreated"
DECISION_CHANGED = "DecisionChanged"
AGENT_STARTED = "AgentStarted"
AGENT_COMPLETED = "AgentCompleted"
TASK_STARTED = "TaskStarted"
TASK_COMPLETED = "TaskCompleted"
VERIFICATION_STARTED = "VerificationStarted"
VERIFICATION_COMPLETED = "VerificationCompleted"
QUALITY_GATE_PASSED = "QualityGatePassed"
QUALITY_GATE_FAILED = "QualityGateFailed"
INCIDENT_CREATED = "IncidentCreated"
PATTERN_DETECTED = "PatternDetected"
RULE_PROPOSED = "RuleProposed"
DEPLOYMENT_COMPLETED = "DeploymentCompleted"
CONFIGURATION_CHANGED = "ConfigurationChanged"

KNOWN_EVENTS = [
    PROJECT_INITIALIZED, MEMORY_CREATED, MEMORY_UPDATED,
    DECISION_CREATED, DECISION_CHANGED,
    AGENT_STARTED, AGENT_COMPLETED, TASK_STARTED, TASK_COMPLETED,
    VERIFICATION_STARTED, VERIFICATION_COMPLETED,
    QUALITY_GATE_PASSED, QUALITY_GATE_FAILED,
    INCIDENT_CREATED, PATTERN_DETECTED, RULE_PROPOSED,
    DEPLOYMENT_COMPLETED, CONFIGURATION_CHANGED,
]

WILDCARD = "*"


class Event:
    def __init__(self, name, payload=None, occurred_at=None):
        self.name = name
        self.payload = payload or {}
        self.occurred_at = occurred_at or datetime.now().strftime(TIMESTAMP_FORMAT)

    def record(self):
        return {"event": self.name, "occurred_at": self.occurred_at, "payload": self.payload}

    def __repr__(self):
        return f"Event({self.name})"


class EventBus:
    def __init__(self, logger=None, enabled=True):
        self._handlers = {}
        self._logger = logger
        self.enabled = enabled
        self.emitted = []

    def subscribe(self, name, handler):
        """Subscribe to one event name, or to WILDCARD for all of them."""
        self._handlers.setdefault(name, []).append(handler)
        return handler

    def unsubscribe(self, name, handler):
        listeners = self._handlers.get(name, [])
        if handler in listeners:
            listeners.remove(handler)

    def subscribers(self, name):
        return list(self._handlers.get(name, [])) + list(self._handlers.get(WILDCARD, []))

    def emit(self, name, payload=None):
        """Publish an event. Returns it, whether or not anything was listening."""
        event = Event(name, payload)
        if not self.enabled:
            return event

        self.emitted.append(event)

        for handler in self.subscribers(name):
            try:
                handler(event)
            except Exception as e:
                # An observer must never be able to fail the operation it observed.
                if self._logger:
                    self._logger.warn("event handler failed",
                                      event=name, handler=getattr(handler, "__name__", repr(handler)),
                                      error=str(e))
        return event

    def drain(self):
        collected, self.emitted = self.emitted, []
        return collected
