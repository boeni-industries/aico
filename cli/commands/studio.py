"""
AICO CLI Studio Commands

Provides commands to start and stop the React-based Studio admin UI.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Add shared module to path for CLI usage FIRST
if getattr(sys, "frozen", False):
    # Running in PyInstaller bundle
    shared_path = Path(sys._MEIPASS) / "shared"
else:
    # Running in development
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.process import ProcessManager
from cli.utils.platform import get_platform_chars

console = Console()
chars = get_platform_chars()


def studio_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help

        subcommands = [
            ("start", "Start the Studio admin UI"),
            ("stop", "Stop the Studio admin UI"),
        ]

        examples = [
            "aico studio start",
            "aico studio start --dev",
            "aico studio stop",
        ]

        format_subcommand_help(
            console=console,
            command_name="studio",
            description="Studio admin UI (React-based dashboard)",
            subcommands=subcommands,
            examples=examples,
        )
        raise typer.Exit()


app = typer.Typer(
    help="Studio admin UI (React-based dashboard)",
    callback=studio_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []},
)


def _get_studio_dir() -> Path:
    """Return the absolute path to the Studio project directory."""
    return Path(__file__).parent.parent.parent / "studio"


def _is_studio_running() -> bool:
    """Check if Studio is currently running using ProcessManager."""
    try:
        process_manager = ProcessManager("studio")
        status = process_manager.get_service_status()
        return bool(status.get("running"))
    except Exception:
        return False


def _open_browser(url: str) -> None:
    """Open the given URL in the default system browser."""
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        console.print(f"[yellow]{chars['warning']} Failed to open browser automatically. Open: {url}[/yellow]")


@app.command("start")
def start(
    dev: bool = typer.Option(True, "--dev/--no-dev", help="Start in development mode using npm/yarn (default: dev)"),
    detach: bool = typer.Option(True, "--detach/--no-detach", help="Run as background service (default: True)"),
    open: bool = typer.Option(True, "--open/--no-open", help="Open Studio UI in browser after start (default: True)"),
):
    """Start the Studio admin UI and optionally open it in the browser."""
    try:
        studio_dir = _get_studio_dir()
        package_json = studio_dir / "package.json"

        if not package_json.exists():
            console.print(f"[red]{chars['cross']} Studio project not found at: {studio_dir}[/red]")
            raise typer.Exit(1)

        console.print("[yellow]⏳ Starting Studio admin UI...[/yellow]")

        if _is_studio_running():
            console.print(f"[yellow]{chars['warning']} Studio is already running[/yellow]")
            console.print("[dim]Use 'aico studio stop' to stop it first if needed[/dim]")
            return

        # Determine package manager and command
        npm_lock = studio_dir / "package-lock.json"
        yarn_lock = studio_dir / "yarn.lock"
        pnpm_lock = studio_dir / "pnpm-lock.yaml"

        if yarn_lock.exists():
            pkg_cmd = ["yarn", "start"] if dev else ["yarn", "build"]
        elif pnpm_lock.exists():
            pkg_cmd = ["pnpm", "start"] if dev else ["pnpm", "build"]
        else:
            # Default to npm
            pkg_cmd = ["npm", "run", "start"] if dev else ["npm", "run", "build"]

        env = dict(os.environ)
        env.setdefault("BROWSER", "none")  # prevent CRA from auto-opening another tab
        env["AICO_SERVICE_MODE"] = "studio"
        env["AICO_DETACH_MODE"] = "true" if detach else "false"

        process_kwargs = {
            "cwd": str(studio_dir),
            "env": env,
        }

        if detach:
            # Run Studio in background using ProcessManager semantics
            # For now, we use a detached subprocess; ProcessManager will track by service name "studio".
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                process_kwargs.update(
                    {
                        "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                        "startupinfo": startupinfo,
                        "stdout": subprocess.DEVNULL,
                        "stderr": subprocess.DEVNULL,
                        "stdin": subprocess.DEVNULL,
                    }
                )
            else:
                process_kwargs.update(
                    {
                        "stdout": subprocess.DEVNULL,
                        "stderr": subprocess.DEVNULL,
                        "stdin": subprocess.DEVNULL,
                        "start_new_session": True,
                    }
                )

            # Start Studio dev server and track PID via ProcessManager
            proc = subprocess.Popen(pkg_cmd, **process_kwargs)

            try:
                pm = ProcessManager("studio")
                pm.write_pid(proc.pid)
            except Exception:
                # PID tracking is best-effort; do not fail startup if this breaks
                console.print(
                    f"[yellow]{chars['warning']} Failed to write Studio PID file; 'aico studio stop' may not work reliably[/yellow]"
                )

            # Give it a moment to start
            import time

            time.sleep(3)

            if _is_studio_running():
                console.print(f"[green]{chars['check']} Studio started as background service[/green]")
            else:
                console.print(f"[yellow]{chars['warning']} Studio process started but status could not be confirmed[/yellow]")
        else:
            # Foreground mode for debugging
            console.print(f"[yellow]{chars['warning']} Running Studio in foreground mode (blocking)[/yellow]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            console.print()

            try:
                console.print(f"[dim]Executing: {' '.join(pkg_cmd)}[/dim]")
                console.print(f"[dim]Working directory: {studio_dir}[/dim]")
                console.print()

                result = subprocess.run(pkg_cmd, cwd=str(studio_dir), env=env)
                # Treat normal exit, SIGTERM (15) and -15 (Unix signal) as graceful.
                if result.returncode in (0, 15, -15):
                    console.print(f"[green]{chars['check']} Studio stopped gracefully[/green]")
                else:
                    console.print(f"[yellow]Studio process exited with code {result.returncode}[/yellow]")
                    console.print(f"[red]{chars['cross']} Studio exited with code {result.returncode}[/red]")
                    raise typer.Exit(result.returncode)
            except KeyboardInterrupt:
                console.print("\n[yellow]Studio process interrupted[/yellow]")
                console.print(f"[green]{chars['check']} Studio stopped gracefully[/green]")
                return

        # Open browser if requested (assume default dev server URL)
        if open:
            url = os.environ.get("AICO_STUDIO_URL", "http://localhost:3000")
            _open_browser(url)

    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to start Studio: {e}[/red]")
        raise typer.Exit(1)


@app.command("stop")
def stop():
    """Stop the Studio admin UI."""
    try:
        console.print(f"[yellow]{chars['hourglass']} Stopping Studio...[/yellow]")
        process_manager = ProcessManager("studio")

        # First try to stop using the tracked PID, if any
        status = process_manager.get_service_status()
        pid = status.get("pid")
        graceful_stopped = False
        if pid:
            graceful_stopped = process_manager.stop_service(timeout=15)

        # Regardless of PID file state, scan for matching Studio processes and
        # terminate them as well. This covers foreground/legacy runs where the
        # PID file was never written.
        try:
            stale_stopped = process_manager.cleanup_stale_processes()
        except Exception:
            stale_stopped = 0

        if graceful_stopped or stale_stopped > 0:
            msg_extra = f" (including {stale_stopped} stale process(es))" if stale_stopped else ""
            console.print(f"[green]{chars['check']} Studio stopped{msg_extra}[/green]")
        else:
            console.print(f"[yellow]{chars['warning']} No running Studio processes found to stop[/yellow]")
            console.print("[dim]If a dev server is running in the foreground of this terminal, press Ctrl+C there.[/dim]")
    except Exception as e:
        console.print(f"[red]{chars['cross']} Failed to stop Studio: {e}[/red]")
        raise typer.Exit(1)
