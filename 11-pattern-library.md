# Pattern Library
> Proven, reusable solutions indexed by problem type. Pull from here before re-inventing.

> **The patterns below are also data.** `coresentinel pattern` keeps the same fields this
> file documents — stack, problem, solution, gotchas, first used in — plus identity
> (`PAT-NNNN`), provenance (which incident taught it) and an occurrence count. A record
> renders back into the format below without loss.
>
> ```bash
> coresentinel pattern add --name "..." --problem "..." --solution "..." --incident INC-0001
> coresentinel pattern list
> ```
>
> Recording the same pattern again counts an occurrence; it does not raise confidence.
> Three sightings of a guess make one guess seen three times.

As you build projects, add your patterns here. Each pattern should include:
- **Stack**: What tech it applies to
- **Problem**: What you're solving
- **Solution**: The approach or code pattern
- **Gotchas**: What to watch out for
- **First used in**: Which project

---

## Starter Patterns

### File Uploads & Document Storage
#### Flysystem SFTP / Local + mPDF Data-URI Render
- **Stack**: Hand-rolled PHP, mPDF, Flysystem
- **Problem**: Images (company logo, user avatars) render fine in HTML views but break when exported to mPDF or SFTP storage.
- **Solution**: Embed images directly as base64 data-URIs (`data:image/png;base64,...`) into the unified HTML view template.
- **Gotchas**: Validate PDF generation using `Output('', STRING_RETURN)` and assert the `%PDF` header byte signature in tests.
- **First used in**: DAISY 2.0 — Invoice PDF rendering

### Real-Time & Event Streams (SSE)
#### Single-Threaded Dev Server Freeze Avoidance
- **Stack**: PHP (Windows), Server-Sent Events (SSE)
- **Problem**: `php -S` built-in dev server on Windows is single-threaded (`PHP_CLI_SERVER_WORKERS` is POSIX-only). An active 55s SSE stream freezes all subsequent HTTP requests.
- **Solution**: Serve local dev via Apache vhost on a custom port (`http://localhost:8081`).
- **Gotchas**: Never run SSE or long-polling loops inside single-threaded dev environments on Windows.
- **First used in**: DAISY 2.0 — Omnichannel Workspace

### Database & Concurrency
#### Atomic Race-Free Action Guard
- **Stack**: MySQL / MariaDB, PHP
- **Problem**: Two agents click "Answer" or "Claim" simultaneously, resulting in race conditions with check-then-update queries.
- **Solution**: Perform a single atomic UPDATE query with state check: `UPDATE calls SET status='answered', agent_id=? WHERE id=? AND status='ringing'`. Verify `$stmt->rowCount() === 1`. If `0`, another worker claimed it first.
- **Gotchas**: Do not check status via `SELECT` prior to `UPDATE` unless inside an explicit InnoDB transaction lock.
- **First used in**: DAISY 2.0 — Call pickup control

### API Integration & Security
#### Encrypted Secrets at Rest
- **Stack**: PHP 8.2, OpenSSL (AES-256-GCM)
- **Problem**: Storing plain-text API keys/webhooks secrets in database tables exposes credentials on database backups.
- **Solution**: Encrypt all third-party secrets before writing to DB using app secret key (`AI::encryptKey($secret)`). Decrypt only at runtime when instantiating client wrappers.
- **Gotchas**: Never display decrypted secrets back to UI input fields; show placeholder badges instead.
- **First used in**: DAISY 2.0 — Channel configuration & AI settings

### SaaS / Feature Gating

