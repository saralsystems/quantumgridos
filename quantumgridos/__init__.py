"""
QuantumGridOS - Real-time Quantum-Power Systems Interface

A high-performance Python library for integrating quantum computing
with power systems optimization and control.
"""

__version__ = "0.1.7"
__author__ = "Your Name"

import sys
if sys.version_info < (3, 9) or sys.version_info >= (3, 12):
    raise RuntimeError(
        f"QuantumGridOS requires Python 3.9-3.11. You are using {sys.version}"
    )

# Core imports
from .core.quantum_interface import QuantumPowerInterface, PowerSystemData, TCPPowerStreamHandler

# Algorithm imports
from .algorithms.qaoa import (
    PowerSystemQAOA,
    QAOAConfig,
    solve_power_network_partitioning,
    solve_generator_scheduling,
)

from .algorithms.vqe import PowerSystemVQE, VQEConfig, solve_opf_quantum, estimate_power_state

# Power systems imports
from .power_systems.network import (
    PowerNetwork,
    Bus,
    Line,
    Generator,
    UnitCommitmentProblem,
    OptimizationProblem,
)

# Convenience imports
from .power_systems.optimizations import (
    MaxCutOptimizer,
    UnitCommitment,
    OptimalPowerFlow,
    StateEstimation,
)

# Mathematical Innovations
from .innovations.mathematical_innovations import (
    PowerFlowPreservingEncoding,
    QuantumPowerSystemEigenvalue,
    QuantumMultiContingencyAnalysis,
    NoiseAdaptiveGridQAOA,
    QuantumPowerInnovations,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "QuantumPowerInterface",
    "PowerSystemData",
    "TCPPowerStreamHandler",
    # Algorithms
    "PowerSystemQAOA",
    "QAOAConfig",
    "PowerSystemVQE",
    "VQEConfig",
    "solve_power_network_partitioning",
    "solve_generator_scheduling",
    "solve_opf_quantum",
    "estimate_power_state",
    # Power Systems
    "PowerNetwork",
    "Bus",
    "Line",
    "Generator",
    "UnitCommitmentProblem",
    "OptimizationProblem",
    # Optimizations
    "MaxCutOptimizer",
    "UnitCommitment",
    "OptimalPowerFlow",
    "StateEstimation",
    # Mathematical Innovations
    "PowerFlowPreservingEncoding",
    "QuantumPowerSystemEigenvalue",
    "QuantumMultiContingencyAnalysis",
    "NoiseAdaptiveGridQAOA",
    "QuantumPowerInnovations",
]


# Package metadata
def get_version():
    """Return the current version"""
    return __version__


def info():
    """Print package information"""
    print(f"QuantumGridOS v{__version__}")
    print("Real-time Quantum-Power Systems Interface")
    print("Documentation: https://quantumgridos.readthedocs.io")
    print("GitHub: https://github.com/yourusername/quantumgridos")
