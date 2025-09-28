#!/usr/bin/env python3
"""
AICO Memory Intelligence Evaluator - Beautiful CLI Runner

Award-winning visual CLI interface that leverages existing AICO modules
and provides stunning Typer/Rich output for memory system evaluation.

This is a simple wrapper that delegates to the main CLI module.
"""

import sys
from pathlib import Path

# Import the beautiful CLI
from .cli import app

if __name__ == "__main__":
    app()
