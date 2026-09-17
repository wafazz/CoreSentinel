# WebAppsBI — Dynamic Web-Based Business Intelligence Dashboard

> **Status**: PH-16 Security Hardening COMPLETE (16 of 18 phases; PH-17 Testing & QA next) · **[LEARN]**
> **Last Updated**: 2026-09-13

## Business Context
- **Client**: client project (fixed fee) — CS `52-handoff-protocol.md` applies at Phase 18
- **Status**: active — PH-01..PH-16 delivered, 178 of 201 requirements. PH-16 found 9 boundary/leak defects (2 high) in a finished system that had passed 15 phase security gates — see `55-self-evolution.md` "WebAppsBI — PH-16"
- **Priority**: high
- **Revenue Model**: fixed-fee build
- **Deployed**: No

## Overview
- **Root**: `Desktop/Codex Lure/project/WebAppsBI`
- **Stack**: Laravel 12.69.2 · PHP 8.3 in production (8.4.10 locally; Composer platform pinned 8.3.23, OpenSpout 4.x — DEC-054) · REST API · Vue 3.5.42 + TypeScript 5.9 · Vite 7.3.6 · Bootstrap 5.3.8 · AdminLTE 4.9.1 · Apache ECharts 6.1.0 · Gridstack.js 13.3.0 · PostgreSQL 16 · Redis 8.4.0 · Laravel Queue/Horizon · Laravel Excel 4.0.2 + PhpSpreadsheet 5.8 · Sanctum 4.3 (SPA cookie)
- **Type**: Business Intelligence / analytics web application (custom, **not** a Power BI embed)
- **Auth**: Sanctum SPA session cookie + code-owned RBAC registry + per-company scope
- **Currency**: per company (`companies.currency_code`); mixed-currency aggregates are **refused**, never summed
- **Payment**: none
- **Database**: PostgreSQL 16 on **`:5433`** (not 5432 — `pg_isready` with no args reports its own default and misled the plan once)
- **Deploy**: single Ubuntu LTS VPS — Nginx + PHP-FPM 8.3 + Supervisor + systemd. **No Node on the production server** (assets built in CI).
- **Scale ceiling**: 5M fact rows · 100k rows/file · 50 companies · 25 concurrent dashboard users

## Documents
- `Planning.md` — 29 sections, **201 requirements**, 18 phases, traceability matrix
- `DevelopmentProgress.md` — live phase tracker
- `DecisionLog.md` — DEC-001..014 + change-control register
- `docs/documentation.md` — module index
- `session-memory.md` — session state

## `[LEARN]` — stacks not yet in the Pattern Library
| Library | Version | Why new |
|---|---|---|
| Apache ECharts | 6.1.0 | No CS coverage. First charting library in the Core other than ApexCharts (used once, different project) |
| Gridstack.js | 13.3.0 | No CS coverage. Drag/resize grid + Vue reactivity is the interesting problem |
| Laravel Excel | 4.0.2 | No CS coverage, and **4.x is a rewrite of 3.x** — every 3.x tutorial is untrustworthy |
| Sanctum SPA cookie auth | 4.3 | The Core's Laravel projects have all used Inertia (session auth without Sanctum) or server-rendered Blade |

Graduate at Phase 8 per `10-learn-protocol.md`: Pattern Library → Init recommendation table →
Review Protocol checklist → Deployment Memory → drop the `[LEARN]` tag.

