"""Check optional native activation at a fresh-process package boundary.

Objective:
- Preserve default Python operation and observable unavailable-extension fallback.

Technical approach:
- Start fresh interpreters so environment opt-in is evaluated before importing rko.
- Block the optional binary dependency at the import-system boundary only.

Flow (pseudocode):
1. Select disabled or explicit native mode in the child environment.
2. Import the ordinary public blending operator without a binary dependency.
3. Assert deterministic behavior and a clear fallback warning when requested.

Important criteria:
- Missing native acceleration must not break the Python installation.

Inputs/Outputs:
- Input: activation environment and absent optional binary.
- Output: subprocess behavior assertions.
"""

import os
import pytest
import subprocess
import sys
import sysconfig


@pytest.mark.parametrize("enabled", [False, True])
def test_missing_optional_native_keeps_public_operator_working(enabled: bool) -> None:
    """Preserve computation and expose requested-but-unavailable native fallback.

    Args:
        enabled (bool): Explicit runtime native opt-in.

    Raises:
        subprocess.CalledProcessError: If import, computation or warning behavior changes.
    """
    code = """
import sys
import warnings
sys.modules['rko._native'] = None
with warnings.catch_warnings(record=True) as observed:
    warnings.simplefilter('always')
    import numpy as np
    from rko.components.blending.blending import blending
    from rko.components.random_streams import RandomStreams
    with RandomStreams(42).activate():
        result = blending(np.array([0.1, 0.2]), np.array([0.8, 0.9]))
    assert result.tolist() == [0.1, 0.2]
    notices = [w for w in observed if 'RKO_USE_NATIVE' in str(w.message)]
    assert len(notices) == EXPECTED
""".replace("EXPECTED", "1" if enabled else "0")
    env = os.environ.copy()
    env["RKO_USE_NATIVE"] = "1" if enabled else "0"
    subprocess.run([sys.executable, "-c", code], env=env, check=True, timeout=30)


@pytest.mark.parametrize("compatible", [False, True])
def test_extension_contract_and_runtime_errors_are_not_confused(compatible: bool) -> None:
    """Fallback on an incompatible binary, but propagate an admitted kernel failure.

    Args:
        compatible (bool): External extension advertises the expected contract.

    Raises:
        subprocess.CalledProcessError: If activation masks errors or admits wrong binaries.
    """
    code = """
import sys
import types
import warnings
module = types.ModuleType('rko._native')
error = LookupError('original kernel failure')
def failing(*args):
    raise error
module.blend_buffers_rng = failing
module.BUILD_MODE = 'release'
module.BLENDING_CONTRACT = __CONTRACT_VALUE__
sys.modules['rko._native'] = module
with warnings.catch_warnings(record=True) as observed:
    warnings.simplefilter('always')
    import numpy as np
    from rko.components.blending.blending import blending
    from rko.components.random_streams import RandomStreams
    with RandomStreams(42).activate():
        try:
            result = blending(np.array([0.1, 0.2]), np.array([0.8, 0.9]))
        except LookupError as caught:
            assert COMPATIBLE and caught is error
        else:
            assert not COMPATIBLE and result.tolist() == [0.1, 0.2]
    notices = [w for w in observed if 'RKO_USE_NATIVE' in str(w.message)]
    assert len(notices) == (0 if COMPATIBLE else 1)
""".replace("__CONTRACT_VALUE__", repr("rko-blending-rng-buffer-v1" if compatible else "wrong"))
    admitted = (
        compatible
        and sys.implementation.name == "cpython"
        and sys.version_info[:2] == (3, 14)
        and not sysconfig.get_config_var("Py_GIL_DISABLED")
    )
    code = code.replace("COMPATIBLE", str(admitted))
    env = os.environ.copy()
    env["RKO_USE_NATIVE"] = "1"
    subprocess.run([sys.executable, "-c", code], env=env, check=True, timeout=30)
