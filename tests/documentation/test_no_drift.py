"""Documentation must describe what exists.

R-10 names documentation drift as a High-likelihood risk, and it was already
real once: F-01 and F-02 were *documented as working* while the verification
engine fabricated the numbers behind them. The README described intent and read
as description.

The mitigation R-10 specifies is this file — every command named in the
documentation must exist in the registry, and every `--json` key the
documentation shows must appear in real output. Both are checked by running the
thing rather than by reading it.

Scope note: a "documented command" means a shell invocation — text inside a
fenced code block or an inline code span that begins with `coresentinel `. Prose
mentioning a word is not a claim that a command exists, and `import coresentinel
as cli` is not an invocation of a command called `as`.
"""

import json
import re
import subprocess
import sys

import pytest

# AGENTS.md is in here deliberately: it teaches commands to a fresh agent, so it
# is exactly the document whose drift would be most expensive, and exempting the
# contributor guide from the rule it documents would be absurd.
CORE_ROOT_DOCS = ["README.md", "AGENTS.md"]

# `coresentinel <verb>` at the start of a shell invocation.
INVOCATION = re.compile(r"(?:^|[\s(`$])coresentinel(?:\.py)?\s+(--?[a-z-]+|[a-z][a-z0-9-]*)")

FENCED = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)
INLINE = re.compile(r"`([^`\n]+)`")

# Commands whose --json payload the documentation shows, and the top-level keys
# it promises. Each is run for real below.
DOCUMENTED_JSON_KEYS = {
    "doctor": {"overall", "checks"},
    "status": {"gates"},
    "context": {"project", "git"},
    "review": {"findings", "verdict"},
    "metrics": {"series", "coverage", "budgets"},
}


@pytest.fixture(scope="module")
def registry():
    import coresentinel as cli
    return cli


@pytest.fixture(scope="module")
def known_names(registry):
    names = set()
    for entry in registry.COMMANDS:
        names.add(entry["name"])
        names.update(entry.get("aliases", []))
    return names


@pytest.fixture(scope="module")
def docs(core_dir):
    """Every protocol document plus the README, as (name, text)."""
    found = [(p.name, p.read_text(encoding="utf-8-sig"))
             for p in sorted(core_dir.glob("[0-9][0-9]-*.md"))]
    for name in CORE_ROOT_DOCS:
        path = core_dir / name
        if path.exists():
            found.append((name, path.read_text(encoding="utf-8-sig")))
    return found


def invocations(text):
    """Verbs invoked in code blocks and inline code spans, ignoring prose."""
    snippets = FENCED.findall(text) + INLINE.findall(text)
    verbs = set()
    for snippet in snippets:
        for line in snippet.splitlines():
            line = line.strip().lstrip("$ ").strip()
            if not line.startswith("coresentinel"):
                continue
            match = INVOCATION.search(" " + line)
            if match:
                verbs.add(match.group(1))
    return verbs


class TestDocumentedCommandsExist:
    def test_every_command_named_in_the_documentation_is_in_the_registry(
            self, docs, known_names):
        """A command the docs teach must be one the CLI answers to."""
        unknown = {}
        for name, text in docs:
            for verb in invocations(text):
                if verb not in known_names:
                    unknown.setdefault(verb, set()).add(name)

        assert not unknown, "documentation names commands that do not exist: " + "; ".join(
            f"'{verb}' in {', '.join(sorted(where))}" for verb, where in sorted(unknown.items()))

    def test_the_extractor_would_actually_catch_drift(self, known_names):
        """Guards the guard.

        A drift test that silently matches nothing passes forever. This proves
        the extractor finds real invocations and rejects an invented one.
        """
        text = "```bash\ncoresentinel doctor --json\ncoresentinel notacommand\n```"
        verbs = invocations(text)
        assert "doctor" in verbs, "the extractor found no invocation in an obvious code block"
        assert "notacommand" in verbs
        assert "notacommand" not in known_names

    def test_prose_is_not_read_as_an_invocation(self):
        """`import coresentinel as cli` must not assert a command called `as`."""
        assert "as" not in invocations("`import coresentinel as cli`")

    def test_every_registered_command_is_documented_somewhere(self, registry, docs):
        """A feature nobody documented is a feature nobody can use."""
        corpus = "\n".join(text for _, text in docs)
        missing = [entry["name"] for entry in registry.COMMANDS
                   if f"`{entry['name']}`" not in corpus
                   and f"coresentinel {entry['name']}" not in corpus]
        assert not missing, f"registered but undocumented: {', '.join(missing)}"


class TestDocumentedJsonKeysExist:
    @pytest.mark.parametrize("command,keys", sorted(DOCUMENTED_JSON_KEYS.items()))
    def test_the_json_payload_carries_the_keys_the_docs_show(
            self, core_dir, tmp_path, command, keys):
        """Run it. A documented key that is not in real output is drift."""
        result = subprocess.run(
            [sys.executable, str(core_dir / "coresentinel.py"), command, "--json"],
            cwd=str(core_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180)

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(f"'{command} --json' did not emit JSON: {exc}\n"
                        f"stdout head: {result.stdout[:300]}")

        missing = sorted(k for k in keys if k not in payload)
        assert not missing, (f"'{command} --json' is documented as carrying {sorted(keys)} "
                             f"but {missing} is absent from real output")


class TestTheReadmeDescribesWhatWasMeasured:
    def test_the_command_surface_block_lists_only_real_commands(self, core_dir, known_names):
        """The README prints a grouped command surface. Every verb in it must exist."""
        readme = (core_dir / "README.md").read_text(encoding="utf-8-sig")
        block = re.search(r"Setup & Diagnostics(.*?)```", readme, re.DOTALL)
        assert block, "the README no longer carries a command surface block"

        listed = set()
        for line in block.group(1).splitlines():
            if "·" not in line:
                continue
            # "Context & Memory         context · project · ..." — the group
            # label is itself space-separated, so split on the run of spaces
            # that separates it from the verbs and keep the tail.
            verbs = re.split(r"\s{2,}", line.strip())[-1]
            listed.update(v.strip() for v in verbs.split("·") if v.strip())

        unknown = sorted(v for v in listed if v not in known_names)
        assert not unknown, f"the README's command surface names {unknown}, which do not exist"

    def test_the_advertised_test_count_is_not_above_the_real_one(self, core_dir):
        """The README states a test count. It must not claim more than exist.

        Counted by collection rather than by execution, so this stays fast. An
        understated count is allowed — the number goes stale downward between
        phases, and that is honest. Overstating is the failure.
        """
        readme = (core_dir / "README.md").read_text(encoding="utf-8-sig")
        claimed = re.search(r"([\d,]+)\s+tests across", readme)
        assert claimed, "the README no longer states a test count"
        advertised = int(claimed.group(1).replace(",", ""))

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
            cwd=str(core_dir), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600)
        collected = re.search(r"(\d+)\s+tests? collected", result.stdout)
        assert collected, f"could not count the suite: {result.stdout[-300:]}"

        real = int(collected.group(1))
        assert advertised <= real, (
            f"the README advertises {advertised} tests; the suite collects {real}")
