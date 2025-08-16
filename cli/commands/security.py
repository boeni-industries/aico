"""
AICO CLI Security Commands

Provides master password setup, management, and security operations.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
import sys

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from sensitive import sensitive

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.security import AICOKeyManager

# Import shared utilities using the same pattern as other CLI modules
from utils.timezone import format_timestamp_local

def security_callback(ctx: typer.Context):
    """Show help when no subcommand is given instead of showing an error."""
    if ctx.invoked_subcommand is None:
        from utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("setup", "Set up master password for AICO (first-time setup)"),
            ("passwd", "Change the master password (affects all databases)"),
            ("status", "Check security health and key management status"),
            ("session", "Show CLI session status and timeout information"),
            ("clear", "Clear cached master key (forces password re-entry)"),
            ("test", "Performance diagnostics and key derivation benchmarking"),
            ("user-create", "Create a new user with optional PIN authentication"),
            ("user-list", "List all users with filtering options"),
            ("user-update", "Update user profile information"),
            ("user-delete", "Soft delete user (mark as inactive)"),
            ("user-auth", "Authenticate user with PIN"),
            ("user-set-pin", "Set or update user PIN"),
            ("user-stats", "Show user statistics and authentication info")
        ]
        
        examples = [
            "aico security setup",
            "aico security status",
            "aico security session",
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
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)"),
    jwt_only: bool = typer.Option(False, "--jwt-only", help="Only initialize JWT secrets (when master password exists)")
):
    """Set up master password for AICO (first-time setup)."""
    
    key_manager = AICOKeyManager()
    
    # Check if already set up
    master_exists = key_manager.has_stored_key()
    
    # Check JWT secret status
    jwt_exists = False
    try:
        jwt_secret = key_manager.get_jwt_secret("api_gateway")
        jwt_exists = bool(jwt_secret)
    except Exception:
        jwt_exists = False
    
    if master_exists:
        if not jwt_only:
            if jwt_exists:
                console.print("✅ [green]Master password and JWT secrets already set up.[/green]")
                console.print("Use 'aico security passwd' to update master password if needed.")
                raise typer.Exit(0)  # Success exit - nothing to do
            else:
                console.print("🔐 [cyan]Master password exists, initializing missing JWT secrets...[/cyan]")
                jwt_only = True  # Force JWT-only mode
        else:
            console.print("🔐 [cyan]Master password exists, initializing JWT secrets only...[/cyan]")
    
    # Get password if not provided (only for new setup)
    if not jwt_only:
        if not password:
            password = typer.prompt("Enter master password", hide_input=True)
            confirm_password = typer.prompt("Confirm master password", hide_input=True)
            
            if password != confirm_password:
                console.print("❌ [red]Passwords do not match[/red]")
                raise typer.Exit(1)
    
    try:
        # Set up master password (only if not jwt_only)
        if not jwt_only:
            console.print("🔐 Setting up master password...")
            master_key = key_manager.setup_master_password(password)
            console.print("✅ [green]Master password set up successfully![/green]")
            console.print("🔑 Master key derived and stored in system keyring")
            console.print("🔐 You can now initialize encrypted databases")
        
        # Initialize JWT secret for API Gateway (zero-effort security)
        actions_taken = []
        if not jwt_only:
            actions_taken.append("Master password configured")
        
        try:
            # Check if JWT secret already exists before attempting to get it
            existing_jwt = None
            try:
                existing_jwt = key_manager.get_jwt_secret("api_gateway")
            except Exception as e:
                # Log JWT retrieval failure but continue - this is expected for first-time setup
                logger.debug(f"JWT secret retrieval failed (expected for first setup): {e}")
                existing_jwt = None
            
            if not existing_jwt:
                jwt_secret = key_manager.get_jwt_secret("api_gateway")  # This will create it
                console.print("🔒 [green]JWT secret initialized for API Gateway[/green]")
                actions_taken.append("JWT secrets initialized")
            else:
                console.print("🔒 [dim]JWT secret already exists for API Gateway[/dim]")
        except Exception as e:
            console.print(f"⚠️ [yellow]JWT secret initialization failed: {e}[/yellow]")
            console.print("   Run 'aico security setup --jwt-only' to retry JWT initialization")
        
        # Summary of actions taken
        if actions_taken:
            console.print(f"\n✅ [bold green]Setup completed successfully![/bold green]")
            console.print("📋 [cyan]Actions taken:[/cyan]")
            for action in actions_taken:
                console.print(f"   • {action}")
        else:
            console.print(f"\n✅ [green]All security components already configured[/green]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to set up master password: {e}[/red]")
        raise typer.Exit(1)


@app.command("passwd")
@sensitive("changes master password - affects all encrypted databases")
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
def status(
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Check security health and key management status."""
    
    key_manager = AICOKeyManager()
    health_info = key_manager.get_security_health_info()
    
    # Create structured security status with sections
    console.print("\n✨ [bold cyan]AICO Security Health[/bold cyan]\n")
    
    # Overall Security Assessment
    security_level = health_info["security_level"]
    if security_level == "Strong":
        level_display = "Strong"
        level_reason = "Recent key, strong algorithm, optimal parameters"
    elif security_level == "Good":
        level_display = "Good"
        level_reason = "Adequate security, consider rotation soon"
    elif security_level == "Needs Rotation":
        level_display = "Needs Rotation"
        level_reason = "Key is old, rotation recommended"
    else:
        level_display = "Not Set Up"
        level_reason = "Master password not configured"
    
    # Overall Status Panel
    status_panel = Panel(
        f"[bold green]{level_display}[/bold green]\n[dim]{level_reason}[/dim]",
        title="🔐 Security Status",
        border_style="green" if security_level in ["Strong", "Good"] else "yellow"
    )
    console.print(status_panel)
    
    if health_info["has_master_key"]:
        # Master Key Section
        key_table = Table(
            title="🔑 Master Key Configuration",
            title_justify="left",
            show_header=True,
            header_style="bold yellow",
            border_style="bright_blue",
            box=box.SIMPLE_HEAD
        )
        key_table.add_column("Property", style="bold white", justify="left")
        key_table.add_column("Value", style="cyan", justify="left")
        
        if health_info["key_created"]:
            formatted_created = format_timestamp_local(health_info["key_created"], show_utc=utc)
            key_table.add_row("Created", formatted_created)
        if health_info["key_age_days"] is not None:
            age_display = f"{health_info['key_age_days']} days"
            if health_info["key_age_days"] > 365:
                age_display += " (Old)"
            elif health_info["key_age_days"] > 180:
                age_display += " (Consider rotation)"
            key_table.add_row("Age", age_display)
        
        key_table.add_row("Algorithm", health_info["algorithm"])
        key_table.add_row("Key Size", f"{health_info['key_size'] * 8}-bit")
        key_table.add_row("Backup", "Regenerable from password")
        
        console.print(key_table)
        
        # Argon2id Parameters Section
        argon_table = Table(
            title="⚡ Key Derivation Parameters (Argon2id)",
            title_justify="left",
            show_header=True,
            header_style="bold yellow",
            border_style="bright_blue",
            box=box.SIMPLE_HEAD
        )
        argon_table.add_column("Parameter", style="bold white", justify="left")
        argon_table.add_column("Value", style="cyan", justify="left")
        argon_table.add_column("Security Impact", style="dim", justify="left")
        
        if health_info["memory_cost_mb"]:
            memory_impact = "High memory = stronger against GPU attacks"
            argon_table.add_row("Memory Cost", f"{health_info['memory_cost_mb']} MB", memory_impact)
        if health_info["iterations"]:
            time_impact = "More iterations = slower brute force"
            argon_table.add_row("Iterations", str(health_info["iterations"]), time_impact)
        if health_info["parallelism"]:
            parallel_impact = "Parallel threads for optimal performance"
            argon_table.add_row("Parallelism", f"{health_info['parallelism']} threads", parallel_impact)
        
        console.print(argon_table)
        
        # JWT Secrets Section
        jwt_table = Table(
            title="🎫 JWT Authentication Secrets",
            title_justify="left",
            show_header=True,
            header_style="bold yellow",
            border_style="bright_blue",
            box=box.SIMPLE_HEAD
        )
        jwt_table.add_column("Service", style="bold white", justify="left")
        jwt_table.add_column("Status", style="cyan", justify="left")
        jwt_table.add_column("Algorithm", style="dim", justify="left")
        jwt_table.add_column("Key Length", style="dim", justify="left")
        
        # Check JWT secret status with details
        try:
            jwt_secret = key_manager.get_jwt_secret()
            if jwt_secret:
                # JWT secret is typically 256-bit (32 bytes) for HS256
                jwt_table.add_row("API Gateway", "Initialized", "HMAC-SHA256", "256-bit")
                jwt_status = "Ready for authentication"
            else:
                jwt_table.add_row("API Gateway", "Missing", "-", "-")
                jwt_status = "Authentication will fail"
        except Exception:
            jwt_table.add_row("API Gateway", "Error", "-", "-")
            jwt_status = "Authentication will fail"
        
        console.print(jwt_table)
        
        # JWT Status Summary
        jwt_panel = Panel(
            jwt_status,
            title="🔐 JWT Status",
            border_style="green" if jwt_status.startswith("Ready") else "red"
        )
        console.print(jwt_panel)
    
    # Show recommendations
    if not health_info["has_master_key"]:
        console.print("\n⚠️ [yellow]Master password not set up[/yellow]")
        console.print("Run 'aico security setup' to get started")
    else:
        # Check JWT secret status for recommendations
        jwt_missing = False
        try:
            jwt_secret = key_manager.get_jwt_secret()
            if not jwt_secret:
                jwt_missing = True
        except Exception:
            jwt_missing = True
        
        if jwt_missing:
            console.print("\n⚠️ [yellow]JWT secrets not initialized[/yellow]")
            console.print("Run 'aico security setup --jwt-only' to initialize JWT secrets")
        elif health_info["rotation_recommended"]:
            console.print("\n🔄 [yellow]Key rotation recommended[/yellow]")
            console.print("Run 'aico security passwd' to update your master password")
        else:
            console.print("\n✅ [green]Security configuration is healthy[/green]")
            console.print("🔐 All systems ready for encrypted operations")


