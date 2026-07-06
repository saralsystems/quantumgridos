QuantumGridOS Documentation
============================

**QuantumGridOS** is a high-performance Python library for real-time integration between quantum computers and power systems. It enables solving power system optimization problems using quantum algorithms (QAOA, VQE) with minimal latency TCP/IP data exchange.

.. image:: https://img.shields.io/badge/python-3.8%2B-blue
   :target: https://www.python.org
   :alt: Python 3.8+

.. image:: https://img.shields.io/badge/license-Apache%202.0-green
   :target: https://github.com/saralsystems/quantumgridos/blob/main/LICENSE
   :alt: Apache 2.0 License

.. image:: https://github.com/saralsystems/quantumgridos/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/saralsystems/quantumgridos/actions/workflows/tests.yml
   :alt: Tests

Key Features
------------

* **Real-time TCP/IP streaming** for power systems data exchange
* **Quantum algorithm support**: QAOA, VQE, Grover's
* **Power system optimizations**: Unit commitment, MaxCut, OPF, State estimation
* **Low-latency architecture** with async I/O and buffer management
* **Hardware agnostic**: Works with IBM Quantum, IonQ, Rigetti, AWS Braket, simulators
* **Mathematical innovations**: Kirchhoff-preserving encoding, quantum eigenvalue, contingency analysis

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install quantumgridos

Basic Example
~~~~~~~~~~~~~

.. code-block:: python

   import quantumgridos as qgo

   # Create a power network (IEEE 14-bus test case)
   network = qgo.PowerNetwork.from_ieee_case(14)

   # Create an optimizer
   optimizer = qgo.MaxCutOptimizer(
       network=network,
       algorithm='qaoa',
       layers=3
   )

   # Solve the partitioning problem
   result = optimizer.solve()
   print(result)

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   low_inertia_handoff
   user_guide/index
   tutorials/index
   examples/index

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/algorithms
   api/power_systems
   api/backends
   api/innovations

.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   contributing
   changelog
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Links
=====

* **GitHub Repository**: https://github.com/saralsystems/quantumgridos
* **PyPI Package**: https://pypi.org/project/quantumgridos/
* **Issue Tracker**: https://github.com/saralsystems/quantumgridos/issues

Support
=======

For questions or issues:

* **Email**: contact@saralsystems.com
* **GitHub Issues**: https://github.com/saralsystems/quantumgridos/issues

License
=======

This project is licensed under the Apache License 2.0 - see the `LICENSE <https://github.com/saralsystems/quantumgridos/blob/main/LICENSE>`_ file for details.

Citation
========

If you use QuantumGridOS in research, please cite:

.. code-block:: bibtex

   @software{quantumgridos,
     title = {QuantumGridOS: Real-time Quantum-Power Systems Interface},
     author = {Saral Systems},
     year = {2025},
     url = {https://github.com/saralsystems/quantumgridos},
     license = {Apache-2.0}
   }
