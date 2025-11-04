"""
CLI utility functions for managing the ChromaDB database.

This module provides user-facing console output for CLI ChromaDB commands.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console

from aico.core.config import ConfigurationManager
from aico.core.paths import AICOPaths

console = Console()

def get_chroma_status_cli(config: Optional[ConfigurationManager] = None) -> Dict[str, Any]:
    """Get the status of the ChromaDB database for CLI display."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    # Use new hierarchical path structure
    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    status = {
        "path": str(semantic_memory_dir),
        "exists": semantic_memory_dir.exists(),
        "size_mb": None,
        "collection_count": 0,
        "collections": {},
    }

    if not semantic_memory_dir.exists():
        return status

    try:
        # Import ChromaDB
        import chromadb
        from chromadb.config import Settings
        
        # Calculate directory size
        total_size = 0
        for file_path in semantic_memory_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        status["size_mb"] = round(total_size / (1024 * 1024), 2)
        
        # Initialize ChromaDB client with proper settings
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        # Get collections
        collections = client.list_collections()
        status["collection_count"] = len(collections)
        
        # Check embedding dimensions from first collection with data
        embedding_dimensions = None
        for collection in collections:
            try:
                count = collection.count()
                status["collections"][collection.name] = count
                
                # Get embedding dimensions from first document if available
                if count > 0 and embedding_dimensions is None:
                    result = collection.get(limit=1, include=['embeddings'])
                    if result.get('embeddings') is not None and len(result['embeddings']) > 0:
                        if result['embeddings'][0] is not None:
                            embedding_dimensions = len(result['embeddings'][0])
            except Exception as e:
                status["collections"][collection.name] = f"Error: {e}"
        
        if embedding_dimensions:
            status["embedding_dimensions"] = embedding_dimensions
        
        # Get embedding model name from config
        try:
            embedding_model = config.get("core.modelservice.transformers.models.embeddings.model_id", "unknown")
            # Extract just the model name (last part after /)
            if "/" in embedding_model:
                embedding_model = embedding_model.split("/")[-1]
            status["embedding_model"] = embedding_model
        except Exception:
            status["embedding_model"] = "unknown"
        
        status["exists"] = True

    except ImportError:
        status["error"] = "ChromaDB not installed. Install with: pip install chromadb"
    except Exception as e:
        status["error"] = str(e)

    return status

def list_chroma_collections(config: Optional[ConfigurationManager] = None) -> Dict[str, Any]:
    """List all ChromaDB collections with their metadata."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    if not semantic_memory_dir.exists():
        return {"error": "ChromaDB directory not found. Run 'aico db init' first."}

    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        collections = client.list_collections()
        
        result = {"collections": []}
        
        for collection in collections:
            try:
                count = collection.count()
                metadata = collection.metadata or {}
                
                result["collections"].append({
                    "name": collection.name,
                    "count": count,
                    "metadata": metadata
                })
            except Exception as e:
                result["collections"].append({
                    "name": collection.name,
                    "count": 0,
                    "error": str(e)
                })
        
        return result
        
    except ImportError:
        return {"error": "ChromaDB not installed. Install with: pip install chromadb"}
    except Exception as e:
        return {"error": str(e)}

def get_chroma_collection_stats(collection_name: str, config: Optional[ConfigurationManager] = None) -> Dict[str, Any]:
    """Get statistics for a specific ChromaDB collection."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    if not semantic_memory_dir.exists():
        return {"error": "ChromaDB directory not found. Run 'aico db init' first."}

    try:
        import chromadb
        from chromadb.config import Settings
        
        # Configure ChromaDB to NOT use default embedding function
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            metadata = collection.metadata or {}
            
            return {
                "count": count,
                "metadata": metadata,
                "name": collection_name
            }
        except Exception as e:
            return {"error": f"Collection '{collection_name}' not found or error accessing it: {e}"}
        
    except ImportError:
        return {"error": "ChromaDB not installed. Install with: pip install chromadb"}
    except Exception as e:
        return {"error": str(e)}

