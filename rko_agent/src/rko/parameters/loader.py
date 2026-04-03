"""Parameter file loader and watcher for the RKO framework.

Objective:
- Read and write per-metaheuristic TOML parameter files at runtime so that
  hyperparameters can be adjusted without restarting the process.

Technical approach:
- Parse ``.toml`` files with the built-in ``tomllib`` module (Python 3.11+).
- Provide a minimal TOML serialiser for the flat ``[offline]`` / ``[online]``
  structure used by every metaheuristic parameter file.
- Offer a background ``ParameterWatcher`` that polls file modification times
  and fires a callback whenever a file is edited externally.

File layout (one TOML file per metaheuristic plus one global config):
- ``config.toml``        – global settings (control, strategy, pool_size …)
- ``sa.toml``            – SA parameters
- ``multi_start.toml``   – MultiStart (no parameters)
- ``ils.toml``           – ILS parameters
- ``vns.toml``           – VNS parameters
- ``lns.toml``           – LNS parameters
- ``grasp.toml``         – GRASP parameters
- ``brkga.toml``         – BRKGA parameters
- ``ga.toml``            – GeneticAlgorithm parameters
- ``pso.toml``           – PSO parameters
- ``brkga_cs.toml``      – BRKGA-CS parameters
- ``ipr.toml``           – IPR (no parameters)

Inputs/Outputs:
- Input:  metaheuristic name string, optional custom directory path.
- Output: offline parameter dict, online Q-Learning grid list-of-lists,
          or global config dict.
"""

import os
import threading
import tomllib
from collections.abc import Callable
from pathlib import Path

_PARAMS_DIR: Path = Path(__file__).parent

_NAME_TO_FILE: dict[str, str] = {
    "SA": "sa",
    "MultiStart": "multi_start",
    "ILS": "ils",
    "VNS": "vns",
    "LNS": "lns",
    "GRASP": "grasp",
    "BRKGA": "brkga",
    "GeneticAlgorithm": "ga",
    "GA": "ga",
    "PSO": "pso",
    "BRKGA_CS": "brkga_cs",
    "IPR": "ipr",
}


def default_params_dir() -> Path:
    """Return the default parameters directory (same folder as this module).

    Returns:
      Path to the directory containing the ``.toml`` parameter files.
    """
    return _PARAMS_DIR


def toml_path(mh_name: str, params_dir: Path | None = None) -> Path:
    """Return the ``.toml`` file path for the given metaheuristic name.

    Args:
      mh_name: Any of the recognised metaheuristic names (e.g. ``"ILS"``,
        ``"BRKGA_CS"``, ``"GeneticAlgorithm"``).
      params_dir: Directory that contains the ``.toml`` files.  Defaults to
        the same directory as this module.

    Returns:
      Absolute ``Path`` to the corresponding ``.toml`` file.

    Raises:
      KeyError: When *mh_name* is not in the known-name mapping.
    """
    stem = _NAME_TO_FILE[mh_name]
    return (params_dir or _PARAMS_DIR) / f"{stem}.toml"


def load_config(params_dir: Path | None = None) -> dict[str, object]:
    """Read ``config.toml`` and return its parsed contents.

    Args:
      params_dir: Directory that contains the ``.toml`` files.

    Returns:
      Nested dict reflecting the sections in ``config.toml``.

    Raises:
      FileNotFoundError: When ``config.toml`` does not exist.
    """
    path = (params_dir or _PARAMS_DIR) / "config.toml"
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def load_offline(
    mh_name: str,
    params_dir: Path | None = None,
) -> dict[str, float | int | bool | str]:
    """Read the ``[offline]`` section for *mh_name* fresh from disk.

    The file is re-read on every call so external edits are always reflected.

    Args:
      mh_name: Recognised metaheuristic name (e.g. ``"ILS"``, ``"BRKGA"``).
      params_dir: Override for the default parameters directory.

    Returns:
      Dict mapping parameter names to their scalar values.  Returns an empty
      dict when the ``[offline]`` section is absent or empty.

    Raises:
      KeyError: When *mh_name* is not recognised.
      FileNotFoundError: When the ``.toml`` file does not exist.
    """
    path = toml_path(mh_name, params_dir)
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return dict(data.get("offline", {}))


def load_online_grid(
    mh_name: str,
    params_dir: Path | None = None,
) -> list[list[float]]:
    """Read the ``[online]`` section and return it as a list-of-lists grid.

    The grid is the direct input for ``QLearningController(parameters=...)``.
    The axis order matches the key order in the ``[online]`` TOML section.

    Args:
      mh_name: Recognised metaheuristic name.
      params_dir: Override for the default parameters directory.

    Returns:
      ``[[param0_values], [param1_values], …]`` – one inner list per
      parameter axis.  Returns an empty list when the ``[online]`` section
      is absent or empty.

    Raises:
      KeyError: When *mh_name* is not recognised.
      FileNotFoundError: When the ``.toml`` file does not exist.
    """
    path = toml_path(mh_name, params_dir)
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    online: dict[str, list[float]] = data.get("online", {})
    return [list(v) for v in online.values()]


def load_online_named(
    mh_name: str,
    params_dir: Path | None = None,
) -> dict[str, list[float]]:
    """Read the ``[online]`` section as an ordered ``{name: [values]}`` dict.

    Args:
      mh_name: Recognised metaheuristic name.
      params_dir: Override for the default parameters directory.

    Returns:
      Ordered dict mapping parameter names to their discrete value lists.

    Raises:
      KeyError: When *mh_name* is not recognised.
      FileNotFoundError: When the ``.toml`` file does not exist.
    """
    path = toml_path(mh_name, params_dir)
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return {k: list(v) for k, v in data.get("online", {}).items()}


