# Flaky Protocol
> "A retry does not fix a race. It hides one."

Activates the moment a test passes and fails without the code changing.

---

## Rule #1: Never Retry to Green

Adding `retries` to make a red suite green is the single most damaging thing you can do to a
test suite. It converts a real signal into noise, and the suite slowly becomes advisory.

Retries are legitimate in exactly one place: **as a diagnostic**, to detect and report flakes
in CI. A test that passes only on retry is reported as a **failure**, never as a pass.

---

## Rule #2: Quarantine Fast, Fix or Delete

A flaky test in the main suite trains the team to ignore red. Within one working day:

1. **Quarantine** it — move it out of the blocking suite
2. **Assign an owner** — a name, not "the team"
3. **Set an expiry** — 2 weeks is a good default
4. **Log it** using the template below

At expiry: fixed, or deleted. No third option. An unowned quarantined test is just a deleted
test that still costs CI minutes.

---

## Step 1: Confirm It Is Actually Flaky

Run it 10 times in a row on the same commit.

| Result | Meaning |
|---|---|
| 10/10 pass | Not flaky here — the difference is the environment. Investigate CI vs local |
| Fails sometimes | Genuine flake. Continue to Step 2 |
| 0/10 pass | Not flaky, just broken. Use the [Debug Protocol](<CORESENTINEL_PATH>/60-debug-protocol.md) |

Also run it **alone** and then **inside the full suite**. Different results means a state or
ordering problem, not a timing one.

---

## Step 2: Classify the Cause

| Cause | Telltale sign | Fix |
|---|---|---|
| **Timing / race** | Fails on slow CI, passes locally | Wait on the condition, never on the clock |
| **Test order** | Passes alone, fails in suite | Remove shared state between tests |
| **Shared data** | Fails only in parallel | Give each test its own data, unique per run |
| **Leftover state** | Fails on second run | Clean up in teardown, or reset before each test |
| **Animation / transition** | Element found but click misses | Wait for the element to be stable, not just present |
| **Network** | Random timeouts | Mock or stub third parties; never hit live services |
| **Time and locale** | Fails overnight, or at month end | Freeze the clock; never assert on `now()` |
| **Auto-generated IDs** | Selector breaks each build | Use stable test IDs, not generated classes |
| **Resource contention** | Fails when CI is busy | Raise the timeout only after ruling out everything above |

---

## Step 3: Fix the Root Cause

The correct fix almost always replaces *waiting for time* with *waiting for a condition*:

```
Bad:   sleep(3000); click(button)
Good:  waitUntil(button is visible and enabled); click(button)

Bad:   sleep(2000); expect(list).toHaveLength(5)
Good:  waitUntil(list has 5 items)      // assertion retries until timeout

Bad:   raise the global timeout to 60s
Good:  find out what the test is actually waiting on
```

If you genuinely cannot find the condition, say so plainly and quarantine it. Do not paper
over it with a longer timeout and call it fixed.

---

## Step 4: Record It

Every confirmed flake goes into
[Self-Evolution](<CORESENTINEL_PATH>/55-self-evolution.md) as an anti-pattern, so the same race is
never diagnosed twice.

```markdown
### Flake: [test name]
- **Symptom**: [how it failed, how often]
- **Confirmed**: [x/10 runs failed]
- **Cause**: [timing / order / shared data / state / network / time / selector]
- **Root cause**: [what was actually racing or leaking]
- **Fix**: [the condition now waited on, or the state now isolated]
- **Quarantined**: [yes/no] · **Owner**: [name] · **Expiry**: [YYYY-MM-DD]
- **Prevention**: [the rule that stops this class of flake recurring]
```

---

## Health Signals

Watch these; they say more than pass rate:

| Signal | Healthy | Investigate |
|---|---|---|
| Flake rate | under 1% of runs | above 5% — trust is already gone |
| Quarantined tests | a handful, all owned | growing, or unowned |
| Time in quarantine | under 2 weeks | over a month — delete them |
| Suite runtime | stable | creeping up each sprint |

**The real measure:** when the suite goes red, does the team investigate, or re-run it? If
they re-run, the suite has stopped being a test and become a formality.
