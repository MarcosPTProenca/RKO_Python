"""Inspect trusted repaired native wheels without uploading release binaries.

Objective:
- Reject incorrect ABI tags, missing notices and unreviewed bundled native libraries.

Technical approach:
- Read wheel metadata and compare bundled notice contents with the source inventory.
- Identify the sole expected extension and retain a digest-only inspection report.

Flow (pseudocode):
1. Open each trusted CI-produced wheel without extracting archive paths.
2. Check normal CPython3.14 native tags and exact bundled notices.
3. Reject additional vendored binaries pending attribution review.

Important criteria:
- Repaired wheel tests establish host-specific compatibility, not universal support.
- Inspection is neither legal ownership approval nor release publication.

Inputs/Outputs:
- Input: trusted wheelhouse produced by the pinned CI builder.
- Output: inspection.json containing hashes, tags and bundled notice identities.
"""

import argparse
import hashlib
import json
import zipfile
from email.parser import Parser
from pathlib import Path


def inspect_wheel(path: Path) -> dict[str, object]:
    """Validate a repaired native wheel's ABI, binary inventory and source notices.

    Args:
        path (Path): Trusted wheel produced by the qualification workflow.

    Returns:
        dict[str, object]: Artifact digest, ABI/platform tags and notice identities.

    Raises:
        ValueError: If the native ABI, binary inventory or notices are incorrect.
        OSError: If the wheel cannot be read.
        zipfile.BadZipFile: If the input is not a readable wheel archive.
    """
    with zipfile.ZipFile(path) as wheel:
        names = wheel.namelist()
        metadata = [name for name in names if name.endswith(".dist-info/WHEEL")]
        if len(metadata) != 1:
            raise ValueError("Expected one wheel metadata record")
        headers = Parser().parsestr(wheel.read(metadata[0]).decode())
        tags = headers.get_all("Tag", [])
        if (
            headers.get("Root-Is-Purelib") != "false"
            or not tags
            or not all(tag.startswith("cp314-cp314-") for tag in tags)
        ):
            raise ValueError("Expected normal CPython3.14 native wheel tags")
        if not all(
            tag.split("-", 2)[2].startswith(("manylinux_", "macosx_", "win_")) for tag in tags
        ):
            raise ValueError("Wheel lacks a repaired portable platform tag")
        parts = path.stem.rsplit("-", 3)
        if len(parts) != 4:
            raise ValueError("Malformed wheel filename")
        filename_tags = {f"{parts[1]}-{parts[2]}-{platform}" for platform in parts[3].split(".")}
        if set(tags) != filename_tags:
            raise ValueError("Wheel filename and metadata tags differ")
        binaries = [name for name in names if name.endswith((".so", ".pyd", ".dll", ".dylib"))]
        if len(binaries) != 1 or not binaries[0].startswith("rko/_native."):
            raise ValueError("Unexpected bundled native library requires attribution review")
        inventories = [
            name for name in names if name.endswith("/licenses/native/licenses/inventory.json")
        ]
        if len(inventories) != 1:
            raise ValueError("Missing native notice inventory")
        inventory = json.loads(wheel.read(inventories[0]))
        prefix = inventories[0].removesuffix("native/licenses/inventory.json")
        for name, digest in inventory["bundled_files_sha256"].items():
            target = prefix + name
            if target not in names or hashlib.sha256(wheel.read(target)).hexdigest() != digest:
                raise ValueError(f"Missing or altered native notice: {name}")
        if not all(prefix + name in names for name in ("LICENSE", "NOTICE")):
            raise ValueError("Missing project license or attribution")
    return {
        "wheel": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "tags": tags,
        "binaries": binaries,
        "notices_sha256": inventory["bundled_files_sha256"],
        "release_authorized": False,
    }


def main() -> None:
    """Write inspection metadata while leaving compiled artifacts local to the CI job.

    Raises:
        ValueError: If no wheel exists or an inspection fails.
        OSError: If input or report files cannot be accessed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheelhouse", type=Path)
    args = parser.parse_args()
    wheels = sorted(args.wheelhouse.glob("*.whl"))
    if not wheels:
        raise ValueError("No native wheels to inspect")
    rows = [inspect_wheel(path) for path in wheels]
    (args.wheelhouse / "inspection.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
