# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**QuantumGridOS** is a high-performance Python library for real-time integration between quantum computers and power systems. It enables solving power system optimization problems using quantum algorithms (QAOA, VQE) with minimal latency TCP/IP data exchange.

**Key capabilities:**
- Real-time TCP/IP streaming for power systems data (binary protocol with microsecond timestamps)
- Quantum algorithms for power optimization: QAOA for network partitioning, VQE for OPF, Grover's for search
- Power system problems: Unit Commitment, MaxCut, Optimal Power Flow, State Estimation
- Hardware-agnostic quantum backends: IBM Quantum, IonQ, Rigetti, local simulators
- Mathematical innovations: Power-flow preserving encoding, quantum eigenvalue analysis, multi-contingency analysis

**Tech stack:** Python 3.8+, Qiskit, numpy, networkx, pandapower, asyncio

## Development Setup

### Initial Setup

```bash
# Clone and install in development mode
git clone https://github.com/saralsystems/quantumgridos.git
cd quantumgridos

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e .[dev]

# Install optional dependencies
pip install -e .[visualization]  # For plotting
pip install -e .[hardware]       # For quantum hardware access
```

### Dependencies

**Core:**
- `qiskit` (>=0.43.0) - Quantum computing framework
- `qiskit-aer` (>=0.12.0) - Quantum simulator
- `qiskit-optimization` (>=0.5.0) - Optimization algorithms
- `numpy`, `scipy`, `pandas` - Scientific computing
- `networkx` (>=2.6.0) - Graph algorithms
- `pandapower` (>=2.10.0) - Power system analysis
- `asyncio-mqtt`, `aiofiles` - Async I/O
- `msgpack`, `protobuf` - Serialization

**Development:**
- `pytest`, `pytest-cov`, `pytest-asyncio` - Testing
- `black` (line-length=100) - Code formatting
- `flake8` - Linting
- `mypy` - Type checking
- `sphinx`, `sphinx-rtd-theme` - Documentation

## Common Commands

### Code Quality

```bash
# Format code with Black (required before commits)
black quantumgridos/
black examples/ demos/

# Check formatting without changes
black --check quantumgridos/

# Lint with flake8
flake8 quantumgridos/ --count --max-complexity=10 --max-line-length=127 --statistics

# Type checking (when configured)
mypy quantumgridos/
```

### Testing

```bash
# Run all tests (note: tests/ directory may not exist yet in early development)
pytest tests/

# Run tests with coverage report
pytest --cov=quantumgridos tests/ --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_qaoa.py -v

# Run tests with async support
pytest tests/ --asyncio-mode=auto

# Run benchmarks
python -m quantumgridos.benchmark
python quantum_vs_classical_benchmark.py
```

### Running Examples and Demos

```bash
# Quick demo of quantum algorithms
python quick_quantum_demo.py

# Complete example with TCP streaming
python examples/complete_example.py

# Run mathematical innovations demos
python demos/master_demo.py
python demos/demo1_kirchhoff_encoding.py
python demos/demo2_quantum_eigenvalue.py

# Start TCP server for testing
python examples/tcp_server.py
```

### Building and Publishing

```bash
# Build package distributions
python -m build

# Check package integrity
twine check dist/*

# Install locally from build
pip install dist/quantumgridos-0.1.0-py3-none-any.whl

# Build documentation
cd docs
make html  # Output in docs/_build/html/
```

### CLI Tools

The package provides CLI commands after installation:

```bash
# Main CLI (check quantumgridos/cli.py for actual implementation)
quantumgridos --help
qgo --help  # Alias
```

## Architecture

### Module Structure

```
quantumgridos/
├── __init__.py              # Public API exports
├── core/
│   └── quantum_interface.py # QuantumPowerInterface, TCPPowerStreamHandler, PowerSystemData
├── algorithms/
│   ├── qaoa.py             # PowerSystemQAOA, QAOAConfig, MaxCut Hamiltonian creation
│   └── vqe.py              # PowerSystemVQE, VQEConfig, OPF quantum solving
├── backends/
│   └── quantum_backends.py # Hardware abstraction for IBM/IonQ/Rigetti
├── power_systems/
│   ├── network.py          # PowerNetwork, Bus, Line, Generator dataclasses
│   └── optimizations.py    # MaxCutOptimizer, UnitCommitment, OptimalPowerFlow, StateEstimation
└── innovations/
    └── mathematical_innovations.py  # PowerFlowPreservingEncoding, NoiseAdaptiveGridQAOA
```

### Key Components

**1. TCP Streaming Layer (`core/quantum_interface.py`)**
- `PowerSystemData`: Dataclass with binary serialization (timestamp, bus voltages/angles, line flows, generator outputs)
- `TCPPowerStreamHandler`: Async TCP client with 64KB buffer, latency tracking, binary protocol
- `QuantumPowerInterface`: Main orchestrator connecting TCP streaming to quantum backends

