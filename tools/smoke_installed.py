"""Exercise a built artifact without importing the source checkout.

Objective:
- Detect missing runtime resources and unusable installed solver entry points.

Technical approach:
- Run under python -I inside an environment containing only the installed artifact.
- Check filtered adaptive graphs and package contents.
- Check seeded serial/thread/spawn execution without modifying caller RNG state.

Flow (pseudocode):
1. Locate the installed package and assert expected data and excluded tests.
2. Read packaged parameters and reference instances.
3. Verify class-based results against an independent objective calculation.

Important criteria:
- Use the main guard and importable callbacks for Windows spawn.
- This is an installation contract check, not an optimization-quality benchmark.

Inputs/Outputs:
- Input: installed wheel or sdist and its runtime dependencies.
- Output: assertions and a success message, or a failing process exit.
"""

import csv
import numpy as np
import os
import pickle
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from rko import RKO
from rko import PoolInitializationMetadata
from rko import SearchMetadata
from rko.components.adaptive_control.q_learning import QLearningController
from rko.examples import instance_pipeline
from rko.examples.run_kp_cpp_instances import default_instances_dir
from rko.examples.run_kp_cpp_instances import read_kp_instance
from rko.parameters.loader import default_params_dir


def decode(keys: np.ndarray) -> np.ndarray:
    """Decode keys without changing the vector.

    Args:
        keys (np.ndarray): Candidate vector.

    Returns:
        np.ndarray: Unmodified candidate.
    """
    return keys


def objective(keys: np.ndarray) -> float:
    """Evaluate the installed smoke objective.

    Args:
        keys (np.ndarray): Candidate vector.

    Returns:
        float: Squared Euclidean norm.
    """
    return float(np.dot(keys, keys))


