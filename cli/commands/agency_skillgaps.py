"""
AICO CLI Agency Skill Gaps Commands

Provides commands for managing skill gaps identified during plan generation:
- List skill gaps by priority/frequency
- View detailed gap specifications
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
from aico.security import AICOKeyManager
from cli.utils.pg_connection import get_pg_connection

# Import decorators
decorators_path = Path(__file__).parent.parent / "decorators"
sys.path.insert(0, str(decorators_path))
from cli.decorators.sensitive import destructive

console = Console()

app = typer.Typer(
    name="skillgaps",
    help="Manage skill gaps identified during plan generation",
    no_args_is_help=True
)


def get_db_connection():
    """Get PostgreSQL database connection for skill gap operations."""
    try:
        return get_pg_connection()
    except Exception as e:
        console.print(f"[red]✗[/red] Error connecting to database: {e}")
        raise typer.Exit(1)


@app.command("ls")
def list_gaps(
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
        aico agency skillgaps ls --json
    """
    try:
        db = get_db_connection()
        
        query = """
            SELECT gap_id, step_description, frequency_count, 
                   priority_score, llm_suggested_skills,
                   first_seen_at, last_seen_at
            FROM aico_core.agency_skill_gaps
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
        
        rows = db.execute(query).fetchall()
        
        if json_output:
            gaps_json = []
            for row in rows:
                gaps_json.append({
                    "gap_id": row[0],
                    "step_description": row[1],
                    "frequency_count": row[2],
                    "priority_score": row[3],
                    "llm_suggested_skills": json.loads(row[4]) if row[4] else [],
                    "first_seen_at": row[5],
                    "last_seen_at": row[6],
                })
            console.print_json(data={"gaps": gaps_json, "total": len(gaps_json)})
            return
        
        if not rows:
            console.print(f"[dim]No skill gaps found[/dim]")
            return
        
        table = Table(
            title="Skill Gaps",
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
            gap_id, desc, freq, priority, suggested, first_seen, last_seen = row
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
                   suggested_skill_spec, notes, first_seen_at, 
                   last_seen_at, created_at
            FROM aico_core.agency_skill_gaps
            WHERE gap_id = %s
            """,
            (gap_id,)
        ).fetchone()
        
        if not row:
            console.print(f"[red]✗[/red] Skill gap not found: {gap_id}")
            raise typer.Exit(1)
        
        (gap_id, desc, suggested, metadata, freq, priority,
         spec, notes, first_seen, last_seen, created) = row
        
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
        
        if notes:
            console.print(f"\n[bold]Notes:[/bold]")
            console.print(f"  {notes}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error showing skill gap: {e}")
        raise typer.Exit(1)


