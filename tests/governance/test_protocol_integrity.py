"""Protocol corpus integrity — the documents the agent is told to obey must exist and resolve."""

import re

import pytest

LINK_PATTERN = re.compile(r'\[[^\]]+\]\(\./([^)#]+)\)')


@pytest.fixture(scope="module")
def protocols(request):
    core = request.config.rootpath
    return sorted(core.glob("[0-9][0-9]-*.md"))


def test_protocol_corpus_is_not_empty(protocols):
    assert len(protocols) >= 20, "the protocol corpus should not shrink unnoticed"


def test_every_protocol_has_a_title(protocols):
    untitled = []
    for path in protocols:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        if not any(line.startswith("# ") for line in lines):
            untitled.append(path.name)
    assert not untitled, f"protocols missing an H1 title: {untitled}"


def test_no_protocol_is_empty(protocols):
    empty = [p.name for p in protocols
             if len(p.read_text(encoding="utf-8-sig", errors="replace").strip()) < 50]
    assert not empty, f"protocol documents with no usable content: {empty}"


@pytest.mark.parametrize("index_file", ["00-identity.md", "README.md"])
def test_index_links_resolve(request, index_file):
    """A broken protocol link means the agent is pointed at a document that does not exist."""
    core = request.config.rootpath
    index = core / index_file
    assert index.exists(), f"{index_file} is missing"

    text = index.read_text(encoding="utf-8-sig", errors="replace")
    broken = []
    for target in LINK_PATTERN.findall(text):
        if target.startswith(("http", "mailto")):
            continue
        if not (core / target).exists():
            broken.append(target)

    assert not broken, f"{index_file} links to non-existent files: {broken}"


def test_registries_are_reachable_from_the_identity_index(request):
    """Identity is the entry point an agent reads first; core capabilities must be listed."""
    core = request.config.rootpath
    text = (core / "00-identity.md").read_text(encoding="utf-8-sig", errors="replace")
    for expected in ["55-self-evolution.md", "13-adapter-protocol.md"]:
        assert expected in text, f"{expected} is not referenced from 00-identity.md"
