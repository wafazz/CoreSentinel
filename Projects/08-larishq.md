# larisHQ — Agent/Stockist + Marketer/Sales Team Management & Ordering SaaS

> **Status**: Active build — PH01 and PH02 verified, PH03 next
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
- **Payment**: manual recording only, no gateway (D032)
- **Database**: `larishq` on MariaDB :3306, `mariadb` driver (D018)
- **Tenancy**: subdomain per HQ, shared schema + `tenant_id` (D002, D026)

## Key Patterns
- **Dynamic 1–8 level hierarchy** — `network_levels` + `network_members` adjacency list. Never `level_1_id..level_8_id` (D003). Cycle/depth by bounded recursive parent walk, no closure table (D004).
- **Level pricing as rows, costs as columns** — `product_prices` keyed by `network_level_id`; `hq_cost_price`/`product_cost_price`/`retail_price` on the variant (D013).
- **Dynamic marketing channels** — `marketing_channels` + `marketer_channel` pivot. FB/Google Ads are seeded rows, never code branches (D012).
- **Margin, not commission, for the network** — agents/stockists earn the price differential; no override engine exists (D014).
- **Snapshot everything that can drift** — order lines snapshot price + level (D011); commission entries snapshot rate + base (D017); orders snapshot channel (D039).
- **Fail closed on pricing** — a product with no price for a member's level is hidden, never falls back (D046).
- **`Gate::before` never answers a model-bound check** (D052) — it resolves bare ability names from the registry and returns null the moment a model is passed, so policies (and PH03's tenant check) can never be short-circuited.
- **A grant can never exceed the granter** (D053) — `User::canGrant()` gates role assignment and role authoring alike. Without it `staff.create` alone was full compromise.
- **One permission source for server and UI** — `auth.permissions` is a flat slug list; nav and buttons both filter through `usePermissions` (D054).

## Anti-Patterns (This Project)
- Never hardcode hierarchy depth, level names, or FB/Google as columns or enums.
- Never pay margin *and* an upline override on the same order — that pays the network twice (D014).
- Never expose `hq_cost_price` or `product_cost_price` to any portal payload (BR-25).
- `APP_TIMEZONE` is silently ignored on Laravel 12 — set the timezone in `config/app.php` and test it (D019, D034).
- `authorizeResource()` is dead on Laravel 12 — it calls `$this->middleware()`, which the base controller no longer has. Use `HasMiddleware`.
- The login route must be **named** `login` — `Authenticate::redirectTo()` returns null on Laravel 12 and the redirect comes from the handler's `route('login')` fallback.
- Never grant a blanket superuser through `Gate::before`; never add an `is_admin` flag (BR-04, guarded by a test).
- No Tailwind, ever (§42).

## Completed
1. **CS Init + verification** (2026-08-31) — environment verified, 37 open questions raised, `Planning.md` written: 18 phases, 148 tasks, 54 decisions, 29 business rules.
2. **PH01 Project Foundation** (2026-08-31, `e009ef4`) — Laravel 12.68 + Inertia 3.3.1 + Vue 3.5 + Bootstrap/AdminLTE, MariaDB and Redis verified, Tailwind removed and guarded. 8 tests.
3. **PH02 Authentication & RBAC** (2026-09-01, `56af2f4`) — session auth, 39-permission registry, 8 seeded roles, `Gate::before` + `BasePolicy`, staff and role CRUD, permission-aware nav. 48 tests, CS verify 100/100.

## Remaining
- PH03 Multi-Tenancy → PH18 Production Readiness (16 phases remaining, 2 of 18 complete)
- **Pending confirmation**: D043 (HQ Cost vs Product Cost definitions) — needed before PH12-T04.

## Carried into PH03
- `BasePolicy::allows()` is the single place the tenant check belongs — every ability already routes through it.
- The session cookie spans all of `*.larishq.test`, so tenant middleware must re-check the user against the resolved tenant on every request.
- `roles` gains `tenant_id` (unique widens to `tenant_id, slug`); `permissions` never does.
- `RoleTemplates::all()` is replayed per tenant on subscriber creation.

## Work Log
- **2026-09-01** — PH02 Authentication & RBAC, run at T2. Schema gated with Fakrul before any code. Review found and closed a real privilege escalation (`staff.create` alone could mint an HQ Owner and set its password) — D053. 48 tests / 136 assertions, pint and build clean, CS verify 100/100, E2E over real HTTP confirming Sales Staff 403 / HQ Owner 200.
- **2026-08-31** — CS init. Environment verified (PHP 8.4.10, MariaDB, Redis 8.4, Node 24). Full spec review surfaced 37 unspecified decisions. `Planning.md` created as the single traceable roadmap. Commission design resolved: margin-only for network (P1b override rejected), rate×base with five-step precedence for marketers (P2/P3/P4 accepted). Fakrul delegated the remaining 34 questions to IRIS; 33 answered and recorded as D018–D050. Laravel 13 recommended and declined — Fakrul reaffirmed Laravel 12; consequences recorded in D019.
