import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path
import sys

def version_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

app = typer.Typer(
    help="Manage and synchronize versions across all AICO system parts.",
    callback=version_callback,
    invoke_without_command=True
)

console = Console()

def get_versions_path():
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle: use sys.executable as base
        exe_path = Path(sys.executable).resolve()
        return (exe_path.parent.parent.parent / "VERSIONS").resolve()
    else:
        # Running from source: use this file's location
        return (Path(__file__).parent.parent.parent / "VERSIONS").resolve()

VERSIONS_PATH = get_versions_path()
PARTS = ["cli", "backend", "frontend", "studio"]


def read_versions():
    """Read the VERSIONS file and return a dict of part -> version."""
    versions = {}
    if not VERSIONS_PATH.exists():
        console.print(f"[red]VERSIONS file not found at {VERSIONS_PATH}")
        raise typer.Exit(1)
    with open(VERSIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                part, version = line.split(":", 1)
                versions[part.strip()] = version.strip()
    return versions

@app.command(
    help="""
Show the version for a system part, or all parts if no part is specified.

Examples:
  aico version show
  aico version show cli
  aico version show all
  aico version show backend
"""
)
def show(
    part: str = typer.Argument(
        None,
        help="Which part to show (cli/backend/frontend/studio/all). If omitted, shows all parts.",
        show_default=False
    )
):
    """
Show the version for a system part, or all parts if no part is specified.

- If [PART] is omitted or 'all', shows all parts' versions.
- Otherwise, shows the version for the specified part.
"""
    versions = read_versions()
    
    if part is None or part == "all":
        # Create modern, styled table
        table = Table(
            title="✨ [bold cyan]AICO System Versions[/bold cyan]",
            title_style="bold cyan",
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        table.add_column("Subsystem", style="bold white", no_wrap=True)
        table.add_column("Version", style="green", justify="left")
        
        # Add rows with clean text (no emojis for proper alignment)
        for p in PARTS:
            v = versions.get(p, "[red]not found[/red]")
            if v != "[red]not found[/red]":
                v = f"[bold green]{v}[/bold green]"
            table.add_row(p, v)
        
        console.print()
        console.print(table)
        console.print()
    else:
        # Single part display with enhanced styling
        v = versions.get(part)
        if v:
            icon = {"cli": "⚡", "backend": "🤖", "frontend": "🖥️", "studio": "⚙️"}.get(part, "📦")
            panel = Panel(
                f"{icon} [bold white]{part}[/bold white]\n[bold green]{v}[/bold green]",
                title="[bold cyan]Version Info[/bold cyan]",
                border_style="bright_blue",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            console.print()
            console.print(panel)
            console.print()
        else:
            console.print(f"\n❌ [red]No version found for subsystem '[bold]{part}[/bold]'[/red]\n")
            raise typer.Exit(1)

# TODO: Implement check, next, bump, history commands

# Supporting functions for version management
def get_project_root():
    """Get the project root directory (parent of cli directory)."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        exe_path = Path(sys.executable).resolve()
        return exe_path.parent.parent.parent
    else:
        # Running from source
        return Path(__file__).parent.parent.parent

def update_cli_version(version: str):
    """Update version in cli/aico.py"""
    cli_file = get_project_root() / "cli" / "aico.py"
    if not cli_file.exists():
        return False
    
    content = cli_file.read_text(encoding='utf-8')
    # Replace __version__ = "x.x.x" with new version
    import re
    new_content = re.sub(
r'__version__\s*=\s*["\'][^"\']*["\']',
        f'__version__ = "{version}"',
        content
    )
    
    if new_content != content:
        cli_file.write_text(new_content, encoding='utf-8')
        return True
    return False

def update_backend_version(version: str):
    """Update version in backend project files"""
    backend_dir = get_project_root() / "backend"
    
    # Check main.py first (current structure)
    main_file = backend_dir / "main.py"
    if main_file.exists():
        content = main_file.read_text(encoding='utf-8')
        import re
        new_content = re.sub(
        r'__version__\s*=\s*["\'][^"\']*["\']',
        f'__version__ = "{version}"',
            content
        )
        if new_content != content:
            main_file.write_text(new_content, encoding='utf-8')
            return True
    
    return False

def update_frontend_version(version: str):
    """Update version in frontend/pubspec.yaml"""
    pubspec_file = get_project_root() / "frontend" / "pubspec.yaml"
    if not pubspec_file.exists():
        return False
    
    content = pubspec_file.read_text(encoding='utf-8')
    import re
    new_content = re.sub(
        r'version:\s*[^\n]+',
        f'version: {version}',
        content
    )
    
    if new_content != content:
        pubspec_file.write_text(new_content, encoding='utf-8')
        return True
    return False

def update_studio_version(version: str):
    """Update version in studio/package.json"""
    package_file = get_project_root() / "studio" / "package.json"
    if not package_file.exists():
        return False
    
    try:
        import json
        with open(package_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'version' in data:
            # Only update if version is different
            if data['version'] != version:
                data['version'] = version
                with open(package_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return True
    except (json.JSONDecodeError, IOError):
        pass
    
    return False

@app.command(
    help="""Sync canonical versions from VERSIONS file to all project files.

Reads the VERSIONS file and updates version strings in:
- cli/aico.py (__version__)
- backend/pyproject.toml or setup.py
- frontend/pubspec.yaml
- studio/package.json

Examples:
  aico version sync
"""
)
def sync():
    """Sync canonical versions from VERSIONS file to all project files."""
    try:
        versions = read_versions()
    except typer.Exit:
        return
    

    
    # Track results
    results = []
    
    # Update each subsystem
    update_functions = {
        "cli": update_cli_version,
        "backend": update_backend_version,
        "frontend": update_frontend_version,
        "studio": update_studio_version
    }
    
    for part in PARTS:
        version = versions.get(part)
        if not version:
            results.append((part, "[red]not found in VERSIONS[/red]"))
            continue
        
        update_func = update_functions[part]
        try:
            success = update_func(version)
            if success:
                results.append((part, f"[bold green]✓ updated to {version}[/bold green]"))
            else:
                results.append((part, "[yellow]⚠ no changes needed[/yellow]"))
        except Exception as e:
            results.append((part, f"[red]✗ error: {str(e)}[/red]"))
    
    # Display results table
    table = Table(
        title="✨ [bold cyan]Version Sync Status[/bold cyan]",
        title_style="bold cyan",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        show_lines=False,
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Subsystem", style="bold white", no_wrap=True)
    table.add_column("Status", style="white", justify="left")
    
    for part, status in results:
        table.add_row(part, status)
    
    console.print(table)
    console.print()
