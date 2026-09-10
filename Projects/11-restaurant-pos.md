# Restaurant POS — Multi-branch QR ordering, waiter POS, KDS, reservations & payment gateways

> **Status**: Approved 2026-09-07 — **PH-00 to PH-03 delivered**, PH-04 next
> **Last Updated**: 2026-09-07

## Business Context
- **Client**: TBD (OQ-01 — branch count and brand not yet confirmed)
- **Status**: active — blocked at the approval gate
- **Priority**: high
- **Revenue Model**: TBD (OQ-17 — timeline and budget not yet set)
- **Deployed**: No

## Overview
- **Root**: `Desktop/Codex Lure/project/Restaurant Ordering System V2`
- **Stack**: Laravel 12 · PHP 8.4 · Inertia 3 · Vue 3.5 · TypeScript · Bootstrap 5 (**no
  Tailwind**) · PostgreSQL 16 · Redis 8 · Laravel Reverb + Echo · Laravel Sanctum · Queues
- **Type**: Restaurant POS / QR ordering / KDS / reservations — multi-branch
- **Auth**: Inertia session for staff; Sanctum for future mobile; signed short-TTL cookies for
  customers (dine-in and pick-up); opaque device tokens for displays and print agents; signature
  verification (not auth) for gateway webhooks
- **Currency**: MYR, stored as integer sen
- **Payment**: **Bayarcash** + **Billplz** (live drivers), cash, static DuitNow QR
- **Database**: PostgreSQL 16 with `btree_gist`; ~45 tables

## Scope (six subsystems, all v1)
1. **QR dine-in ordering** — customer PWA, waiter POS, move/merge, KDS, ESC/POS printing
2. **Multi-branch** — branch-scoped everything, OWNER role, HQ portal, consolidated reporting
3. **Payment gateways** — driver interface, two live drivers, per-branch encrypted config,
   owner settings page, signed idempotent webhooks, reconciliation sweep
4. **Prepaid pick-up orders** — second fulfilment type, paid before the kitchen sees it
5. **Loyalty / vouchers / membership** — three independent owner switches, off by default
6. **Table reservations** — public booking, deposits, seating into a dine-in session

## Key Patterns
Applied from `11-pattern-library.md`:
- **Guarded Atomic Update in Eloquent** — order confirm, voucher last use, slot capacity
- **Enforcing a Constraint on a SUM** — captured payments never exceed the bill
- **Money — Integer Minor Units, Not DECIMAL** — everything in sen
- **Snapshot Every Input a Money Record Depends On** — order line snapshots
- **Stock Ledger — one writer, guarded decrements, reconcilable history** — `StockLedger`
- **Registry-Backed RBAC — `Gate::before` that cannot become a bypass** — permission registry
- **Tenant Scope: read open, write closed** — branch scoping
- **Declared Settings Registry** — restaurant default → branch override
- **Privilege Columns Must Not Be Fillable** — credentials, levels, statuses
- **Audit trails**: derive the tenant from the record; two actor columns; order by
  `created_at DESC, id DESC`

New patterns to capture during the build (`[LEARN]` — none of these are in the library yet):
- PostgreSQL `EXCLUDE USING gist` + `btree_gist` as a booking-overlap guarantee
- Laravel Reverb + Echo channel design: branch-namespaced private channels, thin payloads,
  resync-on-reconnect
- ESC/POS printing via an outbound-polling print agent (no inbound route into a client LAN)
- Gateway webhook discipline: event row first, mutate second; redirect proves nothing
- Two-phase stock (reserve → commit) attached to an order state machine
- PWA on Laravel 12 + Inertia: service worker that must never cache bill state

## Completed
1. **CS init (2026-09-07)** — protocols read, T2 declared, machine verified, `[LEARN]` tagged
2. **`Planning.md`** — 37 sections, **250 requirement IDs**, 68 business rules, 21 Screen
   Briefs, 24 named concurrency races, 15 phases, 17 risks, 17 open questions. Traceability
   verified mechanically: every REQ ID appears in §33.1, no orphans either way.
