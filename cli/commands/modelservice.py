"""
AICO CLI Modelservice Commands

Provides model service management and control.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add shared module to path for CLI usage FIRST
if getattr(sys, 'frozen', False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.process import ProcessManager
from cli.decorators.sensitive import destructive
from cli.utils.help_formatter import format_subcommand_help
from cli.utils.platform import get_platform_chars

console = Console()

# Get platform-appropriate characters
chars = get_platform_chars()


def _is_modelservice_running() -> bool:
    """Check if Modelservice is currently running"""
    try:
        # Primary check: HTTP health endpoint (works for both detached and foreground)
        config = _get_modelservice_config()
        host = config.get('host', '127.0.0.1')
        port = config.get('rest', {}).get('port', 8773)
        
        try:
            response = requests.get(f"http://{host}:{port}/api/v1/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            # If HTTP check fails, fall back to PID check (for detached processes)
            try:
                process_manager = ProcessManager("modelservice")
                status = process_manager.get_service_status()
                return status["running"]
            except Exception:
                return False
        
    except Exception:
        return False


def _get_modelservice_config() -> dict:
    """Get Modelservice configuration from core config"""
    try:
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        return config_manager.get("modelservice", {})
    except Exception:
        return {}


def modelservice_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("start", "Start the Modelservice"),
            ("stop", "Stop the Modelservice"),
            ("restart", "Restart the Modelservice"),
            ("status", "Show Modelservice status and health")
        ]
        
        examples = [
            "aico modelservice start",
            "aico modelservice status",
            "aico modelservice restart"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="modelservice",
            description="Model service management and control",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()


app = typer.Typer(
    help="Model service management and control.",
    callback=modelservice_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


@app.command("start")
def start(
    detach: bool = typer.Option(True, "--detach/--no-detach", help="Run as background service (default: True)")
):
    """Start the Modelservice"""
    try:
        console.print("[yellow]⏳ Starting Modelservice...[/yellow]")
        
        # Check if already running
        if _is_modelservice_running():
            console.print(f"[yellow]{chars['warning']} Modelservice is already running[/yellow]")
            console.print("[dim]Use 'aico modelservice status' to check or 'aico modelservice restart' to restart[/dim]")
            return
        
        import subprocess
        
        # Path to modelservice directory
        project_root = Path(__file__).parent.parent.parent
        modelservice_main = project_root / "modelservice" / "main.py"
        
        if not modelservice_main.exists():
            console.print(f"[red]{chars['cross']} Modelservice not found at: {modelservice_main}[/red]")
            raise typer.Exit(1)
        
        # Get cross-platform Python executable for headless execution
        def get_headless_python(force_visible=False):
            """Get appropriate Python executable for headless execution per platform"""
            if force_visible or not detach:
                # Foreground mode: Always use regular python to show output
                return sys.executable
            elif sys.platform == "win32":
                # Windows background mode: Use pythonw.exe to avoid console window
                python_dir = Path(sys.executable).parent
                pythonw_exe = python_dir / "pythonw.exe"
                return str(pythonw_exe) if pythonw_exe.exists() else sys.executable
            else:
                # macOS/Linux: Use regular python (process will be detached)
                return sys.executable
        
        # Build command
        cmd = [get_headless_python(), "-m", "modelservice.main"]
        
        # Configure process options
        env = dict(os.environ, 
                  AICO_SERVICE_MODE="modelservice",
                  AICO_DETACH_MODE="true" if detach else "false")
        
        process_kwargs = {
            "cwd": str(project_root),
            "env": env
        }
        
        if detach:
            # Background service mode (non-blocking)
            if sys.platform == "win32":
                # Windows: Use STARTUPINFO with STARTF_USESHOWWINDOW to hide console
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                process_kwargs.update({
                    "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    "startupinfo": startupinfo,
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                    "stdin": subprocess.DEVNULL
                })
            else:
                # Unix-like: Standard background process
                process_kwargs.update({
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                    "stdin": subprocess.DEVNULL,
                    "start_new_session": True
                })
            
            process = subprocess.Popen(cmd, **process_kwargs)
            
            # Write PID for process management
            process_manager = ProcessManager("modelservice")
            process_manager.write_pid(process.pid)
            
            # Give it a moment to start
            time.sleep(3)
            
            # Verify it started successfully
            if _is_modelservice_running():
                config = _get_modelservice_config()
                port = config.get('rest', {}).get('port', 8773)
                host = config.get('host', '127.0.0.1')
                
                console.print(f"[green]{chars['check']} Modelservice started as background service[/green]")
                console.print()
                console.print(f"[bold blue]{chars['globe']} Available Endpoints:[/bold blue]")
                console.print(f"  • REST API: [cyan]http://{host}:{port}/api/v1[/cyan]")
                console.print(f"  • Health Check: [cyan]http://{host}:{port}/api/v1/health[/cyan]")
                console.print()
                console.print(f"[dim]{chars['lightbulb']} Test connection: 'aico modelservice status'[/dim]")
            else:
                console.print(f"[red]{chars['cross']} Failed to start Modelservice[/red]")
                console.print("[dim]Check logs for details[/dim]")
                raise typer.Exit(1)
        else:
            # Foreground mode (blocking) - for debugging
            console.print(f"[yellow]{chars['warning']} Running in foreground mode (blocking)[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            console.print()
            
            # Show the exact command being run
            console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]")
            console.print(f"[dim]Working directory: {project_root}[/dim]")
            console.print()
            
            # Run in foreground (this should block and show output)
            try:
                console.print("[dim]Starting modelservice process...[/dim]")
                
                # Use subprocess.run without capture_output to show live output
                result = subprocess.run(
                    cmd, 
                    cwd=str(project_root),
                    env=env,
                    # Don't capture output - let it stream to console
                    stdout=None,
                    stderr=None
                )
                
                console.print(f"[yellow]Modelservice process exited with code {result.returncode}[/yellow]")
                
                if result.returncode != 0 and result.returncode != 15:
                    console.print(f"[red]{chars['cross']} Modelservice exited with code {result.returncode}[/red]")
                    raise typer.Exit(result.returncode)
                else:
                    console.print(f"[green]{chars['check']} Modelservice stopped gracefully[/green]")
                    
            except FileNotFoundError as e:
                console.print(f"[red]{chars['cross']} Command not found: {e}[/red]")
                raise typer.Exit(1)
            except KeyboardInterrupt:
                console.print(f"\n[yellow]Modelservice process exited with code 0[/yellow]")
                console.print(f"[green]{chars['check']} Modelservice stopped gracefully[/green]")
                return  # Exit cleanly without raising exception
            
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{chars['warning']} Modelservice startup interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to start modelservice: {e}[/red]")
        raise typer.Exit(1)


@app.command("stop")
def stop():
    """Stop the Modelservice"""
    try:
        console.print(f"[yellow]{chars['hourglass']} Stopping Modelservice...[/yellow]")
        
        # Check if running first
        if not _is_modelservice_running():
            console.print(f"[yellow]{chars['warning']} Modelservice is not running[/yellow]")
            return
        
        # Try ProcessManager first (works for detached processes with PID files)
        process_manager = ProcessManager("modelservice")
        status = process_manager.get_service_status()
        
        if status["running"] and status.get("pid"):
            # Detached process with PID file - use ProcessManager
            success = process_manager.stop_service(timeout=30)
            if success:
                console.print(f"[green]{chars['check']} Modelservice stopped gracefully[/green]")
                return
        
        # No PID file found - likely foreground process, use psutil to find and stop
        try:
            import psutil
            import signal
            
            stopped_any = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if (cmdline and 
                        any('python' in arg.lower() for arg in cmdline) and
                        any('modelservice.main' in arg for arg in cmdline)):
                        
                        console.print(f"[dim]Found modelservice process (PID: {proc.info['pid']})[/dim]")
                        
                        # Send SIGTERM for graceful shutdown
                        if sys.platform == "win32":
                            proc.terminate()
                        else:
                            proc.send_signal(signal.SIGTERM)
                        
                        # Wait for process to exit gracefully
                        try:
                            proc.wait(timeout=10)
                            stopped_any = True
                            console.print(f"[green]{chars['check']} Modelservice stopped gracefully[/green]")
                        except psutil.TimeoutExpired:
                            # Force kill if graceful shutdown failed
                            proc.kill()
                            stopped_any = True
                            console.print(f"[yellow]{chars['warning']} Modelservice force-stopped[/yellow]")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not stopped_any:
                console.print(f"[yellow]{chars['warning']} No running Modelservice processes found[/yellow]")
                
        except ImportError:
            console.print(f"[red]{chars['cross']} psutil not available. Cannot stop processes automatically.[/red]")
            console.print("[yellow]Please stop the modelservice process manually (Ctrl+C if running in foreground)[/yellow]")
            
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to stop modelservice: {e}[/red]")
        raise typer.Exit(1)


@app.command("restart")
def restart():
    """Restart the Modelservice"""
    console.print(f"[yellow]{chars['restart']} Restarting Modelservice...[/yellow]")
    
    # Stop first
    try:
        stop()
    except typer.Exit:
        pass  # Continue with start even if stop failed
    
    # Wait a moment
    time.sleep(1)
    
    start()


@app.command(help="Show Modelservice status and health")
def status():
    """Show Modelservice status and health."""
    try:
        config = _get_modelservice_config()
        host = config.get('host', '127.0.0.1')
        port = config.get('rest', {}).get('port', 8773)
        
        # Check if running
        is_running = _is_modelservice_running()
        
        # Create status table
        table = Table(title=f"{chars['sparkle']} Modelservice Status", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        
        # Basic status
        status_color = "green" if is_running else "red"
        status_text = "Running" if is_running else "Stopped"
        table.add_row("Status", f"[{status_color}]{status_text}[/{status_color}]")
        table.add_row("Host", host)
        table.add_row("Port", str(port))
        
        if is_running:
            try:
                # Get health info
                response = requests.get(f"http://{host}:{port}/api/v1/health", timeout=2)
                if response.status_code == 200:
                    health_data = response.json()
                    table.add_row("Health", "[green]Healthy[/green]")
                    table.add_row("Version", health_data.get("version", "Unknown"))
                    table.add_row("Service", health_data.get("service", "Unknown"))
                else:
                    table.add_row("Health", f"[red]Unhealthy (HTTP {response.status_code})[/red]")
            except requests.exceptions.RequestException:
                table.add_row("Health", "[red]Unreachable[/red]")
        
        console.print(table)
        
        if is_running:
            console.print(f"\n{chars['bullet']} [cyan]Modelservice endpoint:[/cyan] http://{host}:{port}/api/v1/health")
        
    except Exception as e:
        console.print(f"{chars['cross']} [red]Error checking Modelservice status: {e}[/red]")
        raise typer.Exit(1)
