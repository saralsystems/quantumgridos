"""
Power System Optimization Wrappers
High-level interfaces for common optimization problems
"""

import numpy as np
from typing import Dict, List, Optional, Union
import asyncio
import logging
from dataclasses import dataclass

from ..algorithms.qaoa import PowerSystemQAOA, QAOAConfig
from ..algorithms.vqe import PowerSystemVQE, VQEConfig
from ..power_systems.network import PowerNetwork

logger = logging.getLogger(__name__)


class MaxCutOptimizer:
    """Network partitioning using MaxCut"""
    
    def __init__(self, 
                 network: PowerNetwork,
                 algorithm: str = 'qaoa',
                 layers: int = 3,
                 **kwargs):
        self.network = network
        self.algorithm = algorithm
        self.layers = layers
        
        if algorithm == 'qaoa':
            self.solver = PowerSystemQAOA(QAOAConfig(layers=layers, **kwargs))
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    async def solve_async(self, data: Optional[Dict] = None) -> Dict:
        """Async solve for real-time applications"""
        # Update network if new data provided
        if data:
            self._update_network(data)
        
        # Solve partitioning
        result = await asyncio.to_thread(
            self.solver.solve_maxcut, 
            self.network.graph
        )
        
        return result
    
    def solve(self) -> Dict:
        """Synchronous solve"""
        return self.solver.solve_maxcut(self.network.graph)
    
    def _update_network(self, data: Dict):
        """Update network with real-time data"""
        if 'bus_voltages' in data:
            for i, voltage in enumerate(data['bus_voltages']):
                if i+1 in self.network.buses:
                    self.network.buses[i+1].voltage_magnitude = voltage


class UnitCommitment:
    """Unit commitment optimization"""
    
    def __init__(self,
                 generators: List[Dict],
                 demand_forecast: List[float],
                 time_periods: int = 24,
                 algorithm: str = 'qaoa'):
        
        self.generators = generators
        self.demand_forecast = demand_forecast
        self.time_periods = time_periods
        
        if algorithm == 'qaoa':
            self.solver = PowerSystemQAOA()
        elif algorithm == 'vqe':
            self.solver = PowerSystemVQE()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def update_demand(self, new_demand: Union[float, List[float]]):
        """Update demand forecast"""
        if isinstance(new_demand, float):
            self.demand_forecast = [new_demand]
        else:
            self.demand_forecast = new_demand
    
    def solve(self, period: Optional[int] = None) -> Dict:
        """Solve for specific period or all periods"""
        
        if period is not None:
            # Solve for specific period
            demand = self.demand_forecast[period] if period < len(self.demand_forecast) else self.demand_forecast[-1]
            
            if isinstance(self.solver, PowerSystemQAOA):
                return self.solver.solve_unit_commitment(self.generators, demand)
            else:
                # VQE implementation
                buses = [{'id': i} for i in range(len(self.generators))]
                lines = []
                return self.solver.solve_opf(buses, lines, self.generators)
        
        else:
            # Solve for all periods
            results = []
            for p in range(self.time_periods):
                results.append(self.solve(period=p))
            
            return {'all_periods': results}
    
    def to_scada_format(self, solution: Dict) -> Dict:
        """Convert solution to SCADA-compatible format"""
        scada_data = {
            'timestamp': int(time.time()),
            'unit_status': [],
            'generation_dispatch': [],
            'total_cost': 0
        }
        
        if 'schedule' in solution:
            for gen_info in solution['schedule']:
                scada_data['unit_status'].append(int(gen_info['status']))
                scada_data['generation_dispatch'].append(gen_info['output'])
            
            scada_data['total_cost'] = solution.get('total_cost', 0)
        
        return scada_data


class OptimalPowerFlow:
    """AC/DC Optimal Power Flow"""
    
    def __init__(self, network: PowerNetwork, dc_approximation: bool = False):
        self.network = network
        self.dc_approximation = dc_approximation
        self.solver = PowerSystemVQE()
    
    def solve(self) -> Dict:
        """Solve OPF problem"""
        
        buses = list(self.network.buses.values())
        lines = list(self.network.lines.values())
        generators = list(self.network.generators.values())
        
        # Convert to dict format expected by solver
        buses_dict = [{'id': b.bus_id} for b in buses]
        lines_dict = [
            {
                'from': l.from_bus,
                'to': l.to_bus,
                'capacity': l.rating
            }
            for l in lines
        ]
        generators_dict = [
            {
                'name': g.name or f'Gen_{g.gen_id}',
                'bus': g.bus_id,
                'pmin': g.pmin,
                'pmax': g.pmax,
                'cost': g.cost_b
            }
            for g in generators
        ]
        
        return self.solver.solve_opf(buses_dict, lines_dict, generators_dict)
    
    def get_lagrange_multipliers(self, solution: Dict) -> np.ndarray:
        """Extract Lagrange multipliers (shadow prices)"""
        # Simplified - would need actual dual variables
        n_buses = len(self.network.buses)
        return np.zeros(n_buses)


