"""Simple Q-learning stub for UIRE clarification policy.

This module defines a minimal Q-learning algorithm for deciding whether
to ask clarifying questions or assume defaults.  It is provided as a
reference implementation and not integrated into the API.
"""
from __future__ import annotations
import random
from typing import Dict, Tuple

class QPolicy:
    def __init__(self, alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 0.2):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        # Q-table maps state -> action -> value
        self.q: Dict[Tuple[int], Dict[int, float]] = {}

    def choose_action(self, state: Tuple[int]) -> int:
        # actions: 0 = ask clarifying question, 1 = assume default
        if random.random() < self.epsilon:
            return random.choice([0, 1])
        values = self.q.get(state, {})
        return max(values.keys(), default=0, key=lambda a: values.get(a, 0.0))

    def update(self, state: Tuple[int], action: int, reward: float, next_state: Tuple[int]) -> None:
        values = self.q.setdefault(state, {})
        old = values.get(action, 0.0)
        next_values = self.q.get(next_state, {})
        best_next = max(next_values.values(), default=0.0)
        values[action] = old + self.alpha * (reward + self.gamma * best_next - old)
