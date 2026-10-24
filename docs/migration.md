# Migrating to the standalone prerelease API

[Documentation index](index.md) · [Quickstart](getting-started.md) ·
[Changelog](https://github.com/MarcosPTProenca/RKO/blob/main/CHANGELOG.md)

The existing PyPI `rko` 0.2.1 describes an older environment-oriented API and
Python >=3.8. The standalone `0.3.0a1` source is a **breaking prerelease line**;
its presence in development docs is not evidence of an upload to your chosen index. Do not assume that an unpinned `pip install
rko` supplies the API in these development docs. Public install instructions will
change only after an authorized index upload and clean-install verification.

## Use a clean environment

Use Python **3.14** for the tested target. Metadata requires >=3.14; other newer
interpreters/platforms are not certified by this matrix. Create a separate virtual
environment rather than upgrading an application that depends on the older API.
The distribution and import name remain `rko`; do not install a second distribution
that writes the same namespace into that environment.

Until publication is verified, use the [source installation](getting-started.md).
For an already authorized prerelease, pin its exact verified version/index instead
of blindly accepting the latest package matching the old name. A prerelease label
is not permission to ignore compatibility, licensing or scientific limitations.

## Replace environment wiring with explicit callbacks

The former environment objects/import paths are not compatibility shims in this
API. Implement or bind an ordinary decoder and objective, configure a solver, then
solve. Reader code runs in your application, not implicitly inside the optimizer:

```python
import numpy as np
from rko import RKO


def decode(keys: np.ndarray) -> np.ndarray:
    """Map random keys into numerical solution coordinates.

    Args:
        keys (np.ndarray): Unit-interval priority vector.

    Returns:
        np.ndarray: Coordinates in [-1, 1].
    """
    return 2.0 * keys - 1.0


def cost(solution: np.ndarray) -> float:
    """Compute the finite minimization objective.

    Args:
        solution (np.ndarray): Decoded coordinates.

    Returns:
        float: Squared Euclidean norm.
    """
    return float(np.dot(solution, solution))


solver = RKO(
    decoder=decode, cost=cost, n_variables=4, algorithms=["SA"],
    adaptation="fixed", backend="serial", random_state=42,
    hyperparameters={"SA": {"sa_max": 100, "t0": 1000.0}},
)
result = solver.solve(time_limit=0.1)
print(result.cost, result.keys)
```

For instance-dependent problems, load once before constructing the solver and bind
data with `partial` or a bound method. See the complete [file-to-solution pipeline](problem-adapters.md).
Only reader/decoder/objective are problem-specific requirements; a reader is
unnecessary for already-loaded data, and adapter classes/checkers are optional.

## Other intentional changes

- Individual public algorithms also use `SA(...)` followed by `.solve(...)`, return
  `RKOResult`, and share RKO's defaults. There is no class-level convenience runner
  or compatibility alias. Advanced raw kernels require explicit implementation-module imports.
- Hyperparameters use the same nested per-algorithm mapping everywhere. Partial
  scalar overrides retain defaults and require fixed adaptation. See [parameters](parameters.md).
- `adaptation="fixed"|"adaptive"` is readable mode selection; legacy integer control
  remains supported, but contradictory aliases fail. It is not a network/training mode.
- Default backend is process. Explicit serial mode is suitable for local/non-pickleable
  callbacks. Process callbacks need importability and guarded script entry points.
- Optional validation reconstructs/checks after solving, not an original evaluation
  witness. Static diagrams are not traces. Neither certifies optimality/completeness.
- Core dependencies are NumPy only; reports/docs/release tools are separate optional
  contexts. Historical pandas/Matplotlib environment dependencies are not required.

Alpha/beta/RC APIs can change between explicitly versioned prereleases; pin the
version and consult migration notes rather than assuming stable deprecation guarantees.
Stable publication/deprecation policy requires a separate owner decision.

Consult [status and limitations](status.md) before porting an application. Keep your
own replay/regression tests and do not expect identical timed trajectories or C++
performance merely because installation succeeds. Optional native-build work is
independent; the initial release pipeline does not publish native binary wheels.
