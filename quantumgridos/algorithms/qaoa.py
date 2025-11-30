"""
QAOA Implementation for Power System Optimization
Quantum Approximate Optimization Algorithm
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from dataclasses import dataclass
import networkx as nx
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
from qiskit_algorithms import QAOA as QiskitQAOA, SamplingVQE
from qiskit_algorithms.optimizers import COBYLA, SPSA, ADAM
from qiskit.primitives import StatevectorSampler as Sampler
try:
    from qiskit_aer import AerSimulator
except ImportError:
    AerSimulator = None
from qiskit.quantum_info import SparsePauliOp
import logging

logger = logging.getLogger(__name__)


@dataclass
class QAOAConfig:
    """QAOA configuration parameters"""

    layers: int = 3  # Number of QAOA layers (p parameter)
    optimizer: str = "COBYLA"
    max_iter: int = 100
    shots: int = 1024
    initial_point: Optional[List[float]] = None
    use_warm_start: bool = True
    convergence_threshold: float = 1e-6


class PowerSystemQAOA:
    """QAOA for power system optimization problems"""

    def __init__(self, config: QAOAConfig = None):
        self.config = config or QAOAConfig()
        self.backend = AerSimulator()
        self.sampler = Sampler()

        # Cache for warm starts
        self.parameter_cache = {}
        self.solution_cache = {}

    def create_maxcut_hamiltonian(self, graph: nx.Graph) -> SparsePauliOp:
        """Create MaxCut Hamiltonian for power network partitioning

        Args:
            graph: NetworkX graph representing power network

        Returns:
            Hamiltonian as SparsePauliOp
        """
        n_qubits = graph.number_of_nodes()
        
        # Create mapping from node IDs to qubit indices (0-indexed)
        node_to_qubit = {node: idx for idx, node in enumerate(sorted(graph.nodes()))}
        
        pauli_list = []

        # For each edge, add ZZ interaction
        for u, v in graph.edges():
            weight = graph[u][v].get("weight", 1.0)

            # Create Pauli string with Z on qubits u and v
            pauli_str = ["I"] * n_qubits
            pauli_str[node_to_qubit[u]] = "Z"
            pauli_str[node_to_qubit[v]] = "Z"

            # MaxCut: minimize agreement (maximize disagreement)
            pauli_list.append(("".join(pauli_str), weight / 2))

        # Add constant term
        total_weight = sum(graph[u][v].get("weight", 1.0) for u, v in graph.edges())
        pauli_list.append(("I" * n_qubits, -total_weight / 2))

        return SparsePauliOp.from_list(pauli_list)

    def create_unit_commitment_hamiltonian(
        self, generators: List[Dict], demand: float, penalty: float = 100
    ) -> SparsePauliOp:
        """Create Hamiltonian for unit commitment problem

        Args:
            generators: List of generator specifications
            demand: Total demand to meet
            penalty: Penalty for demand mismatch

        Returns:
            Hamiltonian encoding unit commitment problem
        """
        n_qubits = len(generators)
        pauli_list = []

        # Cost terms (linear)
        for i, gen in enumerate(generators):
            cost = gen.get("cost", 0)
            pauli_str = ["I"] * n_qubits
            pauli_str[i] = "Z"
            pauli_list.append(("".join(pauli_str), -cost / 2))
            pauli_list.append(("I" * n_qubits, cost / 2))

        # Demand constraint (quadratic penalty)
        # (sum(P_i * x_i) - D)^2 where x_i = (1-Z_i)/2

        # Linear terms from expansion
        for i, gen in enumerate(generators):
            power = gen.get("pmax", 0)
            coeff = power * (power - 2 * demand) * penalty / 4
            pauli_str = ["I"] * n_qubits
            pauli_str[i] = "Z"
            pauli_list.append(("".join(pauli_str), -coeff))

        # Quadratic terms
        for i, gen_i in enumerate(generators):
            for j, gen_j in enumerate(generators):
                if i < j:
                    power_i = gen_i.get("pmax", 0)
                    power_j = gen_j.get("pmax", 0)
                    coeff = power_i * power_j * penalty / 4

                    pauli_str = ["I"] * n_qubits
                    pauli_str[i] = "Z"
                    pauli_str[j] = "Z"
                    pauli_list.append(("".join(pauli_str), coeff))

        return SparsePauliOp.from_list(pauli_list)

    def build_qaoa_circuit(self, hamiltonian: SparsePauliOp, n_qubits: int) -> QuantumCircuit:
        """Build parameterized QAOA circuit

        Args:
            hamiltonian: Problem Hamiltonian
            n_qubits: Number of qubits

        Returns:
            Parameterized quantum circuit
        """
        # Create parameter vectors
        gammas = [Parameter(f"γ_{i}") for i in range(self.config.layers)]
        betas = [Parameter(f"β_{i}") for i in range(self.config.layers)]

        # Initialize circuit
        qreg = QuantumRegister(n_qubits, "q")
        creg = ClassicalRegister(n_qubits, "c")
        circuit = QuantumCircuit(qreg, creg)

        # Initial state: uniform superposition
        circuit.h(qreg)

        # QAOA layers
        for layer in range(self.config.layers):
            # Problem unitary (cost Hamiltonian)
            self._add_problem_unitary(circuit, hamiltonian, gammas[layer], n_qubits)

            # Mixer unitary (X rotations)
            for qubit in range(n_qubits):
                circuit.rx(2 * betas[layer], qubit)

        # Measurements
        circuit.measure(qreg, creg)

        return circuit

    def _add_problem_unitary(
        self, circuit: QuantumCircuit, hamiltonian: SparsePauliOp, gamma: Parameter, n_qubits: int
    ):
        """Add problem unitary exp(-i*gamma*H) to circuit"""

        for pauli_string, coeff in hamiltonian.to_list():
            if pauli_string == "I" * n_qubits:
                continue  # Skip identity

            # Find Z positions
            z_positions = [i for i, p in enumerate(pauli_string) if p == "Z"]

            if len(z_positions) == 1:
                # Single Z rotation
                circuit.rz(2 * gamma * coeff, z_positions[0])

            elif len(z_positions) == 2:
                # ZZ interaction
                q1, q2 = z_positions
                circuit.cx(q1, q2)
                circuit.rz(2 * gamma * coeff, q2)
                circuit.cx(q1, q2)

    def optimize_parameters(
        self,
        circuit: QuantumCircuit,
        hamiltonian: SparsePauliOp,
        initial_params: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, float]:
        """Optimize QAOA parameters

        Args:
            circuit: Parameterized QAOA circuit
            hamiltonian: Problem Hamiltonian
            initial_params: Initial parameter values

        Returns:
            Optimal parameters and minimum eigenvalue
        """
        # Select optimizer
        optimizer_map = {
            "COBYLA": COBYLA(maxiter=self.config.max_iter),
            "SPSA": SPSA(maxiter=self.config.max_iter),
            "ADAM": ADAM(maxiter=self.config.max_iter),
        }
        optimizer = optimizer_map.get(self.config.optimizer, COBYLA())

        # Initial point
        if initial_params is None:
            if self.config.use_warm_start and self.parameter_cache:
                # Use cached parameters from similar problem
                initial_params = self._get_warm_start_params(hamiltonian)
            else:
                # Random initialization
                initial_params = np.random.uniform(0, 2 * np.pi, 2 * self.config.layers)

        # Create VQE instance with custom ansatz (the QAOA circuit)
        # We use SamplingVQE to avoid QiskitQAOA's default ansatz which causes sparse warnings
        vqe = SamplingVQE(
            sampler=self.sampler,
            ansatz=circuit,
            optimizer=optimizer,
            initial_point=initial_params,
        )

        # Run optimization
        result = vqe.compute_minimum_eigenvalue(hamiltonian)

        # Cache results
        self._cache_results(hamiltonian, result.optimal_point, result.eigenvalue)

        return result.optimal_point, result.eigenvalue

    def solve_maxcut(self, power_network: nx.Graph, return_partition: bool = True) -> Dict:
        """Solve MaxCut problem for power network partitioning

        Args:
            power_network: Power network as graph
            return_partition: Whether to return actual partition

        Returns:
            Solution dictionary
        """
        start_time = time.time()

        # Create Hamiltonian
        hamiltonian = self.create_maxcut_hamiltonian(power_network)
        n_qubits = power_network.number_of_nodes()

        # Build circuit
        circuit = self.build_qaoa_circuit(hamiltonian, n_qubits)

        # Optimize
        optimal_params, min_eigenvalue = self.optimize_parameters(circuit, hamiltonian)

        # Get solution
        solution_counts = self._sample_optimized_circuit(circuit, optimal_params)

        # Extract best partition
        best_bitstring = max(solution_counts, key=solution_counts.get)

        result = {
            "eigenvalue": min_eigenvalue,
            "optimal_parameters": optimal_params.tolist(),
            "solution_counts": solution_counts,
            "best_solution": best_bitstring,
            "execution_time": time.time() - start_time,
        }

        if return_partition:
            # Convert bitstring to actual partition
            partition_1 = []
            partition_2 = []

            for i, bit in enumerate(best_bitstring):
                if bit == "0":
                    partition_1.append(i)
                else:
                    partition_2.append(i)

            result["partition"] = {
                "set_1": partition_1,
                "set_2": partition_2,
                "cut_value": self._calculate_cut_value(power_network, partition_1, partition_2),
            }

        return result

    def solve_unit_commitment(
        self, generators: List[Dict], demand: float, time_periods: int = 1
    ) -> Dict:
        """Solve unit commitment problem

        Args:
            generators: List of generator specifications
            demand: Demand to meet
            time_periods: Number of time periods (future extension)

        Returns:
            Solution with generator schedule
        """
        # Create Hamiltonian
        hamiltonian = self.create_unit_commitment_hamiltonian(generators, demand)
        n_qubits = len(generators)

        # Build and optimize circuit
        circuit = self.build_qaoa_circuit(hamiltonian, n_qubits)
        optimal_params, min_cost = self.optimize_parameters(circuit, hamiltonian)

        # Get solution
        solution_counts = self._sample_optimized_circuit(circuit, optimal_params)

        # Extract best solution
        best_bitstring = max(solution_counts, key=solution_counts.get)

        # Convert to generator schedule
        schedule = []
        total_output = 0
        total_cost = 0

        for i, (bit, gen) in enumerate(zip(best_bitstring, generators)):
            is_on = bit == "1"
            output = gen["pmax"] if is_on else 0
            cost = gen["cost"] if is_on else 0

            schedule.append(
                {"generator": gen["name"], "status": is_on, "output": output, "cost": cost}
            )

            total_output += output
            total_cost += cost

        return {
            "schedule": schedule,
            "total_output": total_output,
            "total_cost": total_cost,
            "demand": demand,
            "demand_met": abs(total_output - demand) < 0.01,
            "eigenvalue": min_cost,
            "solution_counts": solution_counts,
            "best_solution": best_bitstring,
        }

    def _sample_optimized_circuit(
        self, circuit: QuantumCircuit, params: np.ndarray
    ) -> Dict[str, int]:
        """Sample the optimized circuit"""
        # Bind parameters
        param_dict = {}
        param_names = [p.name for p in circuit.parameters]
        for name, value in zip(param_names, params):
            for p in circuit.parameters:
                if p.name == name:
                    param_dict[p] = value

        bound_circuit = circuit.assign_parameters(param_dict)

        # Run circuit
        job = self.backend.run(bound_circuit, shots=self.config.shots)
        counts = job.result().get_counts()

        return counts

    def _calculate_cut_value(
        self, graph: nx.Graph, partition_1: List[int], partition_2: List[int]
    ) -> float:
        """Calculate the value of a cut"""
        cut_value = 0
        for u, v in graph.edges():
            if (u in partition_1 and v in partition_2) or (u in partition_2 and v in partition_1):
                cut_value += graph[u][v].get("weight", 1.0)
        return cut_value

    def _get_warm_start_params(self, hamiltonian: SparsePauliOp) -> np.ndarray:
        """Get warm start parameters from cache"""
        # Simple strategy: use closest cached problem
        # In practice, could use more sophisticated similarity metrics

        if not self.parameter_cache:
            return np.random.uniform(0, 2 * np.pi, 2 * self.config.layers)

        # Use most recent cached parameters as warm start
        return list(self.parameter_cache.values())[-1]

    def _cache_results(self, hamiltonian: SparsePauliOp, params: np.ndarray, eigenvalue: float):
        """Cache optimization results for warm starts"""
        # Use hash of Hamiltonian as key (simplified)
        key = hash(str(hamiltonian.to_list()))
        self.parameter_cache[key] = params
        self.solution_cache[key] = eigenvalue

        # Limit cache size
        if len(self.parameter_cache) > 100:
            # Remove oldest entries
            oldest_key = list(self.parameter_cache.keys())[0]
            del self.parameter_cache[oldest_key]
            del self.solution_cache[oldest_key]


# Convenience functions
def solve_power_network_partitioning(
    network: nx.Graph, layers: int = 3, optimizer: str = "COBYLA"
) -> Dict:
    """Quick function to solve power network partitioning"""

    config = QAOAConfig(layers=layers, optimizer=optimizer)
    solver = PowerSystemQAOA(config)
    return solver.solve_maxcut(network)


def solve_generator_scheduling(generators: List[Dict], demand: float, **kwargs) -> Dict:
    """Quick function for unit commitment"""

    solver = PowerSystemQAOA()
    return solver.solve_unit_commitment(generators, demand)


import time  # Add at top of file with other imports
