# STMS — Smart Team Management SaaS

> **Status**: Active Development — Phases 3 and 4 done, Phase 5 started (PLATFORM-001)
> **Last Updated**: 2026-09-18

## Business Context
- **Client**: personal project (Fakrul's own SaaS)
- **Status**: active
- **Priority**: medium
- **Revenue Model**: multi-tenant B2B SaaS for SMEs (plans/entitlements planned, `BILL-001` not started)
- **Deployed**: No — deploy target still an open question (Planning.md §9 Q8)

## Overview
- **Root**: `Desktop/Codex Lure/project/stms`
- **Stack**: Laravel 12.69.2 / PHP 8.4.10, Inertia-Laravel 2.0.27, Vue 3.5 + TS 5.x, Tailwind 3 + shadcn-vue (radix-vue), Vite 6
- **Type**: SaaS — multi-tenant work management (tenant workspace + platform-owner context + invited-client portal)
- **Auth**: Laravel session auth (register/login/reset/verify/confirm). Tenant + owner membership created automatically at registration.
- **Database**: XAMPP **MariaDB 10.4.28** on **port 3307** (`stms`; `stms_test` for cross-engine runs) — *not* MySQL 8, despite the original README. **SQLite `:memory:` for the test suite** (phpunit.xml). Suite verified green on both engines. Client: `/Applications/XAMPP/xamppfiles/bin/mysql -u root -h 127.0.0.1 -P 3307`
- **Tests**: PHPUnit 11.5.56, class-based. `tests/Pest.php` exists but **Pest is not installed** — dead file.
- **Repo**: local git only, `main`, no remote configured

## Key Patterns
- **Tenant context via request attributes**: middleware `tenant` resolves the active tenant; controllers read
  `$request->attributes->get('tenant')->id`. There is no global scope — every query filters `tenant_id` by hand.
- **Flat controllers**: all business logic lives in `app/Http/Controllers/*`. There is **no** `app/Actions/`,
  `app/Services/` or `app/Policies/` layer, despite Planning.md §3 specifying one. Match the flat style until
  Fakrul decides to introduce the layer.
- **Authorization by middleware + `abort_unless`**: route groups carry `['auth','verified','tenant','tenant-role:owner,admin']`;
  cross-tenant access returns **404**, cross-tenant *reference* in a payload returns **422**.
- **Server-owned fields last in the spread**: `Model::create([...$data, 'tenant_id' => $tenantId])` — validated input
  can never override tenant/owner columns because they are written after the spread.
- **Inertia pages are hyper-dense single-line templates** (`resources/js/pages/*.vue`). Do not run prettier over an
  existing page to add one line — it reformats the whole file.

## Completed
1. Phase 1 — auth, tenancy, tenant-scoped access control (`AUTH-001`, `TENANT-001`, partial `RBAC-001`)
2. Phase 2 — navigable skeleton for tenant / client / platform contexts, client invitation + activation (`CLIENT-001`)
3. Phase 3 — `TEAM-001`, `PROJECT-001`, `JOB-001` (core), and **`MILESTONE-001` (2026-09-18)**
4. Phase 4 — `BLOCKER-001`, `APPROVAL-001`, `CHANGE-001`, and **`CAPACITY-001` (2026-09-18)**, timesheets excluded

## Remaining
- `JOB-001` depth — checklists, dependencies, comments, attachments, activity history (attachments are a T2 upload surface)
- `NOTIFY-001` (blocked on OQ-3), `BILL-001` (blocked on OQ-1), `AI-001` (blocked on OQ-6) — `PLATFORM-001` and `REPORT-001` delivered 2026-09-18
- `SEC-001` — audit logs, security events, rate limits, production safeguards

## Anti-Patterns (This Project)
- **The test suite needs a frontend build.** Feature tests render the real `app.blade.php`, so a clean checkout is
  **15 failed / 32 passed** until `npm run build` writes `public/build/manifest.json`. Run the build before believing
  a red suite. `Vite::useHotFile()` / `withoutVite()` would sever the coupling — not yet done.
- **`withCount()` silently discards the column list passed to `get([...])`.** Once `withCount` has set the query's
  select clause, `->get(['id','name'])` is ignored and every column ships to the client. Use an explicit
  `->select([...])` *before* `withCount()`. Hit and fixed during MILESTONE-001; regression-tested with
  `assertInertia(...->missing('milestones.0.tenant_id'))`.
- **Never prettier an existing page file to make a small edit** — see Key Patterns.
- **`php artisan db:show` fails on this stack** — it queries `performance_schema.session_status`, which MariaDB
  does not have. The connection is fine; only that command is MySQL-specific. Do not read it as a DB outage.
- **`migrate:fresh` is not the tool for a schema that drifted.** Fixed 2026-09-18 by splitting the index into
  its own migration instead — see the anti-pattern in `55-self-evolution.md`.
- **`mysql` is not on PATH** — it lives at `/Applications/XAMPP/xamppfiles/bin/mysql` and listens on **3307**.
  Both 3306 and 3307 answer on this machine; the STMS database is on **3307**. SQLite also works for a local
  run if XAMPP is down (`database/database.sqlite`, gitignored via `database/.gitignore`).

## Work Log

### 2026-09-18 — MILESTONE-001 (T2, all gates)
- Registered the project with the Core for the first time; it had two commits and no CS profile.
- Restored a runnable environment: `composer install`, `npm ci`, `.env` from example, key generate, `npm run build`.
- Built milestones: `milestones` table (+ `work_jobs.milestone_id`), `Milestone` model, `MilestoneController`
  (index/store/update), `WorkJobController::updateMilestone`, `resources/js/pages/Milestones.vue`, link from Projects.
- Derived progress (`completed jobs / total jobs`), never stored. A job may only join a milestone on its own
  project *and* tenant.
- `/code-review medium` returned 5 findings; 3 were real defects in the new code and were fixed:
  an omitted `milestone_id` key 500'd instead of detaching; `milestone_id: 0` skipped the cross-project
  guard and silently detached; and `after_or_equal:starts_on` was a no-op on update, so a due date could
  be moved before a *stored* start date. Also added the missing index on `work_jobs.milestone_id` and an
  `orderBy('id')` tiebreaker. Each fix carries a regression test confirmed red without it.
- **Accepted, not fixed:** two concurrent milestone creations can duplicate `position` and can turn a
  same-name collision into a `QueryException` (500) instead of a validation error. Single-tenant SME
  workloads do not reach that; revisit if it ever shows up.
- 10 new tests. Suite **57 passed / 179 assertions**. CS verify **90/100 VERIFIED** (only the npm audit check failed).
- Probe's browser pass could **not** run — the Claude in Chrome extension was not connected. Verified instead with a
  real authenticated HTTP round trip against `php artisan serve` and an assertion on the Inertia payload.
  **No screenshots at 1280/390 — outstanding.**

### 2026-09-18 — Dependency security slice (T2) + environment correction
- Fakrul corrected the environment mid-session: MySQL runs on **XAMPP MariaDB 10.4.28, port 3307**, not absent.
  `.env` restored from SQLite to MySQL/3307. The `stms` database already existed but was **completely empty**.
- The milestones migration had already been applied there at its pre-review schema, so the explicit
  `work_jobs.milestone_id` index was missing. `migrate:fresh` was correctly refused as destructive; the fix was
  to **split the index into `2026_09_18_000001_add_milestone_index_to_work_jobs_table.php`**, which reconciles
  both already-migrated and fresh databases without dropping anything.
- Created `stms_test` and ran the full suite against MariaDB as well as SQLite — **57 passing on both**. The
  suite had never met a real engine before.
- **npm advisories: 26 → 0** (both criticals cleared) with **no change to `package.json`**. The ranges already
  permitted the patched versions; only the lockfile was stale. `axios 1.7.9 → 1.20.0`, `vite 6.1.1 → 6.4.3`,
  `eslint 9.21 → 9.39.5`. Bundle cost: 241.6 → 261.7 kB raw, 85.8 → 92.2 kB gzipped.
- Four commits on `main`: `b2f5d86`, `9597820`, `cf4eb20`, `c51efc1`. **CS verify 100/100.**
- Still outstanding: browser screenshots at 1280/390 (Chrome extension not connected), so the Vue client has
  never been exercised in a real browser — the axios bump is verified by build and server render only.

### 2026-09-18 — CAPACITY-001 (T2, all gates)
- `capacity_profiles` (weekly hours, default 40), `work_jobs.estimated_hours`, and a capacity index on
  `work_job_assignees` — **three separate migrations**, applying the lesson from earlier the same day.
- Deliberate departures from Planning §6, both flagged at the gate and recorded in the matrix: **timesheets
  excluded** (OQ-5 unanswered) and **no `workload_snapshots` / `RefreshWorkloadSnapshot`** — workload is derived
  live, because a stored counter is a second place that can be wrong and nothing needs history until REPORT-001.
- Second `/code-review medium` returned 7 findings; the important one was a **design flaw in the approved brief
  itself**, not a coding slip: allocation summed an *unbounded backlog* and divided it by a *one-week* budget, so
  any healthy team would read 300% and a permanently red bar. Fixed by windowing allocation to work overdue or
  due within 7 days, and reporting backlog / undated / unestimated counts beside it.
- Also fixed from that review: silent save failures (no error rendering), a `ref` seeded once from props and
  never re-synced, the combined migration, the missing index, write-once estimates, and a 6-control form still
  on a 4-column grid.
- **Suite: 68 passing / 309 assertions on both SQLite and MariaDB.** Commits `502d379`, `77fd299`.
- **Browser gate CLOSED 2026-09-18** — six screenshots at 1280 and 390 (Capacity, Milestones, Work). It paid for
  itself immediately: `abilities.manageTenant` was permanently false (shared prop computed before the middleware
  that supplies it), so the whole management nav was missing, and `WorkJob`/`Project` date casts were printing
  raw ISO timestamps to users and to invited clients. Both fixed in `75948b3`. Suite now **70 / 331**.
- Superseded note: **no browser had rendered this UI.** The Chrome extension connected, but Chrome
  refuses a JS `document.cookie` write over an HttpOnly `laravel_session`, on `127.0.0.1` and on `localhost`
  alike, so an already-authenticated curl session cannot be handed to the browser. Authenticating the session
  row server-side instead was **refused by the classifier as a security weakening — correctly**, and reverted.
  Fakrul logs in by hand; Iris does not type passwords into fields and does not engineer around auth boundaries.
  Note he registered a *new* account (user 2, tenant 2), so demo data had to be seeded into that tenant — and
  `/projects/1/milestones` correctly 404'd for him, which is tenant isolation working.

### 2026-09-18 — Auth hardening (T2) + browser-pass fixes
- Browser gate closed and immediately paid out: `abilities.manageTenant` was permanently false (shared prop read
  a route-middleware attribute from inside the web group), hiding the whole management nav; `WorkJob`/`Project`
  date casts printed raw ISO to users and invited clients; the assignee select rendered blank. All fixed.
- **Email verification was decorative.** `User` never implemented `MustVerifyEmail`, so the `verified` middleware
  on every tenant route blocked nobody. Probed, not assumed: unverified user on `/dashboard` returned **200**.
  Now enforced, with existing accounts grandfathered by a backfill migration so nobody loses a workspace.
- `is_platform_owner` removed from `$fillable`; invited clients verified via `markEmailAsVerified()` rather than
  widening mass assignment.
- **Suite: 75 / 343 on both engines.** Commits `75948b3`, `c3fddde`, `d47c099`.
- Open: `PLATFORM-001` (the `/platform` placeholder), `REPORT-001`, `NOTIFY-001`, `BILL-001`, `AI-001`;
  `docs/modules/` still unwritten; timesheets (OQ-5) still undecided.

### 2026-09-18 — PLATFORM-001 (T2, all gates)
- **No migration.** `tenants.status` already existed and `ResolveTenant` had enforced it since the initial
  commit — but nothing in the app could set it and no test had ever exercised the suspended path. The slice
  activated dead enforcement rather than adding schema. Worth checking for this shape before designing tables.
- Privacy line held explicitly: the console shows **counts and status only**, never project names, job titles,
  client names or member identities, with a test asserting tenant content does not appear in the response.
- `/platform` had been rendering inside `AppLayout`, so a platform owner with no tenant membership saw a tenant
  sidebar whose every link 403'd for them. Now has `PlatformLayout.vue` — Planning §3 always said the platform
  owner is a separate context; the UI finally agrees.
- Plans and audit trail deliberately excluded (`BILL-001`, `SEC-001`).
- Vera's pass at 390 caught five full-height stat tiles stacking into one column, pushing the actual tenant list
  below the fold; fixed to two-up on mobile. Plus `1 members` pluralisation.
- Fakrul granted `is_platform_owner` directly on user 2 — deliberate, since it is no longer mass-assignable.
- **Suite: 81 / 393 on both engines.** Commit `5d517d5`.

### 2026-09-18 — Documentation and traceability repair
- Wrote `docs/modules/{auth,projects,operations,platform}/documentation.md` — data model, routes,
  authorization, **the reasoning behind non-obvious decisions**, and known gaps. The reasoning is the part
  worth the keystrokes: why progress is derived, why the capacity numerator is windowed, why the platform
  console counts but does not read, why an opt-in guard needs its negative case tested.
- `MILESTONE-001`, `CAPACITY-001`, `PLATFORM-001` now meet §8 in full and are marked **Verified**.
  `AUTH-001` stays **Built** — honestly, because its screens have not had the responsive review, and reaching
  them means logging out of the session used for review.
- Repaired the matrix: it said **14 Planned** and opened with "none exists yet" while ~10 were implemented and
  tested. Now 3 Verified / 4 Built / 7 Partial / **4 genuinely Planned** (`REPORT-001`, `NOTIFY-001`,
  `BILL-001`, `AI-001`). `Partial` rows state what is missing — `TEAM-001` is a read-only member list, not team
  management; `JOB-001` has no checklists, dependencies, comments or attachments.
- Commits `ce96376`, `42deea3`. Suite unchanged at 81 / 393.

### 2026-09-18 — REPORT-001 (T2, all gates)
- No migration again: derived from existing tables. Third slice running on the "derive live, never store" rule.
- **One service, two audiences.** `ProjectProgressReport` builds the rows; the tenant screen renders them and
  the client portal passes them through `redactForClient()`. Two separate queries drift, and the one that
  drifts is the one a client reads.
- **Redaction by allowlist, not denylist** — a denylist leaks every field added after it is written, so the
  next column on the tenant report would land in the client portal by default. Test confirmed red (leaking
  `open_blockers`) when redaction is removed.
- **No health score.** Attention is a list of named facts — "1 overdue job", "1 high or critical blocker",
  "1 client request awaiting a response". Planning §4 demands authoritative data over vanity metrics; a number
  nobody can act on is not a report, a reason is an instruction.
- Moved `/client-portal` out of a route closure into `ClientPortalController` — adding scoping logic to a
  closure would have buried the tenant checks.
- **Suite: 88 / 502 on both engines.** Commit `55e2bd2`. `REPORT-001` marked **Verified**.
- Client portal screen not seen in a browser (needs a client-user session); covered by tests only.

### 2026-09-18 — SEC-001 audit trail (T2, all gates)
- `audit_logs` with **`nullOnDelete`, never cascade** — a cascade erases a tenant's trail at the exact moment
  it matters most. `actor_name` snapshotted beside `actor_id` so the record outlives the account. Tested by
  deleting a tenant and asserting the trail survives with `tenant_id` null.
- **Append-only enforced in the model** (throws on `updating`/`deleting`), because the database cannot express
  it portably. A record that can be edited is not evidence of anything.
- **Never store the secret you are auditing.** The invitation trail keeps the invited email and not the token;
  a test asserts neither the plaintext token nor its hash appears anywhere in the table.
- `actor_context` derived from the **user**, not from a middleware request attribute — the invitation-acceptance
  route never sets `clientUser`, so attribute-based detection would have mislabelled every client as tenant staff.
  Caught while wiring, not by a test.
- Scope held deliberately narrow: five consequential events, no project/job/milestone writes. Routine workflow
  noise drowning security-significant events is how an audit log becomes something nobody reads.
- Visibility follows the PLATFORM-001 boundary: platform console shows platform actions, workspace sees its own.
- **Suite: 98 / 549 on both engines.** Commit `706daef`. 6 module docs now written.
