#!/usr/bin/env python3
"""
Simple ChromaDB to pgvector migration script.
Runs standalone without AICO dependencies.
"""

import os
import sys
from pathlib import Path

def main():
    # Configuration
    chroma_path_raw = os.environ.get("AICO_LEGACY_CHROMA_DIR")
    if not chroma_path_raw:
        print("❌ Missing AICO_LEGACY_CHROMA_DIR")
        print("   This is a one-off legacy migration script and requires an explicit ChromaDB data directory.")
        return 1

    CHROMA_PATH = Path(chroma_path_raw)

    PG_HOST = os.environ.get("AICO_PG_HOST", "127.0.0.1")
    PG_PORT = int(os.environ.get("AICO_PG_PORT", "5432"))
    PG_DB = os.environ.get("AICO_PG_DB", "aico")
    PG_USER = os.environ.get("AICO_PG_USER", "postgres")
    PG_PASSWORD = os.environ.get("AICO_PG_PASSWORD")
    if not PG_PASSWORD:
        print("❌ Missing AICO_PG_PASSWORD")
        print("   Provide Postgres credentials via env vars for this one-off migration.")
        return 1
    
    print("=" * 80)
    print("ChromaDB → Postgres/pgvector Migration")
    print("=" * 80)
    print()
    
    # Check ChromaDB directory
    if not CHROMA_PATH.exists():
        print(f"❌ ChromaDB directory not found: {CHROMA_PATH}")
        print("   No data to migrate. Exiting.")
        return 0
    
    print(f"✓ ChromaDB directory: {CHROMA_PATH}")
    print(f"✓ Postgres: {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    
    # Import dependencies
    try:
        import chromadb
        from chromadb.config import Settings
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extras import Json
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Install: pip install chromadb psycopg2-binary")
        return 1
    
    # Connect to ChromaDB
    try:
        client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        collections = client.list_collections()
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB: {e}")
        return 1
    
    print(f"✓ Found {len(collections)} collections: {[c.name for c in collections]}")
    print()
    
    # Connect to Postgres
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD,
        )
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Failed to connect to Postgres: {e}")
        return 1
    
    # Ensure extension + schema
    cur.execute("CREATE SCHEMA IF NOT EXISTS aico_core")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("SET search_path TO aico_core, public")
    print("✓ Postgres connected, pgvector extension enabled")
    print()
    
    # Migrate each collection
    total_migrated = 0
    for coll in collections:
        name = coll.name
        collection = client.get_collection(name)
        count = collection.count()
        
        if count == 0:
            print(f"⊘ Skipping empty collection: {name}")
            continue
        
        # Get embedding dimension
        sample = collection.get(limit=1, include=["embeddings"])
        embeddings = (sample or {}).get("embeddings") or []
        if not embeddings or not embeddings[0]:
            print(f"⚠️  Skipping {name} - no embeddings found")
            continue
        
        dim = len(embeddings[0])
        table_name = f"chroma_{name}"
        
        print(f"→ Migrating {name} ({count} documents, {dim}d embeddings)")
        
        # Create table
        cur.execute(
            sql.SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    embedding vector({dim}) NOT NULL,
                    document TEXT,
                    metadata JSONB,
                    migrated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """).format(
                table=sql.Identifier(table_name),
                dim=sql.Literal(dim)
            )
        )
        
        # Migrate in batches
        batch_size = 500
        offset = 0
        migrated = 0
        
        while offset < count:
            chunk = collection.get(
                limit=batch_size,
                offset=offset,
                include=["embeddings", "documents", "metadatas"],
            )
            
            ids = (chunk or {}).get("ids") or []
            if not ids:
                break
            
            docs = (chunk or {}).get("documents") or []
            metas = (chunk or {}).get("metadatas") or []
            embs = (chunk or {}).get("embeddings") or []
            
            # Build rows
            rows = []
            for i, _id in enumerate(ids):
                emb = embs[i]
                emb_text = "[" + ",".join(str(float(x)) for x in emb) + "]"
                doc = docs[i] if i < len(docs) else None
                meta = metas[i] if i < len(metas) else None
                rows.append((_id, emb_text, doc, Json(meta) if meta is not None else None))
            
            # Bulk upsert
            args_str = ",".join(cur.mogrify("(%s,%s::vector,%s,%s)", r).decode("utf-8") for r in rows)
            cur.execute(
                sql.SQL("""
                    INSERT INTO {table} (id, embedding, document, metadata)
                    VALUES {values}
                    ON CONFLICT (id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        document = EXCLUDED.document,
                        metadata = EXCLUDED.metadata,
                        migrated_at = CURRENT_TIMESTAMP;
                """).format(
                    table=sql.Identifier(table_name),
                    values=sql.SQL(args_str)
                )
            )
            
            migrated += len(rows)
            offset += len(rows)
            print(f"  ✓ {migrated}/{count} documents migrated", end="\r")
        
        print(f"  ✓ {migrated}/{count} documents migrated")
        total_migrated += migrated
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 80)
    print(f"✅ Migration completed: {total_migrated} total documents migrated")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
