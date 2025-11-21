"""
QuantumGridOS Complete Example
Demonstrates real-time quantum-power systems integration
"""

import asyncio
import numpy as np
import time
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import QuantumGridOS components
from quantumgridos.core.quantum_interface import (
    QuantumPowerInterface,
    PowerSystemData,
    TCPPowerStreamHandler
)
from quantumgridos.algorithms.qaoa import PowerSystemQAOA, QAOAConfig
from quantumgridos.algorithms.vqe import PowerSystemVQE, VQEConfig  
from quantumgridos.power_systems.network import (
    PowerNetwork,
    UnitCommitmentProblem
)


class PowerSystemSimulator:
    """Simulates real-time power system data stream"""
    
    def __init__(self, network: PowerNetwork, update_rate: float = 0.1):
        self.network = network
        self.update_rate = update_rate
        self.time = 0
        
    async def generate_stream(self) -> PowerSystemData:
        """Generate realistic power system measurements"""
        
        # Add some realistic variations
        noise_level = 0.01
        
        # Collect measurements
        bus_voltages = []
        bus_angles = []
        
        for bus_id in sorted(self.network.buses.keys()):
            bus = self.network.buses[bus_id]
            
            # Add time-varying components and noise
            v_mag = bus.voltage_magnitude + noise_level * np.random.randn()
            v_ang = bus.voltage_angle + 0.01 * np.sin(0.1 * self.time)
            
            bus_voltages.append(v_mag)
            bus_angles.append(v_ang)
        
        # Estimate line flows
        line_flows = []
        for line in self.network.lines.values():
            # Simplified power flow calculation
            v1 = self.network.buses[line.from_bus].voltage_magnitude
            v2 = self.network.buses[line.to_bus].voltage_magnitude
            theta = (self.network.buses[line.from_bus].voltage_angle - 
                    self.network.buses[line.to_bus].voltage_angle)
            
            p_flow = v1 * v2 * np.sin(theta) / line.reactance
            p_flow += noise_level * np.random.randn() * 10  # MW
            line_flows.append(p_flow)
        
        # Generator outputs
        generator_outputs = []
        for gen in self.network.generators.values():
            # Vary around nominal
            output = 0.7 * gen.pmax + 0.1 * gen.pmax * np.sin(0.05 * self.time)
            generator_outputs.append(output)
        
        # Load demands with daily pattern
        load_demands = []
        load_pattern = 0.8 + 0.2 * np.sin(2 * np.pi * self.time / 86400)  # Daily cycle
        
        for bus_id, load in self.network.loads.items():
            demand = load['P'] * load_pattern
            load_demands.append(demand)
        
        self.time += self.update_rate
        
        return PowerSystemData(
            timestamp=time.time(),
            bus_voltages=np.array(bus_voltages),
            bus_angles=np.array(bus_angles),
            line_flows=np.array(line_flows),
            generator_outputs=np.array(generator_outputs),
            load_demands=np.array(load_demands)
        )


async def example_maxcut_partitioning():
    """Example: Network partitioning using QAOA MaxCut"""
    
    print("\n" + "="*60)
    print("EXAMPLE 1: Power Network Partitioning with QAOA MaxCut")
    print("="*60)
    
    # Create IEEE 14-bus network
    network = PowerNetwork.from_ieee_case(14)
    print(f"Loaded IEEE 14-bus system with {len(network.buses)} buses")
    
    # Setup QAOA solver
    qaoa_config = QAOAConfig(
        layers=3,
        optimizer='COBYLA',
        shots=1024
    )
    qaoa_solver = PowerSystemQAOA(qaoa_config)
    
    # Solve partitioning problem
    print("\nSolving network partitioning problem...")
    result = qaoa_solver.solve_maxcut(network.graph)
    
    print(f"\nResults:")
    print(f"  Minimum eigenvalue: {result['eigenvalue']:.4f}")
    print(f"  Execution time: {result['execution_time']:.2f} seconds")
    print(f"  Best solution: {result['best_solution']}")
    
    if 'partition' in result:
        print(f"\nNetwork Partition:")
        print(f"  Area 1: Buses {result['partition']['set_1']}")
        print(f"  Area 2: Buses {result['partition']['set_2']}")
        print(f"  Cut value: {result['partition']['cut_value']:.2f}")


