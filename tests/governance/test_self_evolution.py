"""Controlled Self-Evolution — proposals must be evidence-backed and human-approved."""

import json

import pytest


@pytest.fixture
def evolve(tmp_path, monkeypatch):
    import coresentinel_evolve as engine

    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    monkeypatch.setattr(engine, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(engine, "EVOLUTION_FILE", memory_dir / "evolution_proposals.json")
    return engine


class TestProposalPipeline:
    def test_new_proposal_is_never_auto_approved(self, evolve):
        """The entire point of CSE: an agent cannot approve its own rule change."""
        evolve.propose_evolution("anti-patterns.json", "Add rule", "Incident RUN-#1")

        proposal = evolve.load_proposals()[0]
        assert proposal["review_status"] == "PENDING_REVIEW"
        assert proposal["approver"] is None

    def test_proposal_retains_evidence_and_impact(self, evolve):
        evolve.propose_evolution("40-security-protocol.md", "Require CSP headers",
                                 "OWASP audit finding", "Medium risk; touches deploy config")

        proposal = evolve.load_proposals()[0]
        assert proposal["evidence"] == "OWASP audit finding"
        assert proposal["impact_analysis"] == "Medium risk; touches deploy config"
        assert proposal["target_protocol"] == "40-security-protocol.md"

    def test_proposal_is_versioned_and_timestamped(self, evolve):
        evolve.propose_evolution("x.json", "change", "evidence")
        proposal = evolve.load_proposals()[0]
        assert proposal["version"]
        assert proposal["timestamp"]

    def test_proposals_accumulate(self, evolve):
        evolve.propose_evolution("a.json", "first", "e1")
        evolve.propose_evolution("b.json", "second", "e2")
        assert len(evolve.load_proposals()) == 2

    def test_proposal_ids_are_unique(self, evolve):
        for i in range(10):
            evolve.propose_evolution(f"file{i}.json", f"change {i}", "evidence")
        ids = [p["id"] for p in evolve.load_proposals()]
        assert len(ids) == len(set(ids)), f"duplicate proposal ids issued: {ids}"


class TestApproval:
    def test_approval_records_the_human_approver(self, evolve):
        evo_id = evolve.propose_evolution("x.json", "change", "evidence")
        assert evolve.approve_proposal(evo_id, "Fakrul") is True

        proposal = evolve.load_proposals()[0]
        assert proposal["review_status"] == "APPROVED"
        assert proposal["approver"] == "Fakrul"
        assert proposal["approved_at"]

    def test_unknown_proposal_is_rejected(self, evolve):
        evolve.propose_evolution("x.json", "change", "evidence")
        assert evolve.approve_proposal("EVO-DOES-NOT-EXIST", "Fakrul") is False

    def test_approval_does_not_touch_other_proposals(self, evolve):
        first = evolve.propose_evolution("a.json", "first", "e1")
        evolve.propose_evolution("b.json", "second", "e2")

        evolve.approve_proposal(first, "Fakrul")
        statuses = {p["id"]: p["review_status"] for p in evolve.load_proposals()}
        assert statuses[first] == "APPROVED"
        assert list(statuses.values()).count("PENDING_REVIEW") == 1

    def test_empty_ledger_survives_a_read(self, evolve):
        assert evolve.load_proposals() == []
