"""Confirm installed timed portfolios with a frozen independent thirty-seed protocol.

Objective:
- Separate validated collection from evidence sufficient to qualify native execution.

Technical approach:
- Reuse unprofiled installed workers with new seeds and fixed settings.
- Require six complete source-identical backend/adaptation shards.
- Use distribution-free paired-median order-statistic intervals with Bonferroni coverage.

Flow (pseudocode):
1. Write source hashes and immutable acceptance criteria before collecting trials.
2. Collect all thirty paired seeds per callback/dimension/backend/adaptation group.
3. Validate coverage and report quality, time-per-evaluation and sampled-PSS gates.

Important criteria:
- Quality admits no positive paired-median normalized regret difference.
- Failure to establish a gate is not proof of harm and never changes the protocol.
- Exact interval coverage assumes independent seed-pair observations; ties are conservative.
- Validated experiment completion is not release authorization or automatic qualification.

Inputs/Outputs:
- Input: installed wheel interpreter for collection, or six downloaded shard artifacts.
- Output: raw independent evidence and explicit qualification/uncertainty reports.
"""

import argparse
import hashlib
import json
import math
import statistics
from benchmarks.native_portfolio import NativePortfolioStudy
from pathlib import Path


class NativeConfirmation:
    """Own the immutable timed confirmation definition and evidence validation.

    Responsibilities:
    - Keep pilot seeds and repeated CI observations out of independent confirmation.
    - Reject incomplete, mixed, profiled or retrospectively altered experiment evidence.
    - Distinguish gate failure from technical collection failure.

    Attributes:
        SPEC (dict): Immutable statistical design, workload settings and acceptance rules.
        ROOT (Path): Repository containing maintained benchmark and production sources.
    """

    ROOT = Path(__file__).resolve().parents[1]
    SPEC = {
        "version": "rko-timed-confirmation-v1",
        "repeats": 30,
        "seed_start": 50000,
        "seconds": 2.0,
        "dimensions": [20, 500],
        "workloads": ["object", "permutation"],
        "backends": ["serial", "thread", "process"],
        "adaptations": ["fixed", "adaptive"],
        "python": "3.14.9",
        "numpy": "2.4.3",
        "family_error_probability": 0.05,
        "intervals": 72,
        "quality_median_difference_upper": 0.0,
        "large_median_throughput_gain_minimum": 0.10,
        "protected_time_per_evaluation_upper": 1.05,
        "sampled_tree_pss_ratio_upper": 1.10,
        "interval_method": "exact_binomial_order_statistics_bonferroni_paired_median",
    }

    @classmethod
    def definition(cls) -> dict:
        """Fingerprint product, native build inputs and measurement implementations.

        Returns:
            dict: Protocol and exact source input digests recorded before collection.

        Raises:
            OSError: If maintained source or native build configuration cannot be read.
        """
        paths = [path for path in (cls.ROOT / "src/rko").rglob("*.py") if "tests" not in path.parts]
        paths.extend((cls.ROOT / "src/rko/parameters").glob("*.toml"))
        paths.extend((cls.ROOT / "native/src").rglob("*.rs"))
        paths.extend(
            cls.ROOT / name
            for name in (
                "native/Cargo.toml",
                "native/Cargo.lock",
                "setup.py",
                "pyproject.toml",
                "uv.lock",
                "rust-toolchain.toml",
                "benchmarks/native_confirmation.py",
                "benchmarks/native_portfolio.py",
                "tools/smoke_portfolio.py",
                ".github/workflows/native-qualification.yml",
            )
        )
        return {
            "spec": cls.SPEC,
            "inputs_sha256": {
                path.relative_to(cls.ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(paths)
            },
        }

    @staticmethod
    def digest(definition: dict) -> str:
        """Hash a canonical confirmation definition independently of JSON formatting.

        Args:
            definition (dict): Explicit protocol and source hashes.

        Returns:
            str: Canonical SHA256 identity.
        """
        return hashlib.sha256(json.dumps(definition, sort_keys=True).encode()).hexdigest()

    @classmethod
    def collect(cls, args: argparse.Namespace) -> None:
        """Freeze criteria before running one complete installed-wheel shard.

        Args:
            args (argparse.Namespace): Installed interpreter, output and shard identity.

        Raises:
            Exception: Any invalid setting, source drift or worker failure propagates.
        """
        args.repeats, args.seed_start, args.seconds = (
            cls.SPEC["repeats"],
            cls.SPEC["seed_start"],
            cls.SPEC["seconds"],
        )
        args.scope = "independent_preregistered_timed_confirmation"
        study = NativePortfolioStudy(args)
        definition = cls.definition()
        (args.output / "confirmation.json").write_text(
            json.dumps(definition, indent=2), encoding="utf-8"
        )
        study.run()
        if cls.definition() != definition:
            raise ValueError("Confirmation source inputs changed during collection")
        (args.output / "confirmation-complete.json").write_text(
            json.dumps({"definition_sha256": cls.digest(definition), "pairs": 120}),
            encoding="utf-8",
        )

    @classmethod
    def interval(cls, values: list[float]) -> dict:
        """Bound a paired population median with exact binomial order statistics.

        Args:
            values (list[float]): Thirty finite independent seed-pair observations.

        Returns:
            dict: Sample median, simultaneous bounds, rank and conservative coverage.

        Raises:
            ValueError: If sample coverage or finiteness is invalid.
        """
        if len(values) != cls.SPEC["repeats"] or not all(math.isfinite(value) for value in values):
            raise ValueError("Expected thirty finite paired observations")
        ordered, n, rank, tail = sorted(values), len(values), 0, 0.0
        allowance = cls.SPEC["family_error_probability"] / (2 * cls.SPEC["intervals"])
        for candidate in range(1, n // 2 + 1):
            probability = sum(math.comb(n, j) for j in range(candidate)) / 2**n
            if probability > allowance:
                break
            rank, tail = candidate, probability
        if rank == 0:
            raise ValueError("Insufficient observations for finite simultaneous median bounds")
        return {
            "median": statistics.median(ordered),
            "simultaneous95": [ordered[rank - 1], ordered[n - rank]],
            "lower_rank_one_based": rank,
            "interval_coverage_lower_bound": 1 - 2 * tail,
        }

    @staticmethod
    def positive(value: object) -> bool:
        """Recognize finite positive numeric measurements, excluding booleans.

        Args:
            value (object): Raw JSON measurement.

        Returns:
            bool: Whether the observation is a positive finite scalar.
        """
        return type(value) in (int, float) and math.isfinite(value) and value > 0

    @classmethod
    def analyze(cls, root: Path) -> dict:
        """Validate all raw shards before computing conservative qualification gates.

        Args:
            root (Path): Downloaded artifact parent containing six confirmation folders.

        Returns:
            dict: Full group results, failures and explicit qualification status.

        Raises:
            ValueError: If coverage, completion, source identity or measurements are invalid.
            OSError: If any required evidence file cannot be read.
        """
        definitions = sorted(root.rglob("confirmation.json"))
        if len(definitions) != 6:
            raise ValueError("Expected exactly six completed confirmation shards")
        groups: dict[tuple, list[dict]] = {}
        shards, expected_definition, runtime = set(), None, None
        for path in definitions:
            definition = json.loads(path.read_text())
            if definition != cls.definition():
                raise ValueError("Changed frozen confirmation definition or source inputs")
            if expected_definition is not None and definition != expected_definition:
                raise ValueError("Mixed source definitions across confirmation shards")
            expected_definition = definition
            complete = json.loads(path.with_name("confirmation-complete.json").read_text())
            if complete != {"definition_sha256": cls.digest(definition), "pairs": 120}:
                raise ValueError("Missing or inconsistent source-verified completion")
            protocol = json.loads(path.with_name("protocol.json").read_text())
            shard = (protocol["backend"], protocol["adaptation"])
            if (
                shard in shards
                or shard[0] not in cls.SPEC["backends"]
                or shard[1] not in cls.SPEC["adaptations"]
            ):
                raise ValueError("Duplicate or invalid shard identity")
            shards.add(shard)
            for key in ("repeats", "seed_start", "seconds", "dimensions", "workloads"):
                if protocol[key] != cls.SPEC[key]:
                    raise ValueError(f"Changed collection protocol: {key}")
            if protocol["scope"] != "independent_preregistered_timed_confirmation" or any(
                protocol["threads"].get(key) != "1"
                for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
            ):
                raise ValueError("Wrong confirmation scope or native thread configuration")
            rows = [
                json.loads(line)
                for line in path.with_name("pairs.jsonl").read_text().splitlines()
                if line.strip()
            ]
            if len(rows) != 120:
                raise ValueError("Incomplete or extra confirmation pairs")
            installed_identity = None
            for row in rows:
                if row.get("kind") != "pair":
                    raise ValueError("Unexpected non-pair observation")
                NativePortfolioStudy.validate_pair(
                    {label: row[label] for label in ("python", "native")}
                )
                baseline, native = row["python"], row["native"]
                if (native["backend"], native["adaptation"]) != shard:
                    raise ValueError("Row belongs to a different shard")
                seed = native["seed"]
                if (
                    type(seed) is not int
                    or not cls.SPEC["seed_start"]
                    <= seed
                    < cls.SPEC["seed_start"] + cls.SPEC["repeats"]
                ):
                    raise ValueError("Pilot or non-confirmation seed")
                order = (
                    ["python", "native"]
                    if (seed - cls.SPEC["seed_start"]) % 2 == 0
                    else ["native", "python"]
                )
                if row["order"] != order or native["seconds"] != cls.SPEC["seconds"]:
                    raise ValueError("Changed paired order or search budget")
                if (
                    native["dimension"] not in cls.SPEC["dimensions"]
                    or native["workload"] not in cls.SPEC["workloads"]
                ):
                    raise ValueError("Unexpected callback or dimension")
                identity = native["installed_sources_sha256"]
                if installed_identity is not None and identity != installed_identity:
                    raise ValueError("Installed source/binary changed within a shard")
                installed_identity = identity
                versions = {key: native["versions"][key] for key in ("python", "numpy", "rko")}
                if (
                    versions["python"] != cls.SPEC["python"]
                    or versions["numpy"] != cls.SPEC["numpy"]
                ):
                    raise ValueError("Changed frozen interpreter or NumPy version")
                if runtime is not None and versions != runtime:
                    raise ValueError("Mixed runtime versions across shards")
                runtime = versions
                for observation in (baseline, native):
                    for key in (
                        "n_evaluations",
                        "pss_complete_samples",
                        "sampled_peak_tree_pss_bytes",
                    ):
                        if type(observation[key]) is not int:
                            raise ValueError(f"Expected integer measurement: {key}")
                    expected_workers = {"serial": 1, "thread": 3, "process": 2}[shard[0]]
                    if observation["n_workers"] != expected_workers:
                        raise ValueError("Changed frozen worker count")
                    for key in (
                        "fresh_process_seconds",
                        "sampled_peak_tree_pss_bytes",
                        "n_evaluations",
                        "pss_complete_samples",
                    ):
                        if not cls.positive(observation[key]):
                            raise ValueError(f"Missing or invalid measurement: {key}")
                    n, cost, regret = (
                        observation["dimension"],
                        observation["cost"],
                        observation["normalized_regret"],
                    )
                    if (
                        type(regret) not in (int, float)
                        or not math.isfinite(regret)
                        or not 0 <= regret <= 1
                    ):
                        raise ValueError("Invalid normalized quality observation")
                    if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
                        raise ValueError("Invalid objective cost")
                    expected_regret = cost / n
                    if observation["workload"] == "permutation":
                        span = n * (n - 1) * (n + 1) / 6
                        expected_regret = (cost - span) / span
                    if regret != expected_regret:
                        raise ValueError(
                            "Quality normalization differs from frozen objective range"
                        )
                key = (*shard, native["dimension"], native["workload"])
                groups.setdefault(key, []).append(row)
        if len(groups) != 24:
            raise ValueError("Incomplete callback/dimension confirmation coverage")
        results = []
        for key, rows in sorted(groups.items()):
            if len(rows) != cls.SPEC["repeats"] or {row["native"]["seed"] for row in rows} != set(
                range(cls.SPEC["seed_start"], cls.SPEC["seed_start"] + cls.SPEC["repeats"])
            ):
                raise ValueError("Missing or duplicate group seeds")
            quality, latency, memory = [], [], []
            for row in rows:
                baseline, native = row["python"], row["native"]
                quality.append(native["normalized_regret"] - baseline["normalized_regret"])
                latency.append(
                    (native["fresh_process_seconds"] / native["n_evaluations"])
                    / (baseline["fresh_process_seconds"] / baseline["n_evaluations"])
                )
                memory.append(
                    native["sampled_peak_tree_pss_bytes"] / baseline["sampled_peak_tree_pss_bytes"]
                )
            q, t, m = (cls.interval(values) for values in (quality, latency, memory))
            speed = (
                (
                    t["median"] <= 1 / (1 + cls.SPEC["large_median_throughput_gain_minimum"])
                    and t["simultaneous95"][1] < 1
                )
                if key[2] == 500
                else t["simultaneous95"][1] <= cls.SPEC["protected_time_per_evaluation_upper"]
            )
            gates = {
                "quality_no_loss_established": q["simultaneous95"][1]
                <= cls.SPEC["quality_median_difference_upper"],
                "time_per_evaluation": speed,
                "sampled_tree_pss": m["simultaneous95"][1]
                <= cls.SPEC["sampled_tree_pss_ratio_upper"],
            }
            results.append(
                {
                    "backend": key[0],
                    "adaptation": key[1],
                    "dimension": key[2],
                    "workload": key[3],
                    "pairs": len(rows),
                    "quality_delta": q,
                    "time_per_evaluation_ratio": t,
                    "sampled_tree_pss_ratio": m,
                    "gates": gates,
                    "all_gates_pass": all(gates.values()),
                }
            )
        accepted = all(group["all_gates_pass"] for group in results)
        return {
            "collection_validated": True,
            "pairs": 720,
            "definition": expected_definition,
            "qualification_status": "established" if accepted else "not_established",
            "all_scoped_gates_pass": accepted,
            "groups": results,
            "release_authorized": False,
        }


def main() -> None:
    """Collect or report a frozen experiment without disguising inconclusive gates.

    Raises:
        Exception: Technical collection or evidence-validation failures propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    collect = actions.add_parser("collect")
    collect.add_argument("--python", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--backend", choices=NativeConfirmation.SPEC["backends"], required=True)
    collect.add_argument(
        "--adaptation", choices=NativeConfirmation.SPEC["adaptations"], required=True
    )
    analyze = actions.add_parser("analyze")
    analyze.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.action == "collect":
        NativeConfirmation.collect(args)
    else:
        report = NativeConfirmation.analyze(args.root)
        (args.root / "summary.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
