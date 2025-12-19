"""
AICO CLI Agency Skill Gaps Commands

Provides commands for managing skill gaps identified during plan generation:
- List skill gaps by priority/frequency
- View detailed gap specifications
- Mark gaps as resolved when skills are implemented
- Export gaps for development planning
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

from rich.console import Console

if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.data.libsql import EncryptedLibSQLConnection
from aico.security import AICOKeyManager

console = Console()

app = typer.Typer(
    name="skillgaps",
    help="Manage skill gaps identified during plan generation",
    no_args_is_help=True
)


def get_db_connection():
    """Get database connection for skill gap operations."""
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
        
        cached_key = key_manager._get_cached_session()
        if cached_key:
            key_manager._extend_session()
            db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
            return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
        import keyring
        stored_key = keyring.get_password(key_manager.service_name, "master_key")
        if stored_key:
            master_key = bytes.fromhex(stored_key)
            key_manager._cache_session(master_key)
            db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
            return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
        
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


@app.command("ls")
def list_gaps(
    status: Optional[str] = typer.Option("identified", "--status", "-s", help="Filter by status (identified, planned, in_progress, resolved)"),
    sort_by: str = typer.Option("frequency", "--sort", help="Sort by: frequency, priority, recent"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of gaps to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List skill gaps identified during plan generation.
    
    Shows gaps sorted by frequency (how often they occur) or priority score.
    Helps developers identify which skills to implement first.
    
    Examples:
        aico agency skillgaps ls
        aico agency skillgaps ls --sort priority --limit 10
        aico agency skillgaps ls --status identified --json
    """
    try:
        db = get_db_connection()
        
        query = """
            SELECT gap_id, step_description, frequency_count, 
                   priority_score, status, llm_suggested_skills,
                   first_seen_at, last_seen_at
            FROM agency_skill_gaps
            WHERE status = ?
        """
        
        if sort_by == "frequency":
            query += " ORDER BY frequency_count DESC, priority_score DESC"
        elif sort_by == "priority":
            query += " ORDER BY priority_score DESC, frequency_count DESC"
        elif sort_by == "recent":
            query += " ORDER BY last_seen_at DESC"
        else:
            console.print(f"[red]✗[/red] Invalid sort option: {sort_by}")
            raise typer.Exit(1)
        
        query += f" LIMIT {limit}"
        
        rows = db.execute(query, (status,)).fetchall()
        
        if json_output:
            gaps_json = []
            for row in rows:
                gaps_json.append({
                    "gap_id": row[0],
                    "step_description": row[1],
                    "frequency_count": row[2],
                    "priority_score": row[3],
                    "status": row[4],
                    "llm_suggested_skills": json.loads(row[5]) if row[5] else [],
                    "first_seen_at": row[6],
                    "last_seen_at": row[7],
                })
            console.print_json(data={"gaps": gaps_json, "total": len(gaps_json)})
            return
        
        if not rows:
            console.print(f"[yellow]No skill gaps found with status '{status}'[/yellow]")
            return
        
        table = Table(
            title=f"Skill Gaps ({status})",
            box=box.SIMPLE_HEAD,
            title_justify="left",
            header_style="bold cyan",
        )
        table.add_column("ID", style="dim", max_width=12, no_wrap=True)
        table.add_column("Description", style="white", max_width=50)
        table.add_column("Freq", style="yellow", justify="right")
        table.add_column("Priority", style="magenta", justify="right")
        table.add_column("Suggested Skills", style="cyan", max_width=25)
        table.add_column("Last Seen", style="green")
        
        for row in rows:
            gap_id, desc, freq, priority, status_val, suggested, first_seen, last_seen = row
            short_id = gap_id.replace("gap_", "")[:10]
            
            suggested_skills = json.loads(suggested) if suggested else []
            skills_str = ", ".join(suggested_skills[:2])
            if len(suggested_skills) > 2:
                skills_str += f" +{len(suggested_skills)-2}"
            
            last_seen_str = last_seen[:10] if last_seen else ""
            
            table.add_row(
                short_id,
                desc[:50] + "..." if len(desc) > 50 else desc,
                str(freq),
                f"{priority:.2f}" if priority else "0.00",
                skills_str or "[dim]none[/dim]",
                last_seen_str,
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(rows)} gap(s) | Sorted by: {sort_by}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing skill gaps: {e}")
        raise typer.Exit(1)


