# WhatsApp Business Automation SaaS — Multi-tenant WhatsApp inbox, campaigns, automation and visual chatbot builder on the official Meta Cloud API

> **Status**: In development — PH-03 of PH-00..PH-15 complete · **[LEARN]** (Meta Cloud API built but never run against live Meta; AI provider layer and flow canvas still unproven)
> **Last Updated**: 2026-09-16

## Business Context
- **Client**: own SaaS
- **Status**: active (planning)
- **Priority**: to be set after Planning.md approval
- **Revenue Model**: SaaS subscription (Starter / Business / Pro); payment gateway deferred until explicitly approved
- **Deployed**: No

## Overview
- **Root**: `/Users/wafazztechnology/Desktop/Codex Lure/project/SaaS-Whatsapp-Complete`
- **Stack (installed, green 2026-09-16)**: Laravel 13.32 + PHP 8.4 REST, Fortify (headless) + Sanctum SPA cookies, spatie/laravel-permission 8 teams mode, Vue 3.5 + TypeScript 5.9 + Bootstrap 5 + AdminLTE 4.9 + Vite, MariaDB local / MySQL 8.4 CI+prod, Redis + Horizon (8 queues), Reverb, Scheduler
- **Type**: Multi-tenant SaaS
- **Auth**: Sanctum SPA cookie auth + Fortify; tenant context from the principal, never the payload
- **Payment**: none until approved (plan enforcement only)
- **Database**: MariaDB locally (owner choice), MySQL 8.4 in CI and production

## Documents
- `Master-Prompt.md` — owner brief (source of scope)
- `Planning.md` — traceable plan, awaiting approval
- `session-memory.md`, `docs/documentation.md`

## [LEARN] — stacks not yet in the Pattern Library
| Area | Why new |
|---|---|
| Meta WhatsApp Cloud API | No library section; Meta patterns cover Threads only |
| Laravel Reverb | Absent from the Pattern Library |
| Horizon at production scale | Only a Windows note exists |
| Vue flow-canvas library | Absent; Omnichannel used @xyflow/react (React) |
| AI provider layer (PHP) | Needs research |

## Key Patterns
Captured in `11-pattern-library.md` -> *Laravel 13 + Vue 3.5 + TypeScript SPA + Sanctum
(multi-tenant SaaS)* on 2026-09-16:
- Composite `(tenant_id, id)` foreign keys via a `tenantForeign` schema macro (MySQL substitute for RLS)
- Tenant-aware queue jobs: context set in job middleware, never in `handle()`
- Reserve-then-commit usage counters for plan limits under concurrency
- Headless Fortify + Sanctum cookies behind a Vue SPA
- `spatie/laravel-permission` teams mode keyed on `tenant_id`
- Vue 3 + TS toolchain traps (`shallowRef` for Vue Flow, `vue-tsc` as its own CI step)

Reused from the library, not re-invented: Tenant Scope read open/write closed, The Grant Ceiling,
Declared Settings Registry, Registry-Backed RBAC. Still ahead: Versioned Credential Encryption
(PH-02), Claim-and-reap (PH-05), Scheduler Dispatch Lease (PH-05), Rate-Limit What Costs Money (PH-04).

## Completed
1. CS init scaffold (session-memory.md, docs/documentation.md, registration) — 2026-09-16
2. Planning.md — 239 REQs, PH-00..PH-15, matrix, 22 assumptions, 20 open questions, 17 Meta VAL items, 26 risks, verdict NOT READY — 2026-09-16

3. Planning approved 2026-09-16; CD-01..CD-07 accepted as recommended
4. PH-00 Foundation built 2026-09-16: Laravel 13.32 + Vue 3.5/TS 5.9 + AdminLTE 4.9, Horizon (8 queues), Reverb, health, redaction, idempotency, CI; Pest 106/106, Vitest 11/11, Larastan L6 0, CS verify 100/100; code review 7 + security review 3 medium/5 low fixed
5. PH-01 Identity / Multi-Tenancy / RBAC / Audit / Entitlements built 2026-09-16: tenancy core,
   Fortify+Sanctum auth with 2FA, teams-mode RBAC with grant ceiling, invitations and team
   management, append-only audit log, settings registry, plan entitlements with reservations;
   SPA screens S-01..S-04, S-23, S-25, S-28. Pest 221/221 (726 assertions, random order),
   Vitest 16/16, Larastan L6 0 errors, Pint/ESLint clean, vue-tsc 0, prod build green,
   CS verify 100/100. Code review 9 findings fixed; security review 0 critical/high, 9 issues
   fixed with regression tests.
