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
from cli.decorators.sensitive import sensitive, destructive

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
from cli.utils.timezone import format_timestamp_local

def _get_key_manager():
    """Helper function to get configured AICOKeyManager instance."""
    from aico.core.config import ConfigurationManager
    config_manager = ConfigurationManager()
    config_manager.initialize(lightweight=True)
    key_manager = AICOKeyManager(config_manager)
    key_manager.config_manager = config_manager  # Attach for CLI use only
    return key_manager

def security_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
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
            ("user-delete", "Delete user (soft delete by default, --hard for permanent)"),
            ("user-cleanup", "Remove all soft-deleted users from database (IRREVERSIBLE)"),
            ("user-auth", "Authenticate user with PIN"),
            ("user-set-pin", "Set or update user PIN"),
            ("user-stats", "Show user statistics and authentication info"),
            ("role-assign", "Assign role to user (admin, user, service, cli)"),
            ("role-revoke", "Revoke role from user"),
            ("role-list", "List user roles and permissions"),
            ("role-show", "Show available roles and their permissions"),
            ("role-check", "Check if user has specific permission"),
            ("role-bootstrap", "Bootstrap admin role for initial setup")
        ]
        
        examples = [
            "aico security setup",
            "aico security status",
            "aico security session",
            "aico security test",
            "aico security passwd",
            "aico security role-bootstrap <user-uuid>",
            "aico security role-assign <user-uuid> admin",
            "aico security role-list <user-uuid>"
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
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)
console = Console()


