# E-Commerce Catalog System — Laravel 12 + Inertia 3 + React 19 + TS on Bootstrap/AdminLTE

> **Status**: Planning — awaiting approval. No implementation started.
> **Last Updated**: 2026-08-14 (retargeted Laravel 13 → **12** after environment decision)
> **Learn Mode**: `[LEARN]` ACTIVE — first project in this stack
> **Runtime is constrained**: XAMPP PHP 8.2.12 caps this project at Laravel 12. PHP 8.2 EOL 2026-12-31.

## Business Context
- **Client**: personal project
- **Status**: active (planning)
- **Priority**: medium
- **Revenue Model**: e-commerce
- **Deployed**: No

## Overview
- **Root**: `C:\Users\fakrul.hakim\Desktop\Test\ecommerce test` *(relocation to `C:\xampp\htdocs\shop` recommended — deep path with a space, and matches the other XAMPP projects)*
- **Stack**: Laravel **12** · Inertia 3 · React 19 · TypeScript 5.9 · Vite 8 · Bootstrap 5.3.8 · AdminLTE 4.3.1 · **MariaDB 10.4.32**
- **Type**: e-commerce catalog (admin-first; storefront scope undecided)
- **Environment**: XAMPP — Apache + **PHP 8.2.12** + MariaDB 10.4.32. Composer not yet installed.
- **Auth**: undecided — no starter kit in use, so nothing ships by default; Fortify if required
- **Currency**: undecided (single-currency assumed)
- **Payment**: none in scope
- **Database**: MariaDB 10.4.32 — `DB_CONNECTION=mariadb`, `utf8mb4_unicode_ci` (MySQL 8's `utf8mb4_0900_ai_ci` does not exist in MariaDB)

## Key Patterns
Pulled into `11-pattern-library.md` under "Laravel 13 + Inertia 3 + React 19 + TypeScript". Project-specific:

- **Prop boundary**: every Inertia prop is a `spatie/laravel-data` DTO. Never a raw Eloquent model — Inertia serializes any `Arrayable` via `toArray()`, exposing every non-`$hidden` column, `$appends` accessor and loaded relation.
- **Persistent AdminLTE shell**: `AdminLayout` assigned via `Page.layout`, never rendered inside a page. Only `<main class="app-main" scroll-region>` swaps on navigation.
- **`Inertia::always()` on `auth` + `flash`**: partial reloads filter the entire prop bag including shared props.
- **`Inertia::shareOnce()`** for the sidebar menu tree and lookups — resolved once, then omitted from every subsequent payload.
- **`option_signature`** on `product_variants`: sorted `option_value_id`s joined by `.`, unique per product. Turns "find the Red/L variant" into one index seek and structurally prevents duplicate option combinations.
- **Rollup columns** on `products` (`min_price_minor`, `max_price_minor`, `in_stock`, `variants_count`, `default_variant_id`), maintained by a `ProductVariant` observer. They exist so the listing page never needs `withMin('variants', …)` — a correlated subquery per row that destroys pagination.
- **Soft-delete unique guard**: `deleted_at_key TIMESTAMP AS (COALESCE(deleted_at,'1970-01-01')) VIRTUAL` + `UNIQUE(slug, deleted_at_key)`. Plain `UNIQUE(slug, deleted_at)` is wrong — MySQL treats NULLs as distinct, so two live rows would both be allowed.

## Completed
1. Project inspection — empty directory, not a git repo
2. Learn Protocol trigger check — both triggers fired
3. Research Sprint (3 parallel agents, all versions verified live 2026-08-14)
4. `Planning.md` + `session-memory.md` + this profile

## Remaining
- ⏸ Approval of `Planning.md` §9
- Phase 0 Environment (BLOCKED — no PHP toolchain on the machine)
- Phases 1–10 per `Planning.md` §6

## Anti-Patterns (This Project)
- **Never** pass a raw Eloquent model as an Inertia prop.
- **Never** `->withMin('variants','price_minor')` or `->with('variants.optionValues.option')` on the catalog listing — that's what the rollup columns are for.
- **Never** read-modify-write stock. Atomic conditional `UPDATE … WHERE stock_quantity >= :qty`, then check affected rows.
- **Never** import AdminLTE's `Treeview`, `SidebarSearch` or `CardWidget` — they own DOM inside the React tree.
- **Never** convert AdminLTE/Bootstrap SCSS to `@use`. Both ship `@import`; Sass hasn't removed it (3.0.0, unshipped) and Bootstrap's docs say the deprecation warnings can be ignored.
- **Never** use `^` on the `admin-lte` version — 5 releases in 3 months, API still moving.
- **Never** assume a `422` from a validation failure — Laravel redirects 302 and Inertia fires `onError()`.
- **Never** deploy without `php artisan route:clear` **before** `npm run build` — Wayfinder generates from the cached route table and a stale one silently produces wrong route files.
- **Never** set `DB_CONNECTION=mysql` here — the DB is MariaDB and Laravel's schema grammar would emit MySQL-8-specific SQL. Use the `mariadb` driver.
- **Never** use `utf8mb4_0900_ai_ci` — that collation does not exist in MariaDB.
- **Never** reference Laravel 13 APIs: `PreventRequestForgery` (12 uses `VerifyCsrfToken`, 419 not 403), `php artisan dev` / `DevCommands`. `Model::automaticallyEagerLoadRelationships()` needs 12.8+.
- **Never** assume the official React starter kit is available — it requires `laravel/framework ^13.17` + PHP ^8.3. This project hand-wires Inertia.

## Environment Constraint (decided 2026-08-14)
XAMPP stays as-is — PHP **8.2.12**, MariaDB **10.4.32** — to avoid disturbing ARMS / codexlure / thread.
That caps the project at **Laravel 12** and pins several packages back a major (`kalnoy/nestedset` 6.0.7,
`eloquent-sluggable` 12.x, `laravel-query-builder` 6.x, `laravel-permission` 7.x), because their current
majors require PHP ^8.3. XAMPP for Windows cannot go higher — the download page offers only 8.0.30 /
8.1.25 / 8.2.12 and the last Windows build was November 2023.

**Runway**: PHP 8.2 is fully EOL **2026-12-31**; Laravel 12 left bug-fix support 2026-08-13 (security → 2027-02-24).
Keep the codebase Laravel-13-ready so the eventual move is a version bump, not a rewrite. **Revisit before December 2026.**

## Work Log

### 2026-08-14 — Planning & Research Sprint
- Learn Mode ON: stack absent from `11-pattern-library.md` and from the `05-init-protocol.md` recommendation table.
- 3 parallel research agents. Findings corrected two major-version assumptions in the brief (Laravel 13 not 12; Inertia 3 not 2) and surfaced a hard blocker: no `php`/`composer`/`laravel` on PATH.
- Wrote `Planning.md` (11 sections), `session-memory.md`, this profile; added a stack section to `11-pattern-library.md`.
- **Stopped before implementation as instructed.** Nothing installed, scaffolded or executed against the project.
- Open decisions recorded in `Planning.md` §9 — PHP environment (Herd Pro $99/yr vs free Laragon), project relocation, and four scope questions the brief did not answer (auth, storefront, cart/orders, currency).
