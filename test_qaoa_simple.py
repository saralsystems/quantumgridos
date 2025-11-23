#!/usr/bin/env python3
"""Simple test of QAOA functionality"""

import networkx as nx
from quantumgridos.algorithms.qaoa import PowerSystemQAOA, QAOAConfig

# Create a simple graph
G = nx.Graph()
G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0)])

# Setup QAOA
qaoa_config = QAOAConfig(layers=2, optimizer="COBYLA", shots=1024)
qaoa_solver = PowerSystemQAOA(qaoa_config)

print("Testing QAOA MaxCut on 4-node graph...")
try:
    result = qaoa_solver.solve_maxcut(G)
    print(f"Success! Eigenvalue: {result['eigenvalue']:.4f}")
    print(f"Best solution: {result['best_solution']}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
