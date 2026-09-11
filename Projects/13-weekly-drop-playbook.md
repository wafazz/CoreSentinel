# Weekly Drop Playbook — 30 weeks of internal R&D drops, each demoed live against a sandbox broken on purpose

> **Status**: Active — Week Zero (sandbox built, habits not yet started)
> **Last Updated**: 2026-09-10

## Business Context
- **Client**: internal — Daythree, R&D Division
- **Status**: active
- **Priority**: high — the drop programme carries **35% of overall KPI**
- **Revenue Model**: none; this is a performance/KPI instrument, not a product
- **Deployed**: No, and never — The Lab is `127.0.0.1` only, by design

## Overview
- **Root**: `Desktop/Weekly Drop Playbook`
- **Stack**: The sandbox (`the-lab/`) is Laravel 12 + PHP ^8.2 + Vue 3.5.42 + Vite 6 + Tailwind 4 + MariaDB 10.4 (XAMPP). The programme itself is Markdown + one HTML spec.
- **Type**: internal enablement programme — 30 presentations, not an application
- **Auth**: `AuthDemoController` is a deliberately unthrottled sign-in *stand-in*, not real auth
- **Currency**: n/a
- **Payment**: n/a
- **Database**: `the_lab` on MariaDB 10.4.32, root/no password, seeded with generated fake records only

### Shape of the thing
One drop per week for thirty weeks: **30 minutes including a live demo**, and it may not be
work a manager already assigned. Five lanes (L1 Vibe coding & AI, L2 Development craft,
L3 New tools, L4 Production enhancement, L5 New process) rotate through six cycles of five
weeks, each cycle hitting every lane exactly once in the order L1→L5. No lane is presented
twice in a row.

The playbook's own diagnosis: *"That is not a slide problem — it's a supply problem."*
Everything in this repo exists to be the supply.

### The Lab
A Laravel + Vue app that is **broken on purpose** — 17 planted flaws, each claimed by a
specific week in `the-lab/LAB.md`. Sandbox only, generated records, no client data, ever.
`php artisan lab:doctor` reports row counts, missing indexes and slow-query timings; run it
before the fix and after the fix, and **the difference between those two runs is the drop**.

## Key Patterns
- **Broken-on-purpose sandbox as demo supply.** The scarce resource in a talk programme is
  not ideas, it is a safe, realistic, always-available thing to fix on stage. Building the
  patient once in week zero makes 30 demos cheap (3–7h each instead of 3–7 days).
- **The measuring tape ships with the patient.** `lab:doctor` exists so every drop has a
  number before and a number after, live, never a screenshot. A topic that cannot be
  measured is rejected before it is prepped.
- **Lane rotation as an anti-repetition guarantee.** A deterministic
  `L((n-1) mod 5 + 1)` schedule means variety is structural, not a matter of remembering
  what you talked about last month. Bench spares carry a lane so a swap cannot break it.
- **Branch per drop.** `week-NN-<slug>` off `master` keeps every past fix runnable and
  demonstrable months later; `master` stays fully broken.
- **Build the patient, not the cure.** The setup script deliberately omits Larastan, Pest,
  Playwright, Horizon and GitHub Actions — installing each of those *is* a drop. Pint is the
  exception: it ships in `laravel/laravel`, so W03 configures it rather than installing it.
- **Two weeks of finished work in the bank.** You present what is already rehearsed. Prep
  estimates assume this cadence; they are wrong if you fall to zero buffer.

## Completed
1. **Week Zero — the sandbox.** Laravel 12 + Vue 3.5.42, 7 migrations (4 lab tables with no
   indexes, on purpose), 5 models, 6 controllers, `FlakyReportJob`, unbound `VisitCounter`,
   2 Vue trap components. Committed broken at `878e70f` on `master`.
2. **Reproducibility.** `the-lab-setup/setup-the-lab.ps1` + 26 stubs rebuild the whole
   sandbox in 6–10 min; picks Laravel 12 or 13 by PHP version; hard-stops if `mysqld` is down.
3. **Measurement.** `app/Console/Commands/LabDoctor.php`.
4. **Flaw index.** All 17 flaws mapped to their fixing week in `the-lab/LAB.md`.
5. **CoreSentinel registration (2026-09-10).** `Planning.md` (`REQ-01`–`REQ-13` + W01–W30
   delivery matrix), `docs/documentation.md`, `session-memory.md`.

## Remaining
- Pain log (`REQ-04`) — not opened. Topics are supposed to come from it.
- W01 and W02 built and rehearsed (`REQ-05`) — Week Zero is not actually finished without these.
- `artefacts/` directory and the per-drop leave-behinds (`REQ-09`).
- Recording destination unresolved (`REQ-10`, `OQ-03`).
- All 30 drops sit at `Planned`. Nothing presented.
- `the-lab` has no git remote — branch-per-drop survives on one machine only (`OQ-04`).
- **`OQ-05`, blocking W01:** the `878e70f` baseline commit is incomplete. Three files are
  modified-uncommitted and one is untracked, so the documented reset `git checkout .`
  reverts a real fix and leaves `/` hitting a database the test schema lacks. Needs
  committing onto `master` before any `week-NN-*` branch is cut.

## Anti-Patterns (This Project)
- **Never fix a Lab flaw outside its assigned week.** This is the one mistake that quietly
  destroys the programme: a flaw fixed in week 1 is a drop that cannot be given in week 17.
  Check `the-lab/LAB.md` before touching anything in `the-lab/app/`.
- **Never copy code out of The Lab into a real project.** `LegacyReportController` and
  `ReactivityTraps.vue` are wrong deliberately. It is not a starter kit.
- **Never put The Lab in `C:\xampp\htdocs`.** Apache would serve a deliberately insecure,
  unthrottled, `APP_DEBUG=true` app to the whole network. `php artisan serve` binds
  `127.0.0.1` and that is the point.
- **Never put client data in the seeders.** Fixed name pools only.
- **Do not "tidy" `APP_DEBUG=true` or the missing indexes.** They are content, not debt.
- **Do not swap a topic across lanes.** Swapping inside a cycle is allowed and expected;
  changing the lane order breaks the no-repeat guarantee.
- **Do not present an unmeasured topic.** No number before and after → pick a different topic.
- **Do not write CS artefacts into `the-lab/`.** Its reset path is `git checkout .` +
  `migrate:fresh`, which would eat them.

## Work Log

### 2026-09-10 — CoreSentinel init (register, not scaffold)
- Ran `Iris CS init` on a directory that already contained the built programme. Confirmed
  with Fakrul that init should register existing work; **no code was generated and no
  existing file was modified**.
- Extracted the 30-week structure from the 44KB `Weekly Drop Playbook.html` via a subagent
  (token discipline — the dump never entered the main context).
- Verified The Lab against its documented claims rather than trusting `LAB.md`: composer
  and package versions, git state, `.env` keys, migration list, app tree, test files.
- Found one drift: the playbook HTML describes The Lab as *Laravel 11, 100k rows*; the app
  actually built is **Laravel 12, 250k orders / 20k customers**. Logged as `OQ-01`.
- Created `Planning.md`, `docs/documentation.md`, `session-memory.md` at the playbook root;
  registered stats labels in `~/.claude/project-labels.json`.
