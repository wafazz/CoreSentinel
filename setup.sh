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

# 1. Update memorycore.conf
cat << EOF > "$TARGET_DIR/memorycore.conf"
# CoreSentinel Configuration
MEMORY_PATH=$TARGET_DIR
STATS_LOG=$TARGET_DIR/agent-usage-log.json
LABELS_FILE=$TARGET_DIR/project-labels.json
AGENT_NAME=$AGENT_NAME
AGENT_ROLE=$AGENT_ROLE
CREATE_SUBAGENTS=$CREATE_SUBAGENTS
SUBAGENT_COUNT=$SUBAGENT_COUNT
SUBAGENT_NAMING=$SUBAGENT_NAMING
EOF
echo "[+] Updated memorycore.conf"

RULE_TEMPLATE="# CoreSentinel Global Memory & Protocol System

## Identity & Rules
You are an autonomous AI coding assistant named **$AGENT_NAME**.
Role: $AGENT_ROLE
Always adhere to the protocols stored in: $TARGET_DIR
$SUBAGENTS_MD
## Quick Reference & Process Roadmap
- Central Index: $TARGET_DIR/00-identity.md
- QA Sentinel Mode: $TARGET_DIR/01-sentinel-identity.md
- Squad Phase Gates: $TARGET_DIR/02-team-protocol.md
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

# 3. Automatically install Git hooks
if [ -f "$TARGET_DIR/install-hooks.sh" ]; then
    chmod +x "$TARGET_DIR/install-hooks.sh"
    "$TARGET_DIR/install-hooks.sh"
fi

echo ""
echo "[Success] CoreSentinel 9.0 successfully installed ($AGENT_NAME) and bound to all local AI coding assistants!"

