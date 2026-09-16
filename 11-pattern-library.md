# Pattern Library
> Proven, reusable solutions indexed by problem type. Pull from here before re-inventing.

> **The patterns below are also data.** `coresentinel pattern` keeps the same fields this
> file documents â€” stack, problem, solution, gotchas, first used in â€” plus identity
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
- **First used in**: DAISY 2.0 â€” Invoice PDF rendering

### Real-Time & Event Streams (SSE)
#### Single-Threaded Dev Server Freeze Avoidance
- **Stack**: PHP (Windows), Server-Sent Events (SSE)
- **Problem**: `php -S` built-in dev server on Windows is single-threaded (`PHP_CLI_SERVER_WORKERS` is POSIX-only). An active 55s SSE stream freezes all subsequent HTTP requests.
- **Solution**: Serve local dev via Apache vhost on a custom port (`http://localhost:8081`).
- **Gotchas**: Never run SSE or long-polling loops inside single-threaded dev environments on Windows.
- **First used in**: DAISY 2.0 â€” Omnichannel Workspace

### Database & Concurrency
#### Atomic Race-Free Action Guard
- **Stack**: MySQL / MariaDB, PHP
- **Problem**: Two agents click "Answer" or "Claim" simultaneously, resulting in race conditions with check-then-update queries.
- **Solution**: Perform a single atomic UPDATE query with state check: `UPDATE calls SET status='answered', agent_id=? WHERE id=? AND status='ringing'`. Verify `$stmt->rowCount() === 1`. If `0`, another worker claimed it first.
- **Gotchas**: Do not check status via `SELECT` prior to `UPDATE` unless inside an explicit InnoDB transaction lock.
- **First used in**: DAISY 2.0 â€” Call pickup control

### API Integration & Security
#### Encrypted Secrets at Rest
- **Stack**: PHP 8.2, OpenSSL (AES-256-GCM)
- **Problem**: Storing plain-text API keys/webhooks secrets in database tables exposes credentials on database backups.
- **Solution**: Encrypt all third-party secrets before writing to DB using app secret key (`AI::encryptKey($secret)`). Decrypt only at runtime when instantiating client wrappers.
- **Gotchas**: Never display decrypted secrets back to UI input fields; show placeholder badges instead.
- **First used in**: DAISY 2.0 â€” Channel configuration & AI settings

### SaaS / Feature Gating

#### Add a gateable feature module (DAISY)
- **Stack**: Hand-rolled PHP (DAISY 2.0), MySQL
- **Problem**: Ship a new module the platform owner can toggle per-plan from the console (shows in the features listing) â€” not an always-on core module.
- **Solution**: The dispatcher auto-gates any module whose name equals a `features.key` (`App.php` dispatch: `Feature::isFeature($module) && !Feature::enabled($module)` â†’ 403). To ship gated module `foo`:
  1. Name it `modules/foo/controller.php` with `foo_index()` â€” module name MUST equal the feature key.
  2. One idempotent migration: `INSERT ... WHERE NOT EXISTS` a `features` row (key='foo'); a `permissions` row (`module='foo', action='view', resource=NULL` â€” use WHERE NOT EXISTS, not INSERT IGNORE, because a NULL resource can't dedupe on the unique key); and grant it to `super-admin`/`system-admin` in `role_permissions`. Migration 031's one-time CROSS JOIN already ran, so a NEW permission is NOT retroactively granted â€” grant it explicitly or existing tenant-admins get 403.
  3. Controller: `RBAC::require('foo.view')` as the first line; every query tenant-scoped by `Auth::tenantId()`.
  4. Route in `App.php` (static literals before `{id}`).
  5. Sidebar nav item gated `RBAC::can('foo.view')`; the sidebar's feature-gate loop hides it off-plan automatically (belt + suspenders).
- **Gotchas**: `Feature::all()`/`isFeature()` read the DB `features` table, NOT `config/plans.php` (that map is fresh-install seed only, kept in sync for catalog consistency). Plans are owner-managed DB data (migration 033) â€” do NOT hardcode plan grants in a migration; leave assignment to the console (enterprise `'*'` gets it free). No migration runner exists: apply with `mysql -u root <db> < migration.sql` and verify the seeded row before assuming the gate resolves.
- **First used in**: DAISY 2.0 â€” analytics module (migration 036)

---

## Laravel 13 + Inertia 3 + React 19 + TypeScript

> âš ï¸ **`[LEARN]` â€” RESEARCH-SOURCED, NOT YET BATTLE-TESTED.** Captured during the Learn Protocol
> Phase 1 Research Sprint on **2026-08-14**, verified live against Packagist / npm registry /
> GitHub releases / official docs and package source â€” but **not yet proven in a shipped build**.
> Treat as `Assumed` confidence (0.50â€“0.89), not `Known`. Promote to full patterns after the first
> project in this stack ships (Learn Protocol Phase 3). First captured in: **E-Commerce Catalog System**.

### Version Baseline (verified 2026-08-14)
Laravel **13.x** (12 left bug-fix support 2026-08-13 â€” there is no LTS) Â· `inertiajs/inertia-laravel` **^3.3** Â·
`@inertiajs/react` + `@inertiajs/vite` **^3.6** Â· React **19.2** (Inertia 3 *requires* 19+) Â·
TypeScript **5.9 â€” NOT 7.0** Â· Vite **8.2** + `laravel-vite-plugin` **^3.2** Â· PHP **8.3â€“8.5** Â·
Bootstrap **5.3.8** (Bootstrap 6 does not exist) Â· AdminLTE **4.3.1** *(â†’ **4.9.1** as of
2026-08-27, re-verified against the npm registry â€” check before pinning)* Â· MySQL **8.0.17+**.
Breeze/Jetstream are dead paths (removed from the installer in L12; starter kits now use Fortify).
Ziggy is displaced by `laravel/wayfinder` (still pre-1.0 at 0.1.21). Axios was removed from Inertia in v3.

### Ecosystem Mapping (Learn Protocol Â§1b)
| Concept | Known (hand-rolled PHP / DAISY 2.0) | Laravel 13 + Inertia 3 + React |
|---|---|---|
| ORM | Hand-written PDO + `Model::query()` | Eloquent |
| Auth | `Auth::` static + session | Laravel Fortify (starter-kit default) |
| Routing | `App.php` dispatcher, literals before `{id}` | `routes/web.php` + `laravel/wayfinder` typed helpers |
| Middleware | Inline guards at controller top | `bootstrap/app.php` `->withMiddleware()` |
| Validation | Manual checks + `$errors[]` | FormRequest â†’ `ValidationException` â†’ **302 redirect**, never 422 |
| Template/View | Unified HTML view templates | React page components resolved by `@inertiajs/vite` |
| CLI | Bare PHP scripts | `php artisan` |
| Queue | None | `queue:work` (Horizon is unusable on native Windows) |
| Cache | None | `Cache::` / Redis |
| Type sync | None | `spatie/laravel-data` + `typescript-transformer`; Wayfinder for routes |

### Inertia 3 â€” Shared Props & Partial Reloads
- **Stack**: Laravel 13, Inertia 3, React 19
- **Problem**: `usePage().props.auth` becomes `undefined` mid-session and the layout throws.
- **Solution**: a partial reload (`router.reload({only:['products']})`) filters the **entire** prop bag, shared props included. Wrap anything the layout always needs in `Inertia::always()`:
  ```php
  'auth'  => Inertia::always(fn () => ['user' => $request->user()?->only('id','name','email')]),
  'flash' => Inertia::always(fn () => ['message' => $request->session()->get('message')]),
  ```
  For heavy, rarely-changing shell data (sidebar menu tree, permission matrix, lookups) use **`Inertia::once()`** â€” resolved once server-side, carried client-side, then omitted from the payload entirely. Declare it in the shared middleware, not per-page; once-props are only remembered while navigating between pages that include them.
  > âš ï¸ **The method is `Inertia::once()`, added in `inertia-laravel` 2.0.12 (Dec 2025).** An earlier draft of this entry said `Inertia::shareOnce()` â€” **no such method exists.** Corrected 2026-08-14 after live verification.
- **Gotchas**: closures defer *computation*, not payload â€” the prop is still sent. An eager `auth.user` with roles/permissions rides every page load, every partial reload and every poll tick, and lands in browser history state (Firefox errors past 16 MiB). `Inertia::lazy()` was renamed `Inertia::optional()` in v3 and the old class is deleted.
- **First used in**: E-Commerce Catalog System (planned)

### Inertia â€” Props Leak Every Model Field
- **Stack**: Laravel 13, Inertia 3
- **Problem**: passing an Eloquent model as a prop exposes far more than intended.
- **Solution**: Inertia serializes any `Arrayable` via `toArray()` â€” every non-`$hidden` column, every `$appends` accessor, every loaded relation, recursively. `$hidden` protects `User.password` and nothing else. Route every prop through a `spatie/laravel-data` DTO (which also generates the matching TS interface). Enforce in code review from commit #1.
- **Gotchas**: Inertia's maintainers state explicitly this is not considered a security issue and there is **no framework-level shield**. v3 moved the initial payload from a `data-page` attribute into `<script type="application/json">` â€” that changed *where* you read it in DevTools, not *whether* it's readable.
- **First used in**: E-Commerce Catalog System (planned)

### Inertia 3 â€” TypeScript via `InertiaConfig` Declaration Merging
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
- **Gotchas**: omitting the bare `import '@inertiajs/core'` makes `declare module` **replace** rather than augment. `tsconfig.include` must cover `**/*.d.ts`. **pnpm users must add `public-hoist-pattern[]=@inertiajs/core` to `.npmrc`** or the augmentation never resolves. Retrofitting this later is painful â€” do it day one.
- **First used in**: E-Commerce Catalog System (planned)

### Inertia 3 â€” Stale Lazy-Chunk 404s After Deploy
- **Stack**: Inertia 3, Vite 8
- **Problem**: an open tab throws `TypeError: Failed to fetch dynamically imported module` after a deploy. Inertia's asset-versioning (409 â†’ full visit) does **not** cover this.
- **Solution**: `@inertiajs/vite` defaults `lazy: true`, so code splitting â€” and therefore content-hashed chunk filenames â€” is on by default in v3. Handle Vite's own event and keep the previous build around:
  ```js
  window.addEventListener('vite:preloadError', (e) => { e.preventDefault(); location.reload() })
  ```
  Root cause of the 404 is atomic-symlink deploys deleting the old `public/build` immediately â€” keep it for a grace period.
- **Gotchas**: background requests deliberately do **not** force a reload (protects unsaved forms), so a long-lived admin tab can sit on stale JS indefinitely. Since v3.6.0 you can intercept: `router.on('location', e => { e.preventDefault(); showToast(...) })`.
- **First used in**: E-Commerce Catalog System (planned)

### AdminLTE 4 in React â€” The Safe/Unsafe Split
- **Stack**: AdminLTE 4.3.1, Bootstrap 5.3.8, React 19, Inertia 3
- **Problem**: "AdminLTE is jQuery, it will fight React" â€” true of v3, **obsolete for v4**.
- **Solution**: AdminLTE 4 is jQuery-free, TypeScript-native, ESM, with an explicit `initialize()`/`teardown()` AbortController lifecycle built for frameworks that construct the layout after `DOMContentLoaded`. Split by what owns the DOM:
  - âœ… **All SCSS** â€” inert, ~90% of AdminLTE's value.
  - âœ… **`PushMenu`, `Layout`, `ColorMode`, `FullScreen`** â€” they write only to `document.body` / `<html>`, outside the React root. React never sees `document.body.classList`. Instantiate once in the persistent layout's `useEffect`, `teardown()` on unmount.
  - âŒ **`Treeview`, `CardWidget`, `SidebarSearch`** â€” they own DOM inside the React tree (`menu-open` classes and inline `slideDown` height styles on React-rendered `<li>`s; `remove` deletes nodes React believes it owns). Re-implement in React, ~200â€“300 lines.
  Use `react-bootstrap@2.10.10` for Modal/Dropdown/Tooltip/Offcanvas â€” AdminLTE's CSS skins them free since they emit standard Bootstrap classes.
- **Gotchas**: the rewrite is a **net gain** â€” a React treeview can auto-expand the active branch by matching `usePage().url` against a typed menu config, which DOM-state cannot do. The official `@adminlte/react` is **hard-coupled to Next.js** (`next/navigation`), v0.4.0, 2 stars â€” unusable outside Next. Every community port is abandoned. `PushMenu` already persists to `localStorage` key `lte.sidebar.state` â€” don't run a second persistence mechanism alongside it. Seed React state from localStorage **synchronously** in `useState(() => â€¦)`, never in an effect, or the sidebar flashes the wrong width.
- **First used in**: E-Commerce Catalog System (planned)

### Bootstrap + AdminLTE 4 through Vite â€” `loadPaths` Is Mandatory
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
- **Gotchas**: **keep `@import`, do not convert to `@use`** â€” AdminLTE 4.3.1's own `adminlte.scss` uses `@import` exclusively, and Bootstrap 5.3's docs carry an official note that the Dart Sass deprecation warnings can be ignored pending a long-term fix (module migration is a Bootstrap **6** goal). Hence `silenceDeprecations`, or every build emits a wall of noise. Pin `admin-lte` **exactly** â€” 5 releases in 3 months. npmjs.com's HTML page shows stale deps (bootstrap ^5.1.3 + jquery) â€” that's 3.2.x metadata leaking; the real 4.3.1 `package.json` has no jQuery at all.
- **First used in**: E-Commerce Catalog System (planned)

### E-Commerce â€” Product Variants Without EAV
- **Stack**: Laravel 13, MySQL 8.0.17+
- **Problem**: model product variations so "unlimited products" stays queryable and extensible.
- **Solution**: option / option_value / variant + `product_variant_option_values` pivot (Shopify/Medusa shape), with **one deviation: the option dictionary is global, not per-product free text** â€” that's what makes catalog-wide faceting ("everything in Red") a plain indexed join instead of string matching. Add `option_signature VARCHAR(191)` on the variant â€” sorted `option_value_id`s joined by `.`, `UNIQUE(product_id, option_signature)`:
  ```sql
  SELECT * FROM product_variants WHERE product_id = :pid AND option_signature = '12.45';
  ```
  One index seek. The frontend already knows which option values were clicked, so it builds the signature client-side. Price/stock/SKU live **only** on variants; every product always gets â‰¥1 variant.
- **Gotchas**: the pivot alone cannot prevent two variants sharing an identical option combination â€” the signature unique key does. Maintain it in the same transaction as the pivot sync (observer). The pivot's InnoDB PK `(variant_id, value_id)` is useless for "which variants are Red" â€” the reverse index `(option_value_id, product_variant_id)` is load-bearing. Nullable `variant_id` on cart/order items looks simpler but buys permanent `IF variant_id IS NULL` branching in every purchase, refund and report path. Design tops out around 50k products with 2â€“3 filters; past that move to Scout + Meilisearch â€” **which needs no schema change, and that's the point of choosing this over EAV or JSON**.
- **First used in**: E-Commerce Catalog System (planned)

### MySQL â€” Soft Deletes Break Unique Indexes
- **Stack**: Laravel, MySQL 8.0.13+
- **Problem**: a soft-deleted row still occupies its `slug` / `sku`, so recreating it fails on the unique index.
- **Solution**: `UNIQUE(slug, deleted_at)` does **not** fix this â€” MySQL treats NULLs as distinct, so two *live* rows would then both be allowed the same slug. Use a generated column as the sentinel:
  ```sql
  deleted_at_key TIMESTAMP AS (COALESCE(deleted_at,'1970-01-01 00:00:00')) VIRTUAL,
  UNIQUE KEY uq_product_slug (slug, deleted_at_key)
  ```
  Live rows share the sentinel and collide correctly; deleted rows are separated by deletion time.
- **Gotchas**: soft-deleting a parent must soft-delete children via a `deleting` observer â€” `ON DELETE CASCADE` never fires for a soft delete. Same trick enforces "one primary image per owner": `primary_guard VARCHAR(96) AS (IF(is_primary, CONCAT(imageable_type,':',imageable_id), NULL)) VIRTUAL` + `UNIQUE(primary_guard)`, since NULLs don't collide.
- **First used in**: E-Commerce Catalog System (planned)

### Money â€” Integer Minor Units, Not DECIMAL
- **Stack**: PHP, MySQL
- **Problem**: rounding bugs that only appear at specific quantities.
- **Solution**: store `INT UNSIGNED price_minor` (cents/sen). Both types are exact *in MySQL* â€” the argument is the **PHP boundary**: PDO returns `DECIMAL` as a **string**, so the first `$product->price * $qty` silently coerces to float. An integer column casts to `int` and stays exact through every operation. Every gateway (Stripe, Adyen, iPay88) takes minor units too, and `INT UNSIGNED` is half the index width of `DECIMAL(10,2)`.
- **Gotchas**: suffix every column `_minor` so the unit is never ambiguous. Ad-hoc SQL and BI tools need `/100`. Three-decimal currencies (KWD, BHD, TND) need a per-currency exponent â€” that's when `moneyphp/money` earns its place; before then a ~40-line value object is less indirection.
- **First used in**: E-Commerce Catalog System (planned)

### MariaDB â€” Indexed Virtual Columns & the `mariadb` Driver
- **Stack**: Laravel 11+, MariaDB 10.2â€“10.4
- **Problem**: MySQL-shaped advice silently breaks on MariaDB.
- **Solution**: Set **`DB_CONNECTION=mariadb`**, not `mysql`. Laravel has had a dedicated `MariaDbConnection` / `MariaDbGrammar` since 11 and `config/database.php` already ships a correct `mariadb` block. The decisive reason: **`renameColumn()` emits `ALTER TABLE â€¦ RENAME COLUMN`, which MariaDB only gained in 10.5.2** â€” `MariaDbGrammar` version-checks and falls back to the legacy `CHANGE old new <definition>` form, `MySqlGrammar` does not. On â‰¤10.4 under the `mysql` driver every `renameColumn()` migration is a hard syntax error. `joinLateral()` and JSON path functions also diverge.
  UNIQUE indexes on `VIRTUAL` generated columns **are** supported (InnoDB, since 10.2.3) â€” `PERSISTENT`/`STORED` is not required, and `COALESCE`/`IF`/`CONCAT` are deterministic enough to be legal in one.
- **Gotchas**: `ALTER TABLE` on a table with an **indexed** virtual column is forced to `ALGORITHM=COPY` â€” every future migration on that table is a full rebuild, and `->algorithm('inplace')` errors. A generated column **cannot read** a column carrying `ON UPDATE CASCADE` / `ON UPDATE SET NULL` / `ON DELETE SET NULL`. `utf8mb4_0900_ai_ci` doesn't exist (that's MySQL 8); `utf8mb4_uca1400_*` needs 10.10+ â€” use `utf8mb4_unicode_ci`, since MariaDB's own default is the weaker `general_ci`. No `defaultStringLength(191)` needed: `innodb_default_row_format` has been `dynamic` since 10.2, giving 3072-byte keys. `JSON` is a `LONGTEXT` alias compared **as text**, and the `->`/`->>` operators don't exist until **13.1**. Identifiers cap at 64 chars and Laravel does not truncate â€” pass explicit names via `constrained(indexName: â€¦)`.
- **First used in**: E-Commerce Catalog System (planned)

## Laravel 12 + Blade + MySQL (server-rendered commerce)