**2. Quantum Algorithms (`algorithms/`)**
- `PowerSystemQAOA`: QAOA implementation with warm-start parameter caching, MaxCut and unit commitment Hamiltonian construction
- `PowerSystemVQE`: VQE for continuous optimization problems (OPF, state estimation)
- Both use parameterized circuits with optimizers (COBYLA, SPSA, ADAM)

**3. Power System Modeling (`power_systems/`)**
- `PowerNetwork`: NetworkX graph representation, Y-bus (admittance matrix) calculation
- IEEE test case loaders: `PowerNetwork.from_ieee_case(14|30|57|118|300)`
- Dataclasses: `Bus` (with bus_type: PQ/PV/Slack), `Line` (impedance, admittance), `Generator` (cost curves, ramp rates)

**4. Backend Abstraction (`backends/`)**
- Hardware-agnostic interface supporting Qiskit Aer (simulator), IBM Quantum, IonQ, Rigetti
- Automatic fallback to simulators when hardware unavailable

### Data Flow

```
Power System (SCADA) 
  → TCP/IP Stream (binary protocol)
    → PowerSystemData (deserialization)
      → Quantum Encoding (problem → Hamiltonian)
        → Quantum Circuit (QAOA/VQE)
          → Backend Execution (simulator/hardware)
            → Result Processing
              → TCP/IP Response (JSON)
                → Power System (control actions)
```

## Design Patterns and Conventions

### Async Programming

All I/O operations use `async`/`await`:

```python
async def process_stream():
    interface = qgo.QuantumPowerInterface(tcp_host='localhost', tcp_port=5000)
    await interface.start()
    
    async for data in interface.tcp_handler.stream():
        result = await interface.process_with_quantum(data, algorithm='qaoa')
        await interface.tcp_handler.send_result(result)
    
    await interface.stop()

# Run with
asyncio.run(process_stream())
```

### Quantum Circuit Construction

QAOA circuits use parameterized gates:

```python
# Typical pattern
hamiltonian = qaoa.create_maxcut_hamiltonian(network.graph)
circuit = qaoa.build_qaoa_circuit(hamiltonian, n_qubits)
optimal_params, energy = qaoa.optimize_parameters(circuit, hamiltonian)
```

### Power Network Units

- **Voltage**: per-unit (p.u.) relative to base voltage
- **Power**: MW (active), MVAr (reactive)
- **Impedance**: p.u. on system base
- **Angles**: radians (not degrees)

### Error Handling

- Always provide simulator fallback for quantum backends
- Handle TCP disconnections gracefully with reconnection logic
- Mock external dependencies (quantum hardware, SCADA systems) in tests

### Performance Tuning Parameters

Key parameters to adjust for performance vs. accuracy:

```python
# QAOA tuning
QAOAConfig(
    layers=3,           # More layers = better quality, slower
    shots=1024,         # More shots = better statistics, slower
    optimizer='COBYLA', # COBYLA (stable) vs SPSA (faster) vs ADAM
    use_warm_start=True # Reuse previous parameters
)

# TCP buffer sizing
TCPPowerStreamHandler(buffer_size=65536)  # 64KB default

# Data buffer for time sync
QuantumPowerInterface(buffer_size=100)  # Circular buffer size
```

## Code Style

### Python Standards

- **PEP 8** compliance enforced
- **Black** formatting with `line-length=100` (see pyproject.toml)
- **Type hints** required for all public API functions and class methods
- **Docstrings** in Google style for all public functions, classes, modules

Example:

```python
def calculate_quantum_metric(
    network: PowerNetwork,
    algorithm: str = "qaoa"
) -> float:
    """Calculate quantum optimization metric for a power network.
    
    Args:
        network: Power network instance with buses and lines
        algorithm: Quantum algorithm to use ('qaoa' or 'vqe')
    
    Returns:
        Optimization metric value (lower is better)
    
    Raises:
        ValueError: If algorithm is not supported
    """
    pass
```

### Import Organization

```python
# Standard library
import asyncio
import struct
from typing import Dict, Any, Optional

# Third-party
import numpy as np
from qiskit import QuantumCircuit

# Local
from quantumgridos.core.quantum_interface import PowerSystemData
```

### Naming Conventions

