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

def agency_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("intentions", "View active intention set for a user"),
            ("profile", "View or edit user value profile"),
            ("policies", "List, add, or remove policy rules"),
            ("consent", "Grant or revoke consent for specific actions"),
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


def get_user_id(user: Optional[str] = None) -> str:
    """Get user ID from argument or config."""
    if user:
        return user
    
    # Try to get from config
    config = ConfigurationManager()
    user_id = config.get("core.user.id")
    
    if not user_id:
        console.print("[red]✗[/red] No user ID specified. Use --user or set core.user.id in config.")
        raise typer.Exit(1)
    
    return user_id


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
                        "goal_id": scored.goal.goal_id,
                        "title": scored.goal.title,
                        "origin": scored.goal.origin.value,
                        "priority": scored.goal.priority.value,
                        "status": scored.goal.status.value,
                        "score": scored.score,
                        "priority_band": scored.priority_band,
                        "score_breakdown": scored.score_breakdown,
                    }
                    for scored in intention_set.intentions
                ]
            }
            console.print_json(data=output)
        else:
            # Rich table output
            if not intention_set.intentions:
                console.print(f"[yellow]No active intentions for user {user_id}[/yellow]")
                return
            
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
            
            for scored in intention_set.intentions:
                goal = scored.goal
                
                # Color code priority band
                band_color = {
                    "critical": "red",
                    "high": "yellow",
                    "normal": "green",
                    "low": "blue"
                }.get(scored.priority_band, "white")
                
                table.add_row(
                    goal.title,
                    goal.origin.value,
                    goal.priority.value,
                    f"{scored.score:.3f}",
                    f"[{band_color}]{scored.priority_band}[/{band_color}]",
                    goal.status.value
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
                UPDATE value_profiles 
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
        query = "SELECT * FROM policy_rules"
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
                INSERT INTO consents (consent_id, user_id, scope, decision, granted_at)
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
                "UPDATE consents SET decision = ?, updated_at = ? WHERE consent_id = ? AND user_id = ?",
                ("denied", datetime.utcnow().isoformat(), revoke, user_id)
            )
            db.commit()
            console.print(f"[green]✓[/green] Consent revoked: {revoke}")
            return
        
        # List consents
        cursor = db.execute(
            "SELECT * FROM consents WHERE user_id = ? ORDER BY granted_at DESC",
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


if __name__ == "__main__":
    app()
