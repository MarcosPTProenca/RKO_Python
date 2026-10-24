"""Resolve explicit optional native blending without requiring a compiled installation.

Objective:
- Keep ordinary Python imports and installations independent of Rust.

Technical approach:
- Read runtime opt-in once when the blending module imports.
- Admit only a release extension matching the frozen replay contract and supported ABI.

Flow (pseudocode):
1. Return Python mode unless explicitly requested.
2. Check interpreter support and import the optional binary.
3. Return a compatible kernel or emit one actionable fallback warning.

Important criteria:
- Runtime kernel/callback failures are never caught as optional-import failures.

Inputs/Outputs:
- Input: RKO_USE_NATIVE and the installed optional extension.
- Output: Compatible callable or None for reference execution.
"""

import importlib
import os
import sys
import sysconfig
import warnings
from collections.abc import Callable

BLENDING_CONTRACT = "rko-blending-rng-buffer-v1"


def load_blending_kernel() -> Callable[..., None] | None:
    """Load explicit native acceleration or explain a safe Python fallback.

    Returns:
        Callable[..., None] | None: Admitted release kernel, otherwise reference mode.

    Raises:
        Exception: Unexpected native initialization defects propagate unchanged.
    """
    mode = os.environ.get("RKO_USE_NATIVE", "0")
    if mode == "0":
        return None
    reason = ""
    kernel = None
    if mode != "1":
        reason = "expected RKO_USE_NATIVE=0 or 1"
    elif (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 14)
        or sysconfig.get_config_var("Py_GIL_DISABLED")
    ):
        reason = "native blending currently supports normal-GIL CPython 3.14 only"
    else:
        try:
            module = importlib.import_module("rko._native")
        except (ImportError, OSError) as error:
            reason = f"optional release extension is unavailable ({error})"
        else:
            kernel = getattr(module, "blend_buffers_rng", None)
            if (
                getattr(module, "BLENDING_CONTRACT", None) != BLENDING_CONTRACT
                or getattr(module, "BUILD_MODE", None) != "release"
                or not callable(kernel)
            ):
                reason = "optional extension does not match the release/replay contract"
    if reason:
        warnings.warn(
            f"RKO_USE_NATIVE: {reason}; using Python blending.", UserWarning, stacklevel=2
        )
        return None
    return kernel
