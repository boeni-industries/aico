/**
 * Operations API Client
 * 
 * Provides functions to fetch operations data including health, metrics, and system status.
 */

import { httpJson } from './http';

const BASE_URL = 'http://localhost:8771/api/v1';

// ============================================================================
// Health & System Metrics
// ============================================================================

export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  uptime: number;
  load_average?: number[] | null;
}

export interface ComponentHealth {
  status: string;
  uptime?: number;
  last_check: string;
  version?: string;
  details?: Record<string, any>;
}

export interface DetailedHealthResponse {
  overall_status: string;
  timestamp: string;
  system_metrics: SystemMetrics;
  components: Record<string, ComponentHealth>;
}

export interface SchedulerStatus {
  running: boolean;
  registered_tasks: number;
  scheduled_tasks: number;
  running_tasks: number;
  next_run_times: Record<string, string>;
}

// ============================================================================
// Database Stats
// ============================================================================

export interface DatabaseMetrics {
  name: string;
  type: string;
  size_bytes: number;
  status: string;
  location: string;
  error_details?: string;
  table_count?: number;
  connection_count?: number;
  wal_size_bytes?: number;
  collection_count?: number;
  document_count?: number;
  index_size_bytes?: number;
  database_count?: number;
  key_count?: number;
  map_size_bytes?: number;
}

export interface DatabaseStatsResponse {
  databases: DatabaseMetrics[];
}

// ============================================================================
// Stage 1: Database Details - Table/Collection Browser
// ============================================================================

export interface TableInfo {
  name: string;
  row_count: number;
  size_bytes?: number;
  columns?: number;
}

export interface CollectionInfo {
  name: string;
  document_count: number;
  metadata?: Record<string, any>;
  dimension?: number;
}

export interface LMDBDatabaseInfo {
  name: string;
  key_count: number;
  size_bytes?: number;
}

export interface DatabaseDetailsResponse {
  database_type: string;
  tables?: TableInfo[];
  collections?: CollectionInfo[];
  databases?: LMDBDatabaseInfo[];
}

// ============================================================================
// User Sessions
// ============================================================================

export interface UserSession {
  user_uuid: string;
  full_name: string;
  nickname?: string;
  session_count: number;
  last_activity: string;
}

export interface ActiveSessionsResponse {
  sessions: UserSession[];
  total_sessions: number;
}

// ============================================================================
// System Topology
// ============================================================================

export interface ServiceNode {
  id: string;
  name: string;
  type: string;
  status: 'healthy' | 'degraded' | 'critical' | 'offline';
  version: string;
  host: string;
  port?: number;
  uptime: string;
}

export interface ServiceConnection {
  from: string;
  to: string;
  protocol: string;
  port?: number;
  status: 'active' | 'inactive';
  latency?: number;
}

export interface TopologyData {
  services: ServiceNode[];
  connections: ServiceConnection[];
  deployment_type: string;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch detailed health status including all components
 */
export async function fetchDetailedHealth(): Promise<DetailedHealthResponse> {
  return httpJson<DetailedHealthResponse>({
    method: 'GET',
    path: `${BASE_URL}/health/detailed`,
  });
}

/**
 * Fetch scheduler status
 */
export async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  return httpJson<SchedulerStatus>({
    method: 'GET',
    path: `${BASE_URL}/scheduler/status`,
  });
}

/**
 * Fetch database statistics
 */
export async function fetchDatabaseStats(): Promise<DatabaseStatsResponse> {
  return httpJson<DatabaseStatsResponse>({
    method: 'GET',
    path: `${BASE_URL}/operations/databases`,
  });
}

/**
 * Fetch detailed database information (tables/collections/databases)
 */
export async function fetchDatabaseDetails(databaseType: string): Promise<DatabaseDetailsResponse> {
  return httpJson<DatabaseDetailsResponse>({
    method: 'GET',
    path: `${BASE_URL}/operations/databases/${databaseType}/details`,
  });
}

// ============================================================================
// Stage 2: SQL Query Interface
// ============================================================================

export interface QueryRequest {
  query: string;
  limit?: number;
  allow_destructive?: boolean;
}

export interface QueryResult {
  success: boolean;
  error?: string;
  columns: string[];
  rows: any[][];
  row_count: number;
  is_destructive: boolean;
}

export interface SchemaMetadata {
  tables: string[];
  columns: Record<string, string[]>;
}

export async function getSchemaMetadata(): Promise<SchemaMetadata> {
  return httpJson<SchemaMetadata>({
    method: 'GET',
    path: `${BASE_URL}/operations/databases/libsql/schema`,
  });
}

export async function executeSQLQuery(request: QueryRequest): Promise<QueryResult> {
  return httpJson<QueryResult>({
    method: 'POST',
    path: `${BASE_URL}/operations/databases/libsql/query`,
    body: request,
  });
}

/**
 * Fetch active user sessions
 */
export async function fetchActiveSessions(): Promise<ActiveSessionsResponse> {
  return httpJson<ActiveSessionsResponse>({
    method: 'GET',
    path: `${BASE_URL}/operations/sessions`,
  });
}

/**
 * Fetch system topology data
 */
export async function fetchTopologyData(): Promise<TopologyData> {
  return httpJson<TopologyData>({
    method: 'GET',
    path: `${BASE_URL}/operations/topology`,
  });
}
