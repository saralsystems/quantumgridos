
import os
import numpy as np
import quantumgridos as qgo
from quantumgridos.core.network import Network

def test_csv_import_and_solve():
    print("\n=== Testing CSV Import and Solver ===")
    folder_path = "examples/test_case_4bus"
    
    # 1. Create Network
    net = qgo.create_network(folder_path, type='csv')
    print(f"Network created: {net}")
    print(f"Buses: {len(net.buses)}")
    print(f"Lines: {len(net.lines)}")
    
    # 2. Check Y-bus
    print("\nY-bus shape:", net.Y_bus.shape)
    print("Y-bus (first 2x2 block):\n", net.Y_bus[:2, :2])
    
    # 3. Run Power Flow (Classical)
    print("\n--- Running Classical NR ---")
    success, x, history, circuit = qgo.run_quantum_nr(net, method='classical', max_iter=10)
    
    if success:
        print("Classical Solution:")
        print("Angles (deg):", net.buses['v_ang'].values)
        print("Magnitudes (pu):", net.buses['v_mag'].values)
    else:
        print("Classical solver failed!")

    # 4. Run Power Flow (Quantum HHL Simulation)
    # Reset network to flat start
    net.buses['v_ang'] = 0.0
    net.buses['v_mag'] = 1.0
    net.buses.loc[net.buses['type'] == 1, 'v_mag'] = 1.05
    net.buses.loc[net.buses['type'] == 2, 'v_mag'] = 1.04
    
    print("\n--- Running Quantum NR (HHL Simulated) ---")
    success, x, history, circuit = qgo.run_quantum_nr(net, method='hhl', max_iter=10)
    
    if success:
        print("Quantum Solution:")
        print("Angles (deg):", net.buses['v_ang'].values)
        print("Magnitudes (pu):", net.buses['v_mag'].values)
    else:
        print("Quantum solver failed!")

def test_txt_import():
    print("\n=== Testing TXT Import ===")
    # Create a dummy Y-bus file
    y_bus = np.array([[2-6j, -1+3j], [-1+3j, 2-6j]])
    np.savetxt("examples/test_ybus.txt", y_bus)
    
    net = qgo.create_network("examples/test_ybus.txt", type='txt')
    print(f"Network created from TXT: {net}")
    print("Y-bus:\n", net.Y_bus)
    
    # Clean up
    if os.path.exists("examples/test_ybus.txt"):
        os.remove("examples/test_ybus.txt")

if __name__ == "__main__":
    test_csv_import_and_solve()
    test_txt_import()
