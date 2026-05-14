"use client";

import { useEffect, useState } from "react";

export type AuthState = {
  address: string | null;
  roles: string[];
  loaded: boolean;
};

function readToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )pantheon_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function useAuth(): AuthState & { token: string | null; signOut: () => void } {
  const [state, setState] = useState<AuthState>({
    address: null,
    roles: [],
    loaded: false,
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const addr = localStorage.getItem("pantheon_address");
    const rolesRaw = localStorage.getItem("pantheon_roles");
    let roles: string[] = [];
    try {
      roles = rolesRaw ? JSON.parse(rolesRaw) : [];
    } catch {
      roles = [];
    }
    setState({ address: addr, roles, loaded: true });
  }, []);

  function signOut() {
    document.cookie = "pantheon_token=; path=/; max-age=0";
    localStorage.removeItem("pantheon_address");
    localStorage.removeItem("pantheon_roles");
    window.location.href = "/signin";
  }

  return { ...state, token: readToken(), signOut };
}
