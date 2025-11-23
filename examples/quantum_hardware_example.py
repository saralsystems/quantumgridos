"""
QuantumGridOS - Real Quantum Hardware Integration Example
Shows how to connect to IBM, Rigetti, IonQ, and AWS Braket
"""

import asyncio
import os
import numpy as np
from typing import Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import QuantumGridOS
from quantumgridos.core.quantum_interface import QuantumPowerInterface, PowerSystemData
from quantumgridos.algorithms.qaoa import PowerSystemQAOA, QAOAConfig
from quantumgridos.algorithms.vqe import PowerSystemVQE, VQEConfig
from quantumgridos.power_systems.network import PowerNetwork
from quantumgridos.backends.quantum_backends import (
    QuantumGridBackend,
    connect_to_ibm_quantum,
    connect_to_rigetti,
    connect_to_ionq,
    connect_to_aws_braket,
    auto_connect,
)


class QuantumHardwareInterface:
    """Extended interface for real quantum hardware"""

    def __init__(self, backend: QuantumGridBackend):
        self.backend = backend
        self.execution_history = []

    async def solve_with_hardware(self, problem_type: str, network: PowerNetwork) -> Dict:
        """Solve power system problem on real quantum hardware"""

        logger.info(f"Solving {problem_type} on {self.backend.provider} quantum hardware")

        if problem_type == "maxcut":
            return await self._solve_maxcut_hardware(network)
        elif problem_type == "unit_commitment":
            return await self._solve_uc_hardware(network)
        else:
            raise ValueError(f"Unknown problem type: {problem_type}")

    async def _solve_maxcut_hardware(self, network: PowerNetwork) -> Dict:
        """Solve MaxCut on real hardware"""

        # Create QAOA solver
        qaoa = PowerSystemQAOA(QAOAConfig(layers=2, shots=1024))

        # Build quantum circuit for MaxCut
        hamiltonian = qaoa.create_maxcut_hamiltonian(network.graph)
        n_qubits = network.graph.number_of_nodes()

        # Limit qubits for real hardware
        if n_qubits > 20:
            logger.warning(f"Network has {n_qubits} buses, truncating to 20 for hardware")
            n_qubits = 20

        circuit = qaoa.build_qaoa_circuit(hamiltonian, n_qubits)

        # Optimize circuit for specific backend
        optimized_circuit = self.backend.optimize_circuit(circuit)

        # Execute on quantum hardware
        result = await asyncio.to_thread(self.backend.execute_qaoa, optimized_circuit, shots=1024)

        # Store execution history
        self.execution_history.append(
            {"problem": "maxcut", "backend": self.backend.provider, "result": result}
        )

        return result


# Example 1: IBM Quantum
async def example_ibm_quantum():
    """Example using IBM Quantum hardware"""

    print("\n" + "=" * 60)
    print("Example: IBM Quantum Hardware")
    print("=" * 60)

    # Method 1: Environment variable
    # export IBM_QUANTUM_TOKEN='your_token_here'

    # Method 2: Direct token
    token = os.getenv("IBM_QUANTUM_TOKEN")
    if not token:
        print("Please set IBM_QUANTUM_TOKEN environment variable")
        print("Get your token from: https://quantum-computing.ibm.com/")
        return

    # Connect to IBM Quantum
    backend = QuantumGridBackend(
        provider="ibm",
        api_token=token,
        backend_name=None,  # Auto-select least busy
        hub="ibm-q",
        group="open",
        project="main",
        use_runtime=True,  # Use Qiskit Runtime for better performance
    )

    # Check backend status
    info = backend.get_status()
    print(f"Connected to: {info['backend_name']}")
    print(f"Number of qubits: {info.get('n_qubits', 'N/A')}")
    print(f"Pending jobs: {info.get('pending_jobs', 'N/A')}")

    # Create small network for testing
    network = PowerNetwork.from_ieee_case(14)

    # Solve on real quantum hardware
    interface = QuantumHardwareInterface(backend)
    result = await interface.solve_with_hardware("maxcut", network)

    print(f"\nQuantum execution results:")
    print(f"  Expectation value: {result.get('expectation_value', 'N/A')}")
    print(f"  Shots: {result.get('shots', 'N/A')}")
    print(f"  Success: {result.get('success', False)}")


# Example 2: Rigetti
async def example_rigetti():
    """Example using Rigetti quantum computer"""

    print("\n" + "=" * 60)
    print("Example: Rigetti Quantum Computer")
    print("=" * 60)

    # Set up Rigetti credentials
    api_key = os.getenv("QCS_API_KEY")
    if not api_key:
        print("Please set QCS_API_KEY environment variable")
        print("Get your key from: https://qcs.rigetti.com/")
        return

    # Connect to Rigetti
    backend = QuantumGridBackend(
        provider="rigetti", api_token=api_key, backend_name="Aspen-M-3"  # Latest Rigetti QPU
    )

    print(f"Connected to Rigetti: {backend.manager.backend}")

    # For Rigetti, we need to convert Qiskit circuits to PyQuil
    from pyquil import Program
    from pyquil.gates import H, CNOT, RZ

    # Create simple quantum program
    program = Program()
    program += H(0)
    program += CNOT(0, 1)
    program += RZ(np.pi / 4, 1)

    # Execute
    result = backend.manager.execute_circuit(program, shots=1000)
    print(f"Rigetti execution: {result['success']}")
    print(f"Sample results: {list(result['counts'].items())[:5]}")


