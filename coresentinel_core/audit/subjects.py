"""
The twelve audit subjects, and how an event becomes a record.

v1 audited one of them. The other eleven happened with no trace — a memory fact
could be rewritten, a rule changed, a gate waived, and nothing anywhere said so.

Wiring is done through the Phase 2 event bus rather than by calling the ledger
from a dozen places. That means *emitting an event is how something gets
audited*, so a subsystem cannot be added later and quietly skip the trail: it
either emits and is recorded, or it does not emit and `audit coverage` says the
subject has never been seen.
"""

AGENT_ACTION = "agent_action"
MEMORY_CHANGE = "memory_change"
DECISION = "decision"
RULE_CHANGE = "rule_change"
TASK_EXECUTION = "task_execution"
FILE_CHANGE = "file_change"
COMMAND_EXECUTION = "command_execution"
QUALITY_GATE = "quality_gate"
VERIFICATION = "verification"
INCIDENT = "incident"
DEPLOYMENT = "deployment"
CONFIGURATION = "configuration_change"
OTHER = "other"

SUBJECTS = [AGENT_ACTION, MEMORY_CHANGE, DECISION, RULE_CHANGE, TASK_EXECUTION,
            FILE_CHANGE, COMMAND_EXECUTION, QUALITY_GATE, VERIFICATION,
            INCIDENT, DEPLOYMENT, CONFIGURATION]

# Event name -> the subject it is recorded under. An event with no mapping is
# still recorded, under OTHER, because dropping it would be the silent gap this
# whole module exists to close.
EVENT_SUBJECTS = {
    "AgentStarted": AGENT_ACTION,
    "AgentCompleted": AGENT_ACTION,
    "TaskStarted": TASK_EXECUTION,
    "TaskCompleted": TASK_EXECUTION,
    "MemoryCreated": MEMORY_CHANGE,
    "MemoryUpdated": MEMORY_CHANGE,
    "DecisionCreated": DECISION,
    "DecisionChanged": DECISION,
    "RuleProposed": RULE_CHANGE,
    "PatternDetected": RULE_CHANGE,
    "QualityGatePassed": QUALITY_GATE,
    "QualityGateFailed": QUALITY_GATE,
    "VerificationStarted": VERIFICATION,
    "VerificationCompleted": VERIFICATION,
    "IncidentCreated": INCIDENT,
    "DeploymentCompleted": DEPLOYMENT,
    "ConfigurationChanged": CONFIGURATION,
    "ProjectInitialized": CONFIGURATION,
}


def subject_for(event_name):
    return EVENT_SUBJECTS.get(event_name, OTHER)


def install(runtime):
    """Subscribe the ledger to every event on this runtime's bus.

    Returns the handler so a caller can unsubscribe it — the tests do, and a
    long-lived process eventually will.
    """
    from coresentinel_core.audit import ledger

    def sink(event):
        payload = dict(event.payload or {})
        actor = payload.pop("agent", None) or payload.pop("actor", None) or "coresentinel"
        result = payload.pop("status", None) or payload.pop("result", None)
        try:
            ledger.append(runtime.store, subject_for(event.name), actor,
                          event.name, result, payload)
        except Exception as e:
            # An audit failure must not fail the operation being audited; it
            # must, however, be loud. A silent gap in the trail is the thing
            # this module exists to prevent.
            runtime.logger.error("audit record not written",
                                 event=event.name, error=str(e))

    runtime.events.subscribe("*", sink)
    return sink
