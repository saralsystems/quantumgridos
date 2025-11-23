"""
Power System Network Models and Optimization Problems
"""

import numpy as np
import networkx as nx
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import pandas as pd
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Bus:
    """Power system bus/node"""

    bus_id: int
    name: str = ""
    bus_type: str = "PQ"  # PQ, PV, or Slack
    voltage_magnitude: float = 1.0  # p.u.
    voltage_angle: float = 0.0  # radians
    active_power: float = 0.0  # MW
    reactive_power: float = 0.0  # MVAr
    base_kv: float = 138.0
    zone: int = 1

    def to_dict(self) -> Dict:
        return {
            "id": self.bus_id,
            "name": self.name,
            "type": self.bus_type,
            "V": self.voltage_magnitude,
            "angle": self.voltage_angle,
            "P": self.active_power,
            "Q": self.reactive_power,
            "base_kV": self.base_kv,
        }


@dataclass
class Line:
    """Transmission line"""

    line_id: int
    from_bus: int
    to_bus: int
    resistance: float  # p.u.
    reactance: float  # p.u.
    susceptance: float = 0.0  # p.u.
    rating: float = 100.0  # MVA
    length: float = 0.0  # km

    @property
    def impedance(self) -> complex:
        return complex(self.resistance, self.reactance)

    @property
    def admittance(self) -> complex:
        z = self.impedance
        if abs(z) > 0:
            return 1 / z
        return complex(0, 0)


@dataclass
class Generator:
    """Power generator"""

    gen_id: int
    bus_id: int
    name: str = ""
    pmin: float = 0.0  # MW
    pmax: float = 100.0  # MW
    qmin: float = -50.0  # MVAr
    qmax: float = 50.0  # MVAr
    cost_a: float = 0.0  # Quadratic cost coefficient
    cost_b: float = 10.0  # Linear cost coefficient
    cost_c: float = 0.0  # Constant cost
    ramp_rate: float = 10.0  # MW/min
    min_up_time: int = 1  # hours
    min_down_time: int = 1  # hours
    startup_cost: float = 0.0
    shutdown_cost: float = 0.0

    def generation_cost(self, power: float) -> float:
        """Calculate generation cost"""
        return self.cost_a * power**2 + self.cost_b * power + self.cost_c