@app.command("stats")
def show_stats():
    """Show statistics about skill gaps.
    
    Displays aggregate metrics including:
    - Total gaps
    - Most frequent gaps
    - Average priority scores
    - Top suggested skills
    
    Examples:
        aico agency skillgaps stats
    """
    try:
        db = get_db_connection()
        
        total_gaps = db.execute(
            "SELECT COUNT(*) FROM aico_core.agency_skill_gaps"
        ).fetchone()[0]
        
        console.print(Panel(
            f"[bold cyan]Total Skill Gaps: {total_gaps}[/bold cyan]",
            title="Skill Gap Statistics",
            border_style="cyan"
        ))
        
        top_gaps = db.execute(
            """
            SELECT step_description, frequency_count, priority_score
            FROM aico_core.agency_skill_gaps
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
            "SELECT AVG(priority_score) FROM aico_core.agency_skill_gaps"
        ).fetchone()[0]
        
        if avg_priority:
            console.print(f"\n[bold]Average Priority Score:[/bold] {avg_priority:.2f}")
        
        all_suggested = db.execute(
            "SELECT llm_suggested_skills FROM aico_core.agency_skill_gaps"
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


@app.command("clear")
def clear_gaps(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Clear skill gaps from database (DESTRUCTIVE).
    
    Permanently removes skill gap records. Use with caution.
    
    Examples:
        aico agency skillgaps clear
        aico agency skillgaps clear --yes
    """
    try:
        db = get_db_connection()
        
        # Count gaps to be deleted
        count_query = "SELECT COUNT(*) FROM aico_core.agency_skill_gaps"
        count = db.execute(count_query).fetchone()[0]
        
        if count == 0:
            console.print(f"[yellow]No skill gaps found[/yellow]")
            return
        
        # Confirm deletion
        if not confirm:
            console.print(f"[yellow]⚠[/yellow] This will permanently delete {count} skill gap(s)")
            confirm_input = typer.confirm("Are you sure you want to continue?")
            if not confirm_input:
                console.print("[dim]Operation cancelled[/dim]")
                return
        
        # Delete gaps
        db.execute("DELETE FROM aico_core.agency_skill_gaps")
        
        db.commit()
        
        console.print(f"[green]✓[/green] Deleted {count} skill gap(s)")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error clearing skill gaps: {e}")
        raise typer.Exit(1)


@app.command("export")
def export_gaps(
    gap_id: Optional[str] = typer.Option(None, "--gap-id", help="Export single gap by ID"),
    format: str = typer.Option("github", "--format", "-f", help="Export format: github, json, csv"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export skill gaps as GitHub issues or structured data.
    
    Exports skill gaps in various formats for development planning.
    GitHub format creates ready-to-use issue templates.
    
    Examples:
        aico agency skillgaps export
        aico agency skillgaps export --gap-id gap_abc123
        aico agency skillgaps export --format json -o gaps.json
    """
    try:
        db = get_db_connection()
        
        # Fetch gaps
        if gap_id:
            if not gap_id.startswith("gap_"):
                gap_id = f"gap_{gap_id}"
            
            rows = db.execute(
                """
                SELECT gap_id, step_description, llm_suggested_skills,
                       frequency_count, priority_score,
                       suggested_skill_spec, first_seen_at, last_seen_at
                FROM aico_core.agency_skill_gaps
                WHERE gap_id = %s
                """,
                (gap_id,)
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT gap_id, step_description, llm_suggested_skills,
                       frequency_count, priority_score,
                       suggested_skill_spec, first_seen_at, last_seen_at
                FROM aico_core.agency_skill_gaps
                ORDER BY frequency_count DESC, priority_score DESC
                """
            ).fetchall()
        
        if not rows:
            console.print(f"[yellow]No skill gaps found{' with ID ' + gap_id if gap_id else ''}[/yellow]")
            return
        
        # Format output
        if format == "github":
            output_text = _format_github_issues(rows)
        elif format == "json":
            output_text = _format_json(rows)
        elif format == "csv":
            output_text = _format_csv(rows)
        else:
            console.print(f"[red]✗[/red] Invalid format: {format}")
            raise typer.Exit(1)
        
        # Write to file or stdout
        if output:
            output.write_text(output_text)
            console.print(f"[green]✓[/green] Exported {len(rows)} gap(s) to {output}")
        else:
            console.print(output_text)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error exporting skill gaps: {e}")
        raise typer.Exit(1)


def _format_github_issues(rows) -> str:
    """Format skill gaps as GitHub issue templates."""
    issues = []
    
    for row in rows:
        gap_id, desc, suggested, freq, priority, spec, first_seen, last_seen = row
        suggested_skills = json.loads(suggested) if suggested else []
        
        issue = f"""## Skill Gap: {desc}

**Frequency:** {freq} occurrence(s)
**Priority Score:** {priority:.2f}
**Suggested Skills:** {', '.join(suggested_skills) if suggested_skills else 'None'}

### Auto-Generated Specification

{spec if spec else 'No specification available'}

### Context

- **Gap ID:** `{gap_id}`
- **First Seen:** {first_seen[:19] if first_seen else 'N/A'}
- **Last Seen:** {last_seen[:19] if last_seen else 'N/A'}

### Implementation Checklist

- [ ] Design skill interface and parameters
- [ ] Implement skill logic
- [ ] Add tests
- [ ] Register skill in skill registry
- [ ] Update documentation

---
"""
        issues.append(issue)
    
    return "\n".join(issues)


def _format_json(rows) -> str:
    """Format skill gaps as JSON."""
    gaps = []
    
    for row in rows:
        gap_id, desc, suggested, freq, priority, spec, first_seen, last_seen = row
        gaps.append({
            "gap_id": gap_id,
            "description": desc,
            "suggested_skills": json.loads(suggested) if suggested else [],
            "frequency_count": freq,
            "priority_score": priority,
            "specification": spec,
            "first_seen_at": first_seen,
            "last_seen_at": last_seen,
        })
    
    return json.dumps({"skill_gaps": gaps, "total": len(gaps)}, indent=2)


def _format_csv(rows) -> str:
    """Format skill gaps as CSV."""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "gap_id", "description", "suggested_skills", "frequency_count",
        "priority_score", "first_seen_at", "last_seen_at"
    ])
    
    # Data
    for row in rows:
        gap_id, desc, suggested, freq, priority, spec, first_seen, last_seen = row
        suggested_skills = json.loads(suggested) if suggested else []
        writer.writerow([
            gap_id, desc, ",".join(suggested_skills), freq,
            priority, first_seen, last_seen
        ])
    
    return output.getvalue()
