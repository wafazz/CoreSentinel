"""
A genuine v1 install, upgraded, with nothing lost.

The compatibility contract in Planning.md §6.6 promises that every v1 command,
memory file, ADR and project config keeps working. Eleven phases asserted pieces
of that in isolation; nothing had ever built a v1 install and driven it through
the upgrade.

So this constructs one the way `10.0.0` left it — six fact layers with no v2
fields, eight-field ADRs, a `RUN-#nnnn` audit trail, a config with no `settings`
key, no database and no record store — then runs the upgrade and asserts, field
by field, that the data that was there is still there and still says the same
thing.

The failure this guards against is not a crash. It is a migration that quietly
drops a field nobody was looking at.
"""

import json
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration

SANDBOX_GLOBS = ["*.py", "*.json", "*.md", "VERSION"]

# Exactly what 10.0.0 wrote: fact, confidence, classification, source and two
# timestamps. No id, no pinned, no transferable, no sources[], no base_confidence.
V1_FACTS = {
    "project": [
        {"fact": "the billing service runs on Python 3.9",
         "confidence": 0.97, "classification": "Known (Empirically Verified)",
         "source": "pyproject.toml", "created_at": "2025-11-02 09:14:00",
         "last_verified": "2025-11-02 09:14:00"},
        {"fact": "invoices are numbered per tenant, never globally",
         "confidence": 0.92, "classification": "Known (Empirically Verified)",
         "source": "billing/invoice.py", "created_at": "2025-11-04 16:40:00",
         "last_verified": "2026-01-08 11:02:00"},
    ],
    "longterm": [
        {"fact": "the payment provider rate-limits at 100 requests per minute",
         "confidence": 0.88, "classification": "Assumed (Inferred)",
         "source": "incident 2025-12-19", "created_at": "2025-12-19 22:31:00",
         "last_verified": "2025-12-19 22:31:00"},
    ],
    "failures": [
        {"fact": "retrying a charge without an idempotency key double-charged a customer",
         "confidence": 0.99, "classification": "Known (Empirically Verified)",
         "source": "post-mortem", "created_at": "2025-12-20 08:00:00",
         "last_verified": "2025-12-20 08:00:00"},
    ],
    "patterns": [
        {"fact": "scope every tenant query by tenant_id in the same clause as the filter",
         "confidence": 0.95, "classification": "Known (Empirically Verified)",
         "source": "review 2025-10-30", "created_at": "2025-10-30 13:20:00",
         "last_verified": "2025-10-30 13:20:00"},
    ],
    "session": [],
    "working": [],
}

# The v1 ADR shape: eight fields, and nothing else.
V1_DECISIONS = [
    {"id": "ADR-001", "decision": "File-based JSON layered memory",
     "reason": "zero external dependencies; portable across IDEs",
     "chosen": "JSON files on disk",
     "alternatives": ["SQLite", "PostgreSQL", "Redis"],
     "status": "Accepted", "created_at": "2025-09-01 10:00:00",
     "author": "Fakrul"},
    {"id": "ADR-002", "decision": "Charge idempotency keys are mandatory",
     "reason": "a retried charge double-billed a customer in December",
     "chosen": "require an Idempotency-Key header on every charge",
     "alternatives": ["client-side dedupe", "nothing"],
     "status": "Accepted", "created_at": "2025-12-21 09:30:00",
     "author": "Fakrul"},
]

V1_AUDIT_TRAIL = [
    {"run_id": "RUN-#4821", "agent": "Backend Engineer", "task": "add idempotency keys",
     "timestamp": "2025-12-21 10:15:00", "result": "PASS",
     "actions": {"files_modified": 3, "tests_executed": 41}},
    {"run_id": "RUN-#9102", "agent": "Security", "task": "audit the charge path",
     "timestamp": "2026-01-05 14:02:00", "result": "PASS",
     "actions": {"files_read": 12}},
]