3. **PH-00 Foundation & multi-branch (2026-09-07)** — Laravel 12.69.1, PostgreSQL 16 +
   `btree_gist`, Redis 8, Reverb, Inertia 3 + Vue 3.5 + TS 5.9 + Bootstrap 5.3 (no Tailwind).
   21 tables across 9 migrations. Permission registry (77 keys, 7 roles), grant ceiling,
   `BranchScope` + `branch.active`, settings resolver (restaurant default → branch override),
   business-day resolver, append-only audit trail (17 declared actions), owner/HQ portal,
   staff management, 7 Inertia screens. **91 tests green** on real PostgreSQL.
4. **PH-01 Tables & QR (2026-09-07)** — dining areas, tables, the operational/derived status
   split with a sole-writer projector, 256-bit QR tokens hashed at rest with one-live-per-table
   enforced by a partial unique index, rotation, print-first QR sheets, the public `/t/{token}`
   landing with per-IP and per-token throttling, and the live floor plan (SB-W1).
   **131 tests / 449 assertions green.** Verified end to end in a browser: issue → print →
   scan → recognised.
5. **PH-02 Menu (2026-09-07)** — stations, categories, items, tags, modifier groups covering
   both variations and add-ons with per-item overrides, per-branch availability and price
   override, a secure image pipeline (sniff → re-encode → private disk → signed URL), browse
   and search behind one query object with a pinned query count, and the menu half of branch
   cloning (completing REQ-FND-013). **183 tests green.**
6. **PH-03 Inventory core (2026-09-07)** — one register for products and ingredients, units
   with conversion, recipes for dishes and add-ons, the append-only movement ledger with a
   sole writer, the level projector plus a rebuild/reconciliation path, two-phase
   reserve/commit/release, the guarded decrement under a row lock, and auto-86 at zero with
   manual-86 precedence. **225 tests / 717 assertions green.**

## Remaining
- **PH-04 Ordering + dine-in PWA** ← next, not blocked
- PH-05 … PH-14 (see `Planning.md` §34)
- **OQ-11 still open**: the stock engine is built and seeded with demonstration recipes, but
  the real ones — which items, what units — are Fakrul's data decision.
- Answer the 🔴 blockers before their phases: OQ-02 (tax → PH-07), OQ-06 (printers → PH-06),
  OQ-08 (design references → every UI phase), OQ-11 (recipe scope → PH-03),
  OQ-14 (gateway accounts → PH-08)
- A true 390px mobile capture (Chrome clamps window width at ~500px; needs device emulation)

## Anti-Patterns (This Project)
- **Never let a redirect settle a bill.** Only a verified callback or the reconciliation sweep
  captures a payment (BR-47). A customer's browser returning from a bank proves only that they
  followed a link.
- **Never broadcast before commit.** Every event is `ShouldDispatchAfterCommit`; otherwise the
  KDS shows tickets that a rolled-back transaction never created.
- **Never put a network call inside a transaction.** Printing, broadcasting and both gateways all
  happen after commit.
- **Never test this schema on SQLite.** Partial unique indexes, `CHECK` constraints, generated
  columns and `EXCLUDE USING gist` carry half the guarantees; SQLite has none of them and would
  green-light code PostgreSQL rejects.
- **Never store an editable table status.** It drifts. Derive `display_status`; keep only the
  admin's `operational_status` editable.
- **Never let "no recipe" and "recipe not entered" look the same.** `is_stock_exempt` is explicit
  (BR-37), or stock silently stops working for that item.
- **Never trust `psql`/`pg_dump` exit codes.** Capture both streams, grep for `ERROR`, then verify
  `information_schema` directly. (Recorded CS anti-pattern; has cost real time twice.)
- **Never rotate `APP_KEY` without re-encrypting `payment_gateway_configs`** — it silently
  destroys every gateway credential.
- **Never re-enable `filesystems.disks.local.serve`.** Laravel registers `GET` *and* `PUT` on
  `storage/{path}` with **no middleware at all**. Found by the route-coverage test in PH-00.
- **Never run `php artisan migrate:fresh --env=testing` without a `.env.testing`** — it falls
  back to `.env` and wipes the development database. `.env.testing` now exists.
- **Never upgrade TypeScript to 7 while vue-tsc 3 is in use** — TS 7 dropped
  `typescript/lib/tsc` from its exports and vue-tsc cannot resolve it.
- **PostgreSQL 16 is on port 5433 on this machine**, not 5432.
- **A QR code can never be reprinted, only reissued.** Tokens are hashed at rest, so printing
  a sheet revokes whatever is already stuck on those tables. Correct, and surprising — it is
  spelled out on the screen for that reason.