#### Add a gateable feature module (DAISY)
- **Stack**: Hand-rolled PHP (DAISY 2.0), MySQL
- **Problem**: Ship a new module the platform owner can toggle per-plan from the console (shows in the features listing) — not an always-on core module.
- **Solution**: The dispatcher auto-gates any module whose name equals a `features.key` (`App.php` dispatch: `Feature::isFeature($module) && !Feature::enabled($module)` → 403). To ship gated module `foo`:
  1. Name it `modules/foo/controller.php` with `foo_index()` — module name MUST equal the feature key.
  2. One idempotent migration: `INSERT ... WHERE NOT EXISTS` a `features` row (key='foo'); a `permissions` row (`module='foo', action='view', resource=NULL` — use WHERE NOT EXISTS, not INSERT IGNORE, because a NULL resource can't dedupe on the unique key); and grant it to `super-admin`/`system-admin` in `role_permissions`. Migration 031's one-time CROSS JOIN already ran, so a NEW permission is NOT retroactively granted — grant it explicitly or existing tenant-admins get 403.
  3. Controller: `RBAC::require('foo.view')` as the first line; every query tenant-scoped by `Auth::tenantId()`.
  4. Route in `App.php` (static literals before `{id}`).
  5. Sidebar nav item gated `RBAC::can('foo.view')`; the sidebar's feature-gate loop hides it off-plan automatically (belt + suspenders).
- **Gotchas**: `Feature::all()`/`isFeature()` read the DB `features` table, NOT `config/plans.php` (that map is fresh-install seed only, kept in sync for catalog consistency). Plans are owner-managed DB data (migration 033) — do NOT hardcode plan grants in a migration; leave assignment to the console (enterprise `'*'` gets it free). No migration runner exists: apply with `mysql -u root <db> < migration.sql` and verify the seeded row before assuming the gate resolves.
- **First used in**: DAISY 2.0 — analytics module (migration 036)

---

## Laravel 13 + Inertia 3 + React 19 + TypeScript

> ⚠️ **`[LEARN]` — RESEARCH-SOURCED, NOT YET BATTLE-TESTED.** Captured during the Learn Protocol
> Phase 1 Research Sprint on **2026-08-14**, verified live against Packagist / npm registry /
> GitHub releases / official docs and package source — but **not yet proven in a shipped build**.
> Treat as `Assumed` confidence (0.50–0.89), not `Known`. Promote to full patterns after the first
> project in this stack ships (Learn Protocol Phase 3). First captured in: **E-Commerce Catalog System**.

### Version Baseline (verified 2026-08-14)
Laravel **13.x** (12 left bug-fix support 2026-08-13 — there is no LTS) · `inertiajs/inertia-laravel` **^3.3** ·
`@inertiajs/react` + `@inertiajs/vite` **^3.6** · React **19.2** (Inertia 3 *requires* 19+) ·
TypeScript **5.9 — NOT 7.0** · Vite **8.2** + `laravel-vite-plugin` **^3.2** · PHP **8.3–8.5** ·
Bootstrap **5.3.8** (Bootstrap 6 does not exist) · AdminLTE **4.3.1** · MySQL **8.0.17+**.
Breeze/Jetstream are dead paths (removed from the installer in L12; starter kits now use Fortify).
Ziggy is displaced by `laravel/wayfinder` (still pre-1.0 at 0.1.21). Axios was removed from Inertia in v3.

### Ecosystem Mapping (Learn Protocol §1b)
| Concept | Known (hand-rolled PHP / DAISY 2.0) | Laravel 13 + Inertia 3 + React |
|---|---|---|
| ORM | Hand-written PDO + `Model::query()` | Eloquent |
| Auth | `Auth::` static + session | Laravel Fortify (starter-kit default) |
| Routing | `App.php` dispatcher, literals before `{id}` | `routes/web.php` + `laravel/wayfinder` typed helpers |
| Middleware | Inline guards at controller top | `bootstrap/app.php` `->withMiddleware()` |
| Validation | Manual checks + `$errors[]` | FormRequest → `ValidationException` → **302 redirect**, never 422 |
| Template/View | Unified HTML view templates | React page components resolved by `@inertiajs/vite` |
| CLI | Bare PHP scripts | `php artisan` |
| Queue | None | `queue:work` (Horizon is unusable on native Windows) |
| Cache | None | `Cache::` / Redis |
| Type sync | None | `spatie/laravel-data` + `typescript-transformer`; Wayfinder for routes |

### Inertia 3 — Shared Props & Partial Reloads
- **Stack**: Laravel 13, Inertia 3, React 19
- **Problem**: `usePage().props.auth` becomes `undefined` mid-session and the layout throws.
- **Solution**: a partial reload (`router.reload({only:['products']})`) filters the **entire** prop bag, shared props included. Wrap anything the layout always needs in `Inertia::always()`:
  ```php
  'auth'  => Inertia::always(fn () => ['user' => $request->user()?->only('id','name','email')]),
  'flash' => Inertia::always(fn () => ['message' => $request->session()->get('message')]),
  ```
  For heavy, rarely-changing shell data (sidebar menu tree, permission matrix, lookups) use **`Inertia::once()`** — resolved once server-side, carried client-side, then omitted from the payload entirely. Declare it in the shared middleware, not per-page; once-props are only remembered while navigating between pages that include them.
  > ⚠️ **The method is `Inertia::once()`, added in `inertia-laravel` 2.0.12 (Dec 2025).** An earlier draft of this entry said `Inertia::shareOnce()` — **no such method exists.** Corrected 2026-08-14 after live verification.
- **Gotchas**: closures defer *computation*, not payload — the prop is still sent. An eager `auth.user` with roles/permissions rides every page load, every partial reload and every poll tick, and lands in browser history state (Firefox errors past 16 MiB). `Inertia::lazy()` was renamed `Inertia::optional()` in v3 and the old class is deleted.
- **First used in**: E-Commerce Catalog System (planned)

### Inertia — Props Leak Every Model Field
- **Stack**: Laravel 13, Inertia 3
- **Problem**: passing an Eloquent model as a prop exposes far more than intended.
- **Solution**: Inertia serializes any `Arrayable` via `toArray()` — every non-`$hidden` column, every `$appends` accessor, every loaded relation, recursively. `$hidden` protects `User.password` and nothing else. Route every prop through a `spatie/laravel-data` DTO (which also generates the matching TS interface). Enforce in code review from commit #1.
- **Gotchas**: Inertia's maintainers state explicitly this is not considered a security issue and there is **no framework-level shield**. v3 moved the initial payload from a `data-page` attribute into `<script type="application/json">` — that changed *where* you read it in DevTools, not *whether* it's readable.
- **First used in**: E-Commerce Catalog System (planned)

### Inertia 3 — TypeScript via `InertiaConfig` Declaration Merging
- **Stack**: Inertia 3, TypeScript 5.9
- **Problem**: v2's hand-rolled `PageProps` union no longer matches how v3 types shared props.
- **Solution**: augment `InertiaConfig` once, globally, in `resources/js/types/global.d.ts`:
  ```ts
  import '@inertiajs/core'   // REQUIRED
  declare module '@inertiajs/core' {
    export interface InertiaConfig {
      sharedPageProps: { auth: Auth; appName: string }
      flashDataType:   { toast?: { type: 'success'|'error'; message: string } }
      layoutProps:     { title: string }
    }
  }
  ```
  Page-specific props then go on the default export's normal props interface; `usePage<T>()`'s generic now means *page* props only.
- **Gotchas**: omitting the bare `import '@inertiajs/core'` makes `declare module` **replace** rather than augment. `tsconfig.include` must cover `**/*.d.ts`. **pnpm users must add `public-hoist-pattern[]=@inertiajs/core` to `.npmrc`** or the augmentation never resolves. Retrofitting this later is painful — do it day one.
- **First used in**: E-Commerce Catalog System (planned)

### Inertia 3 — Stale Lazy-Chunk 404s After Deploy
- **Stack**: Inertia 3, Vite 8
- **Problem**: an open tab throws `TypeError: Failed to fetch dynamically imported module` after a deploy. Inertia's asset-versioning (409 → full visit) does **not** cover this.
- **Solution**: `@inertiajs/vite` defaults `lazy: true`, so code splitting — and therefore content-hashed chunk filenames — is on by default in v3. Handle Vite's own event and keep the previous build around:
  ```js
  window.addEventListener('vite:preloadError', (e) => { e.preventDefault(); location.reload() })
  ```
  Root cause of the 404 is atomic-symlink deploys deleting the old `public/build` immediately — keep it for a grace period.
- **Gotchas**: background requests deliberately do **not** force a reload (protects unsaved forms), so a long-lived admin tab can sit on stale JS indefinitely. Since v3.6.0 you can intercept: `router.on('location', e => { e.preventDefault(); showToast(...) })`.
- **First used in**: E-Commerce Catalog System (planned)

### AdminLTE 4 in React — The Safe/Unsafe Split
- **Stack**: AdminLTE 4.3.1, Bootstrap 5.3.8, React 19, Inertia 3
- **Problem**: "AdminLTE is jQuery, it will fight React" — true of v3, **obsolete for v4**.
- **Solution**: AdminLTE 4 is jQuery-free, TypeScript-native, ESM, with an explicit `initialize()`/`teardown()` AbortController lifecycle built for frameworks that construct the layout after `DOMContentLoaded`. Split by what owns the DOM:
  - ✅ **All SCSS** — inert, ~90% of AdminLTE's value.
  - ✅ **`PushMenu`, `Layout`, `ColorMode`, `FullScreen`** — they write only to `document.body` / `<html>`, outside the React root. React never sees `document.body.classList`. Instantiate once in the persistent layout's `useEffect`, `teardown()` on unmount.
  - ❌ **`Treeview`, `CardWidget`, `SidebarSearch`** — they own DOM inside the React tree (`menu-open` classes and inline `slideDown` height styles on React-rendered `<li>`s; `remove` deletes nodes React believes it owns). Re-implement in React, ~200–300 lines.
  Use `react-bootstrap@2.10.10` for Modal/Dropdown/Tooltip/Offcanvas — AdminLTE's CSS skins them free since they emit standard Bootstrap classes.
- **Gotchas**: the rewrite is a **net gain** — a React treeview can auto-expand the active branch by matching `usePage().url` against a typed menu config, which DOM-state cannot do. The official `@adminlte/react` is **hard-coupled to Next.js** (`next/navigation`), v0.4.0, 2 stars — unusable outside Next. Every community port is abandoned. `PushMenu` already persists to `localStorage` key `lte.sidebar.state` — don't run a second persistence mechanism alongside it. Seed React state from localStorage **synchronously** in `useState(() => …)`, never in an effect, or the sidebar flashes the wrong width.
- **First used in**: E-Commerce Catalog System (planned)

### Bootstrap + AdminLTE 4 through Vite — `loadPaths` Is Mandatory
- **Stack**: Vite 8, Dart Sass, AdminLTE 4.3.1, Bootstrap 5.3.8
- **Problem**: `Can't find stylesheet to import` on every Bootstrap partial.
- **Solution**: AdminLTE 4 no longer vendors Bootstrap (it's a **peer dependency** `^5.3.8`), so its SCSS bare-imports it and Dart Sass can't resolve that. Required in `vite.config.ts`:
  ```ts
  css: { preprocessorOptions: { scss: {
    loadPaths: ['node_modules'],
    silenceDeprecations: ['import','global-builtin','color-functions','mixed-decls'],
    quietDeps: true,
  }}}
  ```
  Variable overrides must sit **after functions, before the AdminLTE import**:
  ```scss
  @import "bootstrap/scss/functions";
  $primary: #2b6cb0;
  @import "admin-lte/src/scss/adminlte";
  ```
- **Gotchas**: **keep `@import`, do not convert to `@use`** — AdminLTE 4.3.1's own `adminlte.scss` uses `@import` exclusively, and Bootstrap 5.3's docs carry an official note that the Dart Sass deprecation warnings can be ignored pending a long-term fix (module migration is a Bootstrap **6** goal). Hence `silenceDeprecations`, or every build emits a wall of noise. Pin `admin-lte` **exactly** — 5 releases in 3 months. npmjs.com's HTML page shows stale deps (bootstrap ^5.1.3 + jquery) — that's 3.2.x metadata leaking; the real 4.3.1 `package.json` has no jQuery at all.
- **First used in**: E-Commerce Catalog System (planned)

### E-Commerce — Product Variants Without EAV
- **Stack**: Laravel 13, MySQL 8.0.17+
- **Problem**: model product variations so "unlimited products" stays queryable and extensible.
- **Solution**: option / option_value / variant + `product_variant_option_values` pivot (Shopify/Medusa shape), with **one deviation: the option dictionary is global, not per-product free text** — that's what makes catalog-wide faceting ("everything in Red") a plain indexed join instead of string matching. Add `option_signature VARCHAR(191)` on the variant — sorted `option_value_id`s joined by `.`, `UNIQUE(product_id, option_signature)`:
  ```sql
  SELECT * FROM product_variants WHERE product_id = :pid AND option_signature = '12.45';
  ```
  One index seek. The frontend already knows which option values were clicked, so it builds the signature client-side. Price/stock/SKU live **only** on variants; every product always gets ≥1 variant.
- **Gotchas**: the pivot alone cannot prevent two variants sharing an identical option combination — the signature unique key does. Maintain it in the same transaction as the pivot sync (observer). The pivot's InnoDB PK `(variant_id, value_id)` is useless for "which variants are Red" — the reverse index `(option_value_id, product_variant_id)` is load-bearing. Nullable `variant_id` on cart/order items looks simpler but buys permanent `IF variant_id IS NULL` branching in every purchase, refund and report path. Design tops out around 50k products with 2–3 filters; past that move to Scout + Meilisearch — **which needs no schema change, and that's the point of choosing this over EAV or JSON**.
- **First used in**: E-Commerce Catalog System (planned)

### MySQL — Soft Deletes Break Unique Indexes
- **Stack**: Laravel, MySQL 8.0.13+
- **Problem**: a soft-deleted row still occupies its `slug` / `sku`, so recreating it fails on the unique index.
- **Solution**: `UNIQUE(slug, deleted_at)` does **not** fix this — MySQL treats NULLs as distinct, so two *live* rows would then both be allowed the same slug. Use a generated column as the sentinel:
  ```sql
  deleted_at_key TIMESTAMP AS (COALESCE(deleted_at,'1970-01-01 00:00:00')) VIRTUAL,
  UNIQUE KEY uq_product_slug (slug, deleted_at_key)
  ```
  Live rows share the sentinel and collide correctly; deleted rows are separated by deletion time.
- **Gotchas**: soft-deleting a parent must soft-delete children via a `deleting` observer — `ON DELETE CASCADE` never fires for a soft delete. Same trick enforces "one primary image per owner": `primary_guard VARCHAR(96) AS (IF(is_primary, CONCAT(imageable_type,':',imageable_id), NULL)) VIRTUAL` + `UNIQUE(primary_guard)`, since NULLs don't collide.
- **First used in**: E-Commerce Catalog System (planned)

### Money — Integer Minor Units, Not DECIMAL
- **Stack**: PHP, MySQL
- **Problem**: rounding bugs that only appear at specific quantities.
- **Solution**: store `INT UNSIGNED price_minor` (cents/sen). Both types are exact *in MySQL* — the argument is the **PHP boundary**: PDO returns `DECIMAL` as a **string**, so the first `$product->price * $qty` silently coerces to float. An integer column casts to `int` and stays exact through every operation. Every gateway (Stripe, Adyen, iPay88) takes minor units too, and `INT UNSIGNED` is half the index width of `DECIMAL(10,2)`.
- **Gotchas**: suffix every column `_minor` so the unit is never ambiguous. Ad-hoc SQL and BI tools need `/100`. Three-decimal currencies (KWD, BHD, TND) need a per-currency exponent — that's when `moneyphp/money` earns its place; before then a ~40-line value object is less indirection.
- **First used in**: E-Commerce Catalog System (planned)

### MariaDB — Indexed Virtual Columns & the `mariadb` Driver
- **Stack**: Laravel 11+, MariaDB 10.2–10.4
- **Problem**: MySQL-shaped advice silently breaks on MariaDB.
- **Solution**: Set **`DB_CONNECTION=mariadb`**, not `mysql`. Laravel has had a dedicated `MariaDbConnection` / `MariaDbGrammar` since 11 and `config/database.php` already ships a correct `mariadb` block. The decisive reason: **`renameColumn()` emits `ALTER TABLE … RENAME COLUMN`, which MariaDB only gained in 10.5.2** — `MariaDbGrammar` version-checks and falls back to the legacy `CHANGE old new <definition>` form, `MySqlGrammar` does not. On ≤10.4 under the `mysql` driver every `renameColumn()` migration is a hard syntax error. `joinLateral()` and JSON path functions also diverge.
  UNIQUE indexes on `VIRTUAL` generated columns **are** supported (InnoDB, since 10.2.3) — `PERSISTENT`/`STORED` is not required, and `COALESCE`/`IF`/`CONCAT` are deterministic enough to be legal in one.
- **Gotchas**: `ALTER TABLE` on a table with an **indexed** virtual column is forced to `ALGORITHM=COPY` — every future migration on that table is a full rebuild, and `->algorithm('inplace')` errors. A generated column **cannot read** a column carrying `ON UPDATE CASCADE` / `ON UPDATE SET NULL` / `ON DELETE SET NULL`. `utf8mb4_0900_ai_ci` doesn't exist (that's MySQL 8); `utf8mb4_uca1400_*` needs 10.10+ — use `utf8mb4_unicode_ci`, since MariaDB's own default is the weaker `general_ci`. No `defaultStringLength(191)` needed: `innodb_default_row_format` has been `dynamic` since 10.2, giving 3072-byte keys. `JSON` is a `LONGTEXT` alias compared **as text**, and the `->`/`->>` operators don't exist until **13.1**. Identifiers cap at 64 chars and Laravel does not truncate — pass explicit names via `constrained(indexName: …)`.
- **First used in**: E-Commerce Catalog System (planned)

## Laravel 12 + Blade + MySQL (server-rendered commerce)

> **BATTLE-TESTED.** Shipped in **Basic Custom E-Commerce** (2026-08-27): Laravel 12.68,
> PHP 8.3, Blade, MySQL 8/MariaDB 10.4, no Node, no queues. 199 tests / 564 assertions
> green on both engines. These are `Known` confidence, unlike the `[LEARN]`
> Laravel 13 + Inertia block above — which remains research-sourced and is **not**
> promoted by this project, because Inertia, React, Vite and Fortify were never used.

### Fail Closed on an Unverifiable Third-Party Response
- **Stack**: Laravel 12, any REST gateway (first used against ToyyibPay)
- **Problem**: You must confirm a payment server-side, but the vendor's API reference
  is unobtainable (403 to automated fetch) and community sources disagree on the
  response field names. You cannot write a parser you can prove correct.
- **Solution**: Do not guess a single field name, and do not block delivery either.
  Read an ordered list of **documented candidate keys**, and return an explicit
  `unverified` result when none matches:
  ```php
  private const STATUS_KEYS = ['billpaymentStatus', 'billPaymentStatus', 'status'];
  $status = $this->firstString($row, self::STATUS_KEYS);
  if ($status === null) {
      return PaymentVerification::unverified('No recognised status field.', $row);
  }
  ```
  `unverified` is a first-class outcome, not an exception: the caller leaves the order
  **pending**. Ship the integration complete and inert; one config change activates it
  once a human confirms the shape. Log the `reason` verbatim so the person resolving it
  is told exactly what was missing.
- **Gotchas**: The failure mode must be asymmetric and you must say so out loud —
  refusing to settle a real payment is recoverable, marking an unpaid order paid is not.
  Make the ambiguity configurable where it is cheap (`TOYYIBPAY_AMOUNT_FORMAT=decimal|cents`)
  and have the mismatch log print **both** interpretations, so the correct setting is
  obvious from one live response. Write the "this is deliberate, not a bug" note into the
  README and the deploy runbook — otherwise the next developer 'fixes' it by guessing.
- **First used in**: Basic Custom E-Commerce — REQ-005 / OQ-11

### OAuth Refresh-Token Rotation Under Concurrency
- **Stack**: Laravel 11+, any OAuth 2 provider that rotates refresh tokens (EasyParcel Open API)
- **Problem**: The refresh token changes on every use. Two concurrent requests that both
  find the access token expired will both refresh; rotation invalidates one of the results
  and the integration dies silently at the *next* refresh, hours later.
- **Solution**: Serialise with an atomic cache lock and **re-read the token row inside the
  lock** — the waiter must not act on the row it read before blocking:
  ```php
  return Cache::lock('provider:refresh', 10)->block(5, function () {
      $fresh = $this->token();                       // re-read INSIDE the lock
      if (! $fresh->isExpired()) return $fresh->access_token;   // someone else did it
      $this->storeTokens($this->requestToken([...])); // persist the NEW refresh token
      return $this->token()?->access_token;
  });
  ```
- **Gotchas**: **Persisting the new refresh token is the whole point** — keeping the old one
  is the silent killer. The `file` cache driver supports `Cache::lock()`, so this needs no
  Redis and no extra table. Tokens cannot live in `.env`: they rotate at runtime, and after
  `config:cache` Laravel does not read `.env` at all — store them in a table with the
  Eloquent `encrypted` cast. Set the app cipher **before** the first token is written;
  changing it later makes existing ciphertext undecryptable.
- **First used in**: Basic Custom E-Commerce — REQ-006

### Money Across a Decimal-String API Boundary
- **Stack**: PHP 8.3, any API returning prices as strings (EasyParcel `pricing.total_amount`)
- **Problem**: Internal money is integer minor units, but the vendor returns `"10.84"`.
  A `(int) ($amount * 100)` conversion reintroduces exactly the float error the integer
  storage exists to prevent.
- **Solution**: One conversion function, called once at the service boundary, that never
  multiplies by 100 as a float — split on the decimal point, pad to three places, and round
  on the third digit as integers:
  ```php
  [$whole, $fraction] = array_pad(explode('.', $trimmed, 2), 2, '0');
  $fraction = str_pad(substr($fraction, 0, 3), 3, '0', STR_PAD_RIGHT);
  $minor = intdiv((int) $whole * 1000 + (int) $fraction + 5, 10);
  ```
  Reject anything not matching `/^-?\d+(\.\d+)?$/` rather than coercing it.
- **Gotchas**: Round at the third decimal, don't truncate — `"10.999"` must become `1100`,
  not `1099`. Keep the reverse (`format()`) display-only and never parse it back for
  arithmetic. Some gateways take minor units directly (ToyyibPay `billAmount` is in cents),
  in which case the correct amount of conversion code is **none**.
- **First used in**: Basic Custom E-Commerce — REQ-006

### Forced First-Login Password Change (handover credentials)
- **Stack**: Laravel 11+ with the default auth guard
- **Problem**: A seeded or handed-over admin credential survives into production because
  "force a password change on first login" was written in the runbook instead of the code.
- **Solution**: Three parts, none optional. A `users.must_change_password` flag; middleware
  on the whole admin group that redirects everywhere except the change form **and logout**
  (omit logout and you trap the user); and a seeder that **refuses to run in production**
  without real credentials in env:
  ```php
  if (app()->isProduction() && (blank($email) || blank($password))) {
      throw new RuntimeException('Refusing to seed a default admin in production.');
  }
  ```
  Provide `php artisan shop:create-admin` using `$this->secret()` as the supported server
  path — the password then never reaches the screen or shell history.
- **Gotchas**: Set the flag even when a real password was supplied via env: the person who
  typed it into `.env` should not be the only one who knows it. Call
  `Auth::logoutOtherDevices()` on change. Enforce the policy with
  `Password::min(12)->letters()->numbers()` and require `current_password`.
- **First used in**: Basic Custom E-Commerce — REQ-009

### Guarded Atomic Update in Eloquent (Laravel form of the Race-Free Action Guard)
- **Stack**: Laravel 11+, MySQL/MariaDB
- **Problem**: Decrement stock, or transition an order to paid, exactly once under
  concurrent callers — without `SELECT` then `UPDATE`.
- **Solution**: Put the predicate in the write and check the affected row count. The query
  builder returns it:
  ```php
  $ok = ProductVariant::query()->whereKey($id)
      ->where('stock_qty', '>=', $qty)->decrement('stock_qty', $qty) === 1;

  $first = Order::query()->whereKey($id)
      ->where('payment_status', PaymentStatus::Pending->value)
      ->update(['payment_status' => PaymentStatus::Paid->value]) === 1;
  ```
  Only the caller that gets `1` proceeds. A duplicate gateway callback gets `0` and is a no-op.
- **Gotchas**: Never `$model->decrement()` on a **loaded** model — that reads then writes and
  reintroduces the race. Test it against the **real engine**; SQLite will not tell the truth
  about these guarantees. When the guarded decrement fails after money was taken, flag the
  order (`needs_review`) rather than accepting it silently.
- **First used in**: Basic Custom E-Commerce — REQ-005 / REQ-008
  (Laravel expression of *Atomic Race-Free Action Guard*, above.)

### Route Model Binding — two traps in one nested admin resource
- **Stack**: Laravel 11+
- **Problem**: Two separate 404/500 bugs that both look like "the route is wrong".
- **Solution**:
  1. **`getRouteKeyName()` leaks.** Setting it to `'slug'` for pretty storefront URLs applies
     to **admin routes too**, so `route('admin.products.edit', $id)` 404s and renaming a
     product changes its admin URL. Pin admin routes explicitly: `{product:id}`.
  2. **A custom key turns on scoped bindings**, and Laravel derives the child relation from
     the **parameter name**: `{variation:id}` under `{product}` calls `Product::variations()`.
     If the relation is `variants()`, name the parameter `{variant}`. The URL segment
     (`/variations`) and the parameter name are independent.
- **Gotchas**: Scoped binding is a bonus once the name is right — a child belonging to another
  parent 404s before your own ownership check runs. Keep the explicit check anyway; it
  documents the invariant and survives a future route change.
- **First used in**: Basic Custom E-Commerce — REQ-001 / REQ-002

### Laravel Without Node (server-rendered, no build step)
- **Stack**: Laravel 11+/12, Blade + Bootstrap, cheap VPS or shared hosting
- **Problem**: The skeleton ships Vite + Tailwind, so deploying a CSS file requires Node on
  the build host — real operational cost for a server-rendered site with one stylesheet.
- **Solution**: Delete `package.json`, `vite.config.js` and `resources/css|js`. Vendor the CSS
  framework into `public/css/` and reference it with `asset()`. Strip every `npm`/`vite` line
  from `composer.json` scripts. Product uploads go to a `public/uploads` filesystem disk, so
  `storage:link` is not needed either.
- **Gotchas**: The skeleton's `welcome.blade.php` calls `@vite` behind a manifest check, so it
  silently keeps working — delete it or you ship a page pulling a remote font CDN. Assert the
  absence in a test (`assertStringNotContainsString('/build/assets', $html)`), otherwise a
  future package quietly reintroduces the dependency. Removing Vite deviates from the stock
  skeleton, so record it as a decision, not a silent omission.
- **First used in**: Basic Custom E-Commerce

### Laravel on Native Windows 11 (no WSL)
- **Stack**: Laravel 13, Windows 11, Vite 8
- **Problem**: which local environment, and what silently degrades.
- **Solution**: **XAMPP is disqualified** — current Windows builds cap at PHP 8.2.12 and Laravel 13 requires ^8.3. Use **Herd for Windows** (MySQL is a Pro feature, $99/yr) or **Laragon 8.6.1** (free, bundles MySQL 9.6 — but use nginx, not Apache, on PHP 8.5). `herd secure` matters more than it sounds: **three Laravel 13 / Inertia 3 features degrade silently on plain HTTP** — `Sec-Fetch-Site` CSRF checking (`PreventRequestForgery` returns **403, not 419**), history encryption (`crypto.subtle` is secure-context-only), and secure cookies. `laravel-vite-plugin` auto-detects Herd's cert via `detectTls` (`valetTls` is deprecated).
- **Gotchas**: **Horizon is confirmed broken** on native Windows — needs `ext-pcntl` *and* `ext-posix`, neither of which PHP-on-Windows has; Herd's maintainers say it's not solvable. `php artisan dev` is degraded: the tabbed `@laravel/multiplex` UI is macOS/Linux only and Pail needs `pcntl_fork`, so you get 3 of 4 processes. Queue workers: Supervisor is Linux-only, use NSSM. You do **not** need Vite `usePolling` on native Windows — every documented case is WSL2/VM/Docker. `resolve.tsconfigPaths` fails on Windows during the **SSR** build (Vite 8 + Rolldown, rolldown#8732). `Cannot find module '../rolldown-binding.win32-x64-msvc.node'` → delete `node_modules` **and** `package-lock.json`, reinstall. Avoid project paths that are deep or contain spaces. NTFS case-insensitivity lets `import './button'` resolve `Button.tsx` locally and break on Linux CI.
- **First used in**: E-Commerce Catalog System (planned)

---

## How to Add Patterns

After completing a significant feature, ask yourself:
1. Would I use this approach again in another project?
2. Did I discover a gotcha that others should know about?
3. Is there a specific code pattern that solved a tricky problem?

If yes to any, add it here under the appropriate category. Create new categories as needed.

Format:
```markdown
### [Category Name]

#### [Pattern Name]
- **Stack**: [e.g. Laravel + React]
- **Problem**: [What you're solving]
- **Solution**: [Code pattern or approach]
- **Gotchas**: [What to watch out for]
- **First used in**: [Project name]
```
