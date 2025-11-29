"""
AICO CLI Emotion Commands

Provides emotional simulation state management and diagnostics.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

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
from aico.core.paths import AICOPaths
from aico.data.libsql.encrypted import EncryptedLibSQLConnection
from aico.security.key_manager import AICOKeyManager

console = Console()

def emotion_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        from cli.utils.help_formatter import format_subcommand_help
        
        subcommands = [
            ("status", "Show current emotional state"),
            ("history", "View emotional state history"),
            ("reset", "Reset to neutral baseline state"),
            ("export", "Export emotional state data"),
            ("stats", "Show emotional statistics"),
        ]
        
        examples = [
            "aico emotion status",
            "aico emotion history --limit 20",
            "aico emotion stats --days 7",
            "aico emotion export --format json",
        ]
        
        format_subcommand_help(
            console=console,
            command_name="emotion",
            description="Emotional simulation state management and diagnostics",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Emotional simulation state management and diagnostics.",
    callback=emotion_callback,
    invoke_without_command=True,
    no_args_is_help=False
)


def _get_db_connection() -> EncryptedLibSQLConnection:
    """Get authenticated database connection with session support"""
    try:
        config = ConfigurationManager()
        key_manager = AICOKeyManager(config)
        db_path = AICOPaths.resolve_database_path("aico.db", "auto")
        
        # Try session-based authentication first
        cached_key = key_manager._get_cached_session()
        if cached_key:
            # Use active session
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
            conn.connect()
            return conn
        
        # Try stored key from keyring
        import keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
            key_manager._cache_session(master_key)  # Cache for future use
            db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
            conn.connect()
            return conn
        
        # Need password
        password = typer.prompt("Enter master password", hide_input=True)
        
        # Reject empty passwords
        if not password or not password.strip():
            console.print("❌ [red]Password cannot be empty[/red]")
            raise typer.Exit(1)
        
        master_key = key_manager.authenticate(password, interactive=False, force_fresh=False)
        db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        conn = EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        conn.connect()
        
        return conn
        
    except Exception as e:
        console.print(f"❌ [red]Error connecting to database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive
def status():
    """
    Show current emotional state.
    
    Displays AICO's current emotional state including feeling label,
    mood dimensions (valence/arousal), and expression parameters.
    """
    try:
        db = _get_db_connection()
        
        # Get current state
        cursor = db.execute(
            "SELECT timestamp, subjective_feeling, mood_valence, mood_arousal, intensity, "
            "warmth, directness, formality, engagement, closeness, care_focus, updated_at "
            "FROM emotion_state WHERE id = 1"
        )
        row = cursor.fetchone()
        
        if not row:
            console.print("ℹ️  [yellow]No emotional state found - system may not have started yet[/yellow]")
            raise typer.Exit(0)
        
        # Parse data
        timestamp = format_timestamp_local(row[0])
        feeling = row[1]
        valence = row[2]
        arousal = row[3]
        intensity = row[4]
        warmth = row[5]
        directness = row[6]
        formality = row[7]
        engagement = row[8]
        closeness = row[9]
        care_focus = row[10]
        updated_at = format_timestamp_local(row[11])
        
        # Determine emoji and color based on feeling
        feeling_map = {
            "neutral": ("😐", "white"),
            "calm": ("😌", "cyan"),
            "warm_concern": ("🤗", "yellow"),
            "protective": ("🛡️", "blue"),
            "curious": ("🤔", "magenta"),
            "playful": ("😄", "green"),
            "melancholic": ("😔", "blue"),
        }
        emoji, color = feeling_map.get(feeling, ("🎭", "white"))
        
        # Create status panel
        status_text = Text()
        status_text.append(f"{emoji} ", style="bold")
        status_text.append(f"{feeling.replace('_', ' ').title()}\n\n", style=f"bold {color}")
        
        status_text.append("Mood Dimensions:\n", style="bold")
        status_text.append(f"  Valence:    {valence:+.2f}  ", style="dim")
        status_text.append(_get_bar(valence, -1, 1) + "\n")
        status_text.append(f"  Arousal:     {arousal:.2f}  ", style="dim")
        status_text.append(_get_bar(arousal, 0, 1) + "\n")
        status_text.append(f"  Intensity:   {intensity:.2f}  ", style="dim")
        status_text.append(_get_bar(intensity, 0, 1) + "\n\n")
        
        status_text.append("Expression Parameters:\n", style="bold")
        status_text.append(f"  Warmth:      {warmth:.2f}  ", style="dim")
        status_text.append(_get_bar(warmth, 0, 1) + "\n")
        status_text.append(f"  Directness:  {directness:.2f}  ", style="dim")
        status_text.append(_get_bar(directness, 0, 1) + "\n")
        status_text.append(f"  Formality:   {formality:.2f}  ", style="dim")
        status_text.append(_get_bar(formality, 0, 1) + "\n")
        status_text.append(f"  Engagement:  {engagement:.2f}  ", style="dim")
        status_text.append(_get_bar(engagement, 0, 1) + "\n")
        status_text.append(f"  Closeness:   {closeness:.2f}  ", style="dim")
        status_text.append(_get_bar(closeness, 0, 1) + "\n")
        status_text.append(f"  Care Focus:  {care_focus:.2f}  ", style="dim")
        status_text.append(_get_bar(care_focus, 0, 1) + "\n\n")
        
        status_text.append(f"State Time:  {timestamp}\n", style="dim")
        status_text.append(f"Updated:     {updated_at}", style="dim")
        
        panel = Panel(
            status_text,
            title="🎭 Current Emotional State",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        console.print(panel)
        
        db.close()
        
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show"),
    feeling: Optional[str] = typer.Option(None, "--feeling", "-f", help="Filter by feeling"),
):
    """
    View emotional state history.
    
    Shows a timeline of AICO's emotional states for mood arc analysis.
    """
    try:
        db = _get_db_connection()
        
        # Build query
        query = "SELECT timestamp, feeling, valence, arousal, intensity FROM emotion_history"
        params = []
        
        if feeling:
            query += " WHERE feeling = ?"
            params.append(feeling)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = db.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        if not rows:
            console.print("ℹ️  [yellow]No emotional history found[/yellow]")
            raise typer.Exit(0)
        
        # Create table
        table = Table(
            title=f"🎭 Emotional State History (last {len(rows)} entries)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Time", style="dim")
        table.add_column("Feeling", style="bold")
        table.add_column("Valence", justify="right")
        table.add_column("Arousal", justify="right")
        table.add_column("Intensity", justify="right")
        table.add_column("Mood", justify="center")
        
        # Add rows (reverse to show chronological order)
        for row in reversed(rows):
            timestamp = format_timestamp_local(row[0])
            feeling_val = row[1]
            valence = row[2]
            arousal = row[3]
            intensity = row[4]
            
            # Determine mood emoji
            if valence > 0.3:
                mood = "😊" if arousal > 0.6 else "😌"
            elif valence < -0.3:
                mood = "😔" if arousal > 0.6 else "😐"
            else:
                mood = "🤔" if arousal > 0.6 else "😐"
            
            # Color feeling based on valence
            if valence > 0.3:
                feeling_style = "green"
            elif valence < -0.3:
                feeling_style = "blue"
            else:
                feeling_style = "white"
            
            table.add_row(
                timestamp,
                Text(feeling_val.replace("_", " ").title(), style=feeling_style),
                f"{valence:+.2f}",
                f"{arousal:.2f}",
                f"{intensity:.2f}",
                mood
            )
        
        console.print(table)
        
        db.close()
        
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive
def reset(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """
    Reset to neutral baseline state.
    
    Resets AICO's emotional state to neutral baseline. History is preserved.
    """
    if not confirm:
        confirmed = typer.confirm("Reset emotional state to neutral baseline?")
        if not confirmed:
            console.print("❌ Reset cancelled")
            raise typer.Exit(0)
    
    try:
        db = _get_db_connection()
        
        # Reset to neutral state
        db.execute(
            """INSERT OR REPLACE INTO emotion_state 
               (id, user_id, timestamp, subjective_feeling, mood_valence, mood_arousal, 
                intensity, warmth, directness, formality, engagement, closeness, care_focus, updated_at)
               VALUES (1, 'system', datetime('now'), 'neutral', 0.0, 0.5, 0.5, 0.6, 0.5, 0.3, 0.6, 0.5, 0.7, datetime('now'))"""
        )
        db.commit()
        
        console.print("✅ [green]Emotional state reset to neutral baseline[/green]")
        
        db.close()
        
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive
def export(
    format: str = typer.Option("json", "--format", "-f", help="Export format (json|csv)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """
    Export emotional state data.
    
    Exports current state and history for analysis or backup.
    """
    try:
        db = _get_db_connection()
        
        # Get current state
        cursor = db.execute(
            "SELECT * FROM emotion_state WHERE id = 1"
        )
        current_state = cursor.fetchone()
        
        # Get history
        cursor = db.execute(
            "SELECT timestamp, feeling, valence, arousal, intensity FROM emotion_history ORDER BY timestamp"
        )
        history = cursor.fetchall()
        
        if format == "json":
            data = {
                "current_state": {
                    "timestamp": current_state[2] if current_state else None,
                    "feeling": current_state[3] if current_state else None,
                    "valence": current_state[4] if current_state else None,
                    "arousal": current_state[5] if current_state else None,
                    "intensity": current_state[6] if current_state else None,
                } if current_state else None,
                "history": [
                    {
                        "timestamp": row[0],
                        "feeling": row[1],
                        "valence": row[2],
                        "arousal": row[3],
                        "intensity": row[4]
                    }
                    for row in history
                ]
            }
            
            output_str = json.dumps(data, indent=2)
        else:
            console.print(f"❌ [red]Unsupported format: {format}[/red]")
            raise typer.Exit(1)
        
        if output:
            output.write_text(output_str)
            console.print(f"✅ [green]Exported to {output}[/green]")
        else:
            console.print(output_str)
        
        db.close()
        
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
@sensitive
def stats(
    days: int = typer.Option(7, "--days", "-d", help="Number of days to analyze"),
):
    """
    Show emotional statistics.
    
    Analyzes emotional patterns over time.
    """
    try:
        db = _get_db_connection()
        
        # Get history for analysis
        cursor = db.execute(
            """SELECT feeling, valence, arousal, intensity 
               FROM emotion_history 
               WHERE timestamp >= datetime('now', '-' || ? || ' days')
               ORDER BY timestamp""",
            (days,)
        )
        rows = cursor.fetchall()
        
        if not rows:
            console.print(f"ℹ️  [yellow]No data for the last {days} days[/yellow]")
            raise typer.Exit(0)
        
        # Calculate statistics
        feelings = {}
        total_valence = 0
        total_arousal = 0
        total_intensity = 0
        
        for row in rows:
            feeling = row[0]
            feelings[feeling] = feelings.get(feeling, 0) + 1
            total_valence += row[1]
            total_arousal += row[2]
            total_intensity += row[3]
        
        count = len(rows)
        avg_valence = total_valence / count
        avg_arousal = total_arousal / count
        avg_intensity = total_intensity / count
        
        # Create stats panel
        stats_text = Text()
        stats_text.append(f"Analysis Period: Last {days} days\n", style="bold")
        stats_text.append(f"Total States: {count}\n\n", style="dim")
        
        stats_text.append("Average Dimensions:\n", style="bold")
        stats_text.append(f"  Valence:   {avg_valence:+.2f}\n", style="dim")
        stats_text.append(f"  Arousal:    {avg_arousal:.2f}\n", style="dim")
        stats_text.append(f"  Intensity:  {avg_intensity:.2f}\n\n", style="dim")
        
        stats_text.append("Feeling Distribution:\n", style="bold")
        for feeling, count_val in sorted(feelings.items(), key=lambda x: x[1], reverse=True):
            percentage = (count_val / count) * 100
            stats_text.append(f"  {feeling.replace('_', ' ').title()}: ", style="dim")
            stats_text.append(f"{count_val} ({percentage:.1f}%)\n")
        
        panel = Panel(
            stats_text,
            title="📊 Emotional Statistics",
            border_style="cyan",
            box=box.ROUNDED
        )
        
        console.print(panel)
        
        db.close()
        
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        raise typer.Exit(1)


def _get_bar(value: float, min_val: float, max_val: float, width: int = 20) -> str:
    """Generate a simple ASCII bar chart"""
    normalized = (value - min_val) / (max_val - min_val)
    filled = int(normalized * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"
