// Studio API configuration
//
// Base URL is expected to point at the AICO API Gateway REST endpoint.
// In development, this will usually be http://localhost:8771/api/v1
// (see config/defaults/core.yaml -> api_gateway.protocols.rest).
//
// For production, set REACT_APP_AICO_API_BASE_URL in the environment.

export const API_BASE_URL =
  process.env.REACT_APP_AICO_API_BASE_URL || 'http://localhost:8771/api/v1';

// Token provider – by default reads a JWT from localStorage.
// The token should be obtained via the normal AICO auth flow
// (e.g. gateway auth login or frontend login) and stored under this key.

const TOKEN_STORAGE_KEY = 'aico_jwt_token';
const REFRESH_TOKEN_STORAGE_KEY = 'aico_refresh_token';
const USER_UUID_STORAGE_KEY = 'aico_user_uuid';
const USER_PROFILE_STORAGE_KEY = 'aico_user_profile';

export function getAuthToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null | undefined) {
  try {
    if (!token) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // Swallow – storage may be unavailable (e.g. privacy mode).
  }
}

export function clearAuthToken() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage errors
  }
}

export function getStoredUserProfile(): unknown | null {
  try {
    const raw = window.localStorage.getItem(USER_PROFILE_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setStoredUserProfile(profile: unknown | null | undefined) {
  try {
    if (!profile) {
      window.localStorage.removeItem(USER_PROFILE_STORAGE_KEY);
    } else {
      window.localStorage.setItem(USER_PROFILE_STORAGE_KEY, JSON.stringify(profile));
    }
  } catch {
    // Ignore storage errors
  }
}

export function getStoredUserUuid(): string | null {
  try {
    return window.localStorage.getItem(USER_UUID_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredUserUuid(uuid: string | null | undefined) {
  try {
    if (!uuid) {
      window.localStorage.removeItem(USER_UUID_STORAGE_KEY);
    } else {
      window.localStorage.setItem(USER_UUID_STORAGE_KEY, uuid);
    }
  } catch {
    // Ignore storage errors
  }
}

export function getRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setRefreshToken(token: string | null | undefined) {
  try {
    if (!token) {
      window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // Ignore storage errors
  }
}

export { setRefreshToken as default };
