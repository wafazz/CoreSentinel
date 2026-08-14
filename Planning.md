# CoreSentinel v2 — AI Engineering Control Plane

> **Status**: Phases 0–11 complete. Phase 12 next.
> **Author**: Iris (principal architect)
> **Planned**: 2026-08-13 · **Last updated**: 2026-08-14
> **Baseline inspected**: `main` @ `216828d`, CoreSentinel `10.1.0`, 436 tests green.
> **Now**: CoreSentinel `10.12.0`, 1,294 tests green. Phase reports in §12, findings status in §11.

---

## 1. Executive Summary

### 1.1 What CoreSentinel is today

CoreSentinel v1 is a **file-based governance and context layer** for AI coding assistants. It is
genuinely built, not aspirational: 5,184 lines of engine Python across 16 root modules, 37 protocol
documents, 3 JSON registries, a 21-command CLI, and 2,434 lines of self-tests (436 passing, verified
locally on 2026-08-13) driven by a 6-stage CI pipeline across 3 operating systems × 3 Python versions.

Its architecture is a **flat module set around a shared file store**. Every engine imports
`coresentinel_memory`, resolves paths relative to `__file__`, reads and writes JSON directly, and
prints a formatted report to stdout. There is no runtime, no service layer, no persistence
abstraction, and no process boundary. This is not an accident — ADR-001 in `memory/decisions.json`
records the deliberate choice of "File-based JSON Layered Memory" over SQLite/PostgreSQL/Redis for
"zero external dependencies; portable across IDEs". That decision was correct for v1 and must be
respected, superseded explicitly, or scoped — never silently reversed.

### 1.2 What v2 must become

> **CoreSentinel v2** — an AI Engineering Control Plane providing persistent project intelligence,
> memory, governance, agent orchestration, verification, auditability, learning and controlled
> self-evolution across AI coding agents.

The transformation is **not** a rewrite. It is three distinct movements applied to a working system:

| Movement | From | To |
| :--- | :--- | :--- |
| **Truthfulness** | Verification and health scores that report PASS without running anything | Every score traceable to a command, its exit code and its output |
| **Structure** | 16 flat modules sharing globals and reimplementing helpers | A modular monolith with a runtime, service interfaces and a persistence port |
| **Agency** | A passive rules file the agent may read | An active control plane that dispatches, constrains, verifies and audits agents |

### 1.3 The finding that reorders everything

The brief's recommended sequence starts with Core Runtime. Repository analysis proves a different
order is technically superior, and this is the single most important conclusion of Phase 0:

**CoreSentinel's verification engine currently fabricates evidence.**

Measured, not inferred — an **empty directory** containing no code, no git repository and no tests,
submitting the claim *"I fixed the authentication vulnerability"*:

```console
$ coresentinel verify --claim "I fixed the authentication vulnerability"
  [✓] Linter & Formatting            : PASS  (Syntax & style conform to repository rules)
  [✓] Dependency Vulnerability Audit : PASS  (No critical vulnerabilities in lockfiles)
  [✓] Diff Inspection                : PASS  (Diff stat: Git diff clean)
  ...
  Status : VERIFIED
  Score  : 80/100

$ coresentinel score --json
  { "Architecture": 90, "Code Quality": 96, "Documentation": 88,
    "Reliability": 93, "Dependencies": 97, "overall_score": 89 }
```

Three of six evidence checks (`Linter`, `Dependency Audit`, `Diff Inspection`) are hardcoded `PASS`
with an invented justification string — `coresentinel.py:170-201`. Five of seven health dimensions
are hardcoded constants — `coresentinel_score.py:31-84`. Four of eight quality gates return
`PASS` unconditionally — `coresentinel_gates.py:76-132`.

This is the exact failure mode the product exists to prevent, committed by the product itself.
Everything the brief asks for downstream — quality gates, project health, the learning engine,
controlled evolution — **consumes these numbers**. Building orchestration on top of a verifier that
lies propagates the lie into every new subsystem and makes the audit trail a record of fiction.

**Therefore Phase 1 is Evidence Integrity, before any architectural work.** It is small, it is
cheap, it is the highest-value change in the entire roadmap, and it makes every later phase
measurable. The runtime work follows immediately in Phase 2.

---

## 2. Method

Phase 0 inspection covered, in order:

1. Full file tree (78 entries, 31 Python files, 40 markdown, 15 JSON) — no file skipped.
2. `README.md` in full, and all 37 numbered protocol documents.
3. All 16 root Python modules read line by line.
4. `tests/conftest.py` and the test suite layout; all 436 tests executed locally.
5. All 3 JSON registries and all 9 memory ledgers, shape and content.
6. The CI workflow, both installers, both hook installers.
7. **Empirical probes** against a sandboxed copy for every claim in §4 — no finding below is
   inferred from reading alone.

---

## 3. Current Architecture Analysis

### 3.1 Inventory

| Layer | Artifacts | LOC |
| :--- | :--- | ---: |
| CLI dispatcher | `coresentinel.py` (registry of 21 commands + evidence suite) | 873 |
| Memory engines | `_memory` `_recall` `_lifecycle` | 1,345 |
| Host adapters | `_adapters` | 519 |
| Diagnostics | `_doctor` | 471 |
| Telemetry | `agent-stats.py` | 454 |
| Review / gates | `_review` `_gates` | 490 |
| Context / init | `_context` `_init` | 356 |
| Governance ledgers | `_audit` `_evolve` `_score` `_squad` | 481 |
| Security scanner | `sentinel-validator.py` | 155 |
| **Engine total** | **16 modules** | **5,184** |
| Self-tests | 14 files + `conftest.py`, 436 tests | 2,434 |
| Governance corpus | 37 protocols, 3 registries | — |

### 3.2 Runtime topology

```text
coresentinel.py  (COMMANDS registry → handler → lazy `import coresentinel_<engine>`)
        │
        ├── every engine defines its own: SCRIPT_DIR, run_cmd(), read_json(), print_header()
        │
        └── every engine reads/writes: <core>/memory/*.json   (Core scope)
                                       <project>/.coresentinel/memory/*.json   (project scope)
```

There is no shared runtime object, no configuration file that engines read, no dependency
injection, and no in-process boundary between "compute a result" and "print a report". Most
engines interleave the two: `run_evidence_verification()` computes scores and prints them in the
same 112-line function, which is why `verify` has no `--json` mode while `doctor`, `status`,
`context`, `review`, `score` and `adapter export` do.

### 3.3 Subsystem assessment

**Memory engine — the strongest subsystem.** Six fact layers plus a decision ledger, confidence
classification with enforced thresholds (`≥0.90` Known / `≥0.50` Assumed / below Unknown), stable
content-derived fact ids (`fact_id()` SHA-1), and a genuine project/core scoping split resolved by
walking up for `.coresentinel/config.json` the way git finds `.git`. `load_layer()` returns
`(data, error)` and refuses to overwrite a corrupt layer — a real safety property, tested.

**Memory lifecycle — well designed.** `decay` is idempotent because it derives the target from
`base_confidence` and age rather than the current value; `promote` requires an explicit
`transferable` mark to cross from project to Core scope; `consolidate` keeps the highest confidence
rather than averaging; `compact` summarises rather than deletes; every destructive operation
snapshots first and is a dry run until `--apply`. This is the part of v1 most worth preserving
verbatim.

**Recall engine — solid retrieval, unused by context.** Term coverage + phrase bonus + confidence
weight floored at 0.5, searching fact layers, ADR ledger and journal in one pass. It works. But
nothing calls it during context assembly — `coresentinel_context.collect_memory_facts()` dumps
**every** fact from `project`, `patterns` and `longterm` unconditionally. The intelligence exists
and is not wired to the place that needs it.

**Adapter layer — correctly conceived, narrowly scoped.** Registry-driven (8 hosts, adding one is a
JSON entry), dry-run by default, `CORESENTINEL:MANAGED` marker, refuses to clobber hand-authored
files, backs up on `--force`. But it is a **rules-file projection layer**, not an agent adapter
layer: it renders markdown *to* a host and has no path for invoking an agent or normalising a
response back.

**Squad contracts — data without an engine.** 17 contracts declaring `input_contract`,
`output_contract`, `authority`, `constraints`, `verification_gate`. `coresentinel_squad.py` (97
lines) only lists and prints them. Nothing dispatches an agent, enforces an authority boundary, or
validates that an output contract was satisfied. The README's claim that "a read-only researcher
cannot silently write files" is a statement about a JSON document, not an enforced runtime property.

**Governance ledgers — thin but honest.** `evolve` (propose → approve, sequential collision-free
ids) and `audit` (run cards) work as documented. `audit` uses `random.randint(1000,9999)` for run
ids — collision-prone and non-monotonic — and records are appended with no integrity chaining.

**Doctor — the best-engineered command.** Seven checks each returning
`{check, status, summary, findings, fix}`, correct `HEALTHY`/`DEGRADED`/`CRITICAL` rollup, remediation
hints, `--json`, exit 1 on FAIL. This structure is the template the rest of the system should adopt.

**Self-test suite — strong isolation, weak assertions in one place.** `conftest.py` enforces real
guarantees: no test touches the real `memory/`, mutating tests run against a sandbox copy, diff
engines get a real throwaway git repo. But `tests/verification/test_evidence_suite.py` asserts
*shape*, not *truth*: that six categories are printed, that `/100` appears, that dimensions are in
range and average correctly. `test_status_thresholds` reimplements the threshold logic inside the
test and asserts it against itself — a tautology that would pass if the engine were deleted.

---

## 4. Verified Findings

Every item below was reproduced against the working tree or a sandbox on 2026-08-13.

| # | Severity | Finding | Evidence |
| :--- | :--- | :--- | :--- |
| **F-01** | **Critical** | `verify` awards 45/100 points from three hardcoded `PASS` checks that execute nothing (`Linter`, `Dependency Audit`, `Diff Inspection`). Check 1 awards 20/20 whether the tree is dirty or clean. | Empty non-git dir scored **80/100 VERIFIED** on the claim "I fixed the authentication vulnerability". `coresentinel.py:169-201` |
| **F-02** | **Critical** | `score` invents 5 of 7 dimensions from constants: Architecture 90, Code Quality 96, Documentation 88, Reliability 93, Dependencies 97. Only Security and Testing execute anything. | Empty dir scored **89/100**. `coresentinel_score.py:31-84` |
| **F-03** | **High** | 4 of 8 quality gates (`Plan`, `Architecture`, `Implementation`, `Deployment`) return `PASS` with no check. `Implementation` runs `git status` and discards the result. | `coresentinel_gates.py:76-132` |
| **F-04** | **High** | Five call sites shell out to bare `python`, absent on macOS and on Debian/Ubuntu with only `python3`. The Security gate, Review gate, Verification gate, `verify`'s anti-pattern check and `score`'s Security dimension therefore fail for the wrong reason on this class of machine. | `which python` → not found. `coresentinel.py:178`, `_gates.py:84,112,122`, `_score.py:42` |
| **F-05** | **High** | Trailing value-flags crash with an uncaught `IndexError` traceback instead of a usage error. | `coresentinel memory add --fact x --layer` → `IndexError`. Same at `decision add --title`. `coresentinel.py:245`, `:416` |
| **F-06** | **Medium** | `run_cmd` uses `shell=True` with f-string-interpolated paths in 6 modules, at 3 different timeouts (30/60/120s). A path containing a quote is a command-injection surface. | 6 independent `run_cmd` definitions |
| **F-07** | **Medium** | Context assembly dumps every fact from three layers with no relevance filter or budget — the "context bloat" failure the brief explicitly forbids. The ranked `recall` engine that would fix it is never called. | `_context.py:101-121` |
| **F-08** | **Medium** | The ADR ledger is Core-global only, unlike facts. Ten repositories share one decision list. Schema has 8 fields; the brief requires 18 (no problem, context, evidence, author, agent, confidence, related files/incidents/decisions, supersedes). | `_memory.py:268-296` |
| **F-09** | **Medium** | Audit run ids are `random.randint(1000,9999)` — collision-prone, non-monotonic, and the trail has no tamper-evidence. | `_audit.py:43-44` |
| **F-10** | **Low** | `memorycore.conf` is written by both installers and read by no engine — dead config shipping another machine's absolute Windows paths and a UTF-8 BOM. | `grep` across all `*.py` |
| **F-11** | **Low** | `project-labels.json` ships 13 absolute paths from a different user's machine (`C--Users-fakrul-hakim-OneDrive---Daythree-Digital-Berhad-...`). | Committed file contents |
| **F-12** | **Low** | README states "37 protocols" in four places and "(36 documents)" in the protocol directory heading. Actual count is 37. | `ls [0-9][0-9]-*.md \| wc -l` → 37 |
| **F-13** | **Low** | `coresentinel.py:30-62` is 33 consecutive blank lines. | File inspection |
| **F-14** | **Low** | Verification tests assert output shape, not evidential truth; `test_status_thresholds` asserts a reimplementation of the logic against itself. | `tests/verification/test_evidence_suite.py:72-81` |
| **F-15** | **Info** | Duplication: `run_cmd` ×6, `read_json` ×4, `print_header` ×3, VERSION reading ×3, UTF-8 stdout reconfiguration ×13. | Cross-module grep |