- **`tables.display_status` has exactly one writer**, `TableStatusProjector`. Nothing else may
  set it, and it is not fillable. PH-04 and PH-10 extend that one method.
- **Never mass-assign a foreign key or `branch_id`.** `firstOrCreate(['branch_id' => …])`
  throws under `preventSilentlyDiscardingAttributes`. Build the model and assign explicitly, or
  create through the relation. This cost three round-trips in PH-02 alone.
- **A ledger must release what it holds, not what it is told.** `commitSale` originally
  released the sale quantity, which drove `reserved` negative whenever a sale had no prior
  reservation. It now reads the outstanding hold from the ledger itself.
- **Composite FKs are the cheapest tenant guarantee available.** `menu_items(menu_category_id,
  branch_id)` referencing `menu_categories(id, branch_id)` makes a cross-branch menu item
  impossible at the storage layer, for the price of one extra unique index.
- **Never give a page prop the same name as a shared Inertia prop.** Page props win the merge
  and silently shadow the shared one, so the layout renders against `undefined` — a blank
  screen, a console error, and a fully green test suite. Shared keys here are `auth`,
  `branchContext`, `flash`.
- **Never read request-scoped state eagerly in `HandleInertiaRequests::share()`.** Inertia's
  base middleware calls `share()` *before* `$next($request)`, so route middleware has not run
  yet. Every shared value must be a closure.

## Work Log

### 2026-09-07 — CS init and planning
- Read `Project-Prompt.md` (1,190 lines) and the CS protocol set (00, 02, 05, 18, 20, 25, 53).
- Declared **T2 Full**: the build touches schema, auth/authz, payments, tenant scoping, file
  upload, deploy config and a public API — every T2 surface there is.
- Phase 1 (Scout): verified the local toolchain — PHP 8.4.10, Composer 2.8.10, Node 24.19,
  PostgreSQL 16.14 running (password required), Redis 8.4 running, `pdo_pgsql` + `redis` present.
  Confirmed PostgreSQL, Reverb, ESC/POS and PWA are absent from `11-pattern-library.md` →
  Learn Mode on.
- Authored `Planning.md` §§1–27, then Fakrul added six scope items in two messages. Each was
  folded back through the sections already written — state machines, schema, permissions,
  realtime, concurrency, UX, audit — rather than appended as a new chapter. Then §§28–37.
- **Stopped at the approval gate**, as both `Project-Prompt.md` and CS Phase 2 require.

### 2026-09-07 — PH-00 Foundation & multi-branch
- Scaffolded from the plain `laravel/laravel` skeleton, stripped Tailwind, added Inertia/Vue/TS
  + Bootstrap 5 + Reverb + Sanctum + Pest.
- 9 migrations / 21 tables. Verified the end state through `information_schema` rather than
  trusting the migration exit code (recorded CS anti-pattern).
- Wrote the permission registry as a code enum with the §23.3 matrix encoded in `RoleKey`, so
  the seeder is derived from the plan rather than hand-maintained.
- `BranchIsolationTest` is **generated from the router**: it walks every route carrying
  `branch.active` with a foreign branch id. New routes are covered automatically.
- Three real defects were caught by the guards rather than by review:
  `preventLazyLoading` caught an N+1 in `effectiveTimezone()`; `preventSilentlyDiscarding`
  caught my own test helper writing privilege columns; `RouteAuthCoverageTest` caught
  Laravel's unauthenticated `PUT storage/{path}`.
- Mistake made and corrected: ran `migrate:fresh --env=testing` with no `.env.testing`, which
  wiped the dev database (seed data only). Cause removed by creating `.env.testing`.

### 2026-09-07 — PH-00 browser pass (Phase 4 Probe)
- Four defects that 88 green tests could not see, all found by one screenshot:
  1. `DashboardController`'s `branch` page prop **shadowed** the shared `branch` prop. Every
     authenticated screen rendered blank. Shared key renamed `branchContext`.
  2. `share()` ran before `branch.active`, so the sidebar read "No branch" and the switcher
     was empty. All shared values are now closures.
  3. Owner portal (no `branch.active` by design) displayed "No branch" — now "All branches".
  4. Below 992px the sidebar hid with no alternative nav, and the header overflowed.
