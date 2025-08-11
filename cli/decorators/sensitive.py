"""
Sensitive Command Decorators

Provides decorators to mark CLI commands as sensitive (requiring fresh authentication).
"""

import functools
import sys
from pathlib import Path
from typing import Callable, Any

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.security import AICOKeyManager


def sensitive(reason: str = "sensitive operation"):
    """
    Decorator to mark a command as sensitive, requiring fresh authentication.
    
    This decorator works transparently - no code changes needed in the decorated function.
    It pre-authenticates and caches the session, so existing authentication calls will work.
    
    Args:
        reason: Human-readable reason why this command is sensitive
        
    Usage:
        @sensitive("data export")
        @app.command()
        def export():
            pass
            
        @sensitive("destructive operation")  
        @app.command()
        def delete():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            
            # Get command path for logging
            command_path = f"{func.__module__.split('.')[-1]}.{func.__name__}"
            
            # Show explanation BEFORE asking for password (better UX)
            from rich.console import Console
            console = Console()
            console.print(f"🔐 [yellow]Sensitive operation:[/yellow] {reason}")
            console.print("   [dim]Fresh authentication required for security[/dim]")
            
            # Force fresh authentication for sensitive commands
            key_manager = AICOKeyManager()
            
            # Force fresh authentication and cache it
            try:
                master_key = key_manager.authenticate(interactive=True, force_fresh=True)
                # Cache the session so subsequent authenticate() calls in the function work
                key_manager._cache_session(master_key)
                
                # Log sensitive command execution
                try:
                    from aico.core.logging import _get_logger
                    _get_logger().info(f"Sensitive command executed: {command_path} ({reason})")
                except ImportError:
                    # Fallback logging if _get_logger not available
                    print(f"🔐 Sensitive command executed: {command_path} ({reason})")
            except Exception as e:
                from rich.console import Console
                console = Console()
                console.print(f"[red]Authentication failed: {e}[/red]")
                import typer
                raise typer.Exit(1)
            
            # Execute the original command - it will find the cached session
            return func(*args, **kwargs)
        
        # Mark function as sensitive for introspection
        wrapper._is_sensitive = True
        wrapper._sensitive_reason = reason
        return wrapper
    
    return decorator


def destructive(reason: str = "dangerous operation"):
    """
    Decorator to mark a command as dangerous, requiring fresh authentication.
    
    This is an alias for @sensitive but with clearer semantic meaning for
    operations that could cause data loss or system issues if interrupted.
    
    Args:
        reason: Human-readable reason why this command is dangerous
        
    Usage:
        @destructive("rebuilds database structure")
        @app.command()
        def vacuum():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            
            # Get command path for logging
            command_path = f"{func.__module__.split('.')[-1]}.{func.__name__}"
            
            # Show explanation BEFORE asking for password (better UX)
            from rich.console import Console
            console = Console()
            console.print(f"⚠️  [red]Dangerous operation:[/red] {reason}")
            console.print("   [dim]Fresh authentication required for security[/dim]")
            
            # Force fresh authentication for destructive commands
            key_manager = AICOKeyManager()
            
            # Force fresh authentication and cache it
            try:
                master_key = key_manager.authenticate(interactive=True, force_fresh=True)
                # Cache the session so subsequent authenticate() calls in the function work
                key_manager._cache_session(master_key)
                
                # Log dangerous command execution
                try:
                    from aico.core.logging import _get_logger
                    _get_logger().info(f"Dangerous command executed: {command_path} ({reason})")
                except ImportError:
                    # Fallback logging if _get_logger not available
                    print(f"⚠️ Dangerous command executed: {command_path} ({reason})")
            except Exception as e:
                from rich.console import Console
                console = Console()
                console.print(f"[red]Authentication failed: {e}[/red]")
                import typer
                raise typer.Exit(1)
            
            # Execute the original command - it will find the cached session
            return func(*args, **kwargs)
        
        # Mark function as destructive for introspection
        wrapper._is_sensitive = True
        wrapper._sensitive_reason = f"destructive: {reason}"
        return wrapper
    
    return decorator


def is_sensitive_command(func: Callable) -> bool:
    """
    Check if a function is marked as sensitive.
    
    Args:
        func: Function to check
        
    Returns:
        True if function is marked as sensitive
    """
    return getattr(func, '_is_sensitive', False)


def get_sensitive_reason(func: Callable) -> str:
    """
    Get the reason why a function is marked as sensitive.
    
    Args:
        func: Function to check
        
    Returns:
        Reason string or empty string if not sensitive
    """
    return getattr(func, '_sensitive_reason', '')
