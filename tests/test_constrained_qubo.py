import numpy as np

from quantumgridos.algorithms.qubo import (
    QUBOProblem,
    make_constrained_bit_matrix,
    solve_constrained_qubo_qaoa_statevector,
)


def test_make_constrained_bit_matrix_enforces_one_hot_groups():
    states = make_constrained_bit_matrix(5, [[0, 1], [2, 3, 4]])

    assert states.shape == (6, 5)
    assert all(int(row[[0, 1]].sum()) == 1 for row in states)
    assert all(int(row[[2, 3, 4]].sum()) == 1 for row in states)


def test_constrained_qaoa_returns_only_feasible_one_hot_states():
    problem = QUBOProblem(
        linear=np.array([-3.0, 0.0, 0.0, -2.0]),
        quadratic=np.zeros((4, 4)),
        variable_names=["a0", "a1", "b0", "b1"],
    )

    solutions = solve_constrained_qubo_qaoa_statevector(
        problem,
        one_hot_groups=[[0, 1], [2, 3]],
        layers=1,
        maxiter=20,
        top_k=4,
        seed=11,
        restarts=1,
    )

    assert solutions
    assert all(sum(solution.bitstring[index] for index in [0, 1]) == 1 for solution in solutions)
    assert all(sum(solution.bitstring[index] for index in [2, 3]) == 1 for solution in solutions)
    assert solutions[0].metadata["basis_states"] == 4
