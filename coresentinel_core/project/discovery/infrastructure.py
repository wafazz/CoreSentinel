"""
Database, container, CI and environment detection.

The database is the fact v1 never recorded at all, and the one an agent is most
likely to guess wrong. Three independent sources are read, strongest first: a
compose service image states what actually runs, an environment key states what
the application is configured to talk to, and a driver dependency states only
what it *can* talk to.
"""

import re
from pathlib import Path

from coresentinel_core.project.discovery.base import (
    finding, read_text, node_dependencies, php_dependencies,
    python_dependencies, go_dependencies, rust_dependencies)

# Image name fragment -> engine. Matched against the image reference only, so a
# service merely *named* "db" proves nothing.
IMAGE_ENGINES = [
    ("postgres", "PostgreSQL"), ("postgis", "PostgreSQL"), ("timescale", "PostgreSQL"),
    ("mariadb", "MariaDB"), ("mysql", "MySQL"), ("percona", "MySQL"),
    ("mongo", "MongoDB"), ("redis", "Redis"), ("valkey", "Valkey"),
    ("memcached", "Memcached"), ("elasticsearch", "Elasticsearch"),
    ("opensearch", "OpenSearch"), ("clickhouse", "ClickHouse"),
    ("cassandra", "Cassandra"), ("rabbitmq", "RabbitMQ"), ("kafka", "Kafka"),
    ("minio", "MinIO"), ("mssql", "SQL Server"), ("sqlserver", "SQL Server"),
]

# Driver package -> engine it can reach. Weaker evidence: a driver proves
# capability, not use, so these are recorded at lower confidence.
DRIVER_ENGINES = {
    "pg": "PostgreSQL", "postgres": "PostgreSQL", "psycopg2": "PostgreSQL",
    "psycopg2-binary": "PostgreSQL", "psycopg": "PostgreSQL", "asyncpg": "PostgreSQL",
    "mysql2": "MySQL", "mysqlclient": "MySQL", "pymysql": "MySQL",
    "mongoose": "MongoDB", "pymongo": "MongoDB", "mongodb": "MongoDB",
    "redis": "Redis", "ioredis": "Redis", "predis/predis": "Redis",
    "sqlite3": "SQLite", "better-sqlite3": "SQLite",
    "elasticsearch": "Elasticsearch", "@elastic/elasticsearch": "Elasticsearch",
}

ENV_DB_KEYS = ["DB_CONNECTION", "DATABASE_URL", "DB_DRIVER", "DATABASE_ENGINE",
               "DB_TYPE", "SQL_ENGINE"]

ENV_VALUE_ENGINES = [
    ("postgres", "PostgreSQL"), ("pgsql", "PostgreSQL"),
    ("mariadb", "MariaDB"), ("mysql", "MySQL"),
    ("sqlite", "SQLite"), ("mongodb", "MongoDB"), ("sqlsrv", "SQL Server"),
]

COMPOSE_FILES = ["docker-compose.yml", "docker-compose.yaml",
                 "compose.yml", "compose.yaml"]

CONTAINER_MARKERS = [
    ("Dockerfile", "Dockerfile"),
    ("Containerfile", "Containerfile"),
    (".dockerignore", ".dockerignore"),
]

CI_MARKERS = [
    (".github/workflows", "GitHub Actions"),
    (".gitlab-ci.yml", "GitLab CI"),
    ("Jenkinsfile", "Jenkins"),
    (".circleci/config.yml", "CircleCI"),
    ("azure-pipelines.yml", "Azure Pipelines"),
    ("bitbucket-pipelines.yml", "Bitbucket Pipelines"),
    (".drone.yml", "Drone"),
    ("appveyor.yml", "AppVeyor"),
]

IMAGE_LINE = re.compile(r"^\s*image:\s*['\"]?([^'\"\s]+)", re.M)
ENV_LINE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=(.*)$", re.M)


