"""Preserve Python-only packaging with an explicitly requested mixed Rust build.

Objective:
- Keep source installation independent of a Rust compiler unless native build is requested.

Technical approach:
- Retain setuptools metadata and register one release-only optional component on opt-in.
- Treat an explicitly requested native compilation failure as a build failure.

Flow (pseudocode):
1. Validate RKO_BUILD_NATIVE and the supported native interpreter ABI.
2. Register a locked release Rust extension only for an explicit request.
3. Delegate ordinary package construction to setuptools.

Important criteria:
- Runtime activation is separate: RKO_USE_NATIVE defaults to disabled.

Inputs/Outputs:
- Input: build environment and the existing pyproject metadata.
- Output: pure Python distribution or explicitly built platform wheel.
"""

import os
import sys
import sysconfig
from setuptools import setup
from setuptools_rust import Binding
from setuptools_rust import RustExtension

mode = os.environ.get("RKO_BUILD_NATIVE", "0")
if mode not in ("0", "1"):
    raise RuntimeError("RKO_BUILD_NATIVE must be 0 or 1")
extensions: list[RustExtension] = []
if mode == "1":
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 14)
        or sysconfig.get_config_var("Py_GIL_DISABLED")
    ):
        raise RuntimeError("RKO_BUILD_NATIVE=1 supports normal-GIL CPython 3.14 only")
    extensions.append(
        RustExtension(
            "rko._native",
            path="native/Cargo.toml",
            binding=Binding.PyO3,
            cargo_manifest_args=["--locked"],
            features=["extension-module"],
            debug=False,
            optional=False,
        )
    )
setup(rust_extensions=extensions)