class PowerNetwork:
    """Power system network model"""

    def __init__(self):
        self.buses: Dict[int, Bus] = {}
        self.lines: Dict[int, Line] = {}
        self.generators: Dict[int, Generator] = {}
        self.loads: Dict[int, Dict] = {}

        self._graph: Optional[nx.Graph] = None
        self._ybus: Optional[np.ndarray] = None

    def add_bus(self, bus: Bus):
        """Add bus to network"""
        self.buses[bus.bus_id] = bus
        self._graph = None  # Invalidate graph cache

    def add_line(self, line: Line):
        """Add transmission line"""
        self.lines[line.line_id] = line
        self._graph = None
        self._ybus = None  # Invalidate Ybus cache

    def add_generator(self, gen: Generator):
        """Add generator"""
        self.generators[gen.gen_id] = gen

    def add_load(self, bus_id: int, p_load: float, q_load: float):
        """Add load at bus"""
        self.loads[bus_id] = {"P": p_load, "Q": q_load}

    @property
    def graph(self) -> nx.Graph:
        """Get NetworkX graph representation"""
        if self._graph is None:
            self._build_graph()
        return self._graph

    def _build_graph(self):
        """Build NetworkX graph from network data"""
        self._graph = nx.Graph()

        # Add nodes
        for bus_id, bus in self.buses.items():
            self._graph.add_node(bus_id, bus=bus, type=bus.bus_type, voltage=bus.voltage_magnitude)

        # Add edges
        for line_id, line in self.lines.items():
            weight = 1.0 / abs(line.impedance) if abs(line.impedance) > 0 else 1.0
            self._graph.add_edge(
                line.from_bus,
                line.to_bus,
                line_id=line_id,
                weight=weight,
                resistance=line.resistance,
                reactance=line.reactance,
                rating=line.rating,
            )

    @property
    def ybus(self) -> np.ndarray:
        """Get admittance matrix (Y-bus)"""
        if self._ybus is None:
            self._build_ybus()
        return self._ybus

    def _build_ybus(self):
        """Build admittance matrix"""
        n = len(self.buses)
        self._ybus = np.zeros((n, n), dtype=complex)

        # Map bus IDs to indices
        bus_idx = {bus_id: i for i, bus_id in enumerate(sorted(self.buses.keys()))}

        for line in self.lines.values():
            i = bus_idx[line.from_bus]
            j = bus_idx[line.to_bus]
            y = line.admittance

            # Off-diagonal elements
            self._ybus[i, j] -= y
            self._ybus[j, i] -= y

            # Diagonal elements
            self._ybus[i, i] += y + 1j * line.susceptance / 2
            self._ybus[j, j] += y + 1j * line.susceptance / 2

    @classmethod
    def from_ieee_case(cls, case: int) -> "PowerNetwork":
        """Load standard IEEE test case

        Args:
            case: IEEE case number (14, 30, 57, 118, 300)
        """
        network = cls()

        if case == 14:
            network._load_ieee14()
        elif case == 30:
            network._load_ieee30()
        elif case == 57:
            network._load_ieee57()
        else:
            raise ValueError(f"IEEE case {case} not implemented")

        return network

    def _load_ieee14(self):
        """Load IEEE 14-bus test case"""
        # Buses
        bus_data = [
            (1, "Slack", 1.06, 0.0),
            (2, "PV", 1.045, -4.98),
            (3, "PV", 1.01, -12.72),
            (4, "PQ", 1.019, -10.33),
            (5, "PQ", 1.02, -8.78),
            (6, "PV", 1.07, -14.22),
            (7, "PQ", 1.062, -13.37),
            (8, "PV", 1.09, -13.36),
            (9, "PQ", 1.056, -14.94),
            (10, "PQ", 1.051, -15.1),
            (11, "PQ", 1.057, -14.79),
            (12, "PQ", 1.055, -15.07),
            (13, "PQ", 1.05, -15.16),
            (14, "PQ", 1.036, -16.04),
        ]

        for bus_id, bus_type, v_mag, v_ang in bus_data:
            self.add_bus(
                Bus(
                    bus_id=bus_id,
                    bus_type=bus_type,
                    voltage_magnitude=v_mag,
                    voltage_angle=np.radians(v_ang),
                )
            )

        # Lines
        line_data = [
            (1, 1, 2, 0.01938, 0.05917, 0.0528),
            (2, 1, 5, 0.05403, 0.22304, 0.0492),
            (3, 2, 3, 0.04699, 0.19797, 0.0438),
            (4, 2, 4, 0.05811, 0.17632, 0.034),
            (5, 2, 5, 0.05695, 0.17388, 0.0346),
            (6, 3, 4, 0.06701, 0.17103, 0.0128),
            (7, 4, 5, 0.01335, 0.04211, 0.0),
            (8, 4, 7, 0.0, 0.20912, 0.0),
            (9, 4, 9, 0.0, 0.55618, 0.0),
            (10, 5, 6, 0.0, 0.25202, 0.0),
            (11, 6, 11, 0.09498, 0.19890, 0.0),
            (12, 6, 12, 0.12291, 0.25581, 0.0),
            (13, 6, 13, 0.06615, 0.13027, 0.0),
            (14, 7, 8, 0.0, 0.17615, 0.0),
            (15, 7, 9, 0.0, 0.11001, 0.0),
            (16, 9, 10, 0.03181, 0.08450, 0.0),
            (17, 9, 14, 0.12711, 0.27038, 0.0),
            (18, 10, 11, 0.08205, 0.19207, 0.0),
            (19, 12, 13, 0.22092, 0.19988, 0.0),
            (20, 13, 14, 0.17093, 0.34802, 0.0),
        ]

        for line_id, from_bus, to_bus, r, x, b in line_data:
            self.add_line(
                Line(
                    line_id=line_id,
                    from_bus=from_bus,
                    to_bus=to_bus,
                    resistance=r,
                    reactance=x,
                    susceptance=b,
                    rating=100.0,
                )
            )

        # Generators
        gen_data = [
            (1, 1, 0, 332.4, 10, 0.02),
            (2, 2, 0, 140, 15, 0.025),
            (3, 3, 0, 100, 30, 0.03),
            (6, 6, 0, 100, 40, 0.04),
            (8, 8, 0, 100, 35, 0.035),
        ]

        for gen_id, bus_id, pmin, pmax, cost_b, cost_a in gen_data:
            self.add_generator(
                Generator(
                    gen_id=gen_id, bus_id=bus_id, pmin=pmin, pmax=pmax, cost_a=cost_a, cost_b=cost_b
                )
            )

        # Loads
        load_data = [
            (2, 21.7, 12.7),
            (3, 94.2, 19.0),
            (4, 47.8, -3.9),
            (5, 7.6, 1.6),
            (6, 11.2, 7.5),
            (9, 29.5, 16.6),
            (10, 9.0, 5.8),
            (11, 3.5, 1.8),
            (12, 6.1, 1.6),
            (13, 13.5, 5.8),
            (14, 14.9, 5.0),
        ]

        for bus_id, p_load, q_load in load_data:
            self.add_load(bus_id, p_load, q_load)

    def _load_ieee30(self):
        """Load IEEE 30-bus test case"""
        # Implementation similar to IEEE 14
        pass

    def _load_ieee57(self):
        """Load IEEE 57-bus test case"""
        pass

    def to_quantum_encoding(self) -> Dict[str, np.ndarray]:
        """Convert network to quantum-ready encoding"""

        # State vector for amplitude encoding
        state_vector = []

        # Bus voltages and angles
        for bus_id in sorted(self.buses.keys()):
            bus = self.buses[bus_id]
            state_vector.append(bus.voltage_magnitude)
            state_vector.append(bus.voltage_angle / np.pi)  # Normalize

        # Line flows (simplified)
        for line in self.lines.values():
            # Estimate power flow
            v1 = self.buses[line.from_bus].voltage_magnitude
            v2 = self.buses[line.to_bus].voltage_magnitude
            theta = self.buses[line.from_bus].voltage_angle - self.buses[line.to_bus].voltage_angle

            p_flow = v1 * v2 * np.sin(theta) / line.reactance
            state_vector.append(p_flow / 100)  # Normalize by base

        # Generator outputs
        for gen in self.generators.values():
            bus = self.buses[gen.bus_id]
            state_vector.append(bus.active_power / gen.pmax)  # Normalize

        return {
            "state_vector": np.array(state_vector),
            "adjacency_matrix": nx.to_numpy_array(self.graph),
            "ybus": self.ybus,
            "n_buses": len(self.buses),
            "n_lines": len(self.lines),
            "n_generators": len(self.generators),
        }

    def export_to_json(self, filepath: str):
        """Export network to JSON format"""
        data = {
            "buses": [bus.to_dict() for bus in self.buses.values()],
            "lines": [
                {
                    "id": line.line_id,
                    "from": line.from_bus,
                    "to": line.to_bus,
                    "R": line.resistance,
                    "X": line.reactance,
                    "B": line.susceptance,
                    "rating": line.rating,
                }
                for line in self.lines.values()
            ],
            "generators": [
                {
                    "id": gen.gen_id,
                    "bus": gen.bus_id,
                    "Pmin": gen.pmin,
                    "Pmax": gen.pmax,
                    "cost_b": gen.cost_b,
                    "cost_a": gen.cost_a,
                }
                for gen in self.generators.values()
            ],
            "loads": self.loads,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_json(cls, filepath: str) -> "PowerNetwork":
        """Load network from JSON"""
        with open(filepath, "r") as f:
            data = json.load(f)

        network = cls()

        # Load buses
        for bus_data in data["buses"]:
            network.add_bus(
                Bus(
                    bus_id=bus_data["id"],
                    name=bus_data.get("name", ""),
                    bus_type=bus_data.get("type", "PQ"),
                    voltage_magnitude=bus_data.get("V", 1.0),
                    voltage_angle=bus_data.get("angle", 0.0),
                )
            )

        # Load lines
        for line_data in data["lines"]:
            network.add_line(
                Line(
                    line_id=line_data["id"],
                    from_bus=line_data["from"],
                    to_bus=line_data["to"],
                    resistance=line_data.get("R", 0.01),
                    reactance=line_data.get("X", 0.1),
                    susceptance=line_data.get("B", 0.0),
                    rating=line_data.get("rating", 100),
                )
            )

        # Load generators
        for gen_data in data["generators"]:
            network.add_generator(
                Generator(
                    gen_id=gen_data["id"],
                    bus_id=gen_data["bus"],
                    pmin=gen_data.get("Pmin", 0),
                    pmax=gen_data.get("Pmax", 100),
                    cost_b=gen_data.get("cost_b", 10),
                    cost_a=gen_data.get("cost_a", 0),
                )
            )

        # Load loads
        network.loads = data.get("loads", {})

        return network

    def get_power_flow_jacobian(self) -> np.ndarray:
        """Get Jacobian matrix for Newton-Raphson power flow"""
        n = len(self.buses)
        J = np.zeros((2 * n, 2 * n))

        # Simplified Jacobian calculation
        # In practice, would compute actual partial derivatives

        return J

    def to_scada_format(self) -> bytes:
        """Convert to SCADA/EMS format for real systems"""
        # Binary format for efficient transmission
        data = []

        # Header
        data.append(len(self.buses).to_bytes(2, "big"))
        data.append(len(self.lines).to_bytes(2, "big"))
        data.append(len(self.generators).to_bytes(2, "big"))

        # Bus data
        for bus in self.buses.values():
            data.append(
                struct.pack(
                    "!IffBf",
                    bus.bus_id,
                    bus.voltage_magnitude,
                    bus.voltage_angle,
                    {"PQ": 0, "PV": 1, "Slack": 2}[bus.bus_type],
                    bus.base_kv,
                )
            )

        return b"".join(data)


class OptimizationProblem:
    """Base class for power system optimization problems"""

    def __init__(self, network: PowerNetwork):
        self.network = network

    def to_qubo(self) -> Tuple[Dict, float]:
        """Convert to QUBO formulation"""
        raise NotImplementedError

    def to_ising(self) -> Tuple[np.ndarray, np.ndarray]:
        """Convert to Ising formulation"""
        raise NotImplementedError

    def decode_solution(self, bitstring: str) -> Dict:
        """Decode quantum solution to problem solution"""
        raise NotImplementedError


class UnitCommitmentProblem(OptimizationProblem):
    """Unit commitment optimization"""

    def __init__(self, network: PowerNetwork, demand_forecast: List[float], time_periods: int = 24):
        super().__init__(network)
        self.demand_forecast = demand_forecast
        self.time_periods = time_periods

    def to_qubo(self) -> Tuple[Dict, float]:
        """Convert UC to QUBO"""
        Q = {}

        # Decision variables: x[g,t] = 1 if generator g is on at time t
        n_gens = len(self.network.generators)

        for t in range(self.time_periods):
            demand = (
                self.demand_forecast[t]
                if t < len(self.demand_forecast)
                else self.demand_forecast[-1]
            )

            # Generation cost terms
            for g_idx, (g_id, gen) in enumerate(self.network.generators.items()):
                var_idx = g_idx * self.time_periods + t

                # Linear cost
                Q[(var_idx, var_idx)] = gen.cost_b * gen.pmax

                # Startup cost (if turning on)
                if t > 0:
                    prev_var = g_idx * self.time_periods + (t - 1)
                    Q[(prev_var, var_idx)] = -gen.startup_cost / 2

            # Demand constraint (soft constraint with penalty)
            penalty = 1000

            for g1_idx, (g1_id, gen1) in enumerate(self.network.generators.items()):
                for g2_idx, (g2_id, gen2) in enumerate(self.network.generators.items()):
                    var1 = g1_idx * self.time_periods + t
                    var2 = g2_idx * self.time_periods + t

                    coeff = penalty * gen1.pmax * gen2.pmax / (demand**2) if demand > 0 else 0

                    if var1 == var2:
                        Q[(var1, var2)] = (
                            Q.get((var1, var2), 0) - 2 * penalty * gen1.pmax / demand
                            if demand > 0
                            else 0
                        )
                    else:
                        Q[(var1, var2)] = Q.get((var1, var2), 0) + coeff

        return Q, 0.0

    def decode_solution(self, bitstring: str) -> Dict:
        """Decode UC solution"""
        n_gens = len(self.network.generators)
        schedule = []

        for t in range(self.time_periods):
            period_schedule = []
            total_generation = 0
            total_cost = 0

            for g_idx, (g_id, gen) in enumerate(self.network.generators.items()):
                var_idx = g_idx * self.time_periods + t

                if var_idx < len(bitstring):
                    is_on = bitstring[var_idx] == "1"
                else:
                    is_on = False

                generation = gen.pmax if is_on else 0
                cost = gen.generation_cost(generation) if is_on else 0

                period_schedule.append(
                    {
                        "generator": gen.name or f"Gen_{g_id}",
                        "status": is_on,
                        "generation": generation,
                        "cost": cost,
                    }
                )

                total_generation += generation
                total_cost += cost

            schedule.append(
                {
                    "period": t,
                    "generators": period_schedule,
                    "total_generation": total_generation,
                    "total_cost": total_cost,
                    "demand": self.demand_forecast[t] if t < len(self.demand_forecast) else 0,
                }
            )

        return {"schedule": schedule}


import struct  # Add at top with other imports
