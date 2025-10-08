#!/usr/bin/env python3
"""
AICO Memory Intelligence Evaluator - Beautiful CLI

Award-winning visual CLI interface using Typer and Rich for stunning memory evaluation.
Follows AICO's visual style guide with modern, minimal, clean aesthetics.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.tree import Tree
from rich import box
from rich.live import Live
from rich.layout import Layout
from rich.status import Status

# Add shared path for AICO modules
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

# Import AICO modules (avoid logging for now to prevent initialization issues)
try:
    from aico.__version__ import __version__ as aico_version
except ImportError:
    aico_version = "unknown"

# Import memory evaluation framework
from .evaluator import MemoryIntelligenceEvaluator
from .scenarios import ScenarioLibrary
from .reporters import RichReporter

# Initialize console
console = Console()

# Create simple Typer app
app = typer.Typer(
    help="AICO Memory System Evaluator - Multi-scenario memory testing framework",
    no_args_is_help=True,
    add_completion=False
)


def print_header():
    """Print clean header"""
    console.print("\n[bold blue]AICO Memory Evaluator[/bold blue]")
    console.print("[dim]Multi-scenario memory system testing framework[/dim]\n")


def show_scenarios():
    """Show available scenarios with detailed information"""
    library = ScenarioLibrary()
    scenarios = library.list_scenarios()
    default_set = library.get_default_multi_scenario_set()
    
    console.print("[bold]Available Scenarios:[/bold]")
    console.print()
    
    for name in scenarios:
        scenario = library.get_scenario(name)
        if scenario:
            # Mark default scenarios
            default_marker = " [bold green]★[/bold green]" if name in default_set else ""
            
            console.print(f"  [cyan]{name}[/cyan]{default_marker}")
            console.print(f"    📝 {scenario.description}")
            console.print(f"    🎯 Difficulty: {scenario.difficulty_level} | 💬 Turns: {len(scenario.conversation_turns)} | ⏱️ Est: {scenario.estimated_duration_minutes}min")
            
            # Show tags
            if scenario.tags:
                tags_str = ", ".join(scenario.tags[:4])  # Show first 4 tags
                console.print(f"    🏷️  Tags: [dim]{tags_str}[/dim]")
            console.print()
    
    console.print(f"[bold green]★[/bold green] = Default multi-scenario set ({len(default_set)} scenarios)")
    console.print(f"[dim]Use 'run' without arguments to run the default set[/dim]")
    console.print()


def create_metrics_panel(result) -> Panel:
    """Create beautiful metrics display panel"""
    
    # Create metrics grid
    metrics_grid = Table.grid(padding=1)
    metrics_grid.add_column(style="bold cyan", width=25)
    metrics_grid.add_column(style="white", width=10)
    metrics_grid.add_column(style="dim white", width=30)
    
    # Overall score with visual bar
    overall_pct = result.overall_score.percentage
    overall_bar = "█" * int(overall_pct / 5) + "░" * (20 - int(overall_pct / 5))
    overall_color = "green" if overall_pct >= 85 else "yellow" if overall_pct >= 70 else "red"
    
    metrics_grid.add_row(
        "🎯 Overall Score",
        f"[bold {overall_color}]{overall_pct:.1f}%[/bold {overall_color}]",
        f"[{overall_color}]{overall_bar}[/{overall_color}]"
    )
    
    # Individual metrics
    metrics = [
        ("🧭 Context Adherence", result.context_adherence.percentage),
        ("🧠 Knowledge Retention", result.knowledge_retention.percentage),
        ("🏷️  Entity Extraction", result.entity_extraction.percentage),
        ("💬 Conversation Relevancy", result.conversation_relevancy.percentage),
        ("🧵 Semantic Memory Quality", result.semantic_memory_quality.percentage),
        ("✨ Response Quality", result.response_quality.percentage),
        ("🔒 Memory Consistency", result.memory_consistency.percentage)
    ]
    
    for name, score in metrics:
        color = "green" if score >= 85 else "yellow" if score >= 70 else "red"
        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        
        metrics_grid.add_row(
            name,
            f"[{color}]{score:.1f}%[/{color}]",
            f"[{color}]{bar}[/{color}]"
        )
    
    return Panel(
        metrics_grid,
        title="📊 Evaluation Results",
        border_style="bright_green" if overall_pct >= 85 else "yellow" if overall_pct >= 70 else "red",
        padding=(1, 2)
    )


def create_performance_panel(result) -> Panel:
    """Create beautiful performance metrics panel"""
    
    perf_grid = Table.grid(padding=1)
    perf_grid.add_column(style="bold blue", width=25)
    perf_grid.add_column(style="white", width=15)
    
    perf = result.performance_metrics
    avg_time = perf.get('average_response_time_ms', 0)
    max_time = perf.get('max_response_time_ms', 0)
    
    # Performance indicators
    time_color = "green" if avg_time < 1500 else "yellow" if avg_time < 2500 else "red"
    
    perf_grid.add_row("⚡ Avg Response Time", f"[{time_color}]{avg_time:.0f}ms[/{time_color}]")
    perf_grid.add_row("🚀 Max Response Time", f"{max_time:.0f}ms")
    perf_grid.add_row("⏱️  Total Duration", f"{result.total_duration_seconds:.1f}s")
    perf_grid.add_row("🔄 Turns per Minute", f"{perf.get('turns_per_minute', 0):.1f}")
    perf_grid.add_row("💬 Conversation Turns", f"{result.conversation_turns}")
    
    return Panel(
        perf_grid,
        title="⚡ Performance Metrics",
        border_style="bright_blue",
        padding=(1, 2)
    )


@app.command("list")
def list_scenarios():
    """List available test scenarios"""
    print_header()
    show_scenarios()

@app.command("scenarios")  
def scenarios_alias():
    """List available test scenarios (alias for 'list')"""
    print_header()
    show_scenarios()


@app.command("run")
def run_evaluation(
    scenarios: Optional[List[str]] = typer.Argument(None, help="Scenarios to run (default: all 3 diverse scenarios)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    single: Optional[str] = typer.Option(None, "--single", "-s", help="Run single scenario"),
    reuse_user: bool = typer.Option(False, "--reuse-user", help="Reuse same user across all scenarios (for deduplication testing)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Use existing user ID (for persistent deduplication testing)")
):
    """Run memory evaluation test(s)"""
    
    print_header()
    
    if user_id:
        console.print(f"[bold cyan]🔒 PERSISTENT USER MODE: Using user {user_id[:8]}...[/bold cyan]")
        console.print()
    elif reuse_user:
        console.print("[bold yellow]🔄 DEDUPLICATION TEST MODE: Reusing same user across all scenarios[/bold yellow]")
        console.print()
    
    async def run_async():
        evaluator = MemoryIntelligenceEvaluator(reuse_user=reuse_user, user_id=user_id)
        library = ScenarioLibrary()
        
        try:
            # Determine which scenarios to run
            if single:
                scenario_names = [single]
                console.print(f"🧠 Running single scenario: [cyan]{single}[/cyan]")
            elif scenarios:
                scenario_names = scenarios
                console.print(f"🧠 Running {len(scenarios)} scenarios: [cyan]{', '.join(scenarios)}[/cyan]")
            else:
                scenario_names = library.get_default_multi_scenario_set()
                console.print(f"🧠 Running default multi-scenario evaluation ([cyan]{len(scenario_names)} scenarios[/cyan])")
            
            # Run scenarios
            results = []
            total_start_time = datetime.now()
            
            for i, scenario_name in enumerate(scenario_names, 1):
                console.print(f"\n{'='*60}")
                console.print(f"📊 SCENARIO {i}/{len(scenario_names)}: [bold cyan]{scenario_name}[/bold cyan]")
                console.print(f"{'='*60}")
                
                scenario = library.get_scenario(scenario_name)
                if not scenario:
                    console.print(f"[red]❌ Scenario '{scenario_name}' not found[/red]")
                    continue
                
                console.print(f"📝 {scenario.description}")
                console.print(f"⏱️  Estimated duration: {scenario.estimated_duration_minutes} minutes")
                console.print(f"🎯 Difficulty: {scenario.difficulty_level}")
                
                with console.status(f"[bold blue]🧠 Processing memory operations (may take up to 20s)...[/bold blue]"):
                    result = await evaluator.run_comprehensive_evaluation(scenario_name)
                
                results.append((scenario_name, result))
                
                # Display individual scenario results
                console.print(f"\n[bold green]✅ Scenario Complete: {scenario_name}[/bold green]")
                console.print(f"🎯 Overall Score: [bold]{result.overall_score.percentage:.1f}%[/bold]")
                console.print(f"📈 Key Metrics:")
                console.print(f"  Context Adherence........ {result.context_adherence.percentage:6.1f}%")
                console.print(f"  Knowledge Retention...... {result.knowledge_retention.percentage:6.1f}%")
                console.print(f"  Entity Extraction........ {result.entity_extraction.percentage:6.1f}%")
                console.print(f"  Conversation Relevancy... {result.conversation_relevancy.percentage:6.1f}%")
                console.print(f"  Semantic Memory Quality.. {result.semantic_memory_quality.percentage:6.1f}%")
                console.print(f"  Response Quality......... {result.response_quality.percentage:6.1f}%")
                console.print(f"  Memory Consistency....... {result.memory_consistency.percentage:6.1f}%")
                
                if verbose:
                    perf = result.performance_metrics
                    console.print(f"\n⚡ Performance:")
                    console.print(f"  Average Response Time.... {perf.get('average_response_time_ms', 0):6.0f}ms")
                    console.print(f"  Max Response Time........ {perf.get('max_response_time_ms', 0):6.0f}ms")
                    console.print(f"  Total Duration........... {result.total_duration_seconds:6.1f}s")
            
            # Calculate and display compound results
            if len(results) > 1:
                total_duration = (datetime.now() - total_start_time).total_seconds()
                
                console.print(f"\n{'='*60}")
                console.print(f"📊 COMPOUND EVALUATION RESULTS")
                console.print(f"{'='*60}")
                
                # Calculate weighted averages
                total_weight = 0
                weighted_scores = {
                    'overall': 0, 'context_adherence': 0, 'knowledge_retention': 0,
                    'entity_extraction': 0, 'conversation_relevancy': 0,
                    'semantic_memory_quality': 0, 'response_quality': 0, 'memory_consistency': 0
                }
                
                for scenario_name, result in results:
                    # Weight by scenario difficulty and turn count
                    scenario = library.get_scenario(scenario_name)
                    difficulty_weight = {"easy": 1, "medium": 1.2, "hard": 1.5, "expert": 2.0}.get(scenario.difficulty_level, 1.0)
                    turn_weight = len(scenario.conversation_turns) / 4.0  # Normalize to 4-turn baseline
                    weight = difficulty_weight * turn_weight
                    total_weight += weight
                    
                    weighted_scores['overall'] += result.overall_score.percentage * weight
                    weighted_scores['context_adherence'] += result.context_adherence.percentage * weight
                    weighted_scores['knowledge_retention'] += result.knowledge_retention.percentage * weight
                    weighted_scores['entity_extraction'] += result.entity_extraction.percentage * weight
                    weighted_scores['conversation_relevancy'] += result.conversation_relevancy.percentage * weight
                    weighted_scores['semantic_memory_quality'] += result.semantic_memory_quality.percentage * weight
                    weighted_scores['response_quality'] += result.response_quality.percentage * weight
                    weighted_scores['memory_consistency'] += result.memory_consistency.percentage * weight
                
                # Normalize by total weight
                for key in weighted_scores:
                    weighted_scores[key] /= total_weight
                
                # Display compound results
                overall_color = "green" if weighted_scores['overall'] >= 85 else "yellow" if weighted_scores['overall'] >= 70 else "red"
                console.print(f"🎯 [bold {overall_color}]Compound Overall Score: {weighted_scores['overall']:.1f}%[/bold {overall_color}]")
                
                console.print(f"\n📈 Detailed Compound Metrics:")
                for metric, score in weighted_scores.items():
                    if metric != 'overall':
                        color = "green" if score >= 85 else "yellow" if score >= 70 else "red"
                        metric_name = metric.replace('_', ' ').title()
                        console.print(f"  {metric_name:.<25} [{color}]{score:6.1f}%[/{color}]")
                
                console.print(f"\n⚡ Compound Performance:")
                console.print(f"  Scenarios Completed...... {len(results)}")
                console.print(f"  Total Evaluation Time.... {total_duration:.1f}s")
                console.print(f"  Average per Scenario..... {total_duration/len(results):.1f}s")
                
                # Individual scenario summary
                print(f"📋 Individual Results:")
                for scenario_name, result in results:
                    color = "✅" if result.overall_score.percentage >= 85 else "⚠️" if result.overall_score.percentage >= 70 else "❌"
                    print(f"  {color} {scenario_name}: {result.overall_score.percentage:.1f}%")
                
                # ACTIONABLE INSIGHTS: Provide specific improvement recommendations
                console.print(f"\n{'='*60}")
                console.print(f"🔧 ACTIONABLE INSIGHTS & IMPROVEMENT RECOMMENDATIONS")
                console.print(f"{'='*60}")
                
                # Analyze weakest areas across all scenarios
                all_metrics = {
                    'context_adherence': [],
                    'knowledge_retention': [],
                    'entity_extraction': []
                }
                
                for scenario_name, result in results:
                    all_metrics['context_adherence'].append(result.context_adherence.percentage)
                    all_metrics['knowledge_retention'].append(result.knowledge_retention.percentage)
                    all_metrics['entity_extraction'].append(result.entity_extraction.percentage)
                
                # Find weakest areas and provide specific recommendations
                avg_scores = {k: sum(v)/len(v) for k, v in all_metrics.items()}
                weakest_metric = min(avg_scores, key=avg_scores.get)
                weakest_score = avg_scores[weakest_metric]
                
                if weakest_score < 70:
                    console.print(f"🚨 [bold red]CRITICAL ISSUE IDENTIFIED[/bold red]")
                    console.print(f"   Weakest Area: {weakest_metric.replace('_', ' ').title()} ({weakest_score:.1f}%)")
                    
                    if weakest_metric == 'context_adherence':
                        console.print(f"   💡 [bold]Recommendations:[/bold]")
                        console.print(f"      • Check context retrieval relevance scoring")
                        console.print(f"      • Verify semantic memory embeddings quality")
                        console.print(f"      • Review context filtering thresholds")
                        console.print(f"      • Analyze LLM context utilization patterns")
                    elif weakest_metric == 'knowledge_retention':
                        console.print(f"   💡 [bold]Recommendations:[/bold]")
                        console.print(f"      • Improve entity extraction accuracy")
                        console.print(f"      • Check fact storage and retrieval pipeline")
                        console.print(f"      • Review conversation segmentation logic")
                        console.print(f"      • Verify user_facts ChromaDB indexing")
                    elif weakest_metric == 'entity_extraction':
                        console.print(f"   💡 [bold]Recommendations:[/bold]")
                        console.print(f"      • Review GLiNER model performance")
                        console.print(f"      • Check NER request/response pipeline")
                        console.print(f"      • Verify entity storage in ChromaDB")
                        console.print(f"      • Analyze entity type coverage")
                
                # Scenario-specific insights
                console.print(f"\n📊 [bold]Scenario-Specific Insights:[/bold]")
                for scenario_name, result in results:
                    if result.overall_score.percentage < 80:
                        console.print(f"   ⚠️ {scenario_name}:")
                        
                        # Check specific details for actionable insights
                        if hasattr(result.context_adherence, 'details') and result.context_adherence.details:
                            details = result.context_adherence.details
                            if 'elements_found' in details and 'total_elements_tested' in details:
                                found = details['elements_found']
                                total = details['total_elements_tested']
                                if found < total * 0.7:
                                    console.print(f"      • Context elements missing: {total-found}/{total}")
                                    console.print(f"      • Focus on improving context retrieval for this scenario type")
                        
                        if hasattr(result.entity_extraction, 'details') and result.entity_extraction.details:
                            details = result.entity_extraction.details
                            if 'gliner_tests' in details:
                                low_precision_turns = [t for t in details['gliner_tests'] if t.get('precision', 1) < 0.7]
                                if low_precision_turns:
                                    console.print(f"      • Entity extraction precision issues in {len(low_precision_turns)} turns")
                                    console.print(f"      • Review GLiNER model for this conversation type")
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return 1
        finally:
            await evaluator.cleanup()
    
    exit_code = asyncio.run(run_async())
    raise typer.Exit(exit_code)




if __name__ == "__main__":
    app()
