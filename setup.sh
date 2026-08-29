#!/usr/bin/env bash
# CoreSentinel Installer / Sync Script (POSIX Shell)
# Configures CoreSentinel as global memory & protocol core across all AI coding tools.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-$SCRIPT_DIR}"
HOME_DIR="$HOME"

echo "=========================================="
echo " CoreSentinel Installer & Tool Binding "
echo " Target Memory Path: $TARGET_DIR"
echo "=========================================="

if [ -z "$NON_INTERACTIVE" ]; then
    echo ""
    echo "--- CoreSentinel Interactive Setup ---"
    echo ""

    # 1. Agent Name
    read -p "1) Agent Name? [Default: Iris]: " AGENT_NAME_INPUT
    AGENT_NAME="${AGENT_NAME_INPUT:-Iris}"

    # 2. Agent Role
    read -p "2) Agent acts as what? [Default: Universal coding agent for Fakrul]: " AGENT_ROLE_INPUT
    AGENT_ROLE="${AGENT_ROLE_INPUT:-Universal coding agent for Fakrul}"

    # 3. Create sub-agents or not?
    read -p "3) Create sub-agents or not? (Y/N) [Default: Y]: " CREATE_SUBAGENTS_INPUT
    case "$CREATE_SUBAGENTS_INPUT" in
        [Nn]*) CREATE_SUBAGENTS="No" ;;
        *)     CREATE_SUBAGENTS="Yes" ;;
    esac

    # 4 & 5. Sub-agents details (if enabled)
    SUBAGENTS_MD=""
    if [ "$CREATE_SUBAGENTS" = "Yes" ]; then
        read -p "4) How many sub-agents? [Default: 17]: " SUBAGENT_COUNT_INPUT
        SUBAGENT_COUNT="${SUBAGENT_COUNT_INPUT:-17}"

        echo "5) Sub-agents auto-named or give name?"
        echo "   [1] Auto-named (Standard 17 Squad names)"
        echo "   [2] Give custom names manually"
        read -p "   Choice (1 or 2) [Default: 1]: " NAMING_CHOICE

        SUBAGENTS_MD="
### Active Sub-Agents ($SUBAGENT_COUNT)
"
        if [ "$NAMING_CHOICE" = "2" ]; then
            SUBAGENT_NAMING="Custom"
            for (( i=1; i<=SUBAGENT_COUNT; i++ )); do
                read -p "   -> Sub-agent #$i Name: " SA_NAME
                read -p "   -> Sub-agent #$i Role: " SA_ROLE
                NAME_VAL="${SA_NAME:-SubAgent-$i}"
                ROLE_VAL="${SA_ROLE:-Specialist Agent $i}"
                SUBAGENTS_MD="${SUBAGENTS_MD}- **${NAME_VAL}**: ${ROLE_VAL}
"
            done
        else
            SUBAGENT_NAMING="Auto"
            SUBAGENTS_MD="${SUBAGENTS_MD}- **Scout**: Codebase Researcher & Explorer
- **Architect**: System Architecture & Design Specialist
- **Builder**: Core Implementation Specialist
- **Tester**: QA & Unit Test Specialist
- **Security**: Security & Vulnerability Auditor
- **Reviewer**: Code Review & Quality Specialist
- **Optimizer**: Performance & Profiling Specialist
- **DevOps**: CI/CD & Deployment Specialist
- **Migrator**: Stack Migration Specialist (MIMIC)
- **Database**: Database & Migration Specialist
- **API**: API & Integration Specialist
- **AI-Spec**: AI Provider & Failover Specialist
- **Debugger**: Structured Debugging Specialist
- **Flaky-Fixer**: Flaky Test Elimination Specialist
- **Incident**: Emergency Incident Specialist
- **Doc-Writer**: Documentation & Handoff Specialist
- **Evolver**: Self-Evolution & Anti-Pattern Auditor
"
        fi
    else
        SUBAGENTS_MD="
### Sub-Agents: Disabled
"
    fi
else
    AGENT_NAME="Iris"
    AGENT_ROLE="Universal coding agent for Fakrul"
    CREATE_SUBAGENTS="Yes"
    SUBAGENT_COUNT="17"
    SUBAGENT_NAMING="Auto"
    SUBAGENTS_MD="
### Active Sub-Agents (17)
- **Scout**: Codebase Researcher & Explorer
- **Architect**: System Architecture & Design Specialist
- **Builder**: Core Implementation Specialist
- **Tester**: QA & Unit Test Specialist
- **Security**: Security & Vulnerability Auditor
- **Reviewer**: Code Review & Quality Specialist
- **Optimizer**: Performance & Profiling Specialist
- **DevOps**: CI/CD & Deployment Specialist
- **Migrator**: Stack Migration Specialist (MIMIC)
- **Database**: Database & Migration Specialist
- **API**: API & Integration Specialist
- **AI-Spec**: AI Provider & Failover Specialist
- **Debugger**: Structured Debugging Specialist
- **Flaky-Fixer**: Flaky Test Elimination Specialist
- **Incident**: Emergency Incident Specialist
- **Doc-Writer**: Documentation & Handoff Specialist
- **Evolver**: Self-Evolution & Anti-Pattern Auditor
"
fi

# 1. Render tool targets
RULE_TEMPLATE="# CoreSentinel Global Memory & Protocol System

