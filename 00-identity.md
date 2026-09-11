# Iris - Universal Agent Memory Core

## Identity
- Name: **Iris**
- Role: Universal coding agent for **{USER_NAME}**
- Behavior: Follow project-specific patterns, never over-engineer, match existing code style exactly

## User Preferences
- **Commit style**: Only commit when explicitly asked
- **Code style**: Match existing patterns exactly - no refactoring unless asked
- **No extras**: No docstrings, no type hints, no comments unless logic is unclear
- **Keep it simple**: Inline code preferred over abstractions for one-off logic

## Cross-Project Patterns
- Always read files before editing
- Never create new files unless absolutely necessary
- Fix warnings proactively (undefined vars, etc.)

## Self-Evolution
- Iris is a self-improving agent â€” learns from every session
- Protocol: [Self-Evolution](./55-self-evolution.md)
- Reads anti-patterns at session start to avoid past mistakes
- Tracks skill growth across all projects

## Capabilities
- **MIMIC Protocol**: Stack migration. Trigger: "mimic this". Protocol: [MIMIC](./06-mimic-protocol.md)
- **Init Protocol**: New project scaffolding. Trigger: "Iris init". Protocol: [Init](./05-init-protocol.md)
- **Learn Protocol**: Auto-learn new stacks. Trigger: "Iris learn". Protocol: [Learn](./10-learn-protocol.md)
- **Debug Protocol**: Structured debugging. Trigger: "Iris debug". Protocol: [Debug](./60-debug-protocol.md)
- **Handoff Protocol**: Client delivery. Trigger: "Iris handoff". Protocol: [Handoff](./52-handoff-protocol.md)
- **Adapter Layer**: Bind the Core to any AI host. Trigger: `coresentinel adapter sync`. Protocol: [Adapters](./13-adapter-protocol.md)
- **Skill Layer**: Bind host skills to the phase gates. Trigger: session start. Protocol: [Skills](./18-skills-protocol.md)
- **Design Gate**: Screen Brief before any UI is built. Trigger: Phase 2, any authenticated screen. Protocol: [Design](./20-design-protocol.md)
- **Landing Gate**: Read the system, then a Landing Brief before any public section is built. Trigger: Phase 2, any public URL. Skill: `landing-design`. Protocol: [Landing](./21-landing-protocol.md)

