"""
Simple setup for AICO shared library.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = Path(__file__).parent / "requirements.txt"
    if requirements_path.exists():
        with open(requirements_path, 'r', encoding='utf-8') as f:
            requirements = []
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    requirements.append(line)
            return requirements
    return []

setup(
    name="aico-shared",
    version="0.1.0",
    packages=find_packages(),
    # Using implicit namespace packages (PEP 420) - no namespace_packages needed
    install_requires=read_requirements(),
    python_requires=">=3.8",
    zip_safe=False,
)