> **BATTLE-TESTED.** Shipped in **Basic Custom E-Commerce** (2026-08-27): Laravel 12.68,
> PHP 8.3, Blade, MySQL 8/MariaDB 10.4, no Node, no queues. 199 tests / 564 assertions
> green on both engines. These are `Known` confidence, unlike the `[LEARN]`
> Laravel 13 + Inertia block above â€” which remains research-sourced and is **not**
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
- **Gotchas**: The failure mode must be asymmetric and you must say so out loud â€”
  refusing to settle a real payment is recoverable, marking an unpaid order paid is not.
  Make the ambiguity configurable where it is cheap (`TOYYIBPAY_AMOUNT_FORMAT=decimal|cents`)
  and have the mismatch log print **both** interpretations, so the correct setting is
  obvious from one live response. Write the "this is deliberate, not a bug" note into the
  README and the deploy runbook â€” otherwise the next developer 'fixes' it by guessing.
- **First used in**: Basic Custom E-Commerce â€” REQ-005 / OQ-11

### OAuth Refresh-Token Rotation Under Concurrency
- **Stack**: Laravel 11+, any OAuth 2 provider that rotates refresh tokens (EasyParcel Open API)
- **Problem**: The refresh token changes on every use. Two concurrent requests that both
  find the access token expired will both refresh; rotation invalidates one of the results
  and the integration dies silently at the *next* refresh, hours later.
- **Solution**: Serialise with an atomic cache lock and **re-read the token row inside the
  lock** â€” the waiter must not act on the row it read before blocking:
  ```php
  return Cache::lock('provider:refresh', 10)->block(5, function () {
      $fresh = $this->token();                       // re-read INSIDE the lock
      if (! $fresh->isExpired()) return $fresh->access_token;   // someone else did it
      $this->storeTokens($this->requestToken([...])); // persist the NEW refresh token
      return $this->token()?->access_token;
  });
  ```
- **Gotchas**: **Persisting the new refresh token is the whole point** â€” keeping the old one
  is the silent killer. The `file` cache driver supports `Cache::lock()`, so this needs no
  Redis and no extra table. Tokens cannot live in `.env`: they rotate at runtime, and after
  `config:cache` Laravel does not read `.env` at all â€” store them in a table with the
  Eloquent `encrypted` cast. Set the app cipher **before** the first token is written;
  changing it later makes existing ciphertext undecryptable.
- **First used in**: Basic Custom E-Commerce â€” REQ-006

### Money Across a Decimal-String API Boundary
- **Stack**: PHP 8.3, any API returning prices as strings (EasyParcel `pricing.total_amount`)
- **Problem**: Internal money is integer minor units, but the vendor returns `"10.84"`.
  A `(int) ($amount * 100)` conversion reintroduces exactly the float error the integer
  storage exists to prevent.
- **Solution**: One conversion function, called once at the service boundary, that never
  multiplies by 100 as a float â€” split on the decimal point, pad to three places, and round
  on the third digit as integers:
  ```php
  [$whole, $fraction] = array_pad(explode('.', $trimmed, 2), 2, '0');
  $fraction = str_pad(substr($fraction, 0, 3), 3, '0', STR_PAD_RIGHT);
  $minor = intdiv((int) $whole * 1000 + (int) $fraction + 5, 10);
  ```
  Reject anything not matching `/^-?\d+(\.\d+)?$/` rather than coercing it.
- **Gotchas**: Round at the third decimal, don't truncate â€” `"10.999"` must become `1100`,
  not `1099`. Keep the reverse (`format()`) display-only and never parse it back for
  arithmetic. Some gateways take minor units directly (ToyyibPay `billAmount` is in cents),
  in which case the correct amount of conversion code is **none**.
- **First used in**: Basic Custom E-Commerce â€” REQ-006

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
  path â€” the password then never reaches the screen or shell history.
- **Gotchas**: Set the flag even when a real password was supplied via env: the person who
  typed it into `.env` should not be the only one who knows it. Call
  `Auth::logoutOtherDevices()` on change. Enforce the policy with
  `Password::min(12)->letters()->numbers()` and require `current_password`.
- **First used in**: Basic Custom E-Commerce â€” REQ-009

### Guarded Atomic Update in Eloquent (Laravel form of the Race-Free Action Guard)
- **Stack**: Laravel 11+, MySQL/MariaDB
- **Problem**: Decrement stock, or transition an order to paid, exactly once under
  concurrent callers â€” without `SELECT` then `UPDATE`.
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
- **Gotchas**: Never `$model->decrement()` on a **loaded** model â€” that reads then writes and
  reintroduces the race. Test it against the **real engine**; SQLite will not tell the truth
  about these guarantees. When the guarded decrement fails after money was taken, flag the
  order (`needs_review`) rather than accepting it silently.
- **First used in**: Basic Custom E-Commerce â€” REQ-005 / REQ-008
  (Laravel expression of *Atomic Race-Free Action Guard*, above.)

### Route Model Binding â€” two traps in one nested admin resource
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
- **Gotchas**: Scoped binding is a bonus once the name is right â€” a child belonging to another
  parent 404s before your own ownership check runs. Keep the explicit check anyway; it
  documents the invariant and survives a future route change.
- **First used in**: Basic Custom E-Commerce â€” REQ-001 / REQ-002

### Renaming a Status Enum That Is Already in the Database
- **Stack**: Laravel 11+, PHP 8.1+ backed enums, MySQL/MariaDB
- **Problem**: A client wants their own operational vocabulary for a status column that is
  already populated (`pending_payment` â†’ `pending`, `paid` â†’ `new_order`, `shipped` â†’
  `in_delivery`, plus a genuinely new case).
- **Solution**: Because the column is `VARCHAR` and the enum lives in PHP, this is a **data**
  migration, not a schema one â€” but it is not optional: historical rows would otherwise hold
  values the enum can no longer cast, and **every read of them throws**. Remap, then move the
  column default, in one reversible migration:
  ```php
  private const RENAMES = ['pending_payment' => 'pending', 'paid' => 'new_order'];
  foreach (self::RENAMES as $from => $to) {
      DB::table('orders')->where('order_status', $from)->update(['order_status' => $to]);
  }
  $table->string('order_status', 32)->default('pending')->change();
  ```
  Write `down()` as the exact inverse and **run the rollback once** to prove it.
- **Gotchas**: Separate **system-set** states from **operator-selectable** ones. A state the
  system concludes (an oversell flag, a reconciliation hold) must not be assignable by hand:
  expose `selectable()` on the enum, restrict the form with
  `Rule::enum(Status::class)->only(Status::selectable())`, but keep every case in the **list
  filter** so those rows stay findable. Critically â€” if the current value is not in the
  `<select>`, the browser falls back to the **first option**, and saving the form silently
  reassigns the record. Render the current state as a selected `(current)` option when it is
  not selectable. Put domain predicates (`countsAsSale()`) on the enum so reports cannot drift
  from one another.
- **First used in**: Basic Custom E-Commerce (order statuses, 2026-08-27)

### Dashboard Metrics You Do Not Have Data For
- **Stack**: Any reporting UI built to a reference design
- **Problem**: A dashboard mock specifies tiles the system has no data source for â€” ad spend
  and ROAS on a store that tracks no advertising, "paid + COD" on a prepaid-only store.
- **Solution**: Never render a fabricated figure to fill a slot, and never render `0` for an
  untracked metric â€” **"we spent nothing" is a different claim from "we do not track this"**.
  Three honest options, in order of preference: (1) replace the tile with a metric the data
  actually supports â€” average order value, payment conversion; (2) give the figure a real
  admin-maintained source and compute from it; (3) render an explicit *Not tracked* state.
  Where an average or ratio has no denominator, pass `null` and say so â€” an average of nothing
  is undefined, not zero. Same for percentage change against a zero baseline: "up from zero"
  is not a percentage; render a dash.
- **Gotchas**: When you add a setting purely to feed a metric and then drop the metric, **remove
  the setting too** â€” validation rule, accessor, form field and test â€” or it becomes cruft
  behind a feature that no longer exists. Also check whether two tiles are structurally
  identical in *this* system before shipping both: a prepaid-only store's "sales" and
  "collection" coincide by construction, and the reference design only distinguished them
  because that business had COD.
- **First used in**: Basic Custom E-Commerce (owner dashboard, 2026-08-27)

### AdminLTE 4 in a Blade App Without Node
- **Stack**: Laravel 11+/12, Blade, AdminLTE 4.9.1, Bootstrap 5.3
- **Problem**: Get a real admin template without adopting a Node build chain, and
  without loading it from a CDN at runtime.
- **Solution**: AdminLTE 4 is a CSS/JS theme over Bootstrap 5.3, so in a Blade app it is
  a **template choice, not a framework change** â€” routes, controllers and models are
  untouched. Vendor four things into `public/`: `adminlte.min.css`, `adminlte.min.js`,
  Bootstrap's **`bootstrap.bundle.min.js`**, and Bootstrap Icons' CSS **plus its
  `fonts/*.woff2`**. Shell markup:
  `app-wrapper` â†’ `app-header` / `app-sidebar` (`data-bs-theme="dark"`) /
  `app-main` â†’ `app-content-header` + `app-content`. Sidebar toggling is
  `data-lte-toggle="sidebar"`; treeview is `data-lte-toggle="treeview"` on the `ul`.
