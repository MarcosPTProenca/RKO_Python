"""Check that the native dependency lock and bundled notices stay synchronized.

Objective:
- Prevent a native dependency/toolchain update from silently dropping notice review.

Technical approach:
- Compare every resolved registry package/checksum with the committed inventory.
- Verify exact notice digests and the pinned Rust toolchain version.

Flow (pseudocode):
1. Read the locked dependency graph and source-identified notice inventory.
2. Reject missing/changed dependencies or notice files.
3. Report inventory coverage without asserting legal ownership or release approval.

Important criteria:
- The owner's combined-implementation licensing gate in NOTICE remains unresolved.

Inputs/Outputs:
- Input: committed Cargo.lock, rust-toolchain.toml and native/licenses inventory.
- Output: notice consistency assertion, not legal certification.
"""

import hashlib
import json
import tomllib
from pathlib import Path


def check(root: Path) -> dict[str, int | str]:
    """Validate the exact dependency/toolchain notice inventory.

    Args:
        root (Path): Repository or unpacked source-distribution root.

    Returns:
        dict[str, int | str]: Verified package count and toolchain identifier.

    Raises:
        ValueError: If notices or lock identities changed without review.
        OSError: If a required source or license file is missing.
    """
    lock = tomllib.loads((root / "native/Cargo.lock").read_text())
    inventory = json.loads((root / "native/licenses/inventory.json").read_text())
    expected = {
        (p["name"], p["version"], p["checksum"]) for p in lock["package"] if p.get("source")
    }
    actual = {(p["name"], p["version"], p["checksum"]) for p in inventory["cargo_packages"]}
    if actual != expected or len(actual) != len(inventory["cargo_packages"]):
        raise ValueError("Native dependency notices do not match Cargo.lock")
    if any(
        not p["license_expression"] or not p["license_texts"] for p in inventory["cargo_packages"]
    ):
        raise ValueError("Incomplete native dependency license inventory")
    for name, digest in inventory["bundled_files_sha256"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not name.startswith("native/licenses/"):
            raise ValueError("Invalid native notice path")
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Native notice content changed without inventory review")
    toolchain = tomllib.loads((root / "rust-toolchain.toml").read_text())["toolchain"]["channel"]
    if toolchain != inventory["rust_toolchain"]["version"]:
        raise ValueError("Native toolchain notices do not match the pinned version")
    return {"cargo_packages": len(expected), "rust_toolchain": toolchain}


def main() -> None:
    """Check this source checkout without requiring a Rust compiler.

    Raises:
        Exception: Source/inventory validation failures propagate.
    """
    print(json.dumps(check(Path(__file__).resolve().parents[1])))


if __name__ == "__main__":
    main()
