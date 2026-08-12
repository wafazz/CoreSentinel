"""Recovery — corrupt, missing and BOM-encoded state must degrade honestly, never silently."""

import json

import pytest

import coresentinel_doctor as doctor


def status_of(checks, name):
    return next(c["status"] for c in checks if c["check"] == name)


class TestCorruptState:
    def test_corrupt_memory_layer_fails_the_doctor(self, tmp_path, monkeypatch):
        memory = tmp_path / "memory"
        memory.mkdir()
        for layer in doctor.MEMORY_LAYERS:
            (memory / f"{layer}.json").write_text('{"facts": []}', encoding="utf-8")
        (memory / "project.json").write_text("{ this is not json", encoding="utf-8")

        monkeypatch.setattr(doctor, "MEMORY_DIR", memory)
        result = doctor.check_memory()

        assert result["status"] == "FAIL"
        assert any("CORRUPT" in f for f in result["findings"])

    def test_corrupt_layer_is_named_in_the_findings(self, tmp_path, monkeypatch):
        memory = tmp_path / "memory"
        memory.mkdir()
        for layer in doctor.MEMORY_LAYERS:
            (memory / f"{layer}.json").write_text('{"facts": []}', encoding="utf-8")
        (memory / "failures.json").write_text("<<<corrupt>>>", encoding="utf-8")

        monkeypatch.setattr(doctor, "MEMORY_DIR", memory)
        findings = " ".join(doctor.check_memory()["findings"])
        assert "failures" in findings

    def test_missing_memory_directory_fails_with_a_remedy(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "MEMORY_DIR", tmp_path / "absent")
        result = doctor.check_memory()

        assert result["status"] == "FAIL"
        assert "init" in (result["fix"] or ""), "a failing check must suggest a remedy"

    def test_partial_memory_warns_rather_than_fails(self, tmp_path, monkeypatch):
        memory = tmp_path / "memory"
        memory.mkdir()
        (memory / "project.json").write_text('{"facts": []}', encoding="utf-8")

        monkeypatch.setattr(doctor, "MEMORY_DIR", memory)
        assert doctor.check_memory()["status"] == "WARN"

    def test_corrupt_registry_fails_the_agent_check(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "SCRIPT_DIR", tmp_path)
        (tmp_path / "squad-contracts.json").write_text("not json at all", encoding="utf-8")
        assert doctor.check_agent_registry()["status"] == "FAIL"

    def test_incomplete_contract_warns(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "SCRIPT_DIR", tmp_path)
        (tmp_path / "squad-contracts.json").write_text(
            json.dumps({"squad": [{"name": "Ghost"}]}), encoding="utf-8")

        result = doctor.check_agent_registry()
        assert result["status"] == "WARN"
        assert any("Ghost" in f for f in result["findings"])


class TestMissingAssets:
    def test_missing_core_asset_fails_configuration(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "SCRIPT_DIR", tmp_path)
        result = doctor.check_configuration()

        assert result["status"] == "FAIL"
        assert any("MISSING" in f for f in result["findings"])

    def test_missing_anti_pattern_database_fails_security(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "SCRIPT_DIR", tmp_path)
        assert doctor.check_security_rules()["status"] == "FAIL"

    def test_empty_anti_pattern_database_fails_security(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "SCRIPT_DIR", tmp_path)
        (tmp_path / "anti-patterns.json").write_text(
            json.dumps({"anti_patterns": []}), encoding="utf-8")
        assert doctor.check_security_rules()["status"] == "FAIL"

    def test_unenforced_rule_warns(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "SCRIPT_DIR", tmp_path)
        (tmp_path / "anti-patterns.json").write_text(json.dumps(
            {"anti_patterns": [{"id": "AP-X", "enforcement": ""}]}), encoding="utf-8")
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")

        result = doctor.check_security_rules()
        assert result["status"] == "WARN"
        assert any("AP-X" in f for f in result["findings"])


class TestEncodingRecovery:
    """Windows tooling writes BOMs constantly; a BOM must not look like corruption."""

    def test_bom_encoded_json_still_parses(self, tmp_path):
        target = tmp_path / "bom.json"
        target.write_text(json.dumps({"facts": [{"fact": "x"}]}), encoding="utf-8-sig")

        data, error = doctor.read_json(target)
        assert error is None, f"BOM-encoded JSON was misread as corrupt: {error}"
        assert data["facts"][0]["fact"] == "x"

    def test_bom_encoded_memory_layer_is_healthy(self, tmp_path, monkeypatch):
        memory = tmp_path / "memory"
        memory.mkdir()
        for layer in doctor.MEMORY_LAYERS:
            (memory / f"{layer}.json").write_text('{"facts": []}', encoding="utf-8-sig")

        monkeypatch.setattr(doctor, "MEMORY_DIR", memory)
        assert doctor.check_memory()["status"] == "OK"

    def test_bom_encoded_project_manifest_is_parsed(self, tmp_path):
        import coresentinel_context as context
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"react": "18.0.0"}}), encoding="utf-8-sig")
        assert "React" in context.detect_frameworks(tmp_path)

    def test_genuinely_corrupt_file_is_still_reported(self, tmp_path):
        """The BOM fix must not swallow real corruption."""
        target = tmp_path / "broken.json"
        target.write_text("{ definitely not json", encoding="utf-8")

        data, error = doctor.read_json(target)
        assert data is None and error


class TestAdapterSyncSafety:
    def test_unmanaged_target_is_never_overwritten(self, tmp_path, capsys):
        import coresentinel_adapters as adapters
        original = "# hand-authored rules I care about\n"
        (tmp_path / "AGENTS.md").write_text(original, encoding="utf-8")

        assert adapters.sync_adapter("generic", "project", apply_changes=True,
                                     target_dir=str(tmp_path)) is False
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == original
        assert "BLOCKED" in capsys.readouterr().out

    def test_forced_overwrite_leaves_a_backup(self, tmp_path):
        import coresentinel_adapters as adapters
        original = "# hand-authored rules\n"
        (tmp_path / "AGENTS.md").write_text(original, encoding="utf-8")

        adapters.sync_adapter("generic", "project", apply_changes=True, force=True,
                              target_dir=str(tmp_path))

        backups = list(tmp_path.glob("*.coresentinel.bak"))
        assert backups, "forced overwrite destroyed the original with no backup"
        assert backups[0].read_text(encoding="utf-8") == original

    def test_dry_run_writes_nothing(self, tmp_path):
        import coresentinel_adapters as adapters
        adapters.sync_adapter("generic", "project", apply_changes=False, target_dir=str(tmp_path))
        assert not (tmp_path / "AGENTS.md").exists(), "a dry run created a file"

    def test_managed_file_is_updated_without_a_backup(self, tmp_path):
        import coresentinel_adapters as adapters
        adapters.sync_adapter("generic", "project", apply_changes=True, target_dir=str(tmp_path))
        adapters.sync_adapter("generic", "project", apply_changes=True, target_dir=str(tmp_path))

        assert adapters.MANAGED_MARKER in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert not list(tmp_path.glob("*.coresentinel.bak"))