- **Gotchas**: AdminLTE's JS does **not** include Bootstrap's â€” dropdowns and the
  sidebar toggle need the bundle loaded first, in that order. Bootstrap Icons' CSS
  references `fonts/` **relative to itself**, so the directory layout must be preserved;
  assert the resolved path on disk in a test (not over HTTP â€” serving static files is the
  web server's job and the router will 404 them). `woff2` precedes `woff` in the
  `@font-face` src, so shipping only the woff2 is safe. Delete any hand-rolled sidebar CSS
  the theme now owns rather than leaving it to collide. Pin the version: AdminLTE 4 moved
  4.3 â†’ 4.9 inside a few months.
- **First used in**: Basic Custom E-Commerce (admin panel, 2026-08-27)

### Laravel Without Node (server-rendered, no build step)
- **Stack**: Laravel 11+/12, Blade + Bootstrap, cheap VPS or shared hosting
- **Problem**: The skeleton ships Vite + Tailwind, so deploying a CSS file requires Node on
  the build host â€” real operational cost for a server-rendered site with one stylesheet.
- **Solution**: Delete `package.json`, `vite.config.js` and `resources/css|js`. Vendor the CSS
  framework into `public/css/` and reference it with `asset()`. Strip every `npm`/`vite` line
  from `composer.json` scripts. Product uploads go to a `public/uploads` filesystem disk, so
  `storage:link` is not needed either.
- **Gotchas**: The skeleton's `welcome.blade.php` calls `@vite` behind a manifest check, so it
  silently keeps working â€” delete it or you ship a page pulling a remote font CDN. Assert the
  absence in a test (`assertStringNotContainsString('/build/assets', $html)`), otherwise a
  future package quietly reintroduces the dependency. Removing Vite deviates from the stock
  skeleton, so record it as a decision, not a silent omission.
- **First used in**: Basic Custom E-Commerce

### Laravel 12 â€” `authorizeResource()` Is Dead, Use `HasMiddleware`
- **Stack**: Laravel 11+/12, resource controllers
- **Problem**: `$this->authorizeResource(Model::class, 'model')` in a controller constructor
  throws `Call to undefined method ...::middleware()` at request time â€” not at boot, so it
  looks like a routing fault.
- **Solution**: Laravel 11 moved middleware out of controllers, and the base `Controller` no
  longer has `middleware()`. `AuthorizesRequests::authorizeResource()` still calls it.
  Implement `HasMiddleware` and declare the same mapping explicitly:
  ```php
  class TransactionController extends Controller implements HasMiddleware
  {
      public static function middleware(): array
      {
          return [
              new Middleware('can:viewAny,'.Transaction::class, only: ['index']),
              new Middleware('can:create,'.Transaction::class, only: ['create', 'store']),
              new Middleware('can:update,transaction', only: ['edit', 'update']),
              new Middleware('can:delete,transaction', only: ['destroy']),
          ];
      }
  }
  ```
  The route-parameter form (`can:update,transaction`) resolves the bound model, so it keeps
  the "a method added later is covered by default" property `authorizeResource` had.
- **Gotchas**: keep the `AuthorizesRequests` trait only if a method still calls
  `$this->authorize()` directly. Route-model binding runs in `SubstituteBindings` (web group)
  **before** a route-level `admin` middleware, so an unauthorised request to a *nonexistent*
  id returns **404, not 403** â€” a test asserting 403 must use a real record or it passes for
  the wrong reason.
- **First used in**: Daily Spend â€” REQ-05â€¦REQ-13 (2026-08-29)

### Laravel 12 â€” `APP_TIMEZONE` Is Silently Ignored
- **Stack**: Laravel 11+/12 (slim skeleton)
- **Problem**: `APP_TIMEZONE=Asia/Kuala_Lumpur` in `.env` has no effect. `config('app.timezone')`
  stays `UTC`, `now()` returns UTC, and anything anchored to the app clock (scheduler,
  admin dashboards, seeders) lands on a different calendar day from users whose own timezone
  is set correctly.
- **Solution**: the slimmed `config/app.php` ships **`'timezone' => 'UTC'`** as a literal, not
  `env('APP_TIMEZONE', 'UTC')`. Change it, then assert it:
  ```php
  $this->assertSame(env('APP_TIMEZONE'), config('app.timezone'));
  ```
- **Gotchas**: this is invisible until two clocks are compared â€” the app looked fine because
  every *user-facing* query used `$user->timezone`. It surfaced only when demo data seeded with
  `now()` failed to appear under "today". Any project mixing `config('app.timezone')` and a
  per-user timezone needs this assertion.
- **First used in**: Daily Spend (2026-08-29)

### Date Columns Are Calendar Days, Not Instants
- **Stack**: Any ORM over MySQL/MariaDB with a `DATE` column
- **Problem**: a scheduled job compared `$model->next_date` (a `DATE` cast to Carbon) against
  `Carbon::now($user->timezone)->startOfDay()`. Same printed value, different instants â€”
  midnight-UTC vs midnight-UTC+8 â€” so `lte()` returned **false** and a due-today record never
  fired. Silent: no error, just nothing happening.
- **Solution**: compare calendar dates as calendar dates. ISO strings sort and compare
  correctly and carry no zone:
  ```php
  $today = Carbon::now($tz)->toDateString();
  while ($model->next_date->toDateString() <= $today) { â€¦ }
  ```
  Same for equality â€” `->toDateString() === $tomorrow` rather than `isSameDay()`.
- **Gotchas**: the failure only appears when the app clock and the user clock straddle
  midnight, so it passes all day and breaks for a window each night. Storing the column as
  `DATE` (not `DATETIME`) is the right call and removes conversion from every report path â€”
  but only if the *comparisons* respect that too.
- **First used in**: Daily Spend â€” REQ-13 (2026-08-29)

### Privilege Columns Must Not Be Fillable â€” and the Silent No-Op That Follows
- **Stack**: Laravel, any version
- **Problem**: `users.role` and `users.status` were correctly kept out of `$fillable`. An admin
  controller then did `$user->update(['status' => $validated['status']])` â€” which mass-assignment
  protection silently discards. **Suspending a user did nothing, with no error and a success
  toast.** A green-looking feature that had never worked.
- **Solution**: keep privilege out of `$fillable`, and give the model one explicit method that
  is the only supported path:
  ```php
  public function changeStatus(UserStatus $status): void
  {
      $this->forceFill(['status' => $status])->save();
  }
  ```
  Same for `email_verified_at` when a profile update should reset verification.
- **Gotchas**: `update()` returning `true` proves the query ran, not that the field changed.
  Any field deliberately excluded from `$fillable` needs a named mutator, or every future
  caller reintroduces the bug. A feature test asserting the *resulting state* catches it;
  one asserting the redirect does not.
- **First used in**: Daily Spend â€” REQ-20 (2026-08-29)

### Laravel on Native Windows 11 (no WSL)
- **Stack**: Laravel 13, Windows 11, Vite 8
- **Problem**: which local environment, and what silently degrades.
- **Solution**: **XAMPP is disqualified** â€” current Windows builds cap at PHP 8.2.12 and Laravel 13 requires ^8.3. Use **Herd for Windows** (MySQL is a Pro feature, $99/yr) or **Laragon 8.6.1** (free, bundles MySQL 9.6 â€” but use nginx, not Apache, on PHP 8.5). `herd secure` matters more than it sounds: **three Laravel 13 / Inertia 3 features degrade silently on plain HTTP** â€” `Sec-Fetch-Site` CSRF checking (`PreventRequestForgery` returns **403, not 419**), history encryption (`crypto.subtle` is secure-context-only), and secure cookies. `laravel-vite-plugin` auto-detects Herd's cert via `detectTls` (`valetTls` is deprecated).
- **Gotchas**: **Horizon is confirmed broken** on native Windows â€” needs `ext-pcntl` *and* `ext-posix`, neither of which PHP-on-Windows has; Herd's maintainers say it's not solvable. `php artisan dev` is degraded: the tabbed `@laravel/multiplex` UI is macOS/Linux only and Pail needs `pcntl_fork`, so you get 3 of 4 processes. Queue workers: Supervisor is Linux-only, use NSSM. You do **not** need Vite `usePolling` on native Windows â€” every documented case is WSL2/VM/Docker. `resolve.tsconfigPaths` fails on Windows during the **SSR** build (Vite 8 + Rolldown, rolldown#8732). `Cannot find module '../rolldown-binding.win32-x64-msvc.node'` â†’ delete `node_modules` **and** `package-lock.json`, reinstall. Avoid project paths that are deep or contain spaces. NTFS case-insensitivity lets `import './button'` resolve `Button.tsx` locally and break on Linux CI.
- **First used in**: E-Commerce Catalog System (planned)

### Registry-Backed RBAC â€” `Gate::before` That Cannot Become a Bypass
- **Stack**: Laravel 12 (any version with `Gate::before`), Inertia + Vue frontend
- **Problem**: a granular permission system needs `$user->can('staff.create')` to work without
  defining a Gate per slug â€” but the obvious `Gate::before` that grants it also short-circuits
  every model-bound policy, including tenant scoping. That turns a convenience into an IDOR
  generator the moment multi-tenancy lands.
- **Solution**: `before` answers **only** argument-free abilities, and returns `null` on a miss.
  ```php
  Gate::before(function (User $user, string $ability, array $arguments = []) {
      if ($arguments !== []) {
          return null;              // model-bound -> must reach the policy
      }

      return $user->hasPermission($ability) ?: null;   // null, never false
  });
  ```
  Verified in the framework source: `Gate::callBeforeCallbacks()` calls
  `$before($user, $ability, $arguments)` â€” the third argument is real, not assumed.
  Pair it with a `BasePolicy` whose every ability routes through one `allows()` method, so the
  tenant check has exactly one place to be added later.
- **Gotchas**: returning `false` instead of `null` on a miss silently kills every non-registry
  gate. The permission registry belongs in **code** (a `Permissions` class) with the table as its
  projection â€” validating `permissions.*` against the code list is what stops a crafted payload
  attaching an arbitrary string as a grant. And a superuser must hold every permission as
  **explicit rows**, never a wildcard or an `is_admin` flag: the moment a bypass exists, the
  granular registry is decoration.
- **First used in**: larisHQ â€” PH02 (2026-09-01)

### The Grant Ceiling â€” a user may never hand out what they do not hold
- **Stack**: any role/permission system with user-management permissions
- **Problem**: `staff.create` looks like a modest permission. With role assignment unguarded it
  is **full compromise**: create a user, attach the all-powerful role, choose its password, log
  in as it. The same hole exists one door along â€” if `roles.create` can author a role out of
  permissions its author lacks, role creation becomes the escalation path instead.
- **Solution**: one predicate, enforced on both doors.
  ```php
  public function canGrant(array $slugs): bool
  {
      return array_diff($slugs, $this->permissionSlugs()) === [];
  }
  ```
  Validate role **assignment** against the union of the selected roles' permissions, and role
  **authoring** against the posted permission list. Then narrow the forms to the same set, so the
  UI never offers a checkbox the validator will refuse.
- **Gotchas**: this is invisible in a fresh install, because the seeded superuser holds
  everything and passes trivially â€” it only bites the first real custom role. Test it in both
  directions: a rejection *and* an acceptance, or a too-strict ceiling ships unnoticed.
  Editing an existing role that already exceeds your ceiling correctly fails closed.
- **First used in**: larisHQ â€” PH02 (2026-09-01)

### Subdomain Multi-Tenancy on Laravel 12 â€” the four things that actually bite
- **Stack**: Laravel 12, Inertia 3, shared-schema tenancy (`tenant_id`), subdomain per tenant
- **Problem**: `Route::domain('{tenant}.'.$domain)` plus a global scope looks like a twenty-line
  feature. Four framework behaviours make it not one, and every one of them fails at runtime in a
  path you will not exercise by reading the code.
- **Solution**:
  1. **Resolve the tenant in a middleware *group*, never an alias.** `Authenticate` and
     `SubstituteBindings` are in the framework's middleware priority list, so route middleware runs
     *after* them. Resolve later than the guard and `EloquentUserProvider` looks a user up with no
     tenant bound â€” the scope has nothing to apply. Prepend to `web`, and no-op when the route has
     no `{tenant}` parameter.
  2. **`$route->forgetParameter('tenant')` once bound.** Otherwise Laravel passes the subdomain as
     the **first argument to every action in the group**, and every controller you ever write has
     to declare a parameter it never uses. The symptom is
     `destroy(): Argument #1 ($role) must be of type Role, string given`.
  3. **`URL::defaults(['tenant' => $slug])`, or `route()` throws.** Any named route inside the
     domain group needs the domain parameter â€” including the `route('login')` the unauthenticated
     handler calls, which turns a redirect into a 500.
  4. **Set `redirectGuestsTo()` in `bootstrap/app.php`, not a service provider.** The framework
     registers its own `fn () => route('login')` inside `afterResolving(HttpKernel::class)`, which
     runs *after* providers boot and silently wins.
- **Gotchas**: `EloquentUserProvider::retrieveById()` uses `newQuery()`, so global scopes **do**
  apply to authentication â€” that is what makes `unique(tenant_id, email)` work, and it means a
  foreign session simply resolves to no user rather than erroring. A shared `SESSION_DOMAIN=.{domain}`
  cookie spans every subdomain: do **not** invalidate the session when a user lands on another
  tenant's host, or visiting a URL signs them out of their own.
- **First used in**: larisHQ â€” PH03 (2026-09-01)

### Tenant Scope: read open, write closed
- **Stack**: any shared-schema multi-tenant ORM with global scopes
- **Problem**: what should a tenant-owned query do when *no* tenant is bound? Console commands,
  seeders and a cross-tenant admin console all legitimately run without one, so the scope cannot
  simply hard-fail. But "no filter" on a write puts a row in the wrong customer's data.
- **Solution**: give the two directions opposite defaults, and say why in the code.
  ```php
  // read: no tenant bound -> no filter
  public function apply(Builder $builder, Model $model): void
  {
      if (! app(Tenancy::class)->has()) { return; }
      $builder->where($model->qualifyColumn('tenant_id'), app(Tenancy::class)->id());
  }

  // write: no tenant bound -> refuse
  static::creating(function (Model $model) {
      if ($model->getAttribute('tenant_id') !== null) { return; }
      if (! app(Tenancy::class)->has()) { throw TenantContextMissing::forModel($model); }
      $model->setAttribute('tenant_id', app(Tenancy::class)->id());
  });
  ```
  An unscoped read shows too much and a test catches it. An unscoped write corrupts data and
  nothing catches it. Add a `RequireTenant` middleware on tenant route groups so a group added
  later without the domain constraint is a loud 500, not a quiet cross-tenant read.
- **Gotchas**: keep `tenant_id` **out of `$fillable`** â€” and then remember that
  `updateOrCreate(['tenant_id' => $id, â€¦])` silently drops it from the new instance and your own
  write-refusal throws. Use `firstOrNew()` and assign explicitly. The lookup half of the attributes
  still scopes correctly; only the instantiation drops them.
- **First used in**: larisHQ â€” PH03 (2026-09-01)

### Declared Settings Registry â€” code owns the keys, the table owns the overrides
- **Stack**: Laravel (any), applies to any per-account settings store
- **Problem**: "add a settings table" produces a free-form key/value store with no type, no
  default and no validation. A misspelled key then reads as *unset* and the caller falls back
  silently, and the settings screen can offer a field nothing in the codebase reads.
- **Solution**: declare the settings in code, exactly as you would permissions.
  ```php
  final class Settings
  {
      public const REGISTRY = [
          'commission.clawback_days' => [
              'type' => 'int', 'default' => 14, 'group' => 'Commission',
              'label' => 'Clawback window (days)', 'min' => 0, 'max' => 365,
          ],
      ];
  }
  ```
  The table stores overrides only. `get()` casts to the declared type and falls back to the
  declared default. An undeclared key **throws** rather than returning null. The UI renders from
  the registry and the FormRequest generates its rules from it, so the screen cannot show a field
  the validator would reject, and the validator cannot accept a key nothing reads.
- **Gotchas**: **memoise per account, not globally** â€” a queue worker handles several tenants in
  one process and a flat cache serves one customer's settings to another. Starting with a single
  entry is correct and honest: a phase adds a key when it has something to read, and the phase
  that needs the value adds a key instead of building a store.
- **First used in**: larisHQ â€” PH04 (2026-09-01)

### Configurable-Depth Hierarchy â€” adjacency list, strict adjacency, no closure table
- **Stack**: Laravel + MySQL/MariaDB; any ORM with a self-referencing table
- **Problem**: "1 to 8 configurable levels, names chosen by the customer" is repeatedly built as
  `level_1_id â€¦ level_8_id`, which hardcodes the maximum, wastes seven columns on a two-level
  customer, and makes "who is above this person" a different query per depth.
- **Solution**: `levels` (number, customer-chosen name) + `members` (`parent_id`, `level_id`),
  and **strict adjacency** â€” a member's parent must sit on exactly the level above. That single
  rule buys three things:
  1. Cycles become *structurally impossible*: level numbers strictly decrease going up. Keep the
     bounded parent walk anyway as defence in depth, but do not describe it as the guard.
  2. The tree renders from one query â€” group by `parent_id`, nest recursively. A closure table is
     maintenance for a depth-bounded problem that does not have it.
  3. A customer wanting a flatter network configures fewer levels, which is what the range is for.
  Enforce the maximum in **three** places: the service (so the customer gets a sentence), the HTTP
  layer, and a database `CHECK` constraint (so a forgotten code path cannot write row nine).
  ```php
  DB::statement('ALTER TABLE network_levels ADD CONSTRAINT levels_range CHECK (level_number BETWEEN 1 AND 8)');
  ```
- **Gotchas**: deletion is the sharp edge. Refuse while a member has **any** child, not just an
  active one â€” detaching an inactive child leaves it below the top level with no parent, which
  adjacency says cannot exist. Make routine removal a status change instead. Levels may be added
  at the bottom and renamed freely (the id is the key, the name is a label), but a populated level
  can never be deleted or renumbered, and only the *deepest* level may be removed at all.
- **First used in**: larisHQ â€” PH05 (2026-09-01)

### Configurable Categories Without Code Branches (channels, tags, sources, types)
- **Stack**: any; shown in Laravel + a pivot table
- **Problem**: a requirement lists options by name â€” "Facebook Ads only", "Google Ads only", "a
  mix of both", "any channel the customer adds" â€” and it reads like four features. Built that way
  it becomes an enum plus `if ($channel === 'facebook')`, and the fourth condition quietly becomes
  a lie.
- **Solution**: the named options are **rows**, and the conditions are **states of one pivot**.
  | Stated condition | How it is represented |
  |---|---|
  | A only | one row in the pivot |
  | B only | one row |
  | mix of A and B | two rows |
  | anything the customer adds | customer inserts a row; assignment is unchanged |
  Ship the named ones as **seed data in config**, not constants in code, and seed them **once** at
  provisioning. Then prove it with a test that **invents an option inside the test at runtime**,
  assigns it, and asserts it works â€” and a second test that greps the application source for the
  named options and requires zero hits.
- **Gotchas**: seed once, never re-sync â€” a "create if missing" walk cannot distinguish "never
  created" from "deleted on purpose", so it resurrects what the customer removed. Never delete an
  option that has been used; deactivate, because assignments and (later) snapshots reference it.
  And **strip comments before running the grep guard** â€” the comment explaining why no branch
  exists contains the very words the guard forbids.
- **First used in**: larisHQ â€” PH06 (2026-09-01)

### Stock Ledger â€” one writer, guarded decrements, reconcilable history
- **Stack**: any SQL database; shown in Laravel + MariaDB
- **Problem**: inventory goes wrong in two ways that both look fine in testing â€” a stock change
  that leaves no history, and two concurrent orders that each check availability, each see
  enough, and both take it.
- **Solution**: one service is the *only* thing that changes a quantity, and every change writes
  its movement in the same transaction. The decrement is a **guarded conditional update**:
  ```php
  $updated = Stock::whereKey($id)->where('quantity', '>=', $qty)->decrement('quantity', $qty);
  if ($updated === 0) { throw InsufficientStock::â€¦; }   // someone got there first
  ```
  The check and the write are one statement, evaluated by the database, so two callers cannot
  both pass it. Back it with a `CHECK (quantity >= 0)` for anything that ever bypasses the
  service. Movements carry a **signed** quantity and no running balance, so "level == sum of
  movements" stays a real assertion rather than a comparison of two copies of one number.
- **Gotchas**: a transfer must be one transaction wrapping a guarded decrement and an increment â€”
  then a short source throws and *neither* side moves, which is the only honest meaning of
  "atomic". Keep the level as a stored column rather than summing history on read: availability
  has to be checked inside the guarded update, and summing under a lock is a different and much
  slower thing. And note what you have *not* tested: a transactional test harness cannot exercise
  true parallelism, because a second connection blocks on row locks instead of racing â€” say so
  rather than implying the concurrency is proven.
- **First used in**: larisHQ â€” PH08 (2026-09-02)

### Data Minimisation You Can Actually Enforce
- **Stack**: any; shown in Laravel + Pest
- **Problem**: "collect only what is necessary" is a sentence in a specification. Six months
  later the table has a date of birth, an identity number and a free-text notes field that
  someone has been pasting medical details into â€” each added reasonably, none decided.
- **Solution**: make the *absence* of columns testable.
  ```php
  it('collects only the fields the specification lists', function () {
      expect(Schema::getColumnListing('customers'))->toBe([
          'id', 'tenant_id', 'code', 'name', 'email', 'phone', /* â€¦ */ 'created_at', 'updated_at',
      ]);
  });
  ```
  Adding a field now fails the suite, so it has to be argued for in a pull request rather than
  slipped in. Pair it with a **removal path that actually erases**: delete the row when nothing
  references it, and when history depends on it, anonymise in place â€” clear every personal field,
  keep the row and its internal code so totals still reconcile.
- **Gotchas**: name the personal fields **once**, as a constant on the model, and have both the
  anonymiser and the guard read it â€” otherwise the two drift and a field added to one is missed
  by the other. "Deactivate" is not erasure and should not be described as it. And keep an
  internal handle (a code) out of the personal list: orders are read by it, and it identifies a
  record rather than a person.
- **First used in**: larisHQ â€” PH09 (2026-09-02)

### Snapshot Every Input a Money Record Depends On
- **Stack**: any transactional system â€” orders, invoices, payroll, commission
- **Problem**: an order is written today and read in two years. If it *joins* to the product's
  price, the customer's tier, the salesperson's team or the item's cost, then every one of those
  changing quietly rewrites history â€” and the rewrite is invisible, because the query still
  returns a number that looks right.
- **Solution**: at the moment the record is created, **copy** every input into it. Not just the
  obvious one:
  ```
  order_lines: unit_price          <- the price charged
               network_level_id    <- the tier that produced it
               hq_cost_price       <- the cost the margin/commission is computed from
               product_name, sku   <- so the line stays readable after a rename
  orders:      sales_team_id       <- the salesperson's team at the time
               marketing_channel_id
  ```
  The test that proves it is not "the order has a price" but **"change the price afterwards and
  assert the order does not move"** â€” plus the same for every other copied input.
- **Gotchas**: the cost snapshot is the one people miss, because nothing on the order screen shows
  it â€” it surfaces a phase later when commission is computed from *today's* cost and quietly
  overpays or underpays. Keep the cart free of prices entirely so the line is created exactly
  once; a draft carrying snapshots has to rewrite its own lines whenever the buyer changes. And
  make every attribution foreign key `restrict` on delete: the record must never lose the answer
  to a question it was designed to answer.
- **First used in**: larisHQ â€” PH10 (2026-09-02)

### Enforcing a Constraint on a SUM (payments, credit limits, quotas)
- **Stack**: any SQL database; shown in Laravel + MariaDB
- **Problem**: "recorded payments must never exceed the order total" reads like the stock problem
  and is not. Stock lives in **one row**, so `UPDATE â€¦ WHERE quantity >= ?` decides atomically. A
  payment total is a **sum across rows**, and no single-row condition can express it â€” so the
  obvious `if (sum + amount > total) reject;` is a read-then-write race, and two concurrent
  payments can both pass it.
- **Solution**: lock the **parent** for the duration, then take the sum under that lock.
  ```php
  DB::transaction(function () use ($order, $amount) {
      $locked = Order::whereKey($order->id)->lockForUpdate()->firstOrFail();
      $paid   = Payment::where('order_id', $locked->id)->sum('amount');

      if ($paid + $amount > $locked->total) { throw PaymentRefused::exceedsTotal(...); }
      if ($paid + $amount < 0)              { throw PaymentRefused::exceedsPaid(...); }

      Payment::create([...]);
  });
  ```
  Concurrent writers against the same parent queue instead of racing, and writers against
  *different* parents are unaffected.
- **Gotchas**: pick the tool from the **shape of the constraint**, not from what worked last time
  â€” a single-row guard and a parent lock are both correct, for different shapes. Use **signed
  amounts** so payments and refunds are one table and one invariant (`0 â‰¤ sum â‰¤ total`) covers
  both ends. Never store the running balance: the whole requirement is that it reconciles, and a
  stored copy turns that into a comparison of two copies of one number. And take the amount from
  the user as **positive plus a direction** â€” a typed minus sign is an expensive typo.
- **First used in**: larisHQ â€” PH11 (2026-09-02)

### First-Match Rule Chains (commission rates, pricing tiers, discount policies)
- **Stack**: any; shown in Laravel + MariaDB
- **Problem**: "the product rate wins, else the category rate, else the customer's own, else the
  default" is usually built as one table with several nullable scope columns â€” and then two
  things go wrong. A row sets *two* scopes and nobody knows which step it belongs to; and a plain
  `UNIQUE(tenant, product_id, category_id, â€¦)` silently permits two defaults, because SQL treats
  NULLs as distinct.
- **Solution**: make both impossible in the schema.
  ```sql
  -- exactly one scope, or none for the default
  CHECK ((product_id IS NOT NULL) + (category_id IS NOT NULL)
       + (customer_id IS NOT NULL) + (team_id IS NOT NULL) <= 1)

  -- one rule per target, and exactly one default
  ADD COLUMN scope_key VARCHAR(40) AS (CASE
      WHEN product_id  IS NOT NULL THEN CONCAT('product:',  product_id)
      WHEN category_id IS NOT NULL THEN CONCAT('category:', category_id)
      â€¦ ELSE 'default' END) STORED;
  UNIQUE (tenant_id, scope_key)
  ```
  The generated column has one source â€” the scope columns â€” so it cannot drift. Resolve by
  fetching every candidate in one query and ranking in PHP by a `specificity()` derived from
  which column is set; ranking in SQL means a CASE expression that must be kept in step with the
  code's ordering.
- **Gotchas**: build the test as the **whole chain, then dismantle it** â€” one test per step,
  deleting the more specific rule each time, plus the empty case. `where('col', null)` compiles to
  `= NULL` and matches nothing, so add each `orWhere` only when there is a value. And snapshot the
  resolved rate **and its type** onto whatever the rule produced: the point of a rule chain is
  that it changes, and history must not change with it.
- **First used in**: larisHQ â€” PH12 (2026-09-02)

---

## Multi-surface Laravel: one app, two audiences, one login table

*Stack: Laravel 12 + Inertia 3 + Vue 3.5. First used: larisHQ PH15 (2026-09-04).*

An admin console and a customer/partner portal in one application, sharing authentication and a
tenant but nothing else. Four patterns that made the boundary structural rather than remembered.

### 1. The subject is bound from the session, never present in a URL
**Problem:** a portal user must act only as themselves, and every `{id}` in a route is something
they can change.
**Solution:** a request-scoped singleton (`PortalContext`) that middleware fills from the
authenticated user's linkage. No portal route takes the subject as a parameter, so the controller
has no identifier to validate and IDOR is unrepresentable rather than defended against. Mirrors the
tenancy pattern of reading the subdomain and nothing else.
**Gotcha:** re-assert the subject on *every* request that touches shared state. A per-user cart
carried over from console use will still point wherever the console last set it.

### 2. Split the permission registry by surface, then let the existing grant ceiling do the work
**Problem:** keeping portal grants away from console users.
**Solution:** tag permission *groups* with a surface and derive `consoleSlugs()`/`portalSlugs()`;
give the widest console role `consoleSlugs()`, not everything.
**Payoff:** if the codebase already has a "a grant can never exceed the granter" rule filtering the
role editor and the role picker, the split enforces itself â€” no console user holds a portal slug,
so those pickers never offer one. State the rule explicitly as well, so a future template that
carried the wrong slug cannot quietly reopen it.

### 3. Prove a cross-surface boundary by enumerating the router
**Problem:** "no admin route is reachable from the portal" is a claim about routes that do not exist
yet.
**Solution:** walk `Route::getRoutes()`, reject the portal's own name prefix and shared auth, and
assert the portal user is refused on each. **Add a third test asserting the enumeration is
non-empty** â€” the failure mode of an enumerated guard is that it silently enumerates zero and
passes forever.

### 4. Crossing between two root-view shells needs a full page visit
**Problem:** two surfaces with different stylesheets, chosen once per full page load.
**Solution:** `Inertia::location()` on login, logout and any redirect that crosses. An ordinary
Inertia redirect swaps the page component inside the shell it started in, so the user lands on the
right page wearing the wrong CSS. It degrades to a normal redirect for non-Inertia callers, so tests
hitting the endpoint directly still work.
**Gotcha:** the framework's `redirectUsersTo` needs a branch per surface too, or an authenticated
portal user visiting `/login` is bounced to an admin route they cannot open.

### 5. Ship the grant path, or the surface is unreachable
A portal is not delivered until an admin can *open* it. A service method that mints a login is not a
feature until a route and a control call it â€” grep for a production caller before calling the phase
done. This shipped as two complete portals that nobody could sign in to, because the login-issuing
service had had no caller since the phase that wrote it.

---

## Audit trails and notifications in a multi-tenant Laravel app

*Stack: Laravel 12 + Inertia. First used: larisHQ PH16 (2026-09-04).*

### 1. Declare the audited actions; do not scatter them
A registry class holding event => label, with `assertDeclared()` called from the recording helper.
The list becomes data: one test walks every `recordAudit('literal')` in `app/` and asserts each is
declared, so a misspelt event fails the suite instead of writing a row nothing will ever query.
Same shape as a permission or settings registry.

### 2. Derive the tenant from the audited record, never from the request
`tenant_id = $model->tenant_id ?? ($model instanceof Tenant ? $model->id : null)`. No read of
request state at all, which is what makes one audit helper work identically in a tenant request, an
admin-console request that binds no tenant, a queued job and a console command. The alternative â€”
filling it from the bound tenant â€” breaks on every surface that has none.

### 3. Two actor columns beat one polymorphic pair
When a system has exactly two identity tables (tenant users and platform operators) and a
deliberate boundary saying there will not be a third, two nullable foreign keys keep referential
integrity that a morph would trade away for generality nothing needs. At most one is set; both null
means a console command.

### 4. A null tenant scopes correctly for free
A platform-level audit row with `tenant_id = null` is invisible to every tenant (the global scope
filters `tenant_id = X`) and visible on the console that binds no tenant (the scope adds nothing).
The isolation you already built answers the new question without a special case.

**Gotcha:** a "refuse writes with no tenant" guard will reject that row. Make the guard ask
`array_key_exists`, not `!== null` â€” it exists to catch *forgetting*, and an explicit null is an
answer. The NOT NULL constraint on genuinely tenant-owned tables is the real backstop.

### 5. Never deliver a new permission by re-running the role provisioner
A provisioning routine that replays role templates rewrites names, descriptions and permission sets.
Safe at creation, destructive afterwards. To give existing tenants a newly added permission, sync
only the "holds everything" role â€” where a full sync is definitionally correct and the policy
already forbids editing it â€” and leave every customised role alone.

### 6. Order any list whose timestamp has one-second resolution by a tiebreak
`ORDER BY created_at DESC, id DESC`. With a UUID key the tiebreak is arbitrary but *stable*, which
is what a reader needs â€” an unstable chronological order reshuffles the page on every load.

### 7. Auditing anonymisation
The one place where recording carelessly undoes the operation. Record the internal handle and the
event; never the values you just cleared.

---

## Third-Party Grants & Token Lifecycles

> Written after the Threads connection work on 2026-09-11. Both entries generalise
> well beyond Meta: any API that gates behaviour on a review-granted scope, and any
> API whose token expires on a calendar rather than on use, has these two shapes.

#### Ask the Provider What the Token Actually Holds

- **Stack**: Any OAuth/token API â€” verified on Meta Threads (Laravel 12 + Inertia 3 + Vue 3.5)
- **Problem**: A permission granted by App Review changes what an endpoint *returns*
  without changing its **status code**. Threads `keyword_search` answers `200` whether or
  not `threads_keyword_search` was approved â€” unapproved, it silently searches only the
  authenticated user's own posts. A short result list is indistinguishable from a quiet
  keyword. The tempting workaround is a checkbox in Settings where the operator records
  what App Review said. That is an assertion, and it decays: it is wrong the moment a
  scope is revoked, an app is unpublished, or a different token is pasted in.
- **Solution**: Find the introspection endpoint and read the grant. Meta's is
  `GET /v1.0/debug_token?input_token={token}`, returning
  `{ is_valid, expires_at, issued_at, scopes[], user_id }`. Call it during connection
  verification and store the result as discovered state, not operator input. Let the
  platform's answer **overrule** whatever the operator asserted, and test that it does.
  The same call usually yields two more things worth having: the token's expiry, and the
  account id that write endpoints need.
- **Gotchas**: Meta documents the *inspecting* token as belonging to "a Threads tester",
  so introspection may be refused on a production app â€” degrade to the old wording and
  say "unconfirmed" rather than failing the connection or claiming a scope. `is_valid`
  absent is not `is_valid: false`; only an explicit false means the provider disowned the
  token. Timestamps are Unix seconds, and `0` means "never expires", not 1970.
- **First used in**: Social Media Listening Tools (Threads connection)

#### A Token That Expires on a Calendar Needs a Job, Not a Button

- **Stack**: Any long-lived-token API â€” verified on Meta Threads
- **Problem**: A Threads long-lived token lasts 60 days, must be **â‰¥24 hours old** before
  it can be refreshed, and once lapsed *cannot be refreshed or exchanged at all* â€” only
  replaced by hand. Nothing announces the lapse: ingestion keeps running and searches keep
  returning `200` with nothing in them. A "Reconnect" button does not help, because the
  failure mode is that nobody is looking.
- **Solution**: A scheduled command that renews inside the last N days (14 gives a
  fortnight of retries before anything is lost), refuses when the token is younger than
  the provider's minimum age, and refuses when the expiry is **unknown** â€” an expiry
  nobody has established is not grounds for a cron job to start rewriting credentials.
  Almost every run is a no-op, which is what makes it cheap to run daily. Exit non-zero on
  a failed *due* refresh so CI or the scheduler treats it as the incident it is.
- **Gotchas**: Refresh/exchange endpoints are often **unversioned** root paths
  (`{host}/refresh_access_token`), so a shared client that builds URLs as
  `host + '/' + version` genuinely cannot reach them â€” give them their own path rather
  than bending the client. These endpoints also take the token as a **query parameter**;
  there is no header form, so the usual "never put a token in a query string" rule cannot
  apply here â€” document why. Restart the age clock on the new token, or the next run
  refreshes something the provider still considers too young.
- **First used in**: Social Media Listening Tools (`ThreadsTokenService`)

## Laravel 13 + Inertia 3 + Vue 3.5 + Bootstrap/AdminLTE (console, no TypeScript)

### Version Baseline (verified live 2026-09-08)
Laravel **13.30.1** Â· PHP 8.4 Â· `inertiajs/inertia-laravel` **3.3.3** Â·
`@inertiajs/vue3` + `@inertiajs/vite` **3.7.0** Â· Vue **3.5.42** Â· Vite **8.2.2** Â·
`laravel-vite-plugin` **3.2.0** Â· `@vitejs/plugin-vue` 6.x Â· Bootstrap **5.3.8** Â·
admin-lte **4.9.1** Â· ApexCharts **7.1.0** + `vue3-apexcharts` Â· `sass-embedded`.
The Laravel 13 skeleton now ships **Tailwind + `@tailwindcss/vite` by default** â€” uninstall
both when the project ships Bootstrap, or two CSS frameworks compile into one bundle.
`Inertia::always()` and `Inertia::once()` both confirmed present in 3.3.3.

### AdminLTE 4 Layout Classes Collide With a Hand-Rolled Inertia Shell
- **Stack**: AdminLTE 4.9.1, Bootstrap 5.3.8, Inertia 3, Vue 3.5
- **Problem**: the mobile sidebar never appeared. The element was in the DOM, carried the
  right `is-open` class, and computed `transform: matrix(1,0,0,1,0,0)` â€” and still sat
  entirely off-screen at `x: -250`.
- **Solution**: **do not reuse AdminLTE's own layout class names** (`.app-wrapper`,
  `.app-sidebar`, `.app-main`, `.app-content`) for a hand-rolled shell. AdminLTE 4 styles
  those itself and drives them from body classes plus its PushMenu JS, so two stylesheets
  fight over one box: computed width was AdminLTE's `250px` rather than the authored
  `15.5rem`, and its negative offset held the panel off-canvas. Namespace the layout
  (`slt-*`, `app2-*`, anything) and keep AdminLTE's SCSS for what it genuinely provides â€”
  cards, nav, forms, tables. Also drop the `adminlte.js` import and the
  `layout-fixed sidebar-expand-lg` body classes when none of its JS is used.
- **Gotchas**: the tell is a **computed width that is not the width you authored** â€” check
  that first, it identifies the collision in one look. The reason to hand-roll at all is the
  Safe/Unsafe Split above: Treeview writes `menu-open` classes and inline heights onto nodes
  the framework owns. A hand-rolled treeview is also a net gain â€” it can auto-expand the
  active branch by matching `usePage().url` against a typed menu config, which DOM state
  cannot do.
- **First used in**: Social Media Listening Tool (2026-09-08)

### Sidebar Config as the Single Source of Truth, Asserted by Test
- **Stack**: Laravel 13 + Inertia 3 (applies to any framework)
- **Problem**: sidebar links and the router drift apart, and a dead link is found by a user.
- **Solution**: one PHP class owns the nav tree, resolves `route()` names to paths
  server-side (so the frontend never learns how routing works), and exposes a flat
  `routeNames()` list. A feature test then walks the tree and asserts every link responds,
  plus that every registered name exists. Dead navigation becomes a failing assertion.
- **Gotchas**: resolve `href` in a private mapper and keep `routeNames()` reading the raw
  *definition*, or the flattener runs `route()` twice for no reason.
- **First used in**: Social Media Listening Tool (2026-09-08)

### Third-Party Capability Is a Type Plus a Declaration, Never a Boolean
- **Stack**: any multi-provider integration (social APIs, payment gateways, couriers)
- **Problem**: one fat `Provider` interface forces every provider to implement methods it
  cannot honour, so "can it?" becomes a runtime `try/catch` and the UI ends up guessing.
- **Solution**: a **narrow base interface plus capability marker interfaces**
  (`SupportsKeywordDiscovery`, `SupportsReply`, â€¦). `$provider instanceof SupportsReply`
  is resolved by the language, and calling an unsupported method becomes unwritable.
  Then add a **second, declarative map** â€” `capabilities(): Capabilities` returning a
  four-state enum (`Supported` Â· `Unsupported` Â· `RequiresPermission` Â·
  `RequiresVerification`) **with a human reason string per capability**, rendered verbatim
  in the UI. `instanceof` answers "did we write it?"; only the declaration answers "is our
  app approved for it?" and "have we confirmed it still exists?".
- **Gotchas**: the reason string is the whole point â€” a greyed-out button with no
  explanation is what the pattern exists to prevent. Capabilities belong in **code**, not a
  table: they are properties of somebody else's API, not of our configuration, so they
  should appear in a diff. Keep a test asserting every provider declares every capability
  with a non-empty reason.
- **First used in**: Social Media Listening Tool (2026-09-08)

### Inertia Props Are Built From Arrays, and a Test Says So
- **Stack**: Laravel + Inertia (any adapter)
- **Problem**: Inertia serialises any `Arrayable` via `toArray()` â€” every non-hidden column,
  every appended accessor, every loaded relation, recursively. `$hidden` is not a security
  boundary, and Inertia's maintainers state there is no framework-level shield.
- **Solution**: build props from explicit arrays or DTOs, never from a model instance, and
  enforce it from commit one with a test that walks every page's prop bag recursively and
  fails on any credential-shaped **key that carries a value**. Field *descriptors* may
  legitimately name `app_secret` (a form has to label its inputs) â€” what must never appear
  is a value against that name.
- **Gotchas**: retrofitting this after the first leak means auditing every controller. It
  costs ~40 lines on day one.
- **First used in**: Social Media Listening Tool (2026-09-08)

---


## Laravel 12 + Vue 3 SPA + Sanctum cookie auth (REST, no Inertia)

First used in: **WebAppsBI** (2026-09-13). The Core's other Laravel + Vue projects all
use Inertia; this is the first REST + standalone SPA build, and the auth model behaves
differently enough to be worth its own section.

### Version Baseline (verified on the machine, 2026-09-13)
Laravel 12.69.2 · PHP 8.4.10 · Sanctum 4.3 · Vue 3.5.42 · TypeScript 5.9.3 ·
Vite 7.3.6 · @vitejs/plugin-vue 6.0.8 · Pinia 4.0.3 · Vue Router 4.6.4 ·
Bootstrap 5.3.8 · AdminLTE 4.9.1 · PostgreSQL 16.14 · Redis 8.4.0 · Pest 3.8.7

### Sanctum SPA: the stateful-domain mismatch that fails one request late
- **Stack**: Laravel 12 + Sanctum 4 SPA cookie auth
- **Problem**: `POST /auth/login` returns **200**, and the very next authenticated
  request returns **401**. Nothing in the logs explains it.
- **Cause**: `SANCTUM_STATEFUL_DOMAINS` does not contain `APP_URL`'s **host *and port***.
  Sanctum decides statefulness from the Origin/Referer header; when the request is not
  stateful, session middleware never runs, so `Auth::attempt()` succeeds in memory and
  nothing is persisted. Serving on `:8383` while the list says `:8000` is enough.
- **Solution**: assert it in the health check, not in a runbook:
  ```php
  $needle = $port ? "{$host}:{$port}" : $host;
  $covered = in_array($needle, config('sanctum.stateful', []), true)
          || in_array($host, config('sanctum.stateful', []), true);
  ```
- **Gotchas**:
  - The failure is *one request later* than the mistake, so it reads like a session-driver
    or cookie bug. It is neither.
  - A defensive `if ($request->hasSession())` guard around `session()->regenerate()` turns
    the loud `Session store not set` 500 into this silent 401. Keep the guard (it is right
    for genuinely stateless calls) **but pair it with the check above**.

### Testing a Sanctum SPA: the suite must send an Origin header
- **Problem**: feature tests pass while exercising a code path the real SPA never takes.
  `postJson()` sends no Origin/Referer, so Sanctum treats every test request as stateless
  and session behaviour (fixation defence, `logoutOtherDevices`, logout) is never tested.
- **Solution**: in `tests/TestCase::setUp()`, `$this->withHeader('Origin', config('app.url'))`.
- **Gotchas**: once requests become stateful the suite needs a real `APP_KEY` in
  `phpunit.xml` — session cookies are encrypted, and the missing key only surfaces at
  that moment, presenting as an unrelated 500.
- **Also**: switching authenticated users with two `actingAs()` calls in one
  session-based test leaves the first session in place and returns 401, masking whatever
  403 the test was actually asserting. Split into one test per actor.

### A custom API error renderer must map STATUS, not exception class
- **Problem**: `Gate::authorize()` throws `AuthorizationException`, but Laravel converts
  it to an `HttpException` **before** a custom `render()` callback sees it. Matching on
  `$e instanceof AuthorizationException` therefore never fires, and every 403 silently
  degrades to a generic error code.
- **Solution**: derive the stable `error.code` from `$e->getStatusCode()`:
  `401 → UNAUTHENTICATED`, `403 → FORBIDDEN`, `404 → NOT_FOUND`, `429 → RATE_LIMITED`.
- **Gotchas**: the frontend must switch on `error.code`, never on `message`.

### A semantic 503 needs a client that treats it as data
- **Problem**: `/health` returns 503 when degraded so uptime monitoring can alarm. The
  admin screen whose entire purpose is diagnosing a degraded system then rendered
  "unexpected response", because the HTTP interceptor throws on any non-2xx.
- **Solution**: `validateStatus: (s) => s === 200 || s === 503` on that one call.
- **Gotchas**: this is a general shape — any endpoint whose non-2xx body is the payload
  needs an explicit opt-in at the client, or the interceptor eats the useful part.

### Bootstrap + AdminLTE 4 through Vite with Dart Sass modules
- **Problem**: `@use` must precede every other rule, but Bootstrap's variable overrides
  must precede its `@import`. Putting `@use 'base'` after the vendor imports fails with
  *"@use rules must be written before any other rules"*.
- **Solution**: a `_vendor.scss` partial that does `@use 'tokens'`, then the `$primary`
  etc. overrides, then the `@import`s. `app.scss` becomes two lines — `@use 'vendor';`
  then `@use 'base';` — which also gives the correct cascade order for free.
- **Gotchas**: `loadPaths: ['node_modules']` is still mandatory. AdminLTE 4's Sass entry
  is `admin-lte/src/scss/adminlte.scss` (its `package.json` `sass` field), not `dist`.

### Pest arch tests are the only layering rule that survives
- **Solution**: assert the dependency directions rather than documenting them.
  ```php
  arch('domain does not depend on the framework')
      ->expect('App\Domain')->not->toUse(['Illuminate\Http', 'App\Services', 'App\Http']);
  arch('controllers contain no raw database access')
      ->expect('App\Http\Controllers')->not->toUse(['Illuminate\Support\Facades\DB']);
  ```
- **Gotchas**: the DB rule immediately caught a health-check controller querying directly.
  The fix was to extract a `HealthService` — which is the right design anyway. Resist
  adding an exemption; the rule earns its keep by being absolute.

### Route-coverage test: the authorisation rule that outlives the phase that wrote it
- **Solution**: enumerate `Route::getRoutes()`, skip an explicit public allow-list, and
  assert every remaining API route gathers an `auth:` middleware. A new endpoint shipped
  without it fails the build.
- **Gotchas**: twelve phases later nobody remembers the access model, but a red suite is
  impossible to ignore. Pair it with a table-driven cross-tenant probe once scoping exists.


### Company-scoped access in a single-tenant app — one resolver, or none

- **Stack**: Laravel 12 + PostgreSQL 16. First used in **WebAppsBI** PH-02 (2026-09-13).
- **Problem**: not multi-tenancy (one database, one app) but *row-level company scoping*:
  a user may read some companies and not others, with an optional hierarchy.
- **Solution**: exactly one resolver, and no second path to the same answer.
  ```php
  $permitted = $this->permittedCompanyIds($user);        // from the SESSION
  $scope     = $requested === [] ? $permitted
                                 : array_intersect($requested, $permitted);
  if ($scope === []) throw new DomainException('COMPANY_FORBIDDEN', ..., 403);
  ```
- **Gotchas**:
  - **Return 403, never an empty result set.** An empty list is indistinguishable from
    "no data": it informs no legitimate user, deters no attacker, and cannot be asserted in
    a test. The 403 is the only outcome that is checkable.
  - **Descendant inheritance must be opt-in per grant.** Defaulting it on is the convenience
    that quietly hands a regional manager the whole group.
  - Bump a `users.access_version` on every grant change and make it part of any cache key,
    so a revoked user cannot be served a result computed under their old entitlements.

### Two-dimensional authorisation: permission × scope, and the half that gets forgotten

- **Problem**: authorisation here is *what action* AND *whose rows*. A `hasAny($user, $perm)`
  helper answers only the first, and reads as though it answered both.
- **Solution**: name them so the wrong one is uncomfortable to reach for —
  `hasAny()` (company-agnostic screens only) and `hasAnyForCompany($user, $companyId, $perm)`.
  Every policy method asserts **both**:
  ```php
  return $this->access->canAccess($user, $company->id)
      && $this->permissions->hasAnyForCompany($user, $company->id, Permission::COMPANY_VIEW);
  ```
- **Gotchas**: scope and permission expansion **must use the same traversal code**. When each
  had its own, a descendant-including grant expanded scope but not permissions — the user
  reached the subsidiary's route and was then refused by its policy. One `CompanyTree` class,
  called by both. Two copies of a traversal rule is one copy too many.

### Derived columns must be derived in the model, not by whichever caller remembers

- **Problem**: `companies.depth` is derived from `parent_id`. It was correctly kept out of
  `$fillable`, and the controller set it by hand. A seeder then mass-assigned `parent_id`,
  `depth` stayed 0, and the tree rendered flat — **while the entire test suite passed**,
  because every test went through the careful controller.
- **Solution**:
  ```php
  protected static function booted(): void {
      static::saving(function (self $m): void {
          if ($m->isDirty('parent_id') || ! $m->exists) {
              $m->depth = HierarchyGuard::depthFor($m->parent_id);
          }
      });
  }
  ```
- **Gotchas**: "the controller sets it correctly" is a property of the controller, not of the
  data. The second writer always arrives — here, immediately, as the seeder. Found by looking
  at the screen, not by any test.

### Bounded tree walks — never recurse until done

- **Problem**: descendant expansion and ancestor cycle-checking both walk a tree that user
  input can reshape. An unbounded walk over a malformed tree is an infinite loop in production.
- **Solution**: bound every walk by `MAX_DEPTH` and treat exceeding it as corruption:
  a named `HIERARCHY_CORRUPT` error, refusing the write rather than adding to the mess.
  Guard cycles by walking **up** from the proposed parent and refusing if it reaches the
  moving node; guard depth by checking `newDepth + heightOf($subtree)`, not just `newDepth` —
  otherwise a shallow move drags a deep subtree past the ceiling.
- **Gotchas**: PostgreSQL can express "not its own parent" as a CHECK; it cannot express "no
  cycles". The deeper guarantee has to live in code, so it must live in a guard that every
  write path calls.

### A table-driven cross-tenant probe is the regression suite

- **Solution**: a Pest `dataset()` of `[method, uri, payload]` × actor classes
  (owner / other-tenant admin / no-access / unauthenticated), plus one test that enumerates
  the router and fails when a route binding `{company}` lacks the scope middleware.
- **Gotchas**: the router-enumeration test is the one that survives. Twelve phases later
  nobody remembers the access model, but a red build is impossible to ignore.


### Visibility as the atomic unit — how a long import stays safe

- **Stack**: Laravel 12 + PostgreSQL. First used in **WebAppsBI** PH-03 (2026-09-13).
- **Problem**: an import of 100k+ rows cannot run in one transaction (lock duration, WAL
  bloat, and one bad row losing everything), yet a partial import must never be readable.
- **Solution**: move atomicity up a level. Rows are written under a `dataset_id` whose status
  is `processing`; **analytics reads only `status = 'active'`**. Activation is one small
  transaction that archives the predecessor and promotes the successor.
  ```sql
  CREATE UNIQUE INDEX datasets_one_active_per_company_period
  ON datasets (company_id, period_start, period_end)
  WHERE status = 'active' AND deleted_at IS NULL;
  ```
- **Gotchas**:
  - The partial unique index is the real guard, not the service. Catch the
    `QueryException` on that index name and return **409**, not 500 — a lost race is a
    conflict, not a crash.
  - Rollback becomes `DELETE FROM facts WHERE dataset_id = ?`, and it can take as long as it
    needs because nothing is waiting on it.
  - Test the guard by writing `status = 'active'` **directly via the query builder**, bypassing
    the service. If that succeeds, the guarantee lives in the service and not in the database.

### A state machine that names what IS possible

- **Problem**: a status column with good intentions eventually lets a half-imported dataset go
  live. "Invalid transition" alone tells the user nothing about what to do.
- **Solution**: one `ALLOWED` map, and an error carrying the legal moves:
  ```php
  throw new DomainException('INVALID_DATASET_TRANSITION',
      sprintf('A dataset that is %s cannot become %s.', $from->label(), $to->label()),
      409, ['from' => ..., 'to' => ..., 'allowed' => self::allowedFrom($from)]);
  ```
  The detail view returns `meta.allowed_transitions`, so the UI renders exactly the actions
  that will succeed rather than offering ones the server will refuse.
- **Gotchas**: write the illegal transitions as an explicit test list, each named for the bug
  it prevents (`processing → active`, `archived → active`, `failed → completed`). A test that
  only walks the happy path proves the machine exists, not that it refuses anything.

### Null is not false — a derived boolean that cannot yet be answered

- **Problem**: `countsReconcile()` returned `bool`. Mid-import, `imported + rejected ≠ total`
  is *true*, so every in-flight dataset rendered "counts do not reconcile" — turning the one
  signal that should mean "this import is broken" into noise on every row.
- **Solution**: return `?bool`. `null` for any state where the question has no answer yet, and
  the UI shows progress (`5,100 / 8,000`) instead of a verdict. Callers check `!== true`, so
  `null` can never be mistaken for a pass.
- **Gotchas**: this is the same rule as null-vs-zero for metrics, one type over. Any derived
  boolean computed from in-flight data needs a third state, and the *caller* has to be written
  for three outcomes — `if (!$x)` silently treats unknown as failure.

### Never ship a default password in a seeder

- **Problem**: `Hash::make('ChangeMe!2026')` in `DatabaseSeeder` is a committed credential. It
  reaches every clone, every CI log and every repository backup. `must_change_password` only
  helps if the legitimate admin signs in before anyone else — on a fresh deploy that window is
  exactly when nobody is watching.
- **Solution**: read `ADMIN_PASSWORD` from the environment; when absent, `Str::password(24)`
  and print it once to the operator. Then guard it:
  ```php
  expect($contents)->not->toMatch('/Hash::make\([\'"][^\'"]+[\'"]\)/');
  ```
- **Gotchas**: run the scan over *every* file in `database/seeders/`, not just the main one —
  demo and test seeders are where the literal reappears.


## Untrusted spreadsheet ingestion (PhpSpreadsheet 5.x + Laravel Excel 4.x)

First used in **WebAppsBI** PH-04 (2026-09-13). Verified against
`maatwebsite/excel 4.0.2` and `phpoffice/phpspreadsheet 5.9.0`.

### Laravel Excel 4.x is not the rewrite people fear
- The concerns a chunked import needs — `WithChunkReading`, `WithHeadingRow`,
  `WithReadFilter`, `WithStartRow`, `WithLimit`, `SkipsEmptyRows`, `ToCollection` — all
  still exist in 4.0.2. Requirements moved (`php ^8.3`, `illuminate ^12||^13`,
  `phpspreadsheet ^5.8`), not the API surface.
- **Still verify before writing code.** The check cost one `ls vendor/.../Concerns/` and
  retired a HIGH risk that had been carried for four phases.

### Build every reader in one factory, hardened by construction
```php
$reader->setReadDataOnly(true);          // styles/drawings are most of the memory
$reader->setIgnoreRowsWithNoCells(true); // no phantom Sheet1
$reader->setAllowExternalImages(false);  // an image URL in an upload is SSRF
$reader->setReadFilter($boundedWindow);  // bounded rows AND columns
```
- **Gotcha**: a reader constructed anywhere else will miss one of these, and the one it
  misses is the one that matters. One factory, no exceptions.

### Measure a zip bomb from the central directory, never by decompressing
```php
for ($i = 0; $i < $zip->numFiles; $i++) {
    $stat = $zip->statIndex($i);
    $compressed += $stat['comp_size'];
    $uncompressed += $stat['size'];
}
```
- Guard the **absolute** expansion first, then the ratio: a modest ratio on a huge archive
  is still a huge archive. 200:1 sits far above real Excel output and far below a bomb.
- `EncryptedPackage` in the archive is the reliable tell for a password-protected `.xlsx`.
- **Gotcha**: assert in the test that refusing it was *cheap* (peak memory delta), not only
  that it was refused — otherwise a future change could start decompressing and still pass.

### `rangeToArray()` pads to the bound you asked for
- A 5-column sheet read with a 256-column guard returns **251 empty columns**. Those become
  phantom columns in a mapping UI.
- Trim trailing columns blank in *every* row of the window. **Keep** a blank column between
  two populated ones — it is a real column, and removing it shifts every header after it,
  silently re-pointing a saved mapping.

### Never evaluate a formula from an uploaded file
- `getCalculatedValue()` is execution of attacker-authored input. Pass
  `calculateFormulas: false` and read the cached value Excel wrote.
- It is also the **honest** answer: the cached value is what the author last saw and signed
  off. Recomputing can silently disagree with their own figures.
- State it in the response (`meta.formulas_evaluated: false`) so the UI can tell the user.

### Detect the header row by *two* filled cells, not one
- Real finance workbooks open with a title block. A single-cell row is that title. Scanning
  for the first row with **≥ 2** non-blank cells skips it reliably.
- Detection is a suggestion, never a decision: re-render the preview on every header-row
  change so the user sees column names appear. That is the cheapest correctness feedback in
  an import flow — picking row 1 instead of row 4 collapses the table visibly.

### Flag BOTH occurrences of a duplicate header
- Marking only the second leaves the user unable to tell which column is which.
- Disambiguate deterministically (`amount`, `amount_2`) so a saved mapping keeps pointing at
  the same column next month.

### `$request->validate()` does not cast
- The `integer` rule *validates* a query-string param and still hands back the string `"1"`,
  which fails an `int` parameter type at runtime. Cast once at the boundary
  (`(int) $validated['x']` or `$request->integer('x')`), never downstream.

### A named rejection with a fix, not "invalid file"
- One enum per reason, each carrying `message()` **and** `fix()`. `"412 rows rejected"` is a
  wall; `"company 'Acme SDN' is not registered — add it as an alias"` is a task.
- Assert in a test that **no** rejection message contains a path separator: parser exceptions
  leak file paths, and translating them is where that leak happens.


## Mapping arbitrary spreadsheet columns onto fixed fields

First used in **WebAppsBI** PH-05 (2026-09-13). The screen this produces is the
highest-stakes minute a finance user spends in a BI product: a wrong mapping puts
revenue in the expense column and every number downstream is wrong.

### Declare the date format. Never detect it per row.
- **Problem**: `03/04/2026` is 3 April under `d/m/Y` and 4 March under `m/d/Y`. Both parse.
  Both look right. Auto-detection corrupts a year of data and the corruption is invisible
  until someone notices Q1 and Q2 are swapped.
- **Solution**: the format is part of the mapping, applied strictly, and the UI renders what
  the chosen format makes of a **real value from that column**:
  `31/01/2026 reads as 31 January 2026`.
- **Gotchas**:
  - `DateTimeImmutable::createFromFormat()` is lenient: it reads `31/02/2026` as 3 March.
    Check `getLastErrors()` and treat **any warning** as a failure, or impossible dates roll
    silently into real ones.
  - Excel stores dates as serials, so a data-only read returns `45678`, not a date. That is
    the common case, not the edge.

### Parse money to an exact decimal STRING, never a float
- `numeric(20,4)` in PostgreSQL, string across the API, `bcmath` for scaling. A float
  anywhere on that path loses precision before the database ever sees it.
- Handle, because real exports contain all of them: `1,234.56`, `1.234,56`, `(1,234)`
  (accounting negative), `RM 1,234`, `12.5%`, `1234-` (mainframe trailing minus), and
  numbers stored as text.
- **Round before truncating**: `bcadd($v, '0.00005', 8)` then `bcadd($v, '0', 4)`, or
  `0.00005` becomes `0.0000`. And never emit `-0.0000`.

### A parse result has THREE states, not two
- **value**, **blank** (`-`, `n/a`, `nil`, empty → `null`), **error** (present but
  unparseable). Collapsing blank into error rejects every sparse workbook; collapsing error
  into blank silently discards real numbers.
- Blank is `null`, never `0`: "not reported" and "reported as zero" are different facts.

### Fuzzy header matching: cap the absolute edit distance, not just the ratio
- **Problem**: `Status` matched `state` (Region) at 0.67 — two edits over six characters.
  A similarity ratio is meaningless on short words, and the score makes a bad guess look
  considered.
- **Solution**: `levenshtein(a,b) <= max(1, intdiv(len, 4))` **in addition to** the ratio.
  Real typos still match (`Revenu` → revenue 0.86); `Status` correctly gets nothing.
- **Also**: score every header against every field first, then assign **greedily by
  confidence**. Assigning in header order lets a weak early match claim a field that a later
  column matches exactly.
- A bad suggestion is worse than none. Below the threshold, offer nothing.

### Suggestions are presented, never applied
- Show the confidence. Auto-applying is how revenue reaches the expense column with nobody
  having decided anything.

### Template versions are immutable; the dataset snapshots what it used
- Editing writes **version N+1** and repoints `current_version_id`. It never mutates N.
- The dataset also stores the definition it was mapped with, so an import stays explainable
  a year later even if the template was since edited or deleted.

### Applying a saved template to a drifted workbook needs a reconciliation REPORT
- Headers drift. Last month's template against two renamed columns still "works" — it just
  points somewhere else. That is the most likely route to a silently wrong import.
- Report four outcomes: matched exactly · matched after normalisation (case/spacing, absorbed
  but **still reported**) · missing and required (**blocking**) · missing and optional
  (warning). Plus headers the template does not cover.
- Block when a *measure* is lost, not only when an identity field is — a template that maps
  only company and date imports nothing.

### Where a unique index protects user-supplied text, pair it with a validation rule
- The index alone turns "that name is taken" into a **500**. Keep the index (it is the real
  guarantee under a race) and add `Rule::unique` for the field-level message.

### Design the mapping so a new client is data, not code
- Synonyms, date formats, separators, sign handling, currency tokens and row filters all live
  in config or in the mapping definition. Adapting to a client's real workbook should mean
  editing a template, not editing PHP.


## Bulk import into a PostgreSQL fact table

First used in **WebAppsBI** PH-06/07 (2026-09-13).

### Decide every row in PHP before issuing any SQL
- **Problem**: PostgreSQL aborts the **entire transaction** on a failed statement, unlike
  MySQL. A bad row reaching an `INSERT` inside a 2,000-row chunk transaction discards the
  1,999 good rows batched with it.
- **Solution**: the normaliser issues no SQL at all. It returns either a complete set of
  values or a named rejection, and only then does the chunk transaction run.
- **Gotchas**: this rules out "insert and catch the exception per row" entirely. Where a
  genuine race remains (a unique index on a dimension), wrap that one statement in a
  `SAVEPOINT` rather than letting it poison the chunk.

### Make visibility the atomic unit, not the write
- Rows are written under the importing `dataset_id`; analytics reads only `active` datasets.
  A failed import is therefore *invisible* rather than destructive, and rollback is a
  `DELETE` that can take as long as it needs because nothing is waiting on it.
- **Test it by fingerprinting**: serialise the active dataset's rows before and after a
  failing import and assert byte equality. Asserting "no exception was thrown" proves nothing.

### Never create a master record from an import
- Resolve company/customer/product by code, then exact name, then alias. **No match rejects
  the row.** A record created from a typo silently becomes real, and every figure filed
  against it vanishes from the consolidated view with nobody noticing.
- Distinguish "does not exist" from "exists but belongs elsewhere" — they need different fixes.
- Dimension auto-creation is acceptable where declared per column, but flag the row
  (`created_by_import`) so an accidental "Leasng" is visible as something the import invented.

### Group rejections by reason, and give each one a fix
- `"412 rows rejected"` is a wall. `"412 rows: company 'Acme SDN' is not registered — add it
  as an alias"` is a task someone finishes in a minute.
- Sort groups by how fixable they are, not by count.
- Raw rejected values belong in an access-controlled table, **never** in the application log —
  a rejected row still contains the client's data.

### Resume a chunked job from a persisted cursor
```php
if ($cursor > 0) {
    Fact::where('dataset_id', $id)->where('source_row_number', '>=', $resumeAt)->delete();
    Rejection::where('dataset_id', $id)->where('source_row_number', '>=', $resumeAt)->delete();
}
```
- **Gotcha**: test idempotency by re-running a job that already *completed*, not only one that
  crashed mid-way. A redelivery after success is the common case on a busy queue.

### Poll on "not finished", never on "currently running"
- A job dispatched but not yet picked up still shows its pre-dispatch status. A UI polling on
  `status === 'processing'` concludes nothing is happening and stops — then sits stale until
  the user reloads. The bug only appears when the worker is not instantaneous, i.e. always.
- Track `queued` separately and poll until the record reaches a **terminal** state.

### An empty state derived from a count must ask whether the count is meaningful yet
- Zero rejections on a dataset that was never imported is not "every row imported". Zero-because-
  nothing-ran and zero-because-nothing-failed are different facts and must not share a message.

### PostgreSQL schema details worth copying
- `GENERATED ALWAYS AS (EXTRACT(YEAR FROM d)) STORED` for period parts: grouping by month must
  not mean `EXTRACT()` over millions of rows per dashboard load. They are **not writable** —
  an insert naming them fails, which a test should assert.
- `CHECK (a IS NOT NULL OR b IS NOT NULL OR c IS NOT NULL)` to forbid a row with an identity
  and no figures.
- Store money as `numeric(20,4)`; Laravel's `decimal:4` cast returns a **string**, which is
  what you want all the way to the API.


## A controlled analytics layer (registry, not query builder)

First used in **WebAppsBI** PH-08 (2026-09-13).

### The registry IS the security boundary
- A request carries a **key**; the SQL fragment lives in a code-owned registry entry. Nothing
  the caller supplied is ever interpolated into a query.
- Validate keys with `Rule::in(Registry::keys())` in the FormRequest, so an unknown key is a
  422 that never reaches query construction.
- This gives real flexibility — any permitted metric × dimension × aggregation — with **zero**
  dynamic identifiers. Test it with injection payloads through *every* keyed field: metric,
  dimension, aggregation, comparison, and the drill-down sort column.

### Walk the whole registry in a test, or half of it has never run
- A registry entry is a query that only exists when someone selects it. `period_month`
  shipped with a `GROUP BY` that omitted its label expression — valid PHP, invalid SQL,
  silent until executed.
- Two tests pay for themselves: **every dimension grouped**, and **every metric under each
  aggregation it declares**. They are four lines each and catch a whole class of bug.
- PostgreSQL specifics: any selected non-aggregate must appear in `GROUP BY`. An expression
  built only from grouped columns is fine; a *different* expression over the same column is not.

### Metric honesty — the rules that stop a BI tool lying plausibly
```sql
sum(profit) / nullif(sum(revenue), 0)   -- margin is UNDEFINED on no revenue, not 0%
```
- **Growth with no base period, or a zero base, is `null`** — not `+100%`, not `0%`.
- **A sum over no rows is `null`**, not `0`. Return a `meta.empty` flag so the UI can say
  "no data for this period" rather than showing a confident zero.
- **A genuine zero must stay distinguishable** from no data. Test both.
- **Refuse to total across currencies.** MYR + SGD is wrong in every currency. Return
  per-currency subtotals and a message instead — a refusal that is still useful.
- **Bucket a truncated tail explicitly** into `other`, never drop it silently.
- When a comparison cannot be computed, say `comparison_available: false` rather than omitting
  the key — absence is ambiguous, an explicit false is not.

### Cache keys that make staleness unreachable, not merely expired
```
analytics:v1:{user.access_version}:{query fingerprint}:{active-dataset fingerprint}
```
- Activating a dataset changes the fingerprint, so old entries can never be hit again. TTL is
  a safety net, never the invalidation strategy.
- The access version in the key means a revoked user cannot be served a figure computed under
  their old entitlements — cheaper and more reliable than trying to evict per user.

### Every response states its provenance
- `meta.datasets`, `meta.row_count`, `meta.currency`. Any figure on screen can name the file
  it came from without a round trip, which is what makes drill-down credible.

### Batch endpoint: resolve scope once, fail per widget
- A twelve-widget dashboard is one request. Scope resolution happens once; each query is
  cached independently.
- **Partial failure is per query.** One misconfigured widget returns its own error while the
  other eleven render. Classify it distinctly (`INVALID_WIDGET_CONFIG`) — reporting it as
  `SERVER_ERROR` sends the user hunting for a fault that is a widget setting.

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

---

## Admin Template Design Language (AdminLTE 4 â€” Blade and Inertia alike)

> The mechanics of AdminLTE live above (*Safe/Unsafe Split*, *`loadPaths` Is Mandatory*,
> *AdminLTE 4 in a Blade App Without Node*). This section is the **visual** layer â€” the
> decisions that were being re-made, differently, on every project.
> Process rules and the Screen Brief live in [20-design-protocol.md](./20-design-protocol.md).
>
> **Confidence:** the component map is read from AdminLTE 4's own demo pages and docs.
> Verify a component against the installed version's demo before leaning on it â€” the
> markup is stable across v3â†’v4 but the class list is not a contract.

### 1. Reach for the template's component before writing markup
- **Stack**: AdminLTE 4.3+, Bootstrap 5.3
- **Problem**: every project hand-rolls a stat tile, a panel and a page header in slightly
  different utility classes. The result is inconsistent within itself, which is exactly what
  makes a UI read as generated â€” a person reuses, a generator re-invents.
- **Solution**: map the need to the component that already exists, and only then consider markup.

  | Need | Component | Use when |
  |---|---|---|
  | Headline number, one per KPI | `small-box` | Dashboard, glance density, has a drill-through link |
  | Number with a label and icon, in a row | `info-box` | Secondary metrics, tighter than `small-box` |
  | Any titled container | `card` + `card-header` / `card-body` | The default. `card-outline` for a lighter frame |
  | Actions belonging to a container | `card-tools` in the header | Never a loose button floating above the card |
  | Page title + breadcrumb | `content-header` | Every page, identically. Do not re-style per page |
  | Inline warning tied to content | `callout` | Not a toast, not a modal |
  | Nav with children | `sidebar-menu` + `nav-treeview` | Keep depth â‰¤ 2; deeper belongs in-page |

- **Gotchas**: `small-box` is *loud* by design â€” four of them side by side is the single most
  recognisable generated-dashboard shape. Use at most two, for numbers someone actually acts
  on, and demote the rest to `info-box` or a plain table. If a screen needs a component the
  template lacks, build it **once**, in the shared component directory, in the template's own
  class vocabulary â€” never inline on the page that needed it first.
- **First used in**: larisHQ (Inertia+Vue), Basic Custom E-Commerce (Blade)

### 2. Override centrally, never per page
- **Problem**: a screen carrying both AdminLTE classes and a pile of ad-hoc utility classes
  reads as two people arguing. It is instantly visible and it is why "fix the spacing" notes
  keep coming back â€” the spacing was never systematic to begin with.
- **Solution**: one SCSS entry point. Override Bootstrap's variables (colour, spacing scale,
  border radius, font stack) at the documented insertion point â€” **after functions, before the
  AdminLTE import**, per *Bootstrap + AdminLTE 4 through Vite* above. Every page then inherits.
