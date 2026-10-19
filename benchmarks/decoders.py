"""Compare the reference threshold decoder with a feasible ranked decoder.

Objective:
- Measure how a Knapsack-aware decoder changes solution quality under RKO.

Technical approach:
- Run the same four-algorithm process portfolio on the pinned KPLIB instance.
- Compare threshold and key-weighted profit-density decoders across three seeds.
- Verify feasibility, objective accounting, and the exact optimum independently.

Flow (pseudocode):
1. Verify the pinned instance and compute the exact 0/1 optimum.
2. Run both decoders with the same portfolio, budget, and seed set.
3. Write checked profit, weight, feasibility, gap, and elapsed time to CSV.

Important criteria:
- The C++ threshold decoder remains unchanged as a reference.
- Startup and callback overrun are included in elapsed time.
- One instance and three seeds are directional evidence only.

Inputs/Outputs:
- Input: pinned KPLIB instance path and output CSV path.
- Output: independently verified per-run results in CSV and on stdout.
"""

import argparse
import csv
import hashlib
import time
from knapsack import exact_profit
from pathlib import Path
from rko import RKO
from rko.examples.run_kp_cpp_instances import GreedyKnapsackDecoder
from rko.examples.run_kp_cpp_instances import decode_knapsack
from rko.examples.run_kp_cpp_instances import evaluate_solution
from rko.examples.run_kp_cpp_instances import make_cost
from rko.examples.run_kp_cpp_instances import read_kp_instance

_INSTANCE_SHA256 = "8f555b2b40dff1298d841a8e5abc327a8f1135ce8188e84249cd1352f959ffed"
_ALGORITHMS = ("SA", "BRKGA", "GA", "PSO")


def main() -> None:
    """Run paired decoder trials and persist verified measurements.

    Raises:
        AssertionError: If the instance fingerprint or returned accounting is invalid.
        OSError: If benchmark inputs or output cannot be read or written.
        ValueError: If the supplied file is not the pinned KPLIB instance.
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
        "decoder",
        "seed",
        "budget_seconds",
        "profit",
        "weight",
        "feasible",
        "gap_percent",
        "elapsed_seconds",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for label, decoder in (
            ("threshold", decode_knapsack),
            ("capacity_aware", GreedyKnapsackDecoder(instance)),
        ):
            for seed in (42, 43, 44):
                started = time.perf_counter()
                result = RKO(
                    decoder,
                    make_cost(instance),
                    instance.n_items,
                    algorithms=_ALGORITHMS,
                    backend="process",
                    random_state=seed,
                ).solve(15.0)
                elapsed = time.perf_counter() - started
                decisions = decoder(result.keys)
                profit, weight, feasible = evaluate_solution(decisions, instance)
                assert feasible
                assert result.cost == -float(profit)
                assert profit <= optimum
                row = {
                    "decoder": label,
                    "seed": seed,
                    "budget_seconds": 15,
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
