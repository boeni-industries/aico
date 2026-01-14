"""
AICO CLI Agency Proactive Conversation Commands

Provides commands for managing proactive conversation initiations:
- List pending/historical initiations
- View detailed initiation information
- Respond to initiations
- View learning statistics
- Manage user preferences
- Test initiation system
"""

import typer
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.console import Console
from pathlib import Path
import sys
import json
from datetime import datetime
from typing import Optional

# Add shared module to path
if getattr(sys, 'frozen', False):
    shared_path = Path(sys._MEIPASS) / 'shared'
else:
    shared_path = Path(__file__).parent.parent.parent / "shared"

sys.path.insert(0, str(shared_path))

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths
from aico.security import AICOKeyManager
from cli.utils.pg_connection import get_pg_connection

console = Console()

app = typer.Typer(
    name="proactive",
    help="Manage proactive conversation initiations"
)


def get_db_connection():
    """Get PostgreSQL database connection for proactive operations."""
    try:
        return get_pg_connection()
    except Exception as e:
        console.print(f"[red]✗[/red] Error connecting to database: {e}")
        raise typer.Exit(1)


def get_current_user_id(db) -> str:
    """Get current user ID from database."""
    cursor = db.cursor()
    cursor.execute("SELECT uuid FROM aico_core.user_profiles WHERE is_active = true LIMIT 1")
    user = cursor.fetchone()
    if not user:
        console.print("[red]✗[/red] No active user found")
        raise typer.Exit(1)
    return user['uuid']


