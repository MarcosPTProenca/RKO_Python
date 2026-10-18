# RKO Python

A Python Random-Key Optimizer inspired by
[RKO C++ v2](https://github.com/RKO-solver/RKO_Cpp_v2.0), with cooperating
metaheuristics, adaptive parameter control and process-based multicore execution.

The Python library lives in [`rko_agent/`](rko_agent/). Its primary API is the
`RKO` class: configure the problem and portfolio, call `solve(time_limit)`, and
inspect the returned `RKOResult`. See the [library guide](rko_agent/README.md)
for callback requirements, examples, supported backends and validation commands.

## Development and installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
cd rko_agent
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest src/rko/tests -q
uv build
```

The wheel and source distribution contain configuration files and the two small
reference Knapsack fixtures. CI tests both installed artifacts in isolated
environments on Linux and Windows, including real spawned solver execution.

## Status

Development continues on branch `rko` in `MarcosPTProenca/RKO-Agent`. This is not a
finished replacement release for the separate `RKO_Python` repository.
The [professional-library audit](rko_agent/docs/audits/2026-10-18-professional-library-audit.md)
and [remediation plan](rko_agent/docs/plans/2026-10-18-audit-remediation.md) record
remaining correctness, usability and performance work. Passing smoke tests does
not establish scientific or production readiness.

A project-wide license has not yet been chosen by the owner. The bundled
reference data retains its upstream MIT notice and provenance; that notice is
not a license grant for this entire project.
