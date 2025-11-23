
import sys
import traceback

def verify_installation():
    print("Verifying QuantumGridOS installation...")
    try:
        import quantumgridos
        print(f"SUCCESS: Imported quantumgridos version {quantumgridos.__version__}")
        
        from quantumgridos.algorithms.qaoa import PowerSystemQAOA
        print("SUCCESS: Imported PowerSystemQAOA")
        
        from quantumgridos.backends.quantum_backends import QuantumGridBackend
        print("SUCCESS: Imported QuantumGridBackend")
        
        # Check if we can instantiate backend (mock/simulator)
        backend = QuantumGridBackend(provider="simulator")
        print(f"SUCCESS: Instantiated QuantumGridBackend with provider={backend.provider}")
        
        print("Verification passed!")
        return True
    except Exception as e:
        print(f"FAILURE: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_installation()
    sys.exit(0 if success else 1)
