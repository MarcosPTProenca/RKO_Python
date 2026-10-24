"""Check the compiled optional-kernel trust boundary with a real extension.

Objective:
- Protect output ownership, draw order and failure propagation in compiled builds.

Technical approach:
- Require the real binary when RKO_TEST_NATIVE=1; otherwise explicitly skip if absent.
- Exercise the extension boundary without replacing the native implementation.

Flow (pseudocode):
1. Admit valid float64 buffers and verify ordered draws and exact decisions.
2. Reject invalid buffers before RNG consumption or output writes.
3. Propagate the original failing RNG instance without partial output.

Important criteria:
- Missing binaries cannot silently turn native CI into a Python-only green run.

Inputs/Outputs:
- Input: independently owned buffers and observable RNG callables.
- Output: native contract assertions.
"""

import importlib
import importlib.util
import numpy as np
import os
import pytest
from types import ModuleType


@pytest.fixture
def native() -> ModuleType:
    """Load the actual extension or explicitly report why it is absent.

    Returns:
        ModuleType: Compiled extension.
    """
    if importlib.util.find_spec("rko._native") is None:
        if os.environ.get("RKO_TEST_NATIVE") == "1":
            pytest.fail("Native CI requires the compiled rko._native extension")
        pytest.skip("Optional extension was not built")
    return importlib.import_module("rko._native")


def test_native_draw_order_reads_parents_after_draws(native: ModuleType) -> None:
    """Retain mutation precedence, thresholds and late parent snapshot semantics.

    Args:
        native (ModuleType): Real compiled kernel.

    Raises:
        AssertionError: If draws, snapshots or output ownership change.
    """
    a = np.full(4, 0.1)
    b = np.array([0.8, 0.0, 0.4, 2.0])
    values = iter([0.02, 0.5, 0.019, 0.7, 0.1, 0.49, 1.0, 0.5])
    count = 0

    def draw() -> float:
        nonlocal count
        count += 1
        if count == 8:
            b[0] = 0.3
        return next(values)

    out = np.full(4, -100.0)
    native.blend_buffers_rng(a, b, out, True, draw)
    assert count == 8 and out.tolist() == [1.0 - 0.3, 0.7, 0.1, 0.0]
    assert a.tolist() == [0.1] * 4 and out.flags.owndata and out.flags.writeable


@pytest.mark.parametrize("case", ["readonly", "stride", "dimension", "length", "dtype"])
def test_native_validates_before_rng_or_writes(native: ModuleType, case: str) -> None:
    """Refuse unsupported buffers without consuming draws or exposing partial output.

    Args:
        native (ModuleType): Compiled extension.
        case (str): Invalid layout or shape.

    Raises:
        AssertionError: If validation changes the RNG or output.
    """
    count = 0

    def draw() -> float:
        nonlocal count
        count += 1
        return 0.9

    a = np.ones((1, 2)) if case == "dimension" else np.ones(2)
    if case == "dtype":
        a = a.astype(np.float32)
    b = np.ones(1 if case == "length" else 2)
    storage = np.full(4, -100.0)
    out = storage[::2] if case == "stride" else storage[:2]
    if case == "readonly":
        out.flags.writeable = False
    with pytest.raises((BufferError, ValueError)):
        native.blend_buffers_rng(a, b, out, False, draw)
    assert count == 0 and np.all(storage == -100.0)


def test_native_rng_error_preserves_output(native: ModuleType) -> None:
    """Keep the user's exact RNG exception and do not publish partial results.

    Args:
        native (ModuleType): Compiled extension.

    Raises:
        AssertionError: If error identity, output or draw count changes.
    """
    error = LookupError("original RNG failure")
    count = 0

    def draw() -> float:
        nonlocal count
        count += 1
        if count == 3:
            raise error
        return 0.9

    a, b, out = np.zeros(2), np.ones(2), np.full(2, -100.0)
    with pytest.raises(LookupError) as caught:
        native.blend_buffers_rng(a, b, out, False, draw)
    assert caught.value is error and count == 3 and out.tolist() == [-100.0, -100.0]
