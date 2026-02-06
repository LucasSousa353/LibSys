import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { authApi, usersApi } from '../services/api';
import type { AuthState, User } from '../types';

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    token: localStorage.getItem('access_token'),
    user: null,
    role: (localStorage.getItem('user_role') as AuthState['role']) || null,
    mustResetPassword: localStorage.getItem('must_reset_password') === 'true',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }

    usersApi.me()
      .then((user: User) => {
        setState(prev => ({
          ...prev,
          isAuthenticated: true,
          token,
          user,
          role: user.role ?? prev.role,
          mustResetPassword: user.must_reset_password ?? prev.mustResetPassword,
        }));
        if (user.role) {
          localStorage.setItem('user_role', user.role);
        }
        if (typeof user.must_reset_password === 'boolean') {
          localStorage.setItem('must_reset_password', String(user.must_reset_password));
        }
      })
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('token_type');
        localStorage.removeItem('user_role');
        localStorage.removeItem('must_reset_password');
        setState({
          isAuthenticated: false,
          token: null,
          user: null,
          role: null,
          mustResetPassword: false,
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await authApi.login(email, password);
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('token_type', response.token_type);
      localStorage.setItem('user_role', response.role);
      localStorage.setItem('must_reset_password', String(response.must_reset_password));
      
      setState({
        isAuthenticated: true,
        token: response.access_token,
        user: null,
        role: response.role,
        mustResetPassword: response.must_reset_password,
      });
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('user_role');
    localStorage.removeItem('must_reset_password');
    setState({
      isAuthenticated: false,
      token: null,
      user: null,
      role: null,
      mustResetPassword: false,
    });
  };

  return (
    <AuthContext.Provider value={{ ...state, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