6. Phase 7 Cost (2026-09-16): ~$61 of Opus 5 API spend for the whole project to date
   (planning + PH-00 + PH-01), 206 API calls; 96% of input tokens were cache reads. Two new
   production dependencies (fortify, spatie/laravel-permission); no infra cost delta yet.
7. Phase 8 Persist (2026-09-16): 6 patterns -> `11-pattern-library.md`; 11 anti-patterns +
   4 learned skills -> `55-self-evolution.md`; this profile and `00-identity.md` updated.
8. PH-02 Meta Integration & Webhook Engine built 2026-09-16, all 9 gates run. Graph client with a
   four-class error classifier, webhook ingest (raw-body HMAC, hash dedupe, per-field handlers),
   Embedded Signup with provider-attested WABA binding, versioned credential keyring with rotation,
   health states, 14-day purge, platform replay; SPA S-24 and S-34. Pest 397/397 (1173 assertions),
   Vitest 36/36, Larastan L6 0, CS verify 100/100.
   Five plan changes approved from research (CHANGE-002..006). Phase 5 review: 11 findings, all
   fixed — including two features that were **reported done and were not built**: phone-number
   registration and the Connect button. Phase 6 security (CS 40 by hand): 0 critical, 0 high,
   3 medium + 7 low + 6 info, all fixed.
9. Phase 7 Cost (2026-09-16): PH-02 cost ~$39; project to date ~$100 across 451 Opus 5 calls.
   94 files, 7,890 insertions, **zero new dependencies**.

