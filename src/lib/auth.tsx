import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, apiRequest, ensureCsrfToken } from "./api";
import { useRouter } from "./router";
import type { AppUser, AuthResponse, MeResponse, Role } from "./types";

type AuthContextValue = {
  user: AppUser | null;
  loading: boolean;
  devMode: boolean;
  login: (email: string, password: string) => Promise<AuthResponse>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<AuthResponse>;
  refresh: () => Promise<AppUser | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function homeForRole(role: Role): string {
  return (
    { rh: "/rh", lider: "/lider", instrutor: "/instrutor", funcionario: "/funcionario" }[role] ??
    "/"
  );
}

export function nextStepFor(user: AppUser): string {
  if (user.must_change_password) return "/trocar-senha";
  return homeForRole(user.role);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [devMode, setDevMode] = useState(false);
  const { navigate } = useRouter();

  const refresh = useCallback(async (): Promise<AppUser | null> => {
    try {
      const data = await apiRequest<MeResponse>("/api/auth/me");
      setUser(data.user);
      setDevMode(Boolean(data.dev_mode));
      return data.user;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
        return null;
      }
      throw error;
    }
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await ensureCsrfToken();
        const data = await apiRequest<MeResponse>("/api/auth/me");
        if (active) {
          setUser(data.user);
          setDevMode(Boolean(data.dev_mode));
        }
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiRequest<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiRequest<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
    } catch {
      // A sessão local é encerrada mesmo se o servidor já tiver expirado.
    }
    setUser(null);
    navigate("/", { replace: true });
  }, [navigate]);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const data = await apiRequest<AuthResponse>("/api/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    });
    setUser(data.user);
    return data;
  }, []);

  const value = useMemo(
    () => ({ user, loading, devMode, login, logout, changePassword, refresh }),
    [user, loading, devMode, login, logout, changePassword, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth precisa estar dentro de AuthProvider");
  return context;
}
