# ChronosMatch: Zero-Copy High-Frequency Trading Engine

ChronosMatch is an educational Python project that simulates a high-frequency
trading (HFT) order-processing pipeline. It brings together fixed-width binary
order records, an `mmap`-backed single-producer/single-consumer (SPSC) ring
buffer, a price-time-priority limit order book, synthetic order generation,
local performance measurements, and a terminal dashboard.

The title references zero-copy concepts, but the application is not an
end-to-end zero-copy system: orders are encoded into the ring buffer and
decoded into Python `Order` objects on the consumer side. This is a local
simulation, not a live trading application. It has no exchange connectivity,
order routing, or production latency guarantees.

## Project status

The Python implementation was checked on 2026-10-27 in this workspace on
Windows 11 with Python 3.14.6. The observed validation was:

- `python -m pytest -q` — **41 passed**.
- `python -m compileall -q .` — completed successfully.
- `python main.py struct-test` — passed.
- `python main.py ring-test` — passed.
- `python main.py verify` — matching correctness checks passed.
- `python scripts/run_demo.py --duration 1 --target-ops 10000` — completed;
  all 4,032 enqueued orders were processed and no orders were dropped in that
  run.
- `python main.py audit --orders 1000` — all four audit workloads completed.

Demo counts and benchmark timings are observations from one machine and one
run, not expected rates or performance promises. Synthetic orders and local
system load can change the results. Pytest emitted a non-fatal
`pytest-asyncio` deprecation warning about its default fixture loop scope.

## Features

- BUY/SELL orders with numeric validation and fixed-size binary serialization.
- An `mmap`-backed FIFO ring buffer with full/empty detection and wraparound.
- Thread synchronization and cooperating cross-process synchronization:
  Windows named mutexes and POSIX `flock`.
- A price-time-priority limit order book with best-price execution, FIFO
  priority at equal prices, partial fills, multiple fills, and resting
  residual orders.
- An asynchronous synthetic-order producer, an integrated producer/consumer
  demo, and separate-process producer and consumer scripts.
- In-process order, trade, volume, latency, and throughput metrics.
- Matching verification, serialization/transport audit, and ANSI terminal
  dashboard.
- Regression tests for serialization, buffer behavior, matching, and pipeline
  behavior.

See [features.md](./features.md) for a detailed inventory of implemented
features and limitations. See [expected-results.md](./expected-results.md) for
what the project commands are expected to do.

## Requirements

- Python **3.14.6** is the version validated for this workspace.
- `pip`
- Windows PowerShell or another terminal

Runtime dependencies are listed in `hft_engine\requirements.txt`:

- `sortedcontainers==2.4.0`

Development dependencies are listed in
`hft_engine\requirements-dev.txt`:

- the runtime requirements
- `pytest==9.1.1`

The optional Cython source in `hft_engine\cython_src` is not needed for the
Python CLI. It has not been built or validated as part of the checks above.

## Install

Open PowerShell in the repository root (the folder containing this README):

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\hft_engine\requirements-dev.txt
Set-Location .\hft_engine
```

Confirm that `python --version` reports `Python 3.14.6`. If you have multiple
Python installations, create the virtual environment with the intended Python
interpreter and select that environment in VS Code.

If PowerShell prevents environment activation, invoke the virtual-environment
interpreter directly from the repository root:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r .\hft_engine\requirements-dev.txt
```

Then enter `hft_engine` and substitute `..\.venv\Scripts\python.exe` for
`python` in the commands below.

## Run commands

Run application commands from the `hft_engine` directory.

### Smoke tests and matching verification

```powershell
python main.py struct-test
python main.py ring-test
python main.py verify
```

`struct-test` checks BUY and SELL binary round trips. `ring-test` checks a
16-slot buffer through full and empty states. `verify` runs matching
correctness scenarios and a local latency sample; it exits unsuccessfully if
a correctness check fails.

### Integrated demo

