# Test Data & Environment Protocol
> "A test that depends on data it did not create is a test waiting to fail."

---

## The Three Rules

1. **Create what you need.** Never assume a record exists because it existed last week.
2. **Own what you create.** Unique per test, per run — no shared fixtures being mutated.
3. **Clean up after yourself.** Or run somewhere disposable that gets reset wholesale.

---

## Choosing an Approach

| Approach | Use when | Watch out for |
|---|---|---|
| **Factory / builder** | Default choice. Test creates exactly what it needs | Slow if it creates a deep object graph for one field |
| **Fixture file** | Static reference data — country lists, tax tables | Goes stale silently; nobody updates it |
| **Seeded database** | Large read-only datasets, reporting tests | Tests start depending on seed contents; treat seeds as an API |
| **Transaction rollback** | Fast DB-level isolation | Does not work when the code under test commits or uses queues |
| **Fresh namespace / tenant per run** | Parallel and E2E | Costs setup time; needs teardown or expiry |

Prefer factories. They keep the test readable — the data it needs is visible in the test.

---

## Uniqueness in Parallel

Anything unique-constrained must be unique **per run**, not just per test file:

```
Bad:   "test@example.com"                  collides the moment two runs overlap
Good:  "test+{run_id}-{n}@example.com"
Good:  "user-{uuid}@example.test"
```

Use a reserved, non-deliverable domain for email. Never a real one you do not own.

---

## Time

- Freeze or inject the clock; never assert against `now()`
- Test explicitly around boundaries: month end, year end, DST changes, leap day
- Store and compare in UTC; assert display formatting separately
- A test that only fails overnight or at month end is a time-dependency bug, not a flake

## Locale and Currency

- Pin locale in test config; do not inherit the machine's
- Assert on values and codes, not formatted strings, unless formatting is the thing under test
- Currency in minor units (cents) — never floats

---

## Environments

| Environment | Purpose | Rule |
|---|---|---|
| **Local** | Fast feedback while writing | Must work offline; third parties mocked |
| **CI** | Gate on every push | Deterministic, isolated, no shared mutable state |
| **Staging** | Integration and E2E against real services | Sandbox credentials only; data reset on a schedule |
| **Production** | Smoke checks only | Read-only, clearly-labelled synthetic accounts, never destructive |

**Never point an automated suite at production with write access.** If a smoke test must run
there, it reads, or it uses a dedicated synthetic account that cannot touch real records.

Environment config comes from environment variables with a documented local default. Switching
environment must be one variable — and must never be possible by accident.

---

## Secrets

Follow [Security Protocol](<CORESENTINEL_PATH>/40-security-protocol.md). In tests specifically:

- [ ] No credentials in test files, fixtures, config committed to git, or CI logs
- [ ] Test accounts are separate from real accounts and clearly named
- [ ] Sandbox keys for payment and third-party services — never live keys
- [ ] Recorded fixtures (VCR-style cassettes) scrubbed of tokens before commit
- [ ] Screenshots and traces on failure reviewed — they capture whatever was on screen

If a secret does leak into a repo or a CI artefact: rotate it immediately, revoke the old one,
then scrub history. In that order.

---

## Real Customer Data

Never in tests. Not anonymised, not "just this once", not in a staging clone.

Need realistic volume or shape? Generate it. A seeded generator gives you a million rows that
look real, carry no legal risk, and are reproducible from a seed value.