@pytest.fixture(scope="module")
def v1_install(tmp_path_factory):
    """A CoreSentinel 10.0.0 install and a project bound by it, before upgrade."""
    from pathlib import Path

    root = tmp_path_factory.mktemp("v1")
    core_dir = Path(__file__).resolve().parent.parent.parent

    core = root / "core"
    core.mkdir()
    for pattern in SANDBOX_GLOBS:
        for src in core_dir.glob(pattern):
            shutil.copy2(src, core / src.name)
    shutil.copytree(core_dir / "coresentinel_core", core / "coresentinel_core",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # --- Core memory, as v1 wrote it ---------------------------------------
    memory = core / "memory"
    memory.mkdir()
    for layer in ("longterm", "failures", "patterns"):
        (memory / f"{layer}.json").write_text(
            json.dumps({"facts": V1_FACTS[layer]}, indent=2), encoding="utf-8")
    (memory / "decisions.json").write_text(
        json.dumps(V1_DECISIONS, indent=2), encoding="utf-8")
    (memory / "audit_trail.json").write_text(
        json.dumps(V1_AUDIT_TRAIL, indent=2), encoding="utf-8")
    for layer in ("working", "session", "project"):
        (memory / f"{layer}.json").write_text(
            json.dumps({"facts": V1_FACTS[layer]}, indent=2), encoding="utf-8")

    # --- a bound project, v1 style: no "settings", no config_version --------
    project = root / "billing"
    (project / ".coresentinel" / "memory").mkdir(parents=True)
    (project / ".coresentinel" / "config.json").write_text(json.dumps({
        "project_name": "billing",
        "core_dir": str(core),
        "initialized_at": "2025-11-02 09:00:00",
        "stack": ["Python"],
        "frameworks": [],
        "test_runner": "pytest",
        "verification": {"command": "coresentinel verify", "pass_threshold": 80},
        "bound_hosts": [],
    }, indent=2), encoding="utf-8")
    for layer in ("working", "session", "project"):
        (project / ".coresentinel" / "memory" / f"{layer}.json").write_text(
            json.dumps({"facts": V1_FACTS[layer]}, indent=2), encoding="utf-8")
    (project / ".coresentinel" / "memory" / "project.json").write_text(
        json.dumps({"facts": V1_FACTS["project"]}, indent=2), encoding="utf-8")
    (project / "pyproject.toml").write_text("[project]\nname='billing'\n", encoding="utf-8")

    assert not (core / "coresentinel.db").exists()
    assert not (core / "records").exists()

    return {"root": root, "core": core, "project": project}


@pytest.fixture(scope="module")
def upgraded(v1_install):
    """Run the upgrade. Returns the install plus the migrate result."""
    result = subprocess.run(
        [sys.executable, str(v1_install["core"] / "coresentinel.py"), "migrate", "--json"],
        cwd=str(v1_install["project"]), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300)
    return {**v1_install, "migrate": result}


def run(install, *argv):
    return subprocess.run(
        [sys.executable, str(install["core"] / "coresentinel.py"), *argv],
        cwd=str(install["project"]), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300)


class TestTheUpgradeSucceeds:
    def test_migrate_exits_cleanly_on_a_v1_install(self, upgraded):
        assert upgraded["migrate"].returncode == 0, upgraded["migrate"].stderr[-500:]

    def test_migrate_emits_a_machine_readable_result(self, upgraded):
        payload = json.loads(upgraded["migrate"].stdout)
        assert payload["backend"] in {"json", "sqlite"}


class TestNoFactWasLost:
    def test_every_v1_fact_still_loads(self, upgraded):
        """Field by field, not merely by count."""
        stored = json.loads(
            (upgraded["core"] / "memory" / "longterm.json").read_text(encoding="utf-8"))
        facts = {f["fact"]: f for f in stored["facts"]}

        for original in V1_FACTS["longterm"]:
            assert original["fact"] in facts, f"lost: {original['fact']}"
            kept = facts[original["fact"]]
            for field, value in original.items():
                assert kept[field] == value, (
                    f"'{field}' changed on upgrade: {value!r} -> {kept[field]!r}")

    def test_the_project_scoped_layer_is_untouched(self, upgraded):
        stored = json.loads((upgraded["project"] / ".coresentinel" / "memory" /
                             "project.json").read_text(encoding="utf-8"))
        assert [f["fact"] for f in stored["facts"]] == \
               [f["fact"] for f in V1_FACTS["project"]]

    def test_recall_finds_a_v1_fact_after_the_upgrade(self, upgraded):
        result = run(upgraded, "recall", "idempotency", "--json")
        assert result.returncode == 0, result.stderr[-400:]
        assert "double-charged" in result.stdout

    def test_the_failures_layer_survived(self, upgraded):
        """Failures are exempt from decay and are the most costly to lose."""
        stored = json.loads(
            (upgraded["core"] / "memory" / "failures.json").read_text(encoding="utf-8"))
        assert len(stored["facts"]) == len(V1_FACTS["failures"])


class TestNoDecisionWasLost:
    def test_every_v1_adr_still_renders(self, upgraded):
        """Read with --core, because a v1 install recorded them at Core scope."""
        result = run(upgraded, "decision", "list", "--core", "--json")
        assert result.returncode == 0, result.stderr[-400:]
        rendered = result.stdout
        for original in V1_DECISIONS:
            assert original["id"] in rendered
            assert original["chosen"] in rendered

    def test_core_decisions_are_invisible_from_a_bound_project_by_default(self, upgraded):
        """The upgrade's sharpest edge, pinned so the migration guide stays true.

        Nothing is lost — the file is untouched — but a v1 install recorded
        every decision at Core scope, and a bound project reads its own ledger
        alone. That default is deliberate (unioning them made one repository's
        decisions look like governance for another), so the upgrade note is
        `decision list --core`, not a change to the default.
        """
        default = run(upgraded, "decision", "list", "--json")
        assert json.loads(default.stdout)["count"] == 0

        explicit = run(upgraded, "decision", "list", "--core", "--json")
        assert json.loads(explicit.stdout)["count"] >= len(V1_DECISIONS)

    def test_the_eight_v1_fields_keep_their_values(self, upgraded):
        stored = json.loads(
            (upgraded["core"] / "memory" / "decisions.json").read_text(encoding="utf-8"))
        by_id = {d["id"]: d for d in (stored if isinstance(stored, list)
                                      else stored.get("decisions", []))}

        for original in V1_DECISIONS:
            kept = by_id[original["id"]]
            for field, value in original.items():
                assert kept[field] == value, (
                    f"{original['id']}.{field} changed: {value!r} -> {kept[field]!r}")

    def test_added_fields_are_null_rather_than_invented(self, upgraded):
        """A backfill that guesses a value is worse than one that admits nothing."""
        result = run(upgraded, "migrate", "decisions", "--json")
        assert result.returncode == 0, result.stderr[-400:]

        stored = json.loads(
            (upgraded["core"] / "memory" / "decisions.json").read_text(encoding="utf-8"))
        records = stored if isinstance(stored, list) else stored.get("decisions", [])
        for record in records:
            for field in ("problem", "context", "evidence"):
                if field in record:
                    assert record[field] in (None, "", []), (
                        f"{record['id']}.{field} was invented as {record[field]!r}")

    def test_the_contradiction_guard_works_against_a_v1_decision(self, upgraded, tmp_path):
        """ADR-002 was recorded by v1. The v2 guard must still enforce it.

        Checked at Core scope — where a v1 install's decisions live — by running
        from a directory that is not inside a bound project.
        """
        result = subprocess.run(
            [sys.executable, str(upgraded["core"] / "coresentinel.py"), "decision", "verify",
             "--change", "drop the idempotency key requirement on charges"],
            cwd=str(tmp_path), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300)

        assert result.returncode == 1, (
            f"contradicting a v1 decision exited {result.returncode}\n{result.stdout[-600:]}")
        assert "ADR-002" in result.stdout
        assert "idempotency" in result.stdout.lower()


class TestTheV1AuditTrailIsHonest:
    def test_v1_records_are_kept(self, upgraded):
        trail = upgraded["core"] / "memory" / "audit_trail.json"
        assert trail.is_file(), "the v1 audit trail was deleted by the upgrade"
        assert len(json.loads(trail.read_text(encoding="utf-8"))) == len(V1_AUDIT_TRAIL)

    def test_v1_records_are_not_retro_signed(self, upgraded):
        """Hashing them now would assert an integrity that never existed."""
        for record in json.loads(
                (upgraded["core"] / "memory" / "audit_trail.json").read_text(encoding="utf-8")):
            assert "hash" not in record or record.get("hash") is None

    def test_the_new_chain_verifies_after_the_upgrade(self, upgraded):
        result = run(upgraded, "audit", "verify", "--json")
        assert result.returncode == 0, result.stderr[-400:]
        assert json.loads(result.stdout)["verdict"] == "INTACT"


class TestTheV1ProjectConfigStillResolves:
    def test_a_config_without_a_settings_key_still_binds(self, upgraded):
        result = run(upgraded, "config", "get", "storage.backend", "--json")
        assert result.returncode == 0, result.stderr[-400:]

    def test_the_v1_binding_fields_are_preserved(self, upgraded):
        config = json.loads((upgraded["project"] / ".coresentinel" /
                             "config.json").read_text(encoding="utf-8"))
        assert config["project_name"] == "billing"
        assert config["verification"]["pass_threshold"] == 80

    def test_the_project_is_still_recognised_as_bound(self, upgraded):
        result = run(upgraded, "status", "--json")
        assert result.returncode == 0
        assert "billing" in result.stdout


class TestTheUpgradedInstallWorks:
    def test_doctor_is_not_critical_on_an_upgraded_install(self, upgraded):
        result = run(upgraded, "doctor", "--json")
        payload = json.loads(result.stdout)
        failed = [c["check"] for c in payload["checks"] if c["status"] == "FAIL"]
        assert not failed, f"upgrading a v1 install broke: {failed}"

    def test_deleting_the_database_loses_no_memory_or_decisions(self, upgraded):
        """The claim ADR-001's split rests on, tested against real v1 data."""
        database = upgraded["core"] / "coresentinel.db"
        if database.exists():
            database.unlink()

        result = run(upgraded, "recall", "idempotency", "--json")
        assert result.returncode == 0
        assert "double-charged" in result.stdout

        stored = json.loads(
            (upgraded["core"] / "memory" / "decisions.json").read_text(encoding="utf-8"))
        records = stored if isinstance(stored, list) else stored.get("decisions", [])
        assert {d["id"] for d in records} >= {"ADR-001", "ADR-002"}
