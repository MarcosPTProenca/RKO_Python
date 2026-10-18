"""Adaptive Q-learning control for metaheuristics.

Objective:
- Dynamically adjust search parameters using reinforcement learning over a discrete state space.

Technical approach:
- Model parameter combinations as states and local transitions as actions.
- Update Q-values with an epsilon-greedy policy and the Bellman equation.

Flow (pseudocode):
1. Build feasible states and actions.
2. Choose actions through exploration/exploitation.
3. Update Q-values and learning parameters over time.

Important criteria:
- Cyclical epsilon control.
- Recompute the current best action after every Q update.

Inputs/Outputs:
- Input: parameter grid, rewards, and current time.
- Output: selected action, learning parameters, and updated Q-table.
"""

import math
import random
from dataclasses import dataclass
from dataclasses import field


@dataclass
class QState:
    """Represents a discrete state in the Q-table.

    Responsibilities:
    - Store parameter values that define the state.
    - Maintain feasible actions and associated Q-estimates.

    Attributes:
      label (int): Unique state identifier.
      par (list[float]): Parameter vector for the state.
      ci (float): Auxiliary state metric.
      numN (int): Auxiliary neighborhood counter.
      Ai (list[int]): Indices of states reachable by each action.
      Qa (list[float]): Q-values for each feasible action.
      sumQ (float): Auxiliary sum of Q-values.
      maxQ (float): Maximum current Q-value in the state.
      minA (int): Auxiliary index for minimum action.
      maxA (int): Index of the current best action.
    """

    label: int
    par: list[float]
    ci: float = 0.0
    numN: int = 0
    Ai: list[int] = field(default_factory=list)
    Qa: list[float] = field(default_factory=list)
    sumQ: float = 0.0
    maxQ: float = 0.0
    minA: int = 0
    maxA: int = 0


class QLearningController:
    """Controls adaptive parameter tuning via Q-learning.

    Responsibilities:
    - Build the feasible state and action space.
    - Select actions and update Q-values throughout execution.

    Attributes:
      parameters (list[list[float]]): Discrete parameter grid.
      states (list[QState]): States and actions derived from the grid.
      epsilon_max (float): Upper exploration bound.
      epsilon_min (float): Lower exploration bound.
      restart_epsilon (int): Epsilon restart counter.
      max_time (float): Time horizon used for normalization.
      ti (int): Time window for periodic control.
    """

    def __init__(
        self,
        parameters: list[list[float]],
        *,
        epsilon_max: float = 1.0,
        epsilon_min: float = 0.1,
        restart_epsilon: int = 1,
        max_time: float = 1.0,
    ) -> None:
        """Initializes the Q-learning controller.

        Args:
          parameters: Discrete parameter grid used to create states.
          epsilon_max: Maximum exploration value.
          epsilon_min: Minimum exploration value.
          restart_epsilon: Restart counter for exploration.
          max_time: Maximum execution time for dynamic normalization.
        """
        self.parameters = parameters
        if parameters and all(len(values) > 0 for values in parameters):
            self.states: list[QState] = self._create_states(parameters)
        else:
            self.states = []
        self.epsilon_max = epsilon_max
        self.epsilon_min = epsilon_min
        self.restart_epsilon = restart_epsilon
        self.max_time = max_time
        self.ti = max(1, int(max_time * 0.1))

    @staticmethod
    def _create_states(parameters: list[list[float]]) -> list[QState]:
        """Creates discrete states and feasible actions for the Q-structure.

        Args:
          parameters (list[list[float]]): Discrete values per parameter.

        Returns:
          list[QState]: List of initialized states with actions and Q-values.

        Raises:
          ValueError: When required by external domain validation.
        """
        if not parameters:
            return []

        num_par = len(parameters)
        num_states = 1
        for values in parameters:
            num_states *= max(1, len(values))

        states: list[QState] = []
        for i in range(num_states):
            states.append(QState(label=i, par=[0.0] * num_par))

        n_c = 1
        for j in range(num_par):
            n_c *= len(parameters[j])
            for i in range(num_states):
                column_index = i // (num_states // n_c)
                column_index = column_index % len(parameters[j])
                states[i].par[j] = parameters[j][column_index]

        for i in range(num_states):
            for j in range(num_states):
                distance = 0
                for k in range(num_par):
                    if states[i].par[k] != states[j].par[k]:
                        distance += 1

                if distance <= 1:
                    states[i].Ai.append(j)
                    q0 = random.uniform(0.005, 0.01)
                    states[i].Qa.append(q0)
                    if q0 > states[i].maxQ:
                        states[i].maxQ = q0
                        states[i].maxA = len(states[i].Ai) - 1

        return states

    def choose_action(self, st: int, epsilon: float) -> int:
        """Selects an action using an epsilon-greedy policy.

        Args:
          st (int): Index of the current state.
          epsilon (float): Exploration probability.

        Returns:
          int: Index of the selected action in the state's action list.

        Raises:
          ValueError: When required by external domain validation.
        """
        if not self.states:
            return 0
        state = self.states[st]
        if not state.Ai:
            return 0

        if random.random() <= 1.0 - epsilon:
            return state.maxA
        return random.randint(0, len(state.Ai) - 1)

    def set_parameters(self, current_time: float) -> tuple[float, float, float, int, float, int]:
        """Updates dynamic exploration and learning parameters.

        Args:
          current_time (float): Current execution time.

        Returns:
          tuple[float, float, float, int, float, int]: Epsilon, learning factor,
            discount factor, restart_epsilon, epsilon_max e ti.

        Raises:
          ValueError: When required by external domain validation.
        """
        self.ti = max(1, int(self.max_time * 0.1))

        if current_time >= self.restart_epsilon * self.ti:
            self.restart_epsilon += 1
            self.epsilon_max = self.epsilon_max - 0.1
            if self.epsilon_max < self.epsilon_min:
                self.epsilon_max = self.epsilon_min
            epsilon = self.epsilon_max
        else:
            epsilon = self.epsilon_min + 0.5 * (self.epsilon_max - self.epsilon_min) * (
                1 + math.cos(((int(current_time) % self.ti) / float(self.ti)) * math.pi)
            )

        lf = 1.0 - (0.9 * current_time / self.max_time) if self.max_time > 0 else 1.0
        df = 0.8
        return epsilon, lf, df, self.restart_epsilon, self.epsilon_max, self.ti

    def update_q_value(self, st: int, at: int, reward: float, lf: float, df: float) -> None:
        """Updates a Q-value using the Bellman equation.

        Args:
          st (int): Index of the current state.
          at (int): Index of the selected action in the current state.
          reward (float): Reward observed in the transition.
          lf (float): Learning rate.
          df (float): Discount factor.

        Returns:
          None: Update a estrutura of states in-place.

        Raises:
          ValueError: When required by external domain validation.
        """
        if not self.states:
            return

        state = self.states[st]
        if at < 0 or at >= len(state.Ai):
            return

        st_next = state.Ai[at]
        q_old = state.Qa[at]
        q_new = q_old + lf * (reward + df * self.states[st_next].maxQ - q_old)
        state.Qa[at] = q_new

        state.maxA = max(range(len(state.Qa)), key=state.Qa.__getitem__)
        state.maxQ = state.Qa[state.maxA]


