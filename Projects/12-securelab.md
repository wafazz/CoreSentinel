# SecureLab — Intentionally vulnerable internal web-app pentest lab

> **Status**: Delivered (v1) — 2026-09-10
> **Last Updated**: 2026-09-10

## Business Context
- **Client**: internal (Daythree) — technical learning + KPI demonstration
- **Status**: delivered
- **Priority**: medium
- **Revenue Model**: none (internal training asset)
- **Deployed**: No — local only by design (`127.0.0.1`), must never be deployed

## Overview
- **Root**: `Desktop/Internal Pentest/SecureLab`
- **Stack**: Laravel 12.69.2, PHP 8.3.30 (Laragon), SQLite, Blade, Bootstrap 5.3.3 (vendored, no Node)
- **Type**: security training lab ("SecureLab" internal company portal)
- **Auth**: session-based, roles admin/staff
- **Talk**: "Secure by Testing: A Practical Internal Web Application Pentest"

## Key Patterns
- **Runtime BEFORE/AFTER security toggle** — `SECURELAB_VULN` env → `config/securelab.php`
  → `App\Security\Toggle::vulnerable()`, read live per request. `php artisan serve`
  re-bootstraps each request, so flipping `.env` + refresh switches vuln↔fixed with **no
  restart**. See [[11-pattern-library.md]] new entry.
- **Vulnerability isolation** — each finding has a Vulnerable* and Secure* class/branch side
  by side; the fix is a readable diff, the rest of the app is not vulnerable.
- **Dual-mode feature tests** — every exploit asserted to succeed in vuln mode and fail in
  secure mode via `config(['securelab.vulnerable'=>...])`. This IS the automated retest.
- Laragon PHP 8.3 (XAMPP's 8.2.12 too old for Laravel 12) — same call as RezekiHUB.

## Completed
1. Scaffold, 4 migrations (users+role/salary, feedback, uploads, activities), seeder (4 demo accounts)
2. Auth, dashboard, admin user management, profile/IDOR, search/SQLi, feedback/XSS, upload
3. Four findings + fixes behind the toggle; 27 tests (72 assertions) green
4. Live exploit + retest captured (IDOR leak→403, SQLi 4 rows→0, UNION schema→none)
5. Docs: Planning.md, README, docs/{pentest-methodology,findings,remediation,retest,presentation-demo,documentation}.md
6. Presentation deck published as Artifact

## Findings (all closed)
| # | Finding | Severity | Endpoint |
|---|---|---|---|
| F1 | IDOR / Broken Access Control | High | GET /users/{id} |
| F2 | SQL Injection | Critical | GET /search?q= |
| F3 | Stored XSS | High | /feedback |
| F4 | Insecure File Upload | Medium | POST /upload |

## Anti-Patterns (This Project)
- Never let the upload finding gain a code-execution sink — it stays "unsafe handling only"
  (private non-web disk, no execution) so the lab can never compromise the host.
- `.env` ships `SECURELAB_VULN=true` (demo box); `.env.example` ships `false` (safe clone).

## Related
- [[11-weekly-drop-playbook]] — the other internal "broken-on-purpose Laravel sandbox" R&D
  programme; same broad idea (planted flaws for demos), different cadence.

## Work Log
### 2026-09-10 — Build (T2, full squad in-context)
- Full CS init + T2 build in one session. 27 tests green; live before/after verified over HTTP.
- Deck: Artifact https://claude.ai/code/artifact/695bf246-8fb8-4190-913d-46315c08ccf4
