Installation
============

Requirements
------------

* Python 3.8 or higher
* pip package manager

Basic Installation
------------------

Install QuantumGridOS from PyPI:

.. code-block:: bash

   pip install quantumgridos

This will install the core package with all required dependencies.

Development Installation
------------------------

For development, clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/saralsystems/quantumgridos.git
   cd quantumgridos
   pip install -e .[dev]

Optional Dependencies
---------------------

Visualization
~~~~~~~~~~~~~

For plotting and visualization features:

.. code-block:: bash

   pip install quantumgridos[visualization]

This includes:

* matplotlib
* plotly
* seaborn

Quantum Hardware
~~~~~~~~~~~~~~~~

For real quantum hardware support:

.. code-block:: bash

   pip install quantumgridos[hardware]

This includes:

* qiskit-ibmq-provider (IBM Quantum)
* pyquil (Rigetti)
* amazon-braket-sdk (AWS Braket)

All Optional Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~

To install all optional dependencies:

.. code-block:: bash

   pip install quantumgridos[dev,visualization,hardware]

Verifying Installation
----------------------

Verify the installation:

.. code-block:: python

   import quantumgridos as qgo
   print(qgo.__version__)
   # Output: 0.1.0

Run a quick test:

.. code-block:: python

   import quantumgridos as qgo

   # Create a simple network
   network = qgo.PowerNetwork.from_ieee_case(14)
   print(f"Created network with {len(network.buses)} buses")
   # Output: Created network with 14 buses

Dependencies
------------

Core Dependencies
~~~~~~~~~~~~~~~~~

* qiskit >= 0.43.0
* qiskit-aer >= 0.12.0
* qiskit-optimization >= 0.5.0
* numpy >= 1.21.0
* scipy >= 1.7.0
* pandas >= 1.3.0
* networkx >= 2.6.0
* pandapower >= 2.10.0
* asyncio-mqtt >= 0.12.0
* aiofiles >= 0.8.0
* msgpack >= 1.0.0
* protobuf >= 3.19.0
* structlog >= 21.5.0

Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~

* pytest >= 7.0.0
* pytest-cov >= 3.0.0
* pytest-asyncio >= 0.18.0
* black >= 22.0.0
* flake8 >= 4.0.0
* mypy >= 0.950
* sphinx >= 4.5.0
* sphinx-rtd-theme >= 1.0.0

Troubleshooting
---------------

Import Error
~~~~~~~~~~~~

If you encounter import errors, ensure you have the correct Python version:

.. code-block:: bash

   python --version
   # Should be 3.8 or higher

Permission Errors
~~~~~~~~~~~~~~~~~

On some systems, you may need to use:

.. code-block:: bash

   pip install --user quantumgridos

Virtual Environment (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use a virtual environment to avoid conflicts:

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   pip install quantumgridos

Conda Environment
~~~~~~~~~~~~~~~~~

If using Conda:

.. code-block:: bash

   conda create -n qgo python=3.9
   conda activate qgo
   pip install quantumgridos

Upgrading
---------

To upgrade to the latest version:

.. code-block:: bash

   pip install --upgrade quantumgridos

Uninstallation
--------------

To uninstall:

.. code-block:: bash

   pip uninstall quantumgridos

Next Steps
----------

After installation, check out the :doc:`quickstart` guide to get started with QuantumGridOS.
