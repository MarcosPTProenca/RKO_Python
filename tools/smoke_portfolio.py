"""Validate installed timed portfolios with unchanged opaque Python callbacks.

Objective:
- Check adaptive and fixed SA/GA/BRKGA portfolios across execution backends.

Technical approach:
- Use picklable numerical-object and permutation callbacks in isolated interpreters.
- Record each participating process's selected blending implementation.
- Independently recompute results, history, seed mapping and evaluation accounting.

Flow (pseudocode):
1. Check installed provenance and prepare private callback observations.
2. Construct and solve a bounded public portfolio.
3. Verify detached results and emit raw quality/time/resource metadata.

Important criteria:
- Functional kernel probes are disabled during measurement collection.
- Timed trajectories are not required to replay across faster implementations.
- Reported elapsed time is not a general speed or quality acceptance claim.

Inputs/Outputs:
- Input: bounded solver settings and explicit native environment set before import.
- Output: independently validated raw trial JSON or an original failure.
"""

import argparse
import hashlib
import json
import multiprocessing as mp
import numpy as np
import os
import pickle
import random
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from rko import RKO
from rko.components.blending.blending import _native_blend
from rko.components.blending.blending import blending
from rko.components.random_streams import RandomStreams


@dataclass
class OpaqueDecoder:
    """Decode an opaque payload and observe each process without changing search RNG.

    Responsibilities:
    - Keep callbacks importable for spawn and retain independent result validation.
    - Probe real kernel calls only in explicitly functional trials.

    Attributes:
        directory (Path): Per-trial observation directory.
        ordering (bool): Decode a stable permutation instead of continuous values.
        functional (bool): Run an untimed-contract probe inside the first callback.
        seen (set[int]): Process IDs already observed in this decoder instance.
    """

    directory: Path
    ordering: bool
    functional: bool
    seen: set[int] = field(default_factory=set)

    def __call__(self, keys: np.ndarray) -> dict[str, np.ndarray]:
        """Record admission and return the original numerical or ordering payload.

        Args:
            keys (np.ndarray): Decoder-owned candidate vector.

        Returns:
            dict[str, np.ndarray]: Unchanged numerical values or stable permutation.

        Raises:
            AssertionError: If a functional native probe never invokes the kernel.
            OSError: If process observations cannot be retained.
        """
        pid = os.getpid()
        if pid not in self.seen:
            self.seen.add(pid)
            calls = 0
            if self.functional and _native_blend is not None:

                def profile(frame: object, event: str, arg: object) -> None:
                    """Observe one actual C-kernel call during a functional-only check.

                    Args:
                        frame (object): Interpreter frame, unused.
                        event (str): CPython event kind.
                        arg (object): C callable being invoked.
                    """
                    nonlocal calls
                    if event == "c_call" and arg is _native_blend:
                        calls += 1

                previous = sys.getprofile()
                sys.setprofile(profile)
                try:
                    with RandomStreams(0).activate():
                        blending(np.array([0.1, 0.2]), np.array([0.8, 0.9]))
                finally:
                    sys.setprofile(previous)
                assert calls == 1
            record = {
                "pid": pid,
                "process": mp.current_process().name,
                "native_admitted": _native_blend is not None,
                "functional_calls": calls,
            }
            self.directory.joinpath(f"{pid}.json").write_text(json.dumps(record), encoding="utf-8")
        return {"values": np.argsort(keys, kind="stable") if self.ordering else keys}


@dataclass(frozen=True)
class OpaqueObjective:
    """Score opaque numerical objects or positional permutation assignments.

    Responsibilities:
    - Keep objective implementations identical between baseline and native trials.

    Attributes:
        ordering (bool): Use weighted permutation assignment rather than sphere.
    """

    ordering: bool

    def __call__(self, payload: dict[str, np.ndarray]) -> float:
        """Compute the original finite callback score once.

        Args:
            payload (dict[str, np.ndarray]): Decoder-produced representation.

        Returns:
            float: Positional assignment cost or numerical squared norm.
        """
        values = payload["values"]
        if self.ordering:
            return float(np.dot(values, np.arange(1, len(values) + 1)))
        return sum(float(value) ** 2 for value in values)


