"""
VQE Implementation for Power System Optimization
Variational Quantum Eigensolver
"""

import numpy as np
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
import scipy.optimize as opt
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit_algorithms import VQE as QiskitVQE
from qiskit_algorithms.optimizers import SLSQP, L_BFGS_B, COBYLA
from qiskit.circuit.library import TwoLocal, RealAmplitudes, EfficientSU2
from qiskit_aer.primitives import Estimator
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator
import logging

logger = logging.getLogger(__name__)


@dataclass
class VQEConfig:
    """VQE configuration parameters"""

    ansatz: str = "RealAmplitudes"  # Type of variational ansatz
    optimizer: str = "SLSQP"
    max_iter: int = 200
    initial_point: Optional[np.ndarray] = None
    entanglement: str = "linear"  # full, linear, circular
    reps: int = 3  # Depth of ansatz
    convergence_threshold: float = 1e-7
    gradient_method: str = "finite_diff"  # finite_diff, parameter_shift


class PowerSystemVQE:
    """VQE for power system eigenvalue problems"""

    def __init__(self, config: VQEConfig = None):
        self.config = config or VQEConfig()
        self.backend = AerSimulator(method="statevector")
        self.estimator = Estimator()

        # Cache for optimization trajectory
        self.optimization_history = []
        self.parameter_history = []

    def create_opf_hamiltonian(
        self, buses: List[Dict], lines: List[Dict], generators: List[Dict]
    ) -> SparsePauliOp:
        """Create Hamiltonian for Optimal Power Flow problem

        Encodes AC-OPF as QUBO then to Ising Hamiltonian
        """
        n_buses = len(buses)
        n_gens = len(generators)
        n_qubits = n_buses + n_gens  # Simplified encoding

        pauli_list = []

        # Generation cost terms
        for i, gen in enumerate(generators):
            # Linear cost
            cost = gen.get("cost", 1.0)
            pauli_str = ["I"] * n_qubits
            pauli_str[i] = "Z"
            pauli_list.append(("".join(pauli_str), -cost / 2))

        # Power balance constraints (quadratic penalty)
        penalty = 1000  # Large penalty for constraint violation

        for bus_idx, bus in enumerate(buses):
            # Net power at bus should be zero
            # Simplified: encode as penalty term

            # Find generators at this bus
            gens_at_bus = [i for i, g in enumerate(generators) if g.get("bus", -1) == bus_idx]

            if gens_at_bus:
                # Add quadratic terms for power balance
                for gi in gens_at_bus:
                    for gj in gens_at_bus:
                        if gi < gj:
                            pauli_str = ["I"] * n_qubits
                            pauli_str[gi] = "Z"
                            pauli_str[gj] = "Z"
                            pauli_list.append(("".join(pauli_str), penalty / 4))

        # Line flow constraints (simplified)
        for line in lines:
            from_bus = line["from"]
            to_bus = line["to"]
            capacity = line.get("capacity", 100)

            # Add penalty for exceeding line capacity
            # Simplified encoding
            pauli_str = ["I"] * n_qubits
            if from_bus < n_qubits and to_bus < n_qubits:
                pauli_str[from_bus] = "Z"
                pauli_str[to_bus] = "Z"
                pauli_list.append(("".join(pauli_str), penalty / (4 * capacity)))

        return SparsePauliOp.from_list(pauli_list)

    def create_state_estimation_hamiltonian(
        self, measurements: np.ndarray, measurement_matrix: np.ndarray
    ) -> SparsePauliOp:
        """Create Hamiltonian for power system state estimation

        Minimize ||z - Hx||^2 where:
        - z: measurements
        - H: measurement matrix
        - x: state variables (encoded in qubits)
        """
        n_measurements = len(measurements)
        n_states = measurement_matrix.shape[1]
        n_qubits = int(np.ceil(np.log2(n_states)))

        if n_qubits > 20:  # Practical limit
            logger.warning(f"State estimation requires {n_qubits} qubits, truncating")
            n_qubits = 20

        pauli_list = []

        # Encode least squares objective as Ising
        # Simplified: use diagonal approximation

        for i in range(min(n_qubits, n_measurements)):
            # Linear terms from (Hz - z)^T(Hz - z)
            coeff = -2 * measurements[i] * measurement_matrix[i, i] if i < n_states else 0

            pauli_str = ["I"] * n_qubits
            pauli_str[i] = "Z"
            pauli_list.append(("".join(pauli_str), coeff / 4))

            # Quadratic terms (simplified)
            for j in range(i + 1, min(n_qubits, n_measurements)):
                if i < n_states and j < n_states:
                    coeff = measurement_matrix[i, i] * measurement_matrix[j, j]

                    pauli_str = ["I"] * n_qubits
                    pauli_str[i] = "Z"
                    pauli_str[j] = "Z"
                    pauli_list.append(("".join(pauli_str), coeff / 4))

        return SparsePauliOp.from_list(pauli_list)

    def build_ansatz(self, n_qubits: int) -> QuantumCircuit:
        """Build variational ansatz circuit

        Args:
            n_qubits: Number of qubits

        Returns:
            Parameterized quantum circuit
        """
        if self.config.ansatz == "RealAmplitudes":
            ansatz = RealAmplitudes(
                n_qubits, entanglement=self.config.entanglement, reps=self.config.reps
            )
        elif self.config.ansatz == "EfficientSU2":
            ansatz = EfficientSU2(
                n_qubits, entanglement=self.config.entanglement, reps=self.config.reps
            )
        elif self.config.ansatz == "TwoLocal":
            ansatz = TwoLocal(
                n_qubits,
                rotation_blocks=["ry", "rz"],
                entanglement_blocks="cz",
                entanglement=self.config.entanglement,
                reps=self.config.reps,
            )
        else:
            # Custom hardware-efficient ansatz
            ansatz = self._build_custom_ansatz(n_qubits)

        return ansatz

    def _build_custom_ansatz(self, n_qubits: int) -> QuantumCircuit:
        """Build custom hardware-efficient ansatz"""

        n_params = n_qubits * (self.config.reps + 1) * 2
        params = ParameterVector("θ", n_params)

        circuit = QuantumCircuit(n_qubits)
        param_idx = 0

        # Initial rotation layer
        for q in range(n_qubits):
            circuit.ry(params[param_idx], q)
            param_idx += 1
            circuit.rz(params[param_idx], q)
            param_idx += 1

        # Entangling layers
        for _ in range(self.config.reps):
            # Entangling gates
            if self.config.entanglement == "linear":
                for q in range(n_qubits - 1):
                    circuit.cx(q, q + 1)
            elif self.config.entanglement == "full":
                for q1 in range(n_qubits):
                    for q2 in range(q1 + 1, n_qubits):
                        circuit.cx(q1, q2)
            else:  # circular
                for q in range(n_qubits):
                    circuit.cx(q, (q + 1) % n_qubits)

            # Rotation layer
            for q in range(n_qubits):
                circuit.ry(params[param_idx], q)
                param_idx += 1
                circuit.rz(params[param_idx], q)
                param_idx += 1

        return circuit

    def optimize(
        self,
        hamiltonian: SparsePauliOp,
        ansatz: QuantumCircuit,
        initial_point: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, float, Dict]:
        """Run VQE optimization

        Returns:
            Optimal parameters, minimum eigenvalue, and info dict
        """
        # Select optimizer
        optimizer_map = {
            "SLSQP": SLSQP(maxiter=self.config.max_iter),
            "L-BFGS-B": L_BFGS_B(maxiter=self.config.max_iter),
            "COBYLA": COBYLA(maxiter=self.config.max_iter),
        }
        optimizer = optimizer_map.get(self.config.optimizer, SLSQP())

        # Initial point
        if initial_point is None:
            n_params = ansatz.num_parameters
            initial_point = np.random.uniform(-np.pi, np.pi, n_params)

        # Reset history
        self.optimization_history = []
        self.parameter_history = []

        # Callback to track optimization
        def callback(eval_count, parameters, mean, std):
            self.optimization_history.append(mean)
            self.parameter_history.append(parameters.copy())

        # Create VQE instance
        vqe = QiskitVQE(
            estimator=self.estimator,
            ansatz=ansatz,
            optimizer=optimizer,
            initial_point=initial_point,
            callback=callback,
        )

        # Run VQE
        result = vqe.compute_minimum_eigenvalue(hamiltonian)

        info = {
            "iterations": len(self.optimization_history),
            "final_cost": result.eigenvalue,
            "optimal_parameters": result.optimal_point,
            "optimization_trajectory": self.optimization_history,
            "converged": len(self.optimization_history) < self.config.max_iter,
        }

        return result.optimal_point, result.eigenvalue, info

    def solve_opf(self, buses: List[Dict], lines: List[Dict], generators: List[Dict]) -> Dict:
        """Solve Optimal Power Flow problem using VQE

        Returns:
            Solution dictionary with generator dispatch
        """
        import time

        start_time = time.time()

        # Create Hamiltonian
        hamiltonian = self.create_opf_hamiltonian(buses, lines, generators)
        n_qubits = min(len(buses) + len(generators), 20)  # Practical limit

        # Build ansatz
        ansatz = self.build_ansatz(n_qubits)

        # Optimize
        opt_params, min_cost, info = self.optimize(hamiltonian, ansatz)

        # Sample optimized circuit to get solution
        optimized_circuit = ansatz.assign_parameters(opt_params)
        optimized_circuit.measure_all()

        job = self.backend.run(optimized_circuit, shots=1024)
        counts = job.result().get_counts()

        # Extract solution
        best_solution = max(counts, key=counts.get)

        # Decode solution to generator dispatch
        dispatch = []
        total_cost = 0

        for i, gen in enumerate(generators):
            if i < len(best_solution):
                is_on = best_solution[i] == "1"
                output = gen["pmax"] * 0.8 if is_on else gen["pmin"]  # Simplified
            else:
                output = gen["pmin"]

            cost = gen["cost"] * output
            dispatch.append(
                {"generator": gen.get("name", f"Gen_{i}"), "output": output, "cost": cost}
            )
            total_cost += cost

        return {
            "dispatch": dispatch,
            "total_cost": total_cost,
            "minimum_eigenvalue": min_cost,
            "solution_bitstring": best_solution,
            "optimization_info": info,
            "execution_time": time.time() - start_time,
        }

    def solve_state_estimation(
        self,
        measurements: np.ndarray,
        measurement_matrix: np.ndarray,
        measurement_covariance: Optional[np.ndarray] = None,
    ) -> Dict:
        """Solve power system state estimation using VQE

        Args:
            measurements: Measurement vector
            measurement_matrix: H matrix relating states to measurements
            measurement_covariance: Measurement error covariance (optional)

        Returns:
            Estimated state vector and statistics
        """
        # Create Hamiltonian
        hamiltonian = self.create_state_estimation_hamiltonian(measurements, measurement_matrix)

        n_states = measurement_matrix.shape[1]
        n_qubits = min(int(np.ceil(np.log2(n_states))), 20)

        # Build ansatz
        ansatz = self.build_ansatz(n_qubits)

        # Optimize
        opt_params, min_residual, info = self.optimize(hamiltonian, ansatz)

        # Extract state estimate
        optimized_circuit = ansatz.assign_parameters(opt_params)
        optimized_circuit.measure_all()

        job = self.backend.run(optimized_circuit, shots=2048)
        counts = job.result().get_counts()

        # Convert measurement outcomes to state estimates
        state_estimates = []
        probabilities = []

        for bitstring, count in counts.items():
            # Decode bitstring to continuous state values
            # Simplified: map to discrete levels
            state_vector = np.array([1.0 if bit == "1" else 0.0 for bit in bitstring[:n_states]])

            state_estimates.append(state_vector)
            probabilities.append(count / 2048)

        # Weighted average as final estimate
        final_estimate = np.zeros(n_states)
        for state, prob in zip(state_estimates, probabilities):
            final_estimate += state * prob

        # Calculate residuals
        residuals = measurements - measurement_matrix @ final_estimate

        return {
            "state_estimate": final_estimate,
            "residuals": residuals,
            "residual_norm": np.linalg.norm(residuals),
            "chi_squared": np.sum(residuals**2),
            "minimum_eigenvalue": min_residual,
            "optimization_info": info,
            "measurement_fit": {
                "measurements": measurements.tolist(),
                "fitted": (measurement_matrix @ final_estimate).tolist(),
            },
        }

    def adaptive_vqe(
        self, hamiltonian: SparsePauliOp, n_qubits: int, threshold: float = 0.01
    ) -> Dict:
        """Adaptive VQE that grows ansatz based on gradient"""

        # Start with shallow ansatz
        current_reps = 1
        best_energy = float("inf")

        results = []

        while current_reps <= 5:  # Max depth
            self.config.reps = current_reps
            ansatz = self.build_ansatz(n_qubits)

            # Use previous optimum as starting point if available
            if results:
                # Pad previous parameters for deeper ansatz
                prev_params = results[-1]["parameters"]
                n_new_params = ansatz.num_parameters
                initial_point = np.zeros(n_new_params)
                initial_point[: len(prev_params)] = prev_params
                initial_point[len(prev_params) :] = np.random.uniform(
                    -0.1, 0.1, n_new_params - len(prev_params)
                )
            else:
                initial_point = None

            # Optimize
            opt_params, energy, info = self.optimize(hamiltonian, ansatz, initial_point)

            results.append(
                {"depth": current_reps, "energy": energy, "parameters": opt_params, "info": info}
            )

            # Check for convergence
            if best_energy - energy < threshold:
                break

            best_energy = energy
            current_reps += 1

        return {
            "final_energy": best_energy,
            "final_depth": current_reps,
            "optimization_trajectory": results,
            "converged": (best_energy - energy < threshold),
        }


# Convenience functions
def solve_opf_quantum(
    buses: List[Dict], lines: List[Dict], generators: List[Dict], **kwargs
) -> Dict:
    """Quick function to solve OPF with VQE"""

    solver = PowerSystemVQE()
    return solver.solve_opf(buses, lines, generators)


def estimate_power_state(measurements: np.ndarray, H_matrix: np.ndarray, **kwargs) -> Dict:
    """Quick function for state estimation"""

    solver = PowerSystemVQE()
    return solver.solve_state_estimation(measurements, H_matrix)