- **Gotchas**: the moment a page needs a one-off override, that is evidence the variable is
  wrong or a shared component is missing. Fix it centrally; a per-page exception becomes the
  next project's inconsistency.

### 3. Density is a per-screen class, not a global padding
- **Problem**: an operator's daily order table and a twice-a-month settings form get the same
  roomy padding, so the table wastes half the screen and the form feels cramped and unloved.
- **Solution**: pick the density in the Screen Brief and apply the matching pattern:
  `dense-table` â†’ `table-sm`, no card padding around the table, sticky header, right-aligned
  numerics Â· `roomy-form` â†’ standard card padding, one column, generous label spacing Â·
  `glance-dashboard` â†’ â‰¤2 `small-box`, everything else demoted.
- **Gotchas**: density follows **usage frequency**, not screen importance. The most important
  screen in the product is often the one used twice a year, and it should be roomy.

### 4. Tabular data has its own rules and they are not negotiable
- **Problem**: currency left-aligned next to a name column, IDs in a proportional font, three
  date formats on one page. Individually trivial; together they are the reason a table looks
  amateur even when every value is correct.
- **Solution**: numerics right-aligned with `font-variant-numeric: tabular-nums` and a fixed
  decimal count; currency symbol once in the column header, not per cell; IDs, codes and hashes
  in the monospace stack; one date format defined centrally and used everywhere.
