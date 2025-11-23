"""
Setup configuration for QuantumGridOS
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="quantumgridos",
    version="0.1.0",
    author="Saral Systems",
    author_email="contact@saralsystems.com",
    description="Real-time quantum computing interface for power systems optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/saralsystems/quantumgridos",
    license="Apache-2.0",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8, <3.12",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "sphinx>=4.5.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "visualization": [
            "matplotlib>=3.5.0",
            "plotly>=5.0.0",
            "seaborn>=0.11.0",
        ],
        "hardware": [
            "qiskit-ibmq-provider>=0.19.0",
            "pyquil>=3.0.0",
            "amazon-braket-sdk>=1.35.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "quantumgridos=quantumgridos.cli:main",
            "qgo=quantumgridos.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "quantumgridos": ["data/*.json", "data/*.csv"],
    },
)
