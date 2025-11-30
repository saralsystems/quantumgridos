
import os
import numpy as np
import pandas as pd
from quantumgridos.core.network import Network


def from_csv(folder_path: str) -> Network:
    """
    Create a Network object from a folder containing CSV files.
    Expected files: bus.csv, line.csv. Optional: gen.csv, load.csv.
    """
    net = Network(name=os.path.basename(folder_path))
    
    # Load Buses
    bus_file = os.path.join(folder_path, 'bus.csv')
    if os.path.exists(bus_file):
        df_bus = pd.read_csv(bus_file)
        # Map columns if necessary, assuming standard names for now
        # Expected: id, type, v_mag, v_ang, p_load, q_load, base_kv
        # We can add more robust column mapping later
        for _, row in df_bus.iterrows():
            net.add_bus(
                bus_id=int(row.get('id', row.name + 1)),
                bus_type=int(row.get('type', 3)),
                v_mag=float(row.get('v_mag', 1.0)),
                v_ang=float(row.get('v_ang', 0.0)),
                p_load=float(row.get('p_load', 0.0)),
                q_load=float(row.get('q_load', 0.0)),
                base_kv=float(row.get('base_kv', 110.0))
            )
    else:
        raise FileNotFoundError(f"bus.csv not found in {folder_path}")

    # Load Lines
    line_file = os.path.join(folder_path, 'line.csv')
    if os.path.exists(line_file):
        df_line = pd.read_csv(line_file)
        for _, row in df_line.iterrows():
            net.add_line(
                from_bus=int(row['from_bus']),
                to_bus=int(row['to_bus']),
                r=float(row['r']),
                x=float(row['x']),
                b=float(row.get('b', 0.0)),
                rate_a=float(row.get('rate_a', 0.0))
            )

    # Load Generators
    gen_file = os.path.join(folder_path, 'gen.csv')
    if os.path.exists(gen_file):
        df_gen = pd.read_csv(gen_file)
        for _, row in df_gen.iterrows():
            net.add_generator(
                bus_id=int(row['bus']),
                p_gen=float(row['p_gen']),
                q_gen=float(row.get('q_gen', 0.0)),
                p_min=float(row.get('p_min', 0.0)),
                p_max=float(row.get('p_max', 0.0)),
                q_min=float(row.get('q_min', 0.0)),
                q_max=float(row.get('q_max', 0.0))
            )

    net.build_y_bus()
    return net

def from_txt(file_path: str) -> Network:
    """
    Create a Network object from a text file containing a raw Y-bus matrix.
    The file should contain complex numbers or real/imag parts.
    
    Format: Space or comma separated values. Complex numbers as a+bj.
    """
    try:
        # Try reading as complex numbers directly
        # This is a simple parser, might need more robustness for various formats
        raw_data = np.loadtxt(file_path, dtype=complex)
    except ValueError:
        # Fallback: maybe it's formatted differently
        # For now, assume standard numpy readable format
        raise ValueError(f"Could not parse Y-bus from {file_path}")

    if raw_data.ndim != 2 or raw_data.shape[0] != raw_data.shape[1]:
        raise ValueError("Y-bus must be a square matrix")

    n_buses = raw_data.shape[0]
    net = Network(name=f"From_TXT_{os.path.basename(file_path)}")
    
    # Create dummy buses since we only have Y-bus
    for i in range(n_buses):
        net.add_bus(bus_id=i+1, bus_type=3 if i > 0 else 1) # Bus 1 is slack by default
        
    net.Y_bus = raw_data
    return net


