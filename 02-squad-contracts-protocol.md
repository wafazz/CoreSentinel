# 🛡️ 17-Specialist Squad Agent Contracts & Orchestration Protocol

> **Explicit Agent Contracts, Input/Output Artifact Schemas, Authority Levels & Guardrails**  
> CoreSentinel transforms the specialist squad into a formal agent orchestration system with explicit input/output contracts.

---

## 📐 Agent Contract Specification Schema

Every specialist in the CoreSentinel squad operates under an explicit contract:

```
  ┌─────────────────────────────────────────────────────────────┐
  │ SPECIALIST AGENT CONTRACT                                  │
  ├─────────────────────────────────────────────────────────────┤
  │ 1. Role & Capability      : Specialist scope & domain      │
  │ 2. Input Contract         : Required upstream artifacts    │
  │ 3. Output Contract        : Generated downstream artifacts │
  │ 4. Authority Level        : Read/Write/Execute boundaries  │
  │ 5. Constraints            : Hard guardrails & rules        │
  │ 6. Verification Gate      : Mandatory evidence checklist   │
  └─────────────────────────────────────────────────────────────┘
```

---

## 👥 Core Squad Contracts Overview

### 1. Architect Agent
* **Role**: System Architecture & Design Specialist
* **Input Contract**: `user_requirements.md`, `scout_research_notes.md`
* **Output Contract**: `architecture_proposal.md`, `component_schema.json`
* **Authority**: System design & schema definition
* **Constraints**: No unverified external dependencies
* **Verification Gate**: Mermaid architecture diagram & interface schema

### 2. Security Agent
* **Role**: OWASP AppSec & Vulnerability Auditor
* **Input Contract**: `implementation_code`, `git_diff`
* **Output Contract**: `security_findings.json`, `vulnerability_report.md`
* **Authority**: Security audit & commit block authority
* **Constraints**: Block any hardcoded keys or unscoped SQL queries
* **Verification Gate**: `sentinel-validator` zero security violations

### 3. Tester Agent
* **Role**: QA & Unit Test Specialist
* **Input Contract**: `implementation_code`, `feature_spec.md`
* **Output Contract**: `test_suite_code`, `test_execution_report.json`
* **Authority**: Test file creation & runner execution
* **Constraints**: No commented assertions or arbitrary delays
* **Verification Gate**: 100% test pass rate on newly written tests

### 4. Reviewer Agent (Cato & Sage)
* **Role**: Code Quality & Logic Reviewer
* **Input Contract**: `implementation_code`, `test_execution_report.json`, `security_findings.json`
* **Output Contract**: `review_approval_report.md`
* **Authority**: Phase gate pass/reject authorization
* **Constraints**: Reject superficial symptom patches or silent exception swallows
* **Verification Gate**: Review checklist fully verified with empirical evidence

---

## 🔐 Enforced Permissions

The first six fields describe an agent. The seventh **constrains** it.

Until v10.6 `authority` was prose and nothing read it at runtime — the claim that a
read-only researcher could not write files was a statement about a JSON document. Each
contract now carries a `permissions` block, and an agent is handed a **sandbox** rather than
the filesystem or a shell.

| Level | Meaning |
| :--- | :--- |
| **`ALLOW`** | Granted outright |
| **`LIMITED`** | Granted only inside a declared scope — a path prefix or a program name |
| **`ASK`** | Requires approval; denied outright when the run is not interactive |
| **`DENY`** | Not granted |

The eight permissions: `filesystem.read`, `filesystem.write`, `shell.execute`,
`network.access`, `git.commit`, `git.push`, `deployment`, `production.access`.

**Default for every agent: `filesystem.read` and nothing else.** An agent whose contract
declares no permissions stays read-only — the fallback is deliberately useless rather than
permissive.

```json
"permissions": {
  "levels": { "filesystem.read": "ALLOW", "filesystem.write": "LIMITED",
              "shell.execute": "LIMITED" },
  "scopes": { "filesystem.write": ["tests/", "spec/"],
              "shell.execute": ["pytest", "npm", "phpunit"] }
}
```

Rules that hold regardless of what a contract asks for:

1. **`LIMITED` with no scope grants nothing.** Otherwise the safest-looking level silently
   becomes the widest.
2. **Every path is contained** inside the project root, so `filesystem.write` never means
   "anywhere on disk".
3. **`git.push`, `deployment` and `production.access` cannot be granted without a stated
   reason.** The blast radius is the production system.
4. **Every denial is recorded** on the result and in the audit trail. A refusal nobody can
   see is indistinguishable from an agent that never tried.

---

## 🏃 Execution

Roles CoreSentinel can perform itself run for real and return evidence carrying a command
and an exit code: **Scout** (retrieval), **Security** (scanner), **Tester** (suite),
**Reviewer** (diff), **Evolver** (learning candidate).

Every other role reports **`UNSUPPORTED`** until an agent adapter is bound. That is the same
rule as `UNKNOWN` in verification: a capability that is not there says so rather than
returning a confident nothing.

A result is validated before it is recorded. A `COMPLETED` result carrying neither evidence
nor actions is rejected — that is the claim this system exists to refuse.

---

## ⚡ CLI Commands

```bash
# List all 17 specialist agent contracts
coresentinel agent list

# View contract specification for a specific specialist
coresentinel agent show Architect

# See what an agent may actually do, and under what limits
coresentinel agent permissions Scout
coresentinel agent permissions            # every contract, plus escalation holders

# Run one role, or the whole pipeline
coresentinel agent run Security --objective "Scan the change set"
coresentinel task plan --objective "Add Redis caching to product listing"
coresentinel task run  --objective "Add Redis caching to product listing"
coresentinel task run  --roles Scout,Security,Reviewer
```