- Added `SharedPropsTest`, which walks every authenticated parameterless GET screen. Confirmed
  it goes RED when the shadowing bug is reintroduced — a guard that cannot fail is worthless.
- **Lesson**: the Phase 4 screenshot step is not ceremony. Skipping it in the first pass is
  what let a blank-screen bug reach "delivered".

### 2026-09-07 — PH-01 Tables & QR
- Two migrations, two partial unique indexes (`tables(branch_id, number) WHERE deleted_at IS
  NULL`, `table_qr_tokens(table_id) WHERE revoked_at IS NULL`), three CHECK constraints. All
  verified through `information_schema`, not the migration exit code.
- The brief listed seven table statuses. Analysed, they are two things: an admin flag and a
  projection. Split accordingly — that decision is what keeps a floor plan from drifting.
- Browser pass again earned its keep: `printQrSheet` 500'd on a lazy-load that the
  single-table print test did not cover. Fixed, and the new test was confirmed to go RED
  without the fix.
- Table sort was wrong in a way only a person would notice: `A3` sorted between `2` and `10`.
  Now groups by letter prefix, then by number.
- Deviated from the plan on QR sheets: print-optimised HTML rather than a PDF library. Raised
  in `Planning.md` §33.2 rather than absorbed silently.

### 2026-09-07 — PH-02 Menu
- One structure for variations and add-ons: they differ only by `selection_type` and min/max.
  Modelling them separately would have duplicated every query for no gain.
- Availability lives in its own table, not on the item row: item definition is cold config,
  availability is hot operational state changed several times a service. `manually_86ed` is
  what makes BR-39 decidable — stock arriving must not undo a chef's deliberate 86.
- Secure upload is decode-and-re-encode, not extension checking. A file that survives being
  re-encoded to WebP is genuinely an image; that is what kills EXIF payloads and polyglots.
- `MenuQuery` has a query-count test. Adding stock awareness at PH-03 will make the menu the
  hottest read in the system, and that test is what stops it becoming an N+1 quietly.
- Placement bug caught by a test: 86-ing was nested under `can:admin.access`, which a waiter
  does not hold. Planning.md §15.3 had it on the POS surface and was right.
- **Unresolved and reported to Fakrul**: browser automation cannot fire any Vue `@click` in
  this app — click lands, no request, no console error, on every page, dev and production
  builds alike. All affected endpoints pass over real HTTP in the suite. One human click will
  settle whether it is the app or the tooling.

### 2026-09-07 — PH-03 Inventory core
- One register for both kinds of stock. A bottled drink and a bag of rice are the same thing to
  a ledger: something you hold, count and run out of. Two tables would mean two reconciliations
  and two ways to be wrong.
- Two-phase stock (BR-36) is the decision that matters: reserve at placement, commit at
  confirmation, release on cancel. One phase either oversells or leaks stock on abandoned carts.
- `stock_levels.available` is a PostgreSQL GENERATED column, not an application calculation —
  it is read on every menu render and every submit, and a derived value computed in three
  places will disagree with itself.
- The double-deduction guarantee is a unique index on
  `(reference_type, reference_id, stock_item_id, type)`, proven by inserting a duplicate
  directly and watching PostgreSQL refuse it. Not an application check.
- Concurrency tests assert the row lock exists by querying `pg_locks` rather than simulating
  contention. Reported honestly as: mechanisms proven, parallel load not — that belongs in
  PH-14.
- Browser automation degraded further this phase: it now fails to deliver typing as well as
  clicks, intermittently. Still unconfirmed whether app or tooling; asked Fakrul for one click.

### 2026-09-07 — PH-04 Ordering & dine-in PWA
- **Browser automation resolved itself.** Clicks, typing and modals all worked normally through
  a full diner-to-waiter journey. It was the tooling, not the app; Fakrul never needed to click.
- **A whole class of test can pass by asserting nothing.** The suite runs on the null
  broadcaster, whose `auth()` approves everything, so all seven "must refuse" channel assertions
  returned 200 and went green. Channel authorisation had never once been exercised. The fix was
  structural, not a test tweak: authorisation logic cannot live in `routes/channels.php`,
  because a routes file is not testable. It lives in `ChannelAuthoriser` now, and the tests were
  verified to go red when the branch check is removed.
  **Generalises: when a test suite substitutes a null driver, ask what that driver returns.**
