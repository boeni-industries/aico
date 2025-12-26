import React from 'react';
import { setAuthToken, clearAuthToken, getAuthToken, getStoredUserUuid, setStoredUserUuid } from '../api/config';
import { authenticateUser, AuthenticationResponseDto, UserDto, fetchUserProfile } from '../api/users';

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

  // On initial load, try to restore session from stored token + user UUID
  React.useEffect(() => {
    const token = getAuthToken();
    const storedUserUuid = getStoredUserUuid();
    if (!token || !storedUserUuid) {
      return;
    }

    let cancelled = false;

    async function hydrate(userUuid: string) {
      try {
        const user = await fetchUserProfile(userUuid);
        if (cancelled) return;
        setState({ user, accessToken: token, refreshToken: null });
      } catch {
        // If profile fetch fails (e.g. token expired), clear stale storage
        if (cancelled) return;
        clearAuthToken();
        setStoredUserUuid(null);
        setState({ user: null, accessToken: null, refreshToken: null });
      }
    }

    hydrate(storedUserUuid);

    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (userUuid: string, pin: string) => {
    const response: AuthenticationResponseDto = await authenticateUser({ user_uuid: userUuid, pin });
    if (!response.success || !response.user || !response.jwt_token) {
      throw new Error(response.error || 'Authentication failed');
    }
    setAuthToken(response.jwt_token);
    setStoredUserUuid(response.user.uuid);
    setState({
      user: response.user,
      accessToken: response.jwt_token,
      refreshToken: response.refresh_token ?? null,
    });
  };

  const logout = () => {
    clearAuthToken();
    setStoredUserUuid(null);
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
