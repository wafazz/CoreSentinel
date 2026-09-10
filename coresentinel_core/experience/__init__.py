"""
The experience layer — the input stage the learning loop never had.

`learning/observer.py` draws lessons from three sources, and its own docstring
names the ceiling: they are "all of them things somebody already wrote down".
Somebody files the incident, records the failure, captures the pattern; then
somebody runs `evolve observe`. The mill had no hopper.

This package is the hopper. It listens to the event bus, turns outcome events
into experiences, and stops there. An experience is an observation, not a
lesson — `learning/` decides what any of it means, and a human decides what any
of it changes.

Three rules hold the whole package together:

  * **Never fail the operation being observed.** Capture is a listener. The bus
    already guarantees this (`runtime/events.py`), and nothing here may rely on
    that guarantee alone.
  * **Never store a credential.** Every payload passes through
    `security/redaction.py` before it reaches a repository.
  * **Never grow without bound.** A signature makes recurrence a count, and
    retention folds and caps. A learning system that accumulates forever becomes
    the context bloat CoreSentinel exists to remove.
"""

from coresentinel_core.experience import records, retention, capture, analysis

__all__ = ["records", "retention", "capture", "analysis"]