@app.command("show")
def show_gap(
    gap_id: str = typer.Argument(..., help="Gap ID to show details for"),
):
    """Show detailed information about a specific skill gap.
    
    Displays the full specification including suggested skills, metadata,
    and auto-generated implementation requirements.
    
    Examples:
        aico agency skillgaps show gap_abc123
        aico agency skillgaps show f6ac018c8f
    """
    try:
        db = get_db_connection()
        
        if not gap_id.startswith("gap_"):
            gap_id = f"gap_{gap_id}"
        
        row = db.execute(
            """
            SELECT gap_id, step_description, llm_suggested_skills,
                   step_metadata, frequency_count, priority_score,
                   status, suggested_skill_spec, resolved_skill_id,
                   notes, first_seen_at, last_seen_at, created_at
            FROM agency_skill_gaps
            WHERE gap_id = ?
            """,
            (gap_id,)
        ).fetchone()
        
        if not row:
            console.print(f"[red]✗[/red] Skill gap not found: {gap_id}")
            raise typer.Exit(1)
        
        (gap_id, desc, suggested, metadata, freq, priority, status,
         spec, resolved_id, notes, first_seen, last_seen, created) = row
        
        suggested_skills = json.loads(suggested) if suggested else []
        step_meta = json.loads(metadata) if metadata else {}
        
        console.print(Panel(
            f"[bold cyan]{gap_id}[/bold cyan]",
            title="Skill Gap Details",
            border_style="cyan"
        ))
        
        console.print(f"\n[bold]Description:[/bold]")
        console.print(f"  {desc}")
        
        console.print(f"\n[bold]Metrics:[/bold]")
        console.print(f"  Frequency: [yellow]{freq}[/yellow] occurrence(s)")
        console.print(f"  Priority:  [magenta]{priority:.2f}[/magenta]")
        console.print(f"  Status:    [cyan]{status}[/cyan]")
        
        if suggested_skills:
            console.print(f"\n[bold]LLM Suggested Skills:[/bold]")
            for skill in suggested_skills:
                console.print(f"  • {skill}")
        
        if spec:
            console.print(f"\n[bold]Auto-Generated Specification:[/bold]")
            console.print(Panel(spec, border_style="dim"))
        
        if step_meta:
            console.print(f"\n[bold]Context Metadata:[/bold]")
            if "goal_id" in step_meta:
                console.print(f"  Goal ID: {step_meta['goal_id']}")
            if "plan_id" in step_meta:
                console.print(f"  Plan ID: {step_meta['plan_id']}")
        
        console.print(f"\n[bold]Timeline:[/bold]")
        console.print(f"  First seen: {first_seen[:19] if first_seen else 'N/A'}")
        console.print(f"  Last seen:  {last_seen[:19] if last_seen else 'N/A'}")
        
        if resolved_id:
            console.print(f"\n[bold green]✓ Resolved by skill:[/bold green] {resolved_id}")
        
        if notes:
            console.print(f"\n[bold]Notes:[/bold]")
            console.print(f"  {notes}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error showing skill gap: {e}")
        raise typer.Exit(1)


