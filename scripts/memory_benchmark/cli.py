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
    help="AICO Memory System Evaluator",
    no_args_is_help=True,
    add_completion=False
)


def print_header():
    """Print clean header"""
    console.print("\n[bold blue]AICO Memory Evaluator[/bold blue]")
    console.print("[dim]Testing memory system performance[/dim]\n")


def show_scenarios():
    """Show available scenarios in simple format"""
    library = ScenarioLibrary()
    scenarios = library.list_scenarios()
    
    console.print("[bold]Available Scenarios:[/bold]")
    for name in scenarios:
        scenario = library.get_scenario(name)
        if scenario:
            console.print(f"  [cyan]{name}[/cyan] - {scenario.description}")
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


@app.command("run")
def run_evaluation(
    scenario: str = typer.Argument("comprehensive_memory_test", help="Scenario to run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
):
    """Run memory evaluation test"""
    
    print_header()
    
    async def run_async():
        evaluator = MemoryIntelligenceEvaluator()
        
        try:
            console.print(f"Running scenario: [cyan]{scenario}[/cyan]")
            
            with console.status("[bold blue]Evaluating memory system..."):
                result = await evaluator.run_comprehensive_evaluation(scenario)
            
            # Simple results display
            console.print(f"\n[bold]Results:[/bold]")
            console.print(f"Overall Score: [green]{result.overall_score.percentage:.1f}%[/green]")
            console.print(f"Context Adherence: {result.context_adherence.percentage:.1f}%")
            console.print(f"Knowledge Retention: {result.knowledge_retention.percentage:.1f}%")
            console.print(f"Entity Extraction: {result.entity_extraction.percentage:.1f}%")
            
            if verbose and evaluator.current_session:
                console.print(f"\nConversation turns: {len(evaluator.current_session.conversation_log)}")
                for i, turn in enumerate(evaluator.current_session.conversation_log):
                    console.print(f"  Turn {i+1}: {turn.get('response_time_ms', 0):.0f}ms")
            
            return 0 if result.overall_score.percentage >= 70 else 1
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1
        finally:
            await evaluator.cleanup()
    
    exit_code = asyncio.run(run_async())
    raise typer.Exit(exit_code)




if __name__ == "__main__":
    app()
