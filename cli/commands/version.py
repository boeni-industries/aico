import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path
import sys
import re
import json

# Import utils
utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(utils_path))
from timezone import format_timestamp_local, get_timezone_suffix

# Standard Rich console - encoding is fixed at app startup
from rich.console import Console

def version_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("show", "Show the version for a subsystem, or all subsystems if no subsystem is specified"),
            ("history", "Show the version history for a subsystem (or all subsystems) using git history"),
            ("sync", "Sync canonical versions from VERSIONS file to all project files"),
            ("check", "Check that all project files match the canonical versions in the VERSIONS file"),
            ("next", "Preview the next version number for a subsystem or all subsystems"),
            ("bump", "Bump the version for a subsystem and update all relevant files")
        ]
        
        examples = [
            "aico version show",
            "aico version show cli", 
            "aico version sync",
            "aico version check",
            "aico version bump cli patch"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="version",
            description="Manage and synchronize versions across all AICO subsystems",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Manage and synchronize versions across all AICO subsystems.",
    callback=version_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)

# Standard Rich console - encoding is fixed at app startup
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
SUBSYSTEMS = ["shared", "cli", "backend", "frontend", "studio"]


def read_versions():
    """Read the VERSIONS file and return a dict of subsystem -> version."""
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
                subsystem, version = line.split(":", 1)
                versions[subsystem.strip()] = version.strip()
    return versions

