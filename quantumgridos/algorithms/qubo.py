"""Generic QUBO utilities for quantum-grid candidate generation.

The helpers in this module intentionally model only the binary master problem.
Continuous dispatch, frequency dynamics, protection timing, and inverter
physics should be validated outside the QUBO by domain-specific engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np


BitString = Tuple[int, ...]


@dataclass
class QUBOProblem:
    """Dense QUBO model for small and medium candidate-generation problems.

    The objective is

        constant + linear @ x + sum_{i < j} quadratic[i, j] x_i x_j

    for binary vector x. Diagonal entries in ``quadratic`` are folded into the
    linear vector during initialization.
    """

    linear: np.ndarray
    quadratic: np.ndarray
    constant: float = 0.0
    variable_names: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.linear = np.asarray(self.linear, dtype=float)
        self.quadratic = np.asarray(self.quadratic, dtype=float)

        if self.quadratic.shape != (self.num_variables, self.num_variables):
            raise ValueError("quadratic must be a square matrix matching linear length")

        diagonal = np.diag(self.quadratic).copy()
        if np.any(diagonal):
            self.linear = self.linear + diagonal
            self.quadratic = self.quadratic.copy()
            np.fill_diagonal(self.quadratic, 0.0)

        upper = np.triu(self.quadratic, 1)
        lower = np.tril(self.quadratic, -1).T
        self.quadratic = upper + lower

        if not self.variable_names:
            self.variable_names = [f"x_{i}" for i in range(self.num_variables)]
        if len(self.variable_names) != self.num_variables:
            raise ValueError("variable_names length must match linear length")

    @property
    def num_variables(self) -> int:
        return int(self.linear.shape[0])

    def energy(self, bits: Sequence[int]) -> float:
        x = np.asarray(bits, dtype=float)
        if x.shape != self.linear.shape:
            raise ValueError("bit vector length does not match QUBO")
        return float(self.constant + self.linear @ x + x @ self.quadratic @ x)

    def energies(self, bit_matrix: np.ndarray) -> np.ndarray:
        x = np.asarray(bit_matrix, dtype=float)
        return self.constant + x @ self.linear + np.einsum("bi,ij,bj->b", x, self.quadratic, x)

    def assignment(self, bits: Sequence[int]) -> Dict[str, int]:
        return {name: int(bit) for name, bit in zip(self.variable_names, bits)}

    def copy(self) -> "QUBOProblem":
        return QUBOProblem(
            linear=self.linear.copy(),
            quadratic=self.quadratic.copy(),
            constant=self.constant,
            variable_names=list(self.variable_names),
            metadata=dict(self.metadata),
        )


@dataclass
class QUBOSolution:
    """Result returned by a QUBO candidate generator."""

    bitstring: BitString
    energy: float
    solver: str
    probability: Optional[float] = None
    samples: int = 0
    metadata: Dict = field(default_factory=dict)

    def as_dict(self, problem: Optional[QUBOProblem] = None) -> Dict:
        payload = {
            "bitstring": "".join(str(bit) for bit in self.bitstring),
            "energy": self.energy,
            "solver": self.solver,
            "probability": self.probability,
            "samples": self.samples,
            "metadata": self.metadata,
        }
        if problem is not None:
            payload["assignment"] = problem.assignment(self.bitstring)
        return payload


def make_bit_matrix(num_variables: int) -> np.ndarray:
    """Return all binary vectors in ascending integer order."""

    if num_variables < 1:
        raise ValueError("num_variables must be positive")
    if num_variables > 24:
        raise ValueError("exact bit matrix is limited to 24 variables")

    values = np.arange(2**num_variables, dtype=np.uint64)
    shifts = np.arange(num_variables, dtype=np.uint64)
    return ((values[:, None] >> shifts) & 1).astype(np.int8)


def _normalize_one_hot_groups(
    num_variables: int,
    one_hot_groups: Optional[Sequence[Sequence[int]] | Mapping[str, Sequence[int]]],
) -> List[Tuple[int, ...]]:
    if one_hot_groups is None:
        return []

    groups_iterable = one_hot_groups.values() if isinstance(one_hot_groups, Mapping) else one_hot_groups
    groups: List[Tuple[int, ...]] = []
    seen: set[int] = set()
    for raw_group in groups_iterable:
        group = tuple(int(index) for index in raw_group)
        if len(group) < 2:
            raise ValueError("one-hot groups must contain at least two variables")
        for index in group:
            if index < 0 or index >= num_variables:
                raise ValueError("one-hot group index is outside the QUBO variable range")
            if index in seen:
                raise ValueError("one-hot groups must be disjoint")
            seen.add(index)
        groups.append(group)
    return groups


def make_constrained_bit_matrix(
    num_variables: int,
    one_hot_groups: Optional[Sequence[Sequence[int]] | Mapping[str, Sequence[int]]] = None,
    *,
    max_states: int = 1_000_000,
) -> np.ndarray:
    """Return all binary states satisfying supplied one-hot constraints.

    Variables not included in a one-hot group remain ordinary binary
    variables. The returned ordering is deterministic and intended for
    statevector experiments in the feasible subspace.
    """

    if num_variables < 1:
        raise ValueError("num_variables must be positive")

    groups = _normalize_one_hot_groups(num_variables, one_hot_groups)
    grouped_indices = {index for group in groups for index in group}
    binary_indices = [index for index in range(num_variables) if index not in grouped_indices]
    state_count = (2 ** len(binary_indices)) * int(np.prod([len(group) for group in groups], dtype=np.int64) if groups else 1)
    if state_count > max_states:
        raise ValueError(
            f"constrained state space has {state_count} states, above max_states={max_states}"
        )

    rows: List[np.ndarray] = []
    binary_assignments = np.array(
        list(np.ndindex(*(2 for _ in binary_indices))) if binary_indices else [()],
        dtype=np.int8,
    )
    group_assignments = list(np.ndindex(*(len(group) for group in groups))) if groups else [()]

    for binary_values in binary_assignments:
        for group_values in group_assignments:
            bits = np.zeros(num_variables, dtype=np.int8)
            for index, value in zip(binary_indices, binary_values):
                bits[index] = int(value)
            for group, selected_position in zip(groups, group_values):
                bits[group[int(selected_position)]] = 1
            rows.append(bits)

    return np.vstack(rows).astype(np.int8)


def solve_qubo_exact(problem: QUBOProblem, top_k: int = 10) -> List[QUBOSolution]:
    """Enumerate all states and return the best assignments.

    This is intended as a correctness baseline for small QUBOs and as a strong
    comparator for near-term quantum experiments.
    """

    bit_matrix = make_bit_matrix(problem.num_variables)
    energies = problem.energies(bit_matrix)
    order = np.argsort(energies, kind="stable")[:top_k]

    return [
        QUBOSolution(
            bitstring=tuple(int(v) for v in bit_matrix[idx]),
            energy=float(energies[idx]),
            solver="exact",
            probability=None,
            samples=1,
        )
        for idx in order
    ]


def solve_qubo_simulated_annealing(
    problem: QUBOProblem,
    reads: int = 128,
    sweeps: int = 500,
    top_k: int = 10,
    seed: Optional[int] = None,
    start_temperature: float = 4.0,
    end_temperature: float = 0.05,
) -> List[QUBOSolution]:
    """Simple simulated-annealing baseline for binary QUBOs."""

    rng = np.random.default_rng(seed)
    n = problem.num_variables
    best: Dict[BitString, QUBOSolution] = {}
    schedule = np.geomspace(start_temperature, end_temperature, max(2, sweeps))

    for _ in range(reads):
        bits = rng.integers(0, 2, size=n, dtype=np.int8)
        energy = problem.energy(bits)

        for temperature in schedule:
            i = int(rng.integers(0, n))
            trial = bits.copy()
            trial[i] = 1 - trial[i]
            trial_energy = problem.energy(trial)
            delta = trial_energy - energy
            if delta <= 0 or rng.random() < np.exp(-delta / temperature):
                bits = trial
                energy = trial_energy

        key = tuple(int(v) for v in bits)
        if key not in best or energy < best[key].energy:
            best[key] = QUBOSolution(key, float(energy), "simulated_annealing", samples=1)
        else:
            best[key].samples += 1

    return sorted(best.values(), key=lambda item: item.energy)[:top_k]


def qubo_to_ising(problem: QUBOProblem):
    """Convert a QUBO to a Qiskit SparsePauliOp Ising Hamiltonian."""

    try:
        from qiskit.quantum_info import SparsePauliOp
    except ImportError as exc:
        raise ImportError("qiskit is required for qubo_to_ising") from exc

    n = problem.num_variables
    constant = float(problem.constant)
    z_terms = np.zeros(n, dtype=float)
    zz_terms: Dict[Tuple[int, int], float] = {}

    for i, coeff in enumerate(problem.linear):
        constant += coeff / 2.0
        z_terms[i] += -coeff / 2.0

    for i in range(n):
        for j in range(i + 1, n):
            coeff = float(problem.quadratic[i, j])
            if coeff == 0.0:
                continue
            constant += coeff / 4.0
            z_terms[i] += -coeff / 4.0
            z_terms[j] += -coeff / 4.0
            zz_terms[(i, j)] = zz_terms.get((i, j), 0.0) + coeff / 4.0

    paulis: List[Tuple[str, float]] = []
    if constant:
        paulis.append(("I" * n, constant))

    for i, coeff in enumerate(z_terms):
        if coeff:
            label = ["I"] * n
            label[n - 1 - i] = "Z"
            paulis.append(("".join(label), float(coeff)))

    for (i, j), coeff in zz_terms.items():
        if coeff:
            label = ["I"] * n
            label[n - 1 - i] = "Z"
            label[n - 1 - j] = "Z"
            paulis.append(("".join(label), float(coeff)))

    return SparsePauliOp.from_list(paulis or [("I" * n, 0.0)])


def solve_qubo_qaoa_statevector(
    problem: QUBOProblem,
    layers: int = 1,
    maxiter: int = 80,
    top_k: int = 10,
    seed: Optional[int] = None,
) -> List[QUBOSolution]:
    """Run a compact Qiskit statevector QAOA experiment for a QUBO.

    This solver is deliberately sized for near-term demonstrations and local
    simulation. It is appropriate for Braket-scale toy instances, not utility-
    scale optimization.
    """

    if problem.num_variables > 16:
        raise ValueError("statevector QAOA is limited to 16 variables by default")

    try:
        from qiskit import QuantumCircuit
        from qiskit.circuit import ParameterVector
        from qiskit.quantum_info import Statevector
        from scipy.optimize import minimize
    except ImportError as exc:
        raise ImportError("qiskit and scipy are required for statevector QAOA") from exc

    rng = np.random.default_rng(seed)
    n = problem.num_variables
    bit_matrix = make_bit_matrix(n)
    energies = problem.energies(bit_matrix)
    gammas = ParameterVector("gamma", layers)
    betas = ParameterVector("beta", layers)

    def build_circuit() -> QuantumCircuit:
        circuit = QuantumCircuit(n)
        circuit.h(range(n))
        for layer in range(layers):
            for i, coeff in enumerate(problem.linear):
                if coeff:
                    circuit.rz(-gammas[layer] * coeff, i)
            for i in range(n):
                for j in range(i + 1, n):
                    coeff = float(problem.quadratic[i, j])
                    if coeff == 0.0:
                        continue
                    circuit.rz(-gammas[layer] * coeff / 2.0, i)
                    circuit.rz(-gammas[layer] * coeff / 2.0, j)
                    circuit.cx(i, j)
                    circuit.rz(gammas[layer] * coeff / 2.0, j)
                    circuit.cx(i, j)
            for i in range(n):
                circuit.rx(2.0 * betas[layer], i)
        return circuit

    circuit = build_circuit()
    parameters = list(gammas) + list(betas)

    def probabilities(params: np.ndarray) -> np.ndarray:
        bound = circuit.assign_parameters({param: value for param, value in zip(parameters, params)})
        state = Statevector.from_instruction(bound)
        return np.asarray(state.probabilities(), dtype=float)

    def expectation(params: np.ndarray) -> float:
        probs = probabilities(params)
        return float(np.dot(probs, energies))

    initial = rng.uniform(0.0, np.pi, size=2 * layers)
    result = minimize(expectation, initial, method="COBYLA", options={"maxiter": maxiter})
    probs = probabilities(np.asarray(result.x, dtype=float))
    order = np.argsort(-probs, kind="stable")

    unique: List[QUBOSolution] = []
    seen: set[BitString] = set()
    for idx in order:
        bits = tuple(int(v) for v in bit_matrix[idx])
        if bits in seen:
            continue
        seen.add(bits)
        unique.append(
            QUBOSolution(
                bitstring=bits,
                energy=float(energies[idx]),
                solver="qaoa_statevector",
                probability=float(probs[idx]),
                samples=0,
                metadata={
                    "layers": layers,
                    "maxiter": maxiter,
                    "optimizer": "COBYLA",
                    "objective": float(result.fun),
                    "success": bool(result.success),
                },
            )
        )
        if len(unique) >= top_k:
            break

    return sorted(unique, key=lambda item: item.energy)


def _build_feasible_mixer_pairs(
    bit_matrix: np.ndarray,
    one_hot_groups: List[Tuple[int, ...]],
    *,
    one_hot_mixer: str = "complete",
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Build feasible-neighbor pairs for binary and one-hot mixers."""

    basis_index = {tuple(int(value) for value in row): idx for idx, row in enumerate(bit_matrix)}
    grouped_indices = {index for group in one_hot_groups for index in group}
    binary_indices = [index for index in range(bit_matrix.shape[1]) if index not in grouped_indices]

    binary_pairs: set[Tuple[int, int]] = set()
    one_hot_pairs: set[Tuple[int, int]] = set()

    for row_index, row in enumerate(bit_matrix):
        bits = np.asarray(row, dtype=np.int8)
        for index in binary_indices:
            trial = bits.copy()
            trial[index] = 1 - trial[index]
            neighbor = basis_index.get(tuple(int(value) for value in trial))
            if neighbor is not None and neighbor != row_index:
                binary_pairs.add(tuple(sorted((row_index, neighbor))))

        for group in one_hot_groups:
            selected_positions = [index for index in group if bits[index] == 1]
            if len(selected_positions) != 1:
                continue
            selected = selected_positions[0]
            if one_hot_mixer == "ring":
                position = group.index(selected)
                targets = [group[(position - 1) % len(group)], group[(position + 1) % len(group)]]
            elif one_hot_mixer == "complete":
                targets = [index for index in group if index != selected]
            else:
                raise ValueError("one_hot_mixer must be 'complete' or 'ring'")

            for target in targets:
                trial = bits.copy()
                trial[selected] = 0
                trial[target] = 1
                neighbor = basis_index.get(tuple(int(value) for value in trial))
                if neighbor is not None and neighbor != row_index:
                    one_hot_pairs.add(tuple(sorted((row_index, neighbor))))

    return sorted(binary_pairs), sorted(one_hot_pairs)


