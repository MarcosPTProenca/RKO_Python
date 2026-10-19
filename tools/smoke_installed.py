"""Exercise a built artifact without importing the source checkout.

Objective:
- Detect missing runtime resources and unusable installed solver entry points.

Technical approach:
- Run under python -I inside an environment containing only the installed artifact.
- Check package contents and solve a small problem with serial and spawn execution.

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
import shutil
import subprocess
import tempfile
from pathlib import Path
from rko import RKO
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
    for backend in ("serial", "process"):
        for algorithm, dimension in (("MultiStart", 3), ("PSO", 64)):
            result = RKO(
                decode,
                objective,
                dimension,
                algorithms=[algorithm],
                control=0,
                backend=backend,
                random_state=42,
            ).solve(0.05)
            keys = np.asarray(result.keys)
            assert len(keys) == dimension
            assert np.all((keys >= 0.0) & (keys < 1.0))
            assert np.isclose(result.cost, objective(keys))
    bounded = RKO(
        decode,
        objective,
        64,
        algorithms=["MultiStart", "IPR", "PSO"],
        control=0,
        backend="process",
        n_jobs=1,
        random_state=42,
    ).solve(0.1)
    assert len(bounded.keys) == 64
    assert np.isclose(bounded.cost, objective(np.asarray(bounded.keys)))
    executable = shutil.which("rko")
    assert executable is not None
    with tempfile.TemporaryDirectory(prefix="rko-installed-cli-") as temporary:
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
