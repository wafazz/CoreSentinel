# 🧪 CoreSentinel Self-Test & CI Protocol

> **CoreSentinel does not only verify the projects it governs — it verifies itself.**
> A governance system that is not itself tested is an unverified claim.

---

## 🗂️ Suite Layout

```text
tests/
├── conftest.py        Shared fixtures & isolation guarantees
├── memory/            Layered memory, confidence classification, ADR ledger
├── governance/        Quality gates, self-evolution pipeline, protocol integrity
├── verification/      Evidence suite, health scoring, static review engine
├── security/          Secret & anti-pattern scanner, rule database integrity
├── agents/            17-specialist contract registry & authority boundaries
├── recovery/          Corrupt, missing and BOM-encoded state handling
├── telemetry/         Session log parsing, token accounting, aggregation
└── integration/       End-to-end CLI behaviour in a sandboxed Core
```

Run the suite:

```bash
pip install -r requirements-dev.txt
python -m pytest              # everything
python -m pytest tests/security -q
python -m pytest tests/integration -q
```

---

## 🔒 Isolation Rules (enforced in `conftest.py`)

A test suite for a memory system must never write to that memory system.

1. **No test touches the real `memory/` directory.** Unit tests monkeypatch the engine's `MEMORY_DIR` and layer paths onto `tmp_path`.
2. **No test writes to the user's home directory** or to any host config path (`~/.claude/`, `~/.cursor/`, …).
3. **Mutating tests run against a sandbox** — the `sandbox` fixture copies the Core into `tmp_path`, so `init`, `sync` and ledger writes land in a throwaway tree.
4. **Diff-driven engines get a real git repository** from the `git_repo` fixture, never the CoreSentinel repo itself.

> This is not hypothetical hygiene: an early manual test of `coresentinel init` seeded three scratch-project facts into the real `memory/project.json`.
> The fixtures exist so that cannot happen again.

---

## 🎯 What Each Package Guarantees

| Package | Representative guarantees |
| :--- | :--- |
| **memory** | Confidence boundaries are exact (`0.90` Known, `0.8999` not); re-initializing never erases facts; the ADR ledger issues sequential ids |
| **governance** | Security gates precede Implementation; a waived gate never reports as PASS; a new evolution proposal is never auto-approved; every index link resolves |
| **verification** | Only *added* lines are reviewed; `--strict` promotes missing tests to blocking; health dimensions stay in range and average correctly |
| **security** | Real credential formats are caught and safe patterns are not; every anti-pattern rule is complete; Verification-category rules are `STRICT_BLOCK` |
| **agents** | All 17 contracts declare inputs, outputs, authority and a verification gate; read-only agents declare a read-only constraint |
| **recovery** | Corrupt JSON fails loudly with the layer named; missing assets suggest a remedy; BOM-encoded files parse; unmanaged host files are never overwritten |
| **telemetry** | The shallowest usage block wins (no double counting); malformed log lines are skipped, not fatal; repeat edits count once |
| **integration** | Every command answers `--help`; unknown commands exit 1 with a suggestion; every `--json` contract parses and carries no BOM; read-only commands do not mutate the ledger |

---

## 🔁 CI Pipeline

```text
Pull Request
     ↓
CoreSentinel Tests      unit suite across 6 packages
     ↓
Security                scanner suite + validator + PR diff review
     ↓
Lint                    byte-compile, ruff (E9/F63/F7/F82), JSON registry validation
     ↓
Integration             integration suite + CLI smoke + JSON contracts + verify
     ↓
Compatibility           3 operating systems × 3 Python versions
     ↓
PASS / FAIL
```

Defined in [`.github/workflows/coresentinel-ci.yml`](./.github/workflows/coresentinel-ci.yml). Each stage `needs` the previous one, so a security failure never reaches Integration. The final `gate` job runs with `if: always()` and fails unless **every** upstream stage succeeded — make it the required status check on `main`.

**Compatibility matrix:** `ubuntu-latest`, `windows-latest`, `macos-latest` × Python `3.9`, `3.11`, `3.13`. CoreSentinel's floor is Python 3.9; every engine and test file is verified to parse under the 3.9 grammar.

---

## ➕ Adding Tests

1. Put the test in the package that matches the **subsystem**, not the file it happens to touch.
2. Use the fixtures — never construct paths into the real `memory/` directory.
3. Assert on behaviour that would harm a user if it broke, not on incidental formatting.
4. A test that documents a fixed bug should say so in its name or docstring, so the regression is legible.

> Every bug this suite has caught is listed in the commit that introduced the fix.
> When a test fails, first ask whether the test or the engine is wrong — both have been guilty.