@app.command(
    help="""
Show the version for a subsystem, or all subsystems if no subsystem is specified.

Examples:
  aico version show
  aico version show cli
  aico version show all
  aico version show backend
"""
)
def show(
    subsystem: str = typer.Argument(
        None,
        help="Which subsystem to show (shared/cli/backend/frontend/studio/all). If omitted, shows all subsystems.",
        show_default=False
    )
):
    """
Show the version for a subsystem, or all subsystems if no subsystem is specified.

- If [SUBSYSTEM] is omitted or 'all', shows all subsystems' versions.
- Otherwise, shows the version for the specified subsystem.
"""
    versions = read_versions()
    
    if subsystem is None or subsystem == "all":
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
        for s in SUBSYSTEMS:
            v = versions.get(s, "[red]not found[/red]")
            if v != "[red]not found[/red]":
                v = f"[bold green]{v}[/bold green]"
            table.add_row(s, v)
        
        console.print()
        console.print(table)
        console.print()
    else:
        # Single subsystem display with enhanced styling
        v = versions.get(subsystem)
        if v:
            icon = {"shared": "📚", "cli": "⚡", "backend": "🤖", "frontend": "🖥️", "studio": "⚙️"}.get(subsystem, "📦")
            panel = Panel(
                f"{icon} [bold white]{subsystem}[/bold white]\n[bold green]{v}[/bold green]",
                title="[bold cyan]Version Info[/bold cyan]",
                border_style="bright_blue",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            console.print()
            console.print(panel)
            console.print()
        else:
            console.print(f"\n❌ [red]No version found for subsystem '[bold]{subsystem}[/bold]'[/red]\n")
            raise typer.Exit(1)

@app.command(
    help="""
Show the version history for a subsystem (or all subsystems) using the git history of the VERSIONS file.

Examples:
  aico version history cli
  aico version history backend
  aico version history all
"""
)
def history(
    subsystem: str = typer.Argument(
        None,
        help="Which subsystem to show history for (shared/cli/backend/frontend/studio/all). If omitted, shows all.",
        show_default=False
    ),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """
    Show the version history for a subsystem (or all subsystems).
    """
    import subprocess
    import re
    import datetime

    versions_path = get_project_root() / "VERSIONS"
    if not versions_path.exists():
        console.print(f"[red]VERSIONS file not found at {versions_path}")
        raise typer.Exit(1)

    # Get git log with patch for VERSIONS file
    try:
        result = subprocess.run([
            "git", "log", "-p", "--", str(versions_path)
        ], capture_output=True, text=True, check=True)
        log = result.stdout
    except Exception as e:
        console.print(f"[red]Error running git log: {e}")
        raise typer.Exit(1)

    # Parse log for version changes
    entries = []
    current_commit = None
    for line in log.splitlines():
        if line.startswith("commit "):
            current_commit = {
                "hash": line.split()[1],
                "author": "",
                "date": "",
                "msg": "",
                "changes": []
            }
        elif line.startswith("Author:") and current_commit:
            current_commit["author"] = line[len("Author:"):].strip()
        elif line.startswith("Date:") and current_commit:
            # Parse Git date and store as ISO format for timezone handling
            dt = line[len("Date:"):].strip()
            try:
                dt_obj = datetime.datetime.strptime(dt, "%a %b %d %H:%M:%S %Y %z")
                # Store as ISO format with timezone for later formatting
                current_commit["date"] = dt_obj.isoformat()
            except Exception:
                current_commit["date"] = dt
        elif line.startswith("    ") and current_commit and not current_commit["msg"]:
            current_commit["msg"] = line.strip()
        elif line.startswith("@@") and current_commit:
            pass  # ignore hunk headers
        elif (line.startswith("+") or line.startswith("-")) and not line.startswith("+++" ) and not line.startswith("---") and current_commit:
            # Only consider version lines
            match = re.match(r"[+-](\w+):\s*([\d\.]+)", line)
            if match:
                current_commit["changes"].append((line[0], match.group(1), match.group(2)))
        elif line.strip() == "" and current_commit and current_commit["changes"]:
            entries.append(current_commit)
            current_commit = None
    if current_commit and current_commit["changes"]:
        entries.append(current_commit)

    # Build history for each subsystem
    history_map = {s: [] for s in SUBSYSTEMS}
    for entry in entries:
        # Group changes by subsystem
        for sign, part, ver in entry["changes"]:
            if part in SUBSYSTEMS:
                history_map[part].append({
                    "commit": entry["hash"],
                    "author": entry["author"],
                    "date": entry["date"],
                    "msg": entry["msg"],
                    "sign": sign,
                    "version": ver
                })

    # Prepare table output
    subsystems_to_show = SUBSYSTEMS if subsystem is None or subsystem == "all" else [subsystem]
    for s in subsystems_to_show:
        changes = history_map[s]
        if not changes:
            console.print(f"[yellow]No history found for {s}[/yellow]")
            continue
        table = Table(
            title=f"✨ [bold cyan]Version History: {s}[/bold cyan]",
            title_style="bold cyan",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        table.add_column("Old", style="white", justify="left")
        table.add_column("New", style="bold green", justify="left")
        table.add_column("Commit", style="dim", justify="left")
        table.add_column("Author", style="white", justify="left")
        # Dynamic date column header based on timezone preference
        date_header = f"Date{get_timezone_suffix(utc)}"
        table.add_column(date_header, style="white", justify="left")
        table.add_column("Message", style="dim", justify="left")

        # Build version change pairs (old, new)
        version_pairs = []
        prev = None
        for change in changes:
            if change["sign"] == "-":
                prev = change["version"]
            elif change["sign"] == "+" and prev is not None:
                version_pairs.append((prev, change["version"], change))
                prev = None
        for old, new, meta in version_pairs:
            # Format timestamp using timezone utility
            formatted_date = format_timestamp_local(meta["date"], show_utc=utc) if meta["date"] and "T" in str(meta["date"]) else meta["date"]
            table.add_row(
                old,
                f"[bold green]{new}[/bold green]",
                meta["commit"][:8],
                meta["author"],
                formatted_date,
                meta["msg"]
            )
        console.print()
        console.print(table)
        console.print()

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
    """Update version in cli/pyproject.toml"""
    cli_file = get_project_root() / "cli" / "pyproject.toml"
    if not cli_file.exists():
        return False
    
    content = cli_file.read_text(encoding='utf-8')
    # Replace version = "x.x.x" with new version
    import re
    new_content = re.sub(
        r'version\s*=\s*["\'][^"\']*["\']',
        f'version = "{version}"',
        content
    )
    
    if new_content != content:
        cli_file.write_text(new_content, encoding='utf-8')
        return True
    return False

# Update version in shared/setup.py
def update_shared_version(version: str):
    """Update version in shared/pyproject.toml"""
    pyproject_file = get_project_root() / "shared" / "pyproject.toml"
    if not pyproject_file.exists():
        return False
    
    content = pyproject_file.read_text(encoding='utf-8')
    # Replace version = "x.x.x" with new version
    import re
    new_content = re.sub(
        r'version\s*=\s*["\'][^"\']*["\']',
        f'version = "{version}"',
        content
    )
    
    if new_content != content:
        pyproject_file.write_text(new_content, encoding='utf-8')
        return True
    return False

# Update version in backend project files
def update_backend_version(version: str):
    """Update version in backend project files (both pyproject.toml and main.py)"""
    backend_dir = get_project_root() / "backend"
    updated = False
    
    # Update pyproject.toml
    pyproject_file = backend_dir / "pyproject.toml"
    if pyproject_file.exists():
        content = pyproject_file.read_text(encoding='utf-8')
        import re
        new_content = re.sub(
            r'version\s*=\s*["\'][^"\']*["\']',
            f'version = "{version}"',
            content
        )
        if new_content != content:
            pyproject_file.write_text(new_content, encoding='utf-8')
            updated = True
    
    # Update main.py __version__
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
            updated = True
    
    return updated

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
    except (json.JSONDecodeError, IOError) as e:
        # Log JSON file operation failure - this could indicate file corruption or permissions
        from rich.console import Console
        console = Console()
        console.print(f"[yellow]Warning: Failed to update package.json version in {package_file}: {e}[/yellow]")
    
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
        "shared": update_shared_version,
        "cli": update_cli_version,
        "backend": update_backend_version,
        "frontend": update_frontend_version,
        "studio": update_studio_version
    }
    
    for element in SUBSYSTEMS:
        version = versions.get(element)
        if not version:
            results.append((element, "[red]not found in VERSIONS[/red]"))
            continue
        
        update_func = update_functions[element]
        try:
            success = update_func(version)
            if success:
                results.append((element, f"[bold green]✓ updated to {version}[/bold green]"))
            else:
                results.append((element, "[yellow]⚠ no changes needed[/yellow]"))
        except Exception as e:
            results.append((element, f"[red]✗ error: {str(e)}[/red]"))
    
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
    
    for subsystem, status in results:
        table.add_row(subsystem, status)
    
    console.print(table)
    console.print()

# === Helper functions to read actual versions from project files ===
# All helpers use 'subsystem' terminology for clarity and consistency.

@app.command(
    help="""
Check that all project files match the canonical versions in the VERSIONS file.

Reports mismatches and exits with error if any are found.

Examples:
  aico version check
  aico version check cli
  aico version check all
  aico version check backend
"""
)
def check(
    subsystem: str = typer.Argument(
        None,
        help="Which subsystem to check (shared/cli/backend/frontend/studio/all). If omitted, checks all subsystems.",
        show_default=False
    )
):
    """
    Check that all project files match the canonical versions in the VERSIONS file.
    """
    versions = read_versions()
    readers = {
        "shared": read_shared_version,
        "cli": read_cli_version,
        "backend": read_backend_version,
        "frontend": read_frontend_version,
        "studio": read_studio_version
    }
    subsystems_to_check = SUBSYSTEMS if subsystem is None or subsystem == "all" else [subsystem]
    mismatches = []
    table = Table(
        title="✨ [bold cyan]Version Check Status[/bold cyan]",
        title_style="bold cyan",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        show_lines=False,
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Subsystem", style="bold white", no_wrap=True)
    table.add_column("Expected", style="white", justify="left")
    table.add_column("Actual", style="white", justify="left")
    table.add_column("Status", style="white", justify="left")
    for s in subsystems_to_check:
        expected = versions.get(s)
        actual = readers[s]()
        if expected is None:
            table.add_row(s, "[red]not found[/red]", "-", "[red]✗ missing in VERSIONS[/red]")
            mismatches.append(s)
        elif actual is None:
            table.add_row(s, f"[yellow]{expected}[/yellow]", "[red]not found[/red]", "[red]✗ missing in project[/red]")
            mismatches.append(s)
        elif expected != actual:
            table.add_row(s, f"[yellow]{expected}[/yellow]", f"[red]{actual}[/red]", "[red]✗ mismatch[/red]")
            mismatches.append(s)
        else:
            table.add_row(s, f"[green]{expected}[/green]", f"[green]{actual}[/green]", "[bold green]✓ match[/bold green]")
    console.print()
    console.print(table)
    console.print()
    if mismatches:
        console.print("❌ [red]Version check failed: mismatches found.[/red]\n")
        raise typer.Exit(1)
    else:
        console.print("[bold green]All versions match![/bold green]\n")

def read_cli_version():
    cli_file = get_project_root() / "cli" / "pyproject.toml"
    if not cli_file.exists():
        return None
    content = cli_file.read_text(encoding='utf-8')
    import re
    match = re.search(r'version\s*=\s*["\']([^"\']*)["\']', content)
    return match.group(1) if match else None

def read_backend_version():
    # Try pyproject.toml first (canonical source)
    backend_file = get_project_root() / "backend" / "pyproject.toml"
    if backend_file.exists():
        content = backend_file.read_text(encoding='utf-8')
        import re
        match = re.search(r'version\s*=\s*["\']([^"\']*)["\']', content)
        if match:
            return match.group(1)
    
    # Fallback to main.py
    main_file = get_project_root() / "backend" / "main.py"
    if main_file.exists():
        content = main_file.read_text(encoding='utf-8')
        import re
        match = re.search(r'__version__\s*=\s*["\']([^"\']*)["\']', content)
        if match:
            return match.group(1)
    
    return None

def read_frontend_version():
    frontend_file = get_project_root() / "frontend" / "pubspec.yaml"
    if not frontend_file.exists():
        return None
    import re
    content = frontend_file.read_text(encoding='utf-8')
    match = re.search(r'version:\s*([\d\.]+)', content)
    return match.group(1) if match else None

def read_shared_version():
    """Read version from shared/pyproject.toml by parsing the version string."""
    pyproject_file = get_project_root() / "shared" / "pyproject.toml"
    if not pyproject_file.exists():
        return None
    try:
        content = pyproject_file.read_text(encoding='utf-8')
        import re
        match = re.search(r'version\s*=\s*["\']([^"\']*)["\']', content)
        return match.group(1) if match else None
    except Exception:
        return None

def read_studio_version():
    studio_file = get_project_root() / "studio" / "package.json"
    if not studio_file.exists():
        return None
    import json
    try:
        data = json.loads(studio_file.read_text(encoding='utf-8'))
        return data.get("version")
    except Exception:
        return None

@app.command(
    help="""
Preview the next version number for a subsystem or all subsystems, using semantic versioning rules.
No changes are made.
"""
)
def next(
    subsystem: str = typer.Argument(
        None,
        help="Which subsystem to preview (shared/cli/backend/frontend/studio/all). If omitted, previews all subsystems.",
        show_default=False
    ),
    level: str = typer.Argument(
        "patch",
        help="Which level to bump (major/minor/patch). Default: patch.",
        show_default=True
    )
):
    import re
    def bump_version(ver, level):
        main = ver.split('+')[0]
        m = re.match(r'^(\d+)\.(\d+)\.(\d+)', main)
        if not m:
            return None
        major, minor, patch = map(int, m.groups())
        if level == "major":
            return f"{major+1}.0.0"
        elif level == "minor":
            return f"{major}.{minor+1}.0"
        else:
            return f"{major}.{minor}.{patch+1}"

    versions = read_versions()
    subsystems_to_check = SUBSYSTEMS if subsystem is None or subsystem == "all" else [subsystem]
    table = Table(
        title="✨ [bold cyan]Next Version Preview[/bold cyan]",
        title_style="bold cyan",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        show_lines=False,
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Subsystem", style="bold white", no_wrap=True)
    table.add_column("Current", style="white", justify="left")
    table.add_column("Next", style="green", justify="left")
    table.add_column("Level", style="white", justify="left")
    for s in subsystems_to_check:
        current = versions.get(s)
        if not current:
            table.add_row(s, "[red]not found[/red]", "-", "-")
            continue
        next_v = bump_version(current, level)
        if next_v:
            table.add_row(s, f"[green]{current}[/green]", f"[bold yellow]{next_v}[/bold yellow]", f"[dim]{level}[/dim]")
        else:
            table.add_row(s, f"[red]{current}[/red]", "[red]invalid[/red]", f"[dim]{level}[/dim]")
    console.print()
    console.print(table)
    console.print()

@app.command(
    help="""
Bump the version for a subsystem and update all relevant files. Optionally create and push a git tag/commit.

Examples:
  aico version bump backend patch --tag
  aico version bump cli minor --tag --push
"""
)
def bump(
    subsystem: str = typer.Argument(
        ...,
        help="Which subsystem to bump (shared/cli/backend/frontend/studio). Must be specified.",
    ),
    level: str = typer.Argument(
        ...,
        help="Which level to bump (major/minor/patch). Must be specified.",
    ),
    tag: bool = typer.Option(
        False,
        "--tag",
        help="Create and push a git tag after bumping."
    ),
    push: bool = typer.Option(
        False,
        "--push",
        help="Push the commit and tag to remote after bumping. Requires --tag."
    )
):
    """
    Bump the version for a subsystem and update all relevant files. Optionally create and push a git tag/commit.
    """
    import re, subprocess
    from pathlib import Path

    valid_subsystems = set(SUBSYSTEMS)
    valid_levels = {"major", "minor", "patch"}
    if subsystem not in valid_subsystems:
        console.print(f"[red]Invalid subsystem: {subsystem}. Must be one of: {', '.join(sorted(SUBSYSTEMS))}[/red]")
        raise typer.Exit(1)
    if level not in valid_levels:
        console.print(f"[red]Invalid level: {level}. Must be one of: major, minor, patch[/red]")
        raise typer.Exit(1)
    if push and not tag:
        console.print(f"[red]--push requires --tag[/red]")
        raise typer.Exit(1)

    # Check for dirty working directory
    try:
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
        if result.stdout.strip():
            console.print("[red]Refusing to bump: working directory has uncommitted changes. Please commit or stash them first.[/red]")
            raise typer.Exit(1)
    except Exception:
        console.print("[red]Git repository not found or error running git status.[/red]")
        raise typer.Exit(1)

    # Bump version
    versions = read_versions()
    current = versions.get(subsystem)
    if not current:
        console.print(f"[red]No version found for {subsystem} in VERSIONS file.[/red]")
        raise typer.Exit(1)
    def bump_version(ver, level):
        main = ver.split('+')[0]
        m = re.match(r'^(\d+)\.(\d+)\.(\d+)', main)
        if not m:
            return None
        major, minor, patch = map(int, m.groups())
        if level == "major":
            return f"{major+1}.0.0"
        elif level == "minor":
            return f"{major}.{minor+1}.0"
        else:
            return f"{major}.{minor}.{patch+1}"
    new_version = bump_version(current, level)
    if not new_version:
        console.print(f"[red]Could not parse current version: {current}")
        raise typer.Exit(1)

    # Update VERSIONS file
    versions[subsystem] = new_version
    versions_path = get_project_root() / "VERSIONS"
    lines = []
    for s in SUBSYSTEMS:
        v = versions.get(s)
        if v:
            lines.append(f"{s}: {v}\n")
    versions_path.write_text("".join(lines), encoding="utf-8")

    # Always update the subsystem project file after bump
    update_functions = {
        "shared": update_shared_version,
        "cli": update_cli_version,
        "backend": update_backend_version,
        "frontend": update_frontend_version,
        "studio": update_studio_version
    }
    update_func = update_functions[subsystem]
    updated = update_func(new_version)
    if not updated:
        console.print(f"[yellow]Warning: No changes made to the {subsystem} project file (already up-to-date or file missing).[/yellow]")

    # Commit changes
    commit_msg = f"Bump {subsystem} version to {new_version}"
    subprocess.run(["git", "add", str(versions_path)], check=True)
    # For git commits, we need to add both files for backend
    if subsystem == "backend":
        # Add both pyproject.toml and main.py for backend
        backend_pyproject = get_project_root() / "backend" / "pyproject.toml"
        backend_main = get_project_root() / "backend" / "main.py"
        if backend_pyproject.exists():
            subprocess.run(["git", "add", str(backend_pyproject)], check=True)
        if backend_main.exists():
            subprocess.run(["git", "add", str(backend_main)], check=True)
    else:
        project_file = {
            "shared": get_project_root() / "shared" / "pyproject.toml",
            "cli": get_project_root() / "cli" / "pyproject.toml",
            "frontend": get_project_root() / "frontend" / "pubspec.yaml",
            "studio": get_project_root() / "studio" / "package.json"
        }[subsystem]
        subprocess.run(["git", "add", str(project_file)], check=True)
    # Project file addition is now handled above
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)

    tag_name = f"aico-{subsystem}-v{new_version}"
    tag_result = None
    if tag:
        subprocess.run(["git", "tag", tag_name], check=True)
        if push:
            subprocess.run(["git", "push"], check=True)
            subprocess.run(["git", "push", "origin", tag_name], check=True)
        tag_result = f"[green]created{' and pushed' if push else ''}[/green]"
    else:
        tag_result = "[dim]not created[/dim]"

    # Output summary
    table = Table(
        title="✨ [bold cyan]Version Bump Status[/bold cyan]",
        title_style="bold cyan",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        show_lines=False,
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Subsystem", style="bold white", no_wrap=True)
    table.add_column("Old", style="white", justify="left")
    table.add_column("New", style="green", justify="left")
    table.add_column("Level", style="white", justify="left")
    table.add_column("Tag", style="white", justify="left")
    table.add_row(subsystem, f"[yellow]{current}[/yellow]", f"[bold green]{new_version}[/bold green]", f"[dim]{level}[/dim]", tag_result)
    console.print()
    console.print(table)
    console.print()

    studio_file = get_project_root() / "studio" / "package.json"
    if not studio_file.exists():
        return None
    import json
    try:
        data = json.loads(studio_file.read_text(encoding='utf-8'))
        return data.get("version")
    except Exception:
        return None

