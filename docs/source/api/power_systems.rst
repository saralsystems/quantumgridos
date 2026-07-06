Power Systems Module
====================

The power systems module provides power network modeling and optimization problems.

Power Network
-------------

.. automodule:: quantumgridos.power_systems.network
   :members:
   :undoc-members:
   :show-inheritance:

PowerNetwork
~~~~~~~~~~~~

.. autoclass:: quantumgridos.power_systems.network.PowerNetwork
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Bus, Line, and Generator Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.power_systems.network.Bus
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: quantumgridos.power_systems.network.Line
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: quantumgridos.power_systems.network.Generator
   :members:
   :undoc-members:
   :show-inheritance:

Optimizations
-------------

.. automodule:: quantumgridos.power_systems.optimizations
   :members:
   :undoc-members:
   :show-inheritance:

MaxCutOptimizer
~~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.power_systems.optimizations.MaxCutOptimizer
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

UnitCommitment
~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.power_systems.optimizations.UnitCommitment
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

OptimalPowerFlow
~~~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.power_systems.optimizations.OptimalPowerFlow
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

StateEstimation
~~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.power_systems.optimizations.StateEstimation
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Low-Inertia Counterfactual Search
---------------------------------

.. automodule:: quantumgridos.power_systems.low_inertia
   :members:
   :undoc-members:
   :show-inheritance:

Public Data Catalog
~~~~~~~~~~~~~~~~~~~

.. autofunction:: quantumgridos.power_systems.low_inertia.get_low_inertia_public_data_catalog

Examples
--------

Creating IEEE Test Cases
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import PowerNetwork

   # IEEE 14-bus system
   network_14 = PowerNetwork.from_ieee_case(14)

   # IEEE 30-bus system
   network_30 = PowerNetwork.from_ieee_case(30)

   # IEEE 57-bus system
   network_57 = PowerNetwork.from_ieee_case(57)

   print(f"14-bus network: {len(network_14.buses)} buses")

Building Custom Networks
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import PowerNetwork

   network = PowerNetwork()

   # Add buses
   network.add_bus(id=1, name='Bus1', vnom=230, bus_type='slack')
   network.add_bus(id=2, name='Bus2', vnom=230, bus_type='pq')
   network.add_bus(id=3, name='Bus3', vnom=230, bus_type='pv')

   # Add lines
   network.add_line(from_bus=1, to_bus=2, r=0.01, x=0.1, b=0.001)
   network.add_line(from_bus=2, to_bus=3, r=0.02, x=0.15, b=0.002)

   # Add generators
   network.add_generator(
       bus=1,
       pmax=100,
       pmin=20,
       qmax=50,
       qmin=-30,
       cost=50
   )

Network Analysis
~~~~~~~~~~~~~~~~

.. code-block:: python

   network = PowerNetwork.from_ieee_case(14)

   # Get network statistics
   print(f"Buses: {len(network.buses)}")
   print(f"Lines: {len(network.lines)}")
   print(f"Generators: {len(network.generators)}")

   # Compute Y-bus matrix
   ybus = network.compute_ybus()
   print(f"Y-bus shape: {ybus.shape}")

   # Convert to graph
   graph = network.to_networkx()
   print(f"Graph nodes: {graph.number_of_nodes()}")

MaxCut Optimization
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import PowerNetwork, MaxCutOptimizer

   network = PowerNetwork.from_ieee_case(14)

   optimizer = MaxCutOptimizer(
       network=network,
       algorithm='qaoa',
       layers=3
   )

   result = optimizer.solve()
   print(f"Partition: {result['partition']}")
   print(f"Cut value: {result['cut_value']}")

Unit Commitment
~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import UnitCommitment

   generators = [
       {'name': 'G1', 'pmin': 50, 'pmax': 200, 'cost': 1000},
       {'name': 'G2', 'pmin': 20, 'pmax': 100, 'cost': 1500}
   ]

   demand = [150, 180, 200, 170]

   uc = UnitCommitment(generators=generators, demand_forecast=demand)
   result = uc.solve()

   print(f"Schedule: {result['schedule']}")
   print(f"Total cost: {result['total_cost']}")

Optimal Power Flow
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import OptimalPowerFlow, PowerNetwork

   network = PowerNetwork.from_ieee_case(30)

   opf = OptimalPowerFlow(network=network, objective='cost_min')
   result = opf.solve()

   print(f"Optimal generation: {result['generation']}")
   print(f"Total cost: {result['cost']}")

State Estimation
~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import StateEstimation, PowerNetwork

   network = PowerNetwork.from_ieee_case(14)

   # Measurement data
   measurements = {
       'v': [1.02, 1.01, 0.99],  # Voltage measurements
       'p': [50, 30, 20],          # Active power
       'q': [10, 5, 3]             # Reactive power
   }

   state_est = StateEstimation(network=network, measurements=measurements)
   result = state_est.solve()

   print(f"Estimated states: {result['states']}")

Network I/O
~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.power_systems import PowerNetwork

   network = PowerNetwork.from_ieee_case(14)

   # Export to JSON
   network.export_to_json('network.json')

   # Import from JSON
   network_loaded = PowerNetwork.from_json('network.json')

   # Export to MATPOWER format
   network.export_to_matpower('network.m')

See Also
--------

* :doc:`algorithms` - Quantum algorithms
* :doc:`core` - Core interface
* :doc:`../tutorials/power_systems` - Power systems tutorial
