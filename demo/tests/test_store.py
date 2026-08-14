"""taskflow's own suite. CoreSentinel runs this to earn its Testing evidence."""

import pytest

from taskflow.store import BLOCKED, DONE, OPEN, TaskStore, UnknownTask


@pytest.fixture
def store():
    return TaskStore()


class TestAdding:
    def test_a_new_task_starts_open(self, store):
        assert store.add("write the migration guide").status == OPEN

    def test_ids_are_sequential_and_do_not_repeat(self, store):
        ids = [store.add(f"task {i}").id for i in range(5)]
        assert ids == ["TASK-0001", "TASK-0002", "TASK-0003", "TASK-0004", "TASK-0005"]
        assert len(set(ids)) == 5

    def test_a_blank_title_is_refused(self, store):
        with pytest.raises(ValueError):
            store.add("   ")

    def test_the_title_is_trimmed(self, store):
        assert store.add("  spaced  ").title == "spaced"


class TestReading:
    def test_an_unknown_id_raises_rather_than_returning_none(self, store):
        """Returning None would push the failure to the caller's next line."""
        with pytest.raises(UnknownTask):
            store.get("TASK-9999")

    def test_listing_is_newest_first(self, store):
        store.add("first")
        newest = store.add("second")
        assert store.list()[0].id == newest.id

    def test_listing_pages(self, store):
        for i in range(10):
            store.add(f"task {i}")
        assert len(store.list(limit=3)) == 3
        assert len(store.list(limit=3, offset=9)) == 1

    def test_listing_filters_by_status(self, store):
        store.add("stays open")
        store.complete(store.add("gets done").id)
        assert len(store.list(status=DONE)) == 1
        assert len(store.list(status=OPEN)) == 1

    def test_an_unknown_status_filter_is_refused(self, store):
        with pytest.raises(ValueError):
            store.list(status="nonsense")


class TestTransitions:
    def test_completing_marks_done(self, store):
        assert store.complete(store.add("ship it").id).status == DONE

    def test_blocking_requires_a_reason(self, store):
        """A blocked task with no reason is one nobody can unblock."""
        task = store.add("waiting on review")
        with pytest.raises(ValueError):
            store.block(task.id, "")

    def test_blocking_with_a_reason_works(self, store):
        task = store.add("waiting on review")
        assert store.block(task.id, "needs the API key rotated").status == BLOCKED

    def test_counts_cover_every_status(self, store):
        store.add("open one")
        store.complete(store.add("done one").id)
        store.block(store.add("blocked one").id, "upstream")
        assert store.counts() == {OPEN: 1, DONE: 1, BLOCKED: 1}