**F-01 through F-04 are the reason this project needs v2 more than it needs new features.**

---

## 5. Gap Analysis

Classification: **[✔] Implemented** · **[~] Partial** · **[S] Specification only** · **[ ] Missing** ·
**[R] Needs refactoring**

### Module A — Core Runtime

| Capability | State | Notes |
| :--- | :---: | :--- |
| Configuration system | [ ] | `memorycore.conf` is dead (F-10). Engines hardcode paths from `__file__`. |
| Lifecycle / bootstrap | [ ] | No init path; each command constructs its own world. |
| Dependency management | [ ] | Cross-module `import` by bare name; no interfaces. |
| Project registration | [~] | `init` writes `.coresentinel/config.json`; no registry of known projects. |
| Service discovery | [ ] | — |
| Event system | [ ] | — |
| Structured logging | [ ] | `print()` to stdout/stderr; the stream contract is real and tested, but there is no logger. |
| Error handling | [~] | Consistent `(data, error)` in memory; ad-hoc `except Exception` elsewhere. |
| Persistence | [R] | Direct `json.load`/`json.dump` at ~40 call sites. No port, no transaction, no migration. |
| Plugin loading | [ ] | — |
| Health monitoring | [~] | `doctor` is excellent for subsystems; nothing for runtime metrics. |

### Module B — Project Brain

| Capability | State | Notes |
| :--- | :---: | :--- |
| Language / stack detection | [~] | 8 marker files, first-match. No version detection. |
| Framework detection | [~] | Substring match over dependency names — false-positive prone. |
| Database detection | [ ] | — |
| Package manager | [ ] | Inferred implicitly from stack, never recorded. |
| Docker / CI / deployment | [~] | Listed as "key files" only; never parsed. |
| Test runner | [✔] | Correct across npm/pytest/phpunit/cargo/go. |
| Repository state | [✔] | Branch, commit, dirty count, recent log. |
| APIs / services / components | [ ] | — |
| Dependency graph | [ ] | — |
| Architecture model | [ ] | — |
| Knowledge graph | [ ] | — |

### Module C — Memory Engine

| Capability | State | Notes |
| :--- | :---: | :--- |
| 6 layers + scoping | [✔] | Best-built subsystem. Project/Core split is correct and tested. |
| Confidence scoring | [✔] | Thresholds enforced, not decorative. |
| Timestamps / source | [✔] | `created_at`, `last_verified`, `source`. |
| Decay / re-verification | [✔] | Idempotent by construction. |
| Promotion / consolidation / compaction | [✔] | With snapshots and dry-run. |
| Duplicate detection | [✔] | Normalised-form grouping. |
| Provenance | [~] | `sources[]`, `promoted_from` exist. No agent/task attribution. |
| Semantic retrieval | [~] | Lexical ranking only — adequate and dependency-free; no embeddings. |
| **Contextual assembly** | **[ ]** | **F-07. The headline v2 capability. `recall` exists; nothing calls it for context.** |
| Contradiction detection | [ ] | — |
| Importance / relevance score | [~] | Confidence ≠ importance; not modelled. |
| Short-term memory | [~] | `working` layer is a task/status pair, not a turn buffer. |
| Organizational memory | [ ] | — |

### Module D — Decision Intelligence

| Capability | State | Notes |
| :--- | :---: | :--- |
| Ledger with id / title / reason / alternatives | [✔] | Sequential `ADR-NNN`. |
| Full 18-field schema | [~] | 8 of 18 present (F-08). |
| Project scoping | [ ] | Core-global only (F-08). |
| Search | [✔] | Via `decision list --query` and `recall`. |
| **Contradiction guard** | **[ ]** | **The brief's flagship example. Nothing prevents an agent reversing ADR-0042.** |
| `decision verify` | [ ] | — |
| Supersession chain | [ ] | — |

### Module E — Agent Orchestrator

| Capability | State | Notes |
| :--- | :---: | :--- |
| Agent registry | [✔] | 17 contracts, complete and validated by `doctor`. |
| Contract schema | [S] | Declared in JSON and prose; nothing consumes it at runtime. |
| Task / input / context / action / result contracts | [ ] | — |
| Dispatch | [ ] | — |
| Planner | [ ] | — |
| Structured output | [ ] | — |
| Confidence / evidence per agent | [ ] | — |
| Inter-agent distrust | [S] | Documented in `02-team-protocol.md`; unenforced. |

### Module F — Agent Adapter System

| Capability | State | Notes |
| :--- | :---: | :--- |
| Vendor-neutral rules projection | [✔] | 8 hosts, safe sync, managed marker. Genuinely good. |
| Host detection | [✔] | Filesystem + env markers. |
| Context bundle export | [✔] | `coresentinel_api: 1.0` payload. |
| **Agent invocation** | **[ ]** | Adapters render *to* hosts; they cannot *run* one. |
| Response normalisation | [ ] | — |
| Generic CLI / HTTP agent | [ ] | — |

### Module G — MCP

| Capability | State | Notes |
| :--- | :---: | :--- |
| MCP server | [ ] | Appears only as the string `"MCP Servers"` in `adapters.json` extensions. |
| Tool surface (15 verbs in brief) | [ ] | — |
| Governance-respecting, audited MCP | [ ] | — |

### Module H — Quality Gates

| Capability | State | Notes |
| :--- | :---: | :--- |
| 8-gate ordered pipeline | [✔] | With PASS/FAIL/BLOCKED/WAIVED and mandatory waiver rationale. |
| Gate evaluation | [~] | 4 of 8 are stubs (F-03); the other 4 shell out on a broken interpreter path (F-04). |
| Machine-readable result | [ ] | `gate` has no `--json`. |
| Requirement / Documentation gates | [ ] | Brief names 8 gates; 2 do not map to the existing 8. |

### Module I — Verification Engine

| Capability | State | Notes |
| :--- | :---: | :--- |
| Evidence framing & scoring | [~] | Framework is right; **inputs are fabricated (F-01)**. |
| Test execution | [~] | Real for npm/pytest; no other runners; result not captured. |
| Security verification | [~] | Real scanner, 2 secret regexes, broken invocation (F-04). |
| Lint verification | [ ] | Hardcoded PASS. |
| Dependency audit | [ ] | Hardcoded PASS. |
| Diff verification | [ ] | Hardcoded PASS. |
| Performance / benchmark | [ ] | — |
| `{check, command, timestamp, exit_code, output, evidence, status}` record | [ ] | Only a human-readable string survives. |
| `verify --json` | [ ] | — |

### Module J — Project Health

| Capability | State | Notes |
| :--- | :---: | :--- |
| 7 dimensions + status bands | [✔] | Shape and thresholds correct. |
| **Evidence-based scores** | **[ ]** | **5 of 7 invented (F-02).** |
| 12 dimensions per brief | [~] | Missing Governance, Memory, Technical Debt, CI/CD, Deployment. |
| Snapshots / trend | [ ] | — |

### Module K — Incident System

| Capability | State | Notes |
| :--- | :---: | :--- |
| Incident protocol | [S] | `61-incident-protocol.md` — prose only. |
| Incident records (`INC-NNNN`) | [ ] | `failures.json` is an empty fact layer, not an incident store. |
| Links to decisions/commits/tests/patterns | [ ] | — |
| Root-cause → pattern pipeline | [S] | Described in `60`/`61`; no data path. |

### Module L — Learning Engine

| Capability | State | Notes |
| :--- | :---: | :--- |
| Proposal → evidence → approval → version | [✔] | `evolve` works and is tested. |
| Human approval enforced | [✔] | Nothing auto-approves; regression-tested. |
| Observation → candidate rule | [ ] | Proposals are hand-written; nothing generates them. |
| Pattern store (`PAT-NNNN`) | [S] | `11-pattern-library.md` is prose; `patterns.json` is an empty fact layer. |
| Reversibility of an applied evolution | [~] | Approval is recorded but never *applies* a change to a rule file. |

### Module M — Knowledge Graph

| Capability | State | Notes |
| :--- | :---: | :--- |
| Entities / relations | [ ] | No entity has an id usable as a graph node except facts and ADRs. |

### Module N — Audit

| Capability | State | Notes |
| :--- | :---: | :--- |
| Run cards | [✔] | Agent, task, file/test counts, scan results, score. |
| Coverage of the brief's 12 audit subjects | [~] | 1 of 12 (agent runs). No memory-change, rule-change, command, gate or config auditing. |
| Append-oriented | [✔] | Appends only. |
| **Tamper-aware** | **[ ]** | No hash chain, no sequence integrity, random ids (F-09). |

### Module O — Security

| Capability | State | Notes |
| :--- | :---: | :--- |
| Secret scanning | [~] | 2 regexes (generic key assignment, PEM block). Narrow. |
| Anti-pattern scanning | [~] | 4 regexes. Fixture opt-out marker is a nice design. |
| Pre-commit enforcement | [✔] | Hook installers for both shells. |
| Safe command execution | [R] | `shell=True` + interpolated paths ×6 (F-06). |
| Path traversal protection | [ ] | `--project` and adapter paths are resolved without containment checks. |
| Agent permission boundaries | [S] | `authority` strings in JSON; unenforced. |
| AuthN / AuthZ | [ ] | Not needed for local-first single user; **required** the moment the API server exists. |
| Rate limiting | [ ] | Same. |

### Module P — CLI

| Capability | State | Notes |
| :--- | :---: | :--- |
| Registry-driven command surface | [✔] | 21 commands, grouped help, aliases, per-command help, did-you-mean. |
| Exit-code contract | [✔] | Documented and tested. |
| stdout payload / stderr diagnostics | [✔] | Tested against a deliberately damaged Core — a genuinely good property. |
| `--json` coverage | [~] | 6 of 21 commands. `verify`, `gate`, `agent`, `audit`, `evolve`, `decision` lack it. |
| Argument parsing | [R] | Hand-rolled `args.index(x)+1`; crashes on trailing flags (F-05). |
| Brief's new verbs (`project`, `task`, `agent run`, `incident`, `pattern`, `mcp`) | [ ] | — |

### Module Q — API Server

| Capability | State | Notes |
| :--- | :---: | :--- |
| HTTP API | [ ] | **`16-api-protocol.md` is not about CoreSentinel's API** — it is guidance for building webhooks in *governed* projects. The API surface is entirely absent, not merely specified. |
| Versioned routes | [ ] | The `coresentinel_api: "1.0"` marker on JSON payloads is the only versioning that exists. |

### Module R — Web Dashboard

| Capability | State | Notes |
| :--- | :---: | :--- |
| Any UI | [ ] | — |

### Cross-cutting

| Capability | State | Notes |
| :--- | :---: | :--- |
| Data storage / migrations | [ ] | ADR-001 chose files; no schema, no migration path. |
| Event system | [ ] | — |
| Plugin system | [ ] | — |
| Observability / metrics | [ ] | `agent-stats.py` reads host transcripts — telemetry *about hosts*, not about CoreSentinel. |
| Performance (caching, pagination, budgets) | [ ] | Every command reads every file every time. Acceptable at current volume; not at v2 volume. |
| Testing | [✔] | 436 tests, strong isolation, CI-gated. Weak only where noted (F-14). |
| Demo project | [ ] | — |
| Documentation | [~] | Excellent README and protocol corpus; **but it documents fabricated verification as real** (F-01/F-02), which is the documentation defect that matters most. |
| `AGENTS.md` | [ ] | Rendered *to* hosts by the adapter; not authored *for* contributors to this repo. |

**Summary**: of ~95 assessed capabilities — 24 implemented, 27 partial, 6 specification-only,
34 missing, 4 needing refactor.

---

## 6. Target Architecture

### 6.1 Principles

1. **Local-first.** `git clone && coresentinel init && coresentinel doctor` yields value with no
   account, no server, no network.
2. **Zero required runtime dependencies.** Core stays stdlib-only (`sqlite3`, `http.server`,
   `json` are stdlib). Anything else is an optional extra behind a plugin interface.
3. **Vendor-neutral.** No business logic keyed to one AI provider. Hosts are interchangeable workers.
4. **Modular monolith.** One process, clean internal boundaries. No microservices, no brokers,
   no graph or vector database.
5. **Evidence or silence.** A subsystem that cannot measure something reports `UNKNOWN`, never an
   invented number.
6. **Backward compatible.** v1 commands, memory formats, JSON contracts and adapters keep working.
7. **Reversible.** Every destructive or evolutionary operation snapshots and can be undone.

### 6.2 Layered view

