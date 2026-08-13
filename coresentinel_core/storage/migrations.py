"""
Forward-only schema migrations.

Rules, each of which exists because the alternative corrupts a database quietly:

  * Migrations apply in numeric order, and a gap is an error rather than a skip.
  * Each is recorded in `schema_migrations` with a checksum of its text. Editing
    a migration that has already run is refused — the database and the file would
    silently disagree from then on.
  * Applying is idempotent: a migration already recorded is not re-run, and the
    SQL itself uses IF NOT EXISTS so a half-applied file completes cleanly.
  * There is no `down`. Rolling a schema backward in place is how data is lost;
    the reverse of a bad migration is a new migration.
"""

import re
import hashlib
from pathlib import Path

from coresentinel_core.runtime.errors import MigrationError

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
FILENAME_PATTERN = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")

LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    applied_at  TEXT NOT NULL
);
"""


def checksum(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def discover(directory=None):
    """Every migration on disk, in order. Raises on a gap or a malformed name."""
    directory = Path(directory or MIGRATIONS_DIR)
    if not directory.exists():
        return []

    found = []
    for path in sorted(directory.glob("*.sql")):
        match = FILENAME_PATTERN.match(path.name)
        if not match:
            raise MigrationError(f"migration '{path.name}' is not named NNNN_lower_snake.sql",
                                 "Rename it, for example 0002_add_incidents.sql")
        text = path.read_text(encoding="utf-8-sig")
        found.append({"version": match.group(1), "name": match.group(2),
                      "path": path, "sql": text, "checksum": checksum(text)})

    for index, migration in enumerate(found, start=1):
        if int(migration["version"]) != index:
            raise MigrationError(
                f"migration versions must be contiguous from 0001; "
                f"expected {index:04d}, found {migration['version']}",
                "Renumber the migrations so none is missing")
    return found


def applied(connection):
    connection.executescript(LEDGER_SQL)
    rows = connection.execute(
        "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version").fetchall()
    return {row[0]: {"version": row[0], "name": row[1], "checksum": row[2], "applied_at": row[3]}
            for row in rows}


def pending(connection, directory=None):
    done = applied(connection)
    return [m for m in discover(directory) if m["version"] not in done]


def verify(connection, directory=None):
    """Refuse to run against a database whose recorded migrations no longer match disk."""
    done = applied(connection)
    problems = []
    for migration in discover(directory):
        record = done.get(migration["version"])
        if record and record["checksum"] != migration["checksum"]:
            problems.append(
                f"{migration['version']}_{migration['name']}.sql changed after being applied "
                f"({record['checksum']} recorded, {migration['checksum']} on disk)")
    return problems


def migrate(connection, directory=None, now=None):
    """Apply every pending migration. Returns the list applied, newest last."""
    from coresentinel_core.storage.ports import now as timestamp

    problems = verify(connection, directory)
    if problems:
        raise MigrationError("; ".join(problems),
                             "An applied migration must never be edited — add a new one instead")

    performed = []
    for migration in pending(connection, directory):
        try:
            connection.executescript(migration["sql"])
            connection.execute(
                "INSERT INTO schema_migrations (version, name, checksum, applied_at) "
                "VALUES (?, ?, ?, ?)",
                (migration["version"], migration["name"], migration["checksum"],
                 now or timestamp()))
            connection.commit()
        except Exception as e:
            connection.rollback()
            raise MigrationError(
                f"migration {migration['version']}_{migration['name']} failed: {e}",
                "Fix the migration and re-run 'coresentinel migrate'; nothing was committed")
        performed.append({k: migration[k] for k in ("version", "name", "checksum")})
    return performed
