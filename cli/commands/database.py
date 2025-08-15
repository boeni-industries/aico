"""
AICO CLI Database Commands

Provides database initialization, status checking, and management commands.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path
import sys
import os
from typing import Optional

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from sensitive import sensitive, destructive

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
from aico.data.libsql.registry import SchemaRegistry
from aico.core.paths import AICOPaths
from aico.core.config import ConfigurationManager
from aico.core.logging import initialize_cli_logging, get_logger

# Import schemas to ensure they're registered
import aico.data.schemas.core

# Import shared utilities using the same pattern as other CLI modules
from utils.path_display import format_smart_path, create_path_table, display_full_paths_section, display_platform_info, get_status_indicator
from utils.timezone import format_timestamp_local, get_timezone_suffix

def database_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("init", "Initialize a new encrypted AICO database"),
            ("status", "Check database encryption status and information"),
            ("test", "Test database connection and basic operations"),
            ("show", "Show database configuration, paths, and settings"),
            ("ls", "List all tables in database"),
            ("desc", "Describe table structure"),
            ("count", "Count records in table(s)"),
            ("head", "Show first N records from table"),
            ("tail", "Show last N records from table"),
            ("stat", "Database statistics"),
            ("vacuum", "Optimize database"),
            ("check", "Integrity check"),
            ("exec", "Execute raw SQL query"),
            ("sync", "Sync database to match code definitions"),
            ("snapshot", "Capture current state as migration baseline")
        ]
        
        examples = [
            "aico db init",
            "aico db status",
            "aico db ls",
            "aico db desc logs",
            "aico db count --table=logs",
            "aico db sync --dry-run",
            "aico db snapshot --confirm"
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


def _get_database_connection(db_path: str, force_fresh: bool = False) -> EncryptedLibSQLConnection:
    """Helper function to get authenticated database connection with session support."""
    try:
        key_manager = AICOKeyManager()
        
        if not key_manager.has_stored_key():
            console.print("[red]Error: Master key not found. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
        
        # Try session-based authentication first
        if not force_fresh:
            cached_key = key_manager._get_cached_session()
            if cached_key:
                # Use active session
                key_manager._extend_session()
                db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
                return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        # Try stored key from keyring
        import keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
            key_manager._cache_session(master_key)  # Cache for future use
            db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        # Need password - use typer.prompt instead of getpass to avoid hanging
        password = typer.prompt("Enter master password", hide_input=True)
        master_key = key_manager.authenticate(password, interactive=False, force_fresh=force_fresh)
        db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        
        return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
    except Exception as e:
        console.print(f"[red]Error connecting to database: {e}[/red]")
        raise typer.Exit(1)


def _format_table_value(value, column_name: str, utc: bool = False):
    """Format table value with timezone handling for timestamp columns (display only)"""
    if value is None:
        return ""
    
    str_value = str(value)
    
    # Detect timestamp columns by name and format
    timestamp_indicators = ['timestamp', 'created_at', 'updated_at', 'date', 'time']
    is_timestamp_column = any(indicator in column_name.lower() for indicator in timestamp_indicators)
    
    # Check if value looks like ISO timestamp
    is_timestamp_value = ('T' in str_value and ('Z' in str_value or '+' in str_value or str_value.count(':') >= 2))
    
    if (is_timestamp_column or is_timestamp_value) and len(str_value) > 10:
        try:
            return format_timestamp_local(str_value, show_utc=utc)
        except:
            pass  # Fall through to regular formatting
    
    # Truncate long values for display
    if len(str_value) > 50:
        str_value = str_value[:47] + "..."
    
    return str_value


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
    
    # Note: We'll handle existing databases later in the flow
    
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
    
    try:
        # Check if database already exists
        if db_file.exists():
            console.print(f"📁 Database already exists: [cyan]{db_file}[/cyan]")
            console.print("🔗 Connecting to existing database...")
            
            # Connect to existing database using session-based auth
            conn = _get_database_connection(str(db_file))
            
            # Initialize CLI logging with direct database access BEFORE operations
            from aico.core.logging import initialize_cli_logging, get_logger
            try:
                initialize_cli_logging(config, conn)
                # Test that logging actually works by attempting a log write
                test_logger = get_logger("cli", "database")
                test_logger.info("CLI logging initialized successfully for database init")
                console.print("✅ [green]CLI logging initialized and verified[/green]")
            except Exception as e:
                console.print(f"❌ [red]CRITICAL: CLI logging initialization failed: {e}[/red]")
                console.print(f"[red]Logs will only appear in console, not database[/red]")
                import traceback
                console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            
            # Apply any missing schemas
            console.print("📋 Checking for missing database schemas...")
            applied_schemas = SchemaRegistry.apply_core_schemas(conn)
            
            if applied_schemas:
                console.print("✅ [green]Database updated successfully![/green]")
                console.print(f"📋 Applied missing schemas: [cyan]{', '.join(applied_schemas)}[/cyan]")
            else:
                console.print("ℹ️ [blue]Database is up to date - no missing schemas[/blue]")
            
            # Keep connection alive for logging - don't close here
            # Connection will be closed when CLI command exits
        else:
            console.print(f"🔐 Creating encrypted {db_type} database: [cyan]{db_file}[/cyan]")
            
            # Create encrypted database (currently only LibSQL supported)
            if db_type != "libsql":
                console.print(f"❌ [red]Database type '{db_type}' not yet implemented[/red]")
                console.print("Currently supported: libsql")
                raise typer.Exit(1)
            
            # Connect to database using session-based authentication
            conn = _get_database_connection(str(db_file))
            
            # Create the database file
            conn.execute("SELECT 1")  # This creates the database file
            
            # Apply core schemas using schema registry
            console.print("📋 Applying core database schemas...")
            applied_schemas = SchemaRegistry.apply_core_schemas(conn)
            
            console.print("✅ [green]Database created successfully![/green]")
            console.print(f"📋 Applied schemas: [cyan]{', '.join(applied_schemas)}[/cyan]")
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
        # Check if database is encrypted by trying to connect with key manager
        key_manager = AICOKeyManager()
        
        if key_manager.has_stored_key():
            # Database likely encrypted, use session-based authentication
            conn = _get_database_connection(str(db_file))
            
            # Initialize CLI logging with direct database access BEFORE operations
            from aico.core.logging import initialize_cli_logging, get_logger
            config = ConfigurationManager()
            try:
                initialize_cli_logging(config, conn)
                # Test that logging actually works
                test_logger = get_logger("cli", "database")
                test_logger.info("CLI logging initialized successfully for database status")
                console.print("✅ [green]CLI logging verified[/green]")
            except Exception as e:
                console.print(f"❌ [red]CRITICAL: CLI logging failed: {e}[/red]")
                import traceback
                console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
            
            info = conn.get_encryption_info()
        else:
            # No stored key, database might be unencrypted
            conn = EncryptedLibSQLConnection(db_path=str(db_file))
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
        
        # Test encrypted connection
        console.print("\n🔍 Testing encrypted database connection...")
        if conn.verify_encryption():
            console.print("✅ [green]Encrypted connection verified successfully[/green]")
        else:
            console.print("⚠️ [yellow]Encrypted connection verification failed[/yellow]")
        
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
    
    try:
        console.print(f"🔐 Testing database connection: [cyan]{db_file}[/cyan]")
        
        # Use clean connection without automatic logging (to avoid transaction conflicts)
        if password:
            # If password provided, authenticate with it first
            key_manager = AICOKeyManager()
            key_manager.authenticate(password, interactive=False)
        
        # Create clean connection without the automatic INSERT that _get_db_connection() does
        conn = _get_database_connection(str(db_file))
        
        # Comprehensive database test with full CRUD operations
        test_table_name = f"aico_test_{int(__import__('time').time())}"  # Unique table name
        
        try:
            # Test 1: Basic connectivity
            console.print("🔍 Testing basic connectivity...")
            conn.execute("SELECT 1").fetchone()
            console.print("✅ Basic connectivity successful")
            
            # Test 2: Schema check
            console.print("🔍 Testing database schema...")
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            console.print(f"✅ Found {len(tables)} tables")
            
            # Test 3: CREATE - Create test table
            console.print(f"🔍 Testing table creation ({test_table_name})...")
            conn.execute(f"""
                CREATE TABLE {test_table_name} (
                    id INTEGER PRIMARY KEY,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()  # Explicit commit to close transaction
            console.print("✅ Table creation successful")
            
            # Test 4: INSERT - Add test record
            console.print("🔍 Testing insert operation...")
            test_message = f"AICO CLI test message at {__import__('datetime').datetime.now().isoformat()}"
            cursor = conn.execute(
                f"INSERT INTO {test_table_name} (message) VALUES (?)",
                (test_message,)
            )
            test_id = cursor.lastrowid
            conn.commit()  # Explicit commit to close transaction
            console.print(f"✅ Insert operation successful (ID: {test_id})")
            
            # Test 5: READ - Verify the record exists
            console.print("🔍 Testing select operation...")
            result = conn.execute(
                f"SELECT id, message FROM {test_table_name} WHERE id = ?",
                (test_id,)
            ).fetchone()
            if result and result[1] == test_message:
                console.print(f"✅ Select operation successful - record found")
            else:
                raise Exception("Inserted record not found or data mismatch")
            
            # Test 6: UPDATE - Modify the record
            console.print("🔍 Testing update operation...")
            updated_message = f"UPDATED: {test_message}"
            conn.execute(
                f"UPDATE {test_table_name} SET message = ? WHERE id = ?",
                (updated_message, test_id)
            )
            conn.commit()  # Explicit commit to close transaction
            # Verify update
            result = conn.execute(
                f"SELECT message FROM {test_table_name} WHERE id = ?",
                (test_id,)
            ).fetchone()
            if result and result[0] == updated_message:
                console.print("✅ Update operation successful")
            else:
                raise Exception("Update operation failed - data not modified")
            
            # Test 7: DELETE - Remove the test record
            console.print("🔍 Testing delete operation...")
            conn.execute(f"DELETE FROM {test_table_name} WHERE id = ?", (test_id,))
            conn.commit()  # Explicit commit to close transaction
            # Verify deletion
            result = conn.execute(
                f"SELECT COUNT(*) FROM {test_table_name} WHERE id = ?",
                (test_id,)
            ).fetchone()
            if result[0] == 0:
                console.print("✅ Delete operation successful")
            else:
                raise Exception("Delete operation failed - record still exists")
            
            # Test 8: DROP - Remove the test table completely
            console.print(f"🔍 Testing table deletion ({test_table_name})...")
            conn.execute(f"DROP TABLE {test_table_name}")
            conn.commit()  # Explicit commit to close transaction
            # Verify table is gone
            result = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name = ?",
                (test_table_name,)
            ).fetchone()
            if result[0] == 0:
                console.print("✅ Table deletion successful")
                count = 0  # No records since table is deleted
            else:
                raise Exception("Table deletion failed - table still exists")
                
        except Exception as test_error:
            # Cleanup: Try to drop test table if it exists
            try:
                conn.execute(f"DROP TABLE IF EXISTS {test_table_name}")
                console.print(f"🧹 Cleaned up test table: {test_table_name}")
            except:
                pass  # Expected failure during cleanup - table may not exist or connection may be closed
            console.print(f"❌ [red]Database test failed: {test_error}[/red]")
            raise test_error
        
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


