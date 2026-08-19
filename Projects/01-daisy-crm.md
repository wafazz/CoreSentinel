# DAISY 2.0 — Enterprise OmniChannel CRM (hand-rolled PHP, no framework)

> **Status**: Active Development — multi-tenant SaaS + platform-owner billing console built (uncommitted on `fakrul-2.0-e001`)
> **Last Updated**: 2026-08-04

## Business Context
- **Client**: Daythree (Malaysian CX / BPO firm — inferred from seeded KB content, not confirmed by Fakrul)
- **Status**: active
- **Priority**: high
- **Revenue Model**: enterprise CRM / SaaS-ready, SEA + Malaysia BPO market
- **Deployed**: No — local only

## Overview
- **Root**: `C:\Users\fakrul.hakim\Desktop\Day3-Project\Daisy 2.0 - Development\dev-ver-002`
- **Stack**: **PHP 8.2, NO framework** (hand-rolled). MySQL 8 target / MariaDB 10.4 local.
  Bootstrap 5 + Alpine.js + jQuery. Composer used only for leaf libs (mPDF, PhpSpreadsheet,
  Symfony Mailer, HTMLPurifier, AWS SDK, TwoFactorAuth, Flysystem SFTP).
- **Type**: OmniChannel CRM — ticketing, flow builder, workflow engine, AI/KB, campaigns
- **Auth**: session-based + TOTP MFA (`robthree/twofactorauth`), bcrypt cost 12
- **Database**: `daisyx` (dev) / `daisy_test` (tests) — migrations through **041** (SaaS + billing added). Migrations are file-based, no runner: `source database/migrations/0XX.sql`; test bootstrap auto-applies all to `daisy_test`.
- **Local URL**: `http://localhost:8080` — `admin@daisyx.test` / `Admin@123`
- **Scale**: 299 files, ~62k lines, 226 commits (2026-05-19 → 2026-06-14)

## Key Patterns
- **NOT Laravel.** Never suggest Laravel/Eloquent idioms. No Models, Services, Repositories,
  or ViewModels exist despite the plan claiming MVVM.
- **Modules are flat files of plain functions**: `modules/<name>/controller.php` defines
  `tickets_index()`, `omnichannel_send()`. Dispatcher resolves `module@action` to a function.
- **Routing is one hardcoded ~230-entry table** in `app/Core/App.php:116-410`. First-match-wins,
  so register static literals BEFORE `{id}` patterns. Router supports no closures, no middleware.
- **Real-time is SSE, not WebSocket** — `api/v1/events.php`, 2s tick / 55s window, backed by
  `sse_event_queue`. Chat widget uses 3s polling.
- **Multi-tenancy via `tenant_id`** on 42 of 57 tables, enforced in application queries only —
  no DB row-level security. Always scope queries by tenant explicitly.
