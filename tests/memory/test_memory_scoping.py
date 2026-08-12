"""Memory scoping — project state belongs to the project, not to the shared Core.

Regression cover for: running init across several repositories piled every project's
facts into the single global memory/project.json.
"""

import json

import pytest

import coresentinel_memory as mem


@pytest.fixture
def bound_project(tmp_path):
    """A directory bound to CoreSentinel, as `coresentinel init` leaves it."""
    project = tmp_path / "bound"
    (project / mem.CONFIG_DIRNAME).mkdir(parents=True)
    (project / mem.CONFIG_DIRNAME / "config.json").write_text(
        json.dumps({"project_name": "bound"}), encoding="utf-8")
    return project


class TestProjectDiscovery:
    def test_finds_the_binding_at_the_root(self, bound_project):
        assert mem.find_project_root(str(bound_project)) == bound_project

    def test_walks_up_from_a_nested_directory(self, bound_project):
        nested = bound_project / "src" / "api" / "handlers"
        nested.mkdir(parents=True)
        assert mem.find_project_root(str(nested)) == bound_project

    def test_unbound_directory_has_no_root(self, tmp_path):
        assert mem.find_project_root(str(tmp_path)) is None

    def test_a_config_directory_without_config_json_does_not_bind(self, tmp_path):
        (tmp_path / mem.CONFIG_DIRNAME).mkdir()
        assert mem.find_project_root(str(tmp_path)) is None


class TestLayerResolution:
    @pytest.mark.parametrize("layer", ["working", "session", "project"])
    def test_project_scoped_layers_resolve_into_the_project(self, bound_project, layer):
        path = mem.layer_path(layer, str(bound_project))
        assert path.parent.parent == bound_project / mem.CONFIG_DIRNAME
        assert mem.layer_scope(layer, str(bound_project)) == "project"

    @pytest.mark.parametrize("layer", ["longterm", "failures", "patterns", "decisions"])
    def test_shared_layers_stay_in_the_core(self, bound_project, layer):
        """Reusable patterns and cross-project history are the point of the Core store."""
        assert mem.layer_path(layer, str(bound_project)) == mem.MEMORY_LAYERS[layer]
        assert mem.layer_scope(layer, str(bound_project)) == "core"

    @pytest.mark.parametrize("layer", ["working", "session", "project", "patterns"])
    def test_unbound_directory_resolves_everything_to_the_core(self, tmp_path, layer):
        assert mem.layer_path(layer, str(tmp_path)) == mem.MEMORY_LAYERS[layer]
        assert mem.layer_scope(layer, str(tmp_path)) == "core"

    def test_every_layer_is_classified(self):
        assert mem.PROJECT_SCOPED_LAYERS <= set(mem.MEMORY_LAYERS)


class TestScopedWrites:
    def test_fact_lands_in_the_project_store(self, isolated_memory, bound_project):
        assert isolated_memory.add_fact("project", "Uses Express", 0.95, "package.json",
                                        str(bound_project))

        store = bound_project / isolated_memory.CONFIG_DIRNAME / "memory" / "project.json"
        facts = json.loads(store.read_text(encoding="utf-8"))["facts"]
        assert [f["fact"] for f in facts] == ["Uses Express"]

    def test_project_write_never_touches_the_core_store(self, isolated_memory, bound_project):
        """This is the regression: the Core layer must not grow when a project records a fact."""
        isolated_memory.ensure_memory_dir()
        core_layer = isolated_memory.MEMORY_LAYERS["project"]
        before = core_layer.read_bytes()

        isolated_memory.add_fact("project", "Uses Express", 0.95, "package.json",
                                 str(bound_project))

        assert core_layer.read_bytes() == before, \
            "a project-scoped fact leaked into the shared Core memory"

    def test_two_projects_do_not_see_each_other(self, isolated_memory, tmp_path):
        projects = []
        for name in ("alpha", "beta"):
            project = tmp_path / name
            (project / isolated_memory.CONFIG_DIRNAME).mkdir(parents=True)
            (project / isolated_memory.CONFIG_DIRNAME / "config.json").write_text("{}",
                                                                                  encoding="utf-8")
            isolated_memory.add_fact("project", f"{name} fact", 0.95, "test", str(project))
            projects.append(project)

        for project, name in zip(projects, ("alpha", "beta")):
            store = project / isolated_memory.CONFIG_DIRNAME / "memory" / "project.json"
            facts = [f["fact"] for f in json.loads(store.read_text(encoding="utf-8"))["facts"]]
            assert facts == [f"{name} fact"]

    def test_shared_layer_still_writes_to_the_core_from_a_project(self, isolated_memory,
                                                                  bound_project):
        isolated_memory.add_fact("patterns", "Repository pattern works well", 0.95, "review",
                                 str(bound_project))

        core_layer = isolated_memory.MEMORY_LAYERS["patterns"]
        facts = json.loads(core_layer.read_text(encoding="utf-8"))["facts"]
        assert facts[0]["fact"] == "Repository pattern works well"

    def test_write_reports_which_store_was_used(self, isolated_memory, bound_project, capsys):
        isolated_memory.add_fact("project", "Uses Express", 0.95, "package.json",
                                 str(bound_project))
        assert "project scope" in capsys.readouterr().out


class TestCorruptLayerSafety:
    def test_refuses_to_overwrite_an_unreadable_layer(self, isolated_memory, bound_project):
        """Appending to a corrupt layer by resetting it would destroy recorded facts."""
        store = bound_project / isolated_memory.CONFIG_DIRNAME / "memory"
        store.mkdir(parents=True)
        corrupt = store / "project.json"
        corrupt.write_text("{ not json at all", encoding="utf-8")

        assert isolated_memory.add_fact("project", "new", 0.95, "test",
                                        str(bound_project)) is False
        assert corrupt.read_text(encoding="utf-8") == "{ not json at all"

    def test_refusal_explains_itself_on_stderr(self, isolated_memory, bound_project, capsys):
        """Diagnostics belong on stderr — anything on stdout corrupts --json consumers."""
        store = bound_project / isolated_memory.CONFIG_DIRNAME / "memory"
        store.mkdir(parents=True)
        (store / "project.json").write_text("{ broken", encoding="utf-8")

        isolated_memory.add_fact("project", "new", 0.95, "test", str(bound_project))

        captured = capsys.readouterr()
        assert "Refusing to write" in captured.err
        assert "Refusing to write" not in captured.out
