Core Module
===========

The core module provides the main interface for quantum-power systems integration.

Quantum Power Interface
------------------------

.. automodule:: quantumgridos.core.quantum_interface
   :members:
   :undoc-members:
   :show-inheritance:

Main Classes
~~~~~~~~~~~~

QuantumPowerInterface
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: quantumgridos.core.quantum_interface.QuantumPowerInterface
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

TCPPowerStreamHandler
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: quantumgridos.core.quantum_interface.TCPPowerStreamHandler
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

PowerSystemData
^^^^^^^^^^^^^^^

.. autoclass:: quantumgridos.core.quantum_interface.PowerSystemData
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Examples
--------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.core import QuantumPowerInterface

   interface = QuantumPowerInterface(
       quantum_backend='qiskit_aer',
       tcp_host='localhost',
       tcp_port=5000
   )

   await interface.start()

Real-time Processing
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from quantumgridos.core import QuantumPowerInterface

   async def process_data():
       interface = QuantumPowerInterface(
           quantum_backend='qiskit_aer',
           tcp_host='localhost',
           tcp_port=5000
       )

       await interface.start()

       async for data in interface.tcp_stream():
           result = await interface.process_with_quantum(data)
           await interface.send_result(result)

   asyncio.run(process_data())

See Also
--------

* :doc:`algorithms` - Quantum algorithms
* :doc:`power_systems` - Power system modeling
* :doc:`backends` - Quantum backend management
