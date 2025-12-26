import { API_BASE_URL, getAuthToken, setAuthToken, getRefreshToken, setRefreshToken } from './config';
import { ensureSecureSession, wrapEncryptedRequestBody, unwrapEncryptedResponse } from '../transport/secureTransport';

export interface HttpRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
}

export async function httpJson<T>(options: HttpRequestOptions): Promise<T> {
  const { method = 'GET', path, query, body } = options;

  const url = new URL(path.replace(/^\//, ''), API_BASE_URL + '/');

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      url.searchParams.set(key, String(value));
    });
  }

  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // For protected API routes (everything under /api/v1 except health/handshake),
  // establish a secure session and send encrypted payloads.
  const isProtected = !path.startsWith('/health') && !path.startsWith('/handshake');
  if (isProtected) {
    const { clientId } = await ensureSecureSession();
    if (clientId) {
      headers['X-Client-ID'] = clientId;
    }
  }

  let response: Response;
  try {
    const requestBody =
      body === undefined || !isProtected ? body : wrapEncryptedRequestBody(body);

    if (requestBody !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    response = await fetch(url.toString(), {
      method,
      headers,
      body: requestBody !== undefined ? JSON.stringify(requestBody) : undefined,
    });
  } catch (e) {
    const message = (e as Error)?.message || 'Unknown network error';
    throw new Error(`Network error while calling ${url.toString()}: ${message}`);
  }

  if (!response.ok) {
    // If 401 and we have a refresh token, try to refresh and retry once
    if (response.status === 401 && getRefreshToken()) {
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        // Retry the original request with new token
        return httpJson<T>(options);
      }
    }
    
    const text = await response.text().catch(() => '');
    throw new Error(
      `HTTP ${response.status} ${response.statusText} when calling ${url.toString()}` +
        (text ? `: ${text}` : ''),
    );
  }

  // Some endpoints may return 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  const data = await response.json();
  return unwrapEncryptedResponse<T>(data);
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  // Prevent multiple simultaneous refresh attempts
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        return false;
      }

      // Ensure we have an active encryption session before refreshing token
      // This handles the case where both JWT and encryption session expired
      const { clientId } = await ensureSecureSession();
      if (!clientId) {
        return false;
      }

      // Prepare encrypted request body
      const requestBody = wrapEncryptedRequestBody({ refresh_token: refreshToken });

      const response = await fetch(`${API_BASE_URL}/users/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-ID': clientId,
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        return false;
      }

      const data = await response.json();
      const decryptedData = unwrapEncryptedResponse<{ success: boolean; jwt_token?: string; refresh_token?: string }>(data);
      
      if (decryptedData.success && decryptedData.jwt_token) {
        setAuthToken(decryptedData.jwt_token);
        // Update refresh token if backend rotates it
        if (decryptedData.refresh_token) {
          setRefreshToken(decryptedData.refresh_token);
        }
        return true;
      }

      return false;
    } catch {
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}
