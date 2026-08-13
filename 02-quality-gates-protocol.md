# 🛡️ Quality Gates Pipeline Protocol

> **Enforced Quality Gate Pipeline with Explicit Failure Rationale & State Handlers**  
> Every phase transition in CoreSentinel is gated by explicit Quality Gates evaluated with status states: `PASS`, `FAIL`, `BLOCKED`, or `WAIVED`.

---

## 🗺️ Quality Gate Pipeline Flowchart

```text
  Requirement ─► Plan ─► Architecture ─► Security ─► Implementation
                                                          │
  Deployment ◄─ Documentation ◄─ Verification ◄─ Review ◄─┘ Test
```

Ten stages. The original eight keep their names and their order; `Requirement` was added
at the front and `Documentation` before `Deployment` — the two things most often missing at
the end of a change are a statement of what it was for and a record of what it did.

---

## 🏷️ Reason Codes

Every gate result carries a machine-readable `code` beside its prose, so a CI job branches on
**why** a gate failed without parsing a sentence:

```bash
coresentinel gate run --json | jq '.codes'
```

| Code | Meaning |
| :--- | :--- |
| `NO_AUTOMATED_CHECK` | The gate has no mechanically checkable property |
| `NO_TEST_RUNNER` | No test runner is installed or configured here |
| `TESTS_FAILED` | The suite ran and reported failures |
| `SCANNER_CLEAN` / `SCANNER_VIOLATIONS` | The security scanner's verdict |
| `REVIEW_CLEAN` / `REVIEW_BLOCKING` | The static review's verdict |
| `EVIDENCE_SUFFICIENT` / `EVIDENCE_BELOW_THRESHOLD` / `EVIDENCE_INSUFFICIENT` | The evidence suite's verdict |
| `REQUIREMENT_STATED` / `REQUIREMENT_MISSING` | Whether the change has a stated purpose |
| `DOCS_UPDATED` / `DOCS_STALE` / `NO_DOCUMENTATION` | Whether documentation kept pace |
| `NO_REPOSITORY` / `NO_CHANGES` | There was nothing to gate |
| `UPSTREAM_FAILED` | An earlier gate failed |

`NO_TEST_RUNNER` and `TESTS_FAILED` are different facts, and only one of them is a problem
with the change.

---

## 🚦 Gate Status States

| Gate Status | Description & Action Protocol |
| :--- | :--- |
| **`PASS`** | A check ran and the property holds. Its command, exit code and basis are recorded. Proceed to next gate. |
| **`FAIL`** | A check ran and the property is violated. **Blocks every gate after it** until remediated. |
| **`UNKNOWN`** | No automated check exists for this gate, or none could run on this machine. Does **not** block — but is **not a pass**. Clear it with an explicit waiver. |
| **`BLOCKED`** | An earlier gate failed; this one was never evaluated. |
| **`WAIVED`** | Manually waived by user/lead. The rationale is mandatory and recorded in the ledger. |
| **`PENDING`** | Not yet evaluated. The state of every gate in a fresh pipeline. |

---

## ❓ Why `UNKNOWN` exists

Four gates — `Plan`, `Architecture`, `Implementation` and `Deployment` — used to return
`PASS` unconditionally, and `Implementation` ran `git status` and discarded the result. A
fresh pipeline reported **8/8 PASS** against a repository nobody had checked.

Three of them have no mechanically checkable property at all. Reporting a design review as
passed because no code asked a question about it was the single largest source of false
confidence in the pipeline.

`UNKNOWN` is the honest state for those gates. To clear one, a human takes responsibility:

```bash
coresentinel gate waive --gate Architecture --reason "Design reviewed with Fakrul 2026-08-13"
```

A waiver without a rationale is rejected — the pipeline records who accepted the risk and why.

---

## ⚡ CLI Commands

```bash
# Evaluate & run all Quality Gates sequentially
coresentinel gate run
coresentinel gate run --json

# View current Quality Gates Pipeline status
coresentinel gate status
coresentinel gate status --json | jq '.counts'

# Manually waive a specific gate with mandatory justification
coresentinel gate waive --gate Security --reason "Approved temporary exception for sandbox"

# Reset Quality Gates pipeline for a new feature cycle — every gate returns to PENDING
coresentinel gate reset
```

`gate run` exits `1` when any gate is `FAIL` or `BLOCKED`, and `0` otherwise. An `UNKNOWN`
gate does not fail the pipeline; it is reported so the gap is visible rather than hidden
behind a green result.
