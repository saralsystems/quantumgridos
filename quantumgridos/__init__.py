
from quantumgridos.core.network import Network
from quantumgridos.core.network import Network
from quantumgridos.io.parsers import from_csv, from_txt
from quantumgridos.algorithms.power_flow import PowerFlowSolver
from quantumgridos.power_systems.low_inertia import (
    FrequencySecurityCriteria,
    LowInertiaDynamicLabeler,
    LowInertiaOptimizer,
    LowInertiaOption,
    LowInertiaStudy,
    create_low_inertia_study,
    get_low_inertia_public_data_catalog,
    label_low_inertia_dynamics,
    solve_low_inertia_counterfactual,
)

def create_network(source: str, type: str = 'csv', **kwargs) -> Network:
    """
    Factory function to create a network from various sources.
    
    Args:
        source: Path to file/folder
        type: 'csv' or 'txt'
    """
    if type == 'csv':
        return from_csv(source)
    elif type == 'txt':
        return from_txt(source)
    else:
        raise ValueError(f"Unknown network type: {type}")

def run_quantum_nr(network: Network, **kwargs):
    """
    Run Quantum Newton-Raphson Power Flow on the given network.
    
    Args:
        network: The Network object
        kwargs: Arguments for PowerFlowSolver.solve (method, max_iter, etc.)
    """
    solver = PowerFlowSolver(network)
    success, x, history, circuit = solver.solve(**kwargs)
    
    if success:
        print("Power flow converged successfully.")
    else:
        print("Power flow failed to converge.")
        
    return success, x, history, circuit
