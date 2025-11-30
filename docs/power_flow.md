# Quantum Power Flow

QuantumGridOS provides a comprehensive Quantum Power Flow solver that allows you to model power networks and solve for steady-state conditions using quantum algorithms.

## Overview

The solver implements the Newton-Raphson method, a standard technique in power systems analysis. However, it replaces the computationally expensive linear solver step ($J \cdot \Delta x = f$) with quantum algorithms:

1.  **HHL Algorithm**: The Harrow-Hassidim-Lloyd algorithm for solving linear systems.
2.  **Quantum Gradient Estimation**: Using parameter shift rules to estimate the Jacobian matrix.

## Getting Started

### Prerequisites

Ensure you have `quantumgridos` installed:

```bash
pip install quantumgridos
```

## Usage

### 1. Creating a Network

You can create a network model from various sources.

#### From CSV Files
Organize your data in a folder with `bus.csv` and `line.csv`.

**bus.csv format:**
```csv
id,type,v_mag,v_ang,p_load,q_load,base_kv
1,1,1.05,0.0,0.0,0.0,110.0
2,2,1.04,0.0,0.5,0.0,110.0
3,3,1.0,0.0,0.4,0.2,110.0
```
*   `type`: 1=Slack, 2=PV, 3=PQ

**line.csv format:**
```csv
from_bus,to_bus,r,x,b,rate_a
1,2,0.02,0.08,0.02,100.0
```

**Code:**
```python
import quantumgridos as qgo

net = qgo.create_network("path/to/csv_folder", type='csv')
```

#### From Raw Y-Bus (TXT)
Useful for quick testing with a known admittance matrix.

```python
net = qgo.create_network("ybus_matrix.txt", type='txt')
```

### 2. Running Power Flow

Use the `run_quantum_nr` function to solve the power flow.

#### Classical Mode (Baseline)
Use standard `numpy` solvers for validation.

```python
success, x, history = qgo.run_quantum_nr(net, method='classical')
```

#### Quantum Mode: HHL (Fast Simulation)
Simulates the HHL algorithm logic but uses a classical backend for the final solve. This is instant and reliable, perfect for algorithm development and demonstrations.

```python
success, x, history = qgo.run_quantum_nr(net, method='hhl_fast')
```

#### Quantum Mode: HHL (NISQ Execution)
**WARNING**: This attempts to run the actual quantum circuit on a simulator (or connected quantum hardware). Due to the depth of the HHL circuit (QPE + Reciprocal Rotation), this is extremely demanding and may be slow or noisy on current devices.

```python
success, x, history = qgo.run_quantum_nr(net, method='hhl_nisq')
```

### 3. Visualizing Results

The solver returns the convergence history and the generated quantum circuit (if applicable).

#### Convergence Plot
```python
from quantumgridos.utils.visualizer import plot_convergence

plot_convergence(history, title="Quantum NR Convergence")
```

#### Circuit Visualization
You can inspect the quantum circuit generated for the linear system solver (HHL).

```python
from quantumgridos.utils.visualizer import draw_circuit

# run_quantum_nr returns (success, x, history, circuit)
success, x, history, circuit = qgo.run_quantum_nr(net, method='hhl_fast')

if circuit:
    print("Quantum Circuit used for Linear Solver:")
    draw_circuit(circuit)
```

## Technical Details

### The Quantum Advantage
The core bottleneck in classical Newton-Raphson is solving the linear system $J \cdot \Delta x = f$, which scales as $O(N^3)$. The HHL algorithm can theoretically solve this in $O(\log N)$, providing an exponential speedup for very large, sparse matrices.

### Current Limitations
-   **Circuit Depth**: HHL requires deep circuits that are challenging for Noisy Intermediate-Scale Quantum (NISQ) devices.
-   **State Preparation**: Loading the vector $f$ into a quantum state is non-trivial.
-   **Readout**: Extracting the full solution vector $x$ from the quantum state requires tomography, which can negate the speedup.

QuantumGridOS provides a platform to experiment with these algorithms and prepare for the fault-tolerant quantum era.
