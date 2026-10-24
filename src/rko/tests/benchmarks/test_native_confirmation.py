"""Exercise frozen timed-confirmation coverage and exact paired-median uncertainty.

Objective:
- Prevent incomplete or changed experiments from being reported as qualification.

Technical approach:
- Construct all720 neutral paired observations without running timed optimizers.
- Corrupt individual protocol boundaries and separate valid negative results from errors.

Flow (pseudocode):
1. Verify exact median order-statistic ranks for the frozen family coverage.
2. Analyze six complete synthetic shards through the actual report boundary.
3. Reject altered evidence and preserve failed quality gates without changing criteria.

Important criteria:
- These fixtures test analysis, not native performance or real scientific outcomes.

Inputs/Outputs:
- Input: deterministic independent raw-evidence fixtures in temporary folders.
- Output: coverage, uncertainty and gate regression assertions.
"""

import json
import pytest
from benchmarks.native_confirmation import NativeConfirmation
from pathlib import Path


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    """Build all six source-identified thirty-seed shard fixtures.

    Args:
        tmp_path (Path): Isolated raw-evidence root.

    Returns:
        Path: Complete synthetic confirmation parent directory.
    """
    spec, definition = NativeConfirmation.SPEC, NativeConfirmation.definition()
    for backend in spec["backends"]:
        for adaptation in spec["adaptations"]:
            folder = tmp_path / f"{backend}-{adaptation}"
            folder.mkdir()
            (folder / "confirmation.json").write_text(json.dumps(definition))
            (folder / "confirmation-complete.json").write_text(
                json.dumps(
                    {"definition_sha256": NativeConfirmation.digest(definition), "pairs": 120}
                )
            )
            protocol = {
                key: spec[key]
                for key in ("repeats", "seed_start", "seconds", "dimensions", "workloads")
            }
            protocol.update(
                backend=backend,
                adaptation=adaptation,
                scope="independent_preregistered_timed_confirmation",
                threads={
                    key: "1"
                    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
                },
            )
            (folder / "protocol.json").write_text(json.dumps(protocol))
            rows = []
            for dimension in spec["dimensions"]:
                for workload in spec["workloads"]:
                    for seed in range(spec["seed_start"], spec["seed_start"] + spec["repeats"]):
                        row = {
                            "kind": "pair",
                            "order": ["python", "native"]
                            if seed % 2 == 0
                            else ["native", "python"],
                        }
                        for native, label in ((False, "python"), (True, "native")):
                            quality = 0.09 if native else 0.1
                            span = dimension * (dimension - 1) * (dimension + 1) / 6
                            cost = (
                                span * (1 + quality)
                                if workload == "permutation"
                                else quality * dimension
                            )
                            regret = (
                                (cost - span) / span
                                if workload == "permutation"
                                else cost / dimension
                            )
                            row[label] = {
                                "backend": backend,
                                "adaptation": adaptation,
                                "dimension": dimension,
                                "workload": workload,
                                "seconds": 2.0,
                                "seed": seed,
                                "functional": False,
                                "native_admitted": native,
                                "installed_sources_sha256": "a" * 64,
                                "n_workers": {"serial": 1, "thread": 3, "process": 2}[backend],
                                "versions": {"python": "3.14.9", "numpy": "2.4.3", "rko": "dev"},
                                "fresh_process_seconds": 6.0 if backend == "serial" else 2.0,
                                "n_evaluations": 200 if native else 100,
                                "sampled_peak_tree_pss_bytes": 102 if native else 100,
                                "pss_complete_samples": 90,
                                "cost": cost,
                                "normalized_regret": regret,
                            }
                        rows.append(row)
            (folder / "pairs.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return tmp_path


def test_exact_simultaneous_median_order_statistics() -> None:
    """Use finite distribution-free bounds rather than fitted or bootstrap margins.

    Raises:
        AssertionError: If frozen discrete coverage or ranks change.
    """
    interval = NativeConfirmation.interval(list(map(float, range(30))))
    assert interval["lower_rank_one_based"] == 6
    assert interval["simultaneous95"] == [5.0, 24.0]
    assert interval["median"] == 14.5
    assert interval["interval_coverage_lower_bound"] > 1 - 0.05 / 72
    with pytest.raises(ValueError, match="thirty finite"):
        NativeConfirmation.interval([float("nan")] * 30)


def test_complete_confirmation_is_not_release_authorization(evidence: Path) -> None:
    """Qualify only complete passing fixture groups without authorizing publication.

    Args:
        evidence (Path): Six complete synthetic shards.

    Raises:
        AssertionError: If valid coverage or release boundaries change.
    """
    result = NativeConfirmation.analyze(evidence)
    assert result["collection_validated"] and result["all_scoped_gates_pass"]
    assert result["qualification_status"] == "established"
    assert result["pairs"] == 720 and len(result["groups"]) == 24
    assert result["release_authorized"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "source",
        "protocol",
        "pilot",
        "missing",
        "duplicate",
        "profile",
        "memory",
        "quality",
        "completion",
    ],
)
def test_confirmation_rejects_invalid_evidence(evidence: Path, fault: str) -> None:
    """Reject malformed or retrospectively changed evidence at the report boundary.

    Args:
        evidence (Path): Otherwise valid complete experiment.
        fault (str): Individual source, protocol, coverage or measurement violation.

    Raises:
        AssertionError: If invalid raw evidence is admitted.
    """
    folder = evidence / "serial-fixed"
    if fault == "source":
        path = folder / "confirmation.json"
        value = json.loads(path.read_text())
        value["inputs_sha256"]["setup.py"] = "changed"
        path.write_text(json.dumps(value))
    elif fault == "protocol":
        path = folder / "protocol.json"
        value = json.loads(path.read_text())
        value["seconds"] = 3.0
        path.write_text(json.dumps(value))
    elif fault == "completion":
        (folder / "confirmation-complete.json").unlink()
    else:
        path = folder / "pairs.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if fault == "missing":
            rows.pop()
        elif fault == "duplicate":
            rows[-1] = rows[-2]
        else:
            row = rows[0]
            if fault == "pilot":
                row["native"]["seed"] = row["python"]["seed"] = 40000
            elif fault == "profile":
                row["native"]["functional"] = row["python"]["functional"] = True
            elif fault == "memory":
                row["native"]["sampled_peak_tree_pss_bytes"] = None
            else:
                row["native"]["normalized_regret"] = 0.5
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises((ValueError, FileNotFoundError)):
        NativeConfirmation.analyze(evidence)


def test_inferiority_is_a_valid_failed_gate_not_a_collection_error(evidence: Path) -> None:
    """Preserve a completed negative result instead of relaxing the quality margin.

    Args:
        evidence (Path): Complete valid experiment to alter within its declared objective.

    Raises:
        AssertionError: If measured quality loss is hidden or criteria change.
    """
    path = evidence / "serial-fixed/pairs.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        if row["native"]["dimension"] == 20 and row["native"]["workload"] == "object":
            row["native"]["cost"] = 4.0
            row["native"]["normalized_regret"] = 0.2
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    result = NativeConfirmation.analyze(evidence)
    assert result["collection_validated"] and not result["all_scoped_gates_pass"]
    assert result["qualification_status"] == "not_established"
    assert any(not group["gates"]["quality_no_loss_established"] for group in result["groups"])
    assert NativeConfirmation.SPEC["quality_median_difference_upper"] == 0.0
