"""Integration — the CLI as a user and CI pipeline actually invoke it, in a sandboxed Core.

CORESENTINEL:SCANNER-FIXTURES — contains a deliberate credential sample used to prove
'coresentinel review' blocks on a secret leak.
"""

import json

import pytest

import coresentinel as cli

COMMAND_NAMES = [c["name"] for c in cli.COMMANDS]


class TestCommandRegistry:
    def test_every_requested_command_is_registered(self):
        expected = ["init", "doctor", "status", "memory", "context", "verify",
                    "review", "audit", "score", "agent", "evolve"]
        missing = [name for name in expected if not cli.find_command(name)]
        assert not missing, f"commands absent from the CLI surface: {missing}"

    def test_command_names_are_unique(self):
        assert len(COMMAND_NAMES) == len(set(COMMAND_NAMES))

    def test_aliases_never_collide_with_command_names(self):
        aliases = [a for c in cli.COMMANDS for a in c["aliases"]]
        collisions = [a for a in aliases if a in COMMAND_NAMES]
        assert not collisions, f"aliases shadow real commands: {collisions}"

    def test_aliases_are_unique_across_commands(self):
        aliases = [a for c in cli.COMMANDS for a in c["aliases"]]
        assert len(aliases) == len(set(aliases))

    @pytest.mark.parametrize("command", cli.COMMANDS, ids=lambda c: c["name"])
    def test_command_is_documented(self, command):
        assert command["summary"].strip()
        assert command["usage"] and all(u.strip() for u in command["usage"])
        assert command["group"].strip()

    @pytest.mark.parametrize("command", cli.COMMANDS, ids=lambda c: c["name"])
    def test_usage_examples_name_their_own_command(self, command):
        assert any(command["name"] in usage for usage in command["usage"]), \
            f"{command['name']} usage examples do not reference the command"

    def test_lookup_resolves_aliases(self):
        assert cli.find_command("squad")["name"] == "agent"
        assert cli.find_command("health")["name"] == "score"
        assert cli.find_command("adr")["name"] == "decision"

    def test_lookup_is_case_insensitive(self):
        assert cli.find_command("DOCTOR")["name"] == "doctor"


class TestHelpSurface:
    def test_bare_invocation_prints_the_command_index(self, run_cli):
        code, out, _ = run_cli()
        assert code == 0
        for name in ["init", "doctor", "status", "verify", "review"]:
            assert name in out

    def test_help_lists_every_group(self, run_cli):
        _, out, _ = run_cli("help")
        for group in {c["group"] for c in cli.COMMANDS}:
            assert group in out

    @pytest.mark.parametrize("name", COMMAND_NAMES)
    def test_every_command_answers_help(self, run_cli, name):
        code, out, _ = run_cli(name, "--help")
        assert code == 0, f"'{name} --help' exited {code}"
        assert name in out

    def test_help_subcommand_matches_flag(self, run_cli):
        _, from_sub, _ = run_cli("help", "doctor")
        _, from_flag, _ = run_cli("doctor", "--help")
        assert from_sub == from_flag


class TestUnknownCommands:
    def test_unknown_command_fails_loudly(self, run_cli):
        code, out, _ = run_cli("nonsense")
        assert code == 1, "an unknown command must not silently succeed"
        assert "Unknown command" in out

    def test_typo_gets_a_suggestion(self, run_cli):
        _, out, _ = run_cli("docter")
        assert "doctor" in out

    def test_unknown_command_does_not_run_verification(self, run_cli):
        """Regression: unknown commands used to fall through to the verification suite."""
        _, out, _ = run_cli("definitelynotacommand")
        assert "Evidence-Based Gate Verification" not in out


