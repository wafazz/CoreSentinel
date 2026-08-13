"""Persistence port — one contract suite, run against every backend.

The point of the port is that business logic cannot tell the backends apart. So
the contract tests are parametrized over both, and a backend that diverges fails
here rather than in whatever service happens to depend on the difference.
"""

import json
import sqlite3

import pytest

from coresentinel_core.storage import BACKENDS, COLLECTIONS, JsonStore, SqliteStore
from coresentinel_core.storage import migrations
from coresentinel_core.storage.ports import Store
from coresentinel_core.runtime.errors import MigrationError, StorageError


@pytest.fixture(params=sorted(BACKENDS), ids=sorted(BACKENDS))
def store(request, tmp_path):
    """Every contract test runs once per backend."""
    built = BACKENDS[request.param](tmp_path)
    yield built
    built.close()


class TestPortContract:
    def test_every_collection_is_present(self, store):
        assert set(store.collections()) == set(COLLECTIONS)

    def test_append_returns_the_stored_record(self, store):
        stored = store.audit_events.append({"actor": "Iris", "action": "verify"})
        assert stored["actor"] == "Iris"
        assert stored["id"] and stored["recorded_at"]

    def test_a_supplied_id_is_kept(self, store):
        stored = store.audit_events.append({"id": "RUN-0001", "actor": "Iris"})
        assert stored["id"] == "RUN-0001"

    def test_a_record_round_trips_intact(self, store):
        payload = {"actor": "Iris", "nested": {"a": [1, 2]}, "score": 91}
        stored = store.verification_runs.append(payload)
        assert store.verification_runs.get(stored["id"])["nested"] == {"a": [1, 2]}

    def test_recent_returns_newest_first(self, store):
        for index in range(5):
            store.events.append({"event": f"E{index}"})
        assert [r["event"] for r in store.events.recent(3)] == ["E4", "E3", "E2"]

    def test_all_returns_oldest_first(self, store):
        for index in range(3):
            store.events.append({"event": f"E{index}"})
        assert [r["event"] for r in store.events.all()] == ["E0", "E1", "E2"]

    def test_count_tracks_appends(self, store):
        assert store.tasks.count() == 0
        store.tasks.append({"objective": "x"})
        assert store.tasks.count() == 1

    def test_a_missing_record_returns_none(self, store):
        assert store.tasks.get("nope") is None

    def test_clear_empties_the_collection(self, store):
        store.tasks.append({"objective": "x"})
        store.tasks.clear()
        assert store.tasks.count() == 0

    def test_collections_are_independent(self, store):
        store.tasks.append({"objective": "x"})
        assert store.events.count() == 0

    def test_a_non_dict_record_is_refused(self, store):
        with pytest.raises(StorageError):
            store.tasks.append(["not", "a", "record"])

    def test_describe_reports_backend_and_counts(self, store):
        store.tasks.append({"objective": "x"})
        detail = store.describe()
        assert detail["backend"] in BACKENDS
        assert detail["collections"]["tasks"] == 1

    def test_attribute_access_matches_the_repository_lookup(self, store):
        assert store.events is store.repository("events")

    def test_an_unknown_collection_is_refused(self, store):
        with pytest.raises(KeyError):
            store.repository("not_a_collection")

    def test_records_survive_reopening(self, store, tmp_path):
        store.audit_events.append({"actor": "Iris"})
        store.close()
        reopened = BACKENDS[store.backend](tmp_path)
        assert reopened.audit_events.count() == 1
        reopened.close()


class TestJsonBackendSpecifics:
    def test_a_corrupt_line_is_skipped_not_fatal(self, tmp_path):
        """A truncated tail must not make the whole audit trail unreadable."""
        store = JsonStore(tmp_path)
        store.audit_events.append({"actor": "Iris"})
        with open(store.audit_events.path, "a", encoding="utf-8") as f:
            f.write("{ this is not json\n")
        store.audit_events.append({"actor": "Atlas"})

        records = store.audit_events.all()
        assert [r["actor"] for r in records] == ["Iris", "Atlas"]
        assert store.audit_events.skipped == 1

    def test_skipped_lines_are_reported_by_describe(self, tmp_path):
        store = JsonStore(tmp_path)
        store.events.append({"event": "E"})
        with open(store.events.path, "a", encoding="utf-8") as f:
            f.write("garbage\n")
        store.events.all()
        assert store.describe()["skipped_lines"]["events"] == 1

    def test_records_are_one_json_object_per_line(self, tmp_path):
        store = JsonStore(tmp_path)
        store.events.append({"event": "A"})
        store.events.append({"event": "B"})
        lines = store.events.path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert all(json.loads(line) for line in lines)


