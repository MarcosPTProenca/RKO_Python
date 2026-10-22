"""Standalone built-in algorithm entry-point and readable adaptation contracts.

Objective:
- Verify that every built-in algorithm runs from the same problem callbacks.

Technical approach:
- Exercise real bounded serial searches through the inherited class method.
- Check mode resolution, conflicting inputs and legacy keyword compatibility.

Flow (pseudocode):
1. Define deterministic identity decoding and a finite sphere objective.
2. Run every registered class and inspect immutable result metadata.
3. Reject unsupported modes and conflicting legacy inputs.

Important criteria:
- Short time budgets test API contracts, not solution quality or speed.
- Existing constructors and their tuple-returning solve methods remain unchanged.

Inputs/Outputs:
- Input: built-in classes, callbacks and bounded settings.
- Output: assertions covering results, validation and configuration overrides.
"""

import ast
import numpy as np
import pytest
from pathlib import Path
from rko import RKO
from rko.metaheuristics import MetaheuristicBase
from rko.orchestration.configuration import MH_SPECS
from rko.orchestration.configuration import parse_run_config


def decode(keys: np.ndarray) -> np.ndarray:
    """Return keys as the decoded solution.

    Args:
        keys (np.ndarray): Candidate vector.

    Returns:
        np.ndarray: Unchanged candidate.
    """
    return keys


def objective(solution: np.ndarray) -> float:
    """Compute the finite squared Euclidean norm.

    Args:
        solution (np.ndarray): Numerical candidate.

    Returns:
        float: Squared norm to minimize.
    """
    return float(np.dot(solution, solution))


@pytest.mark.parametrize("name", tuple(MH_SPECS))
@pytest.mark.parametrize("adaptation", ["fixed", "adaptive"])
def test_each_algorithm_runs_alone(name: str, adaptation: str) -> None:
    """Run a registered class without requiring caller-managed pools.

    Args:
        name (str): Canonical algorithm name.
        adaptation (str): Requested readable parameter mode.
    """
    result = MH_SPECS[name].constructor.solve_one(
        decode, objective, 3, time_limit=0.01, random_state=42, adaptation=adaptation
    )
    assert result.algorithms == (name,)
    assert result.backend == "serial"
    assert result.adaptation == adaptation
    expected_control = int(adaptation == "adaptive" and MH_SPECS[name].supports_control)
    assert result.searches[0].control == expected_control
    assert result.n_evaluations is not None and result.n_evaluations > 0
    assert len(result.keys) == 3
    assert result.cost == pytest.approx(objective(np.asarray(result.keys)))


@pytest.mark.parametrize("adaptation,control", [("fixed", 0), ("adaptive", 1)])
def test_readable_and_legacy_modes(adaptation: str, control: int) -> None:
    """Keep readable modes and legacy mode codes equivalent.

    Args:
        adaptation (str): Public mode name.
        control (int): Equivalent legacy code.
    """
    result = RKO(
        decode,
        objective,
        3,
        algorithms=["SA"],
        backend="serial",
        adaptation=adaptation,
        control=control,
    ).solve(0.01)
    assert result.control == control
    assert result.adaptation == adaptation


@pytest.mark.parametrize("adaptation", ["online", "offline", "", 0, [], True])
def test_invalid_adaptation_is_rejected(adaptation: object) -> None:
    """Reject unknown names and non-string adaptation values.

    Args:
        adaptation (object): Invalid public input.
    """
    with pytest.raises(ValueError, match="adaptation"):
        RKO(decode, objective, 3, adaptation=adaptation, backend="serial").solve(0.01)


def test_conflicting_modes_are_rejected() -> None:
    """Reject contradictory readable and legacy settings without running callbacks."""
    with pytest.raises(ValueError, match="contradicts"):
        RKO(decode, objective, 3, adaptation="fixed", control=1).solve(0.01)


def test_standalone_scalar_overrides() -> None:
    """Merge single-algorithm scalar overrides with packaged fixed defaults."""
    result = MH_SPECS["GA"].constructor.solve_one(
        decode,
        objective,
        3,
        time_limit=0.01,
        hyperparameters={"size_pop": 8, "prob_mut": 0.1},
    )
    assert dict(result.searches[0].parameters)["size_pop"] == 8
    assert dict(result.searches[0].parameters)["prob_mut"] == 0.1


def test_base_class_is_not_a_registered_algorithm() -> None:
    """Reject invoking the convenience entry point on the abstract base itself."""
    with pytest.raises(ValueError, match="registered"):
        MetaheuristicBase.solve_one(decode, objective, 3, time_limit=0.01)


def test_readable_toml_configuration_and_python_override(tmp_path: Path) -> None:
    """Resolve readable TOML settings and allow explicit Python mode overrides.

    Args:
        tmp_path (Path): Isolated configuration directory.
    """
    raw = {
        "run": {"adaptation": "adaptive", "pool_size": 2},
        "active_metaheuristics": {"list": ["MultiStart"]},
    }
    assert parse_run_config(raw).control == 1
    (tmp_path / "config.toml").write_text(
        '[run]\nadaptation="adaptive"\npool_size=2\n[active_metaheuristics]\nlist=["MultiStart"]\n',
        encoding="utf-8",
    )
    (tmp_path / "multi_start.toml").write_text("[offline]\n[online]\n", encoding="utf-8")
    result = RKO(
        decode, objective, 3, params_dir=tmp_path, backend="serial", adaptation="fixed"
    ).solve(0.01)
    assert result.adaptation == "fixed"


def test_runtime_modules_have_technical_headers() -> None:
    """Keep algorithm and runtime module explanations complete and discoverable."""
    root = Path(__file__).resolve().parents[2]
    required = (
        "Objective:",
        "Technical approach:",
        "Flow (pseudocode):",
        "Important criteria:",
        "Inputs/Outputs:",
    )
    for path in root.rglob("*.py"):
        if "tests" in path.relative_to(root).parts:
            continue
        header = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        assert all(section in header for section in required), str(path)


def test_toml_conflicting_adaptation_is_rejected() -> None:
    """Reject mutually contradictory names in a custom configuration table."""
    with pytest.raises(ValueError, match="contradicts"):
        parse_run_config(
            {
                "run": {"adaptation": "adaptive", "control": 0, "pool_size": 2},
                "active_metaheuristics": {"list": ["SA"]},
            }
        )


def test_legacy_control_without_readable_alias_still_works() -> None:
    """Preserve the existing integer-only Python interface and result metadata."""
    result = RKO(decode, objective, 3, algorithms=["SA"], control=0, backend="serial").solve(0.01)
    assert result.control == 0
    assert result.adaptation == "fixed"


def test_getting_started_example_executes() -> None:
    """Execute the introductory Python snippet and verify its reported incumbent."""
    root = Path(__file__).resolve().parents[4]
    page = (root / "docs" / "getting-started.md").read_text(encoding="utf-8")
    code = page.split("```python\n", 1)[1].split("```", 1)[0]
    namespace = {"__name__": "__main__"}
    exec(compile(code, "docs/getting-started.md", "exec"), namespace)
    result = namespace["result"]
    assert len(result.keys) == 10
    assert result.cost == pytest.approx(
        namespace["objective"](namespace["decode"](np.asarray(result.keys)))
    )
