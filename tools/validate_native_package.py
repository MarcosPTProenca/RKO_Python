"""Validate mixed-package artifacts without making Rust a default installation requirement.

Objective:
- Exercise pure and native wheels/sdists on each supported CI platform.

Technical approach:
- Build into fresh temporary directories to detect stale-binary contamination.
- Hide compilers for pure builds, require native compilation explicitly, and test isolated installs.
- Run the full source suite with the real opt-in extension before artifact checks.

Flow (pseudocode):
1. Build/install pure artifacts with unusable compiler commands.
2. Force a native editable build and execute real native tests and Rust checks.
3. Build/install native artifacts, then prove a later pure build stays pure.

Important criteria:
- No binary publication or release-licensing approval is performed here.

Inputs/Outputs:
- Input: checkout with synced dev dependencies, normal-GIL CPython3.14 and Rust for native steps.
- Output: successful installed-artifact contracts or the original failing command.
"""

import os
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import zipfile
from pathlib import Path


class NativePackageValidation:
    """Own one cross-platform packaging validation lifecycle.

    Responsibilities:
    - Keep source builds and installed-artifact checks separate.
    - Fail rather than disguising a requested native artifact as Python-only.

    Attributes:
        root (Path): Repository checkout.
        output (Path): Fresh ephemeral artifact directories.
    """

    def __init__(self, output: Path) -> None:
        """Bind validation to this checkout and fresh artifact storage.

        Args:
            output (Path): Temporary directory owned by the caller.
        """
        self.root = Path(__file__).resolve().parents[1]
        self.output = output

    def run(
        self,
        command: list[str],
        *,
        native_build: bool = False,
        native_runtime: bool = False,
        no_compiler: bool = False,
    ) -> None:
        """Run a real command with explicit, process-local build/runtime controls.

        Args:
            command (list[str]): Executable and arguments.
            native_build (bool): Request the mixed native build.
            native_runtime (bool): Enable the installed or source native kernel.
            no_compiler (bool): Make compiler use fail in pure-build checks.

        Raises:
            subprocess.CalledProcessError: If any build or validation fails.
        """
        env = os.environ.copy()
        env.update(
            RKO_BUILD_NATIVE="1" if native_build else "0",
            RKO_USE_NATIVE="1" if native_runtime else "0",
        )
        env["PYO3_PYTHON"] = sys.executable
        if native_runtime:
            env["RKO_TEST_NATIVE"] = "1"
        else:
            env.pop("RKO_TEST_NATIVE", None)
        if sys.platform == "linux":
            env["LD_LIBRARY_PATH"] = (
                str(sysconfig.get_config_var("LIBDIR"))
                + os.pathsep
                + env.get("LD_LIBRARY_PATH", "")
            )
        if no_compiler:
            env.update(CARGO="__rko_no_cargo__", RUSTC="__rko_no_rustc__")
        print("Running:", " ".join(command), flush=True)
        subprocess.run(command, cwd=self.root, env=env, check=True, timeout=900)

    def artifacts(self, folder: Path, *, native: bool) -> None:
        """Build isolated wheel/sdist artifacts and exercise their installed interfaces.

        Args:
            folder (Path): New artifact directory.
            native (bool): Require a real compiled native artifact.

        Raises:
            AssertionError: If wheel tags or packaged binary presence are incorrect.
            subprocess.CalledProcessError: If build or installed checks fail.
        """
        self.run(
            ["uv", "build", "--out-dir", str(folder)], native_build=native, no_compiler=not native
        )
        wheels = list(folder.glob("*.whl"))
        sources = list(folder.glob("*.tar.gz"))
        assert len(wheels) == len(sources) == 1
        with zipfile.ZipFile(wheels[0]) as wheel:
            contains = any(
                name.startswith("rko/_native.") and name.endswith((".so", ".pyd"))
                for name in wheel.namelist()
            )
            metadata = next(name for name in wheel.namelist() if name.endswith(".dist-info/WHEEL"))
            pure = "Root-Is-Purelib: true" in wheel.read(metadata).decode()
            assert contains == native and pure != native
            for notice in (
                "LICENSE",
                "NOTICE",
                "THIRD_PARTY_LICENSES.txt",
                "RUST_LIBRARY_COPYRIGHT.html",
            ):
                assert any(
                    name.endswith("/" + notice) and ".dist-info/licenses/" in name
                    for name in wheel.namelist()
                )
        with tarfile.open(sources[0]) as source:
            names = source.getnames()
            for suffix in (
                "/native/Cargo.toml",
                "/native/Cargo.lock",
                "/native/src/lib.rs",
                "/rust-toolchain.toml",
            ):
                assert any(name.endswith(suffix) for name in names)
            assert not any(name.endswith((".so", ".pyd", ".dll")) for name in names)
        for artifact in wheels + sources:
            self.run(
                [
                    "uv",
                    "run",
                    "--isolated",
                    "--no-project",
                    "--with",
                    str(artifact),
                    "python",
                    "-I",
                    "tools/smoke_native.py",
                    "--binary",
                    "present" if native else "absent",
                ],
                native_build=native,
                no_compiler=not native,
            )
        if native:
            self.run(
                [
                    "uv",
                    "run",
                    "--isolated",
                    "--no-project",
                    "--with",
                    str(wheels[0]),
                    "python",
                    "-I",
                    "tools/smoke_installed.py",
                ],
                native_runtime=True,
            )

    def validate(self) -> None:
        """Execute pure, native and post-native-pure validation in order.

        Raises:
            Exception: Original build, native, test or installation failures propagate.
        """
        self.artifacts(self.output / "python", native=False)
        self.run(
            ["uv", "sync", "--locked", "--group", "dev", "--reinstall-package", "rko"],
            native_build=True,
        )
        self.run(
            [
                "uv",
                "run",
                "--locked",
                "--no-sync",
                "cargo",
                "fmt",
                "--manifest-path",
                "native/Cargo.toml",
                "--all",
                "--",
                "--check",
            ]
        )
        self.run(
            [
                "uv",
                "run",
                "--locked",
                "--no-sync",
                "cargo",
                "test",
                "--locked",
                "--manifest-path",
                "native/Cargo.toml",
            ]
        )
        self.run(
            [
                "uv",
                "run",
                "--locked",
                "--no-sync",
                "cargo",
                "clippy",
                "--locked",
                "--manifest-path",
                "native/Cargo.toml",
                "--all-targets",
                "--",
                "-D",
                "warnings",
            ]
        )
        self.run(
            ["uv", "run", "--locked", "--no-sync", "pytest", "src/rko/tests", "-q"],
            native_runtime=True,
        )
        self.artifacts(self.output / "native", native=True)
        self.artifacts(self.output / "python-after-native", native=False)


def main() -> None:
    """Validate without retaining or publishing compiled artifacts.

    Raises:
        Exception: Any failed packaging or installed contract aborts validation.
    """
    with tempfile.TemporaryDirectory(prefix="rko-native-validation-") as directory:
        NativePackageValidation(Path(directory)).validate()


if __name__ == "__main__":
    main()
