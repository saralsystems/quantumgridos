# GitHub Setup for Automatic PyPI Publishing

Your QuantumGridOS package has been successfully published to PyPI! The repository is configured with CI/CD workflows that will automatically publish new versions when you push to the main branch.

## Current Status

✅ Repository pushed to GitHub: https://github.com/saralsystems/quantumgridos
✅ Package published to PyPI: https://pypi.org/project/quantumgridos/
✅ CI/CD workflows configured
⚠️ GitHub Secrets need to be configured for automatic publishing

## Setting Up GitHub Secrets

To enable automatic publishing, you need to add your PyPI API token as a GitHub secret.

### Step 1: Navigate to Repository Settings

1. Go to your repository: https://github.com/saralsystems/quantumgridos
2. Click on **Settings** (top right)
3. In the left sidebar, click **Secrets and variables** → **Actions**

### Step 2: Add PyPI API Token

1. Click the **New repository secret** button
2. Fill in the following:
   - **Name:** `PYPI_API_TOKEN`
   - **Secret:** `<your-pypi-token-here>`
3. Click **Add secret**

**Important:** Keep this token secure and never commit it to the repository!

## How the CI/CD Works

### Automatic Publishing (Main Branch)

Whenever you push to the **main** branch, the workflow:
1. Extracts version from `setup.py`
2. Checks if version already exists on PyPI
3. If new version: Builds → Validates → Publishes → Creates GitHub Release
4. If existing version: Skips publishing (you need to update version number)

### Testing (Pull Requests)

On pull requests, the workflow:
1. Runs tests on multiple OS (Ubuntu, macOS, Windows)
2. Tests Python versions 3.8, 3.9, 3.10, 3.11
3. Checks code formatting and linting
4. Validates package build

### Manual Release

You can also trigger releases manually:
1. Go to **Actions** tab
2. Select **Manual Release** workflow
3. Click **Run workflow**
4. Enter version number (e.g., 0.1.1)
5. Specify if pre-release
6. Click **Run workflow**

## Publishing a New Version

### Method 1: Automatic (Recommended)

1. **Update version number** in both files:
   - `setup.py` (line 15): `version="0.1.1"`
   - `pyproject.toml` (line 6): `version = "0.1.1"`

2. **Update CHANGELOG.md** with changes

3. **Commit and push to main:**
   ```bash
   git add setup.py pyproject.toml CHANGELOG.md
   git commit -m "Bump version to 0.1.1"
   git push origin main
   ```

4. **GitHub Actions automatically publishes** the new version!

5. **Check the workflow:**
   - Go to: https://github.com/saralsystems/quantumgridos/actions
   - Monitor the "Publish to PyPI" workflow

### Method 2: Manual Workflow

1. Go to **Actions** tab
2. Select **Manual Release**
3. Click **Run workflow**
4. Enter new version (e.g., 0.1.1)
5. The workflow updates version files, commits, and publishes

### Method 3: Local Publishing

```bash
# Update version in setup.py and pyproject.toml first

# Clean old builds
rm -rf build/ dist/ *.egg-info

# Build package
python -m build

# Check package
python -m twine check dist/*

# Publish (using environment variable for token)
TWINE_USERNAME=__token__ TWINE_PASSWORD=<your-token> python -m twine upload dist/*
```

## Testing Your Installation

After publishing, test the installation:

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Install from PyPI
pip install quantumgridos

# Test import
python -c "import quantumgridos; print('Success!')"

# Cleanup
deactivate
rm -rf test_env
```

## Workflow Status Badges

Add these badges to your README to show workflow status:

```markdown
[![Tests](https://github.com/saralsystems/quantumgridos/actions/workflows/tests.yml/badge.svg)](https://github.com/saralsystems/quantumgridos/actions/workflows/tests.yml)
[![Publish](https://github.com/saralsystems/quantumgridos/actions/workflows/publish.yml/badge.svg)](https://github.com/saralsystems/quantumgridos/actions/workflows/publish.yml)
```

## Important Links

- **GitHub Repository:** https://github.com/saralsystems/quantumgridos
- **PyPI Package:** https://pypi.org/project/quantumgridos/
- **GitHub Actions:** https://github.com/saralsystems/quantumgridos/actions
- **Issues:** https://github.com/saralsystems/quantumgridos/issues

## Troubleshooting

### "Version already exists on PyPI"

Update the version number in both `setup.py` and `pyproject.toml`. PyPI doesn't allow overwriting existing versions.

### "403 Forbidden" Error

Check that the `PYPI_API_TOKEN` secret is correctly set in GitHub repository settings.

### Workflow Not Running

1. Check that the secret is named exactly: `PYPI_API_TOKEN`
2. Verify the token is valid on PyPI
3. Check workflow file syntax in `.github/workflows/`

### Tests Failing

Review the test output in the Actions tab and fix failing tests before merging to main.

## Security Best Practices

1. ✅ Never commit the PyPI token to the repository
2. ✅ Use GitHub Secrets for storing credentials
3. ✅ Rotate API tokens regularly
4. ✅ Use branch protection rules on main branch
5. ✅ Review all pull requests before merging

## Next Steps

1. ✅ Set up GitHub Secret for PYPI_API_TOKEN (see Step 2 above)
2. Test automatic publishing by updating version and pushing to main
3. Add status badges to README.md
4. Set up branch protection rules (Settings → Branches)
5. Configure code owners (optional)

---

**Congratulations!** Your package is live on PyPI and ready for automatic publishing! 🎉

Install your package:
```bash
pip install quantumgridos
```

View on PyPI: https://pypi.org/project/quantumgridos/
