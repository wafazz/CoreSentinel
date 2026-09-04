# Daily Spend — Simple daily spending SaaS (multi-tenant personal expense tracker)

> **Status**: Built — Phases 1–8 delivered, 137 tests green
> **Last Updated**: 2026-08-29

## Business Context
- **Client**: own SaaS product (Codex Lure)
- **Status**: active
- **Priority**: medium
- **Revenue Model**: SaaS subscription — Free (limited) / Pro RM 9.90 per month
- **Deployed**: No

## Overview
- **Root**: `Desktop/Codex Lure/project/Daily Spend`
- **Stack**: Laravel 12 (see OQ-01) + PHP 8.4 + Inertia 3 + Vue 3.5 + TypeScript 5.9 + Vite 7
  + Bootstrap 5.3.8 + AdminLTE 4.9.1 + MariaDB 11.8.2
- **Type**: multi-tenant SaaS, single database, `user_id` ownership
- **Auth**: hand-written controllers on Laravel's native `Auth` / `Password` facades.
  No Breeze/Jetstream (dead paths), no Fortify (pulls `laravel/passkeys` for out-of-scope features).
  The official `laravel/vue-starter-kit` is **Laravel-13-only** as of 2026-08-28 and cannot be used on L12.
- **Currency**: MYR (per-user display setting; no per-row currency, no conversion)
- **Payment**: none in MVP — subscription state is owner-managed from the admin console
- **Database**: `daily_spend` / `daily_spend_test` on **127.0.0.1:3307, MariaDB 10.4.28**
  (`DB_CONNECTION=mariadb` — on 10.4 the driver is load-bearing, not cosmetic).
  The 11.8.2 instance on 3306 is a different install and is **not** what this project uses.

## Key Patterns
Pulled from `11-pattern-library.md`:
- **AdminLTE 4 safe/unsafe split** — SCSS + `PushMenu`/`Layout`/`ColorMode` are safe (they write
  to `document.body`, outside the framework root); `Treeview`/`CardWidget` are not. The admin
  sidebar here is six flat links, so nothing needs re-implementing.
- **Bootstrap + AdminLTE 4 through Vite** — `scss.loadPaths: ['node_modules']` is mandatory
  (AdminLTE treats Bootstrap as a peer and bare-imports it) plus `silenceDeprecations`.
- **Inertia shared props** — `Inertia::always()` on `auth`/`app`/`features`; a partial reload
  filters the whole prop bag including shared props.
- **Inertia props leak every model field** — models are never passed as props; explicit arrays only.
- **Inertia 3 `InertiaConfig` declaration merging** — set up day one, with the bare
  `import '@inertiajs/core'` or `declare module` replaces instead of augments.
- **Inertia 3 stale lazy-chunk 404s** — handle `vite:preloadError`; keep the previous
  `public/build` for a grace period after deploy.
- **Guarded Atomic Update in Eloquent** — recurring-expense generation advances `next_date` with
  a conditional `update()` and only the caller that gets `1` writes the transaction.
- **Forced first-login password change** — `spend:create-admin` with `$this->secret()`; the
  seeder refuses to run in production without real env credentials.
- **Dashboard metrics you do not have data for** — with no payment gateway, subscription revenue
  is labelled **Contracted MRR**, never presented as collected cash.
- **Route model binding traps** — no `getRouteKeyName()` override anywhere; bind on `id`.
- **MariaDB driver** — `DB_CONNECTION=mariadb`, not `mysql`.

Project-specific:
- **`transaction_date` is a `DATE`.** The user records a calendar day, not an instant. This
  removes timezone conversion from every report path and closes the PHP-vs-SQL day-bucket
  drift anti-pattern by construction.
- **Three-layer tenant isolation**: relationship-scoped queries → policies → ownership
  validation on every incoming foreign key. The third layer is the one people forget, and it
  is the one that stops User A tagging a spend with User B's private `category_id`.
- **Plan config is data, not code.** One Gate loop over `plans.features` and one
  `EnforceTransactionLimit` middleware. No plan name is read anywhere else in the codebase.

## Completed
1. Phase 0 Intake, Phase 1 Research (all versions verified live), Phase 2 Design
2. Phase 1 Foundation — Laravel 12.68 + Inertia 3.3 + Vue 3.5 + TS 5.9 + Vite 7 + Bootstrap
   5.3.8, Tailwind removed, 10 tables, hand-written auth, three role middlewares
