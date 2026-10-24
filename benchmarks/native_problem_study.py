"""Compare the native Rust engine with the C++ reference on non-Knapsack problem families.

Objective:
- Test whether the native engine's advantage over C++ holds beyond Knapsack, on a
  permutation problem (TSP, sorting decoder) and a continuous multimodal problem
  (shifted Rastrigin), neither of which uses constant-time move evaluation.

Technical approach:
- Generate deterministic instances: Euclidean TSP with rounded (TSPLIB EUC_2D) distances
  and Rastrigin with a random optimum shift.
- Build the pinned C++ reference with only its `Problem.h` replaced by the matching
  decoder, and widen the written key precision.
- Run each implementation sequentially, score every returned key vector independently in
  Python, and compare quality: the gap to the best tour found by any trial (TSP) or the
  objective itself (Rastrigin, optimum zero).

Flow (pseudocode):
1. Write instances and build the C++ reference and the native binary.
2. For each instance, solver and replicate run both implementations in alternating order.
3. Re-score the returned keys, write raw rows and print paired exact sign tests.

Important criteria:
- Quality is lower-is-better; TSP uses the gap to the best tour across all trials of the
  instance, Rastrigin the objective value.
- Failed trials stay in the output; an objective that cannot be verified is a failure.

Inputs/Outputs:
- Input: budget, repetitions, solver names, instance sizes and cache/output paths.
- Output: raw trial CSV and a printed paired summary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import numpy as np
import random
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from benchmarks.cpp_python_knapsack import CPP_FLAGS
from benchmarks.cpp_python_knapsack import CPP_REVISION
from benchmarks.cpp_python_knapsack import SAMPLE_SEED
from benchmarks.cpp_python_knapsack import SOLVER_CONFIGS
from benchmarks.cpp_python_knapsack import KnapsackBenchmark
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

TSP_PROBLEM_HEADER = """#ifndef _PROBLEM_H
#define _PROBLEM_H

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <numeric>

struct TProblemData
{
    int n;
    std::vector<double> d;
};

void ReadData(char name[], TProblemData &data)
{
    FILE *arq = fopen(name, "r");
    if (arq == NULL) { printf("\\nERROR: File (%s) not found!\\n", name); exit(1); }
    int n = 0;
    if (fscanf(arq, "%d", &n) != 1) { exit(1); }
    std::vector<double> x(n), y(n);
    for (int i = 0; i < n; i++)
    {
        if (fscanf(arq, "%lf %lf", &x[i], &y[i]) != 2) { exit(1); }
    }
    fclose(arq);
    data.n = n;
    data.d.assign((size_t)n * n, 0.0);
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            data.d[(size_t)i * n + j] = std::floor(std::hypot(x[i] - x[j], y[i] - y[j]) + 0.5);
}

double Decoder(TSol &s, const TProblemData &data)
{
    std::vector<int> order(data.n);
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](int a, int b) {
        return s.rk[a] < s.rk[b] || (s.rk[a] == s.rk[b] && a < b);
    });
    double total = 0.0;
    int previous = order.back();
    for (int city : order)
    {
        total += data.d[(size_t)previous * data.n + city];
        previous = city;
    }
    return total;
}

void FreeMemoryProblem(TProblemData &data)
{
    data.d.clear();
}

#endif
"""


RASTRIGIN_PROBLEM_HEADER = """#ifndef _PROBLEM_H
#define _PROBLEM_H

#include <cmath>
#include <cstdio>

struct TProblemData
{
    int n;
    std::vector<double> shift;
};

void ReadData(char name[], TProblemData &data)
{
    FILE *arq = fopen(name, "r");
    if (arq == NULL) { printf("\\nERROR: File (%s) not found!\\n", name); exit(1); }
    int n = 0;
    if (fscanf(arq, "%d", &n) != 1) { exit(1); }
    data.n = n;
    data.shift.assign(n, 0.0);
    for (int i = 0; i < n; i++)
    {
        if (fscanf(arq, "%lf", &data.shift[i]) != 1) { exit(1); }
    }
    fclose(arq);
}

double Decoder(TSol &s, const TProblemData &data)
{
    const double TAU = 6.283185307179586;
    double total = 10.0 * data.n;
    for (int i = 0; i < data.n; i++)
    {
        double z = -5.12 + 10.24 * s.rk[i] - data.shift[i];
        total += z * z - 10.0 * std::cos(TAU * z);
    }
    return total;
}

