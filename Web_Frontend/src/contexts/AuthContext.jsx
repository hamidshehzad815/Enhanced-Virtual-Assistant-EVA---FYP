import React, { createContext, useContext, useState, useEffect } from 'react';
import apiRequest from '../services/api';

const AuthContext = createContext(null);

/** Turn a thrown apiRequest error into { message, code, fieldErrors }. */
const parseApiError = (err, fallback) => {
  const data = err?.data || {};
  const raw = err?.message || '';
  const networkDown = err instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(raw);
  return {
    message: networkDown
      ? "Can't reach the server. Please check your connection and try again."
      : (data.message || raw || fallback),
    code: data.code,
    fieldErrors: data.errors && typeof data.errors === 'object' && !Array.isArray(data.errors) ? data.errors : {},
  };
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errors, setErrors] = useState({});

  const setAuthenticatedSession = (userData = null) => {
    setUser(userData);
    setIsAuthenticated(Boolean(userData || localStorage.getItem('access_token')));
    setErrors({});
  };

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setAuthenticatedSession(null);
      setIsLoading(false);
      return;
    }
    
    try {
      const response = await apiRequest('/api/auth/me');
      if (response.status === 'success' || response.data) {
        const userData = response.data?.user || response.data || response;
        setAuthenticatedSession(userData);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setAuthenticatedSession(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
    
    // Listen for global logout events (from API client on refresh expiry)
    const handleLogout = () => {
      logout();
    };
    window.addEventListener('auth-logout', handleLogout);
    return () => window.removeEventListener('auth-logout', handleLogout);
  }, []);

  const login = async (email, password) => {
    setIsLoading(true);
    setErrors({});
    try {
      const response = await apiRequest('/api/auth/login', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ email, password }),
      });

      if (response.success || response.status === 'success') {
        const tokens = response.data?.tokens;
        if (tokens) {
          localStorage.setItem('access_token', tokens.access_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);
        }
        
        const userData = response.data?.user || response.data;
        
        if (userData?.is_verified === false) {
          setIsLoading(false);
          return { success: true, isVerified: false, message: 'Email not verified' };
        }

        setAuthenticatedSession(userData);
        setIsLoading(false);
        return { success: true, isVerified: true };
      }
      
      const msg = response.message || response.msg || 'Login failed';
      setErrors({ general: msg });
      setIsLoading(false);
      return { success: false, message: msg };
    } catch (err) {
      const { message, code, fieldErrors } = parseApiError(err, 'Login failed');
      // Field-level problems (empty/invalid email) go under the inputs; credential,
      // verification and account-state problems are shown as one alert.
      setErrors(Object.keys(fieldErrors).length ? fieldErrors : { general: message });
      setIsLoading(false);
      return { success: false, message, code, fieldErrors };
    }
  };

  const signup = async (userData) => {
    setErrors({});
    try {
      const response = await apiRequest('/api/auth/register', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify(userData),
      });

      if (response.status === 'success' || response.success) {
        return {
          success: true,
          emailSent: response.data?.email_sent ?? true,
          message: response.message || 'Registration successful. Please verify your email.',
        };
      }
      return { success: false, message: response.message || 'Signup failed' };
    } catch (err) {
      const { message, fieldErrors } = parseApiError(err, 'Signup failed');
      setErrors(fieldErrors);
      return { success: false, message, fieldErrors };
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await apiRequest('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      console.error('Logout API call failed:', err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setAuthenticatedSession(null);
      setIsLoading(false);
    }
  };

  const updateProfile = async (profileData) => {
    setErrors({});
    try {
      const response = await apiRequest('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify(profileData),
      });
      if (response.status === 'success') {
        const updatedUser = response.data?.user || response.data || response;
        setUser(prev => ({ ...prev, ...updatedUser }));
        return { success: true };
      }
      return { success: false, message: response.message || 'Update failed' };
    } catch (err) {
      const field = err.field || (err.data?.field);
      const message = err.message || 'Failed to update profile';
      setErrors(field ? { [field]: message } : { general: message });
      return { success: false, message };
    }
  };

  const updateUserSnapshot = (updates) => {
    setUser(prev => (prev ? { ...prev, ...updates } : prev));
  };

  const forgotPassword = async (email) => {
    try {
      const response = await apiRequest('/api/auth/forgot-password', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ email }),
      });
      return { success: response.status === 'success' || response.success, message: response.message };
    } catch (err) {
      const { message, fieldErrors } = parseApiError(err, 'Failed to send reset link');
      return { success: false, message, fieldErrors };
    }
  };

  const resetPassword = async (token, new_password, confirm_password) => {
    try {
      const response = await apiRequest('/api/auth/reset-password', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ token, new_password, confirm_password }),
      });
      return { success: response.status === 'success' || response.success, message: response.message };
    } catch (err) {
      const { message, code, fieldErrors } = parseApiError(err, 'Failed to reset password');
      return { success: false, message, code, fieldErrors };
    }
  };

  const verifyEmailApi = async (token) => {
    try {
      const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
      const url = `${baseUrl}/api/auth/verify-email?token=${encodeURIComponent(token)}`;
      const response = await fetch(url, {
        method: 'GET',
      });
      if (response.ok) {
        return { success: true, message: 'Your email has been successfully verified. You can now log in.' };
      } else {
        try {
          const text = await response.text();
          const data = JSON.parse(text);
          return { success: false, message: data.message || data.msg || 'Verification failed' };
        } catch {
          return { success: false, message: 'This verification link is invalid or has expired.' };
        }
      }
    } catch (err) {
      return { success: false, message: err.message || 'Server not reachable' };
    }
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, errors, login, signup, logout, checkAuth, setAuthenticatedSession, updateProfile, updateUserSnapshot, forgotPassword, resetPassword, verifyEmailApi }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
