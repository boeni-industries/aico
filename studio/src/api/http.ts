import { API_BASE_URL, getAuthToken } from './config';
import { ensureSecureSession, wrapEncryptedRequestBody, unwrapEncryptedResponse, getClientId } from '../transport/secureTransport';

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