def create_states(parameters: list[list[float]]) -> list[QState]:
    """Creates states through the compatibility functional interface.

    Args:
      parameters (list[list[float]]): Discrete values per parameter.

    Returns:
      list[QState]: List of initialized states.

    Raises:
      ValueError: When required by external domain validation.
    """
    return QLearningController(parameters).states


def choose_action(states: list[QState], st: int, epsilon: float) -> int:
    """Selects an action through the compatibility functional interface.

    Args:
      states (list[QState]): Previously built Q-learning states.
      st (int): Index of the current state.
      epsilon (float): Exploration probability.

    Returns:
      int: Index of the selected action.

    Raises:
      ValueError: When required by external domain validation.
    """
    controller = QLearningController(parameters=[])
    controller.states = states
    return controller.choose_action(st, epsilon)


def set_q_learning_parameters(
    current_time: float,
    restart_epsilon: int,
    epsilon_max: float,
    epsilon_min: float,
    max_time: float,
) -> tuple[float, float, float, int, float, int]:
    """Updates dynamic parameters through the compatibility functional interface.

    Args:
      current_time (float): Current execution time.
      restart_epsilon (int): Epsilon restart counter.
      epsilon_max (float): Upper exploration bound.
      epsilon_min (float): Lower exploration bound.
      max_time (float): Execution time horizon.

    Returns:
      tuple[float, float, float, int, float, int]: Epsilon, lf, df, restart, epsilon_max, and ti.

    Raises:
      ValueError: When required by external domain validation.
    """
    controller = QLearningController(
        parameters=[],
        epsilon_max=epsilon_max,
        epsilon_min=epsilon_min,
        restart_epsilon=restart_epsilon,
        max_time=max_time,
    )
    return controller.set_parameters(current_time)


def update_q_value(
    states: list[QState], st: int, at: int, reward: float, lf: float, df: float
) -> None:
    """Updates a Q-value through the compatibility functional interface.

    Args:
      states (list[QState]): Q-learning states.
      st (int): Index of the current state.
      at (int): Index of the selected action.
      reward (float): Observed reward.
      lf (float): Learning rate.
      df (float): Discount factor.

    Returns:
      None: Update states in-place.

    Raises:
      ValueError: When required by external domain validation.
    """
    controller = QLearningController(parameters=[])
    controller.states = states
    controller.update_q_value(st, at, reward, lf, df)