def main() -> None:
    """Validate installed resources and actual public execution.

    Raises:
        AssertionError: If packaging or solver result contracts fail.
        OSError: If installed runtime resources cannot be read.
        subprocess.SubprocessError: If the installed terminal command fails or times out.
    """
    package = default_params_dir().parent
    assert not (package / "tests").exists()
    assert (default_params_dir() / "config.toml").is_file()
    assert len(list(default_params_dir().glob("*.toml"))) == 12
    assert read_kp_instance(default_instances_dir() / "kp10.txt").n_items == 10
    assert read_kp_instance(default_instances_dir() / "kp50.txt").n_items == 50
    assert any("LICENSE" in path.name for path in default_instances_dir().iterdir())
    assert package.resolve() != Path(__file__).resolve().parents[1] / "src" / "rko"
    controller = QLearningController(
        [[0.0, 1.0], [0.0, 1.0]], state_filter=lambda values: sum(values) <= 1.0
    )
    assert [state.par for state in controller.states] == [[0.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
    assert [state.Ai for state in controller.states] == [[0, 1, 2], [0, 1], [0, 2]]
    global_rng = pickle.dumps((random.getstate(), np.random.get_state()))
    for backend in ("serial", "thread", "process"):
        for algorithm, dimension, control in (
            ("MultiStart", 3, 0),
            ("IPR", 64, 0),
            ("GRASP", 1, 0),
            ("GRASP", 1, 1),
            ("GRASP", 4, 0),
            ("GRASP", 4, 1),
            ("SA", 64, 0),
            ("SA", 64, 1),
            ("PSO", 64, 0),
            ("PSO", 64, 1),
        ):
            result = RKO(
                decode,
                objective,
                dimension,
                algorithms=[algorithm],
                control=control,
                hyperparameters={"PSO": {"p_size": 4, "w": 0.5}}
                if algorithm == "PSO" and control == 0
                else None,
                backend=backend,
                random_state=42,
            ).solve(0.05)
            keys = np.asarray(result.keys)
            assert len(keys) == dimension
            assert np.all((keys >= 0.0) & (keys < 1.0))
            assert np.isclose(result.cost, objective(keys))
            assert result.n_evaluations >= 1
            assert result.stop_reason == "time_limit"
            assert result.n_workers == 1
            assert result.available_cpus == (
                max(1, os.process_cpu_count() or 1) if backend == "process" else None
            )
            assert len(result.searches) == 1
            report = result.searches[0]
            assert isinstance(report, SearchMetadata)
            assert report.n_evaluations == result.n_evaluations
            assert report.algorithm == algorithm
            assert report.random_state == int(
                np.random.SeedSequence(42).spawn(1)[0].generate_state(1)[0]
            )
            assert dict(result.versions)["numpy"] == np.__version__
            if algorithm == "PSO" and control == 0:
                assert dict(report.parameters)["p_size"] == 4
            assert bool(report.parameter_grid) == (
                algorithm in ("GRASP", "SA", "PSO") and control == 1
            )
            assert pickle.loads(pickle.dumps(result)) == result
        prefilled = RKO(
            decode,
            objective,
            3,
            algorithms=["MultiStart"],
            control=0,
            backend=backend,
            prefill_pool=True,
            pool_size=3,
            random_state=42,
        ).solve(0.05)
        assert isinstance(prefilled.initialization, PoolInitializationMetadata)
        assert prefilled.initialization.n_evaluations == 3
        assert prefilled.initialization.pool_size == 3
        assert prefilled.n_evaluations == 3 + sum(
            report.n_evaluations for report in prefilled.searches
        )
        assert pickle.loads(pickle.dumps(prefilled)) == prefilled
    automatic = RKO(
        decode,
        objective,
        64,
        algorithms=["MultiStart", "PSO"],
        control=0,
        hyperparameters={"PSO": {"p_size": 4}},
        random_state=42,
    ).solve(0.2)
    assert automatic.n_jobs is None
    assert automatic.available_cpus == max(1, os.process_cpu_count() or 1)
    assert automatic.n_workers == min(2, automatic.available_cpus)
    assert [report.algorithm for report in automatic.searches] == ["MultiStart", "PSO"]
    assert np.isclose(automatic.cost, objective(np.asarray(automatic.keys)))
    assert pickle.loads(pickle.dumps(automatic)) == automatic
    uneven = RKO(
        decode,
        objective,
        16,
        algorithms=["MultiStart", "PSO", "GA"],
        control=0,
        hyperparameters={"PSO": {"p_size": 4}, "GA": {"size_pop": 12}},
        backend="process",
        n_jobs=2,
        random_state=42,
    ).solve(0.2)
    assert uneven.n_workers == 2
    assert [report.algorithm for report in uneven.searches] == ["MultiStart", "PSO", "GA"]
    assert 0 < uneven.searches[0].time_limit <= 0.1
    assert 0 <= uneven.searches[1].time_limit <= 0.2
    assert all(0 <= report.time_limit <= 0.2 for report in uneven.searches)
    assert uneven.n_evaluations == sum(report.n_evaluations for report in uneven.searches)
    assert np.isclose(uneven.cost, objective(np.asarray(uneven.keys)))
    assert pickle.loads(pickle.dumps(uneven)) == uneven
    bounded = RKO(
        decode,
        objective,
        64,
        algorithms=["MultiStart", "IPR", "PSO"],
        control=0,
        hyperparameters={"PSO": {"p_size": 4}},
        backend="process",
        n_jobs=1,
        random_state=42,
    ).solve(0.1)
    assert len(bounded.keys) == 64
    assert np.isclose(bounded.cost, objective(np.asarray(bounded.keys)))
    assert bounded.n_workers == 1
    assert [report.algorithm for report in bounded.searches] == ["MultiStart", "IPR", "PSO"]
    assert bounded.n_evaluations == sum(report.n_evaluations for report in bounded.searches)
    assert dict(bounded.searches[-1].parameters)["p_size"] == 4
    assert pickle.dumps((random.getstate(), np.random.get_state())) == global_rng
    instance = instance_pipeline.read_data(
        Path(instance_pipeline.__file__).with_name("instances") / "scheduling.json"
    )
    problem = instance_pipeline.SchedulingProblem(instance)
    for backend in ("serial", "thread", "process"):
        scheduled = RKO(
            problem.decode,
            problem.cost,
            problem.n_variables,
            algorithms=["SA"],
            adaptation="fixed",
            backend=backend,
            random_state=42,
        ).solve(0.1)
        assert scheduled.cost == problem.cost(problem.decode(np.asarray(scheduled.keys)))
        assert scheduled.n_variables == len(instance.processing_times)
    executable = shutil.which("rko")
    assert executable is not None
    with tempfile.TemporaryDirectory(prefix="rko-installed-cli-") as temporary:
        pipeline = subprocess.run(
            [sys.executable, "-I", "-m", "rko.examples.instance_pipeline", "--time-limit", "0.05"],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=temporary,
        )
        assert "four-job scheduling tutorial" in pipeline.stdout
        assert "Schedule (job index, completion time):" in pipeline.stdout
        output = Path(temporary) / "result.csv"
        subprocess.run(
            [
                executable,
                str(default_instances_dir() / "kp10.txt"),
                "--backend",
                "serial",
                "--limit-time",
                "0.01",
                "--random-state",
                "42",
                "--output-csv",
                str(output),
            ],
            check=True,
            timeout=90,
            cwd=temporary,
        )
        with output.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 1 and rows[0]["instance"] == "kp10.txt"
    print(f"Installed artifact passed: {package}")


if __name__ == "__main__":
    main()
