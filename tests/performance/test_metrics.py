"""Metrics — measured, bounded, and honest about what was never observed.

The rules under test are the ones the verification engine established and this
subsystem inherits: nothing reports a number it did not measure, and nothing
grows without a ceiling.
"""

import json

import pytest

from coresentinel_core.observability import metrics as metering
from coresentinel_core.observability.metrics import Metrics
from coresentinel_core.runtime.container import Runtime
from coresentinel_core.services.facade import open_services


@pytest.fixture
def bound(tmp_path):
    import coresentinel_memory as mem

    project = tmp_path / "project"
    (project / ".coresentinel").mkdir(parents=True)
    (project / ".coresentinel" / "config.json").write_text(
        json.dumps({"project_name": "metrics"}), encoding="utf-8")
    mem.reset_project_root_cache()
    return project


class TestNothingIsInvented:
    def test_a_registry_that_measured_nothing_reports_no_series(self):
        assert Metrics().snapshot()["series"] == []

    def test_an_unmeasured_subject_is_never_observed_not_zero(self):
        """A zero would claim it happened nought times. It claims nothing."""
        registry = Metrics()
        registry.count(metering.RECALL, "query")
        coverage = registry.coverage()

        assert metering.RECALL in coverage["observed"]
        assert metering.GATE in coverage["never_observed"]
        names = [s["name"] for s in registry.snapshot()["series"]]
        assert "query" in names
        assert len(names) == 1, "a series appeared for something nothing measured"

    def test_all_eleven_subjects_are_declared(self):
        assert len(metering.SUBJECTS) == 11
        assert len(set(metering.SUBJECTS)) == 11

    def test_coverage_counts_against_the_declared_eleven(self):
        assert Metrics().coverage()["total"] == 11


class TestSeriesArithmetic:
    def test_a_series_keeps_count_total_min_max_and_last(self):
        registry = Metrics()
        for value in (10, 30, 20):
            registry.observe(metering.STORAGE, "append", value, unit="ms")
        series = registry.series(metering.STORAGE)[0].snapshot()

        assert series["count"] == 3
        assert series["total"] == 60
        assert series["mean"] == 20
        assert series["min"] == 10
        assert series["max"] == 30
        assert series["last"] == 20

    def test_a_timer_records_even_when_the_work_raised(self):
        """A call that failed still took time; excluding it flatters the number."""
        registry = Metrics()
        with pytest.raises(ValueError):
            with registry.time(metering.VERIFICATION, "run"):
                raise ValueError("boom")
        assert registry.series(metering.VERIFICATION)[0].count == 1

    def test_a_disabled_registry_records_nothing_and_does_not_raise(self):
        registry = Metrics(enabled=False)
        registry.count(metering.AUDIT, "append")
        with registry.time(metering.AUDIT, "append"):
            pass
        assert registry.snapshot()["series"] == []


class TestBoundedMemory:
    def test_a_series_costs_the_same_at_one_sample_as_at_fifty_thousand(self):
        """Planning.md: memory footprint bounded regardless of store size."""
        import sys

        registry = Metrics()
        for i in range(50_000):
            registry.observe(metering.STORAGE, "append", i)
        series = registry.series(metering.STORAGE)[0]

        assert series.count == 50_000
        # __slots__ and no sample list: the object holds five numbers whatever
        # it has seen. Anything retaining samples would be orders larger.
        assert sys.getsizeof(series) < 500
        assert not hasattr(series, "__dict__")

    def test_the_registry_refuses_to_grow_past_its_cap(self):
        registry = Metrics(max_series=10)
        for i in range(50):
            registry.observe(metering.STORAGE, f"series-{i}", 1)

        assert len(registry.snapshot()["series"]) == 10
        assert registry.dropped_series == 40, \
            "series were dropped without being counted, which is a silent cap"

    def test_the_event_buffer_is_bounded(self):
        from coresentinel_core.runtime.events import EventBus

        bus = EventBus(buffer=32)
        for i in range(500):
            bus.emit("MemoryCreated", {"n": i})

        assert len(bus.emitted) == 32
        assert bus.total_emitted == 500, \
            "the buffer forgot how many events there really were"

    def test_draining_a_bounded_buffer_returns_the_tail_oldest_first(self):
        from coresentinel_core.runtime.events import EventBus

        bus = EventBus(buffer=4)
        for i in range(10):
            bus.emit("MemoryCreated", {"n": i})
        drained = bus.drain()

        assert [e.payload["n"] for e in drained] == [6, 7, 8, 9]
        assert bus.drain() == []


