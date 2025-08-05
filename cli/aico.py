#!/usr/bin/env python3
"""
AICO CLI - Minimal Entrypoint
"""

import sys

__version__ = "0.0.1"

import typer
from commands import version
from rich.console import Console
import sys
from pathlib import Path

app = typer.Typer()
app.add_typer(version.app, name="version")
console = Console()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """AICO CLI: Modular system management and versioning."""
    # Only show help if there are no further commands/args
    if ctx.invoked_subcommand is None and not ctx.args:
        console.print("[bold cyan]AICO CLI[/bold cyan]\n\nModular system management and versioning.")
        console.print("\nAvailable commands:")
        console.print("  [green]version[/green]   Manage and synchronize versions across all AICO system parts\n")
        raise typer.Exit()

if __name__ == "__main__":
    app()
