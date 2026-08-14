"""Project discovery — precision, evidence, and the difference between empty and unknown.

The rule under test everywhere here: a detector reports what a file proves, and
otherwise reports nothing. v1 substring-matched dependency names, which is why
every Laravel project claimed Symfony.
"""

import json
import time

import pytest

from coresentinel_core.project import discovery
from coresentinel_core.project.discovery import base, stack, infrastructure, surface


def write(root, name, content=""):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def values(report, dimension):
    return report["dimensions"][dimension]["values"]


@pytest.fixture
def laravel(tmp_path):
    root = tmp_path / "shop"
    root.mkdir()
    write(root, "composer.json", json.dumps({"require": {
        "php": "^8.2", "laravel/framework": "^11.0",
        "symfony/console": "^7.0", "predis/predis": "^2.0"}}))
    write(root, "composer.lock", "{}")
    write(root, "docker-compose.yml", "services:\n  db:\n    image: postgres:16\n")
    write(root, ".env.example", "APP_KEY=\nDB_CONNECTION=pgsql\n")
    write(root, "routes/api.php", "<?php\n")
    return root


class TestFrameworkPrecision:
    def test_a_laravel_project_does_not_report_symfony(self, laravel):
        """Regression, F-22. Laravel depends on symfony/console, so substring
        matching made every Laravel project claim Symfony."""
        assert values(discovery.inspect(laravel), "frameworks") == ["Laravel"]

    def test_a_lookalike_package_is_not_the_framework(self, tmp_path):
        """next-auth is an auth library, eslint-plugin-vue is a lint plugin and
        @types/react is a type stub. None mean the framework is in use."""
        root = tmp_path / "app"
        root.mkdir()
        write(root, "package.json", json.dumps({"dependencies": {
            "next-auth": "^4", "eslint-plugin-vue": "^9", "@types/react": "^18"}}))
        assert values(discovery.inspect(root), "frameworks") == []

    def test_the_real_package_is_detected(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "package.json", json.dumps({"dependencies": {"next": "^14", "react": "^18"}}))
        detected = values(discovery.inspect(root), "frameworks")
        assert "Next.js" in detected and "React" in detected

    def test_symfony_is_detected_from_its_own_marker(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "composer.json",
              json.dumps({"require": {"symfony/framework-bundle": "^7.0"}}))
        assert values(discovery.inspect(root), "frameworks") == ["Symfony"]

    def test_a_python_requirement_is_matched_on_the_package_name(self, tmp_path):
        root = tmp_path / "api"
        root.mkdir()
        write(root, "requirements.txt", "Django>=4.2\n# flask is only mentioned here\n")
        detected = values(discovery.inspect(root), "frameworks")
        assert detected == ["Django"], "a package named in a comment is not a dependency"

    def test_underscores_and_case_do_not_defeat_matching(self, tmp_path):
        root = tmp_path / "api"
        root.mkdir()
        write(root, "requirements.txt", "SQLAlchemy==2.0\n")
        assert "SQLAlchemy" in values(discovery.inspect(root), "frameworks")


class TestEvidence:
    def test_every_finding_names_the_file_that_proves_it(self, laravel):
        report = discovery.inspect(laravel)
        for dimension in report["dimensions"].values():
            for item in dimension["findings"]:
                assert item["evidence"]["file"], f"{item['value']} cites no file"
                assert item["evidence"]["locator"], f"{item['value']} cites no locator"

    def test_the_framework_evidence_points_at_the_dependency_key(self, laravel):
        finding = next(f for f in discovery.inspect(laravel)["dimensions"]["frameworks"]["findings"])
        assert finding["evidence"]["locator"] == "require['laravel/framework']"

    def test_a_driver_is_weaker_evidence_than_a_running_service(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "package.json", json.dumps({"dependencies": {"pg": "^8"}}))
        finding = discovery.inspect(root)["dimensions"]["datastores"]["findings"][0]
        assert finding["value"] == "PostgreSQL"
        assert finding["confidence"] < 0.9
        assert "not proof it is in use" in finding["evidence"]["detail"]


