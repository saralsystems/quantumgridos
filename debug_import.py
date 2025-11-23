
import sys
import traceback

print(f"Python version: {sys.version}")

try:
    import qiskit
    print(f"qiskit: {qiskit.__version__}")
except ImportError:
    print("qiskit not found")
    traceback.print_exc()

try:
    import qiskit_ibm_runtime
    print(f"qiskit_ibm_runtime: {qiskit_ibm_runtime.__version__}")
except ImportError:
    print("qiskit_ibm_runtime not found")
    traceback.print_exc()

try:
    import qiskit_aer
    print(f"qiskit_aer: {qiskit_aer.__version__}")
except ImportError:
    print("qiskit_aer not found")
    traceback.print_exc()

try:
    from qiskit_aer.primitives import Sampler as AerSampler
    print("Successfully imported AerSampler")
except ImportError:
    print("Failed to import AerSampler")
    traceback.print_exc()
