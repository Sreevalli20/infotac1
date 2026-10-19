# ChronosMatch Expected Results

This document describes the expected behavior of the current commands. Exact
timings, rates, counts from random workloads, and platform strings vary between
runs. The examples below intentionally do not invent benchmark numbers.

Run the commands from the `hft_engine` directory after setting up the project as
described in [README.md](./README.md).

## Environment

```powershell
python --version
```

Expected for the documented setup:

```text
Python 3.14.6
```

If another version is displayed, the command is using a different interpreter
than the version documented and tested for the project.

## Smoke tests

### Binary order serialization

```powershell
python main.py struct-test
```

Expected behavior:

- Prints the 21-byte record size and `=QdIb` format.
- Prints BUY and SELL round-trip results.
- Finishes with `PASS struct self-test`.
- Exits successfully.

The hexadecimal output is deterministic for the supported local byte order.

### mmap ring buffer

```powershell
python main.py ring-test
```

Expected behavior:

- Shows a ring buffer with capacity 16.
- Reports `full : size=16`, followed by `empty: size=0`.
- Finishes with `PASS ring-buffer self-test`.
- Exits successfully and removes its temporary backing file.

### Matching engine verification and latency sample

```powershell
python main.py verify
```

Expected behavior:

- Prints six matching correctness groups: exact-price match, no match,
  partial fill, FIFO time priority, best-price priority, and multi-level sweep.
- Prints a latency sample for 100,000 completed submissions, including the
  Python version, platform, elapsed time, rate, average, P50, P99, P99.9, and
  observed garbage-collection events.
- Prints `All correctness checks PASSED` and exits successfully if all checks
  succeed.
- Returns a non-zero exit status if any correctness check fails.

Latency and throughput are measurements for the current machine and run, not
performance targets or guarantees.

## Integrated producer-to-consumer demo

```powershell
python scripts/run_demo.py --duration 2 --target-ops 50000
```

Expected behavior:

- Prints the Python version, platform, and requested workload.
- Completes after the producer duration and consumer queue drain.
- Prints orders sent, orders processed, trades, traded volume, dropped orders,
  latency summary, and best bid/ask.
- Cleans up the temporary mmap file and joins the consumer thread.

Counts and timings are produced by that execution. Generated orders are random,
and the requested producer rate is a target rather than a guarantee. On a
successful complete drain without a consumer error, processed orders should
equal successfully enqueued orders. Orders may be dropped if the bounded ring
buffer fills.

## Transport and serialization audit

```powershell
python main.py audit --orders 10000
```

Expected behavior:

- Runs the mmap ring-buffer, struct, pickle, and JSON benchmark workloads.
- Prints the Python version, platform, requested order count, wire size, and
  the observed rate, payload accounting, and elapsed duration for each method.
- Prints relative rates calculated from this run and exits successfully if all
  workloads complete.

The measured values are intentionally unspecified here: they depend on the
machine, interpreter, system load, and workload. The methods have different
allocation costs, and their results do not establish that the whole application
is zero-copy or that a particular method is universally faster.

## Automated tests and compilation

```powershell
python -m pytest -q
python -m compileall -q .
```

Expected behavior:

- Pytest reports all discovered tests passing and exits with status 0.
- `compileall` exits with status 0 and normally prints nothing when compilation
  succeeds.
- Either command returns a non-zero status if a test or compilation check
  fails.

The latest test result recorded in the project README was **41 passed** on
Windows with Python 3.14.6. That is a recorded verification result, not a
promise that future code or test changes will have the same count. Rerun both
commands to verify the current checkout.

## Terminal dashboard

```powershell
python main.py dashboard --duration 5 --target-ops 50000
```

Expected behavior:

- Displays the existing ANSI terminal dashboard with live in-process metrics
  and order-book depth.
- Runs for the requested duration, then stops the producer, drains pending
  orders, joins its workers, and closes the temporary ring buffer.
- Shows measurements from the current run; displayed values vary.

Use an ANSI-capable terminal. The standalone `ui/web_dashboard.html` is a
visual mock-up with generated browser-side values; it is not a live view of the
Python engine.

## Interpreting failures and variable results

- A `FAIL` in the verification command or a non-zero exit status indicates a
  correctness failure; inspect the command output and traceback.
- A pytest failure should be investigated rather than worked around by
  weakening assertions.
- Different benchmark or demo values between runs are expected. Compare runs
  only under similar Python, platform, workload, and system-load conditions.
- The optional Cython extension is not part of these expected results; it has
  not been built or validated for Python 3.14.6.
- These checks verify a local simulation. They do not verify exchange
  connectivity, production readiness, guaranteed latency, or end-to-end
  zero-copy behavior.