- **Gotchas**: set `tabular-nums` on the column, not the page â€” proportional figures are correct
  in prose. And decide truncation per column *before* the first long value arrives: `text-truncate`
  with a `title`, never a layout that grows sideways.
- **First used in**: larisHQ â€” agent ledger and commission tables

### 5. The four states are part of the screen, not a follow-up ticket
- **Problem**: screens ship with the happy path only, so empty, loading, error and
  permission-denied are discovered by {USER_NAME} in review â€” every time.
- **Solution**: build empty (carrying the primary action that fills it), loading, error, and
  permission-denied alongside the populated state. An empty state without its call to action is
  a dead end, and it is the state a new tenant sees **first**.
- **Gotchas**: write empty-state copy in the domain's voice â€” "No stockists under this agent yet"
  beats "No data available". This is the most-read and least-written copy in any admin panel.

---

### Runtime BEFORE/AFTER Vulnerability Toggle (intentionally-vulnerable lab)
- **Stack**: Laravel 11+/12, any DB; applies to any "broken on purpose" demo/training app
- **Problem**: A pentest/training lab must show the SAME exploit working (BEFORE) and then
  blocked (AFTER) on stage, ideally without git checkouts, restarts, or shipping a permanently
  vulnerable endpoint.
- **Solution**: One env flag `SECURELAB_VULN` â†’ `config/securelab.php` â†’ a tiny
  `App\Security\Toggle::vulnerable()` read LIVE from config at request time. Each finding keeps
  its weak and fixed paths side by side (e.g. `VulnerableUserSearch` / `SecureUserSearch`, or an
  `if (Toggle::secure()) abort_unless(...)` guard, or `{!! !!}` vs `{{ }}` chosen in Blade). The
  controller just picks the path. Flip `.env` + refresh to switch â€” `php artisan serve`
  re-bootstraps the framework every request, so Dotenv re-reads `.env` with no restart (as long
  as config is NOT cached). A coloured layout banner shows the current mode.
