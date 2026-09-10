# RezekiHUB — SaaS income & profit clarity for Malaysian microentrepreneurs

> **Status**: Active Development — Phase 1 complete, Phase 2 (Business Core) next
> **Last Updated**: 2026-09-02

## Business Context
- **Client**: Fakrul (product owner)
- **Status**: active
- **Priority**: high
- **Revenue Model**: SaaS subscription — Free / Starter / Growth / Business tiers
- **Deployed**: No

## Overview
- **Root**: `C:\Users\fakrul.hakim\Downloads\RH`
- **Stack**: Laravel **13.10.1** (PHP 8.3.30) · MySQL **8.4.3** (port 3307) · Redis 5 via `predis` · Vue **3.5.42** + Inertia **3.7** + Vite 8 · Bootstrap **5.3.8** + Bootstrap Icons · Chart.js 4 · PWA
- **Local toolchain**: **Laragon, not XAMPP** — XAMPP's PHP caps at 8.2.12, below the SPEC §2 floor. MySQL and Redis are started manually, not as services.
- **Type**: SaaS — business finance tracking & insights for microentrepreneurs
- **Auth**: Laravel Fortify; roles Platform Admin / Business Owner / Staff
- **Currency**: MYR (schema tolerates more; no multi-currency engine in V1)
- **Payment**: Subscription billing; Malaysian gateway behind an isolated contract (`AMB-05`, ToyyibPay recommended)
- **Database**: MySQL 8, not yet provisioned
- **Brief**: `Downloads/RH/SPEC.md` (36 sections, authored by Fakrul — never edit)
- **Plan**: `Downloads/RH/Planning.md` (35 REQs, traceability matrix, 9 phases)

## Key Patterns
Pulled from `11-pattern-library.md` — all `[LEARN]` confidence (research-sourced 2026-08-14, not yet battle-tested):
- **Laravel 13 + Inertia 3 version baseline** — Laravel 12 left bug-fix support 2026-08-13; Breeze/Jetstream are dead paths, starter kits use Fortify; Ziggy displaced by `laravel/wayfinder`; Axios removed from Inertia 3.
- **Inertia shared props** — wrap layout-critical props in `Inertia::always()`, or partial reloads blank them. Use `Inertia::once()` for heavy shell data.
- **Inertia props leak every model field** — `toArray()` serializes every non-`$hidden` column and appended accessor, recursively. Route props through DTOs and enforce in review from commit #1. Critical here: financial and tenant data must never ride along by accident.
- **Bootstrap through Vite needs `loadPaths`** — bare SCSS imports fail without it.
- **Laravel on native Windows 11** — relevant to Fakrul's dev machine; Horizon is unusable there.

**Gap:** the library's entry covers **React 19**, not Vue 3. Vue 3 + Inertia 3 needs a Learn Protocol Research Sprint before Phase 1 frontend work.

## Completed
1. **Phase 0 — Discovery & Planning** (2026-09-02) — project inspected, brief preserved, traceable `Planning.md` authored (35 REQs, 16 ambiguities, 9 phases, acceptance criteria), `docs/documentation.md` scaffolded, project registered in the Core.
2. **Phase 1 — Foundation** (2026-09-02, `REQ-01`–`REQ-05`, commit `b6b474b`) — Laravel 13 + Vue 3 + Inertia 3 + Bootstrap 5 wired; Fortify auth on Inertia pages; business + `business_user` structure; three-layer tenancy (fail-closed scope, membership-revalidating middleware, policy); mobile-first layouts. 30 tests / 65 assertions green on real MySQL 8.

3. **Phase 2 — Business Core** (2026-09-02, `REQ-06`–`REQ-12`, commit `1597710`) — 8 tables, 8 models, `SaleService`/`InventoryService`/`ProfitService`, 6 controllers, 12 Vue pages, demo seeder. Sales snapshot unit cost and move stock in one transaction; the inventory ledger reconciles exactly with `current_stock`. 107 tests / 232 assertions green. Two tenancy security holes found and fixed during the build.

## Remaining
- Phase 3 — Financial Intelligence (`REQ-13`–`REQ-17`) ← next
- Phases 3–8 (Financial Intelligence → Growth Tools → AI Advisor → SaaS → PWA → Production Readiness)
- Open ambiguities: `AMB-04` deploy target, `AMB-05` payment gateway, `AMB-13` health-score thresholds
- Reconcile the `CLAUDE.md` / `AGENTS.md` that Laravel 13 shipped into the repo root with the CoreSentinel protocols

## Anti-Patterns (This Project)
- **Never edit `SPEC.md`** — it is Fakrul's brief. All plan changes go in `Planning.md`.
- **Never let the AI layer compute a financial figure.** It explains numbers produced by `app/Services/Financial`. Fabrication is the product's biggest reputational risk (`SPEC.md` §16).
- **Never use Tailwind CSS.** Bootstrap 5 only (`SPEC.md` §2).
- **Never write Bahasa Indonesia.** Malaysian Malay only (`SPEC.md` §27).
- **Never present cash flow as profit** (`SPEC.md` §14) — the distinction must be visible to the user.
- **Never invent a business-health score.** Every badge links to the transparent rule that produced it (`SPEC.md` §7).
- **Never hardcode a plan limit** outside the central feature-gate layer (`SPEC.md` §21).
- **Never resolve COGS from live `cost_price`** — snapshot it, or editing a product silently rewrites history (`SPEC.md` §25).
- **Never tick a `Planning.md` checkbox without** real implementation paths, real passing tests and a `docs/` anchor (Protocol 53 §4).
- **Never add a package, abstraction, interface, repository or event** without answering "is this required by the current business requirement?" with yes (`SPEC.md` §33).
- **Never write an `exists`/`unique` validation rule without an explicit `business_id` constraint.** Validation rules compile to raw query-builder lookups — Eloquent global scopes do not apply, so a forged id from another tenant validates. Use `ScopesToBusiness`. *(Real hole found and fixed 2026-09-02.)*
- **Never let route-model binding run before the tenant context is bound.** `SubstituteBindings` is web-group middleware and normally beats route middleware; with a fail-closed scope that 404s every bound model — and makes cross-tenant tests pass for the wrong reason. Fixed via `prependToPriorityList`. *(Real bug found and fixed 2026-09-02.)*
- **Never write `current_stock` directly.** All stock changes go through `InventoryService` so the ledger stays reconcilable.

## Work Log
### 2026-09-02 — Init Protocol, Phase 0
- Inspected `Downloads\RH`: empty apart from the brief. No Laravel app, no git, no database.
- Moved the brief `Planning.md` → `SPEC.md`; its own §30 reserves the `Planning.md` filename for the traceable progress document.
- Authored `Planning.md`: vision, 6 objectives, scope, non-goals, architecture, stack, 20-table database plan, 35-requirement traceability matrix, 9 phases with checkboxes, per-REQ acceptance criteria, 10+5-point Definition of Done, testing requirements.
- Logged 16 ambiguities. Blocking: sale shape, Laravel 12 vs 13 (support ended 2026-08-13), COGS method, deployment target.
- Scaffolded `docs/documentation.md` per Protocol 53 with anchors reserved for every REQ.
- Registered project in `00-identity.md` and `~/.claude/project-labels.json`.
- **No application code written** — `SPEC.md` §36.9 requires approval before major implementation.
