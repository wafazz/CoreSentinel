# Test Protocol
> "A test earns its place by the bug it would catch."

Strategy and authoring standards for automated tests.

---

## Rule #1: Justify the Test

Before writing, answer in one sentence: **what bug does this catch?**

If the answer is "it covers the function" but no realistic bug would make it fail, do not
write it. Coverage percentage is a diagnostic, never a target.

---

## What to Automate

| Automate | Leave manual |
|---|---|
| Runs every release (regression) | Runs once, ever |
| Deterministic pass/fail | "Does this look right?" |
| Business-critical paths (login, checkout, payment) | Cosmetic polish |
| A bug that escaped to production | Exploratory testing |
| Tedious and error-prone by hand (data permutations) | One-off data migration check |
| Stable requirements | Feature still changing daily |

**Automate on the third occurrence.** First time: do it manually. Second: note it. Third:
automate. Automating a moving feature too early costs more in maintenance than it saves.

---

## The Shape of the Suite

| Layer | Share | Speed | Use for |
|---|---|---|---|
| **Unit** | most | milliseconds | Logic, calculations, edge cases, error branches |
| **Integration / API** | many | seconds | Contracts, database, service boundaries, auth rules |
| **E2E / UI** | few | minutes | Critical user journeys only |

Push each test as far down as it will go. If a rule can be proven at the API layer, do not
prove it by driving a browser. E2E is the most expensive and most fragile layer — spend it on
journeys that lose money when broken.

---

## Naming

A test name states the behaviour and the expected outcome, so a failure is readable without
opening the file.

```
Bad:   testLogin, test_1, it("works")
Good:  login fails with a clear message when the password is wrong
Good:  checkout rejects an expired discount code
```

Pattern: `[subject] [expected behaviour] [when condition]`.

---

## Structure

**Arrange → Act → Assert.** One reason to fail per test.

- Set up only what this test needs
- Perform a single action
- Assert the outcome, not the implementation detail
- Clean up what you created

Multiple assertions are fine when they describe one behaviour. Multiple *actions* usually
means it should be several tests.

---

## Independence

Every test must pass when run:
- alone
- in the full suite
- in a different order
- in parallel with others
- twice in a row

If any of these breaks it, the test is not independent. Fix the test, not the runner config.
See [Flaky Protocol](./28-flaky-protocol.md).

---

## Speed Budget

| Layer | Target |
|---|---|
| Unit suite | under 1 minute |
| Integration suite | under 5 minutes |
| E2E critical path | under 10 minutes |

A suite nobody waits for is a suite nobody runs. When the budget is blown, the answer is
usually to move tests down a layer, not to add machines.

---

## When to Delete a Test

Delete without guilt when a test:
- Covers a feature that no longer exists
- Has been quarantined past its expiry with no owner
- Duplicates coverage that already exists lower down
- Asserts implementation detail that changes on every refactor
- Has never failed for a real bug and realistically never will

Deleting a worthless test is a net gain. Suite trust is the asset being protected.

---

## Covering a Production Bug

Every escaped bug gets a test **before** the fix:

1. Write the test that reproduces it — watch it fail
2. Fix the code — watch it pass
3. Record the root cause as an anti-pattern in
   [Self-Evolution](<CORESENTINEL_PATH>/55-self-evolution.md)

This is the highest-value test you will ever write, because it is proven to catch a bug that
really happened.
