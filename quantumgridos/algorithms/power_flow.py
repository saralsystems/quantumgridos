
import numpy as np
from quantumgridos.core.network import Network
from quantumgridos.algorithms.quantum_solvers import QuantumLinearSolver, QuantumGradientEstimator

class PowerFlowSolver:
    def __init__(self, network: Network):
        self.net = network
        self.linear_solver = QuantumLinearSolver()
        self.gradient_estimator = QuantumGradientEstimator()
        
    def get_unknown_indices(self) -> list:
        """Get indices of unknown variables in the state vector x."""
        n = len(self.net.buses)
        indices = []
        
        # Theta indices (0 to n-1)
        for i, bus in self.net.buses.iterrows():
            if bus['type'] != 1: # Not Slack
                indices.append(i)
                
        # V indices (n to 2n-1)
        for i, bus in self.net.buses.iterrows():
            if bus['type'] == 3: # PQ
                indices.append(n + i)
                
        return indices

    def solve(self, max_iter: int = 10, tol: float = 1e-6, method: str = 'classical', quantum_jacobian: bool = False):
        """
        Run Newton-Raphson Power Flow.
        """
        x = self.net.get_initial_guess()
        P_spec, Q_spec = self.net.get_power_injections()
        unknown_idx = self.get_unknown_indices()
        
        convergence_history = []
        
        print(f"Starting Power Flow (Method: {method})...")
        print(f"Unknown variables: {len(unknown_idx)}")
        
        for i in range(max_iter):
            # 1. Calculate Mismatch
            f = self.calculate_mismatch(x, P_spec, Q_spec)
            error = np.linalg.norm(f, np.inf)
            convergence_history.append(error)
            
            print(f"Iteration {i+1}: Max Mismatch = {error:.6f}")
            
            if error < tol:
                print("Converged!")
                self.update_network(x)
                # Return the last circuit generated (if any)
                return True, x, convergence_history, circuit if 'circuit' in locals() else None
            
            # 2. Calculate Jacobian (Reduced)
            if quantum_jacobian:
                # Wrap mismatch calculation for gradient estimator
                # We only vary unknown variables
                def func_reduced(x_reduced):
                    x_full = x.copy()
                    x_full[unknown_idx] = x_reduced
                    return self.calculate_mismatch(x_full, P_spec, Q_spec)
                
                J = self.gradient_estimator.estimate_jacobian(func_reduced, x[unknown_idx])
            else:
                J = self.calculate_jacobian_reduced(x, unknown_idx, P_spec, Q_spec)
            
            # 3. Solve Linear System: J * dx = f
            try:
                dx, circuit = self.linear_solver.solve(J, f, method=method)
            except np.linalg.LinAlgError:
                print("Jacobian is singular!")
                return False, x, convergence_history, None
            
            # 4. Update State
            x[unknown_idx] = x[unknown_idx] - dx
            
        print("Did not converge within maximum iterations.")
        return False, x, convergence_history, circuit if 'circuit' in locals() else None

    def calculate_jacobian_reduced(self, x: np.ndarray, unknown_idx: list, P_spec, Q_spec) -> np.ndarray:
        """
        Calculate Jacobian with respect to unknown variables only.
        """
        def func_reduced(x_reduced):
            x_full = x.copy()
            x_full[unknown_idx] = x_reduced
            return self.calculate_mismatch(x_full, P_spec, Q_spec)
        
        return self.gradient_estimator.estimate_jacobian(
            func_reduced, 
            x[unknown_idx], 
            epsilon=1e-5
        )

    def calculate_mismatch(self, x: np.ndarray, P_spec: np.ndarray, Q_spec: np.ndarray) -> np.ndarray:
        """
        Calculate mismatch vector f(x) = [P_calc - P_spec, Q_calc - Q_spec]
        Note: We only return mismatch for unknown variables (PQ buses: P&Q, PV buses: P)
        """
        n = len(self.net.buses)
        theta = x[:n]
        v = x[n:]
        
        G = np.real(self.net.Y_bus)
        B = np.imag(self.net.Y_bus)
        
        P_calc = np.zeros(n)
        Q_calc = np.zeros(n)
        
        for i in range(n):
            for j in range(n):
                angle_diff = theta[i] - theta[j]
                P_calc[i] += v[i] * v[j] * (G[i, j] * np.cos(angle_diff) + B[i, j] * np.sin(angle_diff))
                Q_calc[i] += v[i] * v[j] * (G[i, j] * np.sin(angle_diff) - B[i, j] * np.cos(angle_diff))
        
        # Filter mismatches based on bus type
        mismatches = []
        
        for i, bus in self.net.buses.iterrows():
            bus_type = bus['type']
            if bus_type == 1: # Slack
                continue
            elif bus_type == 2: # PV
                mismatches.append(P_calc[i] - P_spec[i])
            elif bus_type == 3: # PQ
                mismatches.append(P_calc[i] - P_spec[i])
                mismatches.append(Q_calc[i] - Q_spec[i])
                
        return np.array(mismatches)

    def calculate_jacobian(self, x: np.ndarray) -> np.ndarray:
        """
        Analytical Jacobian calculation.
        """
        # For simplicity in this implementation, we use finite differences
        # because constructing the analytical Jacobian for general networks 
        # with mixed bus types is verbose. 
        # In a production version, we would implement the full analytical block matrix.
        
        return self.gradient_estimator.estimate_jacobian(
            lambda x_in: self.calculate_mismatch(x_in, *self.net.get_power_injections()), 
            x, 
            epsilon=1e-5
        )

    def update_network(self, x: np.ndarray):
        """Update network dataframe with solution values."""
        n = len(self.net.buses)
        theta = x[:n]
        v = x[n:]
        
        self.net.buses['v_ang'] = np.degrees(theta)
        self.net.buses['v_mag'] = v