- Migrations use an `information_schema` + `PREPARE` guard for idempotent ALTERs (MySQL 8.4
  removed `ADD COLUMN IF NOT EXISTS`; `DELIMITER` can't run under `PDO::exec()`).
- Feature work is planned in `docs/superpowers/plans/` + `specs/` — NOT in the root plan file.

## Completed
1. Foundation — router, DB, session, auth, RBAC, view engine, migrations 001-006
2. Core business — contacts, ticketing w/ scenarios, form builder (23 field types), reporting
3. Engines — flow builder (36 node types), workflow engine, queue, channel config
4. AI — provider abstraction (OpenAI/Azure/Anthropic/Gemini), copilot, usage analytics
5. Real-time — SSE, presence, live chat, embeddable widget, exports, scheduled reports
6. Omnichannel workspace, external API enrichment, campaigns, SLA monitor, KB portal, Sentinel
7. **Multi-tenant SaaS** — tenant resolution (domain/`/{slug}/`), platform operator tier
   (`PlatformAuth`), 3 onboarding modes (direct/request/invite), owner-managed plans + features,
   priced custom-module add-ons, per-tenant branding/custom-fields/domain (migrations 029-036)
8. **Platform-owner billing console** (2026-07-23, uncommitted) — per-plan seat limits, subscriptions,
   invoices + manual/offline payments, invoice view + mPDF PDF, tax, company profile (+logo), AI agent
   keys, revenue dashboard (migrations 037-041). See Work Log.

## Remaining
- **Transport connectors** — WhatsApp / email / SMS ingestion + delivery (see anti-patterns)
- Skills-based routing (de facto baseline for enterprise/BPO buyers)
- PDPA cross-border transfer register (small effort, uncontested vs global vendors)
- WFM / QA / call scoring — ship as a priced module, not v1
- API documentation, README (the plan's own Phase 6 admits docs are unwritten)

## Anti-Patterns (This Project)
- **The omnichannel transport layer does not exist.** All 9 channels are config UI only.
  `modules/api/webhooks.php:15` queues inbound payloads with `type='webhook'` and **no
  `job_class`**, but `bin/queue-worker.php:69` dispatches on `job_class` — every webhook
  fatals, retries 3x, dies. No consumer exists. `app/Jobs/` holds exactly one class.
  Only outbound HTTP in the codebase is to AI providers and `ExternalApi.php`.
- **`App\Exceptions\*` never autoloads.** Four classes in one `Exceptions.php`; PSR-4 can't
  resolve them, nothing requires the file. `RBAC.php:150` throwing `ForbiddenException`
  fatals with "Class not found". Catches at `App.php:491-493` are dead code. Invisible when
  testing as super-admin. **Verified empirically, not theorised.**
  → **FIXED in dev-ver-003 on 2026-08-04** (split one-class-per-file; see Work Log).
  **Still present in dev-ver-002** — apply the same split there if that line is resumed.
- **`composer.lock` is incompatible with the declared PHP floor** — pins `zipstream-php 3.2.2`
  (needs `^8.3`) while `composer.json` says `>=8.2` and CI runs 8.2. CI fails at
  `composer install`. Workaround: `--ignore-platform-req=php-64bit`.
- **`ci.yml` needs `.env.test`**, which `.gitignore` excludes via `.env.*` with no negation.
  Second CI blocker. CI has been red since ~2026-06.
- **Migration 019 is MySQL-8-only** — `expires_at TIMESTAMP NOT NULL` relies on
  `explicit_defaults_for_timestamp=ON`. Fix: add `DEFAULT CURRENT_TIMESTAMP`.
- **Queue worker race** — `bin/queue-worker.php:40-65` runs `SELECT ... FOR UPDATE SKIP LOCKED`
  with no enclosing transaction, so the lock releases immediately and two workers can
  double-process. Also MariaDB <10.6 lacks `SKIP LOCKED` entirely.
- **`sse_event_queue` has zero indexes** and is polled every 2s per connected agent.
- **`daisy_implementation_plan.md` is stale and misleading** — claims 70 tests (actual ~296),
  documents 6 of 28 migrations, lists `flow_versions`/`flow_executions` which never existed,
  and describes a directory structure that does not exist. Do not trust it.
- `views/flows/builder.php` is 2,907 lines; `modules/admin/controller.php` is 1,348.
- `tests/bootstrap.php:22` silently falls back to `.env` when `.env.test` is absent — running
  tests without `.env.test` mutates the DEV database.
- `mysql.exe` can return exit code 0 while a statement fails. Grep output for `ERROR`; do not
  trust `$LASTEXITCODE` when sourcing SQL.

## Work Log

### 2026-08-17 — WhatsApp Business Cloud API Transport (Items 5, 6, 7 Completed)
- **Built full Meta WhatsApp Cloud API integration**:
  - `app/Core/WhatsAppDriver.php`: Outbound text, media (image, document, audio, video), and template message delivery to Meta Graph API (`v20.0`).
  - Webhook verification: `GET /api/v1/webhooks/whatsapp` responds with `hub.challenge` after validating `hub.verify_token` against active WhatsApp channels.
  - Inbound webhook parser: `POST /api/v1/webhooks/whatsapp` extracts incoming messages/media, deduplicates by `wamid`, automatically resolves/creates contacts and interactions, dispatches to Flow/Bot runtime (`FlowRuntime`) or routes to agents (`OmniRouter`), and broadcasts via SSE (`OmniEvents`).
  - Delivery status updates: Ingests Meta status updates (`delivered`, `read`, `failed`) and updates `interaction_messages` metadata.
  - Omnichannel inbox integration: `omnichannel_send()` automatically dispatches outgoing messages to Meta Cloud API when `interaction.channel_type === 'whatsapp'`.
  - Flow builder integration: Added `channel.send_whatsapp` node handler in `FlowRuntime`.
  - Test suite: `tests/Feature/WhatsAppDriverTest.php` (9 tests, 56 assertions, all green). Total test suite: 416 tests passing.

### 2026-08-04 (pm) — CXone phase 2: live tenant, right agent, softphone config found
- **Everything below is VERIFIED against Daythree's PRODUCTION tenant**, not inferred. There is
  still no sandbox — every probe hit the live CelcomDigi BU.
- **The credentials Fakrul supplies matter more than the credentials working.** Channel 9 was
  configured with `anas.rosli@daythree.co` (icAgentId 69050025). It authenticated perfectly, so
  nothing looked wrong — but that agent holds only the `Auto Unbar DEV` skill. The agent Fakrul
  named, `fariz.zainol@daythree.co` (**icAgentId 34597520**), additionally holds **`Test IVR`
  (skill 31504632)**, which is why only that agent can be routed the test inbound call.
  → **A successful token exchange proves NOTHING about routability.** Always check `icAgentId`
  from the `id_token` and then `GET /agents/{id}/skills`. Channel 9 swapped, set **active**,
  `cxone_base_uri` pinned, token cache cleared; `bin/cxone-doctor.php` now runs green.
- **Tenant facts**: tenant `11eef394-8843-acf0-9b64-0242ac110003`, BU **4608239**, cluster A34,
  area au1, API base `https://api-au1.niceincontact.com`, 22 voice POCs, 128 voice skills.
- **Reading the vendor's own npm SDK beat the vendor's docs, by a mile.** `@nice-devone/core-sdk`'s
  `src/constants/api-uri-constants.js` lists **every** Agent API path, and `acd-session-manager.js`
  shows the request/response shape. Result: all our hand-written paths matched **verbatim**, the
  response key is `sessionId` (already handled), and **POST is confirmed** (GET → 405, POST → a
  400 *validation* error). Zero code changes needed. `npm` isn't required — pull the tarball from
  `registry.npmjs.org` and extract with `C:\Windows\System32\tar.exe` (git-bash's `tar` chokes on
  `-C C:\...`, reading the drive letter as a remote host).
- **The WebRTC softphone is licensed and permitted**: BU feature `IntegratedSoftphone` (productId
  53) = enabled; agent permissions `AgentSoftPhone: View` + `AgentSoftPhoneAutoAccept: Enable`.
- **Its config lives at `GET /InContactAPI/services/v30.0/agents/{agentId}/agent-settings`** —
  `webRTCType AudioCodes`, `wss://wrtc-pri.niceincontact.com` + `wrtc-sec`, domain
  `niceincontact.com`, **`webRTCDNIS +1700499993034`**. That settles the CSP `connect-src` hosts.
- **Audio flows browser→CXone, not CXone→browser**: the page SIP-registers to the AudioCodes SBC
  as `setAccount(agentId, agentId, '', '')` (agent id is the SIP user; **no password**), then on an
  AgentLeg event **the browser dials `webRTCDNIS`** with the `agentLegId` in an `X-` header.
- **Still blocked on ONE value**: `startSession` returns `400 InvalidPhoneNumberOrStation` for all
  11 station candidates tried (blank, `softphone`, `WebRTC`, the agent id, SIP URIs, the DNIS in
  4 formats). `/v30.0/stations` returns 0 rows — CXone stations are created at login, not
  pre-provisioned. **Stopped guessing at 3 strikes.** Definitive next step: log into
  `https://cxagent.nicecxone.com/` as that agent with Integrated Softphone selected and read the
  real `POST /agent-sessions` body from DevTools.

### 2026-08-04 — NICE CXone inbound call pickup, phase 1 (dev-ver-003, uncommitted)
- **Different checkout line**: `dev-ver-003/DAISYX` on `main` @ ff5bd8d, migrations at **028**
  before this work → now **029**. This is NOT the dev-ver-002 line (which is at 041 with the
  SaaS/billing console). Do not assume SaaS tables exist in dev-ver-003.
- **Goal**: an authorised agent picks up an inbound voice call from inside DAISY.
  Fakrul's explicit constraint: **audio terminates in the BROWSER**, not a deskphone/SIP.
- **Research (verified, with doc URLs)**: browser audio is genuinely supported —
  `@nice-devone/voice-sdk`'s `CXoneVoiceClient.connectServer()` takes an `HTMLAudioElement`
  and does `getUserMedia`; transport is SIP-over-WSS to an AudioCodes SBC. **It is a JS/TS
  browser SDK — PHP cannot carry the audio.** So the architecture is hybrid: JS softphone in
  the page, PHP for call control + tokens + CRM linkage. NICE names "Custom Agent Client" as a
  supported use case. Accept path (verb unverified):
  `.../v23.0/agent-sessions/{sessionId}/interactions/{contactId}/accept`. Regional base URI
  MUST be discovered via `/.well-known/cxone-configuration?tenantId=`. Ring signal is a
  0–60s long-poll `get-next-event` (200 = events, 304 = none) — **never inside PHP-FPM**.
- **Gates are commercial, not technical**: real CXone tenant + Integrated Softphone enabled by
  an account rep + app registration approved by NICE (~2–3 days). **No documented sandbox.**
  npm packages are `"license": "UNLICENSED"` — get written clarity before shipping.
- **Built (provider-independent half)**: migration `029_voice_call_control.sql` (call lifecycle
  on `voice_calls`, cxone credential columns, `users.cxone_agent_id`/`cxone_session_id`,
  `omnichannel.call.answer` permission); new `CallControlInterface` kept separate from
  `VoiceDriverInterface` so the transcript-only webhook driver is untouched;
  `omnichannel_call_answer()` claiming the call with a **single guarded UPDATE** (rowCount 0 =
  lost the race) rather than the racy check-then-update `omnichannel_claim` uses.
  **9 new tests; full suite 305 tests / 640 assertions / 0 failures.**
- **FIXED — the long-standing `App\Exceptions\*` autoload bug** (open since the 2026-07-21
  survey). Root cause is exactly as first recorded: `app/Exceptions/Exceptions.php` declared
  **four classes in one file**, which PSR-4 (`App\ => app/`, in both the hand-rolled
  `Autoloader` and `composer.json`) cannot resolve — it looks for
  `app/Exceptions/ForbiddenException.php`. The composer classmap contains **no** `App\` entries,
  so nothing rescued it. `RBAC::require()` therefore fataled with "Class not found" and the
  `catch` blocks at `App.php:492-495` were dead code.
  *Why it hid for months*: 8 test files did `require_once BASE_PATH.'/app/Exceptions/Exceptions.php'`
  in `setUp()`, so the suite was green while runtime was broken. `TicketEditRbacTest` even
  carried a comment naming the bug.
  **Fix**: split into one class per file (Forbidden/NotFound/Validation/Unauthorized),
  deleted the combined file, removed all 8 `require_once` workarounds. Verified with a probe:
  all 4 autoload, and `RBAC::require()` throws a catchable `ForbiddenException` (code 403).
  Suite still 305/640/0.
  ⚠️ **My interim claim that `app/Exceptions*` was "absent entirely" was wrong** — a `Glob` for
  `app/Exceptions*` never looked inside the directory. Corrected same session.
- New JSON endpoints still prefer `RBAC::can` + `View::json(...,403)` over `RBAC::require`,
  because require() → `App::run` → `handleError()` renders an **HTML** page, wrong for a
  `fetch()` caller. `omnichannel_close` already used this pattern.
- **Incident**: migration 029 wedged an ALTER on `voice_calls`; the killed thread held the
  metadata lock, shutdown hung, mysqld needed a force-kill. InnoDB recovered, 83 tables intact,
  CHECK TABLE OK, **no data lost**. The instance had already crash-recovered before the session
  began. Two rules updated in 55-self-evolution.md (stderr capture; wedged-ALTER handling).

### 2026-07-23 — Platform-owner SaaS billing console (all UNCOMMITTED on `fakrul-2.0-e001`)
- Iterative build of the operator monetisation surface. Full details in project-root `CHANGES.md`
  (new this session, plus a standing rule to keep it current after every task). Suite: **338 green**.
- **Seat limits** (037): `plans.max_users` (0=unlimited), enforced in `admin_storeUser`, surfaced in
  admin plan/users + platform tenant pages.
- **Billing core** `app/Core/Billing.php` (038): one `subscriptions` row/tenant, `invoices`/`invoice_items`/
  `payments`. No gateway (Fakrul deferred) — settled via manual `payments.method='manual'`, the seam a
  gateway plugs into. Seat-aware self-service plan change (operator override bypasses cap); auto-void +
  reissue the open invoice on plan change (paid untouched); per-period duplicate guard (void doesn't block);
  void invoices hidden from tenants but kept for the operator.
- **Invoice document** `app/Core/InvoiceRenderer.php` — ONE HTML doc drives both the web view and the mPDF
  PDF (`Exporter::toPdfDocument`, A4 portrait). IDOR-guarded tenant access. Company profile = issuer, logo
  embedded as base64 data-URI (renders in HTML + mPDF), default tax snapshotted per invoice.
- **Platform console**: Company Profile (+ dependency-free vanilla-JS canvas logo cropper), Tax Management
  (SST), AI Agent settings (OpenAI/Claude/Gemini, keys encrypted via `AI::encryptKey`, live `testProvider`),
  revenue dashboard on Overview (MRR/ARR/outstanding/collected + plan distribution), collapsible sidebar
  dropdown groups with count badges. Operator-global settings live in the new `platform_settings` k/v table.
- **CSS**: global default `.card` body padding, scoped with `:not(:has(.card-header)):not(:has(.card-body)):not(:has(table))`
  so it can't regress the 111 header cards / table cards / inline-padded cards. `.card-body` for header-card bodies.
- Tests: `tests/Feature/BillingTest.php` (21). New anti-pattern captured (test leakage via non-truncated
  shared tables) + skills (mPDF data-URI, safe global CSS `:has()` defaults, financial snapshotting).

### 2026-07-22 — Analytics module (new gateable feature) — full squad, all phases
- Built `modules/analytics/` — a read-only cross-module executive KPI dashboard (tickets,
  contacts, omnichannel conversations, campaign sends, AI tokens, avg resolution time), with
  7/30/90-day windows, period-over-period deltas, and inline-SVG sparklines. Deliberately
  distinct from the existing `reports` module (Reports = tabular/exportable; Analytics = read-only
  visual insight, no export). Zero new dependencies, zero new tables.
- Registered as a **gateable feature** so it appears in the platform features listing and is
  bundleable per-plan from the console — see the new Pattern Library entry "Add a gateable
  feature module". Migration `036_analytics.sql` (feature row + `analytics.view` permission +
  grants to super-admin/system-admin) applied to `daisyx` and verified live. Plan assignment
  left to the console (enterprise `'*'` gets it free).
- Files: `modules/analytics/controller.php`, `views/analytics/index.php`,
  `database/migrations/036_analytics.sql`, route in `app/Core/App.php:278`,
  `config/plans.php` catalog entry, `views/components/sidebar.php` nav item,
  `tests/Feature/AnalyticsTest.php` + `tests/Feature/AnalyticsGatingTest.php`.
- Ran the full 17-agent gate. Cato found a real timezone bug (PHP `date()` series keys vs SQL
  `DATE()` buckets) + rolling-vs-calendar window skew + unguarded negative resolution time —
  **all three fixed** (anchored every window to `CURDATE()`, added `resolved_at >= created_at`).
  See the new self-evolution anti-pattern. Cipher/Argus/Aegis clean; Ledger negligible cost.
- **Analytics suite: 14/14 green (29 assertions).** Migrations are now through 036.
- Ops follow-up (non-blocking, if a tenant grows large): add composite `(tenant_id, created_at)`
  / `(tenant_id, resolved_at)` on `tickets` before considering any rollup table (Ledger/Aegis).

### 2026-07-21 — Codebase survey, local environment, competitor research
- Full architecture survey. Established the stack is hand-rolled PHP, not Laravel/MVVM.
- Stood up local env on XAMPP (PHP 8.2.12 + MariaDB 10.4): enabled `gd`/`zip`, installed
  Composer to `C:\xampp\php\composer.phar`, created `.env` + `.env.test`, built both DBs,
  added a :8080 vhost with DocumentRoot at `public/`, set `explicit_defaults_for_timestamp=ON`.
  All XAMPP config files backed up as `*.bak-daisy`.
- All 4 suites green: Unit 78 · Integration 18 · Feature 185 (2 benign skips) · Security 15
  = 296 tests, 621 assertions, 0 failures. Verified login → dashboard end-to-end over HTTP.
- Found and empirically confirmed 3 bugs (see Anti-Patterns). **None fixed — awaiting approval.**
- Ran competitor feature-gap research (deep-research, 110 agents, 27 sources, 17/25 claims
  confirmed). Key results: transport connectors are entry-tier table stakes everywhere
  (Zendesk Suite Team $55, Genesys CX 2 $115 / CX 2 Digital $95) so the gap is
  category-definitional; WFM/QA is a paid add-on at every competitor ($50/agent/mo Zendesk,
  Genesys CX 3 $155+) so it is monetisable, not a blocker; AI is metered everywhere
  (Genesys 250 tokens per ORG/month at ~$1 overage, HubSpot 50 credits per resolution) making
  DAISY's unmetered bring-your-own-key AI a genuine commercial differentiator.
  Malaysian PDPA transfer register is a small-effort wedge, but the data-residency angle was
  REFUTED — do not pitch residency as a legal necessity.
  **Research coverage gaps**: only Zendesk + Genesys fully verified. Freshdesk claims refuted
  outright, Salesforce returned zero verified claims, ClickUp not researched. No verified
  evidence on LINE/Viber/WeChat/Zalo, Bahasa Malaysia quality, or local telephony.
- **No application source files edited this session.**