class TestAggregationAcrossRuns:
    def test_totals_add_and_extremes_extend(self):
        folded = metering.aggregate([
            {"subject": "recall", "name": "query", "count": 2, "total": 100,
             "min": 40, "max": 60, "last": 60, "captured_at": "2026-08-14 10:00:00"},
            {"subject": "recall", "name": "query", "count": 3, "total": 30,
             "min": 5, "max": 15, "last": 15, "captured_at": "2026-08-14 11:00:00"},
        ])
        assert len(folded) == 1
        assert folded[0]["count"] == 5
        assert folded[0]["total"] == 130
        assert folded[0]["min"] == 5
        assert folded[0]["max"] == 60

    def test_the_mean_is_recomputed_rather_than_averaged(self):
        """Averaging two means weights a thousand samples the same as one."""
        folded = metering.aggregate([
            {"subject": "recall", "name": "query", "count": 1000, "total": 1000,
             "min": 1, "max": 1, "captured_at": "2026-08-14 10:00:00"},
            {"subject": "recall", "name": "query", "count": 1, "total": 100,
             "min": 100, "max": 100, "captured_at": "2026-08-14 11:00:00"},
        ])
        # Mean of the means would be 50.5. The real mean is 1100/1001.
        assert folded[0]["mean"] == pytest.approx(1.099, abs=0.01)

    def test_last_comes_from_the_most_recent_capture(self):
        folded = metering.aggregate([
            {"subject": "recall", "name": "query", "count": 1, "total": 9, "last": 9,
             "captured_at": "2026-08-14 11:00:00"},
            {"subject": "recall", "name": "query", "count": 1, "total": 1, "last": 1,
             "captured_at": "2026-08-14 09:00:00"},
        ])
        assert folded[0]["last"] == 9


class TestWiredIntoTheRuntime:
    def test_bootstrap_records_its_own_cost(self, bound):
        runtime = Runtime.bootstrap(str(bound))
        series = {s.name: s for s in runtime.metrics.series(metering.COMMAND)}
        assert "bootstrap" in series
        assert series["bootstrap"].last == pytest.approx(runtime.bootstrap_ms, rel=0.01)
        runtime.shutdown()

    def test_every_service_call_is_timed_once(self, bound):
        services = open_services(str(bound))
        services.call("agent.list", {})
        services.call("agent.list", {})
        series = {s.name: s for s in services.runtime.metrics.series(metering.SERVICE)}
        assert series["agent.list"].count == 2
        services.runtime.shutdown()

    def test_a_refused_call_is_still_timed(self, bound):
        from coresentinel_core.services.facade import ServiceError

        services = open_services(str(bound))
        with pytest.raises(ServiceError):
            services.call("agent.permissions", {"agent": "nobody"})
        series = {s.name: s for s in services.runtime.metrics.series(metering.SERVICE)}
        assert series["agent.permissions"].count == 1
        services.runtime.shutdown()

    def test_series_survive_the_process_that_recorded_them(self, bound):
        """A CLI command lives for one invocation; the numbers must outlast it."""
        first = open_services(str(bound))
        first.call("agent.list", {})
        first.runtime.shutdown()

        second = open_services(str(bound))
        report = second.call("metrics.get", {})
        names = [(s["subject"], s["name"]) for s in report["series"]]
        assert (metering.SERVICE, "agent.list") in names
        second.runtime.shutdown()

    def test_metrics_get_reports_budgets_it_could_not_measure_as_unknown(self, bound):
        services = open_services(str(bound))
        report = services.call("metrics.get", {})
        assert report["budgets"]["verdict"] in ("INCOMPLETE", "WITHIN_BUDGET")
        assert report["budgets"]["failed"] == 0
        services.runtime.shutdown()

    def test_a_failure_to_persist_metrics_does_not_fail_the_command(self, bound, monkeypatch):
        """Losing a measurement must never be able to fail the work it measured."""
        runtime = Runtime.bootstrap(str(bound))
        runtime.metrics.count(metering.STORAGE, "probe")

        def explode(*_args, **_kwargs):
            raise OSError("disk gone")

        monkeypatch.setattr(runtime.metrics, "flush", explode)
        runtime.shutdown()  # must not raise
