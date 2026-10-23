"""File-backed scheduling adapter for standalone and portfolio optimization.

Objective:
- Demonstrate explicit instance loading before a domain-neutral random-key search.

Technical approach:
- Read immutable processing times and due dates once from a JSON instance.
- Rank keys stably and use processing times to construct a single-machine schedule.
- Minimize total tardiness using the same instance's due dates.
- Keep the reader outside callback loops and optional reporting outside timed search.

Flow (pseudocode):
1. Read and validate the instance schema in the parent process.
2. Bind the instance to an importable adapter with decode/cost methods.
3. Optimize keys with selected algorithms and the requested execution backend.
4. Decode the incumbent explicitly, print the solution and optionally export a report.

Important criteria:
- This is a synthetic usability example, not an optimization-quality benchmark.
- Bound methods carry data under spawn without reopening the instance file.
- Decoding costs O(n log n) for sorting; objective evaluation costs O(n).
- Final decoding is postprocessing, not another counted objective evaluation.

Inputs/Outputs:
- Input: JSON name, processing_times and due_dates; solver options from the CLI.
- Output: objective and ordered (job index, completion time) pairs, optional HTML report.
"""

import argparse
import json
import numpy as np
from ..reporting import OptimizationReport
from ..solver import RKO
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

type Schedule = tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class SchedulingInstance:
    """Hold one validated scheduling input without live files or mutable arrays.

    Responsibilities:
    - Retain the values shared by decoding and objective evaluation.

    Attributes:
        name (str): Human-readable instance label.
        processing_times (tuple[int, ...]): Positive processing duration of each job.
        due_dates (tuple[int, ...]): Nonnegative due date of each job in the same units.
    """

    name: str
    processing_times: tuple[int, ...]
    due_dates: tuple[int, ...]


def read_data(path: Path) -> SchedulingInstance:
    """Load one scheduling instance before constructing or running any optimizer.

    Args:
        path (Path): UTF-8 JSON file with name, processing_times and due_dates fields.

    Returns:
        SchedulingInstance: Owned immutable input with one due date per job.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If JSON, field names, dimensions or integer domains are invalid.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = {"name", "processing_times", "due_dates"}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("Instance fields must be exactly name, processing_times and due_dates.")
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("Instance name must be a nonempty string.")
    times, dates = data["processing_times"], data["due_dates"]
    if (
        not isinstance(times, list)
        or not isinstance(dates, list)
        or not times
        or len(times) != len(dates)
    ):
        raise ValueError("Processing times and due dates must be nonempty lists of equal length.")
    if any(type(value) is not int or value <= 0 for value in times):
        raise ValueError("Processing times must be positive integers, not booleans.")
    if any(type(value) is not int or value < 0 for value in dates):
        raise ValueError("Due dates must be nonnegative integers, not booleans.")
    return SchedulingInstance(data["name"], tuple(times), tuple(dates))


@dataclass(frozen=True, slots=True)
class SchedulingProblem:
    """Bind loaded instance data to pickleable decoder and minimization callbacks.

    Responsibilities:
    - Build a priority-ordered schedule from keys and loaded processing times.
    - Score that schedule against the same instance's due dates.

    Attributes:
        instance (SchedulingInstance): Validated application-owned input snapshot.
    """

    instance: SchedulingInstance

    @property
    def n_variables(self) -> int:
        """Return the number of priority keys needed for this loaded instance.

        Returns:
            int: One key per job.
        """
        return len(self.instance.processing_times)

    def decode(self, keys: np.ndarray) -> Schedule:
        """Construct completion times in stable increasing random-key order.

        Args:
            keys (np.ndarray): One finite priority key per job; ties retain job-index order.

        Returns:
            Schedule: Ordered job indices paired with their completion times.

        Raises:
            ValueError: If keys are nonnumeric, nonfinite or have the wrong shape.
            TypeError: If keys cannot be converted into a numeric array.
        """
        values = np.asarray(keys, dtype=float)
        if values.ndim != 1 or len(values) != self.n_variables or not np.isfinite(values).all():
            raise ValueError("Decoder needs one finite key per job in a one-dimensional vector.")
        elapsed = 0
        schedule: list[tuple[int, int]] = []
        for index in np.argsort(values, kind="stable"):
            job = int(index)
            elapsed += self.instance.processing_times[job]
            schedule.append((job, elapsed))
        return tuple(schedule)

    def cost(self, solution: Schedule) -> float:
        """Sum positive lateness against the loaded due dates for a decoded schedule.

        Args:
            solution (Schedule): Ordered job/completion pairs returned by this decoder.

        Returns:
            float: Total tardiness to minimize, in the input's time units.

        Raises:
            IndexError: If a supplied schedule refers to a job outside the instance.
            OverflowError: If the summed integer tardiness cannot be represented as a float.
        """
        return float(
            sum(max(0, completion - self.instance.due_dates[job]) for job, completion in solution)
        )


def main(argv: Sequence[str] | None = None) -> None:
    """Load one instance, solve with bound callbacks and optionally export HTML.

    Args:
        argv (Sequence[str] | None): CLI arguments; None reads the process command line.

    Raises:
        SystemExit: If argument parsing fails or help is requested.
        OSError: If instance/report files cannot be accessed.
        ValueError: If the input or solver settings fail validation.
        ImportError: If HTML is requested without the optional reports dependency.
        RuntimeError: If a process worker fails.
        TimeoutError: If managed process execution exceeds its watchdog.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "instance",
        type=Path,
        nargs="?",
        default=Path(__file__).with_name("instances") / "scheduling.json",
    )
    parser.add_argument("--algorithms", nargs="+", default=["SA"])
    parser.add_argument("--backend", choices=("serial", "thread", "process"), default="serial")
    parser.add_argument("--time-limit", type=float, default=1.0)
    parser.add_argument("--n-jobs", type=int, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)
    instance = read_data(args.instance)
    problem = SchedulingProblem(instance)
    result = RKO(
        problem.decode,
        problem.cost,
        problem.n_variables,
        algorithms=args.algorithms,
        adaptation="fixed",
        backend=args.backend,
        n_jobs=args.n_jobs,
        random_state=42,
        history_limit=1000 if args.report else 0,
    ).solve(args.time_limit)
    solution = problem.decode(np.asarray(result.keys))
    print(f"Instance: {instance.name}")
    print(f"Total tardiness: {result.cost}")
    print(f"Schedule (job index, completion time): {solution}")
    if args.report is not None:
        report = OptimizationReport(
            result,
            title=f"Scheduling: {instance.name}",
            metrics={"Instance": instance.name, "Objective": "total tardiness"},
        )
        print(report.write_html(args.report))


if __name__ == "__main__":
    main()
