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
  reason?: string;
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
  reason?: string;
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

export interface QueryTemplate {
  id: string;
  title: string;
  description: string;
  category: 'exploration' | 'analysis' | 'temporal' | 'relationships';
  query: string;
  tags: string[];
}

export interface QueryTemplatesResponse {
  templates: QueryTemplate[];
}

export async function fetchQueryTemplates(): Promise<QueryTemplatesResponse> {
  return httpJson<QueryTemplatesResponse>({
    method: 'GET',
    path: '/kg/query-templates',
  });
}

export async function updateQueryTemplates(templates: QueryTemplate[]): Promise<{ success: boolean; message: string; templates_count: number }> {
  return httpJson<{ success: boolean; message: string; templates_count: number }>({
    method: 'PUT',
    path: '/kg/query-templates',
    body: { templates },
  });
}

// Temporal API Types

export interface NodeVersion {
  id: string;
  user_id: string;
  label: string;
  properties: Record<string, any>;
  confidence: number;
  source_text?: string;
  created_at: string;
  updated_at: string;
  valid_from: string;
  valid_until?: string | null;
  is_current: number;
  canonical_id?: string;
  aliases: string[];
  reason?: string;
}

export interface NodeHistoryResponse {
  canonical_id: string;
  total_versions: number;
  versions: NodeVersion[];
}

export interface ChangeRecord {
  change_type: 'node_created' | 'node_updated' | 'node_deleted' | 
                'edge_created' | 'edge_updated' | 'edge_deleted';
  entity_type: 'node' | 'edge';
  entity_id: string;
  entity_label?: string;
  timestamp: string;
  properties_changed?: string[];
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  source_text?: string;
  reason?: string;
}

export interface ChangesResponse {
  from_timestamp: string;
  to_timestamp: string;
  total_changes: number;
  changes: ChangeRecord[];
}

export interface TemporalGraphRequest {
  as_of: string;
  include_edges?: boolean;
  node_limit?: number;
}

export interface TemporalGraphResponse {
  as_of: string;
  total_nodes: number;
  total_edges: number;
  nodes: NodeVersion[];
  edges: KGEdge[];
}

export interface GraphComparisonRequest {
  from_timestamp: string;
  to_timestamp: string;
}

export interface GraphDiff {
  nodes_added: number;
  nodes_removed: number;
  nodes_modified: number;
  edges_added: number;
  edges_removed: number;
  edges_modified: number;
  added_node_ids: string[];
  removed_node_ids: string[];
  modified_node_ids: string[];
}

export interface GraphComparisonResponse {
  from_timestamp: string;
  to_timestamp: string;
  diff: GraphDiff;
  from_state: Record<string, number>;
  to_state: Record<string, number>;
}

// Temporal API Functions

export async function fetchNodeHistory(nodeId: string): Promise<NodeHistoryResponse> {
  return httpJson<NodeHistoryResponse>({
    method: 'GET',
    path: `/kg/nodes/${nodeId}/history`,
  });
}

export async function fetchChanges(
  fromTimestamp: string,
  toTimestamp: string,
  limit: number = 100
): Promise<ChangesResponse> {
  return httpJson<ChangesResponse>({
    method: 'GET',
    path: '/kg/changes',
    query: { from_timestamp: fromTimestamp, to_timestamp: toTimestamp, limit },
  });
}

export async function fetchTemporalGraphState(
  request: TemporalGraphRequest
): Promise<TemporalGraphResponse> {
  return httpJson<TemporalGraphResponse>({
    method: 'POST',
    path: '/kg/temporal',
    body: request,
  });
}

export async function compareGraphStates(
  request: GraphComparisonRequest
): Promise<GraphComparisonResponse> {
  return httpJson<GraphComparisonResponse>({
    method: 'POST',
    path: '/kg/compare',
    body: request,
  });
}
