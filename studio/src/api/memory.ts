import { httpJson } from './http';

// ============================================================================
// Working Memory Types
// ============================================================================

export interface WorkingMemoryActivity {
  id: string;
  timestamp: string;
  action: 'read' | 'write' | 'evict';
  key: string;
}

export interface WorkingMemoryStats {
  active_items: number;
  capacity: number;
  utilization_percent: number;
  ttl_utilization_percent: number;
  eviction_rate_per_min: number;
  recent_activity: WorkingMemoryActivity[];
}

// ============================================================================
// Semantic Memory Types
// ============================================================================

export interface SemanticCollection {
  name: string;
  count: number;
  dimension: number;
}

export interface SemanticMemoryStats {
  total_vectors: number;
  collections: SemanticCollection[];
  index_size_mb: number;
  avg_retrieval_latency_ms: number;
  retrieval_quality_percent: number;
}

// ============================================================================
// Memory Album Types
// ============================================================================

export interface MemoryAlbumEntry {
  fact_id: string;
  content: string;
  content_type: string;
  category: string | null;
  tags: string[];
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
  conversation_id: string | null;
  message_id: string | null;
}

export interface MemoryAlbumListResponse {
  memories: MemoryAlbumEntry[];
  total: number;
  limit: number;
  offset: number;
}

// ============================================================================
// API Functions
// ============================================================================

export async function fetchWorkingMemoryStats(): Promise<WorkingMemoryStats> {
  const response = await httpJson<WorkingMemoryStats>({
    method: 'GET',
    path: '/memory/working/stats',
  });
  return response;
}

export async function fetchSemanticMemoryStats(): Promise<SemanticMemoryStats> {
  const response = await httpJson<SemanticMemoryStats>({
    method: 'GET',
    path: '/memory/semantic/stats',
  });
  return response;
}

export async function fetchMemoryAlbum(
  category?: string,
  favoritesOnly: boolean = false,
  limit: number = 50,
  offset: number = 0
): Promise<MemoryAlbumListResponse> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (favoritesOnly) params.append('favorites_only', 'true');
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());

  const response = await httpJson<MemoryAlbumListResponse>({
    method: 'GET',
    path: `/memory-album?${params.toString()}`,
  });
  return response;
}
