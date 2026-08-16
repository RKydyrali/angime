"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

export interface AuthState {
  token: string | null;
  role: "tenant" | "admin" | null;
  name: string;
  tenantId: string | null;
}

const AuthContext = createContext<{
  auth: AuthState;
  ready: boolean;
  login: (role: "tenant" | "admin", a: string, b: string) => Promise<void>;
  loginAsTenant: (tenantId: string) => Promise<void>;
  logout: () => void;
}>({
  auth: { token: null, role: null, name: "", tenantId: null },
  ready: false,
  login: async () => {},
  loginAsTenant: async () => {},
  logout: () => {},
});

function readAuth(): AuthState {
  const token = getToken();
  if (!token) return { token: null, role: null, name: "", tenantId: null };
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return {
      token,
      role: payload.role,
      name: payload.sub,
      tenantId: payload.tenant_id || null,
    };
  } catch {
    return { token: null, role: null, name: "", tenantId: null };
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({
    token: null,
    role: null,
    name: "",
    tenantId: null,
  });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setAuth(readAuth());
    setReady(true);
  }, []);

  const apply = (token: string) => {
    setToken(token);
    setAuth(readAuth());
  };

  const login = async (role: "tenant" | "admin", a: string, b: string) => {
    const path = role === "admin" ? "/api/auth/admin/login" : "/api/auth/tenant/login";
    const body =
      role === "admin" ? { username: a, password: b } : { email: a, password: b };
    const res = await api<{ token: string }>(path, { method: "POST", body });
    apply(res.token);
  };

  const loginAsTenant = async (tenantId: string) => {
    const res = await api<{ token: string }>(`/api/admin/tenants/${tenantId}/login-link`, {
      method: "POST",
    });
    apply(res.token);
  };

  const logout = () => {
    setToken(null);
    setAuth({ token: null, role: null, name: "", tenantId: null });
  };

  useEffect(() => {
    const onStorage = () => setAuth(readAuth());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <AuthContext.Provider value={{ auth, ready, login, loginAsTenant, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