def save_online_grid(
    mh_name: str,
    grid: list[list[float]],
    *,
    params_dir: Path | None = None,
) -> None:
    """Overwrite the ``[online]`` values in the TOML file with *grid*.

    The parameter names are inferred from the current file so the axis order
    is preserved.  Offline values and comment blocks are regenerated without
    inline comments.

    Args:
      mh_name: Recognised metaheuristic name.
      grid: New grid ``[[param0_values], [param1_values], …]``.  Must
        contain the same number of axes as the existing ``[online]`` section.
      params_dir: Override for the default parameters directory.

    Raises:
      KeyError: When *mh_name* is not recognised.
      FileNotFoundError: When the ``.toml`` file does not exist.
      ValueError: When *grid* has a different number of axes than the file.
    """
    path = toml_path(mh_name, params_dir)
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    online_keys = list(data.get("online", {}).keys())
    if len(online_keys) != len(grid):
        raise ValueError(
            f"{mh_name}: grid has {len(grid)} axes but file has {len(online_keys)} online keys."
        )

    new_online: dict[str, list[float]] = {
        k: list(v) for k, v in zip(online_keys, grid, strict=False)
    }
    _write_toml(path, dict(data.get("offline", {})), new_online)


def _fmt_value(val: float | int | bool | str) -> str:
    """Format a scalar value for TOML output.

    Args:
      val: Scalar value (int, float, bool, str).

    Returns:
      TOML-compatible string representation.
    """
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, float):
        return repr(val)
    return str(val)


def _write_toml(
    path: Path,
    offline: dict[str, float | int | bool | str],
    online: dict[str, list[float]],
) -> None:
    """Serialise *offline* and *online* back to a TOML file.

    Args:
      path: Destination file path.
      offline: ``{param_name: scalar_value}`` for ``[offline]`` section.
      online: ``{param_name: [values]}`` for ``[online]`` section.
    """
    lines: list[str] = []
    if offline:
        lines.append("[offline]\n")
        for key, val in offline.items():
            lines.append(f"{key} = {_fmt_value(val)}\n")
    else:
        lines.append("[offline]\n")
        lines.append("# (no parameters)\n")

    lines.append("\n[online]\n")
    if online:
        for key, vals in online.items():
            vals_str = ", ".join(_fmt_value(v) for v in vals)
            lines.append(f"{key} = [{vals_str}]\n")
    else:
        lines.append("# (no parameters)\n")

    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


class ParameterWatcher:
    """Background thread that watches a TOML file for external modifications.

    On every *poll_interval* seconds the watcher checks whether the file's
    modification time has changed.  When a change is detected the file is
    re-parsed and the registered callback is called with the new data.

    Responsibilities:
    - Detect file changes via ``os.stat``.
    - Parse the changed file and dispatch a callback.
    - Stop cleanly when :meth:`stop` is called.

    Example::

      def on_change(mh_name, offline, grid):
          print(f"{mh_name} updated: offline={offline}, grid axes={len(grid)}")

      watcher = ParameterWatcher("ILS", on_change, poll_interval=2.0)
      watcher.start()
      # ... run optimisation ...
      watcher.stop()

    Attributes:
      mh_name (str): The metaheuristic whose file is being watched.
      callback (Callable): Called with ``(mh_name, offline_dict, online_grid)``
        whenever the file changes.
      poll_interval (float): Polling period in seconds.
      params_dir (Path): Directory containing the parameter files.
    """

    def __init__(
        self,
        mh_name: str,
        callback: Callable[[str, dict[str, float | int | bool | str], list[list[float]]], None],
        *,
        poll_interval: float = 2.0,
        params_dir: Path | None = None,
    ) -> None:
        """Initialise the watcher without starting the background thread.

        Args:
          mh_name: Recognised metaheuristic name to watch.
          callback: Function called with ``(mh_name, offline, online_grid)``
            when the file changes.
          poll_interval: Seconds between filesystem polls.
          params_dir: Override for the default parameters directory.

        Returns:
          None: Initialises instance state.

        Raises:
          KeyError: When *mh_name* is not in the known-name mapping.
        """
        self.mh_name = mh_name
        self.callback = callback
        self.poll_interval = poll_interval
        self.params_dir = params_dir or _PARAMS_DIR
        self._path: Path = toml_path(mh_name, self.params_dir)
        self._last_mtime: float = 0.0
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event = threading.Event()

    def start(self) -> None:
        """Start the background polling thread.

        Raises:
          RuntimeError: When the watcher is already running.
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError(f"ParameterWatcher for '{self.mh_name}' is already running.")
        self._stop_event.clear()
        self._last_mtime = self._current_mtime()
        self._thread = threading.Thread(target=self._poll, daemon=True, name=f"pw-{self.mh_name}")
        self._thread.start()

    def stop(self) -> None:
        """Signal the polling thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.poll_interval + 1.0)

    def _current_mtime(self) -> float:
        """Return the modification time of the watched file.

        Returns:
          Modification time in seconds since the epoch, or 0.0 if the file
          does not exist.
        """
        try:
            return os.stat(self._path).st_mtime
        except OSError:
            return 0.0

    def _poll(self) -> None:
        """Polling loop executed in the background thread."""
        while not self._stop_event.wait(self.poll_interval):
            mtime = self._current_mtime()
            if mtime != self._last_mtime:
                self._last_mtime = mtime
                try:
                    offline = load_offline(self.mh_name, self.params_dir)
                    grid = load_online_grid(self.mh_name, self.params_dir)
                    self.callback(self.mh_name, offline, grid)
                except Exception:
                    pass