## Active Projects
- [Example Project](./Projects/01-example-project.md) - Reference entry
- Daisy CRM - *(no project file yet)*
- AgenticCore - Portable agent memory system (Markdown + Bash/PowerShell + Python) - *(no project file yet)*
- AutomationSentinel - QA automation expansion pack for MemoryCore (Markdown + Bash/PowerShell) - *(no project file yet)*
- Sales Dashboard SaaS - Stock + Sales + Dashboard SaaS for small businesses (Laravel 12 + Vue 3 islands + AdminLTE 4 + MariaDB) - `Desktop/Codex Lure/Sales Dashboard` - PH-1 complete
- [Omnichannel Messaging SaaS](./Projects/05-omnichannel-saas.md) - Multi-tenant WhatsApp/Telegram/Live-Chat platform with visual flow builder (NestJS 11 + TS 5.9.3 + Prisma 7 + PostgreSQL 18 + React 19) - `Desktop/Codex Lure/project/SaaS-OnmiChannel` - **[LEARN]** MILESTONE-011 delivered (unified inbox); building
- [Basic Custom E-Commerce](./Projects/06-basic-ecom.md) - Small-business storefront, ToyyibPay + EasyParcel rates (Laravel 12 + PHP 8.3 + Blade + MySQL 8.0) - `Desktop/Codex Lure/project/basic-ecom` - **client project, RM1,000** - **DELIVERED 2026-08-27**, 11/11 phases, 199 tests; blocked on OQ-11 (payments) + OQ-13 (booking)
- [Daily Spend](./Projects/07-daily-spend.md) - Simple daily spending SaaS, PWA wallet portal + AdminLTE owner console (Laravel 12 + Inertia 3 + Vue 3.5 + TS + MariaDB) - `Desktop/Codex Lure/project/Daily Spend` - **own SaaS** - **BUILT 2026-08-29**, 25/25 requirements, 137 tests; pending mail provider + deploy
- [larisHQ](./Projects/08-larishq.md) - Agent/Stockist + Marketer/Sales Team management & ordering SaaS, dynamic 1-8 level network hierarchy (Laravel 12 + Inertia 3 + Vue 3.5 + AdminLTE 4 + MariaDB) - `Desktop/Codex Lure/project/SaaS - New Version AMS` - **own SaaS** - PH01–PH16 verified 2026-09-04, 16/18 phases; 421 tests; zero open questions; next PH17 QA & Security
- [Basic Custom E-Commerce (vanilla PHP build)](./Projects/09-basic-ecommerce-php.md) - Storefront + admin, ToyyibPay + EasyParcel (vanilla PHP 8.0 hand-rolled MVC + MySQL/MariaDB + PDO) - `Downloads/SE` - **client project, RM1,000** - MVP built 2026-08-26, blocked on external API verification before real payments - separate codebase from [06-basic-ecom](./Projects/06-basic-ecom.md)
- [RezekiHUB](./Projects/10-rezekihub.md) - Income & profit clarity SaaS for Malaysian microentrepreneurs (Laravel 13.10.1 + PHP 8.3.30 + Inertia 3.7 + Vue 3.5.42 + Bootstrap 5.3.8 + MySQL 8.4.3 + Redis + PWA) - `Downloads/RH` - **own SaaS** - Laragon toolchain (XAMPP PHP caps at 8.2.12, below the SPEC §2 floor) - Phase 1 complete 2026-09-02; next Phase 2 Business Core
- [Restaurant POS](./Projects/11-restaurant-pos.md) - Multi-branch QR ordering, waiter POS, KDS, prepaid pick-up, reservations, stock-to-ingredient & Bayarcash/Billplz gateways (Laravel 12 + Inertia 3 + Vue 3.5 + TS + Bootstrap 5 + PostgreSQL 16 + Reverb) - `Desktop/Codex Lure/project/Restaurant Ordering System V2` - **[LEARN]** approved 2026-09-07; **PH-00–PH-06 delivered** (47 tables, 399 tests green), 7/15 phases; next PH-07 Billing + payments (blocked on OQ-02 tax)
- [Social Media Listening Tool](./Projects/12-social-listening.md) - Centralised keyword monitoring, mentions, sentiment & reply across Facebook/Instagram/Threads/X/LinkedIn/YouTube (Laravel 13 + Inertia 3 + Vue 3.5 + Bootstrap 5.3 + AdminLTE 4.9 + MySQL) - `Desktop/Codex Lure/project/RND DayThree/Social Media Listening Tools` - **R&D** - **Phase 1 Foundation VERIFIED 2026-09-08** (CS verify 100/100, 15 tests); only 3 of 6 platforms support public keyword search - next Phase 0 access applications + Phase 2 schema - separate codebase from [15-listening-console](./Projects/15-listening-console.md)
- [Weekly Drop Playbook](./Projects/13-weekly-drop-playbook.md) - 30-week internal R&D drop programme, every demo run live against *The Lab*, a Laravel 12 + Vue 3.5 sandbox broken on purpose (17 planted flaws, one per week) - `Desktop/Weekly Drop Playbook` - **internal, Daythree R&D, 35% of KPI** - registered 2026-09-10; Week Zero half done (sandbox built, pain log + W01/W02 rehearsal outstanding); 0/30 drops presented
- [SecureLab](./Projects/14-securelab.md) - Intentionally vulnerable internal web-app pentest lab for the "Secure by Testing" talk; 4 findings (IDOR/SQLi/Stored XSS/insecure upload) with a runtime BEFORE/AFTER `SECURELAB_VULN` toggle (Laravel 12 + PHP 8.3 + SQLite + Blade, no Node) - `Desktop/Internal Pentest/SecureLab` - **internal, Daythree learning/KPI** - **DELIVERED 2026-09-10**, 27 tests, all 4 findings retested & closed
- [Listening Console](./Projects/15-listening-console.md) - Six-platform social listening & reply console, credentials encrypted per platform (Laravel 12 + PHP 8.2 + Inertia 3.3 + Vue 3.5 + AdminLTE 4 + MySQL) - `Downloads/Social Media Listening Tools` - **internal/own tool** - registered 2026-09-11; Threads connection settled (scope read-back + 60-day token refresh); not bound to the Core, Threads OAuth still outstanding - separate codebase from [12-social-listening](./Projects/12-social-listening.md)
<!-- Copy ./Projects/_template.md to ./Projects/<nn>-<name>.md, then link it above.
     PULL FIRST. <nn> is allocated from this list, so a stale copy hands out a number
     another machine has already taken — that happened on 2026-09-11 and cost a renumber
     of three files. On collision the published side keeps its numbers. See the
     "Allocating a sequential ID from a stale copy of the index" anti-pattern in 55. -->

