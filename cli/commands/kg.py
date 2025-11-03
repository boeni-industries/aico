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


def _get_database_connection(db_path: str) -> 'EncryptedLibSQLConnection':
    """Get authenticated database connection."""
    from aico.core.config import ConfigurationManager
    from aico.security import AICOKeyManager
    from aico.data.libsql.encrypted import EncryptedLibSQLConnection
    import keyring
    
    config = ConfigurationManager()
    config.initialize(lightweight=True)
    key_manager = AICOKeyManager(config)
    
    if not key_manager.has_stored_key():
        console.print("[red]Error: Master key not found. Run 'aico security setup' first.[/red]")
        raise typer.Exit(1)
    
    # Try session-based authentication first
    cached_key = key_manager._get_cached_session()
    if cached_key:
        key_manager._extend_session()
        db_key = key_manager.derive_database_key(cached_key, "libsql", str(db_path))
        return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    
    # Try stored key from keyring
    stored_key = keyring.get_password(key_manager.service_name, "master_key")
    if stored_key:
        master_key = bytes.fromhex(stored_key)
        key_manager._cache_session(master_key)
        db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
        return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)
    
    # Need password
    password = typer.prompt("Enter master password", hide_input=True)
    if not password or not password.strip():
        console.print("[red]Error: Password cannot be empty[/red]")
        raise typer.Exit(1)
    
    master_key = key_manager.authenticate(password, interactive=False)
    db_key = key_manager.derive_database_key(master_key, "libsql", str(db_path))
    return EncryptedLibSQLConnection(str(db_path), encryption_key=db_key)


@app.command(name="status", help="Show knowledge graph statistics.")
def status():
    """Show knowledge graph statistics (nodes, edges, labels)."""
    async def _status():
        from aico.core.paths import AICOPaths
        
        try:
            # Get database connection
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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
            config.initialize(lightweight=True)
            
            # Connect to modelservice via message bus
            console.print("[dim]Connecting to message bus...[/dim]")
            console.print(f"[dim]DEBUG: Creating ModelserviceClient instance...[/dim]")
            modelservice = ModelserviceClient()
            console.print(f"[dim]DEBUG: ModelserviceClient created: {modelservice}[/dim]")
            
            try:
                console.print(f"[dim]DEBUG: Calling connect() with 10s timeout...[/dim]")
                await asyncio.wait_for(modelservice.connect(), timeout=10.0)
                console.print(f"[dim]DEBUG: connect() returned successfully[/dim]")
                # Give message loop time to start processing
                await asyncio.sleep(0.5)
                console.print("[dim]✓ Connected to message bus[/dim]")
            except asyncio.TimeoutError:
                console.print("[red]Error: Connection to message bus timed out after 10s.[/red]")
                console.print("Make sure backend is running: [cyan]aico gateway status[/cyan]")
                return
            except Exception as e:
                console.print(f"[red]Error: Failed to connect to message bus: {e}[/red]")
                console.print("Make sure backend is running: [cyan]aico gateway status[/cyan]")
                return
            
            console.print("[dim]Initializing extractor...[/dim]")
            extractor = MultiPassExtractor(modelservice, config)
            
            # Extract
            console.print("[dim]Extracting entities and relationships...[/dim]")
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


