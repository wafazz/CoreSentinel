# Controlled Self-Evolution (CSE) Protocol

> **Governed, Versioned & Evidence-Backed AI Evolution**  
> AI agents are prohibited from autonomously altering core governance, security, or identity rules. All rule changes require a formal Controlled Evolution Proposal.

---

## 🔒 Governance Prohibition Rules
1. **No Autonomous Rule Mutations**: An AI agent cannot unilaterally modify system rules or security parameters without human/lead review.
2. **Mandatory Evidence & Impact Analysis**: Every rule addition must present empirical session evidence and risk assessment.
3. **Versioned Release**: Approved changes receive version increments (e.g. `v1.1.0`) and pass regression checks before deployment.

---

## 🗺️ Controlled Evolution Pipeline

```text
  AI Proposes Improvement ➔ Evidence Collection ➔ Impact Analysis ➔ Human Review ➔ Approval ➔ Versioned Change ➔ Regression Test ➔ Deploy
```

---

## 🔬 From Observation to Candidate

An observation is not a lesson, and a lesson is not a rule. The gap is deliberate: a system
that turns every incident straight into governance produces a rulebook nobody reads and a
review queue nobody reads either — and a reviewer who rubber-stamps has stopped being a control.

```bash
coresentinel evolve observe        # derive candidates from what is already recorded
coresentinel evolve candidates     # the queue, by status
```

Three sources, all of them things somebody already wrote down:

| Source | Signal |
| :--- | :--- |
| **Incidents** | A resolved incident's `learning` field |
| **Failures** | The failures memory layer — a fact there is a mistake that happened |
| **Patterns** | A pattern whose occurrence count has risen |

Nothing reads code and infers a lesson. An observer that invents rules from source it does
not understand produces governance nobody agreed to.

### The evidence threshold

A candidate needs **2 distinct sources** before it may be proposed. One incident is an
anecdote; the second is what makes it worth a rule.

- The same source **cannot corroborate itself** — a single noisy incident must not argue its
  way into the rulebook.
- Re-running the observer **never inflates evidence**. It is idempotent by construction.
- A **rejected candidate stays rejected**. Resurfacing a declined lesson on every run is how
  a review queue becomes noise, and noise is how a control stops working.

```bash
coresentinel evolve reject CAND-8efb2da38b --reason "already covered by AP-002"
coresentinel evolve promote CAND-8efb2da38b --reason "obvious enough not to need repeating"
```

`promote` is the escape hatch for a lesson too obvious to wait for. It requires a stated
reason, so the shortcut is visible in the record.

---

## ✅ Approval, and then Application

These are **two separate acts**, and the separation is the point.

`approve` records a human decision and changes no file. Until v10.9 it printed *"Versioned
Change Released"* while writing nothing — the pipeline stopped one step short of doing
anything, and said otherwise.

```bash
coresentinel evolve apply EVO-014      # refused: PENDING_REVIEW, not APPROVED
coresentinel evolve approve EVO-014 --approver "Fakrul"
coresentinel evolve apply EVO-014      # now it happens
coresentinel evolve revert EVO-014     # and it is undone, byte for byte
```

`apply` does five things, in order, and skips none:

1. **The proposal must be `APPROVED`.** An evolution is applied by a human decision, never by
   reaching the end of a pipeline.
2. **The change must be one CoreSentinel knows how to make safely.** Anything else is
   *refused, not attempted* — blindly patching a governance file because a proposal asked
   nicely is the failure this protocol exists to prevent.
3. **The target is snapshotted**, byte for byte.
4. **The change is written** and the registry version bumped.
5. **The result is audited.**

| Target | Change it can make |
| :--- | :--- |
| `anti-patterns.json` | Add a rule |
| `11-pattern-library.md` | Append a pattern in the documented capture format |
| `55-self-evolution.md` | Append an anti-pattern entry |

A newly applied rule is recorded at **`WARNING`**, never `STRICT_BLOCK`. Promotion to blocking
is its own decision, made once the rule has proved itself. Each rule records the proposal and
evidence it came from.

`revert` restores the snapshot **byte-identically**. Every evolution is reversible, which is
what makes approving one a decision rather than a commitment.

---

## ⚡ CLI Commands

```bash
# Observe, and inspect the candidate queue
coresentinel evolve observe
coresentinel evolve candidates
coresentinel evolve reject CAND-abc123 --reason "..."
coresentinel evolve promote CAND-abc123 --reason "..."

# Register a Controlled Self-Evolution Proposal
coresentinel evolve propose \
  --target "anti-patterns.json" \
  --change "Flag repeated relationship queries inside a loop" \
  --evidence "INC-0001, INC-0002" \
  --candidate CAND-abc123 \
  --impact "Low risk; adds a review check"

# List all evolution proposals and review status
coresentinel evolve list

# Approve (a human act), then apply (a separate one), then undo if needed
coresentinel evolve approve EVO-014 --approver "Fakrul"
coresentinel evolve apply   EVO-014
coresentinel evolve revert  EVO-014
```

## Self-Reflection Template
After significant work, Iris asks itself:
1. Did I discover a new pattern worth remembering?
2. Did I make a mistake I should prevent in the future?
3. Is there a rule I should update based on this experience?
4. Can anything I learned here help other projects?

## Evolution Log
Track all self-improvements with version history.

| Date | Type | What Changed | Trigger | Applied To |
|------|------|-------------|---------|------------|
| 2026-07-21 | Anti-Pattern | Never trust a native exe's exit code when sourcing SQL — grep stdout for `ERROR` | Reported "failures: 0" on a migration run that had actually failed | All projects (PowerShell) |
| 2026-07-21 | Anti-Pattern | A grep that finds nothing is not proof of absence — state the scan scope with the claim | Declared "zero MySQL-8-only DDL" after a scan that omitted implicit TIMESTAMP defaults | All projects |
| 2026-07-21 | Skill | Verify class autoloading empirically (throw/catch probe) instead of reasoning about PSR-4 | Confirmed a real `Exceptions.php` autoload bug in DAISY | All PHP projects |
| 2026-07-21 | Skill | XAMPP local-setup recipe for no-framework PHP (port vhost, DocumentRoot at `public/`) | Stood up DAISY without admin elevation | All PHP projects |
| 2026-07-21 | Skill | Check the test bootstrap for `.env` fallback BEFORE running a suite | `tests/bootstrap.php` would have migrated over the dev DB | All projects with test suites |
| 2026-07-21 | Skill | `--ignore-platform-req` to install deps without mutating a tracked `composer.lock` | Lock file demanded PHP 8.3, local was 8.2, no edits authorised | All Composer projects |
| 2026-07-21 | Add Rule | Recorded PowerShell 5.1 `Invoke-WebRequest` byte[] `.Content` gotcha in identity Environment | `.Trim()` failed on a signature check | All projects (PowerShell) |
| 2026-07-21 | Add Skill | `explicit_defaults_for_timestamp=ON` as the MySQL 8 ↔ MariaDB compatibility lever | Migration 019 failed only on MariaDB | All MySQL/MariaDB projects |
| 2026-07-22 | Anti-Pattern | Zero-fill a day series in the DB's timezone frame (anchor to `CURDATE()`), never with PHP `date()` while the buckets come from SQL `DATE()` | Analytics sparkline's newest bar mapped to a day SQL never emitted (UTC vs Asia/KL) — caught in Phase 5 review before ship | All time-series across a PHP↔DB boundary |
| 2026-07-22 | Skill | Calendar-align the headline window to the plotted series so headline == sum(series); floor `AVG(TIMESTAMPDIFF(...))` with `resolved_at >= created_at` | Building the DAISY analytics KPI dashboard | All dashboards |
| 2026-07-23 | Anti-Pattern | A test that writes to a shared table NOT in the global truncate list leaks state into sibling tests — truncate it in the test's own setUp | BillingTest asserted total 99.00 but got 119.00; a prior test's add-on row survived into `tenant_features` | All projects with a shared test DB |
| 2026-07-23 | Anti-Pattern | Under `hx-boost` or a nav-skeleton overlay, download & standalone-page links MUST opt out (`download`, `hx-boost="false"`, `target="_blank"`) or the page shell breaks | {USER_NAME}: PDF button left the platform page stuck on skeleton until refresh | All boosted/SPA-ish layouts |
| 2026-07-23 | Skill | Embed images as base64 data-URIs so they render identically in the HTML view AND mPDF; verify the PDF via `Output('', STRING_RETURN)` + `%PDF` header check | Company logo on invoice view + PDF | All mPDF / dual HTML+PDF renders |
| 2026-07-23 | Skill | Safe global CSS default: count usages first, then scope with `:not(:has(...))` guards and let inline-style specificity win, so existing markup can't regress | Default `.card` body padding across 171 cards (111 with headers) | All shared CSS component classes |
| 2026-07-23 | Skill | Snapshot financial values (tax/price) onto the invoice row at generation; render branding (logo/company) live | DAISY invoices | All billing/invoicing |
| 2026-08-04 | Update Rule | **Corrects the 2026-07-21 rule.** "Grep stdout for ERROR" is NOT enough — `mysql.exe` writes errors to **stderr**. Capturing only stdout reported a clean run on a migration that had crashed | Reported "no ERROR string in output" while 144 stderr error lines existed | All projects, all shells |
| 2026-08-04 | Anti-Pattern | A wedged `ALTER TABLE` holds the table's metadata lock forever; `KILL` leaves it "Killed/Committing alter table" and graceful shutdown hangs — only a force-kill + restart clears it | Migration 029 wedged `voice_calls` in DAISY dev | All MySQL/MariaDB projects |
| 2026-08-04 | Skill | Verify a migration by querying `information_schema` for EVERY object it should create, not by reading the client's output at all | Proved all 16 objects of migration 029 landed after a partial-crash + re-run | All projects with SQL migrations |
| 2026-08-04 | Anti-Pattern | `Glob("dir*")` does NOT look inside `dir/` — never conclude "the file doesn't exist" from a pattern that couldn't have matched it | Told {USER_NAME} `app/Exceptions*` was absent; the file existed one level down | All projects |
| 2026-08-04 | Anti-Pattern | PowerShell 5.1 `Set-Content -Encoding utf8` writes a **BOM**, which breaks `<?php`, shebangs, YAML and JSON | 7 test files fataled with "Namespace declaration has to be the very first statement" | All projects on Windows |
| 2026-08-04 | Skill | A green suite proves nothing if the tests `require_once` what production expects to autoload — grep for setup workarounds when a bug "should" be caught by tests | 8 test files hid the ForbiddenException autoload bug for months | All projects |
| 2026-08-04 | Anti-Pattern | `php -S` is single-threaded and `PHP_CLI_SERVER_WORKERS` is **POSIX-only** — silently ignored on Windows. Never use it for an app with SSE/long-poll | Whole DAISY UI appeared frozen; one SSE call blocked everything for 55s | All PHP projects on Windows |
| 2026-08-04 | Skill | "Links dead on left-click but fine via right-click → open in new tab" = JS is intercepting the click (hx-boost/SPA) and its request never returns — look at server concurrency, not the markup | Diagnosed the frozen DAISY UI from this one symptom | All boosted/SPA-ish apps |
| 2026-08-04 | Skill | **When a vendor's docs are silent, read the vendor's own SDK source.** Pull the tarball from `registry.npmjs.org` (no `npm install`, no auth) and grep its URI-constants / request-builder files | NICE documents no verbs or response shapes; `@nice-devone/core-sdk` listed every Agent API path, confirmed POST, and named the response key | All third-party API integrations |
| 2026-08-04 | Anti-Pattern | **Auth succeeding proves only that the credential is valid — never that the account can do the job.** After a token exchange, assert the *identity* in the token and the entitlements attached to it | Channel authenticated fine on a CXone key belonging to an agent who lacked the skill needed to be routed the call; looked configured, could never ring | All API integrations with per-user credentials |
| 2026-08-04 | Anti-Pattern | **Three strikes on blind-probing an API for a magic value, then go capture the real client's traffic.** Enumerating plausible values against a production endpoint burns time and writes to a live system | 11 candidate station values all returned the same 400; the answer is one DevTools capture of the vendor's own web app | All undocumented API parameters |
| 2026-08-04 | Anti-Pattern | Git-bash `tar` on PATH reads `-C C:\...` as a remote host ("Cannot connect to C: resolve failed") — call `C:\Windows\System32\tar.exe` explicitly, or `cd` first | Extracting npm tarballs on Windows | All projects on Windows |
| 2026-08-10 | Anti-Pattern | Never interpolate a Windows path into a `sed` replacement — GNU sed reads `\U` as "uppercase the rest of the line" and eats the other backslashes. Escape `\ & |` first | AutomationSentinel's `install.sh` rendered `C:\Users\FAKRUL~1.HAK\...` as `C:SERSFAKRUL~1.HAKAPPDATAocaltemp...` in 5 of 6 installed protocol files | All shell templating on Windows |
| 2026-08-10 | Anti-Pattern | `$HOME/Desktop` does not exist when Windows redirects the Desktop into OneDrive — a bash installer probing it silently finds nothing while its PowerShell twin works | Bare `./install.sh` could never locate `memorycore.conf` on this machine; `install.ps1` did, via `[Environment]::GetFolderPath('Desktop')` | All cross-shell installers on Windows |
| 2026-08-10 | Skill | Prove a "never overwrites" installer claim by hashing a user-edited file across a re-run, then running the `--force` path and asserting the **opposite** — same assertion, inverted expectation, so the guard test can't be a tautology | Verifying AutomationSentinel's installers | All installers / scaffolding scripts |
| 2026-08-10 | Skill | Explicitly align agent identity ('Iris') across MemoryCore and project session-memory.md context | Prompted by single-keyword trigger ('Iris'); resolved by reading central MemoryCore profile and writing context | All projects |

