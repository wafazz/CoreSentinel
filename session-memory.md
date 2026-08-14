# Session Memory - CoreSentinel
> Last updated: 2026-08-14 07:25

## Session Context
- **Project**: CoreSentinel — AI Engineering Control Plane
- **Profile**: `~/Desktop/MemoryCore Project/Projects/50-coresentinel.md`
- **Branch**: main (v10.11.0; Phases 1–10 committed and pushed — `153d8eb`, `f8aff36`)
- **Status**: active
- **Focus**: v1 → v2 transformation. Phases 0–10 complete; Phase 11 (Observability & Hardening) is next.

## Current Tasks
- [✔] Phase 0 — full repository inspection, gap analysis, `Planning.md`
- [✔] Phase 1 — Evidence Integrity (released 10.2.0, 477 tests green)
- [✔] Phase 2 — Core Runtime & Persistence Port (released 10.3.0, 583 tests green)
- [✔] Phase 3 — Memory, Context Assembly & Decision Intelligence (released 10.4.0, 643 tests green)
- [✔] Phase 4 — Project Brain & Knowledge Graph (released 10.5.0, 707 tests green)
- [✔] Phase 5 — Agent Protocol, Permissions & Orchestrator (released 10.6.0, 776 tests green)
- [✔] Phase 6 — Adapters, Verification Wiring & Quality Gates (released 10.7.0, 828 tests green)
- [✔] Phase 7 — Audit, Incidents & Security Hardening (released 10.8.0, 896 tests green)
- [✔] Phase 8 — Learning, Patterns & Controlled Evolution (released 10.9.0, 940 tests green)
- [✔] Phase 9 — CLI Consolidation, HTTP API & MCP (released 10.10.0, 999 tests green)
- [✔] Phase 10 — Web Dashboard (released 10.11.0, 1032 tests green)
- [ ] Phases 11–12 — see `Planning.md` §7

## Working Memory
### Active Context
- `Planning.md` at the Core root is the source of truth. Findings status is §11, phase reports §12.
- **1034 tests, ~47s.** `pytest` was missing again at the start of Phase 10 (a `--user` install does not survive); reinstall with `python3 -m pip install --user pytest` before believing a "No module named pytest" error means a broken suite.
- Phase 1 added `coresentinel_exec.py` (safe execution) and `coresentinel_evidence.py` (verification engine). Everything that shells out goes through `coresentinel_exec.run()` — argv lists, no shell, `sys.executable` for Python.

### Decisions Made
- **Phase order deviates from the brief**: Evidence Integrity came BEFORE Core Runtime, because `verify`/`score`/`gate` fabricated results and every downstream subsystem consumes those numbers.
- **`--legacy-scoring` was NOT shipped**, reversing the original recommendation. Keeping a fabricating code path behind a flag reintroduces exactly what Phase 1 removed, and it would be used in CI to preserve a green number. `score --explain` gives users the real need: why each number is what it is.
- **The package is `coresentinel_core/`, settled in Phase 2 on a hard constraint**: the Core root already holds `coresentinel` (the POSIX wrapper) and `coresentinel.py` (the entry point), and a directory cannot share a name with a file beside it. This also meant the CLI never had to move. `conftest.SANDBOX_PACKAGES` copies the package into every sandbox — a new package left out of that list breaks all 144 integration tests with an ImportError.
- **No rewrite.** The engines stay flat modules for now; Phase 3 onward migrates them into `coresentinel_core/` behind re-export shims so `import coresentinel_memory` keeps working.
- **ADR-001 (file-based JSON) is scoped, not reversed.** JSON stays canonical for memory/decisions/journal; SQLite only for audit, verification runs, health snapshots, knowledge relations. Record the split as a superseding ADR via `coresentinel decision add`.
- **Core stays stdlib-only.** API = stdlib `http.server`; FastAPI optional plugin only.

### Blockers / Open Questions
None blocking. Two standing choices from `Planning.md` §10 still hold: commit to Phases 1–8 and review before 9; stdlib `http.server` over FastAPI.