@app.command("ls")
def list_initiations(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status: pending, answered, dismissed"),
    since: Optional[str] = typer.Option(None, "--since", help="Filter by date (YYYY-MM-DD)"),
    until: Optional[str] = typer.Option(None, "--until", help="Filter by date (YYYY-MM-DD)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of results to show"),
    show_stats: bool = typer.Option(False, "--stats", help="Show learning statistics")
):
    """List proactive conversation initiations.
    
    Examples:
        aico agency proactive ls
        aico agency proactive ls --status pending
        aico agency proactive ls --since 2025-12-01 --limit 50
        aico agency proactive ls --stats
    """
    try:
        db = get_db_connection()
        user_id = get_current_user_id(db)
        
        # Build query
        query = """
            SELECT initiation_id, conversation_id, question, 
                   initiated_at, resolution_status, resolved_at,
                   user_response_time, engagement_score, trigger_reason
            FROM conversation_initiations
            WHERE user_id = %s
        """
        params = [user_id]
        
        if status:
            query += " AND resolution_status = %s"
            params.append(status)
        
        if since:
            query += " AND initiated_at >= %s"
            params.append(since)
        
        if until:
            query += " AND initiated_at <= %s"
            params.append(until)
        
        query += " ORDER BY initiated_at DESC LIMIT %s"
        params.append(limit)
        
        cursor = db.execute(query, tuple(params))
        initiations = cursor.fetchall()
        
        if not initiations:
            console.print("[yellow]No initiations found[/yellow]")
            return
        
        # Display table
        table = Table(
            title=f"🗣️ Proactive Conversation Initiations ({len(initiations)})",
            box=box.SIMPLE_HEAD,
            title_justify="left"
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Question", style="white")
        table.add_column("Status", style="green")
        table.add_column("Initiated", style="dim")
        table.add_column("Response Time", justify="right")
        
        for init in initiations:
            response_time = ""
            if init['user_response_time']:
                minutes = init['user_response_time'] // 60
                if minutes < 60:
                    response_time = f"{minutes}m"
                else:
                    hours = minutes // 60
                    response_time = f"{hours}h"
            
            status_color = {
                'pending': '[yellow]pending[/yellow]',
                'answered': '[green]answered[/green]',
                'dismissed': '[red]dismissed[/red]',
                'deferred': '[blue]deferred[/blue]'
            }.get(init['resolution_status'], init['resolution_status'])
            
            table.add_row(
                init['initiation_id'][:8],
                init['question'][:60] + "..." if len(init['question']) > 60 else init['question'],
                status_color,
                init['initiated_at'][:16] if init['initiated_at'] else "",
                response_time
            )
        
        console.print()
        console.print(table)
        console.print()
        
        if show_stats:
            # Show statistics
            stats_query = """
                SELECT 
                    resolution_status,
                    COUNT(*) as count,
                    AVG(user_response_time) as avg_response_time,
                    AVG(engagement_score) as avg_engagement
                FROM conversation_initiations
                WHERE user_id = %s
                GROUP BY resolution_status
            """
            cursor = db.execute(stats_query, (user_id,))
            stats = cursor.fetchall()
            
            stats_table = Table(title="📊 Statistics", box=box.SIMPLE)
            stats_table.add_column("Status", style="cyan")
            stats_table.add_column("Count", justify="right")
            stats_table.add_column("Avg Response Time", justify="right")
            stats_table.add_column("Avg Engagement", justify="right")
            
            for stat in stats:
                avg_time = ""
                if stat['avg_response_time']:
                    minutes = int(stat['avg_response_time'] // 60)
                    avg_time = f"{minutes}m"
                
                avg_eng = ""
                if stat['avg_engagement']:
                    avg_eng = f"{stat['avg_engagement']:.2f}"
                
                stats_table.add_row(
                    stat['resolution_status'],
                    str(stat['count']),
                    avg_time,
                    avg_eng
                )
            
            console.print(stats_table)
            console.print()
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)


@app.command("cat")
def show_initiation(
    initiation_id: str = typer.Argument(..., help="Initiation ID to show")
):
    """Show detailed information about a specific initiation.
    
    Examples:
        aico agency proactive cat abc12345
    """
    try:
        db = get_db_connection()
        user_id = get_current_user_id(db)
        
        cursor = db.execute("""
            SELECT initiation_id, user_id, conversation_id, question,
                   context, urgency, expected_answer_type,
                   trigger_source, trigger_reason,
                   initiated_at, resolution_status, resolved_at,
                   user_response_time, engagement_score, created_at, updated_at
            FROM conversation_initiations
            WHERE initiation_id LIKE ? AND user_id = %s
        """, (f"{initiation_id}%", user_id))
        
        init = cursor.fetchone()
        
        if not init:
            console.print(f"[red]✗[/red] Initiation not found: {initiation_id}")
            raise typer.Exit(1)
        
        # Display details
        console.print()
        console.print(Panel(
            f"[bold cyan]Initiation Details[/bold cyan]\n\n"
            f"[bold]ID:[/bold] {init['initiation_id']}\n"
            f"[bold]Conversation ID:[/bold] {init['conversation_id']}\n"
            f"[bold]Status:[/bold] {init['resolution_status']}\n\n"
            f"[bold]Question:[/bold]\n{init['question']}\n\n"
            f"[bold]Context:[/bold]\n{init['context'] or 'N/A'}\n\n"
            f"[bold]Trigger:[/bold] {init['trigger_source']} - {init['trigger_reason']}\n"
            f"[bold]Urgency:[/bold] {init['urgency']}\n"
            f"[bold]Expected Answer:[/bold] {init['expected_answer_type']}\n\n"
            f"[bold]Initiated:[/bold] {init['initiated_at']}\n"
            f"[bold]Resolved:[/bold] {init['resolved_at'] or 'Not yet'}\n"
            f"[bold]Response Time:[/bold] {init['user_response_time']}s" if init['user_response_time'] else "N/A" + "\n"
            f"[bold]Engagement Score:[/bold] {init['engagement_score']}" if init['engagement_score'] else "N/A",
            border_style="cyan",
            padding=(1, 2)
        ))
        console.print()
        
        # Show learning impact if resolved
        if init['resolution_status'] in ['answered', 'dismissed'] and 'strategy_' in init['trigger_reason']:
            strategy_id = init['trigger_reason'].split('strategy_')[1]
            
            from aico.ai.agency.skills.communication.learning import ContextualBanditLearner
            bandit = ContextualBanditLearner(db)
            
            if strategy_id in bandit.arms:
                arm = bandit.arms[strategy_id]
                console.print(f"[bold cyan]Learning Impact for Strategy '{strategy_id}':[/bold cyan]")
                console.print(f"  Alpha (successes): {arm.alpha:.1f}")
                console.print(f"  Beta (failures): {arm.beta:.1f}")
                console.print(f"  Expected Reward: {arm.alpha / (arm.alpha + arm.beta):.3f}")
                console.print(f"  Total Trials: {int(arm.alpha + arm.beta - 2)}")
                console.print()
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)