## Learned Skills
Track techniques and patterns learned across all projects.

### Skill: Read the vendor's SDK source when the vendor's docs are silent
- **Learned from**: DAISY 2.0 (NICE CXone)
- **Pattern**: When integrating against an API whose docs list paths but not verbs, response
  shapes, or magic values, fetch the vendor's official client library and read it:
  `Invoke-RestMethod https://registry.npmjs.org/@scope/pkg` → `.versions.<latest>.dist.tarball`
  → download → extract with `C:\Windows\System32\tar.exe` (NOT git-bash's `tar`). Then grep for
  a `*-constants.js` / `*-apis.js` file — vendors almost always centralise every endpoint in one —
  and for the service that builds the request. No `npm install`, no auth, no node_modules.
- **Why**: NICE's published docs gave paths only; their own `core-sdk` gave every path, the
  confirmed HTTP verb, the response key, and an undocumented settings endpoint that turned out to
  carry the entire WebRTC configuration. It converted four "unverified assumption" comments into
  facts in about ten minutes, and confirmed the hand-written paths were already correct.
- **Also**: `.d.ts` files are the cleanest form of the request/response contract you'll find.
- **Applied to**: All third-party API integrations

### Anti-Pattern hint (paired): don't confuse authentication with authorisation
- A credential that authenticates is not a credential that can *do the task*. Read the identity
  out of the returned token (`id_token` claims) and query that identity's entitlements — skills,
  permissions, licensed features — before concluding an integration is configured correctly.

### Skill: Prove class autoloading, don't reason about it
- **Learned from**: DAISY 2.0
- **Pattern**: To test whether a class actually resolves, run a throwaway script that does
  `try { throw new \Some\Class('x'); } catch (\Some\Class $e) {...} catch (\Throwable $e) {...}`.
  If it lands in the `Throwable` branch as `Error: Class not found`, autoloading is broken.
- **Why**: PSR-4 reasoning is easy to get wrong (multiple classes in one file, classmap
  optimisation, `catch` clauses that never trigger autoload). One 6-line probe is definitive
  where a paragraph of reasoning is a guess. This found a real bug that had shipped for months.
- **Applied to**: All PHP projects

### Skill: Read the test bootstrap before running any suite
- **Learned from**: DAISY 2.0
- **Pattern**: Open `tests/bootstrap.php` (or equivalent) and check how it picks its database
  BEFORE the first run. Look for `file_exists('.env.test') ? '.env.test' : '.env'` fallbacks
  and for any migration/truncate the bootstrap performs.
- **Why**: DAISY's bootstrap silently falls back to `.env` and then runs every migration.
  Running the suite without `.env.test` present would have rewritten the dev database.
- **Applied to**: All projects with a test suite

### Skill: Install dependencies without mutating a tracked lock file
- **Learned from**: DAISY 2.0
- **Pattern**: When `composer install` fails on a platform requirement and you are not
  authorised to edit files, use `--ignore-platform-req=<req>` (e.g. `php-64bit`) rather than
  `composer update`, which rewrites `composer.lock`.
- **Why**: Keeps the working tree clean and preserves the evidence of the underlying defect
  instead of silently papering over it.
- **Applied to**: All Composer projects

### Skill: MySQL 8 ↔ MariaDB TIMESTAMP compatibility
- **Learned from**: DAISY 2.0
- **Pattern**: `col TIMESTAMP NOT NULL` with no `DEFAULT` gets an implicit
  `DEFAULT '0000-00-00 00:00:00'` when it is not the first TIMESTAMP column. MySQL 8 defaults
  `explicit_defaults_for_timestamp=ON` so this is harmless; MariaDB defaults it OFF, so with
  `NO_ZERO_DATE` in `sql_mode` the CREATE fails with error 1067.
- **Why**: The schema looks portable and passes a syntax scan, but silently loses a table.
  Durable fix is `DEFAULT CURRENT_TIMESTAMP` in the DDL; server-side lever is
  `explicit_defaults_for_timestamp=ON`.
- **Applied to**: All MySQL/MariaDB projects

### Skill: Local vhost without admin elevation
- **Learned from**: DAISY 2.0
- **Pattern**: The hosts file needs elevation; a port-based vhost does not. Add
  `Listen 8080` + `<VirtualHost *:8080>` to `httpd-vhosts.conf` and use `http://localhost:8080`.
  Point `DocumentRoot` at the app's `public/`, never the project root, so `.env`, `app/` and
  `config/` are unreachable over HTTP even if a rewrite rule is missing.
- **Why**: Avoids a blocked elevation prompt mid-setup, and is the safer docroot regardless.
- **Applied to**: All PHP projects on XAMPP/Laragon

### Skill: Separate verified from secondhand when reporting
- **Learned from**: DAISY 2.0
- **Pattern**: When part of an analysis came from subagents and part from files read directly,
  say which is which before drawing conclusions from it.
- **Why**: {USER_NAME} asked "do you know the full flow?" — the honest answer was "structure yes,
  runtime no", and admitting that led straight to discovering the dead webhook consumer.
  Claiming full knowledge would have buried the most important finding in the project.
- **Applied to**: All projects

### Skill: One HTML document for both the web view and the PDF (mPDF + data-URIs)
- **Learned from**: DAISY 2.0 (invoices)
- **Pattern**: Build a single renderer that returns one self-contained HTML fragment (own inline
  `<style>`), and feed the SAME string to the on-screen view and to mPDF. Embed images (logos) as
  base64 `data:image/...` URIs so nothing has to fetch a file or URL — they render identically in
  the browser and in the PDF. Verify the PDF path with a throwaway smoke script:
  `$pdf = $mpdf->Output('', \Mpdf\Output\Destination::STRING_RETURN);` then assert
  `substr($pdf,0,4) === '%PDF'` and that the expected bytes/length are present.
- **Why**: The view and the PDF can never drift, and data-URIs sidestep mPDF's finicky file/URL
  image fetching (and its temp-dir/permissions surprises on deploy). The smoke test proves mPDF
  actually produced a valid document instead of throwing.
- **Applied to**: All projects rendering the same content as HTML and PDF

### Skill: Change a shared CSS class safely (audit → scope with :has → let inline win)
- **Learned from**: DAISY 2.0 (default `.card` padding)
- **Pattern**: Before adding a rule to a class used everywhere, COUNT the usages and the variants
  (`class="card"` = 171, `card-header` = 111, many with inline `padding`). Then scope the new rule so
  it only touches the safe subset — `.card:not(:has(.card-header)):not(:has(.card-body)):not(:has(table))`
  — and rely on inline-style specificity (1,0,0,0) beating the stylesheet, so any element that already
  sets the property is untouched. `:has()` was already used in the codebase, which confirmed support.
- **Why**: A blanket `.card { padding }` would have broken 111 header dividers and double-padded dozens
  of cards. The scoped rule fixes the real pain (flush content) with near-zero regression surface.
- **Applied to**: All shared design-system component classes

### Skill: Snapshot money, render branding live
- **Learned from**: DAISY 2.0 (billing)
- **Pattern**: Persist the applied tax/price ONTO the invoice row (`tax_label`, `tax_rate`,
  `tax_amount`, `total`) at generation time so a later rate change never rewrites history. But resolve
  cosmetic issuer branding (company name, logo) at RENDER time so a logo update flows to every invoice.
  Distinguish "financial truth" (snapshot) from "presentation" (live).
- **Why**: Historical invoices must stay legally/accounting-correct; branding is expected to update.
  Conflating the two either corrupts old totals or freezes stale logos.
- **Applied to**: All billing/invoicing/quoting systems

## Anti-Patterns
Track mistakes to never repeat.

### Anti-Pattern: Trusting a native exe's exit code instead of reading its output
- **What happened**: Ran 28 SQL migrations in a PowerShell loop checking `$LASTEXITCODE`, and
  reported **"failures: 0"** to {USER_NAME}. `mysql.exe` had returned 0 while migration 019 failed
  with error 1067. A table was silently missing; only the test suite caught it later.
- **Impact**: Gave a confidently wrong all-clear. Had to retract it. Worse, if the suite had
  not happened to cover that table, a broken schema would have been signed off as good.
- **Rule**: For native executables — especially `mysql`, `psql`, `mysqldump` — capture stdout
  and **grep it for `ERROR`**. Never report success on exit code alone. Verify the intended
  end state directly (`SELECT COUNT(*) FROM information_schema.tables`), not the process code.
- **Applies to**: All projects, all shells

### Anti-Pattern: Grepping only stdout for `ERROR` (supersedes the 2026-07-21 rule)
- **What happened**: Applied migration 029 with
  `$out = & mysql.exe ... | Out-String`, then grepped `$out` for `ERROR` — exactly what the
  2026-07-21 rule prescribed. It printed **"no ERROR string in output"** and `exit=0`.
  The tool's own captured output held **144 lines** of
  `ERROR 2013/2006 ... Lost connection / MySQL server has gone away`. The pipe captured
  **stdout only**; `mysql.exe` writes every error to **stderr**.
- **Impact**: Declared a migration clean when it had died a third of the way through, leaving
  `voice_calls` half-altered and its metadata lock wedged. The old rule *felt* satisfied,
  which is what made it dangerous — a guard that silently checks the wrong stream is worse
  than no guard, because it manufactures confidence.
- **Rule**: Never let a shell variable be the evidence. Either (a) run the client WITHOUT
  redirecting, so the harness surfaces stdout **and** stderr and you read it yourself, or
  (b) merge streams explicitly. Then — always — **verify the end state directly**: query
  `information_schema.COLUMNS` / `.STATISTICS` for every object the migration should have
  created and assert each one. Output is a hint; schema state is the fact.
- **Applies to**: All projects, all shells, every native CLI (`mysql`, `psql`, `mysqldump`)

### Anti-Pattern: Assuming a hung `ALTER TABLE` will resolve, or that KILL clears it
- **What happened**: An `ALTER TABLE voice_calls ADD COLUMN` hung. `KILL <id>` left the thread
  in `Killed / Committing alter table to storage engine` — still holding the table's metadata
  lock. Every later query on that table queued behind it, `mysqladmin shutdown` returned rc=0
  but the process never exited, and the server stopped accepting new connections (so a
  safety `mysqldump` was no longer possible).
- **Impact**: Burned ~20 minutes and forced a force-kill of the user's shared dev database.
  The backup I wanted to take became impossible *because I waited too long to take it*.
- **Rule**: Take the backup BEFORE the risky DDL, not after it goes wrong. If a thread sits in
  `Committing alter table` after a KILL, stop waiting — it will not clear. Force-kill the
  process and restart; InnoDB is crash-safe and recovers. Also: read the error log at
  startup — if the instance *already* began with "Starting crash recovery", treat it as
  degraded and suspect the server before suspecting your SQL.
- **Applies to**: All MySQL/MariaDB projects

### Anti-Pattern: `php -S` for an app with SSE / long-polling (fatal on Windows)
- **What happened**: Served DAISY with `php -S` and set `PHP_CLI_SERVER_WORKERS=4`, believing
  that gave 4 workers. **That variable is POSIX-only — PHP ignores it on Windows** (it needs
  `fork()`). The server stayed single-threaded. Every page opens an `EventSource` to
  `/api/v1/events` which holds the one worker for its 55s window, so every other request queued
  behind it. {USER_NAME} reported the whole UI as unclickable.
- **Impact**: Looked exactly like a frontend bug. I nearly went hunting for a JS/overlay fault.
  Measured proof: page load **69.5s** with one SSE connection open vs **0.09s** once it closed;
  **0.09s** on Apache under the same conditions.
- **Rule**: If an app has SSE, WebSockets, or long-poll, do not use the PHP built-in server at
  all — use Apache/nginx. Never assume a concurrency flag took effect; **measure it**: hold the
  streaming endpoint open in one process and time an ordinary request in another. Carrying a
  tip from notes without checking it applies to the current OS is how this got in.
- **Applies to**: All PHP projects, especially on Windows

### Skill: Read "dead on click, works via right-click → new tab" as a concurrency symptom
- **Pattern**: If a left-click does nothing but right-click → *Open in new tab* works, the
  pointer IS hitting the element — so it is not an overlay or z-index problem. Something in JS
  (`hx-boost`, a router, an SPA click handler) is calling `preventDefault()` and then its
  request never completes. Right-click bypasses JS entirely, which is why it works.
- **Why**: This single observation splits the search space cleanly: it rules out CSS/overlay
  causes and points at the network/server layer. In DAISY it led straight to the single-threaded
  dev server rather than to the markup.
- **Applies to**: All HTMX-boosted / SPA-ish apps

### Anti-Pattern: Concluding "it doesn't exist" from a search that could not have found it
- **What happened**: Ran `Glob("app/Exceptions*")`, got no results, and told {USER_NAME} the
  directory was "absent entirely" — then wrote that into session memory AND the project
  profile. `app/Exceptions/Exceptions.php` existed the whole time; the pattern matched only
  entries named `Exceptions*` **at that level**, never inside the directory.
- **Impact**: A confidently stated, recorded-in-two-places false fact about the user's
  codebase. It also nearly produced the wrong fix (create the classes from scratch) instead of
  the right one (split an existing multi-class file).
- **Rule**: Before reporting absence, use a pattern that *could* find the thing —
  `**/Exceptions*` or a content grep for `class ForbiddenException`. Better: when the question
  is "does this class exist", grep for its **definition**, not its path. And when a later
  finding contradicts an earlier claim, correct the claim explicitly — including in any
  memory file where it was recorded.
- **Applies to**: All projects

### Anti-Pattern: `Set-Content -Encoding utf8` on Windows PowerShell 5.1 (writes a BOM)
- **What happened**: Stripped a line from 7 PHP test files with
  `Set-Content -Encoding utf8`. PS 5.1 writes UTF-8 **with BOM**, so every file gained
  `EF BB BF` before `<?php`. The whole suite died with
  *"Namespace declaration statement has to be the very first statement"*.
- **Impact**: Turned a clean 3-line cleanup into a broken test suite; the error message points
  at the namespace line and says nothing about encoding, so it reads as a syntax bug.
- **Rule**: For any file a parser reads (PHP, JSON, YAML, shell, `.env`), write with
  `[System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))`.
  Verify with a byte check — first bytes must be the real content, not `239,187,191`.
  In PS 7+, `-Encoding utf8NoBOM` exists; in 5.1 it does not.
- **Applies to**: All projects on Windows

### Anti-Pattern: Trusting a green suite when the tests work around the bug
- **What happened**: `RBAC::require()` fataled at runtime because `App\Exceptions\*` never
  autoloaded — yet 4 tests asserted `expectException(ForbiddenException::class)` and passed.
  Eight test files carried `require_once BASE_PATH.'/app/Exceptions/Exceptions.php'` in
  `setUp()`, manually loading what production expected PSR-4 to load. One even had a comment
  naming the defect. The suite was green for months while the feature was broken in prod.
- **Impact**: The test suite actively concealed a security-relevant bug (permission denials
  crashing instead of returning 403).
- **Rule**: When a bug "should" have been caught by tests but wasn't, grep the tests for
  `require_once`/`include` of application code and for manual bootstrapping in `setUp()`.
  A workaround in test setup is a bug report in disguise. Fix the root cause and **delete the
  workaround** — otherwise the next regression hides in the same place.
- **Applies to**: All projects with a test suite

### Anti-Pattern: Treating an empty grep as proof of absence
- **What happened**: Scanned migrations for `utf8mb4_0900`, `SKIP LOCKED`, `CHECK(`,
  `GENERATED ALWAYS`, found nothing, and told {USER_NAME} there was **"zero MySQL-8-only DDL"**.
  The scan never covered implicit TIMESTAMP defaults, which was the actual incompatibility.
- **Impact**: A confident compatibility all-clear that was wrong, given to a senior who was
  making a stack decision on it.
- **Rule**: A grep proves only what it searched for. Either state the scan scope alongside the
  claim ("no *collation or generated-column* issues found") or verify empirically by running
  the thing. Never let a targeted scan become a general guarantee.
- **Applies to**: All projects

### Anti-Pattern: Reasoning about autoloading instead of testing it
- **What happened**: Started constructing an argument about whether `catch` clauses trigger
  PSR-4 autoload, and how Composer's classmap optimiser treats multi-class files.
- **Impact**: Would have produced a hedged, possibly wrong answer about a real bug.
- **Rule**: When a question is cheaply testable, test it. A 6-line probe script beats a
  paragraph of inference — and it is the difference between "I think this is broken" and
  "this is broken, here is the error."
- **Applies to**: All projects

### Anti-Pattern: Zero-filling a day series with PHP dates while the buckets come from SQL
- **What happened**: An analytics dashboard ran its window filter and `GROUP BY DATE(created_at)` in MySQL, but generated the zero-fill series keys with PHP `date('Y-m-d', strtotime("-{$i} day"))`. MySQL commonly runs UTC while PHP was set to `Asia/Kuala_Lumpur` (UTC+8), so the two disagree on which calendar day "today" is — the newest sparkline bar mapped to a date the SQL `DATE()` never produced, misattributing today's activity every single day. The headline count (a raw range filter) stayed correct, so the chart silently disagreed with its own KPI number.
- **Impact**: Caught in Phase 5 (Cato) before ship, but would have shipped a dashboard whose trend line contradicted its headline — the kind of "looks fine in the demo" bug that erodes trust in the whole reporting surface.
- **Rule**: When zero-filling or day-bucketing a time series, generate the calendar in the SAME timezone frame as the aggregation. Anchor to the DB clock — `$today = SELECT CURDATE()`, then build the series backward from `$today` — or set the DB session TZ to match PHP. Never mix PHP `date()` day keys with SQL `DATE()` buckets. Bonus: calendar-align the headline window to the plotted range so `headline == sum(series)`, and floor duration averages (`resolved_at >= created_at`) so back-dated rows can't push an average negative.
- **Applies to**: All projects doing time-series aggregation across a PHP↔DB boundary

### Anti-Pattern: Running a test suite before checking which DB it targets
- **What happened**: Was one command away from running PHPUnit when `.env.test` did not exist.
  DAISY's bootstrap falls back to `.env` and then executes every migration.
- **Impact**: Would have run 28 migrations against the freshly-seeded **dev** database.
  Caught it by reading `tests/bootstrap.php` first — but only just.
- **Rule**: Before the first suite run on any unfamiliar project, read the bootstrap and
  confirm the test database is isolated. Assume nothing from the config file names.
- **Applies to**: All projects with a test suite

### Anti-Pattern: Test state leaking through a shared table the harness doesn't truncate
- **What happened**: `BillingTest` inserted a custom-module (`features` + `tenant_features`) in one test.
  The base `TestCase::truncateTables()` list didn't include those tables, so the add-on row survived into
  the next test, which then asserted an invoice total of 99.00 and got **119.00** (99 + the leaked 20 add-on).
- **Impact**: A confusing failure that looked like a bug in the code under test but was actually cross-test
  contamination. Cost a debug cycle to trace to setUp, not the assertion.
- **Rule**: When a test writes to a table that isn't in the global truncate list, truncate it in that
  test class's own `setUp()` (I added `tenant_features`, `tax_rates`, `platform_settings`, `features WHERE
  is_custom`). Each test must start from a known-empty state for EVERY table it touches — check the base
  harness's truncate list against the tables your test writes, and top it up locally.
- **Applies to**: All projects with a shared/reused test database

### Anti-Pattern: Download / standalone links break a boosted or skeleton-overlay layout
- **What happened**: The platform console shows a nav-skeleton overlay on any `<a>` click (assuming a page
  nav follows) and the tenant layout uses `<body hx-boost="true">`. A **PDF download** link triggers no
  navigation (Content-Disposition), so the skeleton overlay never cleared — the page sat blank until refresh;
  under `hx-boost` it also tried to AJAX-swap the binary PDF / a full standalone HTML page into the shell.
- **Impact**: {USER_NAME} hit a "stuck skeleton, must refresh" bug immediately after the PDF feature shipped.
- **Rule**: Any link that downloads a file or navigates to a full standalone document (not an app fragment)
  must opt out of the boost/skeleton machinery: add `download` (also satisfies skeleton-handler skip lists),
  `hx-boost="false"`, and for standalone pages `target="_blank"`. When a layout globally intercepts clicks,
  audit every non-fragment link for the opt-out.
- **Applies to**: All HTMX-boosted or click-intercepting (skeleton/SPA-ish) layouts

### Anti-Pattern: Interpolating a Windows path into a `sed` replacement
- **What happened**: AutomationSentinel's `install.sh` rendered its templates with
  `sed -e "s|{MEMORY_PATH}|$MEMORY_PATH|g"`. `MEMORY_PATH` in `memorycore.conf` is a
  Windows path, so the replacement contained `\U`, `\L`, `\A`, `\D`, `\f`, `\c`…
  GNU sed treats `\U` on the right-hand side of `s///` as **uppercase everything
  that follows** and simply drops the backslashes it doesn't recognise.
  `C:\Users\FAKRUL~1.HAK\AppData\Local\Temp\claude\...` came out as
  `C:SERSFAKRUL~1.HAKAPPDATAocaltempaudec--users-...` — wrong path *and* wrong case.
- **Impact**: 5 of 6 installed protocol files carried a dead cross-reference link.
  Silent: exit code 0, "6 written", no warning. The PowerShell installer was fine
  (`String.Replace` is literal), so it only broke for bash users — i.e. only sometimes.
- **Rule**: Escape the replacement before it reaches sed:
  `esc_repl() { printf '%s' "$1" | sed -e 's/[\&|]/\&/g'; }`
  and use a delimiter that isn't in the data. Better still, prefer a literal
  string-replace tool over sed when substituting untrusted/path-shaped values.
  Always assert on the **rendered output**, not on the installer's exit code.
- **Applies to**: All shell templating, all installers, anything on Windows

### Anti-Pattern: Probing `$HOME/Desktop` on Windows
- **What happened**: `install.sh` looked for `memorycore.conf` in
  `$HOME/MemoryCore` and `$HOME/Desktop/CORE`. Windows redirects this machine's
  Desktop into OneDrive, so `$HOME/Desktop` does not exist at all and bare
  `./install.sh` always died with "could not find memorycore.conf".
  `install.ps1` worked, because `[Environment]::GetFolderPath('Desktop')` resolves
  the redirect.
- **Impact**: The documented happy path (`./install.sh` with no arguments) was broken
  on the only machine it ships to, while its PowerShell twin passed — the kind of
  asymmetry that reads as "bash is fine, I tested it".
- **Rule**: Never hardcode `$HOME/Desktop` in a bash script on Windows. Glob the
  redirect: `"$HOME"/OneDrive*/Desktop/...`, and keep the plain path as a fallback.
  When two installers claim parity, run **both** — a passing twin proves nothing
  about the other.
- **Applies to**: All cross-shell installers on Windows

### Anti-Pattern: Reporting a service found by port-scanning instead of by reading the config
- **What happened**: At the Phase 1 gate I reported the dev database as **MariaDB 11.8.2 on
  port 3306**, having found a `mariadbd` listener with `lsof`. {USER_NAME}'s projects all point
  at **port 3307, MariaDB 10.4.28** — a different instance entirely. I only noticed when
  `mariadb -u root` on 3306 failed with access denied and I went looking at sibling `.env`
  files.
- **Impact**: A confidently wrong fact in a gate report a stack decision was made on. It
  mattered: on 10.4 `DB_CONNECTION=mariadb` is load-bearing (`renameColumn` emits syntax the
  engine does not have until 10.5.2), whereas on 11.8 it is merely preferred. Had I built to
  the reported version, the first `renameColumn` migration would have been a hard error.
- **Rule**: A listening socket is a machine fact, not a project fact. To learn which database
  a project uses, read a **sibling project's `.env`** — or the project's own — before running
  `lsof`. When both exist, say which one the projects actually target and why. Same shape as
  the "empty grep proves absence" anti-pattern: the tool answered a question I had not asked.
- **Applies to**: All projects, every environment report

### Anti-Pattern: Faking the channel that the dedupe guard reads
- **What happened**: Wrote `Notification::fake()` in a test asserting a budget warning fires
  **once per month**. The once-per-month guard is a query against the `notifications` table.
  Faking the channel stops the row being written, so the guard never saw its own prior send and
  the test reported 2 notifications. I nearly "fixed" working production code to satisfy it.
- **Impact**: Cost a debug cycle and almost produced a real regression in correct code.
- **Rule**: Before faking a facade, ask what the code under test **reads**. If the guard reads
  the same store the fake intercepts, the fake tests itself. Assert on the real rows instead
  (`$user->notifications()->where(...)->count()`). Fakes are for *outbound* effects you cannot
  observe; they are wrong for a mechanism whose evidence is persisted state.
- **Applies to**: All projects — `Notification::fake`, `Mail::fake`, `Bus::fake`, `Event::fake`

### Skill: Let the seeded demo disagree with the app, then find out why
- **Pattern**: After building, seed realistic demo data and read the app's own numbers back
  through a real request. "Today: 0.00" next to a week total that obviously included today was
  the only visible symptom of `APP_TIMEZONE` being ignored — no test caught it, because every
  test used one clock consistently.
- **Why**: A test suite proves internal consistency. Demo data crossing a real boundary (seed
  clock vs request clock, PHP vs DB) proves the boundary. Cross-check an invariant that must
  hold across the two — here, *the plotted series must sum to the headline*.
- **Applies to**: Any app with time-series or aggregate reporting

### Anti-Pattern: Trusting `update()` on a field that is not fillable
- **What happened**: See the Pattern Library entry *Privilege Columns Must Not Be Fillable*.
  `$user->update(['status' => 'suspended'])` silently discarded the field and returned `true`;
  admin suspension never worked, and the UI showed a success toast.
- **Impact**: A security-relevant control that appeared to work. Caught only because a test
  asserted the **resulting state** rather than the redirect.
- **Rule**: When a field is deliberately outside `$fillable`, `update()` is not the API for it
  — write a named method. And always assert the post-condition, never the response alone: a
  302 to the right place proves routing, not effect.
- **Applies to**: All Laravel projects

---

## Basic Custom E-Commerce — 2026-08-27 (Laravel 12, client delivery)

### Anti-Pattern: A plan that promises a control, and a runbook line that pretends to be it
- **What happened**: `Planning.md` §17.4 said "Force an admin password change on first login."
  I wrote that sentence, approved it, built ten phases, wrote `DEPLOYMENT.md` repeating it as a
  bullet — and **never implemented anything**. `AdminSeeder` shipped `admin@basic-ecom.test`
  with the password `password` and no mechanism to require changing it. It was caught only
  because {USER_NAME} highlighted that one line in the seeder during handoff review.
- **Impact**: A live payment-handling store would have gone out with a known working admin
  credential and a deployment document *claiming* that credential was forced to change. The
  document made the gap harder to see, not easier — anyone auditing the runbook would have
  ticked it off.
- **Rule**: When a plan states a **control**, it is a work item, not prose. At the phase that
  should implement it, grep the plan for imperative security language — "force", "must",
  "require", "never" — and confirm each has a file and a test behind it. A control that exists
  only in a document is a control that does not exist. Prefer the mechanism that cannot be
  skipped: a DB flag plus middleware, not an instruction to a human.
- **Applies to**: Every project with a written plan or runbook

### Anti-Pattern: Phantom completion left in the traceability matrix
- **What happened**: The `REQ-013` row listed `app/Http/Controllers/Admin/ShipmentController.php`
  and "EasyParcelService booking methods" as implementation paths. **Neither existed** — the
  feature was blocked and only its schema, model and enum were built. The row sat there through
  Phases 8–11 and into the client handoff. I only found it because {USER_NAME} asked "complete?"
  and I checked instead of answering from memory.
- **Impact**: The client-facing traceability record claimed delivery of a scope item that was
  never built. `53-documentation-protocol.md` §4.2 forbids exactly this, and I had written the
  matrix myself.
- **Rule**: A traceability matrix is an assertion about the filesystem, so **verify it against
  the filesystem** before any handoff: loop the listed paths and `test -f` each one. When a
  requirement is partially built, split the row explicitly — "Built: … / NOT built: …" — never
  leave the aspirational path list in place with a status chip beside it.
- **Applies to**: Any project under Protocol 53

### Anti-Pattern: Silent `str.replace()` after a formatter rewrote the anchor
- **What happened**: Edited files with `python3` + `str.replace()` throughout. Laravel Pint
  rewrote a fully-qualified `\App\Services\ToyyibPayService::class` to the imported short form
  between two of my edits. My next replacement targeted the FQCN string, matched nothing, and
  **wrote the file back unchanged with no error**. The container binding was never added; all
  15 payment tests failed at once with `BindingResolutionException`.
- **Impact**: Ten minutes chasing a "container" bug that was a no-op edit. The failure was loud
  only because a test suite existed — the same silent miss in a doc edit would have shipped.
- **Rule**: `str.replace()` returns a copy and reports nothing. **Assert the anchor before
  replacing**: `assert old in s, "anchor missing"` / `sys.exit("MISS: ...")`. Re-read the file
  after any formatter, linter or codemod runs — never edit against a remembered version of a
  file a tool has since touched.
- **Applies to**: All scripted file edits

### Anti-Pattern: `Http::fake()` merges — it does not override
- **What happened**: In an end-to-end test I faked `*getBillTransactions` early with a
  placeholder amount, then called `Http::fake()` again later with the correct amount for the
  order that now existed. Laravel **merged** the stub sets; the first pattern still matched, so
  the stale placeholder won. The payment refused to settle on an amount mismatch — which was
  the code behaving **correctly** — and it presented as an application bug.
- **Impact**: Debugged the application for a failure caused entirely by the test harness. The
  dangerous version of this is the opposite outcome: a stale permissive stub making a broken
  guard look like it passes.
- **Rule**: Fake each URL pattern **once per test**. When the response depends on state created
  later in the test, use a **closure** stub that reads that state at call time
  (`'*endpoint' => fn () => Http::response([...Order::firstOrFail()...])`), rather than
  re-faking. When a fake-driven test fails, verify the stub before suspecting the code.
- **Applies to**: All Laravel HTTP-client testing

### Anti-Pattern: A test that asserts the framework's test shim, not the application
- **What happened**: Wrote `assertStatus(419)` to prove CSRF protection on a form POST. It could
  never pass: `ValidateCsrfToken` calls `runningUnitTests()` and skips verification entirely
  under `APP_ENV=testing`. I had written a test of Laravel's own test-mode behaviour and called
  it a security test.
- **Impact**: Would have shipped as false assurance in the security suite — the worst kind of
  test, because its presence stops anyone writing the real one.
- **Rule**: Before asserting a framework behaviour, ask what would have to break for this test
  to fail — if the answer is "the framework", it is not your test. Assert the **project's
  decision** instead: that the form ships a token, and that the CSRF exclusion list contains
  exactly the one route intended and nothing else. Note that Laravel 11+ stores
  `validateCsrfTokens(except:)` in the **static** `$neverVerify`, not the instance `$except`.
- **Applies to**: All framework-level testing

### Anti-Pattern: Docblock describing behaviour the function does not have
- **What happened**: Wrote an order-number generator whose docblock read "Retries a few times on
  collision" over a body that was `random_int(1, 9999)` with **no retry at all**. The random
  suffix also collides roughly half the time by ~120 orders in a day (birthday problem), so the
  comment was describing the mitigation for a defect it was also concealing.
- **Impact**: Caught by writing a test for sequential order numbers. Left alone, a busy day
  would have produced duplicate-key failures at checkout — for real customers, at the worst
  moment.
- **Rule**: A docblock is an assertion; write it **after** the body or verify it against the
  body before committing. When a comment claims a safety property (retry, lock, idempotency,
  validation), there must be a test named for that property. Treat "N random digits" as a
  collision source, not a uniqueness source — derive sequence from state and let a UNIQUE index
  plus a real retry be the guard.
- **Applies to**: All projects

### Anti-Pattern: Overriding a framework base-class method with an incompatible signature
- **What happened**: Added `Setting::all(): array` and `Setting::value(string)` as convenience
  accessors on an Eloquent model. `Model::all($columns = ['*'])` already exists with a different
  signature, and `value()` is forwarded to the query builder via `__callStatic`. The override
  would have broken the Eloquent contract for anything calling `Setting::all()` expecting a
  Collection.
- **Impact**: Caught before it ran, but only because I re-read the file. It would have surfaced
  later as a type error in unrelated code.
- **Rule**: Before naming a static helper on a model, check it against the base class's public
  API. Prefer a name the framework does not use (`cached()`, `getInt()`) over shadowing one it
  does. Convenience is not worth an incompatible override.
- **Applies to**: Eloquent, and any framework base class

### Anti-Pattern: Writing a heredoc into a directory that does not exist
- **What happened**: `cat > app/Services/CartService.php <<'EOF'` where `app/Services/` had never
  been created. The redirect failed, the file was not written, and the only signal was a
  `php -l` error on a missing file at the end of a long command.
- **Impact**: Minor — one wasted round trip. Recorded because the same shape in a longer batch
  would leave a silently missing file among many written ones.
- **Rule**: `mkdir -p` the target directory in the same command as any heredoc write to a new
  path, and verify with `php -l` or `test -f` immediately after.
- **Applies to**: All shell-driven file creation

### Anti-Pattern: Reading state after mutating it, to decide what the mutation did
- **What happened**: `CartController::store()` decided whether a quantity had been capped with
  `$resulting < $this->cart->qtyFor($id) + $requested` — but `qtyFor()` was read **after**
  `add()` had already written. The condition was always true, so every add reported "capped".
- **Impact**: Cosmetic here, but the shape is the same one that produces wrong stock and wrong
  totals elsewhere.
- **Rule**: Capture the before-value into a variable **before** the mutating call. If a function
  needs to report what it changed, have it return that — do not reconstruct it from state the
  call has already altered.
- **Applies to**: All projects

### Anti-Pattern: Repeating a defect I had already written into the anti-pattern log
- **What happened**: Added a `needsReviewCount` view composer registered on `layouts.admin`
  only. The dashboard **child view** renders that variable in its own section, so it was
  undefined and every dashboard request 500'd. This is the *identical* mistake recorded
  earlier the same day as "View composer registered only on `layouts.*`", and the review
  checklist item I wrote for `35-review-protocol.md` says in as many words: *"View composers
  registered for every namespace that renders the shared variable, not just `layouts.*`"*.
- **Impact**: Caught by tests within a minute — but the log entry and the checklist did not
  prevent it, which is the point worth recording. Writing a rule down is not the same as
  reading it at the moment of the decision.
- **Rule**: When a phase's own log already contains an anti-pattern for the exact mechanism
  being touched, **re-read that entry before writing the code**, not after the test fails.
  For view composers specifically: register against every namespace that renders the
  variable, and treat "the layout uses it" as insufficient evidence that only the layout
  uses it.
- **Applies to**: All projects — and to the maintenance of this log itself

### Anti-Pattern: A `str.replace()` anchor pointing at the wrong section number
- **What happened**: Inserted a decision record into `Planning.md` anchored on `### 12.3`,
  believing §12 was the architecture section. §12 is **Database Design**; §12.3 is a table
  list. The `assert` fired correctly — but only *after* an earlier edit in the same script
  had already written to the file, and the commit ran anyway. Result: the stack table gained
  a row cross-referencing a section that does not describe it, the decision record was never
  written, and the docs changelog edit queued behind it was silently skipped.
- **Impact**: A commit that claimed to record a decision and did not. Fixed in a follow-up,
  but the partial-write shape is the hazard: assertions protect the *edit*, not the *batch*.
- **Rule**: Validate **every** anchor in a multi-file edit script **before** writing any
  file — collect failures first, then apply. And verify the section a cross-reference points
  at actually covers the subject; `grep -n '^### '` the target document rather than
  trusting a remembered outline.
- **Applies to**: All scripted multi-file documentation edits

### Anti-Pattern: Logging a rule, then not applying it — twice
- **What happened**: Recorded "validate **every** anchor in a multi-file edit script BEFORE
  writing any file" after a partial batch shipped a commit that claimed a decision it had not
  recorded. Then did the same thing again on the very next feature: an edit script asserted on
  a `Planning.md` anchor that did not match, **wrote the other file first**, and the commit
  went out — a second commit claiming a decision it had not recorded. Separately, in the same
  session, repeated a view-composer defect that was already in this log *and* in the review
  checklist I had written for it.
- **Impact**: Three repeats of two known defects, all caught, none shipped to production —
  but the log demonstrably did not change behaviour. That is the finding worth keeping: a rule
  written after the fact is a record, not a control.
- **Rule**: A recurring defect needs a **mechanism**, not a paragraph. For scripted edits that
  means the script itself validates first and exits before any write — make that the template,
  not the intention:
  ```python
  missing = [k for k, (old, _) in edits.items() if old not in files[k]]
  if missing: sys.exit("ABORT before writing: " + str(missing))
  ```
  And when about to touch a mechanism this log already has an entry for, **re-read that entry
  before writing the code**, not after the test fails.
- **Applies to**: All scripted edits, and to the maintenance of this log

### Anti-Pattern: A published deliverable left behind the code it describes
- **What happened**: Published a client handoff Artifact stating "199 tests / 564 assertions",
  then changed client-visible behaviour three more times — the admin template, the dashboard
  metrics, and the entire order-status vocabulary. The artifact still claimed the old figures
  and said nothing about the workflow states the client would operate with daily. It was only
  caught by explicitly diffing the published document against reality.
- **Impact**: A live client-facing link, quietly wrong, describing a workflow that no longer
  existed. Exactly the "documentation lying about code" failure recorded twice already this
  project — but pointed outward, at the client, which is worse.
- **Rule**: A published artifact is a **deliverable with a URL**, not a snapshot. Any change to
  client-visible behaviour after publishing means re-checking it: diff the claims (version
  numbers, counts, feature lists, workflow names) against the code, then republish to the same
  URL. Add it to the end-of-change checklist alongside tests and docs.
- **Applies to**: All published handoffs, reports and status artifacts

## Learned Skills — Basic Custom E-Commerce

### Skill: Run the guard suites against the real engine, not just SQLite
- **Learned from**: Basic Custom E-Commerce
- **Pattern**: Keep the fast suite on SQLite in-memory, but run every suite that asserts a
  **database-enforced** guarantee — guarded `UPDATE` affected-row counts, UNIQUE collisions,
  collation behaviour — against the actual MySQL/MariaDB target before release. Here that meant
  199 tests green on both engines on every phase, via one env-prefixed command.
- **Why**: The stock-decrement and duplicate-payment guarantees are enforced by the database,
  not by PHP. A test that passes only on SQLite proves nothing about the thing it exists to
  prove. It also caught the dev/prod engine split early (local MariaDB 10.4 vs target MySQL 8).
- **Applied to**: Any project where correctness depends on DB-level constraints

### Skill: Deliver a blocked integration complete and inert, not absent
- **Learned from**: Basic Custom E-Commerce (ToyyibPay, OQ-11)
- **Pattern**: When a third-party contract cannot be verified, still build the whole path —
  service, controller, settlement transaction, tests — with the unverifiable step returning an
  explicit refusal. Ship it switched off behind config, with the refusal reason logged verbatim
  and stated in the README, the deploy runbook and the handoff.
- **Why**: The client gets everything that *can* be built, the remaining work is one confirmation
  rather than a phase, and nobody later mistakes the deliberate refusal for a defect. The
  alternative — guessing the contract — converts an open question into a silent money bug.
- **Applied to**: Any integration blocked on an unobtainable specification

### Skill: Answer "is it complete?" by checking, not by recalling
- **Learned from**: Basic Custom E-Commerce
- **Pattern**: On any completion or handoff question, run the verification before composing the
  answer — working tree clean, suites green on every target, and each claimed implementation
  path confirmed to exist on disk. Then answer from that output.
- **Why**: I had every reason to believe the project was complete, and it was not: one
  requirement's file list was fictional. The check took one command; the wrong answer would have
  gone to a client. Confidence about your own recent work is precisely where verification feels
  least necessary and is most needed.
- **Applied to**: All handoffs, status reports and completion claims

---

## larisHQ — PH02 Authentication & RBAC (2026-09-01)

### Anti-Pattern: Shipping a permission system whose smallest permission is the biggest one
- **What I did**: wrote staff CRUD where the role list validated only as `exists:roles,id`. A
  user holding nothing but `staff.create` could create a user, attach the HQ Owner role, choose
  its password, and log in as it. Every route had a `can:` check; every check passed; the system
  was wide open anyway.
- **Why it happened**: I checked authorization *per endpoint* and never asked what the endpoints
  compose into. "Can this user reach this action?" was answered correctly nine times. "What can
  this user become?" was never asked at all.
- **The rule**: in any RBAC build, the review question is not only *is each route guarded* but
  **what is the maximum privilege reachable from each individual permission**. Wherever one user
  can hand another user access — role assignment, role authoring, invitations, API tokens —
  a grant ceiling is mandatory: `array_diff($granted, $granter->permissions) === []`.
- **Caught by**: my own Phase 5 review, before commit. Reproduced first, then fixed, then
  regression-tested in both directions.

### Anti-Pattern: A guard test that trips on the prose explaining the guard
- **What I did**: wrote a test forbidding `is_admin`-style checks by grepping `app/` for the
  token. It failed immediately — on the comment in `RoleTemplates.php` explaining why no
  `is_admin` flag exists.
- **The rule**: a source-scanning guard must scan **code**, not text. In PHP, strip
  `T_COMMENT`/`T_DOC_COMMENT` with `token_get_all()` before matching. Otherwise the honest thing
  — documenting the rule where it matters — is what breaks the build, and the fix pressure is to
  delete the explanation.
- **Applied to**: every anti-pattern guard test, in any language.

### Anti-Pattern: Assuming a framework helper still does what its name says
- **What I did**: nearly wired unauthenticated redirects assuming `Authenticate::redirectTo()`
  finds the login route. On Laravel 12 it returns **null** unless `redirectUsing()` was called;
  the redirect actually comes from the exception handler's `route('login')` fallback — so the
  route *must* be named `login` or every guest hits an exception instead of a login screen.
  Same session, same shape: `authorizeResource()` still exists and still calls
  `$this->middleware()`, which Laravel 12 controllers no longer have — it is a fatal error, not
  a deprecation.
- **The rule**: for auth, authorization and routing internals, read the installed vendor source
  before writing against it. Both of these read as working code and fail only at runtime, in the
  path you are least likely to exercise by hand.

## Learned Skills — larisHQ

### Skill: Gate the schema before writing the code, in writing
- **Learned from**: larisHQ PH02
- **Pattern**: present the migrations, the design calls behind them and the one genuinely open
  fork *before* Phase 3, and get an explicit approval. Four decisions (permissions global vs
  tenant-scoped, the `Gate::before` contract, `users.status` early, the frontend permission
  payload) were settled in one exchange and never revisited.
- **Why**: schema is the most expensive thing to change after code exists, and the decisions that
  look like implementation detail — where `tenant_id` goes, what `before` may answer — are the
  ones that decide whether the *next* phase is safe.
- **Applied to**: every T2 phase with a migration.

### Skill: Prove the authorization claim over real HTTP, not only in the harness
- **Learned from**: larisHQ PH02
- **Pattern**: after the suite is green, log in as a genuinely limited role against the running
  app and confirm the 403s — GET and POST both — and that no record was written. The feature
  tests said the same thing, but the HTTP pass also caught that sessions only work on a
  `*.larishq.test` host (`SESSION_DOMAIN`), which no test would ever have shown.
- **Why**: the harness bypasses the cookie, the host, the CSRF token rotation and the real
  middleware ordering. Those are exactly where an authorization system is deployed, and exactly
  where the harness is silent.
- **Applied to**: any phase whose acceptance criteria are about who is refused.

---

## larisHQ — PH03 Multi-Tenancy (2026-09-01)

### Anti-Pattern: Reasoning about middleware order instead of running it
- **What I did**: placed tenant resolution as a route-group alias and reasoned that group
  middleware runs before route middleware, so the tenant would be bound before the guard resolved
  a user. Wrong: `Authenticate` and `SubstituteBindings` are in the framework's **middleware
  priority list**, which reorders them ahead of anything not in that list. The guard was querying
  users with no tenant bound.
- **How it surfaced**: not by review. A single test failed with
  `destroy(): Argument #1 ($role) must be of type Role, string given` — a *different* bug — and the
  stack trace in that failure showed the real ordering. One failing test paid for two findings.
- **The rule**: middleware order is a runtime property, not a reading-order property. When
  correctness depends on it, assert it — a test whose failure prints the stack is worth more than
  any amount of confidence about the pipeline.

### Anti-Pattern: `$request->user()` after a second guard exists
- **What I did**: shared `auth.permissions` from `$request->user()?->permissionSlugs()`. Correct
  with one guard. `Authenticate` calls `shouldUse($guard)`, so `auth:platform` makes `platform` the
  default guard **for the whole request** — `$request->user()` then returned a `PlatformUser`, and
  the shared Inertia prop called `permissionSlugs()` on a model that has no such method. A 500 on
  every page of the console that administers every customer.
- **The rule**: the moment an application has two guards, `$request->user()` and bare `auth` stop
  meaning anything specific. Name the guard everywhere — `Auth::guard('web')->user()`,
  `auth:web`, `auth:platform` — including in shared view/prop data, which is the place it is
  easiest to forget and the place it breaks every page at once.

### Anti-Pattern: Writing the same fillable no-op twice in two phases
- **What I did**: kept `tenant_id` out of `$fillable` (correct — it is a privilege column), then
  used `updateOrCreate(['tenant_id' => $id, 'slug' => $slug], …)` in the provisioner *and* in a
  seeder. Mass assignment drops the key from the new instance, so the write-refusal I had just
  written threw on my own code.
- **Why it matters**: `Privilege Columns Must Not Be Fillable — and the Silent No-Op That Follows`
  was already in this log from Daily Spend. I wrote the guard and then walked into its far side
  twice in one phase. Knowing a rule is not the same as recognising the shape at the call site.
- **The rule**: whenever a column is excluded from `$fillable`, grep the codebase for
  `updateOrCreate`/`firstOrCreate`/`create` carrying that column in the *attributes* array. The
  lookup half works; the instantiation half silently does not.

## Learned Skills — larisHQ PH03

### Skill: Let one failing test finish talking before fixing it
- **Learned from**: larisHQ PH03
- **Pattern**: when a test fails with an exception, read the whole stack before changing anything.
  The controller-argument failure was the headline; the middleware ordering bug was visible three
  frames down and would otherwise have shipped, because nothing else in the suite exercised it.
- **Why**: a failing test is the cheapest observability the project has. Fixing the headline and
  re-running discards the rest of what it was telling you.
- **Applied to**: every red test, not just confusing ones.

### Skill: Prove isolation by suspending one tenant and checking the other
- **Learned from**: larisHQ PH03
- **Pattern**: the isolation claim is not "tenant A gets a 404 for tenant B's record" alone. It is
  also "an action against tenant A leaves tenant B untouched". Suspending one subscriber over real
  HTTP and confirming **403 on theirs, 200 on the other's** tests the blast radius, which is what
  the customer actually cares about.
- **Why**: scope tests prove reads are filtered. They say nothing about whether an administrative
  action is correctly targeted. Those are different bugs with the same word attached.
- **Applied to**: any multi-tenant, multi-account or multi-workspace system.

---

## larisHQ — PH04 HQ Business Setup (2026-09-01)

### Anti-Pattern: A dotted data key inside a dot-notation path
- **What I did**: named settings `commission.clawback_days` — readable, groupable, and idiomatic
  — then generated validation rules as `settings.commission.clawback_days`. Laravel reads dots as
  nesting, so that rule addressed `$data['settings']['commission']['clawback_days']`, a path that
  never exists. `required` failed, an error appeared under exactly the key I was asserting, and my
  test went green. The posted value — `400`, well outside the declared `max:365` — was never
  checked at all, and `validated()` returned a nested array the controller could not consume, so
  **saving a setting over HTTP was broken**.
- **How it surfaced**: an Inertia assertion could not address the prop, for the same reason. The
  failure I was annoyed by was the only thing pointing at the real one.
- **The rule**: any key containing the framework's path separator must be escaped at every path
  boundary — validation rules (`settings.commission\.clawback_days`), `data_get`, `old()`,
  Inertia's `where()`. And a green test that asserts *an error exists* proves nothing about
  **which** rule produced it; assert the valid case too, or the failure mode hides inside the
  success.
- **Caught by**: my own test run, before commit.

### Anti-Pattern: Testing a store through its repository and never through its endpoint
- **What I did**: covered the settings repository directly (`set()` then `get()` — green) and
  covered the endpoint only for rejection (403, 422). Nothing ever posted a *valid* value through
  the controller, which is precisely the path that was broken.
- **The rule**: for every store or service with an HTTP surface, at least one test must travel the
  whole route — request, validation, controller, persistence, read-back. Unit-testing the service
  and permission-testing the endpoint can both pass while the seam between them is broken.

### Anti-Pattern: Reseeding roles without reseeding permissions
- **What I did**: added ten permissions to the registry, then ran only `RoleSeeder` to refresh the
  templates. It maps slugs to ids from the table, so the ten new slugs — absent from the table —
  were silently skipped, and the HQ Owner got a 403 on the screens the phase had just built.
- **The rule**: a seeder that resolves foreign keys by natural key fails **silently** when the
  target row is missing. Run the whole seeder chain in order, and prefer a seeder that reports what
  it could not resolve over one that quietly syncs fewer rows.

---

## larisHQ — PH05 Dynamic Hierarchy (2026-09-01)

### Anti-Pattern: `nullable` in front of a rule that has to decide what null means
- **What I did**: wrote `'parent_id' => ['nullable', new ValidNetworkParent($level, $member)]`.
  The rule's first branch says "a member below the top level must have a parent" — and Laravel
  skips **every rule after `nullable`** when the value is null, so that branch never ran. A member
  could be created orphaned below the top level, which is precisely the structural invariant the
  rule exists to protect.
- **How it surfaced**: the test that asserted the refusal failed with "Session is missing expected
  key [errors]" — the one test I nearly did not write, because the rule so obviously handled it.
- **The rule**: `nullable` means *"null is acceptable, stop checking"*. A custom rule that must
  interpret null cannot sit behind it. Use `present` (key must exist, may be null) and let the
  rule decide — `validatePresent` returns true for a present-null key, so the rule runs.
- **Caught by**: my own test run, before commit.

### Anti-Pattern: Ordering an audit trail by a one-second timestamp
- **What I did**: `->latest('created_at')` on the audits relation. Three events written in one
  request share a second, so they came back in arbitrary order and the assertion failed against a
  trail that read differently each time.
- **The rule**: any "history" ordering needs a tiebreaker the database guarantees —
  `ORDER BY created_at DESC, id DESC`. A log that reorders itself between reads is worse than no
  log, because it looks authoritative.

## Learned Skills — larisHQ PH05

### Skill: Prove a configurable dimension at both ends and the boundary, not in the middle
- **Learned from**: larisHQ PH05 (1–8 configurable levels)
- **Pattern**: for anything the customer configures, write the same end-to-end test at the
  **minimum**, at a **typical** value, at the **maximum**, and at **maximum + 1** rejected. Here
  that was 1 level, 2 levels, 8 levels, and a 9th refused — and the 9th refused separately by the
  service, the HTTP layer and a database constraint.
- **Why**: a single mid-range test passes on code that has a hardcoded assumption at either end.
  The 1-level case caught different things from the 8-level case: one has no parents at all, the
  other exercises the full recursive walk.
- **Applied to**: any configurable count, depth, tier or limit.

---

## larisHQ — PH06 Marketers & Channels (2026-09-01)

### Anti-Pattern: Repeating a logged anti-pattern in a new costume
- **What I did**: wrote a guard test grepping the source for `facebook` and `google ads` to prove
  no channel-specific branch exists. It failed on my own doc comments — the ones explaining why no
  branch exists. I had hit exactly this in PH02 with the `is_admin` guard, **written the fix
  (strip comments with `token_get_all`) and logged it as an anti-pattern in this very file**, four
  phases earlier in the same session.
- **Why it happened**: I recognised the *rule* ("guards must scan code, not prose") but not the
  *shape* at the call site, because the subject was different — permissions then, channel names
  now. Logged lessons are indexed by their example, not by their structure.
- **The rule**: when writing any source-scanning guard, go and read how the last one was written.
  The generalisation to hold is "a guard that greps source must strip comments first", and it
  applies to every future guard regardless of what it forbids.

### Anti-Pattern: A comment that describes intent the code does not implement
- **What I did**: wrote `syncDefaultChannels()` to walk the config and create anything missing,
  with the comment *"Only ever adds: a channel an HQ deleted on purpose must not reappear on the
  next sync."* The code did the exact opposite — a deleted channel was missing, so it was
  recreated. The comment was a specification I had written and not implemented.
- **How it surfaced**: the test I wrote from the comment failed. Had I written the test from the
  code instead, both would have agreed and both would have been wrong.
- **The rule**: write the test from the **intent**, never from the implementation. When they
  disagree, that is the test doing its job — and the fix goes in the code, not the comment. A
  comment stating a guarantee is a claim; if nothing enforces it, delete the claim or enforce it.

### Anti-Pattern: Declaring a flaky test fixed because it stopped failing
- **What I did**: hit an intermittent failure, could not reproduce it in ten runs, hardened two
  factories with bounded `fake()->unique()` pools, and was ready to move on. It then failed a
  second time.
- **The rule**: a flake that has stopped reproducing is **not** a flake that has been fixed. Say
  what was observed, at what rate, what was ruled out and what was changed as a precaution — and
  record it as open. Reporting "fixed" on a disappearance trains exactly the wrong reflex, and the
  next person to see it starts from zero.
- **Status**: still open in larisHQ — see `Planning.md` PH06 notes.

---

## larisHQ — PH07 Catalogue & Pricing (2026-09-02)

### Anti-Pattern: Rebuilding the application inside a test
- **What I did**: wanted one test to exercise three hierarchy depths, so I looped and called
  `$this->refreshApplication()` between iterations. The new application opens a **new database
  connection** while the previous one still holds an open `RefreshDatabase` transaction — and that
  transaction holds row locks on `permissions`, which every test's `beforeEach` seeds. The next
  seed blocked for 50 seconds and died with
  `SQLSTATE[HY000] 1205 Lock wait timeout exceeded`.
- **Why it matters far beyond that test**: this was the **intermittent failure I had been chasing
  since PH04** — the one that appeared roughly twice in twenty-five runs, moved between unrelated
  tests, and survived ten isolated runs and three random-order runs. It was never order-dependent
  and never a faker pool; it was lock contention on the one table every test writes, surfacing in
  whichever test happened to seed next.
- **The rule**: never rebuild the container mid-test. To run one test against several
  configurations, use a dataset (`->with([1, 3, 8])`) — each case gets a clean transaction.
- **The wider lesson**: when a flake moves between unrelated tests, stop looking at the tests and
  look at what they **share**. Here it was a single seeded table and a transaction that outlived
  its owner.

## Learned Skills — larisHQ PH07

### Skill: Chase a flake to its shared resource, and say "open" until you have reproduced it
- **Learned from**: larisHQ PH04–PH07
- **Pattern**: three sightings across three phases, each in a different test. I recorded it as
  open, wrote down what had been ruled out, and kept going — then reproduced it deliberately two
  phases later while writing an unrelated test, and the stack trace named the cause in one line.
- **Why**: had I written "fixed — hardened the factories" at the first disappearance, the real
  cause would still be there and the next person would start from zero. Recording *what was
  observed, at what rate, and what was ruled out* is what made the eventual diagnosis a
  five-minute job instead of a fresh investigation.
- **Applied to**: any intermittent failure. State the rate, state the exclusions, keep it open.

### Skill: Re-raise an assumed decision at the moment its cost becomes real
- **Learned from**: larisHQ D043
- **Pattern**: D043 was recorded in planning as "ASSUMED — CONFIRM" with the note that it must be
  settled before PH12. I did not chase it for six phases — but the moment PH07 actually created
  the two columns it describes, I put it in the schema gate as a plain business question with the
  consequence spelled out.
- **Why**: asking at planning time competes with thirty other questions and gets a guess. Asking
  when the code is about to depend on it gets a real answer, because the stakes are visible and
  concrete.
- **Applied to**: every assumption logged as "confirm later" — attach it to the phase that first
  depends on it, and raise it there.

---

## larisHQ — PH08 Inventory (2026-09-02)

### Anti-Pattern: A unique index that includes a nullable column
- **What I nearly did**: put `warehouse_id` and `network_member_id` on `stocks` as nullable
  columns with `UNIQUE(tenant_id, warehouse_id, network_member_id, variant_id)`. In MySQL and
  MariaDB, **NULLs are distinct in a unique index**, so two rows for the same network member —
  both with `warehouse_id IS NULL` — would both be accepted. The constraint reads as if it works
  and enforces nothing on exactly the rows it was written for.
- **The rule**: when a row holds *one of two things*, give that choice its own table with a
  `CHECK` that exactly one side is set, and reference it by a single non-nullable key. Then the
  uniqueness lives somewhere it can actually be expressed, and both sides keep real foreign keys.
- **Caught by**: thinking through the constraint before writing it, prompted by having to justify
  the shape at the schema gate.

### Anti-Pattern: Writing a heredoc into a directory that does not exist — again
- **What I did**: `cat > app/Http/Requests/Concerns/ResolvesStockHolder.php` without creating
  `Concerns/` first. The shell reported the failure, but the same command chain's *later* steps
  had already patched two other files to import the trait — so the codebase referenced a file
  that did not exist.
- **Why it matters**: this exact anti-pattern is already in this log from a previous project. The
  new detail is the failure mode: when a compound command writes a file **and** patches its
  dependents, a partial failure leaves the dependents pointing at nothing.
- **The rule**: `mkdir -p` before any heredoc into a new path, and when one command both creates
  and wires something, check the create succeeded before trusting the wiring.

## Learned Skills — larisHQ PH08

### Skill: Name a scope extension as an extension, and price it before it is chosen
- **Learned from**: larisHQ D071
- **Pattern**: §13 described warehouse-only stock. Tracking what each stockist holds is a
  reasonable thing for the owner to want and an easy thing to slide in as "obviously implied" —
  so I put it at the gate as an explicit choice, with what it costs spelled out: every member
  becomes an inventory location, transfers gain a downstream leg, reconciliation spans the
  network, and the portals owe each member a view. Fakrul chose it knowingly.
- **Why**: the failure mode is not refusing scope, it is *absorbing* it silently — the work
  happens, the specification no longer describes the system, and nobody decided anything. Naming
  it makes it a decision with an owner and a recorded cost.
- **Applied to**: every requirement that is reasonable, unstated, and larger than it looks.

---

## larisHQ — PH09 Customers (2026-09-02)

### Anti-Pattern: `$defaults + $overrides` in PHP
- **What I did**: built an anonymiser as
  `forceFill(array_fill_keys($personalFields, null) + ['name' => 'Removed customer', …])`.
  PHP's `+` on arrays keeps the **left** operand's keys, so the `name` override was silently
  discarded and the code tried to write NULL into a NOT NULL column.
- **The rule**: `+` is not `array_merge`. When combining defaults with overrides, the overrides go
  on the **left** — or use `array_merge`, where the right wins. The failure is silent whenever the
  column happens to be nullable, which is most of the time: here it only surfaced because `name`
  is NOT NULL.

### Anti-Pattern: Trusting a framework's name guess after being burned by it
- **What I did**: named a pivot `marketer_customer`, matching the domain and the planning
  document. Laravel's `belongsToMany` guesses alphabetically — `customer_marketer` — and failed
  at runtime. I had hit exactly this in PH06 with `marketer_channel`, fixed it the same way, and
  **written the lesson into session memory** three phases earlier.
- **Why it keeps happening**: the note said "state the table explicitly when the schema names it
  otherwise", which requires noticing that this *is* such a case. The alphabetical rule is easy to
  check and I did not check it.
- **The rule**: whenever a pivot's two model names are not already in alphabetical order, pass the
  table name. Do not evaluate whether it is needed — pass it.

## Learned Skills — larisHQ PH09

### Skill: Turn a policy sentence into a failing test
- **Learned from**: larisHQ PH09 (§18 "no unnecessary personal data")
- **Pattern**: requirements about what a system must *not* do have no natural home in code — there
  is nothing to point at. Make the absence assertable: a test on the exact column list turns
  "collect only what is necessary" from an intention into something that breaks the build when
  violated.
- **Why**: intentions decay silently and nobody is ever the person who decided to erode them. A
  test makes the erosion a visible choice with an author.
- **Applied to**: any "must not" requirement — no unnecessary data, no cost prices in a payload,
  no admin shortcut, no vendor-specific branch. Each of those became a guard test in this project,
  and each has since caught something.

---

## larisHQ — PH10 Ordering (2026-09-02)

### Anti-Pattern: A factory that can generate data the schema rejects
- **What I did**: `RoleFactory` used `fake()->unique()->jobTitle()` for the name and slugged it
  into a `varchar(64)` column. Most job titles fit. "First-Line Supervisor-Manager of Landscaping,
  Lawn Service, and Groundskeeping Worker" does not — so roughly one run in fifteen died with
  `1406 Data too long`, in whichever test happened to draw it.
- **Why it mattered more than it looks**: this was a **second** intermittent failure with the same
  symptom class as the PH07 lock-wait — random-looking, moving between unrelated tests. Having
  diagnosed one, it was tempting to assume any recurrence was the same thing. It was not.
- **The rule**: every generated string must be bounded against the column it lands in. Faker's
  word-based generators have no length contract, and `unique()` does not add one. Assert it once:
  draw a few hundred and check the longest against the column width.
- **The wider lesson**: after fixing one flaky cause, do not assume the next occurrence is the same
  cause. Read the new stack trace as if the first diagnosis had never happened.

## Learned Skills — larisHQ PH10

### Skill: Prove immutability by changing the source, not by reading the copy
- **Learned from**: larisHQ PH10 (D011, D076)
- **Pattern**: a snapshot test that asserts `line.unit_price === 2000` proves the copy happened
  once. It says nothing about whether the value is a copy or a join, because both return 2000
  today. The test that means something is: place the order, **change the price to something
  else**, and assert the order still reads 2000. Do it for every snapshotted input — price, tier,
  cost, names.
- **Why**: the whole point of a snapshot is behaviour under change, so the test has to contain a
  change. Applied here it also caught what would have been a real bug a phase later — the landed
  cost was not originally in my schema, and writing this test is what surfaced that D044's
  commission base had no stable input.
- **Applied to**: any denormalised copy, cached total, or "as at" record.

---

## larisHQ — PH11 Payments (2026-09-02)

### Skill: Chase a dangling cross-reference when you reach the phase it points at
- **Learned from**: larisHQ D031 → PH11
- **Pattern**: D031 dropped "Refunded" as an order status six phases earlier, with the note that
  it *"belongs to PH11"*. PH11's own task list said nothing about refunds. Building only the task
  list would have left a documented pointer unhonoured and a returned order with no way to be
  settled — and nobody would have noticed for months.
- **Why**: decisions written in one phase routinely defer work into another, and the receiving
  phase's task list is usually written before that deferral exists. Re-read the decisions that
  name the phase you are starting, not just the phase's own tasks.
- **How it played out**: raised as an explicit scope question rather than absorbed silently, so
  the extension has an owner and a decision record (D077).
- **Applied to**: any phase whose predecessors deferred something into it. Grep the decision log
  for the phase name before writing the first line of code.

### Skill: Let the shape of a constraint choose the concurrency tool
- **Learned from**: larisHQ PH08 → PH11
- **Pattern**: PH08 made overselling impossible with a guarded conditional update, and that
  pattern was fresh and successful. PH11's constraint looks identical in English — "never exceed
  the total" — but the quantity being constrained is a **sum across rows**, which no single-row
  `WHERE` can express. It needed a parent lock instead.
- **Why**: reaching for the tool that worked last time is exactly how a read-then-write race gets
  shipped with confidence. One row → conditional update. Sum across rows → lock the parent and
  aggregate under the lock. State which one applies and why, in the code.
- **Applied to**: credit limits, quotas, capacity checks, anything phrased as "the total must not
  exceed".

---

## larisHQ — PH12 Commission (2026-09-02)

### Anti-Pattern: Comparing ids from two different tables
- **What I did**: wrote a test asserting D014 — that no commission entry belongs to a network
  member — as
  `CommissionEntry::whereIn('marketer_id', NetworkMember::pluck('id'))->count() === 0`.
  It failed, and the code was right: marketer ids and network member ids are separate sequences,
  so marketer 1 and member 1 collide numerically. The assertion was a category error that would
  have passed or failed by coincidence either way.
- **The rule**: an id is only meaningful against its own table. To prove a foreign key cannot hold
  the wrong kind of thing, assert it **structurally** (the column does not exist) and
  **referentially** (every value resolves to the intended model) — never by comparing raw ids
  across tables.
- **Caught by**: the test failing on correct code, which is the useful direction for a test to be
  wrong in.

## Learned Skills — larisHQ PH12

### Skill: Depart from an accepted proposal when implementing reveals what it costs
- **Learned from**: larisHQ D078, D079
- **Pattern**: P2 had been accepted months earlier and specified the manager override as a period
  lump sum. Implementing the clawback lifecycle made the cost visible — a lump sum has no per-order
  entry to cancel when one order in the period is returned. Rather than build it as written or
  quietly change it, I put the trade-off at the gate with both shapes priced, and recorded the
  outcome as a decision that *refines* P2 rather than contradicting it.
- **The second case** was smaller and I decided it myself: D045 permits loss-leader pricing, so a
  negative commission base is a real state, and a negative commission would make the HQ's own
  pricing decision into a debt the marketer owes. Floored at zero, recorded, reason stated.
- **Why**: an accepted proposal is a decision made with less information than you have while
  building it. Neither silently following it nor silently changing it is right — surface what
  implementation revealed, and let the record show why the answer moved.
- **Applied to**: any spec written before the thing it specifies existed.

---

## Learned Skills — larisHQ PH13 (2026-09-02)

### Skill: Write the timezone test as the scenario, not as the assertion
- **Learned from**: larisHQ PH13
- **Pattern**: "period boundaries are computed in the configured timezone" is easy to assert
  trivially — `expect(config('app.timezone'))->toBe(...)` — and that proves almost nothing. The
  test that earns its place names the **scenario**: an order placed at 00:30 on the 1st in Kuala
  Lumpur is 16:30 on the last day of the previous month in UTC, so a UTC boundary silently files
  that sale under the wrong period.
- **Why**: timezone bugs produce numbers that are wrong and look completely ordinary. Nobody
  audits a monthly total that is plausible. Writing the failing scenario into the test is what
  makes the bug *findable* rather than merely *prevented today*.
- **Applied to**: any date bucketing — reporting periods, billing cycles, cut-off times, "today's"
  anything.

### Skill: Reuse the schema shape you already proved, and say that you are
- **Learned from**: larisHQ PH08 → PH12 → PH13
- **Pattern**: three phases hit the same problem — a row that must reference exactly one of
  several things, with uniqueness over that choice. The first (stock locations) cost real thought
  and a separate table. The second (commission rules) and third (targets) used a CHECK plus a
  STORED generated key, in minutes, with a comment naming the earlier decision.
- **Why**: a solved shape recognised early is the cheapest thing in a codebase, and the comment
  pointing back is what makes it recognisable to the next person instead of looking like
  coincidence. The failure mode is the opposite one — solving it a third distinct way, and leaving
  three patterns where one would do.
- **Applied to**: any recurring structural problem. Name the earlier decision in the code, not just
  in the log.

---

## larisHQ — PH14 Reports (2026-09-02)

### Anti-Pattern: Subtracting one unsigned column from another
- **What I did**: computed a margin as `SUM((retail_price - unit_price) * quantity)` where all
  three columns are `unsignedInteger`. MySQL and MariaDB do **unsigned** arithmetic there, so the
  moment `unit_price > retail_price` the expression does not go negative — it raises
  `SQLSTATE[22003] 1690 BIGINT UNSIGNED value is out of range` and the whole report 500s.
- **The sharp edge**: casting the subtraction alone was **not enough**. Multiplying the signed
  result by an unsigned `quantity` promotes the whole expression back to unsigned, and it failed
  again with the same error. Every operand needs the cast.
- **How it surfaced**: live data, not the test suite. My test had retail above the level price —
  the normal case — so the underflow never occurred. The dev database happened to contain a
  product priced above retail, which D045 explicitly permits, and that is what broke it.
- **The rule**: if a column can legitimately be subtracted below zero, either store it signed or
  cast **every** operand in the expression. And when a comment claims a behaviour ("can be
  negative; reported as it is"), write the test that exercises it — mine claimed exactly that and
  the code had never done it.

## Learned Skills — larisHQ PH14

### Skill: Read a decision against the schema before building on it
- **Learned from**: larisHQ D048 → D082
- **Pattern**: D048 defined a figure as "computed from data the order already holds". Rather than
  taking that at face value, I checked what the order actually held — and retail was not among the
  snapshots. Building first would have produced a number that quietly changed whenever a product
  was repriced, and it would have looked right every day until someone compared two reports.
- **Why**: a decision written months earlier describes the schema its author *expected*. The
  cheapest moment to find the gap is before the code depends on it; the most expensive is when
  someone notices last quarter's report has moved.
- **Applied to**: any decision that says "computed from" or "derived from" existing data. Go and
  look at the columns.

### Skill: Test the export separately from the screen
- **Learned from**: larisHQ PH14
- **Pattern**: the scoping rule was "a marketer's report covers only their assigned scope", and it
  is easy to satisfy on the screen and miss on the CSV — the export is a second code path to the
  same data, and it is the one that leaves the building.
- **Why**: an export that ignores a scoping rule is the obvious way around it, and nobody notices
  because the screen looks correct. Assert the narrowing on the downloaded bytes, not just on the
  rendered props.
- **Applied to**: any download, API endpoint, or print view that mirrors a scoped screen.
