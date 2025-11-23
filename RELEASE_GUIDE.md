# Release Guide for QuantumGridOS

## Prerequisites

1. **PyPI Account**: Create accounts on both:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **API Tokens**: Generate API tokens for authentication:
   - Go to Account Settings → API tokens
   - Create a token with "Entire account" scope
   - Save the token securely (you won't see it again)

3. **Install build tools**:
   ```bash
   pip install --upgrade build twine
   ```

## Release Process

### Step 1: Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf dist/ build/ *.egg-info
```

### Step 2: Build the Package

```bash
# Build source distribution and wheel
python -m build
```

This creates:
- `dist/quantumgridos-0.1.1.tar.gz` (source distribution)
- `dist/quantumgridos-0.1.1-py3-none-any.whl` (wheel)

### Step 3: Test on TestPyPI (Recommended)

```bash
# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# When prompted, use:
# Username: __token__
# Password: <your-testpypi-token>
```

Test the installation:
```bash
# Create a fresh virtual environment
python3.11 -m venv test_env
source test_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ quantumgridos

# Test imports
python -c "import quantumgridos; print(quantumgridos.__version__)"

# Deactivate and remove test environment
deactivate
rm -rf test_env
```

### Step 4: Upload to PyPI (Production)

```bash
# Upload to production PyPI
python -m twine upload dist/*

# When prompted, use:
# Username: __token__
# Password: <your-pypi-token>
```

### Step 5: Verify Installation

```bash
# Install from PyPI
pip install quantumgridos

# Verify
python -c "import quantumgridos; print(quantumgridos.__version__)"
```

## Using GitHub Actions (Automated)

You have a `publish.yml` workflow that can automate this process:

1. **Create a Git tag**:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```

2. **Add PyPI token to GitHub Secrets**:
   - Go to your GitHub repository → Settings → Secrets and variables → Actions
   - Add a new secret named `PYPI_API_TOKEN`
   - Paste your PyPI API token

3. **The workflow will automatically**:
   - Build the package
   - Upload to PyPI when you push a tag

## Alternative: Using `.pypirc` Configuration

Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <your-pypi-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <your-testpypi-token>
```

Then you can upload without entering credentials:
```bash
# Upload to TestPyPI
twine upload -r testpypi dist/*

# Upload to PyPI
twine upload -r pypi dist/*
```

## Version Bumping

Before each release, update the version in:
- `setup.py` (line 15)
- `pyproject.toml` (line 7)
- `quantumgridos/__init__.py` (line 8)

Current version: **0.1.1**

## Troubleshooting

### "File already exists" error
- You cannot re-upload the same version
- Bump the version number and rebuild

### Import errors after installation
- Check dependencies in `requirements.txt`
- Verify Python version compatibility (3.9-3.11)

### Build fails
- Ensure all files are committed
- Check `MANIFEST.in` if you have non-Python files to include

## Post-Release Checklist

- [ ] Create a GitHub release with release notes
- [ ] Update documentation with new version
- [ ] Announce on relevant channels
- [ ] Monitor PyPI download stats
