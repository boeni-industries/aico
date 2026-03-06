#!/usr/bin/env python3
"""
One-off migration script: ChromaDB → Postgres/pgvector

Migrates all ChromaDB collections (conversation_segments, kg_nodes, kg_edges)
to Postgres tables with pgvector embeddings.

Usage:
    python scripts/migrate_chroma_to_pgvector.py

Requirements:
    - Postgres with pgvector extension installed
    - ChromaDB data directory exists
    - Postgres credentials in keyring (run 'aico deploy pg' first)
"""

import json
import subprocess
import sys
from pathlib import Path

import os

from typing import Optional

def _read_pg_password_from_docker_env() -> Optional[str]:
    env_path = Path(__file__).parent.parent / "docker" / ".env"
    if not env_path.exists():
        return None
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "AICO_PG_PASSWORD":
                return v.strip()
    except Exception:
        return None
    return None


def _pg_escape_literal(value: str) -> str:
    return value.replace("'", "''")


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _try_parse_json(s: str):
    if not isinstance(s, str):
        return None
    t = s.strip()
    if not t:
        return None
    if not (t.startswith("{") or t.startswith("[")):
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


def _ts_or_epoch(value) -> str:
    # Postgres accepts ISO strings; fall back to epoch.
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "1970-01-01T00:00:00Z"


def _vector_literal(vec) -> str:
    # pgvector input format: '[1,2,3]'
    # ensure JSON-ish with floats
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


def _run_psql_sql(sql: str, *, password: str, db_name: str, user: str) -> None:
    # Use dockerized Postgres to avoid requiring host psql/libpq.
    # This assumes the container name is 'aico-postgres' (as in docker-compose.local.yml)
    cmd = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={password}",
        "aico-postgres",
        "psql",
        "-U",
        user,
        "-d",
        db_name,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    subprocess.run(cmd, input=sql.encode("utf-8"), check=True)