def _compose_path(root):
    return next((Path(root) / name for name in COMPOSE_FILES
                 if (Path(root) / name).exists()), None)


def detect_databases(root):
    root = Path(root)
    found, seen = [], set()

    compose = _compose_path(root)
    if compose:
        for match in IMAGE_LINE.finditer(read_text(compose)):
            image = match.group(1).lower()
            for fragment, engine in IMAGE_ENGINES:
                if fragment in image and engine not in seen:
                    seen.add(engine)
                    found.append(finding("datastore", engine, compose.name,
                                         locator=f"service image '{match.group(1)}'",
                                         confidence=0.97))

    for env_name in (".env.example", ".env.sample", ".env.dist", ".env"):
        path = root / env_name
        if not path.exists():
            continue
        for match in ENV_LINE.finditer(read_text(path)):
            key, value = match.group(1), match.group(2).strip().strip("'\"").lower()
            if key not in ENV_DB_KEYS or not value:
                continue
            for fragment, engine in ENV_VALUE_ENGINES:
                if value.startswith(fragment) or value == fragment:
                    if engine not in seen:
                        seen.add(engine)
                        found.append(finding("datastore", engine, env_name,
                                             locator=key, confidence=0.9))
                    break

    dependencies = {}
    dependencies.update(node_dependencies(root))
    dependencies.update(php_dependencies(root))
    dependencies.update(python_dependencies(root))
    dependencies.update(go_dependencies(root))
    dependencies.update(rust_dependencies(root))
    for package, meta in dependencies.items():
        engine = DRIVER_ENGINES.get(package)
        # A driver proves the project *can* reach an engine, not that it does —
        # so it is only reported when nothing stronger already said so.
        if engine and engine not in seen:
            seen.add(engine)
            found.append(finding("datastore", engine, meta.get("section", "dependencies"),
                                 locator=f"driver '{package}'",
                                 detail="driver present; not proof it is in use",
                                 confidence=0.6))
    return found


def detect_containers(root):
    root = Path(root)
    found = [finding("container", label, name, locator="file present", confidence=0.98)
             for name, label in CONTAINER_MARKERS if (root / name).exists()]

    compose = _compose_path(root)
    if compose:
        services = len(IMAGE_LINE.findall(read_text(compose)))
        found.append(finding("container", "Docker Compose", compose.name,
                             locator="compose file", detail=f"{services} service image(s)",
                             confidence=0.98))

    if (root / "k8s").is_dir() or (root / "kubernetes").is_dir():
        found.append(finding("container", "Kubernetes manifests", "k8s/",
                             locator="directory present", confidence=0.8))
    return found


def detect_ci(root):
    root = Path(root)
    found = []
    for marker, label in CI_MARKERS:
        path = root / marker
        if not path.exists():
            continue
        detail = None
        if path.is_dir():
            workflows = sorted(path.glob("*.y*ml"))
            if not workflows:
                continue
            detail = f"{len(workflows)} workflow(s): " + ", ".join(w.name for w in workflows[:4])
        found.append(finding("ci", label, marker, locator="configuration present",
                             detail=detail, confidence=0.98))
    return found


def detect_environment(root):
    """Configuration *keys* only.

    The values are the secrets this product exists to keep out of places they do
    not belong, so nothing here reads past the '='.
    """
    root = Path(root)
    found = []
    for name in (".env.example", ".env.sample", ".env.dist"):
        path = root / name
        if not path.exists():
            continue
        keys = [match.group(1) for match in ENV_LINE.finditer(read_text(path))]
        found.append(finding("environment", f"{len(keys)} configuration key(s)", name,
                             locator="key names only, values never read",
                             detail=", ".join(keys[:8]) + (" …" if len(keys) > 8 else ""),
                             confidence=0.98))

    if (root / ".env").exists() and not (root / ".gitignore").exists():
        found.append(finding("environment", ".env present with no .gitignore", ".env",
                             locator="file present",
                             detail="secrets may be committed", confidence=0.9))
    return found