class TestDoctorCommand:
    def test_healthy_core_exits_zero(self, run_cli):
        code, out, _ = run_cli("doctor")
        assert code == 0
        assert "CoreSentinel:" in out

    def test_reports_all_seven_subsystems(self, run_cli_json):
        _, payload = run_cli_json("doctor", "--json")
        checks = {c["check"] for c in payload["checks"]}
        assert checks == {"Configuration", "Memory", "Governance", "Agent Registry",
                          "Verification Engine", "Security Rules", "Project Context"}

    def test_overall_state_is_recognized(self, run_cli_json):
        _, payload = run_cli_json("doctor", "--json")
        assert payload["overall"] in {"HEALTHY", "DEGRADED", "CRITICAL"}

    def test_every_check_declares_a_status(self, run_cli_json):
        _, payload = run_cli_json("doctor", "--json")
        for check in payload["checks"]:
            assert check["status"] in {"OK", "WARN", "FAIL"}
            assert check["summary"].strip()

    def test_missing_core_asset_fails_the_run(self, run_cli, sandbox):
        (sandbox / "squad-contracts.json").unlink()
        code, out, _ = run_cli("doctor")
        assert code == 1, "doctor must exit non-zero when a subsystem FAILs"
        assert "CRITICAL" in out

    def test_verbose_reveals_individual_findings(self, run_cli):
        _, terse, _ = run_cli("doctor")
        _, verbose, _ = run_cli("doctor", "--verbose")
        assert len(verbose) > len(terse)


class TestStatusCommand:
    def test_status_reports_core_subsystems(self, run_cli):
        code, out, _ = run_cli("status")
        assert code == 0
        for label in ["Project", "Quality Gates", "Memory Entries", "Audit Runs"]:
            assert label in out

    def test_status_json_carries_expected_sections(self, run_cli_json):
        _, payload = run_cli_json("status", "--json")
        for key in ["project", "stack", "git", "host", "gates", "memory", "audit", "evolution"]:
            assert key in payload


class TestInitCommand:
    def test_binds_a_fresh_project(self, run_cli, tmp_path):
        project = tmp_path / "fresh"
        project.mkdir()
        (project / "package.json").write_text('{"name":"demo"}', encoding="utf-8")

        code, out, _ = run_cli("init", str(project))
        assert code == 0
        assert (project / ".coresentinel" / "config.json").exists()
        assert (project / ".coresentinel" / "context.json").exists()

    def test_refuses_to_rebind_without_force(self, run_cli, tmp_path):
        project = tmp_path / "twice"
        project.mkdir()
        run_cli("init", str(project))

        code, out, _ = run_cli("init", str(project))
        assert code == 1
        assert "BLOCKED" in out

    def test_force_rebinds(self, run_cli, tmp_path):
        project = tmp_path / "forced"
        project.mkdir()
        run_cli("init", str(project))

        code, _, _ = run_cli("init", str(project), "--force")
        assert code == 0

    def test_records_detected_stack_in_config(self, run_cli, tmp_path):
        project = tmp_path / "typed"
        project.mkdir()
        (project / "package.json").write_text(
            json.dumps({"dependencies": {"next": "14.0.0"}, "scripts": {"test": "jest"}}),
            encoding="utf-8")

        run_cli("init", str(project))
        config = json.loads((project / ".coresentinel" / "config.json").read_text(encoding="utf-8"))
        assert "Node/TypeScript" in config["stack"]
        assert "Next.js" in config["frameworks"]
        assert config["test_runner"]

    def test_seeded_facts_land_in_the_project_store(self, run_cli, tmp_path):
        project = tmp_path / "scoped"
        project.mkdir()
        (project / "package.json").write_text('{"dependencies":{"express":"4.18.0"}}',
                                              encoding="utf-8")

        run_cli("init", str(project))

        store = project / ".coresentinel" / "memory" / "project.json"
        assert store.exists(), "init did not create the project memory store"
        facts = [f["fact"] for f in json.loads(store.read_text(encoding="utf-8"))["facts"]]
        assert any("scoped" in f for f in facts)

    def test_init_does_not_pollute_the_core_memory(self, run_cli, sandbox, tmp_path):
        """Regression: init used to write every project's facts into the shared Core layer."""
        core_layer = sandbox / "memory" / "project.json"
        before = core_layer.read_bytes()

        for name in ("alpha", "beta"):
            project = tmp_path / name
            project.mkdir()
            (project / "package.json").write_text('{"dependencies":{"react":"18.0.0"}}',
                                                  encoding="utf-8")
            run_cli("init", str(project))

        assert core_layer.read_bytes() == before, \
            "init leaked project facts into the shared Core memory layer"

    def test_projects_do_not_see_each_other_in_context(self, run_cli, run_cli_json, tmp_path):
        for name, dep in (("alpha", "express"), ("beta", "react")):
            project = tmp_path / name
            project.mkdir()
            (project / "package.json").write_text(
                json.dumps({"dependencies": {dep: "1.0.0"}}), encoding="utf-8")
            run_cli("init", str(project))

        _, payload = run_cli_json("context", str(tmp_path / "alpha"), "--json")
        facts = " ".join(f["fact"] or "" for f in payload["memory_facts"])
        assert "alpha" in facts
        assert "beta" not in facts, "one project's context exposed another project's facts"

    def test_does_not_write_outside_the_target(self, run_cli, tmp_path):
        """init must confine its writes to the project it was pointed at."""
        project = tmp_path / "contained"
        project.mkdir()
        sibling = tmp_path / "untouched"
        sibling.mkdir()

        run_cli("init", str(project))

        assert list(sibling.iterdir()) == [], "init wrote outside its target directory"
        assert (project / ".coresentinel").exists()


