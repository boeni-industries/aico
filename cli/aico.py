#!/usr/bin/env python3
"""
AICO CLI - Minimal Entrypoint
"""

import sys

__version__ = "0.0.1"

import typer
from commands import version

app = typer.Typer()
app.add_typer(version.app, name="version")

if __name__ == "__main__":
    app()