- **Gotchas**: Default the flag to `false` in `.env.example` so a fresh clone is safe; the demo
  box's `.env` sets it `true`. Tests force either mode with `config(['securelab.vulnerable'=>...])`
  and assert the exploit succeeds in one and fails in the other â€” that dual-mode test IS the
  automated retest. Never give an "insecure file upload" finding a real execution sink: store on a
  private non-web disk and never execute, so even the weak path cannot compromise the host.
  If you ever run `php artisan config:cache`, the live-flip breaks â€” clear it for the demo.
- **First used in**: SecureLab (2026-09-10) â€” IDOR, SQLi, Stored XSS, insecure upload


---

## Laravel 12 + PostgreSQL 16 + Inertia — multi-provider integration SaaS

> Written after SociaPulse (2026-09-12): five social platform integrations, publishing,
> scheduling, engagement and analytics across 224 tests. **PostgreSQL is newer ground for
> this library than MySQL/MariaDB**, and the first three entries are the ones that cost real
> debugging time. `[LEARN]` graduated — the stack is written down, so the next project starts
> from here.

### PostgreSQL `timestamptz` Needs `'timezone' => 'UTC'` on the Connection

- **Stack**: Laravel (any) + PostgreSQL. Verified on Laravel 12 + PG 16.
- **Problem**: Laravel formats dates as UTC **wall-clock text** (`2026-09-11 17:04:13`) and
  hands that to the driver. A `timestamptz` column has to attach an offset, and with no
  session timezone set PostgreSQL attaches the **server's** — so every timestamp in the
  system lands offset by the machine's UTC offset. On a +08 box, scheduled posts fire eight
  hours early, analytics bucket into the wrong civil day, and token expiry is misread. It is
  **completely invisible to a developer working in UTC**, and nothing errors.
- **Solution**: one line in `config/database.php`:
  ```php
  'pgsql' => [
      // ...
      'search_path' => 'public',
      'timezone' => 'UTC',
  ],
  ```
  Laravel's `PostgresConnector` issues `SET TIME ZONE` when this is present. Then guard it,
  because the symptom is silent:
  ```php
  $this->assertSame('UTC', DB::selectOne('SHOW TIME ZONE')->TimeZone);
  $this->assertStringEndsWith('+00', $model->getRawOriginal('created_at'));
  ```
- **Gotchas**: `APP_TIMEZONE` does **not** fix this — it changes PHP's rendering, not what the
  driver sends. The bug surfaces as a comparison that is wrong by exactly the server offset,
  so `$date->gt(now()->subMinute())` returning false on a timestamp written seconds ago is the
  tell. Storage stays UTC; a tenant's zone is applied on render only.
- **First used in**: SociaPulse (2026-09-12)

### A Failed Statement Aborts the Whole PostgreSQL Transaction

- **Stack**: PostgreSQL, any ORM
- **Problem**: The MySQL habit of `try { insert } catch (UniqueConstraintViolation) { /* it's a
  duplicate, carry on */ }` **does not work on PostgreSQL**. A failed statement puts the
  transaction into an aborted state, and every subsequent query fails with
  `SQLSTATE[25P02] current transaction is aborted, commands ignored until end of transaction
  block`. The catch block runs, the code looks fine, and the request dies afterwards.
- **Solution**: never reach for the exception. Use `ON CONFLICT DO NOTHING`:
  ```php
  $inserted = WebhookEvent::insertOrIgnore([...]);   // returns affected rows
  if ($inserted === 0) { return response('', 200); } // duplicate: ack and drop
  ```
- **Gotchas**: it surfaces first under `RefreshDatabase`, because that wraps each test in a
  transaction — which makes it easy to dismiss as a test artefact. It is not: any surrounding
  transaction behaves identically in production. If an exception genuinely must be caught
  mid-transaction, wrap that statement in a `SAVEPOINT`.
- **First used in**: SociaPulse (2026-09-12) — webhook deduplication

### `$this->connection` Inside an Eloquent Model Is Not the Relation

- **Stack**: Laravel, any version
- **Problem**: A relation named `connection()` is natural domain vocabulary (an OAuth
  connection, a bank connection, a device connection). But `Eloquent\Model` declares a
  **protected `$connection` property** holding the database connection *name*. Inside the class
  that property is accessible, so `__get` never fires, the relation is never loaded, and
  `$this->connection` silently evaluates to a string. It raises a PHP **warning**, not an
  error, and the expression returns null. From **outside** the class the identical expression
  works perfectly, because the property is inaccessible there and `__get` does fire — which is
  what makes it so hard to spot.
- **Solution**: inside the model, call the relation method:
  ```php
  return $this->ownToken()->first()
      ?? $this->connection()->first()?->token()->first();
  ```
- **Gotchas**: the same collision exists for `$table`, `$keyType`, `$perPage`, `$attributes`,
  `$casts`, `$with` and `$dates` — never name a relation after one of those and then use it
  in-model. The failure mode is a null result plus a warning buried in the log, so the
  symptom is "this feature just doesn't work", not a stack trace.
- **First used in**: SociaPulse (2026-09-12) — every publish failed with "no stored credential"

### Tenant Resolution Middleware Is *Appended*, Not Prepended

- **Stack**: Laravel 11/12 (`bootstrap/app.php` middleware config), session-based tenancy
- **Problem**: `$middleware->web(prepend: [ResolveTenant::class])` puts it ahead of
  `StartSession`, and the active tenant is read from the session — so every authenticated page
  500s with `Session store not set on request`. Reaching for route middleware instead is the
  opposite error: it runs after the whole group, too late for anything in the group that needs
  a bound tenant.
- **Solution**: append it, ordered before anything that reads the tenant while building a
  response:
  ```php
  $middleware->web(append: [
      ResolveTenant::class,          // after StartSession, before Inertia's share()
      HandleInertiaRequests::class,
  ]);
  ```
- **Gotchas**: the larisHQ rule "resolve the tenant *before* the guard" applies only when the
  `users` table is itself tenant-scoped (`unique(tenant_id, email)`). Where users are global —
  one person in several workspaces — authentication does not depend on the scope and appending
  is correct. **Check which shape you have before copying either rule.**
- **First used in**: SociaPulse (2026-09-12)

### Versioned Credential Encryption — a Key Version Column, From the First Migration

- **Stack**: any application storing third-party OAuth tokens
- **Problem**: encrypting credentials against one permanent `APP_KEY` makes rotation
  all-or-nothing at a single instant across every row — which in practice means it never
  happens, and a suspected key compromise has no remedy short of asking every customer to
  reconnect. Retrofitting versioning after tokens exist means decrypting production
  credentials during a migration.
- **Solution**: the ciphertext records the key that produced it.
  ```php
  $table->text('access_token');
  $table->string('encryption_key_version', 16);   // the column that makes rotation a job
  ```
  Decryption selects the key by the row's own version, so two versions coexist and rotation is
  a background re-encryption: `Key v1 → decrypt → Key v2 → encrypt → update version`. Keys come
  from a config registry, not `APP_KEY`. Established framework primitives only — the versioning
  is key *management*, never a new cipher.
- **Gotchas**: rotation **must refuse** when the old key is missing, because re-encrypting
  means decrypting first — fail loudly rather than skipping rows nobody can read again. Two
  drills before production: a restore (the app recovers *without any customer reconnecting* —
  that is the pass condition) and a controlled rotation. A backup holding both the ciphertext
  and its key is a plaintext backup.
- **First used in**: SociaPulse (2026-09-12)

### A Scheduler's Dispatch Lease Is Not the Worker's Claim

- **Stack**: any every-minute scheduler feeding a queue
- **Problem**: the scheduler finds due rows and dispatches jobs, but a dispatched row stays
  `queued` until a worker picks it up — so the next minute's tick finds it again and dispatches
  again, piling up jobs that each do nothing. Using the worker's claim column for this breaks
  the claim's guarantee.
- **Solution**: two separate columns for two separate questions. `dispatched_at` is the
  scheduler's lease; `claimed_at` plus a status transition is the worker's claim.
  ```php
  // Lease, taken in one conditional statement so two schedulers cannot both win.
  $took = Target::whereKey($id)
      ->whereIn('status', $claimable)
      ->where(fn ($q) => $q->whereNull('dispatched_at')
          ->orWhere('dispatched_at', '<=', now()->subMinutes(10)))
      ->update(['dispatched_at' => now()]) === 1;
  ```
- **Gotchas**: the lease must go stale (10 min works) or a worker that died holding a row
  strands it forever. **Any reschedule must clear `dispatched_at`** — otherwise the scheduler
  treats the new time as already handled and the item never goes out, which looks like the
  scheduler is simply broken.
- **First used in**: SociaPulse (2026-09-12)

### Signed Permission Overrides, Never a Stored Effective Set

- **Stack**: any role system where roles are defaults rather than fixed grants
- **Problem**: "fixed roles, but let the owner tick individual permissions" invites storing the
  member's resolved permission list. That freezes them against the role definition as it stood
  the day they were customised: when a later release adds a permission to the role default,
  every customised member silently never receives it.
- **Solution**: store only the **differences**, signed.
  ```
  effective = defaults(role) ∪ {explicit grants} \ {explicit revokes}
  ```
  The table holds `(user, permission, granted: bool)`. Setting a permission back to its role
  default **deletes** the row rather than storing agreement — that is what lets future default
  changes keep flowing. A member with no overrides costs zero rows.
- **Gotchas**: pair it with the Grant Ceiling (nobody hands out what they do not hold) and a
  floor the top role cannot lose, or a workspace can make itself unadministerable. Test the
  ceiling in **both** directions: a rejection *and* an acceptance, or a too-strict ceiling
  ships unnoticed. The registry stays in code; an override naming an undeclared key is ignored
  at resolution, not trusted.
- **First used in**: SociaPulse (2026-09-12)

### Classify the Ambiguous Outcome Instead of Reconciling It

- **Stack**: any integration performing an irreversible remote write (publishing, payments, sends)
- **Problem**: an action that was sent but never answered leaves the outcome unknown. Retrying
  may duplicate something that cannot be undone; not retrying may lose it. The textbook answer
  — ask the provider whether the write already exists — needs a lookup endpoint most providers
  do not offer well.
- **Solution**: split failures by whether the provider gave a **definite** answer.
  - Provider responded with an error → nothing was created → safe to retry if retryable.
  - Timeout/connection loss after send → outcome unknown → park in a first-class `unverified`
    state, **never auto-retried**, with a human resolution path in the UI.
  Same safety property as reconciliation, no lookup dependency.
- **Gotchas**: `unverified` must be a real state with real copy, not an error bucket — the user
  needs to be told what happened, what we did *not* do, and what to check. "Refusing to publish
  is recoverable; publishing twice is not" is the sentence that settles every argument about it.
- **First used in**: SociaPulse (2026-09-12)

### Two-Stage Retention — Their Data and Your Figures Expire Differently

- **Stack**: any product storing third-party data under the provider's terms
- **Problem**: one global `data_retention_days` cannot express reality. One provider allows two
  years, another requires its data gone after 30 days, a third wants deletion propagated within
  24 hours. A single number is either illegally long for one or uselessly short for all.
- **Solution**: declare retention **beside each provider** (like capability), with two limits:
  `rawDays` for a stored copy of the provider's own figures, and `derivedDays` for numbers you
  computed. One purge, two stages: strip the raw half first and keep the row, delete the row at
  the derived limit. History survives without holding their data too long.
- **Gotchas**: carry a `confirmed` flag. Where the rule is believed rather than established,
  enforce the **strictest** reading — derived figures inherit the raw limit — and print
  "unconfirmed policy, strict reading" on every purge run so the open question stays visible
  instead of decaying into an assumption.
- **First used in**: SociaPulse (2026-09-12) — YouTube's 30-day Stored Authorized Data rule

### A Missing Ceiling Means OFF, Not Unlimited

- **Stack**: any metered third-party API billed per call
- **Problem**: `if ($cap !== null && $spent > $cap) { stop; }` reads naturally and is exactly
  backwards. An unconfigured ceiling is the state a system is in *before anyone has thought
  about cost* — which is precisely when it should not be spending.
- **Solution**: invert it. No ceiling configured → metered calls refused, with a reason the UI
  renders: *"No spend ceiling is set, so metered calls stay off until one is."* A ceiling of
  zero must degrade cleanly to "unavailable, and here is why", never to an error.
- **Gotchas**: record usage against **both** the tenant that caused it and the platform pool it
  came from — a per-tenant counter cannot answer "is there budget left" and a global one cannot
  answer "who spent it". A per-tenant allowance must bite *before* the platform ceiling, or one
  customer spends what everyone shares.
