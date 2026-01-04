/**
 * Export data utilities for CSV and JSON downloads
 */

import { UserWithSessions, SessionWithUser } from '../api/usersSessions';

/**
 * Convert data to CSV format
 */
function convertToCSV(data: any[], headers: string[]): string {
  const rows = [headers.join(',')];
  
  data.forEach(item => {
    const values = headers.map(header => {
      const value = item[header];
      // Escape quotes and wrap in quotes if contains comma
      if (value === null || value === undefined) return '';
      const stringValue = String(value);
      if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    });
    rows.push(values.join(','));
  });
  
  return rows.join('\n');
}

/**
 * Trigger file download
 */
function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export users to CSV
 */
export function exportUsersToCSV(users: UserWithSessions[]) {
  const headers = [
    'uuid',
    'full_name',
    'nickname',
    'user_type',
    'is_active',
    'primary_language',
    'active_session_count',
    'total_session_count',
    'last_activity',
    'created_at',
  ];
  
  const csv = convertToCSV(users, headers);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  downloadFile(csv, `users_export_${timestamp}.csv`, 'text/csv');
}

/**
 * Export users to JSON
 */
export function exportUsersToJSON(users: UserWithSessions[]) {
  const json = JSON.stringify(users, null, 2);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  downloadFile(json, `users_export_${timestamp}.json`, 'application/json');
}

/**
 * Export sessions to CSV
 */
export function exportSessionsToCSV(sessions: SessionWithUser[]) {
  const headers = [
    'uuid',
    'user_uuid',
    'user_full_name',
    'user_nickname',
    'user_type',
    'device_uuid',
    'device_name',
    'device_type',
    'session_type',
    'is_active',
    'time_remaining',
    'created_at',
    'expires_at',
  ];
  
  const csv = convertToCSV(sessions, headers);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  downloadFile(csv, `sessions_export_${timestamp}.csv`, 'text/csv');
}

/**
 * Export sessions to JSON
 */
export function exportSessionsToJSON(sessions: SessionWithUser[]) {
  const json = JSON.stringify(sessions, null, 2);
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  downloadFile(json, `sessions_export_${timestamp}.json`, 'application/json');
}
