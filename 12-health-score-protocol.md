# 🛡️ CoreSentinel Health Score & Reliability Protocol

> **Quantified 7-Dimension Health Score & System Status Rating**  
> Evaluates project quality across Architecture, Security, Testing, Code Quality, Documentation, Reliability, and Dependencies.

---

## 📐 How a dimension is scored

A dimension is **the fraction of its named signals that are met**. There is no baseline
constant anywhere in the engine.

```text
dimension score = signals met / signals that could be evaluated × 100
overall score   = mean of the dimensions that could be evaluated
```

Every signal declares a **basis**: the command that produced it, or the filesystem
measurement it read. `coresentinel score --explain` prints all of them, so any number here
can be argued with.

> **Why this protocol was rewritten.** Five of the seven dimensions used to open at a
> constant — Architecture 90, Code Quality 96, Documentation 88, Reliability 93,
> Dependencies 97 — adjusted by a file-existence check or two. An empty directory
> containing no code, no git repository and no tests scored **89/100**. A health score that
> a project cannot fail is not a measurement; it is decoration.

---

## 📊 Health Dimensions Matrix

| Dimension | Signals |
| :--- | :--- |
| **Architecture** | README present · architecture documentation present · dependency manifest present · no module exceeds 1000 lines |
| **Security** | `sentinel-validator` scan clean · `.gitignore` present · no environment file committed |
| **Testing** | test suite passes · test files present · test-to-source ratio ≥ 0.2 |
| **Code Quality** | linter reports no violations · no superficial patches in tracked source |
| **Documentation**| README present · README has ≥ 40 lines of substance · LICENSE present · additional documentation present |
| **Reliability** | under version control · ≥ 5 commits of history · CI pipeline configured |
| **Dependencies** | lockfile committed · dependency audit reports no advisories |

---

## ❓ Unevaluable signals and dimensions

A signal that **cannot be evaluated on this machine** — no linter installed, no audit tool
for this stack, not a git repository — is *unavailable*. It is never counted as met.

- A dimension scored on a subset of its signals says so: `100/100 (2 of 3 signals)`.
- A dimension with **no** evaluable signals reports `UNKNOWN` and stays **out of the mean**
  rather than defaulting into it.
- Fewer than **3** evaluable dimensions yields `INDETERMINATE` — there is not enough signal
  to call the project healthy or unhealthy, and saying so is more useful than averaging two
  numbers.

---

## 🚦 System Health Status Ratings

- **`HEALTHY` (Overall Score >= 90/100)**: Production-ready baseline. All quality standards met.
- **`WARNING` (Overall Score 75–89/100)**: Non-blocking issues present. Remediation recommended.
- **`CRITICAL` (Overall Score < 75/100)**: Gate failure. Deployment blocked until remediated.
- **`INDETERMINATE`**: fewer than 3 dimensions could be evaluated. Not a pass and not a
  failure — a statement that this machine could not measure the project.

---

## ⚡ CLI Commands

```bash
# Evaluate & print formatted CoreSentinel Health Scorecard
coresentinel score

# Print the basis for every signal behind every number
coresentinel score --explain

# Alias command
coresentinel health

# Output machine-readable JSON health report for CI/CD pipelines
coresentinel score --json
coresentinel score --json | jq '.unknown_dimensions'
```
