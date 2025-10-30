"""
AICO CLI commands for managing the knowledge graph.
"""

import typer
import asyncio
from rich.console import Console
from rich.table import Table
from rich import box
from typing import Optional
import json

from cli.decorators.sensitive import destructive
from cli.utils.help_formatter import format_subcommand_help

console = Console()


def kg_callback(ctx: typer.Context, help: bool = typer.Option(False, "--help", "-h", help="Show this message and exit.")):
    """Show help when no subcommand is given or --help is used."""
    if ctx.invoked_subcommand is None or help:
        subcommands = [
            ("status", "Show knowledge graph statistics (nodes, edges, labels)."),
            ("extract", "Extract knowledge graph from text (testing)."),
            ("query", "Query knowledge graph semantically."),
            ("ls", "List entities in knowledge graph."),
            ("edges", "List relationships (edges)."),
            ("graph", "Show graph structure around a node."),
            ("temporal", "Show temporal history of an entity."),
            ("stats", "Show detailed graph statistics."),
            ("test-pipeline", "Test extraction pipeline step-by-step."),
            ("clear", "Clear knowledge graph data (DESTRUCTIVE).")
        ]
        
        examples = [
            "aico kg status",
            "aico kg extract 'I moved to San Francisco last year'",
            "aico kg query 'Where do I live?' --user-id user_123",
            "aico kg ls --user-id user_123 --label PERSON",
            "aico kg edges --user-id user_123",
            "aico kg graph --user-id user_123 --node-id node_abc",
            "aico kg temporal --user-id user_123 --entity 'San Francisco'",
            "aico kg stats --user-id user_123",
            "aico kg test-pipeline 'Sarah gave me a piano lesson'",
            "aico kg clear --user-id user_123"
        ]
        
        format_subcommand_help(
            console=console,
            command_name="kg",
            description="Knowledge graph management and inspection.",
            subcommands=subcommands,
            examples=examples
        )
        raise typer.Exit()


app = typer.Typer(
    help="Knowledge graph management and inspection.",
    callback=kg_callback,
    invoke_without_command=True,
    context_settings={"help_option_names": []}
)


@app.command(name="status", help="Show knowledge graph statistics.")
def status():
    """Show knowledge graph statistics (nodes, edges, labels)."""
    async def _status():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        
        try:
            # Get database connection
            config = ConfigurationManager()
            key_manager = AICOKeyManager()
            master_key = key_manager.authenticate(interactive=False)
            db_path = AICOPaths.get_database_path()
            db_key = key_manager.derive_database_key(master_key, "libsql", "aico.db")
            db_connection = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
            
            with db_connection:
                # Get node statistics
                node_stats = db_connection.execute(
                    "SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as users FROM kg_nodes WHERE is_current = 1"
                ).fetchone()
                
                # Get edge statistics
                edge_stats = db_connection.execute(
                    "SELECT COUNT(*) as total FROM kg_edges WHERE is_current = 1"
                ).fetchone()
                
                # Get node type distribution
                node_types = db_connection.execute(
                    "SELECT label, COUNT(*) as count FROM kg_nodes WHERE is_current = 1 GROUP BY label ORDER BY count DESC LIMIT 10"
                ).fetchall()
                
                # Get edge type distribution
                edge_types = db_connection.execute(
                    "SELECT relation_type, COUNT(*) as count FROM kg_edges WHERE is_current = 1 GROUP BY relation_type ORDER BY count DESC LIMIT 10"
                ).fetchall()
            
            # Display results
            table = Table(
                title="🕸️ [bold cyan]Knowledge Graph Status[/bold cyan]",
                title_justify="left",
                border_style="bright_blue",
                header_style="bold yellow",
                box=box.SIMPLE_HEAD,
                padding=(0, 1)
            )
            table.add_column("Metric", style="cyan", justify="left")
            table.add_column("Value", style="green", justify="left")
            
            table.add_row("Total Nodes (Current)", f"{node_stats[0]:,}")
            table.add_row("Total Edges (Current)", f"{edge_stats[0]:,}")
            table.add_row("Users with Data", f"{node_stats[1]:,}")
            
            console.print(table)
            
            # Node types
            if node_types:
                console.print("\n[bold cyan]Top Node Types:[/bold cyan]")
                type_table = Table(box=None, show_header=False)
                type_table.add_column("Type", style="cyan")
                type_table.add_column("Count", style="white")
                for label, count in node_types:
                    type_table.add_row(label, f"{count:,}")
                console.print(type_table)
            
            # Edge types
            if edge_types:
                console.print("\n[bold cyan]Top Relationship Types:[/bold cyan]")
                rel_table = Table(box=None, show_header=False)
                rel_table.add_column("Relationship", style="cyan")
                rel_table.add_column("Count", style="white")
                for rel_type, count in edge_types:
                    rel_table.add_row(rel_type, f"{count:,}")
                console.print(rel_table)
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_status())


