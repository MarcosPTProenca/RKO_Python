"""Validate installed pure/native artifacts through fresh public-interface processes.

Objective:
- Prove default Python mode, opt-in activation and deterministic installed-artifact parity.

Technical approach:
- Compare disabled/enabled workers in isolated interpreters, never importing checkout code.
- Observe the real C-extension call with profiling only during functional checks.
- Check public blending and complete managed searches stopped by an original user exception.

Flow (pseudocode):
1. Start a Python-reference worker and an explicit-native worker.
2. Compare child values, private RNG states and all decoded-candidate prefixes.
3. Require real native execution for native artifacts, or an actionable pure fallback.

Important criteria:
- No profiler or callback exception is used to claim performance or timed quality.

Inputs/Outputs:
- Input: installed artifact and expected binary presence.
- Output: exact functional parity and activation assertions.
"""

import argparse
import hashlib
import importlib.util
import json
import numpy as np
import os
import pickle
import subprocess
import sys
import warnings
from pathlib import Path


def trace_search(constructor: type) -> str:
    """Fingerprint every candidate through a managed public search and user exception.

    Args:
        constructor (type): Public registered algorithm class.

    Returns:
        str: Complete deterministic candidate-prefix digest.

    Raises:
        AssertionError: If the original exception or completed prefix is lost.
    """
    trace = hashlib.sha256()
    count = 0
    stopped = LookupError("completed functional trace")

    def decoder(keys: np.ndarray) -> dict[str, np.ndarray]:
        """Record protected keys while retaining an opaque payload.

        Args:
            keys (np.ndarray): Decoder-owned random keys.

        Returns:
            dict[str, np.ndarray]: Exact objective payload.
        """
        trace.update(keys.tobytes())
        return {"values": keys}

    def objective(payload: dict[str, np.ndarray]) -> float:
        """Score until a fixed functional checkpoint.

        Args:
            payload (dict[str, np.ndarray]): Original decoded object.

        Returns:
            float: Finite score before interruption.

        Raises:
            LookupError: Original observable callback failure at512 evaluations.
        """
        nonlocal count
        count += 1
        if count == 512:
            raise stopped
        return float(np.dot(payload["values"], payload["values"]))

    try:
        constructor(
            decoder,
            objective,
            20,
            backend="serial",
            adaptation="fixed",
            prefill_pool=False,
            random_state=42,
            hyperparameters={"SA": {"sa_max": 10}} if constructor.__name__ == "SA" else None,
        ).solve(3600)
    except LookupError as error:
        assert error is stopped
    else:
        raise AssertionError("original callback error was swallowed")
    assert count == 512
    return trace.hexdigest()


def worker(binary: bool) -> dict:
    """Exercise installed public interfaces and report exact functional fingerprints.

    Args:
        binary (bool): Whether this artifact must include the native module.

    Returns:
        dict: Result/stream/trace fingerprints and real native call count.

    Raises:
        AssertionError: If installation provenance, behavior or activation is wrong.
    """
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        import rko
        from rko.components.blending.blending import blending
        from rko.components.random_streams import RandomStreams
        from rko.metaheuristics import BRKGA
        from rko.metaheuristics import SA
        from rko.metaheuristics import GeneticAlgorithm
    root = Path(__file__).resolve().parents[1]
    assert root not in Path(rko.__file__).resolve().parents, "checkout code was imported"
    assert (importlib.util.find_spec("rko._native") is not None) == binary
    enabled = os.environ.get("RKO_USE_NATIVE") == "1"
    notices = [w for w in observed if "RKO_USE_NATIVE" in str(w.message)]
    assert len(notices) == (1 if enabled and not binary else 0)
    native_module = sys.modules.get("rko._native")
    assert (native_module is not None) == (binary and enabled)
    kernel = getattr(native_module, "blend_buffers_rng", None)
    native_calls = 0

    def profile(frame: object, event: str, arg: object) -> None:
        """Observe actual extension execution without replacing its implementation.

        Args:
            frame (object): Interpreter frame, unused.
            event (str): CPython profile event.
            arg (object): Invoked C callable for c_call events.
        """
        nonlocal native_calls
        if event == "c_call" and arg is kernel:
            native_calls += 1

    digest = hashlib.sha256()
    traces = {}
    sys.setprofile(profile)
    try:
        for n in (1, 20, 500):
            for factor in (-1.0, 1.0):
                for seed in (7, 42, 200):
                    a = np.linspace(0, 0.9999999, n)
                    b = a[::-1].copy()
                    a.flags.writeable = b.flags.writeable = False
                    streams = RandomStreams(seed)
                    with streams.activate():
                        result = blending(a, b, factor)
                    assert result.flags.owndata and result.flags.writeable
                    assert not np.shares_memory(a, result) and not np.shares_memory(b, result)
                    digest.update(result.tobytes())
                    digest.update(
                        pickle.dumps((streams.python.getstate(), streams.numpy.get_state()))
                    )
        for a in (np.array([0.1, 0.8], dtype=np.float32), np.array([0.1, 0.2, 0.8, 0.9])[::2]):
            before = native_calls
            with RandomStreams(42).activate():
                result = blending(a, a[::-1], -1)
            assert native_calls == before
            digest.update(result.tobytes())
        for constructor in (SA, GeneticAlgorithm, BRKGA):
            traces[constructor.__name__] = trace_search(constructor)
    finally:
        sys.setprofile(None)
    assert (native_calls > 0) == (binary and enabled)
    return {"fingerprint": digest.hexdigest(), "traces": traces, "native_calls": native_calls}


def main() -> None:
    """Compare independent installed reference/native workers.

    Raises:
        Exception: Worker, import, native or functional validation failures propagate.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", choices=("absent", "present"), required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.binary == "present")))
        return
    rows = []
    for enabled in (False, True):
        env = os.environ.copy()
        env["RKO_USE_NATIVE"] = "1" if enabled else "0"
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                str(Path(__file__).resolve()),
                "--binary",
                args.binary,
                "--worker",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        rows.append(json.loads(completed.stdout))
    assert rows[0]["fingerprint"] == rows[1]["fingerprint"]
    assert rows[0]["traces"] == rows[1]["traces"]
    print(
        json.dumps(
            {"binary": args.binary, "exact_replay": True, "native_calls": rows[1]["native_calls"]}
        )
    )


if __name__ == "__main__":
    main()
