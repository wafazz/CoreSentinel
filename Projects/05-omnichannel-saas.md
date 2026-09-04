# Omnichannel Messaging SaaS — Multi-tenant WhatsApp/Telegram/Live-Chat platform with a visual flow builder

> **Status**: Building — `MILESTONE-011` (unified inbox) delivered; 001–011 done, 012+ outstanding
> **Last Updated**: 2026-08-25

## Business Context
- **Client**: personal project — *`ASSUMPTION A-01`, unconfirmed by Fakrul*
- **Status**: active `[LEARN]`
- **Priority**: high
- **Revenue Model**: B2B SaaS subscription (plans/limits configurable; **no prices assumed** — `U-05`)
- **Deployed**: No

## Overview
- **Root**: `/Users/wafazztechnology/Desktop/Codex Lure/project/SaaS-OnmiChannel`
- **Stack**: NestJS 11 + Fastify 5 + TypeScript **5.9.3** (not 7 — the toolchain peer-caps below it) + Prisma 7 + **PostgreSQL 18** + Redis · React 19 + Vite 8 + `@xyflow/react` 12
- **Type**: Multi-tenant SaaS (omnichannel messaging + workflow automation)
- **Auth**: JWT access + rotating refresh (reuse-detected), argon2id — separate token audiences for platform vs tenant
- **Currency**: single-currency — `A-10`, unconfirmed
- **Payment**: **none decided** — port + manual adapter (`ADR-016`, `U-04`)
- **Database**: **PostgreSQL 18**, shared schema, mandatory `tenant_id` + **Row-Level Security** (`ADR-015`, `ADR-018`). Local machine runs 14.18 (EOL 2026-11-12) — upgrade required.

## Key Patterns
<!-- New stack for CoreSentinel — Learn Mode active. Graduate these into 11-pattern-library.md at Phase 8. -->
- **Tenant isolation in 4 layers** — request guard derives `tenantId` from the principal (never the payload) → Prisma `$extends` injects `tenant_id` on every tenant-owned query and refuses queries with no tenant context → schema indexes lead with `tenant_id` → **PostgreSQL RLS** policy on `current_setting('app.tenant_id')`, set per *transaction* (`SET LOCAL`, never session — pooled connections leak session state). Layers 1–3 are application code and fallible; RLS holds even for raw SQL. Connect as a role without `BYPASSRLS` or the whole layer is decorative.
- **Framework chosen for its enforcement point, not its popularity** — NestJS won on the guard/DI layer being one place to enforce auth→role→tenant→permission→ownership. A framework without it pushes the top risk onto every developer, every query.
- **Immutable version + pinned FK = structural guarantee** — `FlowExecution` holds `flow_version_id` to an immutable published row, so "editing a draft can't change production" is enforced by the schema rather than by care.
- **Hybrid graph storage** — JSON document is authoritative and loaded whole in one read; the normalised node table is a *rebuildable projection* for analytics only. Name it "derived" in the schema comment, or someone will write to it.
- **Separate entity beats a boolean flag for dangerous states** — internal notes are `conversation_notes`, not `Message{internal:true}`. The adapter port only accepts `Message`, so "note leaked to customer" has no code path.
- **One node per queue job**, not a loop in one job — every step individually retryable, bounded, back-pressured, and `delay` becomes a queue feature instead of a held thread.
- **Verify the toolchain before choosing an architecture that depends on it** — TS 7 decorator metadata was spike-tested (compile + read emitted JS) before committing to decorator-based DI. Cost: two minutes. Would have cost a milestone.

## Completed
1. Master spec reformatted to valid Markdown (`Prompt/MasterPrompt.md`, 88 sections + TOC), original backed up
2. `MILESTONE-001` — `Planning.md`: all 74 MasterPrompt §86 sections, ~110 requirements, full traceability matrix (every row `Planned`)
3. `docs/documentation.md` module index (protocol `53`)
4. `session-memory.md`

## Remaining
- **Approval gate** — blocks everything
- `MILESTONE-002` foundation → `MILESTONE-030` production readiness (see `Planning.md` §67)

## Anti-Patterns (This Project)
- **Never** trust a client-supplied tenant id. It comes from the authenticated principal, always.
- **Never** fetch a tenant-owned row by id alone — `findFirst({ where: { id, tenant_id } })`, no exceptions. Bare-id lookup is how IDOR ships.
- **Never** blindly retry a flow node that may already have dispatched a message — idempotency key `(execution_id, node_id, attempt)` first.
- **Never** add a scripting/eval node to the flow engine. Conditions are a fixed operator set (MasterPrompt §60).
- **Never** assert WhatsApp/Telegram provider behaviour from memory — it is `REQUIRES VERIFICATION` until read in the official docs (MasterPrompt §6).
- **Never** cache conversations/messages/contacts — mutable and tenant-sensitive; a stale inbox is worse than a slow one.
- Prisma 7 driver adapters are per-engine: `@prisma/adapter-pg` (PostgreSQL), `@prisma/adapter-mariadb` (MySQL/MariaDB). `@prisma/adapter-mysql` **does not exist** — verified 404.
- **Postgres partial unique indexes** replace application-level invariants: one `PUBLISHED` version per flow, one `WAITING` execution per conversation, and soft-delete uniqueness — all DDL, no sentinel column. Don't port the MySQL soft-delete workaround; it solves a problem PostgreSQL doesn't have.

## Work Log
### 2026-08-24 — Init + Phase 1 Planning
- Reformatted `MasterPrompt.md`; verified content preservation with a line-level diff (recovered one line missed on the first read pass — the file's last line fell outside the range I'd read).
- Phase 0 intake: work mode recorded as an assumption, not a fact, after Fakrul declined the intake questions.
- Phase 1.5: Pattern Library has **no Node/TypeScript backend entry** → Learn Mode ON.
- Scout sprint: verified every version against the live npm registry + `nodejs/Release/schedule.json`. Key findings — Node 20 EOL 2026-04-30 (machine is on it); TypeScript 7.0.2 is `latest` and **does** emit `design:paramtypes` (spike-tested); TypeORM `latest` is 1.1.0 with 0.3.31 as `legacy`; `@xyflow/react` 12.11.3 is MIT.
- Wrote `Planning.md`. Stopped at the approval gate with zero implementation, per MasterPrompt §3/§4/§88.
- **Mid-session change**: Fakrul directed PostgreSQL instead of MySQL. Recorded as `ADR-018` — a documented deviation from MasterPrompt §57, not a silent swap. Verified PG 14.18 installed and running locally (EOL 2026-11-12) → target PG 18. The move upgraded tenant isolation from 3 layers to 4 by adding RLS, the strongest available answer to `R-01`.
