#!/usr/bin/env python3
"""
AICO CLI - Command Line Interface for AICO
"""

import sys
import os
import platform
from pathlib import Path

# Fix Windows CMD Unicode issues - proven solution from Stack Overflow
# This must be done BEFORE any other imports that might use stdout
if platform.system() == "Windows":
    # Fix stdout encoding for PyInstaller executables on Windows CMD
    # Source: https://stackoverflow.com/questions/44780476/
    try:
        # Check if we're in a PyInstaller bundle and stdout encoding is problematic
        if getattr(sys, 'frozen', False) and sys.stdout.encoding != 'utf-8':
            # Replace stdout with UTF-8 encoded version
            sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', closefd=False)
            sys.stderr = open(sys.stderr.fileno(), 'w', encoding='utf-8', closefd=False)
    except:
        pass
    
    # Set console code page to UTF-8 for Windows CMD
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except:
        pass
    
    # Set environment variable for Python I/O encoding
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add shared directory to Python path for imports
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent / "shared"

sys.path.insert(0, str(shared_path))

import typer
from rich.console import Console

# Create Rich console - no special handling needed after stdout fix
console = Console()

from commands.config import app as config_app
from commands.version import app as version_app
from commands.database import app as database_app
from commands.security import app as security_app

app = typer.Typer(
    name="aico",
    help="✨ AICO - Your AI Companion CLI",
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]}
)

# Add subcommands
app.add_typer(config_app, name="config", help="📝 Configuration management")
app.add_typer(version_app, name="version", help="📦 Version and build information") 
app.add_typer(database_app, name="db", help="🛢️ Database management")
app.add_typer(security_app, name="security", help="🔐 Security and encryption")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    AICO CLI - Modular system management and versioning
    
    A comprehensive command-line interface for managing AICO's configuration,
    databases, security, and versioning across all system components.
    """
    if ctx.invoked_subcommand is None:
        # Import here to avoid circular imports
        from utils.help_formatter import format_command_help
        
        commands = [
            ("📦", "version", "Manage and synchronize versions across all AICO system parts"),
            ("🛢️", "db", "Database initialization, status, and management"),
            ("🔐", "security", "Master password setup and security management"),
            ("📝", "config", "Configuration management and validation")
        ]
        
        examples = [
            "aico version show",
            "aico security setup", 
            "aico db init",
            "aico config list",
            "aico config get api.port"
        ]
        
        format_command_help(
            console=console,
            title="AICO CLI",
            subtitle="Modular system management and versioning",
            commands=commands,
            examples=examples
        )
        raise typer.Exit()

if __name__ == "__main__":
    app()
