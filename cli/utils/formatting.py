"""
Formatting utilities for CLI output.

Provides consistent formatting functions for success, error, and informational messages.
"""

from rich.panel import Panel
from rich.text import Text


def format_success(message: str) -> Panel:
    """Format a success message with green styling."""
    return Panel(
        Text(message, style="bold green"),
        border_style="green",
        title="✅ Success",
        title_align="left"
    )


def format_error(message: str) -> Panel:
    """Format an error message with red styling."""
    return Panel(
        Text(message, style="bold red"),
        border_style="red", 
        title="❌ Error",
        title_align="left"
    )


def format_warning(message: str) -> Panel:
    """Format a warning message with yellow styling."""
    return Panel(
        Text(message, style="bold yellow"),
        border_style="yellow",
        title="⚠️ Warning", 
        title_align="left"
    )


def format_info(message: str) -> Panel:
    """Format an informational message with blue styling."""
    return Panel(
        Text(message, style="bold blue"),
        border_style="blue",
        title="ℹ️ Info",
        title_align="left"
    )


def get_status_chars() -> dict:
    """Get platform-appropriate status characters."""
    import platform
    
    # Use ASCII characters for cross-platform compatibility
    if platform.system() == "Windows":
        return {
            "check": "✓",
            "cross": "✗", 
            "warning": "!",
            "info": "i",
            "running": "►",
            "stopped": "■",
            "globe": "●"
        }
    else:
        return {
            "check": "✓",
            "cross": "✗",
            "warning": "⚠",
            "info": "ℹ",
            "running": "▶",
            "stopped": "⏹",
            "globe": "🌐"
        }
