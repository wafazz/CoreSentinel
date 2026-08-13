"""Agent permissions — enforced at the point of use, not merely declared.

The README has claimed since v1 that "a read-only researcher cannot silently
write files". Until this phase that was a statement about a JSON document.
`test_a_read_only_agent_cannot_write` is the test that makes it true.
"""

import pytest

from coresentinel_core.agents import permissions as perms
from coresentinel_core.agents import registry
from coresentinel_core.agents.sandbox import AgentSandbox, PermissionDenied
from coresentinel_core.runtime.errors import PathSecurityError


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    return root


def sandbox_for(agent, root, **kwargs):
    return AgentSandbox(agent, registry.permissions_for(agent, **kwargs), root)


class TestDefaultDenial:
    def test_an_undeclared_agent_may_only_read(self):
        permission_set = perms.PermissionSet()
        assert permission_set.check(perms.FILESYSTEM_READ).allowed
        for permission in perms.PERMISSIONS:
            if permission != perms.FILESYSTEM_READ:
                assert not permission_set.check(permission).allowed, \
                    f"{permission} was granted by default"

    def test_an_unknown_agent_falls_back_to_the_default_set(self):
        permission_set = registry.permissions_for("NotARegisteredAgent")
        assert permission_set.granted() == [perms.FILESYSTEM_READ]

    def test_an_unknown_permission_is_denied(self):
        assert not perms.PermissionSet().check("filesystem.obliterate").allowed


class TestReadOnlyAgentIsReallyReadOnly:
    def test_a_read_only_agent_cannot_write(self, project):
        """The claim the README has made since v1, now enforced."""
        scout = sandbox_for("Scout", project)
        with pytest.raises(PermissionDenied):
            scout.write("leak.txt", "data")
        assert not (project / "leak.txt").exists(), "the file was written despite the denial"

    def test_the_denial_is_recorded_not_swallowed(self, project):
        """A refusal nobody can see is indistinguishable from never having tried."""
        scout = sandbox_for("Scout", project)
        with pytest.raises(PermissionDenied):
            scout.write("leak.txt", "data")
        assert scout.denials[0]["permission"] == perms.FILESYSTEM_WRITE
        assert scout.denials[0]["agent"] == "Scout"
        assert scout.denials[0]["reason"]

    def test_a_read_only_agent_cannot_execute(self, project):
        scout = sandbox_for("Scout", project)
        with pytest.raises(PermissionDenied):
            scout.execute(["echo", "hello"])

    def test_a_read_only_agent_can_still_read(self, project):
        assert "x = 1" in sandbox_for("Scout", project).read("src/app.py")

    def test_the_denial_reaches_the_orchestrator_callback(self, project):
        seen = []
        scout = AgentSandbox("Scout", registry.permissions_for("Scout"), project,
                             on_denial=seen.append)
        with pytest.raises(PermissionDenied):
            scout.write("leak.txt", "x")
        assert len(seen) == 1


class TestLimitedScope:
    def test_a_limited_grant_allows_only_its_scope(self):
        tester = registry.permissions_for("Tester")
        assert tester.check(perms.SHELL_EXECUTE, "pytest").allowed
        assert not tester.check(perms.SHELL_EXECUTE, "rm").allowed

    def test_a_limited_write_is_confined_to_its_directories(self, project):
        tester = sandbox_for("Tester", project)
        tester.write("tests/test_new.py", "def test_x(): pass\n")
        with pytest.raises(PermissionDenied):
            tester.write("src/app.py", "malicious")
        assert (project / "src" / "app.py").read_text(encoding="utf-8") == "x = 1\n"

    def test_limited_without_a_scope_grants_nothing(self):
        """The safest-looking level must not silently become the widest."""
        permission_set = perms.PermissionSet({perms.FILESYSTEM_WRITE: perms.LIMITED})
        assert not permission_set.check(perms.FILESYSTEM_WRITE, "anything").allowed

    def test_limited_with_no_scope_supplied_is_denied(self):
        permission_set = perms.PermissionSet({perms.SHELL_EXECUTE: perms.LIMITED},
                                             {perms.SHELL_EXECUTE: ["git"]})
        assert not permission_set.check(perms.SHELL_EXECUTE).allowed


