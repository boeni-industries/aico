"""
AICO CLI Modelservice Commands

Provides model service management and control.
"""

import asyncio
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
from rich.text import Text

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
from cli.utils.formatting import get_status_chars
from cli.utils.zmq_client import get_modelservice_health

console = Console()

# Get platform-appropriate characters
chars = get_status_chars()


def _is_modelservice_running() -> bool:
    """Check if Modelservice is currently running"""
    try:
        # Primary check: ZMQ health endpoint
        health_response = get_modelservice_health()
        if health_response.get("success"):
            return True
        
        # Fallback: Check for running processes (optimized scan)
        try:
            import psutil
            # Only scan python processes to reduce overhead
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip non-Python processes early
                    name = proc.info.get('name', '').lower()
                    if not any(py in name for py in ['python']):
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


async def _enhance_health_data(health_data: dict):
    """Enhance health data with actual service checks."""
    import httpx
    import time
    
    if "checks" not in health_data:
        health_data["checks"] = {}
    
    # Run both health checks concurrently with reduced timeout
    async def check_api_gateway():
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get("http://127.0.0.1:8771/api/v1/health")
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "reachable": True,
                        "response_time_ms": round(response_time)
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "reachable": True,
                        "error": f"HTTP {response.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "reachable": False,
                "error": "connection_refused"
            }
        except Exception as e:
            return {
                "status": "unknown",
                "reachable": False,
                "error": str(e)
            }
    
    async def check_ollama():
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get("http://127.0.0.1:11434/api/tags")
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "reachable": True,
                        "status": "running",
                        "response_time_ms": round(response_time)
                    }
                else:
                    return {
                        "healthy": False,
                        "reachable": True,
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    }
        except httpx.ConnectError:
            return {
                "healthy": False,
                "reachable": False,
                "status": "offline",
                "error": "connection_refused"
            }
        except Exception as e:
            return {
                "healthy": False,
                "reachable": False,
                "status": "unknown",
                "error": str(e)
            }
    
    # Run both checks concurrently
    gateway_result, ollama_result = await asyncio.gather(
        check_api_gateway(),
        check_ollama(),
        return_exceptions=True
    )
    
    # Handle results
    if isinstance(gateway_result, Exception):
        health_data["checks"]["api_gateway"] = {
            "status": "unknown",
            "reachable": False,
            "error": str(gateway_result)
        }
    else:
        health_data["checks"]["api_gateway"] = gateway_result
    
    if isinstance(ollama_result, Exception):
        health_data["checks"]["ollama"] = {
            "healthy": False,
            "reachable": False,
            "status": "unknown",
            "error": str(ollama_result)
        }
    else:
        health_data["checks"]["ollama"] = ollama_result


async def _show_service_details(health_data: dict):
    """Show additional service details for healthy services."""
    try:
        # Get Ollama models if available
        if health_data.get("checks", {}).get("ollama", {}).get("healthy", False):
            try:
                from cli.utils.zmq_client import get_ollama_models
                models_response = get_ollama_models()
                if models_response.get("success") and models_response.get("data", {}).get("models"):
                    models = models_response["data"]["models"]
                    
                    console.print()
                    table = Table(title="Available Models", show_header=True, header_style="bold blue")
                    table.add_column("Model", style="cyan", no_wrap=True)
                    table.add_column("Size", justify="right", style="dim")
                    table.add_column("Modified", style="dim")
                    
                    for model in models[:5]:  # Show top 5 models
                        name = model.get("name", "unknown")
                        size = _format_size(model.get("size", 0))
                        modified = model.get("modified_at", "unknown")
                        if modified != "unknown" and len(modified) > 10:
                            modified = modified[:10]  # Show just date part
                        table.add_row(name, size, modified)
                    
                    if len(models) > 5:
                        table.add_row("...", f"+{len(models) - 5} more", "")
                    
                    console.print(table)
            except Exception:
                pass  # Silently skip if models can't be retrieved
        
        # Show configuration summary
        config = _get_modelservice_config()
        if config:
            console.print()
            table = Table(title="Service Configuration", show_header=True, header_style="bold blue")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="dim")
            
            # Show key configuration values
            rest_config = config.get("rest", {})
            ollama_config = config.get("ollama", {})
            
            table.add_row("REST API", f"{rest_config.get('host', '127.0.0.1')}:{rest_config.get('port', 8773)}")
            table.add_row("Ollama URL", f"{ollama_config.get('host', '127.0.0.1')}:{ollama_config.get('port', 11434)}")
            table.add_row("Auto Start", "✓" if ollama_config.get("auto_start", True) else "✗")
            table.add_row("Auto Install", "✓" if ollama_config.get("auto_install", True) else "✗")
            
            console.print(table)
            
    except Exception:
        pass  # Silently skip if details can't be shown


