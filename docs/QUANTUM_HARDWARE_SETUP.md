# Quantum Hardware Integration Guide for QuantumGridOS

This guide explains how to connect QuantumGridOS to real quantum computers from IBM, Rigetti, IonQ, AWS Braket, and others.

## 📋 Table of Contents
- [Quick Start](#quick-start)
- [IBM Quantum](#ibm-quantum)
- [Rigetti](#rigetti)
- [IonQ](#ionq)
- [AWS Braket](#aws-braket)
- [Hardware Comparison](#hardware-comparison)

## 🚀 Quick Start

### Auto-Connect (Simplest Method)
```python
from quantumgridos.backends import auto_connect

# Automatically detects and uses best available backend
backend = auto_connect()
```

### Environment Variables
Set your quantum credentials as environment variables:
```bash
# IBM Quantum
export IBM_QUANTUM_TOKEN="your_token_here"

# Rigetti
export QCS_API_KEY="your_key_here"

# IonQ
export IONQ_API_KEY="your_key_here"

# AWS Braket (via AWS CLI)
aws configure
```

## 🔵 IBM Quantum

### 1. Get Your IBM Quantum Token
1. Sign up at [IBM Quantum Experience](https://quantum-computing.ibm.com/)
2. Go to Account → API Token
3. Copy your token

### 2. Install IBM Dependencies
```bash
pip install qiskit-ibm-runtime qiskit-ibmq-provider
```

### 3. Connect to IBM Quantum
```python
from quantumgridos.backends import QuantumGridBackend

# Method 1: Auto-select least busy backend
backend = QuantumGridBackend(
    provider='ibm',
    api_token='YOUR_TOKEN',  # or use env var IBM_QUANTUM_TOKEN
    backend_name=None,       # Auto-selects least busy
    use_runtime=True        # Uses Qiskit Runtime for better performance
)

# Method 2: Specific backend
backend = QuantumGridBackend(
    provider='ibm',
    api_token='YOUR_TOKEN',
    backend_name='ibmq_manila',  # 5-qubit device
    hub='ibm-q',
    group='open',
    project='main'
)

# Method 3: Premium access (if you have it)
backend = QuantumGridBackend(
    provider='ibm',
    api_token='YOUR_TOKEN',
    backend_name='ibm_brisbane',  # 127-qubit device
    hub='your-hub',
    group='your-group',
    project='your-project'
)
```

### 4. Use with QuantumGridOS
```python
import quantumgridos as qgo

# Create power system optimizer
network = qgo.PowerNetwork.from_ieee_case(14)
optimizer = qgo.MaxCutOptimizer(network)

# Replace default backend with IBM hardware
optimizer.solver.backend = backend.manager.backend

# Solve on real quantum hardware
result = optimizer.solve()
```

### Available IBM Backends
| Backend | Qubits | Type | Access |
|---------|--------|------|--------|
| ibmq_qasm_simulator | 32 | Simulator | Free |
| ibmq_manila | 5 | Real | Free |
| ibmq_quito | 5 | Real | Free |
| ibmq_belem | 5 | Real | Free |
| ibmq_lima | 5 | Real | Free |
| ibm_perth | 7 | Real | Premium |
| ibm_lagos | 7 | Real | Premium |
| ibm_brisbane | 127 | Real | Premium |
| ibm_kyoto | 127 | Real | Premium |

## 🟣 Rigetti

### 1. Get Rigetti Access
1. Sign up at [Rigetti QCS](https://qcs.rigetti.com/)
2. Get your API key from the dashboard

### 2. Install Rigetti Dependencies
```bash
pip install pyquil
```

### 3. Connect to Rigetti
```python
from quantumgridos.backends import QuantumGridBackend

# Connect to Rigetti QPU
backend = QuantumGridBackend(
    provider='rigetti',
    api_token='YOUR_QCS_KEY',  # or env var QCS_API_KEY
    backend_name='Aspen-M-3'   # Latest 80-qubit processor
)

# Or use QVM (simulator)
backend = QuantumGridBackend(
    provider='rigetti',
    backend_name='9q-qvm'  # 9-qubit simulator
)
```

### Available Rigetti Processors
| Processor | Qubits | Architecture |
|-----------|--------|--------------|
| Aspen-M-3 | 80 | Superconducting |
| Ankaa-2 | 84 | Superconducting |
| 9q-qvm | 9 | Simulator |
| 20q-qvm | 20 | Simulator |

## 🟡 IonQ

### 1. Get IonQ Access
1. Sign up at [IonQ Cloud](https://cloud.ionq.com/)
2. Get API key from your dashboard

### 2. Install IonQ Dependencies
```bash
pip install cirq-ionq
```

### 3. Connect to IonQ
```python
from quantumgridos.backends import QuantumGridBackend

# Connect to IonQ
backend = QuantumGridBackend(
    provider='ionq',
    api_token='YOUR_IONQ_KEY',  # or env var IONQ_API_KEY
    backend_name='ionq.qpu.harmony'  # 11-qubit trapped ion
)

# Available IonQ devices:
# - 'ionq.simulator': Unlimited qubits simulator
# - 'ionq.qpu': Auto-select QPU
# - 'ionq.qpu.harmony': 11 qubits, $0.00305/shot
# - 'ionq.qpu.aria-1': 25 qubits, $0.0305/shot
# - 'ionq.qpu.forte': 32 qubits, premium
```

## 🟠 AWS Braket

### 1. Setup AWS Account
1. Create [AWS account](https://aws.amazon.com/)
2. Enable Braket service
3. Configure AWS CLI:
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region
```

### 2. Install AWS Dependencies
```bash
pip install amazon-braket-sdk
```

### 3. Connect to AWS Braket
```python
from quantumgridos.backends import QuantumGridBackend

# Use IonQ via AWS
backend = QuantumGridBackend(
    provider='braket',
    backend_name='IonQ',
    region='us-east-1'
)

# Use Rigetti via AWS
backend = QuantumGridBackend(
    provider='braket',
    backend_name='Rigetti',
    region='us-west-1'
)

# Use Oxford Quantum Circuits
backend = QuantumGridBackend(
    provider='braket',
    backend_name='Oxford',
    region='eu-west-2'
)

# Use local simulator (free)
backend = QuantumGridBackend(
    provider='braket',
    backend_name=None  # Uses local simulator
)
```

### AWS Braket Devices & Pricing
| Provider | Device | Qubits | Cost |
|----------|--------|--------|------|
| IonQ | Harmony | 11 | $0.30/task + $0.003/shot |
| IonQ | Aria | 25 | $0.30/task + $0.030/shot |
| Rigetti | Aspen-M | 80 | $0.30/task + $0.00035/shot |
| Oxford | Lucy | 8 | $0.30/task + $0.00035/shot |
| QuEra | Aquila | 256 | $0.30/task + $0.01/shot |
| Local | Simulator | Unlimited | Free |

## 📊 Hardware Comparison

### Qubit Count
- **Simulator**: Unlimited (limited by RAM)
- **IBM**: 5-433 qubits
- **Rigetti**: 80-84 qubits
- **IonQ**: 11-32 qubits
- **QuEra**: 256 qubits (neutral atom)

### Technology
- **IBM**: Superconducting transmon qubits
- **Rigetti**: Superconducting qubits
- **IonQ**: Trapped ions
- **QuEra**: Neutral atoms

### Key Considerations
| Factor | IBM | Rigetti | IonQ | AWS Braket |
|--------|-----|---------|------|------------|
| Free Tier | ✅ Yes | ❌ No | ❌ No | ✅ Simulator only |
| Fidelity | Good | Good | Excellent | Varies |
| Queue Time | Variable | Short | Short | Short |
| Max Qubits | 433 | 84 | 32 | 256 (QuEra) |
| Circuit Depth | Limited | Limited | Good | Varies |

## 🔧 Advanced Configuration

### Circuit Optimization for Hardware
```python
# Optimize circuit for specific backend topology
from quantumgridos.backends import QuantumGridBackend

backend = QuantumGridBackend(provider='ibm', backend_name='ibmq_manila')

# Get backend properties
info = backend.get_status()
print(f"Qubits: {info['n_qubits']}")
print(f"Coupling map: {info['coupling_map']}")

# Optimize circuit
optimized_circuit = backend.optimize_circuit(your_circuit)
```

### Error Mitigation
```python
# IBM Runtime with error mitigation
backend = QuantumGridBackend(
    provider='ibm',
    use_runtime=True,
    resilience_level=2,  # 0=none, 1=basic, 2=advanced
    optimization_level=3  # Circuit optimization level
)
```

### Batch Execution
```python
# Execute multiple circuits efficiently
circuits = [circuit1, circuit2, circuit3]

results = []
for circuit in circuits:
    result = backend.execute_qaoa(circuit, shots=1000)
    results.append(result)
```

## 💰 Cost Optimization Tips

1. **Use simulators for development**
   - Test on simulators before running on hardware
   - Free and unlimited shots

2. **Optimize shot count**
   - Start with 100-500 shots for testing
   - Increase to 1000-5000 for production

3. **Circuit optimization**
   - Minimize circuit depth
   - Use native gates for each hardware

4. **Batch processing**
   - Group similar circuits
   - Use runtime sessions (IBM)

## 🐛 Troubleshooting

### Common Issues

**IBM: "No backend available"**
```python
# Check available backends
from qiskit import IBMQ
IBMQ.load_account()
provider = IBMQ.get_provider()
print(provider.backends())
```

**Rigetti: "Connection refused"**
```bash
# Check QCS configuration
qcs config list
```

**IonQ: "Invalid API key"**
```python
# Verify API key
import os
print(os.getenv('IONQ_API_KEY'))
```

**AWS: "Access denied"**
```bash
# Check AWS credentials
aws sts get-caller-identity
```

## 📚 Example: Complete Power System Optimization

```python
import quantumgridos as qgo
from quantumgridos.backends import auto_connect

# Auto-connect to best available backend
quantum_backend = auto_connect()

# Create power network
network = qgo.PowerNetwork.from_ieee_case(14)

# Setup QAOA with hardware backend
class HardwareQAOA(qgo.PowerSystemQAOA):
    def __init__(self, backend):
        super().__init__(qgo.QAOAConfig(layers=2, shots=1000))
        self.hardware = backend
    
    def _sample_optimized_circuit(self, circuit, params):
        # Override to use real hardware
        bound_circuit = circuit.bind_parameters(params)
        optimized = self.hardware.optimize_circuit(bound_circuit)
        result = self.hardware.execute_qaoa(optimized)
        return result['counts']

# Create optimizer with hardware backend
optimizer = HardwareQAOA(quantum_backend)

# Solve network partitioning on real quantum computer
result = optimizer.solve_maxcut(network.graph)

print(f"Solved on: {quantum_backend.provider}")
print(f"Partition: {result['partition']}")
print(f"Cut value: {result['partition']['cut_value']}")
```

## 🔗 Resources

- [IBM Quantum Documentation](https://quantum-computing.ibm.com/docs/)
- [Rigetti QCS Docs](https://docs.rigetti.com/)
- [IonQ Documentation](https://ionq.com/docs/)
- [AWS Braket Documentation](https://docs.aws.amazon.com/braket/)
- [QuantumGridOS GitHub](https://github.com/yourusername/quantumgridos)

## 📧 Support

For issues or questions:
- GitHub Issues: [github.com/yourusername/quantumgridos/issues](https://github.com/yourusername/quantumgridos/issues)
- Email: quantum-support@yourdomain.com
