import { createContext, useContext, useEffect, useState } from "react";
import { api, flushEvents } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authModal, setAuthModal] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    localStorage.setItem("token", data.access_token);
    setUser(data.user);
    await api("/progress/claim", { method: "POST" }).catch(() => {});
    await flushEvents();
    return data.user;
  }

  async function register(name, email, password) {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password })
    });
    localStorage.setItem("token", data.access_token);
    setUser(data.user);
    await api("/progress/claim", { method: "POST" }).catch(() => {});
    await flushEvents();
    return data.user;
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
  }

  function openAuth(mode = "login") {
    setAuthModal(mode);
  }

  function closeAuth() {
    setAuthModal(null);
  }

  async function updateProfile(data) {
    const updated = await api("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data)
    });
    setUser(updated);
    return updated;
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateProfile, authModal, openAuth, closeAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
