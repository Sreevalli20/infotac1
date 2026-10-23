# ChronosMatch — Zero-Copy High-Frequency Trading Engine

ChronosMatch is an educational Python prototype that simulates an order
processing pipeline. It brings together fixed-width binary order records, an
`mmap`-backed single-producer/single-consumer (SPSC) ring buffer, a
price-time-priority limit order book, a synthetic order producer, local
performance measurements, and a terminal dashboard.

The title reflects the project's exploration of zero-copy techniques, not a
claim about the complete Python pipeline. Orders are packed into the ring
buffer and reconstructed as Python objects by the consumer. This is not a live
trading system, does not connect to an exchange, and provides no production or
latency guarantees.

## Current status

The current project checkout was validated on Windows 11 with Python 3.14.6:

- `python -m pytest -q` — **41 passed**.
- `python -m compileall -q .` — completed successfully.
- `python main.py struct-test` and `python main.py ring-test` — both passed.
- `python main.py verify` — all matching checks passed.
- `python scripts/run_demo.py --duration 2 --target-ops 50000` — completed
  without dropped orders in the observed run.

These are measured results from the present workspace and can vary between runs.

## Features

- Validated BUY and SELL order model and fixed-width binary serialization.
- File-backed memory mapping with FIFO, full/empty, wraparound, and cooperating
  process synchronization support.
- Price-time-priority matching, resting-price execution, partial fills, and
  residual orders.
- Asynchronous synthetic order generation, with integrated and separate
  producer/consumer entry points.
- In-process latency and rolling throughput measurements.
- Matching verification, transport/serialization audit, and ANSI terminal
  dashboard.
- Regression tests for serialization, ring-buffer behavior, matching, and
  pipeline integration.

See [features.md](./features.md) for a detailed description of the implemented
features and known boundaries.

## Requirements

- Python **3.14.6**. The current workspace was verified with this version.
- `pip`.
- Windows PowerShell for the commands below.

The runtime dependency is `sortedcontainers==2.4.0`, pinned in
`hft_engine\requirements.txt`. `hft_engine\requirements-dev.txt` includes that
runtime requirement and `pytest==9.1.1` for the regression suite. The
experimental Cython source is optional and is not needed to run the Python
application.

## Setup

Open PowerShell in the repository root—the directory containing this README:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\hft_engine\requirements-dev.txt
Set-Location .\hft_engine
```

The version command should report `Python 3.14.6`. If the `python` command
selects a different interpreter, create the virtual environment using the
installed Python 3.14.6 executable, then select `.venv` as the VS Code
interpreter. If PowerShell blocks environment activation, select the `.venv`
interpreter in VS Code or invoke it directly from `hft_engine`:

```powershell
..\.venv\Scripts\python.exe --version
```

Prefix each Python command with `..\.venv\Scripts\python.exe` instead of
`python` when using this direct invocation.

## Run the application

Run the following from the `hft_engine` directory:

```powershell
# Binary order serialization smoke test
python main.py struct-test

# mmap ring-buffer smoke test
python main.py ring-test

# Matching correctness checks and an actual local latency sample
python main.py verify

# Integrated producer -> ring buffer -> consumer -> matching engine
python scripts/run_demo.py --duration 2 --target-ops 50000

# Transport and serialization benchmark
python main.py audit --orders 10000

# ANSI terminal dashboard
python main.py dashboard --duration 5 --target-ops 50000
```

The smoke tests print `PASS` messages if successful. The demo reports counts
and measurements from that run; its synthetic workload is random and results
can vary. The target operation rate is a target, not a throughput guarantee.
The audit measures each implemented method on the current machine; the
methods do not have identical allocation and serialization costs.

The standalone firehose command is also available:

```powershell
python main.py firehose --duration 5 --target-ops 100000
```

It produces orders without running a consumer, so the bounded ring buffer may
fill and subsequent orders may be counted as dropped.

## Separate producer and consumer processes

The separate-process scripts demonstrate cooperating processes using the same
ring-buffer file. Open two PowerShell terminals. In the first terminal, start
the consumer:

```powershell
Set-Location .\hft_engine
$ipcPath = Join-Path $env:TEMP 'chronosmatch.rb'
python scripts/run_consumer.py --path $ipcPath --timeout 60
```

In the second terminal, start the producer with the same path:

```powershell
Set-Location .\hft_engine
$ipcPath = Join-Path $env:TEMP 'chronosmatch.rb'
python scripts/run_producer.py --path $ipcPath --duration 10 --target-ops 50000
```

The consumer waits up to 10 seconds for the backing file to appear. It exits
after its configured idle timeout; there is no dedicated producer-completion
message. Use `Ctrl+C` to stop it sooner. The producer creates or truncates the
file on startup, so do not point it at a file whose contents must be preserved.
Both processes must use the same path and capacity.

## Tests and verification

Run these commands from `hft_engine`:

```powershell
python -m pytest -q
python -m compileall -q .
```

The tests cover:

- BUY and SELL serialization round trips, field constraints, and malformed
  records.
- Ring-buffer empty/full behavior, FIFO order, wraparound, malformed slots,
  corrupt counters, resource closure, and spawned-process synchronization.
- Best-price and FIFO matching, partial fills, residual quantities, non-crossing
  orders, and invalid submissions.
- Producer-to-buffer-to-matching-engine integration and metrics edge cases.
- A regression check that the verification command returns a failure status
  when a correctness check fails.

Latest local verification in this workspace used Windows 11 and Python
3.14.6:

- `python -m pytest -q` — **41 passed**.
- `python -m compileall -q .` — completed successfully.
- `python main.py struct-test` and `python main.py ring-test` — both completed
  and printed their `PASS` messages.
- `python main.py verify` — all matching correctness checks passed, including
  the completed-submission latency sample.
- `python scripts/run_demo.py --duration 2 --target-ops 50000` — completed;
  the run processed all successfully enqueued orders and reported no drops.

These are results observed from the current checkout during this update.
Re-run the commands after changing code or dependencies to verify the resulting
files. Runtime measurements and generated order counts vary and are not
performance guarantees.

For command-by-command output expectations, see
[expected-results.md](./expected-results.md).

## Project layout

```text
ChronosMatch-Roadmap             Development roadmap
features.md                      Feature inventory and limitations
expected-results.md              Expected command behavior
hft_engine/
├── main.py                      Unified command-line interface
├── requirements.txt             Runtime dependencies
├── requirements-dev.txt         Runtime dependencies plus pytest
├── core/
│   ├── constants.py             Shared format and runtime defaults
│   ├── order_struct.py          Order validation and binary serialization
│   ├── ring_buffer.py           mmap-backed SPSC ring buffer
│   ├── firehose.py              Asynchronous synthetic order producer
│   └── metrics.py               Latency and rolling throughput metrics
├── engine/
│   └── limit_order_book.py      Python price-time-priority matching engine
├── bench/
│   ├── engine_verify.py         Matching checks and latency sample
│   └── ipc_audit.py             Transport/serialization measurements
├── scripts/
│   ├── run_demo.py              Integrated single-process demo
│   ├── run_producer.py          Separate-process producer
│   └── run_consumer.py          Separate-process consumer
├── tests/                       Pytest regression tests
├── ui/
│   ├── dashboard.py             Terminal dashboard
│   └── web_dashboard.html       Standalone visual mock-up
└── cython_src/
    └── lob.pyx                  Experimental optional Cython source