```text
            ┌──────────────────────────────────────────────┐
  SURFACES  │  CLI  ·  HTTP API v1  ·  MCP server  ·  Dashboard │
            └───────────────────────┬──────────────────────┘
                                    │  (all four call the same services;
                                    │   none may bypass governance or audit)
            ┌───────────────────────▼──────────────────────┐
  SERVICES  │ ProjectBrain · Memory · Context · Decisions   │
            │ Orchestrator · Verification · Gates · Health  │
            │ Incidents · Patterns · Learning · Audit       │
            └───────────────────────┬──────────────────────┘
            ┌───────────────────────▼──────────────────────┐
  RUNTIME   │ Config · Container · EventBus · Logging      │
            │ Errors · Paths · SafeExec · Permissions      │
            └───────────────────────┬──────────────────────┘
            ┌───────────────────────▼──────────────────────┐
  STORAGE   │ Repository ports → JsonStore | SqliteStore   │
            │                              | (PostgresStore)│
            └──────────────────────────────────────────────┘

  ADAPTERS (plug into Orchestrator, not into services):
     RulesSync: claude-code · cursor · gemini · codex · copilot · windsurf · antigravity · generic
     Invoke:    CliAgent · HttpAgent · McpAgent
```

### 6.3 Package layout

The new package lives at `coresentinel/`. The 16 root modules **remain as thin re-export shims**
so that `import coresentinel_memory` — which every existing test and any user script relies on —
keeps working unchanged.

```text
coresentinel/
├── runtime/      config · container · events · errors · logging · paths · safe_exec
├── storage/      ports · json_store · sqlite_store · migrations/
├── project/      model · registry · discovery/{language,framework,database,ci,docker,api,tests}
├── memory/       layers · lifecycle · recall · journal · assembly   ← assembly is new
├── decisions/    ledger · schema · contradiction
├── knowledge/    entities · relations · queries
├── agents/       protocol · registry · permissions · planner · orchestrator
│   └── adapters/ base · cli_agent · http_agent · mcp_agent · rules_sync/
├── verification/ engine · evidence · checks/{tests,security,lint,deps,diff,build,benchmark}
├── gates/        pipeline · definitions
├── health/       scoring · dimensions/ · snapshots
├── incidents/    model · ledger · linkage
├── patterns/     model · library
├── learning/     observer · candidates · proposals · apply
├── audit/        ledger (hash-chained) · subjects
├── security/     secrets · policy · redaction
├── observability/ metrics · tracing
├── plugins/      loader · interfaces
├── cli/          app · commands/
├── api/          server · v1/
├── mcp/          server · tools
└── web/          static dashboard (no build step)
```

### 6.4 Storage strategy — respecting ADR-001

ADR-001 chose file-based JSON. v2 does **not** reverse it. It splits by access pattern, and the
split itself is recorded as a superseding ADR through CoreSentinel's own ledger:

| Data | Store | Why |
| :--- | :--- | :--- |
| Memory layers, decisions, journal, config | **JSON files** (unchanged) | Human-readable, git-committable, diffable. The README's "commit `.coresentinel/memory/` to share verified facts with your team" is a real feature. Reversing it would break every v1 install. |
| Audit events, verification runs, health snapshots, agent sessions, tasks, knowledge relations, metrics | **SQLite** (stdlib) | High-volume, append-heavy, needs indexed and ranged queries. Putting these in JSON is what makes v1 re-read every file on every command. |
| Production multi-user deployment | **PostgreSQL** behind the same port | Optional, later, no core changes. |

All access goes through repository ports (`MemoryRepository`, `AuditRepository`, …). Business logic
never sees a filesystem path or a SQL string. Migrations are numbered, forward-only and idempotent.

### 6.5 Agent protocol

The internal contract every adapter translates to and from:

```python
AgentTask     : id, project, agent_role, objective, inputs, context_pack,
                permissions, constraints, deadline, parent_task
AgentResult   : task_id, status, summary, actions[], files_changed[],
                commands_run[], tests[], evidence[], confidence,
                warnings[], unresolved[], raw_response_ref
Evidence      : check, command, cwd, started_at, duration_ms, exit_code,
                output_digest, output_excerpt, artifact_path, status
Permission    : filesystem.read | filesystem.write | shell.execute |
                network.access | git.commit | git.push | deployment | production.access
                → DENY | ASK | LIMITED(scope) | ALLOW
```

Default permission set for any agent is `filesystem.read: ALLOW`, everything else `DENY`.
Escalation is explicit, recorded and audited. **No agent gets unrestricted shell by default.**

### 6.6 Backward-compatibility contract

| Guarantee | Mechanism |
| :--- | :--- |
| Every v1 command name and alias keeps working | Command registry retains all 21 entries; new verbs are additive |
| Every v1 `--json` payload keeps its keys | Additive-only; `coresentinel_api` bumps to `1.1` with the old keys retained |
| `import coresentinel_memory` etc. keeps working | Root modules become re-export shims with a `DeprecationWarning` only from v11.1 |
| v1 memory JSON keeps loading | Schema is additive; new fields optional with defaults |
| v1 `.coresentinel/config.json` keeps resolving | `config_version` added; absent means v1, handled |
| Existing 436 tests keep passing | Regression gate on every phase; a test may be *added to*, never *weakened* |

Where a break is unavoidable it gets: documented rationale, an automated migration
(`coresentinel migrate`), a compatibility shim, migration tests, a `VERSION` major bump and a README
entry.

---

## 7. Implementation Roadmap

Twelve phases. **Phase order deviates from the brief's suggestion**: Evidence Integrity is promoted
ahead of Core Runtime for the reason argued in §1.3. Every phase ends with
`IMPLEMENT → TEST → VERIFY → DOCUMENT → REVIEW` and a report in the brief's required format.

**Standing acceptance criteria for every phase** (in addition to those listed):
all 436 baseline tests still pass; `coresentinel doctor` reports HEALTHY; no `--json` contract loses
a key; no test is deleted or weakened; no new required runtime dependency.

---

### Phase 1 — Evidence Integrity `[✔]`

> **Delivered 2026-08-13, released as `10.2.0`.** 477 tests green (from 436). Report in §12.
> Two deviations from the plan as written, both recorded there: the new modules are flat
> `coresentinel_*.py` rather than a `coresentinel/` package (a package directory shadows
> `coresentinel.py` on import and the sandbox fixture copies no subdirectories — Phase 2
> owns that migration), and `--legacy-scoring` was **not** shipped.

**Objective**: Make every number CoreSentinel reports traceable to a command that actually ran.
Nothing in this repository may claim PASS without an exit code behind it.

**Components**: `verification/evidence.py`, `verification/checks/`, `health/dimensions/`,
`gates/definitions.py`, `runtime/safe_exec.py`.

**Files**
- New: `coresentinel/verification/{engine,evidence}.py`, `checks/{tests,security,lint,deps,diff,build}.py`
- New: `coresentinel/runtime/safe_exec.py` — argv-list execution, no `shell=True`, `sys.executable`
  for Python, per-check timeout, output captured and digested
- Modify: `coresentinel.py` (`run_evidence_verification` → delegate), `coresentinel_score.py`,
  `coresentinel_gates.py`
- Fix: F-04 (bare `python`), F-05 (trailing flags), F-06 (`shell=True`), F-13 (dead lines)

**Storage**: none yet (JSON evidence records alongside existing ledgers).

**API / CLI**
- `verify --json` emitting the full `Evidence` record per check
- `gate run --json`
- `score` gains an `UNKNOWN` state per dimension and a `--explain` flag citing the command behind
  each score
- New exit code `2` = `INDETERMINATE` (a check could not run), distinct from `1` = failed

**Tests**
- An empty directory **must not** verify. Regression test named for F-01.
- Every dimension score must cite a command; a dimension with no runnable command reports `UNKNOWN`
  and is excluded from the mean rather than defaulted to 90.
- `checks/*` unit-tested against fixture repos: passing suite, failing suite, no suite, no git.
- Replace the tautological `test_status_thresholds` with a call into the engine.
- Interpreter-resolution test proving no code path invokes bare `python`.

**Migration**: none. **Backward compat**: `verify` keeps its human output and exit-code contract;
scores may legitimately *drop* — that is the point, and it is documented as a breaking behavioural
change in the release notes.

**Acceptance**
- [✔] Empty directory scores `UNVERIFIED` / `INDETERMINATE`, never `VERIFIED` — exit 2, coverage 0/100
- [✔] Zero hardcoded PASS remains in `verify`, `score`, `gate` — asserted *behaviourally* rather
      than by grep: `test_empty_directory_produces_no_passing_check` and
      `test_no_gate_passes_on_an_empty_directory` fail if any engine can pass without running
      something. A grep would have missed a constant reached through a variable
- [✔] Every evidence item carries `{check, command, exit_code, duration_ms, output_digest, status}`
- [✔] `score --explain` names the basis for every signal behind each of the 7 dimensions
- [✔] README, `12-health-score-protocol`, `02-quality-gates-protocol` and `14-cli-protocol`
      rewritten to match measured behaviour

---

### Phase 2 — Core Runtime & Persistence Port `[✔]`

> **Delivered 2026-08-14, released as `10.3.0`.** 580 tests green (from 477). Report in §12.
> One deviation: the package is `coresentinel_core/`, not `coresentinel/` — the Core root
> already holds `coresentinel` (the POSIX wrapper) and `coresentinel.py` (the entry point),
> and a directory cannot share a name with a file beside it. Recorded there.

**Objective**: A real runtime under the existing engines, without moving their logic yet.

**Components**: config, container, event bus, structured logging, error hierarchy, path safety,
repository ports, SQLite backend, migration runner.

**Files**: `coresentinel/runtime/*`, `coresentinel/storage/*`, `coresentinel/storage/migrations/0001_init.sql`

**Storage**: `<core>/coresentinel.db` and `<project>/.coresentinel/coresentinel.db`. Initial tables:
`schema_migrations`, `projects`, `events`, `audit_events`, `verification_runs`, `health_snapshots`.
JSON layers untouched.

**CLI**: `coresentinel doctor` gains Runtime, Storage and Config checks. `coresentinel config get|set|path`.

**Tests**: config precedence (defaults < core config < project config < env < flags); migration
idempotence and forward-only ordering; event bus delivery and handler-failure isolation; path
containment rejecting `../` escapes; both storage backends satisfying the same port contract suite.

**Migration**: `coresentinel migrate` creates the DB; nothing is moved out of JSON in this phase.
**Backward compat**: absolute — no engine behaviour changes.

**Acceptance**
- [✔] Runtime bootstraps in **0.6 ms** measured, against a 50 ms budget (CI-asserted)
- [✔] One contract suite runs against JsonStore and SqliteStore, parametrized over both
- [✔] Deleting the DB loses no memory, decision or journal data — asserted directly, and the
      schema is asserted to contain no memory/decision/journal table
- [✔] 18 events defined, uniqueness asserted, emitted through a bus whose handler failures
      cannot fail the emitter. **Rendering them via `audit --events` moves to Phase 7**, which
      owns the audit ledger — surfacing events through the v1 audit engine now would have to be
      rewritten there

---

### Phase 3 — Memory, Context Assembly & Decision Intelligence `[✔]`

> **Delivered 2026-08-14, released as `10.4.0`.** 643 tests green (from 583). Report in §12.
> One deviation: the memory engines were **not** relocated into the package. A re-export shim
> silently breaks the test isolation they depend on — demonstrated, not assumed. Recorded there.

**Objective**: Answer *"what does the agent need to know right now?"* instead of dumping the store.
Make decisions first-class and contradiction-aware.

**Components**: `memory/assembly.py`, `decisions/{schema,ledger,contradiction}.py`.

**Files**: move `_memory`/`_recall`/`_lifecycle` logic into `coresentinel/memory/` behind shims;
new assembly and decision modules.

**Storage**: ADR schema extended to 18 fields (additive, optional); ADRs become project-scopable with
Core fallback; `decision_links` table.

**CLI**
- `coresentinel context --task "Add Redis caching to product listing" [--budget 4000]`
- `coresentinel decision show ADR-042`, `decision verify --change "..."`, `decision supersede`
- `decision add` gains `--problem --context --evidence --agent --confidence --relates-to`

**Tests**: assembly returns architecture + prior Redis decisions + related patterns + relevant
incidents for the brief's worked example, and **excludes** unrelated facts; budget is never exceeded;
`decision verify` blocks a change contradicting an accepted ADR and cites it; scope resolution
(project ADRs shadow Core ADRs); v1 8-field ADRs still load and render.

**Migration**: `coresentinel migrate decisions` backfills new fields as `null`, never inventing values.
**Backward compat**: `context` with no `--task` behaves exactly as v1.

**Acceptance**
- [✔] `context --task` returns a bounded pack; budget asserted at 200/500/1500/4000 tokens, and
      asserted again against the sum of the rendered items so the estimate bounds the real text