- **First used in**: SociaPulse (2026-09-12)

### Metric Honesty — Null Is Not Zero, and Incomparable Things Are Never Summed

- **Stack**: any dashboard aggregating several sources
- **Problem**: two quiet lies. Substituting `0` for "the provider never reported this"
  understates every average it lands in; and adding metrics with different counting rules
  (reach vs views vs impressions) produces a number that is true of nothing.
- **Solution**: (a) unavailable renders as *"not available for this channel"*, never `0` —
  enforce it in the query layer, not the template; (b) offer a cross-source total **only** for
  metrics every source defines identically, and have it **name the sources it could not
  include** rather than quietly shrinking its denominator; (c) keep each source's native metric
  name and value verbatim, so a metric's removal upstream does not erase the history you hold.
- **Gotchas**: normalise into a small allow-list and *drop* everything else, rather than
  mapping loosely — an approximate mapping is how an incomparable value ends up in a total
  anyway. Also report coverage (days observed vs requested): a source connected three days ago
  invites a comparison nobody should make.
- **First used in**: SociaPulse (2026-09-12)

### Three Laravel/Test Traps Worth One Line Each

- **`Http::fake()` MERGES stubs, it does not replace them.** A permissive stub in `setUp()`
  matches before a specific one registered later in the test, so the test passes against the
  wrong response. Register the full set per test, and put overrides **last** in the array
  (same-key spread: last wins).
- **`method_exists($disk, 'temporaryUrl')` is always true.** `FilesystemAdapter` declares it
  and the local driver **throws** from inside it. Ask `$disk->providesTemporaryUrls()`.
- **Laravel 12's skeleton has no `app/Http/Middleware/` directory** — `mkdir` before writing
  the first one, or the heredoc silently fails.
- **First used in**: SociaPulse (2026-09-12)

### Reaping an Abandoned Claim — to "Unknown", Never Back to the Queue

- **Stack**: any two-phase claim/complete over a queue (Laravel + Redis/database queues here)
- **Problem**: a worker that atomically claims a row and then dies — OOM killer, host reboot, or
  simply exceeding its own `--timeout` — leaves that row in the in-progress state forever. If
  the in-progress state is (correctly) excluded from the claimable set, no later tick can pick
  it up; if it is not terminal, nothing finishes it; and if it is absent from whatever powers
  the health screen, nobody is ever told. The customer watches "in progress" indefinitely.
- **Solution**: stamp `claimed_at` in the same atomic statement that takes the claim, and reap
  rows whose claim is older than a threshold **on an existing periodic tick** — no new scheduled
  command, so the deploy contract is unchanged. Move them to an explicit **"outcome unknown"**
  state that the health surface already treats as needing a human.
- **Gotchas**: (1) **Do not re-queue.** A worker killed mid-call is indistinguishable from a
  call that never answered — the side effect may well have landed, so retrying risks doing it
  twice, which for a publish, a payment or an email cannot be undone. (2) The threshold must sit
  **clear of the worker's own timeout** (15 min against `--timeout=600` here), and the test that
  protects you is the negative one: a claim *inside* the timeout must be left alone, or the
  reaper reports live work as abandoned. (3) Tie the two numbers together in a comment at both
  ends; raising the worker timeout alone silently breaks it.
- **Smell that finds this bug**: a timestamp column written on every claim and read by no query
  anywhere. The author saw the hazard clearly enough to record the evidence and stopped there.
- **First used in**: SociaPulse (2026-09-12)

### Trust the Reverse Proxy Before Anything Keys on an IP

- **Stack**: Laravel 11/12 behind Nginx/Caddy/ALB/Cloudflare (applies to any framework)
- **Problem**: with TLS terminated at a proxy, every request arrives from the loopback over
  plain http. This is filed as a deployment footnote and is not one: `Request::ip()` is
  typically feeding the **audit log** (so every action records the proxy rather than the actor —
  wrong in a way that still reads as evidence) and is the **key for every rate limiter** (so the
  entire user base shares one bucket; an N-per-hour signup limit refuses customer N+1 and
  everyone after them). `isSecure()` is also false, which decides the session cookie's `Secure`
  flag when it is left to auto-detect.
- **Solution**: set trusted proxies from a **config file** and apply them in a service provider's
  `boot()` via `TrustProxies::at()` / `withHeaders()`. Trust `X-Forwarded-For/Host/Port/Proto`.
  Default to the loopback pair for a same-host proxy; a CDN or load balancer adds its ranges.
- **Gotchas**: `bootstrap/app.php`'s `withMiddleware` closure runs **before config is loaded** —
  `config()` there fatals outright. `env()` *does* resolve there, which makes it the worse trap:
  `php artisan config:cache` skips loading `.env`, so an `env()` call in that closure returns
  null on a cached production build and the proxy goes untrusted **only in production**.
- **Test that proves it**: two requests from one `REMOTE_ADDR` with different `X-Forwarded-For`
  must not share a rate-limit bucket — and a forwarded header from an *untrusted* source must be
  ignored, or every IP-keyed limit becomes bypassable by setting a header.
- **First used in**: SociaPulse (2026-09-12)

### Rate-Limit What Costs Money, Not Only What Authenticates

- **Stack**: Laravel Fortify (the shape is general)
- **Problem**: Fortify rate-limits the login POST and nothing else. Registration,
  `password.email` and `password.update` ship with `guest` alone — unauthenticated and unbounded.
  The password broker's own `throttle => 60` reads like coverage but bounds re-sends to a
  **single address**, which an attacker walking a list of addresses never encounters.
- **Solution**: named limiters for each, applied by a middleware that dispatches on **route
  name** from inside the package's own route group (`config('fortify.middleware')`) — the only
  seam that reaches routes a package defines. Key the reset request **twice**: per IP (stops one
  host walking a list) and per email (stops many hosts mailbombing one person). Prefer per-hour
  buckets to per-minute: a per-minute bucket looks stricter and is weaker, since one request
  every sixty seconds stays under it forever.
- **Gotchas**: (1) Fortify names the registration POST `register.store`, **not** `register` —
  keying on `register` binds the GET that renders the form and leaves the POST open, silently,
  because an unmatched name simply passes through. Assert each mapped name resolves to a real
  POST route. (2) `ThrottleRequests::handle` only resolves a *named* limiter when
  `func_num_args() === 3`; a fourth argument reinterprets the name as a max-attempts count,
  which casts to `0` and closes the endpoint to everybody. (3) An **unregistered** limiter name
  fails the same way — an outage, not a gap — so assert every name is registered.
- **Why it matters more than the bill**: a transactional sender flagged as a spam source stops
  delivering *everything*, including the verification emails registration itself depends on. One
  abused endpoint takes out signup for every real customer.
- **First used in**: SociaPulse (2026-09-12)

### Response-Wide Middleware Belongs in the Global Stack, Not a Route Group

- **Stack**: Laravel 11/12 (the reasoning is framework-general)
- **Problem**: anything that must hold on *every* response — security headers, request ids, CORS
  — registered on the `web` group covers rendered pages and misses the two responses most
  reachable by someone who is not a customer: a **404** never enters the group at all (no route
  matched, so there is no route pipeline), and an **auth redirect** is rendered from an
  exception thrown straight past anything sitting above it in the stack.
- **Solution**: `$middleware->append(...)` — global. Then test the error paths *first*: 404, the
  unauthenticated redirect, the 500. The happy path is the case that proves the least.
- **Companion note (security headers)**: send HSTS only when `$request->isSecure()` — asserting
  it unconditionally pins `localhost` to https in a developer's browser for a year, and browsers
  ignore it on plain http anyway. Leave `preload` off: it is close to irreversible and commits
  every future subdomain, which is a decision about the domain, not a middleware default.
- **First used in**: SociaPulse (2026-09-12)

### A Check That Can Fail *To Run* Needs a Test That It Ran

- **Stack**: any toolchain gate — type checkers, linters, scanners, coverage gates
- **Problem**: tools whose success output is empty fail identically to succeeding. A project
  shipped with **no front-end type checking at all**: `vue-tsc` resolves `typescript/lib/tsc`,
  a subpath the TypeScript 7 native rewrite dropped, so it died on one line of
  `ERR_PACKAGE_PATH_NOT_EXPORTED`, while `vite build` stayed green because vite *transpiles*
  TypeScript without checking it. `vue-tsc@3.3.11` still declares peer `typescript >=5.0.0`,
  which `^7` satisfies, so npm never warned either. Three signals, all reading "fine".
- **Solution**: pin the dependency **exactly** (a caret range floats into the breaking major and
  the failure mode is a checker that stops running, not one that complains), expose the check as
  a named script, invoke it in CI, and write a test asserting all three still hold. Then break
  each one and watch the suite go red.
- **Gotchas**: distrust silence from a tool you have not just watched fail. Prove the checker
  works by injecting a deliberate error before believing a clean run.
- **First used in**: SociaPulse (2026-09-12)

### A Content-Security-Policy for Inertia + Vite that needs no script nonce

- **Stack**: Laravel 12 · Inertia · Vite · Vue 3 · Bootstrap/AdminLTE
- **Problem**: the reflex CSP for an SPA-ish app is nonces everywhere, which means publishing a
  nonce in the DOM for the client to read — and an injected script can read it back and authorise
  itself, which is most of what the policy was for.
- **Solution**: look at the rendered HTML first. A built Inertia page has **no inline executable
  script**: Vite emits external `<script type="module" src>`, and Inertia hands the page over in a
  `<script type="application/json" data-page>` block, which is never *prepared for execution* and
  so is not a `script-src` subject at all. That makes `script-src 'self'` — no nonce, nothing
  published — both the strictest and the simplest policy.
  A nonce is still needed for the `<style>` elements Inertia injects at runtime (progress bar,
  error modal); it honours `createInertiaApp({ nonce })`, read from a `<meta name="csp-nonce">`.
  Publishing *that* costs nothing precisely because `script-src` names no nonce.
  Keep `'unsafe-inline'` on **`style-src-attr`** only — Bootstrap and Popper position dropdowns by
  writing `style` *attributes*, which cannot carry a nonce — so the nonce still governs `<style>`
  elements and CSS-injection cannot read the page out through selector matching.
  Generate the nonce and call `Vite::useCspNonce()` **before** `$next($request)`; set the header
  after. Register the middleware **globally**, or 404s and auth redirects go out bare.
- **Gotchas**: the dev-server relaxation must be gated on `Vite::isRunningHot() && ! app()->isProduction()`
  — a stray gitignored `public/hot` (a crashed dev server, a deploy that rsynced `public/`) would
  otherwise hand a customer the loose policy. **Browser consoles do not report CSP violations to
  automation tools**: violations are browser-generated errors, not `console.*` calls, so an empty
  console is not evidence. Verify with a visual diff and an in-page `securitypolicyviolation`
  listener, and break the policy on purpose once to confirm the instrument reports it.
- **First used in**: SociaPulse (2026-09-12)

### Claim-and-reap for any queued write to a third party

- **Stack**: Laravel queues · PostgreSQL (any DB with a conditional UPDATE)
- **Problem**: a worker that dies mid-send leaves a row in a state nothing can move. If the
  completion timestamp is written *after* the provider answers, it cannot serve as the guard —
  the dangerous window is exactly the one where it is still null.
- **Solution**: three states and two thresholds.
  **Claim** in one conditional `UPDATE ... WHERE status = 'queued'`, checking the affected-row
  count — read-then-write lets two workers both observe `queued`.
  **Reap `sending`** after a threshold comfortably above the worker's own `--timeout`, into an
  `unverified` state that is **never re-sent**: a worker that died mid-send is indistinguishable
  from an unacknowledged success, and re-sending puts a second message in front of a real
  audience. Let the operator overrule it with an explicit acknowledgement **checked server-side**.
  **Reap `queued` too, but much later** (e.g. 60 min vs 15) and into a plainly *failed* state:
  nothing reached the provider, so re-sending is safe, and the long threshold protects a merely
  backed-up queue. Skipping this is what makes an in-flight guard a permanent lock-out.
  Close the state set with a DB CHECK constraint and assert the enum and the constraint agree.
- **Gotchas**: tie both thresholds to the worker timeout and **test that raising one without the
  other fails** — otherwise ordinary long work gets reported as abandoned. Capture any field the
  audit row needs *before* the write that clears it.
- **First used in**: SociaPulse (2026-09-12), publish path then reply path

### A restore drill that can actually fail

- **Stack**: PostgreSQL · any app with application-level encryption
- **Problem**: a documented restore procedure that nobody runs, whose pass condition checks
  configuration rather than capability, certifies a recovery point that cannot recover.
- **Solution**: script it, and make each step refuse to pass vacuously.
  Take the keys **from their own store, passed as a file** — never the app's `.env`, which proves
  only that the running machine can read its own tokens. Restore into a scratch database, refuse
  if the scratch name is empty or equals the live one, and arm the cleanup `trap` **before**
  creating it so a failed restore cannot leave production data lying around.
  Point the real application at the restored copy with environment variables (Laravel's dotenv is
  immutable and yields to the environment) and **decrypt every stored credential** — not "is a key
  configured", which a wrong, truncated or foreign key passes. Fail when there are **no**
  credentials: a drill against an empty table proves the database came back, not the keys.
  Then prove the drill fails: re-run it with a deliberately wrong key and check the exit code.
- **Gotchas**: **match client tools to the server's major version** — several are usually
  installed and `PATH` picks silently; `pg_dump` refuses across versions but `pg_restore` can
  appear to work. Read the server version from the app and refuse on mismatch. Gitignore the dump
  directory: a dump holds every tenant's data and every encrypted credential.
- **First used in**: SociaPulse (2026-09-12), AC-22

### Runtime overrides for controls that must not wait for a deploy

- **Stack**: Laravel 12 · PostgreSQL (any framework with a config layer)
- **Problem**: kill switches, spend ceilings and rate limits read from `config()` are unreachable
  in the incident they exist for — the remedy is an SSH session, a config cache rebuild and a
  restart. But moving them wholly into the database loses the safe, reviewable, version-controlled
  default.