@app.command(name="query", help="Query knowledge graph semantically or with GQL/Cypher.")
def query(
    query_text: Optional[str] = typer.Argument(None, help="Query text or GQL/Cypher query"),
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
    label: Optional[str] = typer.Option(None, "--label", "-l", help="Filter by node label (semantic search only)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of results (semantic search only)"),
    gql: bool = typer.Option(False, "--gql", help="Execute as GQL/Cypher query"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read query from file"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, csv")
):
    """
    Query knowledge graph semantically or with GQL/Cypher.
    
    Examples:
      Semantic search: aico kg query "Where do I live?" --user-id user_123
      GQL query: aico kg query --gql "MATCH (p:PERSON) RETURN p.name" --user-id user_123
      From file: aico kg query --gql --file query.cypher --user-id user_123
    """
    async def _query():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        from aico.ai.knowledge_graph import PropertyGraphStorage
        from aico.ai.knowledge_graph.query import GQLQueryExecutor
        import chromadb
        from chromadb.config import Settings
        from pathlib import Path
        
        try:
            # Read query from file if specified, otherwise use argument
            final_query_text = query_text
            if file:
                query_path = Path(file)
                if not query_path.exists():
                    console.print(f"[red]Error: File not found: {file}[/red]")
                    raise typer.Exit(1)
                final_query_text = query_path.read_text()
                console.print(f"[dim]Reading query from: {file}[/dim]\n")
            
            # Validate query text
            if not final_query_text:
                console.print("[red]Error: Query text required (provide as argument or via --file)[/red]")
                raise typer.Exit(1)
            
            # Initialize storage
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
            chromadb_path = AICOPaths.get_semantic_memory_path()
            chromadb_client = chromadb.PersistentClient(
                path=str(chromadb_path),
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            
            # Execute GQL query or semantic search
            if gql:
                # GQL/Cypher query mode
                # Escape square brackets to prevent Rich from interpreting them as markup
                escaped_query = final_query_text.replace("[", "\\[").replace("]", "\\]")
                console.print(f"[cyan]Executing GQL query:[/cyan]\n{escaped_query}\n")
                
                storage = PropertyGraphStorage(db_connection, chromadb_client, None)
                executor = GQLQueryExecutor(storage, db_connection)
                
                result = await executor.execute(final_query_text, user_id, format=format)
                
                if result["success"]:
                    if format == "json":
                        console.print(result["data"])
                    elif format == "csv":
                        console.print(result["data"])
                    else:  # table
                        console.print(result["data"])
                    
                    metadata = result["metadata"]
                    console.print(f"\n[dim]{metadata['row_count']} row(s) returned[/dim]")
                else:
                    console.print(f"[red]Query failed: {result['error']}[/red]")
                    raise typer.Exit(1)
            
            else:
                # Semantic search mode (existing behavior)
                from sentence_transformers import SentenceTransformer
                embedding_model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
                query_embedding = embedding_model.encode(final_query_text).tolist()
                
                # Build ChromaDB filter
                where_conditions = [
                    {"user_id": user_id},
                    {"is_current": 1}
                ]
                if label:
                    where_conditions.append({"label": label})
                
                where_filter = {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
                
                # Query ChromaDB directly with embedding
                console.print(f"\n[cyan]Searching for:[/cyan] {final_query_text}\n")
                collection = chromadb_client.get_collection("kg_nodes")
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=where_filter
                )
                
                # Fetch full nodes from LibSQL
                nodes = []
                if results["ids"] and results["ids"][0]:
                    storage = PropertyGraphStorage(db_connection, chromadb_client, None)
                    for node_id in results["ids"][0]:
                        node = await storage.get_node(node_id)
                        if node:
                            nodes.append(node)
                
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
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
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
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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


@app.command(name="edges", help="List relationships (edges).")
def list_edges(
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of results")
):
    """List relationships in knowledge graph."""
    async def _list_edges():
        from aico.core.paths import AICOPaths
        
        try:
            # Query database directly
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            db_connection.connect()
            
            # Get edges with node names
            query = """
                SELECT 
                    e.id,
                    e.relation_type,
                    e.confidence,
                    n1.label as source_label,
                    n1.properties as source_props,
                    n2.label as target_label,
                    n2.properties as target_props
                FROM kg_edges e
                JOIN kg_nodes n1 ON e.source_id = n1.id
                JOIN kg_nodes n2 ON e.target_id = n2.id
                WHERE e.user_id = ? AND e.is_current = 1
                ORDER BY e.created_at DESC
                LIMIT ?
            """
            
            results = db_connection.execute(query, (user_id, limit)).fetchall()
            
            if results:
                console.print(f"\n[green]Found {len(results)} relationships:[/green]\n")
                table = Table(box=box.SIMPLE)
                table.add_column("Relationship", style="cyan")
                table.add_column("Confidence", style="green")
                
                for row in results:
                    source_props = json.loads(row[4])
                    target_props = json.loads(row[6])
                    source_name = source_props.get("name", "?")
                    target_name = target_props.get("name", "?")
                    
                    relationship = f"{source_name} [{row[1]}] {target_name}"
                    table.add_row(relationship, f"{row[2]:.2f}")
                
                console.print(table)
            else:
                console.print("[yellow]No relationships found.[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    asyncio.run(_list_edges())


@app.command(name="clear", help="Clear knowledge graph data (DESTRUCTIVE).")
@destructive
def clear(
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="User ID (if not specified, clears ALL data)")
):
    """Clear knowledge graph data."""
    async def _clear():
        from aico.core.config import ConfigurationManager
        from aico.core.paths import AICOPaths
        from aico.security import AICOKeyManager
        from aico.data.libsql.encrypted import EncryptedLibSQLConnection
        
        try:
            # Get database connection
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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
        from aico.ai.knowledge_graph.graph_traversal import GraphQueryEngine
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize storage and query engine
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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
        from aico.ai.knowledge_graph.graph_traversal import GraphQueryEngine
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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
        from aico.ai.knowledge_graph.graph_traversal import GraphQueryEngine
        import chromadb
        from chromadb.config import Settings
        
        try:
            # Initialize
            db_path = AICOPaths.resolve_database_path("aico.db", "auto")
            db_connection = _get_database_connection(str(db_path))
            
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
