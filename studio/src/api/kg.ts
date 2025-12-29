/**
 * Knowledge Graph API
 * 
 * Functions for fetching knowledge graph data from backend API.
 */

import { httpJson } from './http';

export interface KGNode {
  id: string;
  user_id: string;
  label: string;
  properties: Record<string, any>;
  confidence: number;
  source_text: string;
  created_at: string;
  updated_at: string;
  valid_from?: string;
  valid_until?: string;
  is_current: number;
  canonical_id?: string;
  aliases?: string[];
}

export interface KGEdge {
  id: string;
  user_id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  properties: Record<string, any>;
  confidence: number;
  source_text: string;
  created_at: string;
  updated_at: string;
  valid_from?: string;
  valid_until?: string;
  is_current: number;
}

export interface HealthMetrics {
  orphaned_edges: number;
  duplicate_nodes: number;
  stale_nodes_count: number;
  stale_nodes_percent: number;
  property_completeness: number;
  nodes_added_24h: number;
  edges_added_24h: number;
}

export interface StructureMetrics {
  graph_density: number;
  average_degree: number;
  max_degree: number;
  min_degree: number;
  isolated_nodes: number;
  connected_components: number;
  largest_component_size: number;
}

export interface CentralityNode {
  id: string;
  label: string;
  name: string;
  degree?: number;
  score?: number;
}

export interface CentralityMetrics {
  top_by_degree: CentralityNode[];
  top_by_pagerank: CentralityNode[];
  top_by_betweenness: CentralityNode[];
}

export interface TemporalMetrics {
  growth_rate_7d: number;
  growth_rate_30d: number;
  most_active_day: string | null;
  activity_by_day: Record<string, number>;
}

export interface ClusteringMetrics {
  global_clustering_coefficient: number;
  average_clustering_coefficient: number;
  communities_detected: number;
  modularity_score: number;
}

export interface DuplicateNodePair {
  id1: string;
  name1: string;
  label1: string;
  id2: string;
  name2: string;
  label2: string;
  similarity: number;
}

export interface GraphStats {
  total_nodes: number;
  current_nodes: number;
  historical_nodes: number;
  total_edges: number;
  current_edges: number;
  historical_edges: number;
  total_node_properties: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
  storage_size_mb: number;
  user_id: string;
  health: HealthMetrics;
  duplicate_pairs?: DuplicateNodePair[];
  structure: StructureMetrics;
  temporal: TemporalMetrics;
  centrality: CentralityMetrics;
  clustering: ClusteringMetrics;
}

export interface NodesResponse {
  nodes: KGNode[];
  total: number;
  limit: number;
  offset: number;
}

export interface EdgesResponse {
  edges: KGEdge[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchGraphStats(): Promise<GraphStats> {
  return httpJson<GraphStats>({
    method: 'GET',
    path: '/kg/stats',
  });
}

export async function fetchNodes(limit: number = 100, offset: number = 0): Promise<NodesResponse> {
  return httpJson<NodesResponse>({
    method: 'GET',
    path: '/kg/nodes',
    query: { limit, offset },
  });
}

export async function fetchEdges(limit: number = 100, offset: number = 0): Promise<EdgesResponse> {
  return httpJson<EdgesResponse>({
    method: 'GET',
    path: '/kg/edges',
    query: { limit, offset },
  });
}

export async function executeGQLQuery(query: string, format: string = 'json'): Promise<any> {
  return httpJson<any>({
    method: 'POST',
    path: '/kg/query',
    body: { query, format },
  });
}
