Backends Module
===============

The backends module provides quantum backend management for multiple providers.

Quantum Backend Manager
------------------------

.. automodule:: quantumgridos.backends.quantum_backends
   :members:
   :undoc-members:
   :show-inheritance:

QuantumBackendManager
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: quantumgridos.backends.quantum_backends.QuantumBackendManager
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__

Examples
--------

Qiskit Aer Simulator
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.backends import QuantumBackendManager

   backend_manager = QuantumBackendManager(provider='qiskit_aer')
   backend = backend_manager.get_backend()

IBM Quantum
~~~~~~~~~~~

.. code-block:: python

   from quantumgridos.backends import QuantumBackendManager

   backend_manager = QuantumBackendManager(
       provider='ibm',
       token='your-ibm-quantum-token',
       backend_name='ibmq_qasm_simulator'
   )

   backend = backend_manager.get_backend()

AWS Braket
~~~~~~~~~~

.. code-block:: python

   from quantumgridos.backends import QuantumBackendManager

   backend_manager = QuantumBackendManager(
       provider='aws',
       backend_name='SV1'
   )

   backend = backend_manager.get_backend()

Rigetti
~~~~~~~

.. code-block:: python

   from quantumgridos.backends import QuantumBackendManager

   backend_manager = QuantumBackendManager(
       provider='rigetti',
       backend_name='Aspen-M-3'
   )

   backend = backend_manager.get_backend()

IonQ
~~~~

.. code-block:: python

   from quantumgridos.backends import QuantumBackendManager

   backend_manager = QuantumBackendManager(
       provider='ionq',
       token='your-ionq-token'
   )

   backend = backend_manager.get_backend()

Supported Providers
-------------------

* **qiskit_aer**: Qiskit Aer simulator (local, no credentials needed)
* **ibm**: IBM Quantum hardware and simulators
* **aws**: AWS Braket devices and simulators
* **rigetti**: Rigetti quantum computers
* **ionq**: IonQ quantum computers

See Also
--------

* :doc:`../user_guide/quantum_hardware` - Quantum hardware setup guide
* :doc:`core` - Core interface