def query_chroma_collection(
    collection_name: str, 
    query_text: str, 
    limit: int = 5, 
    threshold: float = 0.0,
    config: Optional[ConfigurationManager] = None
) -> Dict[str, Any]:
    """Query a ChromaDB collection for similar documents."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    if not semantic_memory_dir.exists():
        return {"error": "ChromaDB directory not found. Run 'aico db init' first."}

    try:
        import chromadb
        from chromadb.config import Settings
        from aico.ai.memory.fusion import calculate_rrf_scores, calculate_weighted_scores
        
        # Get hybrid search configuration from config
        memory_config = config.get("core.memory.semantic", {})
        fusion_method = memory_config.get("fusion_method", "rrf")
        rrf_rank_constant = memory_config.get("rrf_rank_constant", 0)  # 0 = adaptive
        bm25_min_idf = memory_config.get("bm25_min_idf", 0.6)  # IDF filtering threshold
        min_semantic_score = memory_config.get("min_semantic_score", 0.35)  # Relevance threshold
        semantic_weight = memory_config.get("semantic_weight", 0.7)
        bm25_weight = memory_config.get("bm25_weight", 0.3)
        
        # Step 1: Generate query embeddings via modelservice
        embedding_model = config.get("core.modelservice.ollama.default_models.embedding.name", "paraphrase-multilingual")
        
        try:
            from cli.utils.zmq_client import get_embeddings
            embeddings_response = get_embeddings(embedding_model, query_text)
            if not embeddings_response.get("success"):
                return {"error": f"Failed to generate query embeddings: {embeddings_response.get('error', 'Unknown error')}"}
            
            query_embedding = embeddings_response["data"]["embedding"]
            
        except Exception as e:
            return {"error": f"Modelservice query embedding generation failed: {e}. Is modelservice running?"}
        
        # Step 2: Get ALL documents from ChromaDB for proper BM25 IDF calculation
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        try:
            collection = client.get_collection(collection_name)
            
            # Get collection size to fetch ALL documents
            collection_count = collection.count()
            
            # Query with ALL documents for proper BM25 calculation
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=collection_count  # Fetch ALL documents
            )
            
            if not results["documents"] or not results["documents"][0]:
                return {"documents": []}
            
            # Build document list
            documents = []
            for i, doc in enumerate(results["documents"][0]):
                if doc:
                    documents.append({
                        "id": results["ids"][0][i],
                        "document": doc,
                        "distance": results["distances"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })
            
            # Step 3: Calculate hybrid scores on FULL corpus using configured fusion method
            if fusion_method == "rrf":
                # Use adaptive k if config value is 0, otherwise use config value
                k = None if rrf_rank_constant == 0 else rrf_rank_constant
                scored_documents = calculate_rrf_scores(
                    documents=documents,
                    query_text=query_text,
                    k=k,
                    min_idf=bm25_min_idf,
                    min_semantic_score=min_semantic_score
                )
            else:  # weighted (legacy)
                scored_documents = calculate_weighted_scores(
                    documents=documents,
                    query_text=query_text,
                    semantic_weight=semantic_weight,
                    bm25_weight=bm25_weight,
                    min_idf=bm25_min_idf
                )
            
            # Limit results
            scored_documents = scored_documents[:limit]
            
            return {"documents": scored_documents}
            
        except Exception as e:
            return {"error": f"Error querying collection '{collection_name}': {e}"}
        
    except ImportError:
        return {"error": "ChromaDB not installed. Install with: pip install chromadb"}
    except Exception as e:
        return {"error": str(e)}

def add_chroma_document(
    collection_name: str,
    document: str,
    doc_id: Optional[str] = None,
    metadata: Optional[str] = None,
    config: Optional[ConfigurationManager] = None
) -> Dict[str, Any]:
    """Add a document to a ChromaDB collection using modelservice embeddings."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    if not semantic_memory_dir.exists():
        return {"error": "ChromaDB directory not found. Run 'aico db init' first."}

    try:
        import chromadb
        from chromadb.config import Settings
        
        # Step 1: Generate embeddings via modelservice
        embedding_model = config.get("core.modelservice.ollama.default_models.embedding.name", "paraphrase-multilingual")
        
        try:
            from cli.utils.zmq_client import get_embeddings
            console.print(f"[dim]Generating embeddings via modelservice using {embedding_model}...[/dim]")
            
            embeddings_response = get_embeddings(embedding_model, document)
            if not embeddings_response.get("success"):
                return {"error": f"Failed to generate embeddings: {embeddings_response.get('error', 'Unknown error')}"}
            
            embedding_vector = embeddings_response["data"]["embedding"]
            console.print(f"[dim]Generated {len(embedding_vector)}-dimensional embedding[/dim]")
            
        except Exception as e:
            return {"error": f"Modelservice embedding generation failed: {e}. Is modelservice running?"}
        
        # Step 2: Add to ChromaDB with pre-computed embeddings
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        try:
            # Get or create collection with proper metadata
            try:
                collection = client.get_collection(collection_name)
            except:
                # Collection doesn't exist, create it with metadata
                dimensions = len(embedding_vector)
                collection_metadata = {
                    "embedding_model": embedding_model,
                    "dimensions": dimensions,
                    "created_by": "aico_chroma_add",
                    "version": "1.0"
                }
                collection = client.create_collection(collection_name, metadata=collection_metadata)
            
            # Generate ID if not provided
            if not doc_id:
                doc_id = str(uuid.uuid4())
            
            # Parse metadata if provided
            parsed_metadata = {}
            if metadata:
                try:
                    parsed_metadata = json.loads(metadata)
                except json.JSONDecodeError as e:
                    return {"error": f"Invalid JSON metadata: {e}"}
            
            # Add document with pre-computed embeddings (bypasses ChromaDB's default embedding function)
            collection.add(
                documents=[document],
                ids=[doc_id],
                embeddings=[embedding_vector],  # Pre-computed via modelservice!
                metadatas=[parsed_metadata] if parsed_metadata else None
            )
            
            return {"id": doc_id, "success": True}
            
        except Exception as e:
            return {"error": f"Error adding document to collection '{collection_name}': {e}"}
        
    except ImportError:
        return {"error": "ChromaDB not installed. Install with: pip install chromadb"}
    except Exception as e:
        return {"error": str(e)}

