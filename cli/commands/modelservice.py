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
            response = requests.get(f"http://{host}:{port}/api/v1/health", timeout=1)
            # Accept any response (200, 503, etc.) as "running"
            return True
        except requests.exceptions.RequestException:
            pass  # Continue to process check
        
        # Fallback: Check for running processes (optimized scan)
        try:
            import psutil
            # Only scan python processes to reduce overhead
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip non-Python processes early
                    name = proc.info.get('name', '').lower()
                    if not any(py in name for py in ['python', 'uvicorn']):
                        continue
                        
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        if any(pattern in cmdline_str for pattern in [
                            'modelservice.main',
                            'modelservice/main.py',
                            'AICO_SERVICE_MODE=modelservice'
                        ]):
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            pass
        
        # Final fallback: PID file check (for detached processes only)
        try:
            process_manager = ProcessManager("modelservice")
            status = process_manager.get_service_status()
            return status["running"]
        except Exception:
            pass
        
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
        
        # Direct process termination approach
        try:
            import psutil
            import signal
            
            stopped_any = False
            modelservice_pids = []
            
            console.print(f"[dim]Searching for modelservice processes...[/dim]")
            
            # Find all modelservice processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        
                        # Look for modelservice processes
                        if 'modelservice.main' in cmdline_str:
                            modelservice_pids.append(proc.info['pid'])
                            console.print(f"[dim]Found modelservice process (PID: {proc.info['pid']})[/dim]")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Terminate all modelservice processes
            for pid in modelservice_pids:
                try:
                    process = psutil.Process(pid)
                    console.print(f"[cyan]Terminating modelservice process (PID: {pid})[/cyan]")
                    
                    # Cross-platform graceful shutdown
                    process.terminate()  # Works on all platforms via psutil
                    
                    # Wait for process to exit gracefully
                    try:
                        process.wait(timeout=5)
                        stopped_any = True
                        console.print(f"[green]{chars['check']} Process {pid} stopped gracefully[/green]")
                    except psutil.TimeoutExpired:
                        # Force kill if graceful shutdown failed
                        process.kill()
                        stopped_any = True
                        console.print(f"[yellow]{chars['warning']} Process {pid} force-stopped[/yellow]")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    console.print(f"[dim]Process {pid} already terminated or access denied[/dim]")
                    continue
            
            if stopped_any:
                console.print(f"[green]{chars['check']} All modelservice processes terminated[/green]")
            else:
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
        health_data = {}
        
        # Get health data if running
        if is_running:
            try:
                response = requests.get(f"http://{host}:{port}/api/v1/health", timeout=3)
                health_data = response.json()
            except requests.exceptions.RequestException as e:
                # Service is running but health endpoint failed - still show basic info
                health_data = {
                    "status": "connection_failed", 
                    "version": "0.0.2", 
                    "checks": {
                        "api_gateway": {"status": "unknown", "reachable": False, "error": "connection_failed"},
                        "ollama": {"healthy": False, "reachable": False, "error": "unknown"}
                    }, 
                    "errors": ["Health endpoint unreachable"]
                }
        
        # Primary status header (matching gateway format)
        if is_running:
            health_status = health_data.get("status", "unknown")
            if health_status == "healthy":
                console.print(f"{chars['globe']} [bold green]Modelservice Status: HEALTHY[/bold green]")
            else:
                console.print(f"{chars['globe']} [bold yellow]Modelservice Status: RUNNING (Unhealthy)[/bold yellow]")
            
            version = health_data.get("version", "Unknown")
            console.print(f"   [dim]Version {version} • {host}:{port}[/dim]")
        else:
            console.print(f"{chars['globe']} [bold red]Modelservice Status: OFFLINE[/bold red]")
            console.print(f"   [dim]Not responding • {host}:{port}[/dim]")
        
        console.print()
        
        # Health details if running (show for both healthy and unhealthy)
        if is_running and health_data:
            checks = health_data.get("checks", {})
            errors = health_data.get("errors", [])
            
            if checks:
                table = Table(title="Health Checks", show_header=True, header_style="bold blue")
                table.add_column("Component", style="cyan", no_wrap=True)
                table.add_column("Status", justify="left")
                table.add_column("Details", style="dim")
                
                for component, check_data in checks.items():
                    if isinstance(check_data, dict):
                        status = check_data.get("status", "unknown")
                        if status == "healthy" or check_data.get("healthy", False):
                            status_display = f"[green]{chars['check']} Healthy[/green]"
                            details = f"Response: {check_data.get('response_time_ms', 'N/A')}ms"
                        else:
                            status_display = f"[red]{chars['cross']} Unhealthy[/red]"
                            error = check_data.get("error", "Unknown error")
                            # Wrap long error messages instead of truncating
                            if len(error) > 60:
                                # Split long error into multiple lines
                                import textwrap
                                wrapped_lines = textwrap.wrap(error, width=60)
                                details = "\n".join(wrapped_lines)
                            else:
                                details = error
                    else:
                        status_display = f"[yellow]{chars['warning']} Unknown[/yellow]"
                        details = str(check_data)
                    
                    table.add_row(component.replace("_", " ").title(), status_display, details)
                
                console.print(table)
                console.print()
            
            if errors:
                console.print(f"[red]{chars['cross']} Issues Found:[/red]")
                for error in errors:
                    console.print(f"  • {error}")
                console.print()
        
        # Endpoints table
        if is_running:
            table = Table(title="Available Endpoints", show_header=True, header_style="bold blue")
            table.add_column("Endpoint", style="cyan", no_wrap=True)
            table.add_column("Purpose", style="dim")
            
            endpoints = [
                ("/api/v1/health", "Service health and status"),
                ("/api/v1/handshake", "Encrypted communication setup"),
                ("/api/v1/completions", "Text generation"),
                ("/api/v1/models", "List available models")
            ]
            
            for endpoint, purpose in endpoints:
                table.add_row(f"http://{host}:{port}{endpoint}", purpose)
            
            console.print(table)
        
    except Exception as e:
        console.print(f"{chars['cross']} [red]Error checking Modelservice status: {e}[/red]")
        raise typer.Exit(1)