def trial(args: argparse.Namespace) -> dict[str, object]:
    """Run one installed portfolio and validate accounting, ownership and provenance.

    Args:
        args (argparse.Namespace): Validated trial settings.

    Returns:
        dict[str, object]: Raw independently checked invocation and result observations.

    Raises:
        AssertionError: If solver contracts or child native admission differ.
        Exception: Original solver, callback and filesystem failures propagate.
    """
    import rko

    assert Path(__file__).resolve().parents[1] not in Path(rko.__file__).resolve().parents
    assert np.isfinite(args.seconds) and args.seconds > 0 and args.dimension > 0
    assert sys.flags.optimize == 0, "functional assertions must be enabled"
    package = Path(rko.__file__).resolve().parent
    sources = hashlib.sha256()
    for path in sorted(package.rglob("*")):
        if path.suffix in (".py", ".toml", ".so", ".pyd"):
            sources.update(path.relative_to(package).as_posix().encode())
            sources.update(path.read_bytes())
    before = pickle.dumps((random.getstate(), np.random.get_state()))
    before_children = {child.pid for child in mp.active_children()}
    before_threads = {thread.ident for thread in threading.enumerate()}
    names = ["SA", "GA", "BRKGA"]
    with tempfile.TemporaryDirectory(prefix="rko-portfolio-") as directory:
        decoder = OpaqueDecoder(Path(directory), args.workload == "permutation", args.functional)
        objective = OpaqueObjective(decoder.ordering)
        started = time.perf_counter()
        result = RKO(
            decoder,
            objective,
            args.dimension,
            algorithms=names,
            adaptation=args.adaptation,
            backend=args.backend,
            n_jobs=args.workers if args.backend == "process" else None,
            random_state=args.seed,
            history_limit=8,
            prefill_pool=False,
        ).solve(args.seconds)
        invocation = time.perf_counter() - started
        records = [json.loads(path.read_text()) for path in Path(directory).glob("*.json")]
        keys = np.asarray(result.keys)
        assert keys.shape == (args.dimension,) and np.all((keys >= 0) & (keys < 1))
        payload = {"values": np.argsort(keys, kind="stable") if decoder.ordering else keys}
        assert np.isfinite(result.cost) and result.cost == objective(payload)
        assert result.n_evaluations == sum(report.n_evaluations for report in result.searches)
        assert [report.algorithm for report in result.searches] == names
        seeds = np.random.SeedSequence(args.seed).spawn(len(names))
        assert [report.random_state for report in result.searches] == [
            int(s.generate_state(1)[0]) for s in seeds
        ]
        assert all(
            report.n_evaluations >= 1 and report.stop_reason == "time_limit"
            for report in result.searches
        )
        for report in result.searches:
            assert report.history_limit == 8
            assert 1 <= len(report.history) <= min(8, report.history_observations)
            assert all(0 < point.n_evaluations <= report.n_evaluations for point in report.history)
            assert all(
                a.cost >= b.cost and a.elapsed_seconds <= b.elapsed_seconds
                for a, b in zip(report.history, report.history[1:], strict=False)
            )
            assert bool(report.parameter_grid) == (args.adaptation == "adaptive")
        assert result.stop_reason == "time_limit" and invocation >= result.elapsed_seconds > 0
        assert pickle.loads(pickle.dumps(result)) == result
        assert records and all(
            row["native_admitted"] == (_native_blend is not None) for row in records
        )
        if args.backend == "process":
            workers = [row for row in records if row["process"].startswith("rko-")]
            assert len(workers) == result.n_workers == min(args.workers, len(names))
        if args.functional and _native_blend is not None:
            assert all(row["functional_calls"] == 1 for row in records)
        assert ("rko-native-blending" in dict(result.versions)) == (_native_blend is not None)
    assert pickle.dumps((random.getstate(), np.random.get_state())) == before
    assert {child.pid for child in mp.active_children()} == before_children
    assert {thread.ident for thread in threading.enumerate()} == before_threads
    normalized = result.cost / args.dimension
    if decoder.ordering:
        n = args.dimension
        optimum = n * (n - 1) * (n + 1) / 6
        span = n * (n - 1) * (n + 1) / 6
        normalized = (result.cost - optimum) / span if span else 0.0
    return {
        "installed_sources_sha256": sources.hexdigest(),
        "backend": args.backend,
        "adaptation": args.adaptation,
        "workload": args.workload,
        "dimension": args.dimension,
        "seconds": args.seconds,
        "seed": args.seed,
        "functional": args.functional,
        "native_admitted": _native_blend is not None,
        "invocation_seconds": invocation,
        "elapsed_seconds": result.elapsed_seconds,
        "cost": result.cost,
        "normalized_regret": normalized,
        "n_evaluations": result.n_evaluations,
        "n_workers": result.n_workers,
        "versions": dict(result.versions),
        "process_observations": records,
        "result_sha256": hashlib.sha256(pickle.dumps(result)).hexdigest(),
    }


def main() -> None:
    """Parse bounded settings and emit one trial or the functional coverage matrix.

    Raises:
        Exception: Trial, worker and artifact failures propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("serial", "thread", "process"), default="serial")
    parser.add_argument("--adaptation", choices=("fixed", "adaptive"), default="fixed")
    parser.add_argument("--workload", choices=("object", "permutation"), default="object")
    parser.add_argument("--dimension", type=int, default=20)
    parser.add_argument("--seconds", type=float, default=0.15)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=40000)
    parser.add_argument("--functional", action="store_true")
    parser.add_argument("--matrix", action="store_true")
    args = parser.parse_args()
    if args.matrix:
        assert args.functional, "matrix mode is functional-only, not acceptance timing"
        for backend in ("serial", "thread", "process"):
            for adaptation in ("fixed", "adaptive"):
                for workload in ("object", "permutation"):
                    args.backend, args.adaptation, args.workload = backend, adaptation, workload
                    print(json.dumps(trial(args)), flush=True)
    else:
        print(json.dumps(trial(args)), flush=True)


if __name__ == "__main__":
    main()
