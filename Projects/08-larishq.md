# larisHQ — Agent/Stockist + Marketer/Sales Team Management & Ordering SaaS

> **Status**: Active build — PH01–PH12 verified, PH13 Targets next. Zero open questions.
> **Last Updated**: 2026-09-01

## Business Context
- **Client**: personal project (own SaaS)
- **Status**: active
- **Priority**: high
- **Revenue Model**: SaaS subscription (HQ Subscribers)
- **Deployed**: No

## Overview
- **Root**: `Desktop/Codex Lure/project/SaaS - New Version AMS`
- **Stack**: Laravel 12.68 + Inertia 3.3.1 + Vue 3.5 + Bootstrap 5.3.8 + AdminLTE 4.9.1 + MariaDB + Redis 8.4
- **Type**: Multi-tenant SaaS (agent/stockist network, marketers, ordering)
- **Auth**: Laravel first-party session auth, built PH02. Separate `platform_users` table + guard for Platform Owner (D024, PH03); one tenant-scoped `users` table for HQ staff, agents, stockists, marketers (D025)
- **Currency**: MYR, integer sen (D010, D034)
- **Payment**: manual recording only, no gateway (D032). Built PH11: refunds are negative amounts in the same table (D077), one invariant `0 <= sum <= order.total`, outstanding always computed
- **Database**: `larishq` on MariaDB :3306, `mariadb` driver (D018)
- **Tenancy**: subdomain per HQ, shared schema + `tenant_id` (D002, D026). Built PH03: `TenantScope` on reads, `BelongsToTenant` refuses tenant-less writes, Platform Owner on `admin.` with its own guard.

