# Documentation & Traceability Protocol
> "If it isn't documented, it isn't shipped. If it isn't traceable, it isn't done."

---

## 1. Scope & Objective

Every project governed by CoreSentinel must maintain:
1. **Module & Change Documentation** in `docs/documentation.md` (or `docs/modules/<module>/documentation.md`).
2. **Bidirectional Traceability** in `Planning.md` connecting requirements to code, tests, and documentation.

---

## 2. Rule 1: Module & Change Documentation (`docs/`)

### 2.1 File Location
- **Single-module / standard projects**: `docs/documentation.md`
- **Modular / large multi-service projects**: `docs/modules/<module-name>/documentation.md` with an index at `docs/documentation.md`.

```text
project-root/
├── docs/
│   ├── documentation.md                  <-- Master documentation & architecture
│   └── modules/                          <-- (Optional) Modular breakdown
│       ├── auth/
│       │   └── documentation.md
│       └── billing/
│           └── documentation.md
├── Planning.md                           <-- Traceable requirements & delivery matrix
├── session-memory.md                     <-- Active session memory
└── CHANGELOG.md                          <-- User & release facing version history
```

### 2.2 Standard `documentation.md` Template

Every `documentation.md` must adhere to this exact structure:

```markdown
# Module / System Documentation: [Module Name]

> **Status**: Active | **Last Updated**: YYYY-MM-DD | **Maintainer**: Iris / [Developer]

## 1. Overview & Purpose
- High-level summary of what this module or system does.
- Business problem and requirements it fulfills.

## 2. Architecture & File Structure
| File / Component | Type | Purpose & Responsibility |
|---|---|---|
| `app/Services/PaymentService.php` | Service | Processes charges and handles webhooks |
| `app/Http/Controllers/PaymentController.php` | Controller | Validates HTTP payloads and delegates to service |

## 3. Interfaces, Endpoints & Data Contracts
- **Endpoints / Public Methods**:
  - `POST /api/v1/payments/charge` — Processes card transaction.
- **Request Parameters**:
  - `amount` (int, required, in cents)
  - `currency` (string, required, e.g. `USD`)
- **Responses / Events Emitted**:
  - Returns `201 Created` with payload `{ "transaction_id": "...", "status": "succeeded" }`
  - Emits `PaymentProcessed` event.

## 4. Configuration & Dependencies
- Required environment variables (`.env`):
  - `PAYMENT_GATEWAY_KEY=...`
- Database tables / migrations:
  - `transactions`, `payment_methods`

## 5. Change History & Log
| Date | Change Summary | Impacted Files | Author / Ref |
|---|---|---|---|
| YYYY-MM-DD | Created initial module | `PaymentService.php`, `PaymentController.php` | Iris (`[REQ-01]`) |
| YYYY-MM-DD | Added idempotency key support | `PaymentService.php` | Iris (`[REQ-05]`) |
```

---

## 3. Rule 2: Traceable `Planning.md`

`Planning.md` is the source of truth for technical requirements, architecture, and phase progress. Every feature and task in `Planning.md` must be **100% traceable**.

### 3.1 Traceability Matrix Requirements

Every item in `Planning.md` must carry:
1. **Unique Requirement ID** (`[REQ-01]`, `[REQ-02]`, etc.)
2. **Feature Description**
3. **Implementation Code Files** (explicit paths)
4. **Test Files & Verification** (explicit test paths)
5. **Documentation Link** (path in `docs/`)
6. **Delivery Status** (`Planned` | `In-Progress` | `Verified` | `Done`)

### 3.2 Standard `Planning.md` Traceability Matrix Template

```markdown
# Project Plan: [Project Name]

> **Status**: In Progress | **Last Updated**: YYYY-MM-DD

## 1. Requirements & Traceability Matrix

| Req ID | Feature / Objective | Implementation Files | Test Files | Documentation | Status |
|---|---|---|---|---|---|
| `REQ-01` | User Authentication & JWT | `app/Services/AuthService.php`<br>`app/Http/Controllers/AuthController.php` | `tests/Feature/AuthTest.php` | `docs/documentation.md#auth` | `Done` |
| `REQ-02` | Stripe Payment Integration | `app/Services/PaymentService.php`<br>`app/Http/Controllers/PaymentController.php` | `tests/Unit/PaymentTest.php`<br>`tests/Feature/PaymentFlowTest.php` | `docs/modules/payment/documentation.md` | `In-Progress` |
| `REQ-03` | Automated Invoice Generation | `app/Jobs/GenerateInvoiceJob.php` | `tests/Unit/InvoiceJobTest.php` | `docs/documentation.md#invoices` | `Planned` |

---

## 2. Phase Breakdown

### Phase 1: Authentication & User Setup (`REQ-01`)
- [x] Create database migration for users and tokens (`database/migrations/0001_users.sql`)
- [x] Implement `AuthService.php` with password hashing
- [x] Write unit & integration tests (`tests/Feature/AuthTest.php` — 12 passing tests)
- [x] Document endpoints in `docs/documentation.md#auth`
- [x] Verified with `coresentinel verify` (Score: 100/100)

### Phase 2: Payment Integration (`REQ-02`)
- [ ] Create Stripe payment intent handler
- [ ] Add webhook signature verification
- [ ] Write integration test with mock gateway
- [ ] Document in `docs/modules/payment/documentation.md`
```

---

## 4. Traceability & Integrity Rules

1. **No Orphan Code**: No agent or developer may write or merge code that does not map to a `REQ-xx` item in `Planning.md`.
2. **No Phantom Completion**: No item in `Planning.md` may be marked `[x]` or `Done` without:
   - Real implementation file paths listed.
   - Real test file paths listed with passing verification evidence.
   - Real documentation anchor listed in `docs/`.
3. **No Unrecorded Modules**: Every newly created file in `src/`, `app/`, or `lib/` must be registered in `docs/documentation.md` before the task is closed.

---

## 5. Squad Orchestration & Quality Gate Enforcement

| Agent | Responsibility Under Protocol 53 | Gate Check |
|---|---|---|
| **Architect** | Designs `Planning.md` and seeds requirement IDs (`REQ-01`, `REQ-02`) + initial Traceability Matrix. | `Requirement` & `Architecture` Gates |
| **Builder** | Implements code strictly mapped to `REQ-xx` IDs. Links files in `Planning.md`. | `Implementation` Gate |
| **Tester** | Writes automated tests mapped to `REQ-xx` IDs. Verifies coverage. | `Test` Gate |
| **Doc-Writer** | Author and maintain `docs/documentation.md` and module changelogs. Keeps `Planning.md` matrix updated. | `Documentation` Gate |
| **Reviewer** | Audits working diff against `docs/documentation.md` and `Planning.md`. Rejects PR if docs or matrix are missing. | `Review` & `Verification` Gates |

---

## 6. Verification Commands

```bash
# Verify project passes evidence-based verification
coresentinel verify

# Check quality gates including Documentation and Review
coresentinel gate run --objective "REQ-02: Payment Integration" --report

# Run static review pass over working diff
coresentinel review
```