@app.command(name="extract", help="Extract knowledge graph from text (testing).")
def extract(
    text: str = typer.Argument(..., help="Text to extract from"),
    user_id: str = typer.Option("test_user", "--user-id", "-u", help="User ID")
):
    """Extract knowledge graph from text for testing."""
    async def _extract():
        from aico.core.config import ConfigurationManager
        from aico.ai.knowledge_graph import MultiPassExtractor
        from aico.ai.knowledge_graph.modelservice_client import ModelserviceClient
        import time
        
        try:
            console.print(f"\n[cyan]Extracting from:[/cyan] {text}\n")
            
            # Initialize components
            config = ConfigurationManager()
            modelservice = ModelserviceClient()
            await modelservice.connect()
            
            extractor = MultiPassExtractor(modelservice, config)
            
            # Extract
            start_time = time.time()
            graph = await extractor.extract(text, user_id)
            duration = time.time() - start_time
            
            # Display results
            console.print(f"[green]✓[/green] Extraction complete in {duration:.2f}s\n")
            
            if graph.nodes:
                console.print(f"[bold cyan]Extracted Nodes ({len(graph.nodes)}):[/bold cyan]")
                node_table = Table(box=box.SIMPLE)
                node_table.add_column("Label", style="yellow")
                node_table.add_column("Properties", style="white")
                node_table.add_column("Confidence", style="green")
                
                for node in graph.nodes:
                    props = json.dumps(node.properties, ensure_ascii=False)
                    node_table.add_row(node.label, props[:60], f"{node.confidence:.2f}")
                
                console.print(node_table)
            
            if graph.edges:
                console.print(f"\n[bold cyan]Extracted Edges ({len(graph.edges)}):[/bold cyan]")
                edge_table = Table(box=box.SIMPLE)
                edge_table.add_column("Relation", style="yellow")
                edge_table.add_column("Properties", style="white")
                edge_table.add_column("Confidence", style="green")
                
                for edge in graph.edges:
                    props = json.dumps(edge.properties, ensure_ascii=False)
                    edge_table.add_row(edge.relation_type, props[:60], f"{edge.confidence:.2f}")
                
                console.print(edge_table)
            
            if not graph.nodes and not graph.edges:
                console.print("[yellow]No entities or relationships extracted.[/yellow]")
            
            await modelservice.disconnect()
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_extract())


@app.command(name="query", help="Query knowledge graph semantically.")
def query(
    query_text: str = typer.Argument(..., help="Query text"),
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by node label"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results")
):
    """Query knowledge graph semantically."""
    async def _query():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize storage
            config = ConfigurationManager()
            key_manager = AICOKeyManager()
            master_key = key_manager.authenticate(interactive=False)
            db_path = AICOPaths.get_database_path()
            db_key = key_manager.derive_database_key(master_key, "libsql", "aico.db")
            db_connection = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
            
            chromadb_path = AICOPaths.get_semantic_memory_path()
            chromadb_client = chromadb.PersistentClient(
                path=str(chromadb_path),
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            
            storage = PropertyGraphStorage(db_connection, chromadb_client)
            
            # Search
            console.print(f"\n[cyan]Searching for:[/cyan] {query_text}\n")
            nodes = await storage.search_nodes(query_text, user_id, top_k=limit, label=label)
            
            if nodes:
                console.print(f"[green]Found {len(nodes)} results:[/green]\n")
                table = Table(box=box.SIMPLE)
                table.add_column("Label", style="yellow")
                table.add_column("Properties", style="white")
                table.add_column("Confidence", style="green")
                
                for node in nodes:
                    props = json.dumps(node.properties, ensure_ascii=False)
                    table.add_row(node.label, props[:80], f"{node.confidence:.2f}")
                
                console.print(table)
            else:
                console.print("[yellow]No results found.[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_query())


@app.command(name="ls", help="List entities in knowledge graph.")
def list_entities(
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by label"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of results")
):
    """List entities in knowledge graph."""
    async def _list():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize storage
            config = ConfigurationManager()
            key_manager = AICOKeyManager()
            master_key = key_manager.authenticate(interactive=False)
            db_path = AICOPaths.get_database_path()
            db_key = key_manager.derive_database_key(master_key, "libsql", "aico.db")
            db_connection = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
            
            chromadb_path = AICOPaths.get_semantic_memory_path()
            chromadb_client = chromadb.PersistentClient(
                path=str(chromadb_path),
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            
            storage = PropertyGraphStorage(db_connection, chromadb_client)
            
            # Get nodes
            nodes = await storage.get_user_nodes(user_id, label=label, current_only=True)
            nodes = nodes[:limit]  # Limit results
            
            if nodes:
                console.print(f"\n[green]Found {len(nodes)} entities:[/green]\n")
                table = Table(box=box.SIMPLE)
                table.add_column("ID", style="dim")
                table.add_column("Label", style="yellow")
                table.add_column("Properties", style="white")
                table.add_column("Confidence", style="green")
                
                for node in nodes:
                    props = json.dumps(node.properties, ensure_ascii=False)
                    table.add_row(node.id[:8], node.label, props[:60], f"{node.confidence:.2f}")
                
                console.print(table)
            else:
                console.print("[yellow]No entities found.[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_list())


@app.command(name="clear", help="Clear knowledge graph data (DESTRUCTIVE).")
@destructive
def clear(
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="User ID (if not specified, clears ALL data)")
):
    """Clear knowledge graph data."""
    async def _clear():
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        
        try:
            # Get database connection
            key_manager = AICOKeyManager()
            master_key = key_manager.authenticate(interactive=False)
            db_path = AICOPaths.get_database_path()
            db_key = key_manager.derive_database_key(master_key, "libsql", "aico.db")
            db_connection = EncryptedLibSQLConnection(db_path, encryption_key=db_key)
            
            with db_connection:
                if user_id:
                    # Clear user-specific data
                    db_connection.execute("DELETE FROM kg_edges WHERE user_id = ?", (user_id,))
                    db_connection.execute("DELETE FROM kg_nodes WHERE user_id = ?", (user_id,))
                    console.print(f"[green]✓[/green] Cleared knowledge graph for user: {user_id}")
                else:
                    # Clear all data
                    db_connection.execute("DELETE FROM kg_edges")
                    db_connection.execute("DELETE FROM kg_nodes")
                    console.print("[green]✓[/green] Cleared all knowledge graph data")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_clear())
