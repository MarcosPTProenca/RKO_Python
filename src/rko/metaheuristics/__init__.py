"""Available metaheuristics in RKO.

Objective:
- Centralize metaheuristic strategy implementations for random-key optimization.

Technical approach:
- Define a common contract through an abstract base class.
- Specialize each algorithm in its own module.

Flow (pseudocode):
1. Initialize solution and parameters.
2. Run the exploration/intensification loop.
3. Report the best solution and cost.

Important criteria:
- Respect the time limit.
- Keep best-solution updates consistent.

Inputs/Outputs:
- Input: solution pool, decoder/cost functions, and hyperparameters.
- Output: best random-key vector found and associated objective value.
"""

from __future__ import annotations

from .base import LocalSearchOperator
from .base import MetaheuristicBase
from .base import ShakingOperator
from .brkga import BRKGA
from .brkga_cs import BRKGA_CS
from .ga import GeneticAlgorithm
from .grasp import GRASP
from .ils import ILS
from .ipr import IPR
from .lns import LNS
from .multi_start import MultiStart
from .pso import PSO
from .sa import SA
from .vns import VNS

__all__ = [
    "LocalSearchOperator",
    "MetaheuristicBase",
    "ShakingOperator",
    "BRKGA",
    "BRKGA_CS",
    "GeneticAlgorithm",
    "GRASP",
    "ILS",
    "IPR",
    "LNS",
    "MultiStart",
    "PSO",
    "SA",
    "VNS",
]
