import math

import numpy as np

from quantumgridos.algorithms import grover_query_cost, simulate_grover_adaptive_search


def test_grover_query_cost_matches_square_root_scaling():
    assert grover_query_cost(11_664, 1) == math.ceil((math.pi / 4.0) * math.sqrt(11_664))
    assert grover_query_cost(11_664, 59) == math.ceil((math.pi / 4.0) * math.sqrt(11_664 / 59))
    assert grover_query_cost(10, 0) == math.inf


def test_simulate_grover_adaptive_search_respects_budget_and_improves():
    objectives = np.array([10.0, 8.0, 6.0, 4.0, 2.0, 0.0])

    result = simulate_grover_adaptive_search(
        objectives,
        budget=6,
        seed=7,
        initial_index=0,
    )

    assert result.queries_used <= 6
    assert result.best_objective < objectives[0]
    assert result.best_index in range(len(objectives))
    assert result.sampled_indices[0] == 0
    assert result.metadata["query_model"] == "ideal_grover_adaptive_search"


def test_simulate_grover_adaptive_search_validates_inputs():
    try:
        simulate_grover_adaptive_search([], budget=1)
    except ValueError as exc:
        assert "non-empty" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected invalid objective values to raise")

    try:
        simulate_grover_adaptive_search([1.0], budget=0)
    except ValueError as exc:
        assert "budget" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected invalid budget to raise")