- **Solution**: **config is the default and the floor; a `platform_settings` row is an override.**
  `isOverridden($key) ? get($key) : config($key)` — tested with `array_key_exists`, never `??`,
  because a stored `null` ("deliberately cleared") is not an absent row ("never set"). Deleting the
  row is the recovery path: no migration, no rollback, the deployed configuration applies again.
  Keys are **code-owned** in a registry that refuses undeclared ones, or the table accumulates rows
  that look saved and are never read. Resolve most-specific-first (`switch:x:publish` →
  `switch:x:*` → config's `['*' => false, 'publish' => true]`), or a provider-wide override
  silently swallows a per-capability rule.
- **Gotchas**: cache the whole map under one key and drop it on write — these are read in hot
  loops (per account, per tick), so a query per check is one query per account per tick. Enforce
  the ordering rules rather than documenting them: enabling a *metered* capability with no ceiling
  set is refused, while disabling anything is always allowed — **never put a precondition in front
  of the safe direction**. Audit every change with before/after, and show on the screen whether a
  value is an override or the shipped default, or the operator cannot tell a decision from a
  default.
- **First used in**: SociaPulse (2026-09-12), REQ-71 kill switches and the X spend ceiling

### One Locale, Resolved at the Boundary — Never `Intl(undefined)`

- **Stack**: any UI rendering money, numbers or dates that two people will compare
- **Problem**: `new Intl.NumberFormat(undefined, …)`, `toLocaleString()` and
  `toLocaleDateString()` with no locale all mean *whichever locale this machine is set to*.
  The same report then renders `1,234.56` on one desk and `1.234,56` on the next — the same
  number, read as a different sum. It reviews as an innocuous default and it is a dependency
  on the reader's laptop.
- **Solution**: one configuration value (a `display.locale` setting, defaulted per client),
  delivered on the session-bootstrap call the SPA already makes, applied **once** in a single
  formatting module that every component imports. No component calls `Intl` directly. Ship a
  compile-time-safe fallback constant for the window before the bootstrap response lands.
- **Gotchas**: (a) Intl separates a currency symbol from its digits with a **non-breaking
  space** (U+00A0) — normalise it in assertions or they fail against strings that look
  identical; (b) compact notation differs between Node and Chrome for the same input, so a
  test/browser mismatch on formatting is a *locale* bug until proven otherwise — that
  disagreement is how this one was found; (c) the locale changes the currency symbol, not just
  the separators (`en-MY` renders MYR as `RM`), so confirm the client wants that; (d) bare
  `.toLocaleString()` on integer row counts is the same defect, lower stakes — sweep for it.
- **Test that matters**: format the same value under three locales and assert they differ in
  the expected way. Asserting one locale's output only proves the formatter runs.
- **First used in**: WebAppsBI (2026-09-13, `NFR-18`, DEC-035)

### Cross-Filter That Exempts Its Own Source

- **Stack**: any dashboard where clicking a chart filters the other charts
- **Problem**: applying the selection uniformly narrows the *source* widget too, which redraws
  as a single 100% category. The numbers are right and the screen is a dead end — the control
  used to choose a category has erased every other category, so the only way out is a "clear"
  link the user is not looking at. Every test passes, because no test clicks twice.
- **Solution**: keep the cross-filter as a **transient layer** over the base filter model,
  never written into saved filters or the URL. Resolve each widget's filters through one
  function that drops the cross-filter when the widget groups by the same dimension. Show the
  selection as *state* — chosen item at full opacity, the rest dimmed (~0.2), never removed —
  and make a second click on the chosen item the way out, in addition to an explicit chip.
- **Gotchas**: the exemption belongs in the store keyed by dimension, not in any one chart, or
  the next clickable widget reintroduces the bug. The source widget's own totals then stay
  unfiltered and will legitimately differ from the KPI strip — that is correct, and worth a
  moment's thought before someone "fixes" it.
- **First used in**: WebAppsBI (2026-09-13, `REQ-DASH-013`, DEC-034)

### Log Redaction as a Channel Tap (Laravel + PostgreSQL)

- **Stack**: Laravel 11/12 · Monolog 3 · PostgreSQL (any driver whose errors quote values)
- **Problem**: client data reaches `laravel.log` through the framework, not through application
  code: `QueryException`'s message is the SQL with every binding substituted, and PostgreSQL adds
  `DETAIL: Key (col)=(value)` or `Failing row contains (…)`. A failed batched INSERT writes the
  whole batch. Frame arguments add the bindings again when `zend.exception_ignore_args` is off.
- **Solution**: one invokable class added as `'tap' => [...]` on **every** writing channel
  (`single`, `daily`, `stderr`, `syslog`, `errorlog`, `slack`, `papertrail`). Its processor
  `LogRecord::with()`s a scrubbed message and context: strip `(Connection: … SQL: …)` to the end,
  replace the values after `Key (…)=`, replace `Failing row contains (…)`, redact credential keys
  at any depth, and rebuild any `Throwable` in context as class + scrubbed message + file +
  **argument-free** frames, following `previous` a few levels.
- **Gotchas**: `stack` has no handlers of its own — tap its children. The `emergency` logger
  cannot be tapped. Constraint names and SQLSTATE survive, and are what an operator needs. Test it
  end-to-end: write through a real channel configured from `single`'s config and read the file —
  a unit test on the processor alone does not prove the tap is wired.
- **First used in**: WebAppsBI (2026-09-13, `REQ-SEC-015`, DEC-052)

### Per-Tenant Permissions for Anything That Lists, and Ids Authorised Before Validation

- **Stack**: Laravel policies + FormRequests over a per-company RBAC (any multi-tenant RBAC)
- **Problem**: two shapes of the same boundary leak. (1) A permission held per tenant is checked
  as "held in any tenant" on a listing endpoint, so the list is global. (2) A client-supplied id
  (parent, template version, target company) is validated with `exists`/`unique` before
  authorisation — a 422 then confirms foreign records, and a bare `exists` lets a foreign record be
  attached.
- **Solution**: (1) resolve the tenants where the actor holds the permission
  (`permittedCompanyIds` filtered by `hasAnyForCompany`) and restrict the query to rows granted in
  those tenants; a single-record read outside the set is **404**. (2) authorise in the
  FormRequest's `authorize()` (it runs before `rules()`), or validate only the id's shape, load it,
  authorise, then run the remaining rules. Scope "is this id usable" to the tenant in the query
  itself (`whereHas(... company_id = ? or null)`), and answer foreign with the same message as
  missing. For an action on two records (moving a company), authorise both ends.
- **Gotchas**: global admins bypass `Gate` via `Gate::before`, so do the query restriction outside
  the policy. Remove the moved/attached column from `$fillable` so a later `fill($validated)` cannot
  skip the check. Test with an actor who legitimately manages one side and not the other — an
  outsider with no grants never exercises a two-record action.
- **First used in**: WebAppsBI (2026-09-13, `REQ-SEC-003/004`, DEC-053)

---

## Laravel 13 + Vue 3.5 + TypeScript SPA + Sanctum (multi-tenant SaaS)

> Captured 2026-09-16 from **WhatsApp Business Automation SaaS** PH-00 + PH-01 (foundation,
> identity, tenancy, RBAC, audit, entitlements). Proven by 221 Pest + 16 Vitest tests and a live
> smoke on a running app — **not yet shipped to production**, so treat deployment-shaped claims as
> `Assumed`. The Vue/Sanctum half is distinct from the existing *Laravel 13 + Inertia 3 + React 19*
> section: no Inertia, no Wayfinder, a real JSON API with cookie auth.

### Version Baseline (installed and green 2026-09-16)
Laravel **13.32** · PHP **8.4** · `laravel/fortify` **^1.39** (headless) · `laravel/sanctum` **^4.0**
(SPA cookie mode) · `spatie/laravel-permission` **^8.3** (teams mode) · `laravel/horizon` **^5.49** ·
`laravel/reverb` **^1.11** · Pest **^5.2** · Larastan **^3.12** (level 6) · Vue **3.5** ·
TypeScript **5.9** · AdminLTE **4.9** · Vite. Tests run on in-memory SQLite; MySQL **8.4** in CI.

### Composite `(tenant_id, id)` Foreign Keys — the MySQL substitute for RLS
- **Stack**: Laravel 13 + MySQL 8, multi-tenant, no Postgres RLS available.
- **Problem**: a single-column FK (`contact_id`) lets a row in tenant A point at a parent in
  tenant B. A global Eloquent scope hides it from reads but does not stop the write, and nothing
  at the database level refuses it.
- **Solution**: give every tenant-owned table a `UNIQUE (tenant_id, id)` and declare child FKs as
  composite `(tenant_id, parent_id) REFERENCES parent (tenant_id, id)`. Wrap it in one schema macro
  (`Blueprint::tenantForeign`) so every later migration gets it for free and reviewers have one
  thing to grep for. The database now refuses cross-tenant parents even when the application layer
  is wrong.
- **Gotchas**: the macro must be registered in a service provider that boots before migrations
  (`AppServiceProvider::boot`). SQLite honours the unique index but is lax about the FK, so the
  real proof is the MySQL CI run. Every `->constrained()` in a tenant table is a defect.
- **First used in**: WhatsApp Business Automation SaaS (2026-09-16, REQ-TENANT-005)

### Tenant-Aware Queue Jobs — set the context in middleware, never in `handle()`
- **Stack**: Laravel queues + a global tenant scope driven by a request-scoped context object.
- **Problem**: the tenant context is resolved from the authenticated principal in HTTP middleware.
  A queued job has no request, so the global scope either throws or — worse — silently resolves to
  whatever tenant the worker last served, leaking rows between tenants inside one worker process.
- **Solution**: a `TenantAwareJob` interface plus a `TenantAware` job middleware that reads the
  tenant id serialized on the job, sets the context, runs the job, and clears the context in a
  `finally`. An architecture test asserts that no job calls `TenantContext::set()` directly and
  that every job touching a tenant model implements the interface.
- **Gotchas**: the clear must be in `finally`, or a thrown job poisons the next job on the same
  worker. Serialize the tenant **id**, not the model — a `SerializesModels` reload runs through the
  scope that is not set yet. Retries and `Horizon` restarts re-enter the middleware, so it must be
  idempotent.
- **First used in**: WhatsApp Business Automation SaaS (2026-09-16, REQ-TENANT-004)

### Reserve-then-Commit Usage Counters (plan limits that survive concurrency)
- **Stack**: Laravel + MySQL, SaaS plan entitlements over an asynchronous pipeline.
- **Problem**: `if (count() < limit) { create(); }` is a check-then-act race — two simultaneous
  requests both pass the check and the tenant ends up one over its plan. Counting live rows also
  cannot express "in flight": a queued message has consumed quota but does not exist yet.
- **Solution**: two tables. `usage_counters` holds the committed number per (tenant, metric,
  period); `usage_reservations` holds short-lived holds. The entitlement service takes a row lock
  on the counter (`lockForUpdate`), checks `committed + reserved < limit`, writes a reservation,
  and returns a handle. The worker commits the reservation on success or releases it on failure; a
  scheduled reaper releases expired holds.
- **Gotchas**: the lock has to be on the counter row, not the tenant row, or every metric
  serialises behind one lock. SQLite ignores `lockForUpdate` entirely, so the concurrency test
  proves nothing locally — run it on MySQL in CI and say so in the phase report. Period rollover
  (monthly counters) needs its own key, not a `WHERE created_at >=` scan.
- **First used in**: WhatsApp Business Automation SaaS (2026-09-16, REQ-PLAN-002/003)

### Headless Fortify + Sanctum Cookies Behind a Vue SPA
- **Stack**: Laravel 13 + Fortify (no Blade views) + Sanctum stateful API + Vue 3 SPA on the same
  registrable domain.
- **Problem**: Fortify's defaults assume server-rendered views and redirect responses; a JSON SPA
  needs 2xx/422 and its own reset-link URL. Rolling your own auth to avoid that throws away 2FA,
  throttling, password confirmation and breached-password checks.
- **Solution**: keep Fortify for every credential operation (login, register, password, 2FA,
  profile) and bind the response contracts to JSON responders; point the reset URL at the SPA
  route; put the API behind `statefulApi()` so cookies plus CSRF apply. The app's own
  `/api/v1/...` controllers never touch passwords — profile and password changes go to the Fortify
  endpoints, which is a deviation worth writing down because the API surface then has no
  `PATCH /me` for those fields.
- **Gotchas**: Fortify's rate limiters are named and must be registered per email **and** per
  email+IP, or one attacker IP rotation defeats the cap. `Password::defaults()` with the breached
  check belongs in a service provider, or the invitation-acceptance path creates passwords under
  no policy. Session regeneration on login is Fortify's; anything you add around it must not run
  before it.
- **First used in**: WhatsApp Business Automation SaaS (2026-09-16, REQ-AUTH-001..005)

### `spatie/laravel-permission` Teams Mode Keyed on `tenant_id`
- **Stack**: Laravel 13 + spatie/laravel-permission 8 in teams mode.
- **Problem**: one user belongs to several tenants with a different role in each. Non-teams mode
  gives the union of every grant, so an agent in tenant B inherits their owner role from tenant A.
- **Solution**: enable teams mode with `tenant_id` as the team key and set the team id from the
  resolved tenant context in the same middleware that resolves the tenant — before any `can:`
  middleware runs. Pair it with a declared permission registry (code owns the keys) and a role
  provisioner, so a new permission is a code change plus a seeder run, never a manual grant.
- **Gotchas**: the permission cache is keyed per team; forget it on role changes inside
  `DB::afterCommit`, not inline. A `users.access_version` column is worth adding at the same time —
  bump it on every role or membership change so a future permission cache has something to key on
  (it may legitimately be write-only until that cache exists; record that, or a later audit reads
  it as dead code).
- **First used in**: WhatsApp Business Automation SaaS (2026-09-16, REQ-RBAC-001/002)

### Vue 3 + TypeScript — the two toolchain traps
- **Stack**: Vue 3.5, TypeScript 5.9, Vue Flow, Vite.
- **Problem**: (1) `ref<Edge[]>` on a Vue Flow edge array makes `tsc` recurse into a type that
  exceeds its depth limit — `TS2589: Type instantiation is excessively deep`. (2) `vue-tsc` is not
  part of `vite build`, so a type error ships.
- **Solution**: `shallowRef` for graph node/edge collections (they are replaced wholesale anyway,
  so reactivity depth buys nothing). Run `vue-tsc --noEmit` as its own CI step and prove the step
  works by planting an error once and checking it exits non-zero.
- **Gotchas**: a type-check step that has never failed is not known to work. Pin the Node version
  in `.nvmrc` **and** `engines`, and run the verifier under the shell default runtime.
- **First used in**: WhatsApp Business Automation SaaS (2026-09-16, REQ-FND-010)

---

## Third-party webhook + credential integration (Meta WhatsApp Cloud API)

> Captured 2026-09-16 from **WhatsApp Business Automation SaaS** PH-02. Provider-specific details
> are Meta's, but every pattern below applies to any provider that posts signed webhooks and hands
> you a long-lived token. Proven by 397 Pest + 36 Vitest tests against a fake; **not yet exercised
> against the live provider**, so treat the runtime claims as `Assumed`.

### Signature Verification Over the Raw Body — and the test that proves it
- **Stack**: any framework that decodes JSON before your controller runs.
- **Problem**: the HMAC is over the exact bytes the provider sent. Re-serialising the decoded JSON
  changes unicode escaping, key order and whitespace, so verification fails for every payload that
  is not plain ASCII in the provider's own key order. It passes your tests, because your tests
  build the payload with the same serializer.
- **Solution**: read the raw stream (`$request->getContent()`), HMAC that, `hash_equals` the
  result. Register the route **outside** every middleware group so nothing can touch the body first.
  Decode separately, after verification. Fail closed when the secret is unconfigured — an unset
  secret must never verify, or "webhooks are off" silently becomes "anyone can post events".
- **Gotchas**: the proving test must use a payload the naive implementation fails —
  non-ASCII content **and** unusual key order. A test built with `json_encode` on an ASCII fixture
  passes either way and proves nothing. Never log an unverified body: it is attacker-controlled.
- **First used in**: WhatsApp SaaS (2026-09-16, REQ-WEBHOOK-002)

### Four-Class Error Classification — the AMBIGUOUS class is the one that matters
- **Stack**: any paid third-party API where a call has side effects.
- **Problem**: the usual triad is transient / permanent / auth, and it quietly assumes you know
  whether a failed call took effect. For "unknown error", a timeout, or a connection failure, you
  do not — and retrying is how a customer receives the same message twice, or gets charged twice.
- **Solution**: add a fourth class, `ambiguous`: *the call may already have taken effect*. The
  caller never blind-retries it; it reconciles against the provider's own record first. Default an
  **unrecognised** code with no HTTP status to ambiguous, not transient — guessing "safe to retry"
  is the expensive direction to be wrong in. Hold the mapping in one table with the doc URL, and
  walk every row in a table test.
- **Gotchas**: providers rarely publish a retryability column, so the classification is your
  inference — say so in a comment and re-read it whenever a new kind of call is added. A code the
  provider frames as a rate limit may be a quality signal where retrying makes things worse.
- **First used in**: WhatsApp SaaS (2026-09-16, REQ-META-008)

### Provider-Attested Resource Binding — never trust the browser's id
- **Stack**: any OAuth-ish popup flow that posts resource ids to the parent window.
- **Problem**: the popup hands the browser a resource id and the browser posts it to your server.
  A tenant can post *any* id. If you bind on that, one tenant claims another's resource.
- **Solution**: treat the posted ids as **hints**. Exchange the code, then ask the provider what
  the token actually covers (`debug_token` → `granular_scopes[].target_ids`) and bind on that. A
  hint outside the attested set is refused and audited as a security event. Where the token covers
  exactly one resource and no hint was sent, infer it; where it covers several, refuse rather than
  guess. Filter the attested list by the scope that actually grants the resource type — other
  scopes carry ids of other kinds.
- **Gotchas**: validate the origin of the `postMessage` with an **exact allow-list**. Meta's own
  sample uses `origin.endsWith('facebook.com')`, which `evilfacebook.com` satisfies. Also enforce
  one-resource-to-one-tenant in the database, and decide explicitly whether disconnecting releases
  it — otherwise the first tenant to connect a resource holds it forever.
- **First used in**: WhatsApp SaaS (2026-09-16, CHANGE-004)

### Versioned Credential Keyring — with the length check openssl will not do for you
- **Stack**: PHP/openssl (the trap is not PHP-specific), any stored third-party credential.
- **Problem**: rotating the application key to rotate one integration's secrets is too blunt, and a
  single-key scheme has no window in which old and new ciphertext both decrypt. Worse:
  **`openssl_encrypt` silently zero-pads a short key**. An 8-byte key encrypts happily and
  everything downstream calls it AES-256. Nothing in a deploy reveals it.
- **Solution**: a keyring of `version => key`, the version stored beside each ciphertext, AES-256-GCM
  so tampering throws instead of returning rubbish. **Validate the key length against
  `openssl_cipher_key_length()` and throw** — and assert the keyring at boot, not at first use.
  Ship the key-generation command *and* the rotation job; re-encrypt, then drop the old version.
- **Gotchas**: never fall back to another key version on failure — a GCM tag mismatch is tampering
  or the wrong key, and both are failures. Keep the old version in the ring until rotation reports
  zero rows on it. If a config comment names a command, that command must exist: hand-generating a
  key is exactly how a wrong-length one gets in.
- **First used in**: WhatsApp SaaS (2026-09-16, REQ-SECURITY-006)

### "Unknown" Is Not "Failed" — and it is not "healthy" either
- **Stack**: any health check that depends on a third party.
- **Problem**: a two-valued check (pass/fail) has to call a provider outage something. Called
  `fail`, it tells the customer their integration is broken when it is not. Called `pass`, it
  promotes a genuinely broken integration to healthy the moment the provider has a 5xx.
- **Solution**: three results — `pass`, `fail`, `unknown`. The UI renders `unknown` in grey with
  "couldn't reach them just now", never red. The status machine treats `unknown` as **no
  information**: it may not promote *or* demote. Only a real `pass` on a credential check may
  promote an account.
- **Gotchas**: the bug hides in the aggregator, not the check — `if (no failures) status = healthy`
  scores a page of `unknown` as perfect health. Require positive evidence to promote.
- **First used in**: WhatsApp SaaS (2026-09-16, REQ-META-006/007)

### Store-Then-Acknowledge Webhook Ingest
- **Stack**: any high-volume provider webhook.
- **Problem**: doing the work inline makes the provider's timeout your latency budget, and any
  exception after you have the data turns into a provider retry and a duplicate.
- **Solution**: verify → insert raw (unique index on the payload hash **is** the dedupe) → dispatch
  a job `afterCommit` → 200. A duplicate key is a 200, not an error: you already have it. Nothing
  after the insert may change the HTTP status. Store the hash as `binary(32)`, not 64 hex chars, on
  a table that will hold millions of rows.
- **Gotchas**: cap the **work**, not just the body size — a 3 MB body of minimal entries is tens of
  thousands of handler runs in one job. An unknown field is `ignored`, never `failed`, and logged
  once an hour so a new provider field is visible without flooding. A delivery that resolves to no
  tenant is `orphaned`, not failed, and must not carry a tenant id it does not belong to.
- **First used in**: WhatsApp SaaS (2026-09-16, REQ-WEBHOOK-003/004/005)

## Contact data, consent and bulk file handling (PH-03, WhatsApp SaaS)

### Portable Literal `LIKE` — the ESCAPE clause both engines need
MySQL defaults the LIKE escape character to `\`; SQLite has none. Escaping `%` and `_` without an
explicit `ESCAPE` clause therefore behaves differently on each, and if you test on one and ship on
the other the suite cannot see it. One helper, used by every literal search:

```php
$sql = $column.' LIKE ? ESCAPE '."'\\\\'";   // $column is always a literal from an allow-list
$query->whereRaw($sql, [$pattern], $boolean); // $pattern is bound
```

Escape `\` first, then `%` and `_`. Test the **positive** case — searching for `%` finds the row
containing `%` — because the negative case passes on a filter that matches nothing.

### Two-Axis Consent — ours versus the platform's
Any channel where the end user can mute you at the platform level needs two columns, not one:

| | ours | the platform's |
|---|---|---|
| set by | sign-up, import, keyword, agent | a provider webhook, or an error code on send |
| reversible by us | yes | **never** |

Collapsing them into one status produces a UI that appears to offer a control it does not have. The
send gate is `ours = opted_in AND theirs = allowed AND not suppressed`, computed server-side and
sent to the client as one boolean — the screen must never re-derive it from the parts and drift
from what sending actually does. One service writes both columns and appends to an append-only
event table in the same transaction; an arch test keeps it the only writer.

### Spreadsheet Export Injection — the library will not do this for you
A library that builds cells from raw values will happily emit a live formula. Route every exported
cell through one helper that builds an explicit string cell and prefixes `'` when the value starts
with `= + - @ TAB CR`. Ban the convenient bulk constructor with an arch test, because it is both the
obvious spelling and the vulnerable one. Include the phone-number column: E.164 starts with `+`.

### File Intake Without an AV Scanner
For a CSV/XLSX intake, an AV engine detects none of the three real threats. Ship instead:
server-side `finfo` sniffing (never the client's type or the extension), a strict allow-list, a size
cap, a **zip compression-ratio check** (a real spreadsheet measures ~12x; refuse past ~200x),
`libxml_set_external_entity_loader(fn () => null)` before parsing XLSX, private storage under a
generated name, and short-lived presigned download URLs with `Content-Disposition: attachment`.

### Typed EAV for Tenant-Defined Fields
When tenant-defined attributes must be *filtered on* at scale, a JSON column cannot be indexed for
dynamic keys. Use `value_text` / `value_number` / `value_date` / `value_bool` with an index per type
keyed `(tenant_id, definition_id, value)`. The cost is that **a definition's type is locked once any
value exists** — changing it strands every stored value in the wrong column with no correct
migration. Say so on screen rather than offering one nobody would trust.

### Test on the Engine You Deploy To
Non-negotiable, and cheap to set up on day one. Point `phpunit.xml` at the same engine as `.env`:

```xml
<env name="DB_CONNECTION" value="mysql"/>
<env name="DB_DATABASE" value="<project>_test"/>
```

A SQLite suite cannot see a 64-character identifier overflow, an illegal `ON DELETE SET NULL`, a
collation difference, a strict-mode coercion, or a `LIKE` escape divergence. All five are hard
errors or silent wrong answers in production. Pair it with a migration-source scanner that fails
the build when a generated index name would exceed 64 characters — that one catches the class
before the migration ever runs.
