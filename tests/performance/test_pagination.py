"""Pagination — enforced on every list surface, not offered by some of them.

A list endpoint with no ceiling is a way to ask a governance tool to read its
whole audit trail into memory and hand it back in one response. The point of
these tests is that the enforcement is derived from the catalogue rather than
from a list somebody remembered to update: a new list operation that forgets to
page fails here the day it is added.
"""

import json

import pytest

from coresentinel_core.services.facade import Services, open_services
from coresentinel_core.storage.json_store import JsonStore
from coresentinel_core.storage.ports import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, clamp_page
from coresentinel_core.storage.sqlite_store import SqliteStore

# Read operations that return a collection. Each must return a `page` block.
LIST_OPERATIONS = {
    "project.list": {},
    "memory.search": {"query": "anything"},
    "decision.search": {},
    "agent.list": {},
    "agent.status": {},
    "task.list": {},
    "incident.list": {},
    "pattern.search": {},
    "audit.list": {},
    "metrics.get": {},
}

# Read operations that return a list but are deliberately NOT paged, each with
# the reason. These are fixed enumerations — their length is set by the code,
# not by how much is in the store — so paging them would add a page block to a
# response that can never exceed a dozen entries. The test below re-checks that
# claim rather than trusting this comment.
UNPAGED_BY_DESIGN = {
    "project.inspect": ("unknown_dimensions", 20,
                        "one entry per discovery dimension; there are ten"),
    "agent.permissions": ("declared", 40,
                          "one entry per squad contract; there are seventeen"),
    "gate.status": ("pipeline", 20,
                    "the gate pipeline is a fixed, ordered list of stage names"),
    "health.get": ("unknown_dimensions", 20,
                   "one entry per health dimension; there are seven"),
}


@pytest.fixture
def services(tmp_path):
    import coresentinel_memory as mem

    project = tmp_path / "project"
    (project / ".coresentinel").mkdir(parents=True)
    (project / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "paging"}), encoding="utf-8")
    mem.reset_project_root_cache()

    bound = open_services(str(project))
    yield bound
    bound.runtime.shutdown()


class TestTheCatalogueStaysCovered:
    def test_every_operation_named_here_still_exists(self):
        """Guards the guard: a renamed operation must not silently stop being tested."""
        for name in LIST_OPERATIONS:
            assert name in Services.OPERATIONS, \
                f"{name} is asserted to page but is no longer in the catalogue"

    def test_no_read_operation_returning_a_collection_is_missing_from_this_suite(self, services):
        """A new list endpoint that forgets to page fails here.

        Any read operation whose result carries a list-valued key is a list
        endpoint, whether or not anyone remembered to say so.
        """
        missed = []
        for name, (mode, _) in Services.OPERATIONS.items():
            if mode != "read" or name in LIST_OPERATIONS or name in UNPAGED_BY_DESIGN:
                continue
            try:
                result = services.call(name, {})
            except Exception:
                continue  # needs arguments; covered by its own tests
            if not isinstance(result, dict):
                continue
            collections = [k for k, v in result.items()
                           if isinstance(v, list) and len(v) > 0 and k != "page"]
            if collections:
                missed.append(f"{name} returns {collections} and is neither paged "
                              f"nor listed in UNPAGED_BY_DESIGN with a reason")
        assert not missed, "; ".join(missed)

    @pytest.mark.parametrize("operation", sorted(UNPAGED_BY_DESIGN))
    def test_an_unpaged_list_really_is_bounded_by_the_code(self, services, operation):
        """The exemption has to keep being true.

        Each of these is exempt because its length comes from a fixed
        enumeration. If one ever starts returning data proportional to the
        store, the exemption stops being justified and this fails.
        """
        key, ceiling, reason = UNPAGED_BY_DESIGN[operation]
        result = services.call(operation, {})
        assert len(result.get(key, [])) <= ceiling, (
            f"{operation}.{key} exceeded {ceiling} entries — it is exempt from paging "
            f"because {reason}, which no longer holds")