@app.command()
def session(
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Show CLI session status and timeout information."""
    
    key_manager = AICOKeyManager()
    
    if not key_manager.has_stored_key():
        console.print("❌ [red]No master password set up.[/red]")
        console.print("Use 'aico security setup' first.")
        raise typer.Exit(1)
    
    # Get session information
    session_info = key_manager.get_session_info()
    
    console.print("\n🔐 [bold cyan]CLI Session Status[/bold cyan]\n")
    
    if session_info["active"]:
        # Active session
        console.print("✅ [green]Session Active[/green]")
        
        # Create session details table
        session_table = Table(
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        session_table.add_column("Property", style="bold white", justify="left")
        session_table.add_column("Value", style="cyan", justify="left")
        
        # Format timestamps with timezone awareness
        formatted_created = format_timestamp_local(session_info["created_at"], show_utc=utc)
        formatted_last_accessed = format_timestamp_local(session_info["last_accessed"], show_utc=utc)
        formatted_expires = format_timestamp_local(session_info["expires_at"], show_utc=utc)
        
        session_table.add_row("Created", formatted_created)
        session_table.add_row("Last Accessed", formatted_last_accessed)
        session_table.add_row("Expires", formatted_expires)
        session_table.add_row("Timeout", f"{session_info['timeout_minutes']} minutes")
        session_table.add_row("Time Remaining", f"{session_info['time_remaining_minutes']} minutes")
        
        console.print(session_table)
        
        # Show status based on time remaining
        time_remaining = session_info['time_remaining_minutes']
        if time_remaining > 15:
            console.print(f"\n🟢 [green]Session expires in {time_remaining} minutes[/green]")
        elif time_remaining > 5:
            console.print(f"\n🟡 [yellow]Session expires in {time_remaining} minutes[/yellow]")
        else:
            console.print(f"\n🔴 [red]Session expires soon ({time_remaining} minutes)[/red]")
            
        console.print("\n💡 [dim]Session automatically extends on CLI activity[/dim]")
        
    else:
        # No active session
        console.print("❌ [red]No Active Session[/red]")
        console.print("\n📝 [cyan]Next CLI command will prompt for password[/cyan]")
        console.print(f"🕐 [dim]Session timeout: {key_manager.SESSION_TIMEOUT_MINUTES} minutes[/dim]")


@app.command()
def logout():
    """Clear CLI authentication session."""
    
    try:
        key_manager = AICOKeyManager()
        
        # Check if there's an active session
        session_info = key_manager.get_session_info()
        if not session_info.get('active', False):
            console.print("📝 [cyan]Already logged out[/cyan]")
            return
        
        # Simple: just clear the session cache
        key_manager._clear_session()
        
        console.print("✅ [green]Logged out successfully[/green]")
        console.print("🔐 Next sensitive command will prompt for password")
        
    except Exception as e:
        console.print(f"❌ [red]Logout failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive("clears security credentials and active sessions")
def clear(
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Clear cached master key and active session (forces password re-entry)."""
    
    if not confirm:
        console.print("⚠️ [bold red]WARNING: This will clear your cached master key and session![/bold red]")
        console.print("📝 [cyan]What this does:[/cyan]")
        console.print("  • Removes cached key from system keyring")
        console.print("  • Clears active CLI session")
        console.print("  • Forces password re-entry for next operation")
        console.print("  • [green]NO DATA LOSS[/green] - encrypted databases remain intact")
        console.print("  • Same password will regenerate identical key")
        console.print("")
        console.print("⚠️ [yellow]Risk: If you forget your master password after clearing,\n   all encrypted data becomes permanently inaccessible![/yellow]")
        
        if not typer.confirm("Are you sure you want to continue?"):
            console.print("Operation cancelled.")
            raise typer.Exit()
    
    try:
        key_manager = AICOKeyManager()
        key_manager.clear_stored_key()
        
        console.print("✅ [green]Cached master key cleared successfully[/green]")
        console.print("🔐 Next operation will prompt for master password")
        console.print("💡 [dim]Remember: Same password regenerates same key - no data lost[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to clear cached key: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test():
    """🧪 Test security operations and benchmark key derivation performance."""
    
    key_manager = AICOKeyManager()
    
    if not key_manager.has_stored_key():
        console.print("❌ [red]No master password set up.[/red]")
        console.print("Use 'aico security setup' first.")
        raise typer.Exit(1)
    
    console.print("\n🧪 [bold cyan]Security Operations Test[/bold cyan]\n")
    
    # Test 1: Master Key Access
    console.print("🔑 [yellow]Testing master key access...[/yellow]")
    try:
        import time
        start_time = time.time()
        master_key = key_manager.get_master_key()
        key_access_time = (time.time() - start_time) * 1000
        
        if master_key:
            console.print(f"✅ [green]Master key access: {key_access_time:.1f}ms[/green]")
        else:
            console.print("❌ [red]Master key access failed[/red]")
            return
    except Exception as e:
        console.print(f"❌ [red]Master key access error: {e}[/red]")
        return
    
    # Test 2: JWT Secret Derivation Benchmark
    console.print("\n🎫 [yellow]Testing JWT secret derivation performance...[/yellow]")
    
    try:
        # Benchmark JWT secret generation
        jwt_times = []
        for i in range(3):
            start_time = time.time()
            jwt_secret = key_manager.get_jwt_secret()
            jwt_time = (time.time() - start_time) * 1000
            jwt_times.append(jwt_time)
            
            if i == 0:  # First call might be slower due to derivation
                console.print(f"  First call (derivation): {jwt_time:.1f}ms")
            else:
                console.print(f"  Cached call {i}: {jwt_time:.1f}ms")
        
        avg_time = sum(jwt_times) / len(jwt_times)
        console.print(f"✅ [green]JWT secret average: {avg_time:.1f}ms[/green]")
        
        # JWT Secret Details
        if jwt_secret:
            import hashlib
            secret_hash = hashlib.sha256(jwt_secret.encode()).hexdigest()[:16]
            console.print(f"🔐 [dim]JWT secret hash (first 16 chars): {secret_hash}[/dim]")
            console.print(f"📏 [dim]JWT secret length: {len(jwt_secret)} characters[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]JWT secret test failed: {e}[/red]")
    
    # Test 3: Database Key Derivation Benchmark
    console.print("\n🛢️ [yellow]Testing database key derivation...[/yellow]")
    
    try:
        db_times = []
        for i in range(3):
            start_time = time.time()
            db_key = key_manager.derive_database_key("test_db")
            db_time = (time.time() - start_time) * 1000
            db_times.append(db_time)
            
            if i == 0:
                console.print(f"  First derivation: {db_time:.1f}ms")
            else:
                console.print(f"  Subsequent call {i}: {db_time:.1f}ms")
        
        avg_db_time = sum(db_times) / len(db_times)
        console.print(f"✅ [green]Database key average: {avg_db_time:.1f}ms[/green]")
        
    except Exception as e:
        console.print(f"❌ [red]Database key test failed: {e}[/red]")
    
    # Performance Summary
    console.print("\n📊 [bold cyan]Performance Summary[/bold cyan]")
    
    perf_table = Table(
        show_header=True,
        header_style="bold yellow",
        border_style="bright_blue",
        box=box.SIMPLE_HEAD
    )
    perf_table.add_column("Operation", style="bold white", justify="left")
    perf_table.add_column("Average Time", style="cyan", justify="right")
    perf_table.add_column("Performance", style="green", justify="left")
    
    # Performance assessment
    def assess_performance(time_ms, operation_type):
        if operation_type == "key_access":
            if time_ms < 10:
                return "Excellent"
            elif time_ms < 50:
                return "Good"
            else:
                return "Slow"
        elif operation_type == "derivation":
            if time_ms < 100:
                return "Fast"
            elif time_ms < 500:
                return "Normal"
            else:
                return "Slow"
    
    try:
        perf_table.add_row("Master Key Access", f"{key_access_time:.1f}ms", 
                          assess_performance(key_access_time, "key_access"))
        perf_table.add_row("JWT Secret", f"{avg_time:.1f}ms", 
                          assess_performance(avg_time, "derivation"))
        perf_table.add_row("Database Key", f"{avg_db_time:.1f}ms", 
                          assess_performance(avg_db_time, "derivation"))
        
        console.print(perf_table)
        
        # Overall assessment
        if all(t < 100 for t in [key_access_time, avg_time, avg_db_time]):
            console.print("\n🚀 [green]All security operations performing optimally[/green]")
        elif any(t > 500 for t in [key_access_time, avg_time, avg_db_time]):
            console.print("\n⚠️ [yellow]Some operations are slow - consider system optimization[/yellow]")
        else:
            console.print("\n✅ [green]Security operations within normal performance range[/green]")
            
    except NameError:
        console.print("❌ [red]Performance summary unavailable due to test failures[/red]")


# User Management Commands

@app.command("user-create")
def user_create(
    full_name: str = typer.Argument(None, help="User's full name"),
    nickname: str = typer.Option(None, "--nickname", "-n", help="Optional nickname"),
    user_type: str = typer.Option("parent", "--type", "-t", help="User type (parent, child, admin)"),
    pin: str = typer.Option(None, "--pin", "-p", help="Optional PIN for authentication"),
    ctx: typer.Context = typer.Context
):
    """Create a new user with optional PIN authentication"""
    
    if full_name is None:
        console.print("\n❌ [red]Missing required argument: FULL_NAME[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-create [OPTIONS] FULL_NAME\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print('  aico security user-create "John Doe"')
        console.print('  aico security user-create "Jane Smith" --nickname "Janie" --type child')
        console.print('  aico security user-create "Bob Wilson" --pin 1234 --type parent')
        console.print('  aico security user-create "Alice Cooper" --nickname "Al" --type admin --pin 5678')
        console.print("\n[bold yellow]Options:[/bold yellow]")
        console.print("  --nickname, -n    Optional nickname for the user")
        console.print("  --type, -t        User type: parent, child, admin (default: parent)")
        console.print("  --pin, -p         Optional PIN for authentication")
        console.print("\n[dim]Use 'aico security user-list' to see existing users[/dim]")
        raise typer.Exit(1)
    import asyncio
    from pathlib import Path
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Create user
        async def create_user():
            user = await user_service.create_user(
                full_name=full_name,
                nickname=nickname,
                user_type=user_type,
                pin=pin
            )
            return user
        
        user = asyncio.run(create_user())
        
        # Display success
        console.print(f"\n✅ [green]User created successfully[/green]")
        console.print(f"UUID: {user.uuid}")
        console.print(f"Name: {user.full_name}")
        if user.nickname:
            console.print(f"Nickname: {user.nickname}")
        console.print(f"Type: {user.user_type}")
        if pin:
            console.print("PIN: [dim]Configured[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to create user: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-list")
def user_list(
    user_type: str = typer.Option(None, "--type", "-t", help="Filter by user type"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of users to show")
):
    """List all users"""
    import asyncio
    from pathlib import Path
    from rich.table import Table
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    console = Console()
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # List users
        async def list_users():
            users = await user_service.list_users(user_type=user_type, limit=limit)
            return users
        
        users = asyncio.run(list_users())
        
        if not users:
            console.print("No users found.")
            return
        
        # Create table
        table = Table(title="AICO Users")
        table.add_column("UUID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Nickname", style="yellow")
        table.add_column("Type", style="blue")
        table.add_column("Created", style="dim")
        
        for user in users:
            table.add_row(
                user.uuid[:8] + "...",
                user.full_name,
                user.nickname or "-",
                user.user_type,
                str(user.created_at)[:19] if user.created_at else "-"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ [red]Failed to list users: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-auth")
def user_auth(
    user_uuid: str = typer.Argument(None, help="User UUID"),
    pin: str = typer.Option(None, "--pin", "-p", help="User PIN", hide_input=True)
):
    """Authenticate user with PIN"""
    
    if user_uuid is None:
        console.print("\n❌ [red]Missing required argument: USER_UUID[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-auth [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print('  aico security user-auth abc123def --pin 1234')
        console.print('  aico security user-auth 550e8400-e29b-41d4-a716-446655440000 -p 5678')
        console.print("\n[bold yellow]Required Options:[/bold yellow]")
        console.print("  --pin, -p         User's PIN for authentication")
        console.print("\n[dim]Use 'aico security user-list' to find user UUIDs[/dim]")
        raise typer.Exit(1)
    
    if pin is None:
        console.print("\n❌ [red]Missing required option: --pin[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-auth [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print(f'  aico security user-auth {user_uuid} --pin 1234')
        console.print(f'  aico security user-auth {user_uuid} -p 5678')
        console.print("\n[dim]Use 'aico security user-list' to find user UUIDs[/dim]")
        raise typer.Exit(1)
    import asyncio
    from pathlib import Path
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Authenticate user
        async def authenticate():
            result = await user_service.authenticate_user(user_uuid, pin)
            return result
        
        result = asyncio.run(authenticate())
        
        if result["success"]:
            user = result["user"]
            console.print(f"\n✅ [green]Authentication successful[/green]")
            console.print(f"User: {user.full_name}")
            if user.nickname:
                console.print(f"Nickname: {user.nickname}")
            if result.get("last_login"):
                console.print(f"Last login: {result['last_login']}")
        else:
            console.print(f"\n❌ [red]Authentication failed: {result['error']}[/red]")
            if result.get("failed_attempts"):
                console.print(f"Failed attempts: {result['failed_attempts']}")
            if result.get("locked"):
                console.print("⚠️ [yellow]Account is locked[/yellow]")
        
    except Exception as e:
        console.print(f"❌ [red]Authentication error: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-update")
def user_update(
    user_uuid: str = typer.Argument(None, help="User UUID to update"),
    full_name: str = typer.Option(None, "--name", "-n", help="Update full name"),
    nickname: str = typer.Option(None, "--nickname", help="Update nickname"),
    user_type: str = typer.Option(None, "--type", "-t", help="Update user type (parent, child, admin)")
):
    """Update user profile information"""
    
    if user_uuid is None:
        console.print("\n❌ [red]Missing required argument: USER_UUID[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-update [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print('  aico security user-update abc123def --name "John Smith"')
        console.print('  aico security user-update abc123def --nickname "Johnny"')
        console.print('  aico security user-update abc123def --name "Jane Doe" --nickname "Janie"')
        console.print("\n[bold yellow]Options:[/bold yellow]")
        console.print("  --name, -n        Update user's full name")
        console.print("  --nickname        Update user's nickname (use empty string to clear)")
        console.print("  --type, -t        User type (defaults to 'person' - currently not used)")
        console.print("\n[dim]Use 'aico security user-list' to find user UUIDs[/dim]")
        raise typer.Exit(1)
    import asyncio
    from pathlib import Path
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    # Get default user type from configuration
    default_user_type = config_manager.get("user_profiles.default_user_type", "person")
    
    # Note: user_type field is currently not used - all users are 'person' type
    # Validate user_type if provided (only 'person' is valid)
    if user_type and user_type != "person":
        console.print(f"❌ [red]Invalid user type '{user_type}'. Only 'person' is currently supported.[/red]")
        console.print(f"[dim]Note: The user_type field defaults to '{default_user_type}' and is currently not used.[/dim]")
        raise typer.Exit(1)
    
    # Check if any updates provided
    updates = {}
    if full_name:
        updates['full_name'] = full_name
    if nickname is not None:  # Allow empty string to clear nickname
        updates['nickname'] = nickname if nickname else None
    if user_type:
        updates['user_type'] = user_type
    
    if not updates:
        console.print("❌ [red]No updates provided. Use --name, --nickname, or --type[/red]")
        raise typer.Exit(1)
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Update user
        async def update_user():
            user = await user_service.update_user(user_uuid, updates)
            return user
        
        user = asyncio.run(update_user())
        
        if user:
            console.print(f"\n✅ [green]User updated successfully[/green]")
            console.print(f"UUID: {user.uuid}")
            console.print(f"Name: {user.full_name}")
            if user.nickname:
                console.print(f"Nickname: {user.nickname}")
            console.print(f"Type: {user.user_type}")
            console.print(f"Updated: {user.updated_at}")
        else:
            console.print(f"❌ [red]User not found: {user_uuid}[/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"❌ [red]Failed to update user: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-delete")
def user_delete(
    user_uuid: str = typer.Argument(None, help="User UUID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Soft delete user (mark as inactive)"""
    
    if user_uuid is None:
        console.print("\n❌ [red]Missing required argument: USER_UUID[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-delete [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print('  aico security user-delete abc123def')
        console.print('  aico security user-delete 550e8400-e29b-41d4-a716-446655440000 --confirm')
        console.print("\n[bold yellow]Options:[/bold yellow]")
        console.print("  --confirm         Skip confirmation prompt")
        console.print("\n[dim]This is a soft delete - user data is preserved but marked inactive[/dim]")
        console.print("[dim]Use 'aico security user-list' to find user UUIDs[/dim]")
        raise typer.Exit(1)
    import asyncio
    from pathlib import Path
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Get user first to show what will be deleted
        async def get_user():
            user = await user_service.get_user(user_uuid)
            return user
        
        user = asyncio.run(get_user())
        
        if not user:
            console.print(f"❌ [red]User not found: {user_uuid}[/red]")
            raise typer.Exit(1)
        
        # Confirmation prompt
        if not confirm:
            console.print(f"⚠️ [yellow]About to delete user:[/yellow]")
            console.print(f"  UUID: {user.uuid}")
            console.print(f"  Name: {user.full_name}")
            if user.nickname:
                console.print(f"  Nickname: {user.nickname}")
            console.print(f"  Type: {user.user_type}")
            console.print(f"\n[dim]Note: This is a soft delete - user will be marked inactive but data preserved[/dim]")
            
            if not typer.confirm("Are you sure you want to delete this user?"):
                console.print("Operation cancelled.")
                raise typer.Exit()
        
        # Delete user
        async def delete_user():
            success = await user_service.delete_user(user_uuid)
            return success
        
        success = asyncio.run(delete_user())
        
        if success:
            console.print(f"\n✅ [green]User deleted successfully[/green]")
            console.print(f"User '{user.full_name}' has been marked as inactive")
        else:
            console.print(f"❌ [red]Failed to delete user (may already be inactive)[/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"❌ [red]Failed to delete user: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-set-pin")
def user_set_pin(
    user_uuid: str = typer.Argument(None, help="User UUID"),
    new_pin: str = typer.Option(None, "--new-pin", "-n", help="New PIN", hide_input=True),
    old_pin: str = typer.Option(None, "--old-pin", "-o", help="Current PIN (required if user has existing PIN)", hide_input=True)
):
    """Set or update user PIN"""
    
    if user_uuid is None:
        console.print("\n❌ [red]Missing required argument: USER_UUID[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-set-pin [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print('  aico security user-set-pin abc123def --new-pin 1234')
        console.print('  aico security user-set-pin abc123def -n 5678 --old-pin 1234')
        console.print("\n[bold yellow]Required Options:[/bold yellow]")
        console.print("  --new-pin, -n     New PIN for the user")
        console.print("\n[bold yellow]Optional:[/bold yellow]")
        console.print("  --old-pin, -o     Current PIN (required if user already has a PIN)")
        console.print("\n[dim]Use 'aico security user-list' to find user UUIDs[/dim]")
        raise typer.Exit(1)
    
    if new_pin is None:
        console.print("\n❌ [red]Missing required option: --new-pin[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-set-pin [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print(f'  aico security user-set-pin {user_uuid} --new-pin 1234')
        console.print(f'  aico security user-set-pin {user_uuid} -n 5678 --old-pin 1234')
        console.print("\n[dim]Use 'aico security user-list' to find user UUIDs[/dim]")
        raise typer.Exit(1)
    import asyncio
    from pathlib import Path
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Set PIN
        async def set_pin():
            try:
                result = await user_service.set_pin(user_uuid, new_pin, old_pin)
                return result
            except ValueError as e:
                if "Old PIN required" in str(e):
                    return "old_pin_required"
                elif "User not found" in str(e):
                    return "user_not_found"
                else:
                    raise
        
        result = asyncio.run(set_pin())
        
        if result == "user_not_found":
            console.print(f"❌ [red]User not found: {user_uuid}[/red]")
            raise typer.Exit(1)
        elif result == "old_pin_required":
            console.print("❌ [red]User already has a PIN. Please provide --old-pin to update it.[/red]")
            raise typer.Exit(1)
        elif result is False:
            console.print("❌ [red]Invalid old PIN[/red]")
            raise typer.Exit(1)
        elif result is True:
            console.print("✅ [green]PIN set successfully[/green]")
        
    except Exception as e:
        console.print(f"❌ [red]Error setting PIN: {e}[/red]")
        raise typer.Exit(1)



@app.command("user-stats")
def user_stats():
    """Show user statistics"""
    import asyncio
    from pathlib import Path
    from rich.table import Table
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    console = Console()
    
    try:
        # Initialize configuration and paths
        config_manager = ConfigurationManager()
        
        # Use configuration-based path resolution (following database command pattern)
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = AICOKeyManager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Get stats
        async def get_stats():
            stats = await user_service.get_user_stats()
            return stats
        
        stats = asyncio.run(get_stats())
        
        console.print("\n📊 [bold]User Statistics[/bold]")
        console.print(f"Total Users: {stats.get('total_users', 0)}")
        
        # Users by type
        users_by_type = stats.get('users_by_type', {})
        if users_by_type:
            console.print("\nUsers by Type:")
            for user_type, count in users_by_type.items():
                console.print(f"  {user_type}: {count}")
        
        # Authentication stats
        auth_stats = stats.get('authentication', {})
        if auth_stats:
            console.print(f"\nAuthentication:")
            console.print(f"  Users with PIN: {auth_stats.get('total_with_auth', 0)}")
            console.print(f"  Locked accounts: {auth_stats.get('locked_accounts', 0)}")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to get user stats: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