def clear_chroma_cli(config: Optional[ConfigurationManager] = None) -> None:
    """Clear all documents from ChromaDB collections without deleting the collections themselves."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    try:
        if not semantic_memory_dir.exists():
            console.print(f"❌ [red]ChromaDB database not found at[/red] [cyan]{semantic_memory_dir}[/cyan]")
            console.print("💡 [yellow]Run 'aico db init' to create the database first[/yellow]")
            return
        
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(
                path=str(semantic_memory_dir),
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            # Get all collections and clear their contents
            collections = client.list_collections()
            cleared_count = 0
            
            for collection in collections:
                collection_name = collection.name
                try:
                    # Get all document IDs in the collection
                    result = collection.get()
                    if result['ids']:
                        # Delete all documents in the collection
                        collection.delete(ids=result['ids'])
                        console.print(f"🗑️ [yellow]Cleared {len(result['ids'])} documents from collection[/yellow] [cyan]{collection_name}[/cyan]")
                        cleared_count += len(result['ids'])
                    else:
                        console.print(f"ℹ️ [blue]Collection[/blue] [cyan]{collection_name}[/cyan] [blue]was already empty[/blue]")
                        
                except Exception as e:
                    console.print(f"❌ [red]Error clearing collection {collection_name}: {e}[/red]")
            
            if cleared_count > 0:
                console.print(f"✅ [green]Successfully cleared {cleared_count} total documents from {len(collections)} collections[/green]")
            else:
                console.print(f"ℹ️ [blue]All {len(collections)} collections were already empty[/blue]")
            
            console.print(f"📋 [dim]Collections preserved: {', '.join([c.name for c in collections])}[/dim]")
            
        except ImportError:
            console.print(f"❌ [red]ChromaDB not available - this should not happen with core dependencies[/red]")
            
        except Exception as e:
            console.print(f"[red]Error accessing ChromaDB: {e}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error clearing ChromaDB: {e}[/red]")


async def cleanup_old_facts_admin(days_old: int = 90) -> int:
    """Administrative function to cleanup old temporary facts"""
    try:
        from aico.core.config import ConfigurationManager
        from aico.ai.memory.semantic import SemanticMemoryStore
        
        config = ConfigurationManager()
        config.initialize(lightweight=True)
        
        semantic_store = SemanticMemoryStore(config)
        await semantic_store.initialize()
        
        return await semantic_store.cleanup_old_facts(days_old)
        
    except Exception as e:
        console.print(f"[red]Error cleaning up facts: {e}[/red]")
        return 0

def tail_chroma_collection(
    collection_name: str,
    limit: int = 10,
    full: bool = False,
    config: Optional[ConfigurationManager] = None
) -> Dict[str, Any]:
    """Get the last N documents from a ChromaDB collection."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    if not semantic_memory_dir.exists():
        return {"error": "ChromaDB directory not found. Run 'aico db init' first."}

    try:
        import chromadb
        from chromadb.config import Settings
        from rich.table import Table
        from rich import box
        
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        try:
            collection = client.get_collection(collection_name)
            
            # Get all documents first (including embeddings for --full mode)
            all_results = collection.get(
                include=["documents", "metadatas", "embeddings"]
            )
            
            if not all_results["ids"] or len(all_results["ids"]) == 0:
                return {"error": f"Collection '{collection_name}' is empty"}
            
            total_count = len(all_results["ids"])
            
            # Take the last N documents
            start_idx = max(0, total_count - limit)
            last_ids = all_results["ids"][start_idx:]
            last_documents = all_results["documents"][start_idx:] if all_results.get("documents") is not None else []
            last_metadatas = all_results["metadatas"][start_idx:] if all_results.get("metadatas") is not None else []
            last_embeddings = all_results["embeddings"][start_idx:] if all_results.get("embeddings") is not None else []
            
            # Create formatted output - vertical layout in full mode
            if full:
                # Vertical layout for full mode
                from rich.panel import Panel
                from rich.columns import Columns
                
                panels = []
                for i, doc_id in enumerate(last_ids):
                    document_text = last_documents[i] if i < len(last_documents) else ""
                    metadata = last_metadatas[i] if i < len(last_metadatas) else {}
                    
                    # Build vertical content
                    content_parts = []
                    content_parts.append(f"[bold cyan]ID:[/bold cyan] [dim]{doc_id}[/dim]")
                    content_parts.append("")
                    content_parts.append(f"[bold cyan]Document:[/bold cyan]")
                    content_parts.append(f"  {document_text}")
                    content_parts.append("")
                    
                    # Metadata - consistent order
                    if metadata:
                        content_parts.append(f"[bold cyan]Metadata:[/bold cyan]")
                        # Define consistent order for metadata fields
                        ordered_fields = ['role', 'timestamp', 'conversation_id', 'user_id']
                        
                        # Show ordered fields first
                        for key in ordered_fields:
                            if key in metadata:
                                content_parts.append(f"  [yellow]{key}:[/yellow] {metadata[key]}")
                        
                        # Show any remaining fields (excluding verbose ones)
                        for key, value in metadata.items():
                            if key not in ordered_fields and key not in ['source_message', 'fact_extraction_id', 'reasoning']:
                                content_parts.append(f"  [yellow]{key}:[/yellow] {value}")
                        content_parts.append("")
                    
                    # Embedding info
                    if len(last_embeddings) > 0 and i < len(last_embeddings):
                        embedding = last_embeddings[i]
                        if embedding is not None:
                            try:
                                emb_dim = len(embedding)
                                # Convert numpy array to list and format nicely
                                first_5 = [f"{x:.3f}" for x in embedding[:5]]
                                last_5 = [f"{x:.3f}" for x in embedding[-5:]]
                                
                                content_parts.append(f"[bold cyan]Embedding:[/bold cyan]")
                                content_parts.append(f"  [yellow]Dimensions:[/yellow] {emb_dim}")
                                content_parts.append(f"  [yellow]First 5:[/yellow] [{', '.join(first_5)}]")
                                content_parts.append(f"  [yellow]Last 5:[/yellow] [{', '.join(last_5)}]")
                            except Exception as e:
                                content_parts.append(f"[bold cyan]Embedding:[/bold cyan] [red]Error: {e}[/red]")
                    
                    panel = Panel(
                        "\n".join(content_parts),
                        title=f"[bold]Document {i+1}/{len(last_ids)}[/bold]",
                        border_style="bright_blue",
                        padding=(1, 2)
                    )
                    panels.append(panel)
                
                # Create container with title
                from rich.console import Group
                title = f"✨ [bold cyan]Last {len(last_ids)} documents from '{collection_name}' Collection[/bold cyan]"
                output = Group(title, "", *panels)
                
                return {
                    "table": output,
                    "total_count": total_count,
                    "shown_count": len(last_ids)
                }
            else:
                # Horizontal table for normal mode
                table = Table(
                    title=f"✨ [bold cyan]Last {len(last_ids)} documents from '{collection_name}' Collection[/bold cyan]",
                    title_justify="left",
                    border_style="bright_blue",
                    header_style="bold yellow",
                    box=box.SIMPLE_HEAD,
                    padding=(0, 1),
                    expand=True
                )
                
                table.add_column("ID", style="dim", width=20, no_wrap=True)
                table.add_column("Document", style="cyan", no_wrap=False, min_width=40)
                table.add_column("Metadata", style="bright_blue", no_wrap=False, width=30)
                
                for i, doc_id in enumerate(last_ids):
                    document_text = last_documents[i] if i < len(last_documents) else ""
                    metadata = last_metadatas[i] if i < len(last_metadatas) else {}
                    
                    formatted_id = doc_id[:17] + "..." if len(doc_id) > 20 else doc_id
                    formatted_document = document_text
                    
                    # Format metadata
                    if metadata:
                        metadata_parts = []
                        priority_fields = ['user_id', 'role', 'timestamp', 'conversation_id']
                        for key in priority_fields:
                            if key in metadata:
                                value = metadata[key]
                                if isinstance(value, str) and len(value) > 15:
                                    metadata_parts.append(f"{key}: {value[:12]}...")
                                else:
                                    metadata_parts.append(f"{key}: {value}")
                        formatted_metadata = "\n".join(metadata_parts) if metadata_parts else "[dim]none[/dim]"
                    else:
                        formatted_metadata = "[dim]none[/dim]"
                    
                    table.add_row(formatted_id, formatted_document, formatted_metadata)
            
            return {
                "table": table,
                "total_count": total_count,
                "shown_count": len(last_ids)
            }
            
        except Exception as e:
            return {"error": f"Collection '{collection_name}' not found or error accessing it: {e}"}
        
    except ImportError:
        return {"error": "ChromaDB not installed. Install with: pip install chromadb"}
    except Exception as e:
        return {"error": str(e)}