- [✔] The brief's Redis example reproduced as a test: architecture, the prior Redis decision,
      the related pattern and the incident all retrieved; the payroll export and the PDF
      renderer excluded
- [✔] `decision verify` produces the blocking output, citing the ADR, the reason recorded at the
      time and the evidence — and exits 1, which required fixing a discarded return value
- [✔] Every v1 ADR renders unchanged; the added fields load as explicit nulls, asserted field by
      field against a real v1 record

---

### Phase 4 — Project Brain & Knowledge Graph `[✔]`

> **Delivered 2026-08-14, released as `10.5.0`.** 707 tests green (from 649). Report in §12.

**Objective**: CoreSentinel understands a project, not just its manifest files.

**Components**: `project/discovery/*` (language, framework, database, package manager, docker, CI,
tests, env, API, config, dependencies), `knowledge/{entities,relations}`.

**Storage**: `knowledge_entities`, `knowledge_relations` (typed edges, SQLite; no graph DB).

**CLI**: `coresentinel project inspect|context|list`, `coresentinel knowledge query <entity>`.

**Tests**: fixture projects per stack (Node, Python, PHP/Laravel, Go, Rust, polyglot) asserting
detection precision **and** that an absent signal yields `unknown` rather than a guess; relation
integrity (no dangling edges); discovery completes under 2 s on a 5,000-file repo.

**Backward compat**: `detect_stack` / `detect_project_type` keep their signatures and return types.

**Acceptance**
- [✔] Six stacks detected from their manifests (Node, Python, PHP, Rust, Go, Ruby), plus
      datastore, package manager, CI, container, runtime, environment, testing and API
      dimensions — ten in all
- [✔] Detection never reports a framework it cannot evidence: matched on the exact package,
      with the Laravel/Symfony and next-auth cases as named regressions
- [~] `knowledge query` traverses **project → decision → file → incident → pattern**, with
      every edge carrying its evidence. The literal `feature → controller → table` chain is
      **not** delivered: it requires inferring structure from source code, and a graph that
      guesses which controller implements which feature answers confidently and wrongly.
      Those edges exist the moment they are recorded (`decision add --relates-to`), and a
      test asserts nothing appears in the graph that nobody recorded.

---

### Phase 5 — Agent Protocol, Permissions & Orchestrator `[✔]`

> **Delivered 2026-08-14, released as `10.6.0`.** 776 tests green (from 710). Report in §12.

**Objective**: Turn 17 JSON contracts into an enforced runtime.

**Components**: `agents/{protocol,registry,permissions,planner,orchestrator}.py`.

**Storage**: `agents`, `agent_sessions`, `tasks`, `task_results`, `permissions_grants`.

**CLI**: `coresentinel agent list|show|run`, `coresentinel task run|show|list`,
`coresentinel agent permissions <name>`.

