"""Security scanner — the validator that blocks commits must actually catch violations.

CORESENTINEL:SCANNER-FIXTURES — this file contains deliberate secret and anti-pattern
samples used to prove the scanner catches them. It is exempt from the scanner itself.
"""

import json

import pytest

from conftest import load_hyphenated_module


@pytest.fixture(scope="module")
def validator():
    return load_hyphenated_module("sentinel-validator.py", "sentinel_validator")


class TestSecretDetection:
    @pytest.mark.parametrize("content", [
        'api_key = "sk_live_a1b2c3d4e5f6g7h8i9j0"',
        'API_KEY="AKIAIOSFODNN7EXAMPLEKEY123"',
        'secret_key = "abcdefghijklmnopqrstuvwxyz"',
        'auth_token = "ghp_16CharsAtLeastLongToken"',
        '-----BEGIN RSA PRIVATE KEY-----',
        '-----BEGIN PRIVATE KEY-----',
    ])
    def test_flags_hardcoded_credentials(self, validator, tmp_path, write_file, content):
        target = write_file(tmp_path / "leak.py", content)
        assert validator.check_secrets_and_security([str(target)]), \
            f"scanner missed a hardcoded credential: {content!r}"

    @pytest.mark.parametrize("content", [
        'api_key = os.environ["API_KEY"]',
        'token = config.get("auth_token")',
        'api_key = ""',
        '# api_key = "documentation example only"'.replace("api_key", "sample"),
    ])
    def test_does_not_flag_safe_credential_handling(self, validator, tmp_path, write_file, content):
        target = write_file(tmp_path / "safe.py", content)
        assert not validator.check_secrets_and_security([str(target)]), \
            f"false positive on safe code: {content!r}"

    def test_reports_the_offending_file(self, validator, tmp_path, write_file):
        target = write_file(tmp_path / "leak.py", 'api_key = "sk_live_a1b2c3d4e5f6g7h8"')
        violations = validator.check_secrets_and_security([str(target)])
        assert violations[0][0] == str(target)
        assert violations[0][1], "every violation must carry a description"


class TestSuperficialPatchDetection:
    @pytest.mark.parametrize("content,label", [
        ("try:\n    risky()\nexcept Exception: pass\n", "silent python swallow"),
        ("try { risky() } catch (e) {}", "empty JS catch"),
        ("// assert response.status == 200", "commented JS assertion"),
        ("# assert user.is_admin", "commented python assertion"),
    ])
    def test_flags_masked_failures(self, validator, tmp_path, write_file, content, label):
        target = write_file(tmp_path / "patch.py", content)
        assert validator.check_superficial_patches([str(target)]), f"scanner missed: {label}"

    @pytest.mark.parametrize("content", [
        "try:\n    risky()\nexcept OSError as e:\n    log(e)\n    raise\n",
        "try { risky() } catch (e) { report(e) }",
        "assert response.status == 200",
    ])
    def test_does_not_flag_honest_error_handling(self, validator, tmp_path, write_file, content):
        target = write_file(tmp_path / "honest.py", content)
        assert not validator.check_superficial_patches([str(target)]), \
            f"false positive on legitimate handling: {content!r}"

    def test_scanner_does_not_flag_its_own_rule_definitions(self, validator, core_dir):
        """The validator holds the patterns as literals; scanning itself must not self-report."""
        assert not validator.check_superficial_patches([str(core_dir / "sentinel-validator.py")])


class TestFixtureExemption:
    """The opt-out must be narrow, opening-lines-only, and never silent."""

    def test_marked_file_is_exempt(self, validator, tmp_path, write_file):
        marked = write_file(tmp_path / "fixtures.py",
                            f'"""{validator.FIXTURE_MARKER}"""\n'
                            'api_key = "sk_live_a1b2c3d4e5f6g7h8"\n')
        assert validator.check_secrets_and_security([str(marked)]) == []

    def test_exemption_applies_to_anti_patterns_too(self, validator, tmp_path, write_file):
        marked = write_file(tmp_path / "fixtures.py",
                            f'"""{validator.FIXTURE_MARKER}"""\n'
                            'try:\n    x()\nexcept Exception: pass\n')
        assert validator.check_superficial_patches([str(marked)]) == []

    def test_marker_buried_below_the_header_does_not_exempt(self, validator, tmp_path, write_file):
        """Otherwise a real secret could be hidden by a marker far down the file."""
        buried = write_file(tmp_path / "sneaky.py",
                            "\n" * 40 + f"# {validator.FIXTURE_MARKER}\n"
                            'api_key = "sk_live_a1b2c3d4e5f6g7h8"\n')
        assert validator.check_secrets_and_security([str(buried)]), \
            "a marker outside the opening lines must not grant an exemption"

    def test_unmarked_file_is_still_scanned(self, validator, tmp_path, write_file):
        plain = write_file(tmp_path / "plain.py", 'api_key = "sk_live_a1b2c3d4e5f6g7h8"\n')
        assert validator.check_secrets_and_security([str(plain)])

    def test_exemption_is_announced(self, validator, tmp_path, write_file, capsys):
        marked = write_file(tmp_path / "fixtures.py",
                            f'"""{validator.FIXTURE_MARKER}"""\n'
                            'api_key = "sk_live_a1b2c3d4e5f6g7h8"\n')
        validator.check_secrets_and_security([str(marked)])
        assert "skipped" in capsys.readouterr().out.lower(), \
            "a skipped file must be reported, never silently ignored"


class TestScannerRobustness:
    def test_missing_file_is_skipped_not_fatal(self, validator, tmp_path):
        assert validator.check_secrets_and_security([str(tmp_path / "nope.py")]) == []
        assert validator.check_superficial_patches([str(tmp_path / "nope.py")]) == []

    def test_binary_and_data_files_are_skipped(self, validator, tmp_path, write_file):
        target = write_file(tmp_path / "data.json", '{"api_key": "sk_live_a1b2c3d4e5f6g7h8"}')
        assert validator.check_secrets_and_security([str(target)]) == []

    def test_undecodable_bytes_do_not_crash_the_scan(self, validator, tmp_path):
        target = tmp_path / "binary.py"
        target.write_bytes(b"\xff\xfe\x00\x01 api_key = 'x'")
        validator.check_secrets_and_security([str(target)])


@pytest.fixture(scope="module")
def rules(request):
    path = request.config.rootpath / "anti-patterns.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))["anti_patterns"]


class TestAntiPatternDatabase:
    def test_database_is_populated(self, rules):
        assert len(rules) >= 5

    def test_rule_ids_are_unique(self, rules):
        ids = [r["id"] for r in rules]
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("field", ["id", "category", "name", "rule", "enforcement", "fix_pattern"])
    def test_every_rule_is_complete(self, rules, field):
        incomplete = [r.get("id", "<no id>") for r in rules if not r.get(field)]
        assert not incomplete, f"rules missing '{field}': {incomplete}"

    def test_enforcement_levels_are_recognized(self, rules):
        allowed = {"STRICT_BLOCK", "WARNING"}
        unknown = [(r["id"], r["enforcement"]) for r in rules if r["enforcement"] not in allowed]
        assert not unknown, f"unrecognized enforcement levels: {unknown}"

    def test_verification_rules_are_blocking(self, rules):
        """Evidence and masking rules are the core guarantee — they must not be advisory."""
        for rule in rules:
            if rule["category"] == "Verification":
                assert rule["enforcement"] == "STRICT_BLOCK", \
                    f"{rule['id']} governs verification but is not STRICT_BLOCK"
