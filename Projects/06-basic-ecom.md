# Basic Custom E-Commerce — Small-business storefront with ToyyibPay + EasyParcel rates

> **Status**: **Delivered 2026-08-27** — Phases 1–11 complete. Two items open with the client.
> **Last Updated**: 2026-08-27

## Business Context
- **Client**: Small business (client project — `52-handoff-protocol.md` applies at Phase 11)
- **Status**: delivered (maintenance pending client answers)
- **Priority**: medium
- **Revenue Model**: e-commerce (client delivery, one-off build)
- **Budget**: **RM1,000 hard ceiling** — the single strongest constraint on every decision
- **Deployed**: No — handed off for client deployment (VPS)

## Overview
- **Root**: `~/Desktop/Codex Lure/project/basic-ecom`
- **Spec source**: `Prompt.txt` — client's Laravel 12 / PHP 8.3 instruction, 36 sections, 11 phases
- **Stack**: Laravel 12 · PHP 8.3 · Blade · MySQL 8.0 · Bootstrap 5 (Vite removal pending OQ-10)
- **Type**: e-commerce (single vendor, guest checkout)
- **Auth**: Laravel `auth` guard on the default `users` table. One admin. No customer accounts, no registration routes.
- **Currency**: MYR, single currency, stored as `INT UNSIGNED` sen (`_minor` suffix)
- **Payment**: ToyyibPay (FPX / Malaysian online banking)
- **Shipping**: EasyParcel Open API 2026-06 (OAuth 2.0) — rate quotations **+ shipment booking, AWB & tracking** (REQ-013, client-approved into scope 2026-08-26)
- **Database**: MySQL 8.0, `DB_CONNECTION=mysql`, `utf8mb4_unicode_ci`, InnoDB
- **Deploy target**: VPS (SSH + Composer + cron + Let's Encrypt available)

## Key Patterns
Pulled from `11-pattern-library.md`:

| Pattern | Applied to |
|---|---|
| **Atomic Race-Free Action Guard** | Stock decrement (`WHERE stock_qty >= :qty`, assert affected = 1) and the paid-transition guard (`WHERE payment_status = 'pending'`). Both are what make a duplicate ToyyibPay callback a no-op. |
| **Money — Integer Minor Units, Not DECIMAL** | Every money column is `INT UNSIGNED` + `_minor`. Reinforced by Eloquent's `integer` cast. ToyyibPay's `billAmount` is already in cents, so the payment path needs no conversion at all. |
| **E-Commerce — Product Variants Without EAV** | Documented as the Option B upgrade path. **MVP deliberately collapses it** to a denormalised variant row (2 option axes, `UNIQUE(product_id, option1_value, option2_value)`) — the full dictionary costs +3 tables to buy faceting nobody asked for. |
| **MySQL — Soft Deletes Break Unique Indexes** | The reason `SoftDeletes` is banned on `products` / `categories`. `is_active` boolean instead — no generated-column sentinel needed. |
| **Encrypted Secrets at Rest** | EasyParcel OAuth access + refresh tokens, via the Eloquent `encrypted` cast with `cipher = AES-256-GCM`. |

Project-specific conventions:
- Every product has **≥1 variant**, even an option-less one — kills `IF variant_id IS NULL` branching everywhere.
- Unused option slots store `''`, **never `NULL`** — MySQL treats NULLs as distinct in a unique index.
- Order/payment status are **PHP 8.3 backed enums** cast on the model; DB columns stay `VARCHAR`.
- `Model::shouldBeStrict()` outside production.

## Completed
1. Phase 0 Intake + Phase 1 Research; `Planning.md` approved 2026-08-26.
2. **Phases 2–11 built and delivered 2026-08-27.** 19 commits.
3. **12 of 13 requirements delivered.** REQ-001/002/003/004/006/007/008/009/010/011/012 `Verified`; REQ-005 built but gated on OQ-11; REQ-013 not built (OQ-13).
4. **199 tests / 564 assertions green on SQLite AND MariaDB 10.4.28.** End-to-end purchase flow tested, plus the same flow with both third-party APIs down.
5. Handoff artifact published (private): https://claude.ai/code/artifact/8e821ef2-9501-4fcc-8b02-df30a4921d29

## Remaining — blocked on the client, not on work
- **OQ-11 — ToyyibPay `getBillTransactions` field names.** Until confirmed, `ToyyibPayService` returns `unverified` and orders stay pending. **Live payments cannot settle.** Resolution: confirm the field names + amount format, adjust the candidate keys and `TOYYIBPAY_AMOUNT_FORMAT`.
- **OQ-13 — EasyParcel `shipment/submit` / `shipment/pay` payloads.** REQ-013 booking/AWB/tracking is **not built**; the design is written in `Planning.md` §11.B.5 and is ~2 days once the payloads are confirmed.
- **OQ-12 — EasyParcel credit balance** ownership (only bites once booking exists).
- Client must budget a **Laravel major upgrade** before ~Feb 2027 and the **recurring VPS cost**.

## Anti-Patterns (This Project)
- **Never trust the ToyyibPay callback or return URL.** Re-query `getBillTransactions` server-side and match amount + external reference. The gateway provides no HMAC.
- **Never `SELECT` stock then `UPDATE` it.** One guarded `UPDATE`, check the affected row count.
- **Never store `NULL` in an unused variant option slot.** Two "no-option" variants would both be allowed.
- **Never call `env()` outside `config/`.** `php artisan config:cache` makes it return null in production — silent, and only in prod.
- **Never use `SoftDeletes` alongside a UNIQUE slug/sku here.**
- **Never regenerate `APP_KEY` after the first EasyParcel connect** — the encrypted token rows become undecryptable.
- **Never auto-retry an EasyParcel `pay` call whose outcome is unknown.** A timeout means "maybe charged" — the shipment goes to `needs_reconciliation` and a human resolves it against the EasyParcel dashboard. Auto-retry is how a store pays twice.
- **Never book a shipment from a callback, a GET request, or the payment path.** Booking spends real credit: admin-only POST, behind `UNIQUE(shipments.order_id)`.
- **Do not add a Composer package beyond the Laravel skeleton** without passing the spec §30 gate and recording the justification in `Planning.md`.

## Persisted to MemoryCore (Phase 8)
Written 2026-08-27:
- `11-pattern-library.md` — **7 battle-tested patterns** under a new "Laravel 12 + Blade + MySQL" section: fail-closed third-party verification · OAuth refresh-token rotation under concurrency · money across a decimal-string API boundary · forced first-login password change · guarded atomic update in Eloquent · route-model-binding traps · Laravel without Node.
- `55-self-evolution.md` — **9 anti-patterns and 3 learned skills.** The two that cost the most: a plan that promised a security control and never implemented it, and a traceability row listing files that did not exist.
- `51-deployment-protocol.md` — Recipe **A2** (Laravel server-rendered, no Node, no queue worker) plus the project index row.
- `05-init-protocol.md` — first entry in the stack recommendation table, with the recurring costs to quote separately.
- `35-review-protocol.md` — the Laravel + Blade checklist, replacing the placeholder.

**Not promoted**: the `[LEARN]` Laravel 13 + Inertia block stays research-sourced. This project shipped Laravel **12 + Blade**; Inertia, React, Vite and Fortify were never used, so it is not evidence for them.

## Post-delivery changes (client requests, 2026-08-27)
All after the Phase 11 handoff, all client-visible:
1. **AdminLTE 4.9.1** admin template, vendored locally (no CDN, no Node). Uncovered that the storefront had **never loaded Bootstrap JS** — the mobile navbar toggler had been inert since Phase 4.
2. **Owner/HQ dashboard** — headline tiles + day/week/month/year comparisons. Ads Cost and ROAS were specified but have no data source here, so they became **Average Order Value** and **Payment Conversion**; the ads-spend setting added for them was removed rather than left dead.
3. **Order status vocabulary** → Pending · New Order · Processing · In Delivery · Completed · Returned · Cancelled. `needs_review` retained as **system-set only** (filterable, not assignable). Reversible data migration; settlement now lands on New Order, not Processing.

Handoff artifact **republished** to the same URL after these — it had gone stale at 199 tests and did not mention the new workflow.

**Current: 235 tests / 660 assertions green on SQLite and MariaDB 10.4.28.**

## Work Log

### 2026-08-26 — Init against the client's Laravel 12 spec
- The client supplied their own `Prompt.txt` (36 sections, 11 phases, Laravel 12 / PHP 8.3). It is authoritative — do not edit it.
- `Planning.md` written against it: §25's required section list satisfied (incl. **Cart Design** and **Checkout Design**), phases aligned to §27, traceability per §26.
- **Divergence flagged**: §31 lists `EASYPARCEL_API_KEY` (legacy Connect API), but the verified current API is OAuth 2.0. §31 itself says not to assume those names → **OQ-03**.
- **Divergence flagged**: §19's folder list implies Vite; §6 asks only for Blade/Bootstrap/vanilla JS and §33 lists no Node → **OQ-10**.
- **Scope change (client)**: EasyParcel **shipment booking, AWB & tracking moved INTO scope** → **REQ-013**. Adds `shipments` (10th table), `ShipmentController`, `ShipmentStatus` enum, admin-triggered booking, reconciliation screen. Estimate ~9 → **~11 days**, plus a recurring courier-credit obligation. New questions OQ-12…OQ-16.
- Scout flagged: **Laravel 12 left bug-fix support 2026-08-13** (13 days before this entry). Security fixes to ~2027-02-24. Laravel 13 is current. Client must budget a major upgrade → OQ-08.
- Init Protocol Phases 3a–3f executed. Init Phase 5 (framework scaffold) **halted by spec §35** pending approval of `Planning.md` §21.