## Remaining
- **Owner gate on PH-01** — nothing is committed to git yet (owner's standing instruction)
- PH-00: browser probe (S-00 at 1280/390, 300-node Vue Flow) — waived while the Chrome extension
  is unavailable; staging VPS + domain (REQ-FND-009, OQ-018)
- PH-01: browser visual check of S-01..S-04/S-23/S-25/S-28; MySQL 8.4 concurrency run (needs a
  git remote so CI can run)
- **PH-02 entry is blocked** on: staging HTTPS host (REQ-FND-009), a Meta app with a test WABA,
  and CD-03. Start Meta Business Verification + App Review now (R-012) — it is the long pole.
- PH-03..PH-15
- **PH-02 is code-complete but has never met live Meta.** Before it can be called done:
  connect the test WABA through Embedded Signup on staging, confirm the SDK popup and the
  origin check behave, receive a real inbound delivery, and check VAL-09 empirically
  (whether a test number accepts inbound from numbers off its 5-recipient allow-list).
- REQ-META-002 (assisted connection by the platform owner) deliberately deferred to PH-12 with S-31.
- `/security-review` has still never run on this project: no git remote means no `origin/HEAD`.

## Lessons (candidates for 55-self-evolution / pattern library at Phase 8)
- `install:broadcasting --reverb` can crash after writing `BROADCAST_CONNECTION=reverb` but before keys → every artisan command fails at boot (channels.php builds the broadcaster). Recover with `BROADCAST_CONNECTION=null php artisan reverb:install`; ship `.env.example` with `log`.
- Laravel's Redis cache store returns numeric values as strings; `is_int()` checks pass on the array store in tests and fail in production. Use `is_numeric()`.
- Pest `toContain($needle, $message)` treats the message as a second needle.
- `withSchedule()` events register only when artisan boots; tests must call `Artisan::call('schedule:list')` first.
- Vue Flow `ref<Edge[]>` → TS2589; use `shallowRef`.
- `/security-review` needs `origin/HEAD`; on a repo without commits run the CS 40 checklist through an agent instead.
- Laravel Horizon's default `authorization()` allows any `local` environment; override it.

## Key Decisions (proposed)
- Normalized versioned chatbot storage (rows authoritative, compiled graph cached per immutable version)
- One outbound pipeline with 7 gates; ambiguous sends → `unverified`, never auto-resent
- Inbound Router with single reply slot; conversation `control` none/bot/human separate from status
- Composite (tenant_id, id) FKs as the MySQL substitute for RLS
- Vue Flow behind `FlowCanvas` adapter (bus-factor risk)

## Anti-Patterns (This Project)
- `project/whatsapp-saas` (older sibling) uses Evolution API / Baileys (WhatsApp Web). Never port its transport; Master-Prompt §2 forbids unofficial WhatsApp access.

## Work Log
### 2026-09-16 - CS init
- Registered, scaffolded, planning started from Master-Prompt.md

## PH-01 lessons (2026-09-16)
- Grant ceiling must check the *target member's current* permissions (change/deactivate/remove/reactivate), not only the role being granted.
- Last-owner checks: count *other active* owners, and hold a tenant row lock around check + write.
- `Cache::forget` inside a DB transaction runs before commit, so use `DB::afterCommit`.
- Lowercase emails *before* `unique` validation, or mixed-case duplicates reach the DB constraint (500).
- Redirect allowlists must refuse control chars/whitespace: `"/\t/evil"` becomes `//evil` in `location.assign`.
- AuditLogger falls back to the current tenant; account-level actions need `personal: true`.
- SQLite ignores `lockForUpdate`, so concurrency proofs need the MySQL CI run.

### 2026-09-16 - PH-01 close-out (Phase 7 Cost + Phase 8 Persist)
- Re-ran the gates on the delivered tree: Pest 221/221, CS verify 100/100.
- Phase 7 Cost report produced (see Completed #6).
- Phase 8 Persist: wrote the pattern section, the anti-patterns, this profile and the Core index.
- `[LEARN]` stays on. Laravel 13 + Vue 3 SPA + Sanctum + Horizon + Reverb are now written down and
  proven by a green build; **Meta WhatsApp Cloud API, the Vue flow-canvas library at scale, and the
  PHP AI provider layer are still unproven** — the tag drops when PH-02 and PH-09 land.

## PH-02 lessons (2026-09-16)
- An interface method with no production call site is an unfinished feature. `registerPhoneNumber`
  was declared, implemented twice, and never called — every number stayed unregistered and nothing
  in a green 376-test suite noticed.
- A button whose handler only sets local state is a mockup. No Facebook SDK was loaded anywhere
  while the origin-check code around it was carefully correct.
- `openssl_encrypt` zero-pads a short key and succeeds. Validate against
  `openssl_cipher_key_length()`.
- A scripted edit must assert its anchor; `str.replace` matching nothing is a silent no-op that
  reports success.
- Meta's docs contradict themselves on webhook retry duration (7 days vs 36 hours). Plan against
  the worse figure and record the choice.
- Meta's own Embedded Signup sample validates origin with `endsWith('facebook.com')`. Never copy a
  provider's security checks.

## PH-03 lessons (2026-09-16)

PH-03 (Contacts, tags, attributes, segments, consent, import & export) built 2026-09-16, all 8
gates walked. 10 tables, 38 routes, 5 screens. 569 PHP + 44 Vitest tests, CS verify 100/100.

**The one worth carrying to every project: a helper that is correct on the production database and
wrong on the test database is invisible to the whole test suite.**
Escaping `%` and `_` for a `LIKE` with `addcslashes($v, '%_\\')` is only half the job. MySQL treats
`\` as the default LIKE escape character. **SQLite has no default escape character at all**, so the
same escaped pattern matches a literal backslash there. This project tests on SQLite and runs on
MySQL. A contact named `100% cotton` was unfindable; a segment rule `name contains %` silently
returned the wrong audience. It was only caught because a test asserted the *literal* behaviour
("searching for % finds the one contact containing %") rather than the negative one ("searching for
% does not return everything") — the negative assertion passes on both databases while one of them
is broken. The fix is an explicit `ESCAPE '\'` clause. The same pattern was already in
`AuditLogController` from PH-01 and is still there, tracked as FU-03-01.

**Second: an arch rule you have not seen fail is not a rule.** Four boundary tests were written for
PH-03 and two of them passed vacuously at first — the consent-writer rule matched doc comments and
read paths, and the `Row::fromValues()` ban flagged the two files whose comments explain why the ban
exists. Both were fixed to scan comment-stripped code and, for the consent rule, only array literals
passed to `forceFill`/`update`/`insert`. Each rule was then verified by planting a real violation
and watching it fail. A rule that has only ever been seen to pass is indistinguishable from one that
matches nothing.

**Third: a security control test should assert the threat is still real.** The formula-injection
suite asserts the defusal *and*, as a control, that `Row::fromValues()` still produces a live
formula in the installed openspout. Without that control, a library upgrade that changed the
behaviour would leave the defence as dead code with a green suite.

**Library facts worth not rediscovering:**
- `openspout\Reader\*\Options` is a `final readonly class` in 5.x — constructor arguments, not
  assignable properties. `Row` exposes a public `$cells` array, not `getCells()`.
- `aws/aws-sdk-php` is 67 MB for one service; its own `removeUnusedServices` pre-autoload-dump hook
  cuts it to 4.8 MB. The namespace in `extra` is **case-sensitive**: `S3`, not `s3`.
- libphonenumber: a Malaysian fixed line is `isValidNumber() === true`. Validity is not the test;
  number *type* is. `FIXED_LINE_OR_MOBILE` must be accepted or every US contact is refused.

**Chunking a file by row count when the reader yields line numbers** diverges at the first blank
line and silently skips or duplicates rows around every gap. Chunk by the thing the reader actually
yields.
