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

## ⚡ CLI Commands

```bash
# Register a Controlled Self-Evolution Proposal
coresentinel evolve propose \
  --target "anti-patterns.json" \
  --change "Add SQL injection scanner rule" \
  --evidence "AppSec incident RUN-#9281" \
  --impact "Low risk; adds pre-commit security check"

# List all evolution proposals and review status
coresentinel evolve list

# Approve and version an evolution proposal
coresentinel evolve approve EVO-014 --approver "Fakrul"
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