class TestUnknownVersusEmpty:
    def test_an_empty_directory_reports_unknown_not_none(self, tmp_path):
        root = tmp_path / "void"
        root.mkdir()
        report = discovery.inspect(root)
        assert set(report["unknown_dimensions"]) == set(report["dimensions"])
        assert discovery.summary(report)["datastores"] == discovery.UNKNOWN

    def test_a_known_dimension_is_not_listed_as_unknown(self, laravel):
        report = discovery.inspect(laravel)
        assert "frameworks" not in report["unknown_dimensions"]
        assert "datastores" not in report["unknown_dimensions"]

    def test_the_render_states_that_unknown_is_not_empty(self, tmp_path):
        root = tmp_path / "void"
        root.mkdir()
        rendered = discovery.render(discovery.inspect(root))
        assert "not an empty one" in rendered


class TestTestRunnerDetection:
    """The runner has to be evidenced, and the evidence has to be read."""

    def test_pytest_is_found_from_a_pyproject_config_table(self, tmp_path):
        """A [tool.pytest.ini_options] table is pytest's own configuration.

        The demo project declares pytest only under optional-dependencies and
        carries no pytest.ini, so it was reported as having no runner — correct
        by the evidence rule, but the evidence was sitting in pyproject.toml
        unread.
        """
        root = tmp_path / "app"
        root.mkdir()
        (root / "pyproject.toml").write_text(
            "[project]\nname='app'\n\n[tool.pytest.ini_options]\ntestpaths=['tests']\n",
            encoding="utf-8")

        testing = discovery.inspect(root)["dimensions"]["testing"]
        commands = [f for f in testing["findings"] if f["kind"] == "test_command"]
        assert [f["value"] for f in commands] == ["pytest"]
        assert commands[0]["evidence"]["file"] == "pyproject.toml"
        assert commands[0]["evidence"]["locator"] == "[tool.pytest.ini_options]"

    def test_an_explicit_config_file_still_wins(self, tmp_path):
        """pytest.ini is the stronger signal and must not be displaced."""
        root = tmp_path / "app"
        root.mkdir()
        (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            "[project]\nname='app'\n\n[tool.pytest.ini_options]\n", encoding="utf-8")

        commands = [f for f in discovery.inspect(root)["dimensions"]["testing"]["findings"]
                    if f["kind"] == "test_command"]
        assert len(commands) == 1
        assert commands[0]["evidence"]["file"] == "pytest.ini"

    def test_a_pyproject_without_pytest_config_claims_no_runner(self, tmp_path):
        """Absence of evidence stays absence of a claim."""
        root = tmp_path / "app"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\nname='app'\n", encoding="utf-8")

        commands = [f for f in discovery.inspect(root)["dimensions"]["testing"]["findings"]
                    if f["kind"] == "test_command"]
        assert commands == []


class TestStackCoverage:
    @pytest.mark.parametrize("manifest,content,language", [
        ("package.json", "{}", "Node/TypeScript"),
        ("pyproject.toml", "[project]\nname='x'\n", "Python"),
        ("composer.json", "{}", "PHP"),
        ("Cargo.toml", "[package]\nname='x'\n", "Rust"),
        ("go.mod", "module example.com/x\n\ngo 1.22\n", "Go"),
        ("Gemfile", "source 'https://rubygems.org'\n", "Ruby"),
    ])
    def test_six_stacks_are_detected_from_their_manifest(self, tmp_path, manifest,
                                                         content, language):
        root = tmp_path / "app"
        root.mkdir()
        write(root, manifest, content)
        assert language in values(discovery.inspect(root), "languages")

    def test_a_polyglot_project_reports_every_language(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "package.json", "{}")
        write(root, "go.mod", "module example.com/x\n")
        detected = values(discovery.inspect(root), "languages")
        assert "Node/TypeScript" in detected and "Go" in detected

    def test_source_files_evidence_a_language_without_a_manifest(self, tmp_path):
        """A tree of .py files is a Python project whether or not anyone wrote a manifest."""
        root = tmp_path / "scripts"
        root.mkdir()
        for index in range(4):
            write(root, f"module_{index}.py", "x = 1\n")
        assert "Python" in values(discovery.inspect(root), "languages")

    def test_one_stray_file_does_not_declare_a_language(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "setup.rb", "")
        write(root, "helper.rb", "")
        assert "Ruby" not in values(discovery.inspect(root), "languages")

    @pytest.mark.parametrize("lockfile,manager", [
        ("package-lock.json", "npm"), ("yarn.lock", "yarn"),
        ("composer.lock", "composer"), ("poetry.lock", "poetry"),
        ("Cargo.lock", "cargo"), ("Gemfile.lock", "bundler"),
    ])
    def test_the_package_manager_comes_from_the_lockfile(self, tmp_path, lockfile, manager):
        root = tmp_path / "app"
        root.mkdir()
        write(root, lockfile, "")
        assert values(discovery.inspect(root), "package_managers") == [manager]


