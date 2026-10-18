"""RKO parameter file management.

Objective:
- Provide a single import point for reading, writing, and watching the
  per-metaheuristic TOML parameter files that drive both offline tuning and
  the online Q-Learning control mode.

Technical approach:
- All parameter files live alongside this package (``parameters/``).
- ``tomllib`` (built-in, Python 3.11+) handles reading.
- A custom minimal TOML serialiser handles writing (no third-party deps).
- ``ParameterWatcher`` polls file modification times in a daemon thread.

Inputs/Outputs:
- Input:  metaheuristic name string, optional directory override.
- Output: offline scalar dict, online list-of-lists grid, or global config.
"""

from .loader import ParameterWatcher
from .loader import default_params_dir
from .loader import load_config
from .loader import load_offline
from .loader import load_online_grid
from .loader import load_online_named
from .loader import save_online_grid
from .loader import toml_path

__all__ = [
    "ParameterWatcher",
    "default_params_dir",
    "load_config",
    "load_offline",
    "load_online_grid",
    "load_online_named",
    "save_online_grid",
    "toml_path",
]