## Key Patterns (pulled from 11-pattern-library.md)
- **PostgreSQL `timestamptz` needs `'timezone' => 'UTC'` on the connection** — `REQ-FND-004`
- **A failed statement aborts the whole PostgreSQL transaction** — shapes the entire import design; validate in PHP *before* SQL, savepoints for genuinely racy inserts (`Planning.md` §7.6)
- **Date columns are calendar days, not instants** — `period_date DATE`, never a timestamp
- **Money across a decimal-string API boundary** — `numeric(20,4)` → string → `Intl.NumberFormat`. No float on the money path (DEC-007)
- **Registry-backed RBAC — `Gate::before` that cannot become a bypass** — return `true` or `null`, never `false` (DEC-006)
- **The grant ceiling** — a user may never grant access they do not hold
- **Tenant scope: read open, write closed** — adapted to company scope; the permitted set is derived from the session and intersected, never widened
- **Declared settings registry — code owns the keys, the table owns the overrides** — applied to settings *and* to the analytics metric/dimension registry (DEC-008)
- **Metric honesty — null is not zero, and incomparable things are never summed** (DEC-010)
- **Dashboard metrics you do not have data for** — every widget ships all four states
- **Audit: declare the actions; derive the tenant from the record; two actor columns; tiebreak the sort**
- **A restore drill that can actually fail** — `REQ-OPS-012`, a release gate
- **A CSP for Vite that needs no script nonce**
- **Rate-limit what costs money, not only what authenticates** — analytics/import/export weighted above auth
- **AdminLTE 4 + Bootstrap through Vite — SCSS `loadPaths` is mandatory**
- **Privilege columns must not be fillable**

## Completed
1. **Phase 0 — Intake & Planning (2026-09-12)** — tier T2 declared; toolchain verified on-machine; Pattern Library gap analysis; prior art reviewed; `Planning.md` (201 reqs / 18 phases / 29 sections), `DecisionLog.md`, `DevelopmentProgress.md`, `docs/documentation.md`, `session-memory.md` authored.
8. **PH-08 Analytics Engine (2026-09-13)** — 15/15 requirements. Registry-driven aggregation (no query builder), 5 endpoints, metric-honesty rules as 14 executable cases, cache keys encoding invalidation. **360 tests / 1,014 assertions**. Live: KPI, monthly trend, group-by, batch and drill-down against real imported data.
7. **PH-06/07 Financial Model + Import Pipeline (2026-09-13)** — 26 requirements. `CHANGE-001` swapped the two phases (the import wrote into a table the next phase defined). Fact table with generated period columns and exact decimals; chunked, resumable, idempotent import. **307 tests / 799 assertions**. Full journey run live: map → queue → import → activate, ending in a real aggregate.
6. **PH-05 Dynamic Mapping Engine (2026-09-13)** — 13/13 requirements. Code-owned field registry, exact-decimal and strict-date parsers, confidence-scored suggestions, immutable template versions, reconciliation reports, S-09. **255 tests / 654 assertions**. Verified live against a deliberately messy workbook: resolved to exactly the two broken cells.
5. **PH-04 Excel Upload & Validation (2026-09-13)** — 14/14 requirements. Content-based type verification, zip-bomb guard, hardened readers, bounded reads, queued inspection. **180 tests / 463 assertions**, including a 12-case malicious fixture suite. Verified live: 44-row 3-sheet workbook inspected in 98 ms, header row 4 auto-detected past a title block.
4. **PH-03 Dataset Management (2026-09-13)** — 10/10 requirements. 3 tables, 7 API routes, 8-status guarded state machine, atomic activation behind a partial unique index. **142 tests / 311 assertions**. Supersession verified live: v1 archived pointing at v2, both audited.
3. **PH-02 Company & Access Management (2026-09-13)** — 10/10 requirements. 4 tables (citext, companies, aliases, grants), 9 API routes, company switcher + hierarchy UI. **99 tests / 225 assertions**. Isolation verified live: a scoped editor sees 1 of 4 companies and gets 403 — not an empty list — on the parent.
2. **PH-01 Foundation & Core Architecture (2026-09-13)** — 15/16 requirements Done, 1 partial. 9 tables, 14 API routes, 13 Vue SFCs, 8 TS modules, **43 tests / 124 assertions / 0 failing**. `vue-tsc` clean, `composer audit` + `npm audit` clean. Verified end to end in a browser: login → forced password change → shell → users → settings → system health.

