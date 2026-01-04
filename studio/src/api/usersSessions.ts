/**
 * Users & Sessions API Client
 * 
 * Provides functions to fetch user and session management data.
 */

import { httpJson } from './http';

const BASE_URL = 'http://localhost:8771/api/v1';

// ============================================================================
// Type Definitions
// ============================================================================

export interface UserProfile {
  uuid: string;
  full_name: string;
  nickname?: string;
  user_type: string;
  is_active: boolean;
  primary_language?: string;
  created_at: string;
  updated_at: string;
}

export interface UserCredentials {
  has_pin: boolean;
  failed_attempts: number;
  is_locked: boolean;
  locked_until?: string;
  last_login?: string;
}

export interface DeviceInfo {
  uuid: string;
  device_name: string;
  device_type: string;
  platform: string;
  last_seen?: string;
  is_active: boolean;
}

export interface SessionDetail {
  uuid: string;
  user_uuid: string;
  device_uuid: string;
  session_type: string;
  expires_at: string;
  created_at: string;
  is_active: boolean;
  time_remaining?: string;
}

export interface SessionWithUser extends SessionDetail {
  user_full_name: string;
  user_nickname?: string;
  user_type: string;
  device_name?: string;
  device_type?: string;
}

export interface UserWithSessions extends UserProfile {
  active_session_count: number;
  total_session_count: number;
  last_activity?: string;
  credentials?: UserCredentials;
}

export interface UsersListResponse {
  users: UserWithSessions[];
  total_users: number;
  active_users: number;
}

export interface SessionsListResponse {
  sessions: SessionWithUser[];
  total_sessions: number;
  active_sessions: number;
}

export interface UserDetailResponse {
  user: UserProfile;
  credentials?: UserCredentials;
  active_sessions: SessionDetail[];
  devices: DeviceInfo[];
  statistics: {
    total_sessions: number;
    active_sessions: number;
    expired_sessions: number;
    registered_devices: number;
  };
}

export interface SessionStatistics {
  total_sessions: number;
  active_sessions: number;
  expired_sessions: number;
  sessions_by_type: Record<string, number>;
  sessions_by_device_type: Record<string, number>;
  average_session_duration?: number;
}

export interface SessionStatsResponse {
  statistics: SessionStatistics;
  recent_activity: Array<{
    session_uuid: string;
    created_at: string;
    user_name: string;
    session_type: string;
    device_type: string;
  }>;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch list of users with session information
 */
export async function fetchUsers(params?: {
  user_type?: string;
  is_active?: boolean;
  has_sessions?: boolean;
}): Promise<UsersListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.user_type) queryParams.append('user_type', params.user_type);
  if (params?.is_active !== undefined) queryParams.append('is_active', String(params.is_active));
  if (params?.has_sessions !== undefined) queryParams.append('has_sessions', String(params.has_sessions));
  
  const query = queryParams.toString();
  return httpJson<UsersListResponse>({
    method: 'GET',
    path: `${BASE_URL}/users-sessions/users${query ? `?${query}` : ''}`,
  });
}

/**
 * Fetch detailed information for a specific user
 */
export async function fetchUserDetail(userUuid: string): Promise<UserDetailResponse> {
  return httpJson<UserDetailResponse>({
    method: 'GET',
    path: `${BASE_URL}/users-sessions/users/${userUuid}`,
  });
}

/**
 * Fetch list of sessions with user information
 */
export async function fetchSessions(params?: {
  user_uuid?: string;
  session_type?: string;
  is_active?: boolean;
  device_type?: string;
}): Promise<SessionsListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.user_uuid) queryParams.append('user_uuid', params.user_uuid);
  if (params?.session_type) queryParams.append('session_type', params.session_type);
  if (params?.is_active !== undefined) queryParams.append('is_active', String(params.is_active));
  if (params?.device_type) queryParams.append('device_type', params.device_type);
  
  const query = queryParams.toString();
  return httpJson<SessionsListResponse>({
    method: 'GET',
    path: `${BASE_URL}/users-sessions/sessions${query ? `?${query}` : ''}`,
  });
}

/**
 * Fetch session statistics and analytics
 */
export async function fetchSessionStatistics(): Promise<SessionStatsResponse> {
  return httpJson<SessionStatsResponse>({
    method: 'GET',
    path: `${BASE_URL}/users-sessions/statistics`,
  });
}
