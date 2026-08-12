# Test Pattern Library
> Proven test automation solutions, indexed by problem. Pull from here before re-inventing.

Companion to the main [Pattern Library](<CORESENTINEL_PATH>/11-pattern-library.md). That one holds
application patterns; this one holds test patterns.

Each entry should include:
- **Framework**: What it applies to
- **Problem**: What you were solving
- **Solution**: The approach
- **Gotchas**: What bit you
- **First used in**: Which project

---

## Structure & Setup

### Page Object / Screen Object
<!-- Add your page object conventions -->
<!-- Suggested: one class per page, returns page objects on navigation,
     exposes intent (loginAs) not mechanics (typeUsername, clickSubmit) -->

### Fixtures & Hooks
<!-- Add your setup/teardown patterns -->

### Auth Reuse
<!-- Logging in through the UI for every test is the most common cause of a slow suite.
     Log in once, save the session state, reuse it. Add your project's approach here. -->

---

## Selectors

<!-- Add your selector conventions -->
<!-- Suggested priority order:
     1. Role + accessible name  (also proves accessibility)
     2. Dedicated test id       (data-testid / data-cy)
     3. Stable text
     4. CSS — last resort
     Never: generated class names, nth-child chains, absolute XPath -->

---

## Waiting

<!-- Add your waiting patterns -->
<!-- Rule: wait on the condition, never on the clock. See 28-flaky-protocol.md -->

---

## API & Contract Testing

<!-- Add your API test patterns -->
<!-- Suggested: assert status AND schema — a 200 with the wrong shape is still a bug -->

---

## Mobile

<!-- Add your mobile patterns -->

---

## Performance

<!-- Add your load/performance patterns -->
<!-- Suggested: thresholds define pass/fail, not eyeballing a graph -->

---

## CI Pipeline

<!-- Add your pipeline patterns: parallelisation, sharding, artefacts, reporting -->

---

## Framework Gotchas

Starter notes. Correct and extend these from your own experience — an entry you fixed
yourself is worth more than any of the below.

### Playwright
- Use web-first assertions (`expect(locator).toBeVisible()`) — they auto-retry until timeout
- Prefer `getByRole` and `getByTestId` over CSS or XPath
- Auto-waiting is built in; adding `waitForTimeout` usually means you are hiding a race
- `storageState` reuses a logged-in session instead of logging in per test
- Enable traces on first retry — the trace viewer usually shows the cause immediately
- Runs parallel by default: any shared fixture is a flake waiting to happen

### Cypress
- `.should()` retries; `.then()` does not. Assertions belong in `.should()`
- Never `cy.wait(3000)`. Use `cy.intercept()` and wait on the alias
- Avoid conditional testing (`if` on DOM state) — the DOM may not have settled yet
- State clears between tests but not always between files; do not rely on it
- `data-cy` attributes are the documented convention

### Selenium
- Explicit waits (`WebDriverWait` + expected conditions). Never `Thread.sleep`
- Do not mix implicit and explicit waits — the combination produces unpredictable timeouts
- `StaleElementReferenceException` means the DOM re-rendered: re-find, do not retry blindly
- Page Object Model is close to mandatory at any real size
- Pin driver and browser versions; a browser auto-update breaks suites overnight

### Appium
- Prefer accessibility IDs — they are the most stable locator across platforms
- Real devices and emulators genuinely differ; treat them as separate environments
- Longer waits are legitimately needed here; that is not the same as a fixed sleep
- Reset app state between tests, or leftover state leaks across the suite

### API (Postman / REST clients / code)
- Assert status *and* body schema
- Do not chain tests through shared environment variables — it creates order dependence
- Keep contract tests separate from workflow tests; they fail for different reasons
- Version your collections in git, not in the cloud workspace only

### Load (k6 / JMeter / Gatling)
- Thresholds define pass/fail. A run without thresholds is a demo, not a test
- Include ramp-up and warm-up; cold-start numbers are not your real numbers
- Never run load against production without written sign-off and a stop plan
- Report percentiles (p95, p99), not averages — averages hide the pain

---

## How to Add a Pattern

After finishing a suite or fixing a nasty flake, ask:
1. Would I use this approach on the next project?
2. Did I discover a gotcha that would cost someone else a day?
3. Is there a snippet that solved something genuinely tricky?

If yes to any, add it here.

```markdown
### [Pattern Name]
- **Framework**: [e.g. Playwright + TypeScript]
- **Problem**: [what you were solving]
- **Solution**: [approach or snippet]
- **Gotchas**: [what to watch for]
- **First used in**: [project]
```
