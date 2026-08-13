"""Decision intelligence — schema compatibility, scoping, contradiction, supersession."""

import json

import pytest

from coresentinel_core.decisions import schema, ledger, contradiction


V1_RECORD = {
    "id": "ADR-001",
    "decision": "Use PostgreSQL instead of MongoDB",
    "reason": "Transactional consistency required for the payment ledger",
    "alternatives": ["MongoDB", "MySQL"],
    "chosen": "PostgreSQL",
    "impact": "High",
    "status": "Accepted",
    "created_at": "2026-08-12 11:25:00",
}


@pytest.fixture
def core_only(tmp_path, monkeypatch):
    """An unbound directory: the ledger resolves to the Core store."""
    import coresentinel_memory as mem

    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    unbound = tmp_path / "loose"
    unbound.mkdir()
    return unbound


@pytest.fixture
def bound(core_only, tmp_path):
    """A bound project: the ledger resolves to the project store."""
    root = tmp_path / "shop"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "shop"}), encoding="utf-8")
    return root


class TestSchemaCompatibility:
    def test_a_v1_record_loads_unchanged(self):
        normalized = schema.normalize(V1_RECORD)
        for field, value in V1_RECORD.items():
            assert normalized[field] == value, f"v1 field '{field}' was altered"

    def test_a_v1_record_gains_the_new_fields_as_null(self):
        normalized = schema.normalize(V1_RECORD)
        for field in ["problem", "context", "evidence", "author", "agent", "confidence"]:
            assert normalized[field] is None, f"'{field}' was invented rather than left blank"

    def test_the_v1_title_field_is_preserved_and_aliased(self):
        normalized = schema.normalize(V1_RECORD)
        assert normalized["decision"] == V1_RECORD["decision"]
        assert normalized["title"] == V1_RECORD["decision"]

    def test_completeness_is_reported_not_enforced(self):
        report = schema.completeness(V1_RECORD)
        assert 0 < report["percent"] < 100
        assert "problem" in report["missing"]

    def test_a_thin_record_is_still_accepted(self):
        record = schema.build("Use SQLite", "Zero dependency", "SQLite")
        assert record["problem"] is None and record["status"] == schema.ACCEPTED

    def test_only_accepted_decisions_bind(self):
        assert schema.is_binding(schema.build("x", "y", "z", status=schema.ACCEPTED))
        for status in (schema.PROPOSED, schema.SUPERSEDED, schema.REJECTED):
            assert not schema.is_binding(schema.build("x", "y", "z", status=status))

    @pytest.mark.parametrize("value,expected", [
        ("MongoDB, MySQL", ["MongoDB", "MySQL"]),
        (["MongoDB"], ["MongoDB"]),
        (None, []),
        ("", []),
    ])
    def test_list_fields_accept_a_string_or_a_list(self, value, expected):
        assert schema.split_list(value) == expected


class TestScoping:
    def test_an_unbound_directory_writes_to_the_core(self, core_only):
        record = ledger.add(str(core_only), title="Core level", reason="r", chosen="c")
        assert record["scope"] == ledger.SCOPE_CORE
        assert ledger.ledger_path(str(core_only)) == ledger.core_path()

    def test_a_bound_project_writes_to_its_own_ledger(self, bound):
        record = ledger.add(str(bound), title="Project level", reason="r", chosen="c")
        assert record["scope"] == ledger.SCOPE_PROJECT
        assert ledger.ledger_path(str(bound)).is_relative_to(bound)

    def test_core_decisions_do_not_leak_into_a_bound_project(self, core_only, bound):
        """Regression, F-08 in a new guise: unioning the ledgers surfaced one
        repository's decisions as governance for another, and the noise trained
        users to skip the check."""
        ledger.add(str(core_only), title="Unrelated core decision", reason="r", chosen="Kafka")
        ledger.add(str(bound), title="Project decision", reason="r", chosen="Redis")

        visible = [r["title"] for r in ledger.load(str(bound))]
        assert visible == ["Project decision"]

    def test_the_core_ledger_can_still_be_asked_for_explicitly(self, core_only, bound):
        ledger.add(str(core_only), title="Core decision", reason="r", chosen="Kafka")
        ledger.add(str(bound), title="Project decision", reason="r", chosen="Redis")
        titles = [r["title"] for r in ledger.load(str(bound), include_core=True)]
        assert {"Core decision", "Project decision"} <= set(titles)

    def test_ids_never_collide_across_scopes(self, core_only, bound):
        core_record = ledger.add(str(core_only), title="Core", reason="r", chosen="c")
        project_record = ledger.add(str(bound), title="Project", reason="r", chosen="c")
        assert core_record["id"] != project_record["id"]

    def test_ids_are_sequential(self, bound):
        first = ledger.add(str(bound), title="One", reason="r", chosen="c")
        second = ledger.add(str(bound), title="Two", reason="r", chosen="c")
        assert int(second["id"].split("-")[1]) == int(first["id"].split("-")[1]) + 1

    def test_a_corrupt_ledger_is_never_overwritten(self, bound, capsys):
        path = ledger.ledger_path(str(bound))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")

        assert ledger.add(str(bound), title="x", reason="r", chosen="c") is None
        assert path.read_text(encoding="utf-8") == "{ not json"


