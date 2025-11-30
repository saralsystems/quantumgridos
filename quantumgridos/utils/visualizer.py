
import matplotlib.pyplot as plt
import numpy as np

def plot_convergence(convergence_history: list, title: str = "Power Flow Convergence"):
    """
    Plot the convergence history (mismatch norm vs iterations).
    """
    plt.figure(figsize=(8, 6))
    plt.semilogy(range(1, len(convergence_history) + 1), convergence_history, 'o-', linewidth=2)
    plt.xlabel('Iteration')
    plt.ylabel('Max Mismatch (p.u.)')
    plt.title(title)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.tight_layout()
    plt.show()

def draw_circuit(circuit, filename: str = None):
    """
    Draw the quantum circuit used in the solver.
    """
    if circuit is None:
        print("No circuit to draw.")
        return
        
    print(circuit.draw(output='text'))
    
    if filename:
        circuit.draw(output='mpl', filename=filename)
        print(f"Circuit diagram saved to {filename}")
