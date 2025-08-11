"""
AICO CLI Security Commands

Provides master password setup, management, and security operations.
"""

import typer
from rich.console import Console
from rich.table import Table
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
            ("test", "Performance diagnostics and key derivation benchmarking")
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
    if key_manager.has_stored_key():
        if not jwt_only:
            console.print("⚠️ [yellow]Master password already set up.[/yellow]")
            console.print("Use 'aico security passwd' to update it, or --jwt-only to initialize JWT secrets.")
            raise typer.Exit(1)
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
        try:
            jwt_secret = key_manager.get_jwt_secret("api_gateway")
            console.print("🔒 [green]JWT secret initialized for API Gateway[/green]")
        except Exception as e:
            console.print(f"⚠️ [yellow]JWT secret initialization failed: {e}[/yellow]")
            console.print("   Run 'aico security setup --jwt-only' to retry JWT initialization")
        
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
def status():
    """Check security health and key management status."""
    
    key_manager = AICOKeyManager()
    health_info = key_manager.get_security_health_info()
    
    # Create status table with actionable security information
    table = Table(
        title="✨ [bold cyan]AICO Security Health[/bold cyan]",
        title_style="bold cyan",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        show_lines=False,
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Property", style="bold white", justify="left")
    table.add_column("Value", style="green", justify="left")
    
    # Security health assessment (NO EMOJIS IN TABLE DATA per style guide)
    security_level = health_info["security_level"]
    if security_level == "Strong":
        level_display = "Strong"
    elif security_level == "Good":
        level_display = "Good"
    elif security_level == "Needs Rotation":
        level_display = "Needs Rotation"
    else:
        level_display = "Not Set Up"
    
    table.add_row("Security Health", level_display)
    
    if health_info["has_master_key"]:
        # Key lifecycle information
        if health_info["key_created"]:
            table.add_row("Key Created", health_info["key_created"])
        if health_info["key_age_days"] is not None:
            age_display = f"{health_info['key_age_days']} days"
            if health_info["key_age_days"] > 365:
                age_display += " (Old)"
            elif health_info["key_age_days"] > 180:
                age_display += " (Consider rotation)"
            table.add_row("Key Age", age_display)
        
        # Algorithm strength
        table.add_row("Algorithm", health_info["algorithm"])
        table.add_row("Key Size", f"{health_info['key_size'] * 8}-bit")
        
        # Argon2id parameters
        if health_info["memory_cost_mb"]:
            table.add_row("Memory Cost", f"{health_info['memory_cost_mb']} MB")
        if health_info["iterations"]:
            table.add_row("Iterations", str(health_info["iterations"]))
        if health_info["parallelism"]:
            table.add_row("Parallelism", f"{health_info['parallelism']} threads")
        
        table.add_row("Backup Available", "Yes (regenerable from password)")
    
    console.print(table)
    
    # Show recommendations
    if not health_info["has_master_key"]:
        console.print("\n⚠️ [yellow]Master password not set up[/yellow]")
        console.print("Run 'aico security setup' to get started")
    elif health_info["rotation_recommended"]:
        console.print("\n🔄 [yellow]Key rotation recommended[/yellow]")
        console.print("Run 'aico security passwd' to update your master password")
    else:
        console.print("\n✅ [green]Security configuration is healthy[/green]")
        console.print("🔐 All systems ready for encrypted operations")


@app.command()
def session():
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
        
        from datetime import datetime
        created_at = datetime.fromisoformat(session_info["created_at"])
        last_accessed = datetime.fromisoformat(session_info["last_accessed"])
        expires_at = datetime.fromisoformat(session_info["expires_at"])
        
        session_table.add_row("Created", created_at.strftime("%Y-%m-%d %H:%M:%S"))
        session_table.add_row("Last Accessed", last_accessed.strftime("%Y-%m-%d %H:%M:%S"))
        session_table.add_row("Expires", expires_at.strftime("%Y-%m-%d %H:%M:%S"))
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
    """Performance diagnostics and key derivation benchmarking."""
    
    key_manager = AICOKeyManager()
    
    if not key_manager.has_stored_key():
        console.print("❌ [red]No master password set up.[/red]")
        console.print("Use 'aico security setup' first.")
        raise typer.Exit(1)
    
    try:
        console.print("\n✨ [bold cyan]AICO Security Diagnostics[/bold cyan]\n")
        
        # Authentication test
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            auth_task = progress.add_task("Testing master password authentication...", total=None)
            master_key = key_manager.authenticate(interactive=True)
            progress.update(auth_task, completed=True)
        
        console.print("✅ [green]Master password authentication successful[/green]\n")
        
        # Performance benchmarks with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=False
        ) as progress:
            bench_task = progress.add_task("Running key derivation benchmarks...", total=None)
            benchmark_results = key_manager.benchmark_key_derivation()
            progress.update(bench_task, completed=True)
        
        console.print()
        
        # Create performance table
        perf_table = Table(
            title="✨ [bold cyan]Key Derivation Performance[/bold cyan]",
            title_style="bold cyan",
            title_justify="left",
            border_style="bright_blue",
            header_style="bold yellow",
            show_lines=False,
            box=box.SIMPLE_HEAD,
            padding=(0, 1)
        )
        perf_table.add_column("Operation", style="bold white", justify="left")
        perf_table.add_column("Algorithm", style="magenta", justify="left")
        perf_table.add_column("Iterations", style="blue", justify="left")
        perf_table.add_column("Memory", style="blue", justify="left")
        perf_table.add_column("Time", style="green", justify="left")
        perf_table.add_column("Status", style="green", justify="left")
        
        # Master key derivation (NO EMOJIS IN TABLE DATA per style guide)
        master_time = benchmark_results["master_key_derivation_ms"]
        if isinstance(master_time, int):
            perf_table.add_row("Master Key", "Argon2id", "3", "1024 MB", f"{master_time}ms", "Success")
        else:
            perf_table.add_row("Master Key", "Argon2id", "3", "1024 MB", "N/A", str(master_time))
        
        # Database key derivations
        for db_type, result in benchmark_results["database_key_derivations"].items():
            time_display = f"{result['time_ms']}ms" if result['time_ms'] else "N/A"
            
            # Algorithm-specific parameters
            if db_type == "libsql":
                algorithm = "PBKDF2"
                iterations = "10000"
                memory = "N/A"
            else:  # duckdb, chroma use Argon2id
                algorithm = "Argon2id"
                iterations = "2"
                memory = "256 MB"
            
            perf_table.add_row(f"{db_type.title()} DB", algorithm, iterations, memory, time_display, result['status'])
        
        console.print(perf_table)
        
        # Performance assessment
        assessment = benchmark_results["performance_assessment"]
        if assessment == "Optimal":
            console.print(f"\n✅ [green]Performance: {assessment}[/green]")
        elif assessment in ["Fast", "Slow"]:
            console.print(f"\n🟡 [yellow]Performance: {assessment}[/yellow]")
        else:
            console.print(f"\n⚠️ [red]Performance: {assessment}[/red]")
        
        # Show recommendations
        if benchmark_results["recommendations"]:
            console.print("\n💡 [cyan]Recommendations:[/cyan]")
            for rec in benchmark_results["recommendations"]:
                console.print(f"  • {rec}")
        
    except Exception as e:
        console.print(f"❌ [red]Diagnostic test failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
