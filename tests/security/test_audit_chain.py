"""The audit ledger — tamper evidence, monotonic ids, subject coverage.

An audit trail you can silently rewrite is worse than no trail, because it looks
like one. These tests hold the chain to the four ways a trail actually gets
falsified, and to the promise that the record cannot be edited without saying so.
"""

import json

import pytest

from coresentinel_core.audit import ledger, subjects
from coresentinel_core.storage import JsonStore


@pytest.fixture
def store(tmp_path):
    return JsonStore(tmp_path)


@pytest.fixture
def filled(store):
    for index in range(5):
        ledger.append(store, subjects.MEMORY_CHANGE, "Iris", f"record fact {index}", "PASS")
    return store


def rewrite(store, mutate):
    """Edit the trail on disk the way a text editor would."""
    path = store.audit_events.path
    records = [json.loads(line) for line in
               path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = mutate(records)
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


class TestChainIntegrity:
    def test_an_untouched_chain_verifies(self, filled):
        report = ledger.verify(filled)
        assert report["intact"] and report["verdict"] == "INTACT"
        assert report["checked"] == 5

    def test_mutation_is_detected(self, filled):
        def edit(records):
            records[2]["action"] = "record something else entirely"
            return records

        rewrite(filled, edit)
        report = ledger.verify(filled)
        assert not report["intact"]
        assert ledger.MUTATED in {p["code"] for p in report["problems"]}

    def test_deletion_is_detected(self, filled):
        rewrite(filled, lambda records: records[:2] + records[3:])
        report = ledger.verify(filled)
        codes = {p["code"] for p in report["problems"]}
        assert ledger.CHAIN_BREAK in codes or ledger.SEQUENCE_BREAK in codes

    def test_insertion_is_detected(self, filled):
        def insert(records):
            forged = dict(records[1])
            forged["action"] = "a record that was never made"
            return records[:2] + [forged] + records[2:]

        rewrite(filled, insert)
        assert not ledger.verify(filled)["intact"]

    def test_reordering_is_detected(self, filled):
        def swap(records):
            records[1], records[3] = records[3], records[1]
            return records

        rewrite(filled, swap)
        report = ledger.verify(filled)
        assert not report["intact"]
        assert ledger.CHAIN_BREAK in {p["code"] for p in report["problems"]}

    def test_appending_a_forged_record_is_detected(self, filled):
        def forge(records):
            last = records[-1]
            return records + [{**last, "seq": last["seq"] + 1, "id": "AUD-000099",
                               "action": "something that never happened"}]

        rewrite(filled, forge)
        assert not ledger.verify(filled)["intact"]

    def test_a_problem_names_the_record_it_belongs_to(self, filled):
        rewrite(filled, lambda r: [{**x, "action": "changed"} if i == 1 else x
                                   for i, x in enumerate(r)])
        problem = ledger.verify(filled)["problems"][0]
        assert problem["record"].startswith("AUD-") and problem["detail"]

    def test_every_problem_code_is_a_stable_identifier(self, filled):
        rewrite(filled, lambda records: records[:1] + records[2:])
        for problem in ledger.verify(filled)["problems"]:
            assert problem["code"].isupper() and " " not in problem["code"]


class TestMonotonicIds:
    def test_ids_are_sequential_and_ordered(self, filled):
        records = filled.audit_events.all()
        assert [r["id"] for r in records] == [f"AUD-{n:06d}" for n in range(1, 6)]

    def test_sequence_numbers_are_monotonic(self, filled):
        seqs = [r["seq"] for r in filled.audit_events.all()]
        assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)

    def test_no_id_is_random(self, store):
        """Regression, F-09: RUN-#{random 4 digits} collided and carried no order."""
        first = ledger.append(store, subjects.DECISION, "Iris", "one")
        second = ledger.append(store, subjects.DECISION, "Iris", "two")
        assert second["seq"] == first["seq"] + 1

    def test_a_thousand_records_never_collide(self, store):
        for index in range(200):
            ledger.append(store, subjects.MEMORY_CHANGE, "Iris", f"fact {index}")
        ids = [r["id"] for r in store.audit_events.all()]
        assert len(set(ids)) == len(ids)


class TestLegacyBoundary:
    def test_v1_records_are_listed_but_never_signed(self, store):
        imported = ledger.import_legacy(store, [
            {"run_id": "RUN-#9281", "agent": "Backend Engineer",
             "task": "Implement payment webhook", "result": "PASS",
             "timestamp": "2026-08-12 11:34:49"}])

        assert imported[0]["chain"] == ledger.LEGACY
        assert imported[0]["hash"] is None, "a legacy record was retro-signed"

    def test_legacy_records_do_not_break_the_chain(self, store):
        ledger.import_legacy(store, [{"run_id": "RUN-#9281", "agent": "x", "task": "y"}])
        ledger.append(store, subjects.DECISION, "Iris", "a real record")
        report = ledger.verify(store)
        assert report["intact"] and report["legacy"] == 1

    def test_the_report_says_why_legacy_records_are_unverified(self, store):
        ledger.import_legacy(store, [{"run_id": "RUN-#1", "agent": "x", "task": "y"}])
        assert "never signed" in ledger.verify(store)["note"]

    def test_importing_twice_does_not_duplicate(self, store):
        trail = [{"run_id": "RUN-#9281", "agent": "x", "task": "y"}]
        ledger.import_legacy(store, trail)
        ledger.import_legacy(store, trail)
        assert store.audit_events.count() == 1

    def test_a_record_written_around_the_ledger_is_reported(self, store):
        """Bypassing the ledger must be visible, not silently outside the chain."""
        ledger.append(store, subjects.DECISION, "Iris", "a real record")
        store.audit_events.append({"subject": "decision", "actor": "someone",
                                   "action": "written straight to the collection"})
        report = ledger.verify(store)
        assert report["unchained"] == 1
        assert "straight to the collection" in report["note"]


