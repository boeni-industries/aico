"""
AICO CLI Agency Commands

Provides commands for inspecting and controlling the Agency system:
- View active intention set
- Manage value profile settings
- List and manage policy rules
- Grant/revoke consents
"""

import typer
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path
import sys
import json
from datetime import datetime
from typing import Optional
import contextlib
import io

# Standard Rich console
from rich.console import Console

# Add shared module to path for CLI usage
if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.data.libsql import EncryptedLibSQLConnection
from aico.security import AICOKeyManager
from aico.ai.agency import AgencyEngine
from aico.ai.agency.values_ethics import ValuesEthicsService, PolicyEffect, ProactiveBehaviorLevel

console = Console()


@contextlib.contextmanager
def _suppress_debug_output():
    """Temporarily suppress stdout/stderr noise from underlying components.

    Used by CLI commands that want a clean, UX-friendly output while still
    initializing complex subsystems that may print debug information.
    """
    new_stdout = io.StringIO()
    new_stderr = io.StringIO()
    with contextlib.redirect_stdout(new_stdout), contextlib.redirect_stderr(new_stderr):
        yield

def agency_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("status", "View high-level agency status for a user"),
            ("intentions", "View active intention set for a user"),
            ("goals", "List all goals for a user"),
            ("plans", "List and manage plans"),
            ("executions", "View plan execution status"),
            ("profile", "View or edit user value profile"),
            ("policies", "List, add, or remove policy rules"),
            ("consent", "Grant or revoke consent for specific actions"),
            ("proactive", "Manage proactive conversation initiations"),
            ("metrics", "Display comprehensive KPI dashboard"),
            ("reflection-history", "Analyze reflection run history"),
            ("skill-performance", "Analyze skill execution success rates"),
            ("health", "Run diagnostic health checks"),
            ("lessons", "Manage lessons (list, review, approve, reject)"),
            ("skillgaps", "Manage skill gaps identified during planning"),
        ]
        
        format_subcommand_help(
            console=console,
            command_name="agency",
            description="Inspect and control the Agency system - intentions, values, policies, and consents.",
            subcommands=subcommands
        )
        raise typer.Exit()

app = typer.Typer(
    name="agency",
    help="Inspect and control the Agency system",
    callback=agency_callback,
    invoke_without_command=True,
    no_args_is_help=False
)


def get_db_connection():
    """Get database connection for agency operations."""
    from aico.core.paths import get_default_database_path
    
    db_path = get_default_database_path()
    
    if not db_path.exists():
        console.print("[red]✗[/red] Database not found. Run 'aico database init' first.")
        raise typer.Exit(1)
    
    try:
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        key_manager = AICOKeyManager(config)
        
        if not key_manager.has_stored_key():
            console.print("[red]✗[/red] Master key not found. Run 'aico security setup' first.")
            raise typer.Exit(1)
        
        # Try session-based authentication first
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        # Try stored key from keyring
        import keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
            key_manager._cache_session(master_key)
            db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        # Need password
        password = typer.prompt("Enter master password", hide_input=True)
        if not password or not password.strip():
            console.print("[red]✗[/red] Password cannot be empty")
            raise typer.Exit(1)
        
        master_key = key_manager.authenticate(password, interactive=False, force_fresh=False)
        db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        
        return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error connecting to database: {e}")
        raise typer.Exit(1)


