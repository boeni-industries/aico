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
        # Check if stdout encoding is problematic (both PyInstaller and development)
        if sys.stdout.encoding != 'utf-8':
            # Replace stdout with UTF-8 encoded version
            sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', closefd=False)
            sys.stderr = open(sys.stderr.fileno(), 'w', encoding='utf-8', closefd=False)
    except:
        pass  # Expected failure if already UTF-8 or other issues
    
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

import logging

import typer
from rich.console import Console

# Create Rich console - no special handling needed after stdout fix
console = Console()

# CLI logging now handled automatically by aico.core.logging
# No manual initialization needed - logs go directly to InfluxDB

# Lazy loading strategy: Check sys.argv and only import the command module we need
# This reduces startup time from 1.2s to <0.2s by avoiding 20+ module imports
import importlib

# Map of command names to module paths
COMMAND_MODULES = {
    "logs": "cli.commands.logs",
    "config": "cli.commands.config",
    "version": "cli.commands.version",
    "security": "cli.commands.security",
    "lmdb": "cli.commands.lmdb",
    "chroma": "cli.commands.chroma",
    "kg": "cli.commands.kg",
    "pg": "cli.commands.pg",
    "influx": "cli.commands.influx",
    "deploy": "cli.commands.deploy",
    "scheduler": "cli.commands.scheduler",
    "emotion": "cli.commands.emotion",
    "dev": "cli.commands.dev",
    "bus": "cli.commands.bus",
    "modelservice": "cli.commands.modelservice",
    "ollama": "cli.commands.ollama",
    "tools": "cli.commands.tools",
    "skills": "cli.commands.skills",
    "gateway": "cli.commands.gateway",
    "agency": "cli.commands.agency",
    "interactions": "cli.commands.interactions",
}

# Check if a specific command was requested
requested_command = None
if len(sys.argv) > 1 and sys.argv[1] in COMMAND_MODULES:
    requested_command = sys.argv[1]

# If a specific command was requested, import only that module and run it directly
if requested_command:
    module = importlib.import_module(COMMAND_MODULES[requested_command])
    # Remove the command name from argv so the subcommand sees the right args
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    module.app()
    sys.exit(0)

# Otherwise, fall back to full CLI with all commands (for help, etc.)
from cli.utils.platform import get_platform_chars
chars = get_platform_chars()

from cli.commands.config import app as config_app
from cli.commands.version import app as version_app
from cli.commands.security import app as security_app
from cli.commands.dev import app as dev_app
from cli.commands.logs import app as logs_app
from cli.commands.bus import app as bus_app
from cli.commands.scheduler import app as scheduler_app
from cli.commands.tools import app as tools_app
from cli.commands.skills import app as skills_app
from cli.commands.modelservice import app as modelservice_app
from cli.commands.ollama import app as ollama_app
from cli.commands.lmdb import app as lmdb_app
from cli.commands.chroma import app as chroma_app
from cli.commands.kg import app as kg_app
from cli.commands.emotion import app as emotion_app
from cli.commands.pg import app as pg_app
from cli.commands.influx import app as influx_app
from cli.commands.deploy import app as deploy_app

app = typer.Typer(
    name="aico",
    help=f"{chars['sparkle']} AICO - Your AI Companion CLI",
    rich_markup_mode="rich",
    context_settings={"help_option_names": []}
)