async def example_unit_commitment():
    """Example: Unit commitment with VQE"""
    
    print("\n" + "="*60)
    print("EXAMPLE 2: Unit Commitment with Quantum Optimization")
    print("="*60)
    
    # Define generators
    generators = [
        {'name': 'Coal_1', 'pmin': 50, 'pmax': 200, 'cost': 20},
        {'name': 'Gas_1', 'pmin': 20, 'pmax': 100, 'cost': 35},
        {'name': 'Gas_2', 'pmin': 20, 'pmax': 100, 'cost': 40},
        {'name': 'Nuclear', 'pmin': 100, 'pmax': 400, 'cost': 10},
        {'name': 'Wind', 'pmin': 0, 'pmax': 50, 'cost': 0}
    ]
    
    # Demand for different periods
    demand_forecast = [300, 350, 400, 380, 320, 280]  # MW
    
    print(f"Generators: {len(generators)}")
    print(f"Demand periods: {len(demand_forecast)}")
    print(f"Demand range: {min(demand_forecast)}-{max(demand_forecast)} MW")
    
    # Solve with QAOA
    qaoa = PowerSystemQAOA()
    
    for period, demand in enumerate(demand_forecast):
        print(f"\nPeriod {period+1} - Demand: {demand} MW")
        result = qaoa.solve_unit_commitment(generators, demand)
        
        print("  Generator Schedule:")
        for gen_schedule in result['schedule']:
            if gen_schedule['status']:
                print(f"    {gen_schedule['generator']}: " 
                     f"{gen_schedule['output']} MW @ ${gen_schedule['cost']:.2f}")
        
        print(f"  Total generation: {result['total_output']} MW")
        print(f"  Total cost: ${result['total_cost']:.2f}")
        print(f"  Demand met: {result['demand_met']}")


async def example_real_time_streaming():
    """Example: Real-time TCP streaming with quantum processing"""
    
    print("\n" + "="*60)
    print("EXAMPLE 3: Real-Time Streaming Integration")
    print("="*60)
    
    # Create network and simulator
    network = PowerNetwork.from_ieee_case(14)
    simulator = PowerSystemSimulator(network)
    
    # Initialize quantum interface
    interface = QuantumPowerInterface(
        quantum_backend='qiskit_aer',
        tcp_host='localhost',
        tcp_port=5000
    )
    
    print("Starting real-time simulation...")
    print("Processing 10 time steps...\n")
    
    # Process stream
    for step in range(10):
        # Generate data
        data = await simulator.generate_stream()
        
        # Process with quantum algorithm
        result = await interface.process_with_quantum(
            data,
            algorithm='qaoa',
            layers=2
        )
        
        # Display results
        print(f"Step {step+1}:")
        print(f"  Timestamp: {data.timestamp:.6f}")
        print(f"  Quantum processing time: {result['quantum_time']*1000:.2f} ms")
        print(f"  Generator states: {result['result']['generator_states']}")
        print(f"  Objective value: {result['result']['objective_value']:.4f}")
        
        # Brief pause
        await asyncio.sleep(0.1)
    
    # Show latency statistics
    stats = interface.get_latency_stats()
    if stats:
        print(f"\nLatency Statistics:")
        print(f"  Mean: {stats['mean']*1000:.2f} ms")
        print(f"  Std: {stats['std']*1000:.2f} ms")
        print(f"  P95: {stats['p95']*1000:.2f} ms")


