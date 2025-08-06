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
        console.print("\n✨ [bold cyan]AICO CLI[/bold cyan]")
        console.print("[dim]Modular system management and versioning[/dim]\n")
        console.rule("[bold blue]Available Commands", style="blue")
        console.print("\n📦 [green]version[/green]   Manage and synchronize versions across all AICO system parts\n")
        console.rule("[bold blue]Quick Start", style="blue")
        console.print("\n[yellow]Examples:[/yellow]")
        console.print("  [dim]aico version show[/dim]")
        console.print("  [dim]aico version show cli[/dim]")
        console.print("\n[dim]Use 'aico COMMAND --help' for more information on a command.[/dim]\n")
        raise typer.Exit()

if __name__ == "__main__":
    app()
