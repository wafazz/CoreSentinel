# Social Media Listening Tool — centralised keyword monitoring across six social platforms

> **Status**: Active Development — Phase 1 complete
> **Last Updated**: 2026-09-08

## Business Context
- **Client**: R&D / own build (Day Three R&D track)
- **Status**: active
- **Priority**: medium
- **Revenue Model**: prospective SaaS
- **Deployed**: No

## Overview
- **Root**: `Desktop/Codex Lure/project/RND DayThree/Social Media Listening Tools`
- **Stack**: Laravel 13.30.1 · PHP 8.4 · Inertia 3.3.3 · Vue 3.5.42 · Vite 8.2.2 ·
  Bootstrap 5.3.8 · AdminLTE 4.9.1 · ApexCharts 7.1.0. **No TypeScript, no Tailwind,
  no Redis, no Horizon** — each recorded with a reason in `Planning.md` §3.2
- **Type**: monitoring / analytics console
- **Auth**: planned Fortify + session, code-owned permission registry. **NOT IMPLEMENTED**
- **Database**: MySQL 8.0 / MariaDB (Fakrul's choice). **Phase 1 uses no database at all**
- **Target platforms**: Facebook · Instagram · Threads · X · LinkedIn · YouTube

## The finding that defines this project

Scout's live verification (2026-09-08) established that **only three of the six platforms
can search public content by keyword, each tightly constrained, and Facebook and LinkedIn
offer no public post search at any tier.** The product therefore has two acquisition modes:

| Mode | Platforms |
|---|---|
| **Discovery** (search anyone's public content) | YouTube (quota-bound: 100 units/search of 10,000/day) · Threads (needs `threads_keyword_search`; ~500 queries/7 days) · Instagram (hashtags only; 30 unique per rolling 7 days) · X (metered per read) |
| **Owned-channel** (our own properties only) | Facebook Pages · LinkedIn Organisations · Instagram own media/@mentions · YouTube own channel |

Designing as if all six do Discovery is how this class of product fails.

## Key Patterns
- Capability-typed provider architecture — narrow base interface + capability marker
  interfaces + a declarative four-state map with a reason string per capability
- Sidebar config as single source of truth, asserted by test
- Inertia props built from arrays, enforced by a no-secrets-in-props test
- Layout classes namespaced `slt-*` away from AdminLTE's own
- URL-backed filter state on every screen (Power BI interaction model, AdminLTE shell)
All five written up in `11-pattern-library.md`.

## Completed
1. **Phase 1 Foundation (2026-09-08) — VERIFIED.** Laravel + Inertia + Vue + AdminLTE
   scaffold · working sidebar with the specified tree · 11 routes, all HTTP 200 ·
   interactive sample Dashboard with cross-filtering · Mentions queue with a
   capability-aware reply composer · Keywords with platform-budget surfacing · Analytics ·
   six platform settings screens from one component. CS verify **100/100**, 6/6 checks,
   **15 tests / 345 assertions**. Five bugs found and fixed during verification
   (`Planning.md` §14.6).
2. **`Planning.md`** — 1,445 lines. Product overview, capability matrix with sources and
   confidence, provider architecture, Mermaid ERD, sentiment architecture, security,
   error taxonomy, queue justification, screen briefs, 89 traceable requirements,
   6 implementation phases.

## Remaining
- **Phase 0** — access applications (Meta App Review + Business Verification, LinkedIn
  Standard tier incl. screencast, Google quota increase, X account + written pricing).
  Long lead times, entirely outside our control. **Start immediately.**
- **Phase 2** — schema, models, Fortify auth, RBAC, audit logging, keyword CRUD, export
- **Phase 3** — integrations in lead-time order: YouTube → Threads → Instagram → Facebook
  → X → LinkedIn. **Begins with re-verifying §4, not with code**
- **Phase 4** — sentiment (contract, `NullAnalyzer`, first real analyzer, batch scoring)
- **Phase 5** — reply dispatch, failure taxonomy, retry, circuit breaker
- **Phase 6** — production hardening

## Anti-Patterns (This Project)
- **Never claim a platform capability from memory.** See AP-SML-01 in `55-self-evolution.md`.
  X's whole pricing *model* changed in Feb 2026.
- **Never let a metered platform fetch without a hard ceiling.** X bills per read; a
  listening tool that can silently run up a bill is a defect.
- **Never trust a successful-looking Threads search.** It narrows silently to own posts
  without the scope, and never errors.
- **Never namespace-collide with AdminLTE's layout classes.** See AP-SML-02.

## Gate before the next session
**Fakrul approves the `Planning.md` §6 schema and the §11 screen-brief references before
the first migration is written.**

## Open Questions
OQ-01 multi-tenant? · OQ-02 which platforms are commercially in scope given the capability
matrix? · OQ-03 budget for X reads and AI sentiment · OQ-04 do we hold the platform accounts
to apply with? · OQ-05 expected daily mention volume · OQ-06 deploy target · OQ-07 are the
proposed design references accepted? · OQ-08 is 90-day `raw_payload` retention acceptable?
