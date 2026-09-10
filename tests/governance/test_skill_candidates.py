"""Skill candidates — a higher bar, and a boundary that is never crossed.

A lesson says "this happened". A skill says "here is how to do this kind of
work", and it shapes a whole task once loaded. So the evidence bar is higher,
and the last step is not automated at all: CoreSentinel does not own
`~/.claude/skills/`, and installing a skill is a governance act with a person's
name on it.

`test_the_host_skills_directory_is_never_touched` is the one that matters.
"""

import json
from pathlib import Path

import pytest

from coresentinel_core.learning import candidates, contradiction, skills
from coresentinel_core.storage import JsonStore


@pytest.fixture
def project(tmp_path, monkeypatch):
    import coresentinel_memory as mem

    root = tmp_path / "shop"
    (root / ".coresentinel" / "memory").mkdir(parents=True)
    (root / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "shop"}), encoding="utf-8")
    core_memory = tmp_path / "core-memory"
    core_memory.mkdir()
    monkeypatch.setattr(mem, "MEMORY_DIR", core_memory)
    monkeypatch.setattr(mem, "MEMORY_LAYERS",
                        {name: core_memory / f"{name}.json" for name in mem.MEMORY_LAYERS})
    return root


@pytest.fixture
def store(project):
    return JsonStore(project / ".coresentinel")


@pytest.fixture
def drafts(tmp_path):
    return tmp_path / "skill_candidates"


CONTEXT = "php83.laravel12"


def seed_trusted(store, lesson, context=CONTEXT, occurrences=4):
    for index, source in enumerate((f"{lesson[:6]}-1", f"{lesson[:6]}-2", f"{lesson[:6]}-3")):
        candidates.observe(
            store, lesson, source=source, kind="experience", context=context,
            metrics={"signature": f"SIG-{lesson[:8]}",
                     "by_context": {context or "global": {"success": occurrences,
                                                          "failure": 0}},
                     "success_count": occurrences if index == 0 else 0,
                     "failure_count": 0,
                     "occurrences": occurrences if index == 0 else 0,
                     "contexts": [context] if context else []})
    contradiction.validate(store)


def seed_cluster(store, count=3, occurrences=4, context=CONTEXT):
    for index in range(count):
        seed_trusted(store, f"deployment step {index} needs the queue worker restarted",
                     context=context, occurrences=occurrences)


class TestTheBarIsHigher:
    def test_one_strong_lesson_is_not_a_skill(self, store, drafts):
        seed_trusted(store, "deployment needs the queue worker restarted", occurrences=40)
        report = skills.draft(store, drafts, apply_changes=True)
        assert report["drafted"] == []
        assert "trusted lesson" in report["skipped"][0]["why_not"]

    def test_thin_evidence_behind_enough_lessons_is_not_a_skill(self, store, drafts):
        seed_cluster(store, count=3, occurrences=1)
        report = skills.draft(store, drafts, apply_changes=True)
        assert report["drafted"] == []
        assert "observation" in report["skipped"][0]["why_not"]

    def test_a_real_cluster_qualifies(self, store, drafts):
        seed_cluster(store, count=3, occurrences=4)
        report = skills.draft(store, drafts, apply_changes=True)
        assert report["drafted"], report["skipped"]

    def test_the_thresholds_are_reported(self, store, drafts):
        report = skills.draft(store, drafts)
        assert report["thresholds"] == {"trusted": skills.MIN_TRUSTED,
                                        "experiences": skills.MIN_EXPERIENCES}


class TestTheBoundary:
    def test_the_host_skills_directory_is_never_touched(self, store, drafts, monkeypatch,
                                                        tmp_path):
        """Installing a skill changes how an agent approaches every matching
        task. That is a person's decision, not a confidence score's."""
        fake_home = tmp_path / "home"
        (fake_home / ".claude" / "skills").mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

        seed_cluster(store)
        skills.draft(store, drafts, apply_changes=True)

        assert list((fake_home / ".claude" / "skills").iterdir()) == []

    def test_the_report_says_it_is_not_installed(self, store, drafts):
        seed_cluster(store)
        report = skills.draft(store, drafts, apply_changes=True)
        assert report["installed"] is False
        assert "human act" in report["note"]

    def test_a_dry_run_writes_nothing(self, store, drafts):
        seed_cluster(store)
        report = skills.draft(store, drafts, apply_changes=False)
        assert report["drafted"]
        assert not drafts.exists()


class TestTheDraft:
    def _rendered(self, store, drafts):
        seed_cluster(store)
        report = skills.draft(store, drafts, apply_changes=True)
        return Path(report["drafted"][0]["path"]).read_text(encoding="utf-8")

    def test_it_carries_frontmatter(self, store, drafts):
        body = self._rendered(store, drafts)
        assert body.startswith("---\n")
        assert "name:" in body
        assert "description:" in body

    def test_it_says_it_is_a_draft(self, store, drafts):
        """A generated skill that reads like a finished one invites installation
        without review."""
        body = self._rendered(store, drafts)
        assert "DRAFT" in body
        assert "nobody has reviewed it" in body

    def test_every_lesson_is_traceable(self, store, drafts):
        body = self._rendered(store, drafts)
        assert "evolve explain" in body
        assert "CAND-" in body

    def test_it_describes_rather_than_prescribes(self, store, drafts):
        body = self._rendered(store, drafts)
        assert "What was observed" in body
        assert "none of it prescribes" in body

    def test_the_name_says_when_to_load_it(self, store, drafts):
        seed_cluster(store)
        report = skills.draft(store, drafts, apply_changes=True)
        name = report["drafted"][0]["name"]
        assert "php83" in name or "laravel12" in name
        assert "gate" not in name and "error" not in name


class TestNaming:
    def test_generic_words_are_dropped(self):
        name = skills.name_for("php83.laravel12",
                               ["the quality gate failed with an error",
                                "the quality gate failed again"])
        assert "gate" not in name
        assert "quality" not in name

    def test_shared_terms_win(self):
        name = skills.name_for(None, ["restart the queue worker after deploy",
                                      "the queue worker needs restarting",
                                      "queue worker restart order matters"])
        assert "queue" in name or "worker" in name