# Example 3: IonQ
async def example_ionq():
    """Example using IonQ trapped ion quantum computer"""

    print("\n" + "=" * 60)
    print("Example: IonQ Quantum Computer")
    print("=" * 60)

    api_key = os.getenv("IONQ_API_KEY")
    if not api_key:
        print("Please set IONQ_API_KEY environment variable")
        print("Get your key from: https://cloud.ionq.com/")
        return

    # Connect to IonQ
    backend = QuantumGridBackend(
        provider="ionq",
        api_token=api_key,
        backend_name="ionq.qpu.harmony",  # or 'ionq.simulator', 'ionq.qpu.aria-1'
    )

    print(f"Connected to IonQ: {backend.manager.backend_name}")

    # IonQ uses Cirq circuits
    import cirq

    # Create simple circuit
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit([cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure([q0, q1], key="result")])

    # Execute
    result = backend.manager.execute_circuit(circuit, shots=100)
    print(f"IonQ execution: {result['success']}")
    print(f"Measurement results: {result['counts']}")


# Example 4: AWS Braket
async def example_aws_braket():
    """Example using AWS Braket quantum computers"""

    print("\n" + "=" * 60)
    print("Example: AWS Braket Quantum Computing")
    print("=" * 60)

    # AWS credentials should be configured via AWS CLI or environment variables
    # aws configure
    # or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

    # Connect to AWS Braket
    backend = QuantumGridBackend(
        provider="braket",
        backend_name="IonQ",  # Options: 'IonQ', 'Rigetti', 'Oxford'
        region="us-east-1",
    )

    print(f"Connected to AWS Braket: {backend.manager.backend}")

    # Create Braket circuit
    from braket.circuits import Circuit

    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)

    # Execute
    result = backend.manager.execute_circuit(circuit, shots=100)
    print(f"AWS Braket execution: {result['success']}")
    print(f"Results: {result['counts']}")


# Example 5: Integrated Power System Optimization
async def example_integrated_optimization():
    """Complete example: Power system optimization on quantum hardware"""

    print("\n" + "=" * 60)
    print("Example: Integrated Power System Quantum Optimization")
    print("=" * 60)

    # Auto-detect best available backend
    backend = auto_connect()
    print(f"Using backend: {backend.provider}")

    # Create modified QAOA that uses real backend
    class HardwareQAOA(PowerSystemQAOA):
        def __init__(self, config: QAOAConfig, hardware_backend: QuantumGridBackend):
            super().__init__(config)
            self.hardware_backend = hardware_backend

        def _sample_optimized_circuit(self, circuit, params):
            """Override to use real quantum hardware"""

            # Bind parameters
            param_dict = {}
            param_names = [p.name for p in circuit.parameters]
            for name, value in zip(param_names, params):
                for p in circuit.parameters:
                    if p.name == name:
                        param_dict[p] = value

            bound_circuit = circuit.bind_parameters(param_dict)

            # Optimize for hardware
            optimized = self.hardware_backend.optimize_circuit(bound_circuit)

            # Execute on hardware
            result = self.hardware_backend.manager.execute_circuit(
                optimized, shots=self.config.shots
            )

            return result.get("counts", {})

    # Create network
    network = PowerNetwork.from_ieee_case(14)

    # Setup hardware-aware QAOA
    config = QAOAConfig(layers=2, shots=512)
    hardware_qaoa = HardwareQAOA(config, backend)

    # Solve MaxCut
    print("\nSolving network partitioning on quantum hardware...")
    result = hardware_qaoa.solve_maxcut(network.graph)

    print(f"\nResults:")
    print(f"  Backend: {backend.provider}")
    print(f"  Eigenvalue: {result['eigenvalue']:.4f}")
    print(f"  Best partition: {result['best_solution']}")
    print(f"  Execution time: {result['execution_time']:.2f}s")