class TestAskLevel:
    def test_ask_is_denied_when_nobody_can_be_asked(self):
        permission_set = perms.PermissionSet({perms.GIT_COMMIT: perms.ASK}, interactive=False)
        decision = permission_set.check(perms.GIT_COMMIT)
        assert not decision.allowed and "not interactive" in decision.reason

    def test_ask_is_allowed_when_the_run_is_interactive(self):
        permission_set = perms.PermissionSet({perms.GIT_COMMIT: perms.ASK}, interactive=True)
        assert permission_set.check(perms.GIT_COMMIT).allowed


class TestEscalation:
    @pytest.mark.parametrize("permission", sorted(perms.ESCALATION_ONLY))
    def test_high_blast_radius_permissions_need_a_stated_reason(self, permission):
        with pytest.raises(ValueError):
            perms.PermissionSet().grant(permission)

    def test_a_grant_with_a_reason_is_accepted_and_recorded(self):
        permission_set = perms.PermissionSet()
        record = permission_set.grant(perms.DEPLOYMENT, perms.ALLOW,
                                      reason="release approved by Fakrul")
        assert permission_set.check(perms.DEPLOYMENT).allowed
        assert record["reason"] == "release approved by Fakrul"

    def test_an_ordinary_permission_can_be_granted_without_ceremony(self):
        permission_set = perms.PermissionSet()
        permission_set.grant(perms.FILESYSTEM_WRITE)
        assert permission_set.check(perms.FILESYSTEM_WRITE, "any.txt").allowed

    def test_an_unknown_permission_cannot_be_granted(self):
        with pytest.raises(ValueError):
            perms.PermissionSet().grant("filesystem.obliterate")


class TestPathContainment:
    def test_a_write_outside_the_project_is_refused(self, project):
        builder = sandbox_for("Builder", project)
        with pytest.raises(PathSecurityError):
            builder.write("../escaped.txt", "data")

    def test_containment_is_recorded_as_a_denial(self, project):
        builder = sandbox_for("Builder", project)
        with pytest.raises(PathSecurityError):
            builder.write("../../escaped.txt", "data")
        assert builder.denials[-1]["level"] == "CONTAINMENT"

    def test_a_read_outside_the_project_is_refused(self, project):
        with pytest.raises(PathSecurityError):
            sandbox_for("Scout", project).read("../../../etc/hosts")


class TestGitPermissions:
    def test_committing_needs_its_own_grant(self, project):
        builder = sandbox_for("Builder", project)
        with pytest.raises(PermissionDenied):
            builder.git("commit", "-m", "x")

    def test_pushing_needs_its_own_grant(self, project):
        devops = sandbox_for("DevOps", project, interactive=True)
        with pytest.raises(PermissionDenied):
            devops.git("push")


class TestRegistryDeclarations:
    def test_every_contract_declares_permissions(self):
        overview = registry.audit()
        assert overview["defaulted"] == [], \
            f"contracts without a permission block stay read-only: {overview['defaulted']}"

    def test_no_contract_is_granted_production_access(self):
        for name in registry.names():
            level = registry.permissions_for(name).level(perms.PRODUCTION_ACCESS)
            assert level == perms.DENY, f"{name} holds production access by default"

    def test_no_contract_may_push_without_asking(self):
        for name in registry.names():
            level = registry.permissions_for(name).level(perms.GIT_PUSH)
            assert level in (perms.DENY, perms.ASK), f"{name} can push unattended"

    def test_the_scout_contract_grants_reading_only(self):
        assert registry.permissions_for("Scout").granted() == [perms.FILESYSTEM_READ]

    def test_permissions_survive_the_registry_round_trip(self):
        for name in registry.names():
            assert registry.permissions_for(name).summary(), f"{name} resolved no permissions"