```powershell
python scripts/run_demo.py --duration 2 --target-ops 50000
```

This runs a producer and consumer in the same process, sends decoded orders to
the matching engine, drains pending work, and reports counts and timing from
that run. `--duration` is in seconds and `--target-ops` is a requested order
generation rate, not a guaranteed rate. Because generated orders are random,
counts and matching results can vary.

### Serialization and transport audit

```powershell
python main.py audit --orders 10000
```

The audit compares measured mmap-ring, `struct`, pickle, and JSON workloads.
It reports local timing and throughput information. These methods have
different allocation and serialization costs, so their relative results are
not proof that the complete application is zero-copy or that one method is
universally faster.

### Standalone firehose

```powershell
python main.py firehose --duration 5 --target-ops 100000
```

This command produces orders into a bounded ring buffer without running a
consumer. The buffer can fill, and subsequent orders may be counted as
dropped.

### Terminal dashboard

```powershell
python main.py dashboard --duration 5 --target-ops 50000
```

The ANSI dashboard runs the in-process producer, ring buffer, and matching
engine, then displays counters, recent rates, latency summaries, and book
depth. Use an ANSI-capable terminal. The HTML page at
`hft_engine\ui\web_dashboard.html` is a separate visual mock-up; it is not
connected to the running Python engine or its metrics.

## Separate producer and consumer processes

These scripts demonstrate the shared-file ring buffer with two local
processes. Open two PowerShell terminals at the repository root. Start the
consumer first; it waits for the backing file to appear.

**Terminal 1 — consumer:**

```powershell
Set-Location .\hft_engine
$ipcPath = Join-Path $env:TEMP 'chronosmatch.rb'
python scripts/run_consumer.py --path $ipcPath --timeout 60
```

**Terminal 2 — producer:**

```powershell
Set-Location .\hft_engine
$ipcPath = Join-Path $env:TEMP 'chronosmatch.rb'
python scripts/run_producer.py --path $ipcPath --duration 10 --target-ops 50000
```

Both processes must use the same path and capacity. The producer creates or
truncates the backing file on startup; do not use a path containing data that
must be preserved. The consumer stops after its configured idle timeout
because there is no dedicated producer-completion message. Use `Ctrl+C` to
stop it earlier. Producer and consumer metrics are separate and are not
combined into one report.

## Tests and local verification

From `hft_engine`, run:

```powershell
python -m pytest -q
python -m compileall -q .
```

The tests cover:

- BUY and SELL binary serialization, field boundaries, invalid values, and
  malformed records.
- Ring-buffer empty/full states, FIFO ordering, wraparound, invalid files and
  counters, malformed slots, cleanup, and cross-process synchronization.
- Best-price matching, FIFO at equal prices, partial fills, residual orders,
  non-crossing orders, and invalid submissions.
- Producer/buffer/engine integration, producer stop behavior, and metrics
  edge cases.
- A non-zero verification exit when a correctness check fails.

To reproduce the core smoke checks from the same directory:

```powershell
python main.py struct-test
python main.py ring-test
python main.py verify
python scripts/run_demo.py --duration 1 --target-ops 10000
python main.py audit --orders 1000
```