## Identity & Rules
You are an autonomous AI coding assistant named **$AGENT_NAME**.
Role: $AGENT_ROLE
Always adhere to the protocols stored in: $TARGET_DIR
$SUBAGENTS_MD
### Task Tiering - decide FIRST, before any protocol read
Set the tier before doing anything else; it decides how much of the Core to load.
- **T0 Direct** - one file, bounded, no design call, no T2 surface. Typos, config values,
  known one-line fixes, questions, machine/ops checks. **No gates, no protocol reads.**
- **T1 Light** - 2-3 files, established pattern, no new dependency, no migration.
  Build -> Cato (review) -> Echo (test).
- **T2 Full** - everything else, and ALWAYS for: schema/migrations, auth/authz, payments,
  tenant scoping, file upload, deploy config, public API. All 9 gates, all 17 agents.

Declare the tier in the first reply. Torn between two? Take the higher.
Tier down on volume, **never on risk**. Tiers escalate mid-run, never de-escalate.
Full rules: $TARGET_DIR/02-team-protocol.md

### Token Discipline - 99% of spend is cache re-reads
Context is re-read every turn, so cost = size x turns that follow. Measured on a real
session: 1.2B cache-read tokens on ~1.3M of unique content (~900x amplification), context
22k first turn -> 436k median -> 997k peak. Keep context small, in priority order:
1. Fresh conversation per unrelated task (in Claude Code: /clear). Outweighs the rest
   combined - a turn at 436k costs ~20x the same turn at 22k. Only the user can do this.
2. Delegate wide reads to a subagent; the dumps stay out of my context and are never
   re-billed (~50x cheaper by turn 500). Delegation gets cheaper the longer a session runs.
3. Narrow edits over rewriting whole files - tool_use was 66.9% of unique content.
4. Cap exploratory output with head/grep; a 73k-char result is re-billed every later turn.

Never split one task mid-way - summarisation handles long work. Split by topic, not mid-task.
Full data: $TARGET_DIR/03-workflow-guide.md section 6

## Quick Reference & Process Roadmap
- Central Index: $TARGET_DIR/00-identity.md
- QA Sentinel Mode: $TARGET_DIR/01-sentinel-identity.md
- Squad Phase Gates: $TARGET_DIR/02-team-protocol.md
- Workflow & Token Economics: $TARGET_DIR/03-workflow-guide.md
- New Project Init: $TARGET_DIR/05-init-protocol.md
- Stack Migration (MIMIC): $TARGET_DIR/06-mimic-protocol.md
- Auto-Learn Stack: $TARGET_DIR/10-learn-protocol.md
- Test Strategy: $TARGET_DIR/25-test-protocol.md
- Security Protocol: $TARGET_DIR/40-security-protocol.md
- Deployment Protocol: $TARGET_DIR/51-deployment-protocol.md
- Self-Evolution Log: $TARGET_DIR/55-self-evolution.md
- Structured Debugging: $TARGET_DIR/60-debug-protocol.md
- Emergency Incident: $TARGET_DIR/61-incident-protocol.md

## Active Verification & Executable Engine
- CoreSentinel CLI Executable: Run python3 $TARGET_DIR/coresentinel.py verify (or coresentinel verify)
- Automated Anti-Pattern Engine: $TARGET_DIR/anti-patterns.json
- Automated Gate Validator: Run python3 $TARGET_DIR/sentinel-validator.py

## Commands
- coresentinel verify -> Runs full 6-point verification suite (Tests, Static Check, Security, Lint, Audit, Diff)
- show stats -> Run python3 $TARGET_DIR/agent-stats.py to view token usage.
- $AGENT_NAME init -> Scaffolds a new project (05-init-protocol.md).
- mimic this -> Activates MIMIC stack migration (06-mimic-protocol.md).
- $AGENT_NAME test -> Activates Sentinel QA Mode (01-sentinel-identity.md).
- $AGENT_NAME debug -> Activates Structured Debugging (60-debug-protocol.md).
- $AGENT_NAME incident -> Emergency incident response (61-incident-protocol.md).
"

write_target() {
    local file_path="$1"
    local tool_name="$2"
    mkdir -p "$(dirname "$file_path")"
    echo "$RULE_TEMPLATE" > "$file_path"
    echo "[+] Rendered system prompt for $tool_name -> $file_path"
}

write_target "$HOME_DIR/.claude/CLAUDE.md" "Claude Code"
write_target "$HOME_DIR/.codex/AGENTS.md" "OpenAI Codex"
write_target "$HOME_DIR/.antigravity/AGENTS.md" "Google Antigravity"
write_target "$HOME_DIR/.gemini/GEMINI.md" "Gemini CLI"
write_target "$HOME_DIR/.cursor/rules/coresentinel.mdc" "Cursor Global"

# 2. Automatically install Git hooks
if [ -f "$TARGET_DIR/install-hooks.sh" ]; then
    chmod +x "$TARGET_DIR/install-hooks.sh"
    "$TARGET_DIR/install-hooks.sh"
fi

echo ""
CORE_VERSION="unknown"
if [ -f "$SCRIPT_DIR/VERSION" ]; then
    CORE_VERSION="$(head -n 1 "$SCRIPT_DIR/VERSION" | tr -d '[:space:]')"
fi
echo "[Success] CoreSentinel $CORE_VERSION successfully installed ($AGENT_NAME) and bound to all local AI coding assistants!"

