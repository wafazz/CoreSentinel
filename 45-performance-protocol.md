# Performance & Scalability Protocol (`Iris perf`)

> **Two halves.** Everything from "Trigger" down is guidance for the projects
> CoreSentinel governs. The second half — [CoreSentinel's Own
> Performance](#coresentinels-own-performance) — is about this tool, and it is
> enforced rather than advised.

## Trigger
Activate when investigating high latency, database bottlenecks, memory leaks, high server CPU usage, or real-time event queue degradation. Command: `Iris perf`.

## Phase 1: Database & Query Profiling
1. **Identify Slow Queries**: Inspect query logs, run `EXPLAIN SELECT ...` on candidate slow queries.
2. **Indexing Check**: Verify composite indexes on multi-tenant tables (`(tenant_id, created_at)`, `(tenant_id, status)`).
3. **N+1 Query Elimination**: Audit loops in flat-module controllers for query execution inside `foreach`.
4. **Lock Contention**: Check for table locks or row locks (`FOR UPDATE`) missing proper transaction boundaries or index support.

## Phase 2: Application & Runtime Profiling
1. **I/O & Real-Time Events**: Audit long-poll loops (SSE, HTTP long polling) to ensure they never block single-threaded web server workers (e.g. PHP-FPM / Apache worker pool).
2. **Memory Leaks**: Profile CLI daemons (`bin/*.php`) for accumulating static variables or un-freed resources during execution loops.
3. **Async Queue Throughput**: Verify worker batching, job lock durations, and failed job retries.

## Phase 3: Benchmarking & Optimization
1. **Baseline Measurement**: Measure exact response time and memory usage before modifying code.
2. **Apply Targeted Fix**: Index creation, eager loading, caching, or async offloading.
3. **Re-benchmark**: Empirically verify performance improvements using load benchmarks or micro-benchmarks.

---

## CoreSentinel's Own Performance

> A tool that exists to reduce context waste has to be measured, or the claim is
> just a preference. This half is asserted by the self-test suite; the half above
> is advice.

### 📐 Published Budgets

Every budget lives in `coresentinel_core/observability/budgets.py`, names the
measurement that justifies it, and is asserted by `tests/performance/`. A limit
with no measured basis is a guess wearing a number.

| Budget | Limit | Measured | What it covers |
| :--- | ---: | ---: | :--- |
| `recall.10k_facts_ms` | 200 ms | 40 ms | Rank a query across a 10,000-fact store |
| `context.assemble_10k_facts_ms` | 1500 ms | 213 ms | Assemble a task-relevant pack over 10,000 facts |
| `storage.read_page_of_10k_ms` | 50 ms | 0.5 ms | Read the newest 20 records out of 10,000 |
| `storage.read_page_of_10k_mb` | 1.0 MB | 0.02 MB | Peak heap for that same read |
| `storage.append_800_records_ms` | 4000 ms | 465 ms | Append 800 records to an empty collection |
| `audit.emit_audited_event_ms` | 25 ms | 1.3 ms | One event, persisted and hash-chained |
| `runtime.bootstrap_ms` | 50 ms | 1.4 ms | Construct the runtime for a directory |
| **`audit.append_scaling_ratio`** | **3.0x** | **1.0x** | **Cost at 4,000 records over cost at zero** |

The last one is the only budget that is not a duration, and it is the most
important. Every other limit is in milliseconds and therefore describes the
machine as much as the code — a slower CI runner moves all of them at once. A
ratio holds on any hardware, and it pins the property that actually matters:
**writing record 4,000 must not cost more than writing record 1.**

Before Phase 11 that ratio was **11.4x and still climbing**. A trail that slows
down as it fills is a trail that gets turned off.

### 📈 Metrics

`coresentinel metrics` reports what this tool measures about itself, across
eleven subjects:

```text
command · service · agent · task · verification · gate
memory · context · recall · storage · audit
```

Two rules, inherited from the verification engine for the same reason:

1. **A series exists because something recorded a sample.** There are no
   zero-initialised counters. A subject nobody instrumented reports as *never
   observed* and `metrics coverage` names it. A zero would read as "this
   happened nought times", which is a measurement nobody took.
2. **A series costs the same at one sample as at a million.** Each keeps count,
   total, min, max and last — never the samples. The number of series is capped,
   and a dropped series is counted rather than silently discarded.

```bash
coresentinel metrics                    # series, coverage and budget verdict
coresentinel metrics --subject recall   # one subject
coresentinel metrics coverage           # which of the eleven have been measured
coresentinel metrics budgets            # the published limits and their basis
coresentinel metrics --json | jq '.budgets.verdict'
```

Exits 1 when a measured series is over its budget. A budget nothing measured is
`UNKNOWN`, and a report containing one is `INCOMPLETE` — never `WITHIN_BUDGET`.

> `coresentinel stats` reads the transcripts of AI hosts. `coresentinel metrics`
> measures CoreSentinel. They are different subjects and different commands.

### 📄 Pagination

Every list surface pages. Default 50, maximum 200, and a caller asking for more
gets `clamped: true` rather than silently fewer rows than requested.

```json
"page": { "limit": 50, "offset": 0, "returned": 20, "total": 20,
          "has_more": false, "next_offset": null, "clamped": false,
          "max_page_size": 200 }
```

`total` is `null` where counting it would cost what paging exists to avoid — a
ranked search cannot know its total without scoring every record. `null` and `0`
must not render the same way: one means *not counted*, the other means *none*.

Four read operations are exempt because their length is fixed by the code rather
than by the store — `project.inspect`, `agent.permissions`, `gate.status` and
`health.get` return one entry per dimension, contract or gate. The exemption is
listed with its reason in `tests/performance/test_pagination.py`, and a test
re-checks that each really is bounded. A new list operation that forgets to page
fails that suite the day it is added.

### 🧠 Bounded Memory

| Structure | Bound | Why it needed one |
| :--- | :--- | :--- |
| `EventBus.emitted` | 256 events (`events.buffer`) | Grew for the life of the process; a server retained every event it had ever seen |
| Metric series | 512 (`metrics.max_series`) | An in-memory registry keyed by anything user-derived is a leak |
| Each series | 5 numbers, `__slots__` | Retaining samples would grow with the work done |
| Repository reads | the requested page | Reading 20 of 10,000 records loaded all 10,000 and reversed them — 7 MB to answer a 20-record question |

`total_emitted` records how many events there really were, so a bounded buffer
never misreports the count it is bounding.