The validation results in the [Project status](#project-status) section were
executed in this workspace. Rerun these commands after changing source code or
dependencies; historical results do not establish that a later checkout
passes.

## Architecture

### Order record

Each order occupies 21 bytes and uses the Python `struct` format `=QdIb`:

| Field | Encoding | Size |
| --- | --- | ---: |
| `order_id` | Unsigned 64-bit integer | 8 bytes |
| `price` | 64-bit floating-point number | 8 bytes |
| `quantity` | Unsigned 32-bit integer | 4 bytes |
| `side` | Signed 8-bit integer (`+1` BUY, `-1` SELL) | 1 byte |

The model rejects out-of-range identifiers and quantities, non-finite or
non-positive prices, and invalid sides. The `=` prefix uses native byte order
with standard field sizes and no alignment padding. Treat this as a local IPC
format, not a portable network protocol.

### Ring buffer

The mmap file contains a 16-byte header (64-bit head and tail counters) and
fixed-size order slots. `put(order)` returns `False` when the buffer is full;
`get()` returns `None` when it is empty. Both operations preserve FIFO order
and support wraparound. A thread lock protects access inside a process;
cooperating processes use a Windows named mutex or POSIX `flock`.

The documented topology is one producer and one consumer using the same file
path and capacity. Empty/full operations do not wait for queue space or data,
although lock acquisition itself can block.

### Matching engine and measurements

The Python limit order book uses `sortedcontainers` to order bids by highest
price then insertion sequence, and asks by lowest price then insertion
sequence. Incoming orders execute against eligible resting orders at the
resting price. Partial fills leave any remaining quantity on the book.

Timing and throughput outputs are local measurements. Results depend on the
Python runtime, operating system, workload, machine, and background load.
They should be compared only under similar conditions and are not latency
guarantees.

## Project layout

```text
ChronosMatch-Roadmap              Development roadmap
features.md                       Feature inventory and limitations
expected-results.md               Command behavior reference
hft_engine/
├── main.py                       Unified command-line interface
├── requirements.txt              Runtime dependencies
├── requirements-dev.txt          Runtime dependencies and pytest
├── setup.py                      Optional Cython build configuration
├── core/
│   ├── constants.py              Shared binary and runtime constants
│   ├── order_struct.py           Order validation and serialization
│   ├── ring_buffer.py            mmap-backed SPSC ring buffer
│   ├── firehose.py               Synthetic asynchronous order producer
│   └── metrics.py                Latency and throughput counters
├── engine/
│   └── limit_order_book.py       Price-time-priority matching engine
├── bench/
│   ├── engine_verify.py          Matching checks and latency sample
│   └── ipc_audit.py              Serialization and transport audit
├── scripts/
│   ├── run_demo.py               Integrated producer/consumer demo
│   ├── run_producer.py           Separate-process producer
│   └── run_consumer.py           Separate-process consumer
├── tests/                        Pytest regression tests
├── ui/
│   ├── dashboard.py              ANSI terminal dashboard
│   └── web_dashboard.html        Standalone visual mock-up
└── cython_src/
    └── lob.pyx                   Experimental optional Cython source
```

## Limitations and safety

- Use synthetic orders only. This project does not connect to an exchange or
  place real trades.
- The application is not production trading infrastructure and provides no
  guaranteed throughput or latency.
- The Python pipeline is not end-to-end zero-copy; order objects are
  serialized and reconstructed.
- `cython_src\lob.pyx` is optional, is not used by the Python CLI, and has not
  been built or validated for Python 3.14.6.
- The HTML dashboard is not live telemetry.
- The repository does not currently specify a license. Add an appropriate
  license before redistributing the project under defined reuse terms.
- Review staged files before committing, and do not include credentials,
  private keys, local `.env` files, or other secrets.

## Troubleshooting

- **Import error:** Confirm that the active directory is `hft_engine`, the
  project environment is active, and `requirements-dev.txt` is installed.
- **Unexpected Python version:** Run `python --version` and select the
  intended Python 3.14.6 interpreter or virtual environment.
- **Consumer cannot find the backing file:** Start the consumer and producer
  with the same path; the consumer waits up to 10 seconds for the file.
- **Interrupted or stale IPC file:** Stop the participating processes. The
  producer recreates and truncates its configured file at startup.
- **Variable benchmark values:** This is expected; timings and rates depend
  on the machine, runtime, workload, and system load.
- **Cython build problem:** Cython is optional. The regular Python CLI and
  tests do not require it.

## Roadmap and license

[ChronosMatch-Roadmap](./ChronosMatch-Roadmap) records planned work and
development phases; it is not a guarantee of future milestones. No license is
currently specified in the repository.
