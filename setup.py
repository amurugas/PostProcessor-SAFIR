"""
setup.py – PostProcessor-SAFIR package configuration.

Install the shared utilities in editable mode for development:

    pip install -e .

This makes `import shared` work from any directory.
"""

from setuptools import find_packages, setup

setup(
    name="postprocessor-safir",
    version="0.1.0",
    description="Post-processing utilities for SAFIR structural fire analysis",
    author="amurugas",
    python_requires=">=3.10",
    packages=find_packages(include=["shared", "shared.*"]),
    install_requires=[
        "lxml>=4.9",
        "pandas>=2.0",
        "openpyxl>=3.1",
    ],
    extras_require={
        "dashboard": ["bokeh>=3.0", "streamlit>=1.30"],
        "dev": [
            "flake8>=7.0",
            "flake8-bugbear>=24.0",
            "pytest>=8.0",
            "pytest-cov>=5.0",
            "mypy>=1.9",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
    ],
)
