import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, normalizeError, TOKEN_KEY } from "../api/client";
import type { AuthResponse, User } from "../api/types";
import { AuthContext, type AuthContextValue } from "./context";

const USER_KEY = "climatesense.user";

function readStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(() => readStoredUser());
  const [isLoading, setIsLoading] = useState(Boolean(token));

  const persist = useCallback((nextToken: string | null, nextUser: User | null) => {
    if (nextToken) {
      localStorage.setItem(TOKEN_KEY, nextToken);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    if (nextUser) {
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    } else {
      localStorage.removeItem(USER_KEY);
    }
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!localStorage.getItem(TOKEN_KEY)) {
      setUser(null);
      return;
    }
    const response = await api.get<User>("/users/me/");
    localStorage.setItem(USER_KEY, JSON.stringify(response.data));
    setUser(response.data);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const storedToken = localStorage.getItem(TOKEN_KEY);
    if (!storedToken) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    api
      .get<User>("/users/me/")
      .then((response) => {
        if (cancelled) return;
        localStorage.setItem(USER_KEY, JSON.stringify(response.data));
        setUser(response.data);
        setToken(storedToken);
      })
      .catch((error: unknown) => {
        // Only a rejected token ends the session; an outage must not log people out.
        if (cancelled || normalizeError(error).status !== 401) return;
        persist(null, null);
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [persist]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.post<AuthResponse>("/auth/login/", { email, password });
      persist(response.data.token, response.data.user);
      return response.data.user;
    },
    [persist],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      const response = await api.post<AuthResponse>("/auth/register/", {
        email,
        password,
        display_name: displayName,
      });
      persist(response.data.token, response.data.user);
      return response.data.user;
    },
    [persist],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/");
    } catch {
      // Token may already be expired. Local credentials are still removed.
    } finally {
      persist(null, null);
    }
  }, [persist]);

  const updateUser = useCallback(
    (nextUser: User) => {
      localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
      setUser(nextUser);
    },
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token && user),
      isModerator: Boolean(user?.is_moderator),
      isLoading,
      login,
      register,
      logout,
      updateUser,
      refreshUser,
    }),
    [user, token, isLoading, login, register, logout, updateUser, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
