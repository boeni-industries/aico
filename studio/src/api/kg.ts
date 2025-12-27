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

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  total_node_properties: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
  storage_size_mb: number;
  user_id: string;
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
