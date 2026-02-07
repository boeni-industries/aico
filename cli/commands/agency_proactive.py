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

raise RuntimeError("Legacy proactive CLI commands have been removed; use interactions instead")
        
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