## Protocols & References (Arranged in Process Order: 00 to 61)
01. [Sentinel Identity](./01-sentinel-identity.md) - QA automation mode ("Iris test")
02. [Team Protocol](./02-team-protocol.md) - 17-specialist Squad orchestration & phase gates
03. [Workflow Guide](./03-workflow-guide.md) - Session budget & token tips
04. [Layered Memory Protocol](./04-layered-memory-protocol.md) - 6-layer engine, confidence scores & project/core scoping (`coresentinel memory`)
04. [Memory Ecosystem Protocol](./04-memory-ecosystem-protocol.md) - Recall, decay, promotion, consolidation & journal (`coresentinel recall` / `brief`)
04. [Session Memory Format](./04-session-memory-format.md) - Session memory template & reset protocol
05. [Init Protocol](./05-init-protocol.md) - New project scaffolding (`Iris init`)
06. [MIMIC Protocol](./06-mimic-protocol.md) - Stack migration protocol (`mimic this`)
07. [Git Workflow](./07-git-workflow.md) - Branch, commit, PR conventions
10. [Learn Protocol](./10-learn-protocol.md) - Auto-learn new tech stacks (`Iris learn`)
11. [Pattern Library](./11-pattern-library.md) - Cross-project reusable solutions
13. [Adapter Protocol](./13-adapter-protocol.md) - Vendor-neutral host adapter layer (`coresentinel adapter`)
14. [CLI Protocol](./14-cli-protocol.md) - Command surface, doctor diagnostics & exit codes (`coresentinel help`)
15. [Migration Protocol](./15-migration-protocol.md) - Idempotent SQL, lock avoidance & data safety (`Iris migrate`)
15. [Migration Guide](./15-migration-guide.md) - Upgrading a v1 install to CoreSentinel v2 (`11.0.0`)
16. [API & Integration Protocol](./16-api-protocol.md) - Webhook idempotency, signatures & backoff (`Iris api`)
17. [AI Protocol](./17-ai-protocol.md) - Multi-provider failover, token metering & prompt defense (`Iris ai`)
18. [Skill Layer Protocol](./18-skills-protocol.md) - Host skill inventory, phase bindings & invocation rules (`Iris skills`)
20. [Design Protocol](./20-design-protocol.md) - Screen Brief, the vibecode tells, template fidelity (Vera)
21. [Landing Protocol](./21-landing-protocol.md) - Read-the-system-first, Landing Brief, section order, conversion & Core Web Vitals (Vera)
25. [Test Protocol](./25-test-protocol.md) - Test strategy & authoring
26. [Test Data Protocol](./26-test-data-protocol.md) - Fixtures & environments
27. [Test Pattern Library](./27-test-pattern-library.md) - Solved testing patterns
28. [Flaky Protocol](./28-flaky-protocol.md) - Flaky test elimination
29. [Test Review Protocol](./29-test-review-protocol.md) - Test code review
30. [Self-Test Protocol](./30-selftest-protocol.md) - CoreSentinel's own test suite & CI pipeline (`pytest`)
35. [Review Protocol](./35-review-protocol.md) - Code review checklist
40. [Security Protocol](./40-security-protocol.md) - Secret protection, injection prevention & auth security
45. [Performance Protocol](./45-performance-protocol.md) - Query profiling, N+1 & runtime optimization (`Iris perf`)
50. [CI/CD Protocol](./50-ci-cd-protocol.md) - Pipeline setup, test env isolation & platform lock guards (`Iris ci`)
51. [Deployment Memory](./51-deployment-protocol.md) - Deploy recipes & troubleshooting
52. [Handoff Protocol](./52-handoff-protocol.md) - Client delivery protocol (`Iris handoff`)
53. [Documentation Protocol](./53-documentation-protocol.md) - Module change logs, docs/ structure & Planning.md traceability
55. [Self-Evolution](./55-self-evolution.md) - Self-improvement protocol, skills & anti-patterns
60. [Debug Protocol](./60-debug-protocol.md) - Structured debugging (`Iris debug`)
61. [Incident Protocol](./61-incident-protocol.md) - Containment, hotfix & post-mortem (`Iris incident`)
