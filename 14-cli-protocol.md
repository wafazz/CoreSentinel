# ⌨️ CoreSentinel CLI Protocol

> **One command surface for the whole governance system.**
> Every engine is reachable through `coresentinel <command>`, with grouped help, per-command usage, and CI-safe exit codes.

---

## 🗂️ Command Surface

| Group | Command | Purpose |
| :--- | :--- | :--- |
| **Setup & Diagnostics** | `init` | Bind a project to the CoreSentinel Core |
| | `doctor` | Diagnose the 10 CoreSentinel subsystems |
| | `status` | At-a-glance governance dashboard |
| | `config` | Inspect and change resolved settings |
| | `migrate` | Create or upgrade the record store |
| **Context & Memory** | `context` | Assemble the project context pack, or a task-relevant one with `--task` |
| | `memory` | Inspect or extend the 6-layer memory engine |
| | `project` | Inspect what CoreSentinel understands about a project |
| | `knowledge` | Traverse the relationships between what it knows |
| | `decision` | Architecture Decision Record ledger, with contradiction checking |
| **Verification & Review** | `verify` | Evidence-Based Verification Suite |
| | `review` | Static review pass over the working diff |
| | `gate` | Drive the 8-stage Quality Gates pipeline |
| | `check` | Anti-pattern & secret scanner |
| **Squad & Governance** | `agent` | Inspect, permission-check and run the 17 specialist contracts |
| | `task` | Plan and run an objective across the specialist pipeline |
| | `incident` | Record what went wrong, and what should be different |
| | `pattern` | The pattern library, as data rather than prose |
| | `audit` | AI accountability audit trail |
| | `score` | 7-dimension health scorecard |
| | `evolve` | Controlled Self-Evolution proposal pipeline |
| **Integration** | `serve` | Serve the versioned HTTP API and the dashboard |
| | `mcp` | Run CoreSentinel as an MCP server |
| | `adapter` | Bind the Core to any AI coding host |
| | `metrics` | What CoreSentinel measures about itself |
| | `stats` | Token usage & session telemetry |
| | `hooks` | Install git pre-commit & pre-push hooks |
| | `version` | Product version & build context |

Aliases are accepted where they read naturally: `squad` → `agent`, `health` → `score`, `adr` → `decision`, `gates` → `gate`, `ctx` → `context`, `cse` → `evolve`, `perf` → `metrics`.

---

## 🩺 `coresentinel doctor`

Ten subsystem checks, each resolving to `OK`, `WARN` or `FAIL`:

```text
================================================================
  🛡️  CoreSentinel Doctor — Subsystem Diagnostics
================================================================
  ────────────────────────────────────────────────────────────

  ✓ Configuration          6 core assets present
  ✓ Runtime                bootstrap 1 ms, 4 services
  ✓ Storage                json backend, 12 record(s)
  ✓ Memory                 7 layers valid, 4 recorded entries
  ✓ Governance             34 protocols, ledgers consistent
  ✓ Agent Registry         17 contracts complete
  ✓ Verification Engine    validator + 11 engines operational
  ✓ Security Rules         5 rules armed, 4 blocking
  ✓ Observability          14 series, 7/11 subjects
  ✓ Project Context        Python on 'main', 6 host(s)

  ────────────────────────────────────────────────────────────
  CoreSentinel: HEALTHY
================================================================
```

| Check | What it proves |
| :--- | :--- |
| **Configuration** | All core assets present (`coresentinel.py`, identity, registries, validator) |
| **Runtime** | Runtime bootstraps, services register, settings resolve without a config problem |
| **Storage** | The configured backend opens, its migrations are applied, its records read back |
| **Memory** | All 7 memory layers exist and parse as valid JSON |
| **Governance** | Protocol documents indexed, gate ledger and evolution ledger consistent |
| **Agent Registry** | Every squad contract carries name, role, input, output and authority |
| **Verification Engine** | Validator present and all 7 engine modules importable |
| **Security Rules** | Anti-pattern database loaded with an enforcement level on every rule |
| **Observability** | Metric subjects declared, and every published budget has a measurement behind it |
| **Project Context** | Git repository, detected stack, and at least one AI host bound |

**Overall states:** `HEALTHY` (all OK) · `DEGRADED` (any WARN) · `CRITICAL` (any FAIL).
Non-OK checks print a `➔` remediation hint; `--verbose` prints every finding.

---

## 🔁 Exit Codes

Commands are CI-safe — pipe them straight into a build step:

| Command | Exit 0 | Exit 1 |
| :--- | :--- | :--- |
| `doctor` | HEALTHY or DEGRADED | any subsystem FAIL |
| `verify` | score ≥ 80 (VERIFIED) | score < 80 (UNVERIFIED) — **exit 2** when too little evidence could be executed to judge the claim at all (INDETERMINATE) |
| `review` | no blocking findings | any blocking finding |
| `check` | zero violations | violations detected |
| `init` | project bound | already bound (without `--force`) |
| `decision verify` | no accepted decision is reversed | the change contradicts or revisits one |
| `task run` | the pipeline completed | a role FAILED or was DENIED |
| `gate run` | no gate FAILED | any gate FAILED or was BLOCKED |
| `adapter conformance` | every adapter conforms | any adapter does not |
| `audit verify` | the chain is intact | any record was altered, inserted, removed or reordered |
| `evolve apply` | the change was applied | the proposal is not APPROVED, or the target cannot be changed safely |
| `serve` | — (runs until interrupted) | a non-loopback bind was requested without a configured token |
| *(unknown command)* | — | always exit 1 with a suggestion |

---

## 🏷️ Versioning

The product version lives in one place: the **`VERSION`** file at the Core root. The CLI, both installers, the help header and the adapter context bundle all read it. Nothing hardcodes a version number — that duplication is what let the old `9.0` string drift out of date in two shell scripts.

```bash
coresentinel version        # version + build context
coresentinel --version      # identical
coresentinel -v             # identical
coresentinel version --json # for CI
```

```text
  🛡️  CoreSentinel 10.0.0
  ----------------------------------------------------
  Core Directory         : /path/to/CoreSentinel
  Python                 : 3.13.14
  Platform               : Windows 11
  Protocols              : 36 documents
  Adapter Registry       : v1.0.0
  Squad Contracts        : v1.0.0
  Anti-Pattern Database  : v1.0.0
```

Registries carry their own versions (`adapters.json`, `squad-contracts.json`, `anti-patterns.json`), so a bug report states exactly which rule sets were loaded. To release, edit `VERSION` — nothing else.

> `-v` at the command position means `version`. As a flag to a command (`coresentinel doctor -v`) it still means `--verbose`; the two never collide because one is a command and the other is an argument.

---

## 📡 Output Stream Contract

**stdout carries the payload. stderr carries diagnostics.**

Every `[!]` warning — unreadable registry, missing `VERSION`, corrupt memory layer — is written to stderr. A damaged Core therefore still emits valid JSON on stdout, and `coresentinel doctor --json | jq` keeps working while the warnings remain visible in the terminal.

This is enforced by test: each `--json` command is run against a deliberately damaged Core and its stdout must still parse.

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

## 🎯 `coresentinel context --task`

Without `--task`, the v1 pack: stack, frameworks, test runner, key files, git history and every
recorded fact.

With `--task`, only what that task needs:

```bash
coresentinel context --task "Add Redis caching to product listing" --budget 4000
```

- Facts, decisions, failures, patterns and journal entries are ranked by the **recall** engine —
  term coverage, phrase bonus, confidence weight — not dumped.
- Anti-pattern rules are matched on the `trigger_context` they already declare. `STRICT_BLOCK`
  rules are always included: they are the floor, not a suggestion.
- Any decision the task appears to contradict is lifted to the top and flagged.
- Sections fill in priority order under a shared budget, most-costly-to-get-wrong first.

The token figure is an estimate — characters ÷ 4 — and is labelled as one everywhere it appears.
A real tokenizer would mean a vendor dependency, and the number is only ever used to decide what
fits.

**Truncation is declared.** If the pack does not fit, the count of excluded items and the
highest-scoring one are printed, so a partial pack never reads as a complete one.

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

## 📈 `coresentinel metrics`

What CoreSentinel measures about **itself**, across eleven subjects — `command`,
`service`, `agent`, `task`, `verification`, `gate`, `memory`, `context`,
`recall`, `storage`, `audit`.

```bash
coresentinel metrics                    # series, coverage and the budget verdict
coresentinel metrics coverage           # which subjects have ever been measured
coresentinel metrics budgets            # published limits and the basis for each
coresentinel metrics --subject recall --json
```

There are no zero-initialised counters. A subject nothing has exercised reports
as **never observed** rather than as `0`, for the same reason a health dimension
nothing could evidence reports `UNKNOWN`: a zero is a measurement, and nobody
took one.

Series are aggregates — count, total, min, max, last — never the samples, so a
series costs the same after a million observations as after one. They are
flushed to the record store at shutdown, because a CLI process lives for exactly
one command.

Exits **1** when a measured series is over its published budget. See
[Performance](./45-performance-protocol.md#coresentinels-own-performance) for the
budget table.

> `stats` reads the transcripts of AI hosts. `metrics` measures CoreSentinel.

---

## 📄 Paging

Every list surface pages: default **50**, maximum **200**.

```bash
coresentinel audit list --limit 20 --offset 40
curl "$API/api/v1/audit/list?limit=20&offset=40"
```

A caller asking for more than the maximum receives the maximum with
`"clamped": true` — the response says it was capped rather than quietly
returning fewer rows than were requested. `"total": null` means the collection
was never counted, which is not the same as `0`.

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