## Recent Changes
| File | Change | Status |
|---|---|---|
| `coresentinel_exec.py` | New — argv-list execution, no shell, `sys.executable`, Execution record with exit code/duration/digest | done |
| `coresentinel_evidence.py` | New — 6 real checks, PASS/FAIL/UNKNOWN, coverage floor, INDETERMINATE verdict | done |
| `coresentinel_score.py` | Rewritten on named signals, each stating its basis; `--explain` | done |
| `coresentinel_gates.py` | Real evaluation; manual gates now UNKNOWN; `--json` | done |
| `coresentinel.py` | Delegates verify; dangling-flag guard; 32 dead lines removed; `verify --json` | done |
| `sentinel-validator.py` | `log()` → stderr; now scans untracked files too | done |
| `tests/security/test_safe_execution.py` | New — 25 tests on no-shell, interpreter resolution, execution records | done |
| `tests/verification/test_evidence_suite.py` | Rewritten — asserts evidential truth, not output shape | done |
| README, 3 protocols, CI, VERSION | Updated to match measured behaviour; 10.1.0 → 10.2.0 | done |
| `coresentinel_core/runtime/` | New — errors, paths (containment), config (5-layer precedence), logging (redacting, stderr), events (18 names, isolated handlers), container | done |
| `coresentinel_core/storage/` | New — ports, JsonStore, SqliteStore, forward-only checksummed migrations, `0001_init.sql` | done |
| `coresentinel.py` | Added `config` and `migrate`; unknown-command error moved to stderr | done |
| `coresentinel_doctor.py` | Added Runtime and Storage checks (7 → 9 subsystems) | done |
| `tests/runtime/` | New — 97 tests: config precedence, containment, events, one contract suite over both backends, migration runner | done |
| `tests/conftest.py` | `SANDBOX_PACKAGES` copies `coresentinel_core/` into every sandbox | done |
| `.gitignore`, VERSION | Runtime artifacts ignored; 10.2.0 → 10.3.0 | done |
| `coresentinel_core/memory/assembly.py` | New — task-relevant context, ranked + budgeted + declared truncation | done |
| `coresentinel_core/decisions/` | New — 20-field additive schema, project-scoped ledger, contradiction guard, supersession | done |
| `coresentinel.py` | `context --task/--budget`; `decision show/verify/supersede`; `migrate decisions`; `positional()` fixed; `cmd_decision` returns its exit code | done |
| `coresentinel_recall.py` | Reads the scoped ledger, so recall and brief see project decisions | done |
| `tests/memory/test_context_assembly.py`, `test_decision_intelligence.py` | New — 59 tests | done |
| README, `08-decision-ledger` (rewritten), `04-layered-memory`, `14-cli`, VERSION | 10.3.0 → 10.4.0 | done |
| `coresentinel_core/project/discovery/` | New — evidence-based detection across 10 dimensions, structured manifest keys not substrings | done |
| `coresentinel_core/knowledge/` | New — typed entities and relations, built only from recorded facts; traversal with depth | done |
| `coresentinel.py` | `project inspect/list`, `knowledge query/build/describe` | done |
| `storage` | `knowledge_entities` + `knowledge_relations` collections, migration `0002_knowledge.sql` | done |
| `tests/project/` | New — 58 tests | done |
| README, `14-cli`, VERSION | 10.4.0 → 10.5.0 | done |
| `coresentinel_core/agents/` | New — protocol + validation, 8-permission model, sandbox, registry, 5 built-in agents, planner, orchestrator | done |
| `squad-contracts.json` | All 17 contracts gained an explicit `permissions` block; registry → v1.1.0 | done |
| `coresentinel.py` | `agent permissions/run`, `task plan/run/list` | done |
| `storage` | `agent_sessions` + `task_results` + `permission_grants`, migration `0003_agents.sql` | done |
| `tests/agents/` | +66 tests | done |
| README, `02-squad-contracts` (rewritten), `14-cli`, VERSION | 10.5.0 → 10.6.0 | done |
| `coresentinel_core/agents/adapters/` | New — base + conformance, CLI/HTTP/MCP transports, claim-vs-evidence separation | done |
| `adapters.json` | Invocation profiles for claude-code, codex, gemini-cli, generic; registry → v1.2.0 | done |
| `squad-contracts.json` | Iris/Builder/Debugger/Migrator may delegate to a host binary; registry → v1.2.0 | done |
| `coresentinel_gates.py` | Rewritten — 10 stages, reason codes, `--report`, `--objective` | done |
| `coresentinel.py` | `adapter invoke/conformance`, `gate --report/--objective`, 4 unregistered flags fixed | done |
| `tests/agents/test_adapters.py`, `tests/governance/test_gate_codes.py` | New — 50 tests | done |
| README, `13-adapter`, `02-quality-gates`, `14-cli`, VERSION | 10.6.0 → 10.7.0 | done |
| `coresentinel_core/audit/` | New — hash-chained ledger, 12 subjects, event-bus sink | done |
| `coresentinel_core/incidents/` | New — INC-NNNN with typed links, graph integration | done |
| `coresentinel_core/security/redaction.py` | New — one implementation, imported by the logger and the ledger | done |
| `coresentinel.py` | `audit verify/coverage`, `incident create/show/link/resolve`, emissions at 6 sites | done |
| `orchestrator.py` | Writes audit through the ledger, not around it; side effects audited separately | done |
| `storage` | `incidents` + `incident_links`, migration `0004_incidents.sql` | done |
| `tests/security/test_audit_chain.py`, `tests/governance/test_incidents.py` | New — 65 tests | done |
| README, `09-audit-trail` (rewritten), `61-incident`, `14-cli`, VERSION | 10.7.0 → 10.8.0 | done |
| `coresentinel_core/patterns/` | New — PAT-NNNN library as data, renders back to the documented markdown | done |
| `coresentinel_core/learning/` | New — observer, candidates with an evidence threshold, apply/revert | done |
| `coresentinel_evolve.py` | `get_proposal`/`update_proposal`; removed the false "Versioned Change Released" claim | done |
| `coresentinel.py` | `pattern list/show/add`, `evolve observe/candidates/reject/promote/apply/revert` | done |
| `storage` | `learning_candidates`, migration `0005_learning.sql` | done |
| `tests/governance/test_learning_pipeline.py` | New — 41 tests | done |
| README, `55-self-evolution`, `11-pattern-library`, `14-cli`, VERSION | 10.8.0 → 10.9.0 | done |
| `coresentinel_core/services/` | New — 27 operations, one layer all surfaces call; every write emits | done |
| `coresentinel_core/api/` | New — stdlib HTTP, `/api/v1/*` generated from the catalogue, token auth | done |
| `coresentinel_core/mcp/` | New — JSON-RPC over stdio, tools generated from the catalogue | done |
| `coresentinel.py` | `serve`, `mcp` | done |
| `tests/surfaces/` | New — 53 tests incl. the import-graph bypass guarantee | done |
| README, `16-api-protocol` (rewritten), `14-cli`, `30-selftest`, VERSION | 10.9.0 → 10.10.0 | done |
| `coresentinel_core/web/` | New — allowlisted `index.html` / `app.css` / `app.js`, seven read-only views, no build step | done |
| `coresentinel_core/api/server.py` | Serves the dashboard from the allowlist with a tight CSP + `nosniff`, before routing | done |
| `coresentinel.py` | `serve` banner announces the dashboard URL when the assets are present | done |
| `tests/surfaces/test_dashboard.py` | New — 33 tests: allowlist, traversal, CSP, no-sample-data, endpoint parity, theme | done |
| README, `16-api-protocol`, `14-cli`, `30-selftest`, VERSION | 10.10.0 → 10.11.0 | done |

