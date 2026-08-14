"""
Structured logging.

Diagnostics go to stderr, always. The CLI's documented contract is that stdout
carries the payload so a damaged Core still emits valid JSON — a rule the
anti-pattern scanner broke by logging to stdout, which corrupted every `--json`
payload of any engine that reused its rules in-process.

Values are redacted before they are written. A governance tool that leaks the
secret it just caught has not caught it.
"""

import sys
import json
from datetime import datetime

LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40, "silent": 100}

# Redaction lives in coresentinel_core.security.redaction so the logger and the
# audit ledger cannot drift apart about what counts as a secret.
from coresentinel_core.security.redaction import (REDACTED, SENSITIVE_VALUES,
                                                  is_sensitive_key, redact,
                                                  redact_text)

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

ICON = {"debug": "·", "info": "+", "warn": "!", "error": "✗"}


class Logger:
    def __init__(self, level="info", fmt="text", stream=None):
        self.level = level if level in LEVELS else "info"
        self.format = fmt if fmt in ("text", "json") else "text"
        self.stream = stream or sys.stderr

    def enabled(self, level):
        return LEVELS.get(level, 20) >= LEVELS[self.level]

    def log(self, level, message, **fields):
        if not self.enabled(level):
            return
        safe_message = redact_text(message)
        safe_fields = redact(fields)

        if self.format == "json":
            payload = {"ts": datetime.now().strftime(TIMESTAMP_FORMAT),
                       "level": level, "message": safe_message}
            payload.update(safe_fields)
            print(json.dumps(payload, default=str), file=self.stream)
            return

        suffix = " ".join(f"{k}={v}" for k, v in safe_fields.items())
        line = f"[{ICON.get(level, '·')}] {safe_message}"
        print(f"{line} {suffix}".rstrip(), file=self.stream)

    def debug(self, message, **fields):
        self.log("debug", message, **fields)

    def info(self, message, **fields):
        self.log("info", message, **fields)

    def warn(self, message, **fields):
        self.log("warn", message, **fields)

    def error(self, message, **fields):
        self.log("error", message, **fields)
