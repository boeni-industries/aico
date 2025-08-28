"""
AICO CLI Scheduler Commands

Provides scheduled task management and scheduler status monitoring.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from cron_descriptor import CasingTypeEnum, ExpressionDescriptor

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import sensitive

# Import utils
utils_path = Path(__file__).parent.parent / "utils"
sys.path.insert(0, str(utils_path))
from cli.utils.timezone import format_timestamp_local

# Add shared path for imports
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security.key_manager import AICOKeyManager

console = Console()

def scheduler_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("ls", "List scheduled tasks"),
            ("show", "Show detailed task information"),
            ("create", "Create a new scheduled task"),
            ("update", "Update task configuration"),
            ("enable", "Enable a task"),
            ("disable", "Disable a task"),
            ("delete", "Delete a task"),
            ("trigger", "Manually trigger task execution"),
            ("history", "Show task execution history"),
            ("status", "Show scheduler status")
        ]
        
        examples = [
            "aico scheduler ls",
            "aico scheduler status",
            "aico scheduler show maintenance.log_cleanup",
            "aico scheduler create my_task MyTaskClass '0 2 * * *'"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="scheduler",
            description="Scheduled task management and scheduler status monitoring",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Scheduled task management and scheduler status monitoring.",
    callback=scheduler_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


@app.command("ls")
@sensitive
def list_tasks(
    enabled_only: bool = typer.Option(False, "--enabled", "-e", help="Show only enabled tasks"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table, json")
):
    """List scheduled tasks"""
    try:
        with _get_database_connection() as db:
            # Query tasks from database
            query = "SELECT task_id, task_class, schedule, enabled, created_at, updated_at FROM scheduled_tasks"
            params = ()
            
            if enabled_only:
                query += " WHERE enabled = TRUE"
            
            query += " ORDER BY task_id"
            
            cursor = db.execute(query, params)
            tasks = cursor.fetchall()
            
            if not tasks:
                console.print("[yellow]No scheduled tasks found[/yellow]")
                return
            
            if format_output == "json":
                task_list = []
                for task in tasks:
                    task_list.append({
                        "task_id": task[0],
                        "task_class": task[1],
                        "schedule": task[2],
                        "enabled": bool(task[3]),
                        "created_at": task[4],
                        "updated_at": task[5]
                    })
                console.print(json.dumps(task_list, indent=2))
            else:
                # Table format
                table = Table(
                    title="✨ Scheduled Tasks",
                    box=box.SIMPLE_HEAD,
                    title_justify="left",
                    header_style="bold yellow"
                )
                table.add_column("Task ID", style="cyan", no_wrap=True)
                table.add_column("Class", style="green")
                table.add_column("Schedule", style="yellow")
                table.add_column("Description", style="bright_blue")
                table.add_column("Status", style="green")
                table.add_column("Created", style="dim")
                
                for task in tasks:
                    status = "Enabled" if task[3] else "[dim]Disabled[/dim]"
                    created_at = format_timestamp_local(task[4]) if task[4] else "Unknown"
                    
                    try:
                        descriptor = ExpressionDescriptor(task[2], casing_type=CasingTypeEnum.Sentence)
                        description = descriptor.get_description()
                    except:
                        description = "[dim]Invalid cron[/dim]"
                    
                    table.add_row(
                        task[0],  # task_id
                        task[1],  # task_class
                        task[2],  # schedule
                        description,
                        status,
                        created_at
                    )
                
                console.print()
                console.print(table)
                console.print()
    
    except Exception as e:
        console.print(f"[red]Error listing tasks: {e}[/red]")
        raise typer.Exit(1)


@app.command("show")
@sensitive
def show_task(
    task_id: str = typer.Argument(..., help="Task ID to show"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table, json")
):
    """Show detailed task information"""
    try:
        with _get_database_connection() as db:
            # Get task details
            cursor = db.execute(
                "SELECT task_id, task_class, schedule, config, enabled, created_at, updated_at "
                "FROM scheduled_tasks WHERE task_id = ?", (task_id,)
            )
            task = cursor.fetchone()
            
            if not task:
                console.print(f"[red]Task not found: {task_id}[/red]")
                raise typer.Exit(1)
            
            if format_output == "json":
                task_data = {
                    "task_id": task[0],
                    "task_class": task[1],
                    "schedule": task[2],
                    "config": json.loads(task[3]) if task[3] else {},
                    "enabled": bool(task[4]),
                    "created_at": task[5],
                    "updated_at": task[6]
                }
                console.print(json.dumps(task_data, indent=2))
            else:
                # Table format following AICO style
                table = Table(
                    title=f"✨ [bold cyan]Task Details: {task[0]}[/bold cyan]",
                    title_justify="left",
                    border_style="bright_blue",
                    header_style="bold yellow",
                    box=box.SIMPLE_HEAD,
                    padding=(0, 1)
                )
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                
                status = "Enabled" if task[4] else "Disabled"
                config = json.loads(task[3]) if task[3] else {}
                
                table.add_row("Task ID", task[0])
                table.add_row("Class", task[1])
                table.add_row("Schedule", task[2])
                table.add_row("Status", status)
                table.add_row("Created", format_timestamp_local(task[5]) if task[5] else "Unknown")
                table.add_row("Updated", format_timestamp_local(task[6]) if task[6] else "Unknown")
                
                console.print()
                console.print(table)
                
                if config:
                    console.print("\n[bold cyan]Configuration:[/bold cyan]")
                    console.print(json.dumps(config, indent=2))
                else:
                    console.print("\n[dim]No custom configuration[/dim]")
                console.print()
    
    except Exception as e:
        console.print(f"[red]Error showing task: {e}[/red]")
        raise typer.Exit(1)


@app.command("create")
@sensitive
def create_task(
    task_id: str = typer.Argument(..., help="Unique task identifier"),
    task_class: str = typer.Argument(..., help="Task class name"),
    schedule: str = typer.Argument(..., help="Cron expression"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="JSON config file path"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable task immediately")
):
    """Create a new scheduled task"""
    try:
        # Validate cron expression (basic check)
        cron_fields = schedule.strip().split()
        if len(cron_fields) != 5:
            console.print("[red]Invalid cron expression. Must have 5 fields (minute hour day month weekday)[/red]")
            raise typer.Exit(1)
        
        # Load configuration if provided
        config = {}
        if config_file:
            config_path = Path(config_file)
            if not config_path.exists():
                console.print(f"[red]Config file not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                console.print(f"[red]Invalid JSON in config file: {e}[/red]")
                raise typer.Exit(1)
        
        with _get_database_connection() as db:
            # Check if task already exists
            cursor = db.execute("SELECT task_id FROM scheduled_tasks WHERE task_id = ?", (task_id,))
            if cursor.fetchone():
                console.print(f"[red]Task already exists: {task_id}[/red]")
                raise typer.Exit(1)
            
            # Create task
            now = datetime.now().isoformat()
            config_json = json.dumps(config) if config else None
            
            db.execute("""
                INSERT INTO scheduled_tasks (task_id, task_class, schedule, config, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, task_class, schedule, config_json, enabled, now, now))
            
            db.commit()
            
            status = "enabled" if enabled else "disabled"
            console.print(f"[green]Created task '{task_id}' ({status})[/green]")
    
    except Exception as e:
        console.print(f"[red]Error creating task: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
@sensitive
def update_task(
    task_id: str = typer.Argument(..., help="Task ID to update"),
    schedule: Optional[str] = typer.Option(None, "--schedule", "-s", help="New cron expression"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="JSON config file path"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Enable/disable task")
):
    """Update task configuration"""
    try:
        if not any([schedule, config_file, enabled is not None]):
            console.print("[red]At least one update parameter must be provided[/red]")
            raise typer.Exit(1)
        
        with _get_database_connection() as db:
            # Check task exists
            cursor = db.execute("SELECT * FROM scheduled_tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if not task:
                console.print(f"[red]Task not found: {task_id}[/red]")
                raise typer.Exit(1)
            
            # Build update query
            updates = []
            params = []
            
            if schedule:
                # Validate cron expression
                cron_fields = schedule.strip().split()
                if len(cron_fields) != 5:
                    console.print("[red]Invalid cron expression. Must have 5 fields[/red]")
                    raise typer.Exit(1)
                updates.append("schedule = ?")
                params.append(schedule)
            
            if config_file:
                config_path = Path(config_file)
                if not config_path.exists():
                    console.print(f"[red]Config file not found: {config_file}[/red]")
                    raise typer.Exit(1)
                
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    updates.append("config = ?")
                    params.append(json.dumps(config))
                except json.JSONDecodeError as e:
                    console.print(f"[red]Invalid JSON in config file: {e}[/red]")
                    raise typer.Exit(1)
            
            if enabled is not None:
                updates.append("enabled = ?")
                params.append(enabled)
            
            # Add updated timestamp
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(task_id)
            
            # Execute update
            query = f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE task_id = ?"
            db.execute(query, params)
            db.commit()
            
            console.print(f"[green]Updated task '{task_id}'[/green]")
    
    except Exception as e:
        console.print(f"[red]Error updating task: {e}[/red]")
        raise typer.Exit(1)


@app.command("enable")
@sensitive
def enable_task(task_id: str = typer.Argument(..., help="Task ID to enable")):
    """Enable a scheduled task"""
    try:
        with _get_database_connection() as db:
            cursor = db.execute(
                "UPDATE scheduled_tasks SET enabled = TRUE, updated_at = ? WHERE task_id = ?",
                (datetime.now().isoformat(), task_id)
            )
            
            if cursor.rowcount == 0:
                console.print(f"[red]Task not found: {task_id}[/red]")
                raise typer.Exit(1)
            
            db.commit()
            console.print(f"[green]Enabled task '{task_id}'[/green]")
    
    except Exception as e:
        console.print(f"[red]Error enabling task: {e}[/red]")
        raise typer.Exit(1)


@app.command("disable")
@sensitive
def disable_task(task_id: str = typer.Argument(..., help="Task ID to disable")):
    """Disable a scheduled task"""
    try:
        with _get_database_connection() as db:
            cursor = db.execute(
                "UPDATE scheduled_tasks SET enabled = FALSE, updated_at = ? WHERE task_id = ?",
                (datetime.now().isoformat(), task_id)
            )
            
            if cursor.rowcount == 0:
                console.print(f"[red]Task not found: {task_id}[/red]")
                raise typer.Exit(1)
            
            db.commit()
            console.print(f"[green]Disabled task '{task_id}'[/green]")
    
    except Exception as e:
        console.print(f"[red]Error disabling task: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
@sensitive
def delete_task(
    task_id: str = typer.Argument(..., help="Task ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt")
):
    """Delete a scheduled task"""
    try:
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete task '{task_id}'?")
            if not confirm:
                console.print("[yellow]Operation cancelled[/yellow]")
                raise typer.Exit()
        
        with _get_database_connection() as db:
            cursor = db.execute("DELETE FROM scheduled_tasks WHERE task_id = ?", (task_id,))
            
            if cursor.rowcount == 0:
                console.print(f"[red]Task not found: {task_id}[/red]")
                raise typer.Exit(1)
            
            db.commit()
            console.print(f"[green]Deleted task '{task_id}'[/green]")
    
    except Exception as e:
        console.print(f"[red]Error deleting task: {e}[/red]")
        raise typer.Exit(1)


@app.command("history")
@sensitive
def task_history(
    task_id: str = typer.Argument(..., help="Task ID to show history for"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of executions to show"),
    format_output: str = typer.Option("table", "--format", "-f", help="Output format: table, json")
):
    """Show task execution history"""
    try:
        with _get_database_connection() as db:
            # Check task exists
            cursor = db.execute("SELECT task_id FROM scheduled_tasks WHERE task_id = ?", (task_id,))
            if not cursor.fetchone():
                console.print(f"[red]Task not found: {task_id}[/red]")
                raise typer.Exit(1)
            
            # Get execution history
            cursor = db.execute("""
                SELECT execution_id, status, started_at, completed_at, result, error_message, duration_seconds
                FROM task_executions 
                WHERE task_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (task_id, limit))
            
            executions = cursor.fetchall()
            
            if not executions:
                console.print(f"[yellow]No execution history found for task '{task_id}'[/yellow]")
                return
            
            if format_output == "json":
                exec_list = []
                for exec_data in executions:
                    exec_list.append({
                        "execution_id": exec_data[0],
                        "status": exec_data[1],
                        "started_at": exec_data[2],
                        "completed_at": exec_data[3],
                        "result": json.loads(exec_data[4]) if exec_data[4] else None,
                        "error_message": exec_data[5],
                        "duration_seconds": exec_data[6]
                    })
                console.print(json.dumps(exec_list, indent=2))
            else:
                # Table format
                table = Table(
                    title=f"✨ [bold cyan]Execution History: {task_id}[/bold cyan]",
                    title_justify="left",
                    border_style="bright_blue",
                    header_style="bold yellow",
                    box=box.SIMPLE_HEAD,
                    padding=(0, 1)
                )
                table.add_column("Execution ID", style="cyan", no_wrap=True)
                table.add_column("Status", justify="left")
                table.add_column("Started", style="dim")
                table.add_column("Duration", justify="right")
                table.add_column("Result", style="green")
                
                for exec_data in executions:
                    # Status without emojis (following AICO style guide)
                    status_map = {
                        "completed": "Completed",
                        "failed": "Failed", 
                        "running": "Running",
                        "cancelled": "Cancelled",
                        "skipped": "Skipped"
                    }
                    status = status_map.get(exec_data[1], exec_data[1])
                    
                    # Format duration
                    duration = ""
                    if exec_data[6]:
                        duration = f"{exec_data[6]:.1f}s"
                    
                    # Format result
                    result = ""
                    if exec_data[4]:
                        try:
                            result_data = json.loads(exec_data[4])
                            if result_data.get('success'):
                                result = result_data.get('message', 'Success') or ""
                            else:
                                result = result_data.get('error', 'Failed') or ""
                        except:
                            result = "Invalid result data"
                    elif exec_data[5]:
                        result = exec_data[5] or ""
                    
                    table.add_row(
                        exec_data[0][:8] + "...",  # Truncated execution ID
                        status,
                        format_timestamp_local(exec_data[2]) if exec_data[2] else "Unknown",
                        duration,
                        result[:50] + "..." if len(result) > 50 else result
                    )
                
                console.print()
                console.print(table)
                console.print()
    
    except Exception as e:
        console.print(f"[red]Error getting task history: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
@sensitive
def scheduler_status():
    """Show scheduler status and statistics"""
    try:
        with _get_database_connection() as db:
            # Get task counts
            cursor = db.execute("SELECT COUNT(*) FROM scheduled_tasks")
            total_tasks = cursor.fetchone()[0]
            
            cursor = db.execute("SELECT COUNT(*) FROM scheduled_tasks WHERE enabled = TRUE")
            enabled_tasks = cursor.fetchone()[0]
            
            # Get recent execution stats
            cursor = db.execute("""
                SELECT status, COUNT(*) 
                FROM task_executions 
                WHERE started_at > datetime('now', '-24 hours')
                GROUP BY status
            """)
            recent_executions = dict(cursor.fetchall())
            
            # Display status using table format
            table = Table(
                title="✨ [bold cyan]Scheduler Status[/bold cyan]",
                title_justify="left",
                border_style="bright_blue",
                header_style="bold yellow",
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Tasks", str(total_tasks))
            table.add_row("Enabled Tasks", str(enabled_tasks))
            table.add_row("Disabled Tasks", str(total_tasks - enabled_tasks))
            
            console.print()
            console.print(table)
            
            if recent_executions:
                console.print("\n[bold cyan]Recent Executions (24h):[/bold cyan]")
                for status, count in recent_executions.items():
                    console.print(f"  • {status.title()}: {count}")
            else:
                console.print("\n[dim]No recent executions in the last 24 hours[/dim]")
            console.print()
    
    except Exception as e:
        console.print(f"[red]Error getting scheduler status: {e}[/red]")
        raise typer.Exit(1)


def _get_database_connection():
    """Get database connection for scheduler operations"""
    try:
        from aico.core.paths import AICOPaths
        
        config_manager = ConfigurationManager()
        config_manager.initialize(lightweight=True)
        key_manager = AICOKeyManager(config_manager)
        
        # Get database path using AICO paths
        paths = AICOPaths()
        db_path = paths.resolve_database_path("aico.db")
        
        if not db_path.exists():
            console.print(f"[red]Database not found: {db_path}[/red]")
            console.print("[yellow]Run 'aico db init' to create the database first[/yellow]")
            raise typer.Exit(1)
        
        # Get master key for database encryption
        if not key_manager.has_stored_key():
            console.print("[red]Master key not found. Run 'aico security setup' first.[/red]")
            raise typer.Exit(1)
        
        # Try session-based authentication first
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        else:
            # Try stored key from keyring
            import keyring
            stored_key = keyring.get_password(key_manager.service_name, "master_key")
            if stored_key:
                master_key = bytes.fromhex(stored_key)
                key_manager._cache_session(master_key)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            else:
                # Need password
                password = typer.prompt("Enter master password", hide_input=True)
                master_key = key_manager.authenticate(password, interactive=False)
                db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        
        return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Database connection failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
