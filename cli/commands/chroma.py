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
    query_chroma_collection, get_chroma_collection_stats, add_chroma_document
)
from cli.decorators.sensitive import destructive
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
            ("clear", "Clear all data from the ChromaDB database.")
        ]
        
        examples = [
            "aico chroma status",
            "aico chroma ls",
            "aico chroma count user_facts",
            "aico chroma query user_facts 'What is my name?'",
            "aico chroma add 'My name is John' --metadata '{\"type\": \"personal_info\"}'",
            "aico chroma add 'I like pizza' --collection user_facts --id my_preference",
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
        
        if status_data.get("collections"):
            collections_table = Table(title="Collection Document Counts", box=None, show_header=False)
            collections_table.add_column("Collection", style="cyan")
            collections_table.add_column("Documents", style="white")
            for name, count in status_data["collections"].items():
                collections_table.add_row(name, f"{count:,}")
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
    results = query_chroma_collection(collection_name, query_text, limit, threshold)
    
    if results.get("error"):
        console.print(f"[red]Error: {results['error']}[/red]")
        raise typer.Exit(1)
    
    documents = results.get("documents", [])
    if not documents:
        console.print(f"[yellow]No documents found in collection '{collection_name}' matching '{query_text}'[/yellow]")
        return
    
    table = Table(
        title=f"✨ [bold cyan]Query Results: '{query_text}'[/bold cyan]",
        title_justify="left",
        border_style="bright_blue",
        header_style="bold yellow",
        box=box.SIMPLE_HEAD,
        padding=(0, 1)
    )
    table.add_column("ID", style="dim", width=10)
    table.add_column("Document", style="cyan", no_wrap=False, min_width=40)
    table.add_column("Distance", style="green", justify="right", width=10)
    table.add_column("Metadata", style="bright_blue", no_wrap=False, width=20)
    
    for i, doc in enumerate(documents):
        metadata_str = str(doc.get("metadata", {})) if doc.get("metadata") else ""
        table.add_row(
            doc.get("id", f"doc_{i}"),
            doc.get("document", "")[:100] + ("..." if len(doc.get("document", "")) > 100 else ""),
            f"{doc.get('distance', 0.0):.3f}",
            metadata_str[:50] + ("..." if len(metadata_str) > 50 else "")
        )
    
    console.print(table)

@app.command(name="add", help="Add a document to a collection for testing.")
def add(
    document: str = typer.Argument(..., help="Document text to add"),
    collection_name: Optional[str] = typer.Option("user_facts", "--collection", "-c", help="Name of the collection (default: user_facts)"),
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

@app.command(name="user-facts")
def get_user_facts(
    user_id: str = typer.Argument(..., help="User ID to get facts for"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    confidence: Optional[float] = typer.Option(None, "--confidence", "-conf", help="Minimum confidence threshold"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json")
):
    """Get all facts for a specific user (administrative query)"""
    try:
        import asyncio
        from cli.utils.chroma_utils import get_user_facts_admin
        
        facts = asyncio.run(get_user_facts_admin(user_id, category, confidence))
        
        if not facts:
            console.print(f"[yellow]No facts found for user {user_id}[/yellow]")
            return
        
        if format == "json":
            import json
            console.print(json.dumps(facts, indent=2))
        else:
            # Table format
            from rich.table import Table
            
            table = Table(title=f"Facts for User: {user_id}")
            table.add_column("ID", style="dim")
            table.add_column("Content", style="cyan")
            table.add_column("Category", style="green")
            table.add_column("Confidence", style="yellow")
            table.add_column("Created", style="dim")
            
            for fact in facts:
                metadata = fact.get("metadata", {})
                table.add_row(
                    fact["id"][:20] + "...",
                    fact["content"][:50] + ("..." if len(fact["content"]) > 50 else ""),
                    metadata.get("category", "unknown"),
                    f"{metadata.get('confidence', 0):.2f}",
                    metadata.get("created_at", "unknown")[:10]
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(facts)} facts[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error getting user facts: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="delete-user")
def delete_user_facts(
    user_id: str = typer.Argument(..., help="User ID to delete facts for"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
):
    """Delete all facts for a user (GDPR compliance)"""
    try:
        if not confirm:
            import typer
            if not typer.confirm(f"Are you sure you want to delete ALL facts for user '{user_id}'? This cannot be undone."):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        import asyncio
        from cli.utils.chroma_utils import delete_user_facts_admin
        
        success = asyncio.run(delete_user_facts_admin(user_id))
        
        if success:
            console.print(f"[green]✅ Successfully deleted all facts for user {user_id}[/green]")
        else:
            console.print(f"[red]❌ Failed to delete facts for user {user_id}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error deleting user facts: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="cleanup")
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