## Remaining
- PH-09..PH-18 (see `DevelopmentProgress.md`). PH-02 opens with the **Design Gate**.
- 14 open questions outstanding (`Planning.md` §26). `OQ-01` (real Excel samples) is the highest-value one.
- `REQ-FND-012` partial: the health assertion works; the machine's PHP limits still need raising (needs client go-ahead — it edits Herd's global config).

## Anti-Patterns (This Project)
- **Never create a database column from an Excel header.** No dynamic DDL from user input — it is a security finding, not a feature (DEC-004).
- **Never store business measures as EAV key/value rows.** The prior in-house attempt (`project/Excel Dashboard` / DataLure) used a generic `dataset_rows` table; it cannot be indexed for aggregation. Do not reuse that codebase's shape.
- **Never write import code against a remembered Laravel Excel 3.x API.** 4.x is a rewrite (RISK-02).
- **Never auto-detect a date format per row.** `03/04/2026` is genuinely ambiguous; guessing corrupts a year of data. The format is declared in the mapping (RISK-04).
- **Never coalesce a missing measure to zero.** "Not reported" and "reported as zero" are different business facts.
- **Never return an empty result for an unauthorised company.** Return 403 — an empty list is indistinguishable from "no data" and teaches nobody anything.
- **Never let a `.env`, a stack trace or a SQL fragment reach a production API response.**
- **Never let AdminLTE's default dashboard look leak onto the BI surface.** That is the thing the client is paying for (DEC-012).
- **Never `migrate:rollback` a production fact table.** Roll the code back first; decide about the schema separately, with a backup in hand.

## Work Log

### 2026-09-13 — PH-08: Analytics Engine
- **The registry is the security boundary**: a request carries a key, the SQL lives in code. 8 injection payloads through metric/dimension/aggregation/comparison/sort all 422.
- **Metric honesty as tests**: null margin on zero revenue, null growth with no base, null (not zero) over no rows, genuine zero still distinguishable, mixed currencies **refused** with per-currency subtotals, tail bucketed not dropped.
- Cache key = access_version + query fingerprint + **active-dataset fingerprint**, so activation makes staleness unreachable and a revoked user cannot be served a cached figure.
- **Defect**: `period_month` shipped invalid SQL because its label expression was absent from GROUP BY — valid PHP, broken at runtime, and four of nine dimensions had never been executed by a test. Now two tests walk the *entire* registry (DEC-031).
- **Defect**: metric × aggregation mismatch returned 500 — third repeat of "a domain guard is not a substitute for validation" (DEC-032).
- Also caught myself believing a scripted edit that silently did not apply; recorded as an anti-pattern.

### 2026-09-13 — PH-06/07: Financial Model + Import Pipeline
- **CHANGE-001**: the plan ordered the import before the schema it writes into. Recorded as a change with impact and risk, not silently swapped.
- Fact table: `numeric(20,4)` exact decimals (10,000 × 0.1234 = 1234.0000 asserted), `DATE` periods, generated year/month/quarter, CHECK constraints, 7 indexes.
- Import: decide every row in PHP **before** any SQL (PostgreSQL aborts the whole transaction on a failed statement), per-chunk transactions, resume-from-cursor idempotency, bounded memory.
- **Company resolution never creates** — a typo becoming a real company would delete its figures from the consolidated view.
- **Two defects found by running it**: polling on "is it processing" stopped before a queued job started (DEC-029); and the rejections panel claimed "every row imported" on a dataset never imported (DEC-030) — the third instance of the same null-versus-zero shape.
- Live: map → queue (worker off) → start worker → screen updated without reload → activate → aggregate revenue 6,963,250.7500, margin 0.0854.