app.add_typer(config_app, name="config", help=f"{chars['config']} Configuration management")
app.add_typer(version_app, name="version", help=f"{chars['package']} Version and build information") 
app.add_typer(lmdb_app, name="lmdb", help=f"{chars['database']} LMDB working memory management")
app.add_typer(kg_app, name="kg", help="💡 Knowledge graph management")
app.add_typer(pg_app, name="pg", help=f"{chars['database']} Postgres/Timescale backend management (experimental)")
app.add_typer(influx_app, name="influx", help=f"{chars['database']} InfluxDB time-series database management")
app.add_typer(deploy_app, name="deploy", help=f"{chars['dev']} Deployment orchestration for Postgres/InfluxDB backends")
app.add_typer(security_app, name="security", help=f"{chars['security']} Security and encryption")
app.add_typer(logs_app, name="logs", help=f"{chars['logs']} Log management and analysis")
app.add_typer(scheduler_app, name="scheduler", help="⏰ Task scheduler management")
app.add_typer(emotion_app, name="emotion", help="🎭 Emotional simulation management")
app.add_typer(dev_app, name="dev", help=f"{chars['dev']} Development utilities")
app.add_typer(bus_app, name="bus", help=f"{chars['bus']} Message bus management")
app.add_typer(modelservice_app, name="modelservice", help="🤖 Model service management")
app.add_typer(ollama_app, name="ollama", help="🦙 Ollama model management")
app.add_typer(tools_app, name="tools", help="🛠 Agency tool inspection and live execution")
app.add_typer(skills_app, name="skills", help="🎯 Agency skills inspection and live execution")
app.add_typer(chroma_app, name="chroma", help=f"{chars['database']} ChromaDB semantic memory management")

try:
    from cli.commands import gateway
    app.add_typer(gateway.app, name="gateway", help=f"{chars['gateway']} API Gateway management")
except ImportError:
    pass

try:
    from cli.commands import agency
    app.add_typer(agency.app, name="agency", help="🎯 Agency system control (intentions, values, policies)")
except ImportError:
    pass

try:
    from cli.commands import interactions
    app.add_typer(interactions.app, name="interactions", help="💬 Interaction request testing and simulation")
except ImportError:
    pass

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit.")):
    """AICO CLI - Modular system management and versioning.

    For CLI usage we suppress non-error log output on the console by
    constraining any stream handlers to ERROR level. This keeps commands
    like `aico tools ls` and `aico skills ls` clean while still allowing
    error logs to surface.
    """

    # Restrict console logging to errors only for CLI invocations
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(logging.ERROR)

    # Ensure noisy libraries also respect ERROR-only console policy
    logging.getLogger("shared.security").setLevel(logging.ERROR)
    logging.getLogger("shared.security.service_auth").setLevel(logging.ERROR)
    logging.getLogger("shared.security.transport_identity").setLevel(logging.ERROR)
    logging.getLogger("shared.security.transport").setLevel(logging.ERROR)
    # Handle both no command and --help flag with same custom formatting
    if ctx.invoked_subcommand is None or help:
        # Import here to avoid circular imports
        from cli.utils.help_formatter import format_command_help
        from cli.utils.platform import get_platform_chars
        
        chars = get_platform_chars()
        
        commands = [
            (chars["package"], "version", "Manage and synchronize versions across all AICO system parts"),
            (chars["database"], "lmdb", "LMDB working memory management"),
            (chars["database"], "chroma", "ChromaDB semantic memory management"),
            (chars["database"], "pg", "PostgreSQL database management"),
            (chars["database"], "influx", "InfluxDB time-series database management"),
            ("🚀", "deploy", "Deployment orchestration for Postgres/InfluxDB backends"),
            ("💡", "kg", "Knowledge graph management and inspection"),
            (chars["security"], "security", "Master password setup and security management"),
            (chars["config"], "config", "Configuration management and validation"),
            (chars["logs"], "logs", "Log management and analysis"),
            ("⏰", "scheduler", "Task scheduler management"),
            ("🎭", "emotion", "Emotional simulation state management"),
            ("🚌", "bus", "Message bus testing, monitoring, and management"),
            ("🌐", "gateway", "API Gateway management and protocol control"),
            ("🤖", "modelservice", "Model service management and control"),
            ("🦙", "ollama", "Ollama model management and operations"),
            ("🎯", "agency", "Agency system control (intentions, values, policies, lessons)"),
            ("💬", "interactions", "Interaction request testing and simulation"),
            ("🧹", "dev", "Development utilities (data cleanup, security reset)")
        ]
        
        examples = [
            "aico version show",
            "aico security setup", 
            "aico db init",
            "aico influx status",
            "aico scheduler ls",
            "aico emotion status",
            "aico config list"
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
