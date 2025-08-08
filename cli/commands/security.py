"""
AICO CLI Security Commands

Provides master password setup, management, and security operations.
"""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.security import AICOKeyManager

def security_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("setup", "Set up master password for AICO (first-time setup)"),
            ("passwd", "Change the master password (affects all databases)"),
            ("status", "Check security status and keyring information"),
            ("clear", "Clear stored master key (security incident recovery)"),
            ("test", "Test master password authentication")
        ]
        
        examples = [
            "aico security setup",
            "aico security status",
            "aico security test",
            "aico security passwd"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="security",
            description="Master password setup and security management",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Master password setup and security management.",
    callback=security_callback,
    invoke_without_command=True
)
console = Console()


@app.command()
def setup(
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)")
):
    """Set up master password for AICO (first-time setup)."""
    
    key_manager = AICOKeyManager()
    
    # Check if already set up
    if key_manager.has_stored_key():
        console.print("⚠️ [yellow]Master password already set up.[/yellow]")
        console.print("Use 'aico security change-password' to update it.")
        raise typer.Exit(1)
    
    # Get password if not provided
    if not password:
        password = typer.prompt("Enter master password", hide_input=True)
        confirm_password = typer.prompt("Confirm master password", hide_input=True)
        
        if password != confirm_password:
            console.print("❌ [red]Passwords do not match[/red]")
            raise typer.Exit(1)
    
    try:
        console.print("🔐 Setting up master password...")
        
        # Set up master password
        master_key = key_manager.setup_master_password(password)
        
        console.print("✅ [green]Master password set up successfully![/green]")
        console.print("🔑 Master key derived and stored in system keyring")
        console.print("🔐 You can now initialize encrypted databases")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to set up master password: {e}[/red]")
        raise typer.Exit(1)


@app.command("passwd")
def passwd():
    """Change the master password (affects all databases)."""
    
    key_manager = AICOKeyManager()
    
    if not key_manager.has_stored_key():
        console.print("❌ [red]No master password set up.[/red]")
        console.print("Use 'aico security setup' first.")
        raise typer.Exit(1)
    
    try:
        # Get passwords
        old_password = typer.prompt("Enter current master password", hide_input=True)
        new_password = typer.prompt("Enter new master password", hide_input=True)
        confirm_password = typer.prompt("Confirm new master password", hide_input=True)
        
        if new_password != confirm_password:
            console.print("❌ [red]New passwords do not match[/red]")
            raise typer.Exit(1)
        
        console.print("🔐 Changing master password...")
        
        # Change password
        key_manager.change_password(old_password, new_password)
        
        console.print("✅ [green]Master password changed successfully![/green]")
        console.print("🔑 New master key stored in system keyring")
        console.print("⚠️ [yellow]All database connections will need the new password[/yellow]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to change master password: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Check security status and keyring information."""
    
    key_manager = AICOKeyManager()
    
    # Create status table
    table = Table(title="AICO Security Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    # Add security info
    table.add_row("Service Name", key_manager.service_name)
    table.add_row("Master Key Stored", "✅ Yes" if key_manager.has_stored_key() else "❌ No")
    
    # Get database password info for common types
    for db_type in ["libsql", "duckdb", "chroma"]:
        info = key_manager.get_database_password_info(db_type)
        table.add_row(f"{db_type.title()} KDF", info.get("kdf_algorithm", "Unknown"))
    
    console.print(table)
    
    # Show setup status
    if key_manager.has_stored_key():
        console.print("\n✅ [green]Master password is set up and ready[/green]")
        console.print("🔐 You can initialize encrypted databases")
    else:
        console.print("\n⚠️ [yellow]Master password not set up[/yellow]")
        console.print("Run 'aico security setup' to get started")


@app.command()
def clear(
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Clear stored master key (security incident recovery)."""
    
    if not confirm:
        console.print("⚠️ [bold red]WARNING: This will clear your stored master key![/bold red]")
        console.print("You will need to re-enter your master password for all operations.")
        
        if not typer.confirm("Are you sure you want to continue?"):
            console.print("Operation cancelled.")
            raise typer.Exit()
    
    try:
        key_manager = AICOKeyManager()
        key_manager.clear_stored_key()
        
        console.print("✅ [green]Stored master key cleared successfully[/green]")
        console.print("🔐 Run 'aico security setup' to set up a new master password")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to clear stored key: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test():
    """Test master password authentication."""
    
    key_manager = AICOKeyManager()
    
    if not key_manager.has_stored_key():
        console.print("❌ [red]No master password set up.[/red]")
        console.print("Use 'aico security setup' first.")
        raise typer.Exit(1)
    
    try:
        console.print("🔐 Testing master password authentication...")
        
        # Try authentication (will prompt for password if needed)
        master_key = key_manager.authenticate(interactive=True)
        
        console.print("✅ [green]Master password authentication successful![/green]")
        console.print(f"🔑 Master key length: {len(master_key)} bytes")
        
        # Test key derivation for different database types
        console.print("\n🔍 Testing key derivation...")
        for db_type in ["libsql", "duckdb", "chroma"]:
            try:
                if db_type == "libsql":
                    # LibSQL needs a path for salt management
                    db_key = key_manager.derive_database_key(
                        master_key, db_type, db_path="./test.db"
                    )
                else:
                    db_key = key_manager.derive_database_key(master_key, db_type)
                
                console.print(f"  ✅ {db_type.title()}: {len(db_key)} bytes")
            except Exception as e:
                console.print(f"  ❌ {db_type.title()}: {e}")
        
    except Exception as e:
        console.print(f"❌ [red]Authentication test failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
