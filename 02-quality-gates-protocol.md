# 🛡️ Quality Gates Pipeline Protocol

> **Enforced Quality Gate Pipeline with Explicit Failure Rationale & State Handlers**  
> Every phase transition in CoreSentinel is gated by explicit Quality Gates evaluated with status states: `PASS`, `FAIL`, `BLOCKED`, or `WAIVED`.

---

## 🗺️ Quality Gate Pipeline Flowchart

```
  ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────────┐
  │ 1. PLAN  │ ──► │ 2. ARCH      │ ──► │ 3. SECURITY  │ ──► │ 4. IMPL        │
  └──────────┘     └──────────────┘     └──────────────┘     └────────────────┘
                                                                      │
  ┌──────────┐     ┌──────────────┐     ┌──────────────┐              │
  │ 8. DEPLOY│ ◄── │ 7. VERIFY    │ ◄── │ 6. REVIEW    │ ◄── │ 5. TEST        │
  └──────────┘     └──────────────┘     └──────────────┘     └────────────────┘
```

---

## 🚦 Gate Status States

| Gate Status | Description & Action Protocol |
| :--- | :--- |
| **`PASS`** | Gate check satisfied with empirical logs & zero violations. Proceed to next gate. |
| **`FAIL`** | Violations detected with explicit rationale. Upstream work blocked until remediated. |
| **`BLOCKED`** | Downstream gate waiting for an upstream gate failure to be resolved. |
| **`WAIVED`** | Manually waived by user/lead with mandatory justification reason recorded in ledger. |

---

## ⚡ CLI Commands

```bash
# Evaluate & run all Quality Gates sequentially
coresentinel gate run

# View current Quality Gates Pipeline status
coresentinel gate status

# Manually waive a specific gate with mandatory justification
coresentinel gate waive --gate Security --reason "Approved temporary exception for sandbox"

# Reset Quality Gates pipeline for a new feature cycle
coresentinel gate reset
```
