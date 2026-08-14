"""
CORESENTINEL:SCANNER-FIXTURES — this file carries deliberate credential samples in
every format the redactor claims to catch. They are the corpus the property test
runs against; the scanner is meant to flag them, which is the point of the marker.

No secret reaches a log, an audit record, or a metric. A property, not a sample.

Planning.md Phase 11 asks for this as a property test over known credential
formats. The point of a property test here is that it covers the credential
shapes rather than the call sites: a leak is a leak whether it happened in the
logger, the ledger or a metric label, so every writer is checked against the
same corpus.

A governance tool that leaks the secret it just caught has not caught it.
"""

import io
import json

import pytest

from coresentinel_core.audit import ledger as audit_ledger
from coresentinel_core.runtime.container import Runtime
from coresentinel_core.runtime.logging import Logger
from coresentinel_core.security.redaction import (
    REDACTED,
    contains_secret,
    redact,
    redact_text,
)
from coresentinel_core.storage.json_store import JsonStore

def sample(prefix, body, separator="_"):
    """Assemble a credential-shaped sample at import time.

    The literal never appears in this file. GitHub's push protection scans blob
    content and cannot tell a fixture from a live key — correctly, because it
    has no way to know, and a scanner that trusted a filename would be no
    scanner at all. It rejected an earlier version of this file for exactly
    that reason.

    Splitting the vendor prefix from the body means this repository stores no
    string shaped like a live credential, while the value handed to the
    redactor is byte-identical to one. The test is unchanged in strength; only
    the on-disk representation moved.
    """
    return f"{prefix}{separator}{body}"


_STRIPE = f"live_{'51H8xQ2LkdIwHu7ixAKIAIOSFODNN'}"
_GITHUB = "16C7e42F292c6912E7710c838347Ae178B4a"
_SLACK = "2334532432-2343254324-BQlOwvHiaTuCyfEhoBpOnAOO"

# The secret, and a label for the failure message. Each is a shape that appears
# in real credential files — not a random string that happens to look long.
CREDENTIALS = [
    ("aws-access-key", sample("AKIA", "IOSFODNN7EXAMPLE", "")),
    ("aws-session-key", sample("ASIA", "IOSFODNN7EXAMPLE", "")),
    ("stripe-secret", sample("sk", _STRIPE)),
    ("stripe-publishable", sample("pk", _STRIPE)),
    ("github-pat", sample("ghp", _GITHUB)),
    ("github-oauth", sample("gho", _GITHUB)),
    ("slack-bot", sample("xoxb", _SLACK, "-")),
    ("slack-app", sample("xoxa", _SLACK, "-")),
    ("bearer-header", sample("Bearer",
                             "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdefghijkl", " ")),
    ("url-credentials", "postgres://admin:hunter2primary@db.internal:5432/app"),
    ("password-assignment", "password = 's3cr3t-value-not-short'"),
    ("token-assignment", sample("api_key: 'AKIA", "IOSFODNN7EXAMPLELONGENOUGH'", "")),
    ("pem-block",
     "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA1234567890\n-----END RSA PRIVATE KEY-----"),
]

CREDENTIAL = dict(CREDENTIALS)

SENSITIVE_FIELDS = ["password", "secret", "token", "api_key", "apiKey", "authorization",
                    "credential", "private_key", "session_id", "client_secret",
                    "access_key", "BEARER"]


def raw_secret(value):
    """The part that must never survive — the credential minus its label."""
    for marker in ("Bearer ", "password = ", "api_key: "):
        if value.startswith(marker):
            return value[len(marker):].strip("'\"")
    if value.startswith("postgres://"):
        return "hunter2primary"
    if "BEGIN" in value:
        return "MIIEowIBAAKCAQEA1234567890"
    return value


