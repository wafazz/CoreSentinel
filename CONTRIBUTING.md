# Contributing to CoreSentinel

Thank you for your interest in contributing to CoreSentinel! We welcome contributions from both human engineers and AI coding assistants.

---

## 1. The Prime Directive

> **Nothing reports a result it did not measure.**

Every convention in CoreSentinel stems from this principle. CoreSentinel exists to ensure AI agents and engineering workflows are held to verifiable, evidence-backed standards. 

When contributing code or tests:
- Checks must run real commands and record real exit codes, execution durations, and output digests.
- Never hardcode `PASS` or simulate successful results without measurement.
- If a tool is not installed or cannot run, report `UNKNOWN` (and exclude it from aggregates), never `PASS` or `0`.

For a deep architectural walkthrough and step-by-step guides on adding commands, services, migrations, or adapters, read [AGENTS.md](./AGENTS.md).

---

## 2. Development Setup

CoreSentinel requires **Python 3.9+** and has zero mandatory external runtime dependencies for its core CLI.

```bash
# Clone the repository
git clone https://github.com/wafazz/CoreSentinel.git
cd CoreSentinel

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install development & testing dependencies
pip install -r requirements-dev.txt
```

---

## 3. Running Verifications

Before submitting a Pull Request, run the full verification suite locally:

```bash
# 1. Run all unit, integration, and security tests
python -m pytest tests -q

# 2. Run anti-pattern and secret validation
python sentinel-validator.py

# 3. Verify subsystem health
python coresentinel.py doctor

# 4. Review changed lines against main
python coresentinel.py review

# 5. Check performance budgets
python coresentinel.py metrics budgets
```

All checks must pass with exit code `0`.

---

## 4. How to Contribute

### Adding a New AI Host Adapter
1. Add an entry to `adapters.json` specifying the host configuration and rules file path.
2. Implement any necessary adapter logic in `coresentinel_core/agents/adapters/` if custom handling is needed.
3. Add tests in `tests/agents/test_adapters.py` (test against mocks, never external live network calls).

### Modifying Anti-Patterns or Governance Rules
Rules in `anti-patterns.json` and governance protocols are protected by the **Controlled Self-Evolution (CSE)** pipeline:
```bash
# Propose a rule change with real incident evidence
python coresentinel.py evolve propose --target anti-patterns.json --change "..." --evidence "..."

# Review proposal
python coresentinel.py evolve list
```
Rule changes will not be merged without incident evidence and maintainer review.

---

## 5. Submitting a Pull Request

1. **Branch naming**: `feature/<name>`, `fix/<name>`, or `chore/<name>`.
2. **Commit style**: Conventional commits (`feat: ...`, `fix: ...`, `docs: ...`, `test: ...`).
3. **No regressions**: A test may be added to, never weakened. Removing assertions to make a build pass is strictly forbidden.
4. **Fixture hygiene**: If adding simulated credential strings in test fixtures, mark the file with `CORESENTINEL:SCANNER-FIXTURES` in the first 20 lines and assemble values dynamically from runtime parts.

---

## 6. Code of Conduct & Questions

- Be respectful, constructive, and focused on verifiable quality.
- For architectural discussions, open an Issue or start a Discussion on GitHub.
