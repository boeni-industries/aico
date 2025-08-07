"""
AICO CLI Database Commands

Provides database initialization, status checking, and management commands.
"""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys
import os

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.security import AICOKeyManager
from aico.data.libsql import create_encrypted_database, EncryptedLibSQLConnection

app = typer.Typer()
console = Console()


@app.command()
def init(
    db_path: str = typer.Option("./aico.db", help="Database file path"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)"),
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)")
):
    """Initialize a new encrypted AICO database."""
    
    db_file = Path(db_path)
    
    # Check if database already exists
    if db_file.exists():
        console.print(f"❌ [red]Database already exists: {db_path}[/red]")
        raise typer.Exit(1)
    
    # Check if master password is set up
    key_manager = AICOKeyManager()
    if not key_manager.has_stored_key() and not password:
        console.print("⚠️ [yellow]No master password set up.[/yellow]")
        console.print("Run 'aico security setup' first, or provide --password option.")
        raise typer.Exit(1)
    
    # Get password if not provided
    if not password:
        password = typer.prompt("Enter master password", hide_input=True)
        confirm_password = typer.prompt("Confirm master password", hide_input=True)
        
        if password != confirm_password:
            console.print("❌ [red]Passwords do not match[/red]")
            raise typer.Exit(1)
    
    try:
        console.print(f"🔐 Creating encrypted {db_type} database: [cyan]{db_path}[/cyan]")
        
        # Create encrypted database (currently only LibSQL supported)
        if db_type != "libsql":
            console.print(f"❌ [red]Database type '{db_type}' not yet implemented[/red]")
            console.print("Currently supported: libsql")
            raise typer.Exit(1)
            
        conn = create_encrypted_database(
            db_path=db_path,
            master_password=password,
            store_in_keyring=True
        )
        
        console.print("✅ [green]Database created successfully![/green]")
        console.print(f"📁 Database: {db_path}")
        console.print(f"🔑 Salt file: {db_path}.salt")
        console.print("🔐 Master password stored in system keyring")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to create database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    db_path: str = typer.Option("./aico.db", help="Database file path"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)")
):
    """Check database encryption status and information."""
    
    db_file = Path(db_path)
    
    if not db_file.exists():
        console.print(f"❌ [red]Database not found: {db_path}[/red]")
        raise typer.Exit(1)
    
    try:
        # Try to connect and get encryption info
        conn = EncryptedLibSQLConnection(db_path=db_path)
        
        # Get encryption information
        info = conn.get_encryption_info()
        
        # Create status table
        table = Table(title=f"Database Status: {db_path}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        # Add basic info
        table.add_row("Database Path", str(info.get("database_path", "Unknown")))
        table.add_row("Encrypted", "✅ Yes" if info.get("encrypted") else "❌ No")
        table.add_row("Service Name", info.get("service_name", "Unknown"))
        table.add_row("Has Stored Key", "✅ Yes" if info.get("has_stored_key") else "❌ No")
        
        # Add encryption details
        if info.get("salt_file"):
            salt_exists = "✅ Yes" if info.get("salt_exists") else "❌ No"
            table.add_row("Salt File", f"{info['salt_file']} ({salt_exists})")
        
        table.add_row("KDF Algorithm", info.get("kdf_algorithm", "Unknown"))
        table.add_row("Key Length", f"{info.get('key_length', 'Unknown')} bits")
        
        if info.get("kdf_iterations"):
            table.add_row("KDF Iterations", str(info["kdf_iterations"]))
        
        console.print(table)
        
        # Test connection
        console.print("\n🔍 Testing database connection...")
        if conn.verify_encryption():
            console.print("✅ [green]Database encryption verified successfully[/green]")
        else:
            console.print("⚠️ [yellow]Database encryption verification failed[/yellow]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to check database status: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test(
    db_path: str = typer.Option("./aico.db", help="Database file path"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)"),
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)")
):
    """Test database connection and basic operations."""
    
    db_file = Path(db_path)
    
    if not db_file.exists():
        console.print(f"❌ [red]Database not found: {db_path}[/red]")
        raise typer.Exit(1)
    
    # Get password if not provided
    if not password:
        password = typer.prompt("Enter master password", hide_input=True)
    
    try:
        console.print(f"🔐 Testing database connection: [cyan]{db_path}[/cyan]")
        
        # Create connection with password
        conn = EncryptedLibSQLConnection(
            db_path=db_path,
            master_password=password
        )
        
        # Test basic operations
        with conn:
            # Test table creation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Test insert
            conn.execute(
                "INSERT INTO test_table (message) VALUES (?)",
                ("CLI test message",)
            )
            
            # Test select
            result = conn.execute("SELECT COUNT(*) as count FROM test_table").fetchone()
            count = result[0] if result else 0
            
            # Clean up test data
            conn.execute("DELETE FROM test_table WHERE message = 'CLI test message'")
            conn.commit()
        
        console.print("✅ [green]Database test completed successfully![/green]")
        console.print(f"📊 Total records in test_table: {count}")
        
    except Exception as e:
        console.print(f"❌ [red]Database test failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
