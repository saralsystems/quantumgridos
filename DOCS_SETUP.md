# Documentation Setup Guide

Your QuantumGridOS documentation is now fully configured and ready to be hosted!

## Documentation Structure

```
docs/
├── source/
│   ├── conf.py              # Sphinx configuration
│   ├── index.rst            # Main documentation page
│   ├── installation.rst     # Installation guide
│   ├── quickstart.rst       # Quick start guide
│   ├── api/                 # API documentation
│   │   ├── core.rst
│   │   ├── algorithms.rst
│   │   ├── power_systems.rst
│   │   ├── backends.rst
│   │   └── innovations.rst
│   ├── user_guide/         # User guides
│   │   └── index.rst
│   ├── tutorials/          # Tutorials
│   │   └── index.rst
│   ├── examples/           # Examples
│   │   └── index.rst
│   ├── contributing.rst    # Contributing guide
│   ├── changelog.rst       # Changelog
│   └── license.rst         # License information
├── Makefile                # Build commands
└── requirements.txt        # Doc dependencies
```

## Hosting Options

### Option 1: Read the Docs (Recommended)

**Why Read the Docs?**
- Free for open source projects
- Automatic builds on every commit
- Versioning support
- PDF and ePub downloads
- Search functionality
- Custom domains

**Setup Steps:**

1. **Go to Read the Docs**
   - Visit: https://readthedocs.org/
   - Sign in with your GitHub account

2. **Import Your Project**
   - Click "Import a Project"
   - Select "saralsystems/quantumgridos"
   - Click "Next"

3. **Configure Project**
   - Name: `quantumgridos`
   - Repository URL: `https://github.com/saralsystems/quantumgridos`
   - Default branch: `main`
   - Documentation type: `Sphinx Html`
   - Click "Finish"

4. **Trigger First Build**
   - Click "Build Version"
   - Wait for build to complete (2-3 minutes)

5. **Access Your Docs**
   - Your docs will be available at: `https://quantumgridos.readthedocs.io/`

**Configuration File:**
- `.readthedocs.yaml` is already configured
- Documentation will rebuild automatically on every push to main

### Option 2: GitHub Pages

**Why GitHub Pages?**
- Free hosting
- Integrates directly with GitHub
- Custom domain support
- Automatic HTTPS

**Setup Steps:**

1. **Enable GitHub Pages**
   - Go to: https://github.com/saralsystems/quantumgridos/settings/pages
   - Under "Build and deployment":
     - Source: **GitHub Actions**
   - Save

2. **Push Documentation Workflow**
   - The workflow is already created in `.github/workflows/docs.yml`
   - Push to main branch to trigger first build

3. **Access Your Docs**
   - After build completes, docs will be available at:
   - `https://saralsystems.github.io/quantumgridos/`

4. **Monitor Build**
   - Check: https://github.com/saralsystems/quantumgridos/actions
   - Look for "Build and Deploy Documentation" workflow

## Building Documentation Locally

### Install Dependencies

```bash
pip install -r docs/requirements.txt
pip install sphinx-rtd-theme
```

### Build HTML Documentation

```bash
cd docs
make html
```

### View Documentation

```bash
# On macOS/Linux
open build/html/index.html

# On Windows
start build/html/index.html

# Or use Python's HTTP server
cd build/html
python -m http.server 8000
# Then open: http://localhost:8000
```

### Build PDF Documentation

```bash
cd docs
make latexpdf
```

PDF will be at: `docs/build/latex/quantumgridos.pdf`

### Clean Build

```bash
cd docs
make clean
make html
```

## Updating Documentation

### Adding New API Documentation

1. Create a new `.rst` file in `docs/source/api/`
2. Add autodoc directives:

```rst
New Module
==========

.. automodule:: quantumgridos.newmodule
   :members:
   :undoc-members:
   :show-inheritance:
```

3. Add to `docs/source/api/index.rst` toctree
4. Rebuild documentation

### Adding New Tutorial

1. Create `docs/source/tutorials/new_tutorial.rst`
2. Write tutorial content
3. Add to `docs/source/tutorials/index.rst` toctree
4. Rebuild documentation

### Updating Docstrings

Documentation is auto-generated from code docstrings. Update code and rebuild:

```python
def my_function(param1, param2):
    """
    Brief description.

    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2

    Returns:
        bool: Description of return value

    Example:
        >>> my_function("test", 5)
        True
    """
    return True
```

## Documentation Workflow

### Automatic Updates

1. **Push to Main Branch**
   - Documentation rebuilds automatically
   - Available on Read the Docs within 2-3 minutes
   - Available on GitHub Pages within 5 minutes

