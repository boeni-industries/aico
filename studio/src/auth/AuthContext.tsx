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
    const storedProfile = getStoredUserProfile() as UserDto | null;
    if (!token || !storedUserUuid || !storedProfile) {
      return;
    }

    setState({ user: storedProfile, accessToken: token, refreshToken: null });
  }, []);

  const login = async (userUuid: string, pin: string) => {
    const response: AuthenticationResponseDto = await authenticateUser({ user_uuid: userUuid, pin });
    if (!response.success || !response.user || !response.jwt_token) {
      throw new Error(response.error || 'Authentication failed');
    }
    setAuthToken(response.jwt_token);
    setRefreshToken(response.refresh_token ?? null);
    setStoredUserUuid(response.user.uuid);
    setStoredUserProfile(response.user);
    setState({
      user: response.user,
      accessToken: response.jwt_token,
      refreshToken: response.refresh_token ?? null,
    });
  };

  const logout = () => {
    clearAuthToken();
    setRefreshToken(null);
    setStoredUserUuid(null);
    setStoredUserProfile(null);
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
