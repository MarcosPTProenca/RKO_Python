# Contributing

Contribute to `MarcosPTProenca/RKO`, branch `main`. This is the standalone
library; do not make new changes in an old agent checkout. Read [AGENTS](AGENTS.md)
for repository coding conventions and [current limitations](docs/status.md) before
interpreting a passing test suite as release or scientific validation.

## Development setup

Use Python 3.14 and [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/MarcosPTProenca/RKO.git
cd RKO
uv sync --locked --group dev
uv run --locked pre-commit install
```

Run tools from the repository root. NumPy is the only runtime dependency; avoid
adding a compiler, JIT or native engine without a separately validated need.
Keep callback/result contracts and packaged TOML/fixture resources intact.

## Validate a change

Start with tests covering the touched behavior, then run the complete checks on
an otherwise idle machine or CI:

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest src/rko/tests -q
uv run --locked pre-commit run --all-files
uv build
```

[CI](.github/workflows/ci.yml) checks Ubuntu/Windows, benchmark diagnostics, and
isolated wheel/sdist installations using `tools/smoke_installed.py`. A source-tree
import alone does not prove an installed package works. CI currently uses Python
3.14; additional interpreter/platform support needs explicit coverage.

Documentation changes should keep relative links and runnable examples correct.
Keep the [README](README.md) as the short entry point and detailed contracts in
[the documentation index](docs/index.md). Use [the extension guide](docs/extending.md)
when implementing an algorithm or replacing operators. Update the
[parameter reference](docs/parameters.md) alongside defaults or validation changes.
Link new user-facing pages from an existing guide.

## Documentation website

Preview the same maintained Markdown with the built-in MkDocs theme:

```bash
uv run --locked --only-group docs mkdocs serve
```

Use the reported `/RKO/` URL. Docs tools are a separate locked group, not
runtime dependencies. Before a docs change, run:

```bash
uv run --locked --group docs pytest src/rko/tests/test_documentation_site.py -q
uv run --locked --only-group docs mkdocs build --strict
```

Navigation is the publication allowlist; do not add ignored/internal material.
See [site maintenance and owner setup](docs/documentation-site.md) for file
boundaries, main-only Pages deployment and recovery. Do not advertise a live URL
until deployment succeeds, or confuse development docs with a stable release.

## Bugs and pull requests

For a bug report, include a minimal reader/decoder/objective, failing input or a
small shareable substitute, Python/NumPy/package versions, OS, backend, algorithms,
parameters, seed, worker limits and the complete traceback. Remove private data
and credentials. Explain expected versus observed behavior. For process issues,
show the guarded entry point and whether callbacks are importable.

A pull request should explain **why** the change is needed, the public contract
it affects, tests actually run, and any remaining limits. Add a focused regression
test for a behavior fix. Do not change algorithm semantics or defaults silently;
record intentional differences from C++ and update relevant examples/docs.

## Performance and scientific evidence

Follow [the C++ performance target and acceptance gates](docs/performance.md).
Do not run competing timing experiments alongside an active benchmark or modify
another run's source, cache, output or processes. Use a separate revision/output
for new experiments. Keep raw failures and provenance; predeclare workloads and
comparison rules rather than selecting only favorable cases.

Microbenchmarks, fixed-work traces, quality-at-time results and memory probes
measure different things. Test durations are not performance evidence; RSS sums
are not unique physical memory. Do not infer general C++ parity from one kernel,
one instance or synthetic objectives. Reproducible measurement code and identified
reference observations belong in `benchmarks/`; local audits, plans and generated
analysis stay ignored under the repository's existing conventions.

## Before a release

This development line is **not release-ready**. Before tagging/publishing:

- Resolve imported-code ownership and attribution in [NOTICE](NOTICE); do not
  replace licenses or claim that a compiler port settles provenance.
- Define supported Python/platform versions and the public API/deprecation policy.
- Review API/error documentation, stopping limits and current compatibility gaps.
- Run source, wheel/sdist and clean-install checks for every supported target.
- Record a versioned changelog/migration note and reproduce any published claims.
- Establish the release owner and authenticated publishing process; no new PyPI
  release or native-wheel support is implied by these instructions.

Do not represent this checklist as completed or add speed/platform badges before
the corresponding evidence and distribution path exist.