```

## Technical details and limitations

### Order record

Each order is encoded in 21 bytes with struct format `=QdIb`:

| Field | Encoding | Size |
|---|---|---:|
| `order_id` | Unsigned 64-bit integer | 8 bytes |
| `price` | 64-bit floating-point value | 8 bytes |
| `quantity` | Unsigned 32-bit integer | 4 bytes |
| `side` | Signed 8-bit integer (`+1` BUY, `-1` SELL) | 1 byte |

Prices must be finite and positive. Quantities must be positive and fit the
unsigned 32-bit field; order identifiers must fit the unsigned 64-bit field.
The `=` prefix uses native byte order with standard field sizes and no padding,
so the record is intended for cooperating processes on the same host, not as a
portable network protocol.

### Ring buffer and process model

The mapped file has a 16-byte header followed by fixed-width order slots.
`put(order)` returns `False` when full, and `get()` returns `None` when empty.
Calls may wait to acquire synchronization locks even though queue operations
do not wait for space or data. A thread lock protects access within one process;
Windows uses a named OS mutex and POSIX uses `flock` for cooperating processes.
The intended topology is one producer and one consumer, using the same backing
path and capacity.

### Matching and measurement

The matching engine uses best-price priority and FIFO order at equal prices.
Trades execute at the resting order's price; a partial fill leaves the
unmatched quantity on the book. Benchmark values depend on the interpreter,
platform, workload, and system load. Compare only measurements gathered under
similar conditions. The audit methods have different costs and do not prove
that the complete pipeline avoids copying or that one method is always faster.

### Dashboards and optional Cython

- `ui\dashboard.py` displays in-process simulation metrics in an ANSI terminal.
- `ui\web_dashboard.html` is a standalone browser mock-up with generated values;
  it is not connected to the Python engine or its live metrics.
- `cython_src\lob.pyx` is experimental, is not used by the Python CLI, and has
  not been built or validated with Python 3.14.6. No Cython performance claim
  is made.

## Troubleshooting

- **Import errors:** Run commands from `hft_engine`, activate the project
  environment, and install `requirements-dev.txt` from the repository root.
- **Wrong Python version:** Check `python --version` and select a Python 3.14.6
  interpreter before creating or using `.venv`.
- **Consumer cannot find the backing file:** Start the consumer and producer
  with exactly the same path. The consumer waits up to 10 seconds for the file
  to be created.
- **Stale IPC file or interrupted run:** Stop both processes. The producer
  recreates and truncates its backing file when started; make sure no other
  process still needs that file.
- **Dashboard or demo interrupted:** The integrated demo and terminal
  dashboard request producer shutdown, drain pending orders where applicable,
  join worker threads, and close the mapped file.
- **Cython build issue:** The extension is optional. A Cython installation
  and compatible native compiler are required to experiment with it; neither
  is needed for the Python CLI.

## Roadmap and status

[ChronosMatch-Roadmap](./ChronosMatch-Roadmap) describes planned work by
development phase. Week labels are planning milestones, not verified dates or
commit history. Treat the test result above as the recorded verification
evidence; roadmap entries should be updated only when work and checks have
actually been completed.

## Security and project scope

- Use synthetic orders only. The project does not route real orders or connect
  to an exchange.
- Do not commit credentials, private keys, local `.env` files, or other secrets.
- Review staged files before committing, including local configuration and
  generated artifacts.
- No license is currently specified. Add an appropriate license before
  redistributing the project under particular reuse terms.
