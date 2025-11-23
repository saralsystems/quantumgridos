"""
Quantum Backend Integration Module
Connect to real quantum computers: IBM, Rigetti, IonQ, AWS Braket
"""

import os
import logging
from typing import Dict, Optional, Any, Union, List
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Quantum provider imports
try:
    from qiskit import IBMQ, QuantumCircuit, execute
    from qiskit.providers.ibmq import IBMQBackend
    from qiskit_ibm_runtime import QiskitRuntimeService, Sampler, Estimator

    HAS_IBM = True
except ImportError:
    HAS_IBM = False
    logging.warning("IBM Quantum not installed. Install with: pip install qiskit-ibm-runtime")

try:
    from pyquil import get_qc, Program
    from pyquil.gates import H, CNOT, RZ, RX
    from pyquil.api import QVMConnection

    HAS_RIGETTI = True
except ImportError:
    HAS_RIGETTI = False
    logging.warning("Rigetti not installed. Install with: pip install pyquil")

try:
    from braket.aws import AwsDevice
    from braket.circuits import Circuit as BraketCircuit
    from braket.devices import LocalSimulator

    HAS_BRAKET = True
except ImportError:
    HAS_BRAKET = False
    logging.warning("AWS Braket not installed. Install with: pip install amazon-braket-sdk")

try:
    import cirq
    from cirq.contrib.ionq import Service as IonQService

    HAS_IONQ = True
except ImportError:
    HAS_IONQ = False
    logging.warning("IonQ (via Cirq) not installed. Install with: pip install cirq-ionq")

logger = logging.getLogger(__name__)


class QuantumProvider(Enum):
    """Available quantum hardware providers"""

    SIMULATOR = "simulator"
    IBM = "ibm"
    RIGETTI = "rigetti"
    IONQ = "ionq"
    BRAKET = "braket"
    QUANTINUUM = "quantinuum"


@dataclass
class QuantumBackendConfig:
    """Configuration for quantum backend"""

    provider: QuantumProvider
    backend_name: Optional[str] = None
    shots: int = 1024
    optimization_level: int = 1

    # Credentials
    api_token: Optional[str] = None
    api_url: Optional[str] = None

    # Provider-specific
    hub: Optional[str] = None  # IBM
    group: Optional[str] = None  # IBM
    project: Optional[str] = None  # IBM
    region: Optional[str] = None  # AWS

    # Runtime options
    use_runtime: bool = True  # Use IBM Runtime if available
    resilience_level: int = 1  # Error mitigation level


