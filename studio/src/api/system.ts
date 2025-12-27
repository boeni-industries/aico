/**
 * System API Client
 * 
 * Provides functions to fetch system-wide metrics and overview data.
 */

import { httpJson } from './http';

const BASE_URL = 'http://localhost:8771/api/v1/system';

export interface SystemEvent {
  timestamp: string;
  severity: 'error' | 'warning' | 'info';
  title: string;
  description: string;
  domain: string;
  count: number;
}

export interface SystemOverview {
  uptime_seconds: number;
  uptime_formatted: string;
  active_conversations: number;
  active_goals: number;
  system_status: string;
  recent_events: SystemEvent[];
}

/**
 * Fetch system overview metrics
 */
export async function fetchSystemOverview(): Promise<SystemOverview> {
  return httpJson<SystemOverview>({
    method: 'GET',
    path: `${BASE_URL}/overview`,
  });
}
