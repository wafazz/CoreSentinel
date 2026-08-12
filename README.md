# 🛡️ CoreSentinel

> **Universal AI Agent Protocol, Memory & Autonomous Squad System**  
> *Transform any AI coding assistant into a disciplined, self-evolving software engineering organization.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https.LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Claude_Code_|_Antigravity_|_Gemini_|_Codex_|_Cursor-blue)](#-supported-ai-tools)

**CoreSentinel** is an open-source, file-based memory and governance framework for AI coding assistants. It equips agents with structured software development lifecycles (SDLC), mandatory 17-specialist squad reviews, strict security hardening, zero-hallucination verification gates, continuous self-evolution, and cross-project token telemetry.

---

## 🚀 Key Features

- **🏛️ 17-Specialist Autonomous Squad**: Iris leads specialized personas across Architecture, Security, AppSec, Infra Hardening, Database, Testing, Code Review, UX/A11y, and Cost.
- **🔄 Sequenced SDLC Phase Gates**: 9 ordered phases (Phase 0 Intake → Phase 8 Ship & Persist) with zero skipped gates.
- **🛡️ QA Sentinel Mode (`Iris test`)**: Dedicated test-driven automation mode designed to detect flakes, enforce test independence, and prevent false-pass assertions.
- **🧠 Continuous Self-Evolution Engine**: Auto-records skills and anti-patterns after every task so past mistakes are never repeated.
- **📊 Cross-Tool Telemetry & Analytics**: Scans logs from Claude Code, OpenAI Codex, Antigravity, Gemini CLI, Cursor, and Windsurf to report real-time token spend per project.
- **🔌 Universal Compatibility**: Works seamlessly with any AI CLI or IDE assistant without requiring binary plugins or language lock-in.

---

## 🗺️ Process Roadmap & Protocols

CoreSentinel arranges all protocols chronologically from initial project intake down to post-deployment evolution and incident response:

| Stage / Phase | Protocol File | Purpose / Trigger |
|---|---|---|
| **00 — Identity** | [`00-identity.md`](./00-identity.md) | Central Memory Core & Agent Identity Index |
| | [`01-sentinel-identity.md`](./01-sentinel-identity.md) | QA Automation Mode (`Iris test`) |
| | [`02-team-protocol.md`](./02-team-protocol.md) | 17-Specialist Squad Orchestration & Phase Gates 0–8 |
| | [`03-workflow-guide.md`](./03-workflow-guide.md) | Workflow Guide & Session Token Budgeting |
| | [`04-session-memory-format.md`](./04-session-memory-format.md) | Session Memory Template & Auto-Reset Rules |
| **Phase 0 — Intake** | [`05-init-protocol.md`](./05-init-protocol.md) | Project Scaffolding & Context Gathering (`Iris init`) |
| | [`06-mimic-protocol.md`](./06-mimic-protocol.md) | Stack Migration Protocol (`mimic this`) |
| | [`07-git-workflow.md`](./07-git-workflow.md) | Git Branching, Commit Standards & PR Conventions |
| **Phase 1 — Research** | [`10-learn-protocol.md`](./10-learn-protocol.md) | Auto-Learn New Tech Stacks (`Iris learn`) |
| | [`11-pattern-library.md`](./11-pattern-library.md) | Reusable Architecture & Component Patterns |
| **Phase 2 & 3 — Build** | [`15-migration-protocol.md`](./15-migration-protocol.md) | Idempotent Schema & SQL Migrations (`Iris migrate`) |
| | [`16-api-protocol.md`](./16-api-protocol.md) | Webhooks, Idempotency & Signature Guard (`Iris api`) |
| | [`17-ai-protocol.md`](./17-ai-protocol.md) | AI Multi-Provider Failover & Prompt Defense (`Iris ai`) |
| **Phase 4 — Testing** | [`25-test-protocol.md`](./25-test-protocol.md) | Test Strategy & Speed Budgeting |
| | [`26-test-data-protocol.md`](./26-test-data-protocol.md) | Test Data, Factories & Isolation Rules |
| | [`27-test-pattern-library.md`](./27-test-pattern-library.md) | Proven Test Automation Patterns |
| | [`28-flaky-protocol.md`](./28-flaky-protocol.md) | Flaky Test Root Cause & Isolation |
| | [`29-test-review-protocol.md`](./29-test-review-protocol.md) | Test Suite Quality & Review Checklist |
| **Phase 5 — Review** | [`35-review-protocol.md`](./35-review-protocol.md) | Code Review Checklist (Cato + Sage) |
| **Phase 6 — Security** | [`40-security-protocol.md`](./40-security-protocol.md) | Secret Protection, AppSec & Hardening |
| **Phase 7 — Cost & Perf**| [`45-performance-protocol.md`](./45-performance-protocol.md) | Query Profiling & N+1 Optimization (`Iris perf`) |
| **Phase 8 — Ship** | [`50-ci-cd-protocol.md`](./50-ci-cd-protocol.md) | CI/CD Pipeline Protocol (`Iris ci`) |
| | [`51-deployment-protocol.md`](./51-deployment-protocol.md) | Deployment Recipes & Troubleshooting |
| | [`52-handoff-protocol.md`](./52-handoff-protocol.md) | Client Delivery & Handoff (`Iris handoff`) |
| **Post-Ship & Ops** | [`55-self-evolution.md`](./55-self-evolution.md) | Self-Evolution, Skills & Anti-Patterns Log |
| | [`60-debug-protocol.md`](./60-debug-protocol.md) | Structured Debugging (`Iris debug`) |
| | [`61-incident-protocol.md`](./61-incident-protocol.md) | Emergency Containment & Post-Mortem (`Iris incident`) |

---

## ⚡ Quick Start

### 1. Clone CoreSentinel
```bash
git clone https://github.com/your-username/CoreSentinel.git
cd CoreSentinel
```

### 2. Run Auto-Installer / Tool Binder

#### On Windows (PowerShell):
```powershell
.\setup.ps1
```

#### On Linux / macOS (POSIX Shell):
```bash
chmod +x setup.sh
./setup.sh
```

The installer updates `memorycore.conf` and binds CoreSentinel system instructions directly into your global AI tool configuration directories (`~/.claude`, `~/.antigravity`, `~/.gemini`, `~/.codex`, `~/.cursor`).

---

## 🤖 Supported AI Tools

CoreSentinel binds to all major agentic AI coding platforms out of the box:
- **Claude Code** (`~/.claude/CLAUDE.md`)
- **Google Antigravity** (`~/.antigravity/AGENTS.md`)
- **Gemini CLI** (`~/.gemini/GEMINI.md`)
- **OpenAI Codex** (`~/.codex/AGENTS.md`)
- **Cursor IDE** (`~/.cursor/rules/coresentinel.mdc`)
- **Windsurf, Copilot, Cline, Aider** (via `AGENTS.md` standard)

---

## 👥 The 17-Specialist Squad

Iris leads 17 specialized roles who participate across the project lifecycle:

| Category | Specialists | Key Responsibilities |
|---|---|---|
| **Lead** | **Iris** | Squad orchestration, phase gate enforcement, self-evolution recording |
| **Fullstack** | **Atlas**, **Kai**, **Nova**, **Rex** | Architecture, integrations, core features, refactoring & maintenance |
| **Frontend** | **Luna**, **Vera** | TS/React implementation, UI polish, keyboard/screen-reader accessibility |
| **Code Review** | **Cato**, **Sage** | Logic correctness, edge cases, structural maintainability |
| **Security** | **Argus**, **Cipher**, **Aegis** | Supply chain, OWASP AppSec, infrastructure hardening & CORS/headers |
| **Database** | **Delta**, **Indra** | Normalization & migrations, index profiling & N+1 query optimization |
| **Testing** | **Echo**, **Probe** | Unit/feature suites, end-to-end integration & contract testing |
| **Support** | **Scout**, **Ledger** | Documentation research (read-only), token & cloud infra cost metering |

---

## 📊 Token Usage Telemetry

Track token spend and usage statistics across all installed AI tools:

```bash
python agent-stats.py
```

Outputs formatted tables detailing:
- Input / Output token counts per project
- Tool breakdown (Claude, Antigravity, Gemini, Codex)
- Total session counts & estimated expenditure

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.
