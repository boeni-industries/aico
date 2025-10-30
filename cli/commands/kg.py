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
            ("clear", "Clear knowledge graph data (DESTRUCTIVE)."),
            ("traverse", "Traverse graph from a node (BFS/DFS)."),
            ("path", "Find shortest path between two nodes."),
            ("insights", "Show graph analytics and insights."),
            ("subgraph", "Extract subgraph around a node.")
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
            "aico kg clear --user-id user_123",
            "aico kg traverse --node-id node_abc --max-depth 3",
            "aico kg path --source node_abc --target node_xyz",
            "aico kg insights --user-id user_123",
            "aico kg subgraph --node-id node_abc --radius 2"
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


@app.command(name="traverse", help="Traverse graph from a node (BFS/DFS).")
def traverse(
    node_id: str = typer.Option(..., "--node-id", "-n", help="Starting node ID"),
    max_depth: int = typer.Option(3, "--max-depth", "-d", help="Maximum traversal depth"),
    method: str = typer.Option("bfs", "--method", "-m", help="Traversal method (bfs/dfs)")
):
    """Traverse graph from a starting node."""
    async def _traverse():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        from aico.ai.knowledge_graph.query import GraphQueryEngine
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize storage and query engine
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
            query_engine = GraphQueryEngine(storage)
            
            # Traverse
            console.print(f"\n[cyan]Traversing from node {node_id} ({method.upper()}, depth={max_depth})...[/cyan]\n")
            
            if method.lower() == "bfs":
                results = await query_engine.traverse_bfs(node_id, max_depth=max_depth)
            else:
                results = await query_engine.traverse_dfs(node_id, max_depth=max_depth)
            
            if results:
                console.print(f"[green]Found {len(results)} nodes:[/green]\n")
                table = Table(box=box.SIMPLE)
                table.add_column("Depth", style="yellow")
                table.add_column("Label", style="cyan")
                table.add_column("Properties", style="white")
                
                for node, depth in results:
                    props = json.dumps(node.properties, ensure_ascii=False)
                    table.add_row(str(depth), node.label, props[:60])
                
                console.print(table)
            else:
                console.print("[yellow]No nodes found.[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_traverse())


@app.command(name="path", help="Find shortest path between two nodes.")
def find_path(
    source: str = typer.Option(..., "--source", "-s", help="Source node ID"),
    target: str = typer.Option(..., "--target", "-t", help="Target node ID"),
    max_hops: int = typer.Option(5, "--max-hops", "-m", help="Maximum hops")
):
    """Find shortest path between two nodes."""
    async def _find_path():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        from aico.ai.knowledge_graph.query import GraphQueryEngine
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize
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
            query_engine = GraphQueryEngine(storage)
            
            # Find path
            console.print(f"\n[cyan]Finding path from {source} to {target}...[/cyan]\n")
            path = await query_engine.find_shortest_path(source, target, max_hops=max_hops)
            
            if path:
                console.print(f"[green]Found path with {path.hop_count} hops (weight={path.total_weight:.3f}):[/green]\n")
                
                for i, node in enumerate(path.nodes):
                    props = json.dumps(node.properties, ensure_ascii=False)
                    console.print(f"  [{i}] {node.label}: {props[:60]}")
                    
                    if i < len(path.edges):
                        edge = path.edges[i]
                        console.print(f"      ↓ {edge.relation_type}")
            else:
                console.print("[yellow]No path found.[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_find_path())


@app.command(name="insights", help="Show graph analytics and insights.")
def insights(
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID")
):
    """Show comprehensive graph analytics and insights."""
    async def _insights():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        from aico.ai.knowledge_graph.analytics import GraphAnalytics
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize
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
            analytics = GraphAnalytics(storage)
            
            # Get insights
            console.print(f"\n[cyan]Analyzing knowledge graph for user {user_id}...[/cyan]\n")
            insights_data = await analytics.get_user_insights(user_id)
            
            if insights_data.get("status") == "no_data":
                console.print("[yellow]No knowledge graph data available.[/yellow]")
                return
            
            # Summary
            summary = insights_data.get("summary", {})
            console.print("[bold cyan]📊 Graph Summary:[/bold cyan]")
            console.print(f"  Nodes: {summary.get('total_nodes', 0):,}")
            console.print(f"  Edges: {summary.get('total_edges', 0):,}")
            console.print(f"  Entity Types: {summary.get('entity_types', 0)}")
            console.print(f"  Relationship Types: {summary.get('relationship_types', 0)}")
            console.print(f"  Communities: {summary.get('communities', 0)}\n")
            
            # Top entities
            top_entities = insights_data.get("top_entities", [])[:5]
            if top_entities:
                console.print("[bold cyan]⭐ Most Important Entities:[/bold cyan]")
                for entity in top_entities:
                    node = entity.get("node", {})
                    score = entity.get("importance_score", 0)
                    props = node.get("properties", {})
                    name = props.get("name", "Unknown")
                    label = node.get("label", "")
                    console.print(f"  • {name} ({label}) - Score: {score:.3f}")
                console.print()
            
            # Temporal patterns
            temporal = insights_data.get("temporal_patterns", {})
            if temporal and temporal.get("total_nodes"):
                console.print("[bold cyan]📅 Temporal Patterns:[/bold cyan]")
                console.print(f"  Recent Activity (7d): {temporal.get('recent_activity_7d', 0)} nodes")
                console.print(f"  Growth Rate: {temporal.get('growth_rate_per_day', 0)} nodes/day\n")
            
            # Knowledge gaps
            gaps = insights_data.get("knowledge_gaps", [])[:5]
            if gaps:
                console.print("[bold cyan]🔍 Knowledge Gaps:[/bold cyan]")
                for gap in gaps:
                    gap_type = gap.get("type", "")
                    suggestion = gap.get("suggestion", "")
                    console.print(f"  • {gap_type}: {suggestion}")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_insights())


@app.command(name="subgraph", help="Extract subgraph around a node.")
def subgraph(
    node_id: str = typer.Option(..., "--node-id", "-n", help="Center node ID"),
    radius: int = typer.Option(2, "--radius", "-r", help="Radius (hops)"),
    max_nodes: int = typer.Option(50, "--max-nodes", "-m", help="Maximum nodes")
):
    """Extract and visualize a subgraph around a node."""
    async def _subgraph():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        from aico.ai.knowledge_graph.query import GraphQueryEngine
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize
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
            query_engine = GraphQueryEngine(storage)
            
            # Get subgraph
            console.print(f"\n[cyan]Extracting subgraph around {node_id} (radius={radius})...[/cyan]\n")
            result = await query_engine.get_subgraph(node_id, radius=radius, max_nodes=max_nodes)
            
            # Display center node
            center = result.center_node
            console.print(f"[bold cyan]Center Node:[/bold cyan]")
            console.print(f"  {center.label}: {json.dumps(center.properties, ensure_ascii=False)[:80]}\n")
            
            # Display stats
            console.print(f"[green]Subgraph contains {result.node_count} nodes and {result.edge_count} edges[/green]\n")
            
            # Display neighbors
            if result.neighbors:
                console.print("[bold cyan]Connected Nodes:[/bold cyan]")
                table = Table(box=box.SIMPLE)
                table.add_column("Label", style="yellow")
                table.add_column("Properties", style="white")
                
                for node in result.neighbors[:20]:  # Limit display
                    props = json.dumps(node.properties, ensure_ascii=False)
                    table.add_row(node.label, props[:60])
                
                console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_subgraph())