## Key Patterns
- **Dynamic 1–8 level hierarchy** — `network_levels` + `network_members` adjacency list, built PH05. Never `level_1_id..level_8_id` (D003). Cycle/depth by bounded recursive parent walk, no closure table (D004). The 1–8 bound is enforced in the configurator, over HTTP, and by a MariaDB CHECK. Strict adjacency (D027) makes cycles structurally impossible; the walk is defence in depth.
- **Level pricing as rows, costs as columns** — `product_prices` keyed by `network_level_id`; `hq_cost_price`/`product_cost_price`/`retail_price` on the variant (D013). Built PH07. Costs are `$hidden` on the model so BR-25 fails closed; `withCosts()` reveals them and makes every exposure greppable.
- **D043 confirmed**: product cost = supplier/manufacturing; HQ cost = landed (freight, duty, packaging). D044 pays commission on the landed margin.
- **Dynamic marketing channels** — `marketing_channels` + `marketer_channel` pivot, built PH06. FB/Google are rows seeded from **config**, never code branches (D012). A guard test greps app/ and resources/js/ for their names and requires zero hits. Seeded once, never re-synced (D068).
- **Margin, not commission, for the network** — agents/stockists earn the price differential; no override engine exists (D014). Built PH12: `commission_entries` has no column that could hold a network member, so the rule is structural rather than remembered.
- **Commission precedence is five steps, one scope per rule** — product → category → marketer → team → HQ default (BR-27), with a CHECK forbidding two scopes and a generated `scope_key` carrying uniqueness.
- **Stock: one ledger, guarded decrements** — `StockLedger` is the only thing that changes a quantity, and every change writes a movement in the same transaction. Decrements are `WHERE quantity >= ?` inside the UPDATE, so overselling is impossible rather than unlikely (D030). Locations are warehouses *and* network members (D071).
- **Snapshot everything that can drift** — order lines snapshot price + level (D011) **and landed cost** (D076); commission entries snapshot rate + base (D017); orders snapshot channel (D039) and the marketer's team. Built in PH10 and verified by changing the source values afterwards.
- **Fail closed on pricing** — a product with no price for a member's level is hidden, never falls back (D046).
- **`Gate::before` never answers a model-bound check** (D052) — it resolves bare ability names from the registry and returns null the moment a model is passed, so policies (and PH03's tenant check) can never be short-circuited.
- **A grant can never exceed the granter** (D053) — `User::canGrant()` gates role assignment and role authoring alike. Without it `staff.create` alone was full compromise.
- **One permission source for server and UI** — `auth.permissions` is a flat slug list; nav and buttons both filter through `usePermissions` (D054).
- **Reads fall back open, writes fail closed** — `TenantScope` adds no filter with no tenant bound (console, platform console), but `BelongsToTenant` throws on create. An unscoped read is caught by a test; an unscoped write is caught by nobody.
- **Roles are replayed per tenant** by `TenantProvisioner`, never seeded once globally (D051).
- **Declared registries over free-form stores** — permissions (D051) and settings (D060) both live in `App\Support`, with the table holding only what an HQ has changed. An undeclared key throws rather than reading as null.

## Anti-Patterns (This Project)
- Never hardcode hierarchy depth, level names, or FB/Google as columns or enums.
- Never pay margin *and* an upline override on the same order — that pays the network twice (D014).
- Never expose `hq_cost_price` or `product_cost_price` to any portal payload (BR-25).
- `APP_TIMEZONE` is silently ignored on Laravel 12 — set the timezone in `config/app.php` and test it (D019, D034).
- `authorizeResource()` is dead on Laravel 12 — it calls `$this->middleware()`, which the base controller no longer has. Use `HasMiddleware`.
- The login route must be **named** `login` — `Authenticate::redirectTo()` returns null on Laravel 12 and the redirect comes from the handler's `route('login')` fallback.
- Never grant a blanket superuser through `Gate::before`; never add an `is_admin` flag (BR-04, guarded by a test).
- Never add a tenant-owned model without `use BelongsToTenant` — nothing enforces it and the model is silently unscoped.
- Never put `nullable` before a custom rule that has to decide what *null* means — every rule after `nullable` is skipped and the branch becomes dead code. Use `present`.
- Never enforce a SUM constraint with a single-row guard — lock the parent and sum under the lock (PH11), unlike the single-row `WHERE quantity >= ?` that works for stock (PH08).
- Never let a factory generate data the schema can reject — `fake()->jobTitle()` overflows a varchar(64) slug and produces an intermittent failure.
- Never trust `belongsToMany`'s pivot-name guess when the schema names the table differently — it guesses alphabetically. (Cost two debugging rounds: PH06 and PH09.)
- Never write `$defaults + $overrides` in PHP — `+` keeps the left operand's keys and silently drops the overrides.
- Never rely on a multi-column unique index that includes a nullable column in MariaDB — NULLs are distinct, so duplicates pass. Give the either/or its own table.
- Never call `refreshApplication()` inside a test — it leaves a `RefreshDatabase` transaction open and the next `PermissionSeeder` upsert dies on a 1205 lock-wait. Use a Pest dataset.
- Never write a source-grep guard test without stripping comments first — the prose explaining the rule contains the words the rule forbids. This bit twice (PH02 `is_admin`, PH06 `facebook`).
- Never delete a network member with any child, or a populated/non-deepest level (D064, D029).
- Never `updateOrCreate(['tenant_id' => …])` — `tenant_id` is deliberately not fillable, so it is dropped and the write is refused. `firstOrNew` + explicit assignment.
- Never `$request->user()` once a second guard exists — name the guard (D058).
- Never use a dotted key in a validation rule path without escaping the dots — the rule silently validates a nested path that does not exist.
- Never run `RoleSeeder` without `PermissionSeeder` after adding permissions — new slugs are skipped and roles keep the old set.
- No Tailwind, ever (§42).

## Completed
1. **CS Init + verification** (2026-08-31) — environment verified, 37 open questions raised, `Planning.md` written: 18 phases, 148 tasks, 54 decisions, 29 business rules.
2. **PH01 Project Foundation** (2026-08-31, `e009ef4`) — Laravel 12.68 + Inertia 3.3.1 + Vue 3.5 + Bootstrap/AdminLTE, MariaDB and Redis verified, Tailwind removed and guarded. 8 tests.
3. **PH02 Authentication & RBAC** (2026-09-01, `56af2f4`) — session auth, 39-permission registry, 8 seeded roles, `Gate::before` + `BasePolicy`, staff and role CRUD, permission-aware nav. 48 tests, CS verify 100/100.
4. **PH03 Multi-Tenancy** (2026-09-01, `ce3f6e2`) — subdomain tenancy, global scope + write refusal, tenant middleware chain, Platform Owner console on its own guard and table. 78 tests, CS verify 100/100.

## Remaining
- PH13 Targets → PH18 Production Readiness (6 phases remaining, 12 of 18 complete)
- **Owed forward**: PH09 `marketer_customer` (PH06-T05) · PH10-T01 `marketing_channel_id` snapshot (PH06-T12) · PH10 must refuse deleting a variant an open order references · PH15 must assert BR-25 against real portal endpoints · PH18 needs `storage:link`.
- **Pending confirmation**: D043 (HQ Cost vs Product Cost definitions) — needed before PH12-T04.

## Carried forward
- Every new tenant-owned model must `use BelongsToTenant`; each phase's isolation test is the only thing that catches a model that forgets.
- Deploy (PH18): wildcard DNS, wildcard TLS, `SESSION_SECURE_COOKIE=true`.
- Password reset is unbuilt and now needs the tenant from the reset link — email is unique per tenant, not globally (D056).

## Work Log
- **2026-09-02 (k)** — PH12 Commission at T2, the most intricate phase. Five-step precedence tested step by step; snapshotted ledger proven by changing the rule afterwards; clawback covering cancel, return and return-after-payout. Two recorded departures from the accepted proposal (D078 per-order override, D079 base floored at zero), both with reasons. 304 tests, CS verify 100/100.
- **2026-09-02 (j)** — PH11 Payments at T2. Honoured D031's dangling pointer to this phase by making refunds negative payments (D077). One invariant at both ends; sum constraint enforced by locking the parent, not by a single-row guard. Refusals name the real outstanding figure. 270 tests, CS verify 100/100.
- **2026-09-02 (i)** — PH10 Ordering at T2. The convergence phase: D011 + D076 snapshots, D030 stock at Confirmed, D031's eight statuses each gated by its own §6 permission, D039 channel. Verified immutability by changing prices afterwards, in a test and live. Paid off PH06-T12, PH07's variant guard and PH09's isReferenced. T04 partial (portals are PH15). Second intermittent test failure found and fixed. D075–D076. 250 tests, CS verify 100/100.
- **2026-09-02 (h)** — PH09 Customers at T2. Data minimisation enforced by a column-list guard test rather than by intention. D074 removal (delete if unused, anonymise if referenced) chosen by Fakrul at the gate. Marketer scoping proven live. 221 tests, CS verify 100/100.
- **2026-09-02 (g)** — PH08 Inventory at T2. Flagged member-held stock as beyond §13 at the gate; Fakrul chose the wider scope, recorded as a deliberate extension (D071). Guarded conditional decrements make overselling impossible; reconciliation verified in tests and live. D071–D073. 211 tests, CS verify 100/100.
- **2026-09-02 (f)** — PH07 Catalogue and Level Pricing at T2. D043 confirmed at the gate, closing the project's last open question. Pricing verified at 1/3/8 levels and live with an 8-column grid. D045 and D046 both confirmed over real HTTP. Diagnosed the intermittent suite failure that had been open since PH04: a 1205 lock-wait on the `permissions` upsert caused by an in-test `refreshApplication()`. D069–D070. 188 tests, CS verify 100/100.
- **2026-09-01 (e)** — PH06 Marketers/Teams/Channels at T2. Four channel conditions tested literally, condition 4 inventing a channel at runtime inside the test. Two tasks deferred with the phase that owes them named (T05→PH09, T12→PH10) rather than faked. One real bug: default-channel sync resurrected deleted channels while its comment claimed otherwise. D066–D068. 152 tests, CS verify 100/100. An intermittent suite failure remains open.
- **2026-09-01 (d)** — PH05 Dynamic Hierarchy at T2. Depth is data in the service, validator, tree component and tests; proven at 1, 2 and 8 levels. One real bug: `nullable` before a custom rule made the "parent required below top level" branch dead code, allowing an orphaned member. D062–D065. 132 tests, CS verify 100/100, depth-8 tree rendered over real HTTP.
- **2026-09-01 (c)** — PH04 HQ Business Setup at T2. Settings built as a declared registry (D060), business profile split from `tenants` (D059), territories flat (D061). One real bug: dotted registry keys collide with Laravel's dot notation, so settings validation checked a path that never existed and saving over HTTP was broken — no test had covered the endpoint, only the repository. 100 tests, CS verify 100/100.
- **2026-09-01 (b)** — PH03 Multi-Tenancy at T2. Schema gated first. Three defects found by running it, not by reading it: route middleware runs after `Authenticate` (framework priority list), `Route::domain('{tenant}...')` passes the subdomain as every controller's first argument, and `auth:platform` makes `platform` the default guard so `$request->user()` returned a `PlatformUser` into `permissionSlugs()`. D057/D058. 78 tests, CS verify 100/100, E2E across four hosts.
- **2026-09-01 (a)** — PH02 Authentication & RBAC, run at T2. Schema gated with Fakrul before any code. Review found and closed a real privilege escalation (`staff.create` alone could mint an HQ Owner and set its password) — D053. 48 tests / 136 assertions, pint and build clean, CS verify 100/100, E2E over real HTTP confirming Sales Staff 403 / HQ Owner 200.
- **2026-08-31** — CS init. Environment verified (PHP 8.4.10, MariaDB, Redis 8.4, Node 24). Full spec review surfaced 37 unspecified decisions. `Planning.md` created as the single traceable roadmap. Commission design resolved: margin-only for network (P1b override rejected), rate×base with five-step precedence for marketers (P2/P3/P4 accepted). Fakrul delegated the remaining 34 questions to IRIS; 33 answered and recorded as D018–D050. Laravel 13 recommended and declined — Fakrul reaffirmed Laravel 12; consequences recorded in D019.
