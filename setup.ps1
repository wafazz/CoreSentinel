# CoreSentinel Installer / Sync Script (Windows PowerShell)
# Configures CoreSentinel as global memory & protocol core across all AI coding tools.

param (
    [switch]$Sync,
    [string]$TargetDir = "",
    [switch]$NonInteractive,
    [string]$AgentName = "",
    [string]$AgentRole = "",
    [string]$CreateSubAgents = "",
    [int]$SubAgentCount = 0,
    [string]$SubAgentNaming = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $TargetDir) {
    $TargetDir = $ScriptDir
}

$HomeDir = [Environment]::GetFolderPath("UserProfile")
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " CoreSentinel Installer & Tool Binding " -ForegroundColor Cyan
Write-Host " Target Memory Path: $TargetDir" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

# Interactive Setup Prompts
if (-not $NonInteractive) {
    Write-Host "`n--- CoreSentinel Interactive Setup ---`n" -ForegroundColor Green

    # 1. Agent Name
    if (-not $AgentName) {
        $inputVal = Read-Host "1) Agent Name? [Default: Iris]"
        $AgentName = if ([string]::IsNullOrWhiteSpace($inputVal)) { "Iris" } else { $inputVal.Trim() }
    }

    # 2. Agent Role / Act As
    if (-not $AgentRole) {
        $inputVal = Read-Host "2) Agent acts as what? [Default: Universal coding agent for Fakrul]"
        $AgentRole = if ([string]::IsNullOrWhiteSpace($inputVal)) { "Universal coding agent for Fakrul" } else { $inputVal.Trim() }
    }

    # 3. Create sub-agents or not?
    if (-not $CreateSubAgents) {
        $inputVal = Read-Host "3) Create sub-agents or not? (Y/N) [Default: Y]"
        if ($inputVal -match "^[Nn]") {
            $CreateSubAgents = "No"
        } else {
            $CreateSubAgents = "Yes"
        }
    }

    # 4 & 5. Sub-agents details (if enabled)
    $SubAgentList = @()
    if ($CreateSubAgents -eq "Yes") {
        if ($SubAgentCount -le 0) {
            $inputVal = Read-Host "4) How many sub-agents? [Default: 17]"
            $SubAgentCount = if ([string]::IsNullOrWhiteSpace($inputVal)) { 17 } else { [int]$inputVal.Trim() }
        }

        if (-not $SubAgentNaming) {
            Write-Host "5) Sub-agents auto-named or give name?"
            Write-Host "   [1] Auto-named (Standard 17 Squad names)"
            Write-Host "   [2] Give custom names manually"
            $namingChoice = Read-Host "   Choice (1 or 2) [Default: 1]"
            $SubAgentNaming = if ($namingChoice.Trim() -eq "2") { "Custom" } else { "Auto" }
        }

        $StandardSquad = @(
            @{ Name = "Scout"; Role = "Codebase Researcher & Explorer" },
            @{ Name = "Architect"; Role = "System Architecture & Design Specialist" },
            @{ Name = "Builder"; Role = "Core Implementation Specialist" },
            @{ Name = "Tester"; Role = "QA & Unit Test Specialist" },
            @{ Name = "Security"; Role = "Security & Vulnerability Auditor" },
            @{ Name = "Reviewer"; Role = "Code Review & Quality Specialist" },
            @{ Name = "Optimizer"; Role = "Performance & Profiling Specialist" },
            @{ Name = "DevOps"; Role = "CI/CD & Deployment Specialist" },
            @{ Name = "Migrator"; Role = "Stack Migration Specialist (MIMIC)" },
            @{ Name = "Database"; Role = "Database & Migration Specialist" },
            @{ Name = "API"; Role = "API & Integration Specialist" },
            @{ Name = "AI-Spec"; Role = "AI Provider & Failover Specialist" },
            @{ Name = "Debugger"; Role = "Structured Debugging Specialist" },
            @{ Name = "Flaky-Fixer"; Role = "Flaky Test Elimination Specialist" },
            @{ Name = "Incident"; Role = "Emergency Incident Specialist" },
            @{ Name = "Doc-Writer"; Role = "Documentation & Handoff Specialist" },
            @{ Name = "Evolver"; Role = "Self-Evolution & Anti-Pattern Auditor" }
        )

        if ($SubAgentNaming -eq "Custom") {
            for ($i = 1; $i -le $SubAgentCount; $i++) {
                $nameInput = Read-Host "   -> Sub-agent #$i Name"
                $name = if ([string]::IsNullOrWhiteSpace($nameInput)) { "SubAgent-$i" } else { $nameInput.Trim() }
                $roleInput = Read-Host "   -> Sub-agent #$i Role"
                $role = if ([string]::IsNullOrWhiteSpace($roleInput)) { "Specialist Agent $i" } else { $roleInput.Trim() }
                $SubAgentList += @{ Name = $name; Role = $role }
            }
        } else {
            for ($i = 0; $i -lt $SubAgentCount; $i++) {
                if ($i -lt $StandardSquad.Count) {
                    $SubAgentList += $StandardSquad[$i]
                } else {
                    $num = $i + 1
                    $SubAgentList += @{ Name = "Agent-$num"; Role = "Specialized Task Sub-Agent $num" }
                }
            }
        }
    }
} else {
    # Non-interactive defaults
    if (-not $AgentName) { $AgentName = "Iris" }
    if (-not $AgentRole) { $AgentRole = "Universal coding agent for Fakrul" }
    if (-not $CreateSubAgents) { $CreateSubAgents = "Yes" }
    if ($SubAgentCount -le 0) { $SubAgentCount = 17 }
    if (-not $SubAgentNaming) { $SubAgentNaming = "Auto" }
}

