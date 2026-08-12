# Test Review Protocol
> Run this on test code before saying done. The base review protocol covers app code — this one covers tests.

---

## 1. Does It Actually Test Something

- [ ] I can name the bug this test catches, in one sentence
- [ ] I have seen this test fail (broke the code deliberately, watched it go red)
- [ ] It asserts an outcome, not that a function was merely called
- [ ] It is not duplicating coverage that already exists at a lower layer
- [ ] It would still be valid after a refactor that keeps behaviour identical

## 2. Assertions

- [ ] Every test has at least one meaningful assertion
- [ ] Assertions are specific — `toBe(5)`, not `toBeTruthy()` on a number
- [ ] No assertion on the entire response body when only one field matters
- [ ] Error cases assert the *message or code*, not just that something threw
- [ ] No commented-out or `skip`-ped assertions left behind

## 3. Waiting

- [ ] No fixed `sleep` / `waitForTimeout` / `Thread.sleep` anywhere
- [ ] Waits are on conditions — element state, network response, data present
- [ ] No global timeout raised to make a specific test pass
- [ ] Retry-capable assertions used where the framework offers them

## 4. Selectors (UI)

- [ ] Uses stable identifiers — test IDs, roles, accessible names
- [ ] No selectors depending on generated classes or deep CSS/XPath chains
- [ ] No selectors depending on text that changes with locale or content
- [ ] Selectors live in one place (page object / fixture), not scattered

## 5. Independence

- [ ] Passes alone
- [ ] Passes in the full suite
- [ ] Passes in a different order
- [ ] Passes when run twice in a row
- [ ] Passes in parallel with the rest
- [ ] Does not depend on a previous test having created data

## 6. Test Data

- [ ] Creates the data it needs rather than assuming it exists
- [ ] Uses unique values per run — no hardcoded email that collides in parallel
- [ ] Cleans up what it created, or runs in an isolated transaction/namespace
- [ ] No dependency on the contents of a shared or production-cloned database
- [ ] No real customer data, ever

## 7. Secrets and Environments

- [ ] No credentials, tokens, or keys committed in the test or fixture
- [ ] Reads config from environment, with a documented default for local
- [ ] Does not point at production, and cannot be made to by changing one variable
- [ ] Third-party calls are mocked or stubbed unless the test's purpose is that integration

## 8. Readability

- [ ] The name states behaviour and expected outcome
- [ ] A failure message tells you what broke without opening the file
- [ ] Setup is visible or clearly named, not buried in three layers of helper
- [ ] Follows the structure of neighbouring tests in the same suite

## 9. Cost

- [ ] Runs fast enough for its layer (see [Test Protocol](./25-test-protocol.md))
- [ ] Is at the lowest layer that can prove the behaviour
- [ ] Does not add a new browser launch where an API call would do

## 10. Reporting

- [ ] Failure output is actionable — no bare `expected true to be false`
- [ ] Artefacts on failure where the framework supports them: screenshot, trace, video, logs
- [ ] Any test passing only on retry is reported as a flake, not a pass

---

## Verdict

State one of these plainly. Never round up.

| Verdict | Meaning |
|---|---|
| **Ready** | All boxes above pass |
| **Ready with notes** | Passes, with named follow-ups that do not block |
| **Not ready** | Anything in sections 1, 3, 5 or 7 fails |

Sections 1, 3, 5 and 7 are non-negotiable: a test that proves nothing, sleeps, leaks state,
or leaks a secret does not ship, regardless of deadline.
