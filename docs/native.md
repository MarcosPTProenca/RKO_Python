# Native engine

`backend="native"` runs the eleven algorithms, Q-learning control and the shared elite
pool in a compiled Rust extension (`rko._native`, sources in `crates/`). The Python API,
TOML parameter files, hyperparameter overrides and result metadata are unchanged: Python
still loads and validates every parameter and only passes numeric vectors to the engine.

Measured results against the pinned C++ reference and the Python engine, with their
limits, are in [benchmarks](../benchmarks/README.md#native-engine-versus-c-and-python).
They are not a general speed guarantee.

## Two ways to define a problem

**Native problem (fastest).** The decoder and objective run inside Rust, so every worker
thread runs in parallel with the interpreter lock released. A built-in 0/1 Knapsack is
provided; native problems may also offer constant-time move evaluation.

```python
from rko import RKO
from rko.native import Knapsack

problem = Knapsack(profits=[10, 20, 30], weights=[5, 6, 7], capacity=12)
result = RKO.native(problem, adaptation="adaptive", random_state=42).solve(10.0)
print(result.cost, result.keys, result.n_workers)
```

**Python callbacks (compatible).** The decoder and objective you already have work
unchanged:

```python
result = RKO(decoder, cost, n_variables, backend="native", random_state=42).solve(10.0)
```

Each call receives a fresh NumPy array, exceptions raised in callbacks propagate
unchanged, and non-finite objectives fail the solve. Callbacks execute under the
interpreter lock, so worker threads take turns: the engine removes its own overhead
(startup, framework bookkeeping) but cannot add parallelism to Python code.

## Behavior to know

- `n_jobs` sets native worker threads; the default is one thread per algorithm. With
  fewer threads than algorithms each worker splits its remaining time among its searches.
- Seeds make a single-worker run reproducible only up to timing, as in every backend.
  Random streams are the engine's own, so trajectories differ from the Python engine.
- `prefill_pool=True` fills the pool with `pool_size` random evaluated vectors first and
  reports it as `PoolInitializationMetadata`; the default stays off.
- Nelder-Mead takes its two pool vertices from the best pool entries for SA, GA, LNS,
  GRASP and BRKGA-CS (and may return one of them when better than the incumbent), and
  from two random entries for the others. The Python engine always uses the best entries;
  the C++ reference uses random entries.
- `verbose=True` prints lifecycle lines only; live pool progress is not available.
- Windows, Linux and macOS builds use the same sources; only Linux has measurements.

## Limits

- A portfolio of expensive Python callbacks usually runs better on `backend="process"`,
  whose workers each have their own interpreter. See the callback-portfolio rows in the
  benchmark study.
- IPR alone (without peers filling the pool) and GRASP were not better than C++ in the
  2-second study; the portfolio, which is the default, was.
- Batched or compiled (for example Numba) decoders are not supported yet.

## Build and test

`uv sync` builds the extension (a Rust toolchain is required). After changing Rust code:

```bash
cargo fmt --all --check
cargo clippy --workspace --all-targets --release -- -D warnings
cargo test --release
uv run pytest src/rko/tests/rko/test_native_backend.py -q
```