class QuantumBackendManager:
    """Manages connections to quantum hardware providers"""

    def __init__(self, config: QuantumBackendConfig):
        self.config = config
        self.backend = None
        self.provider_session = None

        # Initialize based on provider
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the quantum backend based on provider"""

        if self.config.provider == QuantumProvider.IBM:
            self._init_ibm()
        elif self.config.provider == QuantumProvider.RIGETTI:
            self._init_rigetti()
        elif self.config.provider == QuantumProvider.IONQ:
            self._init_ionq()
        elif self.config.provider == QuantumProvider.BRAKET:
            self._init_braket()
        else:
            self._init_simulator()

    def _init_ibm(self):
        """Initialize IBM Quantum backend"""
        if not HAS_IBM:
            raise ImportError("IBM Quantum libraries not installed")

        # Get credentials from config or environment
        token = self.config.api_token or os.getenv("IBM_QUANTUM_TOKEN")
        if not token:
            raise ValueError("IBM Quantum token required. Set IBM_QUANTUM_TOKEN or pass api_token")

        if self.config.use_runtime:
            # Use Qiskit Runtime for better performance
            self.provider_session = QiskitRuntimeService(
                channel="ibm_quantum",
                token=token,
                instance=(
                    f"{self.config.hub}/{self.config.group}/{self.config.project}"
                    if all([self.config.hub, self.config.group, self.config.project])
                    else None
                ),
            )

            # Get backend
            backend_name = self.config.backend_name or "ibmq_qasm_simulator"
            self.backend = self.provider_session.get_backend(backend_name)

            logger.info(f"Connected to IBM Quantum Runtime: {backend_name}")
            logger.info(f"Backend config: {self.backend.configuration().n_qubits} qubits")

        else:
            # Use standard IBMQ
            IBMQ.save_account(token, overwrite=True)
            provider = IBMQ.load_account()

            if self.config.hub and self.config.group and self.config.project:
                provider = IBMQ.get_provider(
                    hub=self.config.hub, group=self.config.group, project=self.config.project
                )

            # Get least busy backend if not specified
            if not self.config.backend_name:
                from qiskit.providers.ibmq import least_busy

                backends = provider.backends(
                    filters=lambda x: x.configuration().n_qubits >= 5
                    and not x.configuration().simulator
                    and x.status().operational
                )
                self.backend = least_busy(backends)
                logger.info(f"Selected least busy backend: {self.backend.name()}")
            else:
                self.backend = provider.get_backend(self.config.backend_name)
                logger.info(f"Connected to IBM backend: {self.config.backend_name}")

    def _init_rigetti(self):
        """Initialize Rigetti quantum computer"""
        if not HAS_RIGETTI:
            raise ImportError("PyQuil not installed")

        # Get Rigetti API key
        api_key = self.config.api_token or os.getenv("QCS_API_KEY")
        if api_key:
            os.environ["QCS_API_KEY"] = api_key

        # Connect to quantum computer or QVM
        backend_name = self.config.backend_name or "Aspen-M-3"  # Latest Rigetti QPU

        try:
            # Try to connect to real QPU
            self.backend = get_qc(backend_name)
            logger.info(f"Connected to Rigetti QPU: {backend_name}")
        except Exception as e:
            # Fall back to QVM (Quantum Virtual Machine)
            logger.warning(f"Could not connect to {backend_name}: {e}")
            self.backend = get_qc("9q-qvm")  # 9-qubit simulator
            logger.info("Using Rigetti QVM simulator")

    def _init_ionq(self):
        """Initialize IonQ quantum computer"""
        if not HAS_IONQ:
            raise ImportError("Cirq-IonQ not installed")

        api_key = self.config.api_token or os.getenv("IONQ_API_KEY")
        if not api_key:
            raise ValueError("IonQ API key required. Set IONQ_API_KEY or pass api_token")

        # Create IonQ service
        self.provider_session = IonQService(api_key=api_key)

        # Get backend (device)
        backend_name = self.config.backend_name or "ionq.simulator"
        # Options: 'ionq.simulator', 'ionq.qpu', 'ionq.qpu.harmony', 'ionq.qpu.aria-1'

        self.backend = self.provider_session
        self.backend_name = backend_name
        logger.info(f"Connected to IonQ: {backend_name}")

    def _init_braket(self):
        """Initialize AWS Braket"""
        if not HAS_BRAKET:
            raise ImportError("Amazon Braket SDK not installed")

        # Set AWS credentials if provided
        if self.config.api_token:
            os.environ["AWS_ACCESS_KEY_ID"] = self.config.api_token.split(":")[0]
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.config.api_token.split(":")[1]

        if self.config.region:
            os.environ["AWS_DEFAULT_REGION"] = self.config.region

        # Get device
        if self.config.backend_name:
            # Real quantum devices: 'IonQ', 'Rigetti', 'Oxford', 'QuEra'
            device_arn = f"arn:aws:braket:::{self.config.backend_name}"
            self.backend = AwsDevice(device_arn)
            logger.info(f"Connected to AWS Braket device: {self.config.backend_name}")
        else:
            # Use local simulator
            self.backend = LocalSimulator()
            logger.info("Using AWS Braket local simulator")

    def _init_simulator(self):
        """Initialize local simulator"""
        if HAS_IBM:
            from qiskit import Aer

            self.backend = Aer.get_backend("aer_simulator")
            logger.info("Using Qiskit Aer simulator")
        else:
            logger.warning("No quantum libraries installed, using mock backend")
            self.backend = MockQuantumBackend()

    def execute_circuit(self, circuit: Any, **kwargs) -> Dict:
        """Execute quantum circuit on backend

        Args:
            circuit: Quantum circuit (format depends on provider)
            **kwargs: Additional execution parameters

        Returns:
            Execution results dictionary
        """

        if self.config.provider == QuantumProvider.IBM:
            return self._execute_ibm(circuit, **kwargs)
        elif self.config.provider == QuantumProvider.RIGETTI:
            return self._execute_rigetti(circuit, **kwargs)
        elif self.config.provider == QuantumProvider.IONQ:
            return self._execute_ionq(circuit, **kwargs)
        elif self.config.provider == QuantumProvider.BRAKET:
            return self._execute_braket(circuit, **kwargs)
        else:
            return self._execute_simulator(circuit, **kwargs)

    def _execute_ibm(self, circuit: QuantumCircuit, **kwargs) -> Dict:
        """Execute on IBM Quantum"""

        shots = kwargs.get("shots", self.config.shots)

        if self.config.use_runtime and self.provider_session:
            # Use Runtime Sampler for better performance
            with self.provider_session.get_backend(self.backend.name).open_session() as session:
                sampler = Sampler(
                    session=session,
                    options={"shots": shots, "resilience_level": self.config.resilience_level},
                )

                job = sampler.run(circuit)
                result = job.result()

                # Convert to standard format
                counts = {}
                for outcome, prob in enumerate(result.quasi_dists[0]):
                    if prob > 0:
                        bitstring = format(outcome, f"0{circuit.num_qubits}b")
                        counts[bitstring] = int(prob * shots)

                return {
                    "counts": counts,
                    "shots": shots,
                    "backend": self.backend.name,
                    "success": True,
                }
        else:
            # Standard execution
            job = execute(
                circuit,
                self.backend,
                shots=shots,
                optimization_level=self.config.optimization_level,
            )
            result = job.result()

            return {
                "counts": result.get_counts(),
                "shots": shots,
                "backend": self.backend.name(),
                "success": result.success,
            }

    def _execute_rigetti(self, program: Program, **kwargs) -> Dict:
        """Execute on Rigetti"""

        shots = kwargs.get("shots", self.config.shots)

        # Compile and run
        executable = self.backend.compiler.native_quil_to_executable(program)
        bitstring_results = self.backend.run(executable, shots=shots)

        # Convert to counts format
        counts = {}
        for bitstring in bitstring_results:
            key = "".join(str(bit) for bit in bitstring)
            counts[key] = counts.get(key, 0) + 1

        return {"counts": counts, "shots": shots, "backend": str(self.backend), "success": True}

    def _execute_ionq(self, circuit: cirq.Circuit, **kwargs) -> Dict:
        """Execute on IonQ"""

        shots = kwargs.get("shots", self.config.shots)

        # Run circuit
        result = self.provider_session.run(circuit=circuit, target=self.backend_name, shots=shots)

        # Get results
        counts = dict(result.histogram())

        return {"counts": counts, "shots": shots, "backend": self.backend_name, "success": True}

    def _execute_braket(self, circuit: BraketCircuit, **kwargs) -> Dict:
        """Execute on AWS Braket"""

        shots = kwargs.get("shots", self.config.shots)

        # Run circuit
        task = self.backend.run(circuit, shots=shots)
        result = task.result()

        # Get measurement counts
        counts = dict(result.measurement_counts)

        return {"counts": counts, "shots": shots, "backend": str(self.backend), "success": True}

    def _execute_simulator(self, circuit: Any, **kwargs) -> Dict:
        """Execute on simulator"""

        if HAS_IBM and isinstance(circuit, QuantumCircuit):
            return self._execute_ibm(circuit, **kwargs)
        else:
            # Mock execution
            return self.backend.execute(circuit, **kwargs)

    def get_backend_info(self) -> Dict:
        """Get information about the backend"""

        info = {
            "provider": self.config.provider.value,
            "backend_name": self.config.backend_name,
        }

        if self.config.provider == QuantumProvider.IBM and self.backend:
            config = self.backend.configuration()
            info.update(
                {
                    "n_qubits": config.n_qubits,
                    "basis_gates": config.basis_gates,
                    "coupling_map": config.coupling_map,
                    "operational": self.backend.status().operational,
                    "pending_jobs": self.backend.status().pending_jobs,
                }
            )

        return info


class MockQuantumBackend:
    """Mock backend for testing without quantum libraries"""

    def execute(self, circuit, shots=1024, **kwargs):
        """Mock execution"""
        import random

        # Generate random results
        n_qubits = 5  # Assume 5 qubits
        counts = {}

        for _ in range(shots):
            bitstring = "".join(str(random.randint(0, 1)) for _ in range(n_qubits))
            counts[bitstring] = counts.get(bitstring, 0) + 1

        return {"counts": counts, "shots": shots, "backend": "mock", "success": True}


# Integration with QuantumGridOS
class QuantumGridBackend:
    """High-level interface for QuantumGridOS to use real quantum backends"""

    def __init__(self, provider: str = "simulator", **kwargs):
        """
        Initialize quantum backend for QuantumGridOS

        Args:
            provider: 'ibm', 'rigetti', 'ionq', 'braket', or 'simulator'
            **kwargs: Provider-specific configuration

        Examples:
            # IBM Quantum
            backend = QuantumGridBackend(
                provider='ibm',
                api_token='YOUR_IBM_TOKEN',
                backend_name='ibmq_manila',  # or None for least busy
                hub='ibm-q',
                group='open',
                project='main'
            )

            # Rigetti
            backend = QuantumGridBackend(
                provider='rigetti',
                api_token='YOUR_QCS_KEY',
                backend_name='Aspen-M-3'
            )

            # IonQ
            backend = QuantumGridBackend(
                provider='ionq',
                api_token='YOUR_IONQ_KEY',
                backend_name='ionq.qpu.harmony'
            )

            # AWS Braket
            backend = QuantumGridBackend(
                provider='braket',
                backend_name='IonQ',
                region='us-east-1'
            )
        """

        # Map string to enum
        provider_map = {
            "simulator": QuantumProvider.SIMULATOR,
            "ibm": QuantumProvider.IBM,
            "rigetti": QuantumProvider.RIGETTI,
            "ionq": QuantumProvider.IONQ,
            "braket": QuantumProvider.BRAKET,
        }

        provider_enum = provider_map.get(provider.lower(), QuantumProvider.SIMULATOR)

        # Create config
        config = QuantumBackendConfig(provider=provider_enum, **kwargs)

        # Initialize backend manager
        self.manager = QuantumBackendManager(config)
        self.provider = provider

    def execute_qaoa(self, circuit: Any, shots: int = 1024) -> Dict:
        """Execute QAOA circuit on quantum backend"""

        result = self.manager.execute_circuit(circuit, shots=shots)

        # Add QAOA-specific processing if needed
        if "counts" in result:
            # Calculate expectation value
            total_counts = sum(result["counts"].values())
            expectation = 0

            for bitstring, count in result["counts"].items():
                # Simple expectation calculation (customize based on problem)
                value = sum(int(bit) for bit in bitstring) - len(bitstring) / 2
                expectation += value * count / total_counts

            result["expectation_value"] = expectation

        return result

    def execute_vqe(self, circuit: Any, observable: Any = None, shots: int = 1024) -> Dict:
        """Execute VQE circuit on quantum backend"""

        result = self.manager.execute_circuit(circuit, shots=shots)

        # Calculate expectation value if observable provided
        if observable and "counts" in result:
            # Simplified expectation calculation
            expectation = self._calculate_expectation(result["counts"], observable)
            result["expectation_value"] = expectation

        return result

    def _calculate_expectation(self, counts: Dict, observable: Any) -> float:
        """Calculate expectation value from counts"""

        total = sum(counts.values())
        expectation = 0

        for bitstring, count in counts.items():
            # Simplified - actual implementation would use observable
            eigenvalue = 1 if bitstring.count("0") % 2 == 0 else -1
            expectation += eigenvalue * count / total

        return expectation

    def get_status(self) -> Dict:
        """Get backend status"""
        return self.manager.get_backend_info()

    def optimize_circuit(self, circuit: Any) -> Any:
        """Optimize circuit for specific backend"""

        if self.provider == "ibm" and HAS_IBM:
            from qiskit.transpiler import preset_passmanagers

            # Get optimization pass manager
            pm = preset_passmanagers.generate_preset_pass_manager(
                backend=self.manager.backend, optimization_level=3
            )

            # Optimize circuit
            optimized = pm.run(circuit)

            logger.info(
                f"Circuit optimized: {circuit.num_qubits} -> {optimized.num_qubits} qubits, "
                f"{circuit.depth()} -> {optimized.depth()} depth"
            )

            return optimized

        return circuit


# Example usage functions
def connect_to_ibm_quantum(token: str = None) -> QuantumGridBackend:
    """Quick function to connect to IBM Quantum"""

    return QuantumGridBackend(
        provider="ibm",
        api_token=token or os.getenv("IBM_QUANTUM_TOKEN"),
        backend_name=None,  # Auto-select least busy
        use_runtime=True,
    )


def connect_to_rigetti(api_key: str = None, qpu_name: str = "Aspen-M-3") -> QuantumGridBackend:
    """Quick function to connect to Rigetti"""

    return QuantumGridBackend(
        provider="rigetti", api_token=api_key or os.getenv("QCS_API_KEY"), backend_name=qpu_name
    )


def connect_to_ionq(api_key: str = None, device: str = "ionq.qpu.harmony") -> QuantumGridBackend:
    """Quick function to connect to IonQ"""

    return QuantumGridBackend(
        provider="ionq", api_token=api_key or os.getenv("IONQ_API_KEY"), backend_name=device
    )


def connect_to_aws_braket(device: str = "IonQ", region: str = "us-east-1") -> QuantumGridBackend:
    """Quick function to connect to AWS Braket"""

    return QuantumGridBackend(provider="braket", backend_name=device, region=region)


# Auto-detect best available backend
def auto_connect() -> QuantumGridBackend:
    """Automatically connect to best available quantum backend"""

    # Check for credentials in order of preference
    if os.getenv("IBM_QUANTUM_TOKEN"):
        logger.info("IBM Quantum credentials detected")
        return connect_to_ibm_quantum()

    elif os.getenv("IONQ_API_KEY"):
        logger.info("IonQ credentials detected")
        return connect_to_ionq()

    elif os.getenv("QCS_API_KEY"):
        logger.info("Rigetti credentials detected")
        return connect_to_rigetti()

    elif os.getenv("AWS_ACCESS_KEY_ID"):
        logger.info("AWS credentials detected")
        return connect_to_aws_braket()

    else:
        logger.info("No quantum credentials found, using simulator")
        return QuantumGridBackend(provider="simulator")
