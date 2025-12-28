#!/usr/bin/env python3
"""
Clean ChromaDB edge embeddings to match current libSQL state.
Removes stale embeddings (23 embeddings vs 11 current edges).
"""

import asyncio
import chromadb
from pathlib import Path
import os

async def main():
    # Get ChromaDB path
    data_dir = Path.home() / "Library" / "Application Support" / "aico" / "data"
    chroma_path = data_dir / "chromadb"
    
    print(f"📂 ChromaDB path: {chroma_path}")
    
    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Get or create kg_edges collection
    try:
        collection = client.get_collection("kg_edges")
    except Exception:
        print("   ℹ️  Collection doesn't exist yet, will be created on next extraction")
        return
    
    # Get all edge IDs
    all_edges = collection.get()
    print(f"\n📊 Current state:")
    print(f"   ChromaDB edge embeddings: {len(all_edges['ids'])}")
    
    # Delete all embeddings
    if all_edges['ids']:
        print(f"\n🗑️  Deleting {len(all_edges['ids'])} edge embeddings...")
        collection.delete(ids=all_edges['ids'])
        print(f"   ✅ Deleted all edge embeddings")
    
    # Verify
    remaining = collection.get()
    print(f"\n✅ Final state:")
    print(f"   ChromaDB edge embeddings: {len(remaining['ids'])}")
    print(f"\nℹ️  Edge embeddings will be regenerated on next extraction run")

if __name__ == "__main__":
    asyncio.run(main())