class TestContextCommand:
    def test_context_json_describes_the_project(self, run_cli_json):
        _, payload = run_cli_json("context", "--json")
        assert payload["project"]["name"]
        assert payload["project"]["stack"]
        assert "memory_facts" in payload

    def test_context_reports_git_state(self, run_cli_json, sandbox):
        _, payload = run_cli_json("context", "--json")
        assert "git" in payload and "uncommitted" in payload["git"]


class TestReviewCommand:
    def test_review_json_declares_a_verdict(self, run_cli_json):
        _, payload = run_cli_json("review", "--json")
        assert payload["verdict"] in {"APPROVED", "APPROVED WITH COMMENTS",
                                      "CHANGES REQUIRED", "NOTHING TO REVIEW"}

    def test_review_of_a_secret_leak_exits_nonzero(self, run_cli, git_repo):
        (git_repo.path / "config.py").write_text('api_key = "sk_live_a1b2c3d4e5f6g7h8"\n',
                                                 encoding="utf-8")
        code, out, _ = run_cli("review", str(git_repo.path))
        assert code == 1
        assert "CHANGES REQUIRED" in out


class TestAdapterCommand:
    def test_export_bundle_carries_the_api_contract(self, run_cli_json):
        _, payload = run_cli_json("adapter", "export", "--json")
        for key in ["coresentinel_api", "identity", "governance", "memory",
                    "verification", "telemetry", "host"]:
            assert key in payload

    def test_registry_lists_every_adapter(self, run_cli):
        _, out, _ = run_cli("adapter", "list")
        for host in ["Claude Code", "Cursor", "Gemini CLI", "OpenAI Codex"]:
            assert host in out

    def test_sync_is_a_dry_run_by_default(self, run_cli, tmp_path):
        project = tmp_path / "unbound"
        project.mkdir()
        run_cli("adapter", "sync", "generic", "--scope", "project", cwd=project)
        assert not (project / "AGENTS.md").exists()


class TestJsonContracts:
    @pytest.mark.parametrize("args", [
        ("doctor", "--json"), ("status", "--json"), ("context", "--json"),
        ("review", "--json"), ("score", "--json"), ("adapter", "export", "--json"),
    ])
    def test_json_output_is_parseable(self, run_cli_json, args):
        code, payload = run_cli_json(*args)
        assert isinstance(payload, dict)

    @pytest.mark.parametrize("args", [("doctor", "--json"), ("status", "--json")])
    def test_json_output_carries_no_bom(self, run_cli, args):
        """A BOM breaks jq and every downstream JSON consumer."""
        _, out, _ = run_cli(*args)
        assert not out.startswith("﻿")


class TestReadOnlyCommandsAreSafe:
    @pytest.mark.parametrize("command", [
        ("memory", "show"), ("decision", "list"), ("agent", "list"),
        ("gate", "status"), ("evolve", "list"), ("audit", "list"),
        ("adapter", "list"), ("adapter", "detect"), ("status",), ("context",),
    ])
    def test_inspection_commands_exit_cleanly(self, run_cli, command):
        code, out, err = run_cli(*command)
        assert code == 0, f"'{' '.join(command)}' exited {code}: {err[:300]}"
        assert out.strip(), f"'{' '.join(command)}' produced no output"

    def test_listing_commands_do_not_mutate_state(self, run_cli, sandbox):
        before = {p.name: p.read_bytes() for p in (sandbox / "memory").glob("*.json")}
        for command in [("memory", "show"), ("gate", "status"), ("evolve", "list"),
                        ("audit", "list"), ("status",)]:
            run_cli(*command)

        after = {p.name: p.read_bytes() for p in (sandbox / "memory").glob("*.json")}
        assert before == after, "a read-only command mutated the memory ledger"
