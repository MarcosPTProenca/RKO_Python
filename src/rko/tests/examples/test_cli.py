"""Terminal contracts for the Knapsack problem adapter.

Objective:
- Run a selected instance and external configuration without a Python driver.

Technical approach:
- Check argument boundaries and the installed console command in subprocesses.

Flow (pseudocode):
1. Parse single-instance and legacy batch selections.
2. Reject ambiguous or missing input paths.
3. Execute serial/spawn searches and independently check exported accounting.

Important criteria:
- Preserve paths containing spaces and do not modify user parameter files.

Inputs/Outputs:
- Input: temporary instances, parameter TOMLs and CLI arguments.
- Output: parser assertions and checked CSV results.
"""

import csv
import pytest
import shutil
import subprocess
import sys
from pathlib import Path
from rko.examples.run_kp_cpp_instances import default_instances_dir
from rko.examples.run_kp_cpp_instances import parse_args
from rko.parameters.loader import default_params_dir


def test_legacy_batch_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the existing no-argument bundled-instance selection.

    Args:
        monkeypatch (pytest.MonkeyPatch): Supply an empty command line.
    """
    monkeypatch.setattr(sys, "argv", ["rko"])
    args = parse_args()
    assert args.instance is None
    assert args.instances_dir == default_instances_dir()
    assert args.pattern == "kp*.txt"


def test_positional_instance_preserves_spaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accept a direct instance path without glob-based selection.

    Args:
        tmp_path (Path): Temporary fixture directory.
        monkeypatch (pytest.MonkeyPatch): Supply a direct input argument.
    """
    instance = tmp_path / "tiny instance.txt"
    instance.write_text("3 5 6 1 10 2 12 3", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["rko", str(instance)])
    assert parse_args().instance == instance


@pytest.mark.parametrize("selector", ["--instances-dir", "--pattern"])
def test_single_instance_rejects_batch_selectors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selector: str,
) -> None:
    """Reject conflicting selectors rather than silently ignoring user settings.

    Args:
        tmp_path (Path): Temporary input directory.
        monkeypatch (pytest.MonkeyPatch): Supply conflicting arguments.
        selector (str): Batch-only option.
    """
    instance = tmp_path / "tiny.txt"
    instance.write_text("1 1 1 1", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["rko", str(instance), selector, str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        parse_args()
    assert error.value.code == 2


@pytest.mark.parametrize("name", ["missing.txt", "."])
def test_instance_must_be_a_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    """Report missing files and directories as command-line errors.

    Args:
        tmp_path (Path): Existing directory for the invalid path.
        monkeypatch (pytest.MonkeyPatch): Supply the invalid instance argument.
        name (str): Missing filename or existing directory marker.
    """
    monkeypatch.setattr(sys, "argv", ["rko", str(tmp_path / name)])
    with pytest.raises(SystemExit) as error:
        parse_args()
    assert error.value.code == 2


@pytest.mark.parametrize("backend", ["serial", "process"])
@pytest.mark.parametrize("selection", ["single", "batch"])
def test_console_runs_external_instance_and_parameters(
    tmp_path: Path,
    backend: str,
    selection: str,
) -> None:
    """Execute the real entry point with user-owned configuration and CSV output.

    Args:
        tmp_path (Path): Temporary instance/configuration/result directory.
        backend (str): Serial or spawned execution mode.
        selection (str): Direct path or legacy directory/glob selection.
    """
    executable = shutil.which("rko")
    assert executable is not None
    instance = tmp_path / "tiny instance.txt"
    instance.write_text("3 5 6 1 10 2 12 3", encoding="utf-8")
    parameters = tmp_path / "my parameters"
    parameters.mkdir()
    for source in default_params_dir().glob("*.toml"):
        shutil.copy2(source, parameters / source.name)
    configuration = parameters / "config.toml"
    configuration.write_text(
        '[run]\ncontrol=0\npool_size=2\n[active_metaheuristics]\nlist=["MultiStart"]\n',
        encoding="utf-8",
    )
    before = {path.name: path.read_bytes() for path in parameters.iterdir()}
    output = tmp_path / "my results" / "result.csv"
    arguments = (
        [str(instance)]
        if selection == "single"
        else [
            "--instances-dir",
            str(tmp_path),
            "--pattern",
            instance.name,
        ]
    )
    completed = subprocess.run(
        [
            executable,
            *arguments,
            *(["--n-jobs", "1"] if backend == "process" else []),
            "--params-dir",
            str(parameters),
            "--limit-time",
            "0.05",
            "--backend",
            backend,
            "--random-state",
            "42",
            "--output-csv",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
        cwd=tmp_path,
    )
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    row = rows[0]
    assert row["instance"] == instance.name
    assert int(row["n_items"]) == 3
    assert row["backend"] == backend
    assert row["worker_budget"] == ("1" if backend == "process" else "")
    assert row["seed"] == "42"
    assert float(row["cost"]) == 100000 * max(0, int(row["weight"]) - 5) - int(row["profit"])
    assert "CSV saved to:" in completed.stdout
    assert before == {path.name: path.read_bytes() for path in parameters.iterdir()}