**Tests**: a read-only agent attempting a write is **denied and audited** (this is the test that
makes the README's existing claim true); result-contract validation rejects a malformed agent
response; planner produces a dependency-ordered plan; a failing agent does not corrupt task state;
permission escalation requires explicit grant.

**Backward compat**: `agent list` / `agent show` output unchanged.

**Acceptance**
- [~] `agent run` executes an agent and returns a validated `AgentResult`. **Through a
      built-in executor, not a vendor adapter** — adapters are Phase 6's deliverable, and
      five roles (Scout, Security, Tester, Reviewer, Evolver) run real CoreSentinel
      capabilities and return evidence carrying a command and an exit code. Every other role
      returns `UNSUPPORTED` rather than a fabricated success.
- [✔] All 8 permissions enforced by a sandbox, with `ALLOW` / `LIMITED(scope)` / `ASK` /
      `DENY`, path containment, and denials recorded on the result and in the audit trail
- [✔] Default permission set grants `filesystem.read` only — asserted for the default set,
      for an unregistered agent, and for every one of the 17 contracts
- [✔] The 12-role pipeline runs end to end, in dependency order, with permissions enforced
      per role and results validated before they are recorded

---

### Phase 6 — Adapters, Verification Wiring & Quality Gates `[✔]`

> **Delivered 2026-08-14, released as `10.7.0`.** 828 tests green (from 778). Report in §12.

**Objective**: Vendor-neutral *invocation*, and gates that consume Phase 1 evidence.

**Components**: `agents/adapters/{base,cli_agent,http_agent,mcp_agent}` plus per-host profiles;
`gates/pipeline.py` rewired onto the verification engine.

**CLI**: `coresentinel adapter invoke <host> --task ...`, `coresentinel verify --claim ... --json`,
gates gain Requirement and Documentation stages (10 total, ordered, v1's 8 preserved by name).

**Tests**: adapter conformance suite every adapter must pass; a mock CLI agent and mock HTTP agent
prove normalisation; gate blocking is machine-readable with reason codes.

**Backward compat**: `adapter sync` and the rules-file projection are untouched — invocation is a
new, separate capability on the same registry.

**Acceptance**
- [✔] Three transports implemented and conformance-tested — `cli`, `http`, `mcp` — proved
      against a mock CLI agent, a mock HTTP server and a mock MCP server, so no test depends
      on a vendor being installed. Four hosts declare invocation profiles; two (`claude`,
      `codex`) are present on this machine and detected
- [✔] Every gate carries a machine-readable reason code; `gate run --json | jq '.codes'`
      distinguishes `NO_TEST_RUNNER` from `TESTS_FAILED`
- [✔] `gate run --report` produces the brief's `TASK COMPLETE / FINAL STATUS: APPROVED`
      from real evidence — 5 gates PASS from executed commands on this repository, the rest
      UNKNOWN rather than assumed

---

### Phase 7 — Audit, Incidents & Security Hardening `[✔]`

> **Delivered 2026-08-14, released as `10.8.0`.** 896 tests green (from 831). Report in §12.

**Objective**: Everything important is auditable and tamper-evident; incidents become data.

**Components**: `audit/ledger.py` (hash-chained, monotonic ids), `incidents/*`, `security/*`.

**Storage**: `audit_events` with `prev_hash`/`hash`; `incidents`, `incident_links`.

**CLI**: `coresentinel audit list|show|verify`, `coresentinel incident create|show|link|resolve`.

**Tests**: chain verification detects insertion, deletion and mutation; all 12 audit subjects are
recorded; secrets are redacted from every log and audit path (property test over known credential
formats); path traversal rejected; no `shell=True` remains anywhere (CI-asserted).

**Backward compat**: v1 `audit_trail.json` is imported into the chain, with pre-chain records
marked `unverified_legacy` rather than being retro-signed — an honest boundary.

**Acceptance**
- [✔] `audit verify` detects mutation, deletion, insertion, reordering and a forged append,
      each asserted by editing the trail on disk the way an editor would
- [✔] Ids are monotonic and sequential (`AUD-000001`…), F-09 regression-tested, and 200
      consecutive records are asserted collision-free
- [✔] Incident links resolve to decisions, files, commits, tests, patterns and tasks, and
      reach the knowledge graph — a pattern links back to the incident it was learned from
- [~] **10 of 12 audit subjects recorded** in a worked run. `file_change` records only when
      an agent actually writes through the sandbox, and `deployment` has nothing to emit it
      because CoreSentinel does not deploy. Both are visible in `audit coverage` rather than
      quietly absent

---

### Phase 8 — Learning, Patterns & Controlled Evolution `[✔]`

> **Delivered 2026-08-14, released as `10.9.0`.** 940 tests green (from 899). Report in §12.

**Objective**: Close the loop incident → root cause → pattern → candidate rule → approval → rule.

**Components**: `learning/{observer,candidates,proposals,apply}`, `patterns/*`.

**Storage**: `patterns` (`PAT-NNNN`), `learning_candidates`, extended `evolution_proposals`.

**CLI**: `coresentinel pattern list|show|add`, `coresentinel evolve propose|list|approve|apply|revert`.

**Tests**: no candidate is ever auto-approved (hard regression); `evolve apply` writes the rule file
**and** snapshots it; `evolve revert` restores byte-identically; a rejected candidate does not
resurface every run.

**Acceptance**
- [✔] Full pipeline demonstrated end to end from two seeded incidents: learning → candidate
      → corroboration → proposal → approval → applied rule `AP-006` → byte-identical revert,
      run both on the CLI and as an integration test
- [✔] Human approval provably mandatory — `apply` refuses every status other than `APPROVED`,
      asserted per-status, and a refusal is asserted to write nothing
- [✔] Every applied evolution snapshots first, bumps the registry version, records its origin
      and reverts byte-identically

---

### Phase 9 — CLI Consolidation, HTTP API & MCP `[✔]`

> **Delivered 2026-08-14, released as `10.10.0`.** 999 tests green (from 940). Report in §12.
> One deviation: the CLI was **not** rewritten onto the service layer — recorded there.

**Objective**: Three surfaces over one service layer, none able to bypass governance.

**Components**: `cli/`, `api/v1/`, `mcp/server.py`. Stdlib HTTP server; FastAPI only as an optional
plugin.

**API**: `/api/v1/{projects,memory,context,decisions,agents,tasks,reviews,gates,verification,health,incidents,patterns,audit,knowledge}`.

**MCP**: the brief's 15 verbs; every call authorised, governed and audited identically to the CLI.

**Tests**: a governance-bypass suite — for each surface, prove an unaudited write is impossible;
API contract tests; MCP protocol conformance; auth required on any non-loopback bind.

**Backward compat**: all v1 CLI commands unchanged; new verbs additive; API is `v1` from birth.

**Acceptance**
- [✔] The same operation audits identically through the service layer and MCP, asserted by
      comparing the audit delta of a direct call against the same call over JSON-RPC; the
      API's writes are asserted to extend the chain and leave it intact
- [✔] A non-loopback bind without a configured token is refused at startup, with an
      `UNSAFE_BIND` code — and auto-generating a token there was removed once it was found
      to defeat the check
- [~] `coresentinel mcp` implements `initialize`, `tools/list`, `tools/call` and `ping`, and
      is asserted against protocol conformance. **It has not been mounted in a live
      MCP host** — that needs a host and a human, and a test that requires both does not
      run in CI

---

### Phase 10 — Web Dashboard `[✔]`

**Objective**: A real dashboard over real services — no mock data anywhere.

**Components**: `web/` static assets served by the Phase 9 API. No npm, no build step.

**Views**: Overview, Project, Agent, Memory, Decision, Audit, Health.

**Tests**: every view's data comes from an API endpoint (asserted — no fixture JSON in the bundle);
responsive at 360 px and 1920 px; API failure degrades visibly rather than showing stale numbers.

**Acceptance**
- [✔] Seven views, all live — each rendered in a browser against a running server
- [✔] Zero hardcoded sample data in shipped assets
- [✔] Loads and renders with the API down, showing an explicit error state

---

### Phase 11 — Observability, Performance & Production Hardening `[✔]`

> **Delivered 2026-08-14, released as `10.12.0`.** 1,294 tests green (from 1,033). Report in §12.
> One deviation: **caching, indexes and background jobs were not built.** Profiling said
> the cost was not where those would help, and building them anyway would have been
> optimising by reputation rather than by measurement. Recorded there.

**Objective**: Keep the promise that CoreSentinel reduces context waste rather than adding to it.

**Components**: `observability/*`, caching, pagination, context budgets, indexes, background jobs.

**Tests**: context assembly never exceeds its budget; a 10,000-fact store retrieves in < 200 ms;
pagination enforced on every list endpoint; no secret ever reaches a log (property test).

**Acceptance**
- [✔] Eight budgets published, each naming the measurement behind it, all asserted by
      `tests/performance/` and gated in CI as their own stage. Seven are durations with
      at least 4x headroom; the eighth is a **ratio** — the cost of an audited event into
      a 4,000-record trail over the same event into an empty one — because every
      millisecond limit describes the machine as much as the code. That ratio was
      **11.4x and climbing** before this phase and is **1.0x** after
- [✔] All 11 metric subjects declared and instrumented, with `metrics coverage` naming
      any that nothing has exercised. There are no zero-initialised counters: a subject
      nobody measured reports as never observed, on the same rule that makes an
      unmeasurable health dimension `UNKNOWN` rather than 90
- [✔] Memory bounded at four places that were unbounded: the event buffer (256), the
      metric registry (512 series, drops counted not silent), each series (five numbers
      under `__slots__`, never the samples), and repository reads (the requested page —
      reading 20 of 10,000 records held 7 MB and now holds 0.02 MB)
- [~] **Caching, indexes and background jobs were not built.** Profiling found the cost
      in a filesystem walk repeated per fact, two full file reads per append, and a
      regex pass per record whose result was then ignored. Removing those was worth
      37x on context assembly; a cache in front of them would have hidden them. Indexes
      already existed on every promoted column. A background job runner is a daemon,
      and this is a local-first CLI

---

### Phase 12 — Demo Project, Documentation & Release `[ ]`

**Objective**: Prove the whole chain, and make the documentation match the implementation.

**Components**: `demo/` reference project; the 17 required documents; `AGENTS.md`.

**Tests**: the demo **is** the reference end-to-end test — init → discover → context → memory →
decision → dispatch → modify → test → security → verify → gate → audit → learn, all asserted.

**Acceptance**
- [ ] Demo runs green in CI on all 3 operating systems
- [ ] Every documented feature exists (CI-asserted: documented commands must be in the registry)
- [ ] `AGENTS.md` explains architecture, rules, and how to add a module, adapter, test and doc
- [ ] `VERSION` → `11.0.0`; migration guide published

---

## 8. Risks

| # | Risk | Likelihood | Impact | Mitigation |
| :--- | :--- | :---: | :---: | :--- |
| R-01 | **Phase 1 makes scores drop sharply.** Projects that read 100/100 will read 62/100. This looks like a regression to a user. | High | High | Frame explicitly in release notes as *the fix*; `score --explain` shows the reason for every point; keep v1 numbers reproducible via `--legacy-scoring` for one minor version. |
| R-02 | **Scope is enormous** — 12 phases, ~34 missing capabilities. Half-finished v2 is worse than finished v1. | High | High | Every phase ships independently valuable and independently releasable. Stop after any phase and the product is coherent. No phase depends on a later one. |
| R-03 | **Refactor breaks the 436 tests**, and they are the only proof the system works. | Medium | High | Shim-first: root modules re-export, logic moves behind them. Regression gate every phase. A test may be added to, never weakened — CI-enforced by counting assertions. |
| R-04 | **Agent orchestration becomes a wrapper that adds latency without adding reliability.** | Medium | High | Orchestrator's value is permissions + evidence + audit, not prompt shuffling. If a phase cannot demonstrate a caught failure the raw agent would have shipped, it has not earned its place. |
| R-05 | **Context assembly ships more tokens than it saves** — the exact failure the brief names. | Medium | High | Hard budget, measured token counts in tests, and a benchmark comparing assembled-pack size against v1's dump. Regression if it grows. |
| R-06 | **SQLite introduction is read as reversing ADR-001.** | Medium | Medium | It is not a reversal: JSON stays canonical for human-facing knowledge. Record the split as a superseding ADR through the product's own ledger — dogfooding the exact mechanism the brief demands. |
| R-07 | **API/MCP surfaces bypass governance** by calling repositories directly. | Medium | High | Surfaces may only call services; a CI import-graph check fails the build if `api/` or `mcp/` imports `storage/`. |
| R-08 | **Security regression from new attack surface** (HTTP server, agent shell execution). | Medium | Critical | Loopback-only default; auth mandatory for any other bind; deny-by-default permissions; no `shell=True`; a dedicated security phase before any surface ships. |
| R-09 | **Dependency creep** — FastAPI, pydantic, a vector DB. | Medium | Medium | Core stays stdlib. Any dependency requires an ADR justifying it. CI asserts the core package imports with no third-party module available. |
| R-10 | **Documentation drifts from implementation again** — already true today (F-01/F-02 are documented as working). | High | Medium | CI test: every command named in the docs must exist in the registry; every `--json` key documented must appear in real output. |
| R-11 | **Windows/macOS/Linux divergence.** F-04 shows this has already bitten. | Medium | Medium | Keep the 3×3 compatibility matrix; never invoke an interpreter by name; `pathlib` throughout. |
| R-12 | **Learning engine proposes noise** and trains the user to rubber-stamp approvals. | Medium | Medium | Candidates require evidence from ≥ 2 incidents; rejected candidates are suppressed; proposal volume is itself a monitored metric. |

---

## 9. Definition of Done

**CoreSentinel v2 is complete when all of the following hold.**

> **Marked 2026-08-14 at `10.12.0`, after Phase 11.** This section went eleven phases
> without being touched, so the project's own scorecard read as though nothing had been
> built. That is the failure mode this product exists to name, committed by its plan.
>
> `[✔]` means a phase delivered it *and* the claim was re-checked against the working
> tree today. `[~]` means partly, with the gap stated. `[ ]` means not yet — including
> where I could not verify it from here, which is not the same as it being false.
>
> Marking is against the criterion **as written**. Where the implementation deliberately
> did something different and better, that is a `[~]` with the reason, not a `[✔]` —
> otherwise this list stops describing what was built.

### Truthfulness (non-negotiable)
- [✔] No score, status or gate result anywhere in the system is produced without an executed command — *Phase 1; asserted behaviourally by `test_empty_directory_produces_no_passing_check`*
- [✔] Every evidence record carries check, command, timestamp, exit code, output digest and status — *re-checked today: `verify --json` emits all six, plus `cwd`, `duration_ms`, `output_excerpt`, `weight`*
- [✔] An empty or unbuildable project cannot reach `VERIFIED` — *re-checked today: an empty directory claiming "I fixed the authentication vulnerability" returns `0/100 of the evidence budget could be executed`, no verdict*
- [✔] Unmeasurable dimensions report `UNKNOWN` and are excluded from aggregates — *Phase 1; `score --explain` names the basis for each*
- [~] ~~CI greps for hardcoded PASS constants~~ — **deliberately not done as written.** Phase 1 replaced the grep with behavioural assertions because *"a grep would have missed a constant reached through a variable."* The stronger check shipped; the literal one did not, and ticking this box would describe the weaker thing

### Capability
- [ ] All 18 modules (A–R) reach **[✔] Implemented** or carry a documented, deliberate exclusion — **§5 has not been re-run since Phase 0** and still describes the pre-Phase-1 system. Cannot be marked from a stale gap analysis; refreshing §5 is Phase 12 work
- [✔] Project brain detects ≥ 6 stacks including database, package manager, CI and container facts — *Phase 4; ten dimensions, six stacks*
- [✔] Context assembly is task-relevant and budget-bounded, proven against the brief's Redis example — *Phase 3; budget re-asserted at 200/500/1500/4000 tokens by Phase 11*
- [✔] Decision intelligence blocks a contradiction of an accepted ADR and cites it — *Phase 3; exits 1*
- [✔] Orchestrator runs the 12-role pipeline end to end with enforced permissions — *Phase 5*
- [✔] ≥ 3 real agent adapters invoke and normalise; adding a fourth needs no core change — *Phase 6; `cli`, `http`, `mcp`, conformance-tested against mocks so no test needs a vendor installed*
- [~] MCP exposes the 15 verbs, all governed and audited — 28 service operations are generated onto every surface, so the verb count is exceeded and the governance is enforced by an import-graph test. **Still never mounted in a live MCP host** (Phase 9)
- [~] Audit chain is tamper-evident and covers all 12 subjects — tamper-evidence is complete and detects mutation, deletion, insertion, reordering and a forged append. **Coverage is 10 of 12**: `file_change` records only when an agent writes through the sandbox, and `deployment` has nothing to emit it because CoreSentinel does not deploy. Both are visible in `audit coverage` rather than quietly absent
- [✔] Learning pipeline closes incident → pattern → candidate → approval → applied rule, reversibly — *Phase 8; byte-identical revert*
- [✔] Dashboard serves seven views entirely from live services — *Phase 10; zero sample data, test-enforced*

### Quality
- [✔] Test count ≥ 436 and strictly increasing; **zero tests removed or weakened** — *436 → 1,294 across eleven phases; re-checked today*
- [~] Unit, integration and end-to-end coverage for every new service — unit and integration cover every service; true end-to-end is the demo project, which is Phase 12
- [ ] The demo project is a green CI end-to-end test on 3 operating systems — Phase 12
- [ ] Full CI pipeline green across 3 OS × 3 Python versions — **not verifiable from here.** The matrix has been green, but the Performance stage added in Phase 11 has never run on it. Unticked until it does
- [✔] No `shell=True`; no path used without containment check; no secret reachable in any log — *Phase 1 removed `shell=True` (ast-asserted absent), Phase 7 added path containment, Phase 11 proved the last clause as a property over 13 credential formats × 7 writers*
- [✔] Core package imports with zero third-party modules installed — *re-checked today with an import blocker in `sys.meta_path`*

### Compatibility
- [✔] Every v1 command, alias and exit code still behaves as documented — *`tests/integration/test_cli_surface.py`; every command answers `--help`, unknown commands exit 1 with a suggestion*
- [✔] Every v1 memory file, ADR and project config loads unchanged — *Phase 3 asserted a real v1 record field by field*
- [ ] `coresentinel migrate` upgrades a v1 install with zero data loss, with a migration test proving it — migrations are forward-only, checksum-guarded and idempotent, but **no test drives a genuine v1 install through the upgrade**
- [✔] Any unavoidable break is documented, migrated, shimmed, tested and version-bumped — *the Phase 1 scoring break is the only one, and it is documented as the headline fix*

### Documentation
- [ ] All 17 required documents exist and match implementation — Phase 12
- [ ] `AGENTS.md` enables a fresh AI agent to extend the system without reading the source — Phase 12; the file does not exist
- [ ] CI fails if documentation names a command or JSON key that does not exist — Phase 12; R-10 names this as the mitigation for documentation drift, and it is not built
- [✔] README describes the system as measured, not as intended — *rewritten at Phase 1 to match measured behaviour; test counts and the command surface updated each phase since*

**Score: 18 `[✔]` · 4 `[~]` · 7 `[ ]` of 29** — counted from the marks above, not from memory.
The first draft of this line said "6 `[~]` of 31" because I totalled it by hand, which is
the entire failure this section exists to catch. The seven open items are six Phase 12
deliverables plus the CI matrix, which needs one green run with the new Performance stage.

---

## 10. Decisions Needed Before Phase 1

Three choices change the work materially. My recommendation is stated; I will proceed on the
recommendation unless directed otherwise.

1. **Scoring break (R-01).** Phase 1 will lower real-world scores substantially.
   *Recommendation*: take the break, ship `--legacy-scoring` for one minor version, document it as
   the headline fix of v11.
2. **Roadmap depth.** Phases 1–8 deliver the control plane; 9–12 deliver surfaces and polish.
   *Recommendation*: commit to 1–8 now, review before 9.
3. **Dependency posture for the API.** Stdlib `http.server` (zero dependencies, local-first) versus
   FastAPI (better ergonomics, requires uvicorn + pydantic).
   *Recommendation*: stdlib in core, FastAPI as an optional plugin — consistent with ADR-001 and
   with the brief's "no unnecessary dependencies".

---

## 11. Findings Status

| Finding | State | Closed by |
| :--- | :--- | :--- |
| F-01 `verify` fabricates 45/100 points | **[✔] fixed** | `coresentinel_evidence.py`; empty dir now INDETERMINATE exit 2 |
| F-02 `score` invents 5 of 7 dimensions | **[✔] fixed** | `coresentinel_score.py` signal model; empty dir now 0/100 CRITICAL |
| F-03 4 of 8 gates return PASS with no check | **[✔] fixed** | `coresentinel_gates.py`; manual gates now UNKNOWN |
| F-04 bare `python` in 5 shell-outs | **[✔] fixed** | `coresentinel_exec.python()`; **plus 6 more sites found in the rules payload every host reads** |
| F-05 trailing flags raise `IndexError` | **[✔] fixed** | `dangling_flag()` guard covering every command, not just the two that crashed |
| F-06 `shell=True` ×6 with interpolated paths | **[✔] fixed** | single argv-list executor; ast-asserted absent |
| F-13 33 dead blank lines | **[✔] fixed** | removed |
| F-14 tautological threshold test | **[✔] fixed** | `test_status_thresholds_come_from_the_engine` calls the engine |
| F-15 duplicated `run_cmd`/`read_json`/headers | **[~] partial** | 6 `run_cmd` definitions collapsed to 1; `read_json` and headers remain for Phase 2 |
| **F-16 scanner logs to stdout** *(new)* | **[✔] fixed** | pre-existing latent bug exposed by in-process reuse — corrupted `score --json`, latent in `review --json` |
| **F-17 scanner blind to untracked files** *(new)* | **[✔] fixed** | `git diff` cannot see a new file, so a brand-new file with a secret scanned clean and exited 0 |
| **F-07 context dumps every fact** | **[✔] fixed** | `context --task` ranks, bounds and declares truncation |
| **F-08 ADR ledger Core-global, 8 of 18 fields** | **[✔] fixed** | project-scoped ledger, 20-field additive schema, contradiction guard |
| **F-20 a flag's value read as a positional** *(new)* | **[✔] fixed** | pre-existing: `verify --claim "fixed the login bug"` targeted a directory named after the claim |
| **F-21 `decision` discarded its exit code** *(new)* | **[✔] fixed** | pre-existing: `cmd_decision` ignored the handler's return, so a contradiction exited 0 |
| **F-18 unknown-command error on stdout** *(new)* | **[✔] fixed** | prose in front of any `--json` consumer — same class as F-16 |
| **F-19 silent exception swallow in shipped source** *(new)* | **[✔] fixed** | AP-001 at STRICT_BLOCK, written by me in `Container.shutdown()` and caught by CoreSentinel's own scanner |
| F-10 `memorycore.conf` dead config | **[~] superseded** | replaced by the layered config in Phase 2; the dead file still ships and is removed in Phase 3 |
| F-15 duplicated helpers | **[~] partial** | 6 `run_cmd` → 1 (Phase 1); `read_json`/`print_header` still duplicated |
| **F-22 framework detection by substring** *(new)* | **[✔] fixed** | every Laravel project reported Symfony; `next-auth` reported Next.js |
| **Agent authority unenforced** *(Module E gap)* | **[✔] closed** | the README's read-only claim was true of a JSON file, not of the runtime |
| **F-23 unregistered value flags** *(new)* | **[✔] fixed** | F-20's recurrence: `--objective`, `--roles`, `--depth`, `--as` were read but unregistered, so `gate run --objective "..."` gated a directory named after the objective. Now asserted by a source-scanning test |
| **F-09 random audit ids** | **[✔] fixed** | `RUN-#{random}` replaced by monotonic `AUD-NNNNNN`; 200 records asserted collision-free |
| **Audit covered 1 of 12 subjects** *(Module N gap)* | **[✔] closed** | 10 recorded in a worked run; the 2 remaining are visible in `audit coverage`, not hidden |
| **Incidents were prose only** *(Module K gap)* | **[✔] closed** | `INC-NNNN` records with typed links and graph integration |
| **F-24 `approve` claimed a release it never made** *(new)* | **[✔] fixed** | printed "Versioned Change Released" while writing no rule file |
| **Patterns were prose only** *(Module L gap)* | **[✔] closed** | `PAT-NNNN` records with provenance and occurrence counts |
| **Approval applied nothing** *(Module L gap)* | **[✔] closed** | `apply` writes the rule, snapshots, versions and audits; `revert` restores byte-identically |
| **F-25 auto-token defeated the unsafe-bind refusal** *(new)* | **[✔] fixed** | `serve --host 0.0.0.0` generated a token and served anyway; found by testing the refusal and watching it not fire |
| **No API, no MCP** *(Modules G and Q)* | **[✔] closed** | 27 operations on three surfaces, generated from one catalogue |
| **P-01 context assembly resolved the project binding once per fact** *(new)* | **[✔] fixed** | 10,009 filesystem walks and 80,123 `nt.stat` calls to build one pack. Memoised, and the loop-invariant lookup hoisted out of the loop that never needed to repeat it. Context assembly over 10,000 facts: **9,525 ms → 213 ms** |
| **P-02 every append re-read the whole collection** *(new)* | **[✔] fixed** | `_next_id` called `count()` which called `all()`. Appending record N parsed records 1..N-1 |
| **P-03 the audit ledger re-read the whole trail per record** *(new)* | **[✔] fixed** | `append` → `last()` → `all()`, a second full read on top of P-02. Cost per audited event rose **11.4x** between an empty trail and one holding 4,000, still climbing. Now flat at 1.0x, CI-enforced as a ratio |
| **P-04 SQLite committed with an fsync per record** *(new)* | **[✔] fixed** | 8 ms/record made the sqlite backend *slower than the JSON one it exists to outrun* — 800 records in 5,082 ms. WAL + `synchronous=NORMAL`: **329 ms**. Still a commit per record; a crash loses nothing a process crash would not |
| **P-05 reading 20 records loaded all 10,000** *(new)* | **[✔] fixed** | `recent()` read the file and reversed it: 31 ms and 7 MB to answer a 20-record question. Bounded tail read: **0.5 ms, 0.02 MB** |
| **P-06 the event buffer grew for the life of the process** *(new)* | **[✔] fixed** | bounded ring buffer; `total_emitted` keeps the true count so the bound never misreports what it bounded |
| **P-07 recall built a token set it then ignored** *(new)* | **[✔] fixed** | `t in hay_terms or t in hay` — the second test subsumes the first, so a regex pass per record decided nothing. 11,000 of them per query. Removing it is behaviour-identical and pinned by a test |
| **P-08 redaction blanked `author`, `authority` and `tests_passed`** *(new)* | **[✔] fixed** | `pass(word|wd)?` made the suffix optional so a bare `pass` matched; `auth` matched `author` and `authority` — a decision-ledger field and a squad-contract field. The audit trail was **destroying real records to protect nothing**, and over-redaction is silent. Split into substring / whole-word / exact-key tiers, both directions pinned by 158 property tests |
| **No pagination on any list surface** *(Cross-cutting gap)* | **[✔] closed** | default 50, maximum 200, `clamped` reported rather than silently returning fewer; a test derives the requirement from the catalogue so a new list endpoint that forgets to page fails the day it is added |
| **No observability** *(Cross-cutting gap)* | **[✔] closed** | 11 subjects, bounded registry, budgets, `metrics` command, doctor check |
| F-11, F-12 | [ ] open | housekeeping: leaked paths in `project-labels.json`, README count |

---

## 12. Phase Reports

### Phase 11 — Observability, Performance & Production Hardening

```text
Phase                : 11 — Observability, Performance & Production Hardening
Implemented          : Eleven measured subjects, eight published budgets gated in CI,
                       pagination on every list surface, and eight performance defects
                       closed — every one of them found by measurement, none by reading.
Files changed        : 7 added (observability/{__init__,metrics,budgets}.py,
                       migrations/0006_metrics.sql, tests/performance/{test_budgets,
                       test_pagination,test_metrics,test_no_secret_reaches_a_log}.py)
                       15 modified (coresentinel.py, _memory, _recall, _context, _init,
                       _doctor, runtime/{container,config,events,logging},
                       storage/{ports,json_store,sqlite_store}, audit/ledger,
                       services/facade, security/redaction, conftest, CI, VERSION,
                       README, 14-cli, 30-selftest, 45-performance)
Tests added          : +261 (1,033 → 1,294). Zero removed. Two of my own corrected
                       before they were trusted — see below.
Tests passed         : 1,294 / 1,294 (187s), 1 skipped (symlink creation unavailable
                       on this platform). Validator exit 0, doctor exit 0.

Measured, before and after — median of repeated runs, isolated stores:

   recall over 10,000 facts            179.4 ms  ->    39.7 ms     4.5x
   context assembly over 10,000 facts  9,525 ms  ->     213 ms      45x
   append 800 records (json)           1,869 ms  ->     465 ms       4x
   append 800 records (sqlite)         5,082 ms  ->     329 ms      15x
   newest 20 of 10,000 (json)           31.1 ms  ->     0.5 ms      62x
   heap for that same read                7 MB   ->   0.02 MB     350x
   audited event into a 4,000-record trail:
                                       72.40 ms  ->    1.34 ms      54x
   ...and the shape of that last one is the point:

     records already in the trail       BEFORE      AFTER
     0                                  6.37 ms    1.34 ms
     1,000                             26.51 ms    1.29 ms
     4,000                             72.40 ms    1.34 ms

Known limitations    : - Budgets in milliseconds describe the machine as much as the
                         code. They carry 4x headroom or more so a loaded CI runner
                         does not fail the build for being busy, which means they
                         would not catch a 2x regression. The scaling ratio would.
                       - Filtering the audit trail by subject still walks the whole
                         collection. The port exposes append and read-back, not
                         query-by-column, and pushing a WHERE clause into it would
                         stop the two backends being interchangeable. Unfiltered
                         reads — what every surface issues by default — touch only
                         the page.
                       - Paging a JSON ledger (decisions, patterns, incidents) bounds
                         the response, not the read. Those are human-scale by ADR-001
                         and are read whole by design. Said plainly rather than left
                         to look like the storage-backed paging beside it.
                       - `find_project_root` now caches. A long-lived process that
                         binds a project externally would hold the stale answer until
                         something calls reset. `init` calls it; the test suite clears
                         it around every test; a server does neither yet.
                       - Metrics are flushed at shutdown. A process killed with
                         SIGKILL loses its series. They are measurements, not records,
                         and the audit trail — which is a record — is written as it
                         happens.
                       - No cross-run trend or alerting. `metrics` reports what is
                         recorded; deciding that a number moved is still a human
                         reading two numbers.
Architecture decisions:
   - Measure first, and keep the harness honest. The first version of the benchmark
     ran under tracemalloc, which instruments every allocation and inflated its own
     timings roughly 5x — it reported recall at 197 ms against a 200 ms budget when
     the real figure was 40 ms. The second version wrote every run's events into the
     repository's own record store, so each measurement was taken against a file the
     previous ones had grown. Both were caught by numbers that did not make sense,
     and both would have put a fabricated figure into a report about not fabricating
     figures. Timing and memory are now separate passes against isolated stores.
   - Caching, indexes and background jobs were planned and NOT built. Profiling put
     the cost in a filesystem walk repeated once per fact, two whole-file reads per
     append, and a regex pass per record whose result was then discarded by the line
     below it. Those are defects, not slowness; a cache in front of them would have
     preserved them and hidden them. Indexes already existed on every promoted
     column. A background job runner is a daemon, and this is a local-first CLI.
   - One budget is a ratio rather than a duration, and it is the one that matters.
     Every millisecond limit moves when the hardware does. `audit.append_scaling_ratio`
     asserts that writing record 4,000 costs no more than writing record 1, which is
     true or false regardless of how fast the machine is, and is exactly the property
     whose absence made the audit trail quadratic.
   - Metrics inherit the verification engine's rule: no zero-initialised counters. A
     subject nothing exercised reports as never observed, because a zero is a
     measurement and nobody took one. `metrics coverage` is modelled on
     `audit coverage` for the same reason — absence that is visible is a gap, absence
     that is silent reads as a pass.
   - The pagination test derives its requirement from the service catalogue rather
     than from a list of endpoint names. Four operations are exempt because their
     length comes from a fixed enumeration, and each exemption is recorded with its
     reason and re-checked. A new list operation that forgets to page fails the day
     it is added, not the day someone notices.
   - Two of my own tests were wrong and were corrected rather than deleted: one
     asserted `session_count` should survive redaction when the rule as written
     redacted it, and one asserted a blanket "no unpaged list endpoints" that fired
     correctly on four fixed enumerations. Both were fixed by making the rule more
     precise, which is what found P-08.
   - Released as 10.12.0. The major bump stays reserved for v2 completion.
Next phase           : 12 — Demo Project, Documentation & Release
```

---

### Phase 1 — Evidence Integrity

```text
Phase                : 1 — Evidence Integrity
Implemented          : Verification, health scoring and quality gates rebuilt on executed
                       commands. Shared safe-execution layer. 7 defects closed, 2 new ones
                       found and closed.
Files changed        : 3 added (coresentinel_exec.py, coresentinel_evidence.py,
                       tests/security/test_safe_execution.py)
                       11 modified (coresentinel.py, _score, _gates, _context, _doctor,
                       _review, _adapters, sentinel-validator, README, 3 protocols, CI, VERSION)
Tests added          : +41 (436 → 477). Zero removed. 3 corrected — they asserted the
                       fabricated behaviour and are named for what they now prove.
Tests passed         : 477 / 477 (18.2s). validator exit 0, review APPROVED,
                       compileall clean, all sources parse under the Python 3.9 grammar.
Known limitations    : - Verification depends on tools being installed; a machine without a
                         linter or audit tool legitimately reports UNKNOWN rather than failing.
                       - The 50/100 coverage floor is a judgement call, not a derived constant.
                       - Architecture and Documentation signals are filesystem observations,
                         not commands. They state that basis; they are the weakest dimensions.
                       - F-15 only partly closed: read_json and print_header are still
                         duplicated across engines. Phase 2 owns them.
Architecture decisions:
   - New modules are flat coresentinel_*.py, not the coresentinel/ package Planning.md
     specified. A package directory shadows coresentinel.py on import (packages win over
     modules), breaking `import coresentinel as cli`, and conftest's sandbox fixture copies
     only top-level files, which would break all 144 integration tests. Phase 2 does the
     package migration and updates the fixture in the same change.
   - --legacy-scoring was NOT shipped, reversing the §10 recommendation. Keeping a
     fabricating code path alive behind a flag reintroduces exactly what this phase removes,
     and it would be used in CI to preserve a green number. --explain gives users what they
     actually need: the reason each number is what it is.
   - UNKNOWN is a first-class result across all three engines, excluded from denominators
     rather than defaulted to a pass. Exit code 2 (INDETERMINATE) is now distinct from 1.
   - Released as 10.2.0, not 11.0.0 — Planning.md reserves the major bump for v2 completion.
     The behavioural break is documented rather than silent.
Next phase           : 2 — Core Runtime & Persistence Port
```

### Phase 10 — Web Dashboard

```text
Phase                : 10 — Web Dashboard
Implemented          : A seven-view dashboard served by the Phase 9 API from an
                       allowlist of three files — no npm, no build step, no
                       framework, no sample data. Every panel reads /api/v1 and
                       says so in place when it cannot.
Files changed        : 5 added (web/__init__.py, index.html, app.css, app.js,
                       tests/surfaces/test_dashboard.py) · 6 modified
                       (api/server.py, coresentinel.py, README, 16-api-protocol,
                       14-cli-protocol, 30-selftest-protocol, VERSION)
Tests added          : +33 (999 → 1032). Zero removed, two of my own corrected
                       before they were trusted.
Tests passed         : 1032 / 1032 (45.7s). Validator exit 0. Seven views also
                       verified by hand in a browser against a live server.
Known limitations    : - Read-only. Nothing on the page writes: no gate run, no
                         decision record, no evolution approval. Those are
                         consequential acts and a mouse is a poor audit trail.
                       - No auto-refresh, no streaming. The page fetches when you
                         load it or press Refresh. A polling dashboard on a
                         single-threaded server is a way to make a governance tool
                         the reason a machine is busy.
                       - Assets are served before authorisation, so the HTML, CSS
                         and JS are readable by anyone who can reach the port. They
                         contain no project data — the data still requires the API,
                         and off-loopback reads still require the token.
                       - The offline banner covers the API dying while the page is
                         open. If the server is already down the page cannot load
                         at all, because the server is what serves it.
                       - Verified in one browser (Chrome) at two widths. No
                         cross-browser matrix, no screen-reader audit.
                       - Presentation is untested by machine. The tests assert the
                         boundary, the allowlist and the absence of fixtures; that
                         a panel renders legibly was checked by eye.
Architecture decisions:
   - The dashboard is a client of /api/v1, never of the engines. It was the easiest place
     in the whole system to cheat — read the JSON files directly and skip a network hop —
     and cheating there would have quietly created a fifth surface with no audit story.
   - An allowlist, not a static directory. Three filenames resolve and nothing else does,
     so the asset route cannot be walked into a file read. `..` is a 404 by construction
     rather than by sanitising.
   - Every operation the page calls is a read, asserted by a test against the catalogue's
     own mode flags. The dashboard shows the system; it does not drive it.
   - No sample data, enforced rather than intended: a test strips the tags from each view
     and requires what is left to be empty. A fixture behind a view renders beautifully
     while the thing it claims to show is broken, which is the exact failure this product
     exists to name.
   - A failed panel renders its failure where its number was, and the page never keeps a
     stale figure. Same rule the engines keep — a check that cannot run is UNKNOWN, not a
     pass — applied to pixels.
   - Each view declares its operations in data-endpoints, and a test checks them against
     the catalogue. A renamed operation now fails the build instead of failing silently in
     a browser nobody had open.
Next phase           : 11 — Observability, Performance & Production Hardening
```

---

### Phase 9 — CLI Consolidation, HTTP API & MCP

```text
Phase                : 9 — CLI Consolidation, HTTP API & MCP
Implemented          : A service layer with 27 operations; a versioned stdlib HTTP API
                       generated from it; an MCP server generated from the same
                       catalogue; and an import-graph test enforcing that neither
                       surface can reach past it.
Files changed        : 8 added (5 package modules, 3 test modules) · 6 modified
                       (coresentinel.py, config, README, 3 protocols, VERSION)
Tests added          : +59 (940 → 999). Zero removed, zero corrected.
Tests passed         : 999 / 999 (42.8s). Validator exit 0, review APPROVED,
                       doctor exit 0, Python 3.9 grammar clean.
Known limitations    : - The CLI still calls engines directly. It predates the service
                         layer, has 900+ tests behind it, and rewriting working code to
                         route through a facade would risk a great deal for no behaviour
                         change. The bypass guarantee is enforced on the two NEW surfaces,
                         which are the ones that could have been built wrong.
                       - `http.server` is single-threaded unless --threaded, and is not a
                         production web server. Local-first was the trade.
                       - Auth is a single shared token. No per-caller identity, no scopes,
                         no rotation. Enough for a local control plane; not enough for a
                         multi-user deployment, and the API should not be exposed as one.
                       - MCP has never been mounted in a live host. Conformance is asserted
                         against the protocol, not against an implementation of it.
                       - The service layer wraps engines rather than owning the logic, so a
                         few operations reimplement a little of what the CLI renders
                         (gate.run is the clearest).
Architecture decisions:
   - Routes and MCP tools are GENERATED from the service catalogue. An operation appears
     on every surface at once or on none, which removes the drift where a CLI verb exists
     for a year before the API grows one.
   - The import-graph test is the enforcement. A convention that surfaces "should" call
     services is a convention somebody breaks under deadline; a failing build is not.
   - A write requires the token on every interface, including loopback. A local server is
     reachable by every process on the machine, and "it's only localhost" is how a control
     becomes a formality.
   - A non-loopback bind will not auto-generate a token. Doing so satisfies the check while
     still putting a server on the network whose token nobody had a chance to distribute —
     found by testing the refusal and watching it not fire.
   - An MCP service refusal is a tool result with isError, not a JSON-RPC error. The model
     needs to read why it was refused and act on it, which a protocol error code prevents.
   - stdout carries MCP frames only. One stray print corrupts the stream and the host
     reports a protocol error rather than the message that caused it.
Next phase           : 10 — Web Dashboard
```

---

### Phase 8 — Learning, Patterns & Controlled Evolution

```text
Phase                : 8 — Learning, Patterns & Controlled Evolution
Implemented          : Pattern library as data; a learning observer with an evidence
                       threshold; and the missing half of controlled evolution —
                       apply and revert.
Files changed        : 8 added (5 package modules, 1 SQL migration, 1 test module,
                       2 package inits) · 9 modified (coresentinel.py, _evolve,
                       ports, sqlite_store, .gitignore, README, 4 protocols, VERSION)
Tests added          : +41 (899 → 940). Zero removed, zero corrected.
Tests passed         : 940 / 940 (31.0s). Validator exit 0, review APPROVED,
                       doctor exit 0, Python 3.9 grammar clean.
Known limitations    : - `apply` supports three targets. Any other governance file is
                         refused rather than patched, which is the safe answer but
                         means most protocol changes are still manual.
                       - Candidate matching is a sorted-token fingerprint. Two wordings
                         of one lesson collide correctly; two genuinely different
                         lessons sharing vocabulary would also collide.
                       - The observer reads incidents, failures and patterns. It does
                         not read review findings or verification failures, both of
                         which are plausible sources and neither of which is wired.
                       - Nothing proposes automatically. A corroborated candidate still
                         needs a human to write the proposal — deliberate, but it means
                         the loop is not closed without a person at two points.
                       - `MIN_EVIDENCE = 2` is a judgement call, not a derived constant.
Architecture decisions:
   - A candidate needs two distinct sources before it may be proposed, and the same
     source cannot corroborate itself. One incident is an anecdote; a system that turns
     every anecdote into a rule produces a rulebook nobody reads.
   - Rejection is permanent. Resurfacing a declined lesson on every observation run is
     how a review queue becomes noise, and noise is how a control stops working.
   - Approval and application are separate acts. `approve` records a human decision and
     changes no file; it previously printed "Versioned Change Released" while writing
     nothing, which was a claim about a file it never touched.
   - A newly applied rule is recorded at WARNING, never STRICT_BLOCK. Promotion to
     blocking is its own decision, once the rule has proved itself.
   - An unsupported change shape is refused, not attempted. Blindly patching a governance
     file because a proposal asked is the failure this protocol exists to prevent.
   - The pattern library stays a JSON file, not a SQLite table. A `patterns` index table
     was written and removed: the ADR-001 boundary test from Phase 2 caught it, nothing
     needs the index yet, and relaxing a test in order to cross the boundary it guards is
     exactly the move this project keeps refusing.
   - Recording a pattern again counts an occurrence and does not raise confidence — the
     same rule the memory consolidator uses.
Next phase           : 9 — CLI Consolidation, HTTP API & MCP
```

---

### Phase 7 — Audit, Incidents & Security Hardening

```text
Phase                : 7 — Audit, Incidents & Security Hardening
Implemented          : Hash-chained append-only audit ledger over twelve subjects,
                       wired through the event bus; incident records with typed links
                       and knowledge-graph integration; redaction consolidated into
                       one implementation shared by the logger and the ledger.
Files changed        : 9 added (6 package modules, 1 SQL migration, 2 test modules)
                       · 11 modified (coresentinel.py, container, orchestrator,
                       logging, ports, sqlite_store, knowledge/graph, README,
                       3 protocols, VERSION, 1 test corrected)
Tests added          : +65 (831 → 896). Zero removed. 1 corrected — it pinned the
                       ad-hoc subject string "agent_run" that predated the twelve.
Tests passed         : 896 / 896 (32.1s). Validator exit 0, review APPROVED,
                       Python 3.9 grammar clean.
Known limitations    : - Tamper-evidence, not tamper-proofing. Anyone with write access
                         can recompute the whole chain; what they cannot do is change
                         one record and leave the rest intact. Notarising externally
                         would close that and is not in scope.
                       - `deployment` has no emitter because nothing deploys. The
                         subject is declared and reported as never-recorded rather
                         than dropped.
                       - The JSON backend recomputes the chain tail on every append
                         (O(n) per record). Fine at present volume; the SQLite backend
                         has the index for it and Phase 11 owns the switch.
                       - Redaction is pattern-based. It catches the credential shapes
                         it knows and cannot catch a secret that looks like prose.
                       - Incident severity and root-cause class are recorded, not
                         derived. Nothing infers them from the incident text.
Architecture decisions:
   - Auditing is wired through the event bus rather than by calling the ledger from a
     dozen sites. Emitting an event is how something gets audited, so a subsystem added
     later either emits and is recorded, or does not and appears as an unrecorded subject
     in `audit coverage`. The gap is visible instead of silent.
   - Records written straight to the collection are counted and reported as `unchained`
     rather than treated as chain breaks. A record that was never signed has not been
     tampered with — it was never protected, and that is a different fact. Phase 5's
     orchestrator was rewritten to write through the ledger once this surfaced.
   - v1 records are imported and listed as `unverified_legacy`, never retro-signed.
     Hashing them now would assert an integrity that never existed.
   - Redaction happens before the write and before the hash, so a redacted record still
     verifies. One implementation, imported by both the logger and the ledger, because
     two copies would eventually disagree about what a secret is.
   - An audit failure is logged loudly and never fails the operation being audited. A
     governance tool that breaks the work because it could not describe the work is a
     governance tool people switch off.
   - An incident's `learning` is a first-class field and its absence is reported. The fix
     stops it now; the learning is what stops it recurring, and it is the input Phase 8
     turns into a pattern and then a candidate rule.
Next phase           : 8 — Learning, Patterns & Controlled Evolution
```

---

### Phase 6 — Adapters, Verification Wiring & Quality Gates

```text
Phase                : 6 — Adapters, Verification Wiring & Quality Gates
Implemented          : Agent invocation over three transports with a conformance
                       contract; quality gates rewired onto the evidence engine with
                       two new stages and machine-readable reason codes.
Files changed        : 7 added (5 adapter modules, 2 test modules) · 9 modified
                       (coresentinel.py, _gates rewritten, adapters.json,
                       squad-contracts.json, README, 3 protocols, VERSION,
                       2 existing test modules corrected for the 10-stage pipeline)
Tests added          : +50 (778 → 828). Zero removed. 2 corrected — they pinned the
                       8-stage pipeline and the 3-tuple gate return.
Tests passed         : 828 / 828 (29.4s). Validator exit 0, review APPROVED,
                       doctor exit 0, Python 3.9 grammar clean.
Known limitations    : - No test invokes a real vendor. `claude` and `codex` are detected
                         here, but a suite that needs a paid API and a login is a suite
                         that does not run in CI. Normalisation is proved against mocks.
                       - A text-mode response yields a summary and nothing structured.
                         Claims are only itemised when a host emits JSON, and none of the
                         shipped profiles do by default.
                       - The MCP client is initialize + tools/call. It is not a full MCP
                         implementation and does not try to be.
                       - The Documentation gate compares changed file suffixes. It cannot
                         tell whether the documentation that changed describes the code
                         that changed.
                       - Adapter invocation does not yet feed the orchestrator: `task run`
                         still uses built-in executors only. Wiring UNSUPPORTED roles to
                         adapters is the obvious next step and was not in this phase.
Architecture decisions:
   - An invocation's only evidence is the invocation. Everything the agent says about what
     it did is recorded under `claims`, never `evidence`. Turning "I added tests" into
     evidence of tests would reintroduce at the vendor boundary the exact fabrication
     Phase 1 removed from the middle of the product.
   - Invocation is permission-gated through the Phase 5 sandbox: cli/mcp consume
     shell.execute, http consumes network.access. No contract grants network access, and
     only four contracts may delegate to a host binary at all — declared in the scope list
     so `agent permissions` shows it.
   - `{prompt}` is substituted as one argv element. An objective containing a quote or a
     semicolon is a normal objective, not an injection.
   - The original eight gate names and their order are preserved exactly. Requirement was
     added at the front and Documentation before Deployment; nothing was renamed.
   - Reason codes are stable identifiers, asserted to match [A-Z][A-Z0-9_]* and asserted to
     be declared. A CI job branching on prose breaks the first time wording improves.
Next phase           : 7 — Audit, Incidents & Security Hardening
```

---

### Phase 5 — Agent Protocol, Permissions & Orchestrator

```text
Phase                : 5 — Agent Protocol, Permissions & Orchestrator
Implemented          : AgentTask/AgentResult protocol with validation, an 8-permission
                       model enforced by a sandbox, explicit permissions on all 17
                       contracts, five built-in agents, a planner and an orchestrator.
Files changed        : 11 added (7 package modules, 1 SQL migration, 2 test modules,
                       1 package init) · 7 modified (coresentinel.py, _doctor,
                       squad-contracts.json, ports, sqlite_store, README, 2 protocols)
Tests added          : +66 (710 → 776). Zero removed, zero corrected.
Tests passed         : 776 / 776 (25.4s). Validator exit 0, review APPROVED,
                       Python 3.9 grammar clean.
Known limitations    : - Seven of twelve roles have no executor. They report UNSUPPORTED
                         honestly, but the orchestrator's value is bounded until Phase 6
                         binds adapters.
                       - `ASK` is approved by a constructor flag, not a prompt. There is no
                         interactive approval surface yet; --interactive means "assume the
                         human said yes", which is only safe under supervision.
                       - The sandbox mediates what an agent asks it for. A built-in that
                         imported `os` directly would bypass it — the boundary holds for
                         agents that go through the protocol, which is every adapter-driven
                         agent, but it is not an OS-level jail.
                       - Permission grants are not yet persisted to permission_grants; the
                         table exists and Phase 7 owns the audit ledger that fills it.
                       - The planner is a fixed pipeline, not a decomposition. It selects
                         and orders roles; it does not break an objective into subtasks.
Architecture decisions:
   - The permission block lives in squad-contracts.json as data, authored explicitly.
     Deriving permissions from the prose `authority` string at runtime was considered and
     rejected: that is the guessing this project keeps removing, and a parser that
     mis-reads "Read-only file inspection" grants a write.
   - An agent is handed a sandbox, never the filesystem. A permission that is checked at
     the point of use is enforced; one that is documented is a hope.
   - LIMITED with no declared scope grants nothing. Defaulting it to "everything" would
     make the safest-looking level the widest one in the system.
   - UNSUPPORTED is a first-class status and does not stop the pipeline. Nothing went
     wrong when a capability is simply absent — the same rule as UNKNOWN in verification
     and `unknown` in discovery.
   - A COMPLETED result carrying neither evidence nor actions is rejected by validation.
     That is exactly the claim CoreSentinel exists to refuse, and accepting it because it
     arrived in a well-formed envelope would put an unverifiable claim in the audit trail.
   - Escalation to git.push, deployment or production.access requires a stated reason, and
     no contract holds any of them by default.
Next phase           : 6 — Adapters, Verification Wiring & Quality Gates
```

---

### Phase 4 — Project Brain & Knowledge Graph

```text
Phase                : 4 — Project Brain & Knowledge Graph
Implemented          : Evidence-based discovery across ten dimensions, and a knowledge
                       graph built only from recorded relationships. Two new CLI
                       commands, two new storage collections, migration 0002.
Files changed        : 11 added (7 package modules, 1 SQL migration, 2 test modules,
                       1 package init) · 6 modified (coresentinel.py, ports,
                       sqlite_store, README, 14-cli-protocol, VERSION)
Tests added          : +58 (649 → 707). Zero removed, zero corrected.
Tests passed         : 707 / 707 (23.7s). Validator exit 0, review APPROVED,
                       Python 3.9 grammar clean. Discovery: 2,000 files in under 2s.
Known limitations    : - Framework tables are hand-maintained. An unlisted framework is
                         reported as unknown rather than guessed, which is the right
                         failure but still a gap that grows as ecosystems move.
                       - The TOML reader handles the two dependency shapes that matter,
                         not TOML. tomllib needs Python 3.11 and the floor is 3.9.
                       - API surface detection counts controller files by filename and
                         path keys by regex. Both are declared lower bounds, not parses.
                       - The graph holds no code-level entities (function, class, table),
                         so a feature-to-table chain only exists where someone recorded it.
                       - Discovery is not cached; every call re-scans. ~50ms on this
                         repository, bounded at 20,000 files, addressed in Phase 11.
Architecture decisions:
   - Detection reads structured manifest keys, never raw file text. Measured first:
     v1 reported ['Laravel', 'Symfony'] for a Laravel project because Laravel depends on
     symfony/console, and ['Next.js', 'Vue', 'React'] for a project whose only matches
     were next-auth, eslint-plugin-vue and @types/react.
   - Every finding carries the file and locator that proves it, and a dimension nothing
     evidenced reports `unknown`. Empty and unknown are different facts and only one of
     them is safe to act on — the same rule Phase 1 applied to verification.
   - Source file extensions count as evidence for a language. A tree of .py files is a
     Python project whether or not anyone wrote a manifest; three files is the floor, so
     a stray script does not declare a stack.
   - Driver dependencies are recorded at 0.6 confidence and say so: a driver proves the
     project *can* reach an engine, not that it does. A compose service image proves it.
   - .env files are read for key names only. The values are the secrets this product
     exists to protect.
   - No graph database. Relationships number in the hundreds, are already stored, and the
     graph rebuilds in tens of milliseconds — so `knowledge query` always rebuilds and a
     superseded decision can never linger in an answer. The persisted snapshot exists for
     consumers that cannot rebuild it themselves.
   - Nothing is inferred from source code. An edge exists because a discovery finding, a
     decision or a memory layer recorded it, and a test asserts an unrecorded controller
     never appears in the graph.
Next phase           : 5 — Agent Protocol, Permissions & Orchestrator
```

---

### Phase 3 — Memory, Context Assembly & Decision Intelligence

```text
Phase                : 3 — Memory, Context Assembly & Decision Intelligence
Implemented          : Task-relevant context assembly (F-07) and decision intelligence —
                       20-field additive schema, project-scoped ledger, contradiction
                       guard, supersession (F-08). Two pre-existing CLI defects fixed.
Files changed        : 7 added (4 package modules, 2 test modules, 1 rewritten protocol)
                       8 modified (coresentinel.py, _recall, README, 2 protocols,
                       test_cli_surface, VERSION)
Tests added          : +59 (584 → 643). Zero removed. 1 corrected — it asserted that a flag's
                       value should be read as a positional argument, which is the defect.
Tests passed         : 643 / 643 (20.7s). Validator exit 0, review APPROVED.
Known limitations    : - Contradiction detection is lexical, not semantic. It cannot tell that
                         ADR-001's "Redis" (rejected as a memory store) is unrelated to a task
                         about a product cache. Biased toward flagging by design, and every
                         finding cites the ADR so dismissal is cheap — but it will produce
                         false positives on repositories with overlapping vocabulary.
                       - The token budget is an estimate (characters/4), labelled as one
                         everywhere. It bounds what is assembled, not what a model will count.
                       - Section share ceilings are judgement calls, not derived from data.
                       - Assembly re-reads every layer per call; no caching yet. Fine at
                         current volume, addressed in Phase 11.
                       - The memory engines still do not read runtime config, so the Phase 2
                         DEFAULTS and the engine constants can still drift.
Architecture decisions:
   - The memory engines were NOT moved into the package. Planning specified it; a minimal
     repro showed a re-export shim breaks the isolation the fixtures depend on — patching
     MEMORY_DIR on the shim has no effect on what the function reads, so the suite would
     write to the real memory/ directory. That is the incident 30-selftest-protocol.md
     records the fixtures as existing to prevent. Moving them needs sys.modules aliasing or
     a fixture rewrite, neither of which belongs in the same change as new behaviour.
   - The decision ledger resolves to ONE store, not a union of project and Core. Unioning
     was built, tested against a real project, and reverted: CoreSentinel's own ADRs about
     its memory architecture fired on an unrelated project's Redis work. That is F-08 in a
     new guise — one repository's decisions presented as governance for another — and the
     noise would train users to skip the check.
   - CONTRADICTS and REVISITS block; TOUCHES does not. A check that blocks ordinary work on
     a governed component is a check people route around.
   - Generic words (database, service, system, store) never trigger a finding alone.
   - Truncation is always declared. A pack that silently drops its best excluded item teaches
     the reader to trust it when it should not.
Next phase           : 4 — Project Brain & Knowledge Graph
```

---

### Phase 2 — Core Runtime & Persistence Port

```text
Phase                : 2 — Core Runtime & Persistence Port
Implemented          : coresentinel_core/ package. Runtime (config, paths, logging,
                       events, container, errors) and storage (ports, JSON + SQLite
                       backends, forward-only migrations). Two new CLI commands and
                       two new doctor subsystems.
Files changed        : 14 added (11 package modules, 1 SQL migration, 2 test modules)
                       7 modified (coresentinel.py, _doctor, conftest, test_cli_surface,
                       .gitignore, VERSION, README + 2 protocols)
Tests added          : +106 (477 → 583). Zero removed. 1 renamed — the doctor subsystem
                       set grew from 7 to 9, so the test name no longer said "seven".
                       2 broadened to accept stderr, where the diagnostics now correctly go.
Tests passed         : 583 / 583 (20.4s). Bootstrap measured at 0.6 ms. Validator exit 0,
                       review APPROVED, 12 --json contracts parse, Python 3.9 grammar clean.
Known limitations    : - Nothing consumes the runtime yet beyond doctor, config and
                         migrate. The engines still resolve their own paths and constants;
                         Phase 3 onward migrates them in behind shims.
                       - DEFAULTS duplicates constants that still live in the engines
                         (pass_threshold, compact_budget, decay rate). Both are correct
                         today but they can drift until the engines read from config.
                       - No event is emitted by an existing engine yet — the bus is built
                         and tested, not yet wired into memory/decision/gate paths.
                       - The JSON backend recounts a file to allocate the next id, which is
                         O(n) per append. Fine at current volume, replaced when it isn't.
Architecture decisions:
   - Package is coresentinel_core/, not coresentinel/. The Core root already contains
     `coresentinel` (the POSIX wrapper that puts the CLI on PATH) and `coresentinel.py`
     (the entry point every wrapper, CI job and test fixture invokes). A directory cannot
     share a name with a file beside it, and renaming either breaks the documented command
     surface. This also removed the need to move the CLI, so Phase 2 kept its stated
     objective: a runtime under the engines without moving their logic.
   - ADR-001 is scoped, not reversed. JSON stays canonical for memory, decisions and the
     journal — the knowledge a human reads, commits and diffs. SQLite holds only
     append-heavy machine records. A test asserts the schema contains no memory, decision
     or journal table, so the boundary cannot erode silently.
   - Migrations are forward-only with checksums. Editing an applied migration is refused,
     because from that moment the database and the file disagree and nothing says so.
     There is no rollback: the reverse of a bad migration is a new migration.
   - Every setting reports the layer that produced it. A value whose origin you cannot see
     is a value you will eventually misattribute to the wrong file.
   - Event handlers are isolated. An observer must never be able to fail the operation it
     observed, or adding an audit listener becomes a way to break governance.
   - The scanner is now pointed at CoreSentinel's own source in the test suite. It caught a
     STRICT_BLOCK anti-pattern I had just written; a governance tool exempt from its own
     rules is the failure this product exists to name.
Next phase           : 3 — Memory, Context Assembly & Decision Intelligence
```

---

## 13. Phase 0 Report

```text
Phase                : 0 — Repository Analysis & Planning
Implemented          : Planning.md (this document). No code changed.
Files changed        : 1 added (Planning.md). 0 modified.
Tests added          : 0
Tests passed         : 436 / 436 (baseline verified locally, 14.37s)
Known limitations    : 15 findings recorded in §4; F-01..F-04 are blocking product defects
                       and are the entire content of Phase 1.
Architecture decisions:
   - Phase order deviates from the brief: Evidence Integrity precedes Core Runtime,
     because every downstream subsystem consumes verification and health numbers that
     are currently fabricated.
   - No rewrite. The 16 root modules become re-export shims; logic migrates behind them.
   - ADR-001 (file-based JSON) is preserved for human-facing knowledge and scoped, not
     reversed, by adding SQLite for high-volume machine-facing records.
   - Core remains stdlib-only. Every third-party dependency requires its own ADR.
Next phase           : 1 — Evidence Integrity
```
