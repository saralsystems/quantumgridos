Algorithms Module
=================

The algorithms module provides quantum algorithm implementations for power system optimization.

QAOA (Quantum Approximate Optimization Algorithm)
--------------------------------------------------

.. automodule:: quantumgridos.algorithms.qaoa
   :members:
   :undoc-members:
   :show-inheritance:

PowerSystemQAOA
~~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.algorithms.qaoa.PowerSystemQAOA
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

QAOAConfig
~~~~~~~~~~

.. autoclass:: quantumgridos.algorithms.qaoa.QAOAConfig
   :members:
   :undoc-members:
   :show-inheritance:

VQE (Variational Quantum Eigensolver)
--------------------------------------

.. automodule:: quantumgridos.algorithms.vqe
   :members:
   :undoc-members:
   :show-inheritance:

PowerSystemVQE
~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.algorithms.vqe.PowerSystemVQE
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

VQEConfig
~~~~~~~~~

.. autoclass:: quantumgridos.algorithms.vqe.VQEConfig
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

QAOA for MaxCut
~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.algorithms import PowerSystemQAOA, QAOAConfig
   from quantumgridos.power_systems import PowerNetwork

   # Configure QAOA
   config = QAOAConfig(
       p=3,
       optimizer='cobyla',
       max_iter=100
   )

   # Create network
   network = PowerNetwork.from_ieee_case(14)

   # Initialize QAOA
   qaoa = PowerSystemQAOA(config=config)

   # Solve MaxCut
   result = qaoa.solve_maxcut(network)
   print(f"Optimal partition: {result['partition']}")

QAOA for Unit Commitment
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.algorithms import PowerSystemQAOA

   generators = [
       {'pmin': 50, 'pmax': 200, 'cost': 1000},
       {'pmin': 20, 'pmax': 100, 'cost': 1500}
   ]

   demand = [150, 180, 200]

   qaoa = PowerSystemQAOA()
   result = qaoa.solve_unit_commitment(generators, demand)
   print(f"Schedule: {result['schedule']}")

VQE for State Estimation
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.algorithms import PowerSystemVQE, VQEConfig

   config = VQEConfig(
       optimizer='slsqp',
       ansatz='efficient_su2'
   )

   vqe = PowerSystemVQE(config=config)
   result = vqe.solve_state_estimation(network, measurements)
   print(f"Estimated states: {result['states']}")

Configuration Options
---------------------

QAOA Parameters
~~~~~~~~~~~~~~~

:p: Number of QAOA layers (default: 1)
:optimizer: Classical optimizer ('cobyla', 'slsqp', 'adam') (default: 'cobyla')
:max_iter: Maximum optimization iterations (default: 100)
:shots: Number of measurement shots (default: 1024)
:mixer: Mixer Hamiltonian type ('x', 'xy') (default: 'x')
:init_params: Parameter initialization ('random', 'zero', 'warm_start') (default: 'random')

VQE Parameters
~~~~~~~~~~~~~~

:optimizer: Classical optimizer (default: 'slsqp')
:max_iter: Maximum iterations (default: 200)
:ansatz: Variational form ('real_amplitudes', 'efficient_su2', 'excitation_preserving') (default: 'real_amplitudes')
:shots: Number of shots (default: 2048)
:convergence_tol: Convergence tolerance (default: 1e-6)

Performance Tips
----------------

1. **Number of Layers**: Start with p=1 for QAOA, increase if needed
2. **Optimizer Choice**: Use 'cobyla' for noisy backends, 'slsqp' for simulators
3. **Shots**: More shots = better accuracy but slower
4. **Warm Start**: Use previous solutions to initialize parameters

See Also
--------

* :doc:`power_systems` - Power system modeling
* :doc:`core` - Core interface
* :doc:`../tutorials/qaoa` - QAOA tutorial
* :doc:`../tutorials/vqe` - VQE tutorial
