"""Reject repaired native wheels with unsupported ABI or unreviewed binary notices.

Objective:
- Protect the CI inspection boundary independently of compiler availability.

Technical approach:
- Construct tiny trusted wheel fixtures with exact notice digests.

Flow (pseudocode):
1. Inspect a normal CPython3.14 wheel fixture.
2. Alter its ABI, native dependency set or notice bytes.
3. Require rejection rather than release-ready metadata.

Important criteria:
- Fixture binaries are metadata-only; hosted tests require actual native execution.

Inputs/Outputs:
- Input: temporary wheel archive.
- Output: inspection assertions or a precise rejection.
"""

import hashlib
import json
import pytest
import zipfile
from pathlib import Path
from tools.inspect_native_wheel import inspect_wheel


@pytest.mark.parametrize("fault", ["none", "abi", "library", "notice", "license"])
def test_repaired_wheel_inventory(tmp_path: Path, fault: str) -> None:
    """Require the expected ABI and reject missing notices or extra native libraries.

    Args:
        tmp_path (Path): Isolated fixture directory.
        fault (str): Individual artifact defect or valid case.

    Raises:
        AssertionError: If an invalid repaired wheel is admitted.
    """
    path = tmp_path / "rko-0.3.0.dev0-cp314-cp314-manylinux_2_28_x86_64.whl"
    root = "rko-0.3.0.dev0.dist-info/"
    notice = b"original upstream notice"
    inventory = {
        "bundled_files_sha256": {
            "native/licenses/THIRD_PARTY_LICENSES.txt": hashlib.sha256(notice).hexdigest()
        }
    }
    with zipfile.ZipFile(path, "w") as wheel:
        tag = (
            "cp314t-cp314t-manylinux_2_28_x86_64"
            if fault == "abi"
            else "cp314-cp314-manylinux_2_28_x86_64"
        )
        wheel.writestr(root + "WHEEL", f"Root-Is-Purelib: false\nTag: {tag}\n")
        wheel.writestr("rko/_native.cpython-314-x86_64-linux-gnu.so", b"fixture, not a real binary")
        wheel.writestr(root + "licenses/NOTICE", b"preserved owner gate")
        if fault != "license":
            wheel.writestr(root + "licenses/LICENSE", b"project license")
        wheel.writestr(root + "licenses/native/licenses/inventory.json", json.dumps(inventory))
        wheel.writestr(
            root + "licenses/native/licenses/THIRD_PARTY_LICENSES.txt",
            b"altered" if fault == "notice" else notice,
        )
        if fault == "library":
            wheel.writestr("rko.libs/new.so", b"unreviewed foreign library")
    if fault != "none":
        with pytest.raises(ValueError):
            inspect_wheel(path)
    else:
        row = inspect_wheel(path)
        assert row["release_authorized"] is False
        assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
