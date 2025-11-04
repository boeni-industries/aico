"""
AICO CLI commands for managing the ChromaDB semantic memory database.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich import box
from typing import Optional

from cli.utils.chroma_utils import (
    get_chroma_status_cli, clear_chroma_cli, list_chroma_collections,
    query_chroma_collection, get_chroma_collection_stats, add_chroma_document,
    tail_chroma_collection
)
from cli.decorators.sensitive import destructive, sensitive
from cli.utils.help_formatter import format_subcommand_help

def chroma_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit.")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("status", "Show the status and statistics of the ChromaDB database."),
            ("ls", "List all collections within the ChromaDB database."),
            ("count", "Count the number of documents in a specific collection."),
            ("query", "Query a collection for similar documents."),
            ("add", "Add a document to a collection for testing."),
            ("tail", "View the last N documents from a collection."),
            ("clear", "Clear all data from the ChromaDB database."),
            ("cleanup", "Clean up old temporary facts (maintenance).")
        ]
        
        examples = [
            "aico chroma status",
            "aico chroma ls",
            "aico chroma count conversation_segments",
            "aico chroma query conversation_segments 'What did we discuss about work?'",
            "aico chroma add 'Test conversation segment' --metadata '{\"role\": \"user\", \"confidence\": 0.95}'",
            "aico chroma tail conversation_segments --limit 5",
            "aico chroma clear"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="chroma",
            description="Manage the ChromaDB semantic memory database.",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()

app = typer.Typer(
    help="Manage the ChromaDB semantic memory database.",
    callback=chroma_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)
console = Console()

@app.command(name="status", help="Show the status and statistics of the ChromaDB database.")
def status():
    """Show the status and statistics of the ChromaDB database."""
    status_data = get_chroma_status_cli()
    
    table = Table(
        title="✨ [bold cyan]ChromaDB Semantic Memory Status[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Property", style="cyan", justify="left")
    table.add_column("Value", style="green", justify="left")

    table.add_row("Database Path", status_data["path"])
    table.add_row("Exists", "✅ Yes" if status_data["exists"] else "❌ No")

    if status_data["exists"] and not status_data.get("error"):
        table.add_row("Size (MB)", str(status_data["size_mb"]))
        table.add_row("Collections", str(status_data.get("collection_count", 0)))
        
        # Show embedding dimensions if available
        if status_data.get("embedding_dimensions"):
            dims = status_data["embedding_dimensions"]
            model_name = status_data.get("embedding_model", "unknown")
            table.add_row("Embedding Dimensions", f"[bold green]{dims}[/bold green] ({model_name})")
        
        if status_data.get("collections"):
            collections_table = Table(title="Collection Document Counts", box=None, show_header=False)
            collections_table.add_column("Collection", style="cyan")
            collections_table.add_column("Documents", style="white")
            for name, count in status_data["collections"].items():
                # Handle both numeric counts and error strings
                if isinstance(count, int):
                    collections_table.add_row(name, f"{count:,}")
                else:
                    collections_table.add_row(name, f"[red]{count}[/red]")
            table.add_row("Documents", collections_table)

    elif status_data.get("error"):
        table.add_row("Error", f"[red]{status_data['error']}[/red]")

    console.print(table)

@app.command(name="ls", help="List all collections and their document counts.")
def ls():
    """List all collections and their document counts."""
    collections_data = list_chroma_collections()
    if collections_data.get("error"):
        console.print(f"[red]Error accessing ChromaDB: {collections_data['error']}[/red]")
        raise typer.Exit(1)

    collections = collections_data.get("collections", [])
    if not collections:
        console.print("[yellow]No collections found. ChromaDB may not be initialized.[/yellow]")
        console.print("[dim]Run 'aico db init' to initialize the database.[/dim]")
        return

    table = Table(
        title="✨ [bold cyan]ChromaDB Collections[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("Collection", style="cyan", justify="left")
    table.add_column("Documents", style="green", justify="right")
    table.add_column("Embedding Model", style="bright_blue", justify="left")

    for collection in collections:
        table.add_row(
            collection["name"],
            f"{collection.get('count', 0):,}",
            collection.get("metadata", {}).get("embedding_model", "unknown")
        )

    console.print(table)

@app.command(name="count", help="Count the number of documents in a specific collection.")
def count(collection_name: str = typer.Argument(..., help="Name of the collection to count")):
    """Count the number of documents in a specific collection."""
    stats = get_chroma_collection_stats(collection_name)
    
    if stats.get("error"):
        console.print(f"[red]Error: {stats['error']}[/red]")
        raise typer.Exit(1)
    
    count_value = stats.get("count", 0)
    console.print(f"Collection '[cyan]{collection_name}[/cyan]' contains [green]{count_value:,}[/green] documents")

@app.command(name="query", help="Query a collection for similar documents.")
def query(
    collection_name: str = typer.Argument(..., help="Name of the collection to query"),
    query_text: str = typer.Argument(..., help="Text to search for"),
    limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of results to return"),
    threshold: float = typer.Option(0.0, "--threshold", "-t", help="Minimum similarity threshold (0.0-1.0)")
):
    """Query a collection for similar documents."""
    from rich.panel import Panel
    from rich.console import Group
    
    results = query_chroma_collection(collection_name, query_text, limit, threshold)
    
    if results.get("error"):
        console.print(f"[red]Error: {results['error']}[/red]")
        raise typer.Exit(1)
    
    documents = results.get("documents", [])
    if not documents:
        console.print(f"[yellow]No documents found in collection '{collection_name}' matching '{query_text}'[/yellow]")
        return
    
    # Add explanation about similarity values
    console.print()
    console.print("[bold cyan]🔍 Semantic Search Results[/bold cyan]")
    console.print(f"[dim]Query: '{query_text}' in collection '{collection_name}'[/dim]")
    console.print()
    console.print("[bold yellow]📏 Similarity Explanation:[/bold yellow]")
    console.print("[dim]• Similarity measures how closely your query matches each document[/dim]")
    console.print("[dim]• Higher values = more similar (1.0 = perfect match, 0.0 = no similarity)[/dim]")
    console.print("[dim]• Typical ranges: 0.8-1.0 (very similar), 0.5-0.8 (somewhat similar), 0.0-0.5 (less similar)[/dim]")
    console.print("[dim]• Normalized from raw embedding distances for easier interpretation[/dim]")
    console.print()
    
    # Create vertical panels for each result (like tail --full)
    panels = []
    for i, doc in enumerate(documents):
        doc_id = doc.get("id", f"doc_{i}")
        document_text = doc.get("document", "")
        semantic_score = doc.get('semantic_score', doc.get('similarity', 0.0))
        bm25_score = doc.get('bm25_score', 0.0)
        bm25_normalized = doc.get('bm25_normalized', 0.0)
        hybrid_score = doc.get('hybrid_score', semantic_score)
        metadata = doc.get("metadata", {})
        
        # Build vertical content
        content_parts = []
        content_parts.append(f"[bold cyan]ID:[/bold cyan] [dim]{doc_id}[/dim]")
        content_parts.append("")
        content_parts.append(f"[bold cyan]Document:[/bold cyan]")
        content_parts.append(f"  {document_text}")
        content_parts.append("")
        
        # Similarity scores with color coding
        def format_score_value(score):
            if score > 0.7:
                return f"[bright_green]{score:.3f}[/bright_green]"
            elif score > 0.4:
                return f"[yellow]{score:.3f}[/yellow]"
            else:
                return f"[red]{score:.3f}[/red]"
        
        content_parts.append(f"[bold cyan]Similarity:[/bold cyan]")
        content_parts.append(f"  [yellow]Hybrid:[/yellow] {format_score_value(hybrid_score)}")
        content_parts.append(f"  [dim](Semantic: {semantic_score:.3f}, BM25: {bm25_normalized:.3f})[/dim]")
        content_parts.append("")
        
        # Metadata - consistent order
        if metadata:
            content_parts.append(f"[bold cyan]Metadata:[/bold cyan]")
            # Define consistent order for metadata fields
            ordered_fields = ['role', 'timestamp', 'conversation_id', 'user_id', 'entity_type', 'confidence', 'category', 'created_at']
            
            # Show ordered fields first
            for key in ordered_fields:
                if key in metadata:
                    value = metadata[key]
                    if key == 'confidence' and isinstance(value, (int, float)):
                        content_parts.append(f"  [yellow]{key}:[/yellow] {value:.2f}")
                    elif key == 'created_at' and isinstance(value, str):
                        # Show only date part for brevity
                        date_part = value.split('T')[0] if 'T' in value else value[:10]
                        content_parts.append(f"  [yellow]{key}:[/yellow] {date_part}")
                    else:
                        content_parts.append(f"  [yellow]{key}:[/yellow] {value}")
            
            # Show any remaining fields (excluding verbose ones)
            for key, value in metadata.items():
                if key not in ordered_fields and key not in ['source_message', 'fact_extraction_id', 'reasoning']:
                    content_parts.append(f"  [yellow]{key}:[/yellow] {value}")
        
        panel = Panel(
            "\n".join(content_parts),
            title=f"[bold]Document {i+1}/{len(documents)}[/bold]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        panels.append(panel)
    
    # Display all panels
    for panel in panels:
        console.print(panel)
    
    console.print()
    console.print(f"[dim]Found {len(documents)} result{'s' if len(documents) != 1 else ''} • Showing top {min(limit, len(documents))}[/dim]")

@app.command(name="add", help="Add a document to a collection for testing.")
def add(
    document: str = typer.Argument(..., help="Document text to add"),
    collection_name: Optional[str] = typer.Option("conversation_segments", "--collection", "-c", help="Name of the collection (default: conversation_segments)"),
    doc_id: Optional[str] = typer.Option(None, "--id", help="Document ID (auto-generated if not provided)"),
    metadata: Optional[str] = typer.Option(None, "--metadata", help="JSON metadata for the document")
):
    """Add a document to a collection for testing."""
    result = add_chroma_document(collection_name, document, doc_id, metadata)
    
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)
    
    console.print(f"✅ [green]Added document to collection '[cyan]{collection_name}[/cyan]'[/green]")
    console.print(f"Document ID: [dim]{result.get('id', 'unknown')}[/dim]")

@app.command(name="tail", help="View the last N documents from a collection.")
def tail(
    collection_name: str = typer.Argument(..., help="Name of the collection to tail"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of documents to show"),
    full: bool = typer.Option(False, "--full", help="Show full content without truncation")
):
    """View the last N documents from a collection."""
    try:
        result = tail_chroma_collection(collection_name, limit, full)
        
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        
        table = result.get("table")
        total_count = result.get("total_count", 0)
        shown_count = result.get("shown_count", 0)
        
        console.print()
        console.print(table)
        console.print()
        console.print(f"[dim]Showing last {shown_count} of {total_count} total documents in collection '{collection_name}'[/dim]")
        
    except ValueError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error reading collection: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="clear", help="Clear all data from the ChromaDB database.")
@destructive
def clear_chroma():
    """Clear and reinitialize ChromaDB database"""
    try:
        from cli.utils.chroma_utils import clear_chroma_cli
        clear_chroma_cli()
    except Exception as e:
        console.print(f"[red]Error clearing ChromaDB: {e}[/red]")
        raise typer.Exit(1)

        raise typer.Exit(1)

@app.command(name="cleanup")
@sensitive
def cleanup_old_facts(
    days: int = typer.Option(90, "--days", "-d", help="Delete temporary facts older than N days"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Clean up old temporary facts (maintenance)"""
    try:
        if not confirm:
            import typer
            if not typer.confirm(f"Delete temporary facts older than {days} days?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        import asyncio
        from cli.utils.chroma_utils import cleanup_old_facts_admin
        
        deleted_count = asyncio.run(cleanup_old_facts_admin(days))
        
        if deleted_count > 0:
            console.print(f"[green]✅ Cleaned up {deleted_count} old temporary facts[/green]")
        else:
            console.print("[dim]No old temporary facts found to clean up[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error cleaning up facts: {e}[/red]")
        raise typer.Exit(1)
