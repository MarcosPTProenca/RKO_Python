"""Knapsack threshold-decoder compatibility regressions.

Objective:
- Preserve binary Python-integer outputs and caller-owned input behavior.

Technical approach:
- Use worked threshold patterns across numeric dtypes, array sizes and layouts.
- Exercise scalar fallbacks and array subclasses through the public decoder.

Flow (pseudocode):
1. Construct independent known decisions around the strict threshold.
2. Decode numeric arrays and unsupported or exceptional inputs.
3. Check output types, caller ownership and floating-point policy.

Important criteria:
- Exactly0.5 is not selected; outputs remain fresh lists of Python integers.
- No timing assertions or private implementation hooks are required.

Inputs/Outputs:
- Input: small and large arrays, views, subclasses and ordinary lists.
- Output: deterministic contract assertions, not performance measurements.
"""

import numpy as np
import pytest
from decimal import Decimal
from rko.examples.run_kp_cpp_instances import decode_knapsack


class _ArrayComparisonOverride(np.ndarray):
    """Distinguish array-level comparison from ordinary element iteration.

    Responsibilities:
    - Expose a caller-owned comparison override that scalar decoding must bypass.

    Attributes:
        shape (tuple[int, ...]): Inherited NumPy array dimensions.
    """

    def __gt__(self, other: object) -> np.ndarray:
        """Return an intentionally different array-level comparison.

        Args:
            other (object): Comparison operand, independent of the fixed result.

        Returns:
            np.ndarray: False for every array position.
        """
        return np.zeros(self.shape, dtype=bool)


@pytest.mark.parametrize("dtype", ["float16", "float32", "float64", "int64", "uint64", "bool"])
@pytest.mark.parametrize("size", [0, 1, 20, 499, 500, 501, 1000])
def test_numeric_inputs_preserve_integer_decisions(dtype: str, size: int) -> None:
    """Keep worked decisions and Python scalar types across numeric arrays.

    Args:
        dtype (str): Primitive NumPy dtype under test.
        size (int): Number of caller-owned random keys.

    Raises:
        AssertionError: If decisions, scalar types or caller data change.
    """
    if dtype.startswith("float"):
        values, decisions = [0, 0.25, 0.5, 0.75, 1], [0, 0, 0, 1, 1]
    else:
        values, decisions = [0, 1, 0, 1, 1], [0, 1, 0, 1, 1]
    keys = np.resize(np.array(values, dtype=dtype), size)
    original = keys.tobytes()
    expected = (decisions * ((size + 4) // 5))[:size]
    keys.flags.writeable = False
    result = decode_knapsack(keys)
    assert result == expected
    assert all(type(value) is int for value in result)
    assert keys.tobytes() == original
    assert decode_knapsack(keys) is not result


@pytest.mark.parametrize("dtype", ["float32", "float64"])
def test_threshold_neighbors_remain_strict(dtype: str) -> None:
    """Select only the representable value above one half.

    Args:
        dtype (str): Floating representation of threshold-adjacent values.

    Raises:
        AssertionError: If exact equality or its neighbors are misclassified.
    """
    scalar = np.dtype(dtype).type
    half = scalar(0.5)
    keys = np.tile([half, np.nextafter(half, scalar(0)), np.nextafter(half, scalar(1))], 200)
    assert decode_knapsack(keys) == [0, 0, 1] * 200


@pytest.mark.parametrize("layout", ["strided", "reversed", "big-endian"])
def test_views_and_byte_order_preserve_input(layout: str) -> None:
    """Decode nonstandard layouts without modifying their owner.

    Args:
        layout (str): Noncontiguous, reverse-strided or swapped-byte fixture.

    Raises:
        AssertionError: If decisions or any source bytes change.
    """
    owner = np.tile([0.25, 0.25, 0.75, 0.75], 500)
    if layout == "strided":
        keys, expected = owner[::2], [0, 1] * 500
    elif layout == "reversed":
        keys, expected = owner[::-1], [1, 1, 0, 0] * 500
    else:
        keys, expected = owner.astype(">f8"), [0, 0, 1, 1] * 500
    original = owner.tobytes(), keys.tobytes()
    assert decode_knapsack(keys) == expected
    assert (owner.tobytes(), keys.tobytes()) == original


@pytest.mark.parametrize("nonfinite", [False, True])
def test_thresholds_and_caller_error_policy_remain_unchanged(nonfinite: bool) -> None:
    """Retain decisions and floating settings for finite and exceptional keys.

    Args:
        nonfinite (bool): Include NaN and infinity values in the input.

    Raises:
        AssertionError: If decisions, input bytes or floating policy change.
    """
    values = [np.nan, -np.inf, np.inf, 0.5, 0.75] if nonfinite else [0.25, 0, 1, 0.5, 0.75]
    keys = np.tile(values, 100)
    original = keys.tobytes()
    with np.errstate(all="raise"):
        policy = np.geterr()
        assert decode_knapsack(keys) == [0, 0, 1, 0, 1] * 100
        assert np.geterr() == policy
    assert keys.tobytes() == original


def test_array_subclass_keeps_element_iteration_semantics() -> None:
    """Do not replace a subclass's scalar iteration with its array operator.

    Raises:
        AssertionError: If an array-level override changes public decisions.
    """
    keys = np.full(500, 0.75).view(_ArrayComparisonOverride)
    assert not (keys > 0.5).any()
    assert decode_knapsack(keys) == [1] * 500


def test_lists_and_object_arrays_keep_scalar_comparisons() -> None:
    """Preserve ordinary lists and nonprimitive scalar comparisons.

    Raises:
        AssertionError: If list or Decimal decisions change.
    """
    assert decode_knapsack([0.25, 0.5, 0.75] * 200) == [0, 0, 1] * 200
    keys = np.array([Decimal("0.25"), Decimal("0.5"), Decimal("0.75")] * 200, dtype=object)
    assert decode_knapsack(keys) == [0, 0, 1] * 200


def test_multidimensional_inputs_keep_the_existing_scalar_path() -> None:
    """Retain scalar-column decisions and ambiguous-row errors.

    Raises:
        AssertionError: If previous array-shape behavior changes.
    """
    assert decode_knapsack(np.array([[0.25], [0.75]])) == [0, 1]
    with pytest.raises(ValueError, match="truth value"):
        decode_knapsack(np.tile([0.25, 0.75], (500, 1)))
