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
        pass  # Expected failure on non-PyInstaller or already UTF-8 systems
    
    # Set console code page to UTF-8 for Windows CMD
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except:
        pass  # Expected failure if ctypes/kernel32 not available or already set
    
    # Set environment variable for Python I/O encoding
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add shared directory to Python path for imports
# This is needed because the CLI module name 'aico' conflicts with the shared package name
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development - shared package is installed as editable
    # But we need to ensure it's accessible before our module imports
    pass  # Development mode - shared package installed via editable install

import typer
from rich.console import Console

# Create Rich console - no special handling needed after stdout fix
console = Console()

from commands.config import app as config_app
from commands.version import app as version_app
from commands.database import app as database_app
from commands.security import app as security_app
from commands.dev import app as dev_app
from commands.logs import app as logs_app
from commands.bus import app as bus_app

app = typer.Typer(
    name="aico",
    help="✨ AICO - Your AI Companion CLI",
    rich_markup_mode="rich",
    context_settings={"help_option_names": []}  # Disable built-in help to use custom formatting
)

# Add subcommands
app.add_typer(config_app, name="config", help="📝 Configuration management")
app.add_typer(version_app, name="version", help="📦 Version and build information") 
app.add_typer(database_app, name="db", help="🛢️ Database management")
app.add_typer(security_app, name="security", help="🔐 Security and encryption")
app.add_typer(logs_app, name="logs", help="📋 Log management and analysis")
app.add_typer(dev_app, name="dev", help="🧹 Development utilities")
app.add_typer(bus_app, name="bus", help="🚌 Message bus management")

# Import and register gateway commands
try:
    from commands import gateway
    app.add_typer(gateway.app, name="gateway", help="🌐 API Gateway management")
except ImportError as e:
    # Gateway commands not available
    pass  # Expected when gateway dependencies not installed - CLI continues without gateway commands

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit.")):
    """
    AICO CLI - Modular system management and versioning
    
    A comprehensive command-line interface for managing AICO's configuration,
    databases, security, and versioning across all system components.
    """
    # Handle both no command and --help flag with same custom formatting
    if ctx.invoked_subcommand is None or help:
        # Import here to avoid circular imports
        from utils.help_formatter import format_command_help
        from utils.platform import get_platform_chars
        
        chars = get_platform_chars()
        
        commands = [
            (chars["package"], "version", "Manage and synchronize versions across all AICO system parts"),
            (chars["database"], "db", "Database initialization, status, and management"),
            (chars["security"], "security", "Master password setup and security management"),
            (chars["config"], "config", "Configuration management and validation"),
            ("🚌", "bus", "Message bus testing, monitoring, and management"),
            ("🌐", "gateway", "API Gateway management and protocol control"),
            ("🧹", "dev", "Development utilities (data cleanup, security reset)")
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
