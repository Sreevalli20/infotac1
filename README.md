# ChronosMatch — Zero-Copy High-Frequency Trading Engine

ChronosMatch is an educational Python prototype for a simulated order-processing
pipeline. It explores binary order records, a memory-mapped single-producer /
single-consumer (SPSC) ring buffer, price-time-priority matching, generated
market orders, local performance measurements, and a terminal dashboard.

Despite the project title, the Python pipeline is **not end-to-end zero-copy**:
orders are serialized into the ring buffer and reconstructed as Python
`Order` objects by the consumer. This project is for simulation and learning;
it is not live trading software and makes no production or latency guarantees.

## Requirements

- Python **3.14.6** (the Python implementation has been run on Windows with
  this version).
- `pip`.
- PowerShell for the commands below.

Runtime dependencies are listed in `hft_engine\requirements.txt`. The test
dependency is listed separately in `hft_engine\requirements-dev.txt`. The
optional Cython extension is not required for the Python application.

## Setup

Open PowerShell in the repository root (the directory containing this README):

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\hft_engine\requirements-dev.txt
Set-Location .\hft_engine
```

`python --version` should report `Python 3.14.6`. If PowerShell blocks virtual
environment activation, select the project `.venv` interpreter in VS Code or
invoke it directly as `..\.venv\Scripts\python.exe` while in `hft_engine`.

## Run the application

Run commands from the `hft_engine` directory:

```powershell
# Binary order round-trip smoke check
python main.py struct-test

# mmap ring-buffer full/empty smoke check
python main.py ring-test

# Matching-engine correctness checks and a local latency sample
python main.py verify

# Integrated producer -> ring buffer -> consumer -> matching engine
python scripts/run_demo.py --duration 2 --target-ops 50000

# Transport and serialization benchmark; rates are measured on this machine
python main.py audit --orders 10000

# Live terminal dashboard
python main.py dashboard --duration 5 --target-ops 50000
```

The smoke checks print `PASS` messages. The demo prints actual order, trade,
volume, drop, and timing counts from its run. The random workload is not seeded,
so counts and measurements can vary. No fixed throughput or latency value is
expected.

### Separate-process producer and consumer

For a Windows PowerShell session using the same local IPC file, start the
consumer in one terminal:

```powershell
Set-Location <path-to-repository>\hft_engine
python scripts/run_consumer.py --path C:\Temp\chronosmatch.rb --timeout 60
```

In a second terminal, start the producer with that same path:

```powershell
Set-Location <path-to-repository>\hft_engine
python scripts/run_producer.py --path C:\Temp\chronosmatch.rb --duration 10 --target-ops 50000
```

Replace `<path-to-repository>` with the actual repository path. The producer
creates or truncates the ring-buffer file, so do not start a producer against a
file containing data you need to preserve. The consumer exits after its
configured idle timeout; it does not receive a dedicated producer shutdown
message. Use `Ctrl+C` to stop it sooner.

## Tests and checks

Run these from `hft_engine`:

```powershell
python -m pytest -q
python -m compileall -q .
```

The tests cover:

- BUY and SELL binary order round trips, field bounds, and malformed records.
- Ring-buffer empty/full behavior, FIFO ordering, wraparound, malformed slots,
  cleanup, and Windows spawned-process synchronization.
- Best-price and FIFO matching, partial fills, residual orders, and invalid
  submissions.
- Producer-to-buffer-to-matching-engine integration, stop requests, and empty
  or invalid metric inputs.
- A regression check that the matching verification command returns a failing
  process status if a check fails.

The CLI matching verification is also available with `python main.py verify`.
It reports a local 100,000-submission latency sample; its observed figures are
measurements, not pass/fail performance thresholds.

## Project layout

```text
ChronosMatch-Roadmap             Development plan and progress
hft_engine/
├── main.py                      Unified command-line interface
├── requirements.txt             Runtime dependency pin
├── requirements-dev.txt         Runtime dependencies plus pytest
├── core/
│   ├── constants.py             Shared format and runtime defaults
│   ├── order_struct.py          Order validation and binary serialization
│   ├── ring_buffer.py           mmap-backed SPSC ring buffer
│   ├── firehose.py              Async simulated order producer
│   └── metrics.py               Latency and throughput counters
├── engine/
│   └── limit_order_book.py      Python price-time-priority matching engine
├── bench/
│   ├── engine_verify.py         Matching checks and latency sampling
│   └── ipc_audit.py             Transport/serialization measurements
├── scripts/
│   ├── run_demo.py              Integrated single-process demo
│   ├── run_producer.py          Separate-process producer
│   └── run_consumer.py          Separate-process consumer
├── tests/                       Pytest regression tests
├── ui/
│   ├── dashboard.py             Live terminal dashboard
│   └── web_dashboard.html       Standalone visual simulation
└── cython_src/
    └── lob.pyx                  Experimental optional Cython LOB