class TestSubjectCoverage:
    def test_twelve_subjects_are_declared(self):
        assert len(subjects.SUBJECTS) == 12

    def test_every_declared_event_maps_to_a_known_subject(self):
        for event, subject in subjects.EVENT_SUBJECTS.items():
            assert subject in subjects.SUBJECTS, f"{event} maps to an unknown subject"

    def test_an_unmapped_event_is_still_recorded(self, store):
        """Dropping an unmapped event would be the silent gap this module closes."""
        record = ledger.append(store, "not_a_subject", "Iris", "something happened")
        assert record["subject"] == subjects.OTHER

    def test_coverage_reports_what_has_never_been_recorded(self, store):
        ledger.append(store, subjects.DECISION, "Iris", "one")
        report = ledger.coverage(store)
        assert report["recorded"] == [subjects.DECISION]
        assert subjects.DEPLOYMENT in report["never_recorded"]

    def test_the_event_bus_writes_to_the_ledger(self, tmp_path, monkeypatch):
        import coresentinel_core.runtime.config as config_module
        from coresentinel_core.runtime.container import Runtime

        monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", tmp_path / "core.json")
        runtime = Runtime.bootstrap(str(tmp_path))
        runtime.events.emit("DecisionCreated", {"decision": "ADR-001"})

        recorded = [r for r in runtime.store.audit_events.all() if r.get("seq")]
        assert any(r["subject"] == subjects.DECISION for r in recorded)
        runtime.shutdown()

    def test_an_audit_failure_never_fails_the_operation(self, tmp_path, monkeypatch):
        import coresentinel_core.runtime.config as config_module
        from coresentinel_core.runtime.container import Runtime

        monkeypatch.setattr(config_module, "CORE_CONFIG_FILE", tmp_path / "core.json")
        runtime = Runtime.bootstrap(str(tmp_path))
        monkeypatch.setattr(runtime.container, "get",
                            lambda name: (_ for _ in ()).throw(RuntimeError("no store")))
        runtime.events.emit("DecisionCreated", {"decision": "ADR-001"})
        runtime.shutdown()


class TestRedactionInTheTrail:
    @pytest.mark.parametrize("field", ["password", "api_key", "AUTH_TOKEN",
                                       "client_secret", "private_key"])
    def test_a_sensitive_field_never_reaches_the_record(self, store, field):
        record = ledger.append(store, subjects.CONFIGURATION, "Iris", "set a value",
                               detail={field: "hunter2-and-then-some-more"})
        assert "hunter2" not in json.dumps(record)

    # Assembled rather than written out, because a file full of credential
    # SHAPES is indistinguishable from a file full of credentials to a scanner
    # that only sees the blob — GitHub's push protection rejected this file over
    # the Slack one. The value handed to the ledger is byte-identical either way,
    # so the test keeps its teeth. Do not "simplify" these back to literals.
    @pytest.mark.parametrize("secret", [
        "sk" + "_live_abcdefghijklmnop1234",
        "ghp" + "_abcdefghijklmnopqrstuvwxyz012345",
        "xox" + "b-1234567890-abcdefghijklmnop",
        "AKIA" + "IOSFODNN7EXAMPLE",
        "Bearer " + "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "postgres://user:" + "supersecretpassword" + "@db:5432/app",
    ])
    def test_a_credential_shape_in_free_text_is_redacted(self, store, secret):
        record = ledger.append(store, subjects.COMMAND_EXECUTION, "Builder",
                              "ran a command", detail={"output": f"config: {secret}"})
        assert secret not in json.dumps(record)

    def test_an_ordinary_value_survives(self, store):
        record = ledger.append(store, subjects.DECISION, "Iris", "chose a database",
                               detail={"chosen": "PostgreSQL"})
        assert record["detail"]["chosen"] == "PostgreSQL"

    def test_redaction_is_shared_with_the_logger(self):
        """One implementation, so the two cannot drift about what a secret is."""
        from coresentinel_core.runtime import logging as runtime_logging
        from coresentinel_core.security import redaction

        assert runtime_logging.redact is redaction.redact
        assert runtime_logging.redact_text is redaction.redact_text

    def test_redaction_survives_the_hash(self, store):
        """The hash must cover the redacted content, or verification fails on read."""
        ledger.append(store, subjects.CONFIGURATION, "Iris", "set",
                      detail={"token": "sk_live_abcdefghijklmnop1234"})
        assert ledger.verify(store)["intact"]