@app.command("respond")
def respond_to_initiation(
    initiation_id: str = typer.Argument(..., help="Initiation ID to respond to"),
    response_type: str = typer.Option(..., "--type", "-t", help="Response type: answered, dismissed, deferred"),
    engagement: Optional[float] = typer.Option(None, "--engagement", "-e", help="Engagement score (0.0-1.0)")
):
    """Record a response to a proactive initiation.
    
    Examples:
        aico agency proactive respond abc12345 --type answered --engagement 0.8
        aico agency proactive respond abc12345 --type dismissed
    """
    try:
        if response_type not in ['answered', 'dismissed', 'deferred']:
            console.print("[red]✗[/red] Invalid response type. Must be: answered, dismissed, or deferred")
            raise typer.Exit(1)
        
        if engagement is not None and (engagement < 0.0 or engagement > 1.0):
            console.print("[red]✗[/red] Engagement score must be between 0.0 and 1.0")
            raise typer.Exit(1)
        
        db = get_db_connection()
        user_id = get_current_user_id(db)
        
        # Verify initiation exists
        cursor = db.execute("""
            SELECT initiation_id, resolution_status, initiated_at, trigger_reason
            FROM conversation_initiations
            WHERE initiation_id LIKE ? AND user_id = %s
        """, (f"{initiation_id}%", user_id))
        
        init = cursor.fetchone()
        
        if not init:
            console.print(f"[red]✗[/red] Initiation not found: {initiation_id}")
            raise typer.Exit(1)
        
        if init['resolution_status'] != 'pending':
            console.print(f"[yellow]⚠[/yellow] Initiation already {init['resolution_status']}")
            raise typer.Exit(1)
        
        # Calculate response time
        initiated_at = datetime.fromisoformat(init['initiated_at'])
        resolved_at = datetime.utcnow()
        response_time = int((resolved_at - initiated_at).total_seconds())
        
        # Update initiation
        db.execute("""
            UPDATE conversation_initiations
            SET resolution_status = ?,
                resolved_at = ?,
                user_response_time = ?,
                engagement_score = ?,
                updated_at = %s
            WHERE initiation_id = %s
        """, (
            response_type,
            resolved_at.isoformat(),
            response_time,
            engagement,
            resolved_at.isoformat(),
            init['initiation_id']
        ))
        db.commit()
        
        console.print(f"[green]✓[/green] Response recorded: {response_type}")
        console.print(f"  Response time: {response_time}s ({response_time // 60}m)")
        if engagement:
            console.print(f"  Engagement: {engagement:.2f}")
        
        # Update learning system
        if 'strategy_' in init['trigger_reason']:
            strategy_id = init['trigger_reason'].split('strategy_')[1]
            
            from aico.ai.agency.skills.communication.learning import (
                ContextualBanditLearner,
                extract_contextual_features
            )
            
            context = extract_contextual_features(db, user_id)
            bandit = ContextualBanditLearner(db)
            
            bandit.update_from_outcome(
                strategy_id=strategy_id,
                context=context,
                outcome=response_type,
                response_time=float(response_time) if response_type == 'answered' else None
            )
            
            console.print(f"[green]✓[/green] Learning system updated for strategy '{strategy_id}'")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)


@app.command("stats")
def show_statistics():
    """Display learning statistics and bandit arm performance.
    
    Examples:
        aico agency proactive stats
    """
    try:
        db = get_db_connection()
        user_id = get_current_user_id(db)
        
        from aico.ai.agency.skills.communication.learning import ContextualBanditLearner
        
        bandit = ContextualBanditLearner(db)
        stats = bandit.get_arm_statistics()
        
        # Sort by expected reward
        sorted_stats = sorted(
            stats.items(),
            key=lambda x: x[1]['expected_reward'],
            reverse=True
        )
        
        console.print()
        console.print("[bold cyan]🎓 Learning Statistics - Bandit Arm Performance[/bold cyan]")
        console.print()
        
        table = Table(box=box.SIMPLE_HEAD)
        table.add_column("Strategy", style="cyan")
        table.add_column("Expected Reward", justify="right", style="green")
        table.add_column("Trials", justify="right")
        table.add_column("Alpha (α)", justify="right")
        table.add_column("Beta (β)", justify="right")
        table.add_column("Confidence", justify="right")
        
        for arm_id, arm_stats in sorted_stats:
            confidence = arm_stats['confidence']
            conf_color = "green" if confidence > 0.8 else "yellow" if confidence > 0.5 else "red"
            
            table.add_row(
                arm_id,
                f"{arm_stats['expected_reward']:.3f}",
                str(int(arm_stats['trials'])),
                f"{arm_stats['alpha']:.1f}",
                f"{arm_stats['beta']:.1f}",
                f"[{conf_color}]{confidence:.2f}[/{conf_color}]"
            )
        
        console.print(table)
        console.print()
        
        # Overall statistics
        total_trials = sum(int(s['trials']) for s in stats.values())
        avg_reward = sum(s['expected_reward'] for s in stats.values()) / len(stats)
        
        console.print(f"[bold]Total Trials:[/bold] {total_trials}")
        console.print(f"[bold]Average Expected Reward:[/bold] {avg_reward:.3f}")
        console.print(f"[bold]Number of Strategies:[/bold] {len(stats)}")
        console.print()
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)


