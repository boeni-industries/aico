"""
Simple setup for AICO shared library.
"""

from setuptools import setup, find_packages

setup(
    name="aico-shared",
    version="0.1.0",
    packages=find_packages(),
    namespace_packages=["aico"],
    install_requires=[
        "cryptography>=41.0.0",
        "keyring>=24.0.0",
    ],
    python_requires=">=3.8",
    zip_safe=False,
)
