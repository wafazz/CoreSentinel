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

## ⚡ CLI Commands

```bash
# List all 17 specialist agent contracts
coresentinel squad list

# View contract specification for a specific specialist
coresentinel squad show Architect
coresentinel squad show Security
coresentinel squad show Tester
```
