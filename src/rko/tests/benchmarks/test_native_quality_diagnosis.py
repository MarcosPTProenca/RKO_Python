"""Validate counterbalanced negative-control evidence without timed measurements.

Objective:
- Keep diagnostic Python repeats distinct from native qualification.

Technical approach:
- Build six complete synthetic three-arm case artifacts and corrupt individual boundaries.

Flow (pseudocode):
1. Accept complete balanced source-identified cases and report all contrasts.
2. Reject changed seeds, source, admission, order and adaptive replay proof.
3. Preserve the original unestablished qualification even for favorable diagnostics.

Important criteria:
- Fixture quality differences are not performance evidence.

Inputs/Outputs:
- Input: deterministic temporary raw diagnostic artifacts.
- Output: strict comparison-boundary and scope assertions.
"""

import itertools
import json
import pytest
from benchmarks.native_confirmation import NativeConfirmation
from benchmarks.native_quality_diagnosis import NativeQualityDiagnosis
from pathlib import Path


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    """Build six complete source-identified thirty-triad diagnostic cases.

    Args:
        tmp_path (Path): Independent fixture root.

    Returns:
        Path: Complete synthetic negative-control experiment.
    """
    spec, definition = NativeQualityDiagnosis.SPEC, NativeQualityDiagnosis.definition()
    orders = list(itertools.permutations(spec["arms"]))
    for index, case in enumerate(spec["cases"]):
        folder = tmp_path / str(index)
        folder.mkdir()
        (folder / "definition.json").write_text(json.dumps(definition))
        (folder / "case.json").write_text(json.dumps({"index": index, "case": case}))
        (folder / "complete.json").write_text(
            json.dumps({"definition_sha256": NativeConfirmation.digest(definition), "triads": 30})
        )
        (folder / "functional.json").write_text(
            json.dumps({"exact_replay": True, "adaptive_clock_replay": True, "native_calls": 1})
        )
        rows = []
        backend, adaptation, dimension = case
        for trial in range(30):
            seed = 61000 + trial
            row = {"seed": seed, "order": orders[trial % 6]}
            for arm, regret in (("python_a", 0.1), ("python_b", 0.11), ("native", 0.08)):
                cost = regret * dimension
                searches = [
                    {
                        "algorithm": algorithm,
                        "random_state": pos,
                        "parameters": [["test", 1]],
                        "parameter_grid": [],
                        "control": int(adaptation == "adaptive"),
                        "n_evaluations": 10,
                        "history": [{"cost": cost, "n_evaluations": 10, "elapsed_seconds": 1.0}],
                    }
                    for pos, algorithm in enumerate(("SA", "GA", "BRKGA"))
                ]
                row[arm] = {
                    "backend": backend,
                    "adaptation": adaptation,
                    "dimension": dimension,
                    "workload": "object",
                    "seconds": 2.0,
                    "seed": seed,
                    "functional": False,
                    "native_admitted": arm == "native",
                    "installed_sources_sha256": "a" * 64,
                    "n_workers": {"serial": 1, "thread": 3, "process": 2}[backend],
                    "versions": {"rko": "dev", "python": "3.14.9", "numpy": "2.4.3"},
                    "n_evaluations": 30,
                    "cost": cost,
                    "normalized_regret": cost / dimension,
                    "searches": searches,
                }
            rows.append(row)
        (folder / "triads.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return tmp_path


def test_diagnosis_does_not_requalify_previous_confirmation(evidence: Path) -> None:
    """Keep negative-control descriptions separate from original acceptance.

    Args:
        evidence (Path): Six complete synthetic diagnostic cases.

    Raises:
        AssertionError: If favorable diagnostic contrasts become qualification.
    """
    result = NativeQualityDiagnosis.analyze(evidence)
    assert result["collection_validated"] and result["triads"] == 180
    assert result["fresh_timed_workers"] == 540 and len(result["groups"]) == 6
    assert result["changes_original_qualification"] is False
    assert result["original_qualification_status"] == "not_established"
    assert result["release_authorized"] is False
    for group in result["groups"]:
        assert group["python_repeat"]["losses"] == 30
        assert group["native_vs_a"]["wins"] == group["native_vs_b"]["wins"] == 30
        assert group["adaptive_logical_clock_exact_replay"]


@pytest.mark.parametrize(
    "fault", ["source", "clock", "order", "seed", "control", "configuration", "profile", "coverage"]
)
def test_diagnosis_rejects_changed_comparison(evidence: Path, fault: str) -> None:
    """Reject malformed or instrumented controls before interpreting variability.

    Args:
        evidence (Path): Otherwise valid diagnostic experiment.
        fault (str): Individual source, proof or raw-observation violation.

    Raises:
        AssertionError: If an invalid comparison is admitted.
    """
    folder = evidence / "0"
    if fault == "source":
        path = folder / "definition.json"
        value = json.loads(path.read_text())
        value["inputs_sha256"]["setup.py"] = "changed"
        path.write_text(json.dumps(value))
    elif fault == "clock":
        path = folder / "functional.json"
        value = json.loads(path.read_text())
        value["adaptive_clock_replay"] = False
        path.write_text(json.dumps(value))
    else:
        path = folder / "triads.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if fault == "coverage":
            rows.pop()
        elif fault == "seed":
            rows[0]["seed"] = 50000
        elif fault == "order":
            rows[0]["order"] = list(reversed(rows[0]["order"]))
        elif fault == "control":
            rows[0]["python_b"]["native_admitted"] = True
        elif fault == "configuration":
            rows[0]["python_b"]["searches"][0]["random_state"] = 999
        else:
            rows[0]["native"]["functional"] = rows[0]["python_a"]["functional"] = True
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises(ValueError):
        NativeQualityDiagnosis.analyze(evidence)
