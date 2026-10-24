"""Collect installed-wheel timed portfolio pairs without profiling timed callbacks.

Objective:
- Expose complete invocation, normalized quality and process-tree memory observations.

Technical approach:
- Alternate disabled/enabled native workers in fresh isolated interpreters.
- Run the same opaque callback fixtures and wheel in each variant.
- Sample Linux process-tree proportional memory, excluding this collector.

Flow (pseudocode):
1. Require explicit installed interpreter and bounded paired seed coverage.
2. Launch one worker session at a time and preserve stdout/stderr, including failures.
3. Validate installed source identity and emit descriptive paired observations.

Important criteria:
- This is a timed quality/resource screening protocol, not fixed-work replay.
- Sampled PSS is proportional physical memory, not an exact high-water mark.
- No statistical noninferiority, speedup or C++ parity gate is inferred here.
- Run on otherwise idle hosted runners, never beside the protected historical run.

Inputs/Outputs:
- Input: installed mixed-wheel interpreter, backend, adaptation and new output folder.
- Output: raw logs and source-identified paired JSONL observations.
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from benchmarks.performance_profile import PerformanceProbe
from pathlib import Path


class ProcessTreeMemory:
    """Sample one owned worker process tree without counting collector memory.

    Responsibilities:
    - Follow recursive children while including manager and tracker helpers.
    - Report missing/partial snapshots explicitly rather than inventing zero memory.

    Attributes:
        pid (int): Fresh isolated worker process ID.
        samples (list[int]): Complete tree PSS totals in bytes.
        partial (int): Incomplete snapshots, including process-exit races.
        stop_event (threading.Event): Trial-owned cancellation event.
        thread (threading.Thread): Joined sampler thread.
    """

    def __init__(self, pid: int) -> None:
        """Prepare a sampler for one owned trial process.

        Args:
            pid (int): Worker PID returned by Popen.
        """
        self.pid = pid
        self.samples: list[int] = []
        self.partial = 0
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.sample, name="tree-pss", daemon=True)

    @staticmethod
    def snapshot(pid: int) -> int:
        """Sum PSS for a recursively enumerated live Linux process tree.

        Args:
            pid (int): Root worker PID, excluding the collector.

        Returns:
            int: Process-tree proportional resident bytes.

        Raises:
            OSError: If procfs is unavailable, restricted or a process exits mid-snapshot.
            ValueError: If PSS cannot be read rather than observed as zero.
        """
        pending, seen, total = [pid], set(), 0
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            root = Path(f"/proc/{current}")
            tasks = list((root / "task").iterdir())
            for task in tasks:
                pending.extend(map(int, (task / "children").read_text().split()))
            lines = (root / "smaps_rollup").read_text().splitlines()
            values = [int(line.split()[1]) * 1024 for line in lines if line.startswith("Pss:")]
            if len(values) != 1:
                raise ValueError("Missing PSS observation")
            total += values[0]
        return total

    def sample(self) -> None:
        """Collect complete snapshots approximately every20ms until stopped."""
        while not self.stop_event.is_set():
            try:
                self.samples.append(self.snapshot(self.pid))
            except OSError, ValueError:
                self.partial += 1
            self.stop_event.wait(0.02)

    def start(self) -> None:
        """Start the trial-owned sampler.

        Raises:
            RuntimeError: If the sampler thread cannot be started.
        """
        self.thread.start()

    def stop(self) -> None:
        """Cancel and join the sampler after the worker exits."""
        self.stop_event.set()
        self.thread.join()


class NativePortfolioStudy:
    """Collect explicit paired timed trials without changing worker search callbacks.

    Responsibilities:
    - Preserve complete raw failures and distinguish selection from native speed proof.
    - Reject missing native admission and mixed installed-source identities.

    Attributes:
        args (argparse.Namespace): Bounded installed-worker settings.
        worker (Path): Maintained installed-artifact probe source.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        """Bind collection to explicit settings and a new observation folder.

        Args:
            args (argparse.Namespace): Collector command-line settings.

        Raises:
            ValueError: If settings or Linux measurement support are invalid.
            FileExistsError: If the output folder already exists.
        """
        if sys.platform != "linux" or not Path("/proc/self/smaps_rollup").is_file():
            raise ValueError("Process-tree PSS collection requires Linux procfs")
        if args.repeats < 1 or not 0 <= args.seed_start <= 2**32 - args.repeats:
            raise ValueError("Invalid paired seed coverage")
        if not 0 < args.seconds <= 60:
            raise ValueError("Search duration must be finite and within(0,60] seconds")
        self.args = args
        self.worker = Path(__file__).resolve().parents[1] / "tools/smoke_portfolio.py"
        args.output.mkdir(parents=True, exist_ok=False)

    @staticmethod
    def validate_pair(rows: dict[str, dict]) -> None:
        """Reject fallback, altered settings or mixed installed wheel sources.

        Args:
            rows (dict[str, dict]): Reference and native raw worker observations.

        Raises:
            ValueError: If the pair is incomplete or its comparison boundary differs.
        """
        if set(rows) != {"python", "native"}:
            raise ValueError("Incomplete native/reference pair")
        baseline, candidate = rows["python"], rows["native"]
        if baseline["native_admitted"] or not candidate["native_admitted"]:
            raise ValueError("Native admission or reference selection failed")
        for key in (
            "backend",
            "adaptation",
            "workload",
            "dimension",
            "seconds",
            "seed",
            "functional",
            "installed_sources_sha256",
            "n_workers",
        ):
            if baseline[key] != candidate[key]:
                raise ValueError(f"Mixed pair field: {key}")
        if candidate["functional"]:
            raise ValueError("Functional profiler probes cannot enter timed evidence")
        if any(
            baseline["versions"][key] != candidate["versions"][key]
            for key in ("rko", "python", "numpy")
        ):
            raise ValueError("Mixed runtime versions")

    def run(self) -> None:
        """Collect every preregistered pair and retain failed raw worker output.

        Raises:
            Exception: Original worker, observation or contract failures abort collection.
        """
        args = self.args
        provenance = PerformanceProbe.provenance()
        manifest = {
            "kind": "protocol",
            "provenance": provenance,
            "worker_sha256": hashlib.sha256(self.worker.read_bytes()).hexdigest(),
            "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python": str(args.python),
            "backend": args.backend,
            "adaptation": args.adaptation,
            "repeats": args.repeats,
            "seed_start": args.seed_start,
            "seconds": args.seconds,
            "dimensions": [20, 500],
            "workloads": ["object", "permutation"],
            "pss_sample_seconds": 0.02,
            "scope": "descriptive_timed_screen_not_acceptance",
            "threads": {
                key: os.environ.get(key)
                for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
            },
        }
        (args.output / "protocol.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        installed_identity = None
        with (args.output / "pairs.jsonl").open("w", encoding="utf-8") as pairs:
            for dimension in manifest["dimensions"]:
                for workload in manifest["workloads"]:
                    for index in range(args.repeats):
                        seed, rows = args.seed_start + index, {}
                        order = ("python", "native") if index % 2 == 0 else ("native", "python")
                        for label in order:
                            prefix = args.output / f"{dimension}-{workload}-{seed}-{label}"
                            command = [
                                str(args.python),
                                "-I",
                                str(self.worker),
                                "--backend",
                                args.backend,
                                "--adaptation",
                                args.adaptation,
                                "--dimension",
                                str(dimension),
                                "--workload",
                                workload,
                                "--seed",
                                str(seed),
                                "--seconds",
                                str(args.seconds),
                            ]
                            env = dict(os.environ, RKO_USE_NATIVE="1" if label == "native" else "0")
                            with (
                                prefix.with_suffix(".json").open("w", encoding="utf-8") as stdout,
                                prefix.with_suffix(".stderr").open("w", encoding="utf-8") as stderr,
                            ):
                                started = time.perf_counter()
                                with subprocess.Popen(
                                    command,
                                    env=env,
                                    stdout=stdout,
                                    stderr=stderr,
                                    start_new_session=True,
                                ) as process:
                                    monitor = ProcessTreeMemory(process.pid)
                                    monitor.start()
                                    try:
                                        status = process.wait(timeout=120 + args.seconds * 4)
                                    finally:
                                        if process.poll() is None:
                                            os.killpg(process.pid, signal.SIGKILL)
                                            process.wait()
                                        monitor.stop()
                            elapsed = time.perf_counter() - started
                            if status:
                                raise subprocess.CalledProcessError(status, command)
                            row = json.loads(prefix.with_suffix(".json").read_text())
                            row.update(
                                fresh_process_seconds=elapsed,
                                sampled_peak_tree_pss_bytes=max(monitor.samples, default=None),
                                pss_complete_samples=len(monitor.samples),
                                pss_partial_samples=monitor.partial,
                            )
                            if not monitor.samples:
                                raise ValueError("No complete process-tree PSS observations")
                            rows[label] = row
                        self.validate_pair(rows)
                        identity = rows["native"]["installed_sources_sha256"]
                        if installed_identity is not None and installed_identity != identity:
                            raise ValueError("Installed wheel changed between pairs")
                        installed_identity = identity
                        pairs.write(json.dumps({"kind": "pair", "order": order, **rows}) + "\n")
                        pairs.flush()
        if PerformanceProbe.provenance()["source_sha256"] != provenance["source_sha256"]:
            raise ValueError("Production source changed during collection")
        if (
            hashlib.sha256(self.worker.read_bytes()).hexdigest() != manifest["worker_sha256"]
            or hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            != manifest["collector_sha256"]
        ):
            raise ValueError("Measurement helper changed during collection")


def main() -> None:
    """Collect a bounded descriptive screen with an explicitly installed interpreter.

    Raises:
        Exception: Invalid settings or any failed trial abort collection.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("serial", "thread", "process"), required=True)
    parser.add_argument("--adaptation", choices=("fixed", "adaptive"), required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed-start", type=int, default=40000)
    parser.add_argument("--seconds", type=float, default=2.0)
    NativePortfolioStudy(parser.parse_args()).run()


if __name__ == "__main__":
    main()
