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
        
        for collection in collections:
            try:
                count = collection.count()
                status["collections"][collection.name] = count
            except Exception as e:
                status["collections"][collection.name] = f"Error: {e}"
        
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
        
        # Step 2: Query ChromaDB with pre-computed embeddings
        client = chromadb.PersistentClient(
            path=str(semantic_memory_dir),
            settings=Settings(allow_reset=True, anonymized_telemetry=False)
        )
        
        try:
            collection = client.get_collection(collection_name)
            
            # Query the collection using pre-computed embeddings
            results = collection.query(
                query_embeddings=[query_embedding],  # Use modelservice embeddings!
                n_results=limit
            )
            
            # Format results
            documents = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    distance = results["distances"][0][i] if results["distances"] else 0.0
                    
                    # Apply threshold filter
                    if distance <= threshold or threshold == 0.0:
                        documents.append({
                            "id": results["ids"][0][i] if results["ids"] else f"doc_{i}",
                            "document": results["documents"][0][i],
                            "distance": distance,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {}
                        })
            
            return {"documents": documents}
            
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
    """Clear and re-initialize the ChromaDB database with CLI feedback."""
    if config is None:
        config = ConfigurationManager()
        config.initialize(lightweight=True)

    semantic_memory_dir = AICOPaths.get_semantic_memory_path()
    
    try:
        if semantic_memory_dir.exists():
            # Remove the entire directory
            import shutil
            shutil.rmtree(semantic_memory_dir)
            console.print(f"🗑️ [yellow]Cleared existing ChromaDB database at[/yellow] [cyan]{semantic_memory_dir}[/cyan]")
        
        # Recreate the directory and initialize ChromaDB
        semantic_memory_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(
                path=str(semantic_memory_dir),
                settings=Settings(allow_reset=True, anonymized_telemetry=False)
            )
            
            # Create default collection with embedding model metadata
            collection_name = config.get("memory.semantic.collection_name", "user_facts")
            embedding_model = config.get("core.modelservice.ollama.default_models.embedding.name", "paraphrase-multilingual")
            dimensions = config.get("core.modelservice.ollama.default_models.embedding.dimensions", 768)
            
            metadata = {
                "embedding_model": embedding_model,
                "dimensions": dimensions,
                "created_by": "aico_chroma_clear",
                "version": "1.0"
            }
            client.create_collection(collection_name, metadata=metadata)
            
            console.print("✅ [green]Successfully re-initialized empty ChromaDB database.[/green]")
            console.print(f"📋 Created default collection: [cyan]{collection_name}[/cyan] with model: [cyan]{embedding_model}[/cyan]")
            
        except ImportError:
            console.print("[yellow]⚠️  ChromaDB not installed - database directory created but not initialized[/yellow]")
            console.print("[yellow]   Install with: pip install chromadb[/yellow]")

    except Exception as e:
        console.print(f"❌ [red]Failed to clear ChromaDB database: {e}[/red]")
        raise
