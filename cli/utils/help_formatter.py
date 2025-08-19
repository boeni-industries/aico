"""
Rich help formatter for consistent CLI styling across all commands.
Follows the AICO CLI visual style guide.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text


def format_command_help(
    console: Console,
    title: str,
    subtitle: str,
    commands: list,
    examples: list = None,
    footer: str = None
):
    """
    Format command help with consistent AICO CLI styling.
    
    Args:
        console: Rich console instance
        title: Main title (e.g., "AICO CLI", "Version Management")
        subtitle: Subtitle description
        commands: List of (icon, name, description) tuples
        examples: Optional list of example commands
        footer: Optional footer text
    """
    
    # Header with sparkle
    console.print(f"✨ [bold cyan]{title}[/bold cyan]")
    console.print(f"[dim]{subtitle}[/dim]")
    console.print()
    
    # Available Commands section with blue divider
    console.rule("[bold blue]Available Commands", style="blue")
    console.print()
    
    # Commands with proper alignment
    for icon, name, description in commands:
        # Use consistent spacing like the original design
        # Add extra space for compound emojis that take more visual width
        spacing = "  " if icon == "🛢️" else " "
        console.print(f"{icon}{spacing}[green]{name:<12}[/green] {description}")
    
    console.print()
    
    # Quick Start section if examples provided
    if examples:
        console.rule("[bold blue]Quick Start", style="blue")
        console.print()
        
        console.print("[bold]Examples:[/bold]")
        for example in examples:
            console.print(f"  {example}")
        console.print()
    
    # Footer
    if footer:
        console.print(f"[dim]{footer}[/dim]")
    else:
        console.print("[dim]Use 'aico COMMAND --help' for more information on a command.[/dim]")


def format_subcommand_help(
    console: Console,
    command_name: str,
    description: str,
    subcommands: list,
    examples: list = None
):
    """
    Format subcommand help with consistent styling.
    
    Args:
        console: Rich console instance
        command_name: Name of the parent command
        description: Command description
        subcommands: List of (name, description) tuples
        examples: Optional list of example commands
    """
    
    # Header
    console.print(f"✨ [bold cyan]{command_name.title()} Management[/bold cyan]")
    console.print(f"[dim]{description}[/dim]")
    console.print()
    
    # Commands section
    console.rule("[bold blue]Commands", style="blue")
    console.print()
    
    # Create aligned subcommands with proper coloring
    for name, desc in subcommands:
        console.print(f"[green]{name:<12}[/green] {desc}")
    
    console.print()
    
    # Examples section
    if examples:
        console.rule("[bold blue]Examples", style="blue")
        console.print()
        
        for example in examples:
            console.print(f"  {example}")
        console.print()
    
    console.print("[dim]Use 'aico {command_name} COMMAND --help' for more information on a specific command.[/dim]".format(command_name=command_name))
