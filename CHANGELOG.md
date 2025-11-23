# Changelog

All notable changes to QuantumGridOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Planned features will be listed here

### Changed
- Planned changes will be listed here

### Deprecated
- Features planned for removal will be listed here

### Removed
- Removed features will be listed here

### Fixed
- Bug fixes will be listed here

### Security
- Security updates will be listed here

## [0.1.2] - 2025-11-23

### Fixed
- Fixed critical `IndentationError` in `quantumgridos/core/quantum_interface.py` caused by incorrect import statement
- Changed `from qiskit import Aer` to `from qiskit_aer import Aer` to match modern Qiskit package structure (Qiskit 1.0+)
- This fix resolves a blocking issue that prevented the package from being imported

## [0.1.1] - 2025-11-22

### Changed
- Updated Python version compatibility to support Python 3.9-3.11
- Improved package installation configuration

### Fixed
- Fixed package installation issues with missing submodules
- Ensured all subpackages are correctly included during installation

## [0.1.0] - 2025-01-21

### Added
- Initial release of QuantumGridOS
- Core quantum-power systems interface (`QuantumPowerInterface`)
- TCP/IP streaming for real-time power systems data exchange
- QAOA algorithm implementation for power system optimization
  - MaxCut for network partitioning
  - Unit commitment optimization
- VQE algorithm implementation
- Power system network modeling
  - IEEE 14-bus, 30-bus, and 57-bus test cases
  - Custom network creation
  - NetworkX integration
- Quantum backend support
  - Qiskit Aer simulator
  - IBM Quantum hardware
  - Rigetti quantum hardware
  - AWS Braket integration
  - IonQ integration
- Mathematical innovations
  - Power flow preserving quantum encoding (Kirchhoff-law preservation)
  - Quantum eigenvalue computation for power systems
  - Multi-contingency analysis using quantum search
  - Noise-adaptive QAOA for grid optimization
- High-level optimization wrappers
  - MaxCutOptimizer
  - UnitCommitment
  - OptimalPowerFlow
  - StateEstimation
- Comprehensive examples and demos
  - Quick quantum demo
  - Complete example workflow
  - Quantum vs classical benchmarks
  - Real-world use cases
  - Hardware integration examples
- Documentation
  - README with quick start guide
  - Quantum hardware setup guide
  - API documentation structure
- Testing infrastructure
  - pytest configuration
  - Unit test examples
- Development tools
  - Black code formatting
  - Flake8 linting
  - MyPy type checking

### Documentation
- README.md with comprehensive project overview
- CONTRIBUTING.md with contribution guidelines
- CLA.md for individual contributors
- CLA-CORPORATE.md for corporate contributors
- PYPI_PUBLISHING_GUIDE.md for package publishing
- QUANTUM_HARDWARE_SETUP.md for hardware configuration
- Example notebooks and demos

### Infrastructure
- setup.py for package installation
- pyproject.toml for modern Python packaging
- requirements.txt with all dependencies
- MANIFEST.in for package distribution
- .gitignore with comprehensive exclusions
- Apache 2.0 License

---

## Version History

### Version Naming Scheme

- **0.1.x**: Alpha releases - Initial development, API may change
- **0.x.x**: Beta releases - Feature complete, API stabilizing
- **1.x.x**: Stable releases - Production ready, semantic versioning

### Upgrade Guide

When upgrading between versions, please refer to the migration guides:

- [Migration to 1.0.0](docs/migrations/to_1.0.0.md) *(when available)*

---

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to this project.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

**Project:** QuantumGridOS
**Maintainer:** Saral Systems
**Repository:** https://github.com/saralsystems/quantumgridos