```

## Architecture and limitations

### Binary orders

Each order occupies 21 bytes using the `=QdIb` struct format:

| Field | Encoding | Size |
|---|---|---:|
| `order_id` | Unsigned 64-bit integer | 8 bytes |
| `price` | 64-bit floating-point number | 8 bytes |
| `quantity` | Unsigned 32-bit integer | 4 bytes |
| `side` | Signed 8-bit integer (`+1` BUY, `-1` SELL) | 1 byte |

Prices must be finite and positive, quantities must be positive and fit in
their binary field, and identifiers must fit in an unsigned 64-bit field. The
format uses native byte order, so files are intended for cooperating processes
on the same host rather than as a portable network protocol.

### Ring buffer

The mmap file has a 16-byte header followed by fixed-width order slots. `put`
returns `False` if the buffer is full; `get` returns `None` if it is empty. Calls
serialize access using a thread lock and an OS-level lock for cooperating
processes (a named mutex on Windows and `flock` on POSIX). Participants must use
the same backing path and capacity. The intended configuration is one producer
and one consumer.

### Matching and measurement

The Python limit order book matches at the resting order’s price, prioritizes
the best available price, and preserves FIFO order at equal prices. Partial
fills leave the remaining quantity on the book. Benchmark results depend on
Python, platform, workload, and system load; compare runs only under similar
conditions. The transport benchmark methods do not have identical allocation
costs and do not demonstrate that mmap is faster or that the complete pipeline
avoids copying.

### Dashboards and optional extension

- `ui\dashboard.py` displays current in-process demo metrics in the terminal.
- `ui\web_dashboard.html` is a browser-only visual mock-up: its generated
  prices, trades, and latency values are not connected to the Python engine.
- `cython_src\lob.pyx` is experimental, is not used by the Python CLI, and has
  not been built or validated with Python 3.14.6. No Cython performance claim
  is made.

## Troubleshooting

- **Import error:** Confirm the current directory is `hft_engine`, activate
  `.venv`, and install `..\hft_engine\requirements-dev.txt` from the repository
  root (or `requirements-dev.txt` when inside `hft_engine`).
- **Unexpected Python version:** Check `python --version` and select the Python
  3.14.6 `.venv` interpreter in VS Code.
- **Consumer cannot find the ring file:** Start the consumer with the exact
  path passed to the producer. The consumer waits up to 10 seconds for the
  file to be created.
- **Stale or incompatible ring file:** Stop both processes. The producer
  initializes the file and resets its contents when it starts.
- **Optional Cython build fails:** Cython and a compatible native compiler are
  required; the extension is optional and is not needed for the Python CLI.

## Development progress

The project roadmap tracks planned and completed work. Do not infer that a
commit or task happened on a particular date from the week labels. Update
progress based on work and validation actually performed; do not backdate
commits or present local benchmark readings as guaranteed results.

See [ChronosMatch-Roadmap](./ChronosMatch-Roadmap) for the current plan.

## Security and data

- Do not commit access tokens, credentials, private keys, or local `.env` files.
- Use simulated orders; this project does not connect to an exchange or perform
  real trades.
- Review the staged file list before committing, especially local configuration
  and generated artifacts.

## Author

**Kommavarapu Kameswari Sreevalli**  
GitHub: [@Sreevalli20](https://github.com/Sreevalli20)

## License

No license is currently specified. Add a license before redistributing this
project under particular reuse terms.