### 2026-09-13 — PH-05: Dynamic Mapping Engine
- **RISK-13 accepted** by Fakrul (DEC-026): build on synthetic fixtures, real files verify rather than design. Mitigated by making the fixture *worse than reality* and keeping synonyms/formats/separators as data, not code.
- **The governing rule**: a date format is declared and applied strictly, never detected per row. `03/04/2026` is 3 April or 4 March depending only on that choice, and S-09 renders the parsed result live as the user picks.
- Exact decimals via bcmath (string, never float); three-state parse results so blank ≠ error ≠ value.
- **Defect found by running it**: `Status` suggested as Region at 0.67 — a similarity ratio is meaningless on short words. Capped absolute edit distance by length (DEC-027), verified both directions.
- Browser run against the messy workbook: header row 5 past a merged title block, 6/8 suggestions, and after declaring the date format and `RM` token it resolved from 2-clean/9-broken to **9-clean/2-broken** — exactly the two deliberately bad cells.

### 2026-09-13 — PH-04: Excel Upload & Validation
- **RISK-02 retired**: `maatwebsite/excel 4.0.2` verified against the installed source — every concern the build needs (`WithChunkReading`, `WithHeadingRow`, `WithReadFilter`…) still exists. It had also never actually been installed, despite being in Planning §1.3 since Phase 0.
- Guards: magic-byte verification (OLE2 `.xls` refused *whatever it is named*), zip bomb measured from the central directory without decompressing, sheet/row/column/cell caps, `setAllowExternalImages(false)` against SSRF, sheet-name allow-list, ULID storage names on a private disk.
- **Formulas are never evaluated** — `getCalculatedValue()` appears nowhere; the cached value is both the safe and the honest answer (DEC-025).
- **Three defects**: 251 phantom columns from `rangeToArray()` padding (DEC-023); `$request->validate()` validating `integer` without casting; and a Domain→Service dependency caught by the architecture test — whose fix then hid a missing container binding behind sensible defaults, now covered by a wiring test.
- 12 hostile fixtures, all generated rather than committed.

### 2026-09-13 — PH-03: Dataset Management
- 8-status lifecycle; illegal transitions return 409 **naming the legal moves**, and the detail view publishes `meta.allowed_transitions` so the UI offers only actions that will succeed.
- **Visibility is the atomic unit** (DEC-009 realised): analytics reads only `active`, so a failed import writes rows nothing queries. Activation is one small transaction guarded by a partial unique index — tested by writing `status='active'` directly through the query builder to prove the *database* enforces it, not the service.
- **Defect found on screen**: every in-flight dataset was flagged "counts do not reconcile". `countsReconcile()` now returns `?bool` — null while in flight, progress shown instead (DEC-021).
- **Fakrul caught a hardcoded `ChangeMe!2026` in DatabaseSeeder** that had survived two full security gates. Removed (DEC-022), guarded by a test, and `40-security-protocol.md` now names the directories to sweep rather than stating a concern.

### 2026-09-13 — PH-02: Company & Access Management
- Companies with adjacency-list hierarchy (max depth 5, cycle + subtree-height guards), citext codes, aliases, per-company role grants.
- **One scope resolver**: `CompanyAccessService::resolveScope()` — session-derived, intersected, 403 on empty. No second path.
- Grant ceiling in three parts: company reach, role rank, descendant reach.
- §13.4 access-control matrix as a Pest dataset (21 cases) + a router-enumeration test that fails the build when a `{company}` route ships without scope middleware.
- **Two defects, both real**: (1) scope and permissions expanded descendants differently — extracted `CompanyTree` (DEC-019), found by a test; (2) `depth` drifted from `parent_id` because only the controller derived it — now derived in `Company::booted()` (DEC-020), **found by looking at the screen while every test passed**.
- Closed PH-01's Probe gap: 390 px verified. `resize_window` no-ops on a reused tab; create a fresh one first.
- Persisted 5 patterns and 3 anti-patterns to the Core.