class TestEveryListOperationPages:
    @pytest.mark.parametrize("operation", sorted(LIST_OPERATIONS))
    def test_returns_a_paging_block(self, services, operation):
        result = services.call(operation, dict(LIST_OPERATIONS[operation]))
        assert "page" in result, f"{operation} returned no paging block"
        page = result["page"]
        for field in ("limit", "offset", "returned", "has_more", "clamped", "max_page_size"):
            assert field in page, f"{operation} paging block has no '{field}'"

    @pytest.mark.parametrize("operation", sorted(LIST_OPERATIONS))
    def test_honours_an_explicit_limit(self, services, operation):
        arguments = dict(LIST_OPERATIONS[operation], limit=3)
        page = services.call(operation, arguments)["page"]
        assert page["limit"] == 3
        assert page["returned"] <= 3

    @pytest.mark.parametrize("operation", sorted(LIST_OPERATIONS))
    def test_clamps_a_limit_above_the_maximum_and_says_it_did(self, services, operation):
        arguments = dict(LIST_OPERATIONS[operation], limit=10_000)
        page = services.call(operation, arguments)["page"]
        assert page["limit"] == MAX_PAGE_SIZE
        assert page["clamped"] is True, \
            f"{operation} silently returned fewer records than were asked for"

    @pytest.mark.parametrize("operation", sorted(LIST_OPERATIONS))
    def test_a_limit_arriving_as_a_string_is_still_enforced(self, services, operation):
        """Query strings arrive as text. `?limit=10000` must clamp, not crash."""
        arguments = dict(LIST_OPERATIONS[operation], limit="10000")
        page = services.call(operation, arguments)["page"]
        assert page["limit"] == MAX_PAGE_SIZE


class TestClamping:
    def test_a_missing_limit_becomes_the_default(self):
        assert clamp_page(None, 0) == (DEFAULT_PAGE_SIZE, 0, False)

    def test_zero_and_negative_limits_do_not_mean_everything(self):
        """`?limit=0` must not be read as "no ceiling"."""
        for asked in (0, -1, -10_000):
            limit, _, _ = clamp_page(asked, 0)
            assert limit == DEFAULT_PAGE_SIZE

    def test_a_negative_offset_is_not_a_slice_from_the_end(self):
        assert clamp_page(10, -5)[1] == 0

    def test_unparseable_values_fall_back_rather_than_raise(self):
        assert clamp_page("banana", "elsewhere") == (DEFAULT_PAGE_SIZE, 0, False)

    def test_the_maximum_is_reported_as_not_clamped(self):
        assert clamp_page(MAX_PAGE_SIZE, 0)[2] is False


class TestPagesWalkTheWholeCollection:
    @pytest.mark.parametrize("store_cls", [JsonStore, SqliteStore])
    def test_paging_visits_every_record_exactly_once(self, tmp_path, store_cls):
        store = store_cls(str(tmp_path / store_cls.backend))
        repo = store.repository("audit_events")
        for i in range(55):
            repo.append({"subject": "verification", "actor": "fixture", "action": f"a{i}"})

        seen, offset = [], 0
        while True:
            page = repo.page(10, offset)
            if not page:
                break
            seen.extend(r["action"] for r in page)
            offset += 10

        assert len(seen) == 55
        assert len(set(seen)) == 55, "a record appeared on two pages"
        assert seen[0] == "a54", "pages are not newest-first"
        store.close()

    @pytest.mark.parametrize("store_cls", [JsonStore, SqliteStore])
    def test_an_offset_past_the_end_is_empty_rather_than_an_error(self, tmp_path, store_cls):
        store = store_cls(str(tmp_path / store_cls.backend))
        store.audit_events.append({"subject": "verification", "actor": "f", "action": "only"})
        assert store.audit_events.page(10, 500) == []
        store.close()

    @pytest.mark.parametrize("store_cls", [JsonStore, SqliteStore])
    def test_both_backends_agree_on_the_same_page(self, tmp_path, store_cls):
        """The port contract: swapping the backend must not change the answer."""
        store = store_cls(str(tmp_path / store_cls.backend))
        for i in range(30):
            store.audit_events.append({"subject": "verification", "actor": "f",
                                       "action": f"a{i}"})
        page = store.audit_events.page(5, 10)
        assert [r["action"] for r in page] == [f"a{i}" for i in (19, 18, 17, 16, 15)]
        store.close()


class TestHasMoreIsHonest:
    def test_a_full_first_page_reports_more_to_come(self, services):
        for i in range(8):
            services.call("audit.record", {"actor": "fixture", "action": f"a{i}"})
        page = services.call("audit.list", {"limit": 3})["page"]
        assert page["has_more"] is True
        assert page["next_offset"] == 3

    def test_the_last_page_does_not_promise_another(self, services):
        for i in range(4):
            services.call("audit.record", {"actor": "fixture", "action": f"a{i}"})
        page = services.call("audit.list", {"limit": 50})["page"]
        assert page["has_more"] is False
        assert page["next_offset"] is None

    def test_an_uncounted_collection_reports_no_total_rather_than_zero(self, services):
        """Ranked search cannot know its total without scoring everything.

        Reporting 0 there would be a measurement nobody took.
        """
        page = services.call("memory.search", {"query": "anything", "limit": 2})["page"]
        assert page["total"] is None
        assert page["has_more"] in (True, False)
