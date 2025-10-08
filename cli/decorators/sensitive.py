"""
Sensitive Command Decorators

Provides decorators to mark CLI commands as sensitive (requiring fresh authentication).
"""

import functools
import sys
from pathlib import Path
import functools
from typing import Any

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.security import AICOKeyManager


def sensitive(arg=None, *, reason: str = "sensitive operation"):
    """
    Decorator to mark a command as sensitive, requiring fresh authentication.

    Can be used as @sensitive, @sensitive("reason"), or @sensitive(reason="reason").
    """
    def decorator(func):
        # Determine the actual reason based on how the decorator was called
        actual_reason = reason
        if isinstance(arg, str):
            actual_reason = arg

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            command_path = f"{func.__module__.split('.')[-1]}.{func.__name__}"
            
            from rich.console import Console
            console = Console()
            console.print(f"🔐 [yellow]Sensitive operation:[/yellow] {actual_reason}")
            console.print("   [dim]Authentication required for security[/dim]")
            
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            key_manager = AICOKeyManager(config)

            try:
                key_manager.authenticate(interactive=True, force_fresh=False)
                try:
                    from aico.core.logging import _get_logger
                    _get_logger().info(f"Sensitive command executed: {command_path} ({actual_reason})")
                except ImportError:
                    pass
            except Exception as e:
                console.print(f"[red]Authentication failed: {e}[/red]")
                import typer
                raise typer.Exit(1)
            
            return func(*args, **kwargs)

        wrapper._is_sensitive = True
        wrapper._sensitive_reason = actual_reason
        return wrapper

    if callable(arg):
        # Called as @sensitive without arguments
        return decorator(arg)
    else:
        # Called as @sensitive("reason") or @sensitive(reason="reason")
        return decorator


def destructive(arg=None, *, reason: str = "dangerous operation"):
    """
    An alias for @sensitive for operations that are destructive.

    Can be used as @destructive, @destructive("reason"), or @destructive(reason="reason").
    """
    def decorator(func):
        actual_reason = reason
        if isinstance(arg, str):
            actual_reason = arg

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            command_path = f"{func.__module__.split('.')[-1]}.{func.__name__}"
            
            from rich.console import Console
            console = Console()
            console.print(f"⚠️  [red]Dangerous operation:[/red] {actual_reason}")
            console.print("   [dim]Authentication required for security[/dim]")
            
            from aico.core.config import ConfigurationManager
            config = ConfigurationManager()
            config.initialize(lightweight=True)
            key_manager = AICOKeyManager(config)
            
            try:
                key_manager.authenticate(interactive=True, force_fresh=False)
                try:
                    from aico.core.logging import _get_logger
                    _get_logger().info(f"Dangerous command executed: {command_path} ({actual_reason})")
                except ImportError:
                    pass
            except Exception as e:
                console.print(f"[red]Authentication failed: {e}[/red]")
                import typer
                raise typer.Exit(1)
            
            # Add confirmation prompt for destructive operations
            import typer
            console.print()
            if not typer.confirm(f"⚠️  Are you sure you want to proceed with this dangerous operation?"):
                console.print("[yellow]Operation cancelled by user[/yellow]")
                raise typer.Exit(0)
            console.print()

            return func(*args, **kwargs)

        wrapper._is_sensitive = True
        wrapper._sensitive_reason = f"destructive: {actual_reason}"
        return wrapper

    if callable(arg):
        # Called as @destructive without arguments
        return decorator(arg)
    else:
        # Called as @destructive("reason") or @destructive(reason="reason")
        return decorator


def is_sensitive_command(func) -> bool:
    """
    Check if a function is marked as sensitive.
    
    Args:
        func: Function to check
        
    Returns:
        True if function is marked as sensitive
    """
    return getattr(func, '_is_sensitive', False)


def get_sensitive_reason(func) -> str:
    """
    Get the reason why a function is marked as sensitive.
    
    Args:
        func: Function to check
        
    Returns:
        Reason string or empty string if not sensitive
    """
    return getattr(func, '_sensitive_reason', '')
