import React from 'react';
import {
  setAuthToken,
  clearAuthToken,
  getAuthToken,
  getStoredUserUuid,
  setStoredUserUuid,
  getStoredUserProfile,
  setStoredUserProfile,
  setRefreshToken,
} from '../api/config';
import { authenticateUser, AuthenticationResponseDto, UserDto } from '../api/users';
import { startTokenRefreshMonitoring, stopTokenRefreshMonitoring } from '../utils/tokenManager';
import {
  storeCredentials,
  getStoredCredentials,
  clearStoredCredentials,
  hasStoredCredentials,
} from '../utils/credentialStorage';

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

export interface AuthState {
  user: UserDto | null;
  accessToken: string | null;
  refreshToken: string | null;
}

interface AuthContextValue extends AuthState {
  login: (userUuid: string, pin: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = React.useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
  });

  // Internal authentication function (doesn't store credentials, used for auto re-auth)
  const performAuthentication = React.useCallback(async (userUuid: string, pin: string, storeCredentialsFlag: boolean = false) => {
    const response: AuthenticationResponseDto = await authenticateUser({ user_uuid: userUuid, pin });
    if (!response.success || !response.user || !response.jwt_token) {
      throw new Error(response.error || 'Authentication failed');
    }
    setAuthToken(response.jwt_token);
    setRefreshToken(response.refresh_token ?? null);
    setStoredUserUuid(response.user.uuid);
    setStoredUserProfile(response.user);
    
    // Store encrypted credentials if requested
    if (storeCredentialsFlag) {
      try {
        await storeCredentials(userUuid, pin);
        console.log('[AuthContext] Credentials stored securely for auto re-auth');
      } catch (error) {
        console.warn('[AuthContext] Failed to store credentials:', error);
      }
    }
    
    setState({
      user: response.user,
      accessToken: response.jwt_token,
      refreshToken: response.refresh_token ?? null,
    });
  }, []);

  // On initial load, try to restore session from stored token + user UUID
  React.useEffect(() => {
    const restoreSession = async () => {
      const token = getAuthToken();
      const storedUserUuid = getStoredUserUuid();
      const storedProfile = getStoredUserProfile() as UserDto | null;
      
      // If no token but we have stored credentials, try automatic re-authentication
      if (!token && hasStoredCredentials()) {
        console.log('[AuthContext] No token found but credentials available, attempting auto re-auth...');
        try {
          const credentials = await getStoredCredentials();
          if (credentials) {
            await performAuthentication(credentials.userUuid, credentials.pin, false);
            console.log('[AuthContext] Auto re-authentication successful');
            return;
          }
        } catch (error) {
          console.error('[AuthContext] Auto re-authentication failed:', error);
          clearStoredCredentials(); // Clear invalid credentials
        }
      }
      
      if (!token || !storedUserUuid || !storedProfile) {
        return;
      }

      // Import refreshTokenNow dynamically to avoid circular dependency
      const { refreshTokenNow } = await import('../utils/tokenManager');
      
      // Check if token is expired or expiring soon and refresh if needed
      try {
        const decoded = decodeJWT(token);
        if (decoded && decoded.exp) {
          const expiryTime = decoded.exp * 1000;
          const now = Date.now();
          const timeUntilExpiry = expiryTime - now;
          
          // If token is expired or expires in less than 5 minutes, refresh it now
          if (timeUntilExpiry < 5 * 60 * 1000) {
            console.log('[AuthContext] Token expired or expiring soon, refreshing before restoring session...');
            const refreshed = await refreshTokenNow();
            if (!refreshed) {
              console.warn('[AuthContext] Token refresh failed, attempting auto re-auth...');
              // Try automatic re-authentication with stored credentials
              try {
                const credentials = await getStoredCredentials();
                if (credentials) {
                  await performAuthentication(credentials.userUuid, credentials.pin, false);
                  console.log('[AuthContext] Auto re-authentication successful after refresh failure');
                  return;
                }
              } catch (error) {
                console.error('[AuthContext] Auto re-authentication failed:', error);
              }
              // If auto re-auth also failed, clear session
              clearAuthToken();
              setRefreshToken(null);
              setStoredUserUuid(null);
              setStoredUserProfile(null);
              clearStoredCredentials();
              return;
            }
            // Get the new token after refresh
            const newToken = getAuthToken();
            setState({ user: storedProfile, accessToken: newToken, refreshToken: null });
            return;
          }
        }
      } catch (error) {
        console.error('[AuthContext] Error checking token expiration:', error);
      }

      // Token is still valid, restore session
      setState({ user: storedProfile, accessToken: token, refreshToken: null });
    };

    restoreSession();
  }, [performAuthentication]);

  // Start/stop automatic token refresh monitoring based on authentication state
  React.useEffect(() => {
    if (state.user && state.accessToken) {
      // User is authenticated - start monitoring
      startTokenRefreshMonitoring();
      return () => {
        // Cleanup on unmount
        stopTokenRefreshMonitoring();
      };
    } else {
      // User is not authenticated - ensure monitoring is stopped
      stopTokenRefreshMonitoring();
    }
  }, [state.user, state.accessToken]);

  const login = async (userUuid: string, pin: string) => {
    await performAuthentication(userUuid, pin, true); // Store credentials on manual login
  };

  const logout = () => {
    stopTokenRefreshMonitoring();
    clearAuthToken();
    setRefreshToken(null);
    setStoredUserUuid(null);
    setStoredUserProfile(null);
    clearStoredCredentials(); // Clear encrypted credentials on explicit logout
    setState({ user: null, accessToken: null, refreshToken: null });
  };

  const value: AuthContextValue = {
    ...state,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
