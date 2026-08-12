#!/usr/bin/env bash
# CoreSentinel Git Hook Installer (POSIX Shell)
# Installs automated pre-commit & pre-push validation hooks into .git/hooks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_DIR="$SCRIPT_DIR/.git"
HOOKS_DIR="$GIT_DIR/hooks"

if [ ! -d "$GIT_DIR" ]; then
    echo "[!] Not a git repository ($GIT_DIR missing). Skipping git hook installation."
    exit 0
fi

mkdir -p "$HOOKS_DIR"

cat << 'EOF' > "$HOOKS_DIR/pre-commit"
#!/bin/sh
# CoreSentinel Automated Pre-Commit Verification Hook
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$SCRIPT_DIR/sentinel-validator.py" || python "$SCRIPT_DIR/sentinel-validator.py"
if [ $? -ne 0 ]; then
    echo "[ERR] CoreSentinel Pre-Commit Verification Failed! Commit aborted."
    exit 1
fi
EOF

cat << 'EOF' > "$HOOKS_DIR/pre-push"
#!/bin/sh
# CoreSentinel Automated Pre-Push Verification Hook
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
python3 "$SCRIPT_DIR/sentinel-validator.py" || python "$SCRIPT_DIR/sentinel-validator.py"
if [ $? -ne 0 ]; then
    echo "[ERR] CoreSentinel Pre-Push Verification Failed! Push aborted."
    exit 1
fi
EOF

chmod +x "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/pre-push"

echo "[✓] CoreSentinel Git Hooks installed successfully into $HOOKS_DIR"
