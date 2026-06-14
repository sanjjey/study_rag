/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('academicos_user')); }
    catch { return null; }
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (username, password) => {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const { data } = await api.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('academicos_token', data.access_token);
    const u = { user_id: data.user_id, username: data.username };
    localStorage.setItem('academicos_user', JSON.stringify(u));
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (username, password) => {
    await api.post('/auth/register', { username, password });
    return login(username, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('academicos_token');
    localStorage.removeItem('academicos_user');
    setUser(null);
  }, []);

  useEffect(() => {
    const handle = () => setUser(null);
    window.addEventListener('auth:logout', handle);
    return () => window.removeEventListener('auth:logout', handle);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