@app.command(
    help="""Set up master password for AICO (first-time setup).

Initializes the master password and JWT secrets for secure AICO operations.
This is required before using any encrypted features.

Examples:
  aico security setup
  aico security setup --password mypassword
  aico security setup --jwt-only
"""
)
def setup(
    password: str = typer.Option(None, "--password", "-p", help="Master password (will prompt if not provided)"),
    jwt_only: bool = typer.Option(False, "--jwt-only", help="Only initialize JWT secrets (when master password exists)")
):
    """Set up master password for AICO (first-time setup)."""
    
    key_manager = _get_key_manager()
    
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
                console.print("🔐 [cyan]Master password and JWT secrets exist, validating all security components...[/cyan]")
                jwt_only = True  # Skip password setup but continue with validation
            else:
                console.print("🔐 [cyan]Master password exists, initializing missing JWT secrets...[/cyan]")
                jwt_only = True  # Force JWT-only mode
        else:
            console.print("🔐 [cyan]Master password exists, validating security components...[/cyan]")
    
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
        
        # Initialize file encryption keys (test derivation)
        try:
            console.print("🔐 Testing file encryption key derivation...")
            master_key = key_manager.authenticate(interactive=False)
            
            # Test common file encryption purposes
            test_purposes = ["config", "logs", "chroma", "cache"]
            for purpose in test_purposes:
                file_key = key_manager.derive_file_encryption_key(master_key, purpose)
                # Verify key is 32 bytes for AES-256
                if len(file_key) != 32:
                    raise ValueError(f"Invalid key length for purpose '{purpose}': {len(file_key)} bytes")
            
            console.print("✅ [green]File encryption keys validated[/green]")
            actions_taken.append("File encryption keys validated")
            
        except Exception as e:
            console.print(f"⚠️ [yellow]File encryption key validation failed: {e}[/yellow]")
            console.print("   File encryption may not work properly")
        
        # Initialize CurveZMQ transport keys for message bus encryption
        try:
            console.print("🔒 Setting up CurveZMQ transport encryption...")
            master_key = key_manager.authenticate(interactive=False)
            
            # Test CurveZMQ key derivation for all message bus components
            curve_components = [
                "message_bus_broker",
                "message_bus_client_api_gateway",
                "message_bus_client_log_consumer", 
                "message_bus_client_scheduler",
                "message_bus_client_cli",
                "message_bus_client_modelservice",
                "zmq_log_transport",  # ZMQ log transport for cross-service logging
                "message_bus_client_system_host",
                "message_bus_client_backend_modules"
            ]
            
            for component in curve_components:
                public_key, secret_key = key_manager.derive_curve_keypair(master_key, component)
                # Verify keys are 40-character Z85 encoded strings for CurveZMQ
                if len(public_key) != 40 or len(secret_key) != 40:
                    raise ValueError(f"Invalid CurveZMQ key length for component '{component}': pub={len(public_key)}, sec={len(secret_key)} chars (expected 40)")
                # Verify they are valid Z85 strings
                if not all(c in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#" for c in public_key + secret_key):
                    raise ValueError(f"Invalid Z85 encoding for component '{component}'")
            
            console.print("✅ [green]CurveZMQ transport keys validated[/green]")
            console.print("🛡️ [green]Message bus encryption ready[/green]")
            actions_taken.append("CurveZMQ transport keys validated")
            
        except Exception as e:
            console.print(f"⚠️ [yellow]CurveZMQ transport key validation failed: {e}[/yellow]")
            console.print("   Message bus encryption may not work properly")
        
        # Summary of actions taken
        if actions_taken:
            console.print(f"\n✅ [green]Setup complete! Actions taken:[/green]")
            for action in actions_taken:
                console.print(f"   • {action}")
        
        console.print("\n🚀 [bold green]AICO security is now ready![/bold green]")
        console.print("You can now:")
        console.print("  • Initialize encrypted databases with 'aico db init'")
        console.print("  • Use encrypted files with EncryptedFile class")
        console.print("  • Start the backend with 'aico gateway start'")
        console.print("  • Check security status with 'aico security status'")
        
    except Exception as e:
        console.print(f"❌ [red]Setup failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("passwd")
@sensitive("changes master password - affects all encrypted databases")
def passwd():
    """Change the master password (affects all databases)."""
    
    key_manager = _get_key_manager()
    
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


@app.command(
    help="""Check security health and key management status.

Shows master password status, keyring health, JWT secrets, and security diagnostics.

Examples:
  aico security status
  aico security status --utc
"""
)
def status(
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Check security health and key management status."""
    
    key_manager = _get_key_manager()
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
        
        # Transport Encryption Section
        transport_table = Table(
            title="🚀 Transport Encryption (Frontend-Backend)",
            title_justify="left",
            show_header=True,
            header_style="bold yellow",
            border_style="bright_blue",
            box=box.SIMPLE_HEAD
        )
        transport_table.add_column("Component", style="bold white", justify="left")
        transport_table.add_column("Status", style="cyan", justify="left")
        transport_table.add_column("Details", style="dim", justify="left")
        
        # Default values for error case
        transport_enabled = False
        transport_border = "yellow"
        transport_status = "Transport encryption status unknown"
        algorithm = "Unknown"
        try:
            # Check transport encryption configuration
            transport_config = key_manager.config_manager.get("security", {}).get("transport_encryption", {})
            transport_enabled = transport_config.get("enabled", True)
            algorithm = transport_config.get("algorithm", "XChaCha20-Poly1305")
            if transport_enabled:
                transport_table.add_row("Encryption", "Enabled", f"{algorithm} authenticated encryption")
                transport_table.add_row("Identity Keys", "Ed25519", "Component signing keys")
                transport_table.add_row("Session Keys", "X25519", "Ephemeral key exchange")
                
                # Session settings
                session_config = transport_config.get("session", {})
                timeout = session_config.get("timeout_seconds", 3600)
                transport_table.add_row("Session Timeout", f"{timeout}s", f"{timeout//60} minutes")
                
                # Handshake settings
                handshake_config = transport_config.get("handshake", {})
                challenge_size = handshake_config.get("challenge_size", 32)
                transport_table.add_row("Challenge Size", f"{challenge_size * 8}-bit", "Handshake security")
                
                transport_status = "Zero-effort end-to-end encryption active"
                transport_border = "green"
            else:
                transport_table.add_row("Encryption", "Disabled", "Transport not encrypted")
                transport_table.add_row("Security Level", "Basic HTTPS", "TLS only")
                transport_status = "Transport encryption disabled - using TLS only"
                transport_border = "yellow"
        except Exception as e:
            transport_table.add_row("Configuration", "Error", f"Failed to load: {e}")
            transport_status = f"Transport encryption status error: {e}"
            transport_border = "red"
        console.print(transport_table)
        # Transport Status Summary
        transport_panel = Panel(
            transport_status,
            title="🔐 Transport Security",
            border_style=transport_border
        )
        console.print(transport_panel)
        
        # CurveZMQ Message Bus Encryption Section
        curvezmq_table = Table(
            title="🔒 CurveZMQ Message Bus Encryption",
            title_justify="left",
            show_header=True,
            header_style="bold yellow",
            border_style="bright_blue",
            box=box.SIMPLE_HEAD
        )
        curvezmq_table.add_column("Component", style="bold white", justify="left")
        curvezmq_table.add_column("Status", style="cyan", justify="left")
        curvezmq_table.add_column("Details", style="dim", justify="left")
        
        # Default values for error case
        curvezmq_enabled = False
        curvezmq_border = "yellow"
        curvezmq_status = "CurveZMQ encryption status unknown"
        working_components = 0
        total_components = 0
        
        try:
            # Check CurveZMQ encryption configuration
            transport_config = key_manager.config_manager.get("security", {}).get("transport", {})
            curvezmq_enabled = transport_config.get("message_bus_encryption", True)
            
            if curvezmq_enabled:
                # Test CurveZMQ key derivation for all components
                master_key = key_manager.authenticate(interactive=False)
                curve_components = [
                    ("Broker", "message_bus_broker"),
                    ("API Gateway", "message_bus_client_api_gateway"),
                    ("Log Consumer", "message_bus_client_log_consumer"), 
                    ("Scheduler", "message_bus_client_scheduler"),
                    ("CLI", "message_bus_client_cli"),
                    ("Model Service", "message_bus_client_modelservice"),
                    ("ZMQ Log Transport", "zmq_log_transport"),
                    ("System Host", "message_bus_client_system_host"),
                    ("Backend Modules", "message_bus_client_backend_modules")
                ]
                
                total_components = len(curve_components)
                
                for display_name, component_name in curve_components:
                    try:
                        public_key, secret_key = key_manager.derive_curve_keypair(master_key, component_name)
                        if len(public_key) == 40 and len(secret_key) == 40:
                            curvezmq_table.add_row(display_name, "Ready", "CurveZMQ keypair available")
                            working_components += 1
                        else:
                            curvezmq_table.add_row(display_name, "Invalid", f"Key length error: {len(public_key)}/{len(secret_key)} chars")
                    except Exception as e:
                        curvezmq_table.add_row(display_name, "Error", f"Key derivation failed: {str(e)[:40]}...")
                
                # CurveZMQ configuration details
                curve_config = transport_config.get("curvezmq", {})
                auth_policy = curve_config.get("authentication_policy", "CURVE_ALLOW_ANY")
                key_derivation = curve_config.get("key_derivation", {})
                iterations = key_derivation.get("iterations", 1)
                memory_mb = key_derivation.get("memory_cost", 65536) // 1024  # Convert KiB to MB
                
                curvezmq_table.add_row("Authentication", "Configured", f"Policy: {auth_policy}")
                curvezmq_table.add_row("Key Derivation", "Argon2id", f"{iterations} iterations, {memory_mb}MB memory")
                
                # Overall status
                if working_components == total_components:
                    curvezmq_status = f"All {total_components} components ready for encrypted communication"
                    curvezmq_border = "green"
                elif working_components > 0:
                    curvezmq_status = f"{working_components}/{total_components} components ready - partial encryption"
                    curvezmq_border = "yellow"
                else:
                    curvezmq_status = "No components ready - message bus encryption unavailable"
                    curvezmq_border = "red"
            else:
                curvezmq_table.add_row("Encryption", "Disabled", "Message bus uses plaintext")
                curvezmq_table.add_row("Security Level", "None", "All inter-component communication unencrypted")
                curvezmq_status = "CurveZMQ encryption disabled - plaintext message bus"
                curvezmq_border = "red"
                
        except Exception as e:
            curvezmq_table.add_row("Configuration", "Error", f"Failed to check status: {str(e)[:50]}...")
            curvezmq_status = f"CurveZMQ status check failed: {e}"
            curvezmq_border = "red"
            
        console.print(curvezmq_table)
        
        # CurveZMQ Status Summary
        curvezmq_panel = Panel(
            curvezmq_status,
            title="🔒 Message Bus Security",
            border_style=curvezmq_border
        )
        console.print(curvezmq_panel)
    
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


@app.command(
    help="""Show CLI session status and timeout information.

Displays current authentication session details, timeout settings, and session health.

Examples:
  aico security session
  aico security session --utc
"""
)
def session(
    utc: bool = typer.Option(False, "--utc", help="Display timestamps in UTC instead of local time")
):
    """Show CLI session status and timeout information."""
    
    key_manager = _get_key_manager()
    
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


@app.command(
    help="""Clear CLI authentication session.

Clears the current CLI authentication session, requiring re-authentication for future commands.

Examples:
  aico security logout
"""
)
def logout():
    """Clear CLI authentication session."""
    
    try:
        key_manager = _get_key_manager()
        
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


@app.command(help="Clear cached master key and active session (forces password re-entry)")
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
        key_manager = _get_key_manager()
        key_manager.clear_stored_key()
        
        console.print("✅ [green]Cached master key cleared successfully[/green]")
        console.print("🔐 Next operation will prompt for master password")
        console.print("💡 [dim]Remember: Same password regenerates same key - no data lost[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Failed to clear cached key: {e}[/red]")
        raise typer.Exit(1)


@app.command(
    help="""Test security operations and benchmark key derivation performance.

Runs comprehensive security diagnostics including key derivation benchmarks,
encryption/decryption tests, and keyring connectivity checks.

Examples:
  aico security test
"""
)
def test():
    """🧪 Test security operations and benchmark key derivation performance."""
    
    key_manager = _get_key_manager()
    
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
        master_key = key_manager.authenticate(interactive=False)
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
    
    test_db_path = "test_security_benchmark.db"
    test_salt_path = f"{test_db_path}.salt"
    
    try:
        db_times = []
        for i in range(3):
            start_time = time.time()
            db_key = key_manager.derive_database_key(master_key, "libsql", test_db_path)
            db_time = (time.time() - start_time) * 1000
            db_times.append(db_time)
            
            if i == 0:
                console.print(f"  First derivation: {db_time:.1f}ms")
            else:
                console.print(f"  Subsequent call {i}: {db_time:.1f}ms")
        
        avg_db_time = sum(db_times) / len(db_times)
        console.print(f"✅ [green]Database key average: {avg_db_time:.1f}ms[/green]")
        
        # Clean up test salt file
        import os
        if os.path.exists(test_salt_path):
            os.remove(test_salt_path)
            console.print(f"🧹 [dim]Cleaned up test salt file[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Database key test failed: {e}[/red]")
        # Clean up on error too
        import os
        if os.path.exists(test_salt_path):
            try:
                os.remove(test_salt_path)
            except:
                pass
    
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
    user_type: str = typer.Option("person", "--type", "-t", help="User type (person)"),
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
        console.print('  aico security user-create "Jane Smith" --nickname "Janie" --type person')
        console.print('  aico security user-create "Bob Wilson" --pin 1234 --type person')
        console.print('  aico security user-create "Alice Cooper" --nickname "Al" --type admin --pin 5678')
        console.print("\n[bold yellow]Options:[/bold yellow]")
        console.print("  --nickname, -n    Optional nickname for the user")
        console.print("  --type, -t        User type: person (default: person)")
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
        key_manager = _get_key_manager()
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


# Role Management Commands

@app.command("role-assign")
def role_assign(
    user_uuid: str = typer.Argument(..., help="User UUID to assign role to"),
    role: str = typer.Argument(..., help="Role name (admin, user, service, cli)"),
    granted_by: str = typer.Option("cli", "--granted-by", "-g", help="Who granted the role")
):
    """Assign role to user"""
    
    try:
        # Initialize database connection
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security.key_manager import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.core.authorization import AuthorizationService
        
        config_manager = ConfigurationManager()
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        authz_service = AuthorizationService(db_conn)
        
        # Validate role exists
        available_roles = authz_service.list_all_roles()
        if role not in available_roles:
            console.print(f"❌ [red]Unknown role: {role}[/red]")
            console.print(f"Available roles: {', '.join(available_roles.keys())}")
            raise typer.Exit(1)
        
        # Assign role
        success = authz_service.assign_role(user_uuid, role, granted_by)
        
        if success:
            console.print(f"✅ [green]Successfully assigned role '{role}' to user {user_uuid}[/green]")
            
            # Show updated roles
            user_roles = authz_service.get_user_roles(user_uuid)
            console.print(f"User roles: {', '.join(user_roles)}")
        else:
            console.print(f"❌ [red]Failed to assign role '{role}' to user {user_uuid}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ [red]Role assignment failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("role-revoke")
def role_revoke(
    user_uuid: str = typer.Argument(..., help="User UUID to revoke role from"),
    role: str = typer.Argument(..., help="Role name to revoke")
):
    """Revoke role from user"""
    
    try:
        # Initialize database connection
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security.key_manager import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.core.authorization import AuthorizationService
        
        config_manager = ConfigurationManager()
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        authz_service = AuthorizationService(db_conn)
        
        # Revoke role
        success = authz_service.revoke_role(user_uuid, role)
        
        if success:
            console.print(f"✅ [green]Successfully revoked role '{role}' from user {user_uuid}[/green]")
            
            # Show updated roles
            user_roles = authz_service.get_user_roles(user_uuid)
            console.print(f"Remaining roles: {', '.join(user_roles)}")
        else:
            console.print(f"❌ [red]Failed to revoke role '{role}' from user {user_uuid}[/red]")
            console.print("Role may not be assigned to this user")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ [red]Role revocation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("role-list")
def role_list(
    user_uuid: str = typer.Argument(None, help="User UUID to show roles for (optional)"),
    show_permissions: bool = typer.Option(False, "--show-permissions", "-p", help="Show detailed permissions")
):
    """List user roles and permissions"""
    
    try:
        # Initialize database connection
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security.key_manager import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.core.authorization import AuthorizationService
        
        config_manager = ConfigurationManager()
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        authz_service = AuthorizationService(db_conn)
        
        if user_uuid:
            # Show specific user's roles
            console.print(f"\n✨ [bold cyan]Roles for User {user_uuid}[/bold cyan]\n")
            
            user_roles = authz_service.get_user_roles(user_uuid)
            
            if not user_roles:
                console.print("❌ [red]No roles assigned to this user[/red]")
                return
            
            # Create roles table
            roles_table = Table(
                title="User Roles",
                title_justify="left",
                show_header=True,
                header_style="bold yellow",
                border_style="bright_blue",
                box=box.SIMPLE_HEAD
            )
            roles_table.add_column("Role", style="bold white", justify="left")
            if show_permissions:
                roles_table.add_column("Permissions", style="cyan", justify="left")
            
            all_roles_config = authz_service.list_all_roles()
            for role in user_roles:
                if show_permissions:
                    permissions = all_roles_config.get(role, [])
                    perms_display = ", ".join(permissions[:3])
                    if len(permissions) > 3:
                        perms_display += f" (+{len(permissions)-3} more)"
                    roles_table.add_row(role, perms_display)
                else:
                    roles_table.add_row(role)
            
            console.print(roles_table)
            
            if show_permissions:
                # Show all permissions summary
                user_permissions = authz_service.get_user_permissions(user_uuid)
                console.print(f"\n📋 [cyan]Total permissions: {len(user_permissions)}[/cyan]")
        else:
            # Show all available roles
            console.print("\n✨ [bold cyan]Available Roles[/bold cyan]\n")
            
            all_roles = authz_service.list_all_roles()
            
            roles_table = Table(
                title="Role Definitions",
                title_justify="left",
                show_header=True,
                header_style="bold yellow",
                border_style="bright_blue",
                box=box.SIMPLE_HEAD
            )
            roles_table.add_column("Role", style="bold white", justify="left")
            roles_table.add_column("Permissions", style="cyan", justify="left")
            
            for role, permissions in all_roles.items():
                perms_display = ", ".join(permissions[:3])
                if len(permissions) > 3:
                    perms_display += f" (+{len(permissions)-3} more)"
                roles_table.add_row(role, perms_display)
            
            console.print(roles_table)
            console.print("\n[dim]Use 'aico security role-list <user-uuid>' to see user-specific roles[/dim]")
            
    except Exception as e:
        console.print(f"❌ [red]Failed to list roles: {e}[/red]")
        raise typer.Exit(1)


@app.command("role-show")
def role_show(
    role_name: str = typer.Argument(None, help="Specific role to show details for")
):
    """Show available roles and their permissions"""
    
    try:
        # Initialize database connection
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security.key_manager import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.core.authorization import AuthorizationService
        from aico.core.topics import AICOTopics
        
        config_manager = ConfigurationManager()
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        authz_service = AuthorizationService(db_conn)
        
        all_roles = authz_service.list_all_roles()
        
        if role_name:
            # Show specific role details
            if role_name not in all_roles:
                console.print(f"❌ [red]Unknown role: {role_name}[/red]")
                console.print(f"Available roles: {', '.join(all_roles.keys())}")
                raise typer.Exit(1)
            
            console.print(f"\n✨ [bold cyan]Role: {role_name}[/bold cyan]\n")
            
            permissions = all_roles[role_name]
            
            # Create permissions table
            perms_table = Table(
                title=f"Permissions for '{role_name}' Role",
                title_justify="left",
                show_header=True,
                header_style="bold yellow",
                border_style="bright_blue",
                box=box.SIMPLE_HEAD
            )
            perms_table.add_column("Permission", style="bold white", justify="left")
            perms_table.add_column("Description", style="cyan", justify="left")
            
            # Add permission descriptions
            perm_descriptions = {
                "admin/*": "Full administrative access",
                AICOTopics.ALL_SYSTEM: "System management operations",
                AICOTopics.ALL_LOGS: "Log management and access",
                "config/*": "Configuration management",
                "users/*": "User management operations",
                "audit/*": "Audit log access",
                AICOTopics.ALL_CONVERSATION: "Conversation access",
                "memory/read": "Read memory data",
                "personality/read": "Read personality data",
                "profile/*": "Profile management",
                AICOTopics.SYSTEM_HEALTH_CHECK: "Health check access",
                "logs/write": "Write log entries",
                "events/*": "Event handling",
                "debug/*": "Debug operations"
            }
            
            for perm in permissions:
                desc = perm_descriptions.get(perm, "Custom permission")
                perms_table.add_row(perm, desc)
            
            console.print(perms_table)
        else:
            # Show all roles summary
            console.print("\n✨ [bold cyan]All Available Roles[/bold cyan]\n")
            
            for role, permissions in all_roles.items():
                console.print(f"🔐 [bold white]{role}[/bold white]")
                console.print(f"   Permissions: {len(permissions)}")
                console.print(f"   Examples: {', '.join(permissions[:3])}")
                if len(permissions) > 3:
                    console.print(f"   (+{len(permissions)-3} more)")
                console.print()
            
            console.print("[dim]Use 'aico security role-show <role-name>' for detailed permissions[/dim]")
            
    except Exception as e:
        console.print(f"❌ [red]Failed to show roles: {e}[/red]")
        raise typer.Exit(1)


@app.command("role-check")
def role_check(
    user_uuid: str = typer.Argument(..., help="User UUID to check"),
    permission: str = typer.Argument(..., help="Permission to check (e.g., 'admin.logs', 'config.read')")
):
    """Check if user has specific permission"""
    
    try:
        # Initialize database connection
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security.key_manager import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.core.authorization import AuthorizationService
        
        config_manager = ConfigurationManager()
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        authz_service = AuthorizationService(db_conn)
        
        # Check permission
        has_permission = authz_service.has_permission(user_uuid, permission)
        
        console.print(f"\n🔍 [bold cyan]Permission Check[/bold cyan]\n")
        console.print(f"User: {user_uuid}")
        console.print(f"Permission: {permission}")
        
        if has_permission:
            console.print(f"Result: ✅ [green]GRANTED[/green]")
            
            # Show which roles grant this permission
            user_roles = authz_service.get_user_roles(user_uuid)
            all_roles = authz_service.list_all_roles()
            
            granting_roles = []
            for role in user_roles:
                role_permissions = all_roles.get(role, [])
                for perm in role_permissions:
                    if perm == "*" or permission == perm:
                        granting_roles.append(role)
                        break
                    elif perm.endswith("*") and permission.startswith(perm[:-1]):
                        granting_roles.append(role)
                        break
            
            if granting_roles:
                console.print(f"Granted by roles: {', '.join(granting_roles)}")
        else:
            console.print(f"Result: ❌ [red]DENIED[/red]")
            
            # Show user's current roles
            user_roles = authz_service.get_user_roles(user_uuid)
            console.print(f"User roles: {', '.join(user_roles)}")
            
    except Exception as e:
        console.print(f"❌ [red]Permission check failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("role-bootstrap")
def role_bootstrap(
    user_uuid: str = typer.Argument(..., help="User UUID to bootstrap as admin")
):
    """Bootstrap admin role for initial setup"""
    
    try:
        # Initialize database connection
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security.key_manager import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.core.authorization import AuthorizationService
        
        config_manager = ConfigurationManager()
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        authz_service = AuthorizationService(db_conn)
        
        # Bootstrap admin role
        success = authz_service.bootstrap_admin_user(user_uuid)
        
        if success:
            console.print(f"✅ [green]Successfully bootstrapped admin role for user {user_uuid}[/green]")
            console.print("🔐 User now has full administrative access")
            
            # Show user's roles
            user_roles = authz_service.get_user_roles(user_uuid)
            user_permissions = authz_service.get_user_permissions(user_uuid)
            
            console.print(f"Roles: {', '.join(user_roles)}")
            console.print(f"Permissions: {len(user_permissions)} total")
            
            console.print("\n💡 [dim]User can now access admin endpoints and manage the system[/dim]")
        else:
            console.print(f"❌ [red]Failed to bootstrap admin role for user {user_uuid}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ [red]Admin bootstrap failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-list")
def user_list(
    user_uuid: str = typer.Argument(None, help="Specific user UUID to show (only with --detailed)"),
    user_type: str = typer.Option(None, "--type", "-t", help="Filter by user type"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of users to show"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed information from all user-related tables")
):
    """List all users (or show detailed view of specific user)"""
    import asyncio
    from pathlib import Path
    from rich.table import Table
    from aico.core.config import ConfigurationManager
    from aico.core.paths import AICOPaths
    from aico.security.key_manager import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    from aico.data.user import UserService
    
    console = Console()
    
    # Validate arguments
    if user_uuid and not detailed:
        console.print("\n❌ [red]User UUID can only be specified with --detailed flag[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-list [OPTIONS]                    # List all users")
        console.print("  aico security user-list --detailed                   # Detailed view of all users")
        console.print("  aico security user-list <USER_UUID> --detailed       # Detailed view of specific user")
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
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        if detailed:
            # Detailed view
            if user_uuid:
                # Show detailed info for specific user
                async def get_detailed_user():
                    users = await user_service.list_users(limit=1000)
                    user = next((u for u in users if u.uuid == user_uuid), None)
                    if not user:
                        return None, None, None, None
                    
                    # Get additional data
                    auth_data = await user_service.get_user_authentication(user_uuid)
                    relationships = await user_service.get_user_relationships(user_uuid)
                    # Note: user_sessions would need to be implemented in UserService if available
                    
                    return user, auth_data, relationships, None
                
                user, auth_data, relationships, sessions = asyncio.run(get_detailed_user())
                
                if not user:
                    console.print(f"❌ [red]User not found: {user_uuid}[/red]")
                    raise typer.Exit(1)
                
                # Create detailed table for single user
                table = Table(
                    title=f"✨ [bold cyan]User Details: {user.full_name}[/bold cyan]",
                    title_style="bold cyan",
                    title_justify="left",
                    border_style="bright_blue",
                    header_style="bold yellow",
                    show_lines=False,
                    box=box.SIMPLE_HEAD,
                    padding=(0, 1)
                )
                table.add_column("Field", style="bold white", justify="left")
                table.add_column("Value", style="green", justify="left")
                
                # Basic user info
                table.add_row("UUID", user.uuid)
                table.add_row("Full Name", user.full_name)
                table.add_row("Nickname", user.nickname or "-")
                table.add_row("User Type", user.user_type)
                table.add_row("Active", "[green]Yes[/green]" if user.is_active else "[red]No[/red]")
                table.add_row("Created", str(user.created_at)[:19] if user.created_at else "-")
                table.add_row("Updated", str(user.updated_at)[:19] if user.updated_at else "-")
                
                # Authentication info
                if auth_data:
                    table.add_row("Has PIN", "[green]Yes[/green]" if auth_data.get('has_pin') else "[red]No[/red]")
                    table.add_row("Account Locked", "[red]Yes[/red]" if auth_data.get('is_locked') else "[green]No[/green]")
                    if auth_data.get('failed_attempts'):
                        table.add_row("Failed Attempts", str(auth_data.get('failed_attempts', 0)))
                    if auth_data.get('last_login'):
                        table.add_row("Last Login", str(auth_data.get('last_login'))[:19])
                else:
                    table.add_row("Has PIN", "[red]No[/red]")
                    table.add_row("Account Locked", "[green]No[/green]")
                
                # Relationships
                if relationships:
                    table.add_row("Relationships", f"{len(relationships)} active")
                    for rel in relationships[:3]:  # Show first 3
                        table.add_row(f"  └─ {rel.get('relationship_type', 'unknown')}", rel.get('related_user_name', 'Unknown'))
                    if len(relationships) > 3:
                        table.add_row("  └─ ...", f"+{len(relationships) - 3} more")
                else:
                    table.add_row("Relationships", "None")
                
                console.print()
                console.print(table)
                console.print()
                
            else:
                # Show detailed info for all users
                async def get_all_detailed():
                    users = await user_service.list_users(user_type=user_type, limit=limit)
                    detailed_users = []
                    
                    for user in users:
                        auth_data = await user_service.get_user_authentication(user.uuid)
                        relationships = await user_service.get_user_relationships(user.uuid)
                        detailed_users.append({
                            'user': user,
                            'auth': auth_data,
                            'relationships': relationships
                        })
                    
                    return detailed_users
                
                detailed_users = asyncio.run(get_all_detailed())
                
                if not detailed_users:
                    console.print("No users found.")
                    return
                
                # Create detailed table for all users
                table = Table(
                    title="✨ [bold cyan]AICO Users (Detailed)[/bold cyan]",
                    title_style="bold cyan",
                    title_justify="left",
                    border_style="bright_blue",
                    header_style="bold yellow",
                    show_lines=False,
                    box=box.SIMPLE_HEAD,
                    padding=(0, 1)
                )
                table.add_column("UUID", style="bold white", justify="left", no_wrap=True, min_width=36)
                table.add_column("Name", style="bold white", justify="left")
                table.add_column("Type", style="green", justify="left")
                table.add_column("Active", style="bold white", justify="left")
                table.add_column("PIN", style="bold white", justify="left")
                table.add_column("Locked", style="bold white", justify="left")
                table.add_column("Relationships", style="dim", justify="left")
                table.add_column("Created", style="dim", justify="left")
                
                for item in detailed_users:
                    user = item['user']
                    auth = item['auth'] or {}
                    relationships = item['relationships'] or []
                    
                    # Format status indicators
                    active_status = "[green]Yes[/green]" if user.is_active else "[red]No[/red]"
                    pin_status = "[green]Yes[/green]" if auth.get('has_pin') else "[red]No[/red]"
                    locked_status = "[red]Yes[/red]" if auth.get('is_locked') else "[green]No[/green]"
                    rel_count = f"{len(relationships)}" if relationships else "0"
                    
                    table.add_row(
                        user.uuid,
                        user.full_name,
                        user.user_type,
                        active_status,
                        pin_status,
                        locked_status,
                        rel_count,
                        str(user.created_at)[:19] if user.created_at else "-"
                    )
                
                console.print()
                console.print(table)
                console.print()
        else:
            # Standard list view
            async def list_users():
                users = await user_service.list_users(user_type=user_type, limit=limit)
                return users
            
            users = asyncio.run(list_users())
            
            if not users:
                console.print("No users found.")
                return
            
            # Create table following CLI style guide
            table = Table(
                title="✨ [bold cyan]AICO Users[/bold cyan]",
                title_style="bold cyan",
                title_justify="left",
                border_style="bright_blue",
                header_style="bold yellow",
                show_lines=False,
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            table.add_column("UUID", style="bold white", justify="left", no_wrap=True, min_width=36)
            table.add_column("Name", style="bold white", justify="left")
            table.add_column("Nickname", style="bold white", justify="left")
            table.add_column("Type", style="green", justify="left")
            table.add_column("Active", style="bold white", justify="left")
            table.add_column("Created", style="dim", justify="left")
            
            for user in users:
                # Format active status with color coding
                active_status = "[green]Yes[/green]" if user.is_active else "[red]No[/red]"
                
                table.add_row(
                    user.uuid,  # Full UUID - no truncation
                    user.full_name,
                    user.nickname or "-",
                    user.user_type,
                    active_status,
                    str(user.created_at)[:19] if user.created_at else "-"
                )
            
            console.print()
            console.print(table)
            console.print()
        
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
        key_manager = _get_key_manager()
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
    user_type: str = typer.Option(None, "--type", "-t", help="Update user type)"),
):
    """Update user profile information"""
    
    if user_uuid is None:
        console.print("\n❌ [red]Missing required argument: USER_UUID[/red]\n")
    # ... (rest of the code remains the same)
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
        key_manager = _get_key_manager()
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
    hard: bool = typer.Option(False, "--hard", help="Permanently delete user and all related data (IRREVERSIBLE)"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Delete user (soft delete by default, --hard for permanent deletion)"""
    
    if user_uuid is None:
        console.print("\n❌ [red]Missing required argument: USER_UUID[/red]\n")
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  aico security user-delete [OPTIONS] USER_UUID\n")
        console.print("[bold yellow]Examples:[/bold yellow]")
        console.print('  aico security user-delete abc123def --confirm  # Soft delete')
        console.print('  aico security user-delete abc123def --hard     # Permanent delete')
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
        
        # Use configuration-based path resolution
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Get user first to confirm deletion
        async def get_user():
            users = await user_service.list_users(limit=1000)  # Get all users
            return next((u for u in users if u.uuid == user_uuid), None)
        
        user = asyncio.run(get_user())
        
        if not user:
            console.print(f"❌ [red]User not found: {user_uuid}[/red]")
            raise typer.Exit(1)
        
        if hard:
            # Hard delete - permanent deletion
            console.print(f"\n[bold red]⚠️  PERMANENT DELETION WARNING[/bold red]")
            console.print(f"[bold white]User to be permanently deleted:[/bold white]")
            console.print(f"UUID: {user.uuid}")
            console.print(f"Name: {user.full_name}")
            if user.nickname:
                console.print(f"Nickname: {user.nickname}")
            console.print(f"Type: {user.user_type}")
            console.print(f"Status: {'Active' if user.is_active else 'Inactive'}")
            
            console.print(f"\n[bold red]This will permanently delete:[/bold red]")
            console.print("• User profile and account data")
            console.print("• Authentication data (PIN/passwords)")
            console.print("• User relationships and connections")
            console.print("• Access policies and permissions")
            console.print("• ALL related data in the database")
            
            console.print(f"\n[bold red]This action CANNOT be undone![/bold red]")
            
            if not confirm:
                # Require typing YES to confirm
                confirmation = typer.prompt(f"\nType 'YES' (in capitals) to permanently delete user '{user.full_name}'", show_default=False)
                if confirmation != "YES":
                    console.print("❌ [yellow]Confirmation failed. Operation cancelled.[/yellow]")
                    raise typer.Exit(0)
            
            # Perform hard delete
            async def hard_delete():
                result = await user_service.hard_delete_user(user_uuid)
                return result
            
            result = asyncio.run(hard_delete())
            
            if result:
                console.print(f"\n✅ [green]User permanently deleted[/green]")
                console.print(f"UUID: {user_uuid}")
                console.print(f"Name: {user.full_name}")
                console.print(f"\n[bold yellow]All related data has been permanently removed from the database.[/bold yellow]")
            else:
                console.print(f"❌ [red]Failed to delete user (may have already been deleted)[/red]")
                raise typer.Exit(1)
        else:
            # Soft delete - default behavior
            if not confirm:
                console.print(f"\n[bold yellow]Soft delete user:[/bold yellow]")
                console.print(f"UUID: {user.uuid}")
                console.print(f"Name: {user.full_name}")
                if user.nickname:
                    console.print(f"Nickname: {user.nickname}")
                console.print(f"Type: {user.user_type}")
                console.print(f"\n[dim]This will mark the user as inactive but keep all data.[/dim]")
                
                response = typer.confirm(f"\nAre you sure you want to soft delete user '{user.full_name}'?")
                if not response:
                    console.print("Operation cancelled.")
                    raise typer.Exit(0)
            
            # Perform soft delete
            async def soft_delete():
                result = await user_service.delete_user(user_uuid)
                return result
            
            result = asyncio.run(soft_delete())
            
            if result:
                console.print(f"\n✅ [green]User soft deleted (marked as inactive)[/green]")
                console.print(f"UUID: {user_uuid}")
                console.print(f"Name: {user.full_name}")
                console.print(f"\n[dim]User data is preserved and can be reactivated if needed.[/dim]")
            else:
                console.print(f"❌ [red]Failed to delete user (may have already been deleted)[/red]")
                raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"❌ [red]Failed to delete user: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-cleanup")
@destructive("permanently removes all soft-deleted users from database")
def user_cleanup():
    """Remove all soft-deleted users from database (IRREVERSIBLE)"""
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
        
        # Use configuration-based path resolution
        db_config = config_manager.get("database.libsql", {})
        filename = db_config.get("filename", "aico.db")
        directory_mode = db_config.get("directory_mode", "auto")
        
        db_path = AICOPaths.resolve_database_path(filename, directory_mode)
        
        # Initialize key manager and get database key
        key_manager = _get_key_manager()
        master_key = key_manager.authenticate()
        db_key = key_manager.derive_database_key(master_key, "libsql", db_path)
        
        # Connect to database
        db_conn = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
        user_service = UserService(db_conn)
        
        # Get all soft-deleted users (is_active = FALSE)
        async def get_soft_deleted_users():
            users = await user_service.list_users(limit=10000)
            return [u for u in users if not u.is_active]
        
        soft_deleted_users = asyncio.run(get_soft_deleted_users())
        
        if not soft_deleted_users:
            console.print("\n✅ [green]No soft-deleted users found[/green]")
            console.print("[dim]All users in the database are currently active[/dim]")
            return
        
        # Display users to be permanently deleted
        console.print(f"\n[bold red]⚠️  PERMANENT DELETION WARNING[/bold red]")
        console.print(f"[bold white]Found {len(soft_deleted_users)} soft-deleted user(s) to be permanently removed:[/bold white]\n")
        
        # Create table showing users to be deleted
        table = Table(
            border_style="red",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        table.add_column("UUID", style="dim", justify="left", no_wrap=True)
        table.add_column("Name", style="white", justify="left")
        table.add_column("Nickname", style="cyan", justify="left")
        table.add_column("Type", style="dim", justify="left")
        table.add_column("Deleted", style="dim", justify="left")
        
        for user in soft_deleted_users:
            table.add_row(
                user.uuid[:8] + "...",
                user.full_name,
                user.nickname or "-",
                user.user_type,
                str(user.updated_at)[:19] if user.updated_at else "-"
            )
        
        console.print(table)
        
        console.print(f"\n[bold red]This will permanently delete:[/bold red]")
        console.print("• User profiles and account data")
        console.print("• Authentication data (PINs/passwords)")
        console.print("• User relationships and connections")
        console.print("• Access policies and permissions")
        console.print("• ALL related data for these users")
        console.print(f"\n[bold red]This action CANNOT be undone![/bold red]")
        
        # Require typing the number of users to confirm
        console.print()
        confirmation = typer.prompt(
            f"Type the number '{len(soft_deleted_users)}' to confirm permanent deletion of {len(soft_deleted_users)} user(s)",
            show_default=False
        )
        
        if confirmation != str(len(soft_deleted_users)):
            console.print("❌ [yellow]Confirmation failed. Operation cancelled.[/yellow]")
            raise typer.Exit(0)
        
        # Permanently delete all soft-deleted users
        console.print(f"\n🗑️  [yellow]Permanently deleting {len(soft_deleted_users)} user(s)...[/yellow]")
        
        deleted_count = 0
        failed_count = 0
        
        async def cleanup_users():
            nonlocal deleted_count, failed_count
            for user in soft_deleted_users:
                try:
                    result = await user_service.hard_delete_user(user.uuid)
                    if result:
                        deleted_count += 1
                        console.print(f"  ✓ Deleted: {user.full_name} ({user.uuid[:8]}...)")
                    else:
                        failed_count += 1
                        console.print(f"  ✗ Failed: {user.full_name} ({user.uuid[:8]}...)")
                except Exception as e:
                    failed_count += 1
                    console.print(f"  ✗ Error deleting {user.full_name}: {e}")
        
        asyncio.run(cleanup_users())
        
        # Summary
        console.print(f"\n[bold green]Cleanup Complete[/bold green]")
        console.print(f"✅ Successfully deleted: {deleted_count} user(s)")
        if failed_count > 0:
            console.print(f"❌ Failed to delete: {failed_count} user(s)")
        console.print(f"\n[bold yellow]All soft-deleted users have been permanently removed from the database.[/bold yellow]")
        
    except Exception as e:
        console.print(f"❌ [red]Cleanup failed: {e}[/red]")
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
        key_manager = _get_key_manager()
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
        key_manager = _get_key_manager()
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
        
        # Create main statistics table
        table = Table(
            title="✨ [bold cyan]User Statistics[/bold cyan]",
            title_style="bold cyan",
            title_justify="left",
            border_style="bright_blue",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold yellow",
            padding=(0, 1)
        )
        
        table.add_column("Metric", style="white", justify="left")
        table.add_column("Count", style="bold green", justify="right")
        
        # Add total users
        table.add_row("Total Users", str(stats.get('total_users', 0)))
        
        # Add users by type
        users_by_type = stats.get('users_by_type', {})
        if users_by_type:
            for user_type, count in users_by_type.items():
                table.add_row(f"  └─ {user_type.title()}", str(count))
        
        # Add authentication stats
        auth_stats = stats.get('authentication', {})
        if auth_stats:
            table.add_row("Users with PIN", str(auth_stats.get('total_with_auth', 0)))
            table.add_row("Locked Accounts", str(auth_stats.get('locked_accounts', 0)))
        
        console.print()
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ [red]Failed to get user stats: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
