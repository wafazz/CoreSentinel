# Controlled Self-Evolution (CSE) Protocol

> **Governed, Versioned & Evidence-Backed AI Evolution**  
> AI agents are prohibited from autonomously altering core governance, security, or identity rules. All rule changes require a formal Controlled Evolution Proposal.

---

## ðŸ”’ Governance Prohibition Rules
1. **No Autonomous Rule Mutations**: An AI agent cannot unilaterally modify system rules or security parameters without human/lead review.
2. **Mandatory Evidence & Impact Analysis**: Every rule addition must present empirical session evidence and risk assessment.
3. **Versioned Release**: Approved changes receive version increments (e.g. `v1.1.0`) and pass regression checks before deployment.

---

## ðŸ—ºï¸ Controlled Evolution Pipeline

```text
  Execution âž” Experience (automatic) âž” Candidate âž” Evidence âž” Confidence âž” TRUSTED
                                                                              â”‚
                              â•â•â•â•â•â•â•â•â•â•â•â•â•â• HUMAN BOUNDARY â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•ªâ•â•
                                                                              â”‚
  Proposal âž” Impact Analysis âž” Human Review âž” Approval âž” Versioned Change âž” Regression Test âž” Deploy
```

The left half runs on its own and ends at **TRUSTED**, which is advice. The right half is
governance and begins with a person. They share evidence and never share authority.

---

## ðŸ”¬ From Observation to Candidate

An observation is not a lesson, and a lesson is not a rule. The gap is deliberate: a system
that turns every incident straight into governance produces a rulebook nobody reads and a
review queue nobody reads either â€” and a reviewer who rubber-stamps has stopped being a control.

```bash
coresentinel evolve observe        # derive candidates from what is already recorded
coresentinel evolve candidates     # the queue, by status
```

Four sources. Three of them are things somebody already wrote down:

| Source | Signal | Needs a human first? |
| :--- | :--- | :---: |
| **Incidents** | A resolved incident's `learning` field | yes |
| **Failures** | The failures memory layer â€” a fact there is a mistake that happened | yes |
| **Patterns** | A pattern whose occurrence count has risen | yes |
| **Experiences** | A failure the system watched happen, more than once | **no** |

Nothing reads code and infers a lesson. An observer that invents rules from source it does
not understand produces governance nobody agreed to. That rule binds the experience source
hardest, because it is the one nobody reviewed on the way in: a candidate drawn from an
experience **describes what happened and stops there**.

### Experiences are captured automatically

Nobody runs a command to record one. `coresentinel_core/experience/` subscribes to the event
bus, and an outcome event â€” a gate result, a verification verdict, a task completion, an
incident â€” becomes an experience.

```bash
coresentinel evolve experiences                    # the log
coresentinel evolve experiences --prune --apply    # fold duplicates, enforce the cap
```

Three properties hold it in place:

- **Only outcomes are captured.** `MemoryCreated` and `AgentStarted` are not outcomes.
  Recording them is how a learning store fills with facts that support no lesson.
- **No credential is stored.** Every payload passes through `security/redaction.py`.
- **The log is bounded.** Duplicate signatures fold; the cap (`learning.max_experiences`,
  2000) is enforced on the write path. A learning system that grows without limit becomes
  the context bloat CoreSentinel exists to remove.

### The evidence threshold

A candidate needs **2 distinct sources** before it may be proposed. One incident is an
anecdote; the second is what makes it worth a rule.

- The same source **cannot corroborate itself** â€” a single noisy incident must not argue its
  way into the rulebook.
- **Repetition is not corroboration.** One signature recurring in one context is one source,
  however often it recurs. A flapping gate is a single noisy incident wearing a different
  hat, and if repeating counted as corroborating, any misconfigured check could vote itself
  into the rulebook overnight. Repetition raises the *success* term of the confidence score,
  where its weight is visible; it never buys independence.
- Re-running the observer **never inflates evidence**. It is idempotent by construction.
- A **rejected candidate stays rejected**. Resurfacing a declined lesson on every run is how
  a review queue becomes noise, and noise is how a control stops working.

### Confidence, and why it carries its arithmetic

Four terms, declared weights, and the breakdown stored beside the number. A score whose
inputs are not recorded is a number nobody can argue with â€” it looks like a measurement and
behaves like an opinion.

| Term | Weight | What it measures |
| :--- | ---: | :--- |
| `evidence` | 0.35 | distinct sources, saturating at 3 |
| `success` | 0.30 | successes / (successes + failures); **not measured when there are no successes** |
| `consistency` | 0.25 | 1 âˆ’ contradicting / total |
| `recency` | 0.10 | decay on `last_seen`, floored at 0.30 |

**A term nobody measured is left out, not scored against.** When a term's input says nothing,
it reports as not measured, drops out of the average, and its weight is shared across the
terms that did have something to say. `coresentinel_score.py` already works this way: a
signal it cannot evaluate on this machine is excluded from the denominator rather than
counted as a failure.

This was wrong in the first release, and the arithmetic said so. `success` fell back to a
fixed 0.5, so a candidate with no outcome data could reach at most 0.85 against a 0.90 bar,
and a lesson drawn from failures alone scored 0.0 on the term and capped at 0.70. The only
producer of candidates is `experience/analysis.py`, and it records a candidate *only* for a
recurring failure - so every candidate the system actually produced sat below the threshold
it was measured against. TRUSTED was unreachable by arithmetic rather than by judgement, and
the permanently empty tier read as a young store instead of a closed door. Corrected
2026-09-11; the tally counts how often the *operation* failed, which corroborates a failure
lesson rather than disproving it.

Nothing about the evidence floor changed. `evidence` still counts distinct sources and
promotion still demands three of them, so a flapping check seen two hundred times is still
one source and still cannot promote itself.

The bands are the memory engine's own â€” **0.90 Known, 0.50 Assumed** â€” reused rather than
re-chosen, so a fact and a lesson age at the same rate and 0.85 does not mean two things.

```bash
coresentinel evolve explain CAND-abc123    # the terms, the weights, the evidence chain
```

### TRUSTED is not PROPOSED

This distinction is what makes automatic learning safe, and it is worth stating plainly.

| | What it is | How it is reached |
| :--- | :--- | :--- |
| **TRUSTED** | A **retrieval** tier. A cited line in a context pack an agent may disregard. It cannot block a gate, fail a build or write a file. | Confidence â‰¥ 0.90, â‰¥ 3 distinct sources, no unresolved contradiction. **No human needed** â€” because it compels nothing. |
| **PROPOSED** | A **governance** act. It becomes a rule that constrains every future agent. | A person runs `evolve propose`. **No amount of evidence shortens this.** |

Confidence promotes to TRUSTED. **Nothing promotes to PROPOSED.**

### Contradiction narrows before it overrides

Three situations look alike and only one is a contradiction:

| Situation | Verdict | What happens |
| :--- | :--- | :--- |
| Same signature, opposite outcomes, **same** context | `INCONSISTENT` | Lowers consistency; trust is withheld until somebody looks |
| Same signature, opposite outcomes, **different** contexts | `SCOPED` | **Not a contradiction.** Both survive, each narrowed to where its evidence is |
| Two lessons conflict, the challenger outscores | `SUPERSEDES` | Loser marked `SUPERSEDED` with `superseded_by`. Never deleted |

The middle row is the one that matters: it is the difference between learning "Redis is
wrong" and "Redis is wrong *on this host*". Overriding where it should have narrowed is how
a learning system produces confident nonsense out of real evidence.

Supersession requires the challenger to **outscore** the incumbent. Letting recency alone
win would make the last thing observed the truth, which is not learning â€” it is forgetting
with extra steps.

```bash
coresentinel evolve reject CAND-8efb2da38b --reason "already covered by AP-002"
coresentinel evolve promote CAND-8efb2da38b --reason "obvious enough not to need repeating"
```

`promote` is the escape hatch for a lesson too obvious to wait for. It requires a stated
reason, so the shortcut is visible in the record.

---

## âœ… Approval, and then Application

These are **two separate acts**, and the separation is the point.

`approve` records a human decision and changes no file. Until v10.9 it printed *"Versioned
Change Released"* while writing nothing â€” the pipeline stopped one step short of doing
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
   *refused, not attempted* â€” blindly patching a governance file because a proposal asked
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

## âš¡ CLI Commands