class TestContradictionGuard:
    @pytest.fixture
    def redis_decision(self):
        return schema.build(
            "Use Redis for session storage",
            "MySQL connection saturation was observed under production load",
            "Redis", alternatives="Database sessions, Memcached",
            evidence="INC-1024", decision_id="ADR-042")

    def test_the_briefs_example_is_blocked_and_cites_the_decision(self, redis_decision):
        findings = contradiction.check(
            "I recommend switching from Redis to database sessions.", [redis_decision])
        assert findings[0]["verdict"] == contradiction.CONTRADICTS
        assert findings[0]["blocking"] is True
        assert findings[0]["decision_id"] == "ADR-042"
        assert "saturation" in findings[0]["reason"]
        assert findings[0]["evidence"] == "INC-1024"

    def test_ordinary_related_work_is_not_blocked(self, redis_decision):
        """A check that blocks normal work is a check people route around."""
        findings = contradiction.check(
            "Add Redis caching to the product listing endpoint", [redis_decision])
        assert findings and findings[0]["verdict"] == contradiction.TOUCHES
        assert not any(f["blocking"] for f in findings)

    def test_proposing_a_rejected_alternative_is_flagged(self, redis_decision):
        findings = contradiction.check("Let's use Memcached for sessions", [redis_decision])
        assert findings[0]["verdict"] == contradiction.REVISITS
        assert findings[0]["blocking"] is True

    def test_unrelated_work_produces_nothing(self, redis_decision):
        assert contradiction.check("Rename the invoice PDF template", [redis_decision]) == []

    def test_a_non_binding_decision_does_not_block(self, redis_decision):
        redis_decision["status"] = schema.SUPERSEDED
        assert contradiction.check("switch away from Redis", [redis_decision]) == []

    def test_generic_words_alone_never_trigger_a_finding(self):
        """Matching on 'database' or 'service' flags every sentence, which is the
        fastest way to make the check worthless."""
        generic = schema.build("Use a database", "because", "database", decision_id="ADR-001")
        assert contradiction.check("switch the service to a new system", [generic]) == []

    @pytest.mark.parametrize("phrase", [
        "switch from Redis", "replace Redis", "drop Redis", "stop using Redis",
        "migrate away from Redis", "Redis instead of nothing", "remove Redis",
    ])
    def test_reversal_wording_is_recognised(self, redis_decision, phrase):
        findings = contradiction.check(phrase, [redis_decision])
        assert any(f["blocking"] for f in findings), f"'{phrase}' was not recognised"

    def test_findings_are_ordered_most_severe_first(self, redis_decision):
        other = schema.build("Use Postgres", "ACID", "Postgres", decision_id="ADR-002")
        findings = contradiction.check("switch from Redis to Postgres", [redis_decision, other])
        verdicts = [f["verdict"] for f in findings]
        assert verdicts == sorted(verdicts, key=lambda v: {"CONTRADICTS": 0, "REVISITS": 1,
                                                           "TOUCHES": 2}[v])

    def test_verify_reports_a_clear_verdict_when_nothing_matches(self, bound):
        report = contradiction.verify("Rename a CSS class", str(bound))
        assert report["verdict"] == "CLEAR" and report["blocking"] == 0


class TestSupersession:
    def test_superseding_links_both_records(self, bound):
        old = ledger.add(str(bound), title="Use Redis", reason="r", chosen="Redis")
        new = ledger.add(str(bound), title="Use database sessions", reason="r", chosen="Postgres")

        report = ledger.supersede(old["id"], new["id"], str(bound), "Load profile changed")
        assert report["superseded"]["status"] == schema.SUPERSEDED
        assert report["superseded"]["superseded_by"] == new["id"]
        assert report["superseding"]["supersedes"] == old["id"]

    def test_a_superseded_decision_stops_binding(self, bound):
        old = ledger.add(str(bound), title="Use Redis", reason="r", chosen="Redis")
        new = ledger.add(str(bound), title="Use Postgres", reason="r", chosen="Postgres")
        ledger.supersede(old["id"], new["id"], str(bound))

        assert old["id"] not in [r["id"] for r in ledger.binding(str(bound))]

    def test_a_decision_cannot_supersede_itself(self, bound):
        record = ledger.add(str(bound), title="Use Redis", reason="r", chosen="Redis")
        assert "error" in ledger.supersede(record["id"], record["id"], str(bound))

    def test_superseding_an_unknown_decision_is_refused(self, bound):
        record = ledger.add(str(bound), title="Use Redis", reason="r", chosen="Redis")
        assert "error" in ledger.supersede("ADR-999", record["id"], str(bound))

    def test_the_reversal_stays_visible_after_supersession(self, bound):
        old = ledger.add(str(bound), title="Use Redis", reason="r", chosen="Redis")
        new = ledger.add(str(bound), title="Use Postgres", reason="r", chosen="Postgres")
        ledger.supersede(old["id"], new["id"], str(bound), "Load profile changed")

        stored = ledger.get(old["id"], str(bound))
        assert new["id"] in stored["related_decisions"]