# Example 6: Hybrid Classical-Quantum with Real Hardware
async def example_hybrid_optimization():
    """Hybrid optimization using quantum hardware for hard subproblems"""

    print("\n" + "=" * 60)
    print("Example: Hybrid Classical-Quantum Optimization")
    print("=" * 60)

    # Connect to quantum backend
    backend = auto_connect()

    class HybridOptimizer:
        def __init__(self, quantum_backend: QuantumGridBackend):
            self.quantum_backend = quantum_backend
            self.classical_solver = None  # Could use Gurobi, CPLEX, etc.

        async def solve_unit_commitment(self, generators, demand):
            """Hybrid UC: Classical for commitment, Quantum for dispatch"""

            # Step 1: Use quantum for combinatorial commitment decision
            print("Step 1: Quantum solver for unit commitment...")

            # Create small QUBO for unit commitment
            n_gens = min(len(generators), 5)  # Limit for hardware

            # Build quantum circuit (simplified)
            from qiskit import QuantumCircuit

            qc = QuantumCircuit(n_gens)

            # Apply Hadamard for superposition
            for i in range(n_gens):
                qc.h(i)

            # Add problem-specific gates (simplified)
            qc.measure_all()

            # Execute on quantum hardware
            result = self.quantum_backend.manager.execute_circuit(qc, shots=100)

            # Get best commitment from quantum results
            best_bitstring = max(result["counts"], key=result["counts"].get)
            commitment = [int(bit) for bit in best_bitstring]

            print(f"  Quantum commitment: {commitment}")

            # Step 2: Classical optimization for dispatch
            print("Step 2: Classical solver for economic dispatch...")

            total_output = 0
            dispatch = []

            for i, (gen, commit) in enumerate(zip(generators[:n_gens], commitment)):
                if commit:
                    # Simple proportional dispatch
                    output = min(
                        gen["pmax"],
                        demand
                        * gen["pmax"]
                        / sum(g["pmax"] for g, c in zip(generators[:n_gens], commitment) if c),
                    )
                    total_output += output
                    dispatch.append(output)
                else:
                    dispatch.append(0)

            print(f"  Classical dispatch: {dispatch}")

            return {
                "commitment": commitment,
                "dispatch": dispatch,
                "total_output": total_output,
                "quantum_backend": self.quantum_backend.provider,
            }

    # Define generators
    generators = [
        {"name": "Gen1", "pmax": 100, "cost": 20},
        {"name": "Gen2", "pmax": 150, "cost": 25},
        {"name": "Gen3", "pmax": 200, "cost": 30},
        {"name": "Gen4", "pmax": 80, "cost": 35},
        {"name": "Gen5", "pmax": 120, "cost": 15},
    ]

    demand = 350  # MW

    # Solve with hybrid optimizer
    hybrid = HybridOptimizer(backend)
    result = await hybrid.solve_unit_commitment(generators, demand)

    print(f"\nHybrid Optimization Results:")
    print(f"  Quantum backend: {result['quantum_backend']}")
    print(f"  Commitment: {result['commitment']}")
    print(f"  Dispatch: {result['dispatch']}")
    print(f"  Total output: {result['total_output']:.1f} MW")


# Example 7: Benchmarking Multiple Backends
async def example_benchmark_backends():
    """Benchmark same problem across different quantum backends"""

    print("\n" + "=" * 60)
    print("Example: Benchmarking Across Quantum Backends")
    print("=" * 60)

    # Define simple test problem
    from qiskit import QuantumCircuit

    def create_test_circuit(n_qubits=3):
        qc = QuantumCircuit(n_qubits)
        qc.h(0)
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
        qc.measure_all()
        return qc

    circuit = create_test_circuit(3)

    # Test backends
    backends_to_test = []

    # Add available backends
    if os.getenv("IBM_QUANTUM_TOKEN"):
        backends_to_test.append(("ibm", connect_to_ibm_quantum()))

    if os.getenv("IONQ_API_KEY"):
        backends_to_test.append(("ionq", connect_to_ionq()))

    # Always add simulator
    backends_to_test.append(("simulator", QuantumGridBackend("simulator")))

    print(f"Testing on {len(backends_to_test)} backends\n")

    results = []
    for name, backend in backends_to_test:
        print(f"Running on {name}...")

        import time

        start = time.time()

        try:
            result = backend.manager.execute_circuit(circuit, shots=100)
            elapsed = time.time() - start

            results.append(
                {
                    "backend": name,
                    "success": result["success"],
                    "time": elapsed,
                    "counts": result["counts"],
                }
            )

            print(f"  Success: {result['success']}")
            print(f"  Time: {elapsed:.2f}s")

        except Exception as e:
            print(f"  Failed: {e}")

    # Compare results
    print("\n" + "-" * 40)
    print("Benchmark Summary:")
    print("-" * 40)

    for r in results:
        print(f"{r['backend']:10s}: {r['time']:6.2f}s")


async def main():
    """Run all examples"""

    print("\n" + "=" * 60)
    print("   QuantumGridOS - Real Quantum Hardware Integration")
    print("=" * 60)

    # Check available credentials
    available = []
    if os.getenv("IBM_QUANTUM_TOKEN"):
        available.append("IBM")
    if os.getenv("IONQ_API_KEY"):
        available.append("IonQ")
    if os.getenv("QCS_API_KEY"):
        available.append("Rigetti")
    if os.getenv("AWS_ACCESS_KEY_ID"):
        available.append("AWS Braket")

    print(
        f"\nDetected quantum credentials for: {', '.join(available) if available else 'None (using simulator)'}"
    )

    # Run examples based on available backends
    if "IBM" in available:
        await example_ibm_quantum()

    await example_integrated_optimization()
    await example_hybrid_optimization()

    if len(available) > 0:
        await example_benchmark_backends()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