## Session Recap
> This section survives resets. Keep it under 30 lines.

### What Was Done
- **Phase 10**: a seven-view dashboard served by the Phase 9 API from a three-file allowlist — no npm, no framework, no sample data. Verified in a real browser, not asserted from code: every view rendered live, the contradiction checker returned CONTRADICTS against a decision recorded seconds earlier on the CLI, and killing the server mid-session replaced every panel with its own failure instead of leaving a stale number on screen.
- **Phase 9**: three surfaces over one service layer. 27 operations; the HTTP API's routes and the MCP server's tools are both *generated* from the catalogue, so an operation cannot exist on one surface and be missing from another. An import-graph test fails the build if `api/` or `mcp/` reaches past the service layer. Found F-25: `serve --host 0.0.0.0` auto-generated a token and served anyway, defeating its own refusal.
- **Phase 8**: closed the evolution loop. `evolve approve` had printed "Versioned Change Released" while writing no rule file (F-24). Now: observer derives candidates from incidents/failures/patterns, a candidate needs 2 distinct sources, approval is a separate human act, `apply` snapshots + writes + versions + audits, `revert` restores byte-identically. Patterns became data (`PAT-NNNN`).
- **Phase 7**: the audit trail became tamper-evident. v1 recorded 1 subject of 12 with `RUN-#{random}` ids and no integrity; every record now carries the hash of the one before it, and `audit verify` detects mutation, deletion, insertion and reordering. Incidents became data with a first-class `learning` field. Redaction consolidated into one implementation.
- **Phase 6**: agent invocation over three transports (CLI/HTTP/MCP) with a conformance contract, and quality gates rewired onto the evidence engine — 10 stages with machine-readable reason codes. Found and fixed F-23, a recurrence of F-20: four flags (`--objective`, `--roles`, `--depth`, `--as`) were read but never registered, so `gate run --objective "..."` gated a directory named after the objective. A source-scanning test now prevents the whole class.
- **Phase 5**: agent permissions became real. The README's claim that "a read-only researcher cannot silently write files" was true of a JSON document and false of the runtime; an agent is now handed a sandbox that checks every read, write and command against its contract, contains every path, and audits every denial. The 12-role pipeline runs end to end.
- **Phase 4**: the project brain — ten dimensions, every value naming the file that proves it, `unknown` where nothing did. Fixed F-22: v1 reported `['Laravel','Symfony']` for a Laravel project (Laravel depends on `symfony/console`) and `['Next.js','Vue','React']` for a project whose only matches were `next-auth`, `eslint-plugin-vue` and `@types/react`. Plus a knowledge graph built only from recorded relationships.
- **Phase 0**: inspected the whole repo before changing anything, reproduced every finding empirically, wrote `Planning.md` (12-phase roadmap, gap analysis of ~95 capabilities, risks, definition of done).
- **Phase 1**: rebuilt verification, health scoring and quality gates on commands that actually execute. Closed 7 planned defects (F-01..F-06, F-13, F-14) and 2 found during the work (F-16 scanner logging to stdout, F-17 scanner blind to untracked files).
- **Phase 3**: task-relevant context assembly (F-07) and decision intelligence (F-08) — an agent can no longer quietly reverse an ADR. Found and fixed two pre-existing CLI defects: F-20 (a flag's value read as the target directory — `verify --claim "..."` verified a path named after the claim) and F-21 (`decision` discarded its exit code).
- **Phase 2**: built `coresentinel_core/` — runtime (config, paths, logging, events, container) and storage (one port, JSON + SQLite backends, checksummed forward-only migrations). Two new CLI commands, two new doctor subsystems. Found and closed F-18 (unknown-command error on stdout) and F-19 (a silent exception swallow in my own `Container.shutdown()`, caught by CoreSentinel's own scanner).

### Where We Left Off
- Phase 10 complete and verified: 1032/1032 tests, validator exit 0, seven views rendered by hand in Chrome.
- `doctor` reports DEGRADED for one pending evolution proposal awaiting human review — pre-existing state, not a regression.
- **Committed and pushed** on 2026-08-14: `153d8eb` (phases 1-10, release 10.11.0) and `f8aff36` (gate-state isolation fix). Tree clean, `origin/main` up to date.
- Next action: **Phase 11 — Observability, Performance & Production Hardening** per `Planning.md` §7.

### Key Context for Next Session
- The headline defect is fixed: an empty directory now returns INDETERMINATE (exit 2) instead of 80/100 VERIFIED, and 0/100 CRITICAL instead of 89/100 health. CoreSentinel itself scores 86/100, every number traceable via `score --explain`.
- **UNKNOWN is a first-class result** across verify/score/gate — excluded from denominators, never a pass. Exit code 2 = INDETERMINATE, distinct from 1 = failed.
- Do NOT weaken or delete any test. Standing criterion: test count strictly increasing (436 → 477 → 583 → 643 → 707 → 776 → 828 → 896 → 940 → 999 → 1032 → 1034 so far). Three tests were *corrected* in Phase 1 because they asserted the fabricated behaviour — that is allowed; weakening is not.
- Preserve verbatim: the memory lifecycle engine, project/core scoping, `load_layer()`'s `(data, error)` contract, adapter sync safety, `doctor`'s check structure, conftest isolation.
- Still open: F-15 partially (`read_json`/`print_header` still duplicated). F-09 closed in Phase 7 (monotonic `AUD-NNNNNN`). **F-10, F-11 and F-12 closed 2026-08-14**: `memorycore.conf` deleted and both installers stopped writing it (the migration guide had claimed "it is gone" since Phase 12 — now true); 12 leaked absolute paths stripped from `project-labels.json`; the README protocol directory reconciled to the 38 documents on disk, now held by `test_the_protocol_directory_lists_every_document_on_disk` so the count cannot drift by hand.
- **A doc saying a thing was done is not evidence it was done.** F-10's row read "removed in Phase 3" for nine phases while the file shipped. Where a status line asserts a file was deleted or a value changed, check the tree before believing it.
- The remaining Definition-of-Done gap is **the CI matrix**, which needs one green run carrying the Phase 11 Performance and Phase 12 Demo stages. It cannot be ticked from a developer machine.
- **The memory engines were deliberately NOT moved into the package.** A minimal repro proved a re-export shim breaks test isolation: patching `MEMORY_DIR` on the shim has no effect on what the function reads, so the suite would write to the real `memory/`. Moving them needs `sys.modules` aliasing or a fixture rewrite — its own change, not a side effect of one.
- **The CLI still calls engines directly** — it predates the service layer and rewriting it would risk 900+ tests for no behaviour change. The bypass guarantee is enforced on the two NEW surfaces. Phase 10's dashboard must consume the API, never the engines.
- **Auth is a single shared token**: no identity, no scopes, no rotation. Fine for a local control plane; the API should not be exposed as a multi-user service.
- **The dashboard is read-only and stays that way.** Every operation it calls is a read, asserted against the catalogue's mode flags. Gate runs, decisions and evolution approvals are consequential acts, and a mouse is a poor audit trail.
- **Its assets are served before authorisation**, so anyone who can reach the port can read the HTML/CSS/JS. They carry no project data; the data still needs the API, and off-loopback reads still need the token.
- **The suite used to rewrite the repo's own `memory/gates.json`** via `gate.run` on the service layer. conftest now redirects `coresentinel_gates.GATES_FILE` in an autouse fixture — if a test ever leaves the tree dirty, look for engine state written to the Core root rather than to `tmp_path`.
- **GitHub push protection rejects credential-shaped test fixtures.** `tests/security/test_audit_chain.py` assembles them from parts so no literal token sits in a blob; the value handed to the redactor is identical. Do not "simplify" them back to literals.
- **The offline banner only covers the API dying while the page is open** — the server is also what serves the page, so a cold start with no server shows a browser error, not the banner.
- **MCP has never been mounted in a live host.** Conformance is asserted against the protocol, not an implementation of it.
- **`apply` supports three targets only** (`anti-patterns.json`, `11-pattern-library.md`, `55-self-evolution.md`). Anything else is refused rather than patched — safe, but most protocol changes remain manual.
- **Nothing proposes automatically.** A corroborated candidate still needs a human to write the proposal, then a human to approve it. Two people-shaped gates, deliberately.
- **The ADR-001 boundary test earned its keep**: I added a `patterns` SQLite table and Phase 2's test caught it. Removed the table rather than relax the test.
- **Auditing is wired through the event bus.** Emitting an event IS how something gets audited — a subsystem added later either emits and is recorded, or shows up as an unrecorded subject in `audit coverage`. Never call the ledger directly from a command.
- **Tamper-evidence, not tamper-proofing.** Anyone with write access can recompute the chain; what they cannot do is change one record and leave the rest intact. Don't overstate it.
- **`deployment` is the one audit subject with no emitter** — nothing deploys. Declared and reported as never-recorded rather than dropped.
- **An incident's `learning` is what Phase 8 consumes.** The fix stops it now; the learning stops it recurring. Resolving without one is allowed and reported.
- **An invocation's only evidence is the invocation itself.** What the agent says it did lives under `claims`, never `evidence` — turning "I added tests" into evidence of tests would reintroduce Phase 1's fabrication at the vendor boundary.
- **Adapter invocation is not yet wired into the orchestrator.** `task run` still uses built-in executors only; connecting UNSUPPORTED roles to adapters is the obvious next step and was deliberately not in Phase 6.
- **No test invokes a real vendor.** `claude` and `codex` are detected here, but a suite needing a paid API and a login does not run in CI. Normalisation is proved against mock CLI/HTTP/MCP agents.
- **Seven of twelve pipeline roles have no executor** and report `UNSUPPORTED`. Phase 6 binds vendor adapters; until then the orchestrator's value is bounded. `UNSUPPORTED` does not stop the pipeline — nothing went wrong when a capability is simply absent.
- **The sandbox mediates what an agent asks it for; it is not an OS-level jail.** A built-in that imported `os` directly would bypass it. The boundary holds for anything going through the protocol, which is every adapter-driven agent.
- **`ASK` is a constructor flag, not a prompt.** `--interactive` means "assume the human said yes" — only safe under supervision. A real approval surface is still owed.
- **Nothing in the knowledge graph is inferred from source code.** Edges come from discovery findings, decision `--relates-to`/`related_incidents`, and memory layers. A `feature → controller → table` chain exists only where someone recorded it — asserted by a test that an unrecorded controller never appears.
- **Contradiction detection is lexical, not semantic.** It cannot tell that ADR-001's "Redis" (rejected as a memory store) is unrelated to a product cache. Biased toward flagging by design; every finding cites the ADR so dismissal is cheap.
- **The runtime exists but almost nothing consumes it.** `DEFAULTS` in `coresentinel_core/runtime/config.py` duplicates constants still hardcoded in the engines (pass_threshold, compact_budget, decay rate). They agree today and can drift until Phase 3 makes the engines read config. No engine emits an event yet either.
