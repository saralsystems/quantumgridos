Quick Start Guide
=================

This guide will help you get started with QuantumGridOS in just a few minutes.

Basic Example: MaxCut Optimization
-----------------------------------

The simplest way to use QuantumGridOS is to solve a MaxCut problem for network partitioning:

.. code-block:: python

   import quantumgridos as qgo

   # Step 1: Create a power network
   network = qgo.PowerNetwork.from_ieee_case(14)

   # Step 2: Create an optimizer
   optimizer = qgo.MaxCutOptimizer(
       network=network,
       algorithm='qaoa',
       layers=3
   )

   # Step 3: Solve the problem
   result = optimizer.solve()

   # Step 4: View results
   print(f"Optimal partition: {result['partition']}")
   print(f"Cut value: {result['cut_value']}")

Unit Commitment Example
------------------------

Optimize generator scheduling:

.. code-block:: python

   import quantumgridos as qgo

   # Define generators
   generators = [
       {'name': 'G1', 'pmin': 50, 'pmax': 200, 'cost': 1000},
       {'name': 'G2', 'pmin': 20, 'pmax': 100, 'cost': 1500},
       {'name': 'G3', 'pmin': 30, 'pmax': 150, 'cost': 1200}
   ]

   # Define demand forecast
   demand_forecast = [150, 180, 200, 170]

   # Create unit commitment problem
   uc_problem = qgo.UnitCommitment(
       generators=generators,
       demand_forecast=demand_forecast,
       time_periods=4
   )

   # Solve with quantum algorithm
   solver = qgo.PowerSystemQAOA(config=qgo.QAOAConfig(p=3))
   result = uc_problem.solve(solver)

   print(f"Generator schedule: {result['schedule']}")
   print(f"Total cost: {result['cost']}")

Real-time TCP/IP Streaming
---------------------------

Process power system data in real-time:

.. code-block:: python

   import quantumgridos as qgo
   import asyncio

   # Initialize quantum-power interface
   interface = qgo.QuantumPowerInterface(
       quantum_backend='qiskit_aer',
       tcp_host='localhost',
       tcp_port=5000
   )

   # Define power network
   network = qgo.PowerNetwork.from_ieee_case(14)

   # Create optimizer
   optimizer = qgo.MaxCutOptimizer(network=network, algorithm='qaoa')

   # Process stream
   async def process_stream():
       await interface.start()

       async for data in interface.tcp_stream():
           # Solve optimization problem
           result = await optimizer.solve_async(data)

           # Send result back to power system
           await interface.send_result(result)

           print(f"Processed data at {data.timestamp}")

   # Run
   asyncio.run(process_stream())

Using Different Quantum Backends
---------------------------------

Qiskit Aer Simulator (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import quantumgridos as qgo

   optimizer = qgo.MaxCutOptimizer(
       network=network,
       algorithm='qaoa',
       backend='qiskit_aer'
   )

IBM Quantum Hardware
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import quantumgridos as qgo

   # Initialize IBM backend
   backend_manager = qgo.QuantumBackendManager(
       provider='ibm',
       token='your-ibm-token',
       backend_name='ibmq_qasm_simulator'
   )

   optimizer = qgo.MaxCutOptimizer(
       network=network,
       algorithm='qaoa',
       backend=backend_manager.get_backend()
   )

AWS Braket
~~~~~~~~~~

.. code-block:: python

   import quantumgridos as qgo

   backend_manager = qgo.QuantumBackendManager(
       provider='aws',
       backend_name='SV1'
   )

   optimizer = qgo.MaxCutOptimizer(
       network=network,
       algorithm='qaoa',
       backend=backend_manager.get_backend()
   )

Custom Power Network
--------------------

Create a custom power network:

.. code-block:: python

   import quantumgridos as qgo

   # Initialize empty network
   network = qgo.PowerNetwork()

   # Add buses
   network.add_bus(id=1, name='Bus 1', vnom=230)
   network.add_bus(id=2, name='Bus 2', vnom=230)
   network.add_bus(id=3, name='Bus 3', vnom=230)

   # Add transmission lines
   network.add_line(from_bus=1, to_bus=2, r=0.01, x=0.1)
   network.add_line(from_bus=2, to_bus=3, r=0.02, x=0.15)

   # Add generators
   network.add_generator(bus=1, pmax=100, pmin=20, cost=50)
   network.add_generator(bus=3, pmax=80, pmin=15, cost=60)

   print(f"Network has {len(network.buses)} buses")
   print(f"Network has {len(network.lines)} lines")

VQE Algorithm Example
---------------------

Use Variational Quantum Eigensolver:

.. code-block:: python

   import quantumgridos as qgo

   # Configure VQE
   vqe_config = qgo.VQEConfig(
       optimizer='cobyla',
       max_iter=100,
       ansatz='real_amplitudes'
   )

   # Create VQE solver
   vqe = qgo.PowerSystemVQE(config=vqe_config)

   # Solve state estimation problem
   state_est = qgo.StateEstimation(network=network)
   result = state_est.solve(vqe)

   print(f"Estimated states: {result['states']}")

Mathematical Innovations
------------------------

Kirchhoff-Preserving Encoding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.innovations import PowerFlowPreservingEncoding

   encoder = PowerFlowPreservingEncoding(network)
   circuit = encoder.encode()

   # Circuit preserves Kirchhoff's laws
   print(f"Circuit depth: {circuit.depth()}")

Quantum Eigenvalue Computation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.innovations import QuantumPowerSystemEigenvalue

   eigenvalue_solver = QuantumPowerSystemEigenvalue(network)
   eigenvalues = eigenvalue_solver.compute()

   print(f"System eigenvalues: {eigenvalues}")

Multi-Contingency Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.innovations import QuantumMultiContingencyAnalysis

   contingency = QuantumMultiContingencyAnalysis(network, k=2)
   critical_contingencies = contingency.analyze()

   print(f"Found {len(critical_contingencies)} critical contingencies")

Configuration Options
---------------------

QAOA Configuration
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = qgo.QAOAConfig(
       p=3,                    # Number of QAOA layers
       optimizer='cobyla',     # Classical optimizer
       max_iter=100,          # Maximum iterations
       shots=1024,            # Number of shots
       mixer='x',             # Mixer Hamiltonian
       init_params='random'   # Parameter initialization
   )

VQE Configuration
~~~~~~~~~~~~~~~~~

.. code-block:: python

   config = qgo.VQEConfig(
       optimizer='slsqp',
       max_iter=200,
       ansatz='efficient_su2',
       shots=2048,
       convergence_tol=1e-6
   )

Next Steps
----------

* Read the :doc:`user_guide/index` for detailed explanations
* Explore :doc:`tutorials/index` for advanced use cases
* Check :doc:`examples/index` for complete working examples
* Review the :doc:`api/core` for detailed API documentation

Common Issues
-------------

**Import Error**
   Make sure QuantumGridOS is installed: ``pip install quantumgridos``

**Backend Not Available**
   Install quantum hardware support: ``pip install quantumgridos[hardware]``

**TCP Connection Failed**
   Ensure the TCP server is running and the port is correct

For more help, see the :doc:`user_guide/troubleshooting` section or open an issue on `GitHub <https://github.com/saralsystems/quantumgridos/issues>`_.
