# Review Protocol
> Self-review checklist before delivering code. Run after every significant task.

## When to Run
- After multi-file changes
- After new feature implementation
- After payment/auth/security-related changes
- After database schema changes
- Before saying "done" to {USER_NAME}

---

## Skill Bindings

| Skill | Covers | Owner |
|---|---|---|
| `code-review` | §1 Variables, §10 Edge cases, general correctness | Cato |
| `simplify` | Duplication, over-engineering, reuse — quality only, finds no bugs | Sage |
| `security-review` | §2 Security, §3 Data isolation — see [40](./40-security-protocol.md) | Cipher |
| *(none — by hand)* | §7b Design — see [20](./20-design-protocol.md) | Vera |

Run the skills first, then walk the checklist below for what they cannot know:
the **stack-specific** items — payment callbacks (§5), framework upload methods (§4),
controller→view contracts (§8), route group conventions (§9). A generic reviewer has
no idea that this project CSRF-exempts exactly one route on purpose.

Every skill finding is confirmed in the code before it reaches {USER_NAME}.
Effort levels: `low`/`medium` for a routine diff, `high`+ when the change touches
money, auth, or tenant boundaries. `/code-review ultra` is {USER_NAME}'s to launch.

---

## Checklist

### 1. Variables & Types
- [ ] All variables initialized before use
- [ ] No undefined variable warnings
- [ ] Type definitions updated (if using TypeScript)

### 2. Security
- [ ] No SQL injection (use parameterized queries or ORM)
- [ ] No mass assignment vulnerability (use allowlists)
- [ ] CSRF exempted ONLY for payment/webhook callbacks
- [ ] File uploads validated (type, size)
- [ ] No sensitive data exposed to frontend (passwords, secrets, tokens)
- [ ] Auth middleware on all protected routes

### 2b. Privilege Escalation (any RBAC / user-management surface)
- [ ] No blanket superuser bypass — no `is_admin` flag, no wildcard grant, no `Gate::before` that returns true for everything
- [ ] `Gate::before` (or equivalent) never answers a **model-bound** check — those must reach the policy, or ownership/tenant scoping is bypassable
- [ ] **Grant ceiling**: a user cannot assign a role, or author a role, carrying permissions they do not hold themselves
- [ ] Ask per permission: *what is the maximum privilege reachable from this one alone?* — `staff.create` plus unguarded role assignment is full compromise
- [ ] Permission lists validated against a code-side registry, not just "exists in table"
- [ ] Privilege columns (`status`, `is_system`, role ids) not mass-assignable from request data

### 3. Data Isolation (Multi-User / Multi-Tenant)
- [ ] Queries scoped by user/tenant/owner ID
- [ ] No cross-user data leaks in show/edit/delete routes
- [ ] Authorization check: user owns the resource before update/delete
- [ ] Every new tenant-owned model actually carries the scoping trait — nothing enforces it
- [ ] Reads may fall back unscoped; **writes must fail closed** when no tenant is bound
- [ ] A foreign record returns **404, not 403** — a 403 confirms it exists
- [ ] Blast radius: suspending/deleting one tenant leaves the others serving 200
- [ ] With two or more auth guards, every `$request->user()` and bare `auth` names its guard

### 4. File Uploads (if applicable)
- [ ] Using correct upload method for framework
- [ ] Old file deleted on re-upload
- [ ] Storage accessible (symlinks, permissions)
- [ ] Using relative paths (not hardcoded URLs)

### 5. Payment Integration (if applicable)
- [ ] Callback route CSRF-exempted
- [ ] Return route handles cross-site POST (session loss)
- [ ] Status only set to paid/active AFTER payment confirmation
- [ ] Transaction ID stored
- [ ] Duplicate payment prevention

### 6. Database
- [ ] Timestamp columns nullable (strict mode)
- [ ] No reserved table names (avoid framework conflicts)
- [ ] Foreign keys have proper `onDelete` behavior
- [ ] New columns have defaults or are nullable
- [ ] Migration is reversible

### 7. Frontend — Function (if applicable)
- [ ] Forms work for both create AND edit
- [ ] Flash/toast messages display (success + error)
- [ ] Loading states on submit buttons
- [ ] Mobile responsive (no overflow, no hidden content)

### 7b. Frontend — Design (any user-facing screen) — owner: Vera
Full rules in [20](./20-design-protocol.md). Walk this whenever a screen changed.

