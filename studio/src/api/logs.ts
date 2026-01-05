/**
 * Logs API Client
 * 
 * High-performance API client for querying 8.4M+ log entries
 * Uses admin endpoints at /api/v1/admin/logs with admin authentication
 */

import { httpJson } from './http';

const BASE_URL = '/admin/logs';

export interface LogEvent {
  id: string;
  timestamp: string;
  level: string;
  subsystem: string;
  module: string;
  function: string;
  message: string;
  topic?: string;
  extra_data?: Record<string, any>;
}

export interface LogKPIs {
  error_rate: number;
  error_rate_trend: number;
  log_volume: number;
  log_volume_trend: number;
  error_distribution: {
    error: number;
    warning: number;
    info: number;
    debug: number;
  };
  service_health: number;
  mttd: number;
  storage_usage: number;
  storage_total: number;
  top_error_source: string;
  error_velocity: number;
  log_latency: number;
}

export interface HistogramDataPoint {
  hour: number;
  error: number;
  warning: number;
  info: number;
  debug: number;
}

export interface LogsQueryParams {
  limit?: number;
  offset?: number;
  level?: string;
  subsystem?: string;
  module?: string;
  since?: string;
  until?: string;
  search?: string;
}

export interface LogsQueryResponse {
  logs: LogEvent[];
  total: number;
  has_more: boolean;
}

/**
 * Get log events with filtering and pagination
 */
export async function getLogEvents(params: LogsQueryParams = {}): Promise<LogsQueryResponse> {
  const queryParams = new URLSearchParams();
  
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());
  if (params.level) queryParams.append('level', params.level);
  if (params.subsystem) queryParams.append('subsystem', params.subsystem);
  if (params.module) queryParams.append('module', params.module);
  if (params.since) queryParams.append('since', params.since);
  if (params.until) queryParams.append('until', params.until);
  if (params.search) queryParams.append('search', params.search);
  
  return httpJson({
    method: 'GET',
    path: `${BASE_URL}?${queryParams.toString()}`,
  });
}

/**
 * Get log statistics and KPIs
 */
export async function getLogKPIs(): Promise<LogKPIs> {
  const stats: any = await httpJson({
    method: 'GET',
    path: `${BASE_URL}/stats`,
  });
  
  // Transform stats response to KPIs format
  const total = stats.total_logs || 0;
  const byLevel = stats.by_level || {};
  const errorCount = byLevel.ERROR || 0;
  
  return {
    error_rate: total > 0 ? (errorCount / total) * 100 : 0,
    error_rate_trend: stats.error_rate_trend || 0,
    log_volume: total,
    log_volume_trend: stats.log_volume_trend || 0,
    error_distribution: {
      error: byLevel.ERROR || 0,
      warning: byLevel.WARNING || 0,
      info: byLevel.INFO || 0,
      debug: byLevel.DEBUG || 0,
    },
    service_health: total > 0 ? ((total - errorCount) / total) * 100 : 100,
    mttd: 2.3, // Placeholder
    storage_usage: 2.3, // Placeholder
    storage_total: 10,
    top_error_source: 'unknown',
    error_velocity: 0,
    log_latency: 45,
  };
}

/**
 * Get histogram data for timeline visualization
 * Note: This uses the recent_activity from stats endpoint
 */
export async function getLogHistogram(hours: number = 24): Promise<HistogramDataPoint[]> {
  const stats: any = await httpJson({
    method: 'GET',
    path: `${BASE_URL}/stats`,
  });
  
  // Transform recent_activity to histogram format
  const recentActivity = stats.recent_activity || {};
  const result: HistogramDataPoint[] = [];
  
  for (let i = 0; i < hours; i++) {
    const hour = (new Date().getHours() - hours + i + 1 + 24) % 24;
    const hourKey = hour.toString();
    const count = recentActivity[hourKey] || 0;
    
    // Distribute count across severity levels (rough estimate)
    result.push({
      hour,
      error: Math.floor(count * 0.1),
      warning: Math.floor(count * 0.2),
      info: Math.floor(count * 0.6),
      debug: Math.floor(count * 0.1),
    });
  }
  
  return result;
}

/**
 * Get available subsystems for filtering
 */
export async function getAvailableSubsystems(): Promise<string[]> {
  const stats: any = await httpJson({
    method: 'GET',
    path: `${BASE_URL}/stats`,
  });
  
  const bySubsystem = stats.by_subsystem || {};
  return Object.keys(bySubsystem);
}