def _apply_pair_mixer(
    state: np.ndarray,
    pairs: Sequence[Tuple[int, int]],
    beta: float,
) -> np.ndarray:
    if not pairs:
        return state
    mixed = state.copy()
    c = np.cos(beta)
    s = -1j * np.sin(beta)
    for left, right in pairs:
        a = mixed[left]
        b = mixed[right]
        mixed[left] = c * a + s * b
        mixed[right] = s * a + c * b
    return mixed


def _initial_feasible_state(
    bit_matrix: np.ndarray,
    *,
    warm_start_bitstring: Optional[Sequence[int]] = None,
    warm_start_strength: float = 0.0,
) -> np.ndarray:
    if warm_start_bitstring is None or warm_start_strength <= 0.0:
        return np.full(bit_matrix.shape[0], 1.0 / np.sqrt(bit_matrix.shape[0]), dtype=np.complex128)

    warm = np.asarray(warm_start_bitstring, dtype=np.int8)
    if warm.shape != (bit_matrix.shape[1],):
        raise ValueError("warm_start_bitstring length must match QUBO variables")
    distances = np.sum(np.abs(bit_matrix - warm), axis=1)
    probabilities = np.exp(-float(warm_start_strength) * distances)
    total = float(np.sum(probabilities))
    if total <= 0.0:
        return np.full(bit_matrix.shape[0], 1.0 / np.sqrt(bit_matrix.shape[0]), dtype=np.complex128)
    probabilities /= total
    return np.sqrt(probabilities).astype(np.complex128)