**Against intent**
- [ ] Screen matches its approved Screen Brief — density class, primary action, states
- [ ] Any deviation was raised with {USER_NAME}, not absorbed silently
- [ ] Screenshot taken at 1280 and 390 and actually looked at

**The tells** (§2 of [20](./20-design-protocol.md) — the short form)
- [ ] Not everything is a card; separation is borders/hairlines, shadow only on things that float
- [ ] One accent colour on the primary action only; red/amber/green mean state, not decoration
- [ ] No untouched default palette, no gradient, no glassmorphism, no hero padding in a console
- [ ] No placeholder content survived — no John Doe, no lorem, no invented chart values
- [ ] No ▲ +12.5% badge on a number nobody computed
- [ ] Labels use the **domain's own nouns** from the schema, not generic ones (the loudest tell)
- [ ] Copy sounds like the person doing the job — "No orders yet this month", not "No data available"
- [ ] No emoji as icons; one icon set only

**Real data**
- [ ] Empty, loading, error and permission-denied states exist and are reachable
- [ ] Tested with the widest realistic value — longest name, biggest amount, deepest level
- [ ] Numbers right-aligned, tabular, fixed decimals; currency in the header not every cell; IDs monospace
- [ ] Dates use one format across the page

**Template fidelity**
- [ ] Uses the template's own components and SCSS variables — nothing hand-rolled that it already provides
- [ ] Overrides are central, not per-page utility classes fighting the template

**Keyboard**
- [ ] Visible focus ring, tab order matches visual order, Enter submits

### 8. Controller → View Data
- [ ] Controller passes ALL data the view/component uses
- [ ] No missing prop causing crash or blank page
- [ ] Pagination data included if using paginated queries

### 9. Routes
- [ ] New routes added to correct group
- [ ] Middleware applied (auth, role, subscription)
- [ ] Route names consistent with existing convention
- [ ] No duplicate route names or URIs

### 10. Edge Cases
- [ ] Empty state handled (no data yet)
- [ ] Deleted parent doesn't crash child queries
- [ ] Concurrent access handled (lock for update on stock/balance)
- [ ] Soft-deleted records excluded from active lists

---

## Quick Scan (3-Second Check)
For small changes, at minimum verify:
1. **Will it crash?** — Missing data, undefined vars, null references
2. **Is it safe?** — Auth check, data scoping, no injection
3. **Does it match?** — Existing code style, naming convention, UI pattern

---

## Stack-Specific Extras

### Laravel + Blade
Walked in full on *Basic Custom E-Commerce* (2026-08-27); every item below caught something
real or guards something that did.

- [ ] `@csrf` in every form; `@method('PUT'|'PATCH'|'DELETE')` on non-POST submits
- [ ] `old()` on every input, so a validation bounce does not wipe the form
- [ ] **No `env()` outside `config/`** — after `config:cache` it returns null, in production only
- [ ] `$fillable` on every model; **never `$guarded = []`**. Money, totals and statuses stay out
      of `$fillable` and are set explicitly in code
- [ ] Any request field that is validated but is *not* a model attribute is excluded before
      `new Model($request->validated())` — otherwise strict mode throws
- [ ] No `{!! !!}` outside a reviewed allow-list
- [ ] `Model::shouldBeStrict()` enabled outside production
- [ ] Guarded writes use the query builder and check the affected row count; **never**
      `$model->decrement()` on a loaded instance
- [ ] `getRouteKeyName()` overrides pinned per-route (`{model:id}`) wherever a slug would leak
      into admin URLs
- [ ] Nested route params named after the **relation** (`{variant}` → `variants()`), since a
      custom key enables scoped bindings
- [ ] View composers registered for every namespace that renders the shared variable, not just
      `layouts.*`
- [ ] Components used by error views tolerate a missing `$errors` — an unmatched URL never
      passes through the `web` group, so a naive component turns every 404 into a 500
- [ ] Closures in `DB::transaction()` capture every variable they use in `use (...)`
- [ ] CSRF exclusion list asserted **exactly**, not by "contains". Laravel 11+ keeps
      `validateCsrfTokens(except:)` in the static `$neverVerify`, not the instance `$except`
- [ ] `Http::fake()` called once per URL pattern per test; closure stubs where the response
      depends on state created later
- [ ] Guard suites re-run against the real DB engine, not only SQLite
