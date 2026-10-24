# Changelog

Candidate entries describe source changes, not proof of an index upload. Published
versions must be verified against their tag, manifest and package-index metadata.

## 0.3.0a1 — prerelease changes

First intended prerelease of the standalone development API. This is a breaking
migration from the previously published `rko` 0.2.1 environment API, not a drop-in
upgrade. See [migration guidance](docs/migration.md) and [release procedure](RELEASING.md).

- Explicit application-owned reader → bound decoder/objective → configured solver
  → `solve(time_limit=...)`, with immutable `RKOResult` and optional post-run diagnostics.
- RKO portfolios and eleven individual managed solver objects share the same
  constructor settings, execution implementation and nested hyperparameter mapping.
- Serial/thread/process execution, owned random streams, parameter validation,
  bounded optional histories and documented cancellation/resource limitations.
- NumPy-only core; optional Plotly reports, post-run validation and static decoder
  diagrams with explicit provenance/privacy boundaries.
- Maintained development website and controlled Python-default distribution checks.
- Python >=3.14; release artifact checks target normal CPython 3.14 on Ubuntu/Windows.
- Owner-confirmed current distribution rights/attribution, retained Apache-2.0 code
  license and MIT fixture license, with both texts included in artifacts.

No stable-release, general C++ performance-equivalence, universal interpretability,
complete feasibility certification or native binary-wheel publication is implied.
The initial pipeline publishes only a tested Python-default wheel and sdist.
Historical release artifacts retain their original metadata/licenses.