class TestSqliteBackendSpecifics:
    def test_migrations_are_applied_on_open(self, tmp_path):
        store = SqliteStore(tmp_path)
        assert "0001" in store.describe()["schema"]
        store.close()

    def test_reopening_applies_nothing_further(self, tmp_path):
        SqliteStore(tmp_path).close()
        store = SqliteStore(tmp_path)
        assert store.applied == [], "a migration was applied twice"
        store.close()

    def test_projects_upsert_on_their_root(self, tmp_path):
        store = SqliteStore(tmp_path)
        store.projects.append({"root": "/repo", "name": "first"})
        store.projects.append({"root": "/repo", "name": "second"})
        assert store.projects.count() == 1
        assert store.projects.all()[0]["name"] == "second"
        store.close()

    def test_promoted_columns_are_queryable(self, tmp_path):
        store = SqliteStore(tmp_path)
        store.verification_runs.append({"verdict": "VERIFIED", "score": 91})
        found = store.connection.execute(
            "SELECT score FROM verification_runs WHERE verdict = ?", ("VERIFIED",)).fetchone()
        assert found[0] == 91
        store.close()

    def test_the_database_holds_no_memory_or_decisions(self, tmp_path):
        """ADR-001 is scoped, not reversed: human-facing knowledge stays in JSON."""
        store = SqliteStore(tmp_path)
        tables = {row[0] for row in store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert not tables & {"memories", "facts", "decisions", "journal", "patterns"}
        store.close()


class TestMigrationRunner:
    def test_discovery_is_ordered(self):
        found = migrations.discover()
        assert [m["version"] for m in found] == sorted(m["version"] for m in found)

    def test_a_gap_in_versions_is_refused(self, tmp_path):
        (tmp_path / "0001_a.sql").write_text("SELECT 1;", encoding="utf-8")
        (tmp_path / "0003_c.sql").write_text("SELECT 1;", encoding="utf-8")
        with pytest.raises(MigrationError):
            migrations.discover(tmp_path)

    def test_a_malformed_filename_is_refused(self, tmp_path):
        (tmp_path / "add-incidents.sql").write_text("SELECT 1;", encoding="utf-8")
        with pytest.raises(MigrationError):
            migrations.discover(tmp_path)

    def test_applying_twice_is_a_no_op(self, tmp_path):
        (tmp_path / "0001_a.sql").write_text(
            "CREATE TABLE IF NOT EXISTS t (id INTEGER);", encoding="utf-8")
        connection = sqlite3.connect(":memory:")
        assert len(migrations.migrate(connection, tmp_path)) == 1
        assert migrations.migrate(connection, tmp_path) == []
        connection.close()

    def test_editing_an_applied_migration_is_refused(self, tmp_path):
        path = tmp_path / "0001_a.sql"
        path.write_text("CREATE TABLE IF NOT EXISTS t (id INTEGER);", encoding="utf-8")
        connection = sqlite3.connect(":memory:")
        migrations.migrate(connection, tmp_path)

        path.write_text("CREATE TABLE IF NOT EXISTS t (id INTEGER, extra TEXT);", encoding="utf-8")
        with pytest.raises(MigrationError) as raised:
            migrations.migrate(connection, tmp_path)
        assert "changed after being applied" in str(raised.value)
        connection.close()

    def test_a_failing_migration_commits_nothing(self, tmp_path):
        (tmp_path / "0001_a.sql").write_text("CREATE TABLE t (id INTEGER);", encoding="utf-8")
        (tmp_path / "0002_b.sql").write_text("THIS IS NOT SQL;", encoding="utf-8")
        connection = sqlite3.connect(":memory:")
        with pytest.raises(MigrationError):
            migrations.migrate(connection, tmp_path)
        applied = migrations.applied(connection)
        assert "0002" not in applied
        connection.close()

    def test_each_applied_migration_is_recorded_with_a_checksum(self, tmp_path):
        (tmp_path / "0001_a.sql").write_text("CREATE TABLE t (id INTEGER);", encoding="utf-8")
        connection = sqlite3.connect(":memory:")
        migrations.migrate(connection, tmp_path)
        record = migrations.applied(connection)["0001"]
        assert record["checksum"].startswith("sha256:") and record["applied_at"]
        connection.close()

    def test_there_is_no_downgrade_path(self):
        """The reverse of a bad migration is a new migration, never an in-place rollback."""
        assert not hasattr(migrations, "rollback")
        assert not hasattr(migrations, "downgrade")


class TestBackendIndependence:
    def test_deleting_the_database_loses_no_memory_or_decisions(self, tmp_path, monkeypatch):
        """Acceptance criterion: the sqlite file holds nothing a human wrote."""
        import coresentinel_memory as mem

        memory_dir = tmp_path / "memory"
        memory_dir.mkdir()
        monkeypatch.setattr(mem, "MEMORY_DIR", memory_dir)
        monkeypatch.setattr(mem, "MEMORY_LAYERS",
                            {name: memory_dir / f"{name}.json" for name in mem.MEMORY_LAYERS})
        mem.add_fact("longterm", "PostgreSQL chosen for the ledger", 0.98, "ADR-001", str(tmp_path))
        mem.add_decision("Use PostgreSQL", "transactional consistency", "PostgreSQL")

        store = SqliteStore(tmp_path)
        store.audit_events.append({"actor": "Iris"})
        store.close()
        (tmp_path / "coresentinel.db").unlink()

        assert len(mem.layer_facts("longterm", str(tmp_path))) == 1
        assert json.loads(mem.MEMORY_LAYERS["decisions"].read_text(encoding="utf-8"))

    def test_both_backends_are_registered(self):
        assert set(BACKENDS) == {"json", "sqlite"}
        assert all(issubclass(cls, Store) for cls in BACKENDS.values())