class TestInfrastructure:
    def test_compose_images_identify_the_datastores(self, laravel):
        assert "PostgreSQL" in values(discovery.inspect(laravel), "datastores")

    def test_a_service_merely_named_db_proves_nothing(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "docker-compose.yml", "services:\n  db:\n    image: alpine:3\n")
        assert values(discovery.inspect(root), "datastores") == []

    def test_an_environment_key_identifies_the_engine(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, ".env.example", "DB_CONNECTION=mariadb\n")
        assert "MariaDB" in values(discovery.inspect(root), "datastores")

    def test_environment_values_are_never_read(self, tmp_path):
        """The values are the secrets this product exists to protect."""
        root = tmp_path / "app"
        root.mkdir()
        write(root, ".env.example", "APP_KEY=super-secret-value-1234\nDB_HOST=localhost\n")
        report = discovery.inspect(root)
        rendered = json.dumps(report)
        assert "super-secret-value-1234" not in rendered
        assert "APP_KEY" in rendered

    def test_ci_reports_the_workflow_files(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, ".github/workflows/ci.yml", "on: push\n")
        finding = discovery.inspect(root)["dimensions"]["ci"]["findings"][0]
        assert finding["value"] == "GitHub Actions" and "ci.yml" in finding["evidence"]["detail"]

    def test_an_empty_workflow_directory_is_not_a_ci_pipeline(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        (root / ".github" / "workflows").mkdir(parents=True)
        assert values(discovery.inspect(root), "ci") == []


class TestPerformance:
    def test_discovery_stays_fast_on_a_large_tree(self, tmp_path):
        """Budget is 2s: the project brain must not become the slow part."""
        root = tmp_path / "big"
        root.mkdir()
        write(root, "package.json", json.dumps({"dependencies": {"express": "^4"}}))
        for bucket in range(40):
            for index in range(50):
                write(root, f"src/mod{bucket}/file{index}.ts", "export const x = 1;\n")

        started = time.perf_counter()
        report = discovery.inspect(root)
        elapsed = time.perf_counter() - started

        assert report["scanned_files"] >= 2000
        assert elapsed < 2.0, f"discovery took {elapsed:.2f}s on {report['scanned_files']} files"

    def test_ignored_directories_are_not_walked(self, tmp_path):
        root = tmp_path / "app"
        root.mkdir()
        write(root, "package.json", "{}")
        for index in range(50):
            write(root, f"node_modules/pkg{index}/index.js", "")
        assert discovery.inspect(root)["scanned_files"] < 10

    def test_a_truncated_scan_says_so(self, tmp_path, monkeypatch):
        monkeypatch.setattr(base, "MAX_SCANNED_FILES", 5)
        root = tmp_path / "app"
        root.mkdir()
        for index in range(20):
            write(root, f"file{index}.py", "")
        assert discovery.inspect(root)["scan_truncated"] is True


class TestBackwardCompatibility:
    def test_the_v1_detectors_keep_their_signature_and_return_type(self, laravel):
        import coresentinel as cli
        import coresentinel_doctor as doctor

        assert cli.detect_project_type(laravel) == ["PHP"]
        assert doctor.detect_stack(laravel) == ["PHP"]

    def test_the_v1_context_pack_is_unchanged(self, laravel):
        import coresentinel_context as context
        pack = context.build_project_context(str(laravel))
        assert pack["project"]["stack"] == ["PHP"]
        assert "frameworks" in pack["project"]
