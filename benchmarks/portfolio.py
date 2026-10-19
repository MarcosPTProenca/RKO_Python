"""Compare the measured four-worker preset with the former ten-worker portfolio.

Objective:
- Validate whether a CPU-sized process portfolio improves elapsed time and quality.

Technical approach:
- Run both configurations against the pinned 1,000-item KPLIB instance.
- Use identical process backend, time budget, shared pool size, and seed set.
- Recompute feasibility, objective accounting, and exact optimum independently.

Flow (pseudocode):
1. Verify the pinned instance and compute its exact 0/1 optimum.
2. Create isolated TOML configurations for both portfolios.
3. Run each seed and record time, feasibility, profit, and optimality gap.

Important criteria:
- The four-search preset and ten-search full portfolio are not truncated.
- Process startup and callback overrun are included in measured elapsed time.
- Three seeds on one instance are directional evidence, not a general guarantee.

Inputs/Outputs:
- Input: pinned KPLIB instance path and output CSV path.
- Output: verified CSV rows and concise per-trial console results.
"""

import argparse
import csv
import hashlib
import shutil
import time
from knapsack import exact_profit
from pathlib import Path
from rko import RKO
from rko.examples.run_kp_cpp_instances import decode_knapsack
from rko.examples.run_kp_cpp_instances import evaluate_solution
from rko.examples.run_kp_cpp_instances import make_cost
from rko.examples.run_kp_cpp_instances import read_kp_instance
from rko.parameters.loader import default_params_dir
from tempfile import TemporaryDirectory

_PORTFOLIOS = {
    "four": ("SA", "BRKGA", "GA", "PSO"),
    "full": ("SA", "ILS", "VNS", "LNS", "BRKGA", "BRKGA_CS", "PSO", "GA", "GRASP", "IPR"),
}
_INSTANCE_SHA256 = "8f555b2b40dff1298d841a8e5abc327a8f1135ce8188e84249cd1352f959ffed"


def main() -> None:
    """Run controlled portfolio trials and write independently checked results.

    Raises:
        AssertionError: If the instance fingerprint or solver accounting is invalid.
        OSError: If benchmark inputs or output cannot be read or written.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.instance.read_bytes()).hexdigest() != _INSTANCE_SHA256:
        raise ValueError("Input must be the pinned KPLIB s000.kp benchmark instance.")
    instance = read_kp_instance(args.instance)
    optimum = exact_profit(instance)
    fields = [
        "portfolio",
        "seed",
        "algorithms",
        "budget_seconds",
        "profit",
        "weight",
        "feasible",
        "gap_percent",
        "elapsed_seconds",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="rko-portfolio-") as temporary:
        params = Path(temporary)
        for source in default_params_dir().glob("*.toml"):
            shutil.copy2(source, params / source.name)
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for label, algorithms in _PORTFOLIOS.items():
                (params / "config.toml").write_text(
                    "[run]\ncontrol = 1\npool_size = 10\n"
                    "[active_metaheuristics]\nlist = ["
                    + ", ".join(f'"{name}"' for name in algorithms)
                    + "]\n",
                    encoding="utf-8",
                )
                for seed in (42, 43, 44):
                    started = time.perf_counter()
                    result = RKO(
                        decode_knapsack,
                        make_cost(instance),
                        instance.n_items,
                        params_dir=params,
                        backend="process",
                        random_state=seed,
                    ).solve(10.0)
                    elapsed = time.perf_counter() - started
                    profit, weight, feasible = evaluate_solution(
                        decode_knapsack(result.keys), instance
                    )
                    assert feasible
                    assert result.cost == -float(profit)
                    assert profit <= optimum
                    row = {
                        "portfolio": label,
                        "seed": seed,
                        "algorithms": ";".join(algorithms),
                        "budget_seconds": 10,
                        "profit": profit,
                        "weight": weight,
                        "feasible": feasible,
                        "gap_percent": 100.0 * (optimum - profit) / optimum,
                        "elapsed_seconds": elapsed,
                    }
                    writer.writerow(row)
                    stream.flush()
                    print(row, flush=True)


if __name__ == "__main__":
    main()
