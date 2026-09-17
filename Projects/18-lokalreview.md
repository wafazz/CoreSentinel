# LokalRevieW (LR) — Social-first local discovery + review network, Malaysia-first

> **Status**: Planning — pre-development (no code)
> **Last Updated**: 2026-09-14

## Business Context
- **Client**: own product (Fakrul)
- **Status**: active — planning / validation
- **Priority**: to be set after the Planning.md verdict
- **Revenue Model**: consumers free; businesses freemium subscription + clearly-labelled sponsored discovery
- **Deployed**: No

## Overview
- **Root**: `/Users/wafazztechnology/Desktop/Codex Lure/project/LokalRevieW`
- **Stack (proposed, not installed)**: Laravel + PHP-FPM, Inertia + Vue 3 + TypeScript, Bootstrap 5, PostgreSQL + PostGIS, Redis + Horizon, Sanctum, S3-compatible storage, Nginx on Ubuntu LTS
- **Type**: consumer social network + two-sided marketplace (reviewers ↔ businesses)
- **Auth**: Sanctum (SPA cookie now, tokens for future mobile); admin MFA
- **Currency**: MYR
- **Payment**: undecided — Billplz / ToyyibPay / Stripe / Curlec evaluated behind an abstraction
- **Database**: PostgreSQL + PostGIS (not created)

## Key Patterns
- Carry over from SociaPulse (11-pattern-library.md "Laravel 12 + PostgreSQL 16 + Inertia"):
  `'timezone' => 'UTC'` on the pgsql connection; `ON CONFLICT DO NOTHING`, never catch-and-continue inside a PG transaction.
- Deploy shape: 51-deployment-protocol.md Recipe A4 (PostgreSQL + queue workers) + A4.4 restore-tested backups.

## Completed
1. CS init scaffold (session-memory.md, docs/documentation.md, registration) — 2026-09-14
2. Planning.md — 2026-09-14 (see project root)

## Remaining
- Fakrul decision on Planning.md verdict (**VALIDATE BEFORE BUILDING**) and 7 gates (2 GO, 1 GO-with-legal-condition, 4 VALIDATE MORE)
- Validation experiments before any engineering (Planning.md §95)

## Anti-Patterns (This Project)
- Do not start development on an approved-sounding brief: the brief itself requires a verdict first.

## Work Log
### 2026-09-14 - Init + Planning
- CS init (T2), four Scout research passes (international competitors, Malaysia market/legal/payments, stack versions, pricing/seed data/T&S), Planning.md drafted and self-reviewed.
