"""Idealized Grover adaptive-search utilities.

These helpers are query-complexity simulators. They do not claim hardware
runtime, and they assume the objective predicate can be represented as an
oracle. They are useful for grid-planning studies where quantum is evaluated
as a candidate generator under an objective-oracle budget.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np


@dataclass
class GroverAdaptiveResult:
    """Result from an ideal Grover Adaptive Search query simulation."""

    best_index: int
    best_objective: float
    queries_used: int
    sampled_indices: List[int]
    best_objective_trace: List[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def grover_query_cost(total_states: int, marked_states: int) -> int:
    """Return the ideal Grover query cost for a marked set.

    The expression is ceil((pi / 4) * sqrt(N / M)). It is a query-complexity
    estimate, not a runtime estimate.
    """

    if total_states < 1:
        raise ValueError("total_states must be positive")
    if marked_states < 1:
        return math.inf
    if marked_states > total_states:
        raise ValueError("marked_states cannot exceed total_states")
    return max(1, int(math.ceil((math.pi / 4.0) * math.sqrt(total_states / marked_states))))


def simulate_grover_adaptive_search(
    objective_values: Sequence[float],
    budget: int,
    *,
    seed: Optional[int] = None,
    initial_index: Optional[int] = None,
) -> GroverAdaptiveResult:
    """Simulate ideal Grover Adaptive Search over known objective values.

    Lower objective values are better. The objective array is used here only
    for offline query-accounting studies: at each step the simulator computes
    the number of states better than the incumbent, charges the corresponding
    Grover query cost, and samples a better state if the budget allows.
    """

    values = np.asarray(objective_values, dtype=float)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("objective_values must be a non-empty one-dimensional sequence")
    if budget < 1:
        raise ValueError("budget must be at least 1")

    rng = np.random.default_rng(seed)
    total_states = int(values.size)
    if initial_index is None:
        current = int(rng.integers(0, total_states))
    else:
        current = int(initial_index)
        if current < 0 or current >= total_states:
            raise ValueError("initial_index is outside objective_values")

    sampled_indices = [current]
    best_index = current
    best_objective = float(values[current])
    best_trace = [best_objective]
    queries_used = 1

    while queries_used < budget:
        marked_indices = np.flatnonzero(values < best_objective - 1e-12)
        marked_count = int(marked_indices.size)
        if marked_count == 0:
            break

        query_cost = grover_query_cost(total_states, marked_count)
        remaining = budget - queries_used
        if query_cost <= remaining:
            queries_used += query_cost
            hit = int(rng.choice(marked_indices))
            sampled_indices.append(hit)
            if float(values[hit]) < best_objective:
                best_index = hit
                best_objective = float(values[hit])
                best_trace.append(best_objective)
            continue

        theta = math.asin(math.sqrt(marked_count / total_states))
        success_probability = math.sin((2 * remaining + 1) * theta) ** 2
        queries_used += remaining
        if rng.random() < success_probability:
            hit = int(rng.choice(marked_indices))
            sampled_indices.append(hit)
            if float(values[hit]) < best_objective:
                best_index = hit
                best_objective = float(values[hit])
                best_trace.append(best_objective)
        break

    return GroverAdaptiveResult(
        best_index=best_index,
        best_objective=best_objective,
        queries_used=queries_used,
        sampled_indices=sampled_indices,
        best_objective_trace=best_trace,
        metadata={
            "total_states": total_states,
            "budget": int(budget),
            "query_model": "ideal_grover_adaptive_search",
        },
    )
