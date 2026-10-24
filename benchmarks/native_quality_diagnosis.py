"""Diagnose inconclusive timed quality with counterbalanced Python-repeat controls.

Objective:
- Distinguish implementation-independent timed variability from native-only differences.

Technical approach:
- Collect thirty fresh three-arm trials for each of the six previously inconclusive groups.
- Compare two identical Python implementations and one admitted native implementation.
- Preserve existing per-search histories without adding timed profiling or callbacks.

Flow (pseudocode):
1. Freeze source/settings and validate adaptive exact prefixes under a logical clock.
2. Rotate all six arm orders equally over new seeds and independent interpreters.
3. Report Python-repeat and both native contrasts with unchanged conservative intervals.

Important criteria:
- This is diagnosis, never an extension or replacement of the completed confirmation.
- Shared-baseline contrasts are dependent; no independent difference-in-differences claim.
- Parallel controls cannot alone distinguish OS scheduling from pool cooperation.
- Logical clocks apply only to separate functional checks, not timed observations.

Inputs/Outputs:
- Input: installed mixed-wheel interpreter or six downloaded diagnostic case artifacts.
- Output: complete raw triads, bounded search histories and descriptive diagnostic reports.
"""

import argparse
import hashlib
import itertools
import json
import os
import signal
import subprocess
from benchmarks.native_confirmation import NativeConfirmation
from benchmarks.native_portfolio import NativePortfolioStudy
from pathlib import Path


