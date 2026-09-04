# larisHQ — Agent/Stockist + Marketer/Sales Team Management & Ordering SaaS

> **Status**: Active build — PH01–PH16 verified (421 tests), PH17 QA & Security next. Zero open questions.
> **Last Updated**: 2026-09-04

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
- **Roles are replayed per tenant** by `TenantProvisioner`, never seeded once globally (D051). That method rewrites *every* template's name, description and permissions, so it is safe only at provisioning time — a runtime call to heal one missing role would revert an HQ's customised roles.
- **Console and portal are two surfaces, one login table** (D086) — `Permissions::consoleSlugs()`/`portalSlugs()` split the registry; a user is one or the other, never both. Most of the enforcement was free: D053's `canGrant` already filters the role editor and the staff role picker, and no console user holds a portal slug.
- **A portal user's subject never appears in a URL** (D083) — `PortalContext` is bound by middleware from the session, so a portal route takes no member, marketer or location parameter and IDOR is unrepresentable rather than guarded against.
- **§22 is proven by enumerating the route table** (D085), not a hand-written list, plus a non-empty assertion — the failure mode of an enumerated guard is that it silently enumerates zero. It caught a real regression in the very next phase.
- **Declared registries, now four** — permissions (D051), settings (D060), audited actions (D087), notified events (D089). Each is data a test can walk, and each throws on an undeclared key rather than silently doing nothing.
- **An audit is not a notification** (D089) — one records what an administrator may need to reconstruct, the other interrupts somebody. Deriving one list from the other produces an inbox nobody reads.
- **A platform act belongs to no subscriber** (D090) — nullable `tenant_id` scopes it correctly for free: invisible to every HQ, visible on the console that binds no tenant.
- **Declared registries over free-form stores** — permissions (D051) and settings (D060) both live in `App\Support`, with the table holding only what an HQ has changed. An undeclared key throws rather than reading as null.

## Anti-Patterns (This Project)
- Never hardcode hierarchy depth, level names, or FB/Google as columns or enums.
- Never pay margin *and* an upline override on the same order — that pays the network twice (D014).
- Never expose `hq_cost_price` or `product_cost_price` to any portal payload (BR-25).
- Period boundaries must be computed in `config('app.timezone')`, never UTC — 00:30 on the 1st in KL is the previous month in UTC, and a sale silently lands in the wrong target period.
- `APP_TIMEZONE` is silently ignored on Laravel 12 — set the timezone in `config/app.php` and test it (D019, D034).
- `authorizeResource()` is dead on Laravel 12 — it calls `$this->middleware()`, which the base controller no longer has. Use `HasMiddleware`.
- The login route must be **named** `login` — `Authenticate::redirectTo()` returns null on Laravel 12 and the redirect comes from the handler's `route('login')` fallback.
- Never grant a blanket superuser through `Gate::before`; never add an `is_admin` flag (BR-04, guarded by a test).
- Never add a tenant-owned model without `use BelongsToTenant` — nothing enforces it and the model is silently unscoped.
- Never put `nullable` before a custom rule that has to decide what *null* means — every rule after `nullable` is skipped and the branch becomes dead code. Use `present`.
- Never enforce a SUM constraint with a single-row guard — lock the parent and sum under the lock (PH11), unlike the single-row `WHERE quantity >= ?` that works for stock (PH08).
- Never subtract one unsigned column from another in SQL — it underflows with "BIGINT UNSIGNED out of range" instead of going negative. Cast every operand, including any multiplier.
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
- Never write a revoke without its restore — keeping the linkage on purpose (D063) makes the grant path refuse to run again, so revoke becomes permanent unless something explicitly undoes it.
- Never notify before the write commits — `changeStatus` and `Checkout::place` each commit their own transaction, so a notify placed before them can announce something that then fails.
- Never leave a request-scoped singleton with no reset — bind it to the user or tenant it was resolved for; `PortalContext` is filled only on portal routes, so nothing cleared it on the way out.
- Never let one surface total money differently from another — put the definition on the model (`earned()`), not in each screen.
- Never re-run `RoleSeeder` on a live tenant to deliver a new permission — it rewrites every template and reverts HQ customisations. `OwnerPermissionSeeder` (D091) syncs only HQ Owner, where a full sync is definitionally correct.
- Never let a source-grep guard match a substring — `expo` matched `export` in four files. Word boundaries, and comments stripped. Third instance in this project after `is_admin` and `facebook`.
- Never order a list by `created_at` alone — it has one-second resolution, and a UUID primary key gives no tiebreak, so the list reshuffles on every load. PH05 solved this for audits; PH16 hit it again for notifications.
- Never narrow a *list* and think you have narrowed a *resource* — `StaffController::index` got `console()` while the route binding still resolved any user, which was a full privilege escalation. The list query and the model binding are two separate doors.
- Never write `where($column, $model?->getKey())` — `?->` yields null, Laravel compiles `where(col, null)` to `IS NULL`, and a nullable FK column (D063) then matches. It is a null *value*, not a null *guard*.
- Never repeat another method's docblock as your justification for calling it — read what it does. `syncRoles()` says it leaves customisations alone; it does not.
- Never split one intent across two transactions — `Checkout::place()` commits its own, so a failing follow-up transition leaves a persisted draft the caller promised would not exist.
- Never let one login carry two portal identities — the shared prop and the controller disagreed on precedence, so the nav and the page rendered different people.
- No Tailwind, ever (§42).