- Classes: `PascalCase` (e.g., `PowerSystemQAOA`)
- Functions/methods: `snake_case` (e.g., `create_maxcut_hamiltonian`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PORT`)
- Private: prefix with `_` (e.g., `_build_ybus`)

## Testing

### Test Structure

```bash
tests/
├── test_core/
│   ├── test_quantum_interface.py
│   └── test_tcp_handler.py
├── test_algorithms/
│   ├── test_qaoa.py
│   └── test_vqe.py
├── test_power_systems/
│   ├── test_network.py
│   └── test_optimizations.py
└── conftest.py  # Pytest fixtures
```

### Testing Patterns

```python
import pytest
import asyncio
from quantumgridos import PowerNetwork, MaxCutOptimizer

# Sync test
def test_maxcut_optimizer():
    """Test MaxCut optimizer with IEEE 14-bus."""
    network = PowerNetwork.from_ieee_case(14)
    optimizer = MaxCutOptimizer(network=network, algorithm='qaoa')
    
    result = optimizer.solve()
    
    assert result is not None
    assert 'partition' in result
    assert len(result['partition']) == 14

# Async test
@pytest.mark.asyncio
async def test_tcp_streaming():
    """Test TCP data streaming."""
    handler = TCPPowerStreamHandler('localhost', 5000)
    await handler.connect()
    
    data = await handler.receive_data()
    assert isinstance(data, PowerSystemData)
    
    await handler.disconnect()

# Mock quantum hardware
@pytest.fixture
def mock_backend(monkeypatch):
    """Mock quantum backend to avoid real hardware calls."""
    def mock_init(backend_name):
        from qiskit import Aer
        return Aer.get_backend('aer_simulator')
    
    monkeypatch.setattr(
        'quantumgridos.core.quantum_interface.QuantumPowerInterface._init_quantum_backend',
        mock_init
    )
```

### Coverage Goals

- Target >80% code coverage
- All public APIs must have tests
- Async code tested with `pytest-asyncio`
- Integration tests use Qiskit Aer simulator (no real hardware)

## Documentation

### Building Docs Locally

```bash
cd docs
pip install -r requirements.txt
make html
open _build/html/index.html  # macOS
```

### Documentation Structure

- **Getting Started**: Installation, quick start, first examples
- **API Reference**: Auto-generated from docstrings
- **Power Systems Tutorial**: IEEE cases, network modeling, Y-bus
- **Quantum Algorithms Guide**: QAOA, VQE, Hamiltonian construction
- **Performance Tuning**: Latency optimization, parameter selection

Documentation is automatically built on ReadTheDocs: https://quantumgridos.readthedocs.io

## Important Notes

### Contributor License Agreement (CLA)

**CRITICAL**: All contributors must sign a CLA before contributions can be merged.

- Individual contributors: See `CLA.md`
- Corporate contributors: See `CLA-CORPORATE.md`
- Email signed CLA to: contact@saralsystems.com

### Version Control

- Main branch: `main` (protected, requires PR)
- Development branch: `develop` (merge here first)
- Feature branches: `feature/feature-name`
- Bug fixes: `fix/bug-description`

### CI/CD

GitHub Actions runs on every PR:
- Multi-platform tests (Ubuntu, macOS, Windows)
- Python versions: 3.8, 3.9, 3.10, 3.11
- Linting (flake8), formatting (black), type checking
- Coverage reporting to Codecov

### IEEE Test Cases

Standard test cases are loaded with `PowerNetwork.from_ieee_case(N)`:
- **IEEE 14-bus**: Small system (14 buses, 20 lines, 5 generators)
- **IEEE 30-bus**: Medium system (30 buses, 41 lines, 6 generators)
- **IEEE 57-bus**: Larger system (57 buses, 80 lines)
- **IEEE 118-bus**: Large system for scalability testing

### Quantum Backend Selection

```python
# Simulator (default, fastest)
interface = qgo.QuantumPowerInterface(quantum_backend='qiskit_aer')

# IBM Quantum (requires account setup)
interface = qgo.QuantumPowerInterface(quantum_backend='ibmq')

# IonQ / Rigetti (requires API keys)
interface = qgo.QuantumPowerInterface(quantum_backend='ionq')
```

Always test with simulators first before using real quantum hardware (expensive, limited access).

### Performance Considerations

- TCP latency typically <1ms on localhost
- QAOA with 3 layers, 1024 shots: ~100-500ms on Aer simulator
- Parameter optimization: 50-200 iterations depending on problem size
- Real quantum hardware: seconds to minutes per circuit execution

### External Resources

- **Qiskit Documentation**: https://qiskit.org/documentation/
- **Power System Analysis**: pandapower.readthedocs.io
- **QAOA Tutorial**: https://qiskit.org/textbook/ch-applications/qaoa.html
- **NREL ARIES Architecture**: Quantum-in-Loop (QIL) research papers
- **IEEE Power Systems**: https://icseg.iti.illinois.edu/power-cases/

## Project-Specific Patterns

### Hamiltonian Construction

MaxCut for network partitioning:
```python
# Edge-based ZZ interactions
for u, v in graph.edges():
    weight = graph[u][v].get('weight', 1.0)
    hamiltonian += weight/2 * (Z[u] @ Z[v])
```

Unit Commitment with constraints:
```python
# Cost + penalty for demand mismatch
hamiltonian = sum(cost_i * x_i) + penalty * (sum(P_i * x_i) - demand)^2
```

### Time Synchronization

The interface maintains time offset tracking for clock synchronization between quantum computer and power system:

```python
# Exponential moving average for quantum delay
self.avg_quantum_delay = (1 - alpha) * self.avg_quantum_delay + alpha * current_delay
```

### Warm Start Optimization

QAOA parameters are cached for similar problems:

```python
# Reuse parameters from previous optimization
if self.config.use_warm_start and problem_hash in self.parameter_cache:
    initial_point = self.parameter_cache[problem_hash]
```

This significantly speeds up repeated optimizations on similar networks.
