"""Check explicit native source-build requests at the distribution boundary.

Objective:
- Never silently convert a requested native build into a Python-only wheel.

Technical approach:
- Exercise the actual PEP517 frontend with invalid configuration or missing compiler commands.

Flow (pseudocode):
1. Give the build frontend a fresh output directory and explicit native mode.
2. Make the requested build invalid before compilation.
3. Require a build failure rather than a misleading wheel.

Important criteria:
- The ordinary Python-only build is independently covered by installed-artifact CI.

Inputs/Outputs:
- Input: explicit native build environment.
- Output: observed frontend failure and no published wheel.
"""

import json
import os
import pytest
import shutil
import subprocess
from pathlib import Path
from tools.check_native_licenses import check


@pytest.mark.parametrize("mode", ["invalid", "1"])
def test_explicit_native_build_cannot_silently_fallback(mode: str, tmp_path: Path) -> None:
    """Reject invalid native configuration and missing compiler commands.

    Args:
        mode (str): Invalid or explicitly enabled native build.
        tmp_path (Path): Isolated artifact directory.

    Raises:
        AssertionError: If the build succeeds or leaves a misleading wheel.
    """
    root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env.update(RKO_BUILD_NATIVE=mode, CARGO="__rko_no_cargo__", RUSTC="__rko_no_rustc__")
    completed = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode != 0
    assert not list(tmp_path.glob("*.whl"))
    if mode == "invalid":
        assert "RKO_BUILD_NATIVE" in completed.stderr


def test_native_notice_inventory_rejects_changed_content(tmp_path: Path) -> None:
    """Keep locked dependencies and exact upstream notices synchronized.

    Args:
        tmp_path (Path): Independent source fixture, not the real checkout.

    Raises:
        AssertionError: If altered notices can pass the source consistency check.
    """
    root = Path(__file__).resolve().parents[3]
    names = ["native/Cargo.lock", "rust-toolchain.toml", "native/licenses/inventory.json"]
    inventory = json.loads((root / names[-1]).read_text())
    names.extend(inventory["bundled_files_sha256"])
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)
    assert check(tmp_path) == {"cargo_packages": 14, "rust_toolchain": "1.90.0"}
    (tmp_path / "native/licenses/THIRD_PARTY_LICENSES.txt").write_text("altered notice")
    with pytest.raises(ValueError, match="notice content"):
        check(tmp_path)
