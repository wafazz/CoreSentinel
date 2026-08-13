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