def _format_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


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
        # Check if running
        is_running = _is_modelservice_running()
        health_data = {}
        
        # Get health data if running via ZMQ
        if is_running:
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    # Step 1: Get basic health via ZMQ
                    task = progress.add_task("Checking modelservice health...", total=None)
                    health_response = get_modelservice_health()
                    
                    if health_response.get("success"):
                        health_data = health_response.get("data", {})
                        
                        # Step 2: Enhanced health checks
                        progress.update(task, description="Checking API Gateway and Ollama...")
                        asyncio.run(_enhance_health_data(health_data))
                        
                        progress.update(task, description="Health checks complete!")
                        progress.stop()
                    else:
                        # Service is running but health endpoint failed - still show basic info
                        health_data = {
                            "status": "connection_failed", 
                            "version": "0.0.2", 
                            "checks": {
                                "api_gateway": {"status": "unknown", "reachable": False, "error": "connection_failed"},
                                "ollama": {"healthy": False, "reachable": False, "error": "unknown"}
                            }, 
                            "issues": ["Health endpoint unreachable via ZMQ"]
                        }
            except Exception as e:
                # Fallback health data for display
                health_data = {
                    "status": "connection_failed", 
                    "version": "0.0.2", 
                    "checks": {
                        "api_gateway": {"status": "unknown", "reachable": False, "error": "zmq_connection_failed"},
                        "ollama": {"healthy": False, "reachable": False, "error": "unknown"}
                    }, 
                    "issues": [f"ZMQ health check failed: {str(e)}"]
                }
        
        # Primary status header (matching gateway format)
        if is_running:
            health_status = health_data.get("status", "unknown")
            if health_status == "healthy":
                console.print(f"{chars['globe']} [bold green]Modelservice Status: HEALTHY[/bold green]")
            else:
                console.print(f"{chars['globe']} [bold yellow]Modelservice Status: RUNNING (Unhealthy)[/bold yellow]")
            
            version = health_data.get("version", "Unknown")
            console.print(f"   [dim]Version {version} • ZMQ Message Bus[/dim]")
        else:
            console.print(f"{chars['globe']} [bold red]Modelservice Status: OFFLINE[/bold red]")
            console.print(f"   [dim]Not responding via ZMQ[/dim]")
        
        console.print()
        
        # Health details if running (show for both healthy and unhealthy)
        if is_running and health_data:
            checks = health_data.get("checks", {})
            errors = health_data.get("issues", [])
            
            if checks:
                table = Table(title="Health Checks", show_header=True, header_style="bold blue")
                table.add_column("Component", style="cyan", no_wrap=True)
                table.add_column("Status", justify="left")
                table.add_column("Details", style="dim")
                
                for component, check_data in checks.items():
                    if isinstance(check_data, dict):
                        # Handle different status field names for backward compatibility
                        status = check_data.get("status", "unknown")
                        is_healthy = (status == "healthy" or 
                                    check_data.get("healthy", False) or
                                    check_data.get("reachable", False))
                        
                        if status == "healthy" or (check_data.get("healthy", False) and check_data.get("reachable", False)):
                            status_display = f"[green]{chars['check']} Healthy[/green]"
                            response_time = check_data.get('response_time_ms')
                            if response_time:
                                details = f"{response_time}ms"
                            else:
                                details = "Running"
                        elif status == "running" or check_data.get("status") == "running":
                            status_display = f"[green]{chars['check']} Running[/green]"
                            response_time = check_data.get('response_time_ms')
                            if response_time:
                                details = f"{response_time}ms"
                            else:
                                details = "Service active"
                        elif status == "offline" or check_data.get("error") == "connection_refused":
                            status_display = f"[red]{chars['cross']} Offline[/red]"
                            details = "Service not running"
                        elif status == "timeout" or check_data.get("error") == "timeout":
                            status_display = f"[yellow]{chars['warning']} Timeout[/yellow]"
                            details = "Connection timeout"
                        else:
                            status_display = f"[red]{chars['cross']} Unhealthy[/red]"
                            error = check_data.get("error", "Unknown error")
                            # Clean up common error messages
                            if error == "connection_refused":
                                details = "Service not running"
                            elif error == "connection_failed":
                                details = "Connection failed"
                            elif len(error) > 60:
                                # Wrap long error messages
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
        
        # Additional service information if healthy
        if is_running and health_data.get("status") == "healthy":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Loading service details...", total=None)
                asyncio.run(_show_service_details(health_data))
                progress.stop()
        
        # ZMQ Topics table
        if is_running:
            table = Table(title="Available ZMQ Topics", show_header=True, header_style="bold blue")
            table.add_column("Topic", style="cyan", no_wrap=True)
            table.add_column("Purpose", style="dim")
            
            topics = [
                ("modelservice/health/request", "Service health and status"),
                ("modelservice/completions/request", "Text generation"),
                ("modelservice/models/request", "List available models"),
                ("modelservice/status/request", "Service status information"),
                ("ollama/status/request", "Ollama service status"),
                ("ollama/models/request", "Ollama model management")
            ]
            
            for topic, purpose in topics:
                table.add_row(topic, purpose)
            
            console.print(table)
        
    except Exception as e:
        console.print(f"{chars['cross']} [red]Error checking Modelservice status: {e}[/red]")
        raise typer.Exit(1)