@app.command("preferences")
def manage_preferences(
    show: bool = typer.Option(False, "--show", help="Show current preferences"),
    enable: bool = typer.Option(False, "--enable", help="Enable proactive conversations"),
    disable: bool = typer.Option(False, "--disable", help="Disable proactive conversations"),
    quiet_hours: Optional[str] = typer.Option(None, "--quiet-hours", help="Set quiet hours (e.g., '22-7')"),
    max_per_day: Optional[int] = typer.Option(None, "--max-per-day", help="Max initiations per day")
):
    """View or update user preferences for proactive conversations.
    
    Examples:
        aico agency proactive preferences --show
        aico agency proactive preferences --enable
        aico agency proactive preferences --quiet-hours 22-7
        aico agency proactive preferences --max-per-day 5
    """
    try:
        db = get_db_connection()
        user_id = get_current_user_id(db)
        
        from aico.ai.agency.skills.communication.user_preferences import UserPreferencesManager
        
        prefs_manager = UserPreferencesManager(db)
        prefs = prefs_manager.get_preferences(user_id)
        
        if show or not any([enable, disable, quiet_hours, max_per_day]):
            # Show current preferences
            console.print()
            console.print(Panel(
                f"[bold cyan]User Preferences[/bold cyan]\n\n"
                f"[bold]Enabled:[/bold] {'Yes' if prefs['enabled'] else 'No'}\n"
                f"[bold]Quiet Hours:[/bold] {prefs['quiet_hours'] or 'None'}\n"
                f"[bold]Max Per Day:[/bold] {prefs['max_initiations_per_day']}\n"
                f"[bold]Max Pending:[/bold] {prefs['max_pending']}\n"
                f"[bold]Min Hours Between:[/bold] {prefs['min_hours_between']}\n"
                f"[bold]Preferred Times:[/bold] {prefs['preferred_times'] or 'None'}",
                border_style="cyan",
                padding=(1, 2)
            ))
            console.print()
            console.print("[dim]Note: Preference updates via CLI not yet implemented in database.[/dim]")
            console.print("[dim]These are current defaults. Use API to persist changes.[/dim]")
            console.print()
            return
        
        # Update preferences (note: this would need database schema update)
        console.print("[yellow]⚠[/yellow] Preference updates not yet persisted to database")
        console.print("[yellow]⚠[/yellow] This feature requires database schema extension")
        
        if enable:
            console.print("[green]✓[/green] Would enable proactive conversations")
        if disable:
            console.print("[green]✓[/green] Would disable proactive conversations")
        if quiet_hours:
            console.print(f"[green]✓[/green] Would set quiet hours to: {quiet_hours}")
        if max_per_day:
            console.print(f"[green]✓[/green] Would set max per day to: {max_per_day}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)


@app.command("test")
def test_initiation(
    strategy: Optional[str] = typer.Option(None, "--strategy", "-s", help="Force specific strategy"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show decision without creating initiation")
):
    """Trigger a test proactive initiation for the current user.
    
    Examples:
        aico agency proactive test --dry-run
        aico agency proactive test --strategy time_morning
    """
    try:
        db = get_db_connection()
        user_id = get_current_user_id(db)
        
        from aico.ai.agency.skills.communication.learning import (
            ContextualBanditLearner,
            AdaptivityScorer,
            CivilityScorer,
            extract_contextual_features
        )
        from aico.ai.agency.skills.communication.user_preferences import load_user_preferences
        
        console.print()
        console.print("[bold cyan]🧪 Testing Proactive Conversation System[/bold cyan]")
        console.print()
        
        # Extract context
        context = extract_contextual_features(db, user_id)
        console.print(f"[bold]User Context:[/bold]")
        console.print(f"  Hour of day: {context.hour_of_day}")
        console.print(f"  Day of week: {context.day_of_week}")
        console.print(f"  Time since last interaction: {context.time_since_last_interaction:.1f}h")
        console.print(f"  Recent response rate: {context.recent_response_rate:.2f}")
        console.print(f"  Activity level: {context.user_activity_level}")
        console.print()
        
        # Score dimensions
        adaptivity_scorer = AdaptivityScorer()
        civility_scorer = CivilityScorer()
        user_prefs = load_user_preferences(db, user_id)
        
        patience = adaptivity_scorer.calculate_patience_score(context, context.time_since_last_interaction)
        timing = adaptivity_scorer.calculate_timing_sensitivity(context)
        adaptivity = (patience + timing) / 2
        
        boundary = civility_scorer.calculate_boundary_respect(context, user_prefs)
        emotional = civility_scorer.calculate_emotional_intelligence(context, "test")
        civility = (boundary + emotional) / 2
        
        overall = adaptivity * 0.6 + civility * 0.4
        
        console.print(f"[bold]Scores:[/bold]")
        console.print(f"  Adaptivity: {adaptivity:.3f} (patience={patience:.3f}, timing={timing:.3f})")
        console.print(f"  Civility: {civility:.3f} (boundary={boundary:.3f}, emotional={emotional:.3f})")
        console.print(f"  Overall: {overall:.3f}")
        console.print()
        
        # Select strategy
        bandit = ContextualBanditLearner(db)
        
        if strategy:
            if strategy not in bandit.arms:
                console.print(f"[red]✗[/red] Unknown strategy: {strategy}")
                console.print(f"Available: {', '.join(bandit.arms.keys())}")
                raise typer.Exit(1)
            strategy_id = strategy
            expected_reward = bandit.arms[strategy].alpha / (bandit.arms[strategy].alpha + bandit.arms[strategy].beta)
        else:
            strategy_id, expected_reward = bandit.select_strategy(context)
        
        console.print(f"[bold]Selected Strategy:[/bold] {strategy_id}")
        console.print(f"[bold]Expected Reward:[/bold] {expected_reward:.3f}")
        console.print()
        
        # Decision
        threshold = 0.5
        reward_threshold = 0.3
        should_initiate = overall > threshold and expected_reward > reward_threshold
        
        decision_color = "green" if should_initiate else "yellow"
        console.print(f"[bold {decision_color}]Decision: {'INITIATE' if should_initiate else 'SKIP'}[/bold {decision_color}]")
        console.print(f"  Overall score {overall:.3f} {'>' if overall > threshold else '<='} threshold {threshold}")
        console.print(f"  Expected reward {expected_reward:.3f} {'>' if expected_reward > reward_threshold else '<='} threshold {reward_threshold}")
        console.print()
        
        if dry_run:
            console.print("[dim]Dry run mode - no initiation created[/dim]")
        elif should_initiate:
            # Create test initiation
            import uuid
            initiation_id = str(uuid.uuid4())
            conversation_id = f"{user_id}_{int(datetime.utcnow().timestamp())}"
            
            db.execute("""
                INSERT INTO conversation_initiations (
                    initiation_id, user_id, conversation_id,
                    trigger_source, trigger_reason, question,
                    context, urgency, expected_answer_type,
                    initiated_at, resolution_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, %s)
            """, (
                initiation_id,
                user_id,
                conversation_id,
                "cli_test",
                f"test_strategy_{strategy_id}",
                f"[TEST] This is a test initiation using strategy '{strategy_id}'",
                f"Adaptivity: {adaptivity:.2f}, Civility: {civility:.2f}",
                "medium",
                "text",
                datetime.utcnow().isoformat(),
                "pending",
                datetime.utcnow().isoformat()
            ))
            db.commit()
            
            console.print(f"[green]✓[/green] Created test initiation: {initiation_id[:8]}")
            console.print(f"  View with: aico agency proactive cat {initiation_id[:8]}")
        else:
            console.print("[yellow]Scores too low - no initiation created[/yellow]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise typer.Exit(1)
