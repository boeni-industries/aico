"""
Version Management CLI Commands

Commands to manage database version detection and caching.
"""

import asyncio
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from backend.services.version_detector import get_version_detector

app = typer.Typer(help="Manage database version detection and caching")
console = Console()


@app.command("list")
def list_versions():
    """
    List all detected database versions (with caching).
    
    Versions are cached for 24 hours. Use 'refresh' to force re-detection.
    """
    try:
        detector = get_version_detector()
        versions = asyncio.run(detector.get_all_versions())
        
        # Create table
        table = Table(title="Database Versions", show_header=True, header_style="bold cyan")
        table.add_column("Database", style="cyan", width=20)
        table.add_column("Version", style="green", width=15)
        table.add_column("Status", style="yellow", width=15)
        
        for db_name, version in versions.items():
            # Check if from cache
            cached = detector.cache.get(db_name)
            status = "📦 Cached" if cached else "🔍 Detected"
            table.add_row(db_name, version, status)
        
        console.print(table)
        console.print("\n💡 [dim]Versions are cached for 24 hours. Use 'aico versions refresh' to force re-detection.[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to list versions: {e}[/red]")
        raise typer.Exit(1)


@app.command("refresh")
def refresh_versions(
    database: str = typer.Argument(None, help="Specific database to refresh (or all if not specified)")
):
    """
    Refresh database version detection (invalidate cache).
    
    Examples:
        aico versions refresh              # Refresh all databases
        aico versions refresh PostgreSQL   # Refresh only PostgreSQL
    """
    try:
        detector = get_version_detector()
        
        if database:
            # Refresh specific database
            console.print(f"🔄 Refreshing version for {database}...")
            detector.invalidate_cache(database)
            version = asyncio.run(detector.get_version(database))
            console.print(f"✅ [green]{database} version: {version}[/green]")
        else:
            # Refresh all databases
            console.print("🔄 Refreshing all database versions...")
            detector.invalidate_cache()
            versions = asyncio.run(detector.get_all_versions())
            
            console.print("✅ [green]All versions refreshed:[/green]")
            for db_name, version in versions.items():
                console.print(f"  • {db_name}: {version}")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to refresh versions: {e}[/red]")
        raise typer.Exit(1)


@app.command("show")
def show_version(
    database: str = typer.Argument(..., help="Database name (PostgreSQL, InfluxDB, ChromaDB, LMDB, Ollama)")
):
    """
    Show detailed version information for a specific database.
    
    Example:
        aico versions show PostgreSQL
    """
    try:
        detector = get_version_detector()
        
        # Check cache first
        cached = detector.cache.get(database)
        
        if cached:
            # Show cached version details
            panel = Panel(
                f"[cyan]Version:[/cyan] [green]{cached.version}[/green]\n"
                f"[cyan]Detected:[/cyan] {cached.detected_at}\n"
                f"[cyan]Method:[/cyan] {cached.detection_method}\n"
                f"[cyan]Status:[/cyan] 📦 Cached (valid for 24h)",
                title=f"[bold]{database}[/bold]",
                border_style="cyan"
            )
            console.print(panel)
        else:
            # Detect fresh
            console.print(f"🔍 Detecting {database} version...")
            version = asyncio.run(detector.get_version(database))
            
            # Get fresh cache entry
            cached = detector.cache.get(database)
            
            panel = Panel(
                f"[cyan]Version:[/cyan] [green]{version}[/green]\n"
                f"[cyan]Detected:[/cyan] {cached.detected_at if cached else 'Just now'}\n"
                f"[cyan]Method:[/cyan] {cached.detection_method if cached else 'N/A'}\n"
                f"[cyan]Status:[/cyan] 🔍 Freshly detected",
                title=f"[bold]{database}[/bold]",
                border_style="green"
            )
            console.print(panel)
        
    except Exception as e:
        console.print(f"[red]❌ Failed to show version for {database}: {e}[/red]")
        raise typer.Exit(1)


@app.command("cache-info")
def cache_info():
    """
    Show information about the version cache.
    """
    try:
        detector = get_version_detector()
        cache_file = detector.cache.cache_file
        
        if cache_file.exists():
            import json
            from datetime import datetime
            
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            console.print(Panel(
                f"[cyan]Cache File:[/cyan] {cache_file}\n"
                f"[cyan]Cached Databases:[/cyan] {len(cache_data)}\n"
                f"[cyan]TTL:[/cyan] 24 hours",
                title="[bold]Version Cache Info[/bold]",
                border_style="cyan"
            ))
            
            # Show cache entries
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Database", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("Detected At", style="yellow")
            table.add_column("Age", style="magenta")
            
            for db_name, db_data in cache_data.items():
                detected_at = datetime.fromisoformat(db_data['detected_at'])
                age = datetime.utcnow() - detected_at
                age_str = f"{age.total_seconds() / 3600:.1f}h"
                
                table.add_row(
                    db_name,
                    db_data['version'],
                    detected_at.strftime("%Y-%m-%d %H:%M"),
                    age_str
                )
            
            console.print(table)
        else:
            console.print("[yellow]⚠️  No cache file found. Run 'aico versions list' to populate cache.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to show cache info: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