# Build Sub-agent markdown representation
$SubAgentMd = ""
if ($CreateSubAgents -eq "Yes" -and $SubAgentList.Count -gt 0) {
    $SubAgentLines = @()
    foreach ($sa in $SubAgentList) {
        $SubAgentLines += "- **$($sa.Name)**: $($sa.Role)"
    }
    $SubAgentMd = "`n### Active Sub-Agents ($($SubAgentList.Count))`n" + ($SubAgentLines -join "`n") + "`n"
} else {
    $SubAgentMd = "`n### Sub-Agents: Disabled`n"
}

# 1. Update memorycore.conf
$ConfFile = Join-Path $TargetDir "memorycore.conf"
$ConfContent = @"
# CoreSentinel Configuration
MEMORY_PATH=$TargetDir
STATS_LOG=$TargetDir\agent-usage-log.json
LABELS_FILE=$TargetDir\project-labels.json
AGENT_NAME=$AgentName
AGENT_ROLE=$AgentRole
CREATE_SUBAGENTS=$CreateSubAgents
SUBAGENT_COUNT=$SubAgentCount
SUBAGENT_NAMING=$SubAgentNaming
"@
Set-Content -Path $ConfFile -Value $ConfContent -Encoding UTF8
Write-Host "[+] Updated memorycore.conf" -ForegroundColor Green

# 2. Render tool targets
$Targets = @(
    @{ Tool = "Claude Code";      Path = "$HomeDir\.claude\CLAUDE.md" },
    @{ Tool = "OpenAI Codex";     Path = "$HomeDir\.codex\AGENTS.md" },
    @{ Tool = "Google Antigravity"; Path = "$HomeDir\.antigravity\AGENTS.md" },
    @{ Tool = "Gemini CLI";       Path = "$HomeDir\.gemini\GEMINI.md" },
    @{ Tool = "Cursor Global";    Path = "$HomeDir\.cursor\rules\coresentinel.mdc" }
)

$RuleTemplate = @"
# CoreSentinel Global Memory & Protocol System

## Identity & Rules
You are an autonomous AI coding assistant named **$AgentName**.
Role: $AgentRole
Always adhere to the protocols stored in: `$TargetDir`
$SubAgentMd
## Quick Reference & Process Roadmap
- Central Index: `$TargetDir\00-identity.md`
- QA Sentinel Mode: `$TargetDir\01-sentinel-identity.md`
- Squad Phase Gates: `$TargetDir\02-team-protocol.md`
- New Project Init: `$TargetDir\05-init-protocol.md`
- Stack Migration (MIMIC): `$TargetDir\06-mimic-protocol.md`
- Auto-Learn Stack: `$TargetDir\10-learn-protocol.md`
- Test Strategy: `$TargetDir\25-test-protocol.md`
- Security Protocol: `$TargetDir\40-security-protocol.md`
- Deployment Protocol: `$TargetDir\51-deployment-protocol.md`
- Self-Evolution Log: `$TargetDir\55-self-evolution.md`
- Structured Debugging: `$TargetDir\60-debug-protocol.md`
- Emergency Incident: `$TargetDir\61-incident-protocol.md`

## Active Verification & Enforcement
- Automated Anti-Pattern Engine: `$TargetDir\anti-patterns.json`
- Automated Gate Validator: Run `python "$TargetDir\sentinel-validator.py"`

## Commands
- `show stats` -> Run `python "$TargetDir\agent-stats.py"` to view token usage.
- `verify gate` -> Run `python "$TargetDir\sentinel-validator.py"` to run empirical gate validation.
- `$AgentName init` -> Scaffolds a new project (`05-init-protocol.md`).
- `mimic this` -> Activates MIMIC stack migration (`06-mimic-protocol.md`).
- `$AgentName test` -> Activates Sentinel QA Mode (`01-sentinel-identity.md`).
- `$AgentName debug` -> Activates Structured Debugging (`60-debug-protocol.md`).
- `$AgentName incident` -> Emergency incident response (`61-incident-protocol.md`).
"@

foreach ($item in $Targets) {
    $parent = Split-Path -Parent $item.Path
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Set-Content -Path $item.Path -Value $RuleTemplate -Encoding UTF8
    Write-Host "[+] Rendered system prompt for $($item.Tool) -> $($item.Path)" -ForegroundColor Green
}

# 3. Automatically install Git hooks
$InstallerScript = Join-Path $TargetDir "install-hooks.ps1"
if (Test-Path $InstallerScript) {
    powershell -ExecutionPolicy Bypass -File $InstallerScript
}

Write-Host "`n[Success] CoreSentinel 9.0 successfully installed ($AgentName) and bound to all local AI coding assistants!" -ForegroundColor Cyan