### 2026-09-13 — PH-09: Power BI-Inspired Dashboard (S-13)
- The screen the client is paying for. 6 widgets in **one** batched request: KPI strip, revenue/profit trend, expenses donut, revenue-vs-expenses by company, expense trend, detail table with server-side search/sort/paginate. Cross-filter, drill-down to file + row, four states on every widget.
- ECharts tree-shaken into its own lazy chunk (570 KB / 195 KB gzipped); `EChart.vue` is the **only** place an instance is created.
- Verified in the browser against real imported data, and at **390 px**.
- **Four defects, three found only by looking at the screen**:
  1. The donut's centre total rendered nothing — ECharts drops an option for an **unregistered** component silently, past a clean typecheck and a clean build (DEC-033).
  2. Clicking a slice cross-filtered the donut *itself* into a single 100% ring — the control consumed its own selection and became a dead end (DEC-034).
  3. Every figure was formatted in the **viewer's OS locale** (`Intl(undefined)`), violating the project's own `NFR-18`. Now `display.locale`, delivered on `/auth/me` (DEC-035). Found because a new test disagreed with Chrome.
  4. A bad settings **value** was a 500 and a bad integer was stored then cast to `0` — pre-existing since PH-01, and the **fourth** instance of "a domain guard is not a substitute for validation" (DEC-036).
- **Tooling honesty**: larastan had been in `require-dev` since PH-01, named in eight phase reports, with **no `phpstan.neon`** — it had never analysed a file. Now level 6 with a 107-finding baseline and `composer analyse`. Vitest brought forward from PH-17 (32 tests) because Planning §21.2 assigns it to exactly the units this phase wrote.
- Persisted 5 anti-patterns and 6 learned skills to the Core; escalated the "guard ≠ validation" rule to a checklist item.

### 2026-09-13 — PH-01: Foundation & Core Architecture
- Scaffolded Laravel 12.69.2 + Vue 3.5 SPA + TypeScript 5.9 + Vite 7 + Bootstrap/AdminLTE, PostgreSQL 16.14 on **:5433**, Redis 8.4 split across three logical databases.
- Built: code-owned permission/role/settings registries, `Gate::before` returning true-or-null, audit catalogue with redaction, correlation IDs, uniform API envelope, weighted rate limits, health check.
- **Three defects found by running the app, none by reading it**:
  1. `Gate::before` bypassed the self-disable invariant → invariants moved out of policies into `AccountGuard` (DEC-016).
  2. Sanctum stateful-domain mismatch → login 200, next request 401, silently. Now a health check (DEC-017). My own defensive `hasSession()` guard had converted a loud 500 into that silent failure — logged as an anti-pattern.
  3. `/health` 503 was eaten by the HTTP interceptor, breaking the screen that exists to diagnose it (DEC-018).
- Corrected two planning errors found by verification: PostgreSQL is on **5433 not 5432**, and Vue Router 5 pulls `@pinia/colada` as a peer (DEC-015).
- Persisted to the Core: new Pattern Library section, four anti-patterns and six learned skills in `55-self-evolution.md`.

### 2026-09-12 — Phase 0: Intake, Research, Planning
- CS Core loaded; **T2 Full** declared (schema, auth/authz, tenant scoping, file upload, public API — five absolute T2 surfaces).
- Intake settled: client fixed-fee · medium scale (≤100k rows/file, ≤5M total) · Linux VPS.
- Scout verified every version on the machine rather than assuming: PHP 8.4.10, Composer 2.8.10, Laravel 12.69.2, PG 16 running, Redis 8.4.0, Node 24.19.0, ECharts 6.1.0, Gridstack 13.3.0, Vue 3.5.42, AdminLTE 4.9.1, Laravel Excel 4.0.2 (requires PHP ^8.3 / illuminate ^12||^13 / phpspreadsheet ^5.8).
- **Found a real blocker at intake**: PHP `upload_max_filesize=10M`, `post_max_size=12M`, `memory_limit=128M` silently contradict the large-file requirement. Assigned to `REQ-FND-012` in Phase 1 with a health-check assertion — not left to surface as a Phase 4 bug report.
- TypeScript pinned to 5.9 despite 7.0.2 being published — `vue-tsc` peer range (DEC-013).
- Planning documents authored. **Stopped at WAITING FOR PLANNING APPROVAL as instructed** — no scaffold, no code.
