# QuantumGridOS

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-orange)](https://saralsystems.github.io/quantumgridos/)

**QuantumGridOS** is a Python library for connecting power systems data to quantum computers.
> [!IMPORTANT]
> This library currently supports Python 3.8 to 3.11. Python 3.12+ is not yet supported.

It enables solving power system optimization problems using quantum algorithms (QAOA, VQE) with minimal latency TCP/IP data exchange.

## 🚀 Features

- **Real-time TCP/IP streaming** for power systems data exchange
- **Quantum algorithm support**: QAOA, VQE, Grover's
- **Power system optimizations**: Unit commitment, MaxCut, OPF, State estimation
- **Low-latency architecture** with async I/O and buffer management
- **Hardware agnostic**: Works with IBM Quantum, IonQ, Rigetti, simulators
- **Extensive examples** and documentation

## 📦 Installation

```bash
pip install quantumgridos
```

For development:
```bash
git clone https://github.com/saralsystems/quantumgridos.git
cd quantumgridos
pip install -e .[dev]
```

## 🎯 Quick Start

### Basic MaxCut for Power Network Partitioning

```python
import quantumgridos as qgo

# Initialize quantum-power interface
interface = qgo.QuantumPowerInterface(
    quantum_backend='qiskit_aer',
    tcp_host='localhost',
    tcp_port=5000
)

# Define power network
network = qgo.PowerNetwork.from_ieee_case(14)  # IEEE 14-bus

# Create MaxCut optimizer for network partitioning
optimizer = qgo.MaxCutOptimizer(
    network=network,
    algorithm='qaoa',
    layers=3
)

# Start real-time processing
async def process_stream():
    async for data in interface.tcp_stream():
        # Solve partitioning problem
        result = await optimizer.solve_async(data)
        
        # Send result back to power system
        await interface.send_result(result)

# Run
import asyncio
asyncio.run(process_stream())
```

### Unit Commitment Example

```python
import quantumgridos as qgo

# Configure unit commitment problem
uc_problem = qgo.UnitCommitment(
    generators=[
        {'name': 'G1', 'pmin': 50, 'pmax': 200, 'cost': 1000},
        {'name': 'G2', 'pmin': 20, 'pmax': 100, 'cost': 1500}
    ],
    demand_forecast=[150, 180, 200, 170],
    time_periods=4
)

# Setup quantum solver
solver = qgo.QuantumSolver(
    problem=uc_problem,
    backend='ibmq_qasm_simulator',
    algorithm='vqe',
    optimizer='cobyla'
)

# Solve with TCP streaming
with qgo.TCPInterface(port=5000) as tcp:
    for demand_update in tcp.stream():
        uc_problem.update_demand(demand_update)
        solution = solver.solve()
        tcp.send(solution.to_scada_format())
        solution = solver.solve()
        tcp.send(solution.to_scada_format())
```

### Low-Inertia Counterfactual Search

```python
import quantumgridos as qgo

# Built-in Braket-scale demo case inspired by the GB 9 Aug 2019 disturbance.
study = qgo.create_low_inertia_study()

# QuantumGridOS builds a QUBO candidate-search layer, then validates every
# candidate with reduced frequency-security physics.
result = qgo.solve_low_inertia_counterfactual(
    study,
    solvers=("exact", "annealing", "qaoa"),
    top_k=24,
    qaoa_layers=1,
)

print(result.best.portfolio.selected_labels)
print(result.best.metrics["nadir_hz"])
print(result.best.metrics["max_abs_rocof_hz_s"])
```

Use this API for low-inertia studies where quantum or quantum-inspired solvers
search over approved binary grid/DER settings such as synchronous commitment,
BESS fast-frequency response, grid-forming mode, DER ride-through package, and
pre-event export reduction. Classical physics validation remains authoritative.

For publication screening, enable the native two-area dynamic-label surrogate:

```python
result = qgo.solve_low_inertia_counterfactual(
    study,
    solvers=("exact", "annealing"),
    dynamic_labels=True,
)

label = qgo.label_low_inertia_dynamics(study, bits=result.best.portfolio.bitstring)
print(label.metrics["max_relative_angle_rad"])
print(label.metrics["min_electromechanical_damping_ratio"])
```

The dynamic labeler adds inter-area angle, area-frequency split, and small-signal
damping checks. It is a reproducible reduced electromechanical screen, not a
replacement for RMS/EMT validation.

### Quantum Power Flow

```python
import quantumgridos as qgo

# Load network from CSV
net = qgo.create_network("examples/test_case_4bus", type='csv')

# Run Quantum Newton-Raphson (HHL Fast Mode)
success, x, history, circuit = qgo.run_quantum_nr(net, method='hhl_fast')

if success:
    print("Converged! Voltage Angles:", net.buses['v_ang'].values)
    # Optional: Visualize the circuit
    # from quantumgridos.utils.visualizer import draw_circuit
    # draw_circuit(circuit)
```

## 🏗️ Architecture

```
QuantumGridOS/
├── Core Modules
│   ├── quantum_interface.py     # Quantum backend abstraction
│   ├── tcp_handler.py          # High-performance TCP/IP
│   ├── data_encoder.py         # Power data → Qubits
│   └── time_sync.py            # Clock synchronization
├── Algorithms
│   ├── qaoa.py                 # QAOA implementation
│   ├── vqe.py                  # VQE implementation
│   └── grover.py               # Grover's algorithm
├── Power Systems
│   ├── network.py              # Power network modeling
│   ├── optimizations/
│   │   ├── unit_commitment.py
│   │   ├── opf.py             # Optimal Power Flow
│   │   ├── state_estimation.py
│   │   └── maxcut.py
│   └── converters.py           # IEEE/MATPOWER formats
└── Utils
    ├── benchmarks.py
    └── visualization.py
```

## 📊 Benchmarks

| Problem Type | Network Size | Classical (ms) | Quantum (ms) | Speedup |
|-------------|-------------|---------------|--------------|---------|
| MaxCut | IEEE 14-bus | 120 | 45 | 2.67x |
| Unit Commitment | 10 units | 340 | 180 | 1.89x |
| State Estimation | 30-bus | 250 | 110 | 2.27x |

## 🔌 TCP/IP Protocol

QuantumGridOS uses optimized binary protocol for minimal latency:

```python
# Message format
{
    'timestamp': int64,          # Unix timestamp in microseconds
    'msg_type': uint8,          # 0: data, 1: control, 2: result
    'data': {
        'bus_voltages': float32[],
        'line_flows': float32[],
        'generator_status': bool[]
    }
}
```

## 📚 Documentation

Full documentation available at [saralsystems.github.io/quantumgridos](https://saralsystems.github.io/quantumgridos/)

- [Getting Started Guide](https://saralsystems.github.io/quantumgridos/installation.html)
- [Quick Start](https://saralsystems.github.io/quantumgridos/quickstart.html)
- [API Reference](https://saralsystems.github.io/quantumgridos/api/core.html)
- [User Guide](https://saralsystems.github.io/quantumgridos/user_guide/index.html)
- [Tutorials](https://saralsystems.github.io/quantumgridos/tutorials/index.html)
- [Quantum Power Flow Guide](docs/power_flow.md)

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=quantumgridos tests/

# Run benchmarks
python -m quantumgridos.benchmark
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

All contributors must sign a Contributor License Agreement (CLA) before their contributions can be merged. See [CLA.md](CLA.md) for individual contributors and [CLA-CORPORATE.md](CLA-CORPORATE.md) for corporate contributors.

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file.

## 📖 Citation

If you use QuantumGridOS in research, please cite:

```bibtex
@software{quantumgridos,
  title = {QuantumGridOS: Real-time Quantum-Power Systems Interface},
  author = {Saral Systems},
  year = {2025},
  url = {https://github.com/saralsystems/quantumgridos},
  license = {Apache-2.0}
}
```

## 🙏 Acknowledgments

Based on research from NREL ARIES and quantum-in-loop (QIL) architecture.