async def example_state_estimation():
    """Example: Power system state estimation with VQE"""
    
    print("\n" + "="*60)
    print("EXAMPLE 4: State Estimation with VQE")
    print("="*60)
    
    # Create simple 4-bus system
    network = PowerNetwork()
    
    # Add buses
    from quantumgridos.power_systems.network import Bus, Line
    for i in range(1, 5):
        network.add_bus(Bus(bus_id=i, voltage_magnitude=1.0))
    
    # Add lines (ring topology)
    network.add_line(Line(1, 1, 2, 0.01, 0.1))
    network.add_line(Line(2, 2, 3, 0.01, 0.1))
    network.add_line(Line(3, 3, 4, 0.01, 0.1))
    network.add_line(Line(4, 4, 1, 0.01, 0.1))
    
    print(f"Created {len(network.buses)}-bus test system")
    
    # Simulated measurements
    true_state = np.array([1.0, 0.0, 0.99, -0.05, 0.98, -0.1, 0.99, -0.05])  # V, θ pairs
    
    # Measurement matrix (simplified)
    H = np.array([
        [1, 0, 0, 0, 0, 0, 0, 0],  # V1
        [0, 0, 1, 0, 0, 0, 0, 0],  # V2
        [0, 0, 0, 0, 1, 0, 0, 0],  # V3
        [0, 0, 0, 0, 0, 0, 1, 0],  # V4
        [0, 1, 0, -1, 0, 0, 0, 0], # θ1-θ2
        [0, 0, 0, 1, 0, -1, 0, 0], # θ2-θ3
    ])
    
    # Generate measurements with noise
    noise = 0.01 * np.random.randn(len(H))
    measurements = H @ true_state + noise
    
    print(f"Number of measurements: {len(measurements)}")
    print(f"Number of state variables: {len(true_state)}")
    
    # Solve with VQE
    vqe = PowerSystemVQE(VQEConfig(
        ansatz='RealAmplitudes',
        optimizer='SLSQP',
        reps=2
    ))
    
    print("\nRunning VQE state estimation...")
    result = vqe.solve_state_estimation(measurements, H)
    
    print("\nResults:")
    print(f"  Residual norm: {result['residual_norm']:.6f}")
    print(f"  Chi-squared: {result['chi_squared']:.6f}")
    
    print("\nState Comparison:")
    print("  Variable | True    | Estimated | Error")
    print("  ---------|---------|-----------|-------")
    for i, (true_val, est_val) in enumerate(zip(true_state[:len(result['state_estimate'])], 
                                                 result['state_estimate'])):
        error = abs(true_val - est_val)
        var_name = f"V{i//2+1}" if i % 2 == 0 else f"θ{i//2+1}"
        print(f"  {var_name:8s} | {true_val:7.4f} | {est_val:9.4f} | {error:6.4f}")


async def example_adaptive_optimization():
    """Example: Adaptive quantum optimization"""
    
    print("\n" + "="*60)
    print("EXAMPLE 5: Adaptive Optimization for Voltage Control")
    print("="*60)
    
    # Create network
    network = PowerNetwork.from_ieee_case(14)
    
    # Create voltage control problem (simplified)
    n_buses = 4  # Use subset for demo
    
    # Define cost function for voltage regulation
    def create_voltage_hamiltonian():
        from qiskit.quantum_info import SparsePauliOp
        
        # Minimize voltage deviations from 1.0 p.u.
        pauli_list = []
        
        for i in range(n_buses):
            # Linear term for voltage deviation
            pauli_str = ['I'] * n_buses
            pauli_str[i] = 'Z'
            pauli_list.append((''.join(pauli_str), -1.0))
            
            # Quadratic penalty for large deviations
            for j in range(i+1, n_buses):
                pauli_str = ['I'] * n_buses
                pauli_str[i] = 'Z'
                pauli_str[j] = 'Z'
                pauli_list.append((''.join(pauli_str), 0.5))
        
        return SparsePauliOp.from_list(pauli_list)
    
    # Run adaptive VQE
    vqe = PowerSystemVQE()
    hamiltonian = create_voltage_hamiltonian()
    
    print(f"Running adaptive VQE for {n_buses}-bus voltage control...")
    result = vqe.adaptive_vqe(hamiltonian, n_buses, threshold=0.01)
    
    print(f"\nAdaptive Optimization Results:")
    print(f"  Final energy: {result['final_energy']:.6f}")
    print(f"  Optimal circuit depth: {result['final_depth']}")
    print(f"  Converged: {result['converged']}")
    
    print(f"\nOptimization progression:")
    for step in result['optimization_trajectory']:
        print(f"  Depth {step['depth']}: Energy = {step['energy']:.6f}")


async def main():
    """Run all examples"""
    
    print("\n" + "="*60)
    print("     QuantumGridOS - Power Systems Quantum Computing")
    print("                    Demo Examples")
    print("="*60)
    
    try:
        # Run examples
        await example_maxcut_partitioning()
        await example_unit_commitment()
        await example_real_time_streaming()
        await example_state_estimation()
        await example_adaptive_optimization()
        
        print("\n" + "="*60)
        print("            All Examples Completed Successfully!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