2. **Pull Requests**
   - Documentation builds are tested
   - Ensures no broken links or syntax errors

### Manual Builds

Trigger manual build on Read the Docs:
1. Go to: https://readthedocs.org/projects/quantumgridos/
2. Click "Versions"
3. Click "Build" next to "latest"

Trigger manual build on GitHub Pages:
1. Go to: https://github.com/saralsystems/quantumgridos/actions
2. Select "Build and Deploy Documentation"
3. Click "Run workflow"

## Customization

### Changing Theme

Edit `docs/source/conf.py`:

```python
html_theme = 'sphinx_rtd_theme'  # or 'alabaster', 'sphinx_book_theme', etc.
```

### Adding Logo

1. Add logo file to `docs/source/_static/logo.png`
2. Edit `docs/source/conf.py`:

```python
html_logo = '_static/logo.png'
```

### Custom CSS

1. Create `docs/source/_static/custom.css`
2. Edit `docs/source/conf.py`:

```python
html_static_path = ['_static']
html_css_files = ['custom.css']
```

### Add Extensions

Edit `docs/source/conf.py`:

```python
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_tabs.tabs',  # New extension
]
```

Then install: `pip install sphinx-tabs`

## Versioning (Read the Docs)

Read the Docs automatically creates documentation for:
- **latest**: Latest commit on main branch
- **stable**: Latest release tag
- **v0.1.0**: Each git tag

To create a new version:

```bash
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
```

Access versions at:
- Latest: `https://quantumgridos.readthedocs.io/en/latest/`
- Stable: `https://quantumgridos.readthedocs.io/en/stable/`
- v0.1.0: `https://quantumgridos.readthedocs.io/en/v0.1.0/`

## Troubleshooting

### Build Fails on Read the Docs

1. Check build log: https://readthedocs.org/projects/quantumgridos/builds/
2. Common issues:
   - Missing dependencies in `docs/requirements.txt`
   - Syntax errors in `.rst` files
   - Import errors (add mock imports to `conf.py`)

### Build Fails on GitHub Pages

1. Check Actions log: https://github.com/saralsystems/quantumgridos/actions
2. Verify workflow file syntax
3. Ensure GitHub Pages is enabled

### Links Not Working

- Use relative links in `.rst` files: `:doc:`relative/path``
- For external links: \`Link text <URL>\`_
- Check for broken links: `make linkcheck`

### API Documentation Not Generating

1. Verify module is importable: `python -c "import quantumgridos"`
2. Check autodoc configuration in `conf.py`
3. Add module path: `sys.path.insert(0, os.path.abspath('../../'))`

## Best Practices

1. **Write Good Docstrings**
   - Use Google or NumPy style
   - Include parameters, returns, and examples
   - Keep them up-to-date

2. **Test Locally First**
   - Build docs locally before pushing
   - Check for warnings: `make html`
   - View in browser to verify formatting

3. **Keep Dependencies Light**
   - Only include doc-build dependencies in `docs/requirements.txt`
   - Mock heavy dependencies in `conf.py`

4. **Use Cross-References**
   - Link between docs: `:doc:`other_page``
   - Link to API: `:class:`QuantumPowerInterface``
   - Link to methods: `:meth:`solve``

5. **Include Examples**
   - Add code examples to tutorials
   - Use `.. code-block:: python`
   - Test examples to ensure they work

## Quick Commands Reference

```bash
# Build HTML docs
cd docs && make html

# Build PDF docs
cd docs && make latexpdf

# Clean build
cd docs && make clean

# Check for broken links
cd docs && make linkcheck

# Live reload during development (requires sphinx-autobuild)
pip install sphinx-autobuild
sphinx-autobuild docs/source docs/build/html
```

## Next Steps

1. **Set up Read the Docs** (recommended for public docs)
2. **Enable GitHub Pages** (alternative option)
3. **Add documentation badge to README**:

```markdown
[![Documentation](https://readthedocs.org/projects/quantumgridos/badge/?version=latest)](https://quantumgridos.readthedocs.io/en/latest/)
```

4. **Write more tutorials** in `docs/source/tutorials/`
5. **Add examples** in `docs/source/examples/`
6. **Improve docstrings** in code

## Support

For documentation issues:
- Read the Docs: https://docs.readthedocs.io/
- Sphinx: https://www.sphinx-doc.org/
- GitHub Pages: https://docs.github.com/en/pages

---

**Your documentation is ready!** Choose your hosting option and follow the setup steps above.

**Read the Docs**: https://quantumgridos.readthedocs.io/ (after setup)
**GitHub Pages**: https://saralsystems.github.io/quantumgridos/ (after setup)