@app.command()
def goals(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    compact: bool = typer.Option(False, "--compact", "-c", help="Show a compact horizontal table view"),
):
    """List all goals for a user.

    Shows each goal's status, origin, priority, type, and timestamps so you can
    inspect what the Agency is currently tracking (including curiosity goals).
    """
    try:
        try:
            user_id = get_user_id(user)
        except ValueError as e:
            if str(e) == "NO_USER_CONFIGURED":
                console.print("[red]✗[/red] No user configured.")
                console.print("[yellow]-[/yellow] Use [bold]--user[/bold] to specify a user explicitly, e.g. [cyan]aico agency goals --user <user-id>[/cyan]")
                console.print("[yellow]-[/yellow] Or set a default with [cyan]aico config set core.user.id <user-id>[/cyan]")
                raise typer.Exit(1)
            raise

        db = get_db_connection()

        # Load all goals for the user
        rows = db.execute(
            """
            SELECT goal_id, origin, goal_type, title, description,
                   status, priority, metadata_json, created_at, updated_at
            FROM agency_goals
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()

        if json_output:
            goals_json = []
            for row in rows:
                goals_json.append(
                    {
                        "goal_id": row[0],
                        "origin": row[1],
                        "goal_type": row[2],
                        "title": row[3],
                        "description": row[4],
                        "status": row[5],
                        "priority": row[6],
                        "metadata": json.loads(row[7]) if row[7] else {},
                        "created_at": row[8],
                        "updated_at": row[9],
                    }
                )

            console.print_json(data={"user_id": user_id, "goals": goals_json})
            return

        if not rows:
            console.print(f"[yellow]No goals found for user {user_id}[/yellow]")
            return

        if compact:
            # Original horizontal table layout (compact overview)
            table = Table(
                title=f"Goals for {user_id}",
                box=box.SIMPLE_HEAD,
                title_justify="left",
                header_style="bold cyan",
            )
            table.add_column("ID", style="dim", max_width=10, no_wrap=True)
            table.add_column("Title", style="white", max_width=40)
            table.add_column("Status", style="cyan")
            table.add_column("Priority", style="magenta")
            table.add_column("Origin", style="blue")
            table.add_column("Type", style="yellow")
            table.add_column("Created", style="green")

            for row in rows:
                goal_id, origin, goal_type, title, description, status, priority, metadata_json, created_at, updated_at = row
                short_id = goal_id.split("-")[0] if goal_id else ""
                created_str = created_at[:19] if created_at else ""

                table.add_row(
                    short_id,
                    title or "[dim]<no title>[/dim]",
                    status or "",
                    priority or "",
                    origin or "",
                    goal_type or "",
                    created_str,
                )

            console.print(table)
            console.print(f"\n[dim]Total: {len(rows)} goal(s)[/dim]")
        else:
            console.print(f"[bold cyan]Goals for {user_id}[/bold cyan]\n")

            # Vertical field/value layout to avoid truncation
            for idx, row in enumerate(rows, start=1):
                goal_id, origin, goal_type, title, description, status, priority, metadata_json, created_at, updated_at = row
                short_id = goal_id.split("-")[0] if goal_id else ""
                created_str = created_at[:19] if created_at else ""
                updated_str = updated_at[:19] if updated_at else ""

                table = Table(
                    box=box.SIMPLE_HEAD,
                    show_header=False,
                )
                table.add_column("Field", style="yellow", no_wrap=True)
                table.add_column("Value", style="white")

                table.add_row("Goal #", str(idx))
                table.add_row("ID", goal_id or "")
                table.add_row("Short ID", short_id)
                table.add_row("Title", title or "[dim]<no title>[/dim]")
                if description:
                    table.add_row("Description", description)
                table.add_row("Status", status or "")
                table.add_row("Priority", priority or "")
                table.add_row("Origin", origin or "")
                table.add_row("Type", goal_type or "")
                table.add_row("Created", created_str)
                if updated_str:
                    table.add_row("Updated", updated_str)

                console.print(table)
                console.print()  # Blank line between goals

            console.print(f"[dim]Total: {len(rows)} goal(s)[/dim]")

    except Exception as e:
        console.print(f"[red]✗[/red] Error listing goals: {e}")
        raise typer.Exit(1)


def get_user_id(user: Optional[str] = None) -> str:
    """Get user ID from argument or config."""
    if user:
        return user
    
    # Try to get from config
    config = ConfigurationManager()
    user_id = config.get("core.user.id")
    
    if not user_id:
        # Defer user-facing messaging to the calling command for better UX
        raise ValueError("NO_USER_CONFIGURED")
    
    return user_id


@app.command()
def status(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    limit: int = typer.Option(5, "--limit", "-n", help="Maximum number of intentions to sample"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """View high-level agency status for a user.

    Shows a concise snapshot of the agency state:
    - User and profile highlights (curiosity, proactive level)
    - Number of active intentions
    - Top intention summary (if any)
    """
    try:
        try:
            user_id = get_user_id(user)
        except ValueError as e:
            if str(e) == "NO_USER_CONFIGURED":
                console.print("[red]✗[/red] No user configured.")
                console.print("[yellow]-[/yellow] Use [bold]--user[/bold] to specify a user explicitly, e.g. [cyan]aico agency status --user <user-id>[/cyan]")
                console.print("[yellow]-[/yellow] Or set a default with [cyan]aico config set core.user.id <user-id>[/cyan]")
                raise typer.Exit(1)
            # Re-raise unexpected ValueError
            raise

        # Wrap initialization in debug suppression to keep CLI output clean
        with _suppress_debug_output():
            db = get_db_connection()
            config = ConfigurationManager()

            # Initialize core services
            engine = AgencyEngine(config, db)
            values_service = ValuesEthicsService(db)

            # Fetch value profile
            profile = values_service._get_or_create_profile(user_id)

            # Fetch intention set (reusing existing async pattern)
            import asyncio

            intention_set = asyncio.run(engine.get_intention_set(user_id))

            # Fetch Goal objects for all intentions
            goal_map = {}
            if intention_set.intentions:
                goal_ids = [i.goal_id for i in intention_set.intentions]
                placeholders = ','.join(['?'] * len(goal_ids))
                cursor = db.execute(
                    f"SELECT * FROM agency_goals WHERE goal_id IN ({placeholders})",
                    tuple(goal_ids)
                )
                from aico.ai.agency.models import Goal, GoalOrigin, GoalStatus, GoalPriority
                for row in cursor.fetchall():
                    goal = Goal(
                        goal_id=row["goal_id"],
                        user_id=row["user_id"],
                        origin=GoalOrigin(row["origin"]),
                        goal_type=row["goal_type"],
                        title=row["title"],
                        description=row["description"],
                        status=GoalStatus(row["status"]),
                        priority=GoalPriority(row["priority"]),
                        metadata=json.loads(row["metadata_json"] or "{}"),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"])
                    )
                    goal_map[goal.goal_id] = goal

            # Optional: fetch goal summary for this user
            goals_summary = None
            try:
                cursor = db.execute(
                    "SELECT status, COUNT(*) FROM agency_goals WHERE user_id = ? GROUP BY status",
                    (user_id,),
                )
                rows = cursor.fetchall()
                by_status = {row[0] or "unknown": row[1] for row in rows}

                total_goals = sum(by_status.values())
                completed = by_status.get("completed", 0)
                retired = by_status.get("retired", 0)
                active = by_status.get("active", 0) + by_status.get("pending", 0)
                paused = by_status.get("paused", 0)

                goals_summary = {
                    "total": int(total_goals),
                    "active": int(active),
                    "completed": int(completed),
                    "retired": int(retired),
                    "paused": int(paused),
                    "by_status": {k: int(v) for k, v in by_status.items()},
                }
            except Exception:
                # If schema or query fails, silently skip goals section
                goals_summary = None
        intentions = intention_set.intentions or []

        if len(intentions) > limit:
            intentions = intentions[:limit]

        top_intention = intentions[0] if intentions else None
        top_goal = goal_map.get(top_intention.goal_id) if top_intention else None

        if json_output:
            # JSON-friendly representation
            output = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "profile": {
                    "curiosity_intensity": profile.curiosity_intensity,
                    "proactive_behavior_level": profile.proactive_behavior_level.value,
                    "sensitive_life_areas": profile.sensitive_life_areas,
                },
                "goals": goals_summary,
                "intentions": {
                    "total": len(intention_set.intentions),
                    "sampled": len(intentions),
                    "top": {
                        "goal_id": top_goal.goal_id,
                        "title": top_goal.title,
                        "origin": top_goal.origin.value,
                        "priority": top_goal.priority.value,
                        "status": top_goal.status.value,
                        "intention_status": top_intention.status.value,
                        "arbiter_score": top_intention.arbiter_score,
                        "priority_band": top_intention.priority_band.value,
                        "reasons": top_intention.reasons,
                    } if (top_intention and top_goal) else None,
                },
            }
            console.print_json(data=output)
            return

        # Rich table output
        table = Table(
            title=f"Agency Status for {user_id}",
            box=box.SIMPLE_HEAD,
            title_justify="left",
            header_style="bold cyan",
        )
        table.add_column("Metric", style="yellow", no_wrap=True)
        table.add_column("Value", style="white")

        # Profile summary
        table.add_row("User", user_id)
        table.add_row("Curiosity Intensity", f"{profile.curiosity_intensity:.2f}")
        table.add_row("Proactive Level", profile.proactive_behavior_level.value)

        sensitive = ", ".join(profile.sensitive_life_areas) if profile.sensitive_life_areas else "[dim]None configured[/dim]"
        table.add_row("Sensitive Areas", sensitive)

        # Intention summary
        total_intentions = len(intention_set.intentions)
        table.add_row("Active Intentions", str(total_intentions))

        if top_intention and top_goal:
            band_color = {
                "urgent": "red",
                "normal": "yellow",
                "background": "blue",
            }.get(top_intention.priority_band.value, "white")

            band_str = f"[{band_color}]{top_intention.priority_band.value}[/{band_color}]"
            table.add_row("Top Intention", top_goal.title)
            table.add_row("Top Origin", top_goal.origin.value)
            table.add_row("Top Priority", top_goal.priority.value)
            table.add_row("Top Score", f"{top_intention.arbiter_score:.3f}")
            table.add_row("Top Band", band_str)
            table.add_row("Intention Status", top_intention.status.value)
            table.add_row("Goal Status", top_goal.status.value)
        else:
            table.add_row("Top Intention", "[dim]None[/dim]")

        console.print()
        console.print(table)

        # Goals & activity summary (even if there are no intentions)
        if goals_summary is not None:
            goals_table = Table(
                title="Goals & Activity",
                box=box.SIMPLE_HEAD,
                title_justify="left",
                header_style="bold green",
            )
            goals_table.add_column("Metric", style="yellow", no_wrap=True)
            goals_table.add_column("Value", style="white")

            goals_table.add_row("Total Goals", str(goals_summary.get("total", 0)))
            goals_table.add_row("Active/Pending", str(goals_summary.get("active", 0)))
            goals_table.add_row("Paused", str(goals_summary.get("paused", 0)))
            goals_table.add_row("Completed", str(goals_summary.get("completed", 0)))
            goals_table.add_row("Retired", str(goals_summary.get("retired", 0)))

            console.print()
            console.print(goals_table)
        # If we have a top intention with a score breakdown, show contributing factors
        if top_intention and getattr(top_intention, "score_breakdown", None):
            factors = top_intention.score_breakdown
            factors_table = Table(
                title="Top Intention – Scoring Breakdown",
                box=box.SIMPLE_HEAD,
                title_justify="left",
                header_style="bold magenta",
            )
            factors_table.add_column("Factor", style="yellow", no_wrap=True)
            factors_table.add_column("Value", style="white")

            for name, value in factors.items():
                # Format numeric values nicely, keep others as-is
                if isinstance(value, float):
                    value_str = f"{value:.3f}"
                else:
                    value_str = str(value)
                factors_table.add_row(name, value_str)

            console.print()
            console.print(factors_table)

        console.print(f"\n[dim]Sampled up to {limit} intentions for summary[/dim]")

    except Exception as e:
        console.print(f"[red]✗[/red] Error retrieving status: {e}")
        raise typer.Exit(1)


@app.command()
def intentions(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of intentions to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    View the active intention set for a user.
    
    Shows the top-ranked goals that the agent is currently pursuing or considering,
    along with their scores and priority bands.
    """
    try:
        user_id = get_user_id(user)

        # Suppress noisy debug output from underlying components
        with _suppress_debug_output():
            db = get_db_connection()
            config = ConfigurationManager()
            
            # Initialize engine
            engine = AgencyEngine(config, db)
            
            # Get intention set
            import asyncio
            intention_set = asyncio.run(engine.get_intention_set(user_id))
        
        # Limit results if needed
        if len(intention_set.intentions) > limit:
            intention_set.intentions = intention_set.intentions[:limit]
        
        if json_output:
            # JSON output
            output = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "intentions": [
                    {
                        "intention_id": intention.intention_id,
                        "goal_id": intention.goal_id,
                        "status": intention.status.value,
                        "score": intention.arbiter_score,
                        "priority_band": intention.priority_band.value,
                        "reasons": intention.reasons,
                        "activated_at": intention.activated_at.isoformat() if intention.activated_at else None,
                    }
                    for intention in intention_set.intentions
                ]
            }
            console.print_json(data=output)
        else:
            # Rich table output
            if not intention_set.intentions:
                console.print(f"[yellow]No active intentions for user {user_id}[/yellow]")
                return
            
            # Fetch goal details for display
            goal_ids = [i.goal_id for i in intention_set.intentions]
            placeholders = ','.join('?' * len(goal_ids))
            goals_data = db.execute(
                f"SELECT goal_id, title, origin, priority, status FROM agency_goals WHERE goal_id IN ({placeholders})",
                tuple(goal_ids)
            ).fetchall()
            goals_map = {g["goal_id"]: g for g in goals_data}
            
            table = Table(
                title=f"Active Intention Set for {user_id}",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            
            table.add_column("Title", style="white", no_wrap=False, max_width=40)
            table.add_column("Origin", style="blue")
            table.add_column("Priority", style="magenta")
            table.add_column("Score", style="green", justify="right")
            table.add_column("Band", style="yellow")
            table.add_column("Status", style="cyan")
            
            for intention in intention_set.intentions:
                goal_data = goals_map.get(intention.goal_id)
                
                if not goal_data:
                    continue
                
                # Color code priority band
                band_color = {
                    "urgent": "red",
                    "normal": "green",
                    "background": "blue"
                }.get(intention.priority_band.value, "white")
                
                table.add_row(
                    goal_data["title"],
                    goal_data["origin"],
                    goal_data["priority"],
                    f"{intention.arbiter_score:.3f}",
                    f"[{band_color}]{intention.priority_band.value}[/{band_color}]",
                    intention.status.value
                )
            
            console.print(table)
            console.print(f"\n[dim]Showing {len(intention_set.intentions)} of {limit} max intentions[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error retrieving intentions: {e}")
        raise typer.Exit(1)


@app.command()
def profile(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all profile details"),
    set_curiosity: Optional[float] = typer.Option(None, "--curiosity", help="Set curiosity intensity (0.0-1.0)"),
    set_proactive: Optional[str] = typer.Option(None, "--proactive", help="Set proactive level (quiet/balanced/proactive)"),
    add_sensitive: Optional[str] = typer.Option(None, "--add-sensitive", help="Add sensitive life area"),
    remove_sensitive: Optional[str] = typer.Option(None, "--remove-sensitive", help="Remove sensitive life area"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    View or edit user value profile.
    
    The value profile controls how the agent behaves, including curiosity intensity,
    proactive behavior level, and sensitive life areas.
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        service = ValuesEthicsService(db)
        profile = service._get_or_create_profile(user_id)
        
        # Handle updates
        updated = False
        
        if set_curiosity is not None:
            if not 0.0 <= set_curiosity <= 1.0:
                console.print("[red]✗[/red] Curiosity intensity must be between 0.0 and 1.0")
                raise typer.Exit(1)
            profile.curiosity_intensity = set_curiosity
            updated = True
        
        if set_proactive:
            try:
                level = ProactiveBehaviorLevel(set_proactive.lower())
                profile.proactive_behavior_level = level
                updated = True
            except ValueError:
                console.print(f"[red]✗[/red] Invalid proactive level. Use: quiet, balanced, or proactive")
                raise typer.Exit(1)
        
        if add_sensitive:
            if add_sensitive not in profile.sensitive_life_areas:
                profile.sensitive_life_areas.append(add_sensitive)
                updated = True
        
        if remove_sensitive:
            if remove_sensitive in profile.sensitive_life_areas:
                profile.sensitive_life_areas.remove(remove_sensitive)
                updated = True
        
        # Save updates
        if updated:
            db.execute(
                """
                UPDATE ethics_value_profiles 
                SET curiosity_intensity = ?, 
                    proactive_behavior_level = ?,
                    sensitive_life_areas = ?,
                    updated_at = ?
                WHERE profile_id = ?
                """,
                (
                    profile.curiosity_intensity,
                    profile.proactive_behavior_level.value,
                    json.dumps(profile.sensitive_life_areas),
                    datetime.utcnow().isoformat(),
                    profile.profile_id
                )
            )
            db.commit()
            console.print("[green]✓[/green] Profile updated successfully")
        
        # Display profile
        if json_output:
            output = {
                "profile_id": profile.profile_id,
                "user_id": profile.user_id,
                "curiosity_intensity": profile.curiosity_intensity,
                "proactive_behavior_level": profile.proactive_behavior_level.value,
                "sensitive_life_areas": profile.sensitive_life_areas,
                "allowed_curiosity_domains": profile.allowed_curiosity_domains,
            }
            console.print_json(data=output)
        else:
            panel_content = f"""[bold]User:[/bold] {profile.user_id}
[bold]Profile ID:[/bold] {profile.profile_id}

[bold cyan]Behavior Settings[/bold cyan]
[bold]Curiosity Intensity:[/bold] {profile.curiosity_intensity:.2f}
[bold]Proactive Level:[/bold] {profile.proactive_behavior_level.value}

[bold cyan]Sensitive Life Areas[/bold cyan]
{', '.join(profile.sensitive_life_areas) if profile.sensitive_life_areas else '[dim]None configured[/dim]'}
"""
            
            if show_all:
                panel_content += f"""
[bold cyan]Allowed Curiosity Domains[/bold cyan]
{', '.join(profile.allowed_curiosity_domains) if profile.allowed_curiosity_domains else '[dim]All domains allowed[/dim]'}
"""
            
            console.print(Panel(panel_content, title="Value Profile", border_style="cyan"))
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error managing profile: {e}")
        raise typer.Exit(1)


@app.command()
def policies(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all policies"),
    target_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by target type (goal/plan/curiosity_signal/world_model_update)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List and manage policy rules.
    
    Policies control what goals, plans, and curiosity signals are allowed,
    warned about, or blocked.
    """
    try:
        db = get_db_connection()
        
        # Query policies
        query = "SELECT * FROM ethics_policy_rules"
        params = []
        
        if target_type:
            query += " WHERE target_type = ?"
            params.append(target_type)
        
        query += " ORDER BY priority ASC"
        
        cursor = db.execute(query, tuple(params))
        policies = cursor.fetchall()
        
        if not policies:
            console.print("[yellow]No policies found[/yellow]")
            return
        
        if json_output:
            # Schema: rule_id, rule_name, target_type, conditions_json, effect, user_message_template, priority, enabled, scope, scope_id
            output = [
                {
                    "rule_id": p[0],
                    "rule_name": p[1],
                    "target_type": p[2],
                    "conditions": json.loads(p[3]) if p[3] and isinstance(p[3], str) else (p[3] if p[3] else {}),
                    "effect": p[4],
                    "user_message": p[5],
                    "priority": p[6],
                    "enabled": bool(p[7]),
                    "scope": p[8],
                    "scope_id": p[9],
                }
                for p in policies
            ]
            console.print_json(data=output)
        else:
            table = Table(
                title="Policy Rules",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            
            table.add_column("Rule Name", style="white", no_wrap=False, max_width=30)
            table.add_column("Target", style="blue")
            table.add_column("Effect", style="magenta")
            table.add_column("Scope", style="yellow")
            table.add_column("Priority", style="green", justify="right")
            
            for p in policies:
                # Schema: rule_id, rule_name, target_type, conditions_json, effect, user_message_template, priority, enabled, scope, scope_id
                effect_color = {
                    "allow": "green",
                    "allow_with_warning": "yellow",
                    "needs_consent": "orange1",
                    "block": "red"
                }.get(p[4], "white")
                
                table.add_row(
                    p[1],  # rule_name
                    p[2],  # target_type
                    f"[{effect_color}]{p[4]}[/{effect_color}]",  # effect
                    p[8],  # scope
                    str(p[6])  # priority
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(policies)} policies[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing policies: {e}")
        raise typer.Exit(1)


@app.command()
def consent(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all consents"),
    grant: Optional[str] = typer.Option(None, "--grant", help="Grant consent (provide scope as JSON)"),
    revoke: Optional[str] = typer.Option(None, "--revoke", help="Revoke consent by ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Grant or revoke consent for specific actions.
    
    Consents allow the agent to proceed with actions that would otherwise
    require explicit permission.
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        if grant:
            # Grant new consent
            try:
                scope = json.loads(grant)
            except json.JSONDecodeError:
                console.print("[red]✗[/red] Invalid JSON for consent scope")
                raise typer.Exit(1)
            
            consent_id = f"consent-{user_id}-{datetime.utcnow().timestamp()}"
            
            db.execute(
                """
                INSERT INTO consent_records (consent_id, user_id, scope, decision, granted_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (consent_id, user_id, json.dumps(scope), "granted", datetime.utcnow().isoformat())
            )
            db.commit()
            console.print(f"[green]✓[/green] Consent granted: {consent_id}")
            return
        
        if revoke:
            # Revoke consent
            db.execute(
                "UPDATE consent_records SET decision = ?, updated_at = ? WHERE consent_id = ? AND user_id = ?",
                ("denied", datetime.utcnow().isoformat(), revoke, user_id)
            )
            db.commit()
            console.print(f"[green]✓[/green] Consent revoked: {revoke}")
            return
        
        # List consents
        cursor = db.execute(
            "SELECT * FROM consent_records WHERE user_id = ? ORDER BY granted_at DESC",
            (user_id,)
        )
        consents = cursor.fetchall()
        
        if not consents:
            console.print(f"[yellow]No consents found for user {user_id}[/yellow]")
            return
        
        if json_output:
            output = [
                {
                    "consent_id": c[0],
                    "user_id": c[1],
                    "scope": json.loads(c[2]) if c[2] else {},
                    "decision": c[3],
                    "granted_at": c[4],
                }
                for c in consents
            ]
            console.print_json(data=output)
        else:
            table = Table(
                title=f"Consents for {user_id}",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            
            table.add_column("Consent ID", style="white", max_width=30)
            table.add_column("Scope", style="blue", no_wrap=False, max_width=40)
            table.add_column("Decision", style="magenta")
            table.add_column("Granted At", style="green")
            
            for c in consents:
                scope_str = json.dumps(json.loads(c[2]) if c[2] else {}, indent=None)
                decision_color = "green" if c[3] == "granted" else "red"
                
                table.add_row(
                    c[0],
                    scope_str,
                    f"[{decision_color}]{c[3]}[/{decision_color}]",
                    c[4][:19] if c[4] else ""
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(consents)} consents[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error managing consent: {e}")
        raise typer.Exit(1)


@app.command("plans")
def plans(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    goal: Optional[str] = typer.Option(None, "--goal", "-g", help="Filter by goal ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of plans to show"),
):
    """List plans for a user."""
    try:
        user_id = get_user_id(user)
        
        with _suppress_debug_output():
            db = get_db_connection()
        
        # Build query - join with goals to get user_id
        query = """
            SELECT p.plan_id, p.goal_id, p.status, p.created_at 
            FROM agency_plans p
            JOIN agency_goals g ON p.goal_id = g.goal_id
            WHERE g.user_id = ?
        """
        params = [user_id]
        
        if status:
            query += " AND p.status = ?"
            params.append(status)
        
        if goal:
            query += " AND p.goal_id = ?"
            params.append(goal)
        
        query += " ORDER BY p.created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute(query, tuple(params)).fetchall()
        
        if not rows:
            console.print("[yellow]No plans found[/yellow]")
            return
        
        table = Table(title=f"Plans for {user_id}", box=box.SIMPLE_HEAD)
        table.add_column("Plan ID", style="cyan")
        table.add_column("Goal ID", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")
        
        for row in rows:
            status_color = {
                "draft": "yellow",
                "active": "green",
                "completed": "blue",
                "abandoned": "red"
            }.get(row["status"], "white")
            
            table.add_row(
                row["plan_id"][:8],
                row["goal_id"][:8],
                f"[{status_color}]{row['status']}[/{status_color}]",
                row["created_at"][:19] if row["created_at"] else ""
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(rows)} plans[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing plans: {e}")
        raise typer.Exit(1)


@app.command("executions")
def executions(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number to show"),
):
    """View plan execution status."""
    try:
        user_id = get_user_id(user)
        
        with _suppress_debug_output():
            db = get_db_connection()
        
        # Build query
        query = """
            SELECT execution_id, plan_id, goal_id, status, 
                   progress_percentage, steps_completed, steps_total,
                   started_at, completed_at
            FROM agency_plan_executions 
            WHERE user_id = ?
        """
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = db.execute(query, tuple(params)).fetchall()
        
        if not rows:
            console.print("[yellow]No executions found[/yellow]")
            return
        
        table = Table(title=f"Plan Executions for {user_id}", box=box.SIMPLE_HEAD)
        table.add_column("Execution ID", style="cyan")
        table.add_column("Plan", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Steps", style="white")
        table.add_column("Started", style="dim")
        
        for row in rows:
            status_color = {
                "pending": "yellow",
                "running": "blue",
                "completed": "green",
                "failed": "red",
                "paused": "yellow",
                "cancelled": "red"
            }.get(row["status"], "white")
            
            progress = f"{row['progress_percentage']:.0f}%"
            steps = f"{row['steps_completed']}/{row['steps_total']}"
            
            table.add_row(
                row["execution_id"][:8],
                row["plan_id"][:8],
                f"[{status_color}]{row['status']}[/{status_color}]",
                progress,
                steps,
                row["started_at"][:19] if row["started_at"] else "Not started"
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(rows)} executions[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing executions: {e}")
        raise typer.Exit(1)



@app.command("replan")
def replan_goal(
    goal_id: str = typer.Argument(..., help="Goal ID to replan"),
    force: bool = typer.Option(False, "--force", "-f", help="Force replanning even if plan is active"),
):
    """Regenerate plan for a goal through the backend API."""
    try:
        from cli.utils.api_client import get_backend_client
        
        console.print(f"[cyan]Requesting replanning for goal {goal_id[:8]}...[/cyan]")
        
        with get_backend_client() as client:
            result = client.post(
                f"/api/v1/agency/goals/{goal_id}/replan",
                params={"force": force}
            )
            
            console.print(f"[green]✓[/green] Plan regenerated successfully")
            console.print(f"[dim]Goal: {result['title']}[/dim]")
            console.print(f"[dim]Strategy: {result['metadata'].get('plan_strategy', 'unknown')}[/dim]")
            console.print(f"[dim]Plan ID: {result['metadata'].get('plan_id', 'unknown')[:8]}...[/dim]")
        
    except Exception as e:
        error_msg = str(e)
        if "Cannot connect" in error_msg or "Connection" in error_msg:
            console.print(f"[red]✗[/red] Cannot connect to backend")
            console.print("[yellow]⚠[/yellow] Make sure the backend is running")
        elif "404" in error_msg:
            console.print(f"[red]✗[/red] Goal {goal_id} not found")
        elif "400" in error_msg:
            console.print(f"[yellow]⚠[/yellow] {error_msg}")
        else:
            console.print(f"[red]✗[/red] Error replanning goal: {e}")
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def metrics(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    last: Optional[str] = typer.Option(None, "--last", help="Time window (e.g., '7d', '30d', '1h')"),
    since: Optional[str] = typer.Option(None, "--since", help="Start timestamp (ISO format)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Display comprehensive KPI dashboard for agency system.
    
    Shows key performance indicators including:
    - Goal completion rates
    - Plan success rates
    - Skill execution metrics
    - Reflection run statistics
    - Lesson application rates
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Parse time window
        time_filter = ""
        params = [user_id]
        
        if last:
            from datetime import timedelta
            duration = _parse_duration(last)
            cutoff = (datetime.utcnow() - duration).isoformat()
            time_filter = " AND created_at >= ?"
            params.append(cutoff)
        elif since:
            time_filter = " AND created_at >= ?"
            params.append(since)
        
        # Collect metrics
        metrics_data = {}
        
        # Goal metrics
        goal_stats = db.execute(
            f"""SELECT status, COUNT(*) as count 
                FROM agency_goals 
                WHERE user_id = ?{time_filter}
                GROUP BY status""",
            tuple(params)
        ).fetchall()
        
        total_goals = sum(row["count"] for row in goal_stats)
        completed_goals = next((row["count"] for row in goal_stats if row["status"] == "completed"), 0)
        
        metrics_data["goals"] = {
            "total": total_goals,
            "completed": completed_goals,
            "completion_rate": (completed_goals / total_goals * 100) if total_goals > 0 else 0,
            "by_status": {row["status"]: row["count"] for row in goal_stats}
        }
        
        # Plan metrics (join through goals to get user_id)
        plan_stats = db.execute(
            f"""SELECT p.status, COUNT(*) as count
                FROM agency_plans p
                JOIN agency_goals g ON p.goal_id = g.goal_id
                WHERE g.user_id = ?{time_filter.replace('created_at', 'p.created_at') if time_filter else ''}
                GROUP BY p.status""",
            tuple(params)
        ).fetchall()
        
        total_plans = sum(row["count"] for row in plan_stats)
        completed_plans = next((row["count"] for row in plan_stats if row["status"] == "completed"), 0)
        
        metrics_data["plans"] = {
            "total": total_plans,
            "completed": completed_plans,
            "success_rate": (completed_plans / total_plans * 100) if total_plans > 0 else 0,
            "by_status": {row["status"]: row["count"] for row in plan_stats}
        }
        
        # Execution metrics
        exec_stats = db.execute(
            f"""SELECT status, COUNT(*) as count, AVG(progress_percentage) as avg_progress
                FROM agency_plan_executions
                WHERE user_id = ?{time_filter}
                GROUP BY status""",
            tuple(params)
        ).fetchall()
        
        metrics_data["executions"] = {
            "total": sum(row["count"] for row in exec_stats),
            "by_status": {row["status"]: {"count": row["count"], "avg_progress": row["avg_progress"]} for row in exec_stats}
        }
        
        # Reflection metrics
        reflection_count = db.execute(
            f"""SELECT COUNT(*) as count FROM agency_reflection_runs
                WHERE user_id = ?{time_filter}""",
            tuple(params)
        ).fetchone()["count"]
        
        lesson_count = db.execute(
            f"""SELECT COUNT(*) as count FROM agency_lessons
                WHERE user_id = ?{time_filter}""",
            tuple(params)
        ).fetchone()["count"]
        
        applied_lessons = db.execute(
            f"""SELECT COUNT(*) as count FROM agency_lessons
                WHERE user_id = ? AND status = 'applied'{time_filter}""",
            tuple(params)
        ).fetchone()["count"]
        
        metrics_data["reflection"] = {
            "runs": reflection_count,
            "lessons_generated": lesson_count,
            "lessons_applied": applied_lessons,
            "application_rate": (applied_lessons / lesson_count * 100) if lesson_count > 0 else 0
        }
        
        # Event metrics
        event_count = db.execute(
            f"""SELECT COUNT(*) as count FROM agency_events_log
                WHERE user_id = ?{time_filter}""",
            tuple(params)
        ).fetchone()["count"]
        
        metrics_data["events"] = {
            "total": event_count
        }
        
        if json_output:
            console.print_json(data=metrics_data)
        else:
            # Display formatted dashboard
            console.print(Panel.fit(
                f"[bold cyan]Agency Metrics Dashboard[/bold cyan]\n"
                f"User: {user_id}\n"
                f"Time Window: {last or since or 'All time'}",
                border_style="cyan"
            ))
            
            # Goals table
            goals_table = Table(title="Goals", box=box.ROUNDED)
            goals_table.add_column("Metric", style="cyan")
            goals_table.add_column("Value", style="white")
            goals_table.add_row("Total Goals", str(metrics_data["goals"]["total"]))
            goals_table.add_row("Completed", str(metrics_data["goals"]["completed"]))
            goals_table.add_row("Completion Rate", f"{metrics_data['goals']['completion_rate']:.1f}%")
            console.print(goals_table)
            
            # Plans table
            plans_table = Table(title="Plans", box=box.ROUNDED)
            plans_table.add_column("Metric", style="cyan")
            plans_table.add_column("Value", style="white")
            plans_table.add_row("Total Plans", str(metrics_data["plans"]["total"]))
            plans_table.add_row("Completed", str(metrics_data["plans"]["completed"]))
            plans_table.add_row("Success Rate", f"{metrics_data['plans']['success_rate']:.1f}%")
            console.print(plans_table)
            
            # Reflection table
            reflection_table = Table(title="Reflection & Learning", box=box.ROUNDED)
            reflection_table.add_column("Metric", style="cyan")
            reflection_table.add_column("Value", style="white")
            reflection_table.add_row("Reflection Runs", str(metrics_data["reflection"]["runs"]))
            reflection_table.add_row("Lessons Generated", str(metrics_data["reflection"]["lessons_generated"]))
            reflection_table.add_row("Lessons Applied", str(metrics_data["reflection"]["lessons_applied"]))
            reflection_table.add_row("Application Rate", f"{metrics_data['reflection']['application_rate']:.1f}%")
            console.print(reflection_table)
            
            console.print(f"\n[dim]Total Events: {metrics_data['events']['total']}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error generating metrics: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def reflection_history(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of runs to show"),
    last: Optional[str] = typer.Option(None, "--last", help="Time window (e.g., '7d', '30d')"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze reflection run history and effectiveness.
    
    Shows:
    - Recent reflection runs
    - Lessons generated per run
    - Confidence scores
    - Application status
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Parse time window
        time_filter = ""
        params = [user_id]
        
        if last:
            from datetime import timedelta
            duration = _parse_duration(last)
            cutoff = (datetime.utcnow() - duration).isoformat()
            time_filter = " AND started_at >= ?"
            params.append(cutoff)
        
        # Get reflection runs with lesson counts
        query = f"""
            SELECT 
                r.run_id,
                r.started_at,
                r.completed_at,
                r.status,
                r.trigger_reason,
                COUNT(l.lesson_id) as lessons_generated,
                AVG(l.confidence) as avg_confidence
            FROM agency_reflection_runs r
            LEFT JOIN agency_lessons l ON r.run_id = l.source_reflection_run_id
            WHERE r.user_id = ?{time_filter}
            GROUP BY r.run_id
            ORDER BY r.started_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        runs = db.execute(query, tuple(params)).fetchall()
        
        if not runs:
            console.print("[yellow]No reflection runs found[/yellow]")
            return
        
        if json_output:
            output = [
                {
                    "run_id": r["run_id"],
                    "started_at": r["started_at"],
                    "completed_at": r["completed_at"],
                    "status": r["status"],
                    "trigger_reason": r["trigger_reason"],
                    "lessons_generated": r["lessons_generated"],
                    "avg_confidence": r["avg_confidence"]
                }
                for r in runs
            ]
            console.print_json(data=output)
        else:
            table = Table(title=f"Reflection History for {user_id}", box=box.ROUNDED)
            table.add_column("Run ID", style="cyan")
            table.add_column("Started", style="white")
            table.add_column("Status", style="green")
            table.add_column("Trigger", style="blue")
            table.add_column("Lessons", style="yellow")
            table.add_column("Avg Confidence", style="magenta")
            
            for r in runs:
                status_color = {
                    "completed": "green",
                    "running": "blue",
                    "failed": "red"
                }.get(r["status"], "white")
                
                table.add_row(
                    r["run_id"][:8],
                    r["started_at"][:19] if r["started_at"] else "N/A",
                    f"[{status_color}]{r['status']}[/{status_color}]",
                    r["trigger_reason"] or "N/A",
                    str(r["lessons_generated"]),
                    f"{r['avg_confidence']:.2f}" if r["avg_confidence"] else "N/A"
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(runs)} reflection runs[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error analyzing reflection history: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def skill_performance(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    skill_name: Optional[str] = typer.Option(None, "--skill", "-s", help="Filter by skill name"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of skills to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Analyze skill execution success rates and performance.
    
    Shows:
    - Skill execution counts
    - Success/failure rates
    - Average performance metrics
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Get skill performance from self-model
        query = """
            SELECT 
                entity_id as skill_id,
                performance_summary,
                sample_size,
                confidence,
                last_updated
            FROM agency_self_model
            WHERE user_id = ? AND entity_type = 'skill'
        """
        params = [user_id]
        
        if skill_name:
            query += " AND entity_id = ?"
            params.append(skill_name)
        
        query += " ORDER BY sample_size DESC LIMIT ?"
        params.append(limit)
        
        skills = db.execute(query, tuple(params)).fetchall()
        
        if not skills:
            console.print("[yellow]No skill performance data found[/yellow]")
            return
        
        if json_output:
            output = []
            for s in skills:
                perf = json.loads(s["performance_summary"]) if s["performance_summary"] else {}
                output.append({
                    "skill_id": s["skill_id"],
                    "performance": perf,
                    "sample_size": s["sample_size"],
                    "confidence": s["confidence"],
                    "last_updated": s["last_updated"]
                })
            console.print_json(data=output)
        else:
            table = Table(title=f"Skill Performance for {user_id}", box=box.ROUNDED)
            table.add_column("Skill ID", style="cyan")
            table.add_column("Sample Size", style="white")
            table.add_column("Success Rate", style="yellow")
            table.add_column("Confidence", style="magenta")
            table.add_column("Last Updated", style="dim")
            
            for s in skills:
                perf = json.loads(s["performance_summary"]) if s["performance_summary"] else {}
                success_rate = perf.get("success_rate", 0) * 100  # Convert to percentage
                
                rate_color = "green" if success_rate >= 80 else "yellow" if success_rate >= 60 else "red"
                
                table.add_row(
                    s["skill_id"][:40],  # Truncate long IDs
                    str(s["sample_size"]),
                    f"[{rate_color}]{success_rate:.1f}%[/{rate_color}]",
                    f"{s['confidence']:.2f}",
                    s["last_updated"][:19] if s["last_updated"] else "N/A"
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(skills)} skills[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error analyzing skill performance: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def health(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Run diagnostic health checks on the agency system.
    
    Checks for:
    - Stale reflection runs
    - Abnormal lesson application rates
    - High goal abandonment rates
    - System anomalies
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        health_issues = []
        warnings = []
        info = []
        
        # Check 1: Stale reflection runs
        from datetime import timedelta
        stale_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        
        stale_runs = db.execute(
            """SELECT COUNT(*) as count FROM agency_reflection_runs
               WHERE user_id = ? AND status = 'running' AND started_at < ?""",
            (user_id, stale_cutoff)
        ).fetchone()["count"]
        
        if stale_runs > 0:
            health_issues.append({
                "severity": "warning",
                "check": "stale_reflection_runs",
                "message": f"{stale_runs} reflection runs stuck in 'running' state for >7 days",
                "count": stale_runs
            })
        
        # Check 2: Lesson application rate
        total_lessons = db.execute(
            "SELECT COUNT(*) as count FROM agency_lessons WHERE user_id = ?",
            (user_id,)
        ).fetchone()["count"]
        
        applied_lessons = db.execute(
            "SELECT COUNT(*) as count FROM agency_lessons WHERE user_id = ? AND status = 'applied'",
            (user_id,)
        ).fetchone()["count"]
        
        if total_lessons > 10:
            application_rate = (applied_lessons / total_lessons) * 100
            if application_rate < 20:
                warnings.append({
                    "severity": "warning",
                    "check": "low_lesson_application",
                    "message": f"Low lesson application rate: {application_rate:.1f}% ({applied_lessons}/{total_lessons})",
                    "rate": application_rate
                })
        
        # Check 3: Goal abandonment rate
        total_goals = db.execute(
            "SELECT COUNT(*) as count FROM agency_goals WHERE user_id = ?",
            (user_id,)
        ).fetchone()["count"]
        
        abandoned_goals = db.execute(
            "SELECT COUNT(*) as count FROM agency_goals WHERE user_id = ? AND status = 'abandoned'",
            (user_id,)
        ).fetchone()["count"]
        
        if total_goals > 10:
            abandonment_rate = (abandoned_goals / total_goals) * 100
            if abandonment_rate > 30:
                warnings.append({
                    "severity": "warning",
                    "check": "high_goal_abandonment",
                    "message": f"High goal abandonment rate: {abandonment_rate:.1f}% ({abandoned_goals}/{total_goals})",
                    "rate": abandonment_rate
                })
        
        # Check 4: Failed plan executions
        total_executions = db.execute(
            "SELECT COUNT(*) as count FROM agency_plan_executions WHERE user_id = ?",
            (user_id,)
        ).fetchone()["count"]
        
        failed_executions = db.execute(
            "SELECT COUNT(*) as count FROM agency_plan_executions WHERE user_id = ? AND status = 'failed'",
            (user_id,)
        ).fetchone()["count"]
        
        if total_executions > 10:
            failure_rate = (failed_executions / total_executions) * 100
            if failure_rate > 20:
                warnings.append({
                    "severity": "warning",
                    "check": "high_execution_failure",
                    "message": f"High execution failure rate: {failure_rate:.1f}% ({failed_executions}/{total_executions})",
                    "rate": failure_rate
                })
        
        # Check 5: Recent activity
        recent_cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
        recent_events = db.execute(
            "SELECT COUNT(*) as count FROM agency_events_log WHERE user_id = ? AND created_at >= ?",
            (user_id, recent_cutoff)
        ).fetchone()["count"]
        
        if recent_events == 0:
            info.append({
                "severity": "info",
                "check": "no_recent_activity",
                "message": "No agency events in the last 24 hours"
            })
        
        # Compile health report
        health_status = "healthy" if not health_issues and not warnings else "degraded" if warnings else "unhealthy"
        
        health_report = {
            "status": health_status,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": health_issues,
            "warnings": warnings,
            "info": info
        }
        
        if json_output:
            console.print_json(data=health_report)
        else:
            # Display formatted health report
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red"
            }[health_status]
            
            console.print(Panel.fit(
                f"[bold {status_color}]System Health: {health_status.upper()}[/bold {status_color}]\n"
                f"User: {user_id}\n"
                f"Checked: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                border_style=status_color
            ))
            
            if health_issues:
                console.print("\n[bold red]Issues:[/bold red]")
                for issue in health_issues:
                    console.print(f"  [red]✗[/red] {issue['message']}")
            
            if warnings:
                console.print("\n[bold yellow]Warnings:[/bold yellow]")
                for warning in warnings:
                    console.print(f"  [yellow]⚠[/yellow] {warning['message']}")
            
            if info:
                console.print("\n[bold blue]Info:[/bold blue]")
                for i in info:
                    console.print(f"  [blue]ℹ[/blue] {i['message']}")
            
            if not health_issues and not warnings and not info:
                console.print("\n[green]✓ All checks passed[/green]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error running health check: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


def _parse_duration(duration_str: str) -> "timedelta":
    """
    Parse duration string like '7d', '30d', '1h', '2w' into timedelta.
    """
    from datetime import timedelta
    
    unit = duration_str[-1]
    value = int(duration_str[:-1])
    
    if unit == 'd':
        return timedelta(days=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    elif unit == 'm':
        return timedelta(minutes=value)
    else:
        raise ValueError(f"Unknown duration unit: {unit}")


# Register proactive conversation subcommand
from .agency_proactive import app as proactive_app
app.add_typer(proactive_app, name="proactive")


# ============================================================================
# LESSON MANAGEMENT COMMANDS
# ============================================================================

lessons_app = typer.Typer(
    help="Manage lessons learned by AICO's reflection system",
    invoke_without_command=True,
    no_args_is_help=False
)


@lessons_app.callback(invoke_without_command=True)
def lessons_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")
):
    """Lesson management commands."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("ls", "List all lessons with filtering"),
            ("show", "View detailed lesson information"),
            ("approve", "Approve a lesson for application"),
            ("reject", "Reject a lesson"),
            ("stats", "Display lesson statistics"),
        ]
        
        format_subcommand_help(
            console=console,
            command_name="agency lessons",
            description="Review and manage lessons learned by AICO's reflection system.",
            subcommands=subcommands
        )
        raise typer.Exit()


@lessons_app.command(name="ls")
def ls(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (active, superseded, rejected)"),
    lesson_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by lesson type"),
    min_confidence: Optional[float] = typer.Option(None, "--min-confidence", help="Minimum confidence score (0.0-1.0)"),
    last: Optional[str] = typer.Option(None, "--last", help="Time window (e.g., 7d, 24h, 30m)"),
    since: Optional[str] = typer.Option(None, "--since", help="Since timestamp (ISO format)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of lessons to show"),
    sort: str = typer.Option("created", "--sort", help="Sort by: created, confidence, applied"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List all lessons with optional filtering.
    
    Examples:
        aico agency lessons list --status active
        aico agency lessons list --type skill_tuning --min-confidence 0.7
        aico agency lessons list --last 7d --limit 20
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Build query
        query = """
            SELECT 
                lesson_id,
                lesson_type,
                target_kind,
                target_id,
                summary_text,
                confidence,
                status,
                applied_at,
                created_at,
                source_reflection_run_id
            FROM agency_lessons
            WHERE user_id = ?
        """
        params = [user_id]
        
        # Add filters
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if lesson_type:
            query += " AND lesson_type = ?"
            params.append(lesson_type)
        
        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)
        
        # Time filtering
        if last:
            since_dt = datetime.now() - _parse_duration(last)
            query += " AND created_at >= ?"
            params.append(since_dt.isoformat())
        elif since:
            query += " AND created_at >= ?"
            params.append(since)
        
        # Sorting
        if sort == "created":
            query += " ORDER BY created_at DESC"
        elif sort == "confidence":
            query += " ORDER BY confidence DESC, created_at DESC"
        elif sort == "applied":
            query += " ORDER BY applied_at DESC NULLS LAST, created_at DESC"
        else:
            query += " ORDER BY created_at DESC"
        
        query += " LIMIT ?"
        params.append(limit)
        
        lessons = db.execute(query, tuple(params)).fetchall()
        
        if not lessons:
            console.print("[yellow]No lessons found matching criteria[/yellow]")
            return
        
        if json_output:
            output = [
                {
                    "lesson_id": l["lesson_id"],
                    "lesson_type": l["lesson_type"],
                    "target_kind": l["target_kind"],
                    "target_id": l["target_id"],
                    "summary": l["summary_text"],
                    "confidence": l["confidence"],
                    "status": l["status"],
                    "applied_at": l["applied_at"],
                    "created_at": l["created_at"],
                    "reflection_run_id": l["source_reflection_run_id"]
                }
                for l in lessons
            ]
            console.print_json(data=output)
        else:
            table = Table(title=f"Lessons for {user_id}", box=box.ROUNDED)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Type", style="blue")
            table.add_column("Target", style="magenta")
            table.add_column("Summary", style="white")
            table.add_column("Confidence", style="yellow")
            table.add_column("Status", style="green")
            table.add_column("Applied", style="dim")
            
            for l in lessons:
                # Truncate summary
                summary = l["summary_text"][:60] + "..." if len(l["summary_text"]) > 60 else l["summary_text"]
                
                # Color code confidence
                conf = l["confidence"]
                conf_color = "green" if conf >= 0.8 else "yellow" if conf >= 0.6 else "red"
                
                # Status color
                status_color = "green" if l["status"] == "active" else "red" if l["status"] == "rejected" else "dim"
                
                # Applied status
                applied = "✓" if l["applied_at"] else "-"
                
                table.add_row(
                    l["lesson_id"][:8],
                    l["lesson_type"],
                    f"{l['target_kind']}",
                    summary,
                    f"[{conf_color}]{conf:.2f}[/{conf_color}]",
                    f"[{status_color}]{l['status']}[/{status_color}]",
                    applied
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(lessons)} lessons[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing lessons: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@lessons_app.command(name="show")
def show(
    lesson_id: str = typer.Argument(..., help="Lesson ID to review"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Display detailed information about a specific lesson.
    
    Shows lesson content, evidence, confidence, application history, and related data.
    
    Example:
        aico agency lessons review abc12345
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Get lesson details
        lesson = db.execute(
            """SELECT * FROM agency_lessons 
               WHERE lesson_id = ? AND user_id = ?""",
            (lesson_id, user_id)
        ).fetchone()
        
        if not lesson:
            console.print(f"[red]✗[/red] Lesson not found: {lesson_id}")
            raise typer.Exit(1)
        
        if json_output:
            output = {
                "lesson_id": lesson["lesson_id"],
                "lesson_type": lesson["lesson_type"],
                "target_kind": lesson["target_kind"],
                "target_id": lesson["target_id"],
                "summary": lesson["summary_text"],
                "proposed_change": json.loads(lesson["proposed_change"]) if lesson["proposed_change"] else None,
                "confidence": lesson["confidence"],
                "metrics_basis": json.loads(lesson["metrics_basis"]) if lesson["metrics_basis"] else None,
                "scope": lesson["scope"],
                "status": lesson["status"],
                "superseded_by": lesson["superseded_by"],
                "applied_at": lesson["applied_at"],
                "applied_by": lesson["applied_by"],
                "source_reflection_run_id": lesson["source_reflection_run_id"],
                "evidence_window": {
                    "start": lesson["evidence_window_start"],
                    "end": lesson["evidence_window_end"]
                },
                "related_goal_ids": json.loads(lesson["related_goal_ids"]) if lesson["related_goal_ids"] else [],
                "related_trajectory_ids": json.loads(lesson["related_trajectory_ids"]) if lesson["related_trajectory_ids"] else [],
                "related_event_ids": json.loads(lesson["related_event_ids"]) if lesson["related_event_ids"] else [],
                "created_at": lesson["created_at"],
                "updated_at": lesson["updated_at"]
            }
            console.print_json(data=output)
        else:
            # Header panel
            header = f"[bold cyan]Lesson {lesson['lesson_id'][:8]}[/bold cyan]\n"
            header += f"Type: {lesson['lesson_type']} | Target: {lesson['target_kind']}"
            if lesson["target_id"]:
                header += f" ({lesson['target_id'][:20]})"
            console.print(Panel(header, box=box.ROUNDED))
            
            # Summary
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(lesson["summary_text"])
            
            # Proposed change
            if lesson["proposed_change"]:
                console.print(f"\n[bold]Proposed Change:[/bold]")
                change = json.loads(lesson["proposed_change"])
                console.print_json(data=change)
            
            # Confidence and metrics
            conf = lesson["confidence"]
            conf_color = "green" if conf >= 0.8 else "yellow" if conf >= 0.6 else "red"
            console.print(f"\n[bold]Confidence:[/bold] [{conf_color}]{conf:.2f}[/{conf_color}]")
            
            if lesson["metrics_basis"]:
                console.print(f"\n[bold]Evidence Metrics:[/bold]")
                metrics = json.loads(lesson["metrics_basis"])
                console.print_json(data=metrics)
            
            # Status and application
            status_color = "green" if lesson["status"] == "active" else "red" if lesson["status"] == "rejected" else "dim"
            console.print(f"\n[bold]Status:[/bold] [{status_color}]{lesson['status']}[/{status_color}]")
            
            if lesson["applied_at"]:
                console.print(f"[bold]Applied:[/bold] {lesson['applied_at'][:19]} by {lesson['applied_by']}")
            else:
                console.print(f"[bold]Applied:[/bold] Not yet applied")
            
            if lesson["superseded_by"]:
                console.print(f"[bold]Superseded by:[/bold] {lesson['superseded_by'][:8]}")
            
            # Provenance
            console.print(f"\n[bold]Provenance:[/bold]")
            console.print(f"  Reflection Run: {lesson['source_reflection_run_id'][:8] if lesson['source_reflection_run_id'] else 'N/A'}")
            console.print(f"  Evidence Window: {lesson['evidence_window_start'][:10] if lesson['evidence_window_start'] else 'N/A'} to {lesson['evidence_window_end'][:10] if lesson['evidence_window_end'] else 'N/A'}")
            console.print(f"  Scope: {lesson['scope']}")
            
            # Related entities
            if lesson["related_goal_ids"]:
                goals = json.loads(lesson["related_goal_ids"])
                console.print(f"\n[bold]Related Goals:[/bold] {len(goals)} goal(s)")
            
            if lesson["related_trajectory_ids"]:
                trajs = json.loads(lesson["related_trajectory_ids"])
                console.print(f"[bold]Related Trajectories:[/bold] {len(trajs)} trajectory(ies)")
            
            # Timestamps
            console.print(f"\n[dim]Created: {lesson['created_at'][:19]}[/dim]")
            console.print(f"[dim]Updated: {lesson['updated_at'][:19]}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error reviewing lesson: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@lessons_app.command(name="approve")
def approve(
    lesson_id: str = typer.Argument(..., help="Lesson ID to approve"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Approval reason"),
):
    """
    Approve a lesson for application.
    
    Marks the lesson as approved and enables automatic application by the LessonApplicator.
    
    Example:
        aico agency lessons approve abc12345 --reason "Good improvement"
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Check if lesson exists
        lesson = db.execute(
            """SELECT lesson_id, status, summary_text FROM agency_lessons 
               WHERE lesson_id = ? AND user_id = ?""",
            (lesson_id, user_id)
        ).fetchone()
        
        if not lesson:
            console.print(f"[red]✗[/red] Lesson not found: {lesson_id}")
            raise typer.Exit(1)
        
        if lesson["status"] == "active":
            console.print(f"[yellow]⚠[/yellow] Lesson is already active")
            return
        
        # Update status to active
        now = datetime.now().isoformat()
        db.execute(
            """UPDATE agency_lessons 
               SET status = 'active', updated_at = ?
               WHERE lesson_id = ?""",
            (now, lesson_id)
        )
        db.commit()
        
        console.print(f"[green]✓[/green] Lesson approved: {lesson_id[:8]}")
        console.print(f"  {lesson['summary_text'][:80]}")
        if reason:
            console.print(f"  Reason: {reason}")
        console.print("\n[dim]The lesson will be automatically applied by the LessonApplicator[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error approving lesson: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@lessons_app.command(name="reject")
def reject(
    lesson_id: str = typer.Argument(..., help="Lesson ID to reject"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Rejection reason"),
):
    """
    Reject a lesson to prevent its application.
    
    Marks the lesson as rejected and prevents future application.
    
    Example:
        aico agency lessons reject abc12345 --reason "Not applicable"
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Check if lesson exists
        lesson = db.execute(
            """SELECT lesson_id, status, summary_text FROM agency_lessons 
               WHERE lesson_id = ? AND user_id = ?""",
            (lesson_id, user_id)
        ).fetchone()
        
        if not lesson:
            console.print(f"[red]✗[/red] Lesson not found: {lesson_id}")
            raise typer.Exit(1)
        
        if lesson["status"] == "rejected":
            console.print(f"[yellow]⚠[/yellow] Lesson is already rejected")
            return
        
        # Update status to rejected
        now = datetime.now().isoformat()
        db.execute(
            """UPDATE agency_lessons 
               SET status = 'rejected', updated_at = ?
               WHERE lesson_id = ?""",
            (now, lesson_id)
        )
        db.commit()
        
        console.print(f"[red]✗[/red] Lesson rejected: {lesson_id[:8]}")
        console.print(f"  {lesson['summary_text'][:80]}")
        if reason:
            console.print(f"  Reason: {reason}")
        console.print("\n[dim]The lesson will not be applied[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error rejecting lesson: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@lessons_app.command(name="stats")
def stats(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (defaults to config user)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Display lesson statistics and analytics.
    
    Shows total lessons by status, type, confidence distribution, and application rates.
    
    Example:
        aico agency lessons stats
    """
    try:
        user_id = get_user_id(user)
        db = get_db_connection()
        
        # Get status breakdown
        status_stats = db.execute(
            """SELECT status, COUNT(*) as count
               FROM agency_lessons
               WHERE user_id = ?
               GROUP BY status""",
            (user_id,)
        ).fetchall()
        
        # Get type breakdown
        type_stats = db.execute(
            """SELECT lesson_type, COUNT(*) as count
               FROM agency_lessons
               WHERE user_id = ?
               GROUP BY lesson_type""",
            (user_id,)
        ).fetchall()
        
        # Get confidence distribution
        confidence_stats = db.execute(
            """SELECT 
                COUNT(*) as total,
                AVG(confidence) as avg_confidence,
                MIN(confidence) as min_confidence,
                MAX(confidence) as max_confidence,
                SUM(CASE WHEN confidence >= 0.8 THEN 1 ELSE 0 END) as high_confidence,
                SUM(CASE WHEN confidence >= 0.6 AND confidence < 0.8 THEN 1 ELSE 0 END) as medium_confidence,
                SUM(CASE WHEN confidence < 0.6 THEN 1 ELSE 0 END) as low_confidence
               FROM agency_lessons
               WHERE user_id = ?""",
            (user_id,)
        ).fetchone()
        
        # Get application stats
        application_stats = db.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN applied_at IS NOT NULL THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN applied_at IS NULL AND status = 'active' THEN 1 ELSE 0 END) as pending_application
               FROM agency_lessons
               WHERE user_id = ?""",
            (user_id,)
        ).fetchone()
        
        if json_output:
            output = {
                "by_status": {row["status"]: row["count"] for row in status_stats},
                "by_type": {row["lesson_type"]: row["count"] for row in type_stats},
                "confidence": {
                    "total": confidence_stats["total"],
                    "average": confidence_stats["avg_confidence"],
                    "min": confidence_stats["min_confidence"],
                    "max": confidence_stats["max_confidence"],
                    "high": confidence_stats["high_confidence"],
                    "medium": confidence_stats["medium_confidence"],
                    "low": confidence_stats["low_confidence"]
                },
                "application": {
                    "total": application_stats["total"],
                    "applied": application_stats["applied"],
                    "pending": application_stats["pending_application"],
                    "application_rate": (application_stats["applied"] / application_stats["total"] * 100) if application_stats["total"] > 0 else 0
                }
            }
            console.print_json(data=output)
        else:
            console.print(Panel(f"[bold cyan]Lesson Statistics for {user_id}[/bold cyan]", box=box.ROUNDED))
            
            # Status breakdown
            console.print("\n[bold]By Status:[/bold]")
            status_table = Table(box=box.SIMPLE)
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Count", style="white")
            for row in status_stats:
                status_color = "green" if row["status"] == "active" else "red" if row["status"] == "rejected" else "dim"
                status_table.add_row(f"[{status_color}]{row['status']}[/{status_color}]", str(row["count"]))
            console.print(status_table)
            
            # Type breakdown
            console.print("\n[bold]By Type:[/bold]")
            type_table = Table(box=box.SIMPLE)
            type_table.add_column("Type", style="blue")
            type_table.add_column("Count", style="white")
            for row in type_stats:
                type_table.add_row(row["lesson_type"], str(row["count"]))
            console.print(type_table)
            
            # Confidence distribution
            console.print("\n[bold]Confidence Distribution:[/bold]")
            conf_table = Table(box=box.SIMPLE)
            conf_table.add_column("Metric", style="yellow")
            conf_table.add_column("Value", style="white")
            conf_table.add_row("Average", f"{confidence_stats['avg_confidence']:.2f}" if confidence_stats['avg_confidence'] else "N/A")
            conf_table.add_row("Range", f"{confidence_stats['min_confidence']:.2f} - {confidence_stats['max_confidence']:.2f}" if confidence_stats['min_confidence'] else "N/A")
            conf_table.add_row("[green]High (≥0.8)[/green]", str(confidence_stats["high_confidence"]))
            conf_table.add_row("[yellow]Medium (0.6-0.8)[/yellow]", str(confidence_stats["medium_confidence"]))
            conf_table.add_row("[red]Low (<0.6)[/red]", str(confidence_stats["low_confidence"]))
            console.print(conf_table)
            
            # Application stats
            console.print("\n[bold]Application Status:[/bold]")
            app_table = Table(box=box.SIMPLE)
            app_table.add_column("Metric", style="magenta")
            app_table.add_column("Value", style="white")
            app_table.add_row("Total Lessons", str(application_stats["total"]))
            app_table.add_row("Applied", str(application_stats["applied"]))
            app_table.add_row("Pending Application", str(application_stats["pending_application"]))
            app_rate = (application_stats["applied"] / application_stats["total"] * 100) if application_stats["total"] > 0 else 0
            app_table.add_row("Application Rate", f"{app_rate:.1f}%")
            console.print(app_table)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error generating lesson statistics: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


# Register lessons subcommand
app.add_typer(lessons_app, name="lessons")

# Register skillgaps subcommand
from .agency_skillgaps import app as skillgaps_app
app.add_typer(skillgaps_app, name="skillgaps")


if __name__ == "__main__":
    app()
