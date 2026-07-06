Low-Inertia Research Handoff
============================

This page collects the stable links and execution rules for the low-inertia
counterfactual search workflow in QuantumGridOS.

QuantumGridOS Links
-------------------

* QuantumGridOS repository: https://github.com/saralsystems/quantumgridos
* PyPI package: https://pypi.org/project/quantumgridos/
* Low-inertia API pull request: https://github.com/saralsystems/quantumgridos/pull/2
* Install command: ``pip install quantumgridos``

Project Repository
------------------

* Public project repository: https://github.com/sayonsom/low-inertia-quantum-counterfactuals
* Project documentation folder: https://github.com/sayonsom/low-inertia-quantum-counterfactuals/tree/main/docs

Public Handoff Bundle
---------------------

The July 2026 public handoff bundle contains the event data, public test-system
inputs, model variations, run documents, reports, and manuscript artifacts used
for the low-inertia quantum-grid study.

* S3 bucket: ``qgo-low-inertia-public-data-20260706-654777652612``
* S3 object key: ``public/low_inertia_quantum_public_handoff_20260706.zip``
* S3 URI: ``s3://qgo-low-inertia-public-data-20260706-654777652612/public/low_inertia_quantum_public_handoff_20260706.zip``
* SHA256: ``534e4c6b01845f3ac9e48d4fb3f4b0104db025b2f4f6db833eef26ed65bc3fc2``
* Approximate size: 91 MB

The object currently requires a presigned HTTPS URL. Treat signed URLs as bearer
download links. Do not commit expiring signed URLs to source control or package
documentation. Share the signed URL out-of-band, or generate a fresh one from
the owning AWS account:

.. code-block:: bash

   aws s3 presign \
     s3://qgo-low-inertia-public-data-20260706-654777652612/public/low_inertia_quantum_public_handoff_20260706.zip \
     --expires-in 604800

Original Public Data Sources
----------------------------

Use the S3 bundle for the project run. Use these upstream public links for
provenance, licensing, and refreshed downloads.

* `NESO August 2019 historic frequency data <https://www.neso.energy/data-portal/system-frequency-data/august_2019_-_historic_frequency_data>`_
* `NESO 9 August 2019 incident report <https://www.neso.energy/document/152346/download>`_
* `Power Grid Frequency Database <https://power-grid-frequency.org/database/>`_
* `MATPOWER example cases <https://matpower.app/manual/matpower/ExamplematpowerCases.html>`_
* `MATPOWER case39 description <https://matpower.org/docs/ref/matpower5.0/case39.html>`_
* `MATPOWER case118 description <https://matpower.org/docs/ref/matpower5.0/case118.html>`_
* `RTS-GMLC official repository <https://github.com/GridMod/RTS-GMLC>`_
* `NREL RTS-GMLC overview <https://www.nlr.gov/grid/reliability-test-system>`_

Native Catalog API
------------------

QuantumGridOS exposes these links and execution requirements through a simple
Python helper:

.. code-block:: python

   import quantumgridos as qgo

   catalog = qgo.get_low_inertia_public_data_catalog()
   print(catalog["s3_public_handoff_bundle"]["s3_uri"])
   print(catalog["public_sources"]["neso_august_2019_frequency"])
   print(catalog["execution_requirements"]["cuda_required"])

Execution Requirements
----------------------

CUDA/cuOpt is required for the accelerated baseline. The team should:

* run on a CUDA-capable NVIDIA GPU instance or workstation;
* record GPU model, driver, CUDA toolkit, Python, cuOpt, Qiskit, and QuantumGridOS versions;
* use the same package-variable schema for CPU, CUDA/cuOpt, and Qiskit comparisons;
* measure end-to-end wall-clock time, including load, build, solve, postprocess, and validation;
* validate every CUDA/cuOpt-selected candidate with the same reduced grid-physics validator;
* avoid reporting solver-only timing as the headline result.