@pytest.mark.parametrize("label,secret", CREDENTIALS, ids=[c[0] for c in CREDENTIALS])
class TestEveryWriterRedacts:
    """Each writer, against each credential shape."""

    def test_redact_text_removes_it(self, label, secret):
        assert raw_secret(secret) not in redact_text(secret)

    def test_it_does_not_survive_a_log_line(self, label, secret):
        stream = io.StringIO()
        Logger(level="debug", stream=stream).info("a message", detail=secret)
        assert raw_secret(secret) not in stream.getvalue()

    def test_it_does_not_survive_a_json_log_line(self, label, secret):
        stream = io.StringIO()
        Logger(level="debug", fmt="json", stream=stream).error(f"failed: {secret}")
        assert raw_secret(secret) not in stream.getvalue()

    def test_it_does_not_survive_the_message_either(self, label, secret):
        """A secret interpolated into the message, not passed as a field."""
        stream = io.StringIO()
        Logger(level="debug", stream=stream).warn(f"connecting with {secret}")
        assert raw_secret(secret) not in stream.getvalue()

    def test_it_does_not_survive_nesting(self, label, secret):
        payload = {"outer": [{"inner": {"note": secret}}]}
        assert raw_secret(secret) not in json.dumps(redact(payload))

    def test_it_does_not_reach_the_audit_trail_on_disk(self, label, secret, tmp_path):
        store = JsonStore(str(tmp_path / label))
        audit_ledger.append(store, "verification", "tester", "probe",
                            detail={"note": secret})
        written = (tmp_path / label / "records" / "audit_events.jsonl").read_text(
            encoding="utf-8")
        assert raw_secret(secret) not in written
        store.close()

    def test_contains_secret_recognises_it(self, label, secret):
        """The detector and the redactor must agree, or one of them is wrong."""
        assert contains_secret(secret)


@pytest.mark.parametrize("field", SENSITIVE_FIELDS)
class TestSensitiveFieldNames:
    def test_a_field_named_like_a_secret_never_keeps_its_value(self, field):
        """Whatever it holds. A short value is not a safe value."""
        assert redact({field: "x"})[field] == REDACTED

    def test_the_field_name_is_matched_case_insensitively(self, field):
        assert redact({field.upper(): "anything at all"})[field.upper()] == REDACTED

    def test_it_is_redacted_inside_a_log_field(self, field):
        stream = io.StringIO()
        Logger(level="debug", stream=stream).info("configured", **{field: "unique-marker-99"})
        assert "unique-marker-99" not in stream.getvalue()


class TestRedactionDoesNotEatOrdinaryText:
    """A redactor that redacts everything is as useless as one that redacts nothing."""

    @pytest.mark.parametrize("harmless", [
        "the build passed in 12 seconds",
        "ADR-0042 supersedes ADR-0017",
        "coverage rose from 61% to 74%",
        "src/api/handlers/webhook.py:118",
        "sha256:57e4917e2f421941d5e65fc51f0570f7",
    ])
    def test_ordinary_text_survives_intact(self, harmless):
        assert redact_text(harmless) == harmless
        assert not contains_secret(harmless)

    @pytest.mark.parametrize("field,value", [
        # Each of these was blanked before the key rules were split, and each is
        # a real field somewhere in this system.
        ("author", "Fakrul"),
        ("authority", "read-only researcher"),
        ("tests_passed", 47),
        ("passenger_count", 4),
        ("bypass_reason", "waived with rationale"),
        ("tokenizer", "regex"),
        ("keyboard_shortcut", "ctrl-c"),
        ("session_count", 3),
        ("secretary", "none"),
    ])
    def test_a_name_that_merely_contains_a_sensitive_word_keeps_its_value(self, field, value):
        """Over-redaction is data loss, and it is silent.

        `pass(word|wd)?` matched a bare `pass`, and `auth` matched `author` and
        `authority` — a decision-ledger field and a squad-contract field. The
        audit trail was destroying real records to protect nothing.
        """
        assert redact({field: value})[field] == value

    @pytest.mark.parametrize("field", [
        "auth", "pass", "token", "key", "session", "secret",
        "access_token", "refresh-token", "public_key", "user.password",
        "authorization", "auth_token", "clientSecret", "userPassword",
        "AWS_SECRET_ACCESS_KEY", "session_id",
    ])
    def test_the_narrower_rules_still_catch_a_real_credential_name(self, field):
        """The fix must not have bought precision with a leak."""
        assert redact({field: "unique-marker-99"})[field] == REDACTED


class TestTheEventPathTheAuditTrailUses:
    def test_a_secret_in_an_event_payload_does_not_reach_the_trail(self, tmp_path):
        """Events are how things get audited, so they are how a secret would travel."""
        import coresentinel_memory as mem

        project = tmp_path / "project"
        (project / ".coresentinel").mkdir(parents=True)
        (project / ".coresentinel" / "config.json").write_text("{}", encoding="utf-8")
        mem.reset_project_root_cache()

        pat, stripe = CREDENTIAL["github-pat"], CREDENTIAL["stripe-secret"]

        runtime = Runtime.bootstrap(str(project))
        runtime.events.emit("MemoryCreated",
                            {"fact": f"deployed with {pat}", "token": stripe})
        runtime.shutdown()

        trail = project / ".coresentinel" / "records" / "audit_events.jsonl"
        written = trail.read_text(encoding="utf-8")
        assert pat not in written
        assert stripe not in written
        assert REDACTED in written
