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
$SubAgentList = @()

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

    if ($CreateSubAgents -eq "Yes") {
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

# 1. Render tool targets
$Targets = @(
    @{ Tool = "Claude Code";      Path = "$HomeDir\.claude\CLAUDE.md" },
    @{ Tool = "OpenAI Codex";     Path = "$HomeDir\.codex\AGENTS.md" },
    @{ Tool = "Google Antigravity"; Path = "$HomeDir\.antigravity\AGENTS.md" },
    @{ Tool = "Gemini CLI";       Path = "$HomeDir\.gemini\GEMINI.md" },
    @{ Tool = "Cursor Global";    Path = "$HomeDir\.cursor\rules\coresentinel.mdc" }
)

# Literal template: single-quoted here-string so markdown backticks survive
# (in a double-quoted here-string PowerShell treats ` as its escape character).
$RuleTemplate = @'
# CoreSentinel Global Memory & Protocol System

## Identity & Rules
You are an autonomous AI coding assistant named **{{AGENT_NAME}}**.
Role: {{AGENT_ROLE}}
Always adhere to the protocols stored in: `{{TARGET_DIR}}`
{{SUB_AGENTS}}
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
Full rules: `{{TARGET_DIR}}\02-team-protocol.md`

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
Full data: `{{TARGET_DIR}}\03-workflow-guide.md` section 6

## Quick Reference & Process Roadmap
- Central Index: `{{TARGET_DIR}}\00-identity.md`
- QA Sentinel Mode: `{{TARGET_DIR}}\01-sentinel-identity.md`
- Squad Phase Gates: `{{TARGET_DIR}}\02-team-protocol.md`
- Workflow & Token Economics: `{{TARGET_DIR}}\03-workflow-guide.md`
- Skill Layer (host skills -> phase gates): `{{TARGET_DIR}}\18-skills-protocol.md`
- New Project Init: `{{TARGET_DIR}}\05-init-protocol.md`
- Stack Migration (MIMIC): `{{TARGET_DIR}}\06-mimic-protocol.md`
- Auto-Learn Stack: `{{TARGET_DIR}}\10-learn-protocol.md`
- Test Strategy: `{{TARGET_DIR}}\25-test-protocol.md`
- Security Protocol: `{{TARGET_DIR}}\40-security-protocol.md`
- Deployment Protocol: `{{TARGET_DIR}}\51-deployment-protocol.md`
- Self-Evolution Log: `{{TARGET_DIR}}\55-self-evolution.md`
- Structured Debugging: `{{TARGET_DIR}}\60-debug-protocol.md`
- Emergency Incident: `{{TARGET_DIR}}\61-incident-protocol.md`

## Active Verification & Executable Engine
- CoreSentinel CLI Executable: Run `python "{{TARGET_DIR}}\coresentinel.py" verify` (or `coresentinel verify`)
- Automated Anti-Pattern Engine: `{{TARGET_DIR}}\anti-patterns.json`
- Automated Gate Validator: Run `python "{{TARGET_DIR}}\sentinel-validator.py"`

## Commands
- `coresentinel verify` -> Runs full 6-point verification suite (Tests, Static Check, Security, Lint, Audit, Diff)
- `show stats` -> Run `python "{{TARGET_DIR}}\agent-stats.py"` to view token usage.
- `{{AGENT_NAME}} init` -> Scaffolds a new project (`05-init-protocol.md`).
- `mimic this` -> Activates MIMIC stack migration (`06-mimic-protocol.md`).
- `{{AGENT_NAME}} test` -> Activates Sentinel QA Mode (`01-sentinel-identity.md`).
- `{{AGENT_NAME}} debug` -> Activates Structured Debugging (`60-debug-protocol.md`).
- `{{AGENT_NAME}} incident` -> Emergency incident response (`61-incident-protocol.md`).
'@

$RuleTemplate = $RuleTemplate.Replace('{{AGENT_NAME}}', $AgentName).
                              Replace('{{AGENT_ROLE}}', $AgentRole).
                              Replace('{{TARGET_DIR}}', $TargetDir).
                              Replace('{{SUB_AGENTS}}', $SubAgentMd)

function Write-Target {
    param(
        [string]$FilePath,
        [string]$ToolName,
        [string]$Content
    )

    $parent = Split-Path -Parent $FilePath
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    # Back up before overwriting, but only when the content would actually change.
    # These five targets are routinely hand-edited; a re-install used to erase those
    # edits silently, with no copy kept. Identical re-installs stay backup-free.
    if (Test-Path $FilePath) {
        $existing = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
        if ($null -eq $existing) { $existing = "" }
        if ($existing.TrimEnd() -ne $Content.TrimEnd()) {
            $backupPath = "$FilePath.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            try {
                Copy-Item -Path $FilePath -Destination $backupPath -ErrorAction Stop
                Write-Host "[!] $ToolName file differed - backed up to $backupPath" -ForegroundColor Yellow
            } catch {
                Write-Host "[x] Could not back up $FilePath - leaving it untouched" -ForegroundColor Red
                return
            }
        }
    }

    Set-Content -Path $FilePath -Value $Content -Encoding UTF8
    Write-Host "[+] Rendered system prompt for $ToolName -> $FilePath" -ForegroundColor Green
}

foreach ($item in $Targets) {
    Write-Target -FilePath $item.Path -ToolName $item.Tool -Content $RuleTemplate
}

# 2. Automatically install Git hooks
$InstallerScript = Join-Path $TargetDir "install-hooks.ps1"
if (Test-Path $InstallerScript) {
    powershell -ExecutionPolicy Bypass -File $InstallerScript
}

$VersionFile = Join-Path $PSScriptRoot "VERSION"
$CoreVersion = if (Test-Path $VersionFile) { (Get-Content $VersionFile -TotalCount 1).Trim() } else { "unknown" }
Write-Host "`n[Success] CoreSentinel $CoreVersion successfully installed ($AgentName) and bound to all local AI coding assistants!" -ForegroundColor Cyan

