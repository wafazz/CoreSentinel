"""Squad agent contracts — every specialist must declare inputs, outputs and authority."""

import json

import pytest

import coresentinel_squad as squad

REQUIRED_FIELDS = ["name", "role", "capability", "input_contract",
                   "output_contract", "authority", "constraints", "verification_gate"]

READ_ONLY_AGENTS = ["Scout"]


@pytest.fixture(scope="module")
def contracts(request):
    path = request.config.rootpath / "squad-contracts.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))["squad"]


class TestRegistryIntegrity:
    def test_full_squad_is_registered(self, contracts):
        assert len(contracts) == 17, f"expected 17 specialists, found {len(contracts)}"

    def test_agent_names_are_unique(self, contracts):
        names = [c["name"] for c in contracts]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_every_contract_declares_field(self, contracts, field):
        missing = [c.get("name", "<unnamed>") for c in contracts if not c.get(field)]
        assert not missing, f"contracts missing '{field}': {missing}"

    def test_contract_lists_are_not_empty_strings(self, contracts):
        for contract in contracts:
            for field in ["capability", "input_contract", "output_contract", "constraints"]:
                value = contract[field]
                assert isinstance(value, list) and all(v.strip() for v in value), \
                    f"{contract['name']}.{field} is not a list of non-empty entries"


class TestAuthorityBoundaries:
    @pytest.mark.parametrize("agent_name", READ_ONLY_AGENTS)
    def test_read_only_agents_declare_no_write_authority(self, contracts, agent_name):
        """A researcher that can silently write files is an unbounded agent."""
        contract = next(c for c in contracts if c["name"] == agent_name)
        constraints = " ".join(contract["constraints"]).lower()
        assert "no file write" in constraints or "read-only" in constraints, \
            f"{agent_name} does not declare a read-only constraint"

    def test_every_agent_has_a_verification_gate(self, contracts):
        """No specialist may hand off work without a stated acceptance condition."""
        for contract in contracts:
            gates = contract["verification_gate"]
            assert gates and all(g.strip() for g in gates), \
                f"{contract['name']} declares no verification gate"

    def test_lead_agent_is_present_and_orchestrates(self, contracts):
        lead = next((c for c in contracts if "Lead" in c["role"] or "Orchestrat" in c["role"]), None)
        assert lead is not None, "no squad lead is registered"
        assert lead["authority"], "the squad lead declares no authority"


class TestContractLookup:
    def test_finds_agent_by_exact_name(self, capsys):
        squad.show_agent_contract("Architect")
        assert "Architect" in capsys.readouterr().out

    def test_lookup_is_case_insensitive(self, capsys):
        squad.show_agent_contract("architect")
        out = capsys.readouterr().out
        assert "ARCHITECT" in out.upper()

    def test_unknown_agent_reports_cleanly(self, capsys):
        squad.show_agent_contract("NotARealAgent")
        out = capsys.readouterr().out
        assert "NotARealAgent" in out or "not found" in out.lower()

    def test_listing_covers_the_whole_squad(self, contracts, capsys):
        squad.list_squad()
        out = capsys.readouterr().out
        missing = [c["name"] for c in contracts if c["name"] not in out]
        assert not missing, f"specialists absent from the listing: {missing}"