def _ensure_migration_tables(*, password: str, db_name: str, user: str) -> None:
    # Mapping from legacy Chroma IDs to canonical Postgres KG node IDs
    _run_psql_sql(
        """
        CREATE TABLE IF NOT EXISTS aico_core.migration_chroma_node_map (
            chroma_id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS aico_core.migration_chroma_edge_map (
            chroma_id TEXT PRIMARY KEY,
            edge_id TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        password=password,
        db_name=db_name,
        user=user,
    )

def main():
    print("=" * 80)
    print("ChromaDB → Postgres/pgvector Migration")
    print("=" * 80)
    print()

    # Postgres credentials
    # This script writes to Postgres via `docker exec ... psql`, so we only need:
    # - db name (default: aico)
    # - user (default: postgres)
    # - password (docker/.env or env var)
    db_name = os.environ.get("AICO_PG_DB", "aico")
    user = os.environ.get("AICO_PG_USER", "postgres")

    password = _read_pg_password_from_docker_env() or os.environ.get("AICO_PG_PASSWORD")
    if not password:
        print("❌ ERROR: Postgres password not available")
        print("   Provide it via env var: AICO_PG_PASSWORD=... python scripts/migrate_chroma_to_pgvector.py")
        print("   Or ensure docker/.env contains AICO_PG_PASSWORD=...")
        sys.exit(1)
    
    # Check ChromaDB directory
    # One-off migration: legacy runtime directory structure (macOS)
    semantic_dir = Path.home() / "Library/Application Support/aico/data/memory/semantic"
    if not semantic_dir.exists():
        print(f"❌ ERROR: ChromaDB directory not found at {semantic_dir}")
        sys.exit(1)
    
    print(f"✓ ChromaDB directory: {semantic_dir}")
    print(f"✓ Postgres: {user}@docker:aico-postgres/{db_name}")
    print()
    
    # Import dependencies
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as e:
        print(f"❌ ERROR: Missing dependency: {e}")
        print("   Install: pip install chromadb")
        sys.exit(1)
    
    # Connect to ChromaDB
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(
        path=str(semantic_dir),
        settings=Settings(allow_reset=True, anonymized_telemetry=False),
    )
    
    collections = client.list_collections()
    if not collections:
        print("⚠️  No ChromaDB collections found - nothing to migrate")
        return
    
    print(f"✓ Found {len(collections)} collections: {[c.name for c in collections]}")
    print()
    
    # Migrate each collection into canonical pgvector tables
    # We avoid psycopg2 dependency by sending SQL to dockerized psql.
    total_migrated = 0

    # Ensure extension + schema exists (idempotent)
    _run_psql_sql(
        """
        CREATE SCHEMA IF NOT EXISTS aico_core;
        CREATE EXTENSION IF NOT EXISTS vector;
        """,
        password=password,
        db_name=db_name,
        user=user,
    )

    _ensure_migration_tables(password=password, db_name=db_name, user=user)

    for coll in collections:
        name = coll.name
        collection = client.get_collection(name)
        count = collection.count()
        if count == 0:
            print(f"⊘ Skipping empty collection: {name}")
            continue

        print(f"→ Migrating {name} ({count} documents)")

        batch_size = 250
        offset = 0
        migrated = 0

        while offset < count:
            chunk = collection.get(
                limit=batch_size,
                offset=offset,
                include=["embeddings", "documents", "metadatas"],
            )
            if chunk is None:
                chunk = {}

            ids = chunk.get("ids")
            if ids is None:
                ids = []
            if not ids:
                break

            docs = chunk.get("documents")
            if docs is None:
                docs = []

            metas = chunk.get("metadatas")
            if metas is None:
                metas = []

            embs = chunk.get("embeddings")
            if embs is None:
                embs = []

            statements = ["BEGIN;"]

            if name == "conversation_segments":
                for i, _id in enumerate(ids):
                    emb = embs[i]
                    doc = docs[i] if i < len(docs) else None
                    meta = metas[i] if i < len(metas) else {}

                    # Map to canonical columns
                    user_id = str(meta.get("user_id") or "")
                    conversation_id = str(meta.get("conversation_id") or "")
                    role = str(meta.get("role") or "")
                    content = str(doc or "")
                    ts = str(meta.get("timestamp") or meta.get("created_at") or "")

                    # store original meta blob
                    meta_json = json.dumps(meta, ensure_ascii=False)
                    vec = _vector_literal(emb)

                    statements.append(
                        """
                        INSERT INTO aico_core.conversation_segments
                          (id, user_id, conversation_id, role, content, embedding, timestamp, metadata)
                        VALUES
                          ('{id}', '{user_id}', '{conversation_id}', '{role}', '{content}', '{vec}'::vector, '{ts}'::timestamptz, '{meta}'::jsonb)
                        ON CONFLICT (id) DO UPDATE SET
                          user_id = EXCLUDED.user_id,
                          conversation_id = EXCLUDED.conversation_id,
                          role = EXCLUDED.role,
                          content = EXCLUDED.content,
                          embedding = EXCLUDED.embedding,
                          timestamp = EXCLUDED.timestamp,
                          metadata = EXCLUDED.metadata;
                        """.format(
                            id=_pg_escape_literal(str(_id)),
                            user_id=_pg_escape_literal(user_id),
                            conversation_id=_pg_escape_literal(conversation_id),
                            role=_pg_escape_literal(role),
                            content=_pg_escape_literal(content),
                            vec=_pg_escape_literal(vec),
                            ts=_pg_escape_literal(ts) if ts else "1970-01-01T00:00:00Z",
                            meta=_pg_escape_literal(meta_json),
                        ).strip()
                    )

            elif name == "kg_nodes":
                for i, _id in enumerate(ids):
                    emb = embs[i]
                    doc = docs[i] if i < len(docs) else None
                    meta = metas[i] if i < len(metas) else {}
                    if meta is None:
                        meta = {}
                    parsed_doc = _try_parse_json(doc) if isinstance(doc, str) else None

                    # Base KG node row (must exist due to FK from kg_node_embeddings)
                    user_id = str(meta.get("user_id") or (parsed_doc.get("user_id") if isinstance(parsed_doc, dict) else "") or "")
                    label = str(meta.get("label") or (parsed_doc.get("label") if isinstance(parsed_doc, dict) else "") or "")
                    properties = meta.get("properties")
                    if properties is None and isinstance(parsed_doc, dict):
                        properties = parsed_doc.get("properties")
                    if properties is None:
                        properties = {}
                    confidence = meta.get("confidence")
                    if confidence is None and isinstance(parsed_doc, dict):
                        confidence = parsed_doc.get("confidence")
                    if confidence is None:
                        confidence = 1.0
                    source_text = str(meta.get("source_text") or (parsed_doc.get("source_text") if isinstance(parsed_doc, dict) else "") or (doc or ""))
                    created_at = _ts_or_epoch(meta.get("created_at") or (parsed_doc.get("created_at") if isinstance(parsed_doc, dict) else None))
                    updated_at = _ts_or_epoch(meta.get("updated_at") or (parsed_doc.get("updated_at") if isinstance(parsed_doc, dict) else None) or created_at)
                    valid_from = meta.get("valid_from") or (parsed_doc.get("valid_from") if isinstance(parsed_doc, dict) else None)
                    valid_until = meta.get("valid_until") or (parsed_doc.get("valid_until") if isinstance(parsed_doc, dict) else None)
                    is_current = meta.get("is_current")
                    if is_current is None and isinstance(parsed_doc, dict):
                        is_current = parsed_doc.get("is_current")
                    if is_current is None:
                        is_current = True
                    canonical_id = meta.get("canonical_id") or (parsed_doc.get("canonical_id") if isinstance(parsed_doc, dict) else None)
                    aliases_json = meta.get("aliases_json") or (parsed_doc.get("aliases_json") if isinstance(parsed_doc, dict) else None)
                    language = meta.get("language") or (parsed_doc.get("language") if isinstance(parsed_doc, dict) else None)
                    reason = meta.get("reason") or (parsed_doc.get("reason") if isinstance(parsed_doc, dict) else None)

                    # Insert/merge node by *natural key* constraint (not by id), then map chroma id -> canonical id.
                    # This prevents failures when multiple legacy node ids share the same (user_id,label,properties,is_current).
                    vec = _vector_literal(emb)
                    document = str(doc or "")
                    props_json = _json_dumps(properties)
                    meta_sql = """
                    WITH upsert AS (
                        INSERT INTO aico_core.kg_nodes
                          (id, user_id, label, properties, confidence, source_text, created_at, updated_at,
                           valid_from, valid_until, is_current, canonical_id, aliases_json, language, reason)
                        VALUES
                          ('{id}', '{user_id}', '{label}', '{props}'::jsonb, {confidence}, '{source_text}',
                           '{created_at}'::timestamptz, '{updated_at}'::timestamptz,
                           {valid_from}, {valid_until}, {is_current}, {canonical_id}, {aliases_json}, {language}, {reason})
                        ON CONFLICT ON CONSTRAINT kg_nodes_user_id_label_properties_is_current_key
                        DO UPDATE SET
                          confidence = GREATEST(aico_core.kg_nodes.confidence, EXCLUDED.confidence),
                          source_text = CASE WHEN aico_core.kg_nodes.source_text = '' THEN EXCLUDED.source_text ELSE aico_core.kg_nodes.source_text END,
                          updated_at = EXCLUDED.updated_at
                        RETURNING id
                    ), chosen AS (
                        SELECT id FROM upsert
                        UNION ALL
                        SELECT id FROM aico_core.kg_nodes
                        WHERE user_id = '{user_id}'
                          AND label = '{label}'
                          AND properties = '{props}'::jsonb
                          AND is_current = {is_current}
                        LIMIT 1
                    ), mapped AS (
                        SELECT id AS node_id FROM chosen LIMIT 1
                    ), map_ins AS (
                        INSERT INTO aico_core.migration_chroma_node_map (chroma_id, node_id)
                        SELECT '{chroma_id}', node_id FROM mapped
                        ON CONFLICT (chroma_id) DO UPDATE SET node_id = EXCLUDED.node_id, updated_at = CURRENT_TIMESTAMP
                        RETURNING node_id
                    )
                    INSERT INTO aico_core.kg_node_embeddings (node_id, embedding, document)
                    SELECT node_id, '{vec}'::vector, '{doc}'
                    FROM map_ins
                    ON CONFLICT (node_id) DO UPDATE SET
                      embedding = EXCLUDED.embedding,
                      document = EXCLUDED.document,
                      updated_at = CURRENT_TIMESTAMP;
                    """.format(
                        id=_pg_escape_literal(str(_id)),
                        chroma_id=_pg_escape_literal(str(_id)),
                        user_id=_pg_escape_literal(user_id),
                        label=_pg_escape_literal(label),
                        props=_pg_escape_literal(props_json),
                        confidence=float(confidence),
                        source_text=_pg_escape_literal(source_text),
                        created_at=_pg_escape_literal(created_at),
                        updated_at=_pg_escape_literal(updated_at),
                        valid_from=(f"'{_pg_escape_literal(str(valid_from))}'::timestamptz" if valid_from else "NULL"),
                        valid_until=(f"'{_pg_escape_literal(str(valid_until))}'::timestamptz" if valid_until else "NULL"),
                        is_current=("true" if bool(is_current) else "false"),
                        canonical_id=(f"'{_pg_escape_literal(str(canonical_id))}'" if canonical_id else "NULL"),
                        aliases_json=(f"'{_pg_escape_literal(_json_dumps(aliases_json))}'::jsonb" if aliases_json is not None else "NULL"),
                        language=(f"'{_pg_escape_literal(str(language))}'" if language else "NULL"),
                        reason=(f"'{_pg_escape_literal(str(reason))}'" if reason else "NULL"),
                        vec=_pg_escape_literal(vec),
                        doc=_pg_escape_literal(document),
                    ).strip()
                    statements.append(meta_sql)

            elif name == "kg_edges":
                for i, _id in enumerate(ids):
                    emb = embs[i]
                    doc = docs[i] if i < len(docs) else None
                    meta = metas[i] if i < len(metas) else {}
                    if meta is None:
                        meta = {}
                    parsed_doc = _try_parse_json(doc) if isinstance(doc, str) else None

                    user_id = str(meta.get("user_id") or (parsed_doc.get("user_id") if isinstance(parsed_doc, dict) else "") or "")
                    source_id = str(meta.get("source_id") or (parsed_doc.get("source_id") if isinstance(parsed_doc, dict) else "") or "")
                    target_id = str(meta.get("target_id") or (parsed_doc.get("target_id") if isinstance(parsed_doc, dict) else "") or "")
                    relation_type = str(meta.get("relation_type") or (parsed_doc.get("relation_type") if isinstance(parsed_doc, dict) else "") or "")
                    if not source_id or not target_id or not relation_type:
                        # Can't satisfy kg_edges schema; skip this edge (and its embedding)
                        continue

                    # Translate legacy source/target ids via node map (if present)
                    src_expr = (
                        "(SELECT node_id FROM aico_core.migration_chroma_node_map WHERE chroma_id = '{cid}' LIMIT 1)".format(
                            cid=_pg_escape_literal(source_id)
                        )
                    )
                    tgt_expr = (
                        "(SELECT node_id FROM aico_core.migration_chroma_node_map WHERE chroma_id = '{cid}' LIMIT 1)".format(
                            cid=_pg_escape_literal(target_id)
                        )
                    )
                    # Ensure referenced nodes exist (stub if missing). Use the *original* ids for the stubs to satisfy FK.
                    # Stubs are inserted with is_current=false to avoid violating unique natural-key constraints.
                    for node_id in (source_id, target_id):
                        statements.append(
                            """
                            INSERT INTO aico_core.kg_nodes
                              (id, user_id, label, properties, confidence, source_text, created_at, updated_at, is_current)
                            VALUES
                              ('{id}', '{user_id}', '{label}', '{{}}'::jsonb, 1.0, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, false)
                            ON CONFLICT (id) DO NOTHING;
                            """.format(
                                id=_pg_escape_literal(str(node_id)),
                                user_id=_pg_escape_literal(user_id),
                                label=_pg_escape_literal(str(node_id)),
                            ).strip()
                        )

                    properties = meta.get("properties")
                    if properties is None and isinstance(parsed_doc, dict):
                        properties = parsed_doc.get("properties")
                    confidence = meta.get("confidence")
                    if confidence is None and isinstance(parsed_doc, dict):
                        confidence = parsed_doc.get("confidence")
                    source_text = str(meta.get("source_text") or (parsed_doc.get("source_text") if isinstance(parsed_doc, dict) else "") or (doc or ""))
                    created_at = _ts_or_epoch(meta.get("created_at") or (parsed_doc.get("created_at") if isinstance(parsed_doc, dict) else None))
                    updated_at = _ts_or_epoch(meta.get("updated_at") or (parsed_doc.get("updated_at") if isinstance(parsed_doc, dict) else None) or created_at)
                    valid_from = meta.get("valid_from") or (parsed_doc.get("valid_from") if isinstance(parsed_doc, dict) else None)
                    valid_until = meta.get("valid_until") or (parsed_doc.get("valid_until") if isinstance(parsed_doc, dict) else None)
                    is_current = meta.get("is_current")
                    if is_current is None and isinstance(parsed_doc, dict):
                        is_current = parsed_doc.get("is_current")
                    if is_current is None:
                        is_current = True
                    reason = meta.get("reason") or (parsed_doc.get("reason") if isinstance(parsed_doc, dict) else None)

                    if properties is None:
                        props_expr = "NULL"
                    else:
                        props_expr = f"'{_pg_escape_literal(_json_dumps(properties))}'::jsonb"

                    conf_expr = "NULL" if confidence is None else str(float(confidence))

                    # Insert edge and embedding using canonicalized endpoints when possible.
                    vec = _vector_literal(emb)
                    document = str(doc or "")
                    edge_sql = """
                    WITH endpoints AS (
                        SELECT
                          COALESCE({src_map}, '{src_raw}') AS source_id,
                          COALESCE({tgt_map}, '{tgt_raw}') AS target_id
                    ), upsert AS (
                        INSERT INTO aico_core.kg_edges
                          (id, user_id, source_id, target_id, relation_type, properties, confidence, source_text,
                           created_at, updated_at, valid_from, valid_until, is_current, reason)
                        SELECT
                          '{id}', '{user_id}', source_id, target_id, '{relation_type}', {props}, {confidence}, '{source_text}',
                          '{created_at}'::timestamptz, '{updated_at}'::timestamptz,
                          {valid_from}, {valid_until}, {is_current}, {reason}
                        FROM endpoints
                        ON CONFLICT ON CONSTRAINT kg_edges_user_id_source_id_target_id_relation_type_is_curre_key
                        DO UPDATE SET
                          confidence = COALESCE(EXCLUDED.confidence, aico_core.kg_edges.confidence),
                          properties = COALESCE(EXCLUDED.properties, aico_core.kg_edges.properties),
                          source_text = CASE WHEN aico_core.kg_edges.source_text = '' THEN EXCLUDED.source_text ELSE aico_core.kg_edges.source_text END,
                          updated_at = EXCLUDED.updated_at,
                          reason = COALESCE(EXCLUDED.reason, aico_core.kg_edges.reason)
                        RETURNING id
                    ), map_ins AS (
                        INSERT INTO aico_core.migration_chroma_edge_map (chroma_id, edge_id)
                        SELECT '{chroma_id}', id FROM upsert
                        ON CONFLICT (chroma_id) DO UPDATE SET edge_id = EXCLUDED.edge_id, updated_at = CURRENT_TIMESTAMP
                        RETURNING edge_id
                    )
                    INSERT INTO aico_core.kg_edge_embeddings (edge_id, embedding, document)
                    SELECT edge_id, '{vec}'::vector, '{doc}'
                    FROM map_ins
                    ON CONFLICT (edge_id) DO UPDATE SET
                      embedding = EXCLUDED.embedding,
                      document = EXCLUDED.document,
                      updated_at = CURRENT_TIMESTAMP;
                    """.format(
                        id=_pg_escape_literal(str(_id)),
                        chroma_id=_pg_escape_literal(str(_id)),
                        user_id=_pg_escape_literal(user_id),
                        relation_type=_pg_escape_literal(relation_type),
                        props=props_expr,
                        confidence=conf_expr,
                        source_text=_pg_escape_literal(source_text),
                        created_at=_pg_escape_literal(created_at),
                        updated_at=_pg_escape_literal(updated_at),
                        valid_from=(f"'{_pg_escape_literal(str(valid_from))}'::timestamptz" if valid_from else "NULL"),
                        valid_until=(f"'{_pg_escape_literal(str(valid_until))}'::timestamptz" if valid_until else "NULL"),
                        is_current=("true" if bool(is_current) else "false"),
                        reason=(f"'{_pg_escape_literal(str(reason))}'" if reason else "NULL"),
                        vec=_pg_escape_literal(vec),
                        doc=_pg_escape_literal(document),
                        src_map=src_expr,
                        tgt_map=tgt_expr,
                        src_raw=_pg_escape_literal(source_id),
                        tgt_raw=_pg_escape_literal(target_id),
                    ).strip()
                    statements.append(edge_sql)

            else:
                print(f"⚠️  Skipping unknown collection: {name}")
                break

            statements.append("COMMIT;")
            _run_psql_sql(
                "\n".join(statements) + "\n",
                password=password,
                db_name=db_name,
                user=user,
            )

            migrated += len(ids)
            offset += len(ids)
            print(f"  ✓ {migrated}/{count} documents migrated", end="\r")

        print(f"  ✓ {migrated}/{count} documents migrated")
        total_migrated += migrated
    
    print()
    print("=" * 80)
    print(f"✅ Migration completed: {total_migrated} total documents migrated")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Verify data: SELECT count(*) FROM aico_core.conversation_segments;")
    print("  2. Verify data: SELECT count(*) FROM aico_core.kg_node_embeddings;")
    print("  3. Verify data: SELECT count(*) FROM aico_core.kg_edge_embeddings;")
    print()

if __name__ == "__main__":
    main()