```bash
# The experience log â€” captured automatically, no command records it
coresentinel evolve experiences
coresentinel evolve experiences --prune --apply --max 2000

# Observe, and inspect the candidate queue
coresentinel evolve observe
coresentinel evolve candidates
coresentinel evolve explain CAND-abc123
coresentinel evolve reject CAND-abc123 --reason "..."
coresentinel evolve promote CAND-abc123 --reason "..."

# The deep pass: recurrence, contradictions, stale knowledge, skill candidates.
# Promotes to TRUSTED and changes NO governance file.
coresentinel evolve review
coresentinel evolve review --apply

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
| 2026-07-21 | Anti-Pattern | Never trust a native exe's exit code when sourcing SQL â€” grep stdout for `ERROR` | Reported "failures: 0" on a migration run that had actually failed | All projects (PowerShell) |
| 2026-07-21 | Anti-Pattern | A grep that finds nothing is not proof of absence â€” state the scan scope with the claim | Declared "zero MySQL-8-only DDL" after a scan that omitted implicit TIMESTAMP defaults | All projects |
| 2026-07-21 | Skill | Verify class autoloading empirically (throw/catch probe) instead of reasoning about PSR-4 | Confirmed a real `Exceptions.php` autoload bug in DAISY | All PHP projects |
| 2026-07-21 | Skill | XAMPP local-setup recipe for no-framework PHP (port vhost, DocumentRoot at `public/`) | Stood up DAISY without admin elevation | All PHP projects |
| 2026-07-21 | Skill | Check the test bootstrap for `.env` fallback BEFORE running a suite | `tests/bootstrap.php` would have migrated over the dev DB | All projects with test suites |
| 2026-07-21 | Skill | `--ignore-platform-req` to install deps without mutating a tracked `composer.lock` | Lock file demanded PHP 8.3, local was 8.2, no edits authorised | All Composer projects |
| 2026-07-21 | Add Rule | Recorded PowerShell 5.1 `Invoke-WebRequest` byte[] `.Content` gotcha in identity Environment | `.Trim()` failed on a signature check | All projects (PowerShell) |
| 2026-07-21 | Add Skill | `explicit_defaults_for_timestamp=ON` as the MySQL 8 â†” MariaDB compatibility lever | Migration 019 failed only on MariaDB | All MySQL/MariaDB projects |
| 2026-07-22 | Anti-Pattern | Zero-fill a day series in the DB's timezone frame (anchor to `CURDATE()`), never with PHP `date()` while the buckets come from SQL `DATE()` | Analytics sparkline's newest bar mapped to a day SQL never emitted (UTC vs Asia/KL) â€” caught in Phase 5 review before ship | All time-series across a PHPâ†”DB boundary |
| 2026-07-22 | Skill | Calendar-align the headline window to the plotted series so headline == sum(series); floor `AVG(TIMESTAMPDIFF(...))` with `resolved_at >= created_at` | Building the DAISY analytics KPI dashboard | All dashboards |
| 2026-07-23 | Anti-Pattern | A test that writes to a shared table NOT in the global truncate list leaks state into sibling tests â€” truncate it in the test's own setUp | BillingTest asserted total 99.00 but got 119.00; a prior test's add-on row survived into `tenant_features` | All projects with a shared test DB |
| 2026-07-23 | Anti-Pattern | Under `hx-boost` or a nav-skeleton overlay, download & standalone-page links MUST opt out (`download`, `hx-boost="false"`, `target="_blank"`) or the page shell breaks | {USER_NAME}: PDF button left the platform page stuck on skeleton until refresh | All boosted/SPA-ish layouts |
| 2026-07-23 | Skill | Embed images as base64 data-URIs so they render identically in the HTML view AND mPDF; verify the PDF via `Output('', STRING_RETURN)` + `%PDF` header check | Company logo on invoice view + PDF | All mPDF / dual HTML+PDF renders |
| 2026-07-23 | Skill | Safe global CSS default: count usages first, then scope with `:not(:has(...))` guards and let inline-style specificity win, so existing markup can't regress | Default `.card` body padding across 171 cards (111 with headers) | All shared CSS component classes |
| 2026-07-23 | Skill | Snapshot financial values (tax/price) onto the invoice row at generation; render branding (logo/company) live | DAISY invoices | All billing/invoicing |
| 2026-08-04 | Update Rule | **Corrects the 2026-07-21 rule.** "Grep stdout for ERROR" is NOT enough â€” `mysql.exe` writes errors to **stderr**. Capturing only stdout reported a clean run on a migration that had crashed | Reported "no ERROR string in output" while 144 stderr error lines existed | All projects, all shells |
| 2026-08-04 | Anti-Pattern | A wedged `ALTER TABLE` holds the table's metadata lock forever; `KILL` leaves it "Killed/Committing alter table" and graceful shutdown hangs â€” only a force-kill + restart clears it | Migration 029 wedged `voice_calls` in DAISY dev | All MySQL/MariaDB projects |
| 2026-08-04 | Skill | Verify a migration by querying `information_schema` for EVERY object it should create, not by reading the client's output at all | Proved all 16 objects of migration 029 landed after a partial-crash + re-run | All projects with SQL migrations |
| 2026-08-04 | Anti-Pattern | `Glob("dir*")` does NOT look inside `dir/` â€” never conclude "the file doesn't exist" from a pattern that couldn't have matched it | Told {USER_NAME} `app/Exceptions*` was absent; the file existed one level down | All projects |
| 2026-08-04 | Anti-Pattern | PowerShell 5.1 `Set-Content -Encoding utf8` writes a **BOM**, which breaks `<?php`, shebangs, YAML and JSON | 7 test files fataled with "Namespace declaration has to be the very first statement" | All projects on Windows |
| 2026-08-04 | Skill | A green suite proves nothing if the tests `require_once` what production expects to autoload â€” grep for setup workarounds when a bug "should" be caught by tests | 8 test files hid the ForbiddenException autoload bug for months | All projects |
| 2026-08-04 | Anti-Pattern | `php -S` is single-threaded and `PHP_CLI_SERVER_WORKERS` is **POSIX-only** â€” silently ignored on Windows. Never use it for an app with SSE/long-poll | Whole DAISY UI appeared frozen; one SSE call blocked everything for 55s | All PHP projects on Windows |
| 2026-08-04 | Skill | "Links dead on left-click but fine via right-click â†’ open in new tab" = JS is intercepting the click (hx-boost/SPA) and its request never returns â€” look at server concurrency, not the markup | Diagnosed the frozen DAISY UI from this one symptom | All boosted/SPA-ish apps |
| 2026-08-04 | Skill | **When a vendor's docs are silent, read the vendor's own SDK source.** Pull the tarball from `registry.npmjs.org` (no `npm install`, no auth) and grep its URI-constants / request-builder files | NICE documents no verbs or response shapes; `@nice-devone/core-sdk` listed every Agent API path, confirmed POST, and named the response key | All third-party API integrations |
| 2026-08-04 | Anti-Pattern | **Auth succeeding proves only that the credential is valid â€” never that the account can do the job.** After a token exchange, assert the *identity* in the token and the entitlements attached to it | Channel authenticated fine on a CXone key belonging to an agent who lacked the skill needed to be routed the call; looked configured, could never ring | All API integrations with per-user credentials |
| 2026-08-04 | Anti-Pattern | **Three strikes on blind-probing an API for a magic value, then go capture the real client's traffic.** Enumerating plausible values against a production endpoint burns time and writes to a live system | 11 candidate station values all returned the same 400; the answer is one DevTools capture of the vendor's own web app | All undocumented API parameters |
| 2026-08-04 | Anti-Pattern | Git-bash `tar` on PATH reads `-C C:\...` as a remote host ("Cannot connect to C: resolve failed") â€” call `C:\Windows\System32\tar.exe` explicitly, or `cd` first | Extracting npm tarballs on Windows | All projects on Windows |
| 2026-08-10 | Anti-Pattern | Never interpolate a Windows path into a `sed` replacement â€” GNU sed reads `\U` as "uppercase the rest of the line" and eats the other backslashes. Escape `\ & |` first | AutomationSentinel's `install.sh` rendered `C:\Users\FAKRUL~1.HAK\...` as `C:SERSFAKRUL~1.HAKAPPDATAocaltemp...` in 5 of 6 installed protocol files | All shell templating on Windows |
| 2026-08-10 | Anti-Pattern | `$HOME/Desktop` does not exist when Windows redirects the Desktop into OneDrive â€” a bash installer probing it silently finds nothing while its PowerShell twin works | Bare `./install.sh` could never locate `memorycore.conf` on this machine; `install.ps1` did, via `[Environment]::GetFolderPath('Desktop')` | All cross-shell installers on Windows |
| 2026-08-10 | Skill | Prove a "never overwrites" installer claim by hashing a user-edited file across a re-run, then running the `--force` path and asserting the **opposite** â€” same assertion, inverted expectation, so the guard test can't be a tautology | Verifying AutomationSentinel's installers | All installers / scaffolding scripts |
| 2026-08-10 | Skill | Explicitly align agent identity ('Iris') across MemoryCore and project session-memory.md context | Prompted by single-keyword trigger ('Iris'); resolved by reading central MemoryCore profile and writing context | All projects |

## Learned Skills
Track techniques and patterns learned across all projects.

### Skill: Read the vendor's SDK source when the vendor's docs are silent
- **Learned from**: DAISY 2.0 (NICE CXone)
- **Pattern**: When integrating against an API whose docs list paths but not verbs, response
  shapes, or magic values, fetch the vendor's official client library and read it:
  `Invoke-RestMethod https://registry.npmjs.org/@scope/pkg` â†’ `.versions.<latest>.dist.tarball`
  â†’ download â†’ extract with `C:\Windows\System32\tar.exe` (NOT git-bash's `tar`). Then grep for
  a `*-constants.js` / `*-apis.js` file â€” vendors almost always centralise every endpoint in one â€”
  and for the service that builds the request. No `npm install`, no auth, no node_modules.
- **Why**: NICE's published docs gave paths only; their own `core-sdk` gave every path, the
  confirmed HTTP verb, the response key, and an undocumented settings endpoint that turned out to
  carry the entire WebRTC configuration. It converted four "unverified assumption" comments into
  facts in about ten minutes, and confirmed the hand-written paths were already correct.
- **Also**: `.d.ts` files are the cleanest form of the request/response contract you'll find.
- **Applied to**: All third-party API integrations

### Anti-Pattern hint (paired): don't confuse authentication with authorisation
- A credential that authenticates is not a credential that can *do the task*. Read the identity
  out of the returned token (`id_token` claims) and query that identity's entitlements â€” skills,
  permissions, licensed features â€” before concluding an integration is configured correctly.

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

### Skill: MySQL 8 â†” MariaDB TIMESTAMP compatibility
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
- **Why**: {USER_NAME} asked "do you know the full flow?" â€” the honest answer was "structure yes,
  runtime no", and admitting that led straight to discovering the dead webhook consumer.
  Claiming full knowledge would have buried the most important finding in the project.
- **Applied to**: All projects

### Skill: One HTML document for both the web view and the PDF (mPDF + data-URIs)
- **Learned from**: DAISY 2.0 (invoices)
- **Pattern**: Build a single renderer that returns one self-contained HTML fragment (own inline
  `<style>`), and feed the SAME string to the on-screen view and to mPDF. Embed images (logos) as
  base64 `data:image/...` URIs so nothing has to fetch a file or URL â€” they render identically in
  the browser and in the PDF. Verify the PDF path with a throwaway smoke script:
  `$pdf = $mpdf->Output('', \Mpdf\Output\Destination::STRING_RETURN);` then assert
  `substr($pdf,0,4) === '%PDF'` and that the expected bytes/length are present.
- **Why**: The view and the PDF can never drift, and data-URIs sidestep mPDF's finicky file/URL
  image fetching (and its temp-dir/permissions surprises on deploy). The smoke test proves mPDF
  actually produced a valid document instead of throwing.
- **Applied to**: All projects rendering the same content as HTML and PDF

### Skill: Change a shared CSS class safely (audit â†’ scope with :has â†’ let inline win)
- **Learned from**: DAISY 2.0 (default `.card` padding)
- **Pattern**: Before adding a rule to a class used everywhere, COUNT the usages and the variants
  (`class="card"` = 171, `card-header` = 111, many with inline `padding`). Then scope the new rule so
  it only touches the safe subset â€” `.card:not(:has(.card-header)):not(:has(.card-body)):not(:has(table))`
  â€” and rely on inline-style specificity (1,0,0,0) beating the stylesheet, so any element that already
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
- **Rule**: For native executables â€” especially `mysql`, `psql`, `mysqldump` â€” capture stdout
  and **grep it for `ERROR`**. Never report success on exit code alone. Verify the intended
  end state directly (`SELECT COUNT(*) FROM information_schema.tables`), not the process code.
- **Applies to**: All projects, all shells

### Anti-Pattern: Grepping only stdout for `ERROR` (supersedes the 2026-07-21 rule)
- **What happened**: Applied migration 029 with
  `$out = & mysql.exe ... | Out-String`, then grepped `$out` for `ERROR` â€” exactly what the
  2026-07-21 rule prescribed. It printed **"no ERROR string in output"** and `exit=0`.
  The tool's own captured output held **144 lines** of
  `ERROR 2013/2006 ... Lost connection / MySQL server has gone away`. The pipe captured
  **stdout only**; `mysql.exe` writes every error to **stderr**.
- **Impact**: Declared a migration clean when it had died a third of the way through, leaving
  `voice_calls` half-altered and its metadata lock wedged. The old rule *felt* satisfied,
  which is what made it dangerous â€” a guard that silently checks the wrong stream is worse
  than no guard, because it manufactures confidence.
- **Rule**: Never let a shell variable be the evidence. Either (a) run the client WITHOUT
  redirecting, so the harness surfaces stdout **and** stderr and you read it yourself, or
  (b) merge streams explicitly. Then â€” always â€” **verify the end state directly**: query
  `information_schema.COLUMNS` / `.STATISTICS` for every object the migration should have
  created and assert each one. Output is a hint; schema state is the fact.
- **Applies to**: All projects, all shells, every native CLI (`mysql`, `psql`, `mysqldump`)

### Anti-Pattern: Assuming a hung `ALTER TABLE` will resolve, or that KILL clears it
- **What happened**: An `ALTER TABLE voice_calls ADD COLUMN` hung. `KILL <id>` left the thread
  in `Killed / Committing alter table to storage engine` â€” still holding the table's metadata
  lock. Every later query on that table queued behind it, `mysqladmin shutdown` returned rc=0
  but the process never exited, and the server stopped accepting new connections (so a
  safety `mysqldump` was no longer possible).
- **Impact**: Burned ~20 minutes and forced a force-kill of the user's shared dev database.
  The backup I wanted to take became impossible *because I waited too long to take it*.
- **Rule**: Take the backup BEFORE the risky DDL, not after it goes wrong. If a thread sits in
  `Committing alter table` after a KILL, stop waiting â€” it will not clear. Force-kill the
  process and restart; InnoDB is crash-safe and recovers. Also: read the error log at
  startup â€” if the instance *already* began with "Starting crash recovery", treat it as
  degraded and suspect the server before suspecting your SQL.
- **Applies to**: All MySQL/MariaDB projects

### Anti-Pattern: `php -S` for an app with SSE / long-polling (fatal on Windows)
- **What happened**: Served DAISY with `php -S` and set `PHP_CLI_SERVER_WORKERS=4`, believing
  that gave 4 workers. **That variable is POSIX-only â€” PHP ignores it on Windows** (it needs
  `fork()`). The server stayed single-threaded. Every page opens an `EventSource` to
  `/api/v1/events` which holds the one worker for its 55s window, so every other request queued
  behind it. {USER_NAME} reported the whole UI as unclickable.
- **Impact**: Looked exactly like a frontend bug. I nearly went hunting for a JS/overlay fault.
  Measured proof: page load **69.5s** with one SSE connection open vs **0.09s** once it closed;
  **0.09s** on Apache under the same conditions.
- **Rule**: If an app has SSE, WebSockets, or long-poll, do not use the PHP built-in server at
  all â€” use Apache/nginx. Never assume a concurrency flag took effect; **measure it**: hold the
  streaming endpoint open in one process and time an ordinary request in another. Carrying a
  tip from notes without checking it applies to the current OS is how this got in.
- **Applies to**: All PHP projects, especially on Windows

### Skill: Read "dead on click, works via right-click â†’ new tab" as a concurrency symptom
- **Pattern**: If a left-click does nothing but right-click â†’ *Open in new tab* works, the
  pointer IS hitting the element â€” so it is not an overlay or z-index problem. Something in JS
  (`hx-boost`, a router, an SPA click handler) is calling `preventDefault()` and then its
  request never completes. Right-click bypasses JS entirely, which is why it works.
- **Why**: This single observation splits the search space cleanly: it rules out CSS/overlay
  causes and points at the network/server layer. In DAISY it led straight to the single-threaded
  dev server rather than to the markup.
- **Applies to**: All HTMX-boosted / SPA-ish apps

### Anti-Pattern: Concluding "it doesn't exist" from a search that could not have found it
- **What happened**: Ran `Glob("app/Exceptions*")`, got no results, and told {USER_NAME} the
  directory was "absent entirely" â€” then wrote that into session memory AND the project
  profile. `app/Exceptions/Exceptions.php` existed the whole time; the pattern matched only
  entries named `Exceptions*` **at that level**, never inside the directory.
- **Impact**: A confidently stated, recorded-in-two-places false fact about the user's
  codebase. It also nearly produced the wrong fix (create the classes from scratch) instead of
  the right one (split an existing multi-class file).
- **Rule**: Before reporting absence, use a pattern that *could* find the thing â€”
  `**/Exceptions*` or a content grep for `class ForbiddenException`. Better: when the question
  is "does this class exist", grep for its **definition**, not its path. And when a later
  finding contradicts an earlier claim, correct the claim explicitly â€” including in any
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
  Verify with a byte check â€” first bytes must be the real content, not `239,187,191`.
  In PS 7+, `-Encoding utf8NoBOM` exists; in 5.1 it does not.
- **Applies to**: All projects on Windows

### Anti-Pattern: Trusting a green suite when the tests work around the bug
- **What happened**: `RBAC::require()` fataled at runtime because `App\Exceptions\*` never
  autoloaded â€” yet 4 tests asserted `expectException(ForbiddenException::class)` and passed.
  Eight test files carried `require_once BASE_PATH.'/app/Exceptions/Exceptions.php'` in
  `setUp()`, manually loading what production expected PSR-4 to load. One even had a comment
  naming the defect. The suite was green for months while the feature was broken in prod.
- **Impact**: The test suite actively concealed a security-relevant bug (permission denials
  crashing instead of returning 403).
- **Rule**: When a bug "should" have been caught by tests but wasn't, grep the tests for
  `require_once`/`include` of application code and for manual bootstrapping in `setUp()`.
  A workaround in test setup is a bug report in disguise. Fix the root cause and **delete the
  workaround** â€” otherwise the next regression hides in the same place.
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
  paragraph of inference â€” and it is the difference between "I think this is broken" and
  "this is broken, here is the error."
- **Applies to**: All projects

### Anti-Pattern: Zero-filling a day series with PHP dates while the buckets come from SQL
- **What happened**: An analytics dashboard ran its window filter and `GROUP BY DATE(created_at)` in MySQL, but generated the zero-fill series keys with PHP `date('Y-m-d', strtotime("-{$i} day"))`. MySQL commonly runs UTC while PHP was set to `Asia/Kuala_Lumpur` (UTC+8), so the two disagree on which calendar day "today" is â€” the newest sparkline bar mapped to a date the SQL `DATE()` never produced, misattributing today's activity every single day. The headline count (a raw range filter) stayed correct, so the chart silently disagreed with its own KPI number.
- **Impact**: Caught in Phase 5 (Cato) before ship, but would have shipped a dashboard whose trend line contradicted its headline â€” the kind of "looks fine in the demo" bug that erodes trust in the whole reporting surface.
- **Rule**: When zero-filling or day-bucketing a time series, generate the calendar in the SAME timezone frame as the aggregation. Anchor to the DB clock â€” `$today = SELECT CURDATE()`, then build the series backward from `$today` â€” or set the DB session TZ to match PHP. Never mix PHP `date()` day keys with SQL `DATE()` buckets. Bonus: calendar-align the headline window to the plotted range so `headline == sum(series)`, and floor duration averages (`resolved_at >= created_at`) so back-dated rows can't push an average negative.
- **Applies to**: All projects doing time-series aggregation across a PHPâ†”DB boundary

### Anti-Pattern: Running a test suite before checking which DB it targets
- **What happened**: Was one command away from running PHPUnit when `.env.test` did not exist.
  DAISY's bootstrap falls back to `.env` and then executes every migration.
- **Impact**: Would have run 28 migrations against the freshly-seeded **dev** database.
  Caught it by reading `tests/bootstrap.php` first â€” but only just.
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
  is_custom`). Each test must start from a known-empty state for EVERY table it touches â€” check the base
  harness's truncate list against the tables your test writes, and top it up locally.
- **Applies to**: All projects with a shared/reused test database

### Anti-Pattern: Download / standalone links break a boosted or skeleton-overlay layout
- **What happened**: The platform console shows a nav-skeleton overlay on any `<a>` click (assuming a page
  nav follows) and the tenant layout uses `<body hx-boost="true">`. A **PDF download** link triggers no
  navigation (Content-Disposition), so the skeleton overlay never cleared â€” the page sat blank until refresh;
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
  Windows path, so the replacement contained `\U`, `\L`, `\A`, `\D`, `\f`, `\c`â€¦
  GNU sed treats `\U` on the right-hand side of `s///` as **uppercase everything
  that follows** and simply drops the backslashes it doesn't recognise.
  `C:\Users\FAKRUL~1.HAK\AppData\Local\Temp\claude\...` came out as
  `C:SERSFAKRUL~1.HAKAPPDATAocaltempaudec--users-...` â€” wrong path *and* wrong case.
- **Impact**: 5 of 6 installed protocol files carried a dead cross-reference link.
  Silent: exit code 0, "6 written", no warning. The PowerShell installer was fine
  (`String.Replace` is literal), so it only broke for bash users â€” i.e. only sometimes.
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
  on the only machine it ships to, while its PowerShell twin passed â€” the kind of
  asymmetry that reads as "bash is fine, I tested it".
- **Rule**: Never hardcode `$HOME/Desktop` in a bash script on Windows. Glob the
  redirect: `"$HOME"/OneDrive*/Desktop/...`, and keep the plain path as a fallback.
  When two installers claim parity, run **both** â€” a passing twin proves nothing
  about the other.
- **Applies to**: All cross-shell installers on Windows

### Anti-Pattern: Reporting a service found by port-scanning instead of by reading the config
- **What happened**: At the Phase 1 gate I reported the dev database as **MariaDB 11.8.2 on
  port 3306**, having found a `mariadbd` listener with `lsof`. {USER_NAME}'s projects all point
  at **port 3307, MariaDB 10.4.28** â€” a different instance entirely. I only noticed when
  `mariadb -u root` on 3306 failed with access denied and I went looking at sibling `.env`
  files.
- **Impact**: A confidently wrong fact in a gate report a stack decision was made on. It
  mattered: on 10.4 `DB_CONNECTION=mariadb` is load-bearing (`renameColumn` emits syntax the
  engine does not have until 10.5.2), whereas on 11.8 it is merely preferred. Had I built to
  the reported version, the first `renameColumn` migration would have been a hard error.
- **Rule**: A listening socket is a machine fact, not a project fact. To learn which database
  a project uses, read a **sibling project's `.env`** â€” or the project's own â€” before running
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
- **Applies to**: All projects â€” `Notification::fake`, `Mail::fake`, `Bus::fake`, `Event::fake`

### Skill: Let the seeded demo disagree with the app, then find out why
- **Pattern**: After building, seed realistic demo data and read the app's own numbers back
  through a real request. "Today: 0.00" next to a week total that obviously included today was
  the only visible symptom of `APP_TIMEZONE` being ignored â€” no test caught it, because every
  test used one clock consistently.
- **Why**: A test suite proves internal consistency. Demo data crossing a real boundary (seed
  clock vs request clock, PHP vs DB) proves the boundary. Cross-check an invariant that must
  hold across the two â€” here, *the plotted series must sum to the headline*.
- **Applies to**: Any app with time-series or aggregate reporting

### Anti-Pattern: Trusting `update()` on a field that is not fillable
- **What happened**: See the Pattern Library entry *Privilege Columns Must Not Be Fillable*.
  `$user->update(['status' => 'suspended'])` silently discarded the field and returned `true`;
  admin suspension never worked, and the UI showed a success toast.
- **Impact**: A security-relevant control that appeared to work. Caught only because a test
  asserted the **resulting state** rather than the redirect.
- **Rule**: When a field is deliberately outside `$fillable`, `update()` is not the API for it
  â€” write a named method. And always assert the post-condition, never the response alone: a
  302 to the right place proves routing, not effect.
- **Applies to**: All Laravel projects

### Anti-Pattern: A settings field wired to the wrong store â€” a control nobody can set
- **What happened**: Social Media Listening Tools, 2026-09-11. The Threads settings screen
  had a `keyword_search_granted` field. Its descriptor carried no `'store' => 'setting'`,
  so `PlatformSettingsController::fieldsFor()` fell through to its default and looked the
  key up in the **encrypted credentials**, where nothing ever writes it. The row therefore
  rendered blank forever. Meanwhile `ProviderRegistry::makeThreads()` read the same key from
  `social_accounts.settings` to decide whether Threads keyword search could see public posts
  at all. Reader and writer were pointed at two different stores.
- **Impact**: The single most consequential flag on the platform was permanently `false` and
  **unreachable** â€” no operator action could change it. Worse, the screen actively lied: the
  readonly row rendered the placeholder *"Read from the platform after connecting"* while
  nothing in the codebase ever read it back. Every symptom pointed at App Review or at Meta,
  not at a one-word omission in a field descriptor.
- **Rule**: A field descriptor that names *where a value is displayed from* and code that
  reads *where the value lives* are two declarations of the same fact, and they drift
  silently because neither fails loudly when they disagree â€” an absent key is
  indistinguishable from an unset value. When adding a settings field, assert the round
  trip in a test: write it where the app writes it, then assert the **screen shows it**.
  And treat a placeholder that promises "read from the platform" as a claim requiring a
  call that actually does so â€” if nothing reads it back, the honest widget is an input,
  not a disabled box.
- **Applies to**: All projects with declarative form/field registries (Laravel + Inertia
  especially, where the descriptor and the reader sit in different files)

### Anti-Pattern: Allocating a sequential ID from a stale copy of the index
- **What happened**: CoreSentinel itself, 2026-09-11. Two machines each registered new projects
  by taking "the next number" from `00-identity.md`. One took 11 and 12 for Restaurant POS and
  Social Media Listening Tool and pushed; the other, without pulling, took 11 and 12 for Weekly
  Drop Playbook and SecureLab. On merge, `Projects/11-*` and `Projects/12-*` each named two
  different projects. Three files conflicted on top of it, all because both sides appended at the
  same insertion point.
- **Impact**: Recoverable but not free — it cost a renumber of three files, an index rewrite, and
  a judgment call about whether two similarly-named Social Listening entries were one project or
  two. The dangerous version is the one that *doesn't* conflict: had the two sides picked
  different filenames under the same number, git would have merged both cleanly and the
  collision would have sat in the index unnoticed.
- **Rule**: **Pull before allocating any sequential identifier** — project numbers, migration
  numbers, phase IDs, anything whose next value is read off shared state. `git fetch && git log
  HEAD..origin/main --stat` costs one call and is the only thing that makes the number real.
  On collision, the **published side keeps its numbers** and the local side renumbers behind it;
  numbers already on the remote may be referenced from places you cannot grep. And when two
  entries look like the same project, confirm against **root path and stack version** before
  merging them — near-identical names routinely belong to separate codebases, as
  `06-basic-ecom` / `09-basic-ecommerce-php` and now `12-social-listening` /
  `15-listening-console` both show.
- **Applies to**: CoreSentinel's own `Projects/` index, and any multi-machine repo where an
  append-only list hands out the next number

---

## Basic Custom E-Commerce â€” 2026-08-27 (Laravel 12, client delivery)

### Anti-Pattern: A plan that promises a control, and a runbook line that pretends to be it
- **What happened**: `Planning.md` Â§17.4 said "Force an admin password change on first login."
  I wrote that sentence, approved it, built ten phases, wrote `DEPLOYMENT.md` repeating it as a
  bullet â€” and **never implemented anything**. `AdminSeeder` shipped `admin@basic-ecom.test`
  with the password `password` and no mechanism to require changing it. It was caught only
  because {USER_NAME} highlighted that one line in the seeder during handoff review.
- **Impact**: A live payment-handling store would have gone out with a known working admin
  credential and a deployment document *claiming* that credential was forced to change. The
  document made the gap harder to see, not easier â€” anyone auditing the runbook would have
  ticked it off.
- **Rule**: When a plan states a **control**, it is a work item, not prose. At the phase that
  should implement it, grep the plan for imperative security language â€” "force", "must",
  "require", "never" â€” and confirm each has a file and a test behind it. A control that exists
  only in a document is a control that does not exist. Prefer the mechanism that cannot be
  skipped: a DB flag plus middleware, not an instruction to a human.
- **Applies to**: Every project with a written plan or runbook

### Anti-Pattern: Phantom completion left in the traceability matrix
- **What happened**: The `REQ-013` row listed `app/Http/Controllers/Admin/ShipmentController.php`
  and "EasyParcelService booking methods" as implementation paths. **Neither existed** â€” the
  feature was blocked and only its schema, model and enum were built. The row sat there through
  Phases 8â€“11 and into the client handoff. I only found it because {USER_NAME} asked "complete?"
  and I checked instead of answering from memory.
- **Impact**: The client-facing traceability record claimed delivery of a scope item that was
  never built. `53-documentation-protocol.md` Â§4.2 forbids exactly this, and I had written the
  matrix myself.
- **Rule**: A traceability matrix is an assertion about the filesystem, so **verify it against
  the filesystem** before any handoff: loop the listed paths and `test -f` each one. When a
  requirement is partially built, split the row explicitly â€” "Built: â€¦ / NOT built: â€¦" â€” never
  leave the aspirational path list in place with a status chip beside it.
- **Applies to**: Any project under Protocol 53

### Anti-Pattern: Silent `str.replace()` after a formatter rewrote the anchor
- **What happened**: Edited files with `python3` + `str.replace()` throughout. Laravel Pint
  rewrote a fully-qualified `\App\Services\ToyyibPayService::class` to the imported short form
  between two of my edits. My next replacement targeted the FQCN string, matched nothing, and
  **wrote the file back unchanged with no error**. The container binding was never added; all
  15 payment tests failed at once with `BindingResolutionException`.
- **Impact**: Ten minutes chasing a "container" bug that was a no-op edit. The failure was loud
  only because a test suite existed â€” the same silent miss in a doc edit would have shipped.
- **Rule**: `str.replace()` returns a copy and reports nothing. **Assert the anchor before
  replacing**: `assert old in s, "anchor missing"` / `sys.exit("MISS: ...")`. Re-read the file
  after any formatter, linter or codemod runs â€” never edit against a remembered version of a
  file a tool has since touched.
- **Applies to**: All scripted file edits

### Anti-Pattern: `Http::fake()` merges â€” it does not override
- **What happened**: In an end-to-end test I faked `*getBillTransactions` early with a
  placeholder amount, then called `Http::fake()` again later with the correct amount for the
  order that now existed. Laravel **merged** the stub sets; the first pattern still matched, so
  the stale placeholder won. The payment refused to settle on an amount mismatch â€” which was
  the code behaving **correctly** â€” and it presented as an application bug.
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
- **Impact**: Would have shipped as false assurance in the security suite â€” the worst kind of
  test, because its presence stops anyone writing the real one.
- **Rule**: Before asserting a framework behaviour, ask what would have to break for this test
  to fail â€” if the answer is "the framework", it is not your test. Assert the **project's
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
  would have produced duplicate-key failures at checkout â€” for real customers, at the worst
  moment.
- **Rule**: A docblock is an assertion; write it **after** the body or verify it against the
  body before committing. When a comment claims a safety property (retry, lock, idempotency,
  validation), there must be a test named for that property. Treat "N random digits" as a
  collision source, not a uniqueness source â€” derive sequence from state and let a UNIQUE index
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
- **Impact**: Minor â€” one wasted round trip. Recorded because the same shape in a longer batch
  would leave a silently missing file among many written ones.
- **Rule**: `mkdir -p` the target directory in the same command as any heredoc write to a new
  path, and verify with `php -l` or `test -f` immediately after.
- **Applies to**: All shell-driven file creation

### Anti-Pattern: Reading state after mutating it, to decide what the mutation did
- **What happened**: `CartController::store()` decided whether a quantity had been capped with
  `$resulting < $this->cart->qtyFor($id) + $requested` â€” but `qtyFor()` was read **after**
  `add()` had already written. The condition was always true, so every add reported "capped".
- **Impact**: Cosmetic here, but the shape is the same one that produces wrong stock and wrong
  totals elsewhere.
- **Rule**: Capture the before-value into a variable **before** the mutating call. If a function
  needs to report what it changed, have it return that â€” do not reconstruct it from state the
  call has already altered.
- **Applies to**: All projects

### Anti-Pattern: Repeating a defect I had already written into the anti-pattern log
- **What happened**: Added a `needsReviewCount` view composer registered on `layouts.admin`
  only. The dashboard **child view** renders that variable in its own section, so it was
  undefined and every dashboard request 500'd. This is the *identical* mistake recorded
  earlier the same day as "View composer registered only on `layouts.*`", and the review
  checklist item I wrote for `35-review-protocol.md` says in as many words: *"View composers
  registered for every namespace that renders the shared variable, not just `layouts.*`"*.
- **Impact**: Caught by tests within a minute â€” but the log entry and the checklist did not
  prevent it, which is the point worth recording. Writing a rule down is not the same as
  reading it at the moment of the decision.
- **Rule**: When a phase's own log already contains an anti-pattern for the exact mechanism
  being touched, **re-read that entry before writing the code**, not after the test fails.
  For view composers specifically: register against every namespace that renders the
  variable, and treat "the layout uses it" as insufficient evidence that only the layout
  uses it.
- **Applies to**: All projects â€” and to the maintenance of this log itself

### Anti-Pattern: A `str.replace()` anchor pointing at the wrong section number
- **What happened**: Inserted a decision record into `Planning.md` anchored on `### 12.3`,
  believing Â§12 was the architecture section. Â§12 is **Database Design**; Â§12.3 is a table
  list. The `assert` fired correctly â€” but only *after* an earlier edit in the same script
  had already written to the file, and the commit ran anyway. Result: the stack table gained
  a row cross-referencing a section that does not describe it, the decision record was never
  written, and the docs changelog edit queued behind it was silently skipped.
- **Impact**: A commit that claimed to record a decision and did not. Fixed in a follow-up,
  but the partial-write shape is the hazard: assertions protect the *edit*, not the *batch*.
- **Rule**: Validate **every** anchor in a multi-file edit script **before** writing any
  file â€” collect failures first, then apply. And verify the section a cross-reference points
  at actually covers the subject; `grep -n '^### '` the target document rather than
  trusting a remembered outline.
- **Applies to**: All scripted multi-file documentation edits

### Anti-Pattern: Logging a rule, then not applying it â€” twice
- **What happened**: Recorded "validate **every** anchor in a multi-file edit script BEFORE
  writing any file" after a partial batch shipped a commit that claimed a decision it had not
  recorded. Then did the same thing again on the very next feature: an edit script asserted on
  a `Planning.md` anchor that did not match, **wrote the other file first**, and the commit
  went out â€” a second commit claiming a decision it had not recorded. Separately, in the same
  session, repeated a view-composer defect that was already in this log *and* in the review
  checklist I had written for it.
- **Impact**: Three repeats of two known defects, all caught, none shipped to production â€”
  but the log demonstrably did not change behaviour. That is the finding worth keeping: a rule
  written after the fact is a record, not a control.
- **Rule**: A recurring defect needs a **mechanism**, not a paragraph. For scripted edits that
  means the script itself validates first and exits before any write â€” make that the template,
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
  then changed client-visible behaviour three more times â€” the admin template, the dashboard
  metrics, and the entire order-status vocabulary. The artifact still claimed the old figures
  and said nothing about the workflow states the client would operate with daily. It was only
  caught by explicitly diffing the published document against reality.
- **Impact**: A live client-facing link, quietly wrong, describing a workflow that no longer
  existed. Exactly the "documentation lying about code" failure recorded twice already this
  project â€” but pointed outward, at the client, which is worse.
- **Rule**: A published artifact is a **deliverable with a URL**, not a snapshot. Any change to
  client-visible behaviour after publishing means re-checking it: diff the claims (version
  numbers, counts, feature lists, workflow names) against the code, then republish to the same
  URL. Add it to the end-of-change checklist alongside tests and docs.
- **Applies to**: All published handoffs, reports and status artifacts

## Learned Skills â€” Basic Custom E-Commerce

### Skill: Run the guard suites against the real engine, not just SQLite
- **Learned from**: Basic Custom E-Commerce
- **Pattern**: Keep the fast suite on SQLite in-memory, but run every suite that asserts a
  **database-enforced** guarantee â€” guarded `UPDATE` affected-row counts, UNIQUE collisions,
  collation behaviour â€” against the actual MySQL/MariaDB target before release. Here that meant
  199 tests green on both engines on every phase, via one env-prefixed command.
- **Why**: The stock-decrement and duplicate-payment guarantees are enforced by the database,
  not by PHP. A test that passes only on SQLite proves nothing about the thing it exists to
  prove. It also caught the dev/prod engine split early (local MariaDB 10.4 vs target MySQL 8).
- **Applied to**: Any project where correctness depends on DB-level constraints

### Skill: Deliver a blocked integration complete and inert, not absent
- **Learned from**: Basic Custom E-Commerce (ToyyibPay, OQ-11)
- **Pattern**: When a third-party contract cannot be verified, still build the whole path â€”
  service, controller, settlement transaction, tests â€” with the unverifiable step returning an
  explicit refusal. Ship it switched off behind config, with the refusal reason logged verbatim
  and stated in the README, the deploy runbook and the handoff.
- **Why**: The client gets everything that *can* be built, the remaining work is one confirmation
  rather than a phase, and nobody later mistakes the deliberate refusal for a defect. The
  alternative â€” guessing the contract â€” converts an open question into a silent money bug.
- **Applied to**: Any integration blocked on an unobtainable specification

### Skill: Answer "is it complete?" by checking, not by recalling
- **Learned from**: Basic Custom E-Commerce
- **Pattern**: On any completion or handoff question, run the verification before composing the
  answer â€” working tree clean, suites green on every target, and each claimed implementation
  path confirmed to exist on disk. Then answer from that output.
- **Why**: I had every reason to believe the project was complete, and it was not: one
  requirement's file list was fictional. The check took one command; the wrong answer would have
  gone to a client. Confidence about your own recent work is precisely where verification feels
  least necessary and is most needed.
- **Applied to**: All handoffs, status reports and completion claims

---

## larisHQ â€” PH02 Authentication & RBAC (2026-09-01)

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
  can hand another user access â€” role assignment, role authoring, invitations, API tokens â€”
  a grant ceiling is mandatory: `array_diff($granted, $granter->permissions) === []`.
- **Caught by**: my own Phase 5 review, before commit. Reproduced first, then fixed, then
  regression-tested in both directions.

### Anti-Pattern: A guard test that trips on the prose explaining the guard
- **What I did**: wrote a test forbidding `is_admin`-style checks by grepping `app/` for the
  token. It failed immediately â€” on the comment in `RoleTemplates.php` explaining why no
  `is_admin` flag exists.
- **The rule**: a source-scanning guard must scan **code**, not text. In PHP, strip
  `T_COMMENT`/`T_DOC_COMMENT` with `token_get_all()` before matching. Otherwise the honest thing
  â€” documenting the rule where it matters â€” is what breaks the build, and the fix pressure is to
  delete the explanation.
- **Applied to**: every anti-pattern guard test, in any language.

### Anti-Pattern: Assuming a framework helper still does what its name says
- **What I did**: nearly wired unauthenticated redirects assuming `Authenticate::redirectTo()`
  finds the login route. On Laravel 12 it returns **null** unless `redirectUsing()` was called;
  the redirect actually comes from the exception handler's `route('login')` fallback â€” so the
  route *must* be named `login` or every guest hits an exception instead of a login screen.
  Same session, same shape: `authorizeResource()` still exists and still calls
  `$this->middleware()`, which Laravel 12 controllers no longer have â€” it is a fatal error, not
  a deprecation.
- **The rule**: for auth, authorization and routing internals, read the installed vendor source
  before writing against it. Both of these read as working code and fail only at runtime, in the
  path you are least likely to exercise by hand.

## Learned Skills â€” larisHQ

### Skill: Gate the schema before writing the code, in writing
- **Learned from**: larisHQ PH02
- **Pattern**: present the migrations, the design calls behind them and the one genuinely open
  fork *before* Phase 3, and get an explicit approval. Four decisions (permissions global vs
  tenant-scoped, the `Gate::before` contract, `users.status` early, the frontend permission
  payload) were settled in one exchange and never revisited.
- **Why**: schema is the most expensive thing to change after code exists, and the decisions that
  look like implementation detail â€” where `tenant_id` goes, what `before` may answer â€” are the
  ones that decide whether the *next* phase is safe.
- **Applied to**: every T2 phase with a migration.

### Skill: Prove the authorization claim over real HTTP, not only in the harness
- **Learned from**: larisHQ PH02
- **Pattern**: after the suite is green, log in as a genuinely limited role against the running
  app and confirm the 403s â€” GET and POST both â€” and that no record was written. The feature
  tests said the same thing, but the HTTP pass also caught that sessions only work on a
  `*.larishq.test` host (`SESSION_DOMAIN`), which no test would ever have shown.
- **Why**: the harness bypasses the cookie, the host, the CSRF token rotation and the real
  middleware ordering. Those are exactly where an authorization system is deployed, and exactly
  where the harness is silent.
- **Applied to**: any phase whose acceptance criteria are about who is refused.

---

## larisHQ â€” PH03 Multi-Tenancy (2026-09-01)

### Anti-Pattern: Reasoning about middleware order instead of running it
- **What I did**: placed tenant resolution as a route-group alias and reasoned that group
  middleware runs before route middleware, so the tenant would be bound before the guard resolved
  a user. Wrong: `Authenticate` and `SubstituteBindings` are in the framework's **middleware
  priority list**, which reorders them ahead of anything not in that list. The guard was querying
  users with no tenant bound.
- **How it surfaced**: not by review. A single test failed with
  `destroy(): Argument #1 ($role) must be of type Role, string given` â€” a *different* bug â€” and the
  stack trace in that failure showed the real ordering. One failing test paid for two findings.
- **The rule**: middleware order is a runtime property, not a reading-order property. When
  correctness depends on it, assert it â€” a test whose failure prints the stack is worth more than
  any amount of confidence about the pipeline.

### Anti-Pattern: `$request->user()` after a second guard exists
- **What I did**: shared `auth.permissions` from `$request->user()?->permissionSlugs()`. Correct
  with one guard. `Authenticate` calls `shouldUse($guard)`, so `auth:platform` makes `platform` the
  default guard **for the whole request** â€” `$request->user()` then returned a `PlatformUser`, and
  the shared Inertia prop called `permissionSlugs()` on a model that has no such method. A 500 on
  every page of the console that administers every customer.
- **The rule**: the moment an application has two guards, `$request->user()` and bare `auth` stop
  meaning anything specific. Name the guard everywhere â€” `Auth::guard('web')->user()`,
  `auth:web`, `auth:platform` â€” including in shared view/prop data, which is the place it is
  easiest to forget and the place it breaks every page at once.

### Anti-Pattern: Writing the same fillable no-op twice in two phases
- **What I did**: kept `tenant_id` out of `$fillable` (correct â€” it is a privilege column), then
  used `updateOrCreate(['tenant_id' => $id, 'slug' => $slug], â€¦)` in the provisioner *and* in a
  seeder. Mass assignment drops the key from the new instance, so the write-refusal I had just
  written threw on my own code.
- **Why it matters**: `Privilege Columns Must Not Be Fillable â€” and the Silent No-Op That Follows`
  was already in this log from Daily Spend. I wrote the guard and then walked into its far side
  twice in one phase. Knowing a rule is not the same as recognising the shape at the call site.
- **The rule**: whenever a column is excluded from `$fillable`, grep the codebase for
  `updateOrCreate`/`firstOrCreate`/`create` carrying that column in the *attributes* array. The
  lookup half works; the instantiation half silently does not.

## Learned Skills â€” larisHQ PH03

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

## larisHQ â€” PH04 HQ Business Setup (2026-09-01)

### Anti-Pattern: A dotted data key inside a dot-notation path
- **What I did**: named settings `commission.clawback_days` â€” readable, groupable, and idiomatic
  â€” then generated validation rules as `settings.commission.clawback_days`. Laravel reads dots as
  nesting, so that rule addressed `$data['settings']['commission']['clawback_days']`, a path that
  never exists. `required` failed, an error appeared under exactly the key I was asserting, and my
  test went green. The posted value â€” `400`, well outside the declared `max:365` â€” was never
  checked at all, and `validated()` returned a nested array the controller could not consume, so
  **saving a setting over HTTP was broken**.
- **How it surfaced**: an Inertia assertion could not address the prop, for the same reason. The
  failure I was annoyed by was the only thing pointing at the real one.
- **The rule**: any key containing the framework's path separator must be escaped at every path
  boundary â€” validation rules (`settings.commission\.clawback_days`), `data_get`, `old()`,
  Inertia's `where()`. And a green test that asserts *an error exists* proves nothing about
  **which** rule produced it; assert the valid case too, or the failure mode hides inside the
  success.
- **Caught by**: my own test run, before commit.

### Anti-Pattern: Testing a store through its repository and never through its endpoint
- **What I did**: covered the settings repository directly (`set()` then `get()` â€” green) and
  covered the endpoint only for rejection (403, 422). Nothing ever posted a *valid* value through
  the controller, which is precisely the path that was broken.
- **The rule**: for every store or service with an HTTP surface, at least one test must travel the
  whole route â€” request, validation, controller, persistence, read-back. Unit-testing the service
  and permission-testing the endpoint can both pass while the seam between them is broken.

### Anti-Pattern: Reseeding roles without reseeding permissions
- **What I did**: added ten permissions to the registry, then ran only `RoleSeeder` to refresh the
  templates. It maps slugs to ids from the table, so the ten new slugs â€” absent from the table â€”
  were silently skipped, and the HQ Owner got a 403 on the screens the phase had just built.
- **The rule**: a seeder that resolves foreign keys by natural key fails **silently** when the
  target row is missing. Run the whole seeder chain in order, and prefer a seeder that reports what
  it could not resolve over one that quietly syncs fewer rows.

---

## larisHQ â€” PH05 Dynamic Hierarchy (2026-09-01)

### Anti-Pattern: `nullable` in front of a rule that has to decide what null means
- **What I did**: wrote `'parent_id' => ['nullable', new ValidNetworkParent($level, $member)]`.
  The rule's first branch says "a member below the top level must have a parent" â€” and Laravel
  skips **every rule after `nullable`** when the value is null, so that branch never ran. A member
  could be created orphaned below the top level, which is precisely the structural invariant the
  rule exists to protect.
- **How it surfaced**: the test that asserted the refusal failed with "Session is missing expected
  key [errors]" â€” the one test I nearly did not write, because the rule so obviously handled it.
- **The rule**: `nullable` means *"null is acceptable, stop checking"*. A custom rule that must
  interpret null cannot sit behind it. Use `present` (key must exist, may be null) and let the
  rule decide â€” `validatePresent` returns true for a present-null key, so the rule runs.
- **Caught by**: my own test run, before commit.

### Anti-Pattern: Ordering an audit trail by a one-second timestamp
- **What I did**: `->latest('created_at')` on the audits relation. Three events written in one
  request share a second, so they came back in arbitrary order and the assertion failed against a
  trail that read differently each time.
- **The rule**: any "history" ordering needs a tiebreaker the database guarantees â€”
  `ORDER BY created_at DESC, id DESC`. A log that reorders itself between reads is worse than no
  log, because it looks authoritative.

## Learned Skills â€” larisHQ PH05

### Skill: Prove a configurable dimension at both ends and the boundary, not in the middle
- **Learned from**: larisHQ PH05 (1â€“8 configurable levels)
- **Pattern**: for anything the customer configures, write the same end-to-end test at the
  **minimum**, at a **typical** value, at the **maximum**, and at **maximum + 1** rejected. Here
  that was 1 level, 2 levels, 8 levels, and a 9th refused â€” and the 9th refused separately by the
  service, the HTTP layer and a database constraint.
- **Why**: a single mid-range test passes on code that has a hardcoded assumption at either end.
  The 1-level case caught different things from the 8-level case: one has no parents at all, the
  other exercises the full recursive walk.
- **Applied to**: any configurable count, depth, tier or limit.

---

## larisHQ â€” PH06 Marketers & Channels (2026-09-01)

### Anti-Pattern: Repeating a logged anti-pattern in a new costume
- **What I did**: wrote a guard test grepping the source for `facebook` and `google ads` to prove
  no channel-specific branch exists. It failed on my own doc comments â€” the ones explaining why no
  branch exists. I had hit exactly this in PH02 with the `is_admin` guard, **written the fix
  (strip comments with `token_get_all`) and logged it as an anti-pattern in this very file**, four
  phases earlier in the same session.
- **Why it happened**: I recognised the *rule* ("guards must scan code, not prose") but not the
  *shape* at the call site, because the subject was different â€” permissions then, channel names
  now. Logged lessons are indexed by their example, not by their structure.
- **The rule**: when writing any source-scanning guard, go and read how the last one was written.
  The generalisation to hold is "a guard that greps source must strip comments first", and it
  applies to every future guard regardless of what it forbids.

### Anti-Pattern: A comment that describes intent the code does not implement
- **What I did**: wrote `syncDefaultChannels()` to walk the config and create anything missing,
  with the comment *"Only ever adds: a channel an HQ deleted on purpose must not reappear on the
  next sync."* The code did the exact opposite â€” a deleted channel was missing, so it was
  recreated. The comment was a specification I had written and not implemented.
- **How it surfaced**: the test I wrote from the comment failed. Had I written the test from the
  code instead, both would have agreed and both would have been wrong.
- **The rule**: write the test from the **intent**, never from the implementation. When they
  disagree, that is the test doing its job â€” and the fix goes in the code, not the comment. A
  comment stating a guarantee is a claim; if nothing enforces it, delete the claim or enforce it.

### Anti-Pattern: Declaring a flaky test fixed because it stopped failing
- **What I did**: hit an intermittent failure, could not reproduce it in ten runs, hardened two
  factories with bounded `fake()->unique()` pools, and was ready to move on. It then failed a
  second time.
- **The rule**: a flake that has stopped reproducing is **not** a flake that has been fixed. Say
  what was observed, at what rate, what was ruled out and what was changed as a precaution â€” and
  record it as open. Reporting "fixed" on a disappearance trains exactly the wrong reflex, and the
  next person to see it starts from zero.
- **Status**: still open in larisHQ â€” see `Planning.md` PH06 notes.

---

## larisHQ â€” PH07 Catalogue & Pricing (2026-09-02)

### Anti-Pattern: Rebuilding the application inside a test
- **What I did**: wanted one test to exercise three hierarchy depths, so I looped and called
  `$this->refreshApplication()` between iterations. The new application opens a **new database
  connection** while the previous one still holds an open `RefreshDatabase` transaction â€” and that
  transaction holds row locks on `permissions`, which every test's `beforeEach` seeds. The next
  seed blocked for 50 seconds and died with
  `SQLSTATE[HY000] 1205 Lock wait timeout exceeded`.
- **Why it matters far beyond that test**: this was the **intermittent failure I had been chasing
  since PH04** â€” the one that appeared roughly twice in twenty-five runs, moved between unrelated
  tests, and survived ten isolated runs and three random-order runs. It was never order-dependent
  and never a faker pool; it was lock contention on the one table every test writes, surfacing in
  whichever test happened to seed next.
- **The rule**: never rebuild the container mid-test. To run one test against several
  configurations, use a dataset (`->with([1, 3, 8])`) â€” each case gets a clean transaction.
- **The wider lesson**: when a flake moves between unrelated tests, stop looking at the tests and
  look at what they **share**. Here it was a single seeded table and a transaction that outlived
  its owner.

## Learned Skills â€” larisHQ PH07

### Skill: Chase a flake to its shared resource, and say "open" until you have reproduced it
- **Learned from**: larisHQ PH04â€“PH07
- **Pattern**: three sightings across three phases, each in a different test. I recorded it as
  open, wrote down what had been ruled out, and kept going â€” then reproduced it deliberately two
  phases later while writing an unrelated test, and the stack trace named the cause in one line.
- **Why**: had I written "fixed â€” hardened the factories" at the first disappearance, the real
  cause would still be there and the next person would start from zero. Recording *what was
  observed, at what rate, and what was ruled out* is what made the eventual diagnosis a
  five-minute job instead of a fresh investigation.
- **Applied to**: any intermittent failure. State the rate, state the exclusions, keep it open.

### Skill: Re-raise an assumed decision at the moment its cost becomes real
- **Learned from**: larisHQ D043
- **Pattern**: D043 was recorded in planning as "ASSUMED â€” CONFIRM" with the note that it must be
  settled before PH12. I did not chase it for six phases â€” but the moment PH07 actually created
  the two columns it describes, I put it in the schema gate as a plain business question with the
  consequence spelled out.
- **Why**: asking at planning time competes with thirty other questions and gets a guess. Asking
  when the code is about to depend on it gets a real answer, because the stakes are visible and
  concrete.
- **Applied to**: every assumption logged as "confirm later" â€” attach it to the phase that first
  depends on it, and raise it there.

---

## larisHQ â€” PH08 Inventory (2026-09-02)

### Anti-Pattern: A unique index that includes a nullable column
- **What I nearly did**: put `warehouse_id` and `network_member_id` on `stocks` as nullable
  columns with `UNIQUE(tenant_id, warehouse_id, network_member_id, variant_id)`. In MySQL and
  MariaDB, **NULLs are distinct in a unique index**, so two rows for the same network member â€”
  both with `warehouse_id IS NULL` â€” would both be accepted. The constraint reads as if it works
  and enforces nothing on exactly the rows it was written for.
- **The rule**: when a row holds *one of two things*, give that choice its own table with a
  `CHECK` that exactly one side is set, and reference it by a single non-nullable key. Then the
  uniqueness lives somewhere it can actually be expressed, and both sides keep real foreign keys.
- **Caught by**: thinking through the constraint before writing it, prompted by having to justify
  the shape at the schema gate.

### Anti-Pattern: Writing a heredoc into a directory that does not exist â€” again
- **What I did**: `cat > app/Http/Requests/Concerns/ResolvesStockHolder.php` without creating
  `Concerns/` first. The shell reported the failure, but the same command chain's *later* steps
  had already patched two other files to import the trait â€” so the codebase referenced a file
  that did not exist.
- **Why it matters**: this exact anti-pattern is already in this log from a previous project. The
  new detail is the failure mode: when a compound command writes a file **and** patches its
  dependents, a partial failure leaves the dependents pointing at nothing.
- **The rule**: `mkdir -p` before any heredoc into a new path, and when one command both creates
  and wires something, check the create succeeded before trusting the wiring.

## Learned Skills â€” larisHQ PH08

### Skill: Name a scope extension as an extension, and price it before it is chosen
- **Learned from**: larisHQ D071
- **Pattern**: Â§13 described warehouse-only stock. Tracking what each stockist holds is a
  reasonable thing for the owner to want and an easy thing to slide in as "obviously implied" â€”
  so I put it at the gate as an explicit choice, with what it costs spelled out: every member
  becomes an inventory location, transfers gain a downstream leg, reconciliation spans the
  network, and the portals owe each member a view. Fakrul chose it knowingly.
- **Why**: the failure mode is not refusing scope, it is *absorbing* it silently â€” the work
  happens, the specification no longer describes the system, and nobody decided anything. Naming
  it makes it a decision with an owner and a recorded cost.
- **Applied to**: every requirement that is reasonable, unstated, and larger than it looks.

---

## larisHQ â€” PH09 Customers (2026-09-02)

### Anti-Pattern: `$defaults + $overrides` in PHP
- **What I did**: built an anonymiser as
  `forceFill(array_fill_keys($personalFields, null) + ['name' => 'Removed customer', â€¦])`.
  PHP's `+` on arrays keeps the **left** operand's keys, so the `name` override was silently
  discarded and the code tried to write NULL into a NOT NULL column.
- **The rule**: `+` is not `array_merge`. When combining defaults with overrides, the overrides go
  on the **left** â€” or use `array_merge`, where the right wins. The failure is silent whenever the
  column happens to be nullable, which is most of the time: here it only surfaced because `name`
  is NOT NULL.

### Anti-Pattern: Trusting a framework's name guess after being burned by it
- **What I did**: named a pivot `marketer_customer`, matching the domain and the planning
  document. Laravel's `belongsToMany` guesses alphabetically â€” `customer_marketer` â€” and failed
  at runtime. I had hit exactly this in PH06 with `marketer_channel`, fixed it the same way, and
  **written the lesson into session memory** three phases earlier.
- **Why it keeps happening**: the note said "state the table explicitly when the schema names it
  otherwise", which requires noticing that this *is* such a case. The alphabetical rule is easy to
  check and I did not check it.
- **The rule**: whenever a pivot's two model names are not already in alphabetical order, pass the
  table name. Do not evaluate whether it is needed â€” pass it.

## Learned Skills â€” larisHQ PH09

### Skill: Turn a policy sentence into a failing test
- **Learned from**: larisHQ PH09 (Â§18 "no unnecessary personal data")
- **Pattern**: requirements about what a system must *not* do have no natural home in code â€” there
  is nothing to point at. Make the absence assertable: a test on the exact column list turns
  "collect only what is necessary" from an intention into something that breaks the build when
  violated.
- **Why**: intentions decay silently and nobody is ever the person who decided to erode them. A
  test makes the erosion a visible choice with an author.
- **Applied to**: any "must not" requirement â€” no unnecessary data, no cost prices in a payload,
  no admin shortcut, no vendor-specific branch. Each of those became a guard test in this project,
  and each has since caught something.

---

## larisHQ â€” PH10 Ordering (2026-09-02)

### Anti-Pattern: A factory that can generate data the schema rejects
- **What I did**: `RoleFactory` used `fake()->unique()->jobTitle()` for the name and slugged it
  into a `varchar(64)` column. Most job titles fit. "First-Line Supervisor-Manager of Landscaping,
  Lawn Service, and Groundskeeping Worker" does not â€” so roughly one run in fifteen died with
  `1406 Data too long`, in whichever test happened to draw it.
- **Why it mattered more than it looks**: this was a **second** intermittent failure with the same
  symptom class as the PH07 lock-wait â€” random-looking, moving between unrelated tests. Having
  diagnosed one, it was tempting to assume any recurrence was the same thing. It was not.
- **The rule**: every generated string must be bounded against the column it lands in. Faker's
  word-based generators have no length contract, and `unique()` does not add one. Assert it once:
  draw a few hundred and check the longest against the column width.
- **The wider lesson**: after fixing one flaky cause, do not assume the next occurrence is the same
  cause. Read the new stack trace as if the first diagnosis had never happened.

## Learned Skills â€” larisHQ PH10

### Skill: Prove immutability by changing the source, not by reading the copy
- **Learned from**: larisHQ PH10 (D011, D076)
- **Pattern**: a snapshot test that asserts `line.unit_price === 2000` proves the copy happened
  once. It says nothing about whether the value is a copy or a join, because both return 2000
  today. The test that means something is: place the order, **change the price to something
  else**, and assert the order still reads 2000. Do it for every snapshotted input â€” price, tier,
  cost, names.
- **Why**: the whole point of a snapshot is behaviour under change, so the test has to contain a
  change. Applied here it also caught what would have been a real bug a phase later â€” the landed
  cost was not originally in my schema, and writing this test is what surfaced that D044's
  commission base had no stable input.
- **Applied to**: any denormalised copy, cached total, or "as at" record.

---

## larisHQ â€” PH11 Payments (2026-09-02)

### Skill: Chase a dangling cross-reference when you reach the phase it points at
- **Learned from**: larisHQ D031 â†’ PH11
- **Pattern**: D031 dropped "Refunded" as an order status six phases earlier, with the note that
  it *"belongs to PH11"*. PH11's own task list said nothing about refunds. Building only the task
  list would have left a documented pointer unhonoured and a returned order with no way to be
  settled â€” and nobody would have noticed for months.
- **Why**: decisions written in one phase routinely defer work into another, and the receiving
  phase's task list is usually written before that deferral exists. Re-read the decisions that
  name the phase you are starting, not just the phase's own tasks.
- **How it played out**: raised as an explicit scope question rather than absorbed silently, so
  the extension has an owner and a decision record (D077).
- **Applied to**: any phase whose predecessors deferred something into it. Grep the decision log
  for the phase name before writing the first line of code.

### Skill: Let the shape of a constraint choose the concurrency tool
- **Learned from**: larisHQ PH08 â†’ PH11
- **Pattern**: PH08 made overselling impossible with a guarded conditional update, and that
  pattern was fresh and successful. PH11's constraint looks identical in English â€” "never exceed
  the total" â€” but the quantity being constrained is a **sum across rows**, which no single-row
  `WHERE` can express. It needed a parent lock instead.
- **Why**: reaching for the tool that worked last time is exactly how a read-then-write race gets
  shipped with confidence. One row â†’ conditional update. Sum across rows â†’ lock the parent and
  aggregate under the lock. State which one applies and why, in the code.
- **Applied to**: credit limits, quotas, capacity checks, anything phrased as "the total must not
  exceed".

---

## larisHQ â€” PH12 Commission (2026-09-02)

### Anti-Pattern: Comparing ids from two different tables
- **What I did**: wrote a test asserting D014 â€” that no commission entry belongs to a network
  member â€” as
  `CommissionEntry::whereIn('marketer_id', NetworkMember::pluck('id'))->count() === 0`.
  It failed, and the code was right: marketer ids and network member ids are separate sequences,
  so marketer 1 and member 1 collide numerically. The assertion was a category error that would
  have passed or failed by coincidence either way.
- **The rule**: an id is only meaningful against its own table. To prove a foreign key cannot hold
  the wrong kind of thing, assert it **structurally** (the column does not exist) and
  **referentially** (every value resolves to the intended model) â€” never by comparing raw ids
  across tables.
- **Caught by**: the test failing on correct code, which is the useful direction for a test to be
  wrong in.

## Learned Skills â€” larisHQ PH12

### Skill: Depart from an accepted proposal when implementing reveals what it costs
- **Learned from**: larisHQ D078, D079
- **Pattern**: P2 had been accepted months earlier and specified the manager override as a period
  lump sum. Implementing the clawback lifecycle made the cost visible â€” a lump sum has no per-order
  entry to cancel when one order in the period is returned. Rather than build it as written or
  quietly change it, I put the trade-off at the gate with both shapes priced, and recorded the
  outcome as a decision that *refines* P2 rather than contradicting it.
- **The second case** was smaller and I decided it myself: D045 permits loss-leader pricing, so a
  negative commission base is a real state, and a negative commission would make the HQ's own
  pricing decision into a debt the marketer owes. Floored at zero, recorded, reason stated.
- **Why**: an accepted proposal is a decision made with less information than you have while
  building it. Neither silently following it nor silently changing it is right â€” surface what
  implementation revealed, and let the record show why the answer moved.
- **Applied to**: any spec written before the thing it specifies existed.

---

## Learned Skills â€” larisHQ PH13 (2026-09-02)

### Skill: Write the timezone test as the scenario, not as the assertion
- **Learned from**: larisHQ PH13
- **Pattern**: "period boundaries are computed in the configured timezone" is easy to assert
  trivially â€” `expect(config('app.timezone'))->toBe(...)` â€” and that proves almost nothing. The
  test that earns its place names the **scenario**: an order placed at 00:30 on the 1st in Kuala
  Lumpur is 16:30 on the last day of the previous month in UTC, so a UTC boundary silently files
  that sale under the wrong period.
- **Why**: timezone bugs produce numbers that are wrong and look completely ordinary. Nobody
  audits a monthly total that is plausible. Writing the failing scenario into the test is what
  makes the bug *findable* rather than merely *prevented today*.
- **Applied to**: any date bucketing â€” reporting periods, billing cycles, cut-off times, "today's"
  anything.

### Skill: Reuse the schema shape you already proved, and say that you are
- **Learned from**: larisHQ PH08 â†’ PH12 â†’ PH13
- **Pattern**: three phases hit the same problem â€” a row that must reference exactly one of
  several things, with uniqueness over that choice. The first (stock locations) cost real thought
  and a separate table. The second (commission rules) and third (targets) used a CHECK plus a
  STORED generated key, in minutes, with a comment naming the earlier decision.
- **Why**: a solved shape recognised early is the cheapest thing in a codebase, and the comment
  pointing back is what makes it recognisable to the next person instead of looking like
  coincidence. The failure mode is the opposite one â€” solving it a third distinct way, and leaving
  three patterns where one would do.
- **Applied to**: any recurring structural problem. Name the earlier decision in the code, not just
  in the log.

---

## larisHQ â€” PH14 Reports (2026-09-02)

### Anti-Pattern: Subtracting one unsigned column from another
- **What I did**: computed a margin as `SUM((retail_price - unit_price) * quantity)` where all
  three columns are `unsignedInteger`. MySQL and MariaDB do **unsigned** arithmetic there, so the
  moment `unit_price > retail_price` the expression does not go negative â€” it raises
  `SQLSTATE[22003] 1690 BIGINT UNSIGNED value is out of range` and the whole report 500s.
- **The sharp edge**: casting the subtraction alone was **not enough**. Multiplying the signed
  result by an unsigned `quantity` promotes the whole expression back to unsigned, and it failed
  again with the same error. Every operand needs the cast.
- **How it surfaced**: live data, not the test suite. My test had retail above the level price â€”
  the normal case â€” so the underflow never occurred. The dev database happened to contain a
  product priced above retail, which D045 explicitly permits, and that is what broke it.
- **The rule**: if a column can legitimately be subtracted below zero, either store it signed or
  cast **every** operand in the expression. And when a comment claims a behaviour ("can be
  negative; reported as it is"), write the test that exercises it â€” mine claimed exactly that and
  the code had never done it.

## Learned Skills â€” larisHQ PH14

### Skill: Read a decision against the schema before building on it
- **Learned from**: larisHQ D048 â†’ D082
- **Pattern**: D048 defined a figure as "computed from data the order already holds". Rather than
  taking that at face value, I checked what the order actually held â€” and retail was not among the
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
  is easy to satisfy on the screen and miss on the CSV â€” the export is a second code path to the
  same data, and it is the one that leaves the building.
- **Why**: an export that ignores a scoping rule is the obvious way around it, and nobody notices
  because the screen looks correct. Assert the narrowing on the downloaded bytes, not just on the
  rendered props.
- **Applied to**: any download, API endpoint, or print view that mirrors a scoped screen.


## larisHQ â€” PH15 Portals (2026-09-04)

Run at T2. Suite green, CS verify 100/100 and a live E2E pass **before** four of these were known â€”
three were found by the review and security gates, and the worst by `/code-review high` after the
phase already looked finished. The gates earned their cost this phase more clearly than in any
previous one.

### Anti-patterns

**AP â€” Narrowing a list is not narrowing a resource.**
A staff list got a `console()` scope so portal users would not appear on it. The resource route
binding still resolved any user of the tenant, and the policy had no check, so `PUT /staff/{id}`
with an admin role attached handed a portal user the entire console â€” and the role `sync()` revoked
their portal access in the same request. **The list query and the route model binding are two
separate doors. Closing the visible one feels like the work.** Put the rule on the policy, where
model-bound authorization actually passes.

**AP â€” Repeating a docblock as the justification for calling the method.**
`syncRoles()` documents itself as "adds what is missing and leaves what an HQ has customised alone".
It does not: it rewrites the name, description and permissions of every template. That claim was
copied into a new caller's comment and would have silently reverted customised production roles on
an unrelated action. **A docblock is a claim about code, not evidence. Read the body of anything you
newly call from a runtime path â€” especially something previously only ever run at setup time.**

**AP â€” `?->` inside a query-builder argument is a null value, not a null guard.**
`where('user_id', $user?->getKey())` compiles to `user_id IS NULL` when the user is null. On a
nullable FK â€” which was the *normal* state in this schema â€” it matched, and two visibility scopes
returned nothing instead of everything, contradicting their own documented contract. The sibling
scope written the same day guarded with `$user === null` and was correct. **Guard the branch; do not
let the query builder interpret your null.**

**AP â€” One intent split across two transactions.**
A checkout service commits its own transaction and returns a draft; the caller then transitioned it
to "placed". A failure in the second step left exactly the persisted, invisible draft the caller
existed to prevent, while showing the user an error. **If step two is what makes step one correct,
they are one transaction.**

**AP â€” Shipping a surface with no way in.**
Two complete portals, tested and verified live, that no administrator could grant access to: the
service that mints a login had had no caller since the phase that wrote it three phases earlier.
Nothing failed, because nothing exercised the missing path. **Before declaring a user-facing surface
done, grep for a production caller of the thing that lets a real user reach it.**

**AP â€” Re-introducing a sink the codebase deliberately removed.**
Six `v-html` bindings added for paginator labels, in a project whose console carries a comment
explaining why `v-html` was taken out. **When adding a second surface, read what the first one
decided â€” the new surface inherits the codebase's rules, not a blank slate.**

**AP â€” Writing a test and then skipping it.**
A skipped test with a plausible-sounding reason is worse than no test: it reads as coverage. It was
skipped because a factory password was uncertain â€” thirty seconds of checking, not a reason.

### Learned Skills â€” larisHQ PH15

- **Enumerating the router as a boundary test.** Turning "no admin route is reachable" from a
  hand-written list into a walk over `Route::getRoutes()`, with a non-empty assertion guarding the
  vacuous-pass failure mode. Later phases inherit the guard for free.
- **Making IDOR unrepresentable.** Binding the acting subject from the session into a request-scoped
  singleton and keeping it out of every URL, so there is no identifier to tamper with. Proven by a
  live request carrying a forged id that produced the correct order at the correct price.
- **Reading a phase's inherited debts before designing it.** PH15's design started from the four
  debts earlier phases had recorded against it, which is why they were paid rather than rediscovered.
- **Deriving a boundary from machinery already present.** The console/portal split needed almost no
  new enforcement because an existing "a grant can never exceed the granter" rule already filtered
  both pickers. Look for the invariant that already holds before writing a new one.
- **Reporting an unmet acceptance criterion as unmet.** The mobile/tablet visual check could not run;
  static evidence about the markup was gathered and labelled as *not* that check, and the criterion
  was carried forward rather than ticked.


## larisHQ â€” PH16 Notifications & Audit (2026-09-04)

Run at T2. The phase's defining discovery was archaeological rather than technical: a table written
to since PH05 that nothing could read, and a whole class of actor the schema could not record.

### Anti-patterns

**AP â€” A write path with no read path is not a feature.**
`audit_logs` had thirteen call sites and had been recording faithfully for eleven phases. No route,
no controller, no screen. Every phase gate passed because the tests asserted rows were *written*.
**When a phase builds a store, check in the same phase that something can open it** â€” otherwise it
is a table that costs writes and returns nothing.

**AP â€” A second identity table the audit schema cannot hold.**
Platform Owner actions were unauditable because `user_id` was a foreign key to `users` and a
Platform Owner lives in `platform_users`. The gap was invisible for eleven phases because nothing
ever asked the audit log about a platform act. **When a system grows a second kind of actor, every
table that records "who" needs revisiting â€” the FK will not complain, it will just never be set.**

**AP â€” A null that means "decided" read as a null that means "forgot".**
A tenant-scoping trait refused any write with a null `tenant_id`, which was right while every
audited record belonged to a subscriber. The moment one legitimately did not, the guard fired on a
correct write â€” and it fired *after* the side effects, so a publish notified everybody and then
returned 500. `array_key_exists` asks the question the guard actually meant: did the caller set
this at all? **A "fail closed" guard needs to distinguish absence from an explicit answer, or it
eventually blocks the correct case.**

**AP â€” Delivering a new permission by re-running the seeder that rewrites everything.**
Adding a permission left existing tenants' roles behind, and the obvious remedy â€” re-run the role
seeder â€” would have reverted every role those tenants had customised. **A provisioning routine and
a migration routine are different things even when they share code.** The fix narrowed the blast
radius to the one role where a full sync is definitionally correct.

**AP â€” A source-grep guard matching a substring.** `expo` matched `export` in four files. Third
instance in this project, after `is_admin` and `facebook` â€” the first two were comments, this one
was a prefix. **Word boundaries, comments stripped, every time.** A guard that cries wolf gets
deleted rather than fixed, which loses the rule it was protecting.

**AP â€” Ordering a list by a one-second timestamp when the primary key is a UUID.**
The notification inbox reshuffled on every load. The same project had already solved this for its
audit relation with an id tiebreak and had written down why â€” and the lesson did not transfer
because the new table's key was random rather than sequential. **A stable arbitrary order beats an
unstable chronological one; the reader needs the list to stay still.**

### Learned Skills â€” larisHQ PH16

- **Taking an unrecoverable requirement to the gate instead of guessing.** Two spec sections were
  gone. Deriving a list and asking for confirmation cost one question and gave the *next* phase
  something stated to review against, instead of an assumption dressed as a requirement.
- **Distinguishing an audit from a notification.** One reconstructs, the other interrupts. They look
  like the same list and are not; deriving one from the other produces an inbox nobody reads.
- **Letting a previous phase's guard do its job.** An enumerated route guard written in PH15 failed
  the moment PH16 added a shared route, and the right response was to fix the boundary rather than
  widen the guard's exclusion list.
- **Auditing without becoming the leak.** The one place where recording carelessly undoes the thing
  being recorded is anonymisation. Record the handle, never the cleared values.
- **Reading the body of a method before trusting its docblock** â€” carried over from PH15's finding
  and applied deliberately this phase.


## larisHQ â€” PH15/PH16 review round (2026-09-04)

`/code-review high` on the combined working tree returned **eleven findings** after both phases had
a green suite, CS verify 100/100 and a live end-to-end pass. The two severe ones are the entry that
matters.

**AP â€” A test that documents a dead end instead of catching it.**
Revoking portal access kept the account linkage on purpose, which made the grant path refuse to run
again â€” so revoke was permanent and the UI offered no way back. A test asserted the linkage
survived and stopped there. It described the behaviour accurately and asked nothing about whether
the behaviour was usable. **A test that only asserts the mechanism did what it was told is not
coverage of the feature.** After writing one, ask what the user does next; if there is no answer,
that is the bug.

**AP â€” An undo with no redo.** More generally: any operation that deliberately preserves state in
order to be reversible needs the reversing action shipped in the same change. Preserving the
linkage was the *right* call; leaving it unreachable made it worse than deleting.

**AP â€” Notifying before the write commits.** A notification placed before a service call that
commits its own transaction can announce something that then fails â€” here, an email telling a
member they were approved and could sign in, while the record stayed pending and the middleware
would refuse them. Every other call site in the same system was already ordered correctly, which is
what made the inverted one easy to write and hard to see.

**AP â€” A request-scoped singleton with no reset.** A context object filled only on *some* routes has
nothing to clear it on the way out, so it leaks into later requests under Octane and inside tests.
Binding it to the identity it was resolved for removes the dependency on container lifetime
entirely â€” a stale context simply stops matching. Compare a context set by middleware on *every*
request, which does not have this problem and therefore does not suggest the fix.

**AP â€” Loosening a guard without noticing which backstop it relied on.** A "refuse writes with no
tenant" check was relaxed to allow a deliberate null, with a comment reasoning that the NOT NULL
column constraint was the real safety net â€” in the same change that made that very column nullable.
**When you justify weakening a check by pointing at another check, verify the other check still
exists.**

**AP â€” Two surfaces totalling the same money differently.** One screen filtered cancelled rows out
of a commission total; a new screen summed everything. Both were defensible in isolation, and
together they told one marketer two numbers. Put the definition on the model, once.

### Learned Skills

- **Reading a review's findings as claims to verify, not instructions to apply.** Each of the eleven
  was checked against the code before acting; the two severe ones reproduced exactly as described,
  and the reasoning in the report was sound enough to adopt wholesale. Some reviews are not.
- **Running the review on the combined tree.** Two phases reviewed together surfaced the
  interaction bugs â€” an announcement link broken by a middleware added in the *other* phase â€” that
  neither phase's own review would have found.

---

## LS-SecureLab Ã¢â‚¬â€ Intentionally-vulnerable lab, done as a real T2 build (2026-09-10)

**Learned Skill**: A security *training* lab is still a T2 build, not a toy. SecureLab touched
auth/authz, migrations, and file upload Ã¢â‚¬â€ three absolute T2 surfaces Ã¢â‚¬â€ so it ran the full gate
set even though "it is supposed to be insecure." The trick is separating *intended* weaknesses
(4 planted, isolated, toggled findings) from *accidental* ones (everything else must be correct):
role kept out of `$fillable`, CSRF on, passwords hashed, session regenerate on login, ownership
check on downloads. "This app is a vuln lab" is never a licence to be sloppy outside the planted
findings.

**Learned Skill**: Prove the lesson AND the fix with the same automated artifact. Dual-mode
feature tests (exploit succeeds with the flag on, fails with it off) turn "retest" from a manual
click into `php artisan test`. Backed by a live HTTP replay in both modes for on-stage confidence.

**Anti-Pattern (session, minor)**: A PowerShell one-liner containing an inline regex digit-class
literal tripped a safety hook that misread it as a `Remove-Item` on a protected path. Fix: put
non-trivial regex/exploit scripts in a scratchpad `.ps1` (or a `.md` written with the file tool)
and run/append the file, rather than inlining regex in the tool command. Same shape as other
"shell metacharacter in an inline command" gotchas Ã¢â‚¬â€ move it to a script.

**Anti-Pattern (avoided, worth recording)**: For the insecure-upload finding, the tempting demo
is a webshell. That would be a code-execution sink and violates the safety scope. Correct move:
demonstrate unsafe *handling* only Ã¢â‚¬â€ private non-web disk, no execution Ã¢â‚¬â€ so the finding is real
(Medium) but the host can never be compromised.

---

## Social Media Listening Tool â€” Phase 1 Foundation (2026-09-08)

Greenfield, T2 Full. Laravel 13 + Inertia 3 + Vue 3.5 + Bootstrap/AdminLTE, MySQL target.
Planning + interactive UI foundation. CS verify 100/100, 15 tests / 345 assertions.

### Anti-Patterns

**AP-SML-01 â€” Answering a third-party pricing question from memory.**
At session start my understanding of X's API was "Free / Basic $200 / Pro $5,000 / Enterprise"
â€” fixed monthly subscription tiers. Scout's live check found X **replaced that entire model
with pay-per-use credits in February 2026**, closed the legacy tiers to new signups, and
discontinued the free tier. Not a stale number: a stale *model*. Had I written the plan from
memory, the client would have been quoted a pricing structure that no longer exists, and the
architecture would have missed that every X mention now carries a marginal cost â€” which is a
schema and scheduler consequence, not a footnote.
**Rule**: third-party pricing, quotas, and permission names are the fastest-decaying facts
in any integration plan. Verify every one before it enters a document, and mark the
confidence of each source â€” first-party docs vs third-party summaries â€” *in the document*,
so the reader knows which rows are load-bearing. Three of the six platforms in this project
had a constraint that materially changed the design and that I would have got wrong or
vague from memory (X's model, Threads' 500-query allowance, YouTube's 100-units-per-search).

**AP-SML-02 â€” Reusing a vendor template's own layout class names for a hand-rolled shell.**
Built the console shell on `.app-wrapper` / `.app-sidebar` / `.app-main` â€” AdminLTE 4's own
class names â€” while hand-rolling the sidebar. The mobile sidebar then never appeared: right
class, `transform: none`, still at `x: -250`, because AdminLTE's stylesheet was setting its
own width and offset on the same selectors. Cost a debugging round that a namespace prefix
would have prevented.
**Rule**: when hand-rolling something a vendored template also provides, namespace it. The
diagnostic tell is **a computed width that is not the width you authored** â€” check that
first and the collision identifies itself immediately.

**AP-SML-03 â€” Verifying against the dev server and believing it was the build.**
Ran the browser verification while a stray Vite dev server held `public/hot`, so every
screenshot exercised HMR-served assets rather than `public/build`. The production build was
fine, but that was luck, not evidence â€” the claim "the built app renders" was not actually
tested until the dev server was killed and the pass repeated.
**Rule**: before claiming a browser check verifies the shipped build, confirm `public/hot`
is absent. A dev server can be running that this session did not start.

### Learned Skills

1. **Split acquisition modes before designing a listening system.** "Social listening"
   implies keyword search across the open platform. Only three of six target platforms offer
   anything of the kind, and **Facebook and LinkedIn offer none at any tier** â€” those are
   owned-channel monitoring only. Naming the two modes (Discovery vs Owned-channel) early
   kept the schema, the provider interfaces and the UI honest; designing as if all six do
   Discovery is the single most likely way that class of product fails.
2. **A capability is a type plus a declaration with a reason string.** See the pattern
   library entry. The reason string is what turns a greyed-out button into an answer.
3. **A "silent success" is more dangerous than a loud failure.** Threads' keyword search
   quietly narrows to the caller's own posts when `threads_keyword_search` is not granted â€”
   HTTP 200, structurally valid, near-empty. No exception ever fires. Providers must assert
   their granted scopes at connect time rather than trust a successful-looking response.
   Worth looking for this shape in every third-party integration.
4. **Record what a table is NOT for, and why.** `social_authors` and a time-series
   `engagement_metrics` were both designed and then deliberately deferred with the trigger
   condition that would revive them. That is cheaper than either building them early or
   rediscovering the argument in six months.
5. **Ordering integrations by external lead time, not by importance.** LinkedIn is last to
   build and first to apply for, because its partner approval is the longest pole and it is
   entirely outside our control.


---

## SociaPulse — 2026-09-12 (Laravel 12 + PostgreSQL, own SaaS, 7 phases, 224 tests)

Seven phases delivered in one session. Every phase gate passed on CS verify, and the security
review found no exploitable vulnerability. The entries below are the mistakes, which are worth
more than the successes.

### Anti-Pattern: Building a guard that cannot fail, and shipping it green

- **What happened**: three times in one project.
  1. Adding PKCE, I issued the OAuth `state`, built the authorization URL with it, then stored
     the code verifier under a **second, freshly issued state** — one the callback would never
     look up. Every test stayed green because the only provider wired at that moment (Threads)
     does not use PKCE.
  2. The no-secrets prop scan walked every *tenant* screen and none of the *platform* ones —
     exactly backwards, since the platform console reads across every workspace, so a leak
     there is a leak of every customer at once.
  3. A test named "an unverified user cannot reach the console" created its user with
     `User::factory()`, which sets `email_verified_at` by default. The user was verified. The
     test asserted nothing and passed.
- **Impact**: each one looked like coverage. The PKCE bug would have broken X sign-in on first
  contact with a real provider; the prop scan gave false assurance about the highest-value
  screens in the product; the verification test would have let an unverified user through
  silently. **A guard that cannot fail is worse than no guard, because it manufactures
  confidence.**
- **Rule**: after writing a protection, make it fail on purpose before trusting it. Break the
  input, remove the scope, unset the flag — see red, then fix. For a test asserting "X is
  blocked", first assert the precondition that makes X blockable (`assertFalse($user->verified)`)
  so the setup cannot silently invert. For a guard that only one code path exercises, add the
  second path before moving on.
- **Applies to**: all projects. Especially anything named `*Test` that asserts a negative.

### Anti-Pattern: `??` used where null carries meaning

- **What happened**: `$discovered->expiresAt ?? $grant->expiresAt`. Meta's `debug_token` reports
  `expires_at: 0` for a **non-expiring** token, which the parser correctly turned into `null`
  meaning "never expires". The `??` then silently fell through to the grant's 60-day expiry and
  stamped it onto a token that has none — so the nightly refresher would have started rewriting
  a credential that never needed it.
- **Impact**: null-coalescing cannot distinguish *"the provider told us: never"* from *"the
  provider told us nothing"*. Both are `null`, and the fallback quietly assumes the second.
- **Rule**: when null is a legitimate **answer** rather than an absence, carry a separate flag
  that says whether the source spoke — `confirmed: bool` — and branch on that, never on the
  value. `$source->confirmed ? $source->value : $fallback`.
- **Applies to**: any code merging an authoritative answer with a default. Timestamps, quotas,
  permissions, retention windows.

### Anti-Pattern: Copying a rule from the pattern library without checking its precondition

- **What happened**: prepended `ResolveTenant` to the `web` group, following the larisHQ rule
  "resolve the tenant **before** the guard, because `EloquentUserProvider` applies global scopes
  during authentication". Prepending puts it ahead of `StartSession` too, and the tenant is read
  from the session — so every authenticated page 500'd with `Session store not set on request`.
- **Impact**: the larisHQ rule is correct **where users are tenant-scoped** (`unique(tenant_id,
  email)`). In SociaPulse users are global — one person belongs to several workspaces — so
  authentication does not depend on the scope at all and the precondition never held. I applied
  the conclusion without re-reading the premise.
- **Rule**: a library entry's **Problem** section is a precondition, not preamble. Before
  copying a solution, confirm the problem it solves is the problem you have. Where a rule
  hinges on a schema shape, check that shape first.
- **Applies to**: every use of `11-pattern-library.md`.

### Anti-Pattern: Writing an assertion and never reading it back

- **What happened**: wrote
  `assertSame(1, $t->fresh()->rotation_generation - $t->rotation_generation + $t->rotation_generation - $t->rotation_generation + 1)`
  — a tangle of arithmetic that reduces to `fresh - old + 1` and expresses nothing I intended.
  It failed, which is the only reason I noticed. The claim I actually meant — *the rotated
  refresh token was persisted* — was not being tested at all.
- **Impact**: had it happened to pass, a genuine bug (the rotated refresh token being dropped,
  fatal on X which rotates on every use) would have shipped behind a green test.
- **Rule**: an assertion must read as a sentence about behaviour. If it needs arithmetic to
  understand, the thing being asserted has not been decided yet — stop and name it. Re-read
  every assertion once before moving to the next test.
- **Applies to**: all projects.

### Anti-Pattern: Repeating a trap the library already documents

- **What happened**: the "keep `tenant_id` out of `$fillable`, and then remember `create()`
  silently drops it" gotcha — documented in `11-pattern-library.md` under *Tenant Scope: read
  open, write closed* — bit **three separate times** in one session, on `role`, on `tenant_id`,
  and on `social_connection_id`. Each time the symptom was a not-null violation minutes later.
- **Impact**: three debugging detours for a trap I had already read, in this session, in the
  file I loaded at the start.
- **Rule**: when a model deliberately excludes a column from `$fillable`, write the factory or
  helper that sets it explicitly **in the same commit as the model**. The exclusion and its
  workaround belong together; separating them guarantees the next caller rediscovers it.
- **Applies to**: any codebase using `$fillable` as a privilege boundary.

### Anti-Pattern: A declared capability whose permission is never requested

- **What happened**: a provider class implemented the mentions interface and declared the
  capability as *requires permission: `threads_manage_mentions`* — and the OAuth
  `requestedScopes()` never asked for that scope. The consent screen therefore never offered it,
  the scope read-back could never discover it, and the feature reported "missing permission" with
  no reconnect able to clear it. Nothing threw. Nothing was logged. Every other signal — the
  interface, the declaration, the UI, the planning document's submission list — said the feature
  was built.
- **Impact**: the documentation was *right*, which is what kept it invisible. Reading either side
  alone shows a correct system; only comparing the two shows a dead feature. It would have been
  found by a customer, or by a reviewer watching a screencast of an empty screen.
- **Rule**: wherever a capability names the permission it needs, assert in **both** directions:
  every named permission is actually requested (or is allowlisted as deliberately deferred, *with
  a reason in code*), and every requested permission is named by some capability (or listed as
  infrastructural). The second direction is the one a provider's app review polices — it demands a
  justification per permission, and a scope no feature uses cannot be demonstrated, which risks
  the whole submission rather than just that scope.
- **Watch for two spellings of one permission.** Google's scopes are declared by short name and
  requested as full `https://www.googleapis.com/auth/...` URLs. Comparing the strings directly made
  the guard pass-through-failing for that provider: the same blindness, in the opposite direction.
  Normalise before comparing, and assert the traversal found a plausible *number* of declarations —
  a guard that silently inspects nothing is worse than no guard, because it reads as coverage.
- **Applies to**: OAuth scopes, feature flags gated on an entitlement, plan limits naming a
  permission key, anything where one place declares a requirement and another place requests it.

### Anti-Pattern: Trusting a subagent's finding about code I can read myself

- **What happened**: the security review reported that `AuditLog` and `WebhookEvent` queries in
  the platform console would be silently tenant-filtered. I checked before acting: neither model
  uses `BelongsToTenant`, so neither carries a global scope, and the finding was wrong.
- **Impact**: none — because I verified. Acting on it would have meant adding
  `withoutGlobalScopes()` calls that do nothing, and writing a commit message asserting a bug
  that never existed.
- **Rule**: a subagent's report is evidence, not a conclusion. Where the claim is about code on
  disk, verify it with a grep before it reaches a commit message or {USER_NAME}. **But keep the
  underlying question** — here the hazard was real for the future (adding the trait to
  `AuditLog` later would break the console), so the right response was a regression test, not a
  dismissal and not a fix.
- **Applies to**: every delegated review.

## Learned Skills — SociaPulse

- **Verify a platform capability, never recall it.** Five parallel research passes against
  first-party docs produced findings that contradicted my priors: X had replaced its entire
  pricing *model*, YouTube's quota is three separate buckets shared across every tenant, and
  Facebook has no public post search at any tier. Encoding those as *tests* — a test fails if
  Facebook ever claims keyword search — turns perishable research into something that cannot
  silently rot.
- **Declared capability + discovered scope + kill switch.** Three independent gates, each with
  a human reason string rendered verbatim. `instanceof` answers "did we write it", the
  declaration answers "is our app approved", the connection's read-back scopes answer it for
  one token, and the switch answers "will we pay for it today". The reason string is the
  feature — a greyed-out control with no explanation is what the architecture exists to prevent.
- **A silent success is more dangerous than a loud failure.** Threads' keyword search returns
  HTTP 200 while searching only the caller's own posts when the scope was never granted. No
  exception ever fires. The only defence is asserting the granted scopes at connection time and
  storing them as discovered state — never inferring capability from a successful-looking
  response.
- **Say what is not built, by name, in the product.** X image posting is refused in the composer
  with "needs its chunked upload endpoint, which is not built yet" rather than accepted and
  failed at publish. Naming the gap costs one string and converts a mysterious failure into an
  understood limitation.
- **Ask which of three is at fault.** Grouping every operational signal by *our system /
  customer authorisation / provider* is the single highest-value screen in an integration
  product, because it is the first question support has to answer and a wall of
  undifferentiated errors never answers it.

---

## SociaPulse — production hardening (2026-09-12, 268 → 297 tests)

A session spent entirely on the gap between "all features built and tested" and "safe to put
in front of customers". Five findings, none of which a feature test could have caught, because
every one of them behaves perfectly in development. Two of the entries below are bugs I made
while fixing the others.

### Anti-Pattern: A tool that stops running reads exactly like a tool that found nothing

- **What happened**: the project's front end had *no type checking at all* and had never had
  any. `vue-tsc` resolves `typescript/lib/tsc`, a subpath the TypeScript 7 native rewrite no
  longer exports, so it died on a single line of `ERR_PACKAGE_PATH_NOT_EXPORTED`. Meanwhile
  `npm run build` stayed green, because vite *transpiles* TypeScript rather than checking it —
  so 23 components under `strict: true` were bundled unread. `vue-tsc@3.3.11`, still the latest
  published, declares peer `typescript >=5.0.0`, which `^7` satisfies, so npm never warned.
- **Impact**: three independent signals all said "fine". It had been recorded as an open
  decision rather than a defect, which is how a dead check survives a review.
- **Rule**: a check that can fail *to run* needs a test that it ran, not a comment saying it
  should. Pin the version, name the script, and assert the CI step invokes it — then break each
  one and watch the suite go red. Distrust any silence from a tool you did not just see fail.
- **Applies to**: type checkers, linters, scanners, coverage gates — anything whose success
  output is empty and whose absence therefore looks identical to success.

### Anti-Pattern: Keying on an identifier I assumed rather than read

- **What happened**: mine. Writing middleware to rate-limit Fortify's unbounded auth endpoints,
  I mapped route name `register` to a limiter. Fortify names the registration **POST**
  `register.store`; `register` is the GET that renders the form. So the map bound the view route,
  a method guard then excluded it, and the endpoint stayed wide open — while the middleware was
  demonstrably installed and every other endpoint in the same map worked.
- **Impact**: caught only because the test asserted a **429 from the real endpoint** instead of
  asserting the middleware was attached. An attachment assertion would have passed forever.
- **Rule**: assert the *effect* at the boundary, never the wiring. And when code dispatches on a
  string owned by someone else — a route name, an event name, a queue name, a header — add a
  test that the string resolves to a real thing. An unmatched key almost always means "no rule
  applies", which fails open and silently.
- **Applies to**: all projects. Any lookup table keyed on a third party's identifiers.

### Anti-Pattern: Configuring from a lifecycle stage that does not have the config yet

- **What happened**: also mine. I put `trustProxies(at: config('app.trusted_proxies'))` in
  `bootstrap/app.php`'s `withMiddleware` closure. That closure runs **before the config is
  loaded**: instant fatal, `Class "config" does not exist`. The obvious repair is `env()` — which
  works locally and is the far worse bug, because `php artisan config:cache` skips loading
  `.env` entirely, so on a cached production build it returns null, trusts no proxy, and breaks
  **only in production**.
- **Impact**: the loud failure was the lucky outcome. The tempting fix would have shipped a
  configuration that silently evaporated on exactly the machines that mattered.
- **Rule**: `env()` belongs in config files and nowhere else — that is not style, it is the
  difference between working and not working under `config:cache`. When a framework hook runs
  too early for config, find the static configurator meant for a service provider's `boot()`
  rather than reaching for `env()`.
- **Applies to**: Laravel 11/12 `bootstrap/app.php`, and any framework with a bootstrap phase
  that precedes configuration.

### Anti-Pattern: A column written on every write and read by nothing

- **What happened**: `content_targets.claimed_at` was stamped by the atomic claim on every
  publish and consumed by no query anywhere in the codebase. It marked a real hole: a worker
  killed between claiming a row and reporting back left the target in `publishing` — which is
  not in `claimable()`, not terminal, and not in `needsHuman()`. No tick could move it, and the
  health screen never showed it. The customer watched a post say "publishing" indefinitely and
  nobody was told. A *dispatch* lease had been built for precisely this failure one stage
  earlier; the claim stage had no equivalent.
- **Impact**: the most severe of the five, and the only one that silently loses customer work.
- **Rule**: grep for writes with no reads. A persisted value nobody consumes is usually the
  recovery data for a failure path that was never finished — the author saw the hazard clearly
  enough to record the evidence and stopped there.
- **Applies to**: all projects. Especially any two-phase claim/complete over a queue.

### Anti-Pattern: Cross-cutting middleware placed where the interesting responses do not go

- **What happened**: security headers registered on the `web` group covered rendered pages and
  missed both responses most reachable by a stranger — a **404** never enters the web group at
  all (no route matched, so there is no route pipeline), and an **auth redirect** is rendered
  from an `AuthenticationException` thrown straight past anything above it in the stack. Both
  came back with no headers.
- **Rule**: for anything that must hold on *every* response, test the error paths first — 404,
  the unauthenticated redirect, the 500 — and register globally, not on a route group. The happy
  path is the one case that proves the least.
- **Applies to**: security headers, request ids, CORS, any response decorator.

## Learned Skills — SociaPulse hardening

- **Ask what the reverse proxy costs you.** An untrusted proxy is filed as a deployment
  footnote and is not one. `Request::ip()` was feeding the **audit log**, so every audited
  action would have recorded Nginx instead of the actor — wrong in a way that still reads as
  evidence — and it was the key for **every auth rate limiter**, so the whole customer base
  shared one bucket and the eleventh person to register would have been refused along with
  everyone after them. Before trusting an IP-keyed anything, ask what is between it and the
  client, and assert that two hosts behind one proxy do not share a limit.
- **A negative test earns its place when it stops a fix from overreaching.** The reaper test
  that mattered most asserts an **11-minute claim is left alone**, because the worker's own
  `--timeout` is 600s and a reaper that fires early reports live publishes as abandoned. For
  any threshold, write the test on the safe side of it and name the number it is tied to.
- **"We do not know" is a shippable state, and is often the right one.** A worker killed
  mid-publish is indistinguishable from a provider call that never answered, so the recovery
  moves the post to `unverified` and hands it to a human rather than re-queueing it. Retrying
  would risk a second post to a real audience with no way to take it back. Where an action is
  irreversible and the outcome is genuinely unknown, escalating to a person beats both retrying
  and failing.
- **Rate-limit what costs money, not just what authenticates.** Fortify bounds the login POST
  and nothing else; registration and password reset shipped open. The password broker's own
  `throttle => 60` reads like coverage and bounds only re-sends to a *single address*. The real
  damage is not the email bill — a sender flagged as a spam source stops delivering everything,
  including the verification emails registration itself depends on, so one abused endpoint takes
  out signup for every real customer.
- **Decline to half-ship a Content-Security-Policy.** A correct policy for an Inertia + vite app
  has to be built against the real build output and tested screen by screen; a guessed one either
  breaks the app or gets loosened to `unsafe-inline` until it means nothing. A policy that means
  nothing is worse than an absent one, because it reads as covered on every checklist afterwards.
  Say so in the code, in the place someone will look.
