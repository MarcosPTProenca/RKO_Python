"""Validate compact paired study reports without running the expanded experiment.

Objective:
- Reject incomplete, overlapping or incomparable evidence before publishing summaries.

Technical approach:
- Use the identified pilot as a valid fixture and corrupt individual controls.
- Recompute outcomes and medians independently from its archived trial records.

Flow (pseudocode):
1. Compile known paired rows into compact observations and grouped summaries.
2. Mutate accounting, provenance or pairing fields one at a time.
3. Require validation failures instead of silently merging bad observations.

Important criteria:
- Existing pilot pairs must not be counted twice in an expanded study.
- No timing or statistical-superiority conclusions are inferred by aggregation.

Inputs/Outputs:
- Input: archived JSONL and isolated corrupted copies.
- Output: validated groups or explicit data-validation failures.
"""

import csv
import importlib
import json
import pytest
import statistics
import sys
from pathlib import Path
from types import ModuleType


@pytest.fixture
def reporter(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import optional reporting code from the repository benchmark directory.

    Args:
        monkeypatch (pytest.MonkeyPatch): Expose benchmark tools during the test.

    Returns:
        ModuleType: Report compiler.
    """
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4] / "benchmarks"))
    return importlib.import_module("prefill_report")


def test_report_recomputes_pilot_groups(reporter: ModuleType) -> None:
    """Check compact evidence against the independent identified raw pilot.

    Args:
        reporter (ModuleType): Report compiler.
    """
    source = Path(reporter.__file__).with_name("prefill-work-reference.jsonl")
    report, pairs = reporter.compile_report([source])
    assert report["pairs"] == len(pairs) == 60 and len(report["groups"]) == 12
    for group in report["groups"]:
        selected = [
            row
            for row in pairs
            if (row["algorithm"], row["workload"]) == (group["algorithm"], group["workload"])
        ]
        assert group["pairs"] == len(selected) == 5
        assert group["better"] + group["tied"] + group["worse"] == 5
        assert group["default_median"] == statistics.median(row["default_cost"] for row in selected)
        assert group["prefilled_median"] == statistics.median(
            row["prefilled_cost"] for row in selected
        )
    assert report["timing"] is False


@pytest.mark.parametrize(
    "damage",
    [
        "duplicate",
        "missing_pair",
        "accounting",
        "seed",
        "prefix",
        "nonfinite",
        "cost_type",
        "timing",
        "unknown",
        "missing_field",
        "missing_family",
    ],
)
def test_report_rejects_corrupted_shards(
    reporter: ModuleType,
    tmp_path: Path,
    damage: str,
) -> None:
    """Reject a single scientific-control mutation instead of emitting plausible totals.

    Args:
        reporter (ModuleType): Report compiler.
        tmp_path (Path): Isolated corrupted shard directory.
        damage (str): Control or schema field to corrupt.
    """
    source = Path(reporter.__file__).with_name("prefill-work-reference.jsonl")
    records = [json.loads(line) for line in source.read_text().splitlines()]
    index = next(
        i for i, row in enumerate(records) if row.get("kind") == "trial" and row["prefill"]
    )
    if damage == "duplicate":
        records.append(records[index].copy())
    elif damage == "missing_pair":
        records.pop(index)
    elif damage == "accounting":
        records[index]["search_evaluations"] -= 1
    elif damage == "seed":
        records[index]["search_seed"] += 1
    elif damage == "prefix":
        records[index]["startup_seed_prefix_sha256"] = "bad"
    elif damage == "nonfinite":
        records[index]["cost"] = float("nan")
    elif damage == "cost_type":
        records[index]["cost"] = "invalid"
    elif damage == "timing":
        records[0]["timing"] = True
    elif damage == "unknown":
        records.append({"kind": "unknown"})
    elif damage == "missing_field":
        del records[index]["cost"]
    else:
        records = [row for row in records if row.get("workload") != "flat"]
    target = tmp_path / "corrupt.jsonl"
    target.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
    with pytest.raises(ValueError):
        reporter.compile_report([target])


def test_report_cli_writes_compact_evidence(
    reporter: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exercise workflow output filenames and retained pair evidence end to end.

    Args:
        reporter (ModuleType): Report compiler/CLI.
        monkeypatch (pytest.MonkeyPatch): Supply validated report arguments.
        tmp_path (Path): Isolated input and output directories.
    """
    source = Path(reporter.__file__).with_name("prefill-work-reference.jsonl")
    directory = tmp_path / "raw"
    directory.mkdir()
    (directory / "pilot.jsonl").write_bytes(source.read_bytes())
    prefix = tmp_path / "report" / "prefill-expanded"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prefill_report",
            "--input-dir",
            str(directory),
            "--output-prefix",
            str(prefix),
            "--run-url",
            "https://example.test/study",
        ],
    )
    reporter.main()
    summary = json.loads(prefix.with_name(prefix.name + "-summary.json").read_text())
    assert summary["pairs"] == 60 and summary["workflow_run_url"] == "https://example.test/study"
    with prefix.with_name(prefix.name + "-pairs.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 60 and all(row["evaluations"] == "256" for row in rows)


def test_report_rejects_overlap_and_mixed_provenance(reporter: ModuleType, tmp_path: Path) -> None:
    """Keep repeated pilot seeds and incompatible producer revisions out of combined totals.

    Args:
        reporter (ModuleType): Report compiler.
        tmp_path (Path): Isolated mixed-provenance shard directory.
    """
    source = Path(reporter.__file__).with_name("prefill-work-reference.jsonl")
    with pytest.raises(ValueError, match="duplicate"):
        reporter.compile_report([source, source])
    records = [json.loads(line) for line in source.read_text().splitlines()]
    records[0]["source_revision"] = "different"
    target = tmp_path / "different.jsonl"
    target.write_text("\n".join(json.dumps(row) for row in records), encoding="utf-8")
    with pytest.raises(ValueError, match="mixed study provenance"):
        reporter.compile_report([source, target])
    with pytest.raises(ValueError, match="no study shards"):
        reporter.compile_report([])
