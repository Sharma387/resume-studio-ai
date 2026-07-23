import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import * as authService from '../services/authService';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthContextValue {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => string | null;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY_REFRESH = 'rsai_refresh_token';
const STORAGE_KEY_ACCESS = 'rsai_access_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY_ACCESS));
  const [refreshTokenValue, setRefreshTokenValue] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY_REFRESH));
  const [loading, setLoading] = useState(true);

  // On mount, try to restore session from stored tokens
  useEffect(() => {
    const storedAccess = localStorage.getItem(STORAGE_KEY_ACCESS);
    const storedRefresh = localStorage.getItem(STORAGE_KEY_REFRESH);
    if (storedAccess && storedRefresh) {
      authService.getCurrentUser(storedAccess)
        .then((res) => setUser(res.data))
        .catch(() => {
          // Token expired — try refresh
          authService.refreshToken(storedRefresh)
            .then((tokenRes) => {
              localStorage.setItem(STORAGE_KEY_ACCESS, tokenRes.data.access_token);
              localStorage.setItem(STORAGE_KEY_REFRESH, tokenRes.data.refresh_token);
              setAccessToken(tokenRes.data.access_token);
              setRefreshTokenValue(tokenRes.data.refresh_token);
              return authService.getCurrentUser(tokenRes.data.access_token);
            })
            .then((userRes) => setUser(userRes.data))
            .catch(() => {
              localStorage.removeItem(STORAGE_KEY_ACCESS);
              localStorage.removeItem(STORAGE_KEY_REFRESH);
              setAccessToken(null);
              setRefreshTokenValue(null);
            });
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authService.login(email, password);
    localStorage.setItem(STORAGE_KEY_ACCESS, res.data.tokens.access_token);
    localStorage.setItem(STORAGE_KEY_REFRESH, res.data.tokens.refresh_token);
    setAccessToken(res.data.tokens.access_token);
    setRefreshTokenValue(res.data.tokens.refresh_token);
    setUser(res.data.user);
  }, []);

  const register = useCallback(async (email: string, password: string, full_name: string) => {
    const res = await authService.register(email, password, full_name);
    localStorage.setItem(STORAGE_KEY_ACCESS, res.data.tokens.access_token);
    localStorage.setItem(STORAGE_KEY_REFRESH, res.data.tokens.refresh_token);
    setAccessToken(res.data.tokens.access_token);
    setRefreshTokenValue(res.data.tokens.refresh_token);
    setUser(res.data.user);
  }, []);

  const logout = useCallback(async () => {
    if (refreshTokenValue && accessToken) {
      try { await authService.logout(refreshTokenValue, accessToken); } catch { /* ignore */ }
    }
    localStorage.removeItem(STORAGE_KEY_ACCESS);
    localStorage.removeItem(STORAGE_KEY_REFRESH);
    setAccessToken(null);
    setRefreshTokenValue(null);
    setUser(null);
  }, [refreshTokenValue, accessToken]);

  const getAccessToken = useCallback(() => accessToken, [accessToken]);

  return (
    <AuthContext.Provider value={{
      user, accessToken, refreshToken: refreshTokenValue,
      isAuthenticated: !!user, loading,
      login, register, logout, getAccessToken,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
