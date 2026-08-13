"""
Redaction — one implementation, used by everything that writes.

A governance tool that leaks the secret it just caught has not caught it. The
logger has redacted since Phase 2; the audit ledger needs the same rules, and a
second copy of them would eventually disagree with the first. So the patterns
live here and both import them.

Two kinds of match, because credentials arrive two ways:

  * a field *named* like a secret — its value never survives, whatever it holds;
  * a value *shaped* like a credential in free text, where no field name warns you.
"""

import re

REDACTED = "[redacted]"

# Field names whose values never reach a log line or an audit record.
SENSITIVE_KEYS = re.compile(
    r"(?i)(pass(word|wd)?|secret|token|api[_-]?key|apikey|auth|credential|"
    r"private[_-]?key|session|bearer|access[_-]?key|client[_-]?secret)")

# Credential shapes that appear inside free text, where nothing names them.
SENSITIVE_VALUES = [
    # PEM blocks, whole.
    re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----[\s\S]*?-----END[^-]*-----"),
    # Vendor-prefixed tokens: Stripe, GitHub, Slack, OpenAI, Anthropic.
    re.compile(r"\b(?:sk|pk|rk|ghp|gho|ghu|ghs|ghr|xox[baprs])[-_][A-Za-z0-9_\-]{16,}\b"),
    # Bearer / Authorization headers.
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}\b"),
    # AWS access key ids.
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    # A credential embedded in a URL.
    re.compile(r"://[^/\s:@]+:[^/\s@]+@"),
    # key=value / key: value where the key looks sensitive.
    re.compile(r"(?i)\b(pass(word|wd)?|secret|token|api[_-]?key|auth)\b\s*[:=]\s*"
               r"['\"]?[A-Za-z0-9_\-./+]{12,}['\"]?"),
]


def redact_text(text):
    result = str(text)
    for pattern in SENSITIVE_VALUES:
        result = pattern.sub(REDACTED, result)
    return result


def redact(value):
    """Recursively strip credentials from anything on its way to being written."""
    if isinstance(value, dict):
        return {k: (REDACTED if SENSITIVE_KEYS.search(str(k)) else redact(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def contains_secret(value):
    """Whether anything in this structure would be redacted. For tests and doctor."""
    import json
    rendered = json.dumps(value, default=str) if not isinstance(value, str) else value
    return redact_text(rendered) != rendered
