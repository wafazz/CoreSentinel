"""
The capture subscriber — the only thing in this package that writes.

Wiring goes through the event bus rather than by calling a recorder from a dozen
places, for the same reason `audit/subjects.py` does it: emitting an event is how
something gets learned from, so a subsystem added later either emits and is
observed, or does not and shows up as a gap rather than as a silent zero.

Three guarantees, in the order they matter:

  1. **A capture failure never fails the operation it observed.** The bus
     already catches handler exceptions; this catches them again. Two layers,
     because the day the bus contract changes is not the day a gate run should
     start failing on a learning write.
  2. **No credential is stored.** Every payload goes through
     `security/redaction.py` on the way in. There is no path to the repository
     that skips it — `records.build` deliberately does not write.
  3. **The log stays bounded.** `retention.enforce` runs after an append and
     costs nothing until the cap is actually exceeded.

Capture is a listener. It draws no lessons and proposes no rules; it records
what happened and stops. What any of it *means* is `learning/`'s problem, and
what any of it *changes* is a human's.
"""

from coresentinel_core.experience import records, retention
from coresentinel_core.security import redaction

# The stack a project runs on does not change inside one process, and capture
# runs on every event. Resolving it once per directory is the difference between
# a listener and a tax on every gate run.
_CONTEXT_CACHE = {}

MAX_CONTEXT_TERMS = 6


def reset_context_cache():
    """Tests bind and rebind directories; no test may inherit another's answer."""
    _CONTEXT_CACHE.clear()


def context_key(target_dir="."):
    """A stable fingerprint of the stack a lesson was learned on.

    `None` when discovery evidenced nothing — and `None` means global, which is
    the honest answer for a lesson we cannot place. Guessing a context is worse
    than admitting to none, because a wrongly-scoped lesson is retrieved where it
    does not apply.
    """
    key = str(target_dir or ".")
    if key in _CONTEXT_CACHE:
        return _CONTEXT_CACHE[key]

    resolved = None
    try:
        from coresentinel_core.project.discovery import stack, infrastructure

        # Declared runtimes, frameworks and datastores — and deliberately not
        # `detect_languages`, which is the one detector that walks the tree.
        # A stack a manifest states is also better evidence than one inferred
        # from counting source files, so the cheap answer is the better one.
        findings = (stack.detect_runtime_versions(key)
                    + stack.detect_frameworks(key)
                    + infrastructure.detect_databases(key))

        terms = []
        for item in findings:
            cleaned = "".join(c for c in str(item.get("value", "")).lower()
                              if c.isalnum() or c == ".")
            if cleaned and cleaned not in terms:
                terms.append(cleaned)
        if terms:
            resolved = ".".join(sorted(terms)[:MAX_CONTEXT_TERMS])
    except Exception:
        # Detection is best-effort. A project we cannot read still produces
        # experiences; they are simply global rather than scoped.
        resolved = None

    _CONTEXT_CACHE[key] = resolved
    return resolved


def store_experience(store, event_name, payload, target_dir=".", occurred_at=None):
    """Build, redact and append one experience. Returns it, or None if not captured.

    Public so a caller with an outcome that never became an event can record it
    directly — a user correction, for instance, which no subsystem emits.
    """
    record = records.build(event_name, payload, context_key=context_key(target_dir),
                           occurred_at=occurred_at)
    if record is None:
        return None

    # Redaction covers the whole record, not just the evidence: a gate reason or
    # a task objective can carry a credential as easily as a payload field can.
    safe = redaction.redact(record)
    stored = store.repository(retention.COLLECTION).append(safe)
    return stored


def install(runtime, maximum=None):
    """Subscribe capture to this runtime's bus. Returns the handler.

    Returned so a caller can unsubscribe it — the tests do, and a long-lived
    server eventually will.
    """
    cap = int(maximum if maximum is not None
              else (runtime.config.get("learning.max_experiences") or retention.DEFAULT_MAX))

    def sink(event):
        if not records.is_captured(event.name):
            return
        try:
            store_experience(runtime.store, event.name, event.payload,
                             runtime.target_dir, event.occurred_at)
            retention.enforce(runtime.store, cap)
        except Exception as e:
            # Loud, but never fatal. A missing experience costs a lesson; a
            # failed gate run because a learning write threw costs the work.
            runtime.logger.warn("experience not captured",
                                event=event.name, error=str(e))

    runtime.events.subscribe("*", sink)
    return sink