- **Realtime is silently dead without a queue worker** (RISK-18). Everything visible was healthy
  — Reverb up, Echo connected, auth passing, order committed — and no screen moved, because the
  broadcast jobs sat in Redis unclaimed. No error, no log, no banner. The "disconnected" banner
  watches the socket, which is the wrong half. Worse than an outage, because it looks fine.
- **Verify the traceability matrix against the filesystem, not against memory.** Writing PH-04's
  rows turned up three wrong paths and one requirement (`REQ-TBL-007`, cover count) that was
  never built: PH-01 deferred it to "when a session opens", PH-04 opened sessions and didn't do
  it. Reassigned to PH-05 rather than ticked off.
- `User::stations()` pointed at a pivot table that had never been created — a 500 waiting for
  the first KDS assignment, found because a channel guard called it.
- **The browser pass found five defects again, on a 291-test green suite**: an order shown to
  the diner as the literal string `draft`, `+RM -1.50`, no per-line price in the cart, no
  waiting time on the one screen that exists to stop orders rotting, and `Choose a Ice for Teh O
  Ais`. Four phases, four browser passes, defects every time. It is not optional.
- `npm run typecheck` had been reported as passing since PH-00 and did not exist as a script.
  Run the command before claiming its result.

### 2026-09-07 — PH-05 Waiter POS
- **Two guards that looked right and did nothing.** (1) `SessionMover` relied on `BranchScope` to
  hide foreign rows, so its explicit cross-branch check never executed — a cross-branch merge
  failed with `Undefined array key` instead of a refusal. (2) `PinAuthenticator` called
  `SettingsResolver::bool($key)` without a branch, an overload that returns the declared default,
  so the PIN gate read `false` for every branch that had turned it on.
  **Both compile, both read correctly, both answer a different question than the one asked.**
  The test for the first only caught it because the assertion demanded a specific message.
- Move/merge belongs in one service. The same two rules — no move while paying, locks in
  ascending id order — run through moving a party, moving a round and merging two bills. Split
  across three controller methods, one of them forgets one of the rules.
- BR-19 (moving onto an occupied table is a merge, never implicit) is as much interface as
  domain: the destination list marks which tables would be a merge before the waiter taps.
- Deadlock guard tested the way PH-03 tested stock: the mechanism is proven (real row lock via
  `pg_locks`; ordering independent of the order the caller named the rows), parallel load is
  explicitly deferred to PH-14 rather than claimed.
- `REQ-ORD-011` recorded as not delivered and not scoped, rather than ticked: quantity editing
  needs a DRAFT round and every round is placed on submit, so §25 C8 has nothing to race on yet.
- **The browser pass did not run** — the dev session had expired, and minting one by setting an
  auth cookie was blocked. Asked Fakrul for a single sign-in. Every phase with a browser pass has
  found defects a green suite could not see, so this is an outstanding gap, not a skipped nicety.

### 2026-09-08 — PH-06 Kitchen display & printing
- **Four defects this phase, all the same shape: silent data loss with no error raised.**
  (1) `bytea` bound by PDO as a C string truncated the ESC/POS payload at its first NUL — a real
  ticket would have printed its header and stopped. (2) The same NUL truncated the `text`
  preview. (3) The preview stripper removed control bytes but left their printable arguments,
  so the admin viewer read `@a!ETABLE 4`. (4) Catching a unique violation inside a PostgreSQL
  transaction does not recover it — it poisoned the order transaction it ran inside.
  **The pattern worth carrying: binary data and PostgreSQL text columns do not mix, and an
  error caught inside a transaction still aborted that transaction.**
- A design error the tests caught before the browser did: printing per STATION gives one printer
  two jobs for one order whenever a single machine serves two stations — the ordinary small-shop
  setup. Group by printer, render once.
- The browser pass again found what tests could not: a bare 403 with no way out on a wall tablet,
  and a KDS header that counted items while its lanes counted tickets ("6 new" over four
  tickets). Six phases, six browser passes, defects every time.
- Print jobs are durable rows, not calls: created after commit, rendered once and stored, retried
  with backoff against the stored bytes, and dead-lettered loudly rather than lost quietly.
- `EscPosNetworkDriver` written but **unverified against hardware**. OQ-06 still unanswered, so
  the default stays `null_log`, which writes real bytes to storage. Said plainly in the matrix so
  nobody reads this phase as "printing works".
