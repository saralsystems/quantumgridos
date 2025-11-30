import quantumgridos as qgo
from quantumgridos.utils.visualizer import draw_circuit
import os

# Create a simple 2-bus network (Slack + PQ)
# Using the existing test case folder if available, or creating a minimal one
# For simplicity, let's use the create_network with a dummy file if needed, 
# but better to rely on the one we used before.

# Let's assume examples/test_case_4bus exists from previous steps
# If not, we'll create a minimal one here
if not os.path.exists("examples/viz_test"):
    os.makedirs("examples/viz_test")
    with open("examples/viz_test/bus.csv", "w") as f:
        f.write("id,type,v_mag,v_ang,p_load,q_load,base_kv\n")
        f.write("1,1,1.0,0.0,0.0,0.0,110.0\n")
        f.write("2,3,1.0,0.0,0.5,0.2,110.0\n")
    with open("examples/viz_test/line.csv", "w") as f:
        f.write("from_bus,to_bus,r,x,b,rate_a\n")
        f.write("1,2,0.1,0.2,0.0,100.0\n")

print("Creating network...")
net = qgo.create_network("examples/viz_test", type='csv')

print("Running Quantum Power Flow (HHL Fast)...")
# We use max_iter=1 to ensure we get a circuit even if it doesn't fully converge instantly
success, x, history, circuit = qgo.run_quantum_nr(net, method='hhl_fast', max_iter=2)

print("\nVisualizing Circuit:")
draw_circuit(circuit)

if circuit:
    print("\nCircuit object captured successfully.")
else:
    print("\nFailed to capture circuit.")
