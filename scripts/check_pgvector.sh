#!/bin/bash
# Check if pgvector is enabled and tables exist

export PGPASSWORD='IVxQahLhAmn3XgGrOlnzvq76c3SJDF0h-xVbJRl0jLw'

echo "Checking pgvector extension..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector') as pgvector_enabled;"

echo ""
echo "Checking for pgvector tables..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "SELECT tablename FROM pg_tables WHERE schemaname = 'aico_core' AND (tablename LIKE '%segment%' OR tablename LIKE '%embedding%') ORDER BY tablename;"

echo ""
echo "Checking table counts..."
docker exec -e PGPASSWORD aico-postgres psql -U postgres -d aico -c "SELECT 'conversation_segments' as table, count(*) FROM aico_core.conversation_segments UNION ALL SELECT 'kg_node_embeddings', count(*) FROM aico_core.kg_node_embeddings UNION ALL SELECT 'kg_edge_embeddings', count(*) FROM aico_core.kg_edge_embeddings;" 2>/dev/null || echo "Tables don't exist yet"
