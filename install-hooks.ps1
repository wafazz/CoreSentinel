# CoreSentinel Git Hook Installer (PowerShell)
# Installs automated pre-commit & pre-push validation hooks into .git/hooks

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$GitDir = Join-Path $ScriptDir ".git"
$HooksDir = Join-Path $GitDir "hooks"

if (-not (Test-Path $GitDir)) {
    Write-Host "[!] Not a git repository ($GitDir missing). Skipping git hook installation." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path $HooksDir)) {
    New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null
}

$PreCommitPath = Join-Path $HooksDir "pre-commit"
$PrePushPath = Join-Path $HooksDir "pre-push"

$PreCommitContent = @'
#!/bin/sh
python sentinel-validator.py
if [ $? -ne 0 ]; then
    echo "[ERR] CoreSentinel Pre-Commit Verification Failed! Commit aborted."
    exit 1
fi
'@

$PrePushContent = @'
#!/bin/sh
python sentinel-validator.py
if [ $? -ne 0 ]; then
    echo "[ERR] CoreSentinel Pre-Push Verification Failed! Push aborted."
    exit 1
fi
'@

[System.IO.File]::WriteAllText($PreCommitPath, $PreCommitContent)
[System.IO.File]::WriteAllText($PrePushPath, $PrePushContent)

Write-Host "[OK] CoreSentinel Git Hooks installed successfully into $HooksDir" -ForegroundColor Green