def _get_db_connection():
    """Get database connection for content commands"""
    try:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        key_manager = AICOKeyManager()
        
        # Get database path
        paths = AICOPaths()
        db_path = paths.resolve_database_path("aico.db")
        
        # Connect to database using session-based authentication
        conn = _get_database_connection(str(db_path))
        
        # Initialize CLI logging with direct database transport BEFORE operations
        try:
            initialize_cli_logging(config, conn)
            # Verify logging works by testing actual log write
            test_logger = get_logger("cli", "database")
            test_logger.info("Accessing DB from CLI.")
            console.print("✅ [green]CLI logging verified for test command[/green]")
        except Exception as e:
            console.print(f"❌ [red]CRITICAL: CLI logging failed: {e}[/red]")
            console.print(f"[red]Database logging will not work - logs only in console[/red]")
            import traceback
            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        
        return conn
        
    except Exception as e:
        console.print(f"[red]Error connecting to database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def ls():
    """List all tables in database"""
    conn = _get_db_connection()
    
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    
    if not tables:
        console.print("[yellow]No tables found in database[/yellow]")
        return
    
    table = Table(
        title="✨ [bold cyan]Database Tables[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    
    table.add_column("Table", style="cyan")
    table.add_column("Records", style="white")
    
    for (table_name,) in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            table.add_row(table_name, f"{count:,}")
        except:
            table.add_row(table_name, "Error")
    
    console.print()
    console.print(table)
    console.print()


@app.command()
def desc(table_name: str = typer.Argument(..., help="Table name to describe")):
    """Describe table structure (schema)"""
    conn = _get_db_connection()
    
    try:
        schema = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        
        if not schema:
            console.print(f"[red]Table '{table_name}' not found[/red]")
            raise typer.Exit(1)
        
        table = Table(
            title=f"✨ [bold cyan]Table: {table_name}[/bold cyan]",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        table.add_column("Column", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Null", style="dim")
        table.add_column("Default", style="dim")
        table.add_column("PK", style="yellow")
        
        for col in schema:
            table.add_row(
                col[1],  # name
                col[2],  # type
                "YES" if col[3] == 0 else "NO",  # notnull
                str(col[4]) if col[4] else "",  # default
                "✓" if col[5] == 1 else ""  # pk
            )
        
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error describing table: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def count(
    table: Optional[str] = typer.Option(None, "--table", help="Specific table to count"),
    all: bool = typer.Option(False, "--all", help="Count all tables")
):
    """Count records in table(s)"""
    conn = _get_db_connection()
    
    if table:
        # Count specific table
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            console.print(f"[cyan]{table}[/cyan]: [bold white]{count:,}[/bold white] records")
        except Exception as e:
            console.print(f"[red]Error counting {table}: {e}[/red]")
            raise typer.Exit(1)
    
    elif all:
        # Count all tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        
        count_table = Table(
            title="✨ [bold cyan]Record Counts[/bold cyan]",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        count_table.add_column("Table", style="cyan")
        count_table.add_column("Records", style="white")
        
        total_records = 0
        for (table_name,) in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                count_table.add_row(table_name, f"{count:,}")
                total_records += count
            except:
                count_table.add_row(table_name, "Error")
        
        console.print()
        console.print(count_table)
        console.print(f"\n[bold yellow]Total Records:[/bold yellow] [bold white]{total_records:,}[/bold white]\n")
    
    else:
        console.print("[red]Error: Must specify --table or --all[/red]")
        raise typer.Exit(1)


@app.command()
def head(
    table_name: str = typer.Argument(..., help="Table name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Show first N records from table"""
    conn = _get_db_connection()
    
    try:
        records = conn.execute(f"SELECT * FROM {table_name} LIMIT {limit}").fetchall()
        
        if not records:
            console.print(f"[yellow]Table '{table_name}' is empty[/yellow]")
            return
        
        # Get column names
        columns = [desc[1] for desc in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        
        table = Table(
            title=f"✨ [bold cyan]First {limit} records from {table_name}[/bold cyan]",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        for col in columns:
            col_header = col + get_timezone_suffix(utc) if col.lower() in ['timestamp', 'created_at', 'updated_at', 'date'] else col
            table.add_column(col_header, style="white")
        
        for record in records:
            row_data = []
            for i, value in enumerate(record):
                formatted_value = _format_table_value(value, columns[i], utc)
                row_data.append(formatted_value)
            table.add_row(*row_data)
        
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error reading table: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stat():
    """Database statistics (size, indexes, etc.)"""
    conn = _get_db_connection()
    
    try:
        # Get database file size
        db_path = conn.db_path if hasattr(conn, 'db_path') else "unknown"
        if Path(db_path).exists():
            size_bytes = Path(db_path).stat().st_size
            size_mb = size_bytes / (1024 * 1024)
        else:
            size_mb = 0
        
        # Get table statistics
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'").fetchall()
        
        # Get total records across all tables
        total_records = 0
        for (table_name,) in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                total_records += count
            except Exception as e:
                console.print(f"[yellow]Warning: Could not count records in table '{table_name}': {e}[/yellow]")
                # Continue with other tables - don't let one bad table break entire stats
        
        content = []
        content.append(f"[bold yellow]Database Size:[/bold yellow] [bold white]{size_mb:.2f} MB[/bold white]")
        content.append(f"[bold yellow]Tables:[/bold yellow] [bold white]{len(tables)}[/bold white]")
        content.append(f"[bold yellow]Indexes:[/bold yellow] [bold white]{len(indexes)}[/bold white]")
        content.append(f"[bold yellow]Total Records:[/bold yellow] [bold white]{total_records:,}[/bold white]")
        
        panel = Panel(
            "\n".join(content),
            title="✨ [bold cyan]Database Statistics[/bold cyan]",
            title_align="left",
            border_style="bright_blue",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        console.print()
        console.print(panel)
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error getting database statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@destructive("rebuilds database structure, risk of data loss if interrupted")
def vacuum():
    """Optimize database (VACUUM)"""
    conn = _get_db_connection()
    
    try:
        console.print("🔧 Optimizing database...")
        conn.execute("VACUUM")
        console.print("✅ [green]Database optimization complete[/green]")
        
    except Exception as e:
        console.print(f"[red]Error optimizing database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def check():
    """Integrity check"""
    conn = _get_db_connection()
    
    try:
        console.print("🔍 Running integrity check...")
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        
        if result == "ok":
            console.print("✅ [green]Database integrity check passed[/green]")
        else:
            console.print(f"❌ [red]Database integrity issues: {result}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error checking database integrity: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def tail(
    table_name: str = typer.Argument(..., help="Table name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to show"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Show last N records from table"""
    conn = _get_db_connection()
    
    try:
        # Get total count first to determine if we need ordering
        total_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        if total_count == 0:
            console.print(f"[yellow]Table '{table_name}' is empty[/yellow]")
            return
        
        # Try to get records ordered by ROWID (SQLite's implicit primary key) in descending order
        records = conn.execute(f"SELECT * FROM {table_name} ORDER BY ROWID DESC LIMIT {limit}").fetchall()
        
        if not records:
            console.print(f"[yellow]No records found in table '{table_name}'[/yellow]")
            return
        
        # Get column names
        columns = [desc[1] for desc in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
        
        table = Table(
            title=f"✨ [bold cyan]Last {limit} records from {table_name}[/bold cyan]",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        for col in columns:
            col_header = col + get_timezone_suffix(utc) if col.lower() in ['timestamp', 'created_at', 'updated_at', 'date'] else col
            table.add_column(col_header, style="white")
        
        for record in records:
            row_data = []
            for i, value in enumerate(record):
                formatted_value = _format_table_value(value, columns[i], utc)
                row_data.append(formatted_value)
            table.add_row(*row_data)
        
        console.print()
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"[red]Error reading table: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@destructive("allows arbitrary SQL execution including DROP, DELETE, UPDATE")
def exec(
    query: str = typer.Argument(..., help="SQL query to execute"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Execute raw SQL query"""
    conn = _get_db_connection()
    
    try:
        # Safety check for destructive operations
        query_upper = query.upper().strip()
        if any(query_upper.startswith(op) for op in ["DROP", "DELETE", "UPDATE", "INSERT"]):
            if not typer.confirm(f"Execute potentially destructive query: {query}?"):
                console.print("[yellow]Cancelled[/yellow]")
                return
        
        result = conn.execute(query).fetchall()
        
        if not result:
            console.print("[yellow]Query returned no results[/yellow]")
            return
        
        if format == "json":
            import json
            # Convert to list of dicts for JSON output
            columns = [desc[0] for desc in conn.execute(f"PRAGMA table_info(({query}))").fetchall()]
            if not columns:
                # Fallback for non-table queries
                columns = [f"col_{i}" for i in range(len(result[0]))]
            
            data = [dict(zip(columns, row)) for row in result]
            console.print(json.dumps(data, indent=2, default=str))
        else:
            # Table format
            if result and len(result[0]) > 0:
                # Create table with dynamic columns
                table = Table(
                    title=f"✨ [bold cyan]Query Results[/bold cyan]",
                    title_justify="left",
                    border_style="bright_blue",
                    header_style="bold yellow",
                    box=box.SIMPLE_HEAD,
                    padding=(0, 1)
                )
                
                # Get proper column names from query description
                try:
                    # For simple queries, try to get column names from cursor description
                    cursor = conn.execute(query)
                    if hasattr(cursor, 'description') and cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                    else:
                        # Fallback: try to parse column names from query
                        if "COUNT(*)" in query.upper():
                            columns = ["count"]
                        elif "SELECT *" in query.upper():
                            # Get table name and use PRAGMA table_info
                            import re
                            table_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
                            if table_match:
                                table_name = table_match.group(1)
                                table_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                                columns = [col[1] for col in table_info]
                            else:
                                columns = [f"col_{i+1}" for i in range(len(result[0]))]
                        else:
                            columns = [f"col_{i+1}" for i in range(len(result[0]))]
                except Exception:
                    # Final fallback
                    columns = [f"col_{i+1}" for i in range(len(result[0]))]
                
                for col in columns:
                    col_header = col + get_timezone_suffix(utc) if col.lower() in ['timestamp', 'created_at', 'updated_at', 'date'] else col
                    table.add_column(col_header, style="white")
                
                # Add rows
                for row in result:
                    row_data = []
                    for i, val in enumerate(row):
                        formatted_value = _format_table_value(val, columns[i], utc)
                        row_data.append(formatted_value)
                    table.add_row(*row_data)
                
                console.print()
                console.print(table)
                console.print()
            else:
                console.print("[yellow]Query executed successfully (no results)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error executing query: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def sync(
    db_path: str = typer.Option(None, help="Database file path (optional - uses config default)"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be synced without making changes"),
    confirm: bool = typer.Option(False, "--confirm", help="Actually perform the sync (required for safety)")
):
    """Sync database to match latest schema definitions from code."""
    
    # Load configuration and resolve database path
    config = ConfigurationManager()
    
    if db_path:
        db_file = Path(db_path)
    else:
        db_config = config.get(f"database.{db_type}", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_file = AICOPaths.resolve_database_path(filename, directory_mode)
    
    if not db_file.exists():
        console.print(f"❌ [red]Database not found: {db_file}[/red]")
        raise typer.Exit(1)
    
    try:
        console.print(f"🔄 [bold yellow]Database Schema Sync[/bold yellow]")
        console.print(f"📁 Database: [cyan]{db_file}[/cyan]")
        
        if dry_run:
            console.print("🔍 [yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Get database connection
        conn = _get_database_connection(str(db_file))
        
        # Get latest schema definitions from registry
        from aico.data.libsql.registry import SchemaRegistry
        from aico.data.libsql.schema import SchemaManager
        
        # Get all core schemas and their latest definitions
        core_schemas = SchemaRegistry.get_core_schemas()
        if not core_schemas:
            console.print("❌ [red]No core schemas found in registry[/red]")
            raise typer.Exit(1)
        
        # For each schema, sync to latest version
        all_results = []
        for schema in core_schemas:
            console.print(f"\n📋 [bold cyan]Syncing '{schema.name}' schema[/bold cyan]")
            
            # Create schema manager for this schema
            manager = SchemaManager(conn, schema.definitions)
            
            # Perform sync operation
            result = manager.sync_to_latest_schema(schema.definitions, confirm=confirm, dry_run=dry_run)
            all_results.append((schema.name, result))
            
            # Display results for this schema
            if result["conflicts_found"]:
                console.print(f"⚠️  [yellow]Conflicts found in '{schema.name}':[/yellow]")
                for conflict in result["conflicts_found"]:
                    console.print(f"  • {conflict}")
            
            if result["actions"]:
                console.print(f"📋 [bold cyan]Actions for '{schema.name}':[/bold cyan]")
                for action in result["actions"]:
                    console.print(f"  • {action}")
        
        # Summary
        console.print(f"\n📊 [bold cyan]Sync Summary[/bold cyan]")
        
        summary_table = Table(
            title="Schema Sync Results",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        summary_table.add_column("Schema", style="cyan")
        summary_table.add_column("Status", style="white")
        summary_table.add_column("Version", style="white")
        summary_table.add_column("Conflicts", style="yellow")
        
        for schema_name, result in all_results:
            status = "✅ Success" if result["success"] else "❌ Failed"
            version = f"{result['current_version']} → {result['target_version']}"
            conflicts = str(len(result["conflicts_found"]))
            
            summary_table.add_row(schema_name, status, version, conflicts)
        
        console.print(summary_table)
        
        # Show next steps
        all_success = all(result[1]["success"] for result in all_results)
        if all_success:
            if dry_run:
                console.print(f"\n💡 [bold green]Next Steps[/bold green]")
                console.print("  • Run without --dry-run and with --confirm to apply changes")
                console.print("  • Database will be synced to match latest code definitions")
            else:
                console.print(f"\n✅ [bold green]Database Sync Complete[/bold green]")
                console.print("  • Database now matches latest schema definitions")
                console.print("  • All conflicts have been resolved")
        else:
            console.print(f"\n❌ [bold red]Sync Failed[/bold red]")
            if not confirm and not dry_run:
                console.print("  • Use --confirm to actually perform the sync")
                console.print("  • Use --dry-run to preview changes")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to sync database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def snapshot(
    db_path: str = typer.Option(None, help="Database file path (optional - uses config default)"),
    db_type: str = typer.Option("libsql", help="Database type (libsql, duckdb, chroma, rocksdb)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be snapshotted without making changes"),
    confirm: bool = typer.Option(False, "--confirm", help="Actually perform the snapshot (required for safety)")
):
    """Capture current database state as migration baseline, reset history."""
    
    # Load configuration and resolve database path
    config = ConfigurationManager()
    
    if db_path:
        db_file = Path(db_path)
    else:
        db_config = config.get(f"database.{db_type}", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_file = AICOPaths.resolve_database_path(filename, directory_mode)
    
    if not db_file.exists():
        console.print(f"❌ [red]Database not found: {db_file}[/red]")
        raise typer.Exit(1)
    
    try:
        console.print(f"📸 [bold yellow]Database Schema Snapshot[/bold yellow]")
        console.print(f"📁 Database: [cyan]{db_file}[/cyan]")
        
        if dry_run:
            console.print("🔍 [yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Get database connection
        conn = _get_database_connection(str(db_file))
        
        # Import schema manager
        from aico.data.libsql.schema import SchemaManager
        
        # Create schema manager instance
        schema_manager = SchemaManager(conn)
        
        # Perform snapshot operation
        result = schema_manager.snapshot_current_state(confirm=confirm, dry_run=dry_run)
        
        # Display results
        console.print(f"\n📊 [bold cyan]Snapshot Operation Results[/bold cyan]")
        
        # Create results table
        results_table = Table(
            title="Snapshot Summary",
            border_style="bright_blue",
            header_style="bold yellow",
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        
        results_table.add_column("Property", style="cyan")
        results_table.add_column("Value", style="white")
        
        results_table.add_row("Success", "✅ Yes" if result["success"] else "❌ No")
        results_table.add_row("Current Version", str(result["current_version"]))
        results_table.add_row("Tables Found", str(len(result["tables_found"])))
        results_table.add_row("Migrations Cleared", str(result["migrations_cleared"]))
        results_table.add_row("Dry Run", "✅ Yes" if result["dry_run"] else "❌ No")
        
        console.print(results_table)
        
        # Display actions taken
        if result["actions"]:
            console.print(f"\n📋 [bold cyan]Actions Performed[/bold cyan]")
            for action in result["actions"]:
                console.print(f"  • {action}")
        
        # Display tables found
        if result["tables_found"]:
            console.print(f"\n📊 [bold cyan]Tables in Database[/bold cyan]")
            tables_table = Table(
                border_style="bright_blue",
                header_style="bold yellow",
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            tables_table.add_column("Table Name", style="cyan")
            
            for table_name in sorted(result["tables_found"]):
                tables_table.add_row(table_name)
            
            console.print(tables_table)
        
        # Show next steps
        if result["success"]:
            if dry_run:
                console.print(f"\n💡 [bold green]Next Steps[/bold green]")
                console.print("  • Run without --dry-run and with --confirm to create snapshot")
                console.print("  • Current database structure will become new baseline")
                console.print("  • Migration history will be compressed to single baseline")
            else:
                console.print(f"\n✅ [bold green]Snapshot Created Successfully[/bold green]")
                console.print("  • Current database structure is now baseline (version 1)")
                console.print("  • Migration history has been compressed")
                console.print("  • Future migrations will apply from this snapshot")
        else:
            console.print(f"\n❌ [bold red]Snapshot Failed[/bold red]")
            if not confirm and not dry_run:
                console.print("  • Use --confirm to actually create the snapshot")
                console.print("  • Use --dry-run to preview what would be captured")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to create database snapshot: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
