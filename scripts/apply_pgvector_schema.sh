#!/bin/bash
# Apply pgvector schema to live database

export PGPASSWORD='IVxQahLhAmn3XgGrOlnzvq76c3SJDF0h-xVbJRl0jLw'

echo "Enabling pgvector extension..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "Creating schema..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE SCHEMA IF NOT EXISTS aico_core;"

echo ""
echo "Setting search path..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "SET search_path TO aico_core, public;"

echo ""
echo "Creating conversation_segments table..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico << 'EOF'
CREATE TABLE IF NOT EXISTS aico_core.conversation_segments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
EOF

echo ""
echo "Creating indexes for conversation_segments..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE INDEX IF NOT EXISTS idx_conversation_segments_user ON aico_core.conversation_segments (user_id);"
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE INDEX IF NOT EXISTS idx_conversation_segments_conversation ON aico_core.conversation_segments (conversation_id);"
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE INDEX IF NOT EXISTS idx_conversation_segments_timestamp ON aico_core.conversation_segments (timestamp DESC);"
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE INDEX IF NOT EXISTS idx_conversation_segments_embedding ON aico_core.conversation_segments USING hnsw (embedding vector_cosine_ops);"

echo ""
echo "Creating kg_node_embeddings table..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico << 'EOF'
CREATE TABLE IF NOT EXISTS aico_core.kg_node_embeddings (
    node_id TEXT PRIMARY KEY,
    embedding vector(384) NOT NULL,
    document TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
EOF

echo ""
echo "Creating index for kg_node_embeddings..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE INDEX IF NOT EXISTS idx_kg_node_embeddings_vector ON aico_core.kg_node_embeddings USING hnsw (embedding vector_cosine_ops);"

echo ""
echo "Creating kg_edge_embeddings table..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico << 'EOF'
CREATE TABLE IF NOT EXISTS aico_core.kg_edge_embeddings (
    edge_id TEXT PRIMARY KEY,
    embedding vector(384) NOT NULL,
    document TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
EOF

echo ""
echo "Creating index for kg_edge_embeddings..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "CREATE INDEX IF NOT EXISTS idx_kg_edge_embeddings_vector ON aico_core.kg_edge_embeddings USING hnsw (embedding vector_cosine_ops);"

echo ""
echo "✅ Schema applied successfully!"
