"""
CLI Path Display Utilities

Shared utilities for displaying paths consistently across CLI commands.
Follows DRY principles and CLI visual style guide.
"""

from pathlib import Path
from rich.table import Table
from rich import box
from rich.console import Console


def format_smart_path(path: Path, max_length: int = 50) -> str:
    """
    Format path for optimal display in CLI tables.
    
    Strategies:
    1. Use ~ for home directory (cross-platform)
    2. Show relative path from current directory if shorter
    3. Truncate middle with ... if still too long
    4. Always show filename clearly
    
    Args:
        path: Path to format
        max_length: Maximum display length
        
    Returns:
        str: Formatted path string
    """
    path_str = str(path)
    
    # Strategy 1: Replace home directory with ~
    home = Path.home()
    try:
        relative_to_home = path.relative_to(home)
        home_path = f"~/{relative_to_home}".replace("\\", "/")
    except ValueError:
        home_path = None
    
    # Strategy 2: Show relative to current directory if shorter
    try:
        relative_to_cwd = path.relative_to(Path.cwd())
        cwd_path = f"./{relative_to_cwd}".replace("\\", "/")
    except ValueError:
        cwd_path = None
    
    # Choose the shortest representation
    candidates = [path_str]
    if home_path:
        candidates.append(home_path)
    if cwd_path:
        candidates.append(cwd_path)
    
    best_path = min(candidates, key=len)
    
    # Strategy 3: Truncate middle if still too long (keep filename visible)
    if len(best_path) > max_length:
        filename = path.name
        # Keep first part, middle ..., and filename
        prefix_length = max_length - len(filename) - 5  # 5 for ".../"
        if prefix_length > 10:  # Ensure meaningful prefix
            prefix = best_path[:prefix_length]
            best_path = f"{prefix}.../{filename}"
        else:
            # If path is extremely long, just show end part
            best_path = f".../{best_path[-(max_length-4):]}"
    
    return best_path


def create_path_table(title: str, columns: list) -> Table:
    """
    Create a standardized path table following CLI style guide.
    
    Args:
        title: Table title (will be prefixed with ✨)
        columns: List of (column_name, style, no_wrap) tuples
        
    Returns:
        Table: Configured Rich table
    """
    table = Table(
        title=f"✨ {title}",
        box=box.SIMPLE_HEAD,
        title_justify="left"
    )
    
    for col_name, style, no_wrap in columns:
        table.add_column(col_name, style=style, no_wrap=no_wrap)
    
    return table


def display_full_paths_section(console: Console, paths_data: list, section_title: str = "Full Resolved Paths"):
    """
    Display full paths section consistently across commands.
    
    Args:
        console: Rich console instance
        paths_data: List of (label, path) tuples
        section_title: Section header title
    """
    console.print(f"\n📍 [bold yellow]{section_title}[/bold yellow]")
    for label, path in paths_data:
        console.print(f"  [cyan]{label}[/cyan]: [dim]{path}[/dim]")


def display_platform_info(console: Console, platform_info: dict):
    """
    Display platform information consistently.
    
    Args:
        console: Rich console instance
        platform_info: Platform information dictionary
    """
    console.print(f"\n🖥️ Platform: [cyan]{platform_info['platform']} {platform_info['platform_release']}[/cyan]")
    
    # Show environment overrides if any
    overrides = platform_info.get("environment_overrides", {})
    if any(overrides.values()):
        console.print("\n🔧 [yellow]Environment Overrides[/yellow]")
        for key, value in overrides.items():
            if value:
                console.print(f"  [cyan]{key}[/cyan]: [green]{value}[/green]")


def get_status_indicator(path: Path) -> str:
    """
    Get standardized status indicator for path existence.
    
    Args:
        path: Path to check
        
    Returns:
        str: Status indicator
    """
    return "✅ Yes" if path.exists() else "❌ No"
