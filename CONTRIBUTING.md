# Contributing to QuantumGridOS

Thank you for your interest in contributing to QuantumGridOS! We welcome contributions from the community.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### 1. Fork and Clone the Repository

```bash
git clone https://github.com/saralsystems/quantumgridos.git
cd quantumgridos
```

### 2. Set Up Development Environment

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .[dev]
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 4. Make Your Changes

- Write clear, concise code
- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed

### 5. Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=quantumgridos tests/

# Run linting
flake8 quantumgridos/
black --check quantumgridos/

# Format code
black quantumgridos/
```

### 6. Commit Your Changes

```bash
git add .
git commit -m "Clear description of changes"
```

Follow these commit message guidelines:
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests when applicable

### 7. Sign the Contributor License Agreement (CLA)

**IMPORTANT**: All contributors must sign a CLA before their contributions can be merged.

#### For Individual Contributors:
- Review and sign [CLA.md](CLA.md)
- Email the signed CLA to contact@saralsystems.com
- Or include the signed CLA in your first pull request

#### For Corporate Contributors:
- Review and sign [CLA-CORPORATE.md](CLA-CORPORATE.md)
- Email the signed CLA to contact@saralsystems.com

### 8. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 9. Create a Pull Request

1. Go to the [QuantumGridOS repository](https://github.com/saralsystems/quantumgridos)
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill out the pull request template
5. Submit the pull request

## Development Guidelines

### Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) Python style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use type hints where applicable
- Write docstrings for all public functions, classes, and modules

Example:

```python
def calculate_quantum_metric(
    network: PowerNetwork,
    algorithm: str = "qaoa"
) -> float:
    """
    Calculate quantum optimization metric for a power network.

    Args:
        network: Power network instance
        algorithm: Quantum algorithm to use ('qaoa' or 'vqe')

    Returns:
        Optimization metric value

    Raises:
        ValueError: If algorithm is not supported
    """
    pass
```

### Testing

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Use pytest for testing
- Mock external dependencies (quantum hardware, network calls)

Example test:

```python
import pytest
from quantumgridos import PowerNetwork, MaxCutOptimizer

def test_maxcut_optimizer():
    """Test MaxCut optimizer with IEEE 14-bus network."""
    network = PowerNetwork.from_ieee_case(14)
    optimizer = MaxCutOptimizer(network=network, algorithm='qaoa')

    result = optimizer.solve()

    assert result is not None
    assert 'partition' in result
    assert len(result['partition']) == 14
```

### Documentation

- Update README.md if adding new features
- Add docstrings to all public APIs
- Update or create example files if applicable
- Keep documentation clear and concise

### Quantum Computing Specific Guidelines

- Always provide simulator fallback for quantum algorithms
- Include error handling for quantum hardware failures
- Document quantum circuit complexity
- Provide classical baseline comparisons where applicable

## Types of Contributions

### Bug Fixes

- Search existing issues first
- Create a new issue if one doesn't exist
- Reference the issue in your pull request

### New Features

- Discuss major features in an issue first
- Break large features into smaller, manageable PRs
- Include tests and documentation
- Update CHANGELOG.md

### Documentation

- Fix typos and improve clarity
- Add examples and tutorials
- Improve API documentation
- Add diagrams where helpful

### Performance Improvements

- Provide benchmarks showing improvement
- Ensure backward compatibility
- Document any trade-offs

## Pull Request Process

1. **Ensure all tests pass** before submitting
2. **Update documentation** as needed
3. **Sign the CLA** if you haven't already
4. **Fill out PR template** completely
5. **Address review feedback** promptly
6. **Keep PR scope focused** - one feature/fix per PR

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for user-facing changes)
- [ ] CLA signed
- [ ] Code follows style guidelines
- [ ] Commit messages are clear

## Review Process

1. Maintainers will review your PR within 5 business days
2. Address feedback and update your PR
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release

## Reporting Bugs

### Before Submitting

- Check existing issues
- Verify it's a bug and not a feature
- Test with the latest version

### Creating a Bug Report

Include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Minimal steps to reproduce the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**:
  - OS and version
  - Python version
  - QuantumGridOS version
  - Quantum backend (if applicable)
- **Code Sample**: Minimal code to reproduce the issue
- **Error Messages**: Full error traceback

Example:

```markdown
### Bug Description
MaxCutOptimizer fails with IEEE 30-bus network

### Steps to Reproduce
1. Create IEEE 30-bus network
2. Initialize MaxCutOptimizer
3. Call solve()

### Expected
Partition result

### Actual
ValueError: Invalid network size

### Environment
- OS: Ubuntu 22.04
- Python: 3.9.10
- QuantumGridOS: 0.1.0
- Backend: qiskit_aer

### Code Sample
\```python
network = PowerNetwork.from_ieee_case(30)
optimizer = MaxCutOptimizer(network=network)
optimizer.solve()  # Fails here
\```
```

## Requesting Features

1. Check if the feature already exists or is planned
2. Create a new issue with the "enhancement" label
3. Describe:
   - Use case and motivation
   - Proposed implementation (if you have ideas)
   - Alternatives considered
   - Impact on existing functionality

## Getting Help

- **Documentation**: https://quantumgridos.readthedocs.io
- **Issues**: https://github.com/saralsystems/quantumgridos/issues
- **Email**: contact@saralsystems.com

## Recognition

Contributors will be:
- Listed in the project's AUTHORS file
- Acknowledged in release notes
- Credited in academic citations (if applicable)

## License

By contributing to QuantumGridOS, you agree that your contributions will be licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

All contributions must be accompanied by a signed CLA. See [CLA.md](CLA.md) for more information.

---

Thank you for contributing to QuantumGridOS! Your efforts help make quantum computing more accessible for power systems optimization.

**Project:** QuantumGridOS
**Maintainer:** Saral Systems
**Contact:** contact@saralsystems.com
**Repository:** https://github.com/saralsystems/quantumgridos
