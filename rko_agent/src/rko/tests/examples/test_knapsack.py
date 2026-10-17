"""Knapsack benchmark contract tests.

Objective:
- Check instance validation and spawn-compatible problem callbacks.

Technical approach:
- Exercise public example helpers with small independently solved instances.

Flow (pseudocode):
1. Parse valid and malformed instances.
2. Serialize the objective and evaluate known solutions.
3. Check that invalid solution dimensions are rejected.

Important criteria:
- Serialization must preserve objective values and penalties.

Inputs/Outputs:
- Input: temporary instance files and binary decisions.
- Output: assertions on objective values and validation errors.
"""

import pickle
import pytest
from pathlib import Path
from rko.examples.run_kp_cpp_instances import decode_knapsack
from rko.examples.run_kp_cpp_instances import evaluate_solution
from rko.examples.run_kp_cpp_instances import make_cost
from rko.examples.run_kp_cpp_instances import read_kp_instance


def test_objective_survives_pickle_round_trip(tmp_path: Path) -> None:
    """Preserve known feasible and penalized objectives after serialization.

    Args:
        tmp_path (Path): Temporary directory for the benchmark fixture.
    """
    path = tmp_path / "tiny.txt"
    path.write_text("3 5\n6 1\n10 2\n12 3\n", encoding="utf-8")
    instance = read_kp_instance(path)
    objective = pickle.loads(pickle.dumps(make_cost(instance)))
    assert objective([0, 1, 1]) == -22.0
    assert objective([1, 1, 1]) == 99972.0
    assert evaluate_solution([0, 1, 1], instance) == (22, 5, True)
    assert decode_knapsack([0.5, 0.6, 0.9]) == [0, 1, 1]


@pytest.mark.parametrize("text", ["0 5", "1 -1 6 1", "1 5 6 0", "1 5 -6 1", "1 5 6 1 99"])
def test_reader_rejects_malformed_instances(tmp_path: Path, text: str) -> None:
    """Reject invalid headers, item values and unexpected trailing data.

    Args:
        tmp_path (Path): Temporary directory for the benchmark fixture.
        text (str): Malformed input contents.
    """
    path = tmp_path / "invalid.txt"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        read_kp_instance(path)


@pytest.mark.parametrize("solution", [[1], [0, 1, 2], [0, 1, 1, 0]])
def test_objective_rejects_invalid_decisions(tmp_path: Path, solution: list[int]) -> None:
    """Reject truncated, nonbinary and oversized solution vectors.

    Args:
        tmp_path (Path): Temporary directory for the benchmark fixture.
        solution (list[int]): Invalid binary decisions.
    """
    path = tmp_path / "tiny.txt"
    path.write_text("3 5 6 1 10 2 12 3", encoding="utf-8")
    with pytest.raises(ValueError):
        make_cost(read_kp_instance(path))(solution)
