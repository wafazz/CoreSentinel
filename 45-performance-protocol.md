# Performance & Scalability Protocol (`Iris perf`)

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
