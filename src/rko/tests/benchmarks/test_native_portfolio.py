"""Protect native timed-screen comparison identity and recursive memory boundaries.

Objective:
- Reject fallback or incomparable pairs before producing misleading evidence.

Technical approach:
- Mutate individual comparison fields and model recursive procfs snapshots.

Flow (pseudocode):
1. Accept an otherwise matching timed reference/native pair.
2. Reject altered identities and functional profiling in timed evidence.
3. Sum unique process IDs across all threads without counting collector memory.

Important criteria:
- Timed costs and trajectories may differ legitimately; exact replay is not required.

Inputs/Outputs:
- Input: bounded raw pair and fake procfs snapshots.
- Output: deterministic validation and memory-accounting assertions.
"""

import copy
import pytest
from benchmarks import native_portfolio
from benchmarks.native_portfolio import NativePortfolioStudy
from benchmarks.native_portfolio import ProcessTreeMemory
from pathlib import Path


@pytest.fixture
def pair() -> dict[str, dict]:
    """Create matching reference/native timed observations with different quality.

    Returns:
        dict[str, dict]: Independent otherwise-comparable trial records.
    """
    base = {
        "backend": "process",
        "adaptation": "adaptive",
        "workload": "object",
        "dimension": 500,
        "seconds": 2.0,
        "seed": 40000,
        "functional": False,
        "installed_sources_sha256": "same-wheel",
        "n_workers": 2,
        "native_admitted": False,
        "versions": {"rko": "dev", "python": "3.14", "numpy": "2.4.3"},
        "cost": 30.0,
    }
    return {"python": base, "native": dict(base, native_admitted=True, cost=20.0)}


def test_timed_pairs_do_not_require_equal_trajectories(pair: dict[str, dict]) -> None:
    """Accept different timed quality without inventing an exact replay requirement.

    Args:
        pair (dict[str, dict]): Matching timed pair with different objective values.
    """
    NativePortfolioStudy.validate_pair(pair)


@pytest.mark.parametrize(
    "field",
    [
        "backend",
        "adaptation",
        "workload",
        "dimension",
        "seconds",
        "seed",
        "installed_sources_sha256",
        "n_workers",
    ],
)
def test_comparison_rejects_mixed_identity(pair: dict[str, dict], field: str) -> None:
    """Refuse a pair whose workload or installed artifact changed.

    Args:
        pair (dict[str, dict]): Otherwise comparable timed pair.
        field (str): Comparison boundary to invalidate.

    Raises:
        AssertionError: If a mixed comparison passes.
    """
    changed = copy.deepcopy(pair)
    changed["native"][field] = "different"
    with pytest.raises(ValueError, match="Mixed pair field"):
        NativePortfolioStudy.validate_pair(changed)


@pytest.mark.parametrize("case", ["fallback", "reference-native", "profiled", "missing", "runtime"])
def test_screen_rejects_invalid_admission(pair: dict[str, dict], case: str) -> None:
    """Reject fallback, incomplete pairs and functional-profiler timing samples.

    Args:
        pair (dict[str, dict]): Otherwise comparable timed pair.
        case (str): Admission violation.

    Raises:
        AssertionError: If invalid timed evidence is admitted.
    """
    if case == "fallback":
        pair["native"]["native_admitted"] = False
    elif case == "reference-native":
        pair["python"]["native_admitted"] = True
    elif case == "profiled":
        for row in pair.values():
            row["functional"] = True
    elif case == "runtime":
        pair["native"]["versions"] = dict(pair["native"]["versions"], numpy="different")
    else:
        del pair["native"]
    with pytest.raises(ValueError):
        NativePortfolioStudy.validate_pair(pair)


def test_pss_tree_counts_each_descendant_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Follow children of every thread while deduplicating shared process IDs.

    Args:
        tmp_path (Path): Fake procfs tree outside live process observations.
        monkeypatch (pytest.MonkeyPatch): Scoped procfs path substitution.

    Raises:
        AssertionError: If children are missed or counted twice.
    """
    for pid, children, pss in ((101, "202", 10), (202, "303", 20), (303, "", 30)):
        root = tmp_path / str(pid)
        for task in (pid, pid + 1):
            folder = root / "task" / str(task)
            folder.mkdir(parents=True)
            (folder / "children").write_text(children)
        (root / "smaps_rollup").write_text(f"Rss: 999 kB\nPss: {pss} kB\n")
    monkeypatch.setattr(native_portfolio, "Path", lambda value: tmp_path / Path(value).name)
    assert ProcessTreeMemory.snapshot(101) == 60 * 1024
    (tmp_path / "303/smaps_rollup").write_text("Rss: 99 kB\n")
    with pytest.raises(ValueError, match="Missing PSS"):
        ProcessTreeMemory.snapshot(101)
