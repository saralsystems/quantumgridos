
import numpy as np
import pandas as pd
from typing import Optional, Tuple, List, Dict, Union

class Network:
    """
    QuantumGridOS Network Class
    
    Stores the power system network data including buses, lines, generators, and loads.
    Provides methods to build the admittance matrix (Y-bus) and manage network state.
    """
    
    def __init__(self, name: str = "Network"):
        self.name = name
        self.buses = pd.DataFrame(columns=['id', 'type', 'v_mag', 'v_ang', 'p_load', 'q_load', 'base_kv'])
        self.lines = pd.DataFrame(columns=['from_bus', 'to_bus', 'r', 'x', 'b', 'rate_a'])
        self.generators = pd.DataFrame(columns=['bus', 'p_gen', 'q_gen', 'p_min', 'p_max', 'q_min', 'q_max'])
        self.shunts = pd.DataFrame(columns=['bus', 'g_shunt', 'b_shunt'])
        
        self.Y_bus: Optional[np.ndarray] = None
        self.base_mva = 100.0
        
    def add_bus(self, bus_id: int, bus_type: int = 3, v_mag: float = 1.0, v_ang: float = 0.0, 
                p_load: float = 0.0, q_load: float = 0.0, base_kv: float = 110.0):
        """
        Add a bus to the network.
        bus_type: 1=Slack, 2=PV, 3=PQ
        """
        new_bus = pd.DataFrame([{
            'id': bus_id, 'type': bus_type, 'v_mag': v_mag, 'v_ang': v_ang,
            'p_load': p_load, 'q_load': q_load, 'base_kv': base_kv
        }])
        self.buses = pd.concat([self.buses, new_bus], ignore_index=True)
        
    def add_line(self, from_bus: int, to_bus: int, r: float, x: float, b: float = 0.0, rate_a: float = 0.0):
        """
        Add a transmission line to the network.
        r, x, b are in per unit. b is total line charging susceptance.
        """
        new_line = pd.DataFrame([{
            'from_bus': from_bus, 'to_bus': to_bus, 'r': r, 'x': x, 'b': b, 'rate_a': rate_a
        }])
        self.lines = pd.concat([self.lines, new_line], ignore_index=True)
        
    def add_generator(self, bus_id: int, p_gen: float, q_gen: float = 0.0, 
                      p_min: float = 0.0, p_max: float = 0.0, q_min: float = 0.0, q_max: float = 0.0):
        """Add a generator to the network."""
        new_gen = pd.DataFrame([{
            'bus': bus_id, 'p_gen': p_gen, 'q_gen': q_gen,
            'p_min': p_min, 'p_max': p_max, 'q_min': q_min, 'q_max': q_max
        }])
        self.generators = pd.concat([self.generators, new_gen], ignore_index=True)
        
    def build_y_bus(self):
        """
        Construct the Y-bus admittance matrix from line and shunt data.
        """
        n_buses = len(self.buses)
        if n_buses == 0:
            raise ValueError("Cannot build Y-bus: No buses in network")
            
        # Map bus IDs to matrix indices (0 to n-1)
        bus_id_to_idx = {bid: i for i, bid in enumerate(self.buses['id'])}
        
        Y = np.zeros((n_buses, n_buses), dtype=complex)
        
        # Add line admittances
        for _, line in self.lines.iterrows():
            try:
                i = bus_id_to_idx[line['from_bus']]
                j = bus_id_to_idx[line['to_bus']]
            except KeyError as e:
                raise ValueError(f"Line connects to unknown bus: {e}")
            
            z = line['r'] + 1j * line['x']
            y = 1.0 / z
            b_half = 1j * line['b'] / 2.0
            
            # Off-diagonal terms
            Y[i, j] -= y
            Y[j, i] -= y
            
            # Diagonal terms
            Y[i, i] += y + b_half
            Y[j, j] += y + b_half
            
        # Add shunt admittances
        for _, shunt in self.shunts.iterrows():
            if shunt['bus'] in bus_id_to_idx:
                i = bus_id_to_idx[shunt['bus']]
                Y[i, i] += shunt['g_shunt'] + 1j * shunt['b_shunt']
                
        self.Y_bus = Y
        return Y
    
    def get_initial_guess(self) -> np.ndarray:
        """
        Return initial guess vector [theta_0, ..., theta_n-1, V_0, ..., V_n-1]
        """
        n = len(self.buses)
        # Default flat start: theta = 0, V = 1.0
        # But we use actual values from buses dataframe if available
        theta = np.radians(self.buses['v_ang'].values.astype(float))
        v = self.buses['v_mag'].values.astype(float)
        
        return np.concatenate([theta, v])
    
    def get_power_injections(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate net specified power injections (Gen - Load) for each bus.
        Returns (P_spec, Q_spec) arrays.
        """
        n = len(self.buses)
        bus_id_to_idx = {bid: i for i, bid in enumerate(self.buses['id'])}
        
        P_spec = np.zeros(n)
        Q_spec = np.zeros(n)
        
        # Subtract loads
        for _, bus in self.buses.iterrows():
            idx = bus_id_to_idx[bus['id']]
            P_spec[idx] -= bus['p_load']
            Q_spec[idx] -= bus['q_load']
            
        # Add generation
        for _, gen in self.generators.iterrows():
            if gen['bus'] in bus_id_to_idx:
                idx = bus_id_to_idx[gen['bus']]
                P_spec[idx] += gen['p_gen']
                Q_spec[idx] += gen['q_gen']
                
        return P_spec, Q_spec

    def __repr__(self):
        return f"<Network '{self.name}': {len(self.buses)} buses, {len(self.lines)} lines>"
