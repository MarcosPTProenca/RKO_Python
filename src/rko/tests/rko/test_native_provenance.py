"""Check solver-result provenance for the selected optional blending implementation.

Objective:
- Distinguish admitted acceleration from a merely installed or requested binary.

Technical approach:
- Import the package in independent processes with controlled extension admission.
- Exercise an actual public solve without relying on a native compiler.

Flow (pseudocode):
1. Configure disabled, incompatible or admitted optional extension state.
2. Run the public serial solver and inspect immutable runtime versions.
3. Require native provenance only when acceleration was admitted.

Important criteria:
- Component selection is not evidence that a specific search invoked the kernel.

Inputs/Outputs:
- Input: runtime activation and external module contract.
- Output: asserted result provenance and successful public execution.
"""

import os
import pytest
import subprocess
import sys
import sysconfig


@pytest.mark.parametrize("mode", ["disabled", "incompatible", "admitted"])
def test_solver_records_only_admitted_native_component(mode: str) -> None:
    """Record the selected component without changing default version metadata.

    Args:
        mode (str): Optional extension admission scenario.

    Raises:
        subprocess.CalledProcessError: If selected component provenance is incorrect.
    """
    code = """
import sys
import types
import warnings
import numpy as np
module = types.ModuleType("rko._native")
module.BUILD_MODE = "release"
module.BLENDING_CONTRACT = __CONTRACT_VALUE__
module.blend_buffers_rng = lambda *args: None
sys.modules["rko._native"] = module
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    from rko import RKO
result = RKO(lambda x: x, lambda x: float(np.dot(x, x)), 2,
             algorithms=["MultiStart"], adaptation="fixed", backend="serial",
             random_state=42).solve(0.01)
versions = dict(result.versions)
assert set(versions) == ({"rko", "python", "numpy", "rko-native-blending"}
                        if ADMITTED else {"rko", "python", "numpy"})
if ADMITTED:
    assert versions["rko-native-blending"] == "rko-blending-rng-buffer-v1"
"""
    code = code.replace(
        "__CONTRACT_VALUE__",
        repr("wrong" if mode == "incompatible" else "rko-blending-rng-buffer-v1"),
    )
    admitted = (
        mode == "admitted"
        and sys.implementation.name == "cpython"
        and sys.version_info[:2] == (3, 14)
        and not sysconfig.get_config_var("Py_GIL_DISABLED")
    )
    code = code.replace("ADMITTED", repr(admitted))
    env = dict(os.environ, RKO_USE_NATIVE="0" if mode == "disabled" else "1")
    subprocess.run([sys.executable, "-c", code], env=env, check=True, timeout=30)