3. Phase 2 Subscriber MVP — categories, payment methods, transactions CRUD + filters,
   Quick Add, receipts, dashboard, charts
4. Phase 3 Financial — monthly budget, per-category budgets (Pro), recurring expenses +
   scheduled command, spending calendar
5. Phase 4 Reports — four groupings, filters, streamed CSV + XLSX
6. Phase 5 SaaS — plans, subscriptions, transaction limit, feature gates
7. Phase 6 Admin — AdminLTE console: dashboard, users, subscriptions, plans, default
   categories, settings
8. Phase 7 PWA — manifest, workbox service worker, install prompt, update prompt, icons
9. Phase 8 Testing & hardening — **137 tests / 380 assertions**, 24-test tenant isolation
   matrix, Pint clean, `vue-tsc` clean, `composer audit` + `npm audit` clean

**Verified end-to-end through a live server**: register → login → Quick Add → dashboard
updates → owner console; both role gates return 403.

## Remaining
- Mail provider before launch (`OQ-08`) — password reset works but delivers to the log
- Deploy: VPS, TLS (mandatory — no service worker over plain HTTP), `schedule:run` cron
- Payment gateway when subscriptions need to actually bill
- Laravel 13 upgrade when convenient — `inertia-laravel` already accepts `^13.0`

## Anti-Patterns (This Project)
- Never `CURDATE()` / `NOW()` / `DATE(created_at)` in a report aggregate — anchor every bucket
  and its zero-filled series to one PHP date computed in the user's timezone.
- Never sum money by looping Eloquent models in PHP. PDO returns `DECIMAL` as a **string** and
  the first arithmetic operator coerces it to a float. Sum in SQL; use `bcsub()` for the one
  subtraction that must happen in PHP.
- Never pass an Eloquent model as an Inertia prop.
- Never test this app on SQLite — it lies about foreign keys, `DECIMAL`, and concurrency, and
  all three are load-bearing here.
- Never let a `category_id` or `payment_method_id` pass validation on `exists` alone.

## Work Log

### 2026-08-29 — Built (Phases 1–8)
- 25 requirements, 68 routes, 10 tables, 137 tests. Traceability matrix in `Planning.md` §1
  carries real paths; all 125 verified to exist on disk.
- **Four real bugs the tests and the demo run caught**, all now in the Pattern Library and
  `55-self-evolution.md`: `authorizeResource()` is dead on Laravel 12; `APP_TIMEZONE` is
  silently ignored by the slim `config/app.php`; a `DATE` compared as an instant meant a
  due-today recurring expense never fired; `update()` on a non-fillable privilege column
  silently no-ops, so admin suspension had never worked.
- Deviations from plan recorded in `Planning.md` §25.

### 2026-08-28 — Init
- Ran CoreSentinel Init Protocol on an empty directory.
- Scout verified: Laravel 12.68.0 (last 12.x; bug-fix window closed 2026-08-13) vs 13.29.0
  current; `inertiajs/inertia-laravel` 3.3.1 accepts `^11.35|^12.0|^13.0`; `@inertiajs/vue3`
  and `@inertiajs/vite` 3.7.0; Vue 3.5.42; Vite 7.3.6 (skeleton default) / 8.2.2;
  `laravel-vite-plugin` 2.1.0 — 3.x peers Vite 8 only; TypeScript `latest` is now **7.0.2**,
  5.x line at 5.9.3; `vue-tsc` 3.3.11; Bootstrap 5.3.8; `bootstrap-icons` 1.13.1;
  `admin-lte` 4.9.1; `vite-plugin-pwa` 1.3.0; `chart.js` 4.5.1 + `vue-chartjs` 5.3.4;
  `maatwebsite/excel` 4.0.2 (php ^8.3, illuminate ^12|^13).
- Confirmed `laravel/vue-starter-kit` now requires `laravel/framework ^13.17` — unusable on L12.
- Authored `Planning.md` (25 sections, REQ-01..REQ-25, 16 recorded assumptions, 8 open questions)
  and `docs/documentation.md`. **No application code written** — spec §38 requires approval first.