void FreeMemoryProblem(TProblemData &data)
{
    data.shift.clear();
}

#endif
"""


class ProblemStudy:
    """Run and summarize the native-versus-C++ comparison on one problem family.

    Responsibilities:
    - Generate verified instances and build both executables.
    - Execute alternating trials and independently score returned keys.
    - Summarize paired per-instance gaps with exact sign tests.

    Attributes:
        output_path (Path): Raw trial CSV destination.
        cache_dir (Path): External cache for the C++ source and instances.
        budget_seconds (int): Search budget per trial.
        repetitions (int): Independent repetitions per cell.
        solvers (tuple[str, ...]): Solver display names.
        problem (str): Problem family, `tsp` or `rastrigin`.
        sizes (tuple[int, ...]): Dimensions, one instance group each.
        per_size (int): Instances generated per size.
        rust_grid (str): Native parameter grid flavor.
        benchmark (KnapsackBenchmark): Shared helper for the pinned C++ checkout and stats.
        repo_root (Path): Repository root.
    """

    def __init__(
        self,
        output_path: Path,
        cache_dir: Path,
        *,
        budget_seconds: int,
        repetitions: int,
        solvers: Sequence[str],
        problem: str,
        sizes: Sequence[int],
        per_size: int,
        rust_grid: str,
    ) -> None:
        """Store study options without building or executing anything.

        Args:
            output_path (Path): Raw trial CSV destination.
            cache_dir (Path): External cache directory.
            budget_seconds (int): Positive search budget per trial.
            repetitions (int): Positive repetition count.
            solvers (Sequence[str]): Display names to run.
            problem (str): Problem family, `tsp` or `rastrigin`.
            sizes (Sequence[int]): Positive dimensions.
            per_size (int): Positive number of instances per size.
            rust_grid (str): Native grid flavor, `toml` or `cpp`.

        Raises:
            ValueError: If a solver, problem or grid name is unknown.
        """
        known = {name for name, _ in SOLVER_CONFIGS}
        if any(solver not in known for solver in solvers):
            raise ValueError(f"Unknown solver; choose from {sorted(known)}.")
        if rust_grid not in ("toml", "cpp"):
            raise ValueError("rust_grid must be 'toml' or 'cpp'.")
        if problem not in ("tsp", "rastrigin"):
            raise ValueError("problem must be 'tsp' or 'rastrigin'.")
        self.problem = problem
        self.output_path = output_path
        self.cache_dir = cache_dir
        self.budget_seconds = budget_seconds
        self.repetitions = repetitions
        self.solvers = tuple(solvers)
        self.sizes = tuple(sizes)
        self.per_size = per_size
        self.rust_grid = rust_grid
        self.benchmark = KnapsackBenchmark(
            output_path, cache_dir, budget_seconds=budget_seconds, repetitions=repetitions
        )
        self.repo_root = self.benchmark.repo_root

    def _instances(self) -> list[tuple[str, np.ndarray, Path]]:
        """Write deterministic instances for the selected problem and return them.

        Returns:
            list[tuple[str, np.ndarray, Path]]: Name, instance data and file path.
        """
        directory = self.cache_dir / self.problem
        directory.mkdir(parents=True, exist_ok=True)
        generator = random.Random(SAMPLE_SEED)
        cases = []
        for size in self.sizes:
            for index in range(self.per_size):
                name = f"{self.problem}{size}-{index:02d}"
                path = directory / f"{name}.txt"
                if self.problem == "tsp":
                    data = np.array(
                        [
                            [generator.randrange(1000), generator.randrange(1000)]
                            for _ in range(size)
                        ]
                    )
                    lines = [str(size), *(f"{x} {y}" for x, y in data)]
                else:
                    data = np.array([round(generator.uniform(-2.0, 2.0), 3) for _ in range(size)])
                    lines = [str(size), *(repr(float(shift)) for shift in data)]
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                cases.append((name, data, path))
        return cases

    def score(self, keys: Sequence[float], data: np.ndarray) -> float:
        """Score keys independently of both implementations.

        Args:
            keys (Sequence[float]): Returned random keys.
            data (np.ndarray): City coordinates or Rastrigin shifts.

        Returns:
            float: Closed tour length (index-tied sorting, rounded distances) or the
                shifted Rastrigin value.

        Raises:
            ValueError: If the key count does not match the instance dimension.
        """
        if len(keys) != len(data):
            raise ValueError("Returned key dimension does not match the instance.")
        values = np.asarray(keys)
        if self.problem == "rastrigin":
            z = -5.12 + 10.24 * values - data
            return float(10.0 * len(z) + np.sum(z * z - 10.0 * np.cos(2.0 * math.pi * z)))
        order = np.lexsort((np.arange(len(keys)), values))
        total = 0.0
        previous = int(order[-1])
        for city in order:
            dx = float(data[previous][0] - data[city][0])
            dy = float(data[previous][1] - data[city][1])
            total += math.floor(math.sqrt(dx * dx + dy * dy) + 0.5)
            previous = int(city)
        return total

    def _build_cpp(self, temporary: Path) -> tuple[Path, str]:
        """Build the pinned C++ reference with the TSP problem file.

        Args:
            temporary (Path): Temporary build root.

        Returns:
            tuple[Path, str]: Program directory and a digest of the replaced sources.

        Raises:
            RuntimeError: If source patching or compilation fails.
        """
        repository = self.benchmark._clone_cpp_source()
        archive = subprocess.run(
            ["git", "-C", str(repository), "archive", "--format=tar", CPP_REVISION, "Program"],
            check=True,
            capture_output=True,
        ).stdout
        with tarfile.open(fileobj=BytesIO(archive), mode="r:") as source_archive:
            source_archive.extractall(temporary, filter="data")
        program_dir = temporary / "Program"
        header = TSP_PROBLEM_HEADER if self.problem == "tsp" else RASTRIGIN_PROBLEM_HEADER
        (program_dir / "src" / "Problem" / "Problem.h").write_text(header, encoding="utf-8")
        output_path = program_dir / "src" / "Output.h"
        output = output_path.read_text(encoding="utf-8")
        key_format = 'fprintf(solFile,"%.3lf ", s.rk[i]);'
        if output.count(key_format) != 1:
            raise RuntimeError("Could not locate the pinned C++ key serialization format.")
        output_path.write_text(
            output.replace(key_format, 'fprintf(solFile,"%.17g ", s.rk[i]);'), encoding="utf-8"
        )
        build = subprocess.run(
            ["make", "runRKO", f"CCFLAGS={CPP_FLAGS}"],
            cwd=program_dir,
            check=False,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            raise RuntimeError(f"C++ build failed: {build.stderr[-3000:]}")
        (temporary / "Results").mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(header.encode() + output_path.read_bytes()).hexdigest()
        return program_dir, digest

    def _build_rust(self) -> tuple[Path, str]:
        """Compile the native benchmark binary in release mode.

        Returns:
            tuple[Path, str]: Binary path and a SHA-256 digest of its bytes.

        Raises:
            RuntimeError: If compilation fails.
        """
        build = subprocess.run(
            ["cargo", "build", "--release", "--locked", "--bin", "rko_bench"],
            cwd=self.repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            raise RuntimeError(f"Native build failed: {build.stderr[-3000:]}")
        binary = self.repo_root / "target" / "release" / "rko_bench"
        return binary, hashlib.sha256(binary.read_bytes()).hexdigest()

    def _run_cpp(
        self, program_dir: Path, instance: Path, solver: str
    ) -> tuple[tuple[float, ...] | None, float | None, float, str]:
        """Run one C++ algorithm or portfolio.

        Args:
            program_dir (Path): Built C++ program directory.
            instance (Path): Instance file.
            solver (str): Display name.

        Returns:
            tuple: Keys, reported objective, elapsed seconds and an error message.
        """
        self.benchmark._write_cpp_config(program_dir, solver)
        results = program_dir.parent / "Results"
        for filename in ("Solutions_RKO.txt", "Results_RKO.csv"):
            if (results / filename).exists():
                (results / filename).unlink()
        started = time.perf_counter()
        process = subprocess.run(
            [str(program_dir / "runRKO"), str(instance), str(self.budget_seconds)],
            cwd=program_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(90, self.budget_seconds * 3),
        )
        elapsed = time.perf_counter() - started
        if process.returncode != 0 or not (results / "Solutions_RKO.txt").exists():
            return None, None, elapsed, f"C++ failed: {process.stderr[-500:]}"
        keys, objective = self.benchmark._parse_cpp_solution(
            (results / "Solutions_RKO.txt").read_text(encoding="utf-8")
        )
        return keys, objective, elapsed, ""

    def _run_rust(
        self, binary: Path, instance: Path, solver: str, seed: int
    ) -> tuple[tuple[float, ...] | None, float | None, float, str]:
        """Run one native algorithm or portfolio.

        Args:
            binary (Path): Native benchmark executable.
            instance (Path): Instance file.
            solver (str): Display name.
            seed (int): Engine seed.

        Returns:
            tuple: Keys, reported objective, elapsed seconds and an error message.
        """
        names = (
            "SA,ILS,VNS,BRKGA,BRKGA_CS,PSO,GA,LNS,GRASP,IPR"
            if solver == "RKO-default"
            else solver.replace("-", "_")
        )
        started = time.perf_counter()
        process = subprocess.run(
            [
                str(binary),
                str(instance),
                str(self.budget_seconds),
                "--problem",
                self.problem,
                "--algo",
                names,
                "--grid",
                self.rust_grid,
                "--seed",
                str(seed),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=max(90, self.budget_seconds * 3),
        )
        elapsed = time.perf_counter() - started
        if process.returncode != 0:
            return None, None, elapsed, f"native failed: {process.stderr[-500:]}"
        line = next(
            row for row in process.stdout.splitlines() if row.startswith("RKO_BENCH_RESULT ")
        )
        payload = json.loads(line.removeprefix("RKO_BENCH_RESULT "))
        return tuple(payload["keys"]), float(payload["objective"]), elapsed, ""

    def run(self) -> list[dict[str, str]]:
        """Execute every trial, write raw rows and return them with best-known gaps.

        Returns:
            list[dict[str, str]]: Raw rows read back from disk after gap annotation.

        Raises:
            OSError: If inputs, outputs or tools are unavailable.
            RuntimeError: If a build step fails.
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cases = self._instances()
        binary, binary_hash = self._build_rust()
        rows: list[dict[str, str | float | int]] = []
        with tempfile.TemporaryDirectory(prefix="native-tsp-") as temporary:
            program_dir, patch_hash = self._build_cpp(Path(temporary))
            for case_index, (name, coordinates, path) in enumerate(cases):
                for solver_index, solver in enumerate(self.solvers):
                    for replicate in range(self.repetitions):
                        seed = SAMPLE_SEED + solver_index * 1_000_000 + case_index * 100 + replicate
                        order = ("cpp64", "rust") if replicate % 2 == 0 else ("rust", "cpp64")
                        for implementation in order:
                            if implementation == "cpp64":
                                keys, reported, elapsed, error = self._run_cpp(
                                    program_dir, path, solver
                                )
                            else:
                                keys, reported, elapsed, error = self._run_rust(
                                    binary, path, solver, seed
                                )
                            length = None
                            if keys is not None and not error:
                                try:
                                    length = self.score(keys, coordinates)
                                    tolerance = 1e-6 if implementation == "cpp64" else 1e-9
                                    if reported is None or not math.isclose(
                                        length, reported, rel_tol=1e-9, abs_tol=tolerance
                                    ):
                                        error = f"objective mismatch: {reported} vs {length}"
                                        length = None
                                except ValueError as failure:
                                    error = str(failure)
                            rows.append(
                                {
                                    "instance": name,
                                    "dimension": len(coordinates),
                                    "solver": solver,
                                    "implementation": implementation,
                                    "replicate": replicate,
                                    "seed": seed,
                                    "budget_seconds": self.budget_seconds,
                                    "objective": "" if length is None else length,
                                    "elapsed_seconds": elapsed,
                                    "status": "ok" if length is not None else "error",
                                    "error": error,
                                    "native_binary_sha256": binary_hash,
                                    "cpp_patch_sha256": patch_hash,
                                    "cpp_revision": CPP_REVISION,
                                    "rust_grid": self.rust_grid,
                                    "problem": self.problem,
                                    "platform": sys.platform,
                                }
                            )
                            print(
                                f"{implementation:6s} {solver:12s} {name} r={replicate:02d} "
                                f"objective={rows[-1]['objective']}",
                                flush=True,
                            )
        best: dict[str, float] = {}
        for row in rows:
            if row["status"] == "ok":
                name = str(row["instance"])
                best[name] = min(best.get(name, math.inf), float(row["objective"]))
        for row in rows:
            known = best.get(str(row["instance"]), math.nan)
            if row["status"] != "ok":
                row["quality"] = ""
            elif self.problem == "rastrigin":
                row["quality"] = float(row["objective"])
            else:
                row["quality"] = 100.0 * (float(row["objective"]) - known) / known
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return [{key: str(value) for key, value in row.items()} for row in rows]

    @staticmethod
    def summarize(rows: Sequence[dict[str, str]]) -> str:
        """Pair native and C++ results per instance and render exact sign tests.

        Args:
            rows (Sequence[dict[str, str]]): Annotated raw rows.

        Returns:
            str: Fixed-width paired summary.

        Raises:
            ValueError: If a gap value is nonfinite.
        """
        solvers = sorted({row["solver"] for row in rows})
        medians: dict[str, tuple[list[float], list[float]]] = {}
        failures: dict[str, tuple[int, int]] = {}
        for solver in solvers:
            per_instance: dict[str, dict[str, list[float]]] = {}
            failed = {"rust": 0, "cpp64": 0}
            for row in rows:
                if row["solver"] != solver:
                    continue
                if row["status"] != "ok":
                    failed[row["implementation"]] += 1
                    continue
                per_instance.setdefault(row["instance"], {}).setdefault(
                    row["implementation"], []
                ).append(float(row["quality"]))
            native, reference = [], []
            for sides in per_instance.values():
                if "rust" in sides and "cpp64" in sides:
                    native.append(statistics.median(sides["rust"]))
                    reference.append(statistics.median(sides["cpp64"]))
            medians[solver] = (native, reference)
            failures[solver] = (failed["rust"], failed["cpp64"])
        raw = {
            solver: KnapsackBenchmark.exact_sign_test(
                [a - b for a, b in zip(native, reference, strict=True)]
            )[0]
            for solver, (native, reference) in medians.items()
            if native
        }
        adjusted = KnapsackBenchmark.holm_adjust(raw) if raw else {}
        lines = [
            "\n[quality] rust vs cpp64 (lower is better; B/W/T = rust better/worse/tied)",
            f"{'solver':12} {'rust':>9} {'cpp64':>9} {'diff':>9} {'95% CI':>21} "
            f"{'B/W/T':>9} {'p_holm':>8} {'fail r/c':>9}",
        ]
        for solver, (native, reference) in medians.items():
            if not native:
                continue
            differences = [a - b for a, b in zip(native, reference, strict=True)]
            _, non_tied, positive, negative = KnapsackBenchmark.exact_sign_test(differences)
            low, high = KnapsackBenchmark.bootstrap_median_interval(
                differences, seed=SAMPLE_SEED + sum(map(ord, solver))
            )
            lines.append(
                f"{solver:12} {statistics.median(native):9.3f} {statistics.median(reference):9.3f} "
                f"{statistics.median(differences):9.3f} "
                f"{f'[{low:.3f},{high:.3f}]':>21} "
                f"{negative}/{positive}/{len(differences) - non_tied:<5} "
                f"{adjusted[solver]:8.4f} {failures[solver][0]}/{failures[solver][1]:>6}"
            )
        return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the problem-family study from the command line.

    Args:
        argv (Sequence[str] | None): Optional argument vector.

    Returns:
        int: Zero on completion.

    Raises:
        OSError: If files or tools are unavailable.
        RuntimeError: If a build fails.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "rko-cpp-python-knapsack"
    )
    parser.add_argument("--budget-seconds", type=int, default=2)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--solvers", default="BRKGA,SA,RKO-default")
    parser.add_argument("--problem", choices=("tsp", "rastrigin"), default="tsp")
    parser.add_argument(
        "--sizes", default=None, help="Default 100,300 (tsp) or 30,100 (rastrigin)."
    )
    parser.add_argument("--per-size", type=int, default=5)
    parser.add_argument("--rust-grid", choices=("toml", "cpp"), default="cpp")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)
    study = ProblemStudy(
        args.output,
        args.cache_dir,
        budget_seconds=args.budget_seconds,
        repetitions=args.repetitions,
        solvers=args.solvers.split(","),
        problem=args.problem,
        sizes=[
            int(size)
            for size in (args.sizes or ("100,300" if args.problem == "tsp" else "30,100")).split(
                ","
            )
        ],
        per_size=args.per_size,
        rust_grid=args.rust_grid,
    )
    if args.summary_only:
        with args.output.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
    else:
        rows = study.run()
    sys.stdout.write(study.summarize(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
