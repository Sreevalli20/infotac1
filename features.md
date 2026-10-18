# ChronosMatch Features

ChronosMatch is an educational Python project that simulates an order-processing
pipeline. This document describes what is implemented in the repository, how
the pieces fit together, and which capabilities remain experimental or
simulated.

> **Scope:** The project does not connect to an exchange or place real trades.
> Although “Zero-Copy” appears in the project title, the Python pipeline is not
> end-to-end zero-copy: orders are serialized into the ring buffer and decoded
> into Python `Order` objects by the consumer.

## Implemented features

### Binary order model and wire record

- Defines BUY (`+1`) and SELL (`-1`) order sides.
- Serializes each order into a fixed 21-byte `=QdIb` record:

  | Field | Binary type | Size |
  | --- | --- | ---: |
  | Order identifier | Unsigned 64-bit integer | 8 bytes |
  | Price | 64-bit floating-point value | 8 bytes |
  | Quantity | Unsigned 32-bit integer | 4 bytes |
  | Side | Signed 8-bit integer | 1 byte |

- Provides `pack_order`, `unpack_order`, `pack_into_buffer`, and
  `unpack_from_buffer` helpers.
- Validates order identifier and quantity ranges, positive finite prices, and
  valid sides. Malformed record lengths and invalid decoded values are rejected.
- The `=` struct prefix uses native byte order with standard field sizes and no
  alignment padding. Treat this layout as local-host IPC, not a portable
  network protocol.

### mmap-backed SPSC ring buffer

- Stores fixed-width records in a circular region of a memory-mapped file.
- Uses a 16-byte header: an unsigned 64-bit head counter and an unsigned 64-bit
  tail counter, followed by the order slots.
- Provides non-waiting queue semantics: `put(order)` returns `False` when full;
  `get()` returns `None` when empty.
- Supports FIFO reads and writes, including wraparound.
- Validates capacity, backing-file size, counters, and decoded slot contents.
- Uses a thread lock for access within a process. Cooperating processes opening
  the same path use a Windows named mutex or POSIX `flock`.
- Supports context-manager use and explicit flushing and closing.
- Intended for one producer and one consumer using the same file path and
  capacity. Lock acquisition may wait even though empty/full queue operations
  do not wait for an item or free slot.

### Price-time-priority matching engine

- Maintains separate bid and ask books ordered by price and insertion sequence.
- A BUY can execute against resting asks at or below its limit; a SELL can
  execute against resting bids at or above its limit.
- Selects the best eligible resting price first and preserves FIFO priority
  among orders at the same price.
- Executes at the resting order’s price.
- Supports partial fills, multiple execution records, and residual quantities
  remaining on the book.
- Reports best bid and ask, book depth, top-of-book levels, totals, and the
  elapsed time of the latest matching operation.
- Rejects non-`Order` submissions and revalidates mutable order values before
  modifying the book.

### Simulated order producer and integrated demo

- `core.firehose.Firehose` generates random synthetic orders and writes them to
  a supplied ring buffer.
- Uses configurable target operations per second and duration, with positive
  finite input validation.
- Tracks sent and dropped orders and supports a stop request.
- `scripts/run_demo.py` runs a producer and consumer in one process, feeds
  orders into the matching engine, drains queued orders, joins its consumer
  thread, and closes the temporary ring-buffer file.
- The demo reports counts and timing from its actual run. Its random input is
  not seeded, so measured results can vary between runs.

### Separate-process tools

- `scripts/run_producer.py` creates a ring-buffer file and writes synthetic
  orders into it.
- `scripts/run_consumer.py` opens that file and processes orders through the
  matching engine.
- Both tools must use the same backing-file path and buffer capacity.
- The consumer uses an idle timeout rather than receiving a dedicated producer
  completion message; it can also be stopped with `Ctrl+C`.
- These scripts do not share the in-process `EngineMetrics` object or provide a
  combined producer-and-consumer report.

### Metrics, verification, and benchmarks

- Collects in-process order, trade, volume, and drop counts.
- Records rolling latency samples and percentile summaries, including average,
  minimum, maximum, P50, P90, P99, and P99.9.
- Tracks recent enqueue and dequeue rates using monotonic time.
- Handles empty latency measurements without division by zero and validates
  non-finite or negative samples.
- `bench/engine_verify.py` checks matching scenarios and prints a local latency
  sample for completed submissions. Correctness checks do not enforce a fixed
  speed threshold.
- `bench/ipc_audit.py` compares measured mmap-ring, struct, pickle, and JSON
  workloads and reports the Python version, platform, workload, payload
  accounting, and elapsed time.
- Benchmark methods have different allocation and serialization costs; their
  ratios are local observations, not proof that mmap is faster, avoids all
  copying, or meets a performance guarantee.
- The verification command exits unsuccessfully when a correctness check
  fails.

### Terminal dashboard

- `ui/dashboard.py` runs the in-process producer, ring buffer, and matching
  engine and displays current counters, recent rates, latency samples, and book
  depth in an ANSI terminal dashboard.
- Uses a temporary ring-buffer file and worker threads, then requests producer
  shutdown, drains queued orders, joins workers, and closes resources.
- The dashboard is a local simulation and its observed values depend on the
  machine and workload.

## Available commands

Run these from the `hft_engine` directory after installing dependencies:

```powershell
python main.py struct-test
python main.py ring-test
python main.py verify
python scripts/run_demo.py --duration 2 --target-ops 50000
python main.py audit --orders 10000
python main.py dashboard --duration 5 --target-ops 50000
python -m pytest -q
python -m compileall -q .
```

The unified CLI also provides `firehose`:

```powershell
python main.py firehose --duration 5 --target-ops 100000
```

This standalone producer writes into its ring buffer without a consumer, so the
buffer can fill and later orders may be counted as dropped.

## Automated test coverage

The pytest suite currently covers:

- BUY and SELL binary round trips, numeric boundaries, invalid fields,
  malformed record sizes, and mutated order validation.
- Empty/full ring-buffer behavior, FIFO order, wraparound, capacity and file
  validation, malformed slots, counter corruption, and Windows spawned-process
  synchronization.
- Best-price matching, FIFO priority at equal prices, partial fills, residual
  orders, non-crossing orders, and invalid matching inputs.
- Producer/buffer/engine integration, valid generated values, producer stop
  requests, invalid parameters, and metrics edge cases.
- Non-success exit status when the verification CLI encounters a failed check.

The recorded Windows/Python 3.14.6 run reported 41 passing tests and successful
Python compilation. These results describe the tested Python implementation;
they do not verify the optional Cython module or the HTML mock-up.

## Experimental or not connected

- `cython_src/lob.pyx` is an optional experimental implementation. It is not
  used by the Python CLI and has not been built or validated against the Python
  matching engine on Python 3.14.6.
- `ui/web_dashboard.html` is a standalone browser mock-up. It generates
  illustrative values in JavaScript and is not connected to the Python engine,
  mmap file, or measured metrics.
- The project has no live exchange connectivity, order routing, production
  deployment, or guaranteed latency targets.
- The Python engine is not an end-to-end zero-copy pipeline.

For setup commands and general project details, see [README.md](./README.md).
For planned work and project progress, see
[ChronosMatch-Roadmap](./ChronosMatch-Roadmap).