## Completed
1. **CS Init + verification** (2026-08-31) — environment verified, 37 open questions raised, `Planning.md` written: 18 phases, 148 tasks, 54 decisions, 29 business rules.
2. **PH01 Project Foundation** (2026-08-31, `e009ef4`) — Laravel 12.68 + Inertia 3.3.1 + Vue 3.5 + Bootstrap/AdminLTE, MariaDB and Redis verified, Tailwind removed and guarded. 8 tests.
3. **PH02 Authentication & RBAC** (2026-09-01, `56af2f4`) — session auth, 39-permission registry, 8 seeded roles, `Gate::before` + `BasePolicy`, staff and role CRUD, permission-aware nav. 48 tests, CS verify 100/100.
4. **PH03 Multi-Tenancy** (2026-09-01, `ce3f6e2`) — subdomain tenancy, global scope + write refusal, tenant middleware chain, Platform Owner console on its own guard and table. 78 tests, CS verify 100/100.

## Remaining
- PH17 QA & Security → PH18 Production Readiness (2 phases remaining, 16 of 18 complete)
- **Owed forward**: PH15-T04's visual mobile/tablet browser check was never run (extension not connected) — carry into PH17 · `DevTenantSeeder` does not create the two portal logins · PH18 needs `storage:link` · `app.js` eagerly globs every page, so console users download the portal bundle too · **`audit_logs` and `notifications` have no retention policy** and PH16 adds a row per sign-in — PH18 owes a window · password reset is still unbuilt, which is why D036's second email does not exist · the deploy runbook must name `OwnerPermissionSeeder` (D091).

## Carried forward
- Every new tenant-owned model must `use BelongsToTenant`; each phase's isolation test is the only thing that catches a model that forgets.
- Deploy (PH18): wildcard DNS, wildcard TLS, `SESSION_SECURE_COOKIE=true`.
- Password reset is unbuilt and now needs the tenant from the reset link — email is unique per tenant, not globally (D056).

## Work Log
- **2026-09-04 (o)** — PH16 Notifications & Audit at T2. Found `audit_logs` had been written to since PH05 with **no screen that could open it**, and that Platform Owner actions were **entirely unauditable** — `user_id` points at `users`, and the platform console binds no tenant, so `BelongsToTenant` refused the write. Both fixed (D090), which required teaching that trait to tell "unset" from "explicitly null". Two more registries declared (D087 audited actions, D089 notified events), both derived because §24 and §25 did not survive planning — D087 taken to the gate rather than guessed, since PH17 reviews against it. Three defects found by running it: an HQ Owner 403 on their own audit screen (D091), a 500 on publish, and a non-deterministic inbox order. PH15's route guard caught a §22 regression in this phase, exactly as designed. Then `/code-review` returned **11 findings across PH15 and PH16** on a tree that was already green and verified — two severe, including a revoke that could never be undone and which a PH15 test had blessed. 421 tests, CS verify 100/100. D087–D091.
- **2026-09-03/04 (n)** — PH15 Portals at T2. The first phase needing **no migration**: PH05–PH14 had already built every column. Built two portals on one `/portal` prefix, with the subject bound from the session and absent from every URL (D083) — proven live by a checkout carrying another member's id that booked to the right member at the right price. §22 enforced by enumerating the route table (D085) rather than listing routes by hand. Paid PH10-T04, PH12-T10, BR-25 and D071. **Four defects the green suite did not catch**: the portal's "Place order" produced an invisible draft; `ReportScope` narrowed only for marketers, so a member would have seen every member's margin; six `v-html` sinks reintroduced after the console deliberately removed them; and — found by `/code-review` after everything looked finished — a privilege escalation letting the HQ staff screen hand a network member the whole console, plus a self-healing call that would have reverted customised roles, plus `?->` inside a query builder silently returning nothing. The phase also shipped portals **no HQ could open** until grant/revoke were added: `issueLogin()` had had no caller since PH05. 390 tests, CS verify 100/100. D083–D086.
- **2026-09-02 (m)** — PH14 Reports at T2. Paid D014's debt via D048 Indicative Margin. Found D048 assumed data the schema lacked (D082 adds the retail snapshot), then live data found an unsigned-underflow bug the tests had missed. Scoping applied once and asserted on the export as well as the screen. 345 tests, CS verify 100/100.
- **2026-09-02 (l)** — PH13 Targets at T2. Boundary correctness in the configured timezone tested at every edge; D041 enforced by a generated-column unique index on the *computed* period, proven live. Achievement computed not stored (D080), counted by placed_at (D081). Defines the period concept D078 deferred. 331 tests, CS verify 100/100.
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
