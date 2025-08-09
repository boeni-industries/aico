"""
AICO CLI Database Commands

Provides database initialization, status checking, and management commands.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import box
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
from aico.core.paths import AICOPaths
from aico.core.config import ConfigurationManager

# Import shared utilities using the same pattern as other CLI modules
from utils.path_display import format_smart_path, create_path_table, display_full_paths_section, display_platform_info, get_status_indicator

def database_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("init", "Initialize a new encrypted AICO database"),
            ("status", "Check database encryption status and information"),
            ("test", "Test database connection and basic operations"),
            ("show", "Show database configuration, paths, and settings")
        ]
        
        examples = [
            "aico db init",
            "aico db status",
            "aico db test",
            "aico db show"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="database",
            description="Database initialization, status, and management",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Database initialization, status, and management.",
    callback=database_callback,
    invoke_without_command=True
)
console = Console()





@app.command()
def init(
    db_path: str = typer.Option(None, help="Database file path (optional - uses config default)"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)"),
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)")
):
    """Initialize a new encrypted AICO database."""
    
    # Load configuration and resolve database path
    config = ConfigurationManager()
    
    if db_path:
        # Use provided path directly
        db_file = Path(db_path)
    else:
        # Use configuration-based path resolution
        db_config = config.get(f"database.{db_type}", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_file = AICOPaths.resolve_database_path(filename, directory_mode)
    
    # Check if database already exists
    if db_file.exists():
        console.print(f"❌ [red]Database already exists: {db_path}[/red]")
        raise typer.Exit(1)
    
    # Check if master password is set up
    key_manager = AICOKeyManager()
    master_password_was_created = False
    
    if not key_manager.has_stored_key() and not password:
        console.print("⚠️ [yellow]No master password set up.[/yellow]")
        console.print("Setting up security automatically...")
        
        # Auto-setup security
        password = typer.prompt("Create master password", hide_input=True)
        confirm_password = typer.prompt("Confirm master password", hide_input=True)
        
        if password != confirm_password:
            console.print("❌ [red]Passwords do not match[/red]")
            raise typer.Exit(1)
            
        # Setup master password
        key_manager.setup_master_password(password)
        master_password_was_created = True
        console.print("✅ [green]Security setup complete[/green]")
    
    # Get password if not provided (authentication, not setup)
    if not password:
        if key_manager.has_stored_key():
            # Master password exists - just authenticate
            password = typer.prompt("Enter master password", hide_input=True)
        else:
            # This shouldn't happen (should be handled above), but safety fallback
            console.print("❌ [red]Master password not set up. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
    
    try:
        console.print(f"🔐 Creating encrypted {db_type} database: [cyan]{db_path}[/cyan]")
        
        # Create encrypted database (currently only LibSQL supported)
        if db_type != "libsql":
            console.print(f"❌ [red]Database type '{db_type}' not yet implemented[/red]")
            console.print("Currently supported: libsql")
            raise typer.Exit(1)
            
        conn = create_encrypted_database(
            db_path=str(db_file),
            master_password=password,
            store_in_keyring=True
        )
        
        console.print("✅ [green]Database created successfully![/green]")
        console.print(f"📁 Database: {db_file}")
        console.print(f"🔑 Salt file: {db_file}.salt")
        
        # Only show keyring message if master password was actually created
        if master_password_was_created:
            console.print("🔐 Master password stored in system keyring")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to create database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    db_path: str = typer.Option(None, help="Database file path (optional - uses config default)"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)")
):
    """Check database encryption status and information."""
    
    # Load configuration and resolve database path
    config = ConfigurationManager()
    
    if db_path:
        # Use provided path directly
        db_file = Path(db_path)
    else:
        # Use configuration-based path resolution
        db_config = config.get(f"database.{db_type}", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_file = AICOPaths.resolve_database_path(filename, directory_mode)
    
    if not db_file.exists():
        console.print(f"❌ [red]Database not found: {db_path}[/red]")
        raise typer.Exit(1)
    
    try:
        # Try to connect and get encryption info
        conn = EncryptedLibSQLConnection(db_path=str(db_file))
        
        # Get encryption information
        info = conn.get_encryption_info()
        
        # Create status table
        table = Table(title=f"Database Status: {db_file}")
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
    db_path: str = typer.Option(None, help="Database file path (optional - uses config default)"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)"),
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)")
):
    """Test database connection and basic operations."""
    
    # Load configuration and resolve database path
    config = ConfigurationManager()
    
    if db_path:
        # Use provided path directly
        db_file = Path(db_path)
    else:
        # Use configuration-based path resolution
        db_config = config.get(f"database.{db_type}", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_file = AICOPaths.resolve_database_path(filename, directory_mode)
    
    if not db_file.exists():
        console.print(f"❌ [red]Database not found: {db_file}[/red]")
        raise typer.Exit(1)
    
    # Get password if not provided
    if not password:
        password = typer.prompt("Enter master password", hide_input=True)
    
    try:
        console.print(f"🔐 Testing database connection: [cyan]{db_file}[/cyan]")
        
        # Create connection with password
        conn = EncryptedLibSQLConnection(
            db_path=str(db_file),
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


@app.command("show")
def show():
    """Show database configuration, paths, and settings."""
    
    console.print("🛢️ [bold cyan]Database Configuration & Paths[/bold cyan]\n")
    
    try:
        config = ConfigurationManager()
        
        # Database types to check
        db_types = ["libsql", "chromadb", "duckdb"]
        
        # Create table using shared utility
        table = create_path_table("Database Path Configuration", [
            ("Database Type", "cyan", True),
            ("Filename", "white", True),
            ("Mode", "yellow", True),
            ("Smart Path", "green", False),
            ("Status", "white", True)
        ])
        
        # Show configuration settings table
        config_table = create_path_table("Database Configuration Settings", [
            ("Database Type", "cyan", True),
            ("Setting", "yellow", True),
            ("Value", "white", True),
            ("Source", "green", True)
        ])
        
        for db_type in db_types:
            try:
                # Get configuration
                db_config = config.get(f"database.{db_type}", {})
                
                # Resolve path based on database type
                if db_type == "chromadb":
                    dirname = db_config.get("dirname", "chroma")
                    directory_mode = db_config.get("directory_mode", "auto")
                    resolved_path = AICOPaths.resolve_database_path(dirname, directory_mode)
                    filename_display = dirname
                else:
                    filename = db_config.get("filename", f"{db_type}.db")
                    directory_mode = db_config.get("directory_mode", "auto")
                    resolved_path = AICOPaths.resolve_database_path(filename, directory_mode)
                    filename_display = filename
                
                # Format path and get status
                smart_path = format_smart_path(resolved_path)
                status = get_status_indicator(resolved_path)
                
                table.add_row(
                    db_type.upper(),
                    filename_display,
                    directory_mode,
                    smart_path,
                    status
                )
                
                # Add configuration settings to config table
                if db_type == "libsql":
                    config_table.add_row("LIBSQL", "journal_mode", db_config.get("journal_mode", "WAL"), "database.yaml")
                    config_table.add_row("LIBSQL", "synchronous", db_config.get("synchronous", "NORMAL"), "database.yaml")
                    config_table.add_row("LIBSQL", "cache_size", str(db_config.get("cache_size", 2000)), "database.yaml")
                elif db_type == "chromadb":
                    config_table.add_row("CHROMADB", "collection_name", db_config.get("collection_name", "aico_vectors"), "database.yaml")
                    config_table.add_row("CHROMADB", "distance_function", db_config.get("distance_function", "cosine"), "database.yaml")
                elif db_type == "duckdb":
                    config_table.add_row("DUCKDB", "memory_limit", db_config.get("memory_limit", "1GB"), "database.yaml")
                    config_table.add_row("DUCKDB", "threads", str(db_config.get("threads", 4)), "database.yaml")
                
            except Exception as e:
                table.add_row(
                    db_type.upper(),
                    "❌ Error",
                    "❌ Error", 
                    f"Error: {e}",
                    "❌ Error"
                )
        
        console.print(table)
        console.print("\n")
        console.print(config_table)
        
        # Show full paths for transparency using shared utility
        paths_data = []
        for db_type in db_types:
            try:
                db_config = config.get(f"database.{db_type}", {})
                if db_type == "chromadb":
                    dirname = db_config.get("dirname", "chroma")
                    directory_mode = db_config.get("directory_mode", "auto")
                    resolved_path = AICOPaths.resolve_database_path(dirname, directory_mode)
                else:
                    filename = db_config.get("filename", f"{db_type}.db")
                    directory_mode = db_config.get("directory_mode", "auto")
                    resolved_path = AICOPaths.resolve_database_path(filename, directory_mode)
                
                paths_data.append((db_type.upper(), resolved_path))
            except Exception:
                pass  # Skip errors in detail view
        
        display_full_paths_section(console, paths_data)
        
        # Show platform info
        platform_info = AICOPaths.get_platform_info()
        data_dir = AICOPaths.get_data_directory() / "data"  # Show actual database storage directory
        console.print(f"\n🖥️ Platform: [cyan]{platform_info['platform']} {platform_info['platform_release']}[/cyan]")
        console.print(f"📁 Data Directory: [green]{data_dir}[/green]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to show database paths: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