@app.command("resolve")
def resolve_gap(
    gap_id: str = typer.Argument(..., help="Gap ID to mark as resolved"),
    skill_id: str = typer.Option(..., "--skill", "-s", help="Skill ID that resolves this gap"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Optional notes about the resolution"),
):
    """Mark a skill gap as resolved.
    
    Updates the gap status to 'resolved' and records which skill was implemented
    to address it. This helps track which gaps have been addressed.
    
    Examples:
        aico agency skillgaps resolve gap_abc123 --skill find_local_communities
        aico agency skillgaps resolve f6ac018c8f -s web_search --notes "Implemented with DuckDuckGo API"
    """
    try:
        db = get_db_connection()
        
        if not gap_id.startswith("gap_"):
            gap_id = f"gap_{gap_id}"
        
        existing = db.execute(
            "SELECT gap_id, status FROM agency_skill_gaps WHERE gap_id = ?",
            (gap_id,)
        ).fetchone()
        
        if not existing:
            console.print(f"[red]✗[/red] Skill gap not found: {gap_id}")
            raise typer.Exit(1)
        
        if existing[1] == "resolved":
            console.print(f"[yellow]⚠[/yellow] Gap {gap_id} is already resolved")
            return
        
        now = datetime.utcnow().isoformat()
        
        db.execute(
            """
            UPDATE agency_skill_gaps
            SET status = 'resolved',
                resolved_skill_id = ?,
                notes = ?,
                updated_at = ?
            WHERE gap_id = ?
            """,
            (skill_id, notes, now, gap_id)
        )
        
        console.print(f"[green]✓[/green] Marked gap {gap_id} as resolved")
        console.print(f"  Resolved by: [cyan]{skill_id}[/cyan]")
        if notes:
            console.print(f"  Notes: {notes}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error resolving skill gap: {e}")
        raise typer.Exit(1)


@app.command("stats")
def show_stats():
    """Show statistics about skill gaps.
    
    Displays aggregate metrics including:
    - Total gaps by status
    - Most frequent gaps
    - Average priority scores
    - Top suggested skills
    
    Examples:
        aico agency skillgaps stats
    """
    try:
        db = get_db_connection()
        
        status_counts = db.execute(
            """
            SELECT status, COUNT(*) as count
            FROM agency_skill_gaps
            GROUP BY status
            ORDER BY count DESC
            """
        ).fetchall()
        
        total_gaps = sum(row[1] for row in status_counts)
        
        console.print(Panel(
            f"[bold cyan]Total Skill Gaps: {total_gaps}[/bold cyan]",
            title="Skill Gap Statistics",
            border_style="cyan"
        ))
        
        if status_counts:
            console.print("\n[bold]Gaps by Status:[/bold]")
            for status, count in status_counts:
                console.print(f"  {status:15} {count:3} gap(s)")
        
        top_gaps = db.execute(
            """
            SELECT step_description, frequency_count, priority_score
            FROM agency_skill_gaps
            WHERE status = 'identified'
            ORDER BY frequency_count DESC, priority_score DESC
            LIMIT 5
            """
        ).fetchall()
        
        if top_gaps:
            console.print("\n[bold]Top 5 Most Frequent Gaps:[/bold]")
            for desc, freq, priority in top_gaps:
                short_desc = desc[:60] + "..." if len(desc) > 60 else desc
                console.print(f"  [{freq}x] {short_desc}")
        
        avg_priority = db.execute(
            "SELECT AVG(priority_score) FROM agency_skill_gaps WHERE status = 'identified'"
        ).fetchone()[0]
        
        if avg_priority:
            console.print(f"\n[bold]Average Priority Score:[/bold] {avg_priority:.2f}")
        
        all_suggested = db.execute(
            "SELECT llm_suggested_skills FROM agency_skill_gaps WHERE llm_suggested_skills IS NOT NULL"
        ).fetchall()
        
        skill_counts = {}
        for row in all_suggested:
            skills = json.loads(row[0]) if row[0] else []
            for skill in skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        if skill_counts:
            console.print("\n[bold]Most Suggested Skills:[/bold]")
            sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for skill, count in sorted_skills:
                console.print(f"  {skill:20} {count:3} time(s)")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error showing statistics: {e}")
        raise typer.Exit(1)
