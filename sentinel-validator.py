#!/usr/bin/env python3
"""
CoreSentinel Automated Gate & Verification Validator
Executes pre-flight, post-flight, and gate verification checks to ensure zero-defect delivery.
"""

import sys
import os
import json
import re
import subprocess
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent.resolve()
ANTI_PATTERNS_FILE = SCRIPT_DIR / "anti-patterns.json"

def log(msg, level="INFO"):
    prefixes = {
        "INFO": "[+] ",
        "SUCCESS": "[OK] ",
        "WARNING": "[!] ",
        "ERROR": "[ERR] "
    }
    prefix = prefixes.get(level, "[+] ")
    print(f"{prefix}{msg}")

def load_anti_patterns():
    if not ANTI_PATTERNS_FILE.exists():
        log(f"Anti-patterns file not found at {ANTI_PATTERNS_FILE}", "WARNING")
        return []
    try:
        with open(ANTI_PATTERNS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("anti_patterns", [])
    except Exception as e:
        log(f"Error loading anti-patterns: {e}", "ERROR")
        return []

def check_secrets_and_security(files):
    violations = []
    secret_patterns = [
        (re.compile(r'(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']'), "Potential hardcoded secret key"),
        (re.compile(r'-----BEGIN (RSA|EC|PRIVATE) KEY-----'), "Hardcoded private key block")
    ]
    for file_path in files:
        if not os.path.isfile(file_path):
            continue
        # Skip binary / non-code files
        if file_path.endswith(('.png', '.jpg', '.pdf', '.exe', '.zip', '.pyc', '.json', '.conf')):
            continue
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for pattern, desc in secret_patterns:
                    if pattern.search(content):
                        violations.append((file_path, desc))
        except (OSError, UnicodeDecodeError) as e:
            log(f"Skipping unreadable file {file_path}: {e}", "WARNING")
    return violations

def check_superficial_patches(files):
    violations = []
    patch_patterns = [
        (re.compile(r'except\s+Exception\s*:\s*pass'), "Silent exception swallowing (except Exception: pass)"),
        (re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}'), "Empty catch block in JavaScript/TypeScript"),
        (re.compile(r'//\s*assert'), "Commented-out assertion found in test code"),
        (re.compile(r'#\s*assert'), "Commented-out assertion found in Python test code")
    ]
    for file_path in files:
        if not os.path.isfile(file_path):
            continue
        if file_path.endswith(('.png', '.jpg', '.pdf', '.exe', '.zip', '.pyc', '.json', '.conf')) or "sentinel-validator.py" in file_path:
            continue
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for pattern, desc in patch_patterns:
                    if pattern.search(content):
                        violations.append((file_path, desc))
        except (OSError, UnicodeDecodeError) as e:
            log(f"Skipping unreadable file {file_path}: {e}", "WARNING")
    return violations

def get_staged_or_changed_files():
    try:
        res = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True)
        files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        if not files:
            res = subprocess.run(["git", "diff", "--name-only"], capture_output=True, text=True, check=True)
            files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        return files
    except subprocess.SubprocessError as e:
        log(f"Git diff query warning: {e}", "WARNING")
        return []

def main():
    log("Running CoreSentinel Verification & Gate Validator...", "INFO")
    anti_patterns = load_anti_patterns()
    log(f"Loaded {len(anti_patterns)} anti-pattern rules from index.", "INFO")

    changed_files = get_staged_or_changed_files()
    if not changed_files:
        log("No changed/staged git files detected to validate.", "SUCCESS")
        return 0

    log(f"Validating {len(changed_files)} changed files...", "INFO")
    
    sec_violations = check_secrets_and_security(changed_files)
    patch_violations = check_superficial_patches(changed_files)

    has_errors = False

    if sec_violations:
        has_errors = True
        log("SECURITY VIOLATIONS DETECTED:", "ERROR")
        for f, desc in sec_violations:
            print(f"  - {f}: {desc}")

    if patch_violations:
        has_errors = True
        log("SUPERFICIAL PATCH / MASKING VIOLATIONS DETECTED:", "ERROR")
        for f, desc in patch_violations:
            print(f"  - {f}: {desc}")

    if has_errors:
        log("CoreSentinel Gate Validation FAILED! Resolve violations before proceeding.", "ERROR")
        sys.exit(1)
    else:
        log("All CoreSentinel verification checks PASSED cleanly!", "SUCCESS")
        sys.exit(0)

if __name__ == "__main__":
    main()
