/**
 * Token Manager - Proactive Token Refresh
 * 
 * Automatically refreshes JWT tokens before they expire to maintain
 * seamless user sessions without interruption.
 */

import { getAuthToken, setAuthToken, getRefreshToken, setRefreshToken } from '../api/config';
import { ensureSecureSession, wrapEncryptedRequestBody, unwrapEncryptedResponse } from '../transport/secureTransport';

const API_BASE_URL = process.env.REACT_APP_AICO_API_BASE_URL || 'http://localhost:8771/api/v1';

// JWT token typically expires in 1 hour (3600 seconds)
// Refresh 5 minutes before expiration to be safe
const REFRESH_BEFORE_EXPIRY_MS = 5 * 60 * 1000; // 5 minutes
const CHECK_INTERVAL_MS = 60 * 1000; // Check every minute

let refreshIntervalId: NodeJS.Timeout | null = null;
let isRefreshing = false;

/**
 * Decode JWT token to get expiration time
 */
function decodeJWT(token: string): { exp?: number } | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * Check if token needs refresh
 */
function shouldRefreshToken(): boolean {
  const token = getAuthToken();
  if (!token) return false;

  const decoded = decodeJWT(token);
  if (!decoded || !decoded.exp) return false;

  const expiryTime = decoded.exp * 1000; // Convert to milliseconds
  const now = Date.now();
  const timeUntilExpiry = expiryTime - now;

  // Refresh if token expires in less than 5 minutes
  return timeUntilExpiry < REFRESH_BEFORE_EXPIRY_MS && timeUntilExpiry > 0;
}

/**
 * Perform token refresh
 */
async function performTokenRefresh(): Promise<boolean> {
  if (isRefreshing) {
    console.log('[TokenManager] Refresh already in progress, skipping');
    return false;
  }

  try {
    isRefreshing = true;

    const refreshToken = getRefreshToken();
    console.log('[TokenManager] Refresh token available:', !!refreshToken);
    if (!refreshToken) {
      console.warn('[TokenManager] No refresh token available - cannot refresh');
      return false;
    }

    // Ensure we have an active encryption session
    console.log('[TokenManager] Establishing secure session...');
    const { clientId } = await ensureSecureSession();
    console.log('[TokenManager] Client ID:', clientId);
    if (!clientId) {
      console.warn('[TokenManager] Failed to establish secure session');
      return false;
    }

    // Prepare encrypted request
    const requestBody = wrapEncryptedRequestBody({ refresh_token: refreshToken });
    console.log('[TokenManager] Sending refresh request to:', `${API_BASE_URL}/users/refresh`);

    const response = await fetch(`${API_BASE_URL}/users/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-ID': clientId,
      },
      body: JSON.stringify(requestBody),
    });

    console.log('[TokenManager] Refresh response status:', response.status, response.statusText);
    
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unable to read error');
      console.error('[TokenManager] Token refresh failed:', response.status, errorText);
      return false;
    }

    const data = await response.json();
    const decryptedData = unwrapEncryptedResponse<{
      success: boolean;
      jwt_token?: string;
      refresh_token?: string;
    }>(data);

    console.log('[TokenManager] Decrypted response:', { 
      success: decryptedData.success, 
      hasJwtToken: !!decryptedData.jwt_token,
      hasRefreshToken: !!decryptedData.refresh_token 
    });

    if (decryptedData.success && decryptedData.jwt_token) {
      setAuthToken(decryptedData.jwt_token);
      
      // Update refresh token if backend rotates it
      if (decryptedData.refresh_token) {
        setRefreshToken(decryptedData.refresh_token);
      }

      console.log('[TokenManager] ✅ Token refreshed successfully');
      return true;
    }

    console.warn('[TokenManager] Refresh response did not contain valid token');
    return false;
  } catch (error) {
    console.error('[TokenManager] Token refresh error:', error);
    return false;
  } finally {
    isRefreshing = false;
  }
}

/**
 * Check and refresh token if needed
 */
async function checkAndRefreshToken(): Promise<void> {
  if (shouldRefreshToken()) {
    console.log('[TokenManager] Token expiring soon, refreshing...');
    await performTokenRefresh();
  }
}

/**
 * Start automatic token refresh monitoring
 */
export function startTokenRefreshMonitoring(): void {
  if (refreshIntervalId) {
    console.warn('[TokenManager] Monitoring already started');
    return;
  }

  console.log('[TokenManager] Starting automatic token refresh monitoring');

  // Check immediately on start
  checkAndRefreshToken();

  // Then check every minute
  refreshIntervalId = setInterval(() => {
    checkAndRefreshToken();
  }, CHECK_INTERVAL_MS);
}

/**
 * Stop automatic token refresh monitoring
 */
export function stopTokenRefreshMonitoring(): void {
  if (refreshIntervalId) {
    clearInterval(refreshIntervalId);
    refreshIntervalId = null;
    console.log('[TokenManager] Stopped token refresh monitoring');
  }
}

/**
 * Manually trigger token refresh
 */
export async function refreshTokenNow(): Promise<boolean> {
  console.log('[TokenManager] Manual token refresh requested');
  return performTokenRefresh();
}
