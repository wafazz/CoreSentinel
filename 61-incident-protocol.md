# Incident Protocol (`Iris incident`)

## Trigger
Activate when an unexpected production failure, security breach, data corruption, or severe performance degradation occurs. Command: `Iris incident`.

## Phase 1: Containment & Triage (0-15 Minutes)
1. **Identify Blast Radius**: Determine affected tenants, users, channels, or modules.
2. **Isolate Service**: Disable broken endpoint, webhook, or feature flag if actively causing data loss or high log noise.
3. **Preserve Evidence**: Save error logs, database state snapshots, or failing HTTP payloads before restarting services.

## Phase 2: Diagnosis & Isolation
1. **Log Extraction**: Read un-truncated stack traces and database error logs strictly before touching code.
2. **Reproduce Locally**: Replicate the exact state using local unit/integration tests or CLI probes (`bin/*-doctor.php`).
3. **Classify Root Cause**:
   - Class A: Application logic bug / unhandled edge case
   - Class B: Third-party API failure / vendor outage (e.g. NICE CXone / provider downtime)
   - Class C: Database deadlock / resource exhaustion / lock contention
   - Class D: Configuration or environment drift

## Phase 3: Hotfix & Verification
1. **Minimal Safe Fix**: Apply the smallest possible fix that resolves the issue without introducing architectural drift.
2. **Regression Check**: Run the test suite (`vendor/bin/phpunit` or custom test bootstrap).
3. **Verification**: Execute empirical runtime probe to verify the issue is completely eliminated.

## Recording an Incident

The four phases below have been documented since v1. Nothing recorded their output, so
Phase 4 — the one that turns a bad afternoon into a rule nobody has to relearn — had nowhere
to write.

```bash
coresentinel incident create --title "Database connection exhaustion" \
  --problem "The connection pool was exhausted under peak load" \
  --root-cause "An agent introduced an N+1 query in the listing endpoint" \
  --severity High --class "A: application logic" \
  --file src/ProductController.php

coresentinel incident link INC-0001 --decision ADR-042 --pattern PAT-0032
coresentinel incident resolve INC-0001 \
  --resolution "Added eager loading to the listing query" \
  --learning "Flag repeated relationship queries inside a loop during review"
```

An incident holds four things, and the last two are the point:

| Field | Question it answers |
| :--- | :--- |
| `problem` | What was observed |
| `root_cause` | What actually caused it |
| `resolution` | What was done about it |
| `learning` | What should be different next time |

**The fix is what stops it now; the learning is what stops it recurring.** Resolving without
one is allowed and reported — `coresentinel incident list` names every resolved incident that
recorded no learning.

Incidents are scoped like decisions and project memory: an incident belongs to the repository
it happened in. Links to decisions, files, commits, tests and patterns appear in the knowledge
graph, so a query can walk from the incident to the decision that governs the code that
caused it.

---

## Phase 4: RCA & Prevention (Post-Mortem)
1. **Root Cause Analysis**: Document exact timeline, triggering condition, root cause, and resolution.
2. **Self-Evolution Feed**:
   - If a new mistake or anti-pattern occurred, update `55-self-evolution.md` anti-patterns section.
   - If a new debugging technique proved effective, save to `11-pattern-library.md`.
3. **Update Memory**: Update project profile log and `session-memory.md`.
