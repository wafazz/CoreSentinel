# ⌨️ CoreSentinel CLI Protocol

> **One command surface for the whole governance system.**
> Every engine is reachable through `coresentinel <command>`, with grouped help, per-command usage, and CI-safe exit codes.

---

## 🗂️ Command Surface

| Group | Command | Purpose |
| :--- | :--- | :--- |
| **Setup & Diagnostics** | `init` | Bind a project to the CoreSentinel Core |
| | `doctor` | Diagnose the 7 CoreSentinel subsystems |
| | `status` | At-a-glance governance dashboard |
| **Context & Memory** | `context` | Assemble the project context pack |
| | `memory` | Inspect or extend the 6-layer memory engine |
| | `decision` | Architecture Decision Record ledger |
| **Verification & Review** | `verify` | Evidence-Based Verification Suite |
| | `review` | Static review pass over the working diff |
| | `gate` | Drive the 8-stage Quality Gates pipeline |
| | `check` | Anti-pattern & secret scanner |
| **Squad & Governance** | `agent` | Inspect the 17 specialist agent contracts |
| | `audit` | AI accountability audit trail |
| | `score` | 7-dimension health scorecard |
| | `evolve` | Controlled Self-Evolution proposal pipeline |
| **Integration** | `adapter` | Bind the Core to any AI coding host |
| | `stats` | Token usage & session telemetry |
| | `hooks` | Install git pre-commit & pre-push hooks |

Aliases are accepted where they read naturally: `squad` → `agent`, `health` → `score`, `adr` → `decision`, `gates` → `gate`, `ctx` → `context`, `cse` → `evolve`.

---

## 🩺 `coresentinel doctor`

Seven subsystem checks, each resolving to `OK`, `WARN` or `FAIL`:

```text
================================================================
  🛡️  CoreSentinel Doctor — Subsystem Diagnostics
================================================================
  ────────────────────────────────────────────────────────────

  ✓ Configuration          6 core assets present
  ✓ Memory                 7 layers valid, 4 recorded entries
  ✓ Governance             34 protocols, ledgers consistent
  ✓ Agent Registry         17 contracts complete
  ✓ Verification Engine    validator + 7 engines operational
  ✓ Security Rules         5 rules armed, 4 blocking
  ✓ Project Context        Python on 'main', 6 host(s)

  ────────────────────────────────────────────────────────────
  CoreSentinel: HEALTHY
================================================================
```

| Check | What it proves |
| :--- | :--- |
| **Configuration** | All core assets present (`coresentinel.py`, identity, registries, validator) |
| **Memory** | All 7 memory layers exist and parse as valid JSON |
| **Governance** | Protocol documents indexed, gate ledger and evolution ledger consistent |
| **Agent Registry** | Every squad contract carries name, role, input, output and authority |
| **Verification Engine** | Validator present and all 7 engine modules importable |
| **Security Rules** | Anti-pattern database loaded with an enforcement level on every rule |
| **Project Context** | Git repository, detected stack, and at least one AI host bound |

**Overall states:** `HEALTHY` (all OK) · `DEGRADED` (any WARN) · `CRITICAL` (any FAIL).
Non-OK checks print a `➔` remediation hint; `--verbose` prints every finding.

---

## 🔁 Exit Codes

Commands are CI-safe — pipe them straight into a build step:

| Command | Exit 0 | Exit 1 |
| :--- | :--- | :--- |
| `doctor` | HEALTHY or DEGRADED | any subsystem FAIL |
| `verify` | score ≥ 80 (VERIFIED) | score < 80 (UNVERIFIED) |
| `review` | no blocking findings | any blocking finding |
| `check` | zero violations | violations detected |
| `init` | project bound | already bound (without `--force`) |
| *(unknown command)* | — | always exit 1 with a suggestion |

---

## 🤖 Machine-Readable Output

`doctor`, `status`, `context`, `review`, `score` and `adapter export` all accept `--json`:

```bash
coresentinel doctor --json | jq '.overall'
coresentinel review --json | jq '.findings[] | select(.severity == "BLOCK")'
coresentinel status --json | jq '.gates'
```

---

## 🚀 `coresentinel init`

Binds a project to the Core:

1. Detects stack, frameworks and test runner
2. Writes `.coresentinel/config.json` and `.coresentinel/context.json`
3. Seeds the detected stack into project memory (skipping facts already recorded)
4. Optionally binds an AI host with `--host <id> --apply`

Refuses to overwrite an existing `.coresentinel/config.json` without `--force`.

---

## 🔍 `coresentinel review`

A **static** pass over **added lines only**, so pre-existing code is never flagged:

- Anti-pattern and secret violations (reuses `sentinel-validator.py` rules — no duplicated regexes)
- Debug residue: `console.log`, `debugger`, `var_dump`/`dd()`, debug prints
- Unresolved `TODO` / `FIXME` / `HACK` / `XXX` markers
- Source files changed with no test file changed (`--strict` promotes this to blocking)

Scope is covered by staged, unstaged **and** untracked files — a brand-new file is still a reviewable change.

**Verdicts:** `APPROVED` · `APPROVED WITH COMMENTS` · `CHANGES REQUIRED` · `NOTHING TO REVIEW`

> Logic correctness and maintainability stay with the reviewer agent contracts (Cato and Sage).
> `review` does not claim to judge them.

---

## ⚡ Usage

```bash
# Grouped command index
coresentinel

# Detailed usage for any single command
coresentinel help doctor
coresentinel review --help

# Typical loop
coresentinel init            # bind the project
coresentinel doctor          # confirm subsystems are healthy
coresentinel context         # load project context
coresentinel review          # static review of the diff
coresentinel verify          # evidence-based verification
coresentinel status          # dashboard
```

Unknown commands fail loudly with a suggestion rather than silently running something else:

```text
[!] Unknown command: 'docter'
    Did you mean: doctor, adapter, adapters?
    Run 'coresentinel help' to list all commands.
```