def solve_constrained_qubo_qaoa_statevector(
    problem: QUBOProblem,
    one_hot_groups: Optional[Sequence[Sequence[int]] | Mapping[str, Sequence[int]]] = None,
    *,
    layers: int = 1,
    maxiter: int = 120,
    top_k: int = 10,
    seed: Optional[int] = None,
    max_states: int = 1_000_000,
    one_hot_mixer: str = "complete",
    mixer_beta_mode: str = "separate",
    warm_start_bitstring: Optional[Sequence[int]] = None,
    warm_start_strength: float = 0.0,
    restarts: int = 2,
) -> List[QUBOSolution]:
    """Run statevector QAOA directly in the feasible one-hot subspace.

    The phase separator is the QUBO cost Hamiltonian restricted to feasible
    states. The mixer applies Trotterized rotations between feasible neighbors:
    ordinary bit flips for unconstrained binary variables and XY-style moves
    within one-hot groups. This avoids spending probability mass on invalid
    one-hot assignments.
    """

    if layers < 1:
        raise ValueError("layers must be at least 1")
    if restarts < 1:
        raise ValueError("restarts must be at least 1")
    if mixer_beta_mode not in {"shared", "separate"}:
        raise ValueError("mixer_beta_mode must be 'shared' or 'separate'")

    try:
        from scipy.optimize import minimize
    except ImportError as exc:
        raise ImportError("scipy is required for constrained statevector QAOA") from exc

    rng = np.random.default_rng(seed)
    groups = _normalize_one_hot_groups(problem.num_variables, one_hot_groups)
    bit_matrix = make_constrained_bit_matrix(
        problem.num_variables,
        groups,
        max_states=max_states,
    )
    energies = problem.energies(bit_matrix)
    binary_pairs, one_hot_pairs = _build_feasible_mixer_pairs(
        bit_matrix,
        groups,
        one_hot_mixer=one_hot_mixer,
    )
    initial_state = _initial_feasible_state(
        bit_matrix,
        warm_start_bitstring=warm_start_bitstring,
        warm_start_strength=warm_start_strength,
    )

    params_per_layer = 2 if mixer_beta_mode == "shared" else 3

    def evolve(params: np.ndarray) -> np.ndarray:
        state = initial_state.copy()
        cursor = 0
        for _ in range(layers):
            gamma = params[cursor]
            cursor += 1
            if mixer_beta_mode == "shared":
                beta_binary = beta_one_hot = params[cursor]
                cursor += 1
            else:
                beta_binary = params[cursor]
                beta_one_hot = params[cursor + 1]
                cursor += 2

            state = state * np.exp(-1j * gamma * energies)
            state = _apply_pair_mixer(state, binary_pairs, beta_binary)
            state = _apply_pair_mixer(state, one_hot_pairs, beta_one_hot)
        norm = np.linalg.norm(state)
        return state / norm if norm else state

    def expectation(params: np.ndarray) -> float:
        state = evolve(params)
        probabilities = np.abs(state) ** 2
        return float(np.dot(probabilities, energies))

    best_result = None
    best_value = float("inf")
    best_params = None
    for _ in range(restarts):
        initial = rng.uniform(0.0, np.pi, size=params_per_layer * layers)
        result = minimize(expectation, initial, method="COBYLA", options={"maxiter": maxiter})
        value = float(result.fun)
        if value < best_value:
            best_value = value
            best_result = result
            best_params = np.asarray(result.x, dtype=float)

    if best_params is None or best_result is None:  # pragma: no cover - defensive
        raise RuntimeError("constrained QAOA optimizer did not produce a result")

    final_state = evolve(best_params)
    probabilities = np.abs(final_state) ** 2
    order = np.argsort(-probabilities, kind="stable")

    solutions: List[QUBOSolution] = []
    for idx in order[:top_k]:
        bits = tuple(int(value) for value in bit_matrix[idx])
        solutions.append(
            QUBOSolution(
                bitstring=bits,
                energy=float(energies[idx]),
                solver="constrained_qaoa_statevector",
                probability=float(probabilities[idx]),
                samples=0,
                metadata={
                    "layers": layers,
                    "maxiter": maxiter,
                    "optimizer": "COBYLA",
                    "objective": best_value,
                    "success": bool(best_result.success),
                    "basis_states": int(bit_matrix.shape[0]),
                    "binary_mixer_edges": int(len(binary_pairs)),
                    "one_hot_mixer_edges": int(len(one_hot_pairs)),
                    "one_hot_mixer": one_hot_mixer,
                    "mixer_beta_mode": mixer_beta_mode,
                    "warm_start": warm_start_bitstring is not None and warm_start_strength > 0.0,
                    "warm_start_strength": float(warm_start_strength),
                    "restarts": int(restarts),
                },
            )
        )

    return sorted(solutions, key=lambda item: item.energy)


def dedupe_solutions(solutions: Iterable[QUBOSolution]) -> List[QUBOSolution]:
    """Keep the lowest-energy result per bitstring across solvers."""

    best: Dict[BitString, QUBOSolution] = {}
    for solution in solutions:
        existing = best.get(solution.bitstring)
        if existing is None or solution.energy < existing.energy:
            best[solution.bitstring] = solution
    return sorted(best.values(), key=lambda item: item.energy)