class NativeQualityDiagnosis:
    """Own source-frozen negative controls without changing optimizer behavior.

    Responsibilities:
    - Preserve all original findings and collect genuinely new diagnostic seeds.
    - Check source, coverage, arm balance and exact functional replay independently.

    Attributes:
        ROOT (Path): Checkout containing maintained diagnostic sources.
        SPEC (dict): Fixed cases, seeds and balanced three-arm design.
    """

    ROOT = Path(__file__).resolve().parents[1]
    SPEC = {
        "version": "native-quality-negative-controls-v1",
        "repeats": 30,
        "seed_start": 61000,
        "seconds": 2.0,
        "workload": "object",
        "python": "3.14.9",
        "numpy": "2.4.3",
        "arms": ["python_a", "python_b", "native"],
        "cases": [
            ["process", "adaptive", 20],
            ["process", "fixed", 20],
            ["serial", "adaptive", 20],
            ["serial", "adaptive", 500],
            ["thread", "adaptive", 20],
            ["thread", "fixed", 20],
        ],
        "intervals": "unchanged confirmation ranks6/25; diagnostic only",
        "scope": "diagnosis_not_acceptance_or_additional_confirmation",
    }

    @classmethod
    def definition(cls) -> dict:
        """Freeze diagnostic sources together with existing product/build inputs.

        Returns:
            dict: Explicit design and source content digests.

        Raises:
            OSError: If any maintained source cannot be read.
        """
        inputs = NativeConfirmation.definition()["inputs_sha256"]
        for name in ("benchmarks/native_quality_diagnosis.py", "tools/smoke_native.py"):
            inputs[name] = hashlib.sha256((cls.ROOT / name).read_bytes()).hexdigest()
        return {"spec": cls.SPEC, "inputs_sha256": inputs}

    @staticmethod
    def launch(command: list[str], env: dict[str, str], prefix: Path) -> dict:
        """Run one owned isolated process and retain both successful and failed output.

        Args:
            command (list[str]): Explicit installed-interpreter invocation.
            env (dict[str, str]): Process-local activation state.
            prefix (Path): Unique raw stdout/stderr file stem.

        Returns:
            dict: One successful raw JSON observation.

        Raises:
            Exception: Original timeout, child, filesystem or parsing failures propagate.
        """
        with (
            prefix.with_suffix(".json").open("w", encoding="utf-8") as stdout,
            prefix.with_suffix(".stderr").open("w", encoding="utf-8") as stderr,
        ):
            with subprocess.Popen(
                command, env=env, stdout=stdout, stderr=stderr, start_new_session=True
            ) as process:
                try:
                    status = process.wait(timeout=120)
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
        if status:
            raise subprocess.CalledProcessError(status, command)
        return json.loads(prefix.with_suffix(".json").read_text())

    @classmethod
    def collect(cls, args: argparse.Namespace) -> None:
        """Collect one complete counterbalanced diagnostic case outside the checkout.

        Args:
            args (argparse.Namespace): Installed interpreter, case index and new output path.

        Raises:
            Exception: Invalid evidence, source drift or any subprocess failure propagates.
        """
        if os.name != "posix":
            raise ValueError("Owned diagnostic process groups require a POSIX host")
        args.output.mkdir(parents=True, exist_ok=False)
        definition = cls.definition()
        case = cls.SPEC["cases"][args.case]
        (args.output / "definition.json").write_text(
            json.dumps(definition, indent=2), encoding="utf-8"
        )
        (args.output / "case.json").write_text(
            json.dumps({"index": args.case, "case": case}), encoding="utf-8"
        )
        env = dict(os.environ, RKO_USE_NATIVE="0")
        proof = cls.launch(
            [
                str(args.python),
                "-I",
                str(cls.ROOT / "tools/smoke_native.py"),
                "--binary",
                "present",
            ],
            env,
            args.output / "functional",
        )
        if not (
            proof["exact_replay"] and proof["adaptive_clock_replay"] and proof["native_calls"] > 0
        ):
            raise ValueError("Actual adaptive logical-clock replay was not established")
        orders = list(itertools.permutations(cls.SPEC["arms"]))
        backend, adaptation, dimension = case
        with (args.output / "triads.jsonl").open("w", encoding="utf-8") as output:
            for index in range(cls.SPEC["repeats"]):
                seed = cls.SPEC["seed_start"] + index
                order, rows = orders[index % len(orders)], {}
                for arm in order:
                    command = [
                        str(args.python),
                        "-I",
                        str(cls.ROOT / "tools/smoke_portfolio.py"),
                        "--backend",
                        backend,
                        "--adaptation",
                        adaptation,
                        "--dimension",
                        str(dimension),
                        "--seconds",
                        str(cls.SPEC["seconds"]),
                        "--workload",
                        "object",
                        "--seed",
                        str(seed),
                    ]
                    rows[arm] = cls.launch(
                        command,
                        dict(env, RKO_USE_NATIVE="1" if arm == "native" else "0"),
                        args.output / f"{seed}-{arm}",
                    )
                cls.validate(rows, case, seed)
                output.write(json.dumps({"seed": seed, "order": order, **rows}) + "\n")
                output.flush()
        if cls.definition() != definition:
            raise ValueError("Diagnostic source changed during collection")
        (args.output / "complete.json").write_text(
            json.dumps({"definition_sha256": NativeConfirmation.digest(definition), "triads": 30}),
            encoding="utf-8",
        )

    @classmethod
    def validate(cls, rows: dict, case: list, seed: int) -> None:
        """Reject mixed arms or instrumentation before comparing diagnostic quality.

        Args:
            rows (dict): Three raw independent arm observations.
            case (list): Frozen backend, adaptation and dimension.
            seed (int): Expected independent seed assigned to all arms.

        Raises:
            ValueError: If admission, settings, metadata or observation identity changed.
        """
        for label in ("python_a", "python_b"):
            NativePortfolioStudy.validate_pair({"python": rows[label], "native": rows["native"]})
        identity = rows["python_a"]["installed_sources_sha256"]
        for arm in cls.SPEC["arms"]:
            row = rows[arm]
            if [row["backend"], row["adaptation"], row["dimension"]] != case or row["seed"] != seed:
                raise ValueError("Mixed diagnostic case or seed")
            if (
                row["workload"] != "object"
                or row["seconds"] != cls.SPEC["seconds"]
                or row["functional"]
            ):
                raise ValueError("Changed or profiled diagnostic callbacks")
            if row["installed_sources_sha256"] != identity:
                raise ValueError("Mixed installed diagnostic sources")
            if any(row["versions"][key] != cls.SPEC[key] for key in ("python", "numpy")):
                raise ValueError("Changed diagnostic interpreter or NumPy")
            if row["n_workers"] != {"serial": 1, "thread": 3, "process": 2}[case[0]]:
                raise ValueError("Changed diagnostic worker count")
            if (
                not NativeConfirmation.positive(row["n_evaluations"])
                or not 0 <= row["normalized_regret"] <= 1
            ):
                raise ValueError("Invalid diagnostic result")
            if row["normalized_regret"] != row["cost"] / row["dimension"]:
                raise ValueError("Changed diagnostic quality normalization")
            if [search["algorithm"] for search in row["searches"]] != ["SA", "GA", "BRKGA"]:
                raise ValueError("Incomplete diagnostic search metadata")
            if sum(search["n_evaluations"] for search in row["searches"]) != row["n_evaluations"]:
                raise ValueError("Changed per-search evaluation accounting")
            if any(
                not search["history"] or len(search["history"]) > 8 for search in row["searches"]
            ):
                raise ValueError("Missing bounded diagnostic histories")
            for reference, search in zip(
                rows["python_a"]["searches"], row["searches"], strict=True
            ):
                if any(
                    reference[key] != search[key]
                    for key in (
                        "algorithm",
                        "random_state",
                        "parameters",
                        "parameter_grid",
                        "control",
                    )
                ):
                    raise ValueError("Initial search configuration changed between arms")

    @staticmethod
    def contrast(rows: list[dict], baseline: str, candidate: str) -> dict:
        """Describe a paired quality contrast without declaring new acceptance.

        Args:
            rows (list[dict]): Thirty complete balanced triads.
            baseline (str): Reference arm name.
            candidate (str): Compared arm name.

        Returns:
            dict: Conservative legacy interval, win/tie/loss counts and work-change counts.
        """
        delta = [
            row[candidate]["normalized_regret"] - row[baseline]["normalized_regret"] for row in rows
        ]
        return {
            "quality_delta": NativeConfirmation.interval(delta),
            "wins": sum(value < 0 for value in delta),
            "ties": sum(value == 0 for value in delta),
            "losses": sum(value > 0 for value in delta),
            "losses_with_at_least_as_many_evaluations": sum(
                value > 0 and row[candidate]["n_evaluations"] >= row[baseline]["n_evaluations"]
                for value, row in zip(delta, rows, strict=True)
            ),
            "per_search": [
                {
                    "algorithm": algorithm,
                    "quality_changed_pairs": sum(
                        row[candidate]["searches"][index]["history"][-1]["cost"]
                        != row[baseline]["searches"][index]["history"][-1]["cost"]
                        for row in rows
                    ),
                    "evaluation_count_changed_pairs": sum(
                        row[candidate]["searches"][index]["n_evaluations"]
                        != row[baseline]["searches"][index]["n_evaluations"]
                        for row in rows
                    ),
                }
                for index, algorithm in enumerate(("SA", "GA", "BRKGA"))
            ],
        }

    @classmethod
    def analyze(cls, root: Path) -> dict:
        """Validate six complete cases and retain every diagnostic contrast.

        Args:
            root (Path): Parent of six downloaded raw case directories.

        Returns:
            dict: Descriptive controls and replay proof, never a revised qualification.

        Raises:
            ValueError: If source, functional proof, coverage or balanced order is invalid.
            OSError: If required raw evidence cannot be read.
        """
        files = sorted(root.rglob("definition.json"))
        if len(files) != 6:
            raise ValueError("Expected six diagnostic cases")
        seen, groups = set(), []
        definition = cls.definition()
        orders = list(itertools.permutations(cls.SPEC["arms"]))
        for path in files:
            if json.loads(path.read_text()) != definition:
                raise ValueError("Mixed or changed frozen diagnostic sources")
            folder = path.parent
            complete = json.loads((folder / "complete.json").read_text())
            if complete != {
                "definition_sha256": NativeConfirmation.digest(definition),
                "triads": 30,
            }:
                raise ValueError("Incomplete diagnostic source verification")
            case = json.loads((folder / "case.json").read_text())
            index = case["index"]
            if type(index) is not int or not 0 <= index < len(cls.SPEC["cases"]):
                raise ValueError("Invalid diagnostic case index")
            if index in seen or case["case"] != cls.SPEC["cases"][index]:
                raise ValueError("Duplicate or changed case definition")
            seen.add(index)
            proof = json.loads((folder / "functional.json").read_text())
            if not (
                proof["exact_replay"]
                and proof["adaptive_clock_replay"]
                and proof["native_calls"] > 0
            ):
                raise ValueError("Missing adaptive controlled-clock functional proof")
            rows = [
                json.loads(line)
                for line in (folder / "triads.jsonl").read_text().splitlines()
                if line.strip()
            ]
            if len(rows) != 30 or {row["seed"] for row in rows} != set(range(61000, 61030)):
                raise ValueError("Incomplete, duplicate or reused diagnostic seeds")
            installed = set()
            for row in rows:
                seed = row["seed"]
                if row["order"] != list(orders[(seed - 61000) % 6]):
                    raise ValueError("Unbalanced diagnostic arm order")
                cls.validate(row, case["case"], seed)
                installed.add(row["native"]["installed_sources_sha256"])
            if len(installed) != 1:
                raise ValueError("Installed artifact changed within diagnostic case")
            groups.append(
                {
                    "case": case["case"],
                    "triads": 30,
                    "adaptive_logical_clock_exact_replay": True,
                    "python_repeat": cls.contrast(rows, "python_a", "python_b"),
                    "native_vs_a": cls.contrast(rows, "python_a", "native"),
                    "native_vs_b": cls.contrast(rows, "python_b", "native"),
                }
            )
        return {
            "scope": cls.SPEC["scope"],
            "collection_validated": True,
            "triads": 180,
            "fresh_timed_workers": 540,
            "definition": definition,
            "groups": groups,
            "original_qualification_status": "not_established",
            "changes_original_qualification": False,
            "exclusive_pool_or_scheduler_attribution": False,
            "release_authorized": False,
        }


def main() -> None:
    """Collect or describe negative controls without changing confirmation outcomes.

    Raises:
        Exception: Collection or raw-evidence validation failures propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    collect = actions.add_parser("collect")
    collect.add_argument("--python", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--case", type=int, choices=range(6), required=True)
    analyze = actions.add_parser("analyze")
    analyze.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.action == "collect":
        NativeQualityDiagnosis.collect(args)
    else:
        result = NativeQualityDiagnosis.analyze(args.root)
        (args.root / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
