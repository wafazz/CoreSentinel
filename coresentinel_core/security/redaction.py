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
#
# Split in two, because one alternation could not be both safe and precise.
# `pass(word|wd)?` made the suffix optional, so a bare `pass` matched — and
# `tests_passed`, `passenger_count` and `bypass_reason` were all blanked. `auth`
# matched `author` and `authority`, which are a decision-ledger field and a
# squad-contract field: the audit trail was destroying real data to protect
# nothing. Over-redaction is quiet, which is what made it survive this long.

# Tier 1 — unambiguous. These mean a credential wherever they appear in a name,
# including glued into a longer one (`clientSecret`, `userPassword`).
SENSITIVE_KEY_SUBSTRINGS = re.compile(
    r"(?i)(password|passwd|api[_-]?key|apikey|credential|secret[_-]?key|"
    r"private[_-]?key|bearer|access[_-]?key|client[_-]?secret|auth[_-]?token|"
    r"authorization|authorisation|session[_-]?id)")

# Tier 2 — sensitive as a whole word inside a compound name. `access_token` and
# `public_key` are credentials; `tokenizer` and `keyboard` are not.
SENSITIVE_KEY_WORDS = re.compile(
    r"(?i)(?:^|[^a-z0-9])(token|secret|key)(?:[^a-z0-9]|$)")

# Tier 3 — sensitive only as the entire key. These are the short words that are
# a credential alone and a perfectly ordinary prefix otherwise: `session` is a
# session identifier, `session_count` is a number; `pass` is a password,
# `pass_rate` is a statistic.
SENSITIVE_KEY_EXACT = {"auth", "pass", "session"}


def is_sensitive_key(name):
    """Whether a field with this name must never have its value written.

    Three tiers rather than one alternation, because a single pattern could not
    be both safe and precise: it had to match `client_secret` glued together and
    `access_token` as a word and bare `auth`, without also matching `author`.
    """
    text = str(name)
    return bool(
        SENSITIVE_KEY_SUBSTRINGS.search(text)
        or SENSITIVE_KEY_WORDS.search(text)
        or text.strip().lower() in SENSITIVE_KEY_EXACT)

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
        return {k: (REDACTED if is_sensitive_key(k) else redact(v))
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
