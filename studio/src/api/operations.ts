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
 * Fetch active user sessions
 */
export async function fetchActiveSessions(): Promise<ActiveSessionsResponse> {
  return httpJson<ActiveSessionsResponse>({
    method: 'GET',
    path: `${BASE_URL}/operations/sessions`,
  });
}
