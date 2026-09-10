# Basic Custom E-Commerce — Vanilla PHP 8.0 MVC + MySQL, ToyyibPay + EasyParcel

> **Status**: MVP built — blocked on external API verification before real payments
> **Last Updated**: 2026-08-26
> **Budget**: RM1,000 (fixed) — architecture chosen to fit it, not to impress

## Business Context
- **Client**: small business storefront (spec supplied as `prompt.txt`)
- **Status**: active
- **Priority**: medium
- **Revenue Model**: e-commerce
- **Deployed**: No

## Overview
- **Root**: `C:\Users\fakrul.hakim\Downloads\SE`
- **Stack**: Vanilla PHP **8.0** · hand-rolled MVC · MySQL/MariaDB · PDO · sessions · HTML/CSS/vanilla JS
- **Type**: basic e-commerce (storefront + admin)
- **Auth**: guest checkout for customers; single admin role, session + bcrypt
- **Currency**: MYR — **integer sen** everywhere (`*_minor`)
- **Payment**: ToyyibPay (FPX)
- **Shipping**: EasyParcel — **rate checking only**; booking/tracking OUT OF SCOPE
- **Database**: `se_shop`, InnoDB, `utf8mb4_unicode_ci` (NOT `utf8mb4_0900_ai_ci` — absent on MariaDB)
- **Runtime dependencies**: **zero**. Composer is dev-only (PHPUnit 9.6).

## Key Patterns
Pulled from `11-pattern-library.md`: *E-Commerce Variants Without EAV* (simplified),
*Money — Integer Minor Units*, *Atomic Race-Free Action Guard*, *Soft Deletes Break Unique Indexes*.

Project-specific:

- **Variant design = denormalised, not an option engine.** `product_variants` carries
  `option1_name/value`, `option2_name/value` + `UNIQUE(product_id, option1_value, option2_value)`.
  Chosen over the option/option_value/pivot/signature shape because catalogue-wide faceting was
  never requested and that shape costs +3 tables. A→B migration stays open and non-destructive.
- **Option values are `''`, never NULL.** MySQL treats NULLs as distinct in a unique index, so
  NULL would allow two option-less variants per product and silently defeat the constraint.
- **Money is `INT UNSIGNED` sen.** PDO returns DECIMAL as a *string*, so `$price * $qty` becomes a
  float on first use. ToyyibPay's `billAmount` is already cents → the payment path does zero conversion.
- **Stock: single guarded UPDATE**, `SET stock_qty = stock_qty - :qty WHERE id = :id AND stock_qty >= :min_qty`,
  assert `rowCount() === 1`. Never SELECT-then-UPDATE.
- **Payment verification never trusts the callback.** Both callback and browser return take only the
  bill code, then re-query `getBillTransactions` server-side and compare amount + reference.
  Idempotency via `markPaidIfPending()` guarded transition + `UNIQUE(payments.provider_ref)`.
- **`verifyPayment()` fails closed** — an unrecognised response shape returns `unverified`, never `paid`.
- **Credentials in `.env` only.** Admin Settings shows Configured/Not-configured; no code path renders a secret.
- **Rate API failure falls back to a configurable flat rate** — checkout must never dead-end on a courier outage.

## Completed
1. Init Protocol run against `prompt.txt`; Phase 1.5 stack check passed (no Learn sprint needed)
2. `Planning.md` — 20 sections, REQ-001…012, traceability matrix, approved
3. PHP 8.0 amendment (§4.1) after client requirement change
4. Phases 2–10: schema+seed, core MVC, catalogue+variations, cart+checkout, ToyyibPay, EasyParcel, admin, security, tests, deployment runbook
5. ~70 files; 54 tests / 852 assertions green
6. Live-verified on MariaDB 10.4.32 + PHP dev server, including a forged-callback attack test

## Remaining
- **BLOCKING** — verify ToyyibPay `getBillTransactions` response fields (Planning.md §8.6). Official
  reference 403s to automated fetch; needs a human with a browser. No payment settles until then.
- Verify EasyParcel response envelope + **whether `price` is RM or sen** (§9.4)
- Answer OQ-01 (name), OQ-02 (hosting), OQ-03 (patched vs stock PHP 8.0), OQ-06 (pickup origin), OQ-07 (accounts)
- Optional Phase 7b: EasyParcel booking + tracking
- Optional Phase 9b: order confirmation email (not in spec — flagged as a likely expectation gap)

## Anti-Patterns (This Project)
- **Never** store option values as NULL — see above.
- **Never** reuse a named PDO placeholder in one statement: `EMULATE_PREPARES=false` means native
  prepares, and reuse throws *Invalid parameter number*.
- **Never** write a PHP 8.1+ feature. Local dev is 8.2.12 (XAMPP) but the target is 8.0 — it will
  pass locally and die on the host. No enums, no `readonly`, no `never`, no first-class callables.
- **Never** trust a payment callback's `status`/`amount`. Re-query.
- **Never** hard-delete a product or category — it orphans `order_items` history. Deactivate.
- In a `/`-delimited regex, `[^/]` closes the delimiter. Use `[^\/]`. Cost a 500 on every
  parameterised route until caught in the live smoke test.
- MySQL `ON DUPLICATE KEY UPDATE` and `CONCAT()` are not portable to SQLite — keep them in
  production code and seed test data with portable SQL instead of degrading the real statement.

## Work Log
### 2026-08-26 — Init through MVP
- Ran Init Protocol; read `prompt.txt` (16,246 bytes)
- Verified EasyParcel against `developers.easyparcel.com`; ToyyibPay against community mirror +
  `omnipay-toyyibpay` / `toyyibpay-js-sdk` / `xputerax/toyyibpay` (official ref 403)
- Wrote and got approval for `Planning.md`, then amended for the PHP 8.0 requirement
- Built Phases 2–10; 54 tests green; full E2E verified against MariaDB
- Fixed during build: router regex delimiter bug, PDO placeholder reuse in `decrementStock()`,
  `NOW()` → `CURRENT_TIMESTAMP` for portability