class StateEstimation:
    """Power system state estimation"""
    
    def __init__(self, network: PowerNetwork, measurement_config: Optional[Dict] = None):
        self.network = network
        self.measurement_config = measurement_config or self._default_measurements()
        self.solver = PowerSystemVQE()
        
    def _default_measurements(self) -> Dict:
        """Default measurement configuration"""
        return {
            'voltage_measurements': list(self.network.buses.keys()),
            'power_flow_measurements': [l.line_id for l in self.network.lines.values()],
            'injection_measurements': []
        }
    
    def estimate(self, measurements: np.ndarray) -> Dict:
        """Estimate system state from measurements"""
        
        # Build measurement matrix
        H = self._build_measurement_matrix()
        
        # Solve state estimation
        result = self.solver.solve_state_estimation(measurements, H)
        
        # Map back to network
        self._update_network_state(result['state_estimate'])
        
        return result
    
    def _build_measurement_matrix(self) -> np.ndarray:
        """Build H matrix relating states to measurements"""
        
        n_buses = len(self.network.buses)
        n_measurements = (
            len(self.measurement_config['voltage_measurements']) +
            len(self.measurement_config['power_flow_measurements']) * 2 +
            len(self.measurement_config['injection_measurements']) * 2
        )
        
        H = np.zeros((n_measurements, 2 * n_buses))  # States: V and θ for each bus
        
        # Voltage measurements
        row = 0
        for bus_id in self.measurement_config['voltage_measurements']:
            if bus_id in self.network.buses:
                bus_idx = sorted(self.network.buses.keys()).index(bus_id)
                H[row, 2*bus_idx] = 1  # Voltage magnitude
                row += 1
        
        # Power flow measurements (simplified)
        for line_id in self.measurement_config['power_flow_measurements']:
            if line_id in self.network.lines:
                line = self.network.lines[line_id]
                from_idx = sorted(self.network.buses.keys()).index(line.from_bus)
                to_idx = sorted(self.network.buses.keys()).index(line.to_bus)
                
                # Active power flow
                H[row, 2*from_idx+1] = 1  # from angle
                H[row, 2*to_idx+1] = -1   # to angle
                row += 1
                
                # Reactive power flow (simplified)
                H[row, 2*from_idx] = 1    # from voltage
                H[row, 2*to_idx] = -1     # to voltage  
                row += 1
        
        return H[:row, :]  # Return only filled rows
    
    def _update_network_state(self, state_estimate: np.ndarray):
        """Update network with estimated state"""
        
        for i, bus_id in enumerate(sorted(self.network.buses.keys())):
            if 2*i < len(state_estimate):
                self.network.buses[bus_id].voltage_magnitude = abs(state_estimate[2*i])
                if 2*i+1 < len(state_estimate):
                    self.network.buses[bus_id].voltage_angle = state_estimate[2*i+1]
    
    def get_bad_data_detection(self, result: Dict) -> List[int]:
        """Identify bad measurements"""
        
        threshold = 3.0  # Chi-squared threshold
        bad_measurements = []
        
        residuals = result.get('residuals', np.array([]))
        
        for i, r in enumerate(residuals):
            if abs(r) > threshold:
                bad_measurements.append(i)
        
        return bad_measurements


# Quick access functions
def create_maxcut_optimizer(network_or_case: Union[PowerNetwork, int], **kwargs) -> MaxCutOptimizer:
    """Create MaxCut optimizer quickly"""
    
    if isinstance(network_or_case, int):
        network = PowerNetwork.from_ieee_case(network_or_case)
    else:
        network = network_or_case
    
    return MaxCutOptimizer(network, **kwargs)


def create_uc_optimizer(generators: List[Dict], demand: List[float], **kwargs) -> UnitCommitment:
    """Create unit commitment optimizer"""
    return UnitCommitment(generators, demand, **kwargs)


def create_opf_optimizer(network_or_case: Union[PowerNetwork, int], **kwargs) -> OptimalPowerFlow:
    """Create OPF optimizer"""
    
    if isinstance(network_or_case, int):
        network = PowerNetwork.from_ieee_case(network_or_case)
    else:
        network = network_or_case
    
    return OptimalPowerFlow(network, **kwargs)


def create_state_estimator(network_or_case: Union[PowerNetwork, int], **kwargs) -> StateEstimation:
    """Create state estimator"""
    
    if isinstance(network_or_case, int):
        network = PowerNetwork.from_ieee_case(network_or_case)
    else:
        network = network_or_case
    
    return StateEstimation(network, **kwargs)


import time  # Add at top with other imports
